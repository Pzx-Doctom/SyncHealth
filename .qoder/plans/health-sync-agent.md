# SyncHealth - 健康数据同步与 AI 分析系统

## Context

用户希望构建一个完整的健康数据生态系统：iOS 应用从 Apple Watch 读取全面的健康数据，通过后端 API 传输到 Vue 网页端，网页端提供数据可视化、AI 问答和智能体搭建功能。当前是全新项目，需要从零搭建三个组件。

## 技术选型

| 组件 | 技术栈 |
|------|--------|
| iOS 应用 | SwiftUI + HealthKit (iOS 16+) |
| 后端服务 | Python FastAPI + SQLAlchemy + SQLite |
| 前端应用 | Vue 3 + TypeScript + Pinia + Vue Router |
| 认证方式 | JWT (access + refresh token) |
| 图表库 | ECharts (vue-echarts) |
| AI 层 | 抽象接口，支持 OpenAI / 国内大模型 / 自部署模型 |

## 系统架构

```
iOS App (SwiftUI)  ──POST /sync/upload──>  FastAPI Backend  <──GET /health/*──  Vue Frontend
     │                                         │                                    │
  HealthKit                                 SQLite DB                         ECharts 图表
  Manager                                  AI 抽象层                          AI Chat (WS)
                                          (可插拔 LLM)                       Agent Builder
```

## 项目目录结构

```
SyncHealth/
├── ios/                               # iOS 应用
│   └── SyncHealth/
│       ├── SyncHealth.xcodeproj/
│       └── SyncHealth/
│           ├── App/                   # 应用入口
│           ├── Models/                # 数据模型 (Codable)
│           ├── Services/              # HealthKit、Sync、API、Auth
│           ├── Views/                 # SwiftUI 视图
│           ├── ViewModels/            # MVVM ViewModel
│           └── Utilities/             # Keychain、格式化、常量
│
├── backend/                           # FastAPI 后端
│   ├── pyproject.toml
│   ├── alembic.ini + alembic/        # 数据库迁移
│   └── app/
│       ├── main.py                   # FastAPI 应用工厂
│       ├── config.py                 # 配置管理
│       ├── database.py               # SQLite 引擎
│       ├── models/                   # SQLAlchemy ORM 模型
│       ├── schemas/                  # Pydantic 请求/响应模型
│       ├── api/                      # 路由处理器
│       ├── services/                 # 业务逻辑层
│       │   └── ai/                   # AI 抽象层
│       ├── core/                     # 安全、依赖注入、异常
│       └── tests/
│
├── frontend/                          # Vue 3 前端
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── router/                   # 路由配置
│       ├── stores/                   # Pinia 状态管理
│       ├── api/                      # Axios API 客户端
│       ├── types/                    # TypeScript 类型定义
│       ├── views/                    # 页面组件
│       ├── components/               # 通用/图表/布局组件
│       └── composables/              # 组合式函数
```

## 实现步骤

### 阶段一：后端基础与数据契约

**步骤 1: 后端项目脚手架**
- 创建 `backend/pyproject.toml`，依赖：fastapi, uvicorn, sqlalchemy, alembic, pyjwt, passlib, python-multipart, httpx
- 创建 `backend/app/main.py`：FastAPI 应用工厂，CORS 配置，生命周期事件
- 创建 `backend/app/config.py`：pydantic-settings 配置管理
- 创建 `backend/app/database.py`：SQLAlchemy 引擎 + 会话工厂
- 关键文件：`backend/app/main.py`, `backend/app/config.py`, `backend/app/database.py`

**步骤 2: 数据模型与 Schema 定义（核心）**
- 这是最关键的步骤 —— 所有数据类型的 Pydantic schema 是三端共享的数据契约
- ORM 模型（每种健康数据一张表）：
  - `heart_rates` — 心率、静息心率、步行心率
  - `hrv_samples` — 心率变异性 (SDNN)
  - `activity_samples` — 步数、距离、爬楼、卡路里、站立时间
  - `sleep_sessions` + `sleep_stages` — 睡眠时段与分期
  - `blood_oxygen_samples` — 血氧
  - `body_temperature_samples` — 体温
  - `workout_records` + `workout_hr_zones` — 运动记录与心率区间
  - `ecg_records` — 心电图
  - `respiratory_rate_samples` — 呼吸频率
  - `noise_exposure_samples` — 噪音暴露
  - `mindfulness_sessions` — 正念记录
  - `sync_logs` — 同步日志
  - `ai_agents`, `chat_sessions`, `chat_messages` — AI 相关
- 每条记录共享基础字段：`user_id`, `sample_uuid`(HealthKit UUID，用于去重), `source_device`, `recorded_at`, `synced_at`
- 唯一约束：`(user_id, sample_uuid)` 防止重复
- 关键文件：`backend/app/models/*.py`, `backend/app/schemas/health.py`, `backend/app/schemas/sync.py`

