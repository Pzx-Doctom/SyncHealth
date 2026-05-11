# SyncHealth 项目学习路线

> 面向前端初学者 → AI 开发工程师

测试账号：test@synchealth.com
密码：testpass123

## 项目概况

**SyncHealth** 是一个「个人健康数据同步 + AI 分析」全栈平台，涵盖：

- **前端**：Vue 3 + TypeScript + Pinia + ECharts
- **后端**：Python FastAPI + SQLAlchemy 2.0 + SQLite
- **AI**：集成大语言模型（DeepSeek），支持自定义智能体

---

## 第一阶段：先把项目跑起来（1-2天）

这是最重要的第一步——看到项目实际运行，建立直观理解。

### 1.1 启动后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

打开 `http://localhost:8000/docs`，这是 FastAPI 自动生成的 **Swagger API 文档**，浏览所有接口。

### 1.2 生成测试数据

```bash
python scripts/generate_health_data.py
```

这个脚本会自动注册用户、生成 7 天模拟健康数据、上传到后端。**仔细阅读这个文件**，它是理解整个数据流最好的入口。

### 1.3 启动前端

```bash
cd frontend
npm install
npm run dev
```

打开 `http://localhost:3000`，用 `test@synchealth.com` / `testpass123` 登录，体验所有功能。

---
·
## 第二阶段：吃透前端（你已经会 Vue，重点补 TypeScript 和工程化）

按以下顺序阅读前端文件，**每个文件都要读懂每一行**：

| 顺序 | 文件 | 学习重点 |
|------|------|---------|
| 1 | `frontend/src/main.ts` | Vue 应用入口，Pinia + Router 的挂载方式 |
| 2 | `frontend/src/router/index.ts` | 路由配置、**路由守卫**（beforeEach 认证拦截）、嵌套路由 |
| 3 | `frontend/src/stores/auth.ts` | Pinia Composition API 写法、computed、localStorage 持久化 |
| 4 | `frontend/src/api/client.ts` | **重点**：Axios 拦截器、JWT 自动附加、**401 自动刷新 token + 请求队列** |
| 5 | `frontend/src/types/*.ts` | TypeScript 类型定义，理解前后端数据契约 |
| 6 | `frontend/src/views/LoginView.vue` | 最简单的表单页面，理解 Vue 3 `<script setup>` |
| 7 | `frontend/src/stores/dashboard.ts` | 多个 API 并行调用（Promise.all） |
| 8 | `frontend/src/views/DashboardView.vue` | **重点**：最复杂的页面，包含 ECharts 图表、数据聚合展示 |
| 9 | `frontend/src/views/AIChatView.vue` | AI 对话界面，理解 WebSocket 或普通 HTTP 聊天 |
| 10 | `frontend/src/views/AgentBuilderView.vue` | AI 智能体构建表单 |
| 11 | `frontend/src/components/layout/AppLayout.vue` | 侧边栏布局、router-link 高亮 |

### 需要补的知识点

- **TypeScript**：interface/type、泛型（`PaginatedResponse<T>`）、联合类型（`string | null`）
- **Pinia**：Composition API 风格（`defineStore` + `setup` 函数）
- **ECharts**：`vue-echarts` 的基本用法，看 `DashboardView.vue` 中的趋势图

---

## 第三阶段：理解后端（从你会的 Python 出发）

你已经学过简单 Python，这个后端代码非常规范，按层阅读：
启动后端首先要通过.venv\scripts\activate激活环境，然后执行以下代码启动后端：
`
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
`


### 3.1 入口和配置（1天）

| 文件 | 学习内容 |
|------|---------|
| `backend/app/main.py` | FastAPI 应用创建、CORS 配置、lifespan（启动时初始化数据库） |
| `backend/app/config.py` | **pydantic-settings**：环境变量自动映射到类属性 |
| `backend/app/database.py` | SQLAlchemy 异步引擎、会话工厂、依赖注入 |

### 3.2 数据模型层（1天）—— 对应数据库表

从简单到复杂：

1. `models/user.py` — 最基础，理解 `Mapped[]` 类型注解
2. `models/heart.py` — 注意 `UniqueConstraint`（去重约束）
3. `models/activity.py` — 单表多指标（metric_type 区分步数/距离/卡路里）
4. `models/sleep.py` — **一对多关系**（SleepSession → SleepStage）
5. `models/workout.py` — 同上（WorkoutRecord → WorkoutHRZone）
6. `models/ai.py` — AI 相关三张表

