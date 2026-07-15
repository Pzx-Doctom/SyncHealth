<p align="center">
  <h1 align="center">SyncHealth</h1>
  <p align="center">
    <strong>AI 驱动的个人健康数据同步与分析全栈平台</strong>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square" />
    <img src="https://img.shields.io/badge/Frontend-Vue3-4FC08D?style=flat-square" />
    <img src="https://img.shields.io/badge/Mobile-React_Native-61DAFB?style=flat-square" />
    <img src="https://img.shields.io/badge/AI-OpenAI-412991?style=flat-square" />
  </p>
</p>

---

## 项目简介

SyncHealth 是一个**三端协同**的健康数据平台，通过 Apple HealthKit 采集可穿戴设备数据，利用 **AI 上下文感知推理** 让大模型真正"理解"你的身体状况，并提供个性化健康建议。

```
Apple Watch / HealthKit                    AI 推理
       │                                     │
       ▼                                     ▼
  ┌──────────┐    ┌──────────────┐    ┌──────────────┐
  │  Mobile   │───▶│   Backend    │───▶│  Frontend    │
  │  11种数据  │    │  存储+AI推理  │    │  评分+可视化  │
  └──────────┘    └──────────────┘    └──────────────┘
```

## 解决的核心痛点

**痛点 1：健康数据碎片化** — Apple Watch 采集的心率、睡眠、步数、血氧等 11 种数据散落在手机本地，Apple 健康应用只做原始展示，不做深度分析和跨维度关联，用户难以得出"我到底健不健康"的结论。

**痛点 2：数据采集与 AI 分析断裂** — 让 AI 理解健康数据需要手动截图或复制粘贴，LLM 无法直接"看到"用户的结构化数据，数据采集与 AI 推理之间存在明显鸿沟。

**痛点 3：通用 AI 缺乏专业聚焦** — 通用 ChatGPT 不了解你的身体指标，用户也不懂如何写 Prompt 注入健康上下文，需要可定制、带数据范围约束的智能体系统。

## 核心逻辑流

### 数据同步链路（采集 → 存储）

移动端集成 HealthKit，对心率、心率变异性、步数、睡眠、血氧、体温、运动记录、呼吸率、噪声暴露、正念会话等 **11 种数据**并行查询，转换为统一的 `SyncPayload` 批量上传。后端按 `sample_uuid` 去重插入，嵌套数据（睡眠阶段、运动心率区间）级联处理，同时 iOS 走真实数据、Android 自动降级为模拟数据，确保全平台可运行。

### AI 上下文感知推理链路（存储 → 理解 → 反馈）

这是项目的核心亮点，本质是**面向结构化时序数据的 RAG 变体**。用户发消息后，`context_builder` 对消息做关键词匹配判断涉及的维度（如"睡眠"命中 sleep 关键词），再从数据库按维度聚合查询（心率取 7 天均值/极值、睡眠取每晚时长等），将结果格式化为 Markdown 注入 LLM 系统上下文。LLM 因此拥有精确的数值依据而非模糊描述，通过工厂模式调用的 Provider（兼容 OpenAI/DeepSeek/Ollama）生成回答，支持 HTTP 同步和 WebSocket 流式两种通道。

### 可定制智能体系统

用户可定义智能体的人设 Prompt 和数据访问范围，如"睡眠教练"只访问睡眠与心率数据，实现**数据最小权限原则**——既减少 token 消耗，又聚焦推理质量。

### 健康评分与可视化

以 7 天为窗口，对活动、睡眠、心脏、生命体征四维加权评分（0.3/0.3/0.25/0.15），前端通过 ECharts 雷达图和趋势图直观呈现。

## 功能特性

- **健康数据同步** — 支持 11 种 Apple HealthKit 数据类型的采集与同步，UUID 去重保证数据唯一性
- **AI 智能对话** — 基于用户真实健康数据的上下文感知推理，而非泛泛而谈
- **智能体定制** — 自定义智能体人设与数据访问范围，打造专属健康顾问
- **健康评分** — 四维加权评分算法，雷达图直观展示健康全貌
- **数据可视化** — ECharts 驱动的步数、心率、睡眠、活动能量趋势图
- **流式输出** — WebSocket 实时逐 token 推流，对话体验流畅自然
- **多 LLM 支持** — 工厂模式统一接口，兼容 OpenAI / DeepSeek / Ollama
- **跨平台移动端** — React Native + Expo，iOS 真实数据 / Android 模拟数据自适应

