# W1 Core — 平台 API 本地运行

> **状态**：W1 Core ✅ 已完成（2026-06-03）· `pytest tests/ -q` → **28 passed**

## 快速验证

### 一键启动（推荐）

```powershell
# 仓库根目录，首次：pip install -e . && copy .env.example .env
.\scripts\platform_start.ps1          # 自动起 PG+Redis、API、Train/Infer Worker（3 个小窗）
.\scripts\platform_start.ps1 -Background   # 或后台+日志到 .runtime\logs\
.\scripts\platform_stop.ps1           # 全部停止
```

引擎 GPU 容器仍需单独保持运行（见 [infra/engine/README.md](../../infra/engine/README.md)）；`platform_start.ps1` 会尝试拉起 9880 `api_v2`。

### 手动多终端（调试用）

```powershell
cd infra\docker && docker compose -f docker-compose.dev.yml up -d
.\.venv\Scripts\Activate.ps1
uvicorn apps.api.main:app --reload --port 8001
python -m workers.train.runner
python -m workers.infer.runner
```

### 冒烟测试

```powershell
$env:API_BASE="http://127.0.0.1:8001"
python scripts\smoke_w2_upload_train.py
python scripts\smoke_w2_real_synthesis.py
```

OpenAPI：http://localhost:8001/api/v1/docs（端口见 `.env` 中 `STORAGE_PUBLIC_BASE_URL`）

### Web 工作台（Vue 3）

```powershell
.\scripts\platform_start.ps1    # 终端 1
.\scripts\web_dev.ps1           # 终端 2 → http://127.0.0.1:5173
```

详见 [apps/web/README.md](../web/README.md)。

## 已实现 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/v1/auth/sms/send` | 发验证码（`SMS_MOCK=true` 返回 `mock_code`） |
| POST | `/api/v1/auth/login` | 登录 → `access_token` + `quota` 摘要 |
| GET | `/api/v1/usage/quota` | 当月字符/训练配额 |
| POST | `/api/v1/voices` | 创建音色草稿 → `voice_id` |
| POST | `/api/v1/consents` | 提交授权（`CONSENT_AUTO_APPROVE=true` 时直接 approved） |
| POST | `/api/v1/voices/assets` | 上传训练素材（multipart）+ 同步质检 |
| GET | `/api/v1/voices/assets/{id}/qc` | 质检报告 |
| POST | `/api/v1/voices/assets/{id}/confirm` | 确认锁定素材 |
| POST | `/api/v1/synthesis` | 单条合成 → 202 + `job_id` |
| POST | `/api/v1/voices/{voice_id}/train` | 触发训练 → 202 + `job_id` |
| GET | `/api/v1/jobs/{job_id}` | 任务状态（合成 `audio_url` / 训练 `voice_version_id`） |

### 鉴权

- 生产路径：`Authorization: Bearer {token}`
- 本地调试：`DEV_SKIP_AUTH=true`（默认），使用 `DEV_USER_ID`

Dev 种子用户手机：`13800000001` · user_id `00000000-0000-0000-0000-000000000001`

### Dev 种子 ID

| 用途 | UUID |
|------|------|
| 合成 `voice_version_id` | `11111111-1111-1111-1111-111111111101` |
| 训练 `voice_id` | `11111111-1111-1111-1111-111111111100` |

## 环境变量

见仓库根目录 [`.env.example`](../../.env.example)。

| 变量 | 默认 | 说明 |
|------|------|------|
| `ENGINE_MOCK` | `true` | Infer Worker 占位 wav |
| `ENGINE_TTS_URL` | `http://127.0.0.1:9880` | 真引擎 api_v2 |
| `TRAIN_MOCK` | `true` | Train Worker 占位 VoiceVersion |
| `DEV_SKIP_AUTH` | `true` | 跳过 JWT |
| `SMS_MOCK` | `true` | Mock 短信 |
| `JWT_SECRET` | dev 密钥 | 生产必改 |
| `QUOTA_MONTHLY_CHAR_LIMIT` | `20000` | 月合成字符上限 |
| `QUOTA_MONTHLY_TRAIN_LIMIT` | `1` | 月训练次数上限 |
| `ENGINE_TRAIN_ROOT` | 空 | 上游 GPT-SoVITS 路径 |
| `ENGINE_TRAIN_DOCKER` | 空 | 非空则 `docker exec` 训练 |

