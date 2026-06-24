from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import ActivitySample
from app.models.heart import HeartRate
from app.models.sleep import SleepSession
from app.models.vitals import BloodOxygenSample
from app.schemas.dashboard import DashboardSummary, DashboardTrends, HealthScore, TrendDataPoint


async def _get_watch_filter(db: AsyncSession, user_id: int, time_start: datetime, time_end: datetime | None = None) -> str | None:
    """检测时间范围内是否有 Apple Watch 的 activity 数据（步数/能量/距离等），有则只取 Watch"""
    query = select(func.count()).select_from(ActivitySample).where(
        ActivitySample.user_id == user_id,
        ActivitySample.source_device.ilike("%watch%"),
        ActivitySample.recorded_at >= time_start,
    )
    if time_end:
        query = query.where(ActivitySample.recorded_at < time_end)
    count = (await db.execute(query)).scalar() or 0
    return "%watch%" if count > 0 else None


async def get_dashboard_summary(db: AsyncSession, user_id: int) -> DashboardSummary:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    async def _sum_activity(metric: str, source_device: str | None = None) -> float:
        query = select(func.sum(ActivitySample.value)).where(
            ActivitySample.user_id == user_id,
            ActivitySample.metric_type == metric,
            ActivitySample.recorded_at >= today_start,
        )
        if source_device:
            query = query.where(ActivitySample.source_device.ilike(source_device))
        result = await db.execute(query)
        return result.scalar() or 0.0

    watch_source = await _get_watch_filter(db, user_id, today_start)
    steps = await _sum_activity("steps", watch_source)
    active_energy = await _sum_activity("active_energy_kcal", watch_source)
    resting_energy = await _sum_activity("resting_energy_kcal")
    distance = await _sum_activity("distance_meters", watch_source)
    flights = await _sum_activity("flights_climbed")
    stand = await _sum_activity("stand_hours")

    # Average heart rate today
    hr_result = await db.execute(
        select(func.avg(HeartRate.bpm)).where(
            HeartRate.user_id == user_id,
            HeartRate.measurement_type == "heart_rate",
            HeartRate.recorded_at >= today_start,
        )
    )
    avg_hr = hr_result.scalar()

    # Resting heart rate (latest today)
    rhr_result = await db.execute(
        select(HeartRate.bpm).where(
            HeartRate.user_id == user_id,
            HeartRate.measurement_type == "resting_heart_rate",
            HeartRate.recorded_at >= today_start,
        ).order_by(HeartRate.recorded_at.desc()).limit(1)
    )
    resting_hr = rhr_result.scalar()

    # Walking heart rate average (latest today)
    whr_result = await db.execute(
        select(HeartRate.bpm).where(
            HeartRate.user_id == user_id,
            HeartRate.measurement_type == "walking_heart_rate_average",
            HeartRate.recorded_at >= today_start,
        ).order_by(HeartRate.recorded_at.desc()).limit(1)
    )
    walking_hr = whr_result.scalar()

    # Sleep last night
    yesterday_start = today_start - timedelta(days=1)
    sleep_result = await db.execute(
        select(func.sum(SleepSession.total_duration_minutes)).where(
            SleepSession.user_id == user_id,
            SleepSession.start_time >= yesterday_start,
            SleepSession.start_time < today_start,
        )
    )
    sleep_minutes = sleep_result.scalar()
    sleep_hours = round(sleep_minutes / 60, 1) if sleep_minutes else None

    # Latest SpO2
    spo2_result = await db.execute(
        select(BloodOxygenSample.spo2_percent).where(
            BloodOxygenSample.user_id == user_id,
        ).order_by(BloodOxygenSample.recorded_at.desc()).limit(1)
    )
    spo2 = spo2_result.scalar()

    from app.models.user import User
    user = await db.get(User, user_id)

    return DashboardSummary(
        date=today_start.strftime("%Y-%m-%d"),
        steps=steps,
        active_energy_kcal=active_energy,
        resting_energy_kcal=resting_energy,
        distance_meters=distance,
        flights_climbed=flights,
        avg_heart_rate=round(avg_hr, 1) if avg_hr else None,
        resting_heart_rate=round(resting_hr, 1) if resting_hr else None,
        walking_heart_rate_average=round(walking_hr, 1) if walking_hr else None,
        sleep_hours=sleep_hours,
        spo2_percent=round(spo2, 1) if spo2 else None,
        stand_hours=stand,
        last_sync_at=user.last_sync_at if user else None,
    )


