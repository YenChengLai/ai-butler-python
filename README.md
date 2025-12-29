# 🤖 AI Butler (LINE Bot with Google Gemini & Calendar)

A smart personal assistant built with **Python**, **LINE Messaging API**, and **Google Gemini**. It manages your Google Calendar via natural language and sends scheduled agenda reports using GitHub Actions.

一個基於 **Python**、**LINE Messaging API** 與 **Google Gemini** 打造的智慧個人管家。它能透過自然語言管理 Google 日曆，並利用 GitHub Actions 自動發送每日與每週行程預告。

---

## 🌍 Language / 語言

- [English](#-english-documentation)
- [繁體中文](#-繁體中文說明)

---

## 🇬🇧 English Documentation

### ✨ Features

- **🧠 Smart Intent Routing**: Uses **Google Gemini (Flash model)** to classify user intent (e.g., Calendar, Chat, Expense) and route to specific agents.
- **📅 Calendar Management**: Query and add events to Google Calendar using natural language (e.g., "Book a meeting next Monday at 10 AM").
- **🔔 Scheduled Reports**:
  - **Daily Report**: Sent at **21:30** every night, summarizing tomorrow's schedule.
  - **Weekly Report**: Sent every **Sunday**, summarizing the next 7 days.
  - Powered by **GitHub Actions** (Serverless Cron Jobs).
- **👥 Group Chat Support**: Works in group chats! Wake it up using the trigger word **"管家" (Butler)** (e.g., "Butler, check my schedule").
- **☁️ Cloud Native**: Deployed on **Google Cloud Functions (Gen 2)** or **Cloud Run**.

### 🏗 Architecture

1.  **LINE Platform** sends webhook events to **Google Cloud Function**.
2.  **Main Router** (Gemini) analyzes the intent.
3.  **Agents** (e.g., CalendarAgent) process the request using specific skills.
4.  **GitHub Actions** trigger scheduled scripts (`daily_report.py`, `weekly_report.py`) to push notifications.

### 🚀 Setup & Installation

#### 1. Prerequisites

- A LINE Official Account (with Messaging API).
- A Google Cloud Project (enable **Calendar API**).
- A Google Gemini API Key.
- A Service Account JSON key for Google Calendar access.

#### 2. Environment Variables (.env)

Create a `.env` file locally or set these in your Cloud Function / GitHub Secrets:

```bash
CHANNEL_ACCESS_TOKEN="your_line_channel_access_token"
CHANNEL_SECRET="your_line_channel_secret"
GEMINI_API_KEY="your_gemini_api_key"
CALENDAR_ID="primary" (or your specific calendar ID)
TARGET_GROUP_ID="Cxxxxxxxx..." (The group ID to receive reports)
```

#### 3. GitHub Actions Setup (For Reports)

Go to your repository Settings > Secrets and variables > Actions and add:

- CHANNEL_ACCESS_TOKEN
- CALENDAR_ID
- TARGET_GROUP_ID: Your User ID (U...) or Group ID (C...).
- GCP_SA_KEY_BASE64: Base64 encoded string of your service_account.json.

To generate: base64 -i service_account.json -o sa_base64.txt

#### 4. How to get Group ID?

The ID in the LINE OA Manager URL is NOT the API Group ID.

1. Invite the bot to a group.
2. Check your GCP Logs for the source.groupId when you send a message.
3. Or temporarily use a debug script to echo the ID.
