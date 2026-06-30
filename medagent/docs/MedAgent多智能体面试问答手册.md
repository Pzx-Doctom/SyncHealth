# MedAgent Hub 多智能体系统 — 面试问答手册

> 适用岗位：AI 应用开发 / 大模型应用开发 / Agent 开发工程师
> 项目地址：`medagent/`

---

## 目录

1. [项目概述](#1-项目概述)
2. [架构与图编排](#2-架构与图编排)
3. [完整调用链](#3-完整调用链)
4. [意图识别与路由](#4-意图识别与路由)
5. [Agent 执行与工具调用](#5-agent-执行与工具调用)
6. [容错与防护](#6-容错与防护)
7. [记忆系统](#7-记忆系统)
8. [异步编程](#8-异步编程)
9. [配置与工具链](#9-配置与工具链)
10. [深度追问与薄弱点](#10-深度追问与薄弱点)

---

## 1. 项目概述

### 1.1 这个项目做什么的？

**面试官问**：简单介绍一下 MedAgent 这个项目。

**参考答案**：
MedAgent Hub 是一个基于 LangGraph 的多 Agent 医疗健康对话系统。用户通过 WebSocket 输入健康问题（如"我最近睡不好"），系统通过 LLM 做意图识别分诊，路由到 3 个专业 Agent（健康教练、报告解读、用药管理）或紧急处置通道。每个 Agent 内部使用 ReAct 模式自主调用工具（查健康数据、药品库、附近医院），完成后统一输出回复。支持多轮对话记忆（ChromaDB 向量库 + SQLite 用户画像）、专家间协作（reroute 机制）、流式推送。

**关键代码**：`app/api/chat.py:24`，`app/core/graph.py:120`

---

### 1.2 这个系统的核心设计思想是什么？

**面试官问**：如果用一句话概括这个项目的核心设计理念。

**参考答案**：
**State 驱动的 LLM 自主决策闭环**。不是写死 if-else 规则路由，而是把所有上下文放在 AgentState 中流转，LLM 在每个决策点读 State 做自主判断——triage 判断意图、专家判断工具、条件函数判断下一站。图定义路径上限，LLM 决定实际走哪条路。

**关键代码**：`app/core/state.py:36`（AgentState），`app/core/graph.py:41`（StateGraph）

---

### 1.3 为什么选 LangGraph 而不是 CrewAI / AutoGen？

**面试官问**：市面上有 CrewAI、AutoGen 等 Agent 框架，为什么选 LangGraph？

**参考答案**：
- **CrewAI**：角色驱动，适合"多个 Agent 互相讨论达成共识"的场景。我们这个系统的专家是串行的（一个接一个，不是并行讨论），不需要角色间协商。
- **AutoGen**：微软出品，多 Agent 对话模式强，但偏研究和复杂推理。
- **LangGraph**：有向状态图，天然支持条件分叉 + 循环 + 中断恢复。我们这个系统的 triage 分诊 → 路由 → 专家 → reroute 回 triage 的循环模式，用 LangGraph 的 `add_conditional_edges` 直接表达，不需要额外的协调逻辑。

**一句话**：LangGraph 让你定义"骨架"（节点+边），LLM 决定"血肉"（实际走哪条路）。

**关键代码**：`app/core/graph.py:44-87`

---

### 1.4 Agent 和 Workflow 节点是什么关系？

**面试官问**：这个项目的 Agent 和 workflow 节点是什么关系？能互相替换吗？

**参考答案**：
在这个架构里，**Agent 就是 workflow 节点，workflow 节点就是 Agent**。二者是同一事物不同视角：

- 管理视角：它是一个"workflow 节点"（什么时候执行、下一步去哪）
- 执行视角：它是一个"Agent"（内部用 LLM 做决策）

不能换成纯硬编码规则节点——因为系统处理的是自然语言，"头疼""脑袋像被锤了一样""太阳穴胀痛"是同一个意思，关键词匹配处理不了这种语义变体。

**关键代码**：`app/core/graph.py:44-50`（`workflow.add_node` 的每个节点就是一个 Agent）

---

## 2. 架构与图编排

### 2.1 项目的整体架构是什么？

**面试官问**：画一下这个系统的架构图。

**参考答案**：

```
WebSocket 入口 (chat.py)
       ↓
context_injection（并行加载健康数据 + 记忆 + 知识）
       ↓
triage（LLM 意图识别，输出 JSON）
       ↓
route_after_triage（条件路由）
  ├─ emergency → emergency_node → finalize
  ├─ clarify → finalize（追问用户）
  └─ health_coach / medication / report_interpreter
                ↓
         check_reroute（条件判定）
           ├─ triage（专家举手求援，回 triage 重分诊）
           └─ finalize（输出最终回复）
                ↓
           WebSocket 流式推送 → 前端
```

**关键代码**：`app/core/graph.py:41-87`

---

### 2.2 这个系统使用什么执行模式？

**面试官问**：Agent 的执行模式是什么？ReAct 还是其他？

**参考答案**：
**两层叠加**：外层 LangGraph 编排模式（中央调度 + 顺序推进），内层 ReAct 模式（LLM 自主 想→做→看 循环）。

- 外层：LangGraph 按有向图顺序执行节点，图定义了"可能去哪"，triage 决定"该去哪"
- 内层：每个专家内部是 `create_react_agent` 创建的 ReAct Agent，LLM 自主决定"调哪个工具 → 看结果 → 再决定下一步"，直到觉得够了才输出

**关键代码**：`app/agents/health_coach.py:74`（create_react_agent），`app/core/graph.py:84`（astream 驱动）

---

### 2.3 graph.py 中的图是怎么定义的？

**面试官问**：介绍一下 graph.py 里图的构建过程。

**参考答案**：
用 LangGraph 的 `StateGraph(AgentState)` 构建一个有向有状态图：

1. `add_node` 添加 7 个节点：context_injection、triage、health_coach、medication、report_interpreter、emergency、finalize
2. `add_edge` 固定边：`START → context_injection`、`context_injection → triage`、`emergency → finalize`、`finalize → END`
3. `add_conditional_edges` 条件边：triage 出发走 `route_after_triage`，三个专家出发走 `check_reroute`
4. 编译时绑定 SQLite Checkpointer（用于中断恢复）

**关键代码**：`app/core/graph.py:41-84`（图定义），`app/core/graph.py:135-141`（编译 + Checkpointer）

---

### 2.4 add_conditional_edges 是什么？为什么条件函数会被"自动调用"？

**面试官问**：`route_after_triage` 没有显式调用，为什么它会被执行？

**参考答案**：
这是 LangGraph 的标准 API。`add_conditional_edges` 接收一个函数引用（不是调用），在节点执行完后**由框架自动调用**这个函数，传入当前 State，根据返回值路由到下一个节点。

```python
# 你注册（不调用）：
workflow.add_conditional_edges("triage", route_after_triage, {...})

# LangGraph 内部等价于：
# triage 节点跑完 → next_node = route_after_triage(state) → 路由
```

这是回调机制，不是魔法——和 JS 里 `button.onclick = handleClick` 是一个道理。

**关键代码**：`app/core/graph.py:60-70`（triage 条件边），`app/core/graph.py:72-81`（专家条件边）

---

### 2.5 triage 可以直接到 finalize 吗？

**面试官问**：triage 在什么情况下直接到 finalize？

**参考答案**：
**可以**，两种情况：

1. **信息不足需要追问**：用户说"我不舒服"但没有更多细节 → triage 判定 `needs_clarification = True` → 直接 finalize 输出追问
2. **兜底逻辑**：`target_agent` 为空或不匹配任何专家 → route_after_triage 兜底返回 `"finalize"`

路由优先级：emergency > clarify > target_agent 匹配 > finalize 兜底。

**关键代码**：`app/core/conditions.py:22-45`

---

### 2.6 专家 → check_reroute → {triage | finalize} 是什么意思？

**面试官问**：为什么专家执行完后不是直接去 finalize，而是要经过 check_reroute？

**参考答案**：
这是一个**专家协作机制**。专家干完活后不直接结束，而是经过 check_reroute 判定：

- 如果专家在回复中标记了 `[REROUTE]`（比如健康教练发现涉及用药问题），check_reroute 检测到 `reroute_request` 就**回到 triage 重新分诊**，让 triage 把用户路由到用药管理 Agent
- 如果专家觉得够了、不举手，直接去 finalize 输出

这样实现了"专家之间的间接协作"——不直接互相调用，而是通过 triage 统一协调。

**关键代码**：`app/core/conditions.py:48-69`（check_reroute），`app/agents/health_coach.py:86-91`（[REROUTE] 检测）

---

### 2.7 Reroute 是直接跳到另一个专家还是先回 triage？

**面试官问**：Reroute 后是直接去目标专家，还是先经过 triage？

**参考答案**：
**先回到 triage，重新分诊**。路径是：`health_coach → check_reroute → triage → route_after_triage → medication`。

原因：triage 是唯一的决策中心，需要重新审视全局——也许新信息表明紧急度提升了？也许需要同时找两个专家？所有上下文重新交给 triage 统一决策，比专家之间互相跳转更可控。而且图的出边只有 triage 和 finalize，不可能直接跳到另一个专家。

**关键代码**：`app/core/graph.py:72-81`（专家只有两条出路），`app/core/conditions.py:61-63`（返回 "triage" 而不是 "medication"）

---

### 2.8 AgentState 是什么？它在系统中扮演什么角色？

**面试官问**：AgentState 的设计思路是什么？

**参考答案**：
AgentState 是**所有 Agent 共享的唯一真相来源**。它是一个 TypedDict，包含 `user_query`、`intent`、`severity`、`target_agent`、`reroute_request`、`final_response`、`loop_count` 等字段。

所有 Agent 不直接交流，不互相调用。它们只做一件事：**读 State → 做决策 → 写 State**。triage 写了 `target_agent`，条件函数读到它决定路由；专家写了 `reroute_request`，check_reroute 读到它决定回 triage。

**关键代码**：`app/core/state.py:36-72`（AgentState 定义），`app/core/state.py:75-100`（make_initial_state）

---

### 2.9 state.get() 和 state["key"] 有什么区别？

**面试官问**：为什么代码里用 `state.get("key")` 而不是 `state["key"]`？

**参考答案**：
AgentState 虽然是 TypedDict 类型标注，本质上就是 Python 字典。用 `.get()` 而不是 `[]` 是因为很多字段是 Optional 的，初始状态可能不存在：

- `state.get("reroute_request")` → 没有就返回 None，不会 KeyError 崩溃
- `state.get("loop_count", 0)` → 第二个参数是默认值，初始时为 0

这是防御性编程——LangGraph 在不同节点之间流转 State，某个字段可能在某个节点还没被填充。

**关键代码**：`app/core/conditions.py:57-59`（典型使用）

---

### 2.10 loop_count 是什么？什么情况下会增加？

**面试官问**：loop_count 计数的是什么东西？

**参考答案**：
`loop_count` 是 **triage 节点被执行的次数**。每次 triage_node 执行完毕，return 里调用 `increment_loop` 把 loop_count +1。

只在一种情况下会增加：专家设置了 `reroute_request`，check_reroute 返回 `"triage"`，LangGraph 再次执行 triage 节点。正常一次对话只经过一次 triage，loop_count = 1。

**关键代码**：`app/agents/base.py:158-160`（increment_loop），`app/agents/triage.py:182`（triage_node 的 return 中调用）

---

## 3. 完整调用链

### 3.1 从用户输入到最终回复经历了什么？

**面试官问**：完整的请求处理流程是怎样的？

**参考答案**：
① `chat_websocket`（WebSocket 端点）收到消息 → ② `_handle_chat` 构建空 State → ③ `graph.astream` 启动 LangGraph → ④ context_injection 并行加载健康数据 + 记忆 + 知识 → ⑤ triage 调 LLM 做意图识别，输出 JSON → ⑥ route_after_triage 读 State 决定下一步 → ⑦ 专家节点用 ReAct 模式调工具、生成回复 → ⑧ check_reroute 决定是否回 triage → ⑨ finalize 整理输出 → ⑩ 流式推送 + 持久化记忆。

**关键代码**：`app/api/chat.py:24`（入口），`app/api/chat.py:71`（构建初始 State），`app/api/chat.py:84`（启动图）

---

### 3.2 整个流程的"main"函数是哪个？

**面试官问**：如果我想看懂这个项目，应该从哪个函数开始？

**参考答案**：
`chat_websocket` 是唯一入口，`graph.astream` 是核心引擎。阅读顺序：
1. `chat.py:24` — `chat_websocket`，WebSocket 入口
2. `chat.py:59` — `_handle_chat`，准备 State + 启动图 + 推送结果
3. `graph.py:120` — `get_compiled_graph()`，图的定义
4. `graph.py:84` — `graph.astream`，LangGraph 接管后的自动节点编排

**关键代码**：`app/api/chat.py:24`，`app/core/graph.py:120`

---

### 3.3 入口层的 WebSocket 是怎么处理的？

**面试官问**：为什么用 WebSocket 而不是 HTTP REST？

**参考答案**：
因为需要**流式输出**。AI 的回复是逐 token 生成的，用户应该看到打字机效果而不是等 10 秒一口气出结果。`_process_stream_event` 在图每完成一个节点后把事件（agent_switch、tool_result、thinking、token）通过 WebSocket 实时推送给前端。

**关键代码**：`app/api/chat.py:24`（WebSocket 端点），`app/api/chat.py:133`（_process_stream_event 事件转换）

---

### 3.4 流式事件是怎么分类推送的？

**面试官问**：前端看到了哪些类型的推送事件？

**参考答案**：
`_process_stream_event` 把 LangGraph 的节点更新转换成 6 种事件类型：

| 触发条件 | 事件类型 | 前端展示 |
|---|---|---|
| agent_route 有变化 | `agent_switch` | 展示"正在切换到 XXX Agent" |
| triage_reasoning | `thinking` | 展示"分诊分析中..." |
| tool_calls 有新增 | `tool_result` | 展示工具调用卡片 |
| final_response 有更新 | `token` | 流式文字输出 |
| error 不为空 | `error` | 错误提示 |
| 全部结束 | `done` | 表示对话完成 |

**关键代码**：`app/api/chat.py:133-183`

---

### 3.5 graph.astream 的行为是什么？

**面试官问**：`graph.astream` 每次 yield 的是什么？

**参考答案**：
每完成一个图节点，LangGraph 就 yield 一次 event。event 是一个 dict：`{节点名: 该节点的 State 更新}`。

比如 triage 节点执行完，yield：`{"triage": {"intent": "lifestyle", "severity": "normal", ...}}`。`_handle_chat` 里的 for 循环每次拿到一个 event，传给 `_process_stream_event` 推送给前端，同时记录 `final_state`——当遇到 `"finalize"` 节点时，拿到的 state_update 就是最终结果。

**关键代码**：`app/api/chat.py:84-96`

---

## 4. 意图识别与路由

### 4.1 意图识别是怎么做的？

**面试官问**：系统怎么知道用户的意图是什么？

**参考答案**：
**不是关键词匹配，是 LLM + 路由规则 Prompt → 结构化 JSON**。核心在 `TRIAGE_SYSTEM_PROMPT`，它是一张路由规则表，明确告诉 LLM：

- 什么关键词/特征 → 对应什么意图 → 路由到谁 → 紧急度多少
- 输出格式必须是严格的 JSON（包含 intent、severity、target_agent 等）

LLM 同时看到规则表 + 用户健康数据 + 记忆 + 用户原话，综合做判断。

**关键代码**：`app/agents/triage.py:14-65`（TRIAGE_SYSTEM_PROMPT），`app/agents/triage.py:103-107`（构建 Prompt）

---

### 4.2 为什么用 LLM 做路由而不是关键词匹配？

**面试官问**：用 if-else 关键词匹配不更快更便宜吗？

**参考答案**：
自然语言没有标准格式：
- "头疼" = "脑袋不舒服" = "太阳穴胀痛" = "像被锤了一样" → 关键词匹配只能命中第一个
- "吃了布洛芬之后胃不舒服" → 关键词可能会匹配"胃不舒服"去健康教练，但 LLM 理解"吃了布洛芬之后"是关键，去用药管理

而且这个系统嵌入了用户健康数据和长期记忆，LLM 能看到"这个人正在吃降压药"然后综合判断，关键词完全做不到。

**一句话**：快速 ≠ 准确，医疗场景下语义理解比速度更重要。

---

### 4.3 route_after_triage 的路由优先级是什么？

**面试官问**：如果 triage 返回了多个信号，路由怎么决策？

**参考答案**：
按以下优先级判断：

1. `severity == "emergency"` → 直接去 emergency（安全第一）
2. `intent == "clarify"` 或 `needs_clarification == True` → 去 finalize 追问
3. `target_agent` 能匹配到专家 → 去对应专家
4. 以上都不满足 → 兜底去 finalize

**关键代码**：`app/core/conditions.py:22-45`

---

### 4.4 TRIAGE_SYSTEM_PROMPT 里包含什么内容？

**面试官问**：分诊 Prompt 是怎么设计的？

**参考答案**：
包含三部分：
1. **角色定义**："你是分诊路由专家，绝不直接回答健康问题"
2. **路由规则表**：6 种意图类型 ×（关键词特征 + 路由目标 + 紧急度）
3. **输出格式约束**：严格的 JSON schema，包含 intent、severity、target_agent、reasoning、extracted_entities、needs_clarification 等字段

设计要点是**明确禁止 LLM 自由发挥**——它只能做分诊，不能回答健康问题。

**关键代码**：`app/agents/triage.py:14-65`

---

### 4.5 LLM 输出的 JSON 解析失败怎么办？

**面试官问**：如果 LLM 返回的 JSON 格式不对，怎么处理？

**参考答案**：
`parse_json_response` 有兜底策略：
1. 尝试直接 `json.loads` 解析
2. 尝试从文本中提取 `{...}` 块
3. 全部失败 → 返回 fallback 值：`{"intent": "lifestyle", "severity": "normal", "target_agent": "health_coach"}`

**降级到健康教练是最安全的选择**——它至少能给出通用的健康建议，不会乱分配。

**关键代码**：`app/agents/base.py:109-145`（parse_json_response），`app/agents/triage.py:120-132`（调用 + fallback）

---

### 4.6 triage 这个节点为什么叫"分诊"？

**面试官问**：为什么用"分诊"这个词？

**参考答案**：
Triage 本身就是医学术语——急诊分诊。急诊室里分诊护士做的事和这个节点一模一样：看一眼病人判断紧急度，决定去内科/外科/抢救室，信息不足时追问"疼多久了"。职能完全对应——不治病、不开药，只做判断和分配。

---

### 4.7 triage 在 reroute 场景下有什么特殊行为？

**面试官问**：当专家举手求援（reroute），triage 会怎么做？

**参考答案**：
triage_node 检测到 `state.get("reroute_request")` 有值时，会把 reroute 信息拼进 Prompt：

```
上一个 Agent 请求重新路由
原因: 涉及药物相互作用
携带上下文: {"drug_mentioned": "硝苯地平"}
```

这次 triage 通常会把 `target_agent` 设为上一个专家建议的目标，但**不盲目相信**——它会重新审视整体上下文，自己独立做决策。

**关键代码**：`app/agents/triage.py:90-97`

---

### 4.8 路由信息的可视化——agent_route 是怎么记录的？

**面试官问**：怎么知道一次对话经历了哪些 Agent？

**参考答案**：
`append_route` 函数在每次路由变化时被调用，往 State 的 `agent_route` 列表追加一条记录：`{"from": "triage", "to": "health_coach", "reason": "用户咨询睡眠问题", "timestamp": "..."}`。前端可以展示用户整个对话经过了哪些 Agent、为什么。

**关键代码**：`app/agents/base.py:146-156`（append_route），`app/core/state.py`（agent_route 字段）

---

## 5. Agent 执行与工具调用

### 5.1 Agent 是如何调用工具的？

**面试官问**：具体的工具调用链路是怎样的？

**参考答案**：
四层架构：
1. **定义层**：用 `@tool` 装饰器把普通函数变成 LangChain 工具（`tools/health_data.py` 等）
2. **注册层**：`registry.py` 的 `ALL_TOOLS` 和 `AGENT_TOOLS` 按 Agent 分配工具权限
3. **Agent 创建层**：`create_react_agent(llm, tools, prompt=...)` 把 LLM + 工具包装成 ReAct Agent
4. **自主决策层**：LLM 在 ReAct 循环中自己决定调哪个工具、什么时候调完

**不是写代码控制调用顺序，而是 LLM 根据工具说明书自主决策。**

**关键代码**：`app/tools/registry.py:33-110`，`app/agents/health_coach.py:74`（create_react_agent）

---

### 5.2 工具的权限是怎么分配的？

**面试官问**：健康教练会不会不小心调用用药管理的工具？

**参考答案**：
**不会**。`AGENT_TOOLS` 字典严格按 Agent 划分：

```python
AGENT_TOOLS = {
    "triage": [],                              # 纯推理，不用工具
    "health_coach": ["get_activity_summary", "get_sleep_analysis", "get_heart_rate_trend"],
    "medication": ["lookup_drug_info", "check_drug_interaction"],
    "report_interpreter": ["ocr_medical_report"],
}
```

`get_tools_for_agent("health_coach")` 只返回心跳、睡眠、步数相关工具，药品工具不可见。

**关键代码**：`app/tools/registry.py:67-104`（AGENT_TOOLS），`app/tools/registry.py:107-110`（get_tools_for_agent）

---

### 5.3 Tool Schema 是什么？怎么生成的？

**面试官问**：Tool Schema 是怎么从 Python 函数变成 LLM 能看的格式的？

**参考答案**：
Tool Schema 是工具的"说明书"——告诉 LLM 工具名叫什么、能干什么、需要什么参数。

生成链路：`@tool`（LangChain）→ `StructuredTool.args_schema` → `Pydantic BaseModel.schema()` → JSON Schema → 传给 LLM。

`@tool` 装饰器从函数签名（参数类型注解）+ docstring + Pydantic `Field(description=...)` 提取信息，Pydantic 的 `.schema()` 把它转成标准 JSON Schema 格式，最终以 OpenAI Function Calling 格式塞进 API 请求。

**关键代码**：`app/tools/location.py:49-67`（工具定义示例），`app/tools/location.py:16-31`（args_schema）

---

### 5.4 ReAct 模式具体是怎么运作的？

**面试官问**：解释一下 ReAct 模式。

**参考答案**：
ReAct = Reasoning + Acting，LLM 在 想→做→看 的循环中工作：

```
Thought: "用户睡眠不好，先查睡眠数据"
Action: 调用 get_sleep_analysis(days=7)
Observation: "平均睡眠 6.2 小时，深度睡眠占 12%"
Thought: "数据异常，再查心率"
Action: 调用 get_heart_rate_trend(days=7)
Observation: "静息心率 75bpm，偏高"
Thought: "信息够了，生成建议" → 输出回复
```

**LLM 自主决定调哪个工具、什么时候够了**，不由代码控制。`create_react_agent` 是 LangGraph 提供的工厂函数。

**关键代码**：`app/agents/health_coach.py:74-76`

---

### 5.5 什么是降级 JSON？

**面试官问**：工具调用超时后返回的是什么？

**参考答案**：
降级 JSON 是工具失败时返回的**兜底 JSON 字符串**，让 LLM 知道"这个数据拿不到了，但你别崩溃，用已有信息继续推理"：

```json
{"error": "工具 get_heart_rate_trend 执行超时", "fallback": "数据暂时不可用，请基于已有信息继续分析"}
```

**为什么不是 `return None`？** 因为 LLM 期望工具返回文本，看到这个 JSON 会理解发生什么，基于已有数据继续给建议。抛异常或返回 None 会导致 Agent 崩溃。

**关键代码**：`app/agents/base.py:93-106`

---

### 5.6 工具的调用记录是怎么收集的？

**面试官问**：怎么知道一次对话调用了哪些工具？

**参考答案**：
`extract_tool_calls_from_messages` 遍历 ReAct Agent 的消息历史（AIMessage 中的 tool_calls 和 ToolMessage），提取出结构化记录：

```json
[{"agent": "health_coach", "tool": "get_sleep_analysis", "args": {"days": 7}, "result_snippet": "平均睡眠6.2小时...", "status": "success"}]
```

这些记录写入 State 的 `tool_calls` 字段，前端用它展示工具调用卡片，对话结束后也用于记忆提取。

**关键代码**：`app/agents/base.py:163-202`

---

### 5.7 工具调用为什么需要超时保护？异步不会自动非阻塞吗？

**面试官问**：既然是 `await agent.ainvoke()` 异步执行，为什么还要 `asyncio.wait_for(timeout=15)`？

**参考答案**：
异步 ≠ 不会卡住。`await` 确实释放线程给其他任务，但**当前协程还是会等**——如果高德地图 API 挂了不返回，agent 就永远卡在那，用户一直转圈。

`asyncio.wait_for(timeout=15)` 是"最多等 15 秒，超时就降级"——LLM 看到降级 JSON 后基于已有信息给建议，核心功能不受影响。

**关键代码**：`app/agents/base.py:93`（wait_for timeout=15）

---

## 6. 容错与防护

### 6.1 如何防止死循环？

**面试官问**：系统在哪些层级做了防死循环措施？

**参考答案**：
**三层保护**：

| 层级 | 机制 | 位置 |
|---|---|---|
| Agent 协作循环 | `loop_count < 5`（check_reroute + finalize 双重检查） | `conditions.py:61`，`finalizer.py:24` |
| ReAct 工具循环 | `recursion_limit = 25`（LangGraph 内置） | `create_react_agent` 自动设置 |
| 单次调用 | `@retry(stop_after_attempt=3)` + `asyncio.wait_for(timeout=15)` | `base.py:60`，`base.py:93` |

**极端场景**：即使 5 个专家来回举手、每个专家调 25 次工具、每次网络请求重试 3 遍——最终循环上限必然触发，强制去 finalize。

**关键代码**：`app/core/conditions.py:48-69`，`app/core/finalizer.py:24-29`

---

### 6.2 LLM 调用失败了怎么处理？

**面试官问**：如果 DeepSeek API 挂了怎么办？

**参考答案**：
两层保护：
1. **重试**：`safe_llm_call` 用了 `@retry(stop_after_attempt=3, wait=wait_exponential(...))`，自动重试 3 次（1s → 2s → 4s）
2. **兜底**：3 次都失败后抛 `LLMCallError`，fallback 逻辑生效，triage 降级到默认意图（health_coach），finalize 输出通用错误提示

不抛裸异常、不让前端看到技术细节。

**关键代码**：`app/agents/base.py:60-65`（tenacity 重试），`app/agents/triage.py:120-132`（JSON 解析 fallback）

---

### 6.3 MCP 请求（SyncHealth Backend）挂了怎么办？

**面试官问**：后端服务不可用时，Agent 还能正常工作吗？

**参考答案**：
**可以，有三重降级**：
1. tenacity 重试 3 次（1s → 2s → 4s）
2. 历史缓存 `_fallback_cache`——上次成功返回的数据复用
3. 缓存也没有 → 返回提示文本 "健康数据暂不可用"——LLM 基于知识库和长期记忆继续回答

关键设计：**服务降级但不对用户报错**。

**关键代码**：`app/mcp/client.py:59-68`（重试），`app/mcp/client.py:86-93`（缓存降级）

---

### 6.4 超时保护的参数是怎么配置的？

**面试官问**：超时时间、重试次数这些在哪配？

**参考答案**：
全部在 `.env` / `config.py` 中可配：

| 参数 | 配置项 | 默认值 |
|---|---|---|
| Agent 最大循环次数 | `MAX_LOOPS` | 5 |
| 工具调用超时 | `TOOL_TIMEOUT_SECONDS` | 15s |
| MCP 重连次数 | `MCP_RECONNECT_RETRIES` | 3 |
| LLM API 重试次数 | 硬编码 `stop_after_attempt(3)` | 3 |
| 指数退避范围 | 硬编码 `wait=wait_exponential(min=1, max=4)` | 1-4s |

**关键代码**：`app/config.py:44-50`

---

### 6.5 finalize 节点做了什么兜底？

**面试官问**：最后一道防线是什么？

**参考答案**：
`finalize_node` 是**统一出口**，处理四种情况：
1. `error` 有值 → 输出错误提示（包装成用户能懂的话）
2. `needs_clarification` → 输出追问
3. `loop_count >= MAX_LOOPS` → 输出 "多次路由仍未能得出结论"
4. 正常 → 取 `final_response` 原样输出

**无论什么路径到达 finalize，都会得到一个可展示的输出，不会崩溃。**

**关键代码**：`app/core/finalizer.py:7-36`

---

### 6.6 tenacity 是什么？为什么用它？

**面试官问**：介绍一下 tenacity 库和在项目中的使用。

**参考答案**：
tenacity 是 Python 的重试库。用 `@retry` 装饰器给函数加上自动重试：

```python
@retry(
    stop=stop_after_attempt(3),                    # 最多 3 次
    wait=wait_exponential(min=1, max=4),            # 指数退避 1s→2s→4s
    retry=retry_if_exception_type((httpx.HTTPError,)),  # 只重试网络错误
    reraise=True,                                    # 3 次都失败抛异常
)
```

相比手写 `for i in range(3): try...except...` 更优雅、更可配置，在 `safe_llm_call` 和 MCP 客户端两处使用。

**关键代码**：`app/agents/base.py:60-65`，`app/mcp/client.py:59-68`

---

## 7. 记忆系统

### 7.1 为什么需要记忆？

**面试官问**：没有记忆的话 Agent 对话有什么问题？

**参考答案**：
没有记忆：每次都是"第一次见你"——用户说了 3 次头晕，每次都从头问"什么时候开始的"。

有记忆：Agent 知道用户 3 个月前血压 145/95、正在服硝苯地平、上次建议了监测血压——这次能追问"你有记录血压变化吗？"，每个建议都有延续性。

**在医疗场景，记忆不是锦上添花，是刚需**——用药调整、症状进展必须基于历史信息的连续判断。

---

### 7.2 长期记忆 + 短期记忆是怎么设计的？

**面试官问**：记忆系统有几层？分别怎么实现？

**参考答案**：
**三层记忆**：

| 层级 | 存储 | 内容 | 持久化 |
|---|---|---|---|
| LangGraph Checkpointer | SQLite | 完整对话历史（State 流转） | ✅ |
| 对话摘要缓冲区 | 运行内存 | Token 超限后 LLM 压缩的对话摘要 | ❌ |
| 健康事件向量库 | ChromaDB | 用户健康事件（用药、检查等） | ✅ |
| 用户画像 | SQLite | 年龄、BMI、过敏史、慢性病 | ✅ |

检索策略：对话开始时 `context_injection_node` 并行加载画像 + ChromaDB 语义搜索（top_k=5），拼入 State 的 `memory_context`。

**关键代码**：`app/memory/vector_store.py:17-53`，`app/memory/manager.py:131-172`

---

### 7.3 哪些东西会被存成长期记忆？

**面试官问**：什么事件会被记入 ChromaDB？

**参考答案**：
对话结束后，`extract_and_store_events` 遍历工具调用记录，**不是 LLM 理解对话提取，而是规则匹配**。当前存储 3 种事件：

| 工具被调用 | 存储摘要 | 事件类型 |
|---|---|---|
| `create_medication_reminder` | "用户开始用药: {药品名}" | medication_change |
| `ocr_medical_report` | "用户上传了体检报告并解读" | health_event |
| `ocr_medicine_box` | "用户查询了药品信息" | medication_change |

**设计考虑**：只记"动作型"关键事件（调工具 = 真做了），不记闲聊内容。宁可漏掉信息，也不存进 LLM 可能编造的记忆。

**关键代码**：`app/memory/manager.py:174-231`

---

### 7.4 向量数据库是什么？项目里怎么用的？

**面试官问**：向量数据库在项目中的作用是什么？

**参考答案**：
传统数据库搜"头痛"只找到标题有"头痛"两个字的记录。向量数据库把"头痛"变成 768 维向量 `[0.12, -0.34, ...]`，在向量空间找语义最接近的（"偏头痛""太阳穴胀痛""高血压头晕"都能匹配到）。

**项目用法**：用户说"我最近头晕" → 向量化 → ChromaDB 搜索 → 命中"3个月前血压检查显示145/95"（相似度 0.87）→ 注入 memory_context → Agent 知道要关注血压。

配置：使用 `BAAI/bge-large-zh-v1.5` 中文嵌入模型，通过 SiliconFlow API 远程调用。

**关键代码**：`app/memory/vector_store.py:17-53`（初始化），`app/memory/vector_store.py:113-134`（语义检索）

---

### 7.5 对话结束后 LLM 提取记忆是怎么做的？

**面试官问**：对话结束后是怎么提取健康事件作为记忆的？

**参考答案**：
**实际上不是 LLM 提取的，是规则匹配**。`extract_and_store_events` 直接遍历 `tool_calls` 列表——如果发现了 `create_medication_reminder` 就记"用户开始用药"，发现 `ocr_medical_report` 就记"用户上传报告"。

为什么不用 LLM？规则匹配更快（零成本、100% 准确、不会编造）。只记关键事件节点，对话里的闲聊靠摘要缓冲区记就够了。

**关键代码**：`app/memory/manager.py:174-231`，触发入口 `app/api/chat.py:109-116`

---

### 7.6 对话摘要缓冲区是什么？什么时候触发？

**面试官问**：Token 超限后怎么处理？

**参考答案**：
`_SimpleSummaryMemory` 是一个运行内存级的令牌管理机制。当对话历史总 token 数超过阈值时，用 LLM 把历史压缩成一段摘要：
```
原始: 用户说A→AI回B→用户说C→AI回D→...（5000 tokens）
压缩: "用户持续关注头痛问题，之前建议是减少咖啡因..."
```
不持久化，服务重启后从 LangGraph Checkpointer（SQLite）恢复原始数据重新构建。

**关键代码**：`app/memory/manager.py` 内部 `_SimpleSummaryMemory` 类

---

### 7.7 用户画像存在哪？包含什么信息？

**面试官问**：用户的长期健康信息怎么存？

**参考答案**：
SQLite `UserProfile` 表，存储结构化数据：`age`、`gender`、`bmi`、`chronic_conditions`、`allergies`、`current_medications`、`health_goals`、`home_address`。

为什么用 SQLite 而不是向量库？画像数据是结构化、精确查询场景（"用户的过敏史是什么"），不需要语义检索。向量库处理"用头晕这个模糊概念去找历史上相关的健康事件"。

**关键代码**：`app/memory/manager.py`（UserProfile 管理）

---

## 8. 异步编程

### 8.1 async 和 await 是什么关系？

**面试官问**：`async def` 和 `await` 的职责分别是什么？

**参考答案**：

| 关键字 | 职责 | 位置 |
|---|---|---|
| `async def` | **定义**：声明这个函数是异步的 | 函数定义最前面 |
| `await` | **调用**：等待异步函数的结果 | 函数体内，调用异步函数时 |

`async` 告诉 Python "这个函数里有 await"，`await` 告诉 Event Loop "这个调用可能要等，你先去处理别人"。类比：`async def fn` = 你是协程（能暂停），`await` = 你暂停的那个点。

---

### 8.2 await 后面的代码还能继续执行吗？

**面试官问**：`result = await agent.ainvoke(...)` 后面一行会立即执行吗？

**参考答案**：
**不会**。当前协程中 await 后面的代码会**暂停**，直到 `agent.ainvoke` 完成才继续。但**等的期间 Event Loop 去处理其他用户的请求**——你的协程暂停了，别人在跑。

你自己的 await 会卡住你自己，但不影响整体吞吐效率。

---

### 8.3 Event Loop 是什么？

**面试官问**：解释一下 Event Loop 的工作原理。

**参考答案**：
Event Loop 是一个**单线程任务调度器**，本质上是一个无限循环：

```
while True:
    找一件"就绪"的任务 → 执行一小段 → 
    如果遇到 await → 挂起当前任务，切换下一个
    如果某个挂起任务的 I/O 完成了 → 放回就绪队列
```

一个线程同时伺候多个用户：A 在等 LLM 返回时，Event Loop 切到 B 去加载健康数据，又切到 C 去处理消息——谁的 await 先完成谁先继续。这就是"异步 = 一个服务员同时伺候多桌"。

---

### 8.4 await 和同步调用有什么区别？这不是看起来和同步一样吗？

**面试官问**：`await fn()` 行为不就是"等"吗，和同步有什么区别？

**参考答案**：
**写法像同步，运行是异步**。区别在于"等"的期间：

- 同步 `requests.get(url)`：线程被占着空转 3 秒，不能服务其他用户
- 异步 `await httpx.get(url)`：线程释放给 Event Loop，3 秒内服务了其他 10 个请求

**类比**：同步 = 盯着厨师做菜什么也不干；异步 = 告诉厨师"好了叫我"，然后去接下一桌的单。

---

### 8.5 Python 和 JS 的异步有什么区别？

**面试官问**：Python 的 async/await 和 JavaScript 的一样吗？

**参考答案**：
**语法和语义几乎一模一样**。`async function` ↔ `async def`，`await` ↔ `await`。

唯一区别：JS **天生异步**（浏览器不能卡），`setTimeout` 即使不加 await 也会后台执行。Python **默认同步**，不加 await 的 `async_func()` 会返回一个"没执行的协程对象"，什么都不做。Python 更严格：要么 await（等），要么 `asyncio.create_task()`（后台跑），必须显式选择。

---

## 9. 配置与工具链

### 9.1 配置项是如何从 .env 加载到代码里的？

**面试官问**：`.env` 里的 `MAX_LOOPS=5` 最终是怎么被 `check_reroute` 读到 `settings.MAX_LOOPS` 的？

**参考答案**：
使用 `pydantic-settings` 的 `BaseSettings`，加载链：

1. `config.py` 定义 `Settings(BaseSettings)` 类，类属性 `MAX_LOOPS: int = 5` 是默认值
2. `model_config.env_file` 指向 `.env` 文件
3. `settings = Settings()` 实例化时，`BaseSettings.__init__` 自动读取 `.env` 覆盖默认值
4. `conditions.py` 中 `settings.MAX_LOOPS` 拿到最终值

优先级：OS 环境变量 > `.env` 文件 > 类属性默认值。这是 12-Factor App 推荐的配置管理方式。

**关键代码**：`app/config.py:8-65`

---

### 9.2 为什么 config.py 里很多字段是空的？

**面试官问**：`AI_API_KEY: str = ""` 是空的，运行时不会报错吗？

**参考答案**：
不会，因为 `BaseSettings` 在实例化时从 `.env` 里读取真实值覆盖了默认值。类属性里的空字符串只是**安全兜底**——如果 `.env` 和 OS 环境变量都没配，就用默认值。但像 `AI_API_KEY` 这种必须的，运行时没配到 LLM 调用自然报错，不会"悄无声息的失败"。

**关键代码**：`app/config.py:8-65`，`app/.env`

---

### 9.3 MCP 是什么？在项目中怎么用的？

**面试官问**：介绍一下项目的 MCP 模块。

**参考答案**：
MCP 是一个**基于 HTTP REST 的客户端**，负责从 SyncHealth Backend 服务拉取用户健康数据（心率、睡眠、步数等）。两个接入点：

- `context_injection_node`：对话开始时调 `get_health_context` 获取用户健康全貌
- 健康数据工具：Agent 执行中调 `call_health_tool` 精确查询某类数据

容错设计：tenacity 重试 → 本地缓存降级 → 提示文本兜底。它不是标准的 MCP 协议实现，而是借用了"Model Context Protocol"概念——为 AI 模型提供外部数据上下文。

**关键代码**：`app/mcp/client.py:21-26`（初始化），`app/mcp/client.py:70-93`（get_health_context），`app/mcp/client.py:95-123`（call_health_tool）

---

### 9.4 context_injection 是怎么并行加载的？

**面试官问**：对话开始时的上下文加载为什么那么快？

**参考答案**：
`asyncio.gather` 并行发起三个请求：健康数据（MCP）、长期记忆（ChromaDB）、医学知识（RAG/Dify）——三件事同时做，总耗时 = max(三个中最慢的)，不是三者之和。每个请求失败不会影响其他（`return_exceptions=True`）。

**关键代码**：`app/core/context_injection.py:25-30`

---

### 9.5 市面上还有哪些 Workflow 框架？为什么选 LangGraph？

**面试官问**：除了 LangGraph，还了解哪些 Agent/Workflow 框架？

**参考答案**：

| 框架 | 特点 | 为什么不选 |
|---|---|---|
| CrewAI | 角色驱动多 Agent 协作 | 我们的专家是串行的，不需要角色间协商 |
| AutoGen | 微软出品，多 Agent 对话 | 偏研究，部署复杂 |
| Dify / Coze | 可视化拖拽，低代码 | 定制化受限，适合快速原型 |
| Temporal | 分布式任务编排 | 太重，不是为 LLM 设计的 |

**LangGraph 最适合**：有向状态图天然支持分叉+循环+中断恢复，和 LangChain 生态无缝集成。

---

## 10. 深度追问与薄弱点

### 10.1 如果 LLM 分诊错了怎么办？

**面试官问**：用户说"我胸口疼"，triage 失误判成了 health_coach 而不是 emergency，会发生什么？

**参考答案**：
这是 LLM 分诊的固有风险。当前防护措施：
1. **Prompt 中有明确的紧急关键词**（剧烈胸痛、呼吸困难、意识模糊）——这些是强信号
2. **兜底到 finalize**——即使路由错了，专家至少会给建议（健康教练看到"胸痛"也会建议就医）
3. **severity 字段**——即使去了 health_coach，severity 被 LLM 标记为 attention 的话，Prompt 会提醒 Agent 谨慎对待

**改进方向（可以提，展示思考深度）**：增加关键词硬规则作为 LLM 判断的硬底（比如"胸痛"强制至少 severity=attention）；增加人工审核路径。

---

### 10.2 医疗场景怎么保障准确性和安全性？

**面试官问**：这个大模型给出的医疗建议，怎么保证正确？

**参考答案**：
坦诚承认 + 多层防护：
1. **免责声明**：SystemPrompt 中声明"仅供参考，不构成医疗建议"
2. **知识增强**：每个 Agent 都注入 RAG 医学知识库，不是纯靠 LLM 记忆
3. **紧急通道**：severity="emergency" 固定路由到 emergency 节点（优先推荐打 120、去急诊），不交给普通专家处理
4. **数据可追溯**：工具调用记录可审计（查了什么数据、基于什么做的判断）

**讲真话**：LLM 应用在医疗领域无法做到 100% 准确，这个项目是"健康辅助"而非"医疗诊断"。

---

### 10.3 如果 DeepSeek API 彻底挂了，整个系统就瘫痪了吗？

**面试官问**：API 不可用的极端情况怎么处理？

**参考答案**：
坦诚：是整个系统对 LLM 的依赖。改进方向：
1. 配置 LLM Fallback——DeepSeek 不行自动切换到备用 API（通义千问等）
2. 缓存常见回复——类似问题的回复可以直接返回
3. 部分降级——triage 用规则引擎（关键词匹配）代替 LLM，专家用模板回答

**现状**：项目没有实现这些，因为 LLM 是核心引擎——这确实是一个单点依赖。

---

### 10.4 如何测试和评估 Agent 的表现？

**面试官问**：怎么知道这个 Agent 系统好不好用？

**参考答案**：
现有测试见 `tests/test_studio_batch.py`。理想评估体系：
1. **路由准确率**：人工标注 100 条 query，统计 triage 正确率
2. **工具调用准确率**：看 ReAct Agent 是否调了该调的工具、参数是否正确
3. **回复质量**：人工评分（专业度、相关性、安全性）+ LLM 自动评分
4. **延迟测试**：P50 / P95 / P99 的端到端延迟
5. **压力测试**：并发 WebSocket 连接数上限

**讲真话**：目前只做了基本的手动测试，完善的评估体系是下一步工作。

**关键代码**：`tests/test_studio_batch.py`

---

### 10.5 如何控制 LLM 调用的成本和延迟？

**面试官问**：每次对话都要调好几次 LLM，成本怎么控制？

**参考答案**：
当前成本结构：
- triage 一次 LLM 调用（意图识别：短线）
- 每个专家内部 ReAct 循环（工具选择：多次短调用 + 1 次长调用生回复）
- reroute 会倍数放大

优化方向：
1. **小模型做分诊**：triage 可以用便宜的模型（重要数据已经被工具拿到）
2. **缓存常见 query 的路由决策**
3. **限制 ReAct 最大步数**（当前 25 步可能过于宽松）
4. **摘要缓冲区减少重复上下文**（减少 token 消耗）

---

### 10.6 如果新增一个专家（比如心理医生 Agent），需要改哪些地方？

**面试官问**：怎么扩展系统？

**参考答案**：
6 步扩展：
1. `app/agents/` 下新建 `psychologist.py`（定义 Agent 节点函数）
2. `app/tools/` 下新建工具（心理咨询相关）
3. `app/tools/registry.py`：在 `ALL_TOOLS` 和 `AGENT_TOOLS` 中注册
4. `app/core/graph.py`：`workflow.add_node` + `add_conditional_edges`
5. `app/core/conditions.py`：在 `route_after_triage` 的 route_map 中添加映射
6. `app/agents/triage.py`：在 TRIAGE_SYSTEM_PROMPT 路由规则表中添加"心理咨询"一行

**关键是架构支持松散扩展**——新增专家不需要修改现有专家代码。

---

### 10.7 你是如何学习并搭建这个项目的？遇到了什么坑？

**面试官问**：项目开发过程中最大的挑战是什么？

**参考答案**：
推荐按实际情况说，以下是可以参考的框架：
1. **理解 LangGraph 的 add_conditional_edges**：一开始以为条件函数要手动调，后来才理解是注册回调机制
2. **异步编程**：`await` 和超时保护的关系——异步不会自动防卡死，需要 `asyncio.wait_for`
3. **Reroute 机制设计**：一开始想直接让专家跳转，后来意识到 triage 应该是唯一决策中心
4. **ChromaDB + 嵌入模型初始化**：配置里写了硅基流动 API 但初始化时要显式绑定 embedding function，否则 ChromaDB 会下载本地模型

---

### 10.8 如果要上线部署，还需要做什么？

**面试官问**：这个项目的生产就绪度如何？

**参考答案**：
可以讨论的方向：
1. **LLM Fallback**：主 API 挂了自动切换备用
2. **监控告警**：triage 准确率、端到端延迟、错误率、token 消耗
3. **A/B 测试**：不同 Prompt 版本的对比
4. **速率限制**：防止单个用户刷爆 API 额度
5. **向量库性能**：ChromaDB 单机变多机（考虑迁移到 Qdrant/Milvus）
6. **安全审计**：医疗信息脱敏、对话内容合规
7. **CI/CD**：自动化测试 + 部署流程

---

## 附录：薄弱点速查表

| 薄弱点 | 风险 | 面试话术 |
|---|---|---|
| LLM 分诊准确率 | 路由错误 | "当前靠 Prompt 工程约束，理想情况是需要有标注数据的评估" |
| 单 LLM 依赖 | API 挂了全瘫 | "计划做 LLM Fallback + 规则引擎兜底" |
| 记忆提取靠规则 | 覆盖面窄 | "当前是务实选择，后续可用小模型做结构化提取" |
| 没有端到端测试 | 质量没法量化 | "已搭建基础测试框架，评估体系建设是下一步" |
| ReAct 步数上限 25 | 可能过于宽松 | "可调整为 5-10 步，结合业务场景调优" |
| ChromaDB 单机 | 横向扩展困难 | "数据量不大时够用，后续可迁移到 Qdrant" |

---

> **面试技巧**
> - 面试官最想看的是**你对系统的理解深度**，背诵答案不如讲清楚"为什么这样设计"
> - 遇到不会的问题坦诚说明"当前没实现，但我思考过可以这么做..."
> - 医疗项目特别注意安全性表达——"辅助"而非"诊断"
> - 用具体的代码行号和文件名做支撑，比空谈架构更有说服力
