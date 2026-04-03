import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import ActivitySample
from app.models.environment import MindfulnessSession, NoiseExposureSample
from app.models.heart import HRVSample, HeartRate
from app.models.sleep import SleepSession, SleepStage
from app.models.sync_log import SyncLog
from app.models.user import User
from app.models.vitals import (
    BloodOxygenSample,
    BodyTemperatureSample,
    ECGRecord,
    RespiratoryRateSample,
)
from app.models.workout import WorkoutHRZone, WorkoutRecord
from app.schemas.sync import SyncPayload, SyncResponse


async def _bulk_insert_simple(db: AsyncSession, model_class, items: list, user_id: int) -> tuple[int, int]:
    """Insert samples, skipping duplicates by (user_id, sample_uuid)."""
    if not items:
        return 0, 0

    inserted = 0
    deduplicated = 0
    for item in items:
        data = item.model_dump()
        data["user_id"] = user_id
        data["synced_at"] = datetime.now(timezone.utc)

        existing = await db.execute(
            select(model_class).where(
                model_class.user_id == user_id,
                model_class.sample_uuid == data["sample_uuid"],
            )
        )
        if existing.scalar_one_or_none():
            deduplicated += 1
            continue

        db.add(model_class(**data))
        inserted += 1

    return inserted, deduplicated


async def _insert_sleep_sessions(db: AsyncSession, sessions: list, user_id: int) -> tuple[int, int]:
    if not sessions:
        return 0, 0

    inserted = 0
    deduplicated = 0
    for session_in in sessions:
        existing = await db.execute(
            select(SleepSession).where(
                SleepSession.user_id == user_id,
                SleepSession.sample_uuid == session_in.sample_uuid,
            )
        )
        if existing.scalar_one_or_none():
            deduplicated += 1
            continue

        data = session_in.model_dump(exclude={"stages"})
        data["user_id"] = user_id
        data["synced_at"] = datetime.now(timezone.utc)
        session = SleepSession(**data)
        db.add(session)
        await db.flush()

        for stage_in in session_in.stages:
            stage = SleepStage(session_id=session.id, **stage_in.model_dump())
            db.add(stage)

        inserted += 1

    return inserted, deduplicated


async def _insert_workout_records(db: AsyncSession, records: list, user_id: int) -> tuple[int, int]:
    if not records:
        return 0, 0

    inserted = 0
    deduplicated = 0
    for record_in in records:
        existing = await db.execute(
            select(WorkoutRecord).where(
                WorkoutRecord.user_id == user_id,
                WorkoutRecord.sample_uuid == record_in.sample_uuid,
            )
        )
        if existing.scalar_one_or_none():
            deduplicated += 1
            continue

        data = record_in.model_dump(exclude={"hr_zones"})
        data["user_id"] = user_id
        data["synced_at"] = datetime.now(timezone.utc)
        workout = WorkoutRecord(**data)
        db.add(workout)
        await db.flush()

        for zone_in in record_in.hr_zones:
            zone = WorkoutHRZone(workout_id=workout.id, **zone_in.model_dump())
            db.add(zone)

        inserted += 1

    return inserted, deduplicated


async def process_sync_upload(db: AsyncSession, payload: SyncPayload, user_id: int) -> SyncResponse:
    sync_log = SyncLog(user_id=user_id)
    db.add(sync_log)
    await db.flush()

    total_received = 0
    total_inserted = 0
    total_deduplicated = 0

    # Count total received
    for field_name in [
        "heart_rates", "hrv_samples", "activity_samples", "sleep_sessions",
        "blood_oxygen_samples", "body_temperature_samples", "workout_records",
        "ecg_records", "respiratory_rate_samples", "noise_exposure_samples",
        "mindfulness_sessions",
    ]:
        total_received += len(getattr(payload, field_name))

    try:
        # Simple tables
        simple_mappings = [
            (HeartRate, payload.heart_rates),
            (HRVSample, payload.hrv_samples),
            (ActivitySample, payload.activity_samples),
            (BloodOxygenSample, payload.blood_oxygen_samples),
            (BodyTemperatureSample, payload.body_temperature_samples),
            (ECGRecord, payload.ecg_records),
            (RespiratoryRateSample, payload.respiratory_rate_samples),
            (NoiseExposureSample, payload.noise_exposure_samples),
            (MindfulnessSession, payload.mindfulness_sessions),
        ]

        for model_class, items in simple_mappings:
            ins, dup = await _bulk_insert_simple(db, model_class, items, user_id)
            total_inserted += ins
            total_deduplicated += dup

        # Nested tables
        ins, dup = await _insert_sleep_sessions(db, payload.sleep_sessions, user_id)
        total_inserted += ins
        total_deduplicated += dup

        ins, dup = await _insert_workout_records(db, payload.workout_records, user_id)
        total_inserted += ins
        total_deduplicated += dup

        # Update sync log
        sync_log.status = "completed"
        sync_log.completed_at = datetime.now(timezone.utc)
        sync_log.records_received = total_received
        sync_log.records_inserted = total_inserted
        sync_log.records_deduplicated = total_deduplicated
        sync_log.client_metadata = json.dumps(payload.device_info.model_dump())

        # Update user last sync
        user = await db.get(User, user_id)
        if user:
            user.last_sync_at = datetime.now(timezone.utc)

    except Exception as e:
        sync_log.status = "failed"
        sync_log.error_message = str(e)
        sync_log.completed_at = datetime.now(timezone.utc)
        raise

    return SyncResponse(
        sync_id=sync_log.id,
        records_received=total_received,
        records_inserted=total_inserted,
        records_deduplicated=total_deduplicated,
        status="completed",
    )
