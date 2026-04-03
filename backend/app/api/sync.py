from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.sync_log import SyncLog
from app.models.user import User
from app.schemas.sync import SyncLogResponse, SyncPayload, SyncResponse, SyncStatusResponse
from app.services.sync_service import process_sync_upload

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/upload", response_model=SyncResponse)
async def upload_sync_data(
    payload: SyncPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await process_sync_upload(db, payload, current_user.id)


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SyncLog)
        .where(SyncLog.user_id == current_user.id)
        .order_by(SyncLog.started_at.desc())
        .limit(1)
    )
    last_log = result.scalar_one_or_none()

    return SyncStatusResponse(
        last_sync_at=current_user.last_sync_at,
        last_sync_status=last_log.status if last_log else None,
        records_inserted=last_log.records_inserted if last_log else 0,
    )


@router.get("/history", response_model=list[SyncLogResponse])
async def get_sync_history(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SyncLog)
        .where(SyncLog.user_id == current_user.id)
        .order_by(SyncLog.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return result.scalars().all()
