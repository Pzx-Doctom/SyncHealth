"""Agent 配置 CRUD API"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.profile import AgentConfig
from app.schemas.agent import (
    AgentConfigCreate,
    AgentConfigUpdate,
    AgentConfigOut,
    AgentListResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_USER_ID = "default_user"


@router.get("", response_model=AgentListResponse)
async def list_agents(db: AsyncSession = Depends(get_db)):
    """列出所有 Agent 配置（含全局默认和用户自定义）"""
    result = await db.execute(
        select(AgentConfig).where(
            (AgentConfig.user_id == DEFAULT_USER_ID) | (AgentConfig.user_id.is_(None))
        ).order_by(AgentConfig.agent_name)
    )
    agents = result.scalars().all()
    return AgentListResponse(agents=[AgentConfigOut.model_validate(a) for a in agents])


@router.post("", response_model=AgentConfigOut)
async def create_agent(
    agent: AgentConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建 Agent 配置"""
    agent_data = agent.model_dump()
    agent_data["user_id"] = agent_data.get("user_id", DEFAULT_USER_ID)

    # 检查是否已存在同名配置
    existing = await db.execute(
        select(AgentConfig).where(
            AgentConfig.agent_name == agent.agent_name,
            AgentConfig.user_id == agent_data["user_id"],
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Agent '{agent.agent_name}' 配置已存在")

    new_agent = AgentConfig(**agent_data)
    db.add(new_agent)
    await db.commit()
    await db.refresh(new_agent)
    return AgentConfigOut.model_validate(new_agent)


@router.get("/{agent_name}", response_model=AgentConfigOut)
async def get_agent(agent_name: str, db: AsyncSession = Depends(get_db)):
    """获取单个 Agent 配置"""
    result = await db.execute(
        select(AgentConfig).where(
            AgentConfig.agent_name == agent_name,
            (AgentConfig.user_id == DEFAULT_USER_ID) | (AgentConfig.user_id.is_(None)),
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' 不存在")
    return AgentConfigOut.model_validate(agent)


@router.put("/{agent_name}", response_model=AgentConfigOut)
async def update_agent(
    agent_name: str,
    update: AgentConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新 Agent 配置"""
    result = await db.execute(
        select(AgentConfig).where(
            AgentConfig.agent_name == agent_name,
            AgentConfig.user_id == DEFAULT_USER_ID,
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' 不存在")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(agent, key, value)

    await db.commit()
    await db.refresh(agent)
    return AgentConfigOut.model_validate(agent)


@router.delete("/{agent_name}")
async def delete_agent(agent_name: str, db: AsyncSession = Depends(get_db)):
    """删除 Agent 配置"""
    result = await db.execute(
        select(AgentConfig).where(
            AgentConfig.agent_name == agent_name,
            AgentConfig.user_id == DEFAULT_USER_ID,
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' 不存在")

    await db.delete(agent)
    await db.commit()
    return {"message": f"Agent '{agent_name}' 已删除"}
