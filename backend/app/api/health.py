import math
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.health import (
    ActivitySampleOut,
    BloodOxygenSampleOut,
    BodyTemperatureSampleOut,
    ECGRecordOut,
    HRVSampleOut,
    HeartRateOut,
    MindfulnessSessionOut,
    NoiseExposureSampleOut,
    PaginatedResponse,
    RespiratoryRateSampleOut,
    SleepSessionOut,
    WorkoutRecordOut,
)
from app.services.health_service import (
    query_activity_samples,
    query_blood_oxygen,
    query_body_temperature,
    query_ecg_records,
    query_heart_rates,
    query_hrv_samples,
    query_mindfulness,
    query_noise_exposure,
    query_respiratory_rate,
    query_sleep_sessions,
    query_workouts,
)

router = APIRouter(prefix="/health", tags=["health"])


def _paginate(items, total, page, page_size, schema_class):
    return PaginatedResponse(
        items=[schema_class.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if page_size > 0 else 0,
    )


@router.get("/heart-rate")
async def get_heart_rates(
    start: datetime | None = None, end: datetime | None = None,
    measurement_type: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    items, total = await query_heart_rates(db, current_user.id, start, end, measurement_type, page, page_size)
    return _paginate(items, total, page, page_size, HeartRateOut)


@router.get("/hrv")
async def get_hrv(
    start: datetime | None = None, end: datetime | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    items, total = await query_hrv_samples(db, current_user.id, start, end, page, page_size)
    return _paginate(items, total, page, page_size, HRVSampleOut)


@router.get("/activity")
async def get_activity(
    start: datetime | None = None, end: datetime | None = None,
    metric: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    items, total = await query_activity_samples(db, current_user.id, start, end, metric, page, page_size)
    return _paginate(items, total, page, page_size, ActivitySampleOut)


@router.get("/sleep")
async def get_sleep(
    start: datetime | None = None, end: datetime | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    items, total = await query_sleep_sessions(db, current_user.id, start, end, page, page_size)
    return _paginate(items, total, page, page_size, SleepSessionOut)


@router.get("/blood-oxygen")
async def get_blood_oxygen(
    start: datetime | None = None, end: datetime | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    items, total = await query_blood_oxygen(db, current_user.id, start, end, page, page_size)
    return _paginate(items, total, page, page_size, BloodOxygenSampleOut)


@router.get("/body-temperature")
async def get_body_temperature(
    start: datetime | None = None, end: datetime | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    items, total = await query_body_temperature(db, current_user.id, start, end, page, page_size)
    return _paginate(items, total, page, page_size, BodyTemperatureSampleOut)


@router.get("/workouts")
async def get_workouts(
    start: datetime | None = None, end: datetime | None = None,
    workout_type: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    items, total = await query_workouts(db, current_user.id, start, end, workout_type, page, page_size)
    return _paginate(items, total, page, page_size, WorkoutRecordOut)


@router.get("/ecg")
async def get_ecg(
    start: datetime | None = None, end: datetime | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    items, total = await query_ecg_records(db, current_user.id, start, end, page, page_size)
    return _paginate(items, total, page, page_size, ECGRecordOut)


@router.get("/respiratory-rate")
async def get_respiratory_rate(
    start: datetime | None = None, end: datetime | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    items, total = await query_respiratory_rate(db, current_user.id, start, end, page, page_size)
    return _paginate(items, total, page, page_size, RespiratoryRateSampleOut)


@router.get("/noise-exposure")
async def get_noise_exposure(
    start: datetime | None = None, end: datetime | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    items, total = await query_noise_exposure(db, current_user.id, start, end, page, page_size)
    return _paginate(items, total, page, page_size, NoiseExposureSampleOut)


@router.get("/mindfulness")
async def get_mindfulness(
    start: datetime | None = None, end: datetime | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    items, total = await query_mindfulness(db, current_user.id, start, end, page, page_size)
    return _paginate(items, total, page, page_size, MindfulnessSessionOut)
