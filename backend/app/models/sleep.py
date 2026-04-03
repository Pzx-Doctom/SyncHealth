from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SleepSession(Base):
    __tablename__ = "sleep_sessions"
    __table_args__ = (UniqueConstraint("user_id", "sample_uuid", name="uq_sleep_session"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    sample_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    source_device: Mapped[str] = mapped_column(String(200), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_duration_minutes: Mapped[float] = mapped_column(Float, nullable=False)
    in_bed_duration_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)

    stages: Mapped[list["SleepStage"]] = relationship("SleepStage", back_populates="session", cascade="all, delete-orphan")


class SleepStage(Base):
    __tablename__ = "sleep_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("sleep_sessions.id"), nullable=False)
    stage: Mapped[str] = mapped_column(String(20), nullable=False)  # awake, rem, core, deep
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_minutes: Mapped[float] = mapped_column(Float, nullable=False)

    session: Mapped["SleepSession"] = relationship("SleepSession", back_populates="stages")
