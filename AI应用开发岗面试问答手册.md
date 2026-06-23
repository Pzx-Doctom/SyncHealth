# SyncHealth AI 应用开发岗面试问答手册

> 本手册基于 SyncHealth 项目真实代码编写，所有答案均引用实际文件路径与函数逻辑，可直接用于面试复习与自我演练。
>
> 每题结构：**面试官问题 → 参考答案（基于代码）→ 薄弱点 / 改进方向**

---

## 目录

- [一、项目业务理解（Q1–Q5）](#一项目业务理解q1q5)
- [二、RAG 架构设计（Q6–Q9）](#二rag-架构设计q6q9)
- [三、Agent 智能体设计（Q10–Q12）](#三agent-智能体设计q10q12)
- [四、Prompt 工程（Q13–Q15）](#四prompt-工程q13q15)
- [五、LLM 工程化（Q16–Q19）](#五llm-工程化q16q19)
- [六、流式输出（Q20–Q22）](#六流式输出q20q22)
- [七、数据工程（Q23–Q25）](#七数据工程q23q25)
- [八、系统设计与深度追问（Q26–Q30）](#八系统设计与深度追问q26q30)
- [附录：薄弱点速查表](#附录薄弱点速查表)

---

## 一、项目业务理解（Q1–Q5）

### Q1: 简单介绍一下你的项目，它解决了什么问题？

> **问题**：用一两分钟介绍你的项目，核心解决了什么痛点？

**参考答案**：

SyncHealth 是一个 AI 驱动的个人健康数据同步与分析全栈平台，三端协同（React Native 移动端 + FastAPI 后端 + Vue3 前端）。它解决三个痛点：

1. **健康数据碎片化**——Apple Watch 采集的心率、睡眠、步数、血氧等 11 种数据散落在手机本地，Apple 健康应用只做原始展示，不做深度分析和跨维度关联。
2. **数据采集与 AI 分析断裂**——让 AI 理解健康数据需要手动截图或复制粘贴，LLM 无法直接"看到"用户的结构化数据。
3. **通用 AI 缺乏专业聚焦**——通用 ChatGPT 不了解用户身体指标，用户也不懂如何写 Prompt 注入健康上下文。

核心链路是：移动端采集 HealthKit 数据 → 后端存储 + AI 上下文感知推理 → 前端评分与可视化。其中 AI 推理是最大亮点，本质是面向结构化时序数据的 RAG 变体，让大模型基于用户真实数据回答，而非泛泛而谈。

**薄弱点 / 改进方向**：
- 介绍时容易停留在"功能列表"层面 → 应主动强调 AI 架构亮点（双路 RAG）和工程权衡，体现技术深度。

---

### Q2: 你这个项目的 AI 部分和直接用 ChatGPT 有什么区别？

> **问题**：用户为什么不直接用 ChatGPT 问健康问题，你的项目有什么不可替代性？

**参考答案**：

三点本质区别，都体现在 `backend/app/services/ai/agent_runtime.py` 的 `run_chat()` 编排流程中：

1. **数据私有性**：ChatGPT 不知道用户的心率、睡眠、步数。我的项目在每次对话时，`context_builder.build_health_context()` 会从数据库按维度聚合查询（如心率取 7 天 AVG/MIN/MAX），格式化为 Markdown 注入 LLM 上下文。LLM 因此拥有精确数值依据而非模糊描述。

2. **知识专业性**：通用 ChatGPT 缺乏可信医学知识源。我集成了 Dify 知识库 RAG（`dify_retriever.retrieve_from_dify()`），用用户消息检索医学知识分段，注入 LLM 作为参考，并标注引用来源，前端可展开查看。

3. **可控性**：用户可自定义智能体（Agent），设定人设 Prompt 和数据访问范围（data_scope），实现"睡眠教练只看睡眠和心率"的最小权限控制，这是通用 AI 做不到的。

**薄弱点 / 改进方向**：
- 健康数据注入用的是聚合统计值（均值/极值），非原始时序点 → 改进可引入异常点检测，把异常片段直接喂给 LLM 做归因。
- Dify 知识库内容质量参差（测试结果显示 score=0 的无关结果也被返回） → 改进应在注入前做阈值过滤。

---

### Q3: 整个 AI 对话的完整链路是什么？从用户发消息到收到回复。

> **问题**：画一下或讲一下一次 AI 对话的完整数据流。

**参考答案**：

以同步 HTTP 接口 `POST /ai/chat` 为例（`backend/app/api/ai.py` + `agent_runtime.py`）：

```
用户发消息 message (+ session_id, agent_id)
  │
  ▼
[1] api/ai.py: chat() 接收请求，鉴权
  │
  ▼
[2] agent_runtime.run_chat():
    ├─ 加载/创建 ChatSession
    ├─ 若有 agent_id：加载 AIAgent 的 system_prompt + health_data_scope
    ├─ context_builder.build_health_context()  → 结构化数据 RAG
    │    关键词匹配 → 命中维度做聚合查询 → Markdown 上下文
    ├─ dify_retriever.retrieve_from_dify()     → 文档 RAG
    │    调用 Dify /retrieve API → 医学知识分段 → Markdown 上下文
    ├─ 加载历史消息（最近 20 条，时间正序）
    ├─ 构建 messages 列表：
    │    [system: 人设] + [system: 健康数据] + [system: 医学知识?] + [历史...] + [user: 本次消息]
    ├─ 保存用户消息（含 health_context_snapshot, dify_context_snapshot）
    ├─ provider = factory.get_provider()  → 单例获取 LLM Provider
    ├─ response_text = await provider.chat(messages)
    └─ 保存助手消息，更新 session.last_message_at
  │
  ▼
[3] 返回 { session_id, response, dify_references }
```

WebSocket 流式通道（`/ai/chat/ws`）流程类似，区别在于：流式逐 token 推送，结束时发 `done` 事件携带 `dify_references`，且流式失败自动降级为非流式。

**薄弱点 / 改进方向**：
- 历史消息固定取 20 条，无 token 预算管理 → 长对话可能超上下文窗口 → 改进应按 token 数动态截断。
- 上下文构建（两路 RAG）是串行的 → 改进可用 `asyncio.gather` 并行化，降低延迟。

---

### Q4: 为什么选 FastAPI 而不是 Django/Flask？技术选型理由。

> **问题**：后端技术选型的考量是什么？

**参考答案**：

三个核心考量：

1. **原生异步**：AI 应用大量 I/O 密集（调 LLM API、查数据库、调 Dify），FastAPI 基于 ASGI 原生 `async/await`，配合 `aiosqlite` 异步驱动，能高效处理并发。Django 的同步 ORM 会阻塞事件循环。

2. **流式输出友好**：WebSocket 流式推送 token 需要 async 语义，FastAPI 原生支持 `WebSocket` 端点和 `AsyncIterator`，我在 `provider_openai.py` 的 `stream_chat()` 用 `async for` 逐 token yield。

3. **类型安全 + 自动文档**：Pydantic v2 做 Schema 校验（`schemas/ai.py`），FastAPI 自动生成 Swagger 文档，AI 接口的请求/响应结构一目了然，便于前端联调。

Flask 也能做但需额外引入异步扩展，Django 太重且 ORM 同步阻塞不适合 LLM 高延迟场景。

**薄弱点 / 改进方向**：
- SQLite 单文件数据库并发写入能力弱 → 生产应换 PostgreSQL + asyncpg。
- 无连接池调优 → 高并发下 LLM API 调用可能打满 httpx 连接。

---

### Q5: 这个项目你最有成就感 / 最难的部分是什么？

> **问题**：讲一个你遇到的技术难点。

**参考答案**（建议讲双路 RAG 上下文构建的设计决策）：

最有成就感的是设计"结构化数据 RAG"这个非标准 RAG 变体。

传统 RAG 是文档向量化检索，但健康数据是结构化时序数据（心率采样点、睡眠时段），直接向量化的语义信息很弱。我的做法是在 `context_builder.build_health_context()` 中：先对用户消息做关键词匹配判断涉及的维度（如"睡眠"命中 sleep 关键词），再按维度做聚合查询（心率取 7 天 AVG/MIN/MAX、睡眠取每晚时长），最后格式化为 Markdown 注入 LLM。

难点在于权衡"注入多少数据"和"LLM 理解质量"：全量注入原始采样点会爆 token 且 LLM 难以归纳；只给统计量又可能丢失异常。最终选择聚合统计 + 异常极值的折中方案。

另外，Dify 文档 RAG 与结构化 RAG 的上下文如何组合也是个决策点：我选择以独立 system message 分别注入（人设 / 健康数据 / 医学知识），而非拼成一个大字符串，便于 LLM 区分来源。

**薄弱点 / 改进方向**：
- 关键词路由是硬编码 if/elif，语义覆盖差（"我心跳快"不命中 "heart"） → 改进可用 embedding 做语义路由，或用 LLM 做意图分类。
- 诚实承认这是弱点，反而能体现工程 maturity。

---

## 二、RAG 架构设计（Q6–Q9）

### Q6: 你项目里的 RAG 和标准 RAG 有什么区别？

> **问题**：讲讲你的 RAG 实现，和教科书里的 RAG 有什么不同？

**参考答案**：

标准 RAG 流程：文档分块 → 向量化 → 向量检索 → 拼接 Top-K 片段 → 喂 LLM。

我的项目是**双路 RAG**，其中"结构化数据 RAG"是非标准变体：

| 维度 | 标准 RAG | 我的结构化数据 RAG | 我的文档 RAG（Dify） |
|------|---------|-------------------|---------------------|
| 数据源 | 非结构化文档 | 结构化时序数据（DB 表） | 医学知识文档 |
| 检索方式 | 向量相似度 | 关键词路由 + SQL 聚合查询 | Dify hybrid_search |
| 检索粒度 | 文本块 | 聚合统计值（AVG/MIN/MAX/SUM） | 文本分段 |
| 上下文形式 | 原文拼接 | Markdown 格式化统计报告 | Markdown 分段 + 相关度分数 |

结构化数据 RAG 的核心在 `context_builder.py`：`include_all` 判断消息是否命中任何维度关键词，命中则只查相关维度，未命中则查全部（兜底）。每个维度的查询是定制化的——心率用 `func.avg/min/max`，睡眠取 `SleepSession` 记录逐条列出，步数用 `func.sum`。

这种设计的优势：检索结果精确（是真实数值而非模糊文本），token 消耗可控（聚合后数据量小），无需维护向量库。

**薄弱点 / 改进方向**：
- 关键词路由漏召回 → 见 Q26 详述。
- 未做 Rerank → Dify 结果可引入 reranking model 提升精度。
- 结构化 RAG 无法回答"我上周三晚上 11 点心率多少"这类精确点查询 → 改进可增加时间实体识别，支持精确时间范围查询。

---

### Q7: 你的两路 RAG 上下文是怎么组合注入 LLM 的？为什么这么设计？

> **问题**：健康数据上下文和 Dify 医学知识上下文，如何拼接到 prompt 里？

**参考答案**：

在 `agent_runtime.run_chat()` 中，messages 列表构造顺序如下（见 `agent_runtime.py:72-80`）：

```python
messages = [
    ChatMessage(role="system", content=system_prompt),          # [0] Agent 人设
    ChatMessage(role="system", content=f"User's Health Data:\n\n{health_context}"),  # [1] 健康数据
]
if dify_context:
    messages.append(ChatMessage(role="system", content=f"Medical Knowledge Reference:\n\n{dify_context}"))  # [2] 医学知识
for h in history_msgs:
    messages.append(ChatMessage(role=h.role, content=h.content))  # [3] 历史
messages.append(ChatMessage(role="user", content=message))        # [4] 本次消息
```

设计考量：
1. **分独立 system message 而非拼成一个字符串**：让 LLM 明确区分"用户数据"和"医学常识"两类信息源，降低混淆，也便于在 system prompt 中要求模型"区分个性化建议与通用医学知识"。
2. **健康数据在前、医学知识在后**：健康数据是本次对话最相关的个性化上下文，放更靠近历史的"工作记忆"位置；医学知识是辅助参考。
3. **历史消息正序**：`order_by(created_at.desc()).limit(20)` 取最近 20 条后 `reversed()`，保证时间正序，符合对话逻辑。

**薄弱点 / 改进方向**：
- 多个 system message 不是所有 LLM 都同等对待 → 部分模型会将后续 system 当 user 处理。改进可用单一 system + 明确分隔符，或测试目标模型行为。
- 没有对总 token 做预算 → 上下文 + 历史可能超窗口 → 见 Q27。

---

### Q8: Dify 知识库检索你是怎么集成的？检索失败怎么办？

> **问题**：讲讲 Dify RAG 的接入细节和容错。

**参考答案**：

集成在 `backend/app/services/ai/dify_retriever.py`：

**请求构造**（`retrieve_from_dify()`）：
- 端点：`POST {DIFY_API_BASE}/datasets/{DIFY_DATASET_ID}/retrieve`
- 鉴权：`Authorization: Bearer {DIFY_API_KEY}`
- Body：`query`（截断到 250 字符，Dify 限制）+ `retrieval_model`（search_method / top_k / score_threshold 等可配置）
- search_method 支持 `hybrid_search` / `semantic_search` / `keyword_search` / `full_text_search`，留空则用数据集默认配置

**响应处理**：
- `format_dify_context()`：把 records 格式化为 Markdown（`### [文档名] (relevance: 0.87)` + 内容），注入 LLM
- `parse_dify_records()`：提取结构化引用（文档名、分数、关键词、内容）返回前端展示

**容错设计（优雅降级）**：
- `DIFY_RETRIEVE_ENABLED=False` 时直接返回空列表
- API_KEY / DATASET_ID 缺失 → warning 日志 + 返回空
- `HTTPStatusError` / 任何 Exception → warning 日志 + 返回空列表
- 上游 `run_chat()` 对空 dify_context 不注入该 system message，对话正常进行

这意味着 Dify 挂了不影响核心对话功能，只是少了医学知识参考。

**薄弱点 / 改进方向**：
- score=0 的无关结果也被注入（测试结果可见） → 改进：在 `format_dify_context` 前按 `score > threshold` 过滤，或在 `DIFY_SCORE_THRESHOLD_ENABLED=True` 时让 Dify 服务端过滤。
- 无本地缓存 → 相似 query 重复检索浪费调用 → 改进可加 Redis 缓存 query→records。
- 超时 30s 偏长 → 改进可调短并加 circuit breaker。

---

### Q9: 检索质量你怎么评估和调优？

> **问题**：你怎么知道 RAG 检索出来的内容是好的？怎么调？

**参考答案**：

目前项目的检索质量评估方式：

1. **Dify 侧**：通过 `test_dify_rag.py` 脚本实测多个 query（高血压护理、糖尿病饮食、心率过快、心电图），观察返回 records 的 score 分布。测试结果显示：相关 query score 在 0.5–0.87 之间，无关结果 score=0。

2. **调优手段**（均通过 `config.py` 配置）：
   - `DIFY_SEARCH_METHOD`：从 semantic 切到 hybrid_search（语义+关键词混合）提升召回
   - `DIFY_RETRIEVE_TOP_K`：控制返回数量，平衡信息量与噪声
   - `DIFY_SCORE_THRESHOLD_ENABLED` + `DIFY_SCORE_THRESHOLD`：开启阈值过滤丢弃低分结果
   - `reranking_enable`（当前 False）：可开启 reranking 模型二次排序

3. **结构化数据 RAG 调优**：调整 `context_builder.py` 中各维度的关键词列表和聚合窗口（当前固定 7 天）。

**薄弱点 / 改进方向**：
- 缺乏自动化评估指标（如 faithfulness、answer relevance） → 改进可引入 RAGAS 等框架做离线评估。
- 没有 A/B 测试机制 → 改进可对不同检索配置做线上对比。
- 结构化 RAG 的关键词列表是硬编码，无法自适应 → 改进见 Q26。

---

## 三、Agent 智能体设计（Q10–Q12）

### Q10: 你的 Agent 和业界说的 Agent（如 ReAct、Function Calling Agent）有什么区别？

> **问题**：你项目里的"智能体"到底是不是真正的 Agent？

**参考答案**（诚实回答，体现认知深度）：

要诚实地说，我的 Agent **不是**业界说的自主决策型 Agent（如 ReAct 循环、Function Calling 工具调用型 Agent）。

我的 Agent 更准确说是**可定制的对话角色（Persona）**，体现在 `backend/app/models/ai.py` 的 `AIAgent` 表：
- `system_prompt`：自定义人设（如"你是睡眠教练"）
- `health_data_scope`：JSON 数组，限定可访问的数据维度（如 `["sleep", "heart_rate"]`）

`agent_runtime.run_chat()` 在加载 agent 后，把 `system_prompt` 作为首条 system message，把 `data_scope` 传给 `context_builder` 限定检索范围。

它不具备：工具调用（Function Calling）、多步推理循环（ReAct 的 Thought-Action-Observation）、自主规划。

之所以这样设计：健康问答场景下，用户需求相对明确（问数据 + 要建议），不需要复杂的多步工具编排。引入 ReAct 会增加延迟和 token 成本，收益有限。当前架构是"RAG + 角色定制"的务实选择。

**薄弱点 / 改进方向**：
- 可被追问"那如果要加 Function Calling 怎么做" → 答：在 `BaseLLMProvider` 接口扩展 `chat_with_tools()`，定义 tools schema（如 `query_heart_rate(range)`、`get_sleep_detail(date)`），让 LLM 自主决定调用哪个工具，后端执行后回填结果。这样能支持"帮我查上个月心率最高的那天"这类需要精确查询的复杂需求。
- `data_scope` 当前只影响关键词路由的 `all_types`，未在 SQL 层强制约束 → 见 Q28 安全性。

---

### Q11: Agent 的数据最小权限是怎么实现的？

> **问题**：你说 Agent 可以限制数据访问范围，具体怎么实现的？

**参考答案**：

数据流（`agent_runtime.py:44-55` + `context_builder.py:22-30`）：

1. 创建 Agent 时（`api/agents.py`），用户指定 `health_data_scope: list[str]`（如 `["sleep", "heart_rate"]`），存为 JSON 字符串。
2. 对话时 `run_chat()` 加载 agent，`json.loads(agent.health_data_scope)` 得到 `data_scope`。
3. 传给 `build_health_context(db, user_id, message, data_scope)`。
4. 在 `context_builder` 中，`all_types = data_scope or [全部维度]`，每个维度的查询前都有 `if "heart_rate" in all_types` 这样的判断，不在 scope 内的维度直接跳过，不查数据库也不注入上下文。

效果：一个"睡眠教练"Agent 即使被问到"我的心率多少"，也不会返回心率数据（因为 `heart_rate` 不在 scope）。

**薄弱点 / 改进方向**：
- **这是逻辑层约束，非强制安全边界**：如果未来有人绕过 `context_builder` 直接查库，scope 不生效。改进：在 service 层做权限校验，或在 SQL 查询的 WHERE 条件中硬性过滤 scope。
- `include_all`（消息未命中任何关键词时查全部）会忽略 scope：当 `include_all=True` 时，`if "heart_rate" in all_types or include_all` 这个条件里 `include_all` 短路了 scope 检查 → **这是一个真实 bug**，scope 在 include_all 场景下失效。改进：改为 `if ("heart_rate" in all_types) and (include_all or <命中关键词>)`。

---

### Q12: 多个 Agent 之间会协作吗？能实现多 Agent 编排吗？

> **问题**：你的系统能不能让多个 Agent 协作完成复杂任务？

**参考答案**：

当前不支持多 Agent 协作。每个对话会话（`ChatSession`）绑定单一 `agent_id`（可空，用默认 Prompt），一次对话全程使用同一 Agent 的人设和 scope。

如果要扩展为多 Agent 编排，架构演进路径：

1. **Router Agent 模式**：在 `run_chat` 前加一个轻量路由 Agent，用 LLM 判断用户问题归属哪个专业 Agent（睡眠 / 心脏 / 运动），再转发给对应 Agent 处理。成本低，但只能串行单跳。

2. **Supervisor-Worker 模式**：一个 Supervisor Agent 拆解任务，并行调用多个 Worker Agent（每个有独立 scope），汇总结果。需要引入 Agent 间消息传递机制和结果合并逻辑。

3. **LangGraph 式状态图**：定义 Agent 为节点，边为条件转移，支持循环和人工介入。

考虑到健康问答场景任务复杂度，当前单 Agent + 双路 RAG 已能满足需求，多 Agent 会显著增加延迟和成本。

**薄弱点 / 改进方向**：
- 当前连 Agent 切换都做不到（会话绑定后不可变） → 改进可在对话中支持动态切换 agent_id。
- 无 Agent 间共享上下文机制 → 多 Agent 场景需要设计共享黑板（blackboard）模式。

---

## 四、Prompt 工程（Q13–Q15）

### Q13: 你的 System Prompt 是怎么设计的？考虑了哪些点？

> **问题**：讲讲你的 system prompt 设计思路。

**参考答案**：

默认 system prompt 定义在 `agent_runtime.py:13-22`：

```
You are SyncHealth AI, a knowledgeable and friendly health assistant.
You analyze the user's Apple Watch health data to provide insights,
answer health-related questions, and suggest improvements.
When medical knowledge references are provided, use them to give more
accurate and professional answers, but always clearly distinguish between
general medical knowledge and personalized health advice.
Always be supportive and remind users to consult healthcare professionals
for medical advice. Respond in the same language the user uses.
```

设计考量：
1. **身份与能力边界**：明确是"健康助手"，分析 Apple Watch 数据，避免越界做诊断。
2. **多源信息区分**：明确要求区分"通用医学知识"和"个性化健康建议"，对应双路 RAG 的两路上下文。
3. **医疗免责声明**：提醒咨询专业医生，降低法律风险（健康领域关键）。
4. **多语言跟随**：用用户语言回复，支持中英文用户。
5. **可覆盖**：Agent 可自定义 `system_prompt` 完全替换默认值，实现角色定制。

**薄弱点 / 改进方向**：
- Prompt 是英文，但要求"用用户语言回复" → 中文用户可能受英文 prompt 影响输出风格。改进：可做 prompt 本地化，或强化"严格跟随用户语言"指令。
- 无 Few-shot 示例 → 改进可加入 1-2 个问答示例引导输出格式（如"用 Markdown 分点回答"）。
- 无输出格式约束 → 答案结构不可控。改进可用 structured output / JSON mode。

---

### Q14: 为什么用多个 system message 而不是拼成一个？不同 LLM 对此处理一样吗？

> **问题**：你把人设、健康数据、医学知识分成三个 system message，有什么考量？

**参考答案**：

设计理由（见 Q7 代码）：
1. **语义分离**：让 LLM 明确这是三类不同来源的信息，降低混淆。
2. **可条件注入**：`dify_context` 为空时不追加第三个 system message，避免空上下文干扰。
3. **可追溯**：每个 system message 的内容独立保存在 `health_context_snapshot` / `dify_context_snapshot`，便于调试。

**不同 LLM 的差异**（重要认知）：
- **OpenAI 系（GPT-4o）**：支持多个 system message，会按顺序拼接理解，效果如预期。
- **部分开源模型 / 国内模型**：可能只认第一个 system message，或把后续 system 当 user 处理，导致上下文丢失。
- **DeepSeek / Ollama（OpenAI 兼容接口）**：行为取决于具体实现，需测试。

**薄弱点 / 改进方向**：
- 跨模型兼容性风险 → 改进方案：检测模型类型，对不兼容多 system 的模型，拼接成单一 system message（用明确分隔符如 `===` 区分段落）。
- 没有做模型行为测试 → 应针对目标模型做 A/B 对比。

---

### Q15: 历史消息你是怎么管理的？长对话会不会有问题？

> **问题**：多轮对话的上下文你怎么处理？

**参考答案**：

当前实现（`agent_runtime.py:63-69`）：

```python
history_result = await db.execute(
    select(ChatMessageModel)
    .where(ChatMessageModel.session_id == session.id)
    .order_by(ChatMessageModel.created_at.desc())
    .limit(20)
)
history_msgs = list(reversed(history_result.scalars().all()))
```

策略：取最近 20 条消息，倒序取再正序还原，拼到 system message 之后、当前 user 消息之前。

**问题**：
1. **无 token 预算**：20 条消息若每条几百字，加上健康上下文 + 医学知识，很容易超 8K context（`AI_MAX_CONTEXT_TOKENS=8000`）。
2. **无摘要压缩**：长对话会丢失早期上下文，且无摘要机制。
3. **无优先级**：所有历史平等对待，未区分关键信息。

**薄弱点 / 改进方向**：
- 引入 token 计数（tiktoken）动态截断 → 保留最近 N 条直到接近预算上限。
- 滑动窗口 + 摘要：超过窗口时把早期对话用 LLM 生成摘要，作为 system message 注入。
- 关键信息提取：从历史中抽取健康数据实体（如"用户提到有高血压"）持久化为 user profile，每轮注入。

---

## 五、LLM 工程化（Q16–Q19）

### Q16: 你的多 LLM Provider 是怎么设计的？工厂模式具体怎么用？

> **问题**：讲讲你怎么支持多个大模型的切换。

**参考答案**：

三层设计：

**1. 抽象基类**（`backend/app/services/ai/base.py`）：
```python
class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages, config) -> str: ...        # 同步完成
    @abstractmethod
    async def stream_chat(self, messages, config) -> AsyncIterator[str]: ...  # 流式
    @abstractmethod
    def get_model_info(self) -> ModelInfo: ...                 # 模型元信息
```
还定义了 `ChatMessage`（role + content）、`GenerationConfig`（temperature/max_tokens/top_p）、`ModelInfo` 数据类。

**2. 工厂模式**（`factory.py`）：
```python
_provider_instance: BaseLLMProvider | None = None  # 模块级单例

def get_provider() -> BaseLLMProvider:
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance
    provider_type = settings.AI_PROVIDER
    if provider_type == "openai":
        _provider_instance = OpenAIProvider()
    elif provider_type == "local":      # Ollama
        _provider_instance = OpenAIProvider()
    elif provider_type == "domestic":   # DeepSeek
        _provider_instance = OpenAIProvider()
    ...
    return _provider_instance
```
单例避免重复创建，`reset_provider()` 用于测试时重置。

**3. 具体实现**（`provider_openai.py`）：用 `httpx.AsyncClient` 调 OpenAI 兼容的 `/chat/completions` 接口。

**设计意图**：上层 `agent_runtime` 只依赖 `BaseLLMProvider` 抽象，不关心具体实现，符合依赖倒置原则。新增 Provider（如 Anthropic）只需实现基类 + 在工厂注册。

**薄弱点 / 改进方向**：
- **名不副实**：所有分支都返回 `OpenAIProvider`，因为 DeepSeek/Ollama 都兼容 OpenAI 接口。面试官可能追问"那策略模式体现在哪" → 诚实回答：当前是"OpenAI 协议兼容"假设下的简化，真正多协议（如 Anthropic 原生 API）需独立实现 Provider 类。
- 单例在多配置切换时需手动 reset → 改进可用配置版本号判断是否重建。
- `get_model_info()` 硬编码 `max_context_window=128000` → 应按模型动态查询。

---

### Q17: 策略模式在你项目里体现在哪？

> **问题**：除了工厂模式，还用了哪些设计模式？

**参考答案**：

策略模式体现在 Provider 的可互换性：`OpenAIProvider` 是 `BaseLLMProvider` 接口的一个策略实现。理论上 `agent_runtime` 调用 `provider.chat(messages)` 时，不关心背后是 OpenAI、DeepSeek 还是 Ollama，只要实现同一接口即可互换。

但因为所有 Provider 当前都是 `OpenAIProvider`，策略模式的"多实现"尚未真正体现。要让它名副其实，应：
- `provider_deepseek.py`：DeepSeek 原生 API（若有差异）
- `provider_anthropic.py`：Claude 原生 API（messages 格式不同）
- `provider_ollama.py`：本地模型（可能有流式协议差异）

**其他设计模式**：
- **仓储模式（Service 层）**：`services/` 封装业务逻辑，`api/` 只做路由转发，数据访问通过 SQLAlchemy Session。
- **依赖注入**：FastAPI 的 `Depends(get_db)` / `Depends(get_current_user)` 贯穿全局。

**薄弱点 / 改进方向**：
- 策略模式未真正落地 → 若面试强调，可现场说"如果要支持 Anthropic，我会新增 Provider 类并在 factory 注册"。
- 工厂是简单工厂（if-else），扩展时需改工厂代码 → 改进可用注册表模式（dict 映射 type→class），开闭原则更友好。

---

### Q18: 调用 LLM API 失败了怎么处理？有重试吗？

> **问题**：LLM 调用的健壮性怎么保证的？

**参考答案**：

当前容错机制：

1. **流式降级**（`api/ai.py:113-121`）：
```python
try:
    async for chunk in provider.stream_chat(messages):
        full_response += chunk
        await websocket.send_text(...)
except Exception:
    if not full_response:  # 流式完全没产出才降级
        full_response = await provider.chat(messages)  # 退回非流式
        await websocket.send_text(...)
```

2. **Dify 降级**（`dify_retriever.py`）：任何异常返回空列表，不影响主流程。

3. **httpx 超时**：同步 60s，流式 120s。

**缺失的健壮性**（诚实承认）：
- **无重试机制**：LLM API 429（限流）/ 5xx 应做指数退避重试。
- **无熔断**：连续失败应熔断避免雪崩。
- **无超时分级**：连接超时 / 读取超时未区分。

**薄弱点 / 改进方向**：
- 引入 `tenacity` 做重试（exponential backoff，针对 429/5xx）。
- 引入 circuit breaker（如 `pybreaker`），连续 N 次失败后熔断 M 秒。
- 流式断连无断点续传 → 改进可记录已发送 token 偏移，重连后从断点续传（但 LLM 流式不支持续传，只能整体重试）。
- WebSocket 断连后客户端无重连机制 → 前端应实现自动重连 + 消息补发。

---

### Q19: 你怎么控制 LLM 的生成参数？temperature 等怎么选？

> **问题**：生成配置是怎么管理的？

**参考答案**：

配置层级（`base.py` + `config.py` + `provider_openai.py`）：

`GenerationConfig` 数据类定义可调参数：
```python
@dataclass
class GenerationConfig:
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 1.0
    stop_sequences: list[str] = field(default_factory=list)
```

实际取值：`config.py` 的 `AI_TEMPERATURE=0.7`，在 `provider_openai._build_body()` 中 `cfg = config or GenerationConfig(temperature=settings.AI_TEMPERATURE)`。

**temperature=0.7 的选择理由**：健康问答需要一定创造性（个性化建议）但不能太发散（避免编造医学信息），0.7 是平衡点。如果是纯事实查询应降到 0.2-0.3。

**薄弱点 / 改进方向**：
- `GenerationConfig` 当前未真正使用——`run_chat` 调用 `provider.chat(messages)` 没传 config，走默认值 → 改进应让 Agent 可配置自己的 generation 参数。
- `max_tokens=2048` 偏小，复杂分析可能被截断 → 改进可调大或动态调整。
- 无 stop sequences → 改进可设置 `["User:", "Assistant:"]` 防止模型续写下一条对话。
- 不同任务应用不同参数（事实查询低 temp，建议生成高 temp）→ 改进可按消息意图动态调参。

---

## 六、流式输出（Q20–Q22）

### Q20: WebSocket 流式输出是怎么实现的？讲讲 SSE 解析。

> **问题**：流式 token 推送具体怎么做的？

**参考答案**：

**后端流式产生**（`provider_openai.py:44-66`）：

```python
async def stream_chat(self, messages, config) -> AsyncIterator[str]:
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", f"{base_url}/chat/completions",
                                  headers=..., json=...(stream=True)) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                chunk = json.loads(data_str)
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield content
```

SSE 解析要点：
1. OpenAI 流式返回 `data: {JSON}\n\n` 格式，每行一个 chunk。
2. `line.startswith("data: ")` 过滤非数据行（如空行、注释）。
3. `[DONE]` 标记流结束。
4. `delta.content` 是增量 token，逐个 yield 给上层。
5. `json.JSONDecodeError` 等异常静默跳过（容错不完整 chunk）。

**WebSocket 推送**（`api/ai.py:114-139`）：
```python
async for chunk in provider.stream_chat(messages):
    full_response += chunk
    await websocket.send_text(json.dumps({"type": "token", "content": chunk}))
# 结束发 done 事件
await websocket.send_text(json.dumps({"type": "done", "session_id":..., "dify_references":...}))
```

前端收到 `type:"token"` 逐个拼接，`type:"done"` 结束并展示引用。

**薄弱点 / 改进方向**：
- 无心跳保活 → 长时间无 token 时连接可能被中间代理断开 → 改进定期发 ping。
- `full_response` 在内存累积，超长回复可能 OOM → 一般可接受，但需监控。
- 前端 `AIChatView.vue` 当前实际用的是 HTTP 同步（store.sendMessage），WebSocket 通道未在前端启用 → 改进应前端接入 WS 实现真流式体验。

---

### Q21: 流式失败怎么降级？降级后用户体验如何？

> **问题**：流式中途挂了怎么办？

**参考答案**：

降级逻辑（`api/ai.py:113-121`）：

```python
full_response = ""
try:
    async for chunk in provider.stream_chat(messages):
        full_response += chunk
        await websocket.send_text(json.dumps({"type": "token", "content": chunk}))
except Exception:
    if not full_response:  # 只有完全没产出才降级
        full_response = await provider.chat(messages)  # 同步整包
        await websocket.send_text(json.dumps({"type": "token", "content": full_response}))
```

**降级策略**：
- **完全没产出**（`not full_response`）：退回同步 `provider.chat()`，一次性返回完整内容，用户感觉"等了一会突然全出来"。
- **已产出部分**（`full_response` 非空）：不降级，保留已发送部分，用户看到半截回答——这是当前实现的一个问题。

**薄弱点 / 改进方向**：
- 半截回答场景未处理 → 改进：流式中断后，用已产出内容作为 prefix，调用非流式 `chat()` 续写（需 LLM 支持 prefix，或重新生成整段）。
- 降级调用同样可能失败 → 应再加 try/except 返回友好错误。
- 无断线重连 → 前端 WebSocket 断了无法恢复，改进见 Q18。
- 用户体验：降级后从"逐字"变"整块"，体感差异大 → 可加 loading 动画过渡。

---

### Q22: 为什么同时提供 HTTP 和 WebSocket 两种接口？

> **问题**：两种通道各有什么适用场景？

**参考答案**：

| 维度 | HTTP `POST /ai/chat` | WebSocket `/ai/chat/ws` |
|------|---------------------|------------------------|
| 体验 | 等待完整响应一次性返回 | 逐 token 实时推送 |
| 首字节延迟 | 高（等整段生成） | 低（首个 token 即推） |
| 适用场景 | 简单查询、API 集成、CORS 受限 | 交互式对话、长回复 |
| 鉴权 | Header Bearer token | query param token |
| 状态 | 无状态，每次带 session_id | 长连接，多轮复用 |

**设计理由**：
1. **兼容性**：部分环境（企业代理、旧浏览器）WebSocket 受限，HTTP 兜底。
2. **灵活性**：API 集成方可能只需完整结果，不必维持长连接。
3. **渐进增强**：HTTP 是基础能力，WebSocket 是体验增强。

**薄弱点 / 改进方向**：
- WebSocket 鉴权用 query param token → token 会出现在日志/代理记录中，有泄露风险 → 改进用首条消息鉴权或 Sec-WebSocket-Protocol header。
- WebSocket 无 token 刷新 → 长连接 token 过期后无法续期 → 改进支持连接内刷新。
- 两个接口的上下文构建逻辑重复（`api/ai.py` 的 ws 分支手写了 run_chat 的流程） → 改进应抽取公共编排函数，避免维护两份逻辑。

---

## 七、数据工程（Q23–Q25）

### Q23: HealthKit 数据同步怎么去重的？为什么这么设计？

> **问题**：11 种健康数据批量上传，如何保证不重复？

**参考答案**：

去重在 `backend/app/services/sync_service.py`：

**简单表**（`_bulk_insert_simple()`）：每条数据带 `sample_uuid`（来自 HealthKit），插入前 `SELECT ... WHERE user_id=? AND sample_uuid=?` 查重，存在则跳过（`deduplicated += 1`），否则 `db.add()`。

**嵌套表**（`_insert_sleep_sessions()` / `_insert_workout_records()`）：父记录按 uuid 去重后 `flush()` 拿到 id，再级联插入子记录（SleepStage / WorkoutHRZone），子记录随父记录唯一性保证不重复。

**设计理由**：
1. HealthKit 的 `sample_uuid` 是设备侧全局唯一标识，天然适合做幂等键。
2. 应用层查重而非 DB 唯一约束 → 灵活控制（可统计去重数）+ 避免 INSERT 冲突异常中断批量。
3. `SyncLog` 记录每次同步的 received/inserted/deduplicated 计数，可观测。

**薄弱点 / 改进方向**：
- **N+1 查询**：每条数据一次 SELECT，大批量同步性能差 → 改进：批量预查 `SELECT sample_uuid FROM ... WHERE sample_uuid IN (...)`，内存去重；或用 `INSERT ... ON CONFLICT DO NOTHING`（SQLite UPSERT，代码中已 import `sqlite_insert` 但未使用）。
- **无事务边界**：部分失败时已插入数据不回滚 → 改进应在 `process_sync_upload` 包整体事务。
- **无并发同步控制**：同一用户多次并发上传可能重复处理 → 改进加分布式锁或同步队列。

---

### Q24: 健康评分算法是怎么设计的？为什么用这些权重？

> **问题**：讲讲你的四维评分逻辑。

**参考答案**：

算法在 `dashboard_service.py:get_health_score()`，7 天窗口四维加权：

| 维度 | 权重 | 满分条件 | 扣分逻辑 |
|------|------|---------|---------|
| 活动 | 0.30 | 日均 10000 步 | 线性 `(avg_steps/10000)*100` |
| 睡眠 | 0.30 | 7-9 小时/晚 | <7 线性扣；>9 按 `(h-9)*20` 扣 |
| 心脏 | 0.25 | 静息心率 50-70 | <50 按 `(50-hr)*5` 扣；>70 按 `(hr-70)*3` 扣 |
| 生命体征 | 0.15 | SpO2 接近 100% | ≥90 按 `(spo2/100)*105`；<9 按 `(spo2/90)*50` |

总分 = 加权求和。

**权重设计理由**：活动和睡眠各 0.3（对日常健康影响最大且可干预），心脏 0.25（重要但部分不可控），生命体征 0.15（相对稳定，异常才扣分）。

**SQLite 兼容性处理**（`dashboard_service.py:168-182`）：活动分需"日均步数"，但 SQLite 嵌套聚合不兼容，所以两步查询：先 `GROUP BY date` 查每日总步数，再 Python 求平均。

**薄弱点 / 改进方向**：
- 评分阈值是经验值，无医学循证 → 改进可参考 WHO / AHA 指南，或做成可配置。
- 无个体化基线 → 改进可基于用户历史数据建立个人基线，相对偏差评分。
- 线性扣分过于简单 → 改进可用分段函数或 S 型曲线。
- 权重固定 → 改进可按用户画像（如老年人调高心脏权重）动态调整。

---

### Q25: 聚合查询性能怎么样？数据量大会有问题吗？

> **问题**：`context_builder` 和 `dashboard` 大量聚合查询，性能如何？

**参考答案**：

当前查询特点：
- `context_builder`：每个维度 1 次聚合查询（AVG/MIN/MAX/SUM），7 天窗口。
- `dashboard` 趋势：`get_dashboard_trends` 是 **N+1 查询**——`for day_offset in range(days)` 每天每维度一次查询，30 天就是 30×5=150 次查询。

**性能现状**：SQLite 单机 + 数据量小（个人 7-90 天数据），当前无感知延迟。

**数据量增大后的问题**：
1. N+1 查询线性增长 → 90 天趋势 450 次查询，显著变慢。
2. SQLite 并发写入弱 → 多用户同时同步 + 查询会锁库。
3. 无索引优化复核 → `user_id` 有索引，但 `recorded_at` 范围查询可能未走复合索引。

**薄弱点 / 改进方向**：
- **趋势查询批量化**：改为 `GROUP BY date(recorded_at)` 一次查出所有天，Python 侧组装 → 从 N×M 次降到 M 次。
- **预聚合**：每日跑定时任务预计算日维度统计，存入聚合表，查询直接读聚合表。
- **换 PostgreSQL**：支持并发、窗口函数、物化视图。
- **加复合索引**：`(user_id, recorded_at)` 复合索引加速范围查询。
- **缓存**：dashboard 数据变化慢，可加 Redis 缓存（TTL 5-15 分钟）。

---

## 八、系统设计与深度追问（Q26–Q30）

### Q26: 你的关键词路由有什么局限性？怎么改进？

> **问题**：`context_builder` 用关键词匹配决定查哪些数据，这样有什么问题？

**参考答案**：

**局限性**（`context_builder.py:27-30`）：

```python
include_all = not any(kw in msg_lower for kw in [
    "heart", "sleep", "step", "workout", "exercise", "oxygen", "spo2", ...
])
```

1. **漏召回**：用户说"我心跳快"不包含 "heart"/"hr"/"pulse"/"bpm"，不命中 → 查全部维度（兜底），虽不丢数据但浪费 token。
2. **误召回**：用户说"keep步数"含 "step"，但问的是 app 不是步数数据。
3. **多语言**：中文"睡眠"不在关键词列表（只有英文 "sleep"）→ 中文用户全走 include_all 兜底。
4. **同义词覆盖不全**：如"脉搏""心跳""resting"未全覆盖。
5. **无法理解意图**：纯字符串匹配，无语义理解。

**改进方案（按成本递增）**：

1. **扩充关键词词典**（低成本）：加中文关键词、同义词，维护一个映射表。简单但维护成本高，仍漏语义。

2. **Embedding 语义路由**（中成本）：预定义各维度的描述 embedding（如"心率相关：心跳、脉搏、bpm、心律..."），用户消息 embedding 后算相似度，超阈值则命中。能处理"我心跳快"。

3. **LLM 意图分类**（高成本但最准）：用小模型（如 GPT-4o-mini）做一次意图分类，输出涉及的维度列表。准确但增加一次 LLM 调用延迟。

4. **Function Calling**（架构升级）：定义 `query_heart_rate` / `query_sleep` 等工具，让 LLM 自主决定调用哪个，最灵活但复杂度高。

**我的选择**：当前是 MVP 阶段的快速实现，若上线我会先用方案 1 兜底中文，再逐步引入方案 2。

---

### Q27: 你怎么管理 token 预算？长对话超窗口怎么办？

> **问题**：上下文 + 历史 + 知识可能超 LLM 窗口，你怎么处理？

**参考答案**：

**当前现状**：无 token 预算管理。`AI_MAX_CONTEXT_TOKENS=8000` 配置存在但代码中未使用。历史固定 20 条，加上健康上下文 + Dify 知识（5 条分段，每条几百字），很容易超 8K。

**改进方案**：

1. **Token 计数**：用 `tiktoken`（OpenAI）或模型对应 tokenizer 精确计数每段内容。

2. **预算分配**：
   - System prompt（人设）：固定 ~200 token
   - 健康上下文：预留 ~1000 token
   - Dify 知识：预留 ~2000 token（top_k 动态调）
   - 历史消息：剩余预算，从最近往前填充
   - 当前消息 + 回复：预留 ~2000 token

3. **历史压缩**：
   - 滑动窗口：保留最近 N 条直到预算耗尽。
   - 摘要压缩：超出窗口的历史用 LLM 生成摘要，作为 system message 注入（"之前对话要点：用户有高血压史，关心睡眠质量"）。
   - 关键信息抽取：从历史提取健康实体持久化到 user profile。

4. **动态 top_k**：Dify 检索结果按 score 排序，按剩余预算动态决定注入几条。

**薄弱点 / 改进方向**：
- 当前完全没做，是最大工程债之一 → 面试时诚实承认，重点讲改进思路体现能力。
- 摘要压缩本身消耗 LLM 调用 → 可异步预生成（每 10 轮触发一次摘要）。

---

### Q28: 健康数据是敏感信息，你怎么保证安全和隐私？

> **问题**：健康数据属于敏感 PII，你的项目做了哪些安全措施？还缺什么？

**参考答案**：

**已实现的安全措施**：
1. **JWT 鉴权**：`core/security.py` 生成 access/refresh token，`get_current_user` 依赖注入校验，所有 API 需带 token。
2. **数据隔离**：所有查询 `WHERE user_id = current_user.id`，用户只能看自己的数据。
3. **密码哈希**：bcrypt 单向哈希，不存明文。
4. **WebSocket 鉴权**：连接时校验 token（虽用 query param 有风险）。
5. **Agent 归属校验**：`agent_runtime` 加载 agent 时校验 `agent.user_id == user_id`。

**缺失的安全措施**（诚实承认）：
1. **无 PII 脱敏**：健康数据明文存 SQLite，明文传给 LLM（第三方 API）→ 这是最大风险。改进：传给 LLM 前脱敏（如心率保留数值但去掉时间戳关联），或用本地模型。
2. **无传输加密**：当前 HTTP，生产必须 HTTPS。
3. **无数据加密存储**：SQLite 文件明文 → 改进用 SQLCipher 或字段级加密。
4. **SECRET_KEY 硬编码默认值**：`config.py:14` `"dev-secret-key-change-in-production"` → 生产必须改 + 从环境变量读。
5. **data_scope 非强制安全边界**：见 Q11，逻辑层约束可被绕过。
6. **无审计日志**：谁查了谁的数据无记录 → 改进加 access log。
7. **无内容安全过滤**：用户可输入 prompt injection → 改进做输入过滤 + 输出审核。

**薄弱点 / 改进方向**：
- 传输给 LLM 的数据脱敏是合规关键（GDPR / HIPAA）→ 可探索联邦学习或本地部署模型。
- WebSocket token query param 风险 → 改用 header。

---

### Q29: 如果用户量从 1 个涨到 10 万，你的架构要怎么改？

> **问题**：系统扩展性如何？瓶颈在哪？

**参考答案**：

**当前瓶颈分析**：

1. **数据库**：SQLite 单文件，写锁全库级别，多用户并发同步会锁库。
2. **LLM 调用**：单进程 async，无队列，高并发打满 LLM API 限流。
3. **内存**：流式 `full_response` 累积，大量并发连接 OOM。
4. **无缓存**：dashboard 聚合查询每次重算。

**扩展改造路径**：

| 层级 | 当前 | 改造 |
|------|------|------|
| 数据库 | SQLite 单文件 | PostgreSQL + 读写分离 + 连接池 |
| 部署 | 单进程 uvicorn | 多 worker + 负载均衡（Nginx） |
| LLM 调用 | 同步 await | 消息队列（Redis/Celery）异步处理 + 限流 |
| 缓存 | 无 | Redis 缓存 dashboard 聚合 + Dify 检索结果 |
| WebSocket | 单机内存 | Redis Pub/Sub 支持多实例广播 |
| 流式 | 内存累积 | 限制单连接最大 token + 超时清理 |
| 数据同步 | 应用层去重 | DB 唯一约束 + 批量 UPSERT |
| 监控 | 无 | Prometheus + Grafana（延迟/错误率/token 消耗） |

**优先级**：
1. 换 PostgreSQL（解锁并发）
2. 加 Redis 缓存 + 队列（降 DB 和 LLM 压力）
3. 多实例 + 负载均衡（水平扩展）
4. 监控告警（可观测性）

**薄弱点 / 改进方向**：
- 当前完全没考虑扩展性，是学习项目 → 诚实说明，重点讲改造思路。
- LLM 成本是隐形瓶颈 → 10 万用户每人日均 10 轮，token 成本巨大 → 改进：缓存常见问题答案、用小模型兜底、按用户分级限流。

---

### Q30: 如果让你重新做这个项目，你会怎么改进？

> **问题**：回顾整个项目，你觉得最大的不足和改进优先级是什么？

**参考答案**：

按优先级排序的改进项：

**P0（必须改）**：
1. **token 预算管理**（Q27）——当前长对话必崩，是功能性缺陷。
2. **data_scope 的 include_all bug**（Q11）——权限边界失效，安全问题。
3. **关键词路由加中文支持**（Q26）——中文用户当前全走兜底，体验差。

**P1（应该改）**：
4. **Dify 结果阈值过滤**——score=0 的垃圾结果污染上下文。
5. **换 PostgreSQL**——SQLite 并发瓶颈。
6. **流式中断处理**——半截回答问题（Q21）。
7. **前端接入 WebSocket 真流式**——当前前端用 HTTP，WS 通道空置。

**P2（可以改）**：
8. **引入 Function Calling**——支持精确点查询"上周三心率"。
9. **RAG 评估体系**——RAGAS 离线评估 + 线上 A/B。
10. **历史摘要压缩**——长对话上下文管理。
11. **多 Provider 真正落地**——策略模式名副其实。
12. **安全加固**——PII 脱敏、HTTPS、审计日志。

**架构级反思**：
- 应该从一开始就引入 token 计数和预算管理，而非事后补。
- 双路 RAG 的上下文组合应做模型兼容性测试，而非假设多 system message 通用。
- Agent 的 data_scope 应是 SQL 层强制约束，而非逻辑层 if 判断。

**面试话术**：这些不足我都有清晰认知，如果是生产项目我会按 P0→P1→P2 依次解决。项目作为 MVP 验证了双路 RAG 的可行性，工程化改进有明确路径。

---

## 附录：薄弱点速查表

> 面试官追问时，主动承认弱点 + 给出改进方案，比掩饰更能体现工程 maturity。

| # | 薄弱点 | 所在文件 | 风险等级 | 改进方向 |
|---|--------|---------|---------|---------|
| 1 | 关键词路由硬编码，无中文支持 | `context_builder.py:27-30` | 高 | 扩充词典 → embedding 语义路由 |
| 2 | 无 token 预算管理，长对话超窗口 | `agent_runtime.py:63-69` | 高 | tiktoken 计数 + 滑动窗口 + 摘要 |
| 3 | data_scope 在 include_all 时失效 | `context_builder.py:34` | 高 | 修正条件为 `in scope and (include_all or hit)` |
| 4 | Dify score=0 结果未过滤 | `dify_retriever.py` | 中 | format 前按 threshold 过滤 |
| 5 | 工厂所有分支返回同一 Provider | `factory.py:14-27` | 中 | 实现独立 Provider 类 |
| 6 | 流式中断半截回答不处理 | `api/ai.py:113-121` | 中 | 续写或重新生成 |
| 7 | 多 system message 跨模型兼容性 | `agent_runtime.py:72-80` | 中 | 检测模型，不兼容时拼接 |
| 8 | 无 LLM 调用重试/熔断 | `provider_openai.py` | 中 | tenacity + circuit breaker |
| 9 | 数据同步 N+1 查询 | `sync_service.py:36-44` | 中 | 批量预查 / UPSERT |
| 10 | dashboard 趋势 N+1 查询 | `dashboard_service.py:99-160` | 中 | GROUP BY 批量查 |
| 11 | SQLite 并发瓶颈 | `config.py:11` | 中 | 换 PostgreSQL |
| 12 | 无 PII 脱敏，明文传 LLM | 全局 | 高 | 脱敏 / 本地模型 |
| 13 | SECRET_KEY 默认硬编码 | `config.py:14` | 高 | 强制环境变量 |
| 14 | WebSocket token 在 query param | `api/ai.py:40` | 中 | 改 header / 首消息鉴权 |
| 15 | 无缓存 | 全局 | 中 | Redis 缓存聚合 + 检索 |
| 16 | 前端未接入 WebSocket 真流式 | `AIChatView.vue` | 低 | store 改用 WS |
| 17 | 历史固定 20 条无压缩 | `agent_runtime.py:67` | 中 | 摘要压缩 + profile 提取 |
| 18 | 无 RAG 质量评估 | 全局 | 中 | RAGAS + A/B 测试 |
| 19 | 无监控告警 | 全局 | 中 | Prometheus + Grafana |
| 20 | system prompt 无 few-shot | `agent_runtime.py:13-22` | 低 | 加输出格式示例 |

---

## 面试应答策略建议

1. **先讲架构再讲细节**：被问"怎么实现的"先画链路图，再深入代码。
2. **主动暴露弱点**：在合适时机说"这里有个权衡/不足"，掌控追问节奏。
3. **用代码路径背书**：说"在 `context_builder.py` 的 `build_health_context` 函数里"，体现真实编码。
4. **准备改进方案**：每个弱点都要能说出 2-3 个改进方向，按成本排序。
5. **区分"做了什么"和"为什么"**：面试官更看重决策理由，如"为什么用多 system message 而非拼接"。
6. **诚实不装**：不知道的说"当前没做，但我的思路是..."，比硬编强。

---

*本手册基于 SyncHealth 项目真实代码编写，建议结合源码复习，确保能现场白板画出 AI 对话链路图。*
