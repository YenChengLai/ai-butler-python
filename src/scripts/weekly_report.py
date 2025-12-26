import os
import sys
import datetime
import pytz
import logging
import json  # 新增 json
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    FlexMessage,
    FlexContainer,
)

sys.path.append(os.getcwd())

from src.skills.calendar import CalendarSkills
from src.utils.flex_templates import generate_overview_flex

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WeeklyReport")


def main():
    access_token = os.getenv("CHANNEL_ACCESS_TOKEN")
    # ✅ Fix: 去除空白
    target_id = os.getenv("TARGET_ID", "").strip()

    if not access_token or not target_id:
        logger.error(
            "❌ Missing environment variables: CHANNEL_ACCESS_TOKEN or TARGET_ID"
        )
        return

    logger.info("📅 Initializing Calendar Skill...")
    skills = CalendarSkills()

    tw_tz = pytz.timezone("Asia/Taipei")
    now = datetime.datetime.now(tw_tz)

    days_ahead = 7 - now.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    next_monday = now + datetime.timedelta(days=days_ahead)
    next_monday = next_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    next_sunday = next_monday + datetime.timedelta(
        days=6, hours=23, minutes=59, seconds=59
    )

    time_min = next_monday.isoformat()
    time_max = next_sunday.isoformat()

    logger.info(f"🔍 Querying events from {time_min} to {time_max}")

    result = skills.list_events(time_min=time_min, time_max=time_max)

    if not result["success"]:
        logger.error(f"❌ Query failed: {result['message']}")
        return

    events = result["events"]
    logger.info(f"✅ Found {len(events)} events.")

    flex_json = generate_overview_flex(events)

    if "header" in flex_json:
        flex_json["header"]["contents"][0]["contents"][0]["text"] = "下週行程預告"

    # ✅ Debug: 印出目標 ID (遮蔽部分) 與 JSON 結構
    masked_id = (
        target_id[:4] + "*" * 4 + target_id[-4:] if len(target_id) > 8 else "***"
    )
    logger.info(f"📤 Sending Push Message to {masked_id}")
    # --- 新增這段 Debug 用 ---
    from linebot.v3.messaging import TextMessage  # 記得確認上面有 import

    logger.info(f"📦 Flex Payload (Debug): {json.dumps(flex_json, ensure_ascii=False)}")
    # -----------------------

    configuration = Configuration(access_token=access_token)

    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message(
                PushMessageRequest(
                    to=target_id,
                    messages=[
                        # 🧪 測試用：先傳純文字，排除 JSON 格式錯誤的可能性
                        TextMessage(text=f"測試連線成功！下週有 {len(events)} 個行程。")
                        # 原本的 Flex Message 先註解掉
                        # FlexMessage(
                        #     alt_text="下週行程預告",
                        #     contents=FlexContainer.from_dict(flex_json)
                        # )
                    ],
                )
            )
        logger.info("✅ Weekly report sent successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to send message: {e}")
        if hasattr(e, "body"):
            logger.error(f"🔍 API Response Body: {e.body}")
