# Fish Med Agent API 文档

## 1. 文档说明

本文档定义 `Fish Med Agent` 的后端 `v1` 接口协议，用于支撑鱼病多模态问答、结构化诊断、图片上传、会话历史和知识库检索等核心能力。

- 版本：`v1`
- Base URL：`/api/v1`
- 协议：`HTTPS`
- 数据格式：`application/json`
- 文件上传：`multipart/form-data`

## 2. 设计目标

本接口设计用于支持以下业务场景：

- 鱼病相关文本问答
- 症状描述驱动的病情分析
- 鱼体、病灶、养殖环境图片理解
- 输出结构化诊断建议
- 结合知识库提供疾病参考信息
- 保留会话与消息历史，支持前端对话页展示

## 3. 统一规范

### 3.1 鉴权

默认采用 Bearer Token 方式：

```http
Authorization: Bearer <token>
```

如果部署在可信内网环境，可在网关层统一鉴权，服务内部暂时跳过用户鉴权。

### 3.2 通用响应结构

除流式接口外，所有接口统一返回以下结构：

```json
{
  "code": 200,
  "message": "success",
  "request_id": "req_123456",
  "data": {}
}
```

字段说明：

- `code`：业务状态码
- `message`：状态说明
- `request_id`：请求链路 ID，便于日志追踪
- `data`：业务数据

### 3.3 时间格式

统一使用 ISO 8601 格式，例如：

```text
2026-04-11T10:30:00+08:00
```

### 3.4 分页约定

分页查询统一使用以下参数：

- `page`：页码，从 `1` 开始
- `page_size`：每页条数，默认 `10`，最大 `100`

分页返回结构建议如下：

```json
{
  "list": [],
  "page": 1,
  "page_size": 10,
  "total": 0
}
```

### 3.5 图片约束

- 支持格式：`jpg`、`jpeg`、`png`、`webp`
- 单张最大：`10MB`
- 单次问答最多上传：`5` 张
- 建议保留原图，并生成缩略图用于前端展示

### 3.6 多模态消息格式

用户输入和模型输出统一采用 `content[]` 结构，便于兼容文本和图片：

```json
[
  {
    "type": "text",
    "text": "这条鱼身上有白点"
  },
  {
    "type": "image",
    "file_id": "img_001"
  }
]
```

`v1` 建议支持的内容类型：

- `text`
- `image`

## 4. 接口总览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/healthz` | 健康检查 |
| `POST` | `/files/images` | 上传鱼体、病灶或养殖环境图片 |
| `POST` | `/conversations` | 创建会话 |
| `GET` | `/conversations/{conversation_id}` | 获取会话详情 |
| `GET` | `/conversations/{conversation_id}/messages` | 获取消息历史 |
| `POST` | `/conversations/{conversation_id}/messages` | 发起一次非流式图文问答 |
| `POST` | `/conversations/{conversation_id}/messages/stream` | 发起一次流式图文问答 |
| `POST` | `/diagnosis/analyze` | 执行结构化病情分析 |
| `GET` | `/knowledge/diseases` | 疾病列表检索 |
| `GET` | `/knowledge/diseases/{disease_id}` | 疾病详情查询 |
| `POST` | `/feedback` | 提交用户反馈与结果纠偏 |

## 5. 详细接口定义

### 5.1 健康检查

#### `GET /healthz`

用于服务健康探测和部署探针检查。

响应示例：

```json
{
  "code": "OK",
  "message": "success",
  "request_id": "req_healthz",
  "data": {
    "status": "ok",
    "service": "fish-med-agent",
    "version": "v1"
  }
}
```

### 5.2 图片上传

#### `POST /files/images`

上传鱼体、病灶、水体环境等图片，供问答或诊断接口引用。

请求类型：

```text
multipart/form-data
```

表单字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `file` | file | 是 | 图片文件 |
| `biz_type` | string | 是 | 业务类型，取值建议：`chat`、`diagnosis` |
| `conversation_id` | string | 否 | 所属会话 ID |

