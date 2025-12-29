import os
import sys
import logging
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
)

# 設定 Logging 為 INFO，並強制輸出到 stdout
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("WeeklyReport")


def main():
    logger.info("🚀 Starting Weekly Report Script (Debug Mode)...")

    access_token = os.getenv("CHANNEL_ACCESS_TOKEN")
    target_id = os.getenv("TARGET_ID", "").strip()

    logger.info(f"🔑 Token Check: {'OK' if access_token else 'MISSING'}")

    # 遮罩 ID 檢查
    if target_id:
        masked = (
            target_id[:4] + "****" + target_id[-4:] if len(target_id) > 8 else "***"
        )
        logger.info(f"🎯 Target ID: {masked} (Length: {len(target_id)})")
    else:
        logger.error("❌ Target ID is MISSING or EMPTY!")
        return

    # 初始化設定
    configuration = Configuration(access_token=access_token)

    try:
        logger.info("📡 Attempting to connect to LINE API...")
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)

            # 🔥 極簡測試：只傳純文字，排除 Flex Message 格式錯誤的可能性
            logger.info("📤 Sending SIMPLE TEXT message...")
            line_bot_api.push_message(
                PushMessageRequest(
                    to=target_id,
                    messages=[
                        TextMessage(
                            text="🤖【系統測試】GitHub Action 自動排程連線成功！"
                        )
                    ],
                )
            )
        logger.info("✅ SUCCESS! Message sent.")

    except Exception as e:
        logger.error("❌ FAILURE! Could not send message.")
        logger.error(f"💥 Error Details: {e}")
        if hasattr(e, "body"):
            logger.error(f"🔍 API Body: {e.body}")


if __name__ == "__main__":
    main()
