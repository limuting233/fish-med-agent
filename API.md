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
| `400002` | `400` | 不支持的视频格式（仅 mp4/webm/mov） |
| `400003` | `400` | 视频文件损坏或无法解析 |
| `400004` | `400` | object_key 非法 |
| `404002` | `404` | 图片不存在 |
| `404003` | `404` | 视频不存在 |
| `413001` | `413` | 图片大小超过限制（最大 10MB） |
| `413002` | `413` | 视频大小超过限制（最大 50MB） |
| `413003` | `413` | 视频时长超过限制（最大 30 秒） |
| `500001` | `500` | 文件上传失败（对象存储写入错误） |
| `500002` | `500` | 图片删除失败（对象存储删除错误） |

说明：FastAPI/Pydantic 参数校验错误仍使用框架默认 `422` 响应格式；当前项目尚未封装统一校验异常处理器。

## 3. 鉴权现状

登录接口会签发：

- `access_token`（Bearer Token）
- `refresh_token`（HttpOnly Cookie，path 限定 `/api/v1/auth/token/refresh`）

需要鉴权的接口请在请求头携带：

```http
Authorization: Bearer <access_token>
```

`get_current_user_id()` 会解析并校验 access token（类型 / 过期 / 签名），失败抛 `InvalidAccessTokenError`（401002）。所有标注"鉴权必须"的接口都走这个依赖。

## 4. 接口总览

| 方法 | 路径 | 响应类型 | 说明 |
| --- | --- | --- | --- |
| `GET` | `/healthz` | `ApiResponse[dict]` | 健康检查 |
| `POST` | `/auth/login` | `ApiResponse[TokenResponse]` | 登录并签发 token |
| `GET` | `/conversation/list` | `ApiResponse[list[dict]]` | 获取当前用户会话列表 |
| `POST` | `/chat/stream` | `text/event-stream` | 流式聊天（支持带图 / 带视频） |
| `POST` | `/upload/image` | `ApiResponse[UploadImageResponse]` | 上传单张图片到对象存储 |
| `POST` | `/upload/image/presign` | `ApiResponse[PresignResponse]` | 批量为已有图片 object_key 生成 presigned URL |
| `DELETE` | `/upload/image` | `ApiResponse[DeleteImageResponse]` | 按 object_key 删除单张图片 |
| `POST` | `/upload/video` | `ApiResponse[UploadVideoResponse]` | 上传单段视频到对象存储（ffmpeg 解析时长） |
| `POST` | `/upload/video/presign` | `ApiResponse[PresignResponse]` | 批量为已有视频 object_key 生成 presigned URL |
| `DELETE` | `/upload/video` | `ApiResponse[DeleteVideoResponse]` | 按 object_key 删除单段视频 |

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

当前用户来源：`get_current_user_id()`，从 access token 中解析。

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

用于流式返回模型回复，响应类型为 SSE。鉴权必须。

请求头：

```http
Authorization: Bearer <access_token>
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
      {
        "object_key": "images/2026/05/30/abc.png",
        "content_type": "image/png",
        "extension": "png",
        "size": 162640,
        "original_filename": "图片3.png",
        "url": "http://localhost:9000/fish-med-agent/images/2026/05/30/abc.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...",
        "url_expires_at": 1780164807101
      }
    ],
    "videos": [
      {
        "object_key": "videos/2026/05/30/def.mp4",
        "content_type": "video/mp4",
        "extension": "mp4",
        "size": 4521800,
        "duration_seconds": 12.4,
        "original_filename": "swim.mp4",
        "url": "http://localhost:9000/fish-med-agent/videos/2026/05/30/def.mp4?X-Amz-...",
        "url_expires_at": 1780164807101
      }
    ]
  }
}
```

请求字段：

| 字段 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| `conversation_id` | integer | 是 | 新会话传 `0` | 会话 ID。不存在时后端自动创建 |
| `message.content` | string | 是 | 最少 1 个字符 | 用户文本 |
| `message.images` | array[`ImageInput`] | 否 | 见下方件数总约束 | 上传接口返回的整个 `data` 对象，前端直接透传 |
| `message.videos` | array[`VideoInput`] | 否 | 见下方件数总约束 | 上传接口返回的整个 `data` 对象，前端直接透传 |

> **件数总约束**：`len(images) + len(videos) ≤ 6`，混发也行（如 4 图 + 2 视频）。超过返回 422。每段视频后端会固定抽 3 帧（首/中/尾）送视觉模型，所以视频件数对耗时和成本的影响约等于 3 张图。

**`ImageInput` 结构**（与 `POST /upload/image` 返回的 `data` 字段对齐）：

