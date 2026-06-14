# 基础设施与部署

本目录管理 **自研平台** 的本地/内测部署说明；**GPT-SoVITS GPU 引擎** 使用 Docker Hub 官方镜像，配置见 [engine/](./engine/README.md)。

## 目录

```
infra/
├── README.md                 # 本文件
├── engine/                   # 引擎：Docker Hub + Spike 脚本 + 微调 §11
│   ├── README.md
│   ├── scripts/spike_train_v2pro.py
│   └── samples/
└── docker/                   # 平台：PostgreSQL、Redis
    ├── README.md
    ├── docker-compose.dev.yml
    ├── migrations/           # 001–005，API 启动时自动执行
    └── .env.example
```

## 部署拓扑（MVP-0）

```text
┌──────────────────────────────────────────────────────────────┐
│  本仓库 infra/docker              上游 GPT-SoVITS + Docker Hub │
│  ┌─────────────┐  ┌───────┐       ┌──────────────────────────┐ │
│  │ API :8000   │  │ PG    │       │ CU128-Lite 容器           │ │
│  │ Redis       │──│       │ Job   │ 9874 WebUI / 9880 api_v2 │ │
│  │ Workers     │  └───────┘       │ GPU 训练 Spike 脚本       │ │
│  └─────────────┘                  └──────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
         本机 Python 进程                 引擎容器（独立 compose）
```

## 使用顺序

1. **平台依赖**：`cd docker && docker compose -f docker-compose.dev.yml up -d`
2. **平台 API / Worker**：见 [apps/api/README.md](../apps/api/README.md)
3. **引擎 Spike**：按 [engine/README.md](./engine/README.md) 跑 WebUI / 9880 / 微调 Spike（✅ 2026-06-03 容器闭环）

## 端口速查

| 服务 | 端口 | 说明 |
|------|------|------|
| 平台 API | 8000 | FastAPI `/api/v1` |
| PostgreSQL | 5432 | `voice_platform` 库 |
| Redis | 6379 | Job 队列 `jobs:infer` / `jobs:train` |
| 引擎 WebUI | 9874 | 上游容器 |
| 引擎推理 WebUI | 9872 | 零样本试听 |
| 引擎 api_v2 | 9880 | 平台 Infer Worker 真引擎 |

## 与架构文档

- 部署视图：[docs/architecture/sections/02-架构视图.md](../docs/architecture/sections/02-架构视图.md)
- ADR 引擎 Docker：[docs/architecture/sections/05-技术决策与质量.md](../docs/architecture/sections/05-技术决策与质量.md#adr-004-引擎-docker-hub-官方镜像)
- W1 路线图：[docs/architecture/sections/07-路线图与追溯.md](../docs/architecture/sections/07-路线图与追溯.md)
