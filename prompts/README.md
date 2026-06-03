# 提示词与 Skill 使用说明

## 文件

| 文件 | 用途 | 输出目录 |
|------|------|----------|
| `product-research-system-prompt.md` | 产品调研 System Prompt | `docs/research/*.md` |
| `requirements-analysis-system-prompt.md` | 需求分析 System Prompt | `docs/requirements/*.md` |

Agent **默认将完整文档写入上述目录**，聊天中仅返回路径与摘要。若只要预览、不写文件，请明确说明「仅对话、不写文件」。

## 在 Cursor 中使用

1. **调研**：`@prompts/product-research-system-prompt.md` 或 Skill `gpt-sovits-product-research`
2. **需求分析**：`@prompts/requirements-analysis-system-prompt.md` 或 Skill `gpt-sovits-requirements-analysis`
3. 建议流程：生成调研 `.md` → `@docs/research/xxx.md` → 生成需求 `.md`

## 启动示例

**调研（写入 md）**

```
@prompts/product-research-system-prompt.md
范围：用户画像 + 竞品分析
重点：音色交易市场、国内合规
输出：写入 docs/research/ 的完整 .md 报告
```

**需求分析（写入 md）**

```
@prompts/requirements-analysis-system-prompt.md
阶段：MVP
总工期：4 周（若适用，将自动裁剪为 MVP-0 + MVP+1）
调研报告：@docs/research/2026-06-01-xxx-产品调研报告.md
输出：写入 docs/requirements/ 的完整 .md 需求规格
```

## 目录结构

详见 [docs/README.md](../docs/README.md)。摘要：

```
docs/
├── README.md              总索引
├── PROJECT_CHARTER.md     宪章
├── templates/word/        Word .doc 模板
├── research/              产品调研 → README.md 索引
├── requirements/          实现 SRS + modules/ + diagrams/
└── pm/                    立项/计划/需求分析（评审版）
```

生成文档后请更新对应子目录的 `README.md`。

## Skill 路径

- `.cursor/skills/gpt-sovits-product-research/`
- `.cursor/skills/gpt-sovits-requirements-analysis/`
