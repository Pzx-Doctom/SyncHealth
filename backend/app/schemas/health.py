from datetime import datetime

from pydantic import BaseModel


# --- Base sample schema ---
class HealthSampleBase(BaseModel):
    sample_uuid: str
    source_device: str | None = None
    recorded_at: datetime


# --- Heart ---
class HeartRateIn(HealthSampleBase):
    bpm: float
    motion_context: str | None = None
    measurement_type: str = "heart_rate"


class HeartRateOut(HeartRateIn):
    id: int
    synced_at: datetime
    model_config = {"from_attributes": True}


class HRVSampleIn(HealthSampleBase):
    sdnn_ms: float


class HRVSampleOut(HRVSampleIn):
    id: int
    synced_at: datetime
    model_config = {"from_attributes": True}


# --- Activity ---
class ActivitySampleIn(HealthSampleBase):
    metric_type: str
    value: float
    duration_seconds: float | None = None


class ActivitySampleOut(ActivitySampleIn):
    id: int
    synced_at: datetime
    model_config = {"from_attributes": True}


# --- Sleep ---
class SleepStageIn(BaseModel):
    stage: str  # awake, rem, core, deep
    start_time: datetime
    end_time: datetime
    duration_minutes: float


class SleepStageOut(SleepStageIn):
    id: int
    model_config = {"from_attributes": True}


class SleepSessionIn(HealthSampleBase):
    start_time: datetime
    end_time: datetime
    total_duration_minutes: float
    in_bed_duration_minutes: float | None = None
    stages: list[SleepStageIn] = []


class SleepSessionOut(BaseModel):
    id: int
    sample_uuid: str
    source_device: str | None = None
    recorded_at: datetime
    synced_at: datetime
    start_time: datetime
    end_time: datetime
    total_duration_minutes: float
    in_bed_duration_minutes: float | None = None
    stages: list[SleepStageOut] = []
    model_config = {"from_attributes": True}


# --- Blood Oxygen ---
class BloodOxygenSampleIn(HealthSampleBase):
    spo2_percent: float
    measurement_condition: str | None = None


class BloodOxygenSampleOut(BloodOxygenSampleIn):
    id: int
    synced_at: datetime
    model_config = {"from_attributes": True}


# --- Body Temperature ---
class BodyTemperatureSampleIn(HealthSampleBase):
    temperature_celsius: float
    measurement_location: str | None = None


class BodyTemperatureSampleOut(BodyTemperatureSampleIn):
    id: int
    synced_at: datetime
    model_config = {"from_attributes": True}


# --- Workout ---
class WorkoutHRZoneIn(BaseModel):
    zone_index: int
    lower_bound_bpm: float
    upper_bound_bpm: float
    duration_seconds: float


class WorkoutHRZoneOut(WorkoutHRZoneIn):
    id: int
    model_config = {"from_attributes": True}


class WorkoutRecordIn(HealthSampleBase):
    workout_type: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    total_energy_kcal: float | None = None
    active_energy_kcal: float | None = None
    distance_meters: float | None = None
    avg_heart_rate: float | None = None
    max_heart_rate: float | None = None
    min_heart_rate: float | None = None
    hr_zones: list[WorkoutHRZoneIn] = []


class WorkoutRecordOut(BaseModel):
    id: int
    sample_uuid: str
    source_device: str | None = None
    recorded_at: datetime
    synced_at: datetime
    workout_type: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    total_energy_kcal: float | None = None
    active_energy_kcal: float | None = None
    distance_meters: float | None = None
    avg_heart_rate: float | None = None
    max_heart_rate: float | None = None
    min_heart_rate: float | None = None
    hr_zones: list[WorkoutHRZoneOut] = []
    model_config = {"from_attributes": True}


# --- ECG ---
class ECGRecordIn(HealthSampleBase):
    classification: str
    average_heart_rate: float | None = None
    symptoms_status: str | None = None
    voltage_measurements: str | None = None  # JSON string


class ECGRecordOut(ECGRecordIn):
    id: int
    synced_at: datetime
    model_config = {"from_attributes": True}


# --- Respiratory Rate ---
class RespiratoryRateSampleIn(HealthSampleBase):
    breaths_per_minute: float


class RespiratoryRateSampleOut(RespiratoryRateSampleIn):
    id: int
    synced_at: datetime
    model_config = {"from_attributes": True}


# --- Noise Exposure ---
class NoiseExposureSampleIn(HealthSampleBase):
    decibels: float
    duration_seconds: float | None = None


class NoiseExposureSampleOut(NoiseExposureSampleIn):
    id: int
    synced_at: datetime
    model_config = {"from_attributes": True}


# --- Mindfulness ---
class MindfulnessSessionIn(HealthSampleBase):
    start_time: datetime
    end_time: datetime
    duration_minutes: float


class MindfulnessSessionOut(MindfulnessSessionIn):
    id: int
    synced_at: datetime
    model_config = {"from_attributes": True}


# --- Paginated Response ---
class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int