响应示例：

```json
{
  "code": "OK",
  "message": "success",
  "request_id": "req_upload_001",
  "data": {
    "file_id": "img_001",
    "url": "https://cdn.example.com/fish-med/img_001.jpg",
    "thumbnail_url": "https://cdn.example.com/fish-med/img_001_thumb.jpg",
    "mime_type": "image/jpeg",
    "size": 2481901,
    "width": 1280,
    "height": 960,
    "created_at": "2026-04-11T14:00:00+08:00"
  }
}
```

### 5.3 创建会话

#### `POST /conversations`

创建一条新的问答会话。

请求示例：

```json
{
  "scene": "fish_disease_qa",
  "user_id": "user_001",
  "metadata": {
    "farm_id": "farm_001",
    "pond_id": "pond_03"
  }
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `scene` | string | 是 | 场景标识，建议固定为 `fish_disease_qa` |
| `user_id` | string | 否 | 用户 ID |
| `metadata` | object | 否 | 扩展业务字段 |

响应示例：

```json
{
  "code": "OK",
  "message": "success",
  "request_id": "req_conv_001",
  "data": {
    "conversation_id": "conv_001",
    "title": "草鱼白点病初步咨询",
    "scene": "fish_disease_qa",
    "created_at": "2026-04-11T14:05:00+08:00"
  }
}
```

### 5.4 获取会话详情

#### `GET /conversations/{conversation_id}`

返回单个会话的基本信息。

响应示例：

```json
{
  "code": "OK",
  "message": "success",
  "request_id": "req_conv_detail_001",
  "data": {
    "conversation_id": "conv_001",
    "title": "草鱼白点病初步咨询",
    "scene": "fish_disease_qa",
    "message_count": 6,
    "created_at": "2026-04-11T14:05:00+08:00",
    "updated_at": "2026-04-11T14:12:00+08:00"
  }
}
```

### 5.5 获取消息历史

#### `GET /conversations/{conversation_id}/messages`

查询某个会话下的历史消息列表。

查询参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `page` | integer | 否 | 页码 |
| `page_size` | integer | 否 | 每页条数 |

响应示例：

```json
{
  "code": "OK",
  "message": "success",
  "request_id": "req_msg_list_001",
  "data": {
    "list": [
      {
        "message_id": "msg_u_001",
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "这条草鱼身上有白点，还经常蹭池壁"
          },
          {
            "type": "image",
            "file_id": "img_001",
            "url": "https://cdn.example.com/fish-med/img_001.jpg"
          }
        ],
        "created_at": "2026-04-11T14:06:00+08:00"
      },
      {
        "message_id": "msg_a_001",
        "role": "assistant",
        "content": [
          {
            "type": "text",
            "text": "结合描述和图片，初步怀疑为小瓜虫病。"
          }
        ],
        "created_at": "2026-04-11T14:06:05+08:00"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 2
  }
}
```

### 5.6 非流式图文问答

#### `POST /conversations/{conversation_id}/messages`

在指定会话内发起一次问答。接口负责保存用户消息、执行模型推理、可选检索知识库，并返回模型回复与结构化诊断结果。

请求示例：

```json
{
  "message": {
    "role": "user",
    "content": [
      {
        "type": "text",
        "text": "这条草鱼身上有白点，还经常蹭池壁，帮我判断一下"
      },
      {
        "type": "image",
        "file_id": "img_001"
      }
    ]
  },
  "options": {
    "knowledge_search": true,
    "return_diagnosis_card": true
  }
}
```

请求字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `message.role` | string | 是 | 固定为 `user` |
| `message.content` | array | 是 | 多模态输入内容 |
| `options.knowledge_search` | boolean | 否 | 是否启用知识库检索 |
| `options.return_diagnosis_card` | boolean | 否 | 是否返回结构化诊断卡片 |

响应示例：

```json
{
  "code": "OK",
  "message": "success",
  "request_id": "req_chat_001",
  "data": {
    "user_message_id": "msg_u_002",
    "assistant_message": {
      "message_id": "msg_a_002",
      "role": "assistant",
      "content": [
        {
          "type": "text",
          "text": "从图片和描述看，疑似小瓜虫病。建议先隔离观察，并尽快检测水温、溶氧、氨氮等指标。"
        }
      ],
      "created_at": "2026-04-11T14:10:02+08:00"
    },
    "diagnosis_card": {
      "species": "grass_carp",
      "symptoms": [
        "体表白点",
        "擦身"
      ],
      "suspected_diseases": [
        {
          "disease_id": "d_001",
          "name": "小瓜虫病",
          "probability": 0.82,
          "reason": "白点分布和擦身行为较为典型"
        }
      ],
      "risk_level": "high",
      "actions_now": [
        "隔离观察",
        "检测水温、溶氧、氨氮",
        "减少应激反应"
      ],
      "need_human_expert": false
    },
    "references": [
      {
        "source_id": "kb_001",
        "title": "小瓜虫病",
        "score": 0.93
      }
    ]
  }
}
```

### 5.7 流式图文问答

#### `POST /conversations/{conversation_id}/messages/stream`

用于前端流式渲染模型回复。请求体与非流式接口一致，响应采用 `SSE`。

请求头建议：

```http
Accept: text/event-stream
Content-Type: application/json
```

事件类型建议：

| 事件 | 说明 |
| --- | --- |
| `message.delta` | 文本增量 |
| `references.ready` | 知识库引用已准备完成 |
| `diagnosis.ready` | 结构化诊断卡片已准备完成 |
| `done` | 本次回复完成 |
| `error` | 推理或服务错误 |

SSE 示例：

```text
event: message.delta
data: {"text":"从图片和描述看，"}

