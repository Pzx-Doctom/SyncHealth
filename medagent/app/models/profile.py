"""数据库模型 - Agent 配置与用户画像"""
from datetime import datetime, timezone

from sqlalchemy import Integer, String, Text, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgentConfig(Base):
    """Agent 配置（可由用户自定义 system_prompt 等）"""
    __tablename__ = "agent_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)  # NULL=全局默认
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # agent_name: triage | health_coach | report_interpreter | medication
    display_name: Mapped[str] = mapped_column(String(100), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    enabled_tools: Mapped[list] = mapped_column(JSON, default=list)   # 启用的工具名列表
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class UserProfile(Base):
    """用户健康画像（长期记忆的一部分）"""
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    profile_data: Mapped[dict] = mapped_column(JSON, default=dict)
    # profile_data 示例:
    # {
    #   "age": 28, "gender": "male", "bmi": 22.3,
    #   "chronic_conditions": [], "allergies": ["penicillin"],
    #   "health_goals": ["减重5kg", "每日步数>8000"],
    #   "current_medications": ["氨氯地平 5mg"],
    #   "home_address": "深圳市南山区", "city": "深圳"
    # }
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
