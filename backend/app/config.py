from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/vitaliq"
    
    # JWT Configuration
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    
    # Vital API (external health data integration)
    VITAL_API_KEY: str = ""
    VITAL_API_SECRET: str = ""
    VITAL_ENVIRONMENT: str = "sandbox"  # "sandbox" or "production"
    VITAL_WEBHOOK_SECRET: str = ""
    VITAL_MOCK_MODE: bool = True  # Use mock data instead of real API calls
    
    # App Settings
    DEBUG: bool = True
    APP_NAME: str = "VitalIQ"
    API_V1_PREFIX: str = "/api"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
