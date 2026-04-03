from datetime import datetime

from pydantic import BaseModel

from app.schemas.health import (
    ActivitySampleIn,
    BloodOxygenSampleIn,
    BodyTemperatureSampleIn,
    ECGRecordIn,
    HRVSampleIn,
    HeartRateIn,
    MindfulnessSessionIn,
    NoiseExposureSampleIn,
    RespiratoryRateSampleIn,
    SleepSessionIn,
    WorkoutRecordIn,
)


class DeviceInfo(BaseModel):
    model: str = ""
    os_version: str = ""
    app_version: str = ""


class SyncWindow(BaseModel):
    start: datetime
    end: datetime


class SyncPayload(BaseModel):
    device_info: DeviceInfo = DeviceInfo()
    sync_window: SyncWindow
    heart_rates: list[HeartRateIn] = []
    hrv_samples: list[HRVSampleIn] = []
    activity_samples: list[ActivitySampleIn] = []
    sleep_sessions: list[SleepSessionIn] = []
    blood_oxygen_samples: list[BloodOxygenSampleIn] = []
    body_temperature_samples: list[BodyTemperatureSampleIn] = []
    workout_records: list[WorkoutRecordIn] = []
    ecg_records: list[ECGRecordIn] = []
    respiratory_rate_samples: list[RespiratoryRateSampleIn] = []
    noise_exposure_samples: list[NoiseExposureSampleIn] = []
    mindfulness_sessions: list[MindfulnessSessionIn] = []


class SyncResponse(BaseModel):
    sync_id: int
    records_received: int
    records_inserted: int
    records_deduplicated: int
    status: str


class SyncStatusResponse(BaseModel):
    last_sync_at: datetime | None = None
    last_sync_status: str | None = None
    records_inserted: int = 0


class SyncLogResponse(BaseModel):
    id: int
    started_at: datetime
    completed_at: datetime | None = None
    status: str
    records_received: int
    records_inserted: int
    records_deduplicated: int
    error_message: str | None = None

    model_config = {"from_attributes": True}