**步骤 3: 认证系统**
- JWT：access_token (15min) + refresh_token (30天)
- 密码哈希：bcrypt via passlib
- 端点：`/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me`
- 关键文件：`backend/app/core/security.py`, `backend/app/core/dependencies.py`, `backend/app/api/auth.py`

**步骤 4: 同步上传端点**
- `POST /sync/upload`：接收 iOS 发送的完整 SyncPayload
- SyncPayload 包含所有健康数据类型的数组 + 设备信息 + 同步时间窗口
- 服务层：按 `sample_uuid` 去重，批量插入，写入 sync_log
- 关键文件：`backend/app/api/sync.py`, `backend/app/services/sync_service.py`

**步骤 5: 数据库迁移**
- 配置 Alembic，生成初始迁移脚本
- 关键文件：`backend/alembic.ini`, `backend/alembic/`

### 阶段二：后端读取 API

**步骤 6: 健康数据查询端点**
- 每种数据类型一个端点：`/health/heart-rate`, `/health/sleep`, `/health/activity` 等
- 通用参数：`start`, `end`(日期范围), `page`, `page_size`(分页)
- 心率支持 `resolution` 参数：raw / hourly / daily
- 关键文件：`backend/app/api/health.py`, `backend/app/services/health_service.py`

**步骤 7: Dashboard 聚合端点**
- `/dashboard/summary`：今日快照（步数、卡路里、睡眠、平均心率、血氧）
- `/dashboard/trends?period=7d|30d|90d`：多指标趋势
- `/dashboard/health-score`：综合健康评分
- 关键文件：`backend/app/api/dashboard.py`, `backend/app/services/dashboard_service.py`

**步骤 8: WebSocket 基础**
- `/ai/chat/ws`：WebSocket 端点，先实现 echo 占位
- 关键文件：`backend/app/api/ai.py`

### 阶段三：Vue 前端

**步骤 9: 前端脚手架**
- Vite + Vue 3 + TypeScript + Pinia + Vue Router + Axios
- ECharts (vue-echarts) 图表库
- 关键文件：`frontend/package.json`, `frontend/vite.config.ts`

**步骤 10: 认证流程**
- Login / Register 页面
- Pinia auth store：token 管理、localStorage 持久化
- Axios 拦截器：自动附加 JWT、401 时自动刷新
- Router 导航守卫
- 关键文件：`frontend/src/stores/auth.ts`, `frontend/src/api/client.ts`, `frontend/src/views/LoginView.vue`

**步骤 11: Dashboard 主页**
- 布局：AppHeader + AppSidebar + 主内容区
- MetricCard 卡片、趋势图表、健康评分雷达图
- 关键文件：`frontend/src/views/DashboardView.vue`, `frontend/src/components/charts/*.vue`

**步骤 12: 详情页面**
- 心率、睡眠、运动、活动等详情页
- 每页消费对应 API 端点
- 关键文件：`frontend/src/views/HeartView.vue`, `frontend/src/views/SleepView.vue` 等

**步骤 13: AI Chat 界面**
- ChatWindow + ChatMessage + ChatInput 组件
- WebSocket composable 处理连接、重连、消息
- 关键文件：`frontend/src/views/AIChatView.vue`, `frontend/src/composables/useWebSocket.ts`

**步骤 14: Agent Builder**
- 智能体 CRUD 界面：名称、描述、系统提示词、数据范围选择
- 关键文件：`frontend/src/views/AgentBuilderView.vue`

### 阶段四：AI 抽象层

**步骤 15: 抽象接口**
- `BaseLLMProvider`：`chat()`, `stream_chat()`, `get_model_info()`
- Provider Factory：根据配置实例化正确的 provider
- 关键文件：`backend/app/services/ai/base.py`, `backend/app/services/ai/factory.py`

**步骤 16: Context Builder**
- 根据用户问题关键词，动态组装相关健康数据作为 LLM 上下文
- 结构化 Markdown 表格格式，节省 token
- 关键文件：`backend/app/services/ai/context_builder.py`

**步骤 17: OpenAI 兼容 Provider**
- 使用 httpx 调用 OpenAI API（可配置 base_url 兼容 Ollama 等）
- 关键文件：`backend/app/services/ai/provider_openai.py`

**步骤 18: 连接 AI 到 WebSocket**
- 完整流程：WS 消息 → 加载会话历史 → Context Builder → Provider → 流式响应
- Agent Runtime：注入自定义系统提示词，过滤数据范围
- 关键文件：`backend/app/api/ai.py`, `backend/app/services/ai/agent_runtime.py`

### 阶段五：iOS 应用

**步骤 19: Xcode 项目结构**
- 创建 SwiftUI 项目，配置 HealthKit entitlements 和 background modes
- Info.plist 配置 HealthKit 使用描述
- 关键文件：`ios/SyncHealth/SyncHealth/SyncHealth.entitlements`, `Info.plist`