| 字段 | 类型 | 必填 | 后端使用 | 说明 |
| --- | --- | --- | --- | --- |
| `object_key` | string | 是 | ✅ | MinIO 对象 key，后端用它取原图喂给视觉模型 |
| `content_type` | string | 是 | ✅ | MIME 类型，须匹配 `image/(jpeg|png|webp|gif)` |
| `extension` | string | 是 | - | 文件扩展名 |
| `size` | integer | 是 | - | 字节数，`>= 0` |
| `original_filename` | string \| null | 否 | - | 原始文件名，仅用于日志展示 |
| `url` | string | 否 | - | 前端展示用 URL；后端**忽略**，仅 upload response 携带方便前端透传 |
| `url_expires_at` | integer | 否 | - | URL 过期时间戳；后端**忽略**，同上 |

**`VideoInput` 结构**（与 `POST /upload/video` 返回的 `data` 字段对齐）：

| 字段 | 类型 | 必填 | 后端使用 | 说明 |
| --- | --- | --- | --- | --- |
| `object_key` | string | 是 | ✅ | MinIO 对象 key，必须在 `videos/` 前缀下 |
| `content_type` | string | 是 | ✅ | MIME，须匹配 `video/(mp4|webm|quicktime)` |
| `extension` | string | 是 | - | 文件扩展名 |
| `size` | integer | 是 | - | 字节数 |
| `duration_seconds` | number | 是 | - | 视频时长（秒），由上传接口测得 |
| `original_filename` | string \| null | 否 | - | 原始文件名，仅用于日志/帧描述前缀 |
| `url` / `url_expires_at` | - | 否 | - | 前端展示用，后端**忽略** |

> 前端无需挑字段，把 `POST /upload/image` / `POST /upload/video` 返回的 `data` 对象整体塞进对应数组即可。`ImageInput` / `VideoInput` 默认 `extra="ignore"`，多余字段静默忽略。

额外字段策略：`ChatRequest` 顶层配置 `extra="forbid"`（多传顶层字段会 422），但嵌套对象按各自默认（`ignore`）处理。

当前行为：

- 如果 `conversation_id` 对应会话不存在，会自动创建新会话；新会话标题为 `message.content` 前 10 个字符
- 当前用户 ID 来自 `get_current_user_id()`，从 access token 解析
- **带媒体请求**：进入主对话循环前，先并行调 MiMo VLM 处理所有图片和视频帧：
  - 图片：每张直接喂视觉模型拿一句中文描述
  - 视频：每段视频按 `(0.5/n, 1.5/n, 2.5/n) × duration` 均匀抽 3 帧（如 12s 视频 → 2s / 6s / 10s），每帧独立喂视觉模型
  - **图片描述 + 视频帧描述共享同一个全局 `Semaphore(6)`**，避免一次消息把 MiMo 打爆（最坏 6 视频 × 3 帧 = 18 帧排队等 6 个槽）
  - 描述以 `[用户附图]` 和 `[用户附视频]` 段落形式拼到 user `content` 末尾
  - 主对话模型（DeepSeek）**只看到融合后的纯文本**，不直接处理图片/视频
- 持久化时 user 消息保存融合后 `content` + 单独保留原始 `images` / `videos` 元数据，前端回放时凭 `object_key` 调对应 presign 接口取展示 URL
- 模型可能在生成最终答复前调用工具（`rag_search` / `web_search`），单轮最多 8 次工具循环
- 成功结束后保存 user 和 assistant 消息；模型异常时回滚数据库，返回 `error` SSE 事件

SSE 事件类型：

| event | data | 触发时机 |
| --- | --- | --- |
| `start` | `{}` | 整轮对话开始（一定是第一个事件） |
| `vision.start` | `{"count": number}` | 仅当 `images` 非空时出现，count = 图片张数 |
| `vision.done` | `{"count": number}` | 全部图片识别完成（成功或失败都算） |
| `video.start` | `{"count": number}` | 仅当 `videos` 非空时出现，count = 视频段数 |
| `video.done` | `{"count": number}` | 全部视频抽帧+识别完成 |
| `tool.call` | `{tool_call_id, name, arguments}` | LLM 调工具，`arguments` 是 JSON 字符串 |
| `tool.result` | `{tool_call_id, name, ok, error?, result}` | 工具执行完成，与上一条 `tool.call` 同 `tool_call_id` 配对 |
| `message.delta` | `{"content": "..."}` | 模型文本增量，可能高频出现，前端按顺序拼接 |
| `done` | `{}` | 整轮正常结束（最后一个事件） |
| `error` | `{"message": "..."}` | 整轮失败（最后一个事件），与 `done` 互斥 |

事件顺序约束：

