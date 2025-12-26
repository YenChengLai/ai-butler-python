import logging
from src.services.gcal_service import GCalService

logger = logging.getLogger(__name__)


class CalendarSkills:
    def __init__(self):
        self.service = GCalService()

    def create_event(
        self,
        title: str,
        start_time: str,
        end_time: str,
        location: str = "",
        description: str = "",
    ):
        """[Skill] 建立行程"""
        event_data = {
            "title": title,
            "startTime": start_time,
            "endTime": end_time,
            "location": location,
            "description": description,
        }
        return self.service.create_event(event_data)

    def list_events(self, time_min: str, time_max: str = None):
        """[Skill] 查詢行程"""
        return self.service.list_events(time_min, time_max)

    def delete_event_by_query(self, time_min: str, keyword: str = ""):
        """
        [Skill] 刪除行程 (智慧搜尋刪除)
        1. 根據 time_min 抓取該時段附近的行程
        2. 若有 keyword，篩選標題
        3. 刪除最吻合的那一筆
        """
        logger.info(f"🗑️ Skill: Delete search | Time: {time_min} | Key: {keyword}")

        # 1. 搜尋行程 (範圍設為該時間點的當天)
        # 簡單起見，我們查該時間點往後 24 小時內的
        query_result = self.service.list_events(time_min)
        if not query_result["success"]:
            return {"success": False, "message": "搜尋行程失敗，無法刪除"}

        events = query_result["events"]
        target_event = None

        # 2. 篩選邏輯
        for evt in events:
            # 如果有提供關鍵字，必須包含關鍵字
            if keyword and keyword not in evt.get("summary", ""):
                continue

            # 如果沒關鍵字，預設刪除找到的第一筆 (通常是時間最近的)
            target_event = evt
            break

        # 3. 執行刪除
        if target_event:
            del_result = self.service.delete_event(target_event["id"])
            if del_result["success"]:
                return {"success": True, "deleted_event": target_event}
            else:
                return {"success": False, "message": del_result["message"]}
        else:
            return {"success": False, "message": "找不到符合條件的行程可以刪除"}

    def reschedule_event(
        self,
        old_time_min: str,
        old_keyword: str,
        new_title: str,
        new_start_time: str,
        new_end_time: str,
    ):
        """
        [Skill] 改期 (Reschedule)
        邏輯：先刪除舊的 -> 再建立新的
        """
        logger.info(
            f"🔄 Skill: Reschedule | Old: {old_time_min} | New: {new_start_time}"
        )

        # 1. 嘗試刪除舊行程
        del_result = self.delete_event_by_query(old_time_min, old_keyword)

        # 2. 建立新行程
        # 就算刪除失敗(沒找到舊的)，我們通常還是會建立新的，或是回傳錯誤
        # 這裡策略是：如果找不到舊的，就只建立新的，並在訊息提醒

        create_result = self.create_event(
            title=new_title, start_time=new_start_time, end_time=new_end_time
        )

        return {
            "success": create_result["success"],
            "delete_status": del_result,
            "create_status": create_result,
        }
