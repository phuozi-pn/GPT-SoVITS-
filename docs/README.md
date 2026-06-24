# 文档区索引

GPT-SoVITS 语音克隆及合成系统 · 项目文档总览。

> **结项状态与答辩入口**：[PROJECT_STATUS.md](./PROJECT_STATUS.md)  
> **全仓库结构**：见 [../README.md](../README.md) · **实训 Word 包**：[../deliverables/](../deliverables/)

按 **治理 → 调研 → 需求 → 架构 → 项目管理 → 模板** 分层存放。

## 目录结构

```
GPT/                          # 仓库根 — 见 ../README.md
├── deliverables/             # 实训提交 Word 包（01–07）
├── docs/                     # 本目录
├── infra/ apps/ domains/ voice_platform/ workers/
└── scripts/ prompts/ .cursor/
```

## 文档类型对照

| 用途 | 读哪份 | 格式 |
|------|--------|------|
| 新电脑从零安装 | **[从零安装指南.md](./从零安装指南.md)** |
| 范围与 4 周冻结 | [PROJECT_CHARTER.md](./PROJECT_CHARTER.md) | Markdown |
| 市场 / 竞品 / 合规调研 | [research/](./research/) | Markdown |
| 研发验收、API、测试 | [requirements/2026-06-01-mvp-voice-platform-需求规格说明.md](./requirements/2026-06-01-mvp-voice-platform-需求规格说明.md) | Markdown（SRS v1.2） |
| 子模块 介绍/输入/处理/输出 | [requirements/modules/](./requirements/modules/) | Markdown A–G |
| 用例图、功能结构图 | [requirements/diagrams/](./requirements/diagrams/) | PlantUML |
| 立项 / 计划 / 需求分析（模板体例） | [pm/](./pm/) | Markdown → 同步至 Word 模板 |
| 正式 Word 空白/填报模板 | [templates/word/](./templates/word/) | `.doc` |
| **实训交付物包（01–07）** | [../deliverables/](../deliverables/) | 学校目录结构 `.doc` |
| 本地 Word 导出（不提交 Git） | [pm/exports/](./pm/exports/) | `.docx` 等 |

## 快速链接

### 治理与收尾

| 文档 | 说明 |
|------|------|
| [PROJECT_CHARTER.md](./PROJECT_CHARTER.md) | MVP-0 范围、指标、合规不可砍 |
| [PROJECT_STATUS.md](./PROJECT_STATUS.md) | **结项状态、演示路径、交付对照、待办** |

### 调研

| 文档 | 说明 |
|------|------|
| [research/README.md](./research/README.md) | 调研索引 |
| [2026-06-01-voice-marketplace-compliance-产品调研报告.md](./research/2026-06-01-voice-marketplace-compliance-产品调研报告.md) | v1.1 产品调研 |

### 需求（实现）

| 文档 | 说明 |
|------|------|
| [requirements/README.md](./requirements/README.md) | SRS / 子模块 / UML 索引 |
| [2026-06-01-mvp-voice-platform-需求规格说明.md](./requirements/2026-06-01-mvp-voice-platform-需求规格说明.md) | 实现 SRS v1.2 |

### 架构

| 文档 | 说明 |
|------|------|
| [architecture/README.md](./architecture/README.md) | 架构文档体系（v2.0 分章） |
| [2026-06-03-system-architecture-design-系统架构设计.md](./architecture/2026-06-03-system-architecture-design-系统架构设计.md) | **导读** + 阅读路径 |
| [architecture/sections/](./architecture/sections/) | 正文七部分（背景→路线图） |
| [2026-06-03-system-architecture-系统架构说明.md](./architecture/2026-06-03-system-architecture-系统架构说明.md) | 一页纸速览 |
| [2026-06-03-w1-spike-v2pro-快速验证.md](./architecture/2026-06-03-w1-spike-v2pro-快速验证.md) | 引擎 Spike（历史参考） |
| [2026-06-10-云端GPU训练指南.md](./architecture/2026-06-10-云端GPU训练指南.md) | **推荐：租 GPU 微调** |

### 项目管理（评审 / 出版）

| 文档 | 说明 |
|------|------|
| [pm/README.md](./pm/README.md) | PM 文档索引 |
| [2026-06-01-立项文档.md](./pm/2026-06-01-立项文档.md) | 项目启动 |
| [2026-06-01-项目计划文档.md](./pm/2026-06-01-项目计划文档.md) | 4 周计划 |
| [2026-06-01-需求分析文档.md](./pm/2026-06-01-需求分析文档.md) | 需求规格分析版 v1.1 |

### 模板

| 文档 | 说明 |
|------|------|
| [templates/README.md](./templates/README.md) | Word 与 reference 说明 |

## 实现进度（截至 2026-06-24）

完整矩阵见 **[PROJECT_STATUS.md](./PROJECT_STATUS.md)**。摘要：

| 能力 | 文档 | 状态 |
|------|------|------|
| 上传→QC→训练→合成 | [W2 闭环](./architecture/2026-06-03-w2-upload-train-闭环.md) | ✅ |
| CSV 批量 + 合规 ZIP | [E2E 验收](./architecture/2026-06-10-mvp0-e2e-验收记录.md) | ✅ |
| 云端 GPU 微调 | [GPU 训练指南](./architecture/2026-06-10-云端GPU训练指南.md) | ✅ |
| 云端一键编排 | [编排 MVP](./architecture/2026-06-22-云端训练一键编排-MVP.md) | ✅ MVP |
| 音色馆 + VoiceGrant | [MVP+1](./architecture/2026-06-18-MVP+1音色馆与VoiceGrant.md) | ✅ 第一切片 |
| Web 工作台 | [页面地图](./architecture/2026-06-16-web-frontend-工作流与页面地图.md) | ✅ |

## 维护约定

- 新增调研 → `research/` + 更新 `research/README.md`
- 新增 / 变更 SRS → `requirements/` + 更新 `requirements/README.md`
- 子模块变更 → `requirements/modules/`
- PM 对外文档 → `pm/` 或同步 `deliverables/` 对应目录
- 结项检查 → 更新 [PROJECT_STATUS.md](./PROJECT_STATUS.md)
- 详见 [.cursor/rules/30-docs-versioning.mdc](../.cursor/rules/30-docs-versioning.mdc)

## 仓库外相关

| 路径 | 说明 |
|------|------|
| `../infra/engine/` | GPT-SoVITS **Docker Hub** 启动 + 微调 Spike |
| `../infra/docker/` | 平台 PG + Redis 本地 compose |
| `Desktop/GPT-SOVITS/GPT-SoVITS` | 上游引擎 clone（勿提交本仓库） |
| `prompts/` | 调研 / 需求分析 System Prompt |
| `.cursor/skills/` | Cursor Skills |
| `.cursor/rules/` | 项目规则（范围、合规、文档规范） |
