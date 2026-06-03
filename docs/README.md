# 文档区索引

GPT-SoVITS 语音克隆及合成系统 · 项目文档总览。按 **治理 → 调研 → 需求 → 项目管理 → 模板** 分层存放。

## 目录结构

```
docs/
├── README.md                 ← 本文件（总索引）
├── PROJECT_CHARTER.md        项目宪章（范围冻结、合规红线）
├── templates/                公司 Word 模板 + Markdown 参考结构
├── research/                 产品调研报告
├── requirements/             实现向 SRS、子模块、UML 图
└── pm/                       立项 / 计划 / 需求分析（对外评审版 Markdown）
```

## 文档类型对照

| 用途 | 读哪份 | 格式 |
|------|--------|------|
| 范围与 4 周冻结 | [PROJECT_CHARTER.md](./PROJECT_CHARTER.md) | Markdown |
| 市场 / 竞品 / 合规调研 | [research/](./research/) | Markdown |
| 研发验收、API、测试 | [requirements/2026-06-01-mvp-voice-platform-需求规格说明.md](./requirements/2026-06-01-mvp-voice-platform-需求规格说明.md) | Markdown（SRS v1.2） |
| 子模块 介绍/输入/处理/输出 | [requirements/modules/](./requirements/modules/) | Markdown A–G |
| 用例图、功能结构图 | [requirements/diagrams/](./requirements/diagrams/) | PlantUML |
| 立项 / 计划 / 需求分析（模板体例） | [pm/](./pm/) | Markdown → 同步至 Word 模板 |
| 正式 Word 空白/填报模板 | [templates/word/](./templates/word/) | `.doc` |
| 本地 Word 导出（不提交 Git） | [pm/exports/](./pm/exports/) | `.docx` 等 |

## 快速链接

### 治理

| 文档 | 说明 |
|------|------|
| [PROJECT_CHARTER.md](./PROJECT_CHARTER.md) | MVP-0 范围、指标、合规不可砍 |

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

## 维护约定

- 新增调研 → `research/` + 更新 `research/README.md`
- 新增 / 变更 SRS → `requirements/` + 更新 `requirements/README.md`
- 子模块变更 → `requirements/modules/`
- PM 对外文档 → `pm/` + 必要时更新 `templates/word/` 中对应 `.doc`
- 详见 [.cursor/rules/30-docs-versioning.mdc](../.cursor/rules/30-docs-versioning.mdc)

## 仓库外相关

| 路径 | 说明 |
|------|------|
| `prompts/` | 调研 / 需求分析 System Prompt |
| `.cursor/skills/` | Cursor Skills |
| `.cursor/rules/` | 项目规则（范围、合规、文档规范） |
