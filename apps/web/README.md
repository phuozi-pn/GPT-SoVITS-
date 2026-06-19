# Voice Platform Web (MVP-0)

Vue 3 + Vite + Tailwind 工作台，对接 `apps/api` REST API。

## 开发

```powershell
cd C:\Users\panta\Desktop\GPT
.\scripts\platform_start.ps1    # 终端 1：API + Workers
.\scripts\web_dev.ps1           # 终端 2：http://127.0.0.1:5173
```

登录：手机号验证码（`SMS_MOCK=true` 显示 mock_code）或开发模式跳过。

## 工作流（先看这个）

侧栏按 **三条主线** 分组，默认进入 **文本转语音**（`/library`）。

```
┌─ 制作 ─────────────────────────────────────────┐
│  文本转语音 (/library)   日常单条/多段合成      │
│  批量配音   (/projects)  CSV 多角色 + 合规 ZIP │
└────────────────────────────────────────────────┘
         ↑ 需要音色
┌─ 音色 ─────────────────────────────────────────┐
│  训练工作台 (/studio)    自有声纹：授权→训练     │
│  音色馆     (/catalog)   他人公开音色：试听购买  │
└────────────────────────────────────────────────┘
┌─ 社区 ─────────────────────────────────────────┐
│  动态 (/discover/feed)     时间线与发帖         │
│  精选 (/discover/voices)   推荐音色             │
│  指南 (/discover/guide)    新手上路             │
│  消息 (/community)         私信洽谈             │
└────────────────────────────────────────────────┘
```

**典型路径**

| 目标 | 路径 |
|------|------|
| 快速出一段配音 | 音色馆或文本转语音选音色 → `/library` 合成 |
| 自己训练新音色 | `/studio` 四步 → 完成后在 `/library` 使用 |
| 短剧批量生产 | `/library` 导入权重 → `/projects` 绑角色 → 上传 CSV |
| 买他人音色 | `/catalog` 试听购买 → `/community` 私信卖家 |
| 实名（训练前） | `/kyc`（从训练工作台引导） |

导航与顶栏文案单一数据源：`src/config/navigation.ts`

完整页面地图：[Web 工作流与页面地图](../../docs/architecture/2026-06-16-web-frontend-工作流与页面地图.md)

## 全部路由

| 路由 | 分组 | 说明 |
|------|------|------|
| `/library` | 制作 | 文本转语音制作台（**默认首页**） |
| `/projects` | 制作 | 批量配音 |
| `/studio` | 音色 | 训练工作台（四步向导） |
| `/catalog` | 音色 | 音色馆 |
| `/discover/feed` | 社区 | 动态时间线 |
| `/discover/voices` | 社区 | 精选音色 |
| `/discover/guide` | 社区 | 新手上路 |
| `/discover` | — | 重定向至 `/discover/feed` |
| `/community` | 社区 | 私信收件箱 |
| `/kyc` | 音色 | 实名认证（二级页） |
| `/creator/:id` | 社区 | 创作者主页 |
| `/quality/:id` | 音色 | 相似度 AB 评测 |
| `/verify/:id` | 音色 | 授权验真（外链） |
| `/admin` | 运营 | 运营台（管理员） |
| `/login` | — | 登录 |

## 测试与构建

```powershell
cd apps\web
npm test
npm run build
```

### E2E 金路径（Playwright + API）

需本机 **PostgreSQL + Redis**（`infra/docker/docker-compose.dev.yml`），然后：

```powershell
cd apps\web
npx playwright install chromium
npm run test:e2e
```

Playwright 会并行启动 E2E API（:8001，Windows 用 `scripts/e2e_start_api.py`，Linux/macOS 用 `.sh`）与 Vite（:5173）。种子音色 ID：`22222222-2222-2222-2222-222222222222`（见 `infra/docker/migrations/020_e2e_catalog_seed.sql`）。

| 套件 | 文件 | 说明 |
|------|------|------|
| 展示站 + 购买合成 | `e2e/golden-paths.spec.ts` | 访客叙事、深链、买家 B 购买 |
| 社区 + 验真 | `e2e/social-verify.spec.ts` | 发帖公开流、结账后验真 |

联调购买用例以 **买家 B**（`aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa`）登录，避免自购种子音色（owner 为 user A）。`e2e/fixtures.ts` 提供 `loginDevMode` / `purchaseE2eVoice`（默认每次用 `ephemeralBuyerId()` 新用户，避免重复购买跳过结账）。

本地完整套件：**14 passed**（约 50s，需 `npx playwright install chromium`）。

## 环境

| 变量 | 说明 |
|------|------|
| `VITE_API_BASE` | 可选 API 基址 |
| API `WEB_CORS_ORIGINS` | 含 `http://127.0.0.1:5173` |

样式：`src/styles/tailwind.css` · 制作核心：`components/make/MakeWorkspace.vue`
