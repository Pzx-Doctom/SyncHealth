# SyncHealth 项目学习路线

> 面向前端初学者 → AI 开发工程师
>
> **学习风格提示**：遇到抽象概念不要硬啃，先找生活类比！下面每个核心概念都附带了通俗比喻，帮助你快速建立直觉。

测试账号：test@synchealth.com
密码：testpass123

## 项目概况

**SyncHealth** 是一个「个人健康数据同步 + AI 分析」全栈平台，涵盖：

- **前端**：Vue 3 + TypeScript + Pinia + ECharts
- **后端**：Python FastAPI + SQLAlchemy 2.0 + SQLite
- **AI**：集成大语言模型（DeepSeek），支持自定义智能体

### 后端架构总览（先有个全貌）

```
请求进来 → FastAPI 路由（api/）→ 业务逻辑（services/）→ 数据库操作（models/ + SQLAlchemy）
                ↑                       ↑
          依赖注入（core/）         Schema 校验（schemas/）
```

后端采用经典的**分层架构**，每一层职责明确：

| 层 | 目录 | 职责 | 生活类比 |
|----|------|------|---------|
| 路由层 | `api/` | 接收请求、返回响应，像**前台接待员** | 餐厅服务员——只负责点单和上菜 |
| Schema 层 | `schemas/` | 定义请求/响应的数据格式，像**表格模板** | 银行业务表——规定哪些字段必填 |
| 业务逻辑层 | `services/` | 处理核心逻辑，像**后厨** | 厨师——真正做菜的地方 |
| 数据模型层 | `models/` | 对应数据库表，像**仓库货架** | 仓库——货物按固定格式存放 |
| 核心层 | `core/` | 安全、依赖注入等基础设施 | 餐厅的保安+水电系统 |

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

> **为什么先看 /docs？** 这个页面就是你的「菜单」，让你一眼看到后端能做什么。每个接口都可以直接在页面上测试，比看代码更直观。

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

### 1.4 体验时留意的问题（带着问题看代码更有效）

- 登录后，浏览器哪里存了 token？（提示：打开 DevTools → Application → Local Storage）
- 仪表盘的数据是前端算的还是后端算的？
- AI 对话是普通 HTTP 还是 WebSocket？

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

## 第三阶段：后端入口与基础设施（1天）

> **为什么从入口开始？** 就像了解一栋楼，先找到大门，再逐层参观。

启动后端首先要通过 `.venv\Scripts\activate` 激活环境，然后执行以下代码启动后端：
```
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3.1 应用入口：`main.py` —— 大楼的入口大厅

**读取顺序**：先读 `config.py` → 再读 `main.py` → 最后读 `database.py`

| 核心概念 | 代码 | 生活类比 |
|---------|------|---------|
| `create_app()` 工厂函数 | 不直接创建 app，而是用函数包一层 | 就像连锁店的「开店流程」——统一装修、统一配置，保证每个店都一样 |
| `lifespan` 上下文管理器 | 启动时执行 `init_db()`，关闭时清理资源 | 餐厅「开门营业前备货，打烊后关灯锁门」 |
| CORS 中间件 | 配置允许哪些前端地址访问 | 小区的门禁白名单——只有在名单上的访客才能进 |
| 延迟导入路由 | 在 `create_app()` 内部 `import`，而非文件顶部 | 避免循环引用，就像两个人互相等对方先说话，谁都开不了口 |
| `app = create_app()` | 模块级变量，给 uvicorn 用 | 开店流程执行完毕，餐厅正式挂牌营业 |

### 3.2 全局配置：`config.py` —— 餐厅的经营手册

```python
class Settings(BaseSettings):
    APP_NAME: str = "SyncHealth"
    DATABASE_URL: str = "sqlite+aiosqlite:///./synchealth.db"
    # ...
