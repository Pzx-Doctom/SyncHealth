from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NoiseExposureSample(Base):
    __tablename__ = "noise_exposure_samples"
    __table_args__ = (UniqueConstraint("user_id", "sample_uuid", name="uq_noise_exposure_sample"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    sample_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    source_device: Mapped[str] = mapped_column(String(200), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    decibels: Mapped[float] = mapped_column(Float, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)


class MindfulnessSession(Base):
    __tablename__ = "mindfulness_sessions"
    __table_args__ = (UniqueConstraint("user_id", "sample_uuid", name="uq_mindfulness_session"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    sample_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    source_device: Mapped[str] = mapped_column(String(200), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_minutes: Mapped[float] = mapped_column(Float, nullable=False)
