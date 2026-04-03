from datetime import datetime

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    date: str
    steps: float
    active_energy_kcal: float
    resting_energy_kcal: float
    distance_meters: float
    flights_climbed: float
    avg_heart_rate: float | None = None
    resting_heart_rate: float | None = None
    sleep_hours: float | None = None
    spo2_percent: float | None = None
    stand_hours: float
    last_sync_at: datetime | None = None


class TrendDataPoint(BaseModel):
    date: str
    value: float | None = None


class DashboardTrends(BaseModel):
    period: str
    steps: list[TrendDataPoint] = []
    heart_rate: list[TrendDataPoint] = []
    sleep: list[TrendDataPoint] = []
    active_energy: list[TrendDataPoint] = []
    spo2: list[TrendDataPoint] = []


class HealthScore(BaseModel):
    overall_score: float
    activity_score: float
    sleep_score: float
    heart_score: float
    vitals_score: float
    computed_at: datetime
