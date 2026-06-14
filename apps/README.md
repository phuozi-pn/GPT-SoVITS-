# apps — 应用入口

| 目录 | 说明 | 状态 |
|------|------|------|
| `api/` | FastAPI BFF：鉴权、ComplianceGateway、Job 编排 | ✅ W1 |
| `web/` | Vue 3 工作台 SPA（上传→训练→合成） | ✅ v0.1 |

依赖 `domains/*` 与 `voice_platform/*`，不直接依赖 GPU Worker 实现。

本地运行： [api/README.md](./api/README.md)
