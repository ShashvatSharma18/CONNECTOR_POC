# Cerebro — Enterprise AI Workplace Knowledge Assistant

A multi-source enterprise Retrieval-Augmented Generation (RAG) platform connecting workplace tools (Gmail, Google Chat, Slack, GitHub, Google Drive, SQL Database, Notion, LMS, Local File Share) and the **Universal Document Parser (Parse and Furious)** ensemble for multimodal documents (PDF, Word, Excel, PowerPoint, OCR).

---

## 📁 Project Structure

This repository is organized as a clean Monorepo with completely isolated **Frontend** and **Backend** directories:

```text
source-systems-poc/
│
├── backend/                  # Python / FastAPI Backend & RAG Engine
│   ├── app/                  # FastAPI routes, connectors, RAG services
│   │   ├── connectors/       # Source connectors (Gmail, Slack, Jira, Drive, Universal Parser, etc.)
│   │   ├── chat_service.py   # RAG pipeline, LLM grounding, context fusion
│   │   ├── chat_history.py   # SQLite multi-turn session persistence
│   │   ├── chat_router.py    # REST APIs for chat & connectors
│   │   └── main.py           # FastAPI application entrypoint
│   ├── data/                 # SQLite database storage (chat sessions & active docs)
│   ├── test-share/           # Sample local documents for File Share connector
│   ├── test-lms/             # Mock LMS courses & transcripts
│   ├── requirements.txt      # Python dependencies
│   ├── .env.example          # Environment variables template
│   └── .env                  # Local secret configuration
│
├── frontend/                 # Modern React / Vite / TypeScript Application
│   ├── src/
│   │   ├── components/       # ChatWindow, MessageBubble, MessageComposer, DocumentPreviewModal, etc.
│   │   ├── services/         # Typed API clients for backend communication
│   │   ├── types/            # TypeScript data models (ChatSession, RichCard, etc.)
│   │   └── App.tsx           # Main application shell with Cerebro branding
│   ├── package.json          # Node dependencies & build scripts
│   ├── tsconfig.json         # TypeScript configuration
│   └── vite.config.ts        # Vite configuration & dev server
│
├── .gitignore                # Global git ignore configuration
└── README.md                 # Project documentation
```

---

## 🚀 Getting Started

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Fill in your GROQ_API_KEY, OAuth credentials, etc.

# Start FastAPI server on port 8001
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Backend API will be available at: `http://localhost:8001`  
Swagger API Docs: `http://localhost:8001/docs`

---

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server on port 5173
npm run dev
```

Frontend application will be accessible at: `http://localhost:5173`

---

## ⚡ Key Capabilities

- **Universal Document Parser Ensemble**: High-precision parsing for PDFs, Word, Excel, PowerPoint, and images with OCR and cell-by-cell table grounding.
- **Session-Persistent Document Chat**: Upload a document once and query it across multiple turns without losing context.
- **Interactive Document Inspector Modal**: Inspect extracted text, tables, and statistics directly in the UI.
- **Enterprise Multi-Source Search**: Unified RAG search across Gmail, Google Drive, Google Chat, Slack, GitHub, Jira, Salesforce, ServiceNow, LMS, and SQL databases.
