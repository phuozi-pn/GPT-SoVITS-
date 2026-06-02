---
name: gpt-sovits-product-research
description: >-
  Conducts structured product research for GPT-SoVITS voice cloning platforms
  (user personas, competitive analysis, market, compliance). Use when the user
  asks for product research, market research, user personas, competitor analysis,
  or 调研/竞品/用户画像 for voice clone SaaS or AI dubbing marketplace projects.
---

# GPT-SoVITS 产品调研

## 何时使用

用户需要**产品调研报告**、用户画像、竞品分析、市场/合规/商业模式调研，且项目与 **GPT-SoVITS 语音克隆网络平台**（音色制作、分享交易、AI 短剧配音）相关。

## 执行步骤

1. **读取系统提示词**：打开项目内 [`prompts/product-research-system-prompt.md`](../../prompts/product-research-system-prompt.md)，将其作为本次任务的 System 级约束（角色、模块、输出格式、原则）。
2. **解析用户输入**：提取调研范围、阶段、已知材料、必须回答的 1–3 个问题、目标市场（国内/海外）。
3. **按需检索**：竞品与法规信息优先用 WebSearch/WebFetch 验证；标注来源与日期。
4. **产出报告**：严格遵循提示词中的 Markdown 章节结构；缺数据写「假设 + 验证方法」。
5. **写入文件（必须）**：将完整报告保存至 `docs/research/YYYY-MM-DD-{slug}-产品调研报告.md`（见系统提示词「文档落盘」）；必要时创建目录并更新 `docs/research/README.md` 索引。
6. **收尾**：在对话中返回**文件路径**、执行摘要要点（≤5 条）、待验证 Top3；勿在聊天中重复全文。

## 项目固定上下文（勿改义）

- 技术：GPT-SoVITS；小样本克隆 ~10min；音色-韵律解耦；情感自动/手动；高频指纹、数字水印、敏感词拦截
- 平台：用户自制音色、分享/交易、AI 短剧多角色配音
- 目标：相似度 ≥90%、跨语言情感迁移、可检测与版权保护

## 竞品参考池

国际：ElevenLabs、Play.ht、Resemble AI、Descript  
国内/开源：Fish Audio、MiniMax、火山/阿里/腾讯/讯飞、CosyVoice、Fish Speech、OpenVoice、XTTS、RVC

## 输出要求

- 语言：简体中文
- **交付**：`docs/research/*.md` 完整调研报告文件
- 必含：执行摘要、≥3 类用户画像、竞品对比表、差异化机会、合规要点、风险表、待验证清单
- 不写实现代码（除非用户明确要求 Spike）

## 示例触发语

- 「做一份 GPT-SoVITS 平台的竞品和用户画像调研」
- 「只调研音色交易市场与 ElevenLabs、Fish Audio 对比」

## 延伸阅读

详细模板与表格字段见 [reference.md](reference.md)
