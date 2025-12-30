import os
import sys
import json
import base64
import logging
import datetime
import gspread
from google.oauth2.service_account import Credentials

# 修正 Python 搜尋路徑 (僅為了讓此檔案能順利讀取上層模組)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

logger = logging.getLogger(__name__)


class ExpenseSkills:
    def __init__(self):
        self.spreadsheet_id = os.getenv("SPREADSHEET_ID")
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        self.creds = None

        # 嘗試讀取 Service Account (本地檔案優先，未來可擴充讀取 Env Base64)
        sa_file = "service_account.json"
        if os.path.exists(sa_file):
            try:
                self.creds = Credentials.from_service_account_file(
                    sa_file, scopes=self.scopes
                )
            except Exception as e:
                logger.error("❌ Credential Load Error: %s", e)
        else:
            logger.error("❌ Service Account JSON not found.")

        if not self.creds:
            sa_base64 = os.getenv("GCP_SA_KEY_BASE64")
            if sa_base64:
                try:
                    # 解碼 Base64 -> JSON String -> Dict
                    json_str = base64.b64decode(sa_base64).decode("utf-8")
                    info = json.loads(json_str)
                    self.creds = Credentials.from_service_account_info(
                        info, scopes=self.scopes
                    )
                    logger.info(
                        "✅ Loaded credentials from Environment Variable (Base64)."
                    )
                except Exception as e:
                    logger.error("❌ Failed to load Base64 credentials: %s", e)
            else:
                logger.error(
                    "❌ Critical: No 'service_account.json' found AND 'GCP_SA_KEY_BASE64' is missing."
                )

    def _get_client(self):
        if not self.creds:
            return None
        return gspread.authorize(self.creds)

    def add_expense(
        self,
        date_str: str,
        category: str,
        item: str,
        amount: int,
        project: str = "",
        payer: str = "",
        note: str = "",
    ):
        """
        新增消費記錄 (自動月份分頁管理)
        """
        client = self._get_client()
        if not client:
            return {"success": False, "message": "Google Sheets Auth Failed"}

        try:
            # 1. 解析日期與分頁名稱
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            sheet_name = dt.strftime("%Y-%m")

            # 2. 連線試算表
            sh = client.open_by_key(self.spreadsheet_id)

            # 3. 取得或建立分頁
            try:
                worksheet = sh.worksheet(sheet_name)
            except gspread.WorksheetNotFound:
                # 若無該月分頁，從 Template 複製
                # (僅記錄必要的系統操作 Log)
                logger.info("✨ Creating new sheet: %s", sheet_name)
                try:
                    template_ws = sh.worksheet("Template")
                    worksheet = template_ws.duplicate(new_sheet_name=sheet_name)
                except gspread.WorksheetNotFound:
                    return {"success": False, "message": "Template sheet missing"}

            # 4. 寫入資料
            row_data = [
                date_str,
                category,
                item,
                amount,
                project,
                payer,
                note,
                str(datetime.datetime.now()),
            ]
            worksheet.append_row(row_data)

            # 成功時只印出一行摘要，方便日後查帳
            logger.info("✅ Expense: %s | %s $%s", date_str, item, amount)

            return {
                "success": True,
                "message": f"Recorded: {item} ${amount}",
                "sheet": sheet_name,
            }

        except Exception as e:
            # 只有錯誤時才印出詳細內容
            logger.error("❌ Add Expense Failed: %s", e)
            return {"success": False, "message": str(e)}


# 移除冗長的 Debug 區塊，僅保留簡單的本地執行入口
if __name__ == "__main__":
    # 僅在手動執行此檔案時，才載入 dotenv
    from dotenv import load_dotenv

    load_dotenv()

    logging.basicConfig(level=logging.INFO)

    # 簡單測試一筆
    skill = ExpenseSkills()
    res = skill.add_expense(
        datetime.date.today().isoformat(),
        "系統測試",
        "部署前檢查",
        100,
        "System",
        "Dev",
    )
    print(res)
