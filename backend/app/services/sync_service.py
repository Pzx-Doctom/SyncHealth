import json
from datetime import datetime, timezone

from sqlalchemy import func, select
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


BATCH_SIZE = 100  # SQLite 变量上限 999，每行 8 列约 800 变量，100 条安全


async def _bulk_insert(db: AsyncSession, model_class, items: list, user_id: int) -> tuple[int, int, int]:
    """分批插入，利用唯一约束去重。每批 BATCH_SIZE 条避免超过 SQLite 变量上限"""
    if not items:
        return 0, 0, 0

    all_uuids = [item.sample_uuid for item in items]

    # 统计所有已存在的 UUID（一次查询）
    existing = (await db.scalar(
        select(func.count()).select_from(model_class).where(
            model_class.user_id == user_id,
            model_class.sample_uuid.in_(all_uuids),
        )
    )) or 0

    # 分批组装 + 插入
    now = datetime.now(timezone.utc)
    for i in range(0, len(items), BATCH_SIZE):
        chunk = items[i:i + BATCH_SIZE]
        batch = []
        for item in chunk:
            data = item.model_dump()
            data["user_id"] = user_id
            data["synced_at"] = now
            batch.append(data)
        stmt = sqlite_insert(model_class).values(batch).on_conflict_do_nothing(
            index_elements=["user_id", "sample_uuid"]
        )
        await db.execute(stmt)

    received = len(items)
    deduplicated = existing
    inserted = received - deduplicated
    return received, inserted, deduplicated


async def _bulk_insert_sleep(db: AsyncSession, sessions: list, user_id: int) -> tuple[int, int, int]:
    """分批插入睡眠会话 + 阶段子表"""
    if not sessions:
        return 0, 0, 0

    uuids = [s.sample_uuid for s in sessions]
    existing = (await db.scalar(
        select(func.count()).select_from(SleepSession).where(
            SleepSession.user_id == user_id,
            SleepSession.sample_uuid.in_(uuids),
        )
    )) or 0

    now = datetime.now(timezone.utc)
    for i in range(0, len(sessions), BATCH_SIZE):
        chunk = sessions[i:i + BATCH_SIZE]
        batch = []
        for session_in in chunk:
            data = session_in.model_dump(exclude={"stages"})
            data["user_id"] = user_id
            data["synced_at"] = now
            batch.append(data)
        stmt = sqlite_insert(SleepSession).values(batch).on_conflict_do_nothing(
            index_elements=["user_id", "sample_uuid"]
        )
        await db.execute(stmt)
    await db.flush()

    # 只给新插入的会话添加阶段
    inserted = 0
    if sessions:
        # 查回刚插入的 session id（之前不存在的）
        id_rows = await db.execute(
            select(SleepSession.id, SleepSession.sample_uuid).where(
                SleepSession.user_id == user_id,
                SleepSession.sample_uuid.in_(uuids),
            )
        )
        session_id_map = {row.sample_uuid: row.id for row in id_rows}

        stage_batch = []
        for session_in in sessions:
            sid = session_id_map.get(session_in.sample_uuid)
            if sid is None:
                continue
            for stage_in in session_in.stages:
                stage_batch.append({"session_id": sid, **stage_in.model_dump()})
            inserted += 1

        if stage_batch:
            await db.execute(sqlite_insert(SleepStage).values(stage_batch))

    received = len(sessions)
    deduplicated = existing
    return received, inserted, deduplicated


async def _bulk_insert_workouts(db: AsyncSession, records: list, user_id: int) -> tuple[int, int, int]:
    """分批插入运动记录 + 心率区间子表"""
    if not records:
        return 0, 0, 0

    uuids = [r.sample_uuid for r in records]
    existing = (await db.scalar(
        select(func.count()).select_from(WorkoutRecord).where(
            WorkoutRecord.user_id == user_id,
            WorkoutRecord.sample_uuid.in_(uuids),
        )
    )) or 0

    now = datetime.now(timezone.utc)
    for i in range(0, len(records), BATCH_SIZE):
        chunk = records[i:i + BATCH_SIZE]
        batch = []
        for record_in in chunk:
            data = record_in.model_dump(exclude={"hr_zones"})
            data["user_id"] = user_id
            data["synced_at"] = now
            batch.append(data)
        stmt = sqlite_insert(WorkoutRecord).values(batch).on_conflict_do_nothing(
            index_elements=["user_id", "sample_uuid"]
        )
        await db.execute(stmt)
    await db.flush()

    inserted = 0
    if records:
        id_rows = await db.execute(
            select(WorkoutRecord.id, WorkoutRecord.sample_uuid).where(
                WorkoutRecord.user_id == user_id,
                WorkoutRecord.sample_uuid.in_(uuids),
            )
        )
        record_id_map = {row.sample_uuid: row.id for row in id_rows}

        zone_batch = []
        for record_in in records:
            rid = record_id_map.get(record_in.sample_uuid)
            if rid is None:
                continue
            for zone_in in record_in.hr_zones:
                zone_batch.append({"workout_id": rid, **zone_in.model_dump()})
            inserted += 1

        if zone_batch:
            await db.execute(sqlite_insert(WorkoutHRZone).values(zone_batch))

    received = len(records)
    deduplicated = existing
    return received, inserted, deduplicated


async def process_sync_upload(db: AsyncSession, payload: SyncPayload, user_id: int) -> SyncResponse:
    sync_log = SyncLog(user_id=user_id)
    db.add(sync_log)
    await db.flush()

    total_received = 0
    total_inserted = 0
    total_deduplicated = 0

    try:
        # 简单表：一次批量 INSERT 完成
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
            recv, ins, dup = await _bulk_insert(db, model_class, items, user_id)
            total_received += recv
            total_inserted += ins
            total_deduplicated += dup

        # 嵌套表
        recv, ins, dup = await _bulk_insert_sleep(db, payload.sleep_sessions, user_id)
        total_received += recv
        total_inserted += ins
        total_deduplicated += dup

        recv, ins, dup = await _bulk_insert_workouts(db, payload.workout_records, user_id)
        total_received += recv
        total_inserted += ins
        total_deduplicated += dup

        sync_log.status = "completed"
        sync_log.completed_at = datetime.now(timezone.utc)
        sync_log.records_received = total_received
        sync_log.records_inserted = total_inserted
        sync_log.records_deduplicated = total_deduplicated
        sync_log.client_metadata = json.dumps(payload.device_info.model_dump())

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
