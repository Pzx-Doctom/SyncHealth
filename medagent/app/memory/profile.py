"""用户画像管理 - 长期记忆的关系型部分"""
import logging
from typing import Optional

from sqlalchemy import select

from app.database import async_session_factory
from app.models.profile import UserProfile

logger = logging.getLogger(__name__)


async def get_profile(user_id: str) -> Optional[dict]:
    """获取用户健康画像"""
    async with async_session_factory() as session:
        result = await session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile:
            return profile.profile_data
    return None


async def update_profile(user_id: str, profile_data: dict) -> dict:
    """创建或更新用户画像"""
    async with async_session_factory() as session:
        result = await session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if profile:
            # 合并更新
            existing = profile.profile_data or {}
            existing.update(profile_data)
            profile.profile_data = existing
        else:
            profile = UserProfile(user_id=user_id, profile_data=profile_data)
            session.add(profile)

        await session.commit()
        return profile.profile_data


async def add_medication(user_id: str, medication: str) -> dict:
    """向用户画像添加当前用药"""
    profile = await get_profile(user_id)
    if profile is None:
        profile = {}

    medications = profile.get("current_medications", [])
    if medication not in medications:
        medications.append(medication)
    profile["current_medications"] = medications

    return await update_profile(user_id, profile)


async def remove_medication(user_id: str, medication: str) -> dict:
    """从用户画像移除用药"""
    profile = await get_profile(user_id)
    if profile is None:
        return {}

    medications = profile.get("current_medications", [])
    if medication in medications:
        medications.remove(medication)
    profile["current_medications"] = medications

    return await update_profile(user_id, profile)
