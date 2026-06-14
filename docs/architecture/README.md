# 系统架构文档

自研平台 + GPT-SoVITS V2-PRO 的分层架构、领域划分、运行时契约与治理（理由/评审）。

## 文档体系（v2.0 分章结构）

```
architecture/
├── README.md                          ← 本文件
├── 2026-06-03-system-architecture-design-系统架构设计.md   ← 导读 + 速览 + 阅读路径
├── 2026-06-03-system-architecture-系统架构说明.md         ← 一页纸速览
├── 2026-06-03-w1-spike-v2pro-快速验证.md
├── sections/                          ← 正文（按部分拆分）
│   ├── 01-背景与原则.md
│   ├── 02-架构视图.md
│   ├── 03-领域与交付分层.md
│   ├── 04-运行时与集成.md
│   ├── 05-技术决策与质量.md
│   ├── 06-设计理由与评审.md
│   └── 07-路线图与追溯.md
└── diagrams/                          ← PlantUML
```

## 从哪里开始读？

| 场景 | 入口 |
|------|------|
| 第一次了解 | [架构设计导读](./2026-06-03-system-architecture-design-系统架构设计.md) |
| 评审 / 周报 | [06-设计理由与评审](./sections/06-设计理由与评审.md) |
| 只想要摘要 | [系统架构速览](./2026-06-03-system-architecture-系统架构说明.md) |
| 开始写代码 | [03-领域](./sections/03-领域与交付分层.md) + [04-运行时](./sections/04-运行时与集成.md) |
| 本地跑引擎（合成） | [W1 Spike](./2026-06-03-w1-spike-v2pro-快速验证.md) |
| **云端 GPU 训练** | **[云端 GPU 训练指南](./2026-06-10-云端GPU训练指南.md)** |
| 上传→Mock 训练闭环 | [W2 上传训练](./2026-06-03-w2-upload-train-闭环.md) |
| 权重下载后试听 | [本机合成试听](./2026-06-09-自己素材训练试听指南.md) |
| **云端权重 → Web 合成 / 批量配音** | **[云端权重接入 Web 合成](./2026-06-14-云端权重接入Web合成.md)** |
| 本机跑平台 API | [apps/api/README](../../apps/api/README.md) |

## 分章索引

| 部分 | 文件 | 核心内容 |
|------|------|----------|
| 一 | [01-背景与原则](./sections/01-背景与原则.md) | 目标、P1–P5、约束、优先级 |
| 二 | [02-架构视图](./sections/02-架构视图.md) | 逻辑/部署/边界、六层 |
| 三 | [03-领域与交付分层](./sections/03-领域与交付分层.md) | 上下文、MVP 波次、代码结构 |
| 四 | [04-运行时与集成](./sections/04-运行时与集成.md) | 流程、ER、Job、API、Gateway |
| 五 | [05-技术决策与质量](./sections/05-技术决策与质量.md) | 选型、ADR、扩展点、NFR |
| 六 | [06-设计理由与评审](./sections/06-设计理由与评审.md) | 设计理由、评审、改进项 |
| 七 | [07-路线图与追溯](./sections/07-路线图与追溯.md) | 路线、风险、TBD、REQ 矩阵 |

## 图件

见 [diagrams/README.md](./diagrams/README.md)

## 关联

| 文档 | 关系 |
|------|------|
| [PROJECT_CHARTER.md](../PROJECT_CHARTER.md) | 范围冻结 |
| [SRS v1.2](../requirements/2026-06-01-mvp-voice-platform-需求规格说明.md) | 验收 |
| [requirements/modules/](../requirements/modules/) | 子模块 A–G |
