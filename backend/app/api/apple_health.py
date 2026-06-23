"""
Apple Health 数据导入 API

支持用户上传 iPhone 健康导出的 .zip / .xml 文件，后台流式解析并入库。
复用现有 process_sync_upload 去重与 SyncLog 机制。

端点：
    POST /apple-health/upload        上传文件，返回 task_id，后台异步处理
    GET  /apple-health/status/{id}   查询导入任务状态
    GET  /apple-health/history       查看导入历史（SyncLog）
"""
import logging
import os
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy import select

from app.config import settings
from app.core.dependencies import get_current_user
from app.database import async_session_factory, get_db
from app.models.sync_log import SyncLog
from app.models.user import User
from app.schemas.sync import SyncLogResponse
from app.services.apple_health.adapter import parse_xml_to_payloads
from app.services.sync_service import process_sync_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/apple-health", tags=["apple-health"])

# 模块级任务状态存储（内存，进程重启后丢失；与外部仓库一致）
_import_tasks: dict[str, dict] = {}

ALLOWED_EXTENSIONS = (".xml", ".zip")


@router.post("/upload")
async def upload_apple_health(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    上传 Apple Health 导出文件（.zip 或 .xml），后台异步解析入库。
    返回 task_id 供状态查询。
    """
    filename = (file.filename or "").lower()
    if not filename.endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail="仅支持 .xml 或 .zip 格式的 Apple Health 导出文件",
        )

    # 确保上传目录存在
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)

    # 保存上传文件
    task_id = uuid.uuid4().hex
    save_name = f"{task_id}_{file.filename}"
    save_path = os.path.join(upload_dir, save_name)
    try:
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    finally:
        await file.close()

    # 初始化任务状态
    _import_tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "total_records": 0,
        "inserted": 0,
        "deduplicated": 0,
        "batches": 0,
        "error": None,
        "started_at": datetime.now(timezone.utc),
        "completed_at": None,
    }

    # 后台执行
    background_tasks.add_task(_run_import_task, task_id, save_path, current_user.id)

    return {"task_id": task_id, "status": "pending", "message": "文件已接收，正在后台解析"}


@router.get("/status/{task_id}")
async def get_import_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """查询导入任务状态"""
    task = _import_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    return task


@router.get("/history", response_model=list[SyncLogResponse])
async def get_import_history(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """查看该用户的导入历史（SyncLog）"""
    result = await db.execute(
        select(SyncLog)
        .where(SyncLog.user_id == current_user.id)
        .order_by(SyncLog.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return result.scalars().all()


# ------------------------------------------------------------------
# 后台任务
# ------------------------------------------------------------------

async def _run_import_task(task_id: str, file_path: str, user_id: int) -> None:
    """后台执行：解压（若需要）→ 解析 XML → 分批 SyncPayload → process_sync_upload"""
    task = _import_tasks[task_id]
    task["status"] = "processing"

    xml_path, temp_dir = _extract_if_zip(file_path)
    if not xml_path:
        _fail_task(task, "无法从上传文件中提取 XML")
        _cleanup(file_path, temp_dir)
        return

    try:
        total_inserted = 0
        total_deduplicated = 0
        total_received = 0
        batches = 0

        # 后台任务使用独立的 AsyncSession（不复用请求的 session）
        async with async_session_factory() as db:
            for payload in parse_xml_to_payloads(xml_path):
                response = await process_sync_upload(db, payload, user_id)
                await db.commit()

                total_received += response.records_received
                total_inserted += response.records_inserted
                total_deduplicated += response.records_deduplicated
                batches += 1

                task["total_records"] = total_received
                task["inserted"] = total_inserted
                task["deduplicated"] = total_deduplicated
                task["batches"] = batches

        task["status"] = "completed"
        task["completed_at"] = datetime.now(timezone.utc)
        logger.info(
            "Apple Health 导入完成 task=%s: received=%d inserted=%d dedup=%d batches=%d",
            task_id, total_received, total_inserted, total_deduplicated, batches,
        )
    except Exception as e:
        logger.exception("Apple Health 导入失败 task=%s", task_id)
        _fail_task(task, str(e))
    finally:
        _cleanup(file_path, temp_dir)


def _fail_task(task: dict, error: str) -> None:
    task["status"] = "failed"
    task["error"] = error
    task["completed_at"] = datetime.now(timezone.utc)


def _cleanup(file_path: str, temp_dir: str | None) -> None:
    """清理上传文件与临时解压目录"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except OSError:
        pass
    if temp_dir:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ------------------------------------------------------------------
# ZIP 解压逻辑（vendor 自外部 importer._extract_if_zip）
# ------------------------------------------------------------------

def _extract_if_zip(file_path: str) -> tuple[str | None, str | None]:
    """
    如果是 .zip，解压并返回 (xml_path, temp_dir)。
    优先级：export.xml > export_cda.xml > 最大 XML 文件。
    非 zip 文件直接返回原路径。
    """
    if not file_path.lower().endswith(".zip"):
        return (file_path, None)

    temp_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            standard_path = None
            cda_path = None

            for name in zf.namelist():
                base = os.path.basename(name)
                lower = base.lower()
                if not lower.endswith(".xml"):
                    continue
                if lower == "export.xml":
                    standard_path = name
                elif "export_cda" in lower:
                    cda_path = name

            # 没找到 export.xml 则按文件大小选最大的 XML
            if standard_path is None:
                xml_candidates = []
                for name in zf.namelist():
                    base = os.path.basename(name)
                    if base.lower().endswith(".xml") and "export_cda" not in base.lower():
                        info = zf.getinfo(name)
                        xml_candidates.append((info.file_size, name))
                if cda_path:
                    cda_info = zf.getinfo(cda_path)
                    xml_candidates.append((cda_info.file_size, cda_path))
                if xml_candidates:
                    xml_candidates.sort(key=lambda x: x[0], reverse=True)
                    standard_path = xml_candidates[0][1]

            if standard_path:
                zf.extract(standard_path, temp_dir)
                extracted = os.path.join(temp_dir, standard_path)
                logger.info(
                    "选中 XML: %s (%.0f MB)",
                    os.path.basename(standard_path),
                    os.path.getsize(extracted) / 1024 / 1024,
                )
                return (extracted, temp_dir)
            elif cda_path:
                zf.extract(cda_path, temp_dir)
                extracted = os.path.join(temp_dir, cda_path)
                logger.info("回退到 CDA: %s", os.path.basename(cda_path))
                return (extracted, temp_dir)

            return (None, temp_dir)
    except Exception as e:
        logger.error("解压 ZIP 失败: %s", e)
        return (None, temp_dir)



