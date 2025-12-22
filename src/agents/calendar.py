import logging
from linebot.v3.messaging import TextMessage, FlexMessage, FlexContainer
from src.services.gcal_service import GCalService
from src.utils.flex_templates import (
    generate_create_success_flex,
    generate_overview_flex,
)

logger = logging.getLogger(__name__)


class CalendarAgent:
    def __init__(self):
        self.cal_service = GCalService()

    def handle_intent(self, action, params):
        """
        處理與日曆相關的意圖，並回傳 LINE 訊息物件列表
        """
        logger.info(f"📅 CalendarAgent processing action: {action}")
        reply_messages = []

        try:
            if action == "create":
                logger.info("Executing Create Event...")
                result = self.cal_service.create_event(params)
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
                logger.info(f"Executing Batch Create for {len(events)} events...")
                success_count = 0
                for evt in events:
                    if self.cal_service.create_event(evt)["success"]:
                        success_count += 1
                reply_messages.append(
                    TextMessage(text=f"✅ 批量建立完成！成功: {success_count} 筆")
                )

            elif action == "query":
                logger.info("Executing Query...")
                result = self.cal_service.list_events(
                    params.get("timeMin"), params.get("timeMax")
                )
                if result["success"]:
                    flex_json = generate_overview_flex(result["events"])
                    reply_messages.append(
                        FlexMessage(
                            alt_text="行程總覽",
                            contents=FlexContainer.from_dict(flex_json),
                        )
                    )
                else:
                    reply_messages.append(
                        TextMessage(text=f"❌ 查詢失敗: {result['message']}")
                    )

            elif action == "delete":
                reply_messages.append(TextMessage(text="🗑️ 刪除功能尚未實作"))

            else:
                # 如果是 chat 或其他不認識的 action，這裡回傳 None，讓 Router 決定怎麼辦
                return None

        except Exception as e:
            logger.error(f"Error in CalendarAgent: {e}")
            reply_messages.append(TextMessage(text="❌ 日曆處理發生錯誤"))

        return reply_messages
