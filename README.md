# 🤖 AI Butler (LINE Bot with Multi-Provider AI & Calendar)

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Google%20Cloud%20Functions-green.svg)
![LINE](https://img.shields.io/badge/Messaging-LINE%20API-00C300.svg)
![Gemini](https://img.shields.io/badge/AI-Gemini%20Flash-8E75B2.svg)
![Claude](https://img.shields.io/badge/AI-Claude-D97757.svg)

**AI Butler** is a smart personal assistant built with **Python** and **LINE Messaging API**. It supports multiple AI providers (**Google Gemini** and **Anthropic Claude**, switchable via a single env var), manages your Google Calendar via natural language, and delivers automated daily/weekly schedule reports through GitHub Actions.

**AI Butler** 是一個基於 **Python** 與 **LINE Messaging API** 打造的智慧個人管家。支援多個 AI 模型供應商（**Gemini** 與 **Claude**，透過環境變數一鍵切換），可用自然語言管理 Google 日曆，並透過 GitHub Actions 自動發送每日與每週行程報告。

---

## 📖 Documentation / 說明文件

Please select your preferred language to view the full documentation, installation guide, and architecture details.
請選擇您的語言以查看完整的專案說明、安裝教學與系統架構細節。

### 👉 [🇺🇸 English Documentation](./README.en.md)

### 👉 [🇹🇼 繁體中文說明](./README.zh-tw.md)

---

## ✨ Key Features / 核心功能

- **🧠 Learning Memory System**: Vector-search powered memories. Automatically logs technical or personal facts and retrieves context during chat (RAG).
  - **學習記憶系統**：透過向量檢索 (Vector Search) 儲存並回憶過往對話重點，並在聊天時動態注入上下文 (RAG)。
- **🔌 Multi-Provider AI**: Switch between Gemini and Claude via `LLM_PROVIDER=gemini|claude`. Zero code changes required.
  - **多模型支援**：一行環境變數切換 Gemini / Claude，無需改動程式碼。
- **⚡ Async Architecture**: High concurrency handling with asynchronous event loops, minimizing Cold Start latencies in Serverless environments.
  - **全非同步架構**：大幅降低 GCP Cold Start 造成的延遲，並發處理意圖分類與向量運算。
- **🧠 Smart Intent Routing**: Lightweight models classify user intent in under 0.5s.
  - **智慧意圖分流**：使用輕量模型精準判斷意圖，延遲低於 0.5 秒。
- **📅 Natural Language Calendar**: "Book a meeting next Monday at 10 AM."
  - **自然語言行事曆**：像對秘書說話一樣新增或查詢行程。
- **🔔 Automated Reports**: Daily and Weekly schedule summaries sent via **GitHub Actions**.
  - **自動化行程報表**：每日與每週定時推播行程總覽。
- **👥 Group Chat Support**: Works in groups using the trigger word **"Butler" / "管家"**.
  - **支援群組協作**：可在群組中喚醒機器人。
- **☁️ Serverless**: Built on **Google Cloud Functions (Gen 2)**.
  - **無伺服器架構**：部署於 GCP，輕量且易於擴充。

---

## 📂 Project Structure / 專案結構

```text
.
├── README.md               # This file (Portal)
├── README.en.md            # Detailed English Documentation
├── README.zh-tw.md         # 完整中文說明文件
├── main.py                 # Gateway (Router)
├── src/
│   ├── agents/             # AI Parsers & Controllers
│   ├── skills/             # Deterministic Python Logic
│   ├── services/
│   │   ├── gcal_service.py # Google Calendar driver
│   │   └── llm/            # ✨ LLM abstraction layer (base / gemini / claude / factory)
│   ├── prompts/            # AI System Prompts
│   ├── config.py           # Centralized config (models, providers)
│   └── utils/              # Helpers & Flex Message templates
├── .github/workflows/      # CI/CD & Cron Jobs
└── requirements.txt        # Dependencies
```

## 📄 License

This project is licensed under the MIT License.