- `start` 必然第一；`done` / `error` 必然最后，且互斥
- `vision.*` / `video.*` 只在对应媒体非空时出现，位于所有 `tool.*` / `message.delta` 之前
- 同时带图和视频时，`vision.start` 与 `video.start` 紧邻发出（之后并行处理）；`vision.done` 与 `video.done` 在各自完成时发出（不保证先后顺序）
- `tool.call` 与 `tool.result` 总是成对出现；同一轮可循环多次后才进入 `message.delta`

SSE 示例（带 1 图 + 1 视频）：

```text
event: start
data: {}

event: vision.start
data: {"count":1}

event: video.start
data: {"count":1}

event: vision.done
data: {"count":1}

event: video.done
data: {"count":1}

event: tool.call
data: {"tool_call_id":"call_abc","name":"rag_search","arguments":"{\"query\":\"草鱼 白点 蹭池壁\",\"mode\":\"mix\"}"}

event: tool.result
data: {"tool_call_id":"call_abc","name":"rag_search","ok":true,"result":{"chunks":[]}}

event: message.delta
data: {"content":"从你提供的图片和视频看，"}

event: message.delta
data: {"content":"草鱼的鳃部和行为都符合..."}

event: done
data: {}
```

> **前端实现提示**：浏览器内置 `EventSource` 不支持自定义 headers，无法带 `Authorization`。请使用 `fetch + ReadableStream` 手动解析 SSE。

## 9. 图片 / 视频上传与管理

媒体（图片、视频）存储在 MinIO（S3 协议兼容）对象存储中：
- 图片走 `images/{yyyy}/{mm}/{dd}/{uuid}.{ext}` 前缀
- 视频走 `videos/{yyyy}/{mm}/{dd}/{uuid}.{ext}` 前缀

所有接口都需要鉴权（`Authorization: Bearer <access_token>`）。

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
    "original_filename": "fish.jpg",
    "url": "http://localhost:9000/fish-med-agent/images/2026/05/30/3f2a...c1.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...",
    "url_expires_at": 1780164807101
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
| `url` | string | 可直接 `<img src>` 使用的预签名 URL（默认有效期 1 小时） |
| `url_expires_at` | integer | URL 过期时间，UTC epoch **毫秒**时间戳；保证 `≤` URL 的实际过期点 |

> 部署提示：`url` 的 host 取自 `MINIO_ENDPOINT` 配置。生产环境需将其改为浏览器可达的对外地址，否则签名 URL 不可访问。

错误：`400001`（类型不支持）、`413001`（超过 10MB）、`401002`（未登录/token 无效）、`500001`（对象存储写入失败）。

### `POST /upload/image/presign`

为已有的 object_key 批量补签 presigned URL，用于历史会话回显图片。

请求头：

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

请求体：

```json
{
  "object_keys": [
    "images/2026/05/30/abc.png",
    "images/2026/05/30/def.jpg"
  ]
}
```

请求字段：

| 字段 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| `object_keys` | array[string] | 是 | 长度 `1..50` | 待签名的 object_key 列表 |

成功响应：

```json
{
  "code": 200,
  "message": "success",
  "request_id": "req_123",
  "data": {
    "urls": {
      "images/2026/05/30/abc.png": "http://localhost:9000/fish-med-agent/images/.../abc.png?X-Amz-...",
      "images/2026/05/30/def.jpg": "http://localhost:9000/fish-med-agent/images/.../def.jpg?X-Amz-..."
    },
    "expires_at": 1780164807101
  }
}
```

响应字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `urls` | object[string, string] | `object_key → 预签名 URL` 的字典 |
| `expires_at` | integer | 所有 URL 的统一过期时间，UTC epoch **毫秒**时间戳；保证 `≤` 任一 URL 的实际过期点 |

当前行为与说明：

- 单次最多签 **50** 个 key，超过返回 `422`（Pydantic 校验失败）
- 非法 key（空、含 `..`、不在 `images/` 或 `videos/` 前缀下）会**静默从 `urls` 字典中省略**，前端按 `urls[key]` 缺失处理即可
- 该接口语义上服务图片，但底层 service 同时接受 `images/` 和 `videos/` 前缀；建议前端按内容类型分别调用 `/upload/image/presign` 和 `/upload/video/presign` 以便日志区分
- **不调 `head_object` 检查对象是否存在**，节省一轮 RTT；已删除的 key 也能签出 URL，访问时 MinIO 返 404，前端用 `<img onerror>` 兜底显示占位
- `expires_at` 在签名前一刻计算，**严格不晚于**任一 URL 的实际过期点，前端按 `Date.now() < expires_at` 判断即可

错误：`401002`（未登录/token 无效）。

### `POST /upload/video`

上传单段视频。请求格式为 `multipart/form-data`，字段名为 `file`。

请求头：

