"""LangGraph 图构建 + 编译 + SQLite Checkpointer"""
import logging
from typing import Optional

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import StateGraph, END

from app.config import settings
from app.core.state import AgentState
from app.core.conditions import route_after_triage, check_reroute
from app.core.context_injection import context_injection_node
from app.core.finalizer import finalize_node

logger = logging.getLogger(__name__)

# 全局编译后的图实例
_compiled_graph: Optional[object] = None
_checkpointer: Optional[AsyncSqliteSaver] = None


def build_graph() -> StateGraph:
    """
    构建多 Agent 协作图。

    节点：
      - context_injection  → 数据准备
      - triage             → 分诊路由
      - health_coach       → 健康教练
      - report_interpreter → 报告解读
      - medication         → 用药管理
      - emergency          → 紧急处置（简化版：直接在 finalize 处理）
      - finalize           → 最终输出

    流转：
      START → context_injection → triage
      triage → {health_coach | report_interpreter | medication | emergency | finalize}
      专家 → check_reroute → {triage | finalize}
      emergency → finalize
      finalize → END
    """
    workflow = StateGraph(AgentState)

    # ===== 注册节点 =====
    workflow.add_node("context_injection", context_injection_node)
    workflow.add_node("triage", _get_triage_node())
    workflow.add_node("health_coach", _get_health_coach_node())
    workflow.add_node("report_interpreter", _get_report_interpreter_node())
    workflow.add_node("medication", _get_medication_node())
    workflow.add_node("emergency", _get_emergency_node())
    workflow.add_node("finalize", finalize_node)

    # ===== 设置入口 =====
    workflow.set_entry_point("context_injection")

    # ===== 边 =====
    # context_injection → triage（始终先加载数据再分诊）
    workflow.add_edge("context_injection", "triage")

    # triage → 条件路由到各专家 / emergency / finalize
    workflow.add_conditional_edges(
        "triage",
        route_after_triage,
        {
            "health_coach": "health_coach",
            "report_interpreter": "report_interpreter",
            "medication": "medication",
            "emergency": "emergency",
            "finalize": "finalize",
        },
    )

    # 各专家 → check_reroute（回到 triage 或去 finalize）
    for specialist in ["health_coach", "report_interpreter", "medication"]:
        workflow.add_conditional_edges(
            specialist,
            check_reroute,
            {
                "triage": "triage",
                "finalize": "finalize",
            },
        )

    # emergency → finalize（不循环）
    workflow.add_edge("emergency", "finalize")

    # finalize → END
    workflow.add_edge("finalize", END)

    return workflow


# ===== 节点懒加载（避免循环导入） =====

def _get_triage_node():
    from app.agents.triage import triage_node
    return triage_node


def _get_health_coach_node():
    from app.agents.health_coach import health_coach_node
    return health_coach_node


def _get_report_interpreter_node():
    from app.agents.report_interpreter import report_interpreter_node
    return report_interpreter_node


def _get_medication_node():
    from app.agents.medication import medication_node
    return medication_node


def _get_emergency_node():
    """紧急处置节点：直接输出急救建议 + 附近急诊"""
    from app.agents.emergency import emergency_node
    return emergency_node


async def get_compiled_graph():
    """
    获取编译后的 LangGraph 实例（带 SQLite Checkpointer）。
    Checkpointer 支持中断恢复和对话回溯。
    """
    global _compiled_graph, _checkpointer

    if _compiled_graph is not None:
        return _compiled_graph

    import aiosqlite

    graph = build_graph()

    # 创建异步 SQLite Checkpointer
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    conn = await aiosqlite.connect(db_path)
    _checkpointer = AsyncSqliteSaver(conn)
    await _checkpointer.setup()

    _compiled_graph = graph.compile(checkpointer=_checkpointer)
    logger.info("LangGraph 编译完成，已启用 SQLite Checkpointer")
    return _compiled_graph


async def close_graph():
    """关闭图资源"""
    global _compiled_graph, _checkpointer
    if _checkpointer is not None:
        await _checkpointer.conn.close()
        _checkpointer = None
    _compiled_graph = None