## 技术栈

| 层级 | 技术 |
|------|------|
| **Backend** | FastAPI · SQLAlchemy · SQLite (aiosqlite) · PyJWT · WebSockets · httpx |
| **Frontend** | Vue 3 · TypeScript · Vite · Pinia · ECharts · vue-echarts · Axios |
| **Mobile** | React Native · Expo · TypeScript · NativeWind · react-native-healthkit · Zustand |
| **AI** | OpenAI API · Context-Aware RAG · Multi-Agent · Streaming |

## 项目结构

```
SyncHealth/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/               # REST API 路由 (sync, ai, agents, auth, dashboard...)
│   │   ├── models/            # SQLAlchemy 数据模型
│   │   ├── schemas/           # Pydantic 请求/响应模式
│   │   ├── services/
│   │   │   ├── ai/            # AI 核心模块
│   │   │   │   ├── agent_runtime.py    # Agent 编排层
│   │   │   │   ├── context_builder.py  # 智能上下文构建（关键词路由+聚合查询）
│   │   │   │   ├── factory.py          # LLM Provider 工厂
│   │   │   │   └── provider_openai.py  # OpenAI 兼容 Provider
│   │   │   ├── sync_service.py         # 健康数据同步处理
│   │   │   └── dashboard_service.py    # 健康评分算法
│   │   ├── config.py          # 配置管理
│   │   └── main.py            # 应用入口
│   └── pyproject.toml
├── frontend/                   # Vue3 前端
│   └── src/
│       ├── views/             # 页面 (Dashboard, AIChat, AgentBuilder, Sleep, Heart...)
│       ├── stores/            # Pinia 状态管理
│       └── services/          # API 调用层
├── mobile/                     # React Native 移动端
│   └── src/
│       ├── services/          # HealthKit 采集 + 数据同步
│       ├── screens/           # 页面组件
│       └── stores/            # Zustand 状态管理
└── docs/                       # 文档归档（技术/面试/简历）
    ├── technical/              # 开发/数据/部署/学习资料
    │   ├── LEARNING_GUIDE.md
    │   ├── DEPLOY.md
    │   ├── DEPLOY_METHODOLOGY.md
    │   ├── 开发问题与解决方案.md
    │   ├── 数据采集规则.md
    │   ├── 数据上传导入处理入库流程详解.md
    │   ├── learn_fastapi/
    │   └── learn_vue/
    ├── interview/              # 面试题库与问答手册
    │   ├── 前端面试题库.md
    │   └── AI应用开发岗面试问答手册.md
    └── resume/                 # 简历（含解包版 unpacked/）
```

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- iOS 设备（用于真实 HealthKit 数据，Android/模拟器将使用模拟数据）

### 后端

```bash
cd backend

# 安装依赖
pip install -e ".[dev]"

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 AI_API_KEY 等配置

# 启动服务
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 移动端

```bash
cd mobile

# 安装依赖
npm install

# iOS 启动
npx expo run:ios

# Android 启动
npx expo run:android
```

### 环境变量配置

后端 `.env` 文件示例：

```env
AI_PROVIDER=openai           # openai | domestic | local
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-xxx
AI_MODEL=gpt-4o
AI_MAX_CONTEXT_TOKENS=8000
AI_TEMPERATURE=0.7
```

支持切换为 DeepSeek、Ollama 等兼容 OpenAI 接口的服务。

## AI 驱动构建特征

| 特征 | 体现 |
|------|------|
| **长链推理** | 用户消息 → 关键词路由 → 按维度聚合查询 → 上下文格式化 → LLM 推理 → 结果持久化 |
| **上下文感知** | `context_builder` 根据用户问题动态决定检索哪些数据维度，非全量注入 |
| **Agent 定制** | 用户自建智能体，自定义人设 Prompt + 数据访问范围 |
| **RAG 变体** | 非传统文档向量检索，而是结构化数据聚合查询 → 自然语言上下文 |
| **多端协同** | 移动端采集、后端存储与 AI 推理、前端可视化，三端通过 REST + WebSocket 闭环 |
| **流式输出** | WebSocket + HTTP 双通道，支持实时逐 token 推流 |

---

## MedAgent Hub — 多智能体医疗健康协作系统

MedAgent Hub 是 SyncHealth 的**独立子应用**（位于 `medagent/` 目录），基于 **LangChain + LangGraph** 框架实现 4 个专职 Agent 的协作编排，提供从可穿戴数据洞察、报告解读到用药管理的全方位 AI 健康服务。

### 架构概览

```
SyncHealth 主项目                       MedAgent Hub（独立应用）
┌──────────────────┐     MCP Protocol     ┌────────────────────────────┐
│  FastAPI Backend │◄────────────────────│  FastAPI + LangGraph        │
│  健康数据 + Dify  │                      │  4-Agent 编排 + 长期记忆    │
│  SQLite          │                      │  ChromaDB + SQLite          │
└──────────────────┘                      └────────────────────────────┘
        ▲                                             ▲
        │             WebSocket 流式事件               │
        └───────────── Frontend (Vue3) ───────────────┘