**步骤 20: HealthKitManager**
- 查询 15+ 种数据类型：quantity samples, category samples, workout queries, ECG queries
- 处理授权请求
- 关键文件：`ios/SyncHealth/SyncHealth/Services/HealthKitManager.swift`

**步骤 21: 数据模型 + JSON 编码**
- Swift Codable structs，严格对应后端 Pydantic schema
- 关键文件：`ios/SyncHealth/SyncHealth/Models/HealthDataModels.swift`, `SyncPayload.swift`

**步骤 22: API 客户端 + Auth**
- URLSession HTTP 客户端
- Keychain 存储 JWT
- 401 自动刷新
- 关键文件：`ios/SyncHealth/SyncHealth/Services/APIClient.swift`, `AuthService.swift`

**步骤 23: Sync 服务**
- 增量同步：高水位标记策略（首次 90 天，后续从 lastSyncDate 开始）
- 大负载分片：>5000 条记录时分批上传
- 关键文件：`ios/SyncHealth/SyncHealth/Services/SyncService.swift`

**步骤 24: 后台同步**
- BGProcessingTask 注册，定期同步
- 前台触发：超过 15 分钟未同步时自动触发
- 手动同步按钮
- 关键文件：`ios/SyncHealth/SyncHealth/Services/BackgroundSyncManager.swift`

**步骤 25: iOS UI**
- TabView：Dashboard、数据预览、同步状态、设置、登录
- 关键文件：`ios/SyncHealth/SyncHealth/Views/*.swift`

### 阶段六：集成与测试

**步骤 26: Mock iOS 客户端**
- Python 脚本生成仿真健康数据，POST 到 /sync/upload
- 用于 Windows 环境下测试和开发数据填充
- 关键文件：`backend/tests/mock_ios_client.py`

**步骤 27: 后端测试**
- pytest + httpx AsyncClient
- 测试：认证、同步去重、数据查询、AI 流程
- 关键文件：`backend/tests/test_*.py`

**步骤 28: 端到端验证**
- Mock 客户端上传 → Vue 前端展示 → AI 对话测试

## API 端点概览

### 认证 `/api/v1/auth`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /auth/register | 注册 |
| POST | /auth/login | 登录，返回 JWT |
| POST | /auth/refresh | 刷新 token |
| GET | /auth/me | 当前用户信息 |

### 同步 `/api/v1/sync`（iOS 调用）
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /sync/upload | 上传健康数据（SyncPayload） |
| GET | /sync/status | 最近同步状态 |
| GET | /sync/history | 同步历史 |

### 健康数据 `/api/v1/health`（Vue 调用）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health/heart-rate | 心率数据 |
| GET | /health/hrv | 心率变异性 |
| GET | /health/activity | 活动数据（步数等） |
| GET | /health/sleep | 睡眠数据 |
| GET | /health/blood-oxygen | 血氧 |
| GET | /health/body-temperature | 体温 |
| GET | /health/workouts | 运动记录 |
| GET | /health/ecg | 心电图 |
| GET | /health/respiratory-rate | 呼吸频率 |
| GET | /health/noise-exposure | 噪音暴露 |
| GET | /health/mindfulness | 正念记录 |

### Dashboard `/api/v1/dashboard`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /dashboard/summary | 今日快照 |
| GET | /dashboard/trends | 趋势数据 |
| GET | /dashboard/health-score | 健康评分 |

### AI `/api/v1/ai`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /ai/chat | 同步聊天 |
| WS | /ai/chat/ws | 流式聊天 |
| GET | /ai/sessions | 会话列表 |

### 智能体 `/api/v1/agents`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | /agents | 列表/创建 |
| PUT/DELETE | /agents/{id} | 更新/删除 |

## 关键设计决策

1. **单一上传端点**：iOS 一次调用上传所有数据类型，减少网络请求
2. **UUID 去重**：HealthKit 样本 UUID 作为去重键，增量同步安全可靠
3. **直接上下文注入（非 RAG）**：健康数据是结构化数值，直接查询注入比向量嵌入更高效
4. **每种数据独立表**：查询性能好、Schema 清晰，优于通用 JSON 表
5. **AI Provider 可插拔**：抽象接口 + 工厂模式，配置切换 LLM 提供商

## 验证方式

1. **后端**：启动 FastAPI 服务，运行 pytest 测试套件
2. **Mock 数据**：运行 mock_ios_client.py 填充测试数据
3. **前端**：启动 Vue dev server，验证 Dashboard 图表渲染和数据展示
4. **AI 对话**：通过 WebSocket 发送消息，验证流式响应
5. **iOS**：在 Mac + Xcode 上编译，真机测试 HealthKit 读取和同步
