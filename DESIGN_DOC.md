# VitalIQ — Design Doc

> **Version:** 1.0  
> **Last Updated:** February 2026  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Tech Stack Overview](#3-tech-stack-overview)
4. [Database Design](#4-database-design)
5. [Backend Architecture](#5-backend-architecture)
6. [Frontend Architecture](#6-frontend-architecture)
7. [ML Pipeline](#7-ml-pipeline)
8. [RAG System](#8-rag-system)
9. [API Design](#9-api-design)
10. [Security & Authentication](#10-security--authentication)
11. [Data Flow](#11-data-flow)
12. [Key Features Deep Dive](#12-key-features-deep-dive)
13. [Scalability Considerations](#13-scalability-considerations)
14. [Future Roadmap](#14-future-roadmap)

---

## 1. Executive Summary

### Purpose

VitalIQ is an AI-powered personal health analytics platform that aggregates health data from multiple sources (wearables, manual input), applies machine learning to detect anomalies and correlations, and provides personalized health insights through a conversational AI interface powered by RAG (Retrieval-Augmented Generation).

### Problem Statement

Health data is fragmented across multiple devices and apps. Users struggle to:
- Understand relationships between different health metrics
- Identify unusual patterns that may require attention
- Get actionable, personalized health insights

### Solution

VitalIQ provides:
- **Unified Dashboard** — Single view of all health metrics
- **Anomaly Detection** — ML-powered unusual pattern detection
- **Correlation Analysis** — Discover relationships between metrics
- **AI Health Assistant** — Context-aware chat powered by RAG

---

## 2. System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐   │
│  │  Dashboard  │  │   Trends    │  │   Alerts    │  │  AI Chat     │   │
│  │    Page     │  │    Page     │  │    Page     │  │  (WebSocket) │   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘   │
│         │                │                │                 │           │
│         └────────────────┴────────────────┴─────────────────┘           │
│                                   │                                      │
│                          React Query + Axios                             │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │ HTTP/WebSocket
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              BACKEND (FastAPI)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐   │
│  │   Routers   │  │  Services   │  │  ML Engine  │  │  RAG System  │   │
│  │  (API)      │  │  (Logic)    │  │  (Analysis) │  │  (AI Chat)   │   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘   │
│         │                │                │                 │           │
│         └────────────────┴────────────────┴─────────────────┘           │
│                                   │                                      │
│                            SQLAlchemy (Async)                            │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         PostgreSQL + pgvector                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐   │
│  │ Health Data │  │  Anomalies  │  │Correlations │  │  Embeddings  │   │
│  │   Tables    │  │   Table     │  │   Table     │  │  (Vectors)   │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          External Services                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │  OpenAI API │  │  Vital API  │  │   PubMed    │                      │
│  │  (GPT-4)    │  │ (Wearables) │  │   (Research)│                      │
│  └─────────────┘  └─────────────┘  └─────────────┘                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Interaction

```
User Action → Frontend → API Router → Service Layer → Database/ML/RAG → Response
```

---

## 3. Tech Stack Overview

### Frontend Stack

| Component     | Technology            | Purpose                               |
| ------------- | --------------------- | ------------------------------------- |
| Framework     | React 19              | UI rendering with latest features     |
| Language      | TypeScript            | Type safety and developer experience  |
| Build Tool    | Vite                  | Fast development and optimized builds |
| Styling       | TailwindCSS           | Utility-first CSS framework           |
| Components    | Radix UI              | Accessible, unstyled primitives       |
| Data Fetching | React Query           | Server state management with caching  |
| State         | Zustand               | Lightweight client state management   |
| Routing       | React Router v7       | Client-side navigation                |
| Charts        | Recharts              | Health data visualizations            |
| Forms         | React Hook Form + Zod | Form handling with validation         |

### Backend Stack

| Component  | Technology                  | Purpose                        |
| ---------- | --------------------------- | ------------------------------ |
| Framework  | FastAPI                     | High-performance async API     |
| Language   | Python 3.12                 | ML ecosystem and async support |
| ORM        | SQLAlchemy 2.0              | Async database operations      |
| Migrations | Alembic                     | Database schema versioning     |
| Validation | Pydantic v2                 | Request/response validation    |
| Auth       | python-jose + passlib       | JWT authentication             |
| ML         | scikit-learn, pandas, numpy | Analytics and detection        |
| AI         | OpenAI API (GPT-4)          | Chat and embeddings            |

### Database Stack

| Component     | Technology     | Purpose                   |
| ------------- | -------------- | ------------------------- |
| Primary DB    | PostgreSQL 15+ | Relational data storage   |
| Vector Search | pgvector       | Similarity search for RAG |
| Connection    | asyncpg        | Async PostgreSQL driver   |

---

## 4. Database Design

### Entity Relationship Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                              USER                                     │
│  id (PK) | email | password_hash | name | created_at | preferences   │
└────────────────────────────────────┬─────────────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────────┐
         │                           │                               │
         ▼                           ▼                               ▼
┌─────────────────┐     ┌─────────────────┐           ┌─────────────────┐
│   FOOD_ENTRY    │     │   SLEEP_ENTRY   │           │ EXERCISE_ENTRY  │
│ user_id (FK)    │     │ user_id (FK)    │           │ user_id (FK)    │
│ date            │     │ date            │           │ date            │
│ calories        │     │ duration_hours  │           │ duration_min    │
│ protein_g       │     │ quality_score   │           │ calories_burned │
│ carbs_g         │     │ deep_sleep_pct  │           │ intensity       │
│ fats_g          │     │ rem_sleep_pct   │           │ activity_type   │
└─────────────────┘     └─────────────────┘           └─────────────────┘

         ┌───────────────────────────┼───────────────────────────────┐
         │                           │                               │
         ▼                           ▼                               ▼
┌─────────────────┐     ┌─────────────────┐           ┌─────────────────┐
│   VITAL_SIGNS   │     │  BODY_METRICS   │           │ CHRONIC_METRICS │
│ user_id (FK)    │     │ user_id (FK)    │           │ user_id (FK)    │
│ date            │     │ date            │           │ date            │
│ resting_hr      │     │ weight_kg       │           │ blood_glucose   │
│ hrv             │     │ body_fat_pct    │           │ a1c             │
│ bp_systolic     │     │ muscle_mass_kg  │           │ cholesterol     │
│ bp_diastolic    │     │ bmi             │           │ triglycerides   │
└─────────────────┘     └─────────────────┘           └─────────────────┘

                                     │
         ┌───────────────────────────┼───────────────────────────────┐
         │                           │                               │
         ▼                           ▼                               ▼
┌─────────────────┐     ┌─────────────────┐           ┌─────────────────┐
│    ANOMALY      │     │  CORRELATION    │           │  CHAT_SESSION   │
│ user_id (FK)    │     │ user_id (FK)    │           │ user_id (FK)    │
│ date            │     │ metric_a        │           │ title           │
│ metric_name     │     │ metric_b        │           │ is_active       │
│ metric_value    │     │ correlation_val │           │ created_at      │
│ baseline_value  │     │ p_value         │           │                 │
│ severity        │     │ lag_days        │           │                 │
│ detector_type   │     │ confidence      │           │                 │
└─────────────────┘     └─────────────────┘           └─────────────────┘
```

### Vector Tables (RAG)

```
┌─────────────────────────────────────────────────────────────────────┐
│                      KNOWLEDGE_EMBEDDING                             │
│  id | source_type | source_id | title | content | embedding (vector)│
│  metadata (JSONB) | created_at                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    USER_HISTORY_EMBEDDING                            │
│  id | user_id | entity_type | entity_id | content | embedding       │
│  metadata (JSONB) | created_at                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Indexes

- **Health Tables**: `(user_id, date)` for time-series queries
- **Anomalies**: `(user_id, date, metric_name)` for duplicate detection
- **Correlations**: `(user_id, confidence_score DESC)` for ranking
- **Vector Tables**: `embedding` using `ivfflat` for similarity search

---

## 5. Backend Architecture

### Directory Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Environment configuration
│   ├── database.py          # Database connection and session
│   │
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── food_entry.py
│   │   ├── sleep_entry.py
│   │   ├── anomaly.py
│   │   ├── correlation.py
│   │   └── ...
│   │
│   ├── schemas/             # Pydantic request/response schemas
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   ├── anomaly.py
│   │   └── ...
│   │
│   ├── routers/             # API endpoint handlers
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── dashboard.py     # Dashboard data aggregation
│   │   ├── anomalies.py     # Anomaly detection endpoints
│   │   ├── correlations.py  # Correlation analysis endpoints
│   │   ├── chat.py          # AI chat endpoints
│   │   └── ...
│   │
│   ├── services/            # Business logic layer
│   │   ├── auth_service.py
│   │   ├── anomaly_service.py
│   │   ├── correlation_service.py
│   │   ├── chat_service.py
│   │   └── ...
│   │
│   ├── ml/                  # Machine learning modules
│   │   ├── detectors/       # Anomaly detection algorithms
│   │   ├── correlation/     # Correlation analysis algorithms
│   │   ├── prediction/      # Predictive models
│   │   ├── ensemble.py      # Ensemble methods
│   │   └── feature_engineering.py
│   │
│   ├── rag/                 # RAG (Retrieval-Augmented Generation)
│   │   ├── embedding_service.py
│   │   ├── vector_service.py
│   │   ├── health_knowledge_rag.py
│   │   ├── user_history_rag.py
│   │   └── prompt_builder.py
│   │
│   └── utils/               # Shared utilities
│       ├── security.py      # JWT handling
│       ├── enums.py         # Shared enumerations
│       └── rate_limiter.py  # API rate limiting
│
├── alembic/                 # Database migrations
│   └── versions/
│       ├── 001_initial_schema.py
│       ├── 002_add_correlations.py
│       ├── 003_add_integrations.py
│       └── 004_add_pgvector_rag.py
│
└── knowledge_base/          # RAG curated knowledge
    ├── metrics/
    │   ├── heart/
    │   ├── sleep/
    │   └── nutrition/
    ├── correlations/
    └── interventions/
```

### Layered Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        ROUTERS (API Layer)                      │
│  - Request validation (Pydantic schemas)                        │
│  - Route handling                                               │
│  - Response formatting                                          │
└─────────────────────────────────┬──────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────┐
│                      SERVICES (Business Logic)                  │
│  - Core business rules                                          │
│  - Orchestration of ML/RAG                                      │
│  - Data transformation                                          │
└─────────────────────────────────┬──────────────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
┌─────────────────────┐ ┌─────────────┐ ┌─────────────────────┐
│    ML MODULES       │ │ RAG SYSTEM  │ │  MODELS (ORM)       │
│ - Anomaly detection │ │ - Embeddings│ │ - Database entities │
│ - Correlation       │ │ - Retrieval │ │ - Relationships     │
│ - Prediction        │ │ - Prompts   │ │                     │
└─────────────────────┘ └─────────────┘ └─────────────────────┘
```

---

## 6. Frontend Architecture

### Directory Structure

```
frontend/src/
├── main.tsx                 # Application entry point
├── App.tsx                  # Root component with routing
│
├── api/                     # API client layer
│   ├── client.ts           # Axios instance configuration
│   ├── auth.ts             # Authentication API calls
│   ├── dashboard.ts        # Dashboard data fetching
│   ├── anomalies.ts        # Anomaly endpoints
│   ├── correlations.ts     # Correlation endpoints
│   ├── chat.ts             # Chat API + WebSocket
│   └── index.ts            # Centralized exports
│
├── components/
│   ├── ui/                  # Reusable UI primitives (Radix-based)
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   └── ...
│   │
│   ├── layout/              # App layout components
│   │   ├── AppLayout.tsx    # Main app shell
│   │   ├── Sidebar.tsx      # Navigation sidebar
│   │   └── Header.tsx       # Top header bar
│   │
│   ├── dashboard/           # Dashboard-specific components
│   │   ├── HealthScoreRing.tsx
│   │   ├── MetricCard.tsx
│   │   ├── AnomalySection.tsx
│   │   ├── CorrelationSection.tsx
│   │   └── MorningBriefingCard.tsx
│   │
│   ├── charts/              # Data visualization components
│   │   ├── HealthChart.tsx
│   │   ├── TrendChart.tsx
│   │   └── CorrelationChart.tsx
│   │
│   └── chat/                # AI chat components
│       ├── ChatDrawer.tsx   # Slide-out chat panel
│       ├── ChatFAB.tsx      # Floating action button
│       ├── ChatMessage.tsx  # Message bubbles
│       └── ChatSuggestions.tsx
│
├── contexts/                # React contexts
│   ├── AuthContext.tsx     # Authentication state
│   ├── SettingsContext.tsx # User preferences
│   └── SidebarContext.tsx  # Sidebar state
│
├── hooks/                   # Custom hooks
│   ├── useDashboard.ts     # Dashboard data fetching
│   └── index.ts
│
├── pages/                   # Page components (routes)
│   ├── DashboardPage.tsx
│   ├── TrendsPage.tsx
│   ├── AlertsPage.tsx
│   ├── CorrelationsPage.tsx
│   ├── BriefingPage.tsx
│   ├── LoginPage.tsx
│   └── ...
│
├── types/                   # TypeScript type definitions
│   ├── api.ts              # API response types
│   ├── health.ts           # Health metric types
│   └── index.ts
│
└── lib/                     # Utilities
    ├── utils.ts            # Helper functions
    ├── constants.ts        # App constants
    └── validators.ts       # Zod schemas
```

### State Management Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                        STATE ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │   SERVER STATE   │    │   CLIENT STATE   │                   │
│  │   (React Query)  │    │    (Zustand)     │                   │
│  ├──────────────────┤    ├──────────────────┤                   │
│  │ • Health data    │    │ • UI state       │                   │
│  │ • Anomalies      │    │ • Sidebar open   │                   │
│  │ • Correlations   │    │ • Theme          │                   │
│  │ • User profile   │    │ • Chat open      │                   │
│  │ • Chat history   │    │                  │                   │
│  └──────────────────┘    └──────────────────┘                   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                   AUTH STATE (Context)                │       │
│  │  • User session  • Token management  • Auth status   │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. ML Pipeline

### Anomaly Detection System

VitalIQ uses an **ensemble approach** combining multiple detectors:

```
                    ┌─────────────────────────────────────┐
                    │         Feature Engineering          │
                    │  • Daily feature matrix aggregation  │
                    │  • Baseline calculation              │
                    │  • Missing value handling            │
                    └─────────────────────┬───────────────┘
                                          │
                    ┌─────────────────────┴───────────────┐
                    │                                      │
                    ▼                                      ▼
          ┌─────────────────────┐            ┌─────────────────────┐
          │   Z-Score Detector  │            │ Isolation Forest    │
          ├─────────────────────┤            ├─────────────────────┤
          │ • Statistical       │            │ • Multivariate      │
          │ • Per-metric        │            │ • Pattern-based     │
          │ • Robust (IQR)      │            │ • Unsupervised      │
          │ • Adaptive thresh.  │            │ • Contamination=5%  │
          └──────────┬──────────┘            └──────────┬──────────┘
                     │                                   │
                     └───────────────┬───────────────────┘
                                     │
                                     ▼
                    ┌─────────────────────────────────────┐
                    │         Anomaly Ensemble            │
                    │  • Weighted combination             │
                    │  • Deduplication                    │
                    │  • Severity ranking                 │
                    │  • Z-Score: 40%, IForest: 60%       │
                    └─────────────────────────────────────┘
```

#### Detector Details

| Detector         | Type        | Strengths                 | Use Case             |
| ---------------- | ----------- | ------------------------- | -------------------- |
| Z-Score          | Statistical | Interpretable, per-metric | Single metric spikes |
| Isolation Forest | ML-based    | Multivariate patterns     | Complex anomalies    |
| Ensemble         | Combined    | Best of both              | Final output         |

#### Severity Calculation

```python
# Ensemble score calculation
combined_score = (zscore_weight * zscore_score) + (iforest_weight * iforest_score)

# Severity thresholds
if score >= 0.75: severity = HIGH
elif score >= 0.45: severity = MEDIUM
else: severity = LOW
```

### Correlation Analysis System

```
┌─────────────────────────────────────────────────────────────────┐
│                    CORRELATION AGGREGATOR                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │   Pearson   │ │   Granger   │ │    Cross    │ │  Mutual   │ │
│  │ Correlation │ │  Causality  │ │ Correlation │ │   Info    │ │
│  ├─────────────┤ ├─────────────┤ ├─────────────┤ ├───────────┤ │
│  │ Linear      │ │ Causal dir. │ │ Time-lagged │ │ Non-linear│ │
│  │ Strength    │ │ F-statistic │ │ Lag days    │ │ Dependence│ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
│                                                                  │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Population Baseline Enrichment              │    │
│  │  • Compare to population averages                        │    │
│  │  • Calculate percentile rank                            │    │
│  │  • Flag actionable correlations                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Correlation Types

| Method             | Purpose                     | Output             |
| ------------------ | --------------------------- | ------------------ |
| Pearson            | Linear correlation strength | -1 to 1, p-value   |
| Granger Causality  | Causal direction            | F-stat, direction  |
| Cross-Correlation  | Time-lagged effects         | Optimal lag (days) |
| Mutual Information | Non-linear dependencies     | MI score           |

---

## 8. RAG System

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        RAG PIPELINE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  USER QUERY: "Why is my sleep worse when I exercise late?"      │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   QUERY PROCESSING                       │    │
│  │  • Detect metrics (sleep, exercise)                     │    │
│  │  • Enhance with metric-specific terms                   │    │
│  │  • Generate query embedding (text-embedding-3-large)    │    │
│  └────────────────────────┬────────────────────────────────┘    │
│                           │                                      │
│           ┌───────────────┼───────────────┐                     │
│           │               │               │                      │
│           ▼               ▼               ▼                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐            │
│  │   Health    │ │    User     │ │    Recent       │            │
│  │  Knowledge  │ │   History   │ │    Metrics      │            │
│  ├─────────────┤ ├─────────────┤ ├─────────────────┤            │
│  │ Curated docs│ │ Past chats  │ │ Last 7 days     │            │
│  │ PubMed      │ │ Anomalies   │ │ Feature matrix  │            │
│  │ MedlinePlus │ │ Correlations│ │                 │            │
│  └──────┬──────┘ └──────┬──────┘ └────────┬────────┘            │
│         │               │                  │                     │
│         └───────────────┼──────────────────┘                     │
│                         │                                        │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   PROMPT BUILDER                         │    │
│  │  • System prompt (health assistant persona)             │    │
│  │  • Retrieved knowledge context                          │    │
│  │  • User's health history context                        │    │
│  │  • Conversation history (last 10 messages)              │    │
│  │  • User query                                           │    │
│  └────────────────────────┬────────────────────────────────┘    │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   GPT-4 GENERATION                       │    │
│  │  • Streaming response via WebSocket                     │    │
│  │  • Context-aware, personalized                          │    │
│  │  • Grounded in retrieved knowledge                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Knowledge Sources

| Source       | Type           | Content                          | Update Frequency |
| ------------ | -------------- | -------------------------------- | ---------------- |
| Curated      | Markdown files | Sleep science, HRV, nutrition    | Manual           |
| PubMed       | API            | Research abstracts               | On-demand        |
| MedlinePlus  | API            | Consumer health info             | On-demand        |
| User History | Database       | Personal anomalies, correlations | Real-time        |

### Vector Search Configuration

```python
# Embedding model
OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSIONS = 3072

# Chunking
RAG_CHUNK_SIZE = 1000    # characters
RAG_CHUNK_OVERLAP = 200  # characters

# Retrieval
RAG_TOP_K = 5           # chunks per query
SIMILARITY_THRESHOLD = 0.3
```

---

## 9. API Design

### RESTful Endpoints

| Category        | Method | Endpoint                           | Description                  |
| --------------- | ------ | ---------------------------------- | ---------------------------- |
| **Auth**        | POST   | `/api/auth/register`               | User registration            |
|                 | POST   | `/api/auth/login`                  | User login (returns JWT)     |
|                 | GET    | `/api/auth/me`                     | Get current user             |
| **Dashboard**   | GET    | `/api/dashboard/summary`           | Aggregated health overview   |
|                 | GET    | `/api/dashboard/metrics`           | Detailed metrics             |
| **Health Data** | GET    | `/api/nutrition/`                  | Get food entries             |
|                 | POST   | `/api/nutrition/`                  | Add food entry               |
|                 | GET    | `/api/sleep/`                      | Get sleep entries            |
|                 | GET    | `/api/vitals/`                     | Get vital signs              |
| **Analysis**    | GET    | `/api/anomalies/`                  | Get detected anomalies       |
|                 | POST   | `/api/anomalies/detect`            | Run anomaly detection        |
|                 | GET    | `/api/correlations/`               | Get correlations             |
|                 | POST   | `/api/correlations/detect`         | Run correlation analysis     |
| **AI Features** | GET    | `/api/briefing/`                   | Get morning briefing         |
|                 | POST   | `/api/query/`                      | Natural language query       |
| **Chat**        | GET    | `/api/chat/sessions`               | List chat sessions           |
|                 | POST   | `/api/chat/sessions`               | Create new session           |
|                 | POST   | `/api/chat/sessions/{id}/messages` | Send message (non-streaming) |

### WebSocket Endpoints

```
WS /ws/chat/{session_id}?token={jwt}

Client → Server:
{
  "message": "Why is my sleep worse?"
}

Server → Client (streaming):
{ "type": "chunk", "content": "Based on your..." }
{ "type": "chunk", "content": " data, I can see..." }
{ "type": "done", "message_id": "uuid" }
```

### Response Format

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "total": 100,
    "page": 1,
    "limit": 20
  }
}
```

---

## 10. Security & Authentication

### Authentication Flow

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   Client    │       │   Backend   │       │  Database   │
└──────┬──────┘       └──────┬──────┘       └──────┬──────┘
       │                     │                     │
       │  POST /auth/login   │                     │
       │  {email, password}  │                     │
       │────────────────────>│                     │
       │                     │  Verify password    │
       │                     │────────────────────>│
       │                     │<────────────────────│
       │                     │                     │
       │   {access_token}    │  Generate JWT       │
       │<────────────────────│                     │
       │                     │                     │
       │  GET /api/resource  │                     │
       │  Authorization:     │                     │
       │  Bearer <token>     │                     │
       │────────────────────>│                     │
       │                     │  Validate JWT       │
       │                     │  Extract user_id    │
       │   {resource_data}   │                     │
       │<────────────────────│                     │
```

### Security Measures

| Measure          | Implementation              |
| ---------------- | --------------------------- |
| Password Hashing | bcrypt with salt            |
| JWT Tokens       | HS256 algorithm, 24h expiry |
| CORS             | Configurable origins        |
| Input Validation | Pydantic schemas            |
| SQL Injection    | SQLAlchemy ORM              |
| Rate Limiting    | Per-endpoint limits         |

### JWT Token Structure

```json
{
  "sub": "user_uuid",
  "exp": 1234567890,
  "iat": 1234567890
}
```

---

## 11. Data Flow

### Health Data Ingestion Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA INGESTION FLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐        │
│  │   Manual    │     │   Vital     │     │   Future:   │        │
│  │   Entry     │     │   API       │     │   Apple/Fit │        │
│  └──────┬──────┘     └──────┬──────┘     └──────┬──────┘        │
│         │                   │                   │                │
│         └───────────────────┼───────────────────┘                │
│                             │                                    │
│                             ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    NORMALIZERS                           │    │
│  │  • Convert units  • Validate ranges  • Fill defaults    │    │
│  └────────────────────────┬────────────────────────────────┘    │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    DATABASE TABLES                       │    │
│  │  food_entries | sleep_entries | exercise_entries | ...  │    │
│  └────────────────────────┬────────────────────────────────┘    │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              BACKGROUND ANALYSIS (Optional)              │    │
│  │  • Anomaly detection  • Correlation updates             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Chat/RAG Data Flow

```
User Message
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. Save user message to chat_messages                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Gather RAG Context                                           │
│    a. Build feature matrix (last 7 days)                       │
│    b. Retrieve health knowledge (vector similarity)            │
│    c. Retrieve user history (past insights, anomalies)         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Build Prompt                                                 │
│    • System prompt + knowledge context + user context + query  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Stream Response (GPT-4)                                      │
│    • WebSocket chunks → Client                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Save assistant message + Index for future retrieval          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 12. Key Features Deep Dive

### Morning Briefing Generation

The daily health briefing aggregates overnight data and provides actionable insights:

```python
# Briefing components
1. Sleep quality summary (last night)
2. Vital signs overview (resting HR, HRV)
3. Recent anomalies (last 24h)
4. Active correlations affecting today
5. Personalized recommendations
```

**Generation Flow:**
1. Fetch last night's sleep data
2. Get morning vitals
3. Check for new anomalies
4. Pull top correlations
5. Generate narrative via GPT-4

### Anomaly Explanation

When an anomaly is detected:

```
Anomaly: HRV dropped 35% below baseline

RAG Context Retrieved:
- "Low HRV can indicate stress, poor sleep, or overtraining..."
- "HRV recovery typically takes 24-48 hours..."

AI Explanation:
"Your HRV is significantly lower than your usual range.
Based on your data, this might be related to:
1. The intense workout you logged yesterday
2. Your sleep quality was 20% below normal
Consider taking a recovery day today."
```

### Natural Language Queries

Users can ask questions in plain English:

```
User: "How did my sleep change after I started running?"

Processing:
1. Extract entities: sleep, running (exercise)
2. Query correlation table for sleep ↔ exercise
3. Analyze time series: before vs after running started
4. Generate response with data-backed insights
```

---

## 13. Scalability Considerations

### Current Architecture Limits

| Component     | Current Limit     | Scaling Strategy                  |
| ------------- | ----------------- | --------------------------------- |
| Database      | Single PostgreSQL | Read replicas, connection pooling |
| API           | Single instance   | Horizontal scaling (stateless)    |
| ML Processing | Synchronous       | Background job queue (Celery)     |
| Vector Search | pgvector          | Dedicated vector DB (Pinecone)    |
| OpenAI API    | Rate limits       | Request queuing, caching          |

### Recommended Scaling Path

```
Phase 1 (Current): Single server deployment
     │
     ▼
Phase 2: Add Redis for caching + session store
     │
     ▼
Phase 3: Background job queue for ML tasks
     │
     ▼
Phase 4: Database read replicas
     │
     ▼
Phase 5: Kubernetes orchestration
```

### Performance Optimizations Implemented

- **Async everywhere**: All database operations are async
- **Connection pooling**: SQLAlchemy async session factory
- **Query optimization**: Indexes on frequently queried columns
- **Response caching**: React Query client-side caching
- **Lazy loading**: Feature matrix computed on-demand
- **Batch operations**: Bulk inserts for sync operations

---

## 14. Future Roadmap

### Short-term (Q1 2026)

- Apple HealthKit direct integration
- Google Fit integration
- Medication tracking module
- Improved anomaly explanations

### Medium-term (Q2-Q3 2026)

- Mobile app (React Native)
- Predictive models (sleep prediction, energy forecasting)

### Long-term (2026+)

- Multi-language support
- HIPAA compliance for clinical use
- Integration with EHR systems
- Community benchmarking (opt-in)

---

## Appendix

### A. Environment Variables Reference

```env
# Required
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/vitaliq
SECRET_KEY=your-jwt-secret
OPENAI_API_KEY=sk-...

# Optional
VITAL_API_KEY=           # Wearable integration
VITAL_MOCK_MODE=True     # Use mock data
PUBMED_EMAIL=            # PubMed API access
DEBUG=True               # Enable debug logging
```

### B. Database Migration Commands

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

### C. Useful Development Commands

```bash
# Backend
uvicorn app.main:app --reload --port 8000

# Frontend
npm run dev

# Database shell
psql -U postgres -d vitaliq
```

---

