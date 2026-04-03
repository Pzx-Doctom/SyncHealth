from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import ActivitySample
from app.models.heart import HeartRate
from app.models.sleep import SleepSession
from app.models.vitals import BloodOxygenSample
from app.models.workout import WorkoutRecord


async def build_health_context(db: AsyncSession, user_id: int, message: str, data_scope: list[str] | None = None) -> str:
    """Build a health data context string for the LLM based on the user's question."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    context_parts = []
    msg_lower = message.lower()

    # Determine which data types are relevant
    all_types = data_scope or [
        "heart_rate", "sleep", "activity", "blood_oxygen",
        "workout", "steps", "energy", "temperature",
    ]

    include_all = not any(
        kw in msg_lower
        for kw in ["heart", "sleep", "step", "workout", "exercise", "oxygen", "spo2", "energy", "calorie", "temperature"]
    )

    # Heart rate
    if include_all or any(kw in msg_lower for kw in ["heart", "hr", "pulse", "bpm"]):
        if "heart_rate" in all_types or include_all:
            result = await db.execute(
                select(
                    func.avg(HeartRate.bpm),
                    func.min(HeartRate.bpm),
                    func.max(HeartRate.bpm),
                ).where(
                    HeartRate.user_id == user_id,
                    HeartRate.measurement_type == "heart_rate",
                    HeartRate.recorded_at >= week_ago,
                )
            )
            row = result.one_or_none()
            if row and row[0]:
                context_parts.append(
                    f"## Heart Rate (Last 7 Days)\n"
                    f"- Average: {row[0]:.0f} bpm\n"
                    f"- Min: {row[1]:.0f} bpm\n"
                    f"- Max: {row[2]:.0f} bpm"
                )

    # Sleep
    if include_all or any(kw in msg_lower for kw in ["sleep", "rest", "insomnia"]):
        if "sleep" in all_types or include_all:
            result = await db.execute(
                select(SleepSession).where(
                    SleepSession.user_id == user_id,
                    SleepSession.recorded_at >= week_ago,
                ).order_by(SleepSession.recorded_at.desc()).limit(7)
            )
            sessions = result.scalars().all()
            if sessions:
                lines = ["## Sleep (Last 7 Days)"]
                for s in sessions:
                    lines.append(
                        f"- {s.start_time.strftime('%m/%d')}: "
                        f"{s.total_duration_minutes / 60:.1f} hours"
                    )
                avg_h = sum(s.total_duration_minutes for s in sessions) / len(sessions) / 60
                lines.append(f"- Average: {avg_h:.1f} hours/night")
                context_parts.append("\n".join(lines))

    # Activity / Steps
    if include_all or any(kw in msg_lower for kw in ["step", "walk", "activity", "move", "exercise", "calorie", "energy"]):
        if "activity" in all_types or "steps" in all_types or include_all:
            result = await db.execute(
                select(func.sum(ActivitySample.value)).where(
                    ActivitySample.user_id == user_id,
                    ActivitySample.metric_type == "steps",
                    ActivitySample.recorded_at >= week_ago,
                )
            )
            total_steps = result.scalar() or 0
            context_parts.append(
                f"## Activity (Last 7 Days)\n"
                f"- Total Steps: {total_steps:,.0f}\n"
                f"- Daily Average: {total_steps / 7:,.0f}"
            )

    # Blood Oxygen
    if include_all or any(kw in msg_lower for kw in ["oxygen", "spo2", "breath"]):
        if "blood_oxygen" in all_types or include_all:
            result = await db.execute(
                select(func.avg(BloodOxygenSample.spo2_percent)).where(
                    BloodOxygenSample.user_id == user_id,
                    BloodOxygenSample.recorded_at >= week_ago,
                )
            )
            avg_spo2 = result.scalar()
            if avg_spo2:
                context_parts.append(f"## Blood Oxygen (Last 7 Days)\n- Average SpO2: {avg_spo2:.1f}%")

    # Workouts
    if include_all or any(kw in msg_lower for kw in ["workout", "exercise", "run", "training"]):
        if "workout" in all_types or include_all:
            result = await db.execute(
                select(WorkoutRecord).where(
                    WorkoutRecord.user_id == user_id,
                    WorkoutRecord.recorded_at >= week_ago,
                ).order_by(WorkoutRecord.recorded_at.desc()).limit(5)
            )
            workouts = result.scalars().all()
            if workouts:
                lines = ["## Recent Workouts"]
                for w in workouts:
                    lines.append(
                        f"- {w.start_time.strftime('%m/%d')} {w.workout_type}: "
                        f"{w.duration_seconds / 60:.0f} min, "
                        f"{w.active_energy_kcal or 0:.0f} kcal"
                    )
                context_parts.append("\n".join(lines))

    if not context_parts:
        return "No health data available for the requested period."

    return "\n\n".join(context_parts)
