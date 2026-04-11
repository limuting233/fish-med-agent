# Fish Med Agent

Fish Med Agent 是一个面向水产养殖场景的多模态鱼病问答智能体项目，目标是结合鱼病知识、多轮问答和图像理解能力，为养殖人员提供病害识别、病因分析、处置建议和养殖管理参考。

## 项目目标

项目计划围绕以下能力持续建设：

- 鱼病领域知识问答
- 基于症状描述的病情分析
- 鱼体、病灶、养殖环境图片理解
- 图文混合输入的智能诊断辅助
- 结构化处置建议与风险提示

## 当前状态

当前仓库已经完成以下基础工作：

- 前端已初始化为 `Vue 3 + Vite + TypeScript` 项目
- 后端已初始化为 `uv` 管理的 Python 项目
- 后端 Python 版本约束已设为 `>=3.12,<4.0`
- 已产出接口设计文档 [API.md](./API.md)

当前仍在开发中的部分：

- FastAPI 应用入口
- `healthz` 等基础接口
- 图文问答与结构化诊断能力
- 知识库检索与反馈闭环

## 目录结构

```text
fish-med-agent/
├── API.md               # 后端接口设计文档
├── backend/             # Python 后端工程
│   ├── pyproject.toml
│   ├── uv.lock
│   └── src/
│       └── fish_med_agent/
└── frontend/            # Vue 3 前端工程
```

## 技术栈

### 前端

- Vue 3
- Vite
- TypeScript

### 后端

- Python 3.12+
- uv
- FastAPI
- Uvicorn

## 环境要求

### 前端

- Node.js：`^20.19.0` 或 `>=22.12.0`
- npm：建议使用与 Node.js 匹配的较新版本

### 后端

- Python：`>=3.12,<4.0`
- 建议使用 Conda 管理 Python 环境
- `uv` 用于依赖管理和项目构建

## 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd fish-med-agent
```

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认开发地址通常为：

```text
http://localhost:5173
```

### 3. 初始化后端环境

如果你使用 Conda：

```bash
conda create -n fish-med python=3.12 -y
conda activate fish-med
cd backend
pip install uv
uv sync
```

说明：

- `backend/pyproject.toml` 中维护项目依赖
- `backend/uv.lock` 为锁文件
- `backend/.python-version` 用于声明本项目默认 Python 版本

目前后端工程已经完成初始化，但应用入口和业务接口仍在开发中，因此暂时还不能直接作为完整服务启动。

## 文档说明

- [API.md](./API.md)：后端 `v1` 接口设计文档
- `backend/`：后端代码目录
- `frontend/`：前端代码目录

## 开发建议

建议采用以下方式推进开发：

1. 先完成 FastAPI 应用入口和 `healthz` 接口
2. 再落地图像上传、会话管理、消息接口
3. 最后接入知识库检索、结构化诊断和流式输出

## 后续规划

- 接入多模态大模型
- 构建鱼病知识库与检索能力
- 支持诊断卡片和引用来源展示
- 支持用户反馈与结果纠偏
- 逐步完善前后端联调链路
