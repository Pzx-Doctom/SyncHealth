"""MedAgent Hub - FastAPI 应用入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse

from app.config import settings
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：初始化数据库 + ChromaDB + MCP 连接预热
    await init_db()

    # 延迟导入，避免循环依赖
    from app.memory.vector_store import init_vector_store
    from app.mcp.client import mcp_client

    init_vector_store()
    await mcp_client.warmup()

    yield

    # 关闭：清理资源
    await mcp_client.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="MedAgent Hub - 基于 LangChain/LangGraph 的多智能体医疗健康协作系统",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api.router import api_router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/")
    async def root():
        return RedirectResponse(url="/docs")

    return app


app = create_app()
