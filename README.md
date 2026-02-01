# VitalIQ - Personal Health & Wellness Aggregator

A unified platform that aggregates health data from multiple sources, providing AI-powered anomaly detection and actionable insights.

## Features

- **Unified Health Dashboard** - View all health metrics in one place
- **Comprehensive Tracking** - Nutrition, Sleep, Exercise, Vitals, Body Metrics, Chronic Conditions
- **ML-Powered Anomaly Detection** - Z-Score and Isolation Forest algorithms
- **AI Insights** - OpenAI-powered explanations and recommendations
- **Health Score** - Overall wellness scoring with trend analysis

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0
- **Database**: PostgreSQL with asyncpg
- **ML**: scikit-learn (Isolation Forest), NumPy, Pandas
- **AI**: OpenAI GPT-4 for insights
- **Auth**: JWT with bcrypt password hashing

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- OpenAI API key (optional, for AI insights)

### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create `.env` file**
   ```bash
   # Copy from example and edit
   cp .env.example .env
   ```
   
   Configure your `.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/vitaliq
   SECRET_KEY=your-super-secret-key-change-in-production
   OPENAI_API_KEY=your-openai-api-key
   ```

5. **Create PostgreSQL database**
   ```bash
   createdb vitaliq
   ```

6. **Run migrations**
   ```bash
   alembic upgrade head
   ```

7. **Start the server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

8. **Access API docs**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API Endpoints

### Authentication
| Method | Endpoint             | Description              |
| ------ | -------------------- | ------------------------ |
| POST   | `/api/auth/register` | Register new user        |
| POST   | `/api/auth/login`    | Login, get JWT token     |
| GET    | `/api/auth/me`       | Get current user profile |

### Health Metrics
| Category  | Endpoints                                                     |
| --------- | ------------------------------------------------------------- |
| Nutrition | `GET/POST /api/nutrition`, `GET /api/nutrition/daily-summary` |
| Sleep     | `GET/POST /api/sleep`, `GET /api/sleep/stats`                 |
| Exercise  | `GET/POST /api/exercise`, `GET /api/exercise/weekly-summary`  |
| Vitals    | `GET/POST /api/vitals`                                        |
| Body      | `GET/POST /api/body`                                          |
| Chronic   | `GET/POST /api/chronic`, `GET /api/chronic/trends`            |

### Anomaly Detection
| Method | Endpoint                  | Description               |
| ------ | ------------------------- | ------------------------- |
| GET    | `/api/anomalies`          | List detected anomalies   |
| POST   | `/api/anomalies/detect`   | Trigger anomaly detection |
| GET    | `/api/anomalies/insights` | Get AI-generated insights |

### Dashboard
| Method | Endpoint                      | Description              |
| ------ | ----------------------------- | ------------------------ |
| GET    | `/api/dashboard`              | Unified health dashboard |
| GET    | `/api/dashboard/health-score` | Overall health score     |

### Testing
| Method | Endpoint             | Description        |
| ------ | -------------------- | ------------------ |
| POST   | `/api/mock/generate` | Generate mock data |

## Quick Start Demo

1. Register a user via `/api/auth/register`
2. Login to get JWT token via `/api/auth/login`
3. Generate mock data: `POST /api/mock/generate?days=60`
4. Run anomaly detection: `POST /api/anomalies/detect`
5. View dashboard: `GET /api/dashboard?days=7`
6. Get insights: `GET /api/anomalies/insights`

## Anomaly Detection

VitalIQ uses two ML algorithms for anomaly detection:

### Z-Score Detector
- Detects single-metric anomalies
- Configurable thresholds per metric
- Considers absolute medical bounds

### Isolation Forest
- Detects multivariate anomalies
- Finds unusual combinations of metrics
- Identifies patterns not visible in individual metrics

### Ensemble
- Combines both detectors
- Ranks by severity and confidence
- Deduplicates overlapping detections

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings management
│   ├── database.py          # PostgreSQL connection
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic schemas
│   ├── routers/             # API endpoints
│   ├── services/            # Business logic
│   ├── ml/                  # ML anomaly detection
│   │   ├── detectors/       # Z-Score & Isolation Forest
│   │   ├── ensemble.py      # Result combination
│   │   └── feature_engineering.py
│   └── utils/               # Helpers & utilities
├── alembic/                 # Database migrations
└── requirements.txt
```

## License

MIT

---

### Hackathon Project
Built for demonstrating AI-powered health analytics with real ML anomaly detection.