```

| 核心概念 | 生活类比 |
|---------|---------|
| `BaseSettings`（pydantic-settings） | 经营手册的模板——规定需要哪些配置项 |
| 环境变量覆盖（`.env` 文件） | 同一套手册，不同分店可以自定义（比如改数据库地址） |
| `model_config = SettingsConfigDict(...)` | 告诉系统去哪里找 `.env` 文件 |

### 3.3 数据库基础设施：`database.py` —— 餐厅的后厨系统

这是**最容易觉得抽象的文件**，但理解了类比就简单了：

| 组件 | 代码 | 生活类比 | 作用 |
|------|------|---------|------|
| **Engine 引擎** | `create_async_engine(DATABASE_URL)` | **餐厅前台/接待处** | 管理与数据库的连接池，就像前台管理「几号桌有空」 |
| **SessionFactory 会话工厂** | `async_sessionmaker(engine, ...)` | **取号机** | 每次调用生成一个新的 Session，就像取号机吐一张号 |
| **Session 会话** | `async with session_factory() as session` | **一次就餐过程** | 从入座到结账的完整事务，出错就回滚（像退菜重做） |
| **Base ORM 基类** | `class Base(DeclarativeBase)` | **表单模板 + 登记处** | 所有模型类的父类（模板），同时维护「所有模型」的注册表（登记处） |
| **`get_db()` 依赖** | `async def get_db(): ... yield session` | **服务员专职服务** | 每个请求分配一个专属服务员，请求结束自动结账（commit/rollback） |
| **`init_db()` 初始化** | `async def init_db(): ... run_sync(Base.metadata.create_all)` | **开业前摆桌椅** | 根据所有模型定义，在数据库中创建对应的表 |

> **关键细节：`expire_on_commit=False`**
> 默认情况下，commit 后 Session 会「忘记」已加载的对象（过期）。设为 False 可以在 commit 后继续访问对象属性，这在 FastAPI 的请求周期中非常重要——否则响应序列化时就会报 `DetachedInstanceError`。
>
> 类比：结账后服务员还能记住你点了什么菜，不用再问你一遍。

> **关键细节：`run_sync` 桥接**
> `create_all` 是同步函数，但我们的上下文是异步的。`run_sync` 就像在异步世界里架了一座桥，让我们能安全调用同步代码。

---

## 第四阶段：数据模型层（1天）—— 对应数据库表

> **类比**：模型就是「仓库货架的设计图」，每个模型类 = 一种货架，每个字段 = 货架上的一个格子。

从简单到复杂，按以下顺序阅读：

| 顺序 | 文件 | 学习重点 | 关键概念 |
|------|------|---------|---------|
| 1 | `models/user.py` | 最基础的模型，理解 `Mapped[]` 类型注解 | `mapped_column()`、`index=True`（索引加速查找）、`lambda` 默认值 |
| 2 | `models/heart.py` | 唯一性约束 | `UniqueConstraint`（去重，防止同一条数据重复插入） |
| 3 | `models/activity.py` | 单表多指标设计 | `metric_type` 字段区分步数/距离/卡路里，一种设计模式 |
| 4 | `models/sleep.py` | **一对多关系** | `relationship()` + `ForeignKey`：一个睡眠记录 → 多个睡眠阶段 |
| 5 | `models/workout.py` | 同上的一对多关系 | WorkoutRecord → WorkoutHRZone，巩固关系映射理解 |
| 6 | `models/ai.py` | AI 相关三张表 | 对话、消息、智能体的表设计 |

### 模型字段速查表

| 字段类型 | 用法 | 生活类比 |
|---------|------|---------|
| `Mapped[int]` = `mapped_column(Integer, primary_key=True)` | 自增主键 | 身份证号——每人唯一 |
| `Mapped[str]` = `mapped_column(String(255), unique=True, index=True)` | 唯一 + 有索引 | 手机号——不能重复，查得快 |
| `Mapped[str]` = `mapped_column(String(255))` | 普通字符串 | 昵称——可以重复 |
| `Mapped[datetime]` = `mapped_column(default=lambda: datetime.utcnow())` | 带默认值的时间戳 | 入职日期——默认今天，用 lambda 避免所有记录同一时间 |
| `Mapped[datetime | None]` = `mapped_column(nullable=True)` | 可为空 | 离职日期——还没走就没有 |

> **为什么 `default` 用 `lambda` 而不是直接写 `datetime.utcnow()`？**
> 直接写的话，程序启动时就会执行一次，所有记录都会拿到同一个时间。用 `lambda` 会让每次创建新记录时才执行，拿到的是「那一刻」的时间。

---

## 第五阶段：认证系统（半天）—— 跟着一条登录请求走

> **类比**：认证系统就像小区的门禁系统——刷门禁卡（token）才能进，门禁卡有过期时间，过期了要拿旧卡换新卡（refresh）。

**按请求链路读，从外到内**：

```
用户提交 email+password
  → schemas/auth.py（校验输入格式，像保安检查证件是否规范）
  → api/auth.py（路由：接收请求，像前台登记处）
  → services/auth_service.py（业务逻辑：验证密码、生成 token，像保安核实身份后发门禁卡）
  → core/security.py（工具：密码哈希 + JWT 生成/验证，像制作门禁卡的机器）
  → core/dependencies.py（依赖注入：从 token 解析出当前用户，像刷卡进门）
