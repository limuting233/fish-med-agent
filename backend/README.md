# Fish Med Agent Backend

后端目录用于承载 Fish Med Agent 的 Python 服务端代码，当前采用 `uv` 管理依赖，计划基于 `FastAPI` 构建多模态鱼病问答与诊断接口。

## 当前状态

目前后端已经完成基础项目初始化：

- 已使用 `uv` 初始化 Python 项目
- 包名已调整为 `fish_med_agent`
- Python 版本约束为 `>=3.12,<4.0`
- 已安装核心依赖：`fastapi`、`uvicorn`

当前尚未完成的部分：

- FastAPI 应用入口
- `healthz` 接口
- 会话、消息、图片上传等业务接口
- 知识库检索与诊断服务逻辑

## 技术栈

- Python 3.12+
- uv
- FastAPI
- Uvicorn

## 环境要求

- Python：`>=3.12,<4.0`
- 建议使用 Conda 管理本地环境
- 推荐在项目目录内使用 `uv` 管理依赖和锁文件

## 目录结构

```text
backend/
├── pyproject.toml
├── uv.lock
├── .python-version
├── README.md
├── src/
│   └── fish_med_agent/
│       ├── __init__.py
│       ├── api/
│       ├── core/
│       ├── db/
│       ├── models/
│       ├── rag/
│       ├── repositories/
│       ├── schemas/
│       ├── service/
│       └── utils/
└── test/
```

## 初始化环境

如果本机使用 Conda，建议这样初始化：

```bash
conda create -n fish-med python=3.12 -y
conda activate fish-med
cd backend
pip install uv
uv sync
```

如果已经创建好环境，只需执行：

```bash
cd backend
uv sync
```

## 依赖管理

新增依赖：

```bash
uv add <package-name>
```

更新锁文件：

```bash
uv lock
```

同步当前环境：

```bash
uv sync
```

## Python 版本说明

- [pyproject.toml](/Users/limuting/Desktop/fish-med-agent/backend/pyproject.toml) 中的 `requires-python` 用于声明项目支持的 Python 版本范围
- [backend/.python-version](/Users/limuting/Desktop/fish-med-agent/backend/.python-version) 用于声明本项目默认开发版本

当前建议保持：

```text
.python-version = 3.12
requires-python = ">=3.12,<4.0"
```

## 启动说明

当前后端应用入口尚未实现，因此暂时没有可直接运行的服务启动命令。

后续完成 `src/fish_med_agent/main.py` 后，推荐使用如下方式启动：

```bash
uv run uvicorn fish_med_agent.main:app --reload
```

## 接口文档

接口设计文档位于：

- [API.md](/Users/limuting/Desktop/fish-med-agent/API.md)

建议优先实现以下接口：

1. `GET /api/v1/healthz`
2. `POST /api/v1/files/images`
3. `POST /api/v1/conversations`
4. `POST /api/v1/conversations/{conversation_id}/messages`

## 开发建议

- 不要同时保留两套包根目录，统一使用 `src/fish_med_agent/`
- 先完成应用入口和基础路由，再补业务 service 和 schema
- 接口返回结构建议与 `API.md` 中定义保持一致
- 在 `test/` 目录中补充最基本的接口测试
