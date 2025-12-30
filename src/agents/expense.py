import os
import json
import logging
import datetime
import pathlib
import google.generativeai as genai
from linebot.v3.messaging import TextMessage

# 引入剛剛測試成功的 Skill
from src.skills.expense import ExpenseSkills

logger = logging.getLogger(__name__)


class ExpenseAgent:
    def __init__(self):
        self.skills = ExpenseSkills()
        self.model = genai.GenerativeModel("gemini-3-flash-preview")

    def _load_prompt(self, user_text):
        """讀取 Prompt 並填入變數"""
        current_dir = pathlib.Path(__file__).parent.parent
        prompt_path = current_dir / "prompts" / "expense_agent.txt"

        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

        # 填入當前日期，讓 AI 能推算 "昨天"
        today = datetime.date.today().isoformat()
        prompt = template.replace("{{CURRENT_DATE}}", today)

        # 加入使用者輸入
        return f"{prompt}\n\nUser Input: {user_text}"

    def handle_message(self, user_text, user_id=None):
        """
        處理記帳請求的主流程
        回傳: List[TextMessage]
        """
        logger.info(f"💰 Expense Agent received: {user_text}")

        # 1. 呼叫 Gemini 解析意圖
        try:
            prompt = self._load_prompt(user_text)
            response = self.model.generate_content(prompt)
            cleaned_text = (
                response.text.replace("```json", "").replace("```", "").strip()
            )
            data = json.loads(cleaned_text)

            logger.info(f"🤖 AI Parsed Data: {data}")

        except Exception as e:
            logger.error(f"❌ Gemini Parsing Error: {e}")
            return [
                TextMessage(
                    text="😵‍💫 抱歉，我不確定這筆帳的金額或項目，請再試一次 (例如：午餐 100)"
                )
            ]

        # 2. 呼叫 Skill 寫入 Google Sheets
        try:
            # 確保金額是數字
            amount = int(data.get("amount", 0))
            if amount <= 0:
                return [TextMessage(text="🤔 金額好像怪怪的，請確認一下喔。")]

            result = self.skills.add_expense(
                date_str=data.get("date"),
                category=data.get("category", "其他"),
                item=data.get("item", "未命名項目"),
                amount=amount,
                project=data.get("project", ""),
                payer="",  # 目前先留空，或未來可填入 user_id
            )

            if result["success"]:
                # 3. 組裝成功訊息
                # 如果有專案標籤，特別顯示出來
                project_tag = f" (🏷️{data['project']})" if data["project"] else ""

                reply_text = (
                    f"✅ 已記帳！\n"
                    f"📅 {data['date']}\n"
                    f"📝 {data['item']} ${amount:,}\n"
                    f"📂 {data['category']}{project_tag}\n"
                    f"---------------"
                )
                return [TextMessage(text=reply_text)]
            else:
                return [TextMessage(text=f"💥 記帳失敗: {result['message']}")]

        except Exception as e:
            logger.error(f"❌ Execution Error: {e}")
            return [TextMessage(text="💥 系統發生錯誤，請稍後再試。")]
