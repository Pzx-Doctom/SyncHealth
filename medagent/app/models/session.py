"""数据库模型 - 会话与消息"""
from datetime import datetime, timezone

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Session(Base):
    """对话会话"""
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="新对话")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Message.id"
    )


class Message(Base):
    """对话消息（含多 Agent 追踪信息）"""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant | system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # 多 Agent 追踪元数据（JSON）
    agent_route: Mapped[list] = mapped_column(JSON, default=list)          # Agent 流转路径
    tool_calls: Mapped[list] = mapped_column(JSON, default=list)           # 工具调用记录
    memory_recalls: Mapped[list] = mapped_column(JSON, default=list)       # 记忆召回
    thinking_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_agent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rag_references: Mapped[list] = mapped_column(JSON, default=list)       # RAG 引用

    session: Mapped["Session"] = relationship(back_populates="messages")
