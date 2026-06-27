"""MedAgent Hub 配置管理 - Pydantic Settings"""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "MedAgent Hub"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # ===== 独立数据库 =====
    DATABASE_URL: str = f"sqlite+aiosqlite:///{Path(__file__).resolve().parent.parent / 'data' / 'medagent.db'}"

    # ===== JWT（与 SyncHealth backend 共享密钥） =====
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"

    # ===== SyncHealth MCP Server =====
    SYNCHEALTH_BASE_URL: str = "http://localhost:8000"
    SYNCHEALTH_MCP_TOKEN: str = ""

    # ===== LLM Provider =====
    AI_PROVIDER: str = "domestic"  # openai | domestic | local
    AI_BASE_URL: str = "https://api.deepseek.com/v1"
    AI_API_KEY: str = ""
    AI_MODEL: str = "deepseek-chat"
    AI_TEMPERATURE: float = 0.7

    # 多模态 OCR 模型（药盒/报告识别）
    VISION_MODEL: str = "deepseek-chat"

    # ===== 向量存储 / 嵌入（默认硅基流动 SiliconFlow，OpenAI 兼容） =====
    CHROMA_PERSIST_DIR: str = str(Path(__file__).resolve().parent.parent / "data" / "chroma")
    EMBEDDING_MODEL: str = "BAAI/bge-large-zh-v1.5"
    EMBEDDING_BASE_URL: str = "https://api.siliconflow.cn/v1"
    EMBEDDING_API_KEY: str = ""

    # ===== 地图 API =====
    AMAP_API_KEY: str = ""

    # ===== 循环控制 =====
    MAX_LOOPS: int = 5

    # ===== 错误处理 =====
    LLM_MAX_RETRIES: int = 3
    TOOL_TIMEOUT_SECONDS: int = 15
    MCP_RECONNECT_RETRIES: int = 3

    # ===== CORS =====
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
