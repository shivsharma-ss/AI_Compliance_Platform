from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Sentinel AI Compliance Gateway"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str  # No default - must be provided in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    
    # Seeding
    SEED_DEFAULT_USERS: bool = False  # Gate seeding behind flag

    # Cloud mode — set to true when running on Cloud Run; disables Docker control
    CLOUD_MODE: bool = False

    # Module service URLs (when running in cloud mode)
    PRESIDIO_URL: Optional[str] = None
    TOXICITY_URL: Optional[str] = None
    EU_AI_URL: Optional[str] = None

    # Comma-separated list of enabled module names (e.g. "sentinel-presidio,sentinel-toxicity").
    # If empty or not provided, all known modules are considered enabled.
    ENABLED_MODULES: List[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors_origins(cls, value):
        """Allow comma-separated env var for CORS origins."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("ENABLED_MODULES", mode="before")
    @classmethod
    def split_enabled_modules(cls, value):
        """Allow comma-separated env var for enabled modules."""
        if isinstance(value, str):
            return [m.strip() for m in value.split(",") if m.strip()]
        return value
    
    class Config:
        env_file = ".env"

settings = Settings()