```

**解耦设计**：MedAgent Hub 通过 **MCP（Model Context Protocol）** 从 SyncHealth backend 获取健康数据，而非直接访问数据库，实现两个应用的完全解耦。

### 4 个 Agent

| Agent | 职责 | 工具 |
|-------|------|------|
| 🧭 **Triage**（分诊路由） | 意图识别、紧急度评估、Agent 调度（纯推理，无工具） | 无 |
| 🏃 **健康教练** | 可穿戴数据洞察、生活方式建议、轻度症状分析 | 心率趋势、睡眠分析、活动摘要、健康评分、运动历史、健身知识、附近医疗 |
| 📋 **报告解读** | OCR 体检报告、指标对比、趋势分析、就医建议 | 报告 OCR、指标参考、历史对比、术语解释、健康事件、附近医疗 |
| 💊 **用药管理** | 药盒 OCR、药品查询、相互作用检查、OTC 推荐 | 药盒 OCR、药品查询、相互作用、OTC 推荐、用药提醒、附近医疗 |

**协作机制**：
- 所有消息先经 Triage 分诊，再路由到对应专家 Agent
- 专家 Agent 可通过 `reroute` 机制回退到 Triage 重新路由（上限 5 次循环）
- 紧急情况直接跳转紧急处置，不经过专家 Agent
- `search_nearby_medical` 是共享工具，被所有专家 Agent 调用

### 长期记忆系统

- **用户画像**：存储在 SQLite，包含年龄、慢性病史、过敏史、用药列表、健康目标
- **对话摘要**：`ConversationSummaryBufferMemory`，压缩历史对话要点
- **健康事件向量存储**：ChromaDB 语义检索，支持跨对话记忆（如"上次说的那个头疼后来怎么样了"）

### 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| LLM 调用失败 | 3 次重试 + 指数退避（1s→2s→4s）|
| Tool 执行超时 | 15 秒超时 + 返回部分结果 |
| MCP 连接断开 | 3 次重连 + 降级本地缓存 |
| JSON 解析失败 | 正则最大努力解析 + 兜底路由 |
| 循环路由超限 | MAX_LOOPS=5 强制终止 |

### 启动 MedAgent Hub

```bash
# 1. 先启动 SyncHealth backend（提供 MCP 健康数据）
cd backend
uvicorn app.main:app --reload --port 8000

# 2. 启动 MedAgent Hub
cd medagent
pip install -e ".[dev]"

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 AI_API_KEY、AMAP_API_KEY、SYNCHEALTH_BASE_URL 等

# 启动
uvicorn app.main:app --reload --port 8001
```

### WebSocket 事件协议

客户端连接 `ws://localhost:8001/api/v1/chat/ws`，发送：
```json
{"message": "我最近睡不好", "session_id": null}
```

服务端推送事件：`token` | `agent_switch` | `tool_start` | `tool_result` | `memory_recall` | `thinking` | `done` | `error`

### REST API 端点

| 端点 | 说明 |
|------|------|
| `GET /api/v1/agents` | Agent 配置列表 |
| `GET /api/v1/sessions` | 会话列表 |
| `GET /api/v1/sessions/{id}/messages` | 会话消息历史 |
| `GET /api/v1/memory/profile` | 用户健康画像 |
| `PUT /api/v1/memory/profile` | 更新画像 |
| `GET /api/v1/memory/timeline` | 健康事件时间线 |
| `POST /api/v1/memory/search` | 记忆语义搜索 |

## License

MIT