```

| 顺序 | 文件 | 学习重点 |
|------|------|---------|
| 1 | `schemas/auth.py` | Pydantic 请求/响应模型，理解 `BaseModel` 的字段校验 |
| 2 | `core/security.py` | **bcrypt 密码哈希**（只存哈希不存明文）+ **JWT 生成/验证**（token 的结构：header.payload.signature） |
| 3 | `core/dependencies.py` | **依赖注入**：`get_current_user()` 如何从请求头提取 token → 解码 → 查数据库 → 返回用户对象 |
| 4 | `api/auth.py` | 路由层：`/login`、`/register`、`/refresh` 三个端点 |
| 5 | `services/auth_service.py` | 业务逻辑层：密码校验、token 刷新 |

### 认证核心概念

| 概念 | 解释 | 生活类比 |
|------|------|---------|
| **JWT** | JSON Web Token，三段式加密字符串 | 门禁卡——包含你的信息，但别人无法伪造 |
| **Access Token** | 短期 token（如 30 分钟） | 临时通行证——安全但有效期短 |
| **Refresh Token** | 长期 token（如 7 天） | 续期凭证——用它可以换新的临时通行证 |
| **bcrypt** | 单向哈希算法，不可逆 | 碎纸机——只能碎不能还原，验证时重新碎一次比对碎屑 |
| **依赖注入 `Depends()`** | FastAPI 自动调用函数并将结果传给路由 | 你不用自己去找服务员，系统自动给你分配一个 |

> **前后端联调关键**：对照前端 `api/client.ts` 中的 Axios 拦截器理解 token 的自动附加和 401 自动刷新机制。

---

## 第六阶段：数据同步和查询（1天）

> **类比**：数据同步就像「快递分拣中心」—— 各种包裹（11 种健康数据）一起到，要拆包、分类、去重、上架。

| 顺序 | 文件 | 学习重点 |
|------|------|---------|
| 1 | `schemas/health.py` | 11 种健康数据的 In/Out Schema，理解 Pydantic 如何定义数据契约 |
| 2 | `schemas/sync.py` | `SyncPayload`：一次上传 11 种数据的"大包裹" |
| 3 | `services/sync_service.py` | **核心**：批量插入 + UUID 去重 + 嵌套关系处理 |
| 4 | `services/health_service.py` | 分页查询 + 时间范围过滤 |
| 5 | `services/dashboard_service.py` | **重点**：聚合查询、趋势计算、健康评分算法 |

### 数据流全景图

```
手机/设备采集数据
  → 前端打包成 SyncPayload（11 种数据一起发）
  → api/sync.py 接收
  → sync_service.py 拆包、去重（UUID）、批量写入数据库
  → 用户查询时，health_service.py 做分页+时间过滤
  → 仪表盘请求时，dashboard_service.py 做聚合计算+健康评分
```

---

## 第七阶段：AI 系统（1-2天）—— 项目最大的亮点

> **类比**：AI 系统就像一个「智能健康顾问团队」—— 有调度员（agent_runtime）、资料员（context_builder）、接线员（provider），各司其职。

按数据流顺序读：

```
用户发送消息 → api/ai.py（路由层，像前台接单）
             → services/ai/agent_runtime.py（编排层，像调度员分配任务）
                 → services/ai/context_builder.py（根据用户问题智能检索健康数据，像资料员翻病历）
                 → services/ai/factory.py（获取 LLM Provider，像接线员接通专家电话）
                 → services/ai/provider_openai.py（调用大模型 API，像和专家通话）
             → 保存对话到数据库
             → 返回响应
