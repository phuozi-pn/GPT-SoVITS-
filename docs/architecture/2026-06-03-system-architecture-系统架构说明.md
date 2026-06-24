# 系统架构速览（一页纸）

| 项 | 内容 |
|----|------|
| **版本** | v2.3 |
| **日期** | 2026-06-24 |
| **完整设计** | [系统架构设计导读](./2026-06-03-system-architecture-design-系统架构设计.md) → `sections/` 分章 |
| **引擎** | GPT-SoVITS **`20250606v2pro`** · `model_tag=gsv-v2pro-20250606` |
| **W1 代码** | [apps/api/README.md](../../apps/api/README.md) |

### 变更记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0–v1.2 | 2026-06-03 | 合并版（已迁入分章文档） |
| v2.0 | 2026-06-03 | 收敛为一页纸；细节见 `sections/` |
| v2.2 | 2026-06-03 | 容器微调 Spike 4+4 闭环（`manual-spike-001`） |
| v2.3 | 2026-06-24 | MVP-0 全量交付 + MVP+1 第一切片；见 [PROJECT_STATUS](../PROJECT_STATUS.md) |

---

## 1. 五句话理解架构

1. **产品**：短剧多角色配音工作台，4 周 MVP-0 验证训练+合成+合规闭环。  
2. **分层**：Web → API → ComplianceGateway → Job 队列 → GPU Worker → v2Pro。  
3. **边界**：合规/CSV/项目自研；训练推理走 Worker，不 fork 模型仓库。  
4. **交付波次**：W1–W4 MVP-0 ✅ · MVP+1 音色馆第一切片 ✅ · 云端训练编排 MVP ✅。  
5. **包名**：横切层 Python 包 **`voice_platform`**（非 `platform`）。

---

## 2. 架构原则（P1–P5）

| # | 原则 |
|---|------|
| P1 | 引擎与平台分离 |
| P2 | v2Pro 版本 pinned |
| P3 | 最小 fork（换镜像 tag） |
| P4 | 合规不可绕过 |
| P5 | 4 周可交付，扩展预留 |

→ 展开：[01-背景与原则](./sections/01-背景与原则.md)

---

## 3. ADR 摘要

| ADR | 决策 |
|-----|------|
| 001 | 引擎 **v2Pro**（非 v3/v4 首发） |
| 002 | 不用 Gradio 作生产 UI |
| 003 | 对外下载仅合规导出通道 |
| 004 | 引擎 **Docker Hub** 官方镜像 |

→ 展开：[05-技术决策与质量](./sections/05-技术决策与质量.md)

---

## 4. MVP-0 部署（最小）

| 组件 | 数量 |
|------|------|
| API（本机 :8000） | 1 |
| PostgreSQL + Redis | 各 1 |
| GPU 引擎容器 | 1（WebUI 9874 / api_v2 9880） |
| Infer + Train Worker | 本机 Python 进程 |

→ 展开：[02-架构视图 §2.2](./sections/02-架构视图.md#22-部署架构mvp-0)

---

## 5. Job 类型

| 类型 | Worker | W1 |
|------|--------|-----|
| preprocess | CPU | — |
| train | GPU ~12GB（Spike 单样本 **~6.5GB** 峰值） | ✅ Mock + Spike 4+4 |
| synthesize | GPU ~5GB | ✅ Mock + 9880 |
| export | CPU ffmpeg | W3 |

→ 展开：[04-运行时与集成 §4.3](./sections/04-运行时与集成.md#43-job-编排)

---

## 6. 评审与 TBD

| 项 | 内容 |
|----|------|
| **W1 Core** | ✅ API + Job + JWT + 配额 + Gateway 测试（28 pytest） |
| **Spike** | ✅ 零样本推理 · ✅ 微调 4+4 epoch（5080 16GB） |
| **W2** | CSV / 项目 / 素材上传 API |
| **TBD 全表** | [07-路线图 §7.3](./sections/07-路线图与追溯.md#73-待定项tbd) |

→ 展开：[06-设计理由与评审](./sections/06-设计理由与评审.md)

---

## 7. 图件与 Spike

| 资源 | 路径 | 状态 |
|------|------|------|
| PlantUML | [diagrams/](./diagrams/) | 待补 |
| W1 引擎验证 | [w1-spike](./2026-06-03-w1-spike-v2pro-快速验证.md) | ✅ 推理 + 微调 2026-06-03 |
| 本地运行 | [apps/api/README](../../apps/api/README.md) | ✅ |
