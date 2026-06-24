# GPT-SoVITS 语音克隆及合成网络平台

面向 AI 短剧的多角色语音克隆工作台（MVP-0 · 4 周）。本仓库为 **产品文档 + 平台工程** monorepo；**GPT-SoVITS 引擎** 在上游仓库 / Docker / 云端 GPU 单独部署。

> **实现状态（v0.2 · 2026-06-24）**：✅ MVP-0 全链路（授权→训练→合成→合规导出）· ✅ Web 工作台 · ✅ 音色馆 MVP+1 第一切片 · ✅ 云端训练编排 MVP · 本机 **合成**（9880）；完整微调推荐 **云端 GPU**。

👉 **[项目收尾状态](docs/PROJECT_STATUS.md)** · **[实训交付物包](deliverables/)**

**GitHub**：https://github.com/phuozi-pn/GPT-SoVITS-

> **新电脑从零安装** → **[docs/从零安装指南.md](docs/从零安装指南.md)**（Git / Python / Docker / Node 一步步）

## 工作流（当前推荐）

| 环节 | 在哪里 |
|------|--------|
| 素材整理、平台/Web、冒烟测试 | 本机 Windows |
| 切分 + ASR + 微调 | **租 GPU 服务器 / AutoDL** |
| 权重 scp 回本机 → Web 导入 → 合成/批量 | 本机 |

👉 **[云端 GPU 训练指南](docs/architecture/2026-06-10-云端GPU训练指南.md)**  
👉 **[云端权重接入 Web 合成](docs/architecture/2026-06-14-云端权重接入Web合成.md)**

## 仓库结构

```
GPT/
├── deliverables/         实训提交包（01立项–07日常报告，Word）
├── docs/                 需求、架构、运维文档
├── infra/
│   ├── docker/           PostgreSQL + Redis + 迁移
│   └── engine/           引擎 Docker 脚本、云端 train.sh
├── apps/
│   ├── api/              FastAPI 平台 API
│   └── web/              Vue 3 工作台
├── domains/              领域服务（训练、合成、项目、合规…）
├── voice_platform/       共享内核（Job、配额、存储、JWT）
├── workers/              train / infer / batch Worker
├── scripts/              本机 PowerShell 运维脚本
└── tests/                pytest
```

## 文档入口

| 用途 | 路径 |
|------|------|
| **新电脑从零安装** | **[docs/从零安装指南.md](docs/从零安装指南.md)** |
| **项目收尾 / 答辩** | [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) |
| **实训 Word 提交包** | [deliverables/](deliverables/) |
| **云端训练** | [docs/architecture/2026-06-10-云端GPU训练指南.md](docs/architecture/2026-06-10-云端GPU训练指南.md) |
| **云端一键编排** | [docs/architecture/2026-06-22-云端训练一键编排-MVP.md](docs/architecture/2026-06-22-云端训练一键编排-MVP.md) |
| **权重导入 + 批量配音** | [docs/architecture/2026-06-14-云端权重接入Web合成.md](docs/architecture/2026-06-14-云端权重接入Web合成.md) |
| 本机重启（API + Web + 9880） | [docs/architecture/2026-06-09-本地环境完整重启指南.md](docs/architecture/2026-06-09-本地环境完整重启指南.md) |
| 对外演示脚本 | [docs/architecture/2026-06-19-对外演示路径冻结.md](docs/architecture/2026-06-19-对外演示路径冻结.md) |
| 架构索引 | [docs/architecture/README.md](docs/architecture/README.md) |
| 平台 API | [apps/api/README.md](apps/api/README.md) |
| 引擎 Docker（合成） | [infra/engine/README.md](infra/engine/README.md) |

## 克隆与安装

> 完整图文步骤见 **[docs/从零安装指南.md](docs/从零安装指南.md)**。下面是命令摘要。

> 所有脚本请在 **仓库根目录** `GPT/` 下执行，不要在上一级 `Desktop/` 运行。

```powershell
git clone https://github.com/phuozi-pn/GPT-SoVITS-.git GPT
cd GPT

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env

# 终端 1：平台（需 Docker Desktop 已启动）
.\scripts\dev_restart.ps1 -Background

# 终端 2：Web
.\scripts\web_dev.ps1
```

