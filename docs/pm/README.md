# 项目管理文档（PM Docs）

面向 **立项评审、计划排期、需求出版** 的 Markdown 主稿；章节体例对齐公司 Word 模板。

> 实现向验收细则见 [requirements/](../requirements/)（SRS v1.2 + 子模块 A–G）。

## 索引

| 日期 | Markdown 主稿 | Word 提交 | 说明 |
|------|----------------|-----------|------|
| 2026-06-01 | [2026-06-01-立项文档.md](./2026-06-01-立项文档.md) | [deliverables/01_项目立项/](../deliverables/01_项目立项/) | 项目启动 |
| 2026-06-01 | [2026-06-01-项目计划文档.md](./2026-06-01-项目计划文档.md) | [deliverables/02_项目计划/](../deliverables/02_项目计划/) | 4 周 MVP-0 计划 |
| 2026-06-01 | [2026-06-01-需求分析文档.md](./2026-06-01-需求分析文档.md) | [deliverables/03_需求规格/](../deliverables/03_需求规格/) | 需求分析 v1.1 |

结项状态见 [docs/PROJECT_STATUS.md](../PROJECT_STATUS.md)。

## 子目录

| 目录 | 用途 |
|------|------|
| [exports/](./exports/) | 本地 Word/PDF 导出（**不提交 Git**） |
| [../deliverables/](../deliverables/) | **学校提交包**（01–07 完整目录） |

## 与 requirements/ 的分工

| 目录 | 读者 | 内容侧重 |
|------|------|----------|
| **pm/**（本目录） | 干系人、PM、评审 | 模板章节、摘要、分级表、出版用图表 |
| **requirements/** | 研发、QA、算法 | REQ 验收标准、API、NFR、子模块 I/O 全文 |

两者内容应 **一致不矛盾**；冲突时以实现 SRS（`requirements/2026-06-01-mvp-voice-platform-需求规格说明.md`）为准。