```http
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

请求字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `file` | file | 是 | 待上传的视频文件 |

校验规则：

- **类型**：仅 `mp4` / `webm` / `mov`，按文件 magic number 判断，**不信任** `Content-Type`
  - mp4：前 12 字节含 `ftyp` 且 major brand 非 `qt`
  - mov：前 12 字节含 `ftyp` 且 major brand 以 `qt` 开头（MIME 报 `video/quicktime`）
  - webm：前 4 字节 `0x1A 0x45 0xDF 0xA3`
- **大小**：最大 `50MB`，分块读取，超限立即中止
- **时长**：最大 `30 秒`，服务端落临时文件后 `ffmpeg.probe` 测量
- object_key 由服务端生成，格式为 `videos/{yyyy}/{mm}/{dd}/{uuid}.{ext}`

成功响应：

```json
{
  "code": 200,
  "message": "success",
  "request_id": "req_123",
  "data": {
    "object_key": "videos/2026/05/30/def...e9.mp4",
    "content_type": "video/mp4",
    "extension": "mp4",
    "size": 4521800,
    "duration_seconds": 12.4,
    "original_filename": "swim.mp4",
    "url": "http://localhost:9000/fish-med-agent/videos/2026/05/30/def...e9.mp4?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...",
    "url_expires_at": 1780164807101
  }
}
```

响应字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `object_key` | string | 对象存储中的 key |
| `content_type` | string | 服务端按 magic number 检测出的 MIME |
| `extension` | string | 文件扩展名，例如 `mp4` |
| `size` | integer | 文件大小，字节 |
| `duration_seconds` | number | 视频时长（秒），由 `ffmpeg.probe` 测得 |
| `original_filename` | string \| null | 客户端上传时的原始文件名 |
| `url` | string | 可直接 `<video src>` 使用的预签名 URL（默认 1 小时） |
| `url_expires_at` | integer | URL 过期时间，UTC epoch **毫秒**时间戳 |

错误：`400002`（格式不支持）、`400003`（损坏/无法解析）、`413002`（超 50MB）、`413003`（超 30 秒）、`401002`（未登录/token 无效）、`500001`（对象存储写入失败）。

### `POST /upload/video/presign`

为已有的视频 object_key 批量补签 presigned URL，用于历史会话回显视频。**与 `/upload/image/presign` 行为完全对称**（共用底层 service），区别仅在语义上分流前端调用。请求体、响应体、错误码、约束都一致——参考上方 `/upload/image/presign` 章节。

请求示例：

```json
{
  "object_keys": [
    "videos/2026/05/30/abc.mp4",
    "videos/2026/05/30/def.webm"
  ]
}
```

成功响应：

```json
{
  "code": 200,
  "message": "success",
  "request_id": "req_123",
  "data": {
    "urls": {
      "videos/2026/05/30/abc.mp4": "http://localhost:9000/fish-med-agent/videos/.../abc.mp4?X-Amz-...",
      "videos/2026/05/30/def.webm": "http://localhost:9000/fish-med-agent/videos/.../def.webm?X-Amz-..."
    },
    "expires_at": 1780164807101
  }
}
```

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

### `DELETE /upload/video`

按 object_key 删除单段视频。**行为与 `DELETE /upload/image` 完全对称**（共用底层 `_delete_object_with_check`），差别只在校验前缀和不存在时的错误码。

请求体：

```json
{
  "object_key": "videos/2026/05/30/abc...e9.mp4"
}
```

请求字段：

| 字段 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| `object_key` | string | 是 | 非空，须以 `videos/` 开头且不含 `..` | 上传成功后返回的 object_key |

成功响应：

```json
{
  "code": 200,
  "message": "success",
  "request_id": "req_123",
  "data": {
    "object_key": "videos/2026/05/30/abc...e9.mp4"
  }
}
```

当前行为与说明：

- key 校验只允许操作 `videos/` 前缀下的对象（与图片接口对称隔离）
- 删除前先 `head_object` 探测存在性：不存在返回 `404003`，而不是静默成功
- object_key **未编码用户归属**：任意登录用户均可删任意视频，需要严格归属请在 key 中编码 user_id 或引入媒体归属表

错误：`400004`（object_key 非法）、`404003`（视频不存在）、`401002`（未登录/token 无效）、`500002`（对象存储删除失败）。

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

1. 给参数校验异常（FastAPI/Pydantic 默认 `422`）增加统一响应处理器，对齐 `ApiResponse` 格式
2. 为 `conversation/list` 定义明确的响应 schema，避免直接暴露 ORM 字段名（`metadata_` 等）
3. 上传/删除接口的 `object_key` 未编码用户归属，任意登录用户可删任意媒体；需在 key 中编码 user_id 或引入媒体归属表
4. 登录接口无速率限制，存在暴力破解风险，上线前需接 `slowapi` + Redis
5. 长对话超模型上下文窗口的 token 计算与截断尚未实现