浏览器打开 http://127.0.0.1:5173/studio 。真实 AI 合成需额外配置 9880 引擎，见安装指南 §7。

## 本机快速开始

### 1. 平台 + Web

```powershell
cd C:\Users\panta\Desktop\GPT   # 换成你的 clone 路径

.\scripts\dev_restart.ps1 -Background
.\scripts\web_dev.ps1          # 另开终端
```

| 页面 | URL |
|------|-----|
| 听感 A/B 产出 | `data/tune_ab/`（运行 `scripts/tune_ab_compare.py`） |
| 听感调参指南 | [docs/architecture/2026-06-16-004听感调参指南.md](docs/architecture/2026-06-16-004听感调参指南.md) |
| 工作台（上传/训练） | http://127.0.0.1:5173/studio |
| 音色库（导入权重/试听） | http://127.0.0.1:5173/library |
| 批量配音（CSV + ZIP） | http://127.0.0.1:5173/projects |
| 音色馆（精选/跨用户） | http://127.0.0.1:5173/catalog |
| OpenAPI | http://127.0.0.1:8001/api/v1/docs |

### 2. 引擎合成（9880）

在上游 `GPT-SoVITS` 目录启动 Docker Lite 容器后：

```powershell
.\scripts\engine_api_v2.ps1 -Action start
.\scripts\engine_api_v2.ps1 -Action status
```

`.env` 中设置 `ENGINE_MOCK=false`、`ENGINE_TTS_URL=http://127.0.0.1:9880`，并配置 `ENGINE_TRAIN_ROOT` 指向本机 GPT-SoVITS 根目录（用于权重导入）。

### 3. 云端训练 → 本机试听

```bash
# GPU 服务器上
bash infra/engine/cloud/train.sh /root/train_10min.wav /root/train_out my-voice-001
```

权重 scp 回本机后：

```powershell
.\.venv\Scripts\python.exe scripts\import_engine_weights.py
```

## 脚本（本机常用）

| 脚本 | 用途 |
|------|------|
| `dev_restart.ps1 -Background` | 一键重启 API + Workers |
| `platform_start.ps1` / `platform_stop.ps1` | 平台进程管理 |
| `platform_status.ps1` | 查看 api/train/infer/batch 状态 |
| `web_dev.ps1` | Web 开发服务器 |
| `engine_api_v2.ps1` | 9880 合成引擎 |
| `import_engine_weights.py` | 注册云端权重到平台 |
| `download_bilibili_audio.ps1` | B 站素材下载（需 cookies.txt） |

已弃用的本机 Docker **训练** 脚本见 [scripts/legacy/README.md](scripts/legacy/README.md)。

## 本地不入 Git 的内容

| 路径 | 说明 |
|------|------|
| `.env` | 本地密钥与路径 |
| `data/` | 上传素材与合成产物 |
| `upload-packs/*.zip` | 云端上传大包（见 [upload-packs/README.md](upload-packs/README.md)） |
| `listen_*.wav` | 本地试听文件 |
| `cookies.txt` | B 站下载 Cookie |

## 开发阶段

| 周 | 重点 | 状态 |
|----|------|------|
| W1 Core | Spike + API/Job + 合成 | ✅ |
| W2 Workflow | 上传/QC + Web + 权重导入 + CSV 批量 | ✅ |
| W3 | 合规导出、敏感词 | ✅ |
| W4 | 部署文档、E2E、模块化 | ✅ |
| MVP+1 | 音色馆 + VoiceGrant + 支付/KYC/Webhook 骨架 | ✅ 第一切片 |
| 云端编排 | SSH 微调 + 本机 ASR 预处理 | ✅ MVP |

详见 [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)。

## 仓库外路径

| 路径 | 说明 |
|------|------|
| `GPT-SOVITS/GPT-SoVITS`（与 GPT 同级） | 上游引擎 clone（合成 + 云端训练） |

## License

产品代码与文档：项目自有。GPT-SoVITS：**MIT**。