## 真引擎合成（9880）

容器内（与 WebUI 可并存）：

```bash
bash scripts/docker-api-v2-start.sh
```

平台：

```powershell
$env:ENGINE_MOCK="false"
python -m workers.infer.runner
python scripts\smoke_w1_engine_synthesis.py
```

## 真引擎微调

**推荐**：在租用的 Linux GPU 上执行 [云端 GPU 训练指南](../../docs/architecture/2026-06-10-云端GPU训练指南.md)（`bash infra/engine/cloud/train.sh …`）。

平台 Train Worker（`TRAIN_MOCK=false` + `ENGINE_TRAIN_*`）仅作后续 SaaS 预留；当前 `.env` 保持 `TRAIN_MOCK=true`。

编排脚本：`infra/engine/scripts/spike_train_v2pro.py` · 超参：`infra/engine/train-v2pro-spike.json`

历史本机 Docker Spike 说明见 [W1 Spike §4](../../docs/architecture/2026-06-03-w1-spike-v2pro-快速验证.md)（已 superseded by 云端指南）。

## 代码地图

| 包 | 路径 |
|----|------|
| API 路由 | `apps/api/routes/` |
| 合规门禁 | `domains/compliance/gateway.py` |
| 认证 | `domains/auth/` · `voice_platform/auth/` |
| 配额 | `voice_platform/quota/` |
| Job / 队列 | `voice_platform/job/` |
| 合成 / 训练 | `domains/synthesis/` · `domains/training/` |
| Infer Worker | `workers/infer/runner.py` |
| Train Worker | `workers/train/runner.py` · `engine_adapter.py` |

> Python 包名 **`voice_platform`**（勿与标准库 `platform` 混淆）。

## W1 交付清单

| 项 | 状态 |
|----|------|
| Job + Redis 队列 + PG | ✅ |
| POST `/synthesis` + Infer Worker | ✅ Mock + 9880 |
| POST `/voices/{id}/train` + Train Worker | ✅ Mock + Engine Adapter |
| ComplianceGateway + pytest | ✅ |
| JWT 登录 | ✅ |
| 配额预检 + Job 成功后实扣 | ✅ |
| 微调 Spike 脚本 | ✅ 容器 4+4 + 9880 试听（2026-06-03） |

## W2 · 上传 → 训练闭环

完整用户路径（需 PG + Redis + API + Train Worker）：

```powershell
# .env 建议：QC_DEV_RELAX_DURATION=true（短样本冒烟）
python scripts\smoke_w2_upload_train.py
```

curl 示例：

```powershell
curl -X POST http://localhost:8001/api/v1/voices -H "Content-Type: application/json" -d "{\"name\":\"我的音色\"}"
curl -X POST http://localhost:8001/api/v1/consents -H "Content-Type: application/json" -d "{\"voice_id\":\"<voice_id>\"}"
curl -X POST http://localhost:8001/api/v1/voices/assets -F "voice_id=<voice_id>" -F "ref_text=参考文本" -F "audio_file=@sample.wav"
curl -X POST http://localhost:8001/api/v1/voices/assets/<asset_id>/confirm
curl -X POST http://localhost:8001/api/v1/voices/<voice_id>/train -H "Content-Type: application/json" -d "{\"voice_asset_id\":\"<asset_id>\"}"
```

详见 [W2 上传训练闭环](../../docs/architecture/2026-06-03-w2-upload-train-闭环.md)。

## W2 待办

- 项目 / 角色 / CSV 批量合成
- 授权书文件上传（模块 B 真 multipart）
- flac/mp3 解码、异步 QC、OSS 断点续传
