import os
import json
import logging
import datetime
import pathlib
import google.generativeai as genai
from linebot.v3.messaging import TextMessage

# 引入 Skill
from src.skills.expense import ExpenseSkills
from src.config import GEMINI_MODEL_NAME

logger = logging.getLogger(__name__)


class ExpenseAgent:
    def __init__(self):
        self.skills = ExpenseSkills()
        self.model = genai.GenerativeModel(GEMINI_MODEL_NAME)

    def _load_prompt(self, user_text):
        """讀取 Prompt 並填入變數"""
        current_dir = pathlib.Path(__file__).parent.parent
        prompt_path = current_dir / "prompts" / "expense_agent.txt"

        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

        today = datetime.date.today().isoformat()
        prompt = template.replace("{{CURRENT_DATE}}", today)
        return f"{prompt}\n\nUser Input: {user_text}"

    def handle_message(self, user_text, user_id=None):
        """
        處理記帳與查帳請求的主流程
        """
        logger.info("💰 Expense Agent received: %s", user_text)

        # 1. 呼叫 Gemini 解析意圖
        try:
            prompt = self._load_prompt(user_text)
            response = self.model.generate_content(prompt)
            cleaned_text = (
                response.text.replace("```json", "").replace("```", "").strip()
            )
            ai_response = json.loads(cleaned_text)
            logger.info("🤖 AI Parsed Data: %s", ai_response)

        except Exception as e:
            logger.error("❌ Gemini Parsing Error: %s", str(e))
            return [TextMessage(text="😵‍💫 抱歉，我看不懂這個指令，請再試一次。")]

        # 2. 根據 Action 分流處理
        action = ai_response.get("action")

        if action == "RECORD":
            return self._handle_record(ai_response.get("data", {}))

        elif action == "QUERY":
            return self._handle_query(ai_response.get("params", {}))

        else:
            return [
                TextMessage(text="🤔 AI 無法判斷是要記帳還是查帳，請檢查 Prompt 設定。")
            ]

    def _handle_record(self, data):
        """處理記帳邏輯"""
        try:
            amount = int(data.get("amount", 0))
            if amount <= 0:
                return [TextMessage(text="🤔 金額好像怪怪的，請確認一下喔。")]

            result = self.skills.add_expense(
                date_str=data.get("date"),
                category=data.get("category", "其他"),
                item=data.get("item", "未命名項目"),
                amount=amount,
                project=data.get("project", ""),
                payer="",
            )

            if result["success"]:
                project_tag = f" (🏷️{data['project']})" if data.get("project") else ""
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
            logger.error("Record Error: %s", str(e))
            return [TextMessage(text="💥 記帳系統發生錯誤。")]

    def _handle_query(self, params):
        """處理查詢邏輯 (已針對 NT$ 與多重篩選優化)"""
        start = params.get("start_date")
        end = params.get("end_date")
        col = params.get("filter_column")  # Project 或 Category
        val = params.get("filter_value")

        # 1. 從 Skill 撈資料
        expenses = self.skills.query_expenses(start, end)

        if not expenses:
            return [TextMessage(text=f"🔍 {start} ~ {end} 期間沒有找到支出紀錄。")]

        # 2. 進行篩選 (Filter) - 優化版
        target_expenses = []
        title_prefix = "總支出"

        if col and val:
            # 【優化點 1】支援多重關鍵字 (例如 "餐費, 飲料")
            # 將 AI 回傳的字串用逗號切開，變成清單 ["餐費", "飲料"]
            target_values = [v.strip() for v in val.split(",")]

            # 篩選：只要欄位內容 "包含" 在目標清單中就算符合
            target_expenses = [
                x for x in expenses if str(x.get(col, "")).strip() in target_values
            ]
            title_prefix = f"【{val}】"
        else:
            target_expenses = expenses

        if not target_expenses:
            return [TextMessage(text=f"🔍 {start} ~ {end} 期間沒有符合 {val} 的紀錄。")]

        # 3. 計算統計資料
        total = 0
        breakdown = {}

        # 決定分類依據
        group_key = "Item" if col == "Category" else "Category"

        for row in target_expenses:
            try:
                # 【優化點 2】強力清洗金額格式 (處理 NT$, $, 逗號, 空格)
                amt_raw = str(row.get("Amount", 0))
                # 移除所有非數字與負號的字元 (簡單暴力法)
                clean_amt_str = "".join(
                    filter(lambda x: x.isdigit() or x == "-", amt_raw)
                )

                amt = int(clean_amt_str) if clean_amt_str else 0

                total += amt

                # 分類加總
                key = row.get(group_key) or "其他"
                breakdown[key] = breakdown.get(key, 0) + amt
            except ValueError:
                continue

        # 4. 產生回覆文字
        sorted_breakdown = sorted(
            breakdown.items(), key=lambda item: item[1], reverse=True
        )
        breakdown_text = "\n".join([f"▫️ {k}: ${v:,}" for k, v in sorted_breakdown])

        reply_text = (
            f"📊 {title_prefix} 統計\n"
            f"📅 期間：{start} ~ {end}\n"
            f"💰 總金額：${total:,}\n"
            f"------------------\n"
            f"{breakdown_text}"
        )

        return [TextMessage(text=reply_text)]
