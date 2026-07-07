# 📗 补充专题：Pydantic 深度解析

> Pydantic 是 FastAPI 的数据校验引擎，本文档深入解析其核心机制和高级用法

---

## 目录

1. [Pydantic 核心概念](#1-pydantic-核心概念)
2. [字段类型大全](#2-字段类型大全)
3. [校验器深度使用](#3-校验器深度使用)
4. [模型配置 Config](#4-模型配置-config)
5. [模型序列化与导出](#5-模型序列化与导出)
6. [泛型模型](#6-泛型模型)

---

## 1. Pydantic 核心概念

### 1.1 Pydantic 是什么？

Pydantic 是一个数据校验库，核心是**用 Python 类型提示定义数据模型，自动校验和转换数据**。

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    age: int

# 自动校验
user = User(id="1", name="张三", age="25")  # 字符串会自动转整数
print(user.id)   # 1（int）
print(user.age)  # 25（int）

# 校验失败自动报错
try:
    user = User(id="abc", name="张三", age=25)
except ValidationError as e:
    print(e)  # id: value is not a valid integer
```

### 1.2 Pydantic V1 vs V2

FastAPI 0.100+ 使用 Pydantic V2，主要区别：

| 特性 | V1 | V2 |
|------|----|----|
| 校验器装饰器 | `@validator` | `@field_validator` |
| 根校验器 | `@root_validator` | `@model_validator` |
| ORM 配置 | `orm_mode = True` | `from_attributes = True` |
| 性能 | 基于 Python | 基于 Rust (pydantic-core) |
| 导出方法 | `.dict()` | `.model_dump()` |
| JSON 方法 | `.json()` | `.model_dump_json()` |

```python
# V1 风格
class UserV1(BaseModel):
    name: str
    class Config:
        orm_mode = True

# V2 风格
class UserV2(BaseModel):
    name: str
    model_config = ConfigDict(from_attributes=True)
```

> ### 🏗️ 项目实例：SyncHealth Pydantic V2 实战
>
> SyncHealth 全部使用 Pydantic V2 风格。健康数据的输入/输出 Schema 通过继承实现代码复用，输出模型统一配置 `from_attributes=True`：
>
> ```python
> # backend/app/schemas/health.py - Pydantic V2 Schema 层级
> from datetime import datetime
> from pydantic import BaseModel
>
> # 基础模型：所有健康数据共享的字段
> class HealthSampleBase(BaseModel):
>     sample_uuid: str
>     source_device: str | None = None     # V2 语法：str | None
>     recorded_at: datetime
>
> # 输入模型：继承基础字段 + 类型专属字段
> class HeartRateIn(HealthSampleBase):
>     bpm: float
>     motion_context: str | None = None
>     measurement_type: str = "heart_rate"
>
> # 输出模型：继承输入字段 + 数据库系统字段 + ORM 支持
> class HeartRateOut(HeartRateIn):
>     id: int
>     synced_at: datetime
>     model_config = {"from_attributes": True}  # V2 配置
> ```
>
> #### 为什么 `In` 和 `Out` 要分开？
>
> **`In` 和 `Out` 的核心区别：数据流向不同。**
>
> ```
> 客户端发送数据（POST/PUT）              服务器返回数据（Response）
>        ↓                                       ↑
>   HeartRateIn                              HeartRateOut
>   (只定义客户端该传的字段)                 (定义客户端能看到的字段)
> ```
>
> **① `HeartRateIn`（输入模型）**——给客户端用的"白名单"：
>
> - 只包含业务字段：`bpm`、`sample_uuid`、`source_device`、`recorded_at`
> - 客户端上传心率数据时，JSON 里只能有这些字段
> - **没有 `id` 和 `synced_at`**——因为 `id` 是数据库自增主键、`synced_at` 是服务器写入时的时间戳，客户端无权指定
>
> **② `HeartRateOut`（输出模型）**——给客户端的"响应视图"：
>
> - 继承 `HeartRateIn` 的所有业务字段，再追加系统字段 `id` 和 `synced_at`
> - `model_config = {"from_attributes": True}` 让它能直接从 ORM 对象构建
> - 数据库写入后，返回给客户端的数据自然包含完整信息
>
> **③ 为什么要分离？（安全 + 职责清晰）**
>
> 如果用一个模型同时收发数据，会出现安全漏洞：
>
> ```python
> # ❌ 危险：如果一个模型两端通用
> class HeartRate(BaseModel):
>     id: int          # 客户端 POST 时可能会伪造 id！
>     bpm: float
>     synced_at: datetime  # 客户端可能篡改时间戳
>
> # 恶意请求：
> POST /sync/upload  {"id": 0, "bpm": 9999, "synced_at": "2099-01-01"}
> # 覆盖了历史数据 + 伪造时间戳 —— 安全漏洞！
> ```
>
> ```python
> # ✅ 安全：In/Out 分离，In 模型没有 id 和 synced_at
> # 客户端 POST 时根本无法传入 id，传了也会被 FastAPI 忽略
> POST /sync/upload  {"bpm": 72, ...}
> # 服务器：id 由 DB 自动生成，synced_at 由服务器设置 —— 安全！
> ```
>
> **完整的数据流向示意**：
>
> ```
> ┌─────────────────────────────────────────────────────────┐
> │  客户端 POST 请求                                        │
> │  {"bpm": 72, "sample_uuid": "abc", "recorded_at": "..."}│
> │  ↑ 只能包含 HeartRateIn 定义的字段                       │
> └──────────────────────┬──────────────────────────────────┘
>                       │ FastAPI 用 HeartRateIn 校验
>                       ▼
> ┌─────────────────────────────────────────────────────────┐
> │  数据库写入                                             │
> │  → id = 1523（自动生成）                                │
> │  → synced_at = 2026-07-04T10:00:01（服务器设置）        │
> └──────────────────────┬──────────────────────────────────┘
>                       │ FastAPI 用 HeartRateOut 过滤
>                       ▼
> ┌─────────────────────────────────────────────────────────┐
> │  返回给客户端的 JSON                                     │
> │  {"id":1523, "synced_at":"...", "bpm":72, ...}          │
> │  ↑ 多了系统字段 id 和 synced_at                          │
> └─────────────────────────────────────────────────────────┘
> ```
>
> | 模型 | 方向 | 谁定义字段 | 包含什么 |
> |------|------|-----------|----------|
> | `HeartRateIn` | 客户端 → 服务器 | 客户端 | 纯业务数据（`bpm`, `sample_uuid` 等） |
> | `HeartRateOut` | 服务器 → 客户端 | 服务器 | 业务数据 + 系统字段（`id`, `synced_at`） |
>
> > **一句话**：`In` 决定"客户端能发什么"，`Out` 决定"客户端能看到什么"。两套模型让服务器始终控制数据的可信边界——客户端不能伪造系统字段。
>
> 认证 Schema 采用同样的分离模式（`UserRegister` 含密码输入，`UserResponse` 不含密码输出），简化的字典风格 `model_config`（等效于 `ConfigDict`）：
>
> ```python
> # backend/app/schemas/auth.py - 请求/响应分离
> class UserRegister(BaseModel):
>     email: str
>     password: str
>     display_name: str
>
> class UserResponse(BaseModel):
>     id: int
>     email: str
>     display_name: str
>     created_at: str
>     last_sync_at: str | None = None
>     model_config = {"from_attributes": True}
> ```
>
> 通用分页模型展示了 Pydantic 的泛型用法（简化版）：
>
> ```python
> # backend/app/schemas/health.py - 通用分页响应
> class PaginatedResponse(BaseModel):
>     items: list            # 泛型数据列表
>     total: int             # 总记录数
>     page: int              # 当前页码
>     page_size: int         # 每页大小
>     total_pages: int       # 总页数
> ```

---

## 2. 字段类型大全

### 2.1 基本类型

```python
from pydantic import BaseModel, Field
from typing import Optional, Union, Literal
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from uuid import UUID
from pathlib import Path
from ipaddress import IPv4Address, IPv6Address

class TypeDemo(BaseModel):
    # === 基本类型 ===
    a_str: str                      # 字符串
    a_int: int                      # 整数
    a_float: float                  # 浮点数
    a_bool: bool                    # 布尔值
    a_bytes: bytes                  # 字节

    # === 可选类型 ===
    optional_str: Optional[str] = None  # str 或 None
    optional_int: int | None = None     # Python 3.10+ 简写

    # === 联合类型 ===
    id_field: Union[int, str]           # 可以是 int 或 str
    status: Literal["active", "inactive", "banned"]  # 只能取这几个值

    # === 日期时间 ===
    created_at: datetime = Field(default_factory=datetime.utcnow)
    birth_date: date
    start_time: time
    duration: timedelta

    # === 特殊类型 ===
    decimal_price: Decimal          # 精确小数（适合金额）
    user_id: UUID                   # UUID
    config_path: Path               # 文件路径
    ip: IPv4Address                 # IPv4 地址
```

### 2.2 集合类型

```python
from typing import List, Dict, Set, Tuple, FrozenSet
from pydantic import BaseModel

class CollectionDemo(BaseModel):
    # 列表
    tags: list[str] = []
    scores: list[int]
    # 等价写法
    tags_v2: List[str] = []

    # 字典
    metadata: dict[str, str] = {}
    prices: dict[str, float]
    # 等价写法
    prices_v2: Dict[str, float]

    # 集合
    unique_tags: set[str] = set()

    # 元组（固定长度和类型）
    coordinates: tuple[float, float]  # (x, y)

    # 不可变集合
    permissions: frozenset[str] = frozenset()
```

### 2.3 受限类型（Constrained Types）

```python
from pydantic import (
    BaseModel, Field,
    conint, confloat, constr, conlist, conset, condecimal
)

class ConstrainedDemo(BaseModel):
    # 受限整数：大于 0，小于等于 100
    score: conint(gt=0, le=100)

    # 受限浮点数：大于等于 0.0，小于等于 5.0，步长 0.5
    rating: confloat(ge=0.0, le=5.0, multiple_of=0.5)

    # 受限字符串：最小长度，最大长度，正则
    username: constr(min_length=3, max_length=20, pattern=r"^[a-zA-Z]\w+$")

    # 受限列表：最少 1 个元素，最多 10 个
    tags: conlist(str, min_length=1, max_length=10)

    # 受限 Decimal
    price: condecimal(gt=0, max_digits=10, decimal_places=2)

# 等价于使用 Field 的写法
class FieldDemo(BaseModel):
    score: int = Field(gt=0, le=100)
    rating: float = Field(ge=0.0, le=5.0)
    username: str = Field(min_length=3, max_length=20, pattern=r"^[a-zA-Z]\w+$")
```

---

## 3. 校验器深度使用

### 3.1 字段校验器 @field_validator

**Pydantic V2** 使用 `@field_validator`：

```python
from pydantic import BaseModel, field_validator, ValidationInfo
from typing import ClassVar

class UserRegistration(BaseModel):
    username: str
    password: str
    confirm_password: str
    email: str
    age: int

    # Pydantic V2 风格
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """校验用户名"""
        if len(v.strip()) < 3:
            raise ValueError("用户名至少 3 个字符")
        if not v.isalnum():
            raise ValueError("用户名只能包含字母和数字")
        return v.strip()

    @field_validator("age")
    @classmethod
    def validate_age(cls, v: int) -> int:
        """校验年龄"""
        if v < 0 or v > 150:
            raise ValueError("年龄必须在 0 到 150 之间")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """校验邮箱并转换为小写"""
        v = v.strip().lower()
        if "@" not in v:
            raise ValueError("邮箱格式不正确")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info: ValidationInfo) -> str:
        """确认密码与密码一致"""
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("两次密码不一致")
        return v
```

### 3.2 模型校验器 @model_validator

用于跨字段校验：

```python
from pydantic import BaseModel, model_validator
from typing import Optional

class OrderCreate(BaseModel):
    subtotal: float
    discount: float = 0
    shipping: float = 0
    total: Optional[float] = None

    @model_validator(mode="after")
    def calculate_total(self):
        """自动计算总价"""
        self.total = max(0, self.subtotal - self.discount + self.shipping)
        return self

    # mode="before" 在字段校验前执行
    @model_validator(mode="before")
    @classmethod
    def ensure_discount_not_negative(cls, data):
        """确保折扣不为负数"""
        if isinstance(data, dict) and data.get("discount", 0) < 0:
            data["discount"] = 0
        return data
```

### 3.3 校验器执行顺序

```
1. @model_validator(mode="before")       ← 字段校验前
2. @field_validator("field1")
3. @field_validator("field2")
4. ...（按类中定义顺序）
5. @model_validator(mode="after")         ← 字段校验后
```

### 3.4 校验器复用

```python
from pydantic import field_validator

def no_whitespace_validator(v: str) -> str:
    """通用校验器：去除前后空格，检查非空"""
    v = v.strip()
    if not v:
        raise ValueError("不能为空或全空格")
    return v

def normalize_lowercase(v: str) -> str:
    """通用校验器：转为小写"""
    return v.strip().lower()

class Product(BaseModel):
    name: str
    category: str
    code: str

    # 复用校验器
    _validate_name = field_validator("name")(no_whitespace_validator)
    _validate_category = field_validator("category")(no_whitespace_validator)
    _normalize_code = field_validator("code")(normalize_lowercase)
```

---

## 4. 模型配置 Config

### 4.1 ConfigDict 完整选项

```python
from pydantic import BaseModel, ConfigDict

class User(BaseModel):
    id: int
    name: str
    email: str
    private_notes: str = ""

    # Pydantic V2 配置
    model_config = ConfigDict(
        # ORM 支持
        from_attributes=True,        # 允许从 ORM 对象创建

        # 序列化
        populate_by_name=True,       # 允许用字段名或别名填充
        use_enum_values=True,        # 枚举序列化为值而非名称

        # 校验
        str_strip_whitespace=True,   # 自动去除字符串空格
        str_min_length=1,            # 字符串最小长度
        validate_assignment=True,    # 赋值时校验
        validate_default=True,       # 默认值也校验
        extra="forbid",              # 禁止额外字段（"allow" / "ignore" / "forbid"）

        # 其他
        frozen=False,                # True = 不可变模型
        arbitrary_types_allowed=True, # 允许任意类型

        # 文档
        json_schema_extra={
            "example": {"id": 1, "name": "张三", "email": "zhangsan@example.com"}
        }
    )
```

### 4.2 extra 参数详解

```python
# extra="forbid"：禁止多余字段
class StrictUser(BaseModel):
    name: str
    model_config = ConfigDict(extra="forbid")

# extra="ignore"：忽略多余字段（默认）
class LooseUser(BaseModel):
    name: str
    model_config = ConfigDict(extra="ignore")  # 默认行为

# extra="allow"：保留多余字段
class FlexibleUser(BaseModel):
    name: str
    model_config = ConfigDict(extra="allow")

# 示例
data = {"name": "张三", "age": 25, "hobby": "reading"}

StrictUser(**data)   # ❌ ValidationError: Extra inputs are not permitted
LooseUser(**data)    # ✅ User(name="张三")  age 和 hobby 被忽略
FlexibleUser(**data) # ✅ 包含所有额外字段
```

---

## 5. 模型序列化与导出

### 5.1 导出方法对照

```python
from pydantic import BaseModel
from datetime import datetime

class Item(BaseModel):
    id: int
    name: str
    price: float
    created_at: datetime = Field(default_factory=datetime.now)
    tags: list[str] = []

# Pydantic V1 → V2 方法对照
# .dict()              → .model_dump()
# .json()              → .model_dump_json()
# .copy()              → .model_copy()
# .parse_obj(data)     → .model_validate(data)
# .parse_raw(json)     → .model_validate_json(json)
# .schema()            → .model_json_schema()
# .schema_json()       → .model_json_schema()
# .update_forward_refs() → .model_rebuild()
# .construct()         → .model_construct()
# .__fields__          → .model_fields
# .__validators__      → .model_validators
```

### 5.2 model_dump() 参数

```python
item = Item(id=1, name="测试", price=9.99, tags=["热门"])

# 基本导出
item.model_dump()                    # {"id": 1, "name": "测试", "price": 9.99, ...}

# 排除字段
item.model_dump(exclude={"created_at"})
# 包含字段
item.model_dump(include={"id", "name", "price"})

# 排除未设置的字段（使用默认值的字段）
item.model_dump(exclude_unset=True)
# 排除默认值
item.model_dump(exclude_defaults=True)

# 排除 None
item.model_dump(exclude_none=True)

# 使用别名
item.model_dump(by_alias=True)

# JSON 序列化
item.model_dump_json()               # JSON 字符串
item.model_dump_json(indent=2)       # 格式化 JSON
```

### 5.3 别名与序列化名称

```python
from pydantic import BaseModel, Field

class UserDTO(BaseModel):
    # 数据库字段名和 API 字段名不同
    user_name: str = Field(alias="userName")           # 接收 userName
    first_name: str = Field(serialization_alias="firstName")  # 返回 firstName
    is_active: bool = Field(
        alias="status",                                # 接收时用 status
        serialization_alias="isActive"                 # 返回时用 isActive
    )

# 接收：{"userName": "zhangsan", "status": true, "firstName": "张"}
# 返回：{"userName": "zhangsan", "firstName": "张", "isActive": true}
```

---

## 6. 泛型模型

```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PageResponse(BaseModel, Generic[T]):
    """通用分页响应模型"""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

# 使用
from pydantic import Field

class BookSummary(BaseModel):
    id: int
    title: str
    author: str

class UserBrief(BaseModel):
    id: int
    username: str

# 具体化泛型
BookPage = PageResponse[BookSummary]
UserPage = PageResponse[UserBrief]

# 在 FastAPI 中使用
@app.get("/books/", response_model=PageResponse[BookSummary])
def list_books():
    return {...}
```

---

## 📝 最佳实践总结

| 场景 | 推荐做法 |
|------|----------|
| API Schema 命名 | `XxxCreate` / `XxxUpdate` / `XxxResponse` |
| 敏感字段 | 用单独的 Response 模型排除 |
| 跨字段校验 | 用 `@model_validator` |
| 可复用校验 | 抽取为独立函数，用 `@field_validator` 复用 |
| 生产环境 | 设置 `extra="forbid"` 防止多余字段 |
| ORM 兼容 | 设置 `from_attributes=True` |
| JSON 导出 | 用 `model_dump(mode="json")` 而非手动 `json.dumps` |

---

**返回**：[FastAPI学习路线.md](./FastAPI学习路线.md)
