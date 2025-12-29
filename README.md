# 🤖 AI Butler (LINE Bot with Google Gemini & Calendar)

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Google%20Cloud%20Functions-green.svg)
![LINE](https://img.shields.io/badge/Messaging-LINE%20API-00C300.svg)
![AI](https://img.shields.io/badge/AI-Gemini%20Flash-8E75B2.svg)

**AI Butler** is a smart personal assistant built with **Python**, **LINE Messaging API**, and **Google Gemini**. It streamlines your Google Calendar management via natural language and keeps you updated with automated daily/weekly agenda reports.

**AI Butler** 是一個基於 **Python**、**LINE Messaging API** 與 **Google Gemini** 打造的智慧個人管家。它能透過自然語言輕鬆管理 Google 日曆，並利用 GitHub Actions 自動發送每日與每週的行程預告。

---

## 📖 Documentation / 說明文件

Please select your preferred language to view the full documentation, installation guide, and architecture details.
請選擇您的語言以查看完整的專案說明、安裝教學與系統架構細節。

### 👉 [🇺🇸 English Documentation](./README.en.md)

### 👉 [🇹🇼 繁體中文說明](./README.zh-tw.md)

---

## ✨ Key Features / 核心功能

- **🧠 Smart Intent Routing**: Powered by **Google Gemini (Flash)** to intelligently route requests (Calendar, Chat, Expense, etc.).
  - **智慧意圖分流**：使用 Gemini 模型精準判斷使用者意圖並分流處理。
- **📅 Natural Language Calendar**: "Book a meeting next Monday at 10 AM."
  - **自然語言行事曆**：像對秘書說話一樣新增或查詢行程。
- **🔔 Automated Reports**: Daily and Weekly schedule summaries sent via **GitHub Actions**.
  - **自動化行程報表**：每日與每週定時推播行程總覽。
- **👥 Group Chat Support**: Works perfectly in groups using the trigger word **"Butler" / "管家"**.
  - **支援群組協作**：可在群組中喚醒機器人，協助團隊管理時間。
- **☁️ Serverless**: Built on **Google Cloud Functions (Gen 2)**.
  - **無伺服器架構**：部署於 GCP，輕量且易於擴充。

---

## 📂 Project Structure / 專案結構

```text
.
├── README.md           # This file (Portal)
├── README.en.md        # Detailed English Documentation
├── README.zh-tw.md     # 完整中文說明文件
├── main.py             # Gateway (Router)
├── src/                # Source code (Agents, Skills, Utils)
├── .github/workflows/  # CI/CD & Cron Jobs
└── requirements.txt    # Dependencies
```

## 📄 License

This project is licensed under the MIT License.
