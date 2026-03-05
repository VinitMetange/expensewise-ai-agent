# 💸 ExpenseWise AI Agent

> **WhatsApp-based Agentic AI Expense Management Solution** - Track, analyze, and manage your expenses conversationally using AI agents, with user-owned cloud storage.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic-orange)
![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock-yellow?logo=amazon-aws)
![WhatsApp](https://img.shields.io/badge/WhatsApp-Business_API-green?logo=whatsapp)
![License](https://img.shields.io/badge/License-MIT-purple)

---

## 🎯 Product Vision

ExpenseWise is a **conversational AI expense manager** that lives in WhatsApp. Users simply chat to log expenses, get insights, split bills, and track budgets - with all data stored in **their own cloud storage** (Google Drive, Dropbox, or OneDrive). No app to download. No data vendor lock-in.

---

## 🏗️ Architecture Overview

```
WhatsApp Message
       ↓
  Twilio Webhook (FastAPI)
       ↓
  Orchestrator (LangGraph)
       ↓
  ┌─────────────────────────────────┐
  │  Intent Detection (AWS Bedrock)   │
  └─┬─┬─┬─┬─┬───────────────────┘
    │  │  │  │  │
    ↓  ↓  ↓  ↓  ↓
 Log Cat Budget Insight Storage
Agent Agent Agent  Agent  Agent
    ↓             ↓
Google Drive (User-owned)
```

---

## 🤖 Multi-Agent System

| Agent | Responsibility |
|-------|---------------|
| **Orchestrator** | Intent detection, routing to sub-agents |
| **Logging Agent** | Parse text/voice/receipt expenses |
| **Categorization Agent** | AI-based expense categorization |
| **Budget Agent** | Set, track and alert on budgets |
| **Insight Agent** | Spending analysis and reports |
| **Storage Agent** | CRUD to user's Google Drive |
| **Onboarding Handler** | New user setup and OAuth flow |

---

## 📊 Features

- ✅ **Log expenses** via text: `"Spent $45 on lunch at Chipotle"`
- ✅ **Receipt scanning** via photo messages
- ✅ **Smart categorization** using AWS Bedrock Claude
- ✅ **Budget setting**: `"Set $500 monthly food budget"`
- ✅ **Spending insights**: `"Where am I overspending?"`
- ✅ **Date-range summaries**: `"Show this month's expenses"`
- ✅ **CSV export** to Google Drive
- ✅ **User-owned storage** - data lives in YOUR Google Drive
- ✅ **No app to download** - works entirely in WhatsApp
- ✅ **Multi-currency support**

---

## 📦 Project Structure

```
expensewise-ai-agent/
├── api/
│   ├── models/expense.py       # Pydantic data models
│   ├── routes/
│   │   ├── auth.py             # Google OAuth routes
│   │   └── expenses.py         # Expense REST API
│   ├── config.py               # App configuration
│   ├── database.py             # SQLAlchemy async DB
│   └── main.py                 # FastAPI application
├── agents/
│   ├── orchestrator/graph.py   # LangGraph orchestrator
│   ├── logging_agent/agent.py  # Expense logging
│   ├── categorization_agent/   # AI categorization
│   ├── budget_agent/           # Budget management
│   ├── insight_agent/          # Spending insights
│   ├── storage_agent/          # Cloud storage ops
│   └── onboarding/handler.py   # New user onboarding
├── integrations/
│   ├── whatsapp/               # Twilio WhatsApp
│   └── google_drive/client.py  # Google Drive client
├── Dockerfile
├── docker-compose.yml
├── render.yaml
├── requirements.txt
└── .env.example
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL
- AWS Account with Bedrock access
- Twilio Account with WhatsApp Business API
- Google Cloud Project with Drive API

### 1. Clone & Install

```bash
git clone https://github.com/VinitMetange/expensewise-ai-agent.git
cd expensewise-ai-agent
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Set Up Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create OAuth 2.0 credentials
3. Add `https://your-domain.com/auth/google/callback` as redirect URI
4. Enable Google Drive API
5. Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to `.env`

### 4. Set Up Twilio WhatsApp
1. Create a [Twilio account](https://twilio.com)
2. Enable WhatsApp Sandbox or Business API
3. Set webhook URL: `https://your-domain.com/webhook/whatsapp`
4. Add Twilio credentials to `.env`

### 5. Configure AWS Bedrock
1. Enable Claude model access in AWS Bedrock console
2. Add AWS credentials to `.env`

### 6. Run Locally

```bash
# With Docker Compose
docker-compose up

# Without Docker
uvicorn api.main:app --reload
```

---

## ☁️ Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

1. Fork this repository
2. Click the Deploy button above
3. Set required environment variables in Render dashboard
4. Update `GOOGLE_REDIRECT_URI` with your Render service URL
5. Update Twilio webhook URL with your Render service URL

---

## 💬 Example Conversations

```
User: Spent $42 on groceries at Whole Foods
ExpenseWise: Got it! Logged $42.00 for Groceries at Whole Foods on June 15.
             Your grocery spend this month: $127.50 / $300 budget (42.5%)

User: Show me this week's expenses
ExpenseWise: This week (Jun 10-15):
             Total: $187.30
             - Food: $95.00 (50.7%)
             - Transport: $52.30 (27.9%)
             - Entertainment: $40.00 (21.4%)

User: Am I overspending?
ExpenseWise: Based on this month's data:
             - You're 23% over your food budget
             - Transport is on track
             - You've saved $150 vs last month overall
             Tip: Consider meal prepping to cut food costs!
```

---

## 🔧 Tech Stack

| Layer | Technology |
|-------|------------|
| **Framework** | FastAPI + Python 3.11 |
| **AI Agents** | LangGraph + AWS Bedrock (Claude 3) |
| **Messaging** | Twilio WhatsApp Business API |
| **Storage** | User-owned Google Drive |
| **Database** | PostgreSQL (metadata only) |
| **ORM** | SQLAlchemy async |
| **Deployment** | Docker / Render.com |

---

## 📝 Environment Variables

See `.env.example` for the complete list. Key variables:

```env
# AWS Bedrock
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Twilio WhatsApp
TWILIO_ACCOUNT_SID=your_sid
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Google OAuth
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_REDIRECT_URI=https://your-domain.com/auth/google/callback

# Database
DATABASE_URL=postgresql://user:password@localhost/expensewise
```

---

## 🧑‍💻 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 📞 Support

For questions or support, open a GitHub issue or contact [@VinitMetange](https://github.com/VinitMetange).