event: message.delta
data: {"text":"疑似小瓜虫病。"}

event: diagnosis.ready
data: {"risk_level":"high"}

event: done
data: {"message_id":"msg_a_003"}
```

### 5.8 结构化病情分析

#### `POST /diagnosis/analyze`

适用于独立诊断页面或表单式录入，不依赖对话上下文。

请求示例：

```json
{
  "species": "grass_carp",
  "symptoms": [
    "体表白点",
    "擦身",
    "食欲下降"
  ],
  "images": [
    "img_001",
    "img_002"
  ],
  "water_quality": {
    "temperature": 24.5,
    "dissolved_oxygen": 5.1,
    "ammonia_nitrogen": 0.18,
    "ph": 7.6
  },
  "mortality_rate": 0.03,
  "days_since_onset": 2
}
```

请求字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `species` | string | 否 | 鱼种，如 `grass_carp` |
| `symptoms` | array | 是 | 症状列表 |
| `images` | array | 否 | 图片 ID 列表 |
| `water_quality` | object | 否 | 水质检测参数 |
| `mortality_rate` | number | 否 | 死亡率 |
| `days_since_onset` | integer | 否 | 发病时长，单位天 |

响应示例：

```json
{
  "code": "OK",
  "message": "success",
  "request_id": "req_diag_001",
  "data": {
    "species": "grass_carp",
    "suspected_diseases": [
      {
        "disease_id": "d_001",
        "name": "小瓜虫病",
        "probability": 0.82,
        "reason": "图像可见体表白点，症状描述包含擦身行为"
      },
      {
        "disease_id": "d_002",
        "name": "车轮虫病",
        "probability": 0.31,
        "reason": "存在寄生虫类疾病的相似表征"
      }
    ],
    "risk_level": "high",
    "actions_now": [
      "隔离异常鱼体",
      "复测关键水质指标",
      "降低投喂并减少应激"
    ],
    "follow_up_questions": [
      "白点是否集中在鳍条和鳃部？",
      "近期是否出现快速死亡增加？"
    ],
    "references": [
      {
        "source_id": "kb_001",
        "title": "小瓜虫病",
        "score": 0.93
      }
    ],
    "disclaimer": "结果仅用于辅助判断，不替代专业兽医或水产技术人员现场诊断。"
  }
}
```

### 5.9 疾病列表检索

#### `GET /knowledge/diseases`

用于疾病搜索、疾病库列表页和引用资料查询。

查询参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `keyword` | string | 否 | 关键词，支持病名、别名、症状词 |
| `species` | string | 否 | 鱼种过滤 |
| `page` | integer | 否 | 页码 |
| `page_size` | integer | 否 | 每页条数 |

响应示例：

```json
{
  "code": "OK",
  "message": "success",
  "request_id": "req_kb_list_001",
  "data": {
    "list": [
      {
        "disease_id": "d_001",
        "name": "小瓜虫病",
        "aliases": [
          "白点病"
        ],
        "species_scope": [
          "grass_carp",
          "common_carp"
        ],
        "summary": "由小瓜虫寄生引起，常见体表白点和擦身行为。"
      }
    ],
    "page": 1,
    "page_size": 10,
    "total": 1
  }
}
```

### 5.10 疾病详情查询

#### `GET /knowledge/diseases/{disease_id}`

响应示例：

```json
{
  "code": "OK",
  "message": "success",
  "request_id": "req_kb_detail_001",
  "data": {
    "disease_id": "d_001",
    "name": "小瓜虫病",
    "aliases": [
      "白点病"
    ],
    "pathogen_type": "parasite",
    "applicable_species": [
      "grass_carp",
      "common_carp"
    ],
    "typical_symptoms": [
      "体表白点",
      "擦身",
      "食欲减退"
    ],
    "diagnosis_basis": [
      "体表或鳍条出现小白点",
      "显微镜检查可见寄生虫"
    ],
    "prevention": [
      "加强水质管理",
      "降低养殖密度",
      "减少温差应激"
    ],
    "treatment_notes": [
      "根据养殖规范选择合规处置方案",
      "避免盲目混用药物"
    ],
    "updated_at": "2026-04-11T09:00:00+08:00"
  }
}
```

### 5.11 用户反馈

#### `POST /feedback`

用于收集用户对回复质量、诊断准确性和最终病种结果的反馈，为后续模型和知识库优化提供数据。

请求示例：

```json
{
  "conversation_id": "conv_001",
  "assistant_message_id": "msg_a_002",
  "rating": "down",
  "tags": [
    "diagnosis_inaccurate",
    "suggestion_too_generic"
  ],
  "comment": "实际检测后更像车轮虫病",
  "confirmed_disease": "车轮虫病"
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `conversation_id` | string | 是 | 会话 ID |
| `assistant_message_id` | string | 是 | 被反馈的回复消息 ID |
| `rating` | string | 是 | `up` 或 `down` |
| `tags` | array | 否 | 问题标签 |
| `comment` | string | 否 | 文字说明 |
| `confirmed_disease` | string | 否 | 用户确认病种 |

响应示例：

```json
{
  "code": "OK",
  "message": "success",
  "request_id": "req_feedback_001",
  "data": {
    "feedback_id": "fb_001",
    "created_at": "2026-04-11T14:20:00+08:00"
  }
}
```

## 6. 核心数据模型

### 6.1 Message

```json
{
  "message_id": "msg_xxx",
  "role": "user",
  "content": [
    {
      "type": "text",
      "text": "示例文本"
    }
  ],
  "created_at": "2026-04-11T14:10:00+08:00"
}
```

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `message_id` | string | 消息 ID |
| `role` | string | `user`、`assistant`、`system` |
| `content` | array | 消息内容 |
| `created_at` | string | 创建时间 |

### 6.2 Content Item

文本类型：

```json
{
  "type": "text",
  "text": "鱼体表面有溃疡"
}
```

图片类型：

```json
{
  "type": "image",
  "file_id": "img_001",
  "url": "https://cdn.example.com/fish-med/img_001.jpg"
}
```

### 6.3 Diagnosis Card

```json
{
  "species": "grass_carp",
  "symptoms": [
    "体表白点",
    "擦身"
  ],
  "suspected_diseases": [
    {
      "disease_id": "d_001",
      "name": "小瓜虫病",
      "probability": 0.82,
      "reason": "白点与行为表现匹配"
    }
  ],
  "risk_level": "high",
  "actions_now": [
    "隔离观察",
    "检测水质"
  ],
  "need_human_expert": false
}
```

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `species` | string | 识别或输入的鱼种 |
| `symptoms` | array | 当前识别出的症状 |
| `suspected_diseases` | array | 疑似病种列表 |
| `risk_level` | string | `low`、`medium`、`high` |
| `actions_now` | array | 即刻建议措施 |
| `need_human_expert` | boolean | 是否建议人工专家介入 |

## 7. 错误码设计

| 错误码 | HTTP 状态码 | 说明 |
| --- | --- | --- |
| `INVALID_ARGUMENT` | `400` | 参数缺失、格式错误或取值非法 |
| `UNAUTHORIZED` | `401` | 未登录或鉴权失败 |
| `FORBIDDEN` | `403` | 无访问权限 |
| `NOT_FOUND` | `404` | 资源不存在 |
| `FILE_TOO_LARGE` | `400` | 图片体积超限 |
| `UNSUPPORTED_IMAGE_TYPE` | `400` | 图片格式不支持 |
| `RATE_LIMITED` | `429` | 请求过于频繁 |
| `MODEL_TIMEOUT` | `504` | 模型推理超时 |
| `KNOWLEDGEBASE_UNAVAILABLE` | `503` | 知识库服务暂不可用 |
| `INTERNAL_ERROR` | `500` | 服务内部异常 |

错误响应示例：

```json
{
  "code": "INVALID_ARGUMENT",
  "message": "field `message.content` is required",
  "request_id": "req_error_001",
  "data": null
}
```

## 8. 实现建议

### 8.1 推荐优先级

建议按以下顺序落地：

1. `GET /healthz`
2. `POST /files/images`
3. `POST /conversations`
4. `GET /conversations/{conversation_id}/messages`
5. `POST /conversations/{conversation_id}/messages`
6. `POST /diagnosis/analyze`
7. `GET /knowledge/diseases`
8. `GET /knowledge/diseases/{disease_id}`
9. `POST /conversations/{conversation_id}/messages/stream`
10. `POST /feedback`

### 8.2 推荐后端分层

建议将后端按以下职责划分：

- `api`：路由层，处理请求与响应
- `schemas`：Pydantic 数据模型
- `services`：会话、文件、问答、诊断、知识库等业务逻辑
- `repositories`：数据库访问
- `integrations`：模型服务、对象存储、向量检索、知识库适配

### 8.3 推荐数据库实体

建议至少包含以下表：

- `conversations`
- `messages`
- `files`
- `feedback`
- `diseases`
- `disease_aliases`
- `knowledge_sources`

## 9. 非目标说明

本版本接口文档暂不覆盖以下内容：

- 药物处方和精细剂量开具
- 多租户权限模型
- 完整运营后台接口
- 数据标注与训练平台接口
- 设备实时监测接入协议

这些内容建议在 `v2` 或独立子系统中扩展。

## 10. 文档结论

该版本接口文档优先解决“前端能发起图文问答并拿到结构化诊断结果”的最小闭环，同时为后续知识库扩展、流式输出和反馈优化预留演进空间。

如果后续需要进一步工程化，建议下一步补充：

- OpenAPI `yaml/json` 版本
- 统一错误码枚举定义
- 请求和响应的 Pydantic Schema
- SSE 流式事件详细字段协议
