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
| `400001` | `400` | 不支持的文件类型（仅 jpg/png/webp/gif） |
| `400004` | `400` | object_key 非法 |
| `404002` | `404` | 图片不存在 |
| `413001` | `413` | 文件大小超过限制（最大 10MB） |
| `500001` | `500` | 文件上传失败（对象存储写入错误） |
| `500002` | `500` | 图片删除失败（对象存储删除错误） |

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
| `POST` | `/upload/image` | `ApiResponse[UploadImageResponse]` | 上传单张图片到对象存储 |
| `DELETE` | `/upload/image` | `ApiResponse[DeleteImageResponse]` | 按 object_key 删除单张图片 |

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

## 9. 图片上传与删除

图片存储在 MinIO（S3 协议兼容）对象存储中。两个接口都需要鉴权（`Authorization: Bearer <access_token>`）。

### `POST /upload/image`

上传单张图片。请求格式为 `multipart/form-data`，字段名为 `file`。

请求头：

```http
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

请求字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `file` | file | 是 | 待上传的图片文件 |

校验规则：

- 类型：仅 `jpg` / `png` / `webp` / `gif`，按文件 magic number 判断，**不信任** `Content-Type`
- 大小：最大 `10MB`，分块读取，超限立即中止
- object_key 由服务端生成，格式为 `images/{yyyy}/{mm}/{dd}/{uuid}.{ext}`

成功响应：

```json
{
  "code": 200,
  "message": "success",
  "request_id": "req_123",
  "data": {
    "object_key": "images/2026/05/30/3f2a...c1.jpg",
    "content_type": "image/jpeg",
    "extension": "jpg",
    "size": 184320,
    "original_filename": "fish.jpg"
  }
}
```

响应字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `object_key` | string | 对象存储中的 key，删除/引用时使用 |
| `content_type` | string | 服务端按 magic number 检测出的 MIME |
| `extension` | string | 文件扩展名，例如 `jpg` |
| `size` | integer | 文件大小，单位字节 |
| `original_filename` | string \| null | 客户端上传时的原始文件名 |

错误：`400001`（类型不支持）、`413001`（超过 10MB）、`401002`（未登录/token 无效）、`500001`（对象存储写入失败）。

### `DELETE /upload/image`

按 object_key 删除单张图片。请求体为 JSON。

请求头：

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

请求体：

```json
{
  "object_key": "images/2026/05/30/3f2a...c1.jpg"
}
```

请求字段：

| 字段 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| `object_key` | string | 是 | 非空，须以 `images/` 开头且不含 `..` | 上传成功后返回的 object_key |

成功响应：

```json
{
  "code": 200,
  "message": "success",
  "request_id": "req_123",
  "data": {
    "object_key": "images/2026/05/30/3f2a...c1.jpg"
  }
}
```

当前行为与说明：

- key 校验只允许操作 `images/` 前缀下的对象，防止越权删除 bucket 内其它命名空间
- 删除前先 `head_object` 探测存在性：不存在返回 `404002`，而不是静默成功
- object_key **未编码用户归属**，因此任意登录用户均可删除任意图片；若需"仅能删自己的"，需在 key 中编码 user_id 或引入图片归属表

错误：`400004`（object_key 非法）、`404002`（图片不存在）、`401002`（未登录/token 无效）、`500002`（对象存储删除失败）。

## 10. 当前未实现

以下能力在旧文档中出现过，但当前后端没有对应路由，不能按已实现接口使用：

- 创建会话接口
- 会话详情接口
- 消息历史接口
- 非流式问答接口
- refresh token 续签接口
- 登出接口
- 结构化诊断接口
- 知识库疾病检索接口
- 用户反馈接口

## 11. 现有差距

按现有代码，下一步最应该补的是：

1. 将 `get_current_user_id()` 改为解析并校验 access token
2. 增加 `POST /auth/refresh`
3. 给参数校验异常增加统一响应处理器
4. 为 `conversation/list` 定义明确的响应 schema，避免直接暴露 ORM 字段名
5. 决定 `message.images` 是否进入模型调用；如果暂不支持，应从请求 schema 中移除或文档明确标注
