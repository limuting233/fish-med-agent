# Backend — Fish Med Agent

> 给 Claude / 新加入的开发者读的项目说明。优先于猜测，看完再动代码。

## 一句话定位

面向水产养殖场景的鱼病问答 Agent 的后端服务，基于 FastAPI + PostgreSQL + DeepSeek（LLM），最终目标接入 LightRAG 做知识检索召回。当前处于早期开发阶段，**尚未公网上线**。

## 技术栈

- Python `>=3.12,<4.0`
- 依赖管理：`uv`
- Web 框架：FastAPI + Uvicorn
- 数据库：PostgreSQL（异步驱动 `asyncpg`，同步驱动 `psycopg` 给 alembic 用）
- ORM：SQLAlchemy 2.x（async）
- 迁移：Alembic
- 配置：pydantic-settings（读 `.env.{ENV}`）
- 鉴权：PyJWT（access + refresh 双 token） + `pwdlib[argon2]` 哈希密码
- 日志：Loguru（统一拦截 stdlib `logging`）
- LLM：OpenAI SDK 兼容协议，base_url 指向 DeepSeek
- 计划接入：LightRAG（HTTP 服务，跑在另一个进程，目前未集成）

## 目录结构与分层约定

```
backend/
├── alembic/                       数据库迁移脚本
│   ├── env.py                     从 settings 拼 sqlalchemy.url
│   └── versions/                  迁移文件
├── alembic.ini
├── scripts/
│   └── insert_user.py             命令行创建用户 (没有注册接口前用这个)
├── src/fish_med_agent/
│   ├── main.py                    FastAPI app 工厂, CORS + 中间件 + 异常处理器注册
│   ├── api/
│   │   ├── deps.py                FastAPI 依赖: get_db, get_current_user_id (JWT 解析)
│   │   └── v1/
│   │       ├── router.py          v1 路由聚合
│   │       └── endpoints/         具体端点 (auth, chat, conversation, healthz)
│   ├── core/
│   │   ├── config.py              Settings (pydantic-settings)
│   │   ├── exception.py           业务异常类 (BizException 及子类)
│   │   ├── handlers.py            BizException → 统一 ApiResponse 响应
│   │   ├── logging.py             Loguru 配置 + RequestId ContextVar
│   │   ├── middleware.py          RequestIdMiddleware
│   │   └── security.py            密码哈希 + JWT 编解码
│   ├── db/
│   │   ├── engine.py              async_engine (连接池配置)
│   │   └── session.py             AsyncSessionLocal 工厂
│   ├── models/                    SQLAlchemy ORM 模型, 继承 Base
│   │   ├── base.py                Base 含 id/created_at/updated_at/deleted_at
│   │   ├── user.py
│   │   └── conversation.py
│   ├── repositories/              数据访问层, 只写 SQL/ORM 查询, 不写业务
│   ├── schemas/                   Pydantic 请求/响应模型
│   │   └── response.py            ApiResponse 统一响应封装
│   └── service/                   业务逻辑层, 编排 repo + 外部服务
└── .env.dev                       本地开发配置 (gitignore 中)
```

### 分层规则（重要）

```
endpoint  →  service  →  repository  →  model
   |           |             |
   |           |             └─ 只跟 ORM 打交道, 不调外部, 不抛业务异常
   |           └─ 业务编排, 调多个 repo / 外部服务, 抛 BizException
   └─ HTTP 协议层: 解请求参数, 调 service, 包 ApiResponse 返回
```

- **endpoint 里不写业务逻辑**：超过 5 行业务代码就该挪到 service
- **service 不直接执行 SQL**：所有 ORM 操作走 repository
- **repository 不抛业务异常**：让 service 决定 "没查到 → 抛什么 / 返回 None"
- **schemas 跟 models 严格分开**：`models/` 是 DB 表，`schemas/` 是 API 契约，不要混用

## 启动 & 常用命令

所有命令在 `backend/` 目录下执行。

```bash
# 装依赖 (首次 / 拉到新依赖后)
uv sync

# 启动 dev server (热重载)
uv run uvicorn fish_med_agent.main:app --reload --port 8000

# 数据库迁移
uv run alembic upgrade head                        # 应用所有迁移
uv run alembic revision --autogenerate -m "msg"    # 根据模型变更生成迁移
uv run alembic downgrade -1                        # 回退一步
uv run alembic current                             # 看当前版本

# 创建用户 (注册接口未实现前用这个)
uv run python scripts/insert_user.py --username polo --nickname 老李
```