async def get_dashboard_trends(db: AsyncSession, user_id: int, period: str = "7d") -> DashboardTrends:
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 7)
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    trends = DashboardTrends(period=period)

    for day_offset in range(days):
        day_start = (start + timedelta(days=day_offset)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        date_str = day_start.strftime("%Y-%m-%d")

        # Steps & energy（Watch 优先，避免多源重复）
        watch_source = await _get_watch_filter(db, user_id, day_start, day_end)
        step_q = select(func.sum(ActivitySample.value)).where(
            ActivitySample.user_id == user_id,
            ActivitySample.metric_type == "steps",
            ActivitySample.recorded_at >= day_start,
            ActivitySample.recorded_at < day_end,
        )
        if watch_source:
            step_q = step_q.where(ActivitySample.source_device.ilike(watch_source))
        step_r = await db.execute(step_q)
        trends.steps.append(TrendDataPoint(date=date_str, value=step_r.scalar()))

        # Avg heart rate
        hr_r = await db.execute(
            select(func.avg(HeartRate.bpm)).where(
                HeartRate.user_id == user_id,
                HeartRate.measurement_type == "heart_rate",
                HeartRate.recorded_at >= day_start,
                HeartRate.recorded_at < day_end,
            )
        )
        hr_val = hr_r.scalar()
        trends.heart_rate.append(TrendDataPoint(date=date_str, value=round(hr_val, 1) if hr_val else None))

        # Sleep
        sleep_r = await db.execute(
            select(func.sum(SleepSession.total_duration_minutes)).where(
                SleepSession.user_id == user_id,
                SleepSession.start_time >= day_start,
                SleepSession.start_time < day_end,
            )
        )
        sleep_val = sleep_r.scalar()
        trends.sleep.append(TrendDataPoint(date=date_str, value=round(sleep_val / 60, 1) if sleep_val else None))

        # Active energy
        energy_q = select(func.sum(ActivitySample.value)).where(
            ActivitySample.user_id == user_id,
            ActivitySample.metric_type == "active_energy_kcal",
            ActivitySample.recorded_at >= day_start,
            ActivitySample.recorded_at < day_end,
        )
        if watch_source:
            energy_q = energy_q.where(ActivitySample.source_device.ilike(watch_source))
        energy_r = await db.execute(energy_q)
        trends.active_energy.append(TrendDataPoint(date=date_str, value=energy_r.scalar()))

        # SpO2
        spo2_r = await db.execute(
            select(func.avg(BloodOxygenSample.spo2_percent)).where(
                BloodOxygenSample.user_id == user_id,
                BloodOxygenSample.recorded_at >= day_start,
                BloodOxygenSample.recorded_at < day_end,
            )
        )
        spo2_val = spo2_r.scalar()
        trends.spo2.append(TrendDataPoint(date=date_str, value=round(spo2_val, 1) if spo2_val else None))

    return trends


async def get_health_score(db: AsyncSession, user_id: int) -> HealthScore:
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # Activity score (based on steps: 10000 = 100)
    watch_source = await _get_watch_filter(db, user_id, week_ago)
    daily_steps_q = (
        select(func.sum(ActivitySample.value).label("daily_steps"))
        .where(
            ActivitySample.user_id == user_id,
            ActivitySample.metric_type == "steps",
            ActivitySample.recorded_at >= week_ago,
        )
    )
    if watch_source:
        daily_steps_q = daily_steps_q.where(ActivitySample.source_device.ilike(watch_source))
    daily_steps_q = daily_steps_q.group_by(func.date(ActivitySample.recorded_at))
    daily_steps_r = await db.execute(daily_steps_q)
    daily_steps_rows = daily_steps_r.all()
    if daily_steps_rows:
        avg_steps = sum(r[0] or 0 for r in daily_steps_rows) / len(daily_steps_rows)
    else:
        avg_steps = 0
    activity_score = min(100, (avg_steps / 10000) * 100)

    # Sleep score (7-9 hours = 100)
    sleep_r = await db.execute(
        select(func.avg(SleepSession.total_duration_minutes)).where(
            SleepSession.user_id == user_id,
            SleepSession.recorded_at >= week_ago,
        )
    )
    avg_sleep = sleep_r.scalar() or 0
    sleep_hours = avg_sleep / 60
    if 7 <= sleep_hours <= 9:
        sleep_score = 100.0
    elif sleep_hours < 7:
        sleep_score = max(0, (sleep_hours / 7) * 100)
    else:
        sleep_score = max(0, 100 - (sleep_hours - 9) * 20)

    # Heart score (resting HR 50-70 = 100)
    hr_r = await db.execute(
        select(func.avg(HeartRate.bpm)).where(
            HeartRate.user_id == user_id,
            HeartRate.measurement_type == "resting_heart_rate",
            HeartRate.recorded_at >= week_ago,
        )
    )
    avg_rhr = hr_r.scalar() or 70
    if 50 <= avg_rhr <= 70:
        heart_score = 100.0
    elif avg_rhr < 50:
        heart_score = max(0, 100 - (50 - avg_rhr) * 5)
    else:
        heart_score = max(0, 100 - (avg_rhr - 70) * 3)

    # Vitals score (SpO2 > 95% = good)
    spo2_r = await db.execute(
        select(func.avg(BloodOxygenSample.spo2_percent)).where(
            BloodOxygenSample.user_id == user_id,
            BloodOxygenSample.recorded_at >= week_ago,
        )
    )
    avg_spo2 = spo2_r.scalar() or 97
    vitals_score = min(100, (avg_spo2 / 100) * 105) if avg_spo2 >= 90 else max(0, (avg_spo2 / 90) * 50)

    overall = (activity_score * 0.3 + sleep_score * 0.3 + heart_score * 0.25 + vitals_score * 0.15)

    return HealthScore(
        overall_score=round(overall, 1),
        activity_score=round(activity_score, 1),
        sleep_score=round(sleep_score, 1),
        heart_score=round(heart_score, 1),
        vitals_score=round(vitals_score, 1),
        computed_at=now,
    )
