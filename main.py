import os
import json
import logging
import functions_framework
import pathlib
from dotenv import load_dotenv

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# 引入你的 Agent
from src.agents.calendar import CalendarAgent
from src.agents.expense import ExpenseAgent
from src.services.llm.factory import create_llm_provider

# 1. Setup & Config
load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MainRouter")

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    logger.critical("❌ Critical Error: Missing LINE environment variables (CHANNEL_ACCESS_TOKEN / CHANNEL_SECRET)!")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 設定 Router LLM (求快，用於意圖分類)
router_llm = create_llm_provider(role="router")

# 初始化 Agents
calendar_agent = CalendarAgent()
expense_agent = ExpenseAgent()


def get_router_intent(user_text):
    """
    [Router] 唯一的職責：分類
    讀取 system_prompt.txt (分類專用 Prompt)
    回傳: "CALENDAR", "EXPENSE", or "CHAT"
    """
    current_dir = pathlib.Path(__file__).parent
    prompt_path = current_dir / "src" / "prompts" / "system_prompt.txt"

    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
    except Exception as e:
        logger.error("❌ Error reading system prompt: %s", e)
        return "CHAT"  # 讀不到 Prompt 就當聊天

    # Router 不需要時間參數，只需要分類
    prompt = template.replace("{{USER_INPUT}}", user_text).replace(
        "{{CURRENT_TIME}}", ""
    )

    try:
        data = router_llm.parse_json_response(prompt)
        intent = data.get("intent", "CHAT")
        return intent
    except Exception as e:
        logger.error("❌ Router Decision Error: %s", e)
        return "CHAT"


# 2. Cloud Function Entry
@functions_framework.http
def webhook(request):
    signature = request.headers.get("X-Line-Signature")
    try:
        body = request.get_data(as_text=True)
        handler.handle(body, signature)
    except InvalidSignatureError:
        return "Invalid signature", 400
    except Exception as e:
        logger.error("Webhook Error: %s", e)
        return "Error", 500
    return "OK"


# 3. Message Handler
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_msg = event.message.text.strip()
    source_type = event.source.type

    # 群組喚醒檢查 (在群組內必須加 "管家")
    is_group = source_type in ["group", "room"]
    trigger_word = "管家"

    if is_group:
        if not user_msg.startswith(trigger_word):
            return
        user_msg = user_msg[len(trigger_word) :].strip()

    logger.info("📨 Processing: %s", user_msg)

    # [Step 1] Router 分流 (分類)
    intent = get_router_intent(user_msg)
    logger.info("🚦 Router Intent: %s", intent)

    reply_messages = []

    # [Step 2] 派發給專屬 Agent (解析 + 執行)
    try:
        if intent == "CALENDAR":
            reply_messages = calendar_agent.handle_message(user_msg)

        elif intent == "EXPENSE":
            reply_messages = expense_agent.handle_message(
                user_msg, user_id=event.source.user_id
            )
        else:
            # CHAT 或 未知，選擇忽略以免打擾
            pass

        # [Step 3] 回覆 LINE
        if reply_messages:
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token, messages=reply_messages
                    )
                )
    except Exception as e:
        logger.error("❌ Dispatch Error: %s", e)
