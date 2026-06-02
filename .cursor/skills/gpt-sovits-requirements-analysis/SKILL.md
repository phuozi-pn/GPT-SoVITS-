---
name: gpt-sovits-requirements-analysis
description: >-
  Transforms research into prioritized requirements (MoSCoW, user stories,
  acceptance criteria) for GPT-SoVITS voice SaaS including marketplace and safety.
  Use when the user asks for 需求分析, SRS, PRD, 需求分级, user stories, MVP scope,
  or acceptance criteria for voice clone / AI dubbing platforms.
---

# GPT-SoVITS 需求分析

## 何时使用

已有或并行完成产品调研，需要将结论转化为 **SRS/PRD、MoSCoW 需求分级、用户故事与验收标准**，面向 MVP/GA 排期。

## 执行步骤

1. **读取系统提示词**：[`prompts/requirements-analysis-system-prompt.md`](../../prompts/requirements-analysis-system-prompt.md) 作为 System 约束。
2. **输入检查**：确认阶段（MVP/GA）、调研摘要、技术/合规约束；缺失则在「待决问题」列出。
3. **覆盖功能域**：账号、音色生命周期、合成编辑、作品协作、音色市场、安全合规、平台商业化、NFR——未涉及域标注 N/A。
4. **编写需求**：每条含 ID（REQ-001…）、级别 P0–P3、用户故事、Given-When-Then 验收、依赖、合规关联。
5. **MVP 切片**：默认 2–4 周/迭代；若用户指定 **总工期 4 周**，则 P0≤15、按周 W1–W4 排期，市场/KYC/水印延后 MVP+1。
6. **质量自检**：按提示词清单在文档内输出「质量自检」小节。
7. **写入文件（必须）**：将完整 SRS 保存至 `docs/requirements/YYYY-MM-DD-{slug}-需求规格说明.md`；文内引用 `docs/research/` 对应调研 .md。
8. **收尾**：对话中返回文件路径、P0 条数、待决 Top3；勿重复粘贴全文。

## 域模型术语（统一用词）

音色 Voice · 韵律 Prosody · 情感 Emotion · 作品 Project · 合成任务 Job · 音色市场 Marketplace

## 安全需求（按工期调整）

- **4 周 MVP-0**：授权书、敏感词、显式标识（P0）；水印/指纹/市场上架（MVP+1）
- **常规 MVP**：授权声纹校验、敏感词；指纹/水印按阶段纳入

## 与调研 Skill 协作

- 无调研报告时：先列假设，或建议用户先执行 `gpt-sovits-product-research`
- 调研中的「差异化」→ Should/Could；「合规」→ Must

## 输出要求

- 简体中文；结构见系统提示词 SRS 模板
- **交付**：`docs/requirements/*.md` 完整需求规格文件
- 禁止无验收标准的 P0

## 延伸阅读

需求 ID 命名与 MVP 裁剪见 [reference.md](reference.md)
