from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "SyncHealth"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{Path(__file__).resolve().parent.parent / 'data' / 'synchealth.db'}"

    # JWT
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # AI
    AI_PROVIDER: str = "openai"  # openai | domestic | local
    AI_BASE_URL: str = "https://api.openai.com/v1"
    AI_API_KEY: str = ""
    AI_MODEL: str = "gpt-4o"
    AI_MAX_CONTEXT_TOKENS: int = 8000
    AI_TEMPERATURE: float = 0.7

    # Dify Knowledge Base
    DIFY_API_BASE: str = "https://api.dify.ai/v1"
    DIFY_API_KEY: str = ""
    DIFY_DATASET_ID: str = ""
    DIFY_RETRIEVE_ENABLED: bool = False
    DIFY_SEARCH_METHOD: str = ""  # keyword_search | semantic_search | full_text_search | hybrid_search | ""(use dataset default)
    DIFY_RETRIEVE_TOP_K: int = 5
    DIFY_SCORE_THRESHOLD_ENABLED: bool = False
    DIFY_SCORE_THRESHOLD: float = 0.5

    # Apple Health 导入
    UPLOAD_DIR: str = "./data/uploads"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:3001", "http://localhost:8081", "http://localhost:8082"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