### 3.3 认证系统（半天）

按请求链路读：

1. `schemas/auth.py` — Pydantic 请求/响应模型
2. `core/security.py` — **bcrypt 密码哈希** + **JWT 生成/验证**
3. `core/dependencies.py` — **依赖注入**：从 token 解析出当前用户
4. `api/auth.py` — 路由层，调用 service
5. `services/auth_service.py` — 业务逻辑层

### 3.4 数据同步和查询（1天）

1. `schemas/health.py` — 11 种健康数据的 In/Out Schema
2. `schemas/sync.py` — `SyncPayload`：一次上传 11 种数据的"大包裹"
3. `services/sync_service.py` — **核心**：批量插入 + UUID 去重 + 嵌套关系处理
4. `services/health_service.py` — 分页查询 + 时间范围过滤
5. `services/dashboard_service.py` — **重点**：聚合查询、趋势计算、健康评分算法

### 3.5 AI 系统（1-2天）—— 这是项目最大的亮点

按数据流顺序读：

```
用户发送消息 → api/ai.py（路由层）
             → services/ai/agent_runtime.py（编排层）
                 → services/ai/context_builder.py（根据用户问题智能检索健康数据）
                 → services/ai/factory.py（获取 LLM Provider）
                 → services/ai/provider_openai.py（调用大模型 API）
             → 保存对话到数据库
             → 返回响应
```

需要补的知识点：

- **抽象基类（ABC）**：`BaseLLMProvider` 定义接口
- **工厂模式**：`get_provider()` 根据配置动态创建
- **SSE 流式输出**：解析 `data: {...}` 格式的 Server-Sent Events
- **WebSocket**：`/ai/chat/ws` 端点实现实时对话
- **上下文构建**：根据用户消息关键词，从数据库检索相关健康数据注入 LLM prompt

---

## 第四阶段：深入理解核心概念

| 概念 | 在项目中的体现 |
|------|--------------|
| RESTful API 设计 | 6 组路由、统一 `/api/v1` 前缀、分页参数标准化 |
| JWT 认证 | access_token + refresh_token 双 token 机制 |
| 依赖注入 | FastAPI 的 `Depends()` 贯穿全局 |
| 异步编程 | `async/await` 全异步，aiosqlite 异步数据库 |
| ORM 模式 | SQLAlchemy 2.0 Mapped API，DeclarativeBase |
| 前后端分离 | 前端 Axios + 后端 REST API，Vite 代理解决跨域 |
| 设计模式 | 工厂模式、策略模式（AI Provider）、仓储模式（Service 层） |
| OpenAI API 协议 | `/v1/chat/completions` 标准接口，兼容 DeepSeek/Ollama |

---

## 第五阶段：实践练习（巩固所学）

1. **给项目加一个新功能**：比如"喝水记录"——从 model → schema → service → api → 前端 types → api → store → view 全链路实现
2. **修改 AI 智能体**：换一个自定义 system_prompt，观察对话效果变化
3. **修改健康评分算法**：调整权重和计算逻辑，理解业务逻辑
4. **添加一个新的图表**：在仪表盘页添加一个雷达图展示各维度健康评分

---

## 推荐学习资源

| 主题 | 资源 |
|------|------|
| TypeScript | [typescript-handbook](https://www.typescriptlang.org/docs/handbook/) |
| FastAPI | [fastapi 官方文档](https://fastapi.tiangolo.com/) |
| SQLAlchemy 2.0 | [SQLAlchemy 2.0 文档](https://docs.sqlalchemy.org/en/20/) |
| Pydantic v2 | [pydantic 文档](https://docs.pydantic.dev/latest/) |
| OpenAI API | [OpenAI Chat API](https://platform.openai.com/docs/api-reference/chat) |
| Pinia | [Pinia 官方文档](https://pinia.vuejs.org/) |

---

**建议总学习时间**：2-3 周可以吃透。从第一阶段开始，边跑边看代码，遇到不懂的就搜文档。这个项目的代码质量很高，架构清晰，是非常好的全栈学习素材。
