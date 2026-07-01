from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Columns that may need to be added to existing tables via ALTER TABLE.
# SQLite's CREATE TABLE IF NOT EXISTS won't add new columns to existing tables.
_MIGRATIONS: list[tuple[str, str, str]] = [
    # (table_name, column_name, column_type)
    ("chat_messages", "dify_context_snapshot", "TEXT"),
]


async def _run_migrations(conn) -> None:
    """Add missing columns to existing tables (SQLite safe)."""
    for table, column, col_type in _MIGRATIONS:
        result = await conn.execute(text(f"PRAGMA table_info({table})"))
        existing_columns = {row[1] for row in result}
        if column not in existing_columns:
            await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))


async def init_db():
    async with engine.begin() as conn:
        # create_all 在多 worker 并发启动时有竞态，捕获 "already exists" 错误
        try:
            await conn.run_sync(Base.metadata.create_all)
        except OperationalError:
            pass  # 另一个 worker 已建表，忽略
        await _run_migrations(conn)
