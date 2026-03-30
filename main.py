import os
import json
import logging
import asyncio
import threading
import functions_framework
import pathlib
from dotenv import load_dotenv

from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    AsyncApiClient,
    AsyncMessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.webhook import WebhookParser

# 引入你的 Agent 與 Services
from src.agents.calendar import CalendarAgent
from src.agents.expense import ExpenseAgent
from src.agents.chat import ChatAgent
from src.agents.memory_parser import MemoryParser
from src.services.llm.factory import create_llm_provider
from src.services.llm.embedding import EmbeddingService
from src.services.firestore_service import AsyncFirestoreService

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

# ✅ 冷啟動優化：利用 Lazy Singleton 避免每次 Request 重新分配資源，同時避免 Import 時拋出 event loop 錯誤
parser = WebhookParser(CHANNEL_SECRET)

_line_bot_api_instance = None

async def get_line_bot_api():
    global _line_bot_api_instance
    if _line_bot_api_instance is None:
        # 這裡有 event loop，初始化 aiohttp 才不會拋錯
        async_api_client = AsyncApiClient(configuration)
        _line_bot_api_instance = AsyncMessagingApi(async_api_client)
    return _line_bot_api_instance

router_llm = create_llm_provider(role="router")
calendar_agent = CalendarAgent()
expense_agent = ExpenseAgent()
chat_agent = ChatAgent()
memory_parser = MemoryParser()

# Singleton 實例
embedding_service = EmbeddingService()
firestore_service = AsyncFirestoreService()

async def get_router_intent(user_text) -> tuple[str, bool]:
    """
    [Router] 非同步意圖分類
    回傳: intent (str), needs_memory (bool)
    """
    current_dir = pathlib.Path(__file__).parent
    prompt_path = current_dir / "src" / "prompts" / "system_prompt.txt"

    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
    except Exception as e:
        logger.error("❌ Error reading system prompt: %s", e)
        return "CHAT", False  # 讀不到 Prompt 就當一般聊天

    prompt = template.replace("{{USER_INPUT}}", user_text).replace(
        "{{CURRENT_TIME}}", ""
    )

    try:
        data = await router_llm.aparse_json_response(prompt)
        intent = data.get("intent", "CHAT")
        needs_memory = data.get("needs_memory", False)
        return intent, needs_memory
    except Exception as e:
        logger.error("❌ Router Decision Error: %s", e)
        return "CHAT", False


# ========================================================
# 2. Event Loop 背景執行緒 (修復 WSGI / Async 衝突與 Gunicorn Fork)
# ========================================================
_shared_loop = None
_loop_thread = None

def _start_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def get_shared_loop():
    global _shared_loop, _loop_thread
    if _shared_loop is None:
        # 在 Worker 內真正收到第一個 request 時才建立 Thread，避免被 Gunicorn pre-fork 殺掉
        _shared_loop = asyncio.new_event_loop()
        _loop_thread = threading.Thread(target=_start_background_loop, args=(_shared_loop,), daemon=True)
        _loop_thread.start()
    return _shared_loop

# 3. Cloud Function Entry (Sync Wrapper)
@functions_framework.http
def webhook(request):
    signature = request.headers.get("X-Line-Signature")
    try:
        body = request.get_data(as_text=True)
        
        # 委派給共用的 Event Loop 執行
        loop = get_shared_loop()
        future = asyncio.run_coroutine_threadsafe(
            process_webhook_async(body, signature), loop
        )
        return future.result()
    except InvalidSignatureError:
        return "Invalid signature", 400
    except Exception as e:
        logger.error("Webhook Error: %s", e)
        return "Error", 500


async def process_webhook_async(body, signature):
    events = parser.parse(body, signature)
    
    tasks = []
    for event in events:
        if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
            tasks.append(handle_message(event))
            
    if tasks:
        await asyncio.gather(*tasks)
    return "OK", 200
# 4. Message Handler (Async)
async def handle_message(event):
    user_msg = event.message.text.strip()
    source_type = event.source.type
    user_id = event.source.user_id

    # 群組喚醒檢查 (在群組內必須加 "管家")
    is_group = source_type in ["group", "room"]
    trigger_word = "管家"

    if is_group:
        if not user_msg.startswith(trigger_word):
            return
        user_msg = user_msg[len(trigger_word) :].strip()

    logger.info("📨 Processing: %s", user_msg)

    # ==========================
    # 並發處理 Intent 與 Embedding
    # ==========================
    embedding_task = asyncio.create_task(embedding_service.get_embedding(user_msg))
    intent_task = asyncio.create_task(get_router_intent(user_msg))

    # A & B 平行執行
    embedding, (intent, needs_memory) = await asyncio.gather(embedding_task, intent_task)
    
    logger.info("🚦 Router Intent: %s, Needs Memory: %s", intent, needs_memory)

    reply_messages = []

    try:
        # ==========================
        # Action 分發
        # ==========================
        if intent == "CALENDAR":
            reply_messages = await calendar_agent.handle_message(user_msg)

        elif intent == "EXPENSE":
            reply_messages = await expense_agent.handle_message(
                user_msg, user_id=user_id
            )
            
        else:
            # CHAT 或 未知，先去 DB 撈回憶
            memories = await firestore_service.search_memories(
                query_embedding=embedding,
                user_id=user_id,
                limit=3
            )
            # 整合並發送給 Chat Agent
            reply_messages = await chat_agent.handle_message(user_msg, memories)

        # 若是一般對話或功能，但需要紀錄 Memory
        if needs_memory:
            # 啟動背景 Task 提取記憶與存入 DB，不阻礙 Main Thread 的回應
            async def memory_workflow():
                parsed_mem = await memory_parser.parse_memory(user_msg)
                await firestore_service.save_memory(
                    user_id=user_id,
                    content=user_msg,
                    summary=parsed_mem['summary'],
                    tags=parsed_mem['tags'],
                    memory_type=parsed_mem['memory_type'],
                    embedding=embedding
                )
            
            asyncio.create_task(memory_workflow())

        # ==========================
        # 回覆 LINE
        # ==========================
        if reply_messages:
            api = await get_line_bot_api()
            await api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token, messages=reply_messages
                )
            )
            
    except Exception as e:
        logger.error("❌ Dispatch Error: %s", e)
