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
    FlexMessage,
    FlexContainer,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# 引入自訂模組
from src.services.gcal_service import GCalService
from src.utils.flex_templates import (
    generate_create_success_flex,
    generate_overview_flex,
)

# 1. Setup
load_dotenv()

# 使用 print 代替 logger，確保在 GCP Log 一定看得到
print("🚀 System Initializing...")

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    print("❌ Critical Error: Missing LINE Environment Variables!")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-3-flash-preview")

calendar_service = None


def get_calendar_service():
    global calendar_service
    if not calendar_service:
        calendar_service = GCalService()
    return calendar_service


def get_gemini_response(user_text):
    tw_now = datetime.datetime.now(pytz.timezone("Asia/Taipei")).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # 使用 pathlib 確保路徑正確
    current_dir = pathlib.Path(__file__).parent
    prompt_path = current_dir / "src" / "prompts" / "system_prompt.txt"

    print(f"📂 Reading prompt from: {prompt_path}")

    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
    except Exception as e:
        print(f"❌ Error reading prompt file: {e}")
        return None

    prompt = template.replace("{{CURRENT_TIME}}", tw_now).replace(
        "{{USER_INPUT}}", user_text
    )

    try:
        print("🧠 Calling Gemini API...")
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        print(f"🧠 Gemini Response: {clean_text}")
        return json.loads(clean_text)
    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        return None


# 2. Cloud Function Entry
@functions_framework.http
def webhook(request):
    print("📨 Webhook Triggered!")

    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    print(f"📨 Body received: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ Invalid Signature")
        return "Invalid signature", 400
    except Exception as e:
        print(f"❌ Unknown Error in handler: {e}")
        return "Error", 500

    return "OK"


# 3. Message Handler
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    print("📍 Entering handle_message")

    user_msg = event.message.text.strip()
    user_id = event.source.user_id
    source_type = event.source.type

    print(f"👤 User: {user_id} | Type: {source_type} | Msg: {user_msg}")

    # 群組喚醒詞檢查
    is_group = source_type in ["group", "room"]
    trigger_word = "管家"

    if is_group:
        if not user_msg.startswith(trigger_word):
            print(f"🔇 Group message ignored (No trigger word): {user_msg}")
            return
        user_msg = user_msg[len(trigger_word) :].strip()
        print(f"🔔 Group trigger activated. Process content: {user_msg}")

    # 呼叫 AI
    analysis = get_gemini_response(user_msg)
    if not analysis:
        print("⚠️ Gemini returned None, stopping.")
        return

    action = analysis.get("action") or analysis.get("intent")
    params = analysis.get("params") or analysis.get("parameters") or {}

    print(f"🤖 Action: {action}")

    reply_messages = []
    cal = get_calendar_service()
    action = analysis.get("action")
    params = analysis.get("params", {})

    try:
        if action == "create":
            print("📅 Executing Create Event...")
            result = cal.create_event(params)
            if result["success"]:
                flex_json = generate_create_success_flex(params)
                reply_messages.append(
                    FlexMessage(
                        alt_text="行程已建立",
                        contents=FlexContainer.from_dict(flex_json),
                    )
                )
            else:
                reply_messages.append(
                    TextMessage(text=f"❌ 建立失敗: {result['message']}")
                )

        elif action == "batch_create":
            events = params.get("events", [])
            print(f"📅 Batch creating {len(events)} events...")
            success_count = 0
            for evt in events:
                if cal.create_event(evt)["success"]:
                    success_count += 1
            reply_messages.append(
                TextMessage(text=f"✅ 批量建立完成！成功: {success_count} 筆")
            )

        elif action == "query":
            print("📅 Querying events...")
            result = cal.list_events(params.get("timeMin"), params.get("timeMax"))
            if result["success"]:
                flex_json = generate_overview_flex(result["events"])
                reply_messages.append(
                    FlexMessage(
                        alt_text="行程總覽", contents=FlexContainer.from_dict(flex_json)
                    )
                )
            else:
                reply_messages.append(
                    TextMessage(text=f"❌ 查詢失敗: {result['message']}")
                )

        elif action == "chat":
            reply_messages.append(TextMessage(text=analysis.get("response", "嗯嗯")))

        elif action == "delete":
            reply_messages.append(TextMessage(text="🗑️ 刪除功能尚未實作"))

        # 發送回覆
        if reply_messages:
            print(f"📤 Sending {len(reply_messages)} reply messages...")
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token, messages=reply_messages
                    )
                )
            print("✅ Reply sent successfully")
        else:
            print("⚠️ No reply messages generated.")

    except Exception as e:
        print(f"❌ Error during processing/replying: {e}")
