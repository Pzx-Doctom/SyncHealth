import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundException
from app.database import get_db
from app.models.ai import AIAgent
from app.models.user import User
from app.schemas.ai import AgentCreate, AgentOut, AgentUpdate

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentOut])
async def list_agents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIAgent).where(AIAgent.user_id == current_user.id).order_by(AIAgent.created_at.desc())
    )
    agents = result.scalars().all()
    out = []
    for a in agents:
        scope = json.loads(a.health_data_scope) if a.health_data_scope else None
        out.append(AgentOut(
            id=a.id, name=a.name, description=a.description,
            system_prompt=a.system_prompt, health_data_scope=scope,
            is_active=a.is_active, created_at=a.created_at, updated_at=a.updated_at,
        ))
    return out


@router.post("", response_model=AgentOut)
async def create_agent(
    data: AgentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = AIAgent(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        system_prompt=data.system_prompt,
        health_data_scope=json.dumps(data.health_data_scope) if data.health_data_scope else None,
    )
    db.add(agent)
    await db.flush()
    scope = json.loads(agent.health_data_scope) if agent.health_data_scope else None
    return AgentOut(
        id=agent.id, name=agent.name, description=agent.description,
        system_prompt=agent.system_prompt, health_data_scope=scope,
        is_active=agent.is_active, created_at=agent.created_at, updated_at=agent.updated_at,
    )


@router.put("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: int,
    data: AgentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await db.get(AIAgent, agent_id)
    if not agent or agent.user_id != current_user.id:
        raise NotFoundException("Agent not found")

    if data.name is not None:
        agent.name = data.name
    if data.description is not None:
        agent.description = data.description
    if data.system_prompt is not None:
        agent.system_prompt = data.system_prompt
    if data.health_data_scope is not None:
        agent.health_data_scope = json.dumps(data.health_data_scope)
    if data.is_active is not None:
        agent.is_active = data.is_active

    scope = json.loads(agent.health_data_scope) if agent.health_data_scope else None
    return AgentOut(
        id=agent.id, name=agent.name, description=agent.description,
        system_prompt=agent.system_prompt, health_data_scope=scope,
        is_active=agent.is_active, created_at=agent.created_at, updated_at=agent.updated_at,
    )


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await db.get(AIAgent, agent_id)
    if not agent or agent.user_id != current_user.id:
        raise NotFoundException("Agent not found")

    await db.delete(agent)
    return {"detail": "Deleted"}