OpenAPI 文档：http://localhost:8000/docs

## 配置体系

- 所有配置在 [src/fish_med_agent/core/config.py](src/fish_med_agent/core/config.py) 的 `Settings` 类里集中声明
- 通过 `ENV` 环境变量决定加载哪个 `.env.{ENV}` 文件（默认 `dev`）
- `.env.*` **不能进 git**（已在根 `.gitignore` 中），改动配置时同步更新所有人的本地 `.env.dev` 靠协作沟通
- 生产环境**不依赖 `.env` 文件**，配置走环境变量 / Secret Manager 注入（pydantic-settings 默认会读环境变量，优先级高于 env_file）

### 已知拼写问题

`COOKIE_SAMEITE` 是 `COOKIE_SAMESITE` 的拼写错误（少 S 多 I），整个项目都跟着错。短期保持错误拼写以免连锁修改，长期建议批量改正。

## 统一约定

### 1. 接口响应

所有非流式接口必须包 `ApiResponse`（[schemas/response.py](src/fish_med_agent/schemas/response.py)）：

```python
return success_response(request_id=request_id, data=...)
```

响应结构：

```json
{ "code": 200, "message": "success", "request_id": "req_xxx", "data": {...} }
```

流式接口（chat/stream）走 SSE，不包 ApiResponse。

### 2. 异常处理

- 业务错误**必须抛 `BizException` 的子类**，由 [core/handlers.py](src/fish_med_agent/core/handlers.py) 统一转成 ApiResponse 格式
- 新增业务错误：在 [core/exception.py](src/fish_med_agent/core/exception.py) 里加一个子类，定义 `code` / `message` / `status_code`
- **绝对不要**在 endpoint 里 `raise HTTPException`，破坏统一响应格式

### 3. 日志

```python
from fish_med_agent.core.logging import get_logger
logger = get_logger(__name__)
```

- Loguru 已配好，自动注入 `request_id`（从 `RequestIdMiddleware` 设的 ContextVar 取）
- 生产环境 `LOG_JSON=true`，dev `LOG_JSON=false`（彩色可读）
- **绝对不要 log token / 密码 / API key 等敏感信息**（即使 DEBUG 级别）
- 异常用 `logger.exception(...)` 自带 traceback

### 4. 数据库

- 所有 ORM 模型继承 [models/base.py](src/fish_med_agent/models/base.py) 的 `Base`，自带 `id` / `created_at` / `updated_at` / `deleted_at`
- **软删除**：用 `deleted_at IS NULL` 过滤，不要物理删除
- 查询过滤模板：`where(..., Xxx.deleted_at.is_(None))`，必要时加 `is_active == True`
- session 通过 `get_db` 依赖获取，**不要**在 endpoint/service 里自己 `AsyncSessionLocal()`
- 修改 model 后必须 `alembic revision --autogenerate -m "..."`，autogenerate 结果要人工 review

### 5. 鉴权

- access_token 走 `Authorization: Bearer <token>` 头，1 小时有效
- refresh_token 走 HttpOnly Cookie（path 限定 `/api/v1/auth/token/refresh`），7 天有效
- 需要鉴权的 endpoint 在参数里加 `current_user_id: int = Depends(get_current_user_id)`
- `get_current_user_id` 会校验 `type == "access"`、过期、签名等，失败抛 `InvalidTokenError`
- refresh 接口对称校验 `type == "refresh"`

