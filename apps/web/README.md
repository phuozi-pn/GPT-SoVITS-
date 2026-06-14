# Voice Platform Web (MVP-0)

Vue 3 + Vite 工作台，对接 `apps/api` REST API。

## 开发（前后端分离）

**终端 1 — 平台 API + Workers：**

```powershell
cd C:\Users\panta\Desktop\GPT
.\scripts\platform_start.ps1
```

**终端 2 — Web 开发服务器（代理 `/api` → 8001）：**

```powershell
.\scripts\web_dev.ps1
```

浏览器打开：**http://127.0.0.1:5173**

- 登录页：手机号 + 验证码（`SMS_MOCK=true` 会显示 `mock_code`）
- 或点击 **跳过登录**（需 API 侧 `DEV_SKIP_AUTH=true`）

## 生产构建（可选，由 API 同端口托管）

```powershell
cd apps\web
npm install
npm run build
```

构建产物在 `apps/web/dist/`。重启 API 后访问 **http://127.0.0.1:8001/** 即可（需先 `npm run build`）。

## 页面

| 路由 | 功能 |
|------|------|
| `/login` | 分栏登录页：品牌介绍 + 验证码登录 / 开发免登录 |
| `/studio` | 四步向导：创建音色 → 上传 → 训练 → 合成（步骤条、配额、侧栏日志） |

UI：Vue 3 原生 CSS（无组件库），深色顶栏 + 卡片式工作台，含合规提示与上传拖拽区样式。

## 环境变量

| 变量 | 说明 |
|------|------|
| `VITE_API_BASE` | 可选；默认同源或 Vite 代理 |
| API `WEB_CORS_ORIGINS` | 默认含 `http://127.0.0.1:5173` |

## 与后端对齐

- 端口以 `.env` 中 `STORAGE_PUBLIC_BASE_URL` 为准（默认 **8001**）
- 短 wav 测试：`.env` 设 `QC_DEV_RELAX_DURATION=true`
- Mock 训练/合成：`.env` 设 `TRAIN_MOCK=true` / `ENGINE_MOCK=true`
