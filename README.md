# 🤖 AI Butler (Serverless Python Gateway)

> A smart personal assistant powered by Google Gemini 3.0 & Google Cloud Functions.
>
> 基於 Google Gemini 3.0 與 Google Cloud Functions 打造的個人智慧管家。

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![GCP](https://img.shields.io/badge/Google_Cloud-Functions-4285F4?style=flat&logo=google-cloud&logoColor=white)](https://cloud.google.com/)
[![Gemini](https://img.shields.io/badge/AI-Gemini_3.0-8E75B2?style=flat&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![LINE](https://img.shields.io/badge/Platform-LINE_Bot-00C300?style=flat&logo=line&logoColor=white)](https://developers.line.biz/)

---

## 🌍 Language / 語言版本

Please select your preferred language to read the documentation:
請選擇您偏好的語言以閱讀完整文件：

- [🇹🇼 繁體中文說明 (Traditional Chinese)](./README.zh-tw.md)
- [🇺🇸 English Documentation](./README.en.md)

---

## 🚀 Key Features / 核心功能

- **⚡ Ultra-Fast Routing**: Powered by **Gemini 3.0 Flash**, achieving < 0.5s intent detection.
- **📅 Smart Calendar**: Natural language management for Google Calendar (Query, Create, Batch Create).
- **☁️ Serverless Architecture**: Built on GCP Cloud Functions (Gen 2), optimizing cost to near **$0/month**.
- **🛡️ Secure & Scalable**: Production-grade logging, error handling, and modular agent design.

## 📂 Project Structure

```text
.
├── main.py                 # Gateway Entry Point (Router)
├── src/
│   ├── agents/             # AI Agents (Business Logic)
│   │   ├── calendar.py
│   │   └── (coming soon) expense.py
│   ├── services/           # External API Wrappers
│   │   └── gcal_service.py
│   ├── utils/              # Helpers & UI
│   │   └── flex_templates.py
│   └── prompts/            # AI System Prompts
└── requirements.txt
```
