from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BloodOxygenSample(Base):
    __tablename__ = "blood_oxygen_samples"
    __table_args__ = (UniqueConstraint("user_id", "sample_uuid", name="uq_blood_oxygen_sample"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    sample_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    source_device: Mapped[str] = mapped_column(String(200), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    spo2_percent: Mapped[float] = mapped_column(Float, nullable=False)  # 0-100
    measurement_condition: Mapped[str | None] = mapped_column(String(50), nullable=True)  # background, user_initiated


class BodyTemperatureSample(Base):
    __tablename__ = "body_temperature_samples"
    __table_args__ = (UniqueConstraint("user_id", "sample_uuid", name="uq_body_temp_sample"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    sample_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    source_device: Mapped[str] = mapped_column(String(200), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    temperature_celsius: Mapped[float] = mapped_column(Float, nullable=False)
    measurement_location: Mapped[str | None] = mapped_column(String(50), nullable=True)


class RespiratoryRateSample(Base):
    __tablename__ = "respiratory_rate_samples"
    __table_args__ = (UniqueConstraint("user_id", "sample_uuid", name="uq_respiratory_rate_sample"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    sample_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    source_device: Mapped[str] = mapped_column(String(200), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    breaths_per_minute: Mapped[float] = mapped_column(Float, nullable=False)


class ECGRecord(Base):
    __tablename__ = "ecg_records"
    __table_args__ = (UniqueConstraint("user_id", "sample_uuid", name="uq_ecg_record"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    sample_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    source_device: Mapped[str] = mapped_column(String(200), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    classification: Mapped[str] = mapped_column(String(50), nullable=False)  # sinus_rhythm, atrial_fibrillation, inconclusive
    average_heart_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    symptoms_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    voltage_measurements: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