## 当前已实现的接口（v1）

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/api/v1/healthz` | 否 | 健康检查 |
| POST | `/api/v1/auth/login` | 否 | 用户名密码登录 |
| GET | `/api/v1/auth/me` | 是 | 获取当前用户信息 |
| POST | `/api/v1/auth/token/refresh` | Cookie | 凭 refresh_token 轮换签发新 token 对 |
| GET | `/api/v1/conversation/list` | 是 | 当前用户的会话列表 |
| POST | `/api/v1/chat/stream` | 是 | SSE 流式对话（DeepSeek） |

完整契约见根目录 [API.md](../API.md)（部分内容可能滞后于代码）。

## 关键设计与历史决策

- **双 token 模式**：access 短期 + refresh 长期，refresh 走 Cookie，每次 refresh 都**轮换**（rotation）。当前未做"真·防重放"（旧 token 用过后强制失效），后续可在用户表加 `token_version` 实现
- **DI 风格鉴权**：用 `Depends(get_current_user_id)` 显式标注，不做全局拦截器。考虑未来按 router 级别 `dependencies=[...]` 把鉴权变成"默认开"
- **LLM 解耦**：用 OpenAI SDK 调 DeepSeek（兼容协议）。未来要换模型只改 `DEEPSEEK_*` 配置
- **会话消息存 JSONB**：`Conversation.messages` 是 JSONB 字段，不拆 messages 表。优点是简单，缺点是消息量大后查询不灵活；早期阶段够用

## 已知待办 / 不要踩的坑

### 必须在公网上线前处理（按优先级）

1. **`get_current_user_id` 当前已经接 JWT**，但 [API.md](../API.md) 第 3 节文档过时（仍说"固定返回 1"），文档要更新
2. **登录接口无速率限制**——`/auth/login` 可被无限暴力破解，上线前必须接 `slowapi` + Redis
3. **`JWT_SECRET_KEY` 在 dev 用弱密钥**——生产必须用 `secrets.token_urlsafe(64)` 生成的强随机值，且走 Secret Manager
4. **CORS 当前只放行 localhost**（[main.py](src/fish_med_agent/main.py)），上线前改成生产域名白名单
5. **`LOG_LEVEL=DEBUG` + `ECHO_SQL=true` 是 dev 配置**，生产必须 INFO + false
6. **refresh token 无法主动吊销**——用户改密码 / 强制登出已签发的 token 仍有效。最小成本方案：用户表加 `token_version` 字段写进 JWT payload，校验时对比
7. **没有 logout 接口**——需要补，做法是 `set_cookie(max_age=0)` + （可选）失效 token_version

### 功能性 TODO

- 用户注册 / 邮箱手机验证码 / 密码重置流程全部没有
- 文件 / 图片上传未实现（[schemas/chat.py](src/fish_med_agent/schemas/chat.py) 的 `Message.images` 已经留了字段但后端没处理）
- LightRAG 检索召回未集成（计划把 `POST /query/data` 包成 LLM 的 tool，做成 tool-use 模式的 agent）
- chat_service 里 `# todo 计算messages的token数` 未实现，长对话会超模型上下文

### 代码层面已知问题

- `core/config.py` 字段名 `COOKIE_SAMEITE` 是 typo（应为 SAMESITE），整个项目跟着错，**改要一起改**
- [chat_service.py](src/fish_med_agent/service/chat_service.py) 异常时 yield 的 error 消息可能在 SSE 已开始后才发，前端要处理"流到一半挂掉"的情况
- `Conversation.messages` 是 JSONB，list 拼接后赋值才能触发 SQLAlchemy dirty 检测（不能 `.append()` 原地改），现在的代码已经是用 `+` 拼新 list 是对的，**改这块要保留这个模式**

## 添加新接口的工作流

1. 在 `models/` 加表（如果需要新表）→ `alembic revision --autogenerate -m "..."` → 人工 review 迁移
2. 在 `schemas/` 加请求/响应模型
3. 在 `repositories/` 加 `XxxRepo` 类，只写查询
4. 在 `service/` 加 `XxxService` 类，编排业务
5. 在 `api/v1/endpoints/` 加 endpoint，**包 `ApiResponse`，标 `response_model`**
6. 在 `api/v1/router.py` 注册 router
7. 业务异常加在 `core/exception.py`，继承 `BizException`
8. 更新根目录 [API.md](../API.md)

## 注意事项 / 反模式

- **不要**在 endpoint 里直接操作 ORM，必须走 repository
- **不要** `from xxx import *`
- **不要**用 `print`，统一 `logger`
- **不要**在 service 里返 ORM 对象给 endpoint（看情况；当前代码混着用，新代码建议返 dataclass / dict / schema，避免 endpoint 误碰到延迟加载字段触发 N+1）
- **不要**手写时间字符串，统一 `datetime.now(timezone.utc)`
- **不要** `raise HTTPException`，用 `BizException` 子类
- **不要**把 token、password、API key 写进日志
- **不要**在生产环境 `git add .env.*`

## 协作

- 提交前自己跑一遍 `uv run uvicorn ...` 至少打开 `/docs` 验证路由能加载
- 新增依赖：`uv add <pkg>`，不要手动改 `pyproject.toml`
- PR 描述里说明：改了哪些表 / 是否需要跑迁移 / 是否改了 `.env` 字段（要通知所有人）
