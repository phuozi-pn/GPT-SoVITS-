# 需求规格（实现向）

研发、测试、算法使用的 **SRS、子模块规格与 UML**。对外评审版见 [pm/2026-06-01-需求分析文档.md](../pm/2026-06-01-需求分析文档.md)。

## 命名规则

`YYYY-MM-DD-{主题slug}-需求规格说明.md`

## 主文档

| 版本 | 文件 | 阶段 | 基于调研 |
|------|------|------|----------|
| v1.2 | [2026-06-01-mvp-voice-platform-需求规格说明.md](./2026-06-01-mvp-voice-platform-需求规格说明.md) | MVP-0（4 周）+ NFR/API/测试/运营 | [调研 v1.1](../research/2026-06-01-voice-marketplace-compliance-产品调研报告.md) |
| v1.0 | [2026-06-19-制作场景三分法-短剧情景演唱.md](./2026-06-19-制作场景三分法-短剧情景演唱.md) | 制作三分场景（短剧/情景/演唱） | 架构工作流地图 |
| v1.0 | [2026-06-25-短剧批量配音方案.md](./2026-06-25-短剧批量配音方案.md) | 短剧批量 SOP、CSV 规范、交付质检 | 模块 E/F |
| v1.0 | [2026-06-26-训练配额运营说明.md](./2026-06-26-训练配额运营说明.md) | 训练/合成计量、套餐档位、运营调额 SOP | 模块 A、REQ-023 |

## 子目录

| 目录 | 内容 |
|------|------|
| [modules/](./modules/) | 子模块 A–G：介绍 / 输入 / 处理 / 输出 |
| [diagrams/](./diagrams/) | PlantUML：用例图、功能结构图 |

### 子模块索引

| 模块 | 文件 | REQ |
|------|------|-----|
| A · 账号与配额 | [modules/2026-06-01-module-A-账号与配额.md](./modules/2026-06-01-module-A-账号与配额.md) | 001, 023 |
| B · 授权与告知 | [modules/2026-06-01-module-B-授权与告知.md](./modules/2026-06-01-module-B-授权与告知.md) | 003, 021 |
| C · 素材与质检 | [modules/2026-06-01-module-C-素材上传与质检.md](./modules/2026-06-01-module-C-素材上传与质检.md) | 004 |
| D · 训练与版本 | [modules/2026-06-01-module-D-训练与音色版本.md](./modules/2026-06-01-module-D-训练与音色版本.md) | 005, 022 |
| E · 项目与 CSV | [modules/2026-06-01-module-E-项目角色与CSV.md](./modules/2026-06-01-module-E-项目角色与CSV.md) | 012–014 |
| F · 合成与导出 | [modules/2026-06-01-module-F-合成与导出.md](./modules/2026-06-01-module-F-合成与导出.md) | 007, 010, 011 |
| G · 敏感词 | [modules/2026-06-01-module-G-敏感词拦截.md](./modules/2026-06-01-module-G-敏感词拦截.md) | 009 |

### UML 索引

| 图 | 文件 |
|----|------|
| 系统用例图 | [diagrams/2026-06-01-mvp-voice-platform-系统用例图.puml](./diagrams/2026-06-01-mvp-voice-platform-系统用例图.puml) |
| 功能结构图 | [diagrams/2026-06-01-mvp-voice-platform-系统功能结构图.puml](./diagrams/2026-06-01-mvp-voice-platform-系统功能结构图.puml) |

渲染：VS Code PlantUML 扩展 `Alt+D`，或 [PlantUML 在线](https://www.plantuml.com/plantuml/uml)。
