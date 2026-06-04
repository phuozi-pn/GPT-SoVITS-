# 系统架构文档

本目录描述 **自研平台层 + GPT-SoVITS V2-PRO 引擎层** 的分层架构、部署与开源边界。

## 索引

| 日期 | 文件 | 说明 |
|------|------|------|
| 2026-06-03 | [2026-06-03-system-architecture-系统架构说明.md](./2026-06-03-system-architecture-系统架构说明.md) | 主文档 v1.0（V2-PRO pinned） |
| 2026-06-03 | [2026-06-03-w1-spike-v2pro-快速验证.md](./2026-06-03-w1-spike-v2pro-快速验证.md) | **今天可跑**：上游 v2Pro 本地/WebUI 验证 |
| 2026-06-03 | [diagrams/](./diagrams/) | PlantUML：逻辑 / 部署 / 开源边界 |

## 阅读顺序

1. 系统架构说明 §1–§4（原则 + 分层 + V2-PRO 选型）
2. W1 Spike 快速验证（算法/全栈先跑通 train→infer）
3. 部署图 + 与 [requirements/modules/](../requirements/modules/) 对照

## 关联文档

| 文档 | 关系 |
|------|------|
| [PROJECT_CHARTER.md](../PROJECT_CHARTER.md) | MVP-0 范围与指标 |
| [requirements/2026-06-01-mvp-voice-platform-需求规格说明.md](../requirements/2026-06-01-mvp-voice-platform-需求规格说明.md) | REQ 验收、API |
| [research/2026-06-01-voice-marketplace-compliance-产品调研报告.md](../research/2026-06-01-voice-marketplace-compliance-产品调研报告.md) | §4 技术要点 |
