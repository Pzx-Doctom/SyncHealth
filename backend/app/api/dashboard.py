from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardSummary, DashboardTrends, HealthScore
from app.services.dashboard_service import get_dashboard_summary, get_dashboard_trends, get_health_score

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_dashboard_summary(db, current_user.id)


@router.get("/trends", response_model=DashboardTrends)
async def trends(
    period: str = Query("7d", pattern="^(7d|30d|90d)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_dashboard_trends(db, current_user.id, period)


@router.get("/health-score", response_model=HealthScore)
async def health_score(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_health_score(db, current_user.id)
