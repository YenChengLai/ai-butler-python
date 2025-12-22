import os
import json
import logging
import datetime
import pytz
import pathlib
import functions_framework
from dotenv import load_dotenv
import google.generativeai as genai

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

# 引入 Agent
from src.agents.calendar import CalendarAgent

# 1. Setup & Production Logging
load_dotenv()

# 設定 Logging 格式，這在 GCP Logs Explorer 會比較好讀
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MainGateway")

logger.info("🚀 System Initializing...")

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    logger.critical("❌ Critical Error: Missing LINE Environment Variables!")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-3-flash-preview")

# Agent Instances (Singleton pattern recommended for Cloud Functions)
calendar_agent = CalendarAgent()


def get_gemini_response(user_text):
    tw_now = datetime.datetime.now(pytz.timezone("Asia/Taipei")).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    current_dir = pathlib.Path(__file__).parent
    prompt_path = current_dir / "src" / "prompts" / "system_prompt.txt"

    logger.info(f"📂 Reading prompt from: {prompt_path}")

    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
    except Exception as e:
        logger.error(f"❌ Error reading prompt file: {e}")
        return None

    prompt = template.replace("{{CURRENT_TIME}}", tw_now).replace(
        "{{USER_INPUT}}", user_text
    )

    try:
        logger.info("🧠 Calling Gemini API...")
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        logger.info(f"🧠 Gemini Response: {clean_text}")
        return json.loads(clean_text)
    except Exception as e:
        logger.error(f"❌ Gemini Error: {e}")
        return None


# 2. Cloud Function Entry
@functions_framework.http
def webhook(request):
    # 這裡可以保留 print，因為這是最外層的 HTTP 請求紀錄，GCP 會自動捕捉 request log
    # 但使用 logger 比較統一

    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    # logger.debug 只有在設定 level=DEBUG 時才會顯示，適合大量資料
    # 這裡為了 debug 方便先用 info，上線穩定後可改 debug
    logger.info(f"📨 Webhook Triggered. Body length: {len(body)}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.warning("❌ Invalid Signature")
        return "Invalid signature", 400
    except Exception as e:
        logger.error(f"❌ Unknown Error in handler: {e}")
        return "Error", 500

    return "OK"


# 3. Message Handler (The Router)
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    logger.info("📍 Entering handle_message")

    user_msg = event.message.text.strip()
    source_type = event.source.type

    # 群組喚醒詞檢查
    is_group = source_type in ["group", "room"]
    trigger_word = "管家"

    if is_group:
        if not user_msg.startswith(trigger_word):
            return
        user_msg = user_msg[len(trigger_word) :].strip()
        logger.info(f"🔔 Group trigger activated: {user_msg}")

    # Step 1: 呼叫 AI 判斷意圖
    analysis = get_gemini_response(user_msg)
    if not analysis:
        return

    # 相容性處理 (intent/action)
    action = analysis.get("action") or analysis.get("intent")
    params = analysis.get("params") or analysis.get("parameters") or {}

    logger.info(f"🤖 Routed Action: {action}")

    reply_messages = []

    # Step 2: 路由分發 (Dispatcher)
    try:
        # [Route 1] Calendar Agent
        # 目前我們的 Prompt 還沒區分 Domain，所以先假設 create/query/batch_create 都是 Calendar
        # 未來加入 Expense 時，我們會在 Prompt 裡區分 action 為 'calendar_create' 或 'expense_create'
        if action in ["create", "batch_create", "query", "delete"]:
            reply_messages = calendar_agent.handle_intent(action, params)

        # [Route 2] Chat / Fallback
        elif action == "chat":
            reply_messages.append(TextMessage(text=analysis.get("response", "嗯嗯")))

        # [Route 3] Future Expense Agent
        # elif action in ["expense_create", "expense_query"]:
        #     reply_messages = expense_agent.handle_intent(action, params)

        else:
            logger.warning(f"⚠️ Unknown action: {action}")
            reply_messages.append(TextMessage(text="我不太確定該怎麼處理這個指令 🤔"))

        # Step 3: 發送回覆
        if reply_messages:
            logger.info(f"📤 Sending {len(reply_messages)} reply messages...")
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token, messages=reply_messages
                    )
                )
            logger.info("✅ Reply sent successfully")
        else:
            logger.warning("⚠️ No reply messages generated from agents.")

    except Exception as e:
        logger.error(f"❌ Critical Error in Dispatcher: {e}")
