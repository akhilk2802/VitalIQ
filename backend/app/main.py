from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.routers import auth, nutrition, sleep, exercise, vitals, body, chronic, anomalies, dashboard, mock, correlations


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    await init_db()
    yield
    # Shutdown


app = FastAPI(
    title=settings.APP_NAME,
    description="Personal Health & Wellness Aggregator - Unifying health data with AI-powered insights",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(nutrition.router, prefix=f"{settings.API_V1_PREFIX}/nutrition", tags=["Nutrition"])
app.include_router(sleep.router, prefix=f"{settings.API_V1_PREFIX}/sleep", tags=["Sleep"])
app.include_router(exercise.router, prefix=f"{settings.API_V1_PREFIX}/exercise", tags=["Exercise"])
app.include_router(vitals.router, prefix=f"{settings.API_V1_PREFIX}/vitals", tags=["Vitals"])
app.include_router(body.router, prefix=f"{settings.API_V1_PREFIX}/body", tags=["Body Metrics"])
app.include_router(chronic.router, prefix=f"{settings.API_V1_PREFIX}/chronic", tags=["Chronic Health"])
app.include_router(anomalies.router, prefix=f"{settings.API_V1_PREFIX}/anomalies", tags=["Anomalies"])
app.include_router(correlations.router, prefix=f"{settings.API_V1_PREFIX}/correlations", tags=["Correlations"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_PREFIX}/dashboard", tags=["Dashboard"])
app.include_router(mock.router, prefix=f"{settings.API_V1_PREFIX}/mock", tags=["Mock Data"])


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "healthy",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
