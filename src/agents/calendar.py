import json
import logging
import datetime
import pathlib
import google.generativeai as genai
from linebot.v3.messaging import TextMessage, FlexMessage, FlexContainer
from src.services.gcal_service import GCalService
from src.utils.flex_templates import (
    generate_create_success_flex,
    generate_overview_flex,
)
from src.skills.calendar import CalendarSkills

logger = logging.getLogger(__name__)


class CalendarAgent:
    def __init__(self):
        self.skills = CalendarSkills()
        self.model = genai.GenerativeModel("gemini-3-flash-preview")

        # ✅ 優化：在初始化時就讀入 Prompt，之後重複使用
        # 這樣在 Cloud Functions 熱啟動 (Warm Start) 時，就不用重新讀檔，提升效能
        self.prompt_template = self._load_prompt()

    def _load_prompt(self):
        """
        讀取 Prompt 檔案內容。
        """
        current_dir = pathlib.Path(__file__).parent.parent
        prompt_path = current_dir / "prompts" / "calendar_agent.txt"

        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                logger.info(
                    "✅ Calendar Prompt loaded successfully from %s", prompt_path
                )
                return f.read()
        except Exception as e:
            logger.error("❌ Error reading calendar prompt: %s", e)
            return ""

    def _normalize_args(self, args):
        """
        [資料清洗] 強制將 Gemini 可能給錯的 key 轉回我們 Skill 支援的 key
        """
        new_args = args.copy()

        # 1. 處理標題 (title vs summary)
        if "summary" in new_args and "title" not in new_args:
            new_args["title"] = new_args.pop("summary")

        # 2. 處理時間 (camelCase vs snake_case 防呆)
        # 雖然 Prompt 規定 start_time，但防萬一它給 startTime
        if "startTime" in new_args and "start_time" not in new_args:
            new_args["start_time"] = new_args.pop("startTime")
        if "endTime" in new_args and "end_time" not in new_args:
            new_args["end_time"] = new_args.pop("endTime")

        # 3. 處理 Reschedule 的欄位
        if "new_summary" in new_args and "new_title" not in new_args:
            new_args["new_title"] = new_args.pop("new_summary")

        return new_args

    def handle_message(self, user_msg):
        # 1. 檢查 Prompt 是否載入成功
        if not self.prompt_template:
            return [TextMessage(text="❌ 系統錯誤：Prompt 載入失敗，請檢查 Log")]

        # 2. 替換變數 (使用記憶體中的 Template，無需 IO)
        dt_now = datetime.datetime.now().isoformat()
        prompt = self.prompt_template.replace("{{USER_INPUT}}", user_msg).replace(
            "{{CURRENT_TIME}}", dt_now
        )

        # 3. Call Gemini
        try:
            response = self.model.generate_content(prompt)
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_text)

            skill = data.get("skill")
            raw_args = data.get("args", {})

            # 🔥 關鍵修復：在這裡進行參數清洗
            args = self._normalize_args(raw_args)

            logger.info("Gemini parsed: skill=%s, args=%s (Normalized)", skill, args)

        except Exception as e:
            logger.error("Gemini parsing failed: %s", e)
            return [TextMessage(text="❌ 無法理解您的日曆指令")]

        # 4. Dispatch Skill
        reply_messages = []

        try:
            if skill == "create_event":
                # 直接使用清洗過的 args
                result = self.skills.create_event(**args)
                if result["success"]:
                    # 準備給 UI 用的資料 (Flex Template 需要 startTime/endTime/title)
                    ui_data = {
                        "title": args.get("title"),
                        "startTime": args.get("start_time"),
                        "endTime": args.get("end_time"),
                        "location": args.get("location", ""),
                    }
                    flex_json = generate_create_success_flex(ui_data)
                    reply_messages.append(
                        FlexMessage(
                            alt_text="行程已建立",
                            contents=FlexContainer.from_dict(flex_json),
                        )
                    )
                else:
                    reply_messages.append(
                        TextMessage(text=f"❌ 建立失敗: {result.get('message')}")
                    )

            elif skill == "batch_create":
                # Batch 處理
                raw_events = args.get("events", [])
                if not isinstance(raw_events, list):
                    raw_events = [args]  # 防呆

                success_count = 0
                for evt in raw_events:
                    # 🔥 每一筆 event 也要清洗
                    clean_evt = self._normalize_args(evt)
                    if self.skills.create_event(**clean_evt)["success"]:
                        success_count += 1

                reply_messages.append(
                    TextMessage(text=f"✅ 批量建立完成！共建立 {success_count} 筆行程")
                )

            elif skill == "list_events":
                result = self.skills.list_events(**args)
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
                        TextMessage(text=f"❌ 查詢失敗: {result.get('message')}")
                    )

            elif skill == "delete_event":
                result = self.skills.delete_event_by_query(**args)
                if result["success"]:
                    deleted_title = result["deleted_event"].get("summary", "行程")
                    reply_messages.append(
                        TextMessage(text=f"🗑️ 已刪除行程：{deleted_title}")
                    )
                else:
                    reply_messages.append(
                        TextMessage(text=f"❌ 刪除失敗：{result['message']}")
                    )

            elif skill == "reschedule_event":
                result = self.skills.reschedule_event(**args)

                msg = ""
                if result["delete_status"]["success"]:
                    msg += "🗑️ 舊行程已刪除\n"
                else:
                    msg += "⚠️ 找不到舊行程 (直接建立新行程)\n"

                if result["create_status"]["success"]:
                    ui_data = {
                        "title": args.get("new_title"),
                        "startTime": args.get("new_start_time"),
                        "endTime": args.get(
                            "new_end_time"
                        ),  # Flex Template 其實沒用到 endTime 顯示，但傳入無妨
                    }
                    # 這裡為了簡單，重複使用 create success template
                    flex_json = generate_create_success_flex(ui_data)
                    reply_messages.append(
                        FlexMessage(
                            alt_text="行程已改期",
                            contents=FlexContainer.from_dict(flex_json),
                        )
                    )
                else:
                    msg += "❌ 新行程建立失敗"
                    reply_messages.append(TextMessage(text=msg))

            else:
                reply_messages.append(TextMessage(text=f"🤔 尚未支援的技能: {skill}"))

        except TypeError as te:
            # 捕捉類似 unexpected keyword argument 的錯誤
            logger.error("Parameter Mismatch: %s", te)
            reply_messages.append(TextMessage(text="❌ 參數格式錯誤，請重試"))
        except Exception as e:
            logger.error("Skill execution failed: %s", e)
            reply_messages.append(TextMessage(text="❌ 執行動作時發生錯誤"))

        return reply_messages
