# /init — 生成/更新项目宪章（Project Charter）

## 目的

把当前仓库的“项目宪章（项目宪法）”固化到 `docs/PROJECT_CHARTER.md`，并同步生成/更新 `.cursor/rules/` 规则文件，让后续在 Cursor 中的 Agent 自动遵守：

- **4 周 MVP-0**（范围冻结）
- **合规最低集**（授权书、显式标识、敏感词、AI 告知）
- **文档落盘规范**（`docs/research/`、`docs/requirements/`）
- 输出语言：**简体中文**

## 你必须执行的动作（逐条完成）

1. **读取现有文档作为事实来源**（不要编造）：
   - `docs/research/2026-06-01-voice-marketplace-compliance-产品调研报告.md`
   - `docs/requirements/2026-06-01-mvp-voice-platform-需求规格说明.md`
2. **生成或增量更新** `docs/PROJECT_CHARTER.md`：
   - 保留版本与变更记录（如已存在则升版本）
   - 明确：愿景、4 周目标、成功指标、范围冻结（MVP-0 14 条 P0 + MVP+1 清单）、合规红线、决策机制、文档规范
3. **生成或更新** `.cursor/rules/` 下的规则文件（若已存在则增量更新，不要重复堆砌）：
   - `00-language.mdc`
   - `10-mvp0-scope-4weeks.mdc`
   - `20-compliance-safety-redlines.mdc`
   - `30-docs-versioning.mdc`
4. **对话中只返回**：
   - 写入/更新了哪些文件（含路径）
   - 宪章的 5 条核心要点
   - MVP-0 的“必须/禁止”各 Top5

## 宪章模板（写入 docs/PROJECT_CHARTER.md）

按以下结构输出（可扩充，但不要删章节）：

```markdown
# 项目宪章（Project Charter）：GPT-SoVITS 语音克隆网络平台

## 文档信息
- 版本：
- 更新日期：
- 关联调研：
- 关联需求规格：

## 1. 愿景与边界
## 2. 4 周 MVP-0 目标（不可变更，除非走变更流程）
## 3. 成功指标（4 周末验收）
## 4. 范围冻结
### 4.1 MVP-0（4 周）必须交付（14 条 P0）
### 4.2 MVP+1（第 5–8 周）候选清单
## 5. 合规与安全红线（必须遵守）
## 6. 文档与版本管理规范（GitHub）
## 7. 决策与变更流程（谁能改、怎么改、如何记录）
## 8. 附录：术语表
```

## 重要约束（不可违反）

- 不要在宪章里加入实现代码。
- 不要把“音色交易市场 UI”写进 4 周 MVP-0。
- 合规最低集必须写成“必须交付”，不要写“后续再做”。

