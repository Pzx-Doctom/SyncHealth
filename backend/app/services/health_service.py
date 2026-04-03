from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.activity import ActivitySample
from app.models.environment import MindfulnessSession, NoiseExposureSample
from app.models.heart import HRVSample, HeartRate
from app.models.sleep import SleepSession
from app.models.vitals import (
    BloodOxygenSample,
    BodyTemperatureSample,
    ECGRecord,
    RespiratoryRateSample,
)
from app.models.workout import WorkoutRecord


def _default_date_range() -> tuple[datetime, datetime]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=7)
    return start, end


async def query_heart_rates(
    db: AsyncSession, user_id: int, start: datetime | None, end: datetime | None,
    measurement_type: str | None = None, page: int = 1, page_size: int = 100,
) -> tuple[list, int]:
    if not start or not end:
        start, end = _default_date_range()

    query = select(HeartRate).where(
        HeartRate.user_id == user_id,
        HeartRate.recorded_at >= start,
        HeartRate.recorded_at <= end,
    )
    if measurement_type:
        query = query.where(HeartRate.measurement_type == measurement_type)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(HeartRate.recorded_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all(), total


async def query_hrv_samples(
    db: AsyncSession, user_id: int, start: datetime | None, end: datetime | None,
    page: int = 1, page_size: int = 100,
) -> tuple[list, int]:
    if not start or not end:
        start, end = _default_date_range()

    query = select(HRVSample).where(
        HRVSample.user_id == user_id, HRVSample.recorded_at >= start, HRVSample.recorded_at <= end,
    )
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    query = query.order_by(HRVSample.recorded_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all(), total


async def query_activity_samples(
    db: AsyncSession, user_id: int, start: datetime | None, end: datetime | None,
    metric_type: str | None = None, page: int = 1, page_size: int = 100,
) -> tuple[list, int]:
    if not start or not end:
        start, end = _default_date_range()

    query = select(ActivitySample).where(
        ActivitySample.user_id == user_id,
        ActivitySample.recorded_at >= start,
        ActivitySample.recorded_at <= end,
    )
    if metric_type:
        query = query.where(ActivitySample.metric_type == metric_type)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    query = query.order_by(ActivitySample.recorded_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all(), total


async def query_sleep_sessions(
    db: AsyncSession, user_id: int, start: datetime | None, end: datetime | None,
    page: int = 1, page_size: int = 100,
) -> tuple[list, int]:
    if not start or not end:
        start, end = _default_date_range()

    query = select(SleepSession).options(selectinload(SleepSession.stages)).where(
        SleepSession.user_id == user_id,
        SleepSession.recorded_at >= start,
        SleepSession.recorded_at <= end,
    )
    count_q = select(func.count()).select_from(
        select(SleepSession).where(
            SleepSession.user_id == user_id,
            SleepSession.recorded_at >= start,
            SleepSession.recorded_at <= end,
        ).subquery()
    )
    total = (await db.execute(count_q)).scalar() or 0
    query = query.order_by(SleepSession.recorded_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().unique().all(), total


async def query_blood_oxygen(
    db: AsyncSession, user_id: int, start: datetime | None, end: datetime | None,
    page: int = 1, page_size: int = 100,
) -> tuple[list, int]:
    if not start or not end:
        start, end = _default_date_range()

    query = select(BloodOxygenSample).where(
        BloodOxygenSample.user_id == user_id,
        BloodOxygenSample.recorded_at >= start,
        BloodOxygenSample.recorded_at <= end,
    )
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    query = query.order_by(BloodOxygenSample.recorded_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all(), total


async def query_body_temperature(
    db: AsyncSession, user_id: int, start: datetime | None, end: datetime | None,
    page: int = 1, page_size: int = 100,
) -> tuple[list, int]:
    if not start or not end:
        start, end = _default_date_range()

    query = select(BodyTemperatureSample).where(
        BodyTemperatureSample.user_id == user_id,
        BodyTemperatureSample.recorded_at >= start,
        BodyTemperatureSample.recorded_at <= end,
    )
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    query = query.order_by(BodyTemperatureSample.recorded_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all(), total


async def query_workouts(
    db: AsyncSession, user_id: int, start: datetime | None, end: datetime | None,
    workout_type: str | None = None, page: int = 1, page_size: int = 100,
) -> tuple[list, int]:
    if not start or not end:
        start, end = _default_date_range()

    query = select(WorkoutRecord).options(selectinload(WorkoutRecord.hr_zones)).where(
        WorkoutRecord.user_id == user_id,
        WorkoutRecord.recorded_at >= start,
        WorkoutRecord.recorded_at <= end,
    )
    if workout_type:
        query = query.where(WorkoutRecord.workout_type == workout_type)

    count_q = select(func.count()).select_from(
        select(WorkoutRecord).where(
            WorkoutRecord.user_id == user_id,
            WorkoutRecord.recorded_at >= start,
            WorkoutRecord.recorded_at <= end,
        ).subquery()
    )
    total = (await db.execute(count_q)).scalar() or 0
    query = query.order_by(WorkoutRecord.recorded_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().unique().all(), total


async def query_ecg_records(
    db: AsyncSession, user_id: int, start: datetime | None, end: datetime | None,
    page: int = 1, page_size: int = 100,
) -> tuple[list, int]:
    if not start or not end:
        start, end = _default_date_range()

    query = select(ECGRecord).where(
        ECGRecord.user_id == user_id, ECGRecord.recorded_at >= start, ECGRecord.recorded_at <= end,
    )
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    query = query.order_by(ECGRecord.recorded_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all(), total


async def query_respiratory_rate(
    db: AsyncSession, user_id: int, start: datetime | None, end: datetime | None,
    page: int = 1, page_size: int = 100,
) -> tuple[list, int]:
    if not start or not end:
        start, end = _default_date_range()

    query = select(RespiratoryRateSample).where(
        RespiratoryRateSample.user_id == user_id,
        RespiratoryRateSample.recorded_at >= start,
        RespiratoryRateSample.recorded_at <= end,
    )
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    query = query.order_by(RespiratoryRateSample.recorded_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all(), total


async def query_noise_exposure(
    db: AsyncSession, user_id: int, start: datetime | None, end: datetime | None,
    page: int = 1, page_size: int = 100,
) -> tuple[list, int]:
    if not start or not end:
        start, end = _default_date_range()

    query = select(NoiseExposureSample).where(
        NoiseExposureSample.user_id == user_id,
        NoiseExposureSample.recorded_at >= start,
        NoiseExposureSample.recorded_at <= end,
    )
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    query = query.order_by(NoiseExposureSample.recorded_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all(), total


async def query_mindfulness(
    db: AsyncSession, user_id: int, start: datetime | None, end: datetime | None,
    page: int = 1, page_size: int = 100,
) -> tuple[list, int]:
    if not start or not end:
        start, end = _default_date_range()

    query = select(MindfulnessSession).where(
        MindfulnessSession.user_id == user_id,
        MindfulnessSession.recorded_at >= start,
        MindfulnessSession.recorded_at <= end,
    )
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    query = query.order_by(MindfulnessSession.recorded_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all(), total
