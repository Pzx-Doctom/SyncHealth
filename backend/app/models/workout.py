from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WorkoutRecord(Base):
    __tablename__ = "workout_records"
    __table_args__ = (UniqueConstraint("user_id", "sample_uuid", name="uq_workout_record"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    sample_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    source_device: Mapped[str] = mapped_column(String(200), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    workout_type: Mapped[str] = mapped_column(String(100), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    total_energy_kcal: Mapped[float | None] = mapped_column(Float, nullable=True)
    active_energy_kcal: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_heart_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_heart_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_heart_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    hr_zones: Mapped[list["WorkoutHRZone"]] = relationship("WorkoutHRZone", back_populates="workout", cascade="all, delete-orphan")


class WorkoutHRZone(Base):
    __tablename__ = "workout_hr_zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workout_id: Mapped[int] = mapped_column(Integer, ForeignKey("workout_records.id"), nullable=False)
    zone_index: Mapped[int] = mapped_column(Integer, nullable=False)
    lower_bound_bpm: Mapped[float] = mapped_column(Float, nullable=False)
    upper_bound_bpm: Mapped[float] = mapped_column(Float, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)

    workout: Mapped["WorkoutRecord"] = relationship("WorkoutRecord", back_populates="hr_zones")
