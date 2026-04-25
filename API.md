# Fish Med Agent API 文档

## 1. 当前范围

本文档只描述当前后端代码已经注册的 `v1` 接口，不包含规划接口。

- Base URL：`/api/v1`
- 数据格式：`application/json`
- 除流式接口外，响应统一使用 `ApiResponse`
- 请求 ID 由 `RequestIdMiddleware` 写入 `X-Request-Id` 响应头

当前路由来自：

- `backend/src/fish_med_agent/api/v1/router.py`
- `backend/src/fish_med_agent/api/v1/endpoints/*.py`

## 2. 统一响应

非流式接口成功响应：

```json
{
  "code": 200,
  "message": "success",
  "request_id": "req_xxx",
  "data": {}
}
```

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | integer | 业务状态码，成功固定为 `200` |
| `message` | string | 状态说明，成功为 `success` |
| `request_id` | string | 请求链路 ID |
| `data` | any | 业务数据 |

业务异常响应：

```json
{
  "code": 401001,
  "message": "用户名或密码错误",
  "request_id": "req_xxx",
  "data": null
}
```

当前业务错误码：

| code | HTTP 状态码 | 说明 |
| --- | --- | --- |
| `401001` | `401` | 用户名或密码错误 |
| `401002` | `401` | 无效 token |

说明：FastAPI/Pydantic 参数校验错误仍使用框架默认 `422` 响应格式；当前项目尚未封装统一校验异常处理器。

## 3. 鉴权现状

登录接口会签发：

- `access_token`
- `refresh_token`

前端请求工具会按 Bearer Token 方式发送：

```http
Authorization: Bearer <access_token>
```

但当前后端 `get_current_user_id()` 仍固定返回 `1`，没有实际解析 `Authorization` 请求头。因此：

- `POST /auth/login` 已实现真实用户名密码校验和 token 签发
- `GET /conversation/list`、`POST /chat/stream` 代码上依赖 `current_user_id`
- 当前 `current_user_id` 实际恒为 `1`

## 4. 接口总览

| 方法 | 路径 | 响应类型 | 说明 |
| --- | --- | --- | --- |
| `GET` | `/healthz` | `ApiResponse[dict]` | 健康检查 |
| `POST` | `/auth/login` | `ApiResponse[TokenResponse]` | 登录并签发 token |
| `GET` | `/conversation/list` | `ApiResponse[list[dict]]` | 获取当前用户会话列表 |
| `POST` | `/chat/stream` | `text/event-stream` | 流式聊天 |

## 5. 健康检查

### `GET /healthz`

用于服务健康探测。

请求参数：无。

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "request_id": "req_123",
  "data": {
    "status": "ok",
    "service": "fish-med-agent",
    "service_version": "0.1.0",
    "api_version": "v1"
  }
}
```

## 6. 登录

### `POST /auth/login`

使用用户名和密码登录。密码会通过 `pwdlib` 的 `PasswordHash` 校验，数据库中应保存哈希后的密码。

请求体：

```json
{
  "username": "admin",
  "password": "your-password"
}
```

请求字段：

| 字段 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| `username` | string | 是 | `1..64` | 用户名 |
| `password` | string | 是 | `1..128` | 密码 |

成功响应：

```json
{
  "code": 200,
  "message": "success",
  "request_id": "req_123",
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

响应字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `access_token` | string | 访问令牌 |
| `refresh_token` | string | 刷新令牌 |
| `token_type` | string | 固定为 `bearer` |
| `expires_in` | integer | access token 过期时间，单位秒 |

用户名不存在、用户禁用、密码错误时返回：

```json
{
  "code": 401001,
  "message": "用户名或密码错误",
  "request_id": "req_123",
  "data": null
}
```

## 7. 会话列表

### `GET /conversation/list`

返回当前用户的会话列表。

请求参数：无。

当前用户来源：`get_current_user_id()`，现阶段固定为 `1`。

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "request_id": "req_123",
  "data": [
    {
      "id": 1,
      "title": "草鱼白点病",
      "user_id": 1,
      "summary": null,
      "messages": [
        {
          "role": "user",
          "content": "这条草鱼身上有白点",
          "created": "2026-04-25T10:00:00+00:00"
        }
      ],
      "metadata_": {
        "last_message_at": "2026-04-25T10:01:00+00:00"
      },
      "created_at": "2026-04-25T10:00:00+00:00",
      "updated_at": "2026-04-25T10:01:00+00:00",
      "deleted_at": null
    }
  ]
}
```

说明：

- 响应直接来自 `Conversation.to_dict()`
- `metadata_` 是 SQLAlchemy 模型字段名，对应数据库列 `metadata`
- 当前接口没有分页
- 排序依据为 `metadata["last_message_at"]` 倒序

## 8. 流式聊天

### `POST /chat/stream`

用于流式返回模型回复，响应类型为 SSE。

请求头：

```http
Content-Type: application/json
Accept: text/event-stream
```

请求体：

```json
{
  "conversation_id": 1,
  "message": {
    "content": "这条草鱼身上有白点，还经常蹭池壁，帮我判断一下",
    "images": [
      "https://example.com/fish_001.jpg"
    ]
  }
}
```

请求字段：

| 字段 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| `conversation_id` | integer | 是 | - | 会话 ID |
| `message.content` | string | 是 | 最少 1 个字符 | 用户文本 |
| `message.images` | array[string] | 否 | - | 图片 URL 列表；当前模型调用未使用该字段 |

额外字段：禁止。`ChatRequest` 配置了 `extra="forbid"`。

当前行为：

- 如果 `conversation_id` 对应会话不存在，会自动创建新会话
- 新会话标题为 `message.content` 前 10 个字符
- 当前用户 ID 来自 `get_current_user_id()`，现阶段固定为 `1`
- 模型调用只传入文本历史，不传图片
- 成功结束后保存 user 和 assistant 两条消息
- 模型异常时回滚数据库，并返回 `error` SSE 事件

SSE 事件：

| event | data | 说明 |
| --- | --- | --- |
| `start` | `{}` | 流开始 |
| `message.delta` | `{"content":"..."}` | 模型文本增量 |
| `done` | `{}` | 流结束 |
| `error` | `{"message":"模型响应失败，请稍后重试"}` | 模型调用或保存失败 |

SSE 示例：

```text
event: start
data: {}

event: message.delta
data: {"content":"从图片和描述看，"}

event: message.delta
data: {"content":"疑似小瓜虫病。"}

event: done
data: {}
```

## 9. 当前未实现

以下能力在旧文档中出现过，但当前后端没有对应路由，不能按已实现接口使用：

- 图片上传
- 创建会话接口
- 会话详情接口
- 消息历史接口
- 非流式问答接口
- refresh token 续签接口
- 登出接口
- 结构化诊断接口
- 知识库疾病检索接口
- 用户反馈接口

## 10. 现有差距

按现有代码，下一步最应该补的是：

1. 将 `get_current_user_id()` 改为解析并校验 access token
2. 增加 `POST /auth/refresh`
3. 给参数校验异常增加统一响应处理器
4. 为 `conversation/list` 定义明确的响应 schema，避免直接暴露 ORM 字段名
5. 决定 `message.images` 是否进入模型调用；如果暂不支持，应从请求 schema 中移除或文档明确标注
