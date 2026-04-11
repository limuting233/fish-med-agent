# Fish Med Agent Frontend

前端目录用于承载 Fish Med Agent 的用户交互界面，当前基于 `Vue 3 + Vite + TypeScript` 初始化，后续将用于实现鱼病图文问答、图片上传、诊断卡片展示和会话管理能力。

## 当前状态

目前前端已经完成基础脚手架初始化：

- 使用 `Vue 3`
- 使用 `Vite`
- 使用 `TypeScript`

当前仍在开发中的部分：

- 智能问答页面
- 图片上传入口
- 对话历史管理
- 结构化诊断结果展示
- 与后端接口联调

## 技术栈

- Vue 3
- Vite
- TypeScript

## 环境要求

- Node.js：`^20.19.0` 或 `>=22.12.0`
- npm：建议使用较新版本

## 目录结构

```text
frontend/
├── package.json
├── package-lock.json
├── index.html
├── vite.config.ts
├── tsconfig.json
├── public/
│   └── favicon.ico
└── src/
    ├── main.ts
    └── App.vue
```

## 安装依赖

```bash
cd /Users/limuting/Desktop/fish-med-agent/frontend
npm install
```

## 本地开发

启动开发服务器：

```bash
npm run dev
```

默认访问地址通常为：

```text
http://localhost:5173
```

## 构建与预览

生产构建：

```bash
npm run build
```

本地预览构建结果：

```bash
npm run preview
```

## 可用脚本

当前 [package.json](/Users/limuting/Desktop/fish-med-agent/frontend/package.json) 中已定义：

- `npm run dev`：启动开发环境
- `npm run build`：执行类型检查并构建
- `npm run preview`：预览生产构建

## 联调说明

当前前端仍是基础模板，后续联调建议：

- 统一以后端 `/api/v1` 作为接口前缀
- 在本地开发阶段通过 Vite 代理转发到后端服务
- 先联调 `healthz`，再联调会话和消息接口

## 后续建议

建议优先补充以下前端模块：

1. 聊天主界面
2. 图片上传组件
3. 诊断卡片组件
4. 会话列表与消息历史
5. 接口请求层与错误提示处理
