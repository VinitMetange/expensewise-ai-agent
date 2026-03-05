# 💸 ExpenseWise AI Agent

> **WhatsApp-based Agentic AI Expense Management Solution** — Track, analyze, and manage your expenses conversationally using AI agents, with user-owned cloud storage.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic-orange)
![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock-yellow?logo=amazon-aws)
![WhatsApp](https://img.shields.io/badge/WhatsApp-Business_API-green?logo=whatsapp)
![License](https://img.shields.io/badge/License-MIT-purple)

---

## 🌟 Product Vision

ExpenseWise is a **conversational AI expense manager** that lives in WhatsApp. Users simply chat to log expenses, get insights, split bills, and track budgets — with all data stored in **their own cloud storage** (Google Drive, Dropbox, or OneDrive). No app to download. No data vendor lock-in.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER CHANNELS                           │
│          WhatsApp Business API    │    Web Dashboard (Next.js) │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                   ORCHESTRATOR AGENT                           │
│              (LangGraph + AWS Bedrock Claude)                   │
└──────┬──────────┬──────────┬──────────┬──────────┬─────────────┘
       │          │          │          │          │
  ┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼───┐ ┌───▼────────┐
  │Logging │ │Categor-│ │Insight │ │Budget │ │  Cloud     │
  │ Agent  │ │ization │ │ Agent  │ │ Agent │ │  Storage   │
  │        │ │ Agent  │ │        │ │       │ │  Agent     │
  └────┬───┘ └───┬────┘ └───┬────┘ └───┬───┘ └───┬────────┘
       └──────────────────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │   USER CLOUD STORE  │
              │ Google Drive /      │
              │ Dropbox / OneDrive  │
              └─────────────────────┘
```

---

## ✨ Key Features

### 🤖 Multi-Agent Intelligence
- **Orchestrator Agent** — Routes intent, manages conversation state
- **Expense Logging Agent** — Parses free text, voice notes, and receipt photos
- **Categorization Agent** — Auto-categorizes with custom override support
- **Insight Agent** — Generates spending trends, patterns, and reports
- **Budget Agent** — Manages budget limits and proactive alerts
- **Cloud Storage Agent** — Reads/writes to user's own cloud storage

### 💬 WhatsApp-First Experience
- Add expenses via plain text: `"Spent 450 on lunch at Truffles"`
- Upload receipts as images for auto OCR parsing
- Send voice notes for hands-free logging
- Ask natural questions: `"How much did I spend on food this week?"`
- Receive daily summaries and weekly reports

### ☁️ User-Owned Storage
- All data stored in **user's Google Drive / Dropbox / OneDrive**
- Structured as JSON + CSV for easy export
- Zero vendor lock-in — user owns their financial data
- Optional Google Sheets sync for live dashboards

### 📊 Smart Reporting
- Daily spend summary (auto-delivered every evening)
- Weekly and monthly trend reports
- Category-wise breakdown with visualizations
- Budget utilization alerts
- Export to PDF or Google Sheets

### 🎉 Event-Based Expense Sessions
- Create named sessions: `"Start Goa Trip expenses"`
- Tag expenses to events automatically
- Group expense splitting with participants
- Session summary and settlement report

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| AI Orchestration | LangGraph + AWS Bedrock (Claude 3.x) |
| WhatsApp Integration | Twilio WhatsApp API / Meta Cloud API |
| Backend API | FastAPI (Python 3.11+) |
| Web Dashboard | Next.js + TailwindCSS |
| Database | PostgreSQL (user metadata) |
| Storage | Google Drive API / Dropbox API / OneDrive API |
| OCR | AWS Textract / Google Vision API |
| Voice | AWS Transcribe / Whisper |
| Queue | AWS SQS / Redis |
| Hosting | AWS Lambda + API Gateway / ECS |
| Observability | LangSmith + CloudWatch |

---

## 📁 Project Structure

```
expensewise-ai-agent/
├── agents/                    # All AI agents
│   ├── orchestrator/          # Main routing + state agent
│   ├── logging_agent/         # Expense parsing & logging
│   ├── categorization_agent/  # Category inference
│   ├── insight_agent/         # Analytics & reporting
│   ├── budget_agent/          # Budget monitoring
│   └── storage_agent/         # Cloud storage I/O
├── api/                       # FastAPI backend
│   ├── routes/                # API route handlers
│   ├── models/                # Pydantic data models
│   └── middleware/            # Auth, logging, rate limiting
├── integrations/
│   ├── whatsapp/              # WhatsApp webhook handler
│   ├── google_drive/          # Google Drive connector
│   ├── dropbox/               # Dropbox connector
│   └── onedrive/              # OneDrive connector
├── web/                       # Next.js web dashboard
├── infrastructure/            # AWS CDK / Terraform IaC
├── tests/                     # Unit + integration tests
├── docs/                      # Product spec & architecture docs
├── scripts/                   # Dev utilities & data migration
├── .env.example               # Environment variable template
├── requirements.txt           # Python dependencies
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+ (for web dashboard)
- AWS Account with Bedrock access
- Twilio or Meta WhatsApp Business API credentials
- Google Drive / Dropbox API credentials

### Installation

```bash
# Clone the repo
git clone https://github.com/VinitMetange/expensewise-ai-agent.git
cd expensewise-ai-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Fill in your API keys in .env

# Run locally
uvicorn api.main:app --reload
```

### Environment Variables

```env
# AWS
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# WhatsApp
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
WHATSAPP_FROM=whatsapp:+14155238886

# Storage
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/expensewise

# LangSmith (observability)
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=expensewise
```

---

## 🗺️ Roadmap

### Phase 1 — MVP (Month 1-2)
- [ ] WhatsApp webhook + basic message routing
- [ ] Expense logging from plain text
- [ ] Google Drive storage integration
- [ ] Category auto-tagging
- [ ] Daily summary messages

### Phase 2 — Core Features (Month 3-4)
- [ ] Receipt OCR via image upload
- [ ] Voice note transcription + parsing
- [ ] Budget tracking and alerts
- [ ] Weekly/monthly reports
- [ ] Web dashboard (read-only)

### Phase 3 — Advanced (Month 5-6)
- [ ] Event-based expense sessions
- [ ] Group expense splitting
- [ ] Dropbox + OneDrive connectors
- [ ] Investment & wealth insights
- [ ] n8n workflow automation

### Phase 4 — Scale (Month 7+)
- [ ] Multi-currency support
- [ ] Bank statement import
- [ ] Tax categorization (India GST / ITR)
- [ ] API for third-party integrations
- [ ] Mobile app (React Native)

---

## 🤝 Contributing

This is currently a solo founder project. Contributions, feedback, and feature suggestions are welcome!

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -m 'Add my feature'`
4. Push to branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Vinit Metange**
- Product Manager & AI Enthusiast
- LinkedIn: [linkedin.com/in/vinitmetange](https://linkedin.com/in/vinitmetange)
- Building AI-powered products that solve real problems

---

> *"Your expenses. Your data. Your AI."*
