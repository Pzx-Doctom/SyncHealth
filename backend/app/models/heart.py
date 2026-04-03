from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class HeartRate(Base):
    __tablename__ = "heart_rates"
    __table_args__ = (UniqueConstraint("user_id", "sample_uuid", name="uq_heart_rate_sample"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    sample_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    source_device: Mapped[str] = mapped_column(String(200), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    bpm: Mapped[float] = mapped_column(Float, nullable=False)
    motion_context: Mapped[str] = mapped_column(String(50), nullable=True)  # sedentary, active, unset
    measurement_type: Mapped[str] = mapped_column(String(50), nullable=False)  # heart_rate, resting_heart_rate, walking_heart_rate_average


class HRVSample(Base):
    __tablename__ = "hrv_samples"
    __table_args__ = (UniqueConstraint("user_id", "sample_uuid", name="uq_hrv_sample"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    sample_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    source_device: Mapped[str] = mapped_column(String(200), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    sdnn_ms: Mapped[float] = mapped_column(Float, nullable=False)