```

| 顺序 | 文件 | 学习重点 |
|------|------|---------|
| 1 | `models/ai.py` | AI 相关三张表的结构 |
| 2 | `schemas/ai.py` | AI 请求/响应的 Schema |
| 3 | `api/ai.py` | AI 路由：普通 HTTP + SSE 流式 + WebSocket 三种接口 |
| 4 | `services/ai/factory.py` | **工厂模式**：根据配置动态创建 Provider |
| 5 | `services/ai/provider_openai.py` | **策略模式**：实现 `BaseLLMProvider` 接口，调用大模型 API |
| 6 | `services/ai/context_builder.py` | **上下文构建**：根据用户消息关键词检索相关健康数据 |
| 7 | `services/ai/agent_runtime.py` | **编排层**：串联以上所有组件 |
| 8 | `api/agents.py` | 智能体 CRUD 管理 |

### 需要补的知识点

| 知识点 | 在项目中的体现 | 生活类比 |
|--------|--------------|---------|
| **抽象基类（ABC）** | `BaseLLMProvider` 定义接口，子类必须实现 | 岗位说明书——规定了这个岗位必须做什么 |
| **工厂模式** | `get_provider()` 根据配置动态创建 Provider | HR——根据部门需求招不同的人 |
| **策略模式** | 不同的 Provider（OpenAI/Ollama）可互换 | 同一个岗位，不同员工轮流上 |
| **SSE 流式输出** | 解析 `data: {...}` 格式的 Server-Sent Events | 说话时一个字一个字蹦出来，而不是等全部说完 |
| **WebSocket** | `/ai/chat/ws` 端点实现实时对话 | 打电话——双向实时通信 |
| **上下文构建** | 根据用户消息关键词，从数据库检索相关健康数据注入 LLM prompt | 看病前先翻病历，把相关资料给医生 |

---

## 第八阶段：核心概念总结

学完所有代码后，回头对照这张表，检验自己的理解：

| 概念 | 在项目中的体现 | 你能解释了吗？ |
|------|--------------|--------------|
| RESTful API 设计 | 6 组路由、统一 `/api/v1` 前缀、分页参数标准化 | ☐ |
| JWT 认证 | access_token + refresh_token 双 token 机制 | ☐ |
| 依赖注入 | FastAPI 的 `Depends()` 贯穿全局 | ☐ |
| 异步编程 | `async/await` 全异步，aiosqlite 异步数据库 | ☐ |
| ORM 模式 | SQLAlchemy 2.0 Mapped API，DeclarativeBase | ☐ |
| 前后端分离 | 前端 Axios + 后端 REST API，Vite 代理解决跨域 | ☐ |
| 设计模式 | 工厂模式、策略模式（AI Provider）、仓储模式（Service 层） | ☐ |
| OpenAI API 协议 | `/v1/chat/completions` 标准接口，兼容 DeepSeek/Ollama | ☐ |
| Lifespan 生命周期 | 应用启动/关闭时执行初始化/清理逻辑 | ☐ |
| 分层架构 | api → service → model，职责分离 | ☐ |

---

## 第九阶段：实践练习（巩固所学）

1. **给项目加一个新功能**：比如"喝水记录"——从 model → schema → service → api → 前端 types → api → store → view 全链路实现
2. **修改 AI 智能体**：换一个自定义 system_prompt，观察对话效果变化
3. **修改健康评分算法**：调整权重和计算逻辑，理解业务逻辑
4. **添加一个新的图表**：在仪表盘页添加一个雷达图展示各维度健康评分

### 新功能全链路开发清单（以"喝水记录"为例）

```
后端：
  □ models/water.py        — 定义 WaterIntake 模型
  □ schemas/water.py       — 定义请求/响应 Schema
  □ services/water_service.py — 实现 CRUD 业务逻辑
  □ api/water.py           — 定义路由端点
  □ api/router.py          — 注册新路由

前端：
  □ types/water.ts         — 定义 TypeScript 类型
  □ api/water.ts           — 封装 API 调用
  □ stores/water.ts        — Pinia store
  □ views/WaterView.vue    — 页面组件
```

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

## 学习节奏建议

| 阶段 | 时间 | 产出目标 |
|------|------|---------|
| 第一阶段：跑起来 | 1-2 天 | 能在本地运行，体验所有功能，看懂 /docs 页面 |
| 第二阶段：前端 | 3-4 天 | 每个文件都能读懂，理解数据流从 API 到页面 |
| 第三阶段：入口与基础设施 | 1 天 | 能解释 engine/session/base/依赖注入 每个概念 |
| 第四阶段：数据模型 | 1 天 | 能自己写一个简单模型 |
| 第五阶段：认证系统 | 半天 | 能画出一条登录请求的完整调用链 |
| 第六阶段：数据同步和查询 | 1 天 | 理解批量插入+去重+聚合查询 |
| 第七阶段：AI 系统 | 1-2 天 | 理解工厂模式+策略模式+上下文构建 |
| 第八阶段：概念总结 | 半天 | 对照清单，能解释每个核心概念 |
| 第九阶段：实践练习 | 2-3 天 | 完成至少一个全链路新功能 |

**建议总学习时间**：2-3 周可以吃透。从第一阶段开始，边跑边看代码，遇到不懂的就搜文档。这个项目的代码质量很高，架构清晰，是非常好的全栈学习素材。
