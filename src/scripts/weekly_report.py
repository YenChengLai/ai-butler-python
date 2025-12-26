import os
import sys
import datetime
import pytz
import logging
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    FlexMessage,
    FlexContainer,
)

# 為了能 import 專案模組，將根目錄加入 sys.path
sys.path.append(os.getcwd())

from src.skills.calendar import CalendarSkills
from src.utils.flex_templates import generate_overview_flex

# 設定 Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WeeklyReport")


def main():
    # 1. 檢查必要環境變數
    access_token = os.getenv("CHANNEL_ACCESS_TOKEN")
    target_id = os.getenv("TARGET_ID")  # 這可以是 Group ID 或 User ID

    if not access_token or not target_id:
        logger.error(
            "❌ Missing environment variables: CHANNEL_ACCESS_TOKEN or TARGET_ID"
        )
        return

    # 2. 初始化 Skill (直接重用既有的邏輯！)
    logger.info("📅 Initializing Calendar Skill...")
    skills = CalendarSkills()

    # 3. 計算時間範圍 (下週一 ~ 下週日)
    tw_tz = pytz.timezone("Asia/Taipei")
    now = datetime.datetime.now(tw_tz)

    # 找到下一個星期一
    days_ahead = 7 - now.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    next_monday = now + datetime.timedelta(days=days_ahead)
    next_monday = next_monday.replace(hour=0, minute=0, second=0, microsecond=0)

    # 結束時間為下週日晚上 23:59
    next_sunday = next_monday + datetime.timedelta(
        days=6, hours=23, minutes=59, seconds=59
    )

    time_min = next_monday.isoformat()
    time_max = next_sunday.isoformat()

    logger.info(f"🔍 Querying events from {time_min} to {time_max}")

    # 4. 執行查詢
    result = skills.list_events(time_min=time_min, time_max=time_max)

    if not result["success"]:
        logger.error(f"❌ Query failed: {result['message']}")
        return

    events = result["events"]
    logger.info(f"✅ Found {len(events)} events.")

    # 5. 產生 Flex Message
    # 如果沒行程，我們也可以選擇不通知，或是傳送「下週無行程」
    flex_json = generate_overview_flex(events)

    # 修改標題讓它看起來像週報
    if "header" in flex_json:
        flex_json["header"]["contents"][0]["contents"][0]["text"] = "下週行程預告"

    # 6. 發送 Push Message
    logger.info("📤 Sending Push Message...")
    configuration = Configuration(access_token=access_token)

    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message(
                PushMessageRequest(
                    to=target_id,
                    messages=[
                        FlexMessage(
                            alt_text="下週行程預告",
                            contents=FlexContainer.from_dict(flex_json),
                        )
                    ],
                )
            )
        logger.info("✅ Weekly report sent successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to send message: {e}")


if __name__ == "__main__":
    main()
