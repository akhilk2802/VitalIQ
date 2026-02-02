# 🩺 VitalIQ

**AI-Powered Personal Health & Wellness Platform**

VitalIQ aggregates health data from wearables and health devices, detects anomalies, finds correlations, and provides personalized AI-driven insights through a conversational interface.

![Tech Stack](https://img.shields.io/badge/React-19-blue) ![Tech Stack](https://img.shields.io/badge/FastAPI-0.109-green) ![Tech Stack](https://img.shields.io/badge/PostgreSQL-pgvector-blue) ![Tech Stack](https://img.shields.io/badge/OpenAI-GPT--4-purple)

📖 **[View Full Design Document](./DESIGN_DOC.md)** — Detailed architecture, data flow, ML pipeline, and RAG system documentation.

---

## ✨ Key Features

| Feature                        | Description                                                    |
| ------------------------------ | -------------------------------------------------------------- |
| 📊 **Unified Dashboard**        | Sleep, nutrition, exercise, vitals & body metrics in one place |
| 🤖 **AI Health Chat**           | Conversational assistant powered by OpenAI + RAG               |
| 🔍 **Anomaly Detection**        | ML-powered unusual pattern detection                           |
| 🔗 **Correlation Analysis**     | Discover relationships between health metrics                  |
| ☀️ **Morning Briefings**        | AI-generated daily health summaries                            |
| 💬 **Natural Language Queries** | Ask about your health in plain English                         |

---

## 🛠️ Tech Stack

### Frontend
- **React 19** + **TypeScript** + **Vite**
- **TailwindCSS** + **Radix UI** (Component library)
- **React Query** (Data fetching) + **Zustand** (State)
- **Recharts** (Visualizations)

### Backend
- **FastAPI** (Python 3.12+)
- **SQLAlchemy** (Async ORM) + **Alembic** (Migrations)
- **PostgreSQL** + **pgvector** (Vector search for RAG)
- **OpenAI API** (GPT-4 + Embeddings)
- **scikit-learn** / **pandas** / **numpy** (ML & Analytics)

---

## 📋 Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 15+ with `pgvector` extension
- OpenAI API Key

---

## 🚀 Quick Start

### 1. Clone & Setup Database

```bash
git clone https://github.com/akhilk2802/VitalIQ
cd VitalIQ
```

```bash
# Create PostgreSQL database with pgvector extension
psql -U postgres -c "CREATE DATABASE vitaliq;"
psql -U postgres -d vitaliq -c "CREATE EXTENSION vector;"
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/vitaliq
SECRET_KEY=your-super-secret-key-change-in-production
OPENAI_API_KEY=sk-your-openai-api-key

# Optional: Wearable integrations
VITAL_API_KEY=
VITAL_MOCK_MODE=True
```

Run migrations and start the server:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

✅ Backend running at **http://localhost:8000**  
📚 API Docs at **http://localhost:8000/docs**

### 3. Frontend Setup

```bash
cd frontend

npm install
npm run dev
```

✅ Frontend running at **http://localhost:5173**

---

## 📁 Project Structure

```
VitalIQ/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── config.py         # Environment config
│   │   ├── database.py       # DB connection
│   │   ├── models/           # SQLAlchemy models
│   │   ├── routers/          # API endpoints
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   ├── ml/               # ML modules (anomaly, correlation)
│   │   ├── rag/              # RAG system for AI chat
│   │   └── integrations/     # External API integrations
│   ├── alembic/              # Database migrations
│   ├── knowledge_base/       # RAG knowledge documents
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── pages/            # Page components
│   │   ├── components/       # Reusable UI components
│   │   ├── api/              # API client
│   │   ├── contexts/         # React contexts
│   │   ├── hooks/            # Custom hooks
│   │   └── types/            # TypeScript definitions
│   └── package.json
│
└── README.md
```

---

## 🔧 Common Commands

| Command                                    | Description                   |
| ------------------------------------------ | ----------------------------- |
| `uvicorn app.main:app --reload`            | Start backend dev server      |
| `alembic upgrade head`                     | Run database migrations       |
| `alembic revision --autogenerate -m "msg"` | Create new migration          |
| `npm run dev`                              | Start frontend dev server     |
| `npm run build`                            | Build frontend for production |

---

## 🌐 API Overview

| Endpoint              | Description                      |
| --------------------- | -------------------------------- |
| `/api/auth/*`         | Authentication & user management |
| `/api/dashboard/*`    | Aggregated health overview       |
| `/api/nutrition/*`    | Food & nutrition tracking        |
| `/api/sleep/*`        | Sleep data & analysis            |
| `/api/exercise/*`     | Workout tracking                 |
| `/api/vitals/*`       | Heart rate, HRV, blood pressure  |
| `/api/anomalies/*`    | Anomaly detection results        |
| `/api/correlations/*` | Health metric correlations       |
| `/api/chat/*`         | AI health assistant              |
| `/api/briefing/*`     | Daily health summaries           |
| `/api/query/*`        | Natural language queries         |

---

## 🔑 Environment Variables

| Variable          | Description                         |
| ----------------- | ----------------------------------- |
| `DATABASE_URL`    | PostgreSQL connection string        |
| `SECRET_KEY`      | JWT signing key                     |
| `OPENAI_API_KEY`  | OpenAI API key for AI features      |
| `VITAL_API_KEY`   | Vital API for wearable integrations |
| `VITAL_MOCK_MODE` | Use mock data (default: `True`)     |

