# -*- coding: utf-8 -*-
"""Fill 实训个人周报 template via Word COM."""
import shutil
from pathlib import Path

import win32com.client

SRC = Path(r"c:\Users\panta\Desktop\GPT\docs\templates\word\实训个人周报--模版.doc")
DST_DIR = Path(r"c:\Users\panta\Desktop\GPT\docs\pm\exports")
DST = DST_DIR / "2026-06-03-实训个人周报-陶攀.doc"

CONTENT = {
    "name": "陶攀",
    "student_id": "",  # 学号请自行补填
    "class": "2302班",
    "project": "GPT-SoVITS语音克隆及合成系统（短剧向工作台）",
    "week": "2026.06.02—2026.06.08（项目第1周 / W1）",
    "practice": """一、本周主要学习内容
1. GPT-SoVITS 语音克隆原理与短剧配音业务场景：零样本/微调、GPT（s1）+ SoVITS（s2）两阶段训练流程。
2. MVP-0 范围冻结与合规红线：14 条 P0 需求（授权书、敏感词、AI 告知、显式标识导出等不可裁剪）。
3. 软件工程文档规范：调研报告 → 需求规格（SRS）→ 子模块规格 → 架构说明的分层写法。

二、项目实践内容
1. 完成项目立项、4 周项目计划及需求分析文档（v1.1），对齐公司 Word 模板体例。
2. 编写实现向 SRS v1.2 及 A–G 七个子模块规格（介绍/输入/处理/输出/验收）。
3. 绘制系统用例图、功能结构图（PlantUML），并在需求分析文档中补充 Mermaid 功能结构图。
4. 整理 docs 文档区目录（research / requirements / pm / architecture），更新索引与版本规范。
5. 完成系统架构说明 v1.0：确定引擎基线为 GPT-SoVITS v2Pro（tag 20250606v2pro），明确自研平台与开源引擎边界。
6. 编写 W1 Spike 快速验证指南，在本机（RTX 5080）着手搭建上游 WebUI 运行环境。""",
    "problems": """一、遇到的问题

1. 文档体例不统一、双轨维护成本高
立项/计划/需求分析需同时满足公司 Word 模板与公司评审习惯，初期 Markdown 正文与 .doc 模板章节对应关系不清晰，容易出现「改了 md 忘了同步 Word」或版本号不一致的问题。

2. 需求粒度难以把握
MVP-0 仅 4 周，但短剧配音涉及账号、合规、素材质检、训练、CSV 批量、导出等完整链路。若全部写进一份 SRS 会过于臃肿；若拆太细又担心开发对不上验收标准。

3. 引擎版本选型困难
GPT-SoVITS 上游存在 v2 / v2Pro / v3 / v4 多条技术路线：v3/v4 音质潜力高但对素材质量更挑剔；v2Pro 增加 SV 嵌入后训练流程更复杂。结合「~10 分钟普通干声可训」「单卡可部署」「4 周内可集成」等约束，难以快速拍板。

4. 自研平台与开源引擎边界模糊
若直接把 Gradio WebUI 当生产系统，无法满足多租户、CSV 批量、配额与合规门禁；若深度 fork 模型代码进业务仓库，upstream 升级与 OOM 隔离都会变难。

5. 本地运行环境搭建受阻
本机为 Windows + Python 3.12 + RTX 5080（16GB）。上游官方更推荐 Linux 与 Python 3.10/3.11；预训练权重体积大、目录结构需与 WebUI 配置严格对齐；新显卡与 PyTorch/CUDA 版本匹配也存在不确定性。

6. Git 与 Office 文件管理
.docx 导出物是否入库、模板 .doc 与生成物如何区分，初期 .gitignore 配置不当导致 docx 被忽略或误提交。

二、思考过程与解决方法

1. 文档双轨问题
思考：评审对外看 Word，研发对内看 Markdown，必须明确「单一事实来源」而非两套并行正文。
方法：约定 docs/pm/*.md 与 docs/requirements/ 为唯一正文源；templates/word/ 只保留空白/填报模板；本地导出统一放 docs/pm/exports/ 且 gitignore；新增 .cursor/rules/30-docs-versioning.mdc 固化命名与索引更新流程。小改用文内版本号（v1.0→v1.1），变更记录表留痕。

2. 需求粒度问题
思考：出版向需求分析与实现向 SRS 受众不同，不应混在一份文档里硬塞 API 细节。
方法：拆成三层——调研报告（Why）、PM 需求分析（What + 用例/数据字典）、实现 SRS + 子模块 A–G（How + 验收）。子模块统一采用「介绍/输入/处理/输出/异常/验收」六段式，与 14 条 P0 一一映射，便于 WBS 分工。

3. 引擎选型问题
思考：用 ADR 方式列出备选方案与拒绝理由，以 W1 Spike 可验证性为最高优先级，而非追最新版本。
方法：对照 REQ-004/005 与宪章成功指标，编写架构说明 §3 ADR，选定 v2Pro（tag 20250606v2pro，model_tag=gsv-v2pro-20250606）。理由：10min 普通干声可训、SV 提升相似度、推理速度接近 v2、训练 VRAM ~12GB 单 A10/5080 可跑；MVP-0 只维护一条引擎线，v3/v4 推迟到 MVP+1 评估。

4. 平台/引擎边界问题
思考：P0 中的合规、CSV、配额是产品能力，不应 fork 进模型仓库；Worker 应可替换、可 pinned、可回滚。
方法：架构六层拆分——Presentation/Platform/Compliance 自研，Engine 层容器化 Train/Infer Worker，Post 层 ffmpeg 显式标识。最小 fork，升级 = 换镜像 tag；Gradio 仅作 W1 Spike 调试，不作生产 UI。

5. 本地环境问题
思考：Spike 目标是「验证引擎可行」而非「一次搭完生产环境」，应分 P0/P1/P2 递进。
方法：编写 W1 Spike 指南——clone pinned tag → venv → 本地权重放入 pretrained_models/ → webui.py 零样本试听（P0/P1）；完整微调留 P2。Python 3.12 若装依赖失败则改 3.11 venv；Windows 报错则记录日志并备选 WSL2；5080 优先试 cu124 PyTorch，用 python -c 验证 torch.cuda.is_available()。

6. Git/Office 管理问题
思考：模板要入库、导出物不应污染仓库历史。
方法：.gitignore 忽略 exports/* 但保留 exports/README.md；仅提交 .doc 模板；docx 由同学生成后本地提交或交导师，不强制进 main。

三、收获与反思

1. 先冻结范围再写细：宪章 14 条 P0 不动，细节往子模块和架构 TBD 里填，避免需求膨胀。
2. 文档也是交付物：索引、版本号、交叉引用和代码同等重要，否则团队找不到「该信哪份」。
3. 技术 Spike 要趁早：引擎选型不能只看 Wiki，必须本机跑通一次再写 Worker 接口。

四、下周计划

1. 跑通 GPT-SoVITS v2Pro 零样本/微调 + 单句合成 Spike，记录 VRAM/耗时，回填架构 §11 TBD。
2. 补全架构 PlantUML 图件，启动业务 API 与训练 Job 队列骨架（REQ-005/022）。""",
}


def set_cell(table, row, col, text: str) -> None:
    cell = table.Cell(row, col)
    rng = cell.Range
    rng.Text = text
    # trim trailing cell mark
    if rng.Text.endswith("\r\x07"):
        rng.End = rng.End - 1


def main() -> None:
    DST_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC, DST)

    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    doc = word.Documents.Open(str(DST.resolve()))
    t = doc.Tables(1)

    # Row1: 姓名 | 学号 | 专业班级
    set_cell(t, 1, 2, CONTENT["name"])
    set_cell(t, 1, 4, CONTENT["student_id"])
    set_cell(t, 1, 6, CONTENT["class"])

    # Row2: 项目名称 | 时间/周次（col3-6 may be merged）
    set_cell(t, 2, 2, CONTENT["project"])
    set_cell(t, 2, 4, CONTENT["week"])

    # Row3-4: long text cells (col2 merged across)
    set_cell(t, 3, 2, CONTENT["practice"])
    set_cell(t, 4, 2, CONTENT["problems"])

    doc.Save()
    doc.Close()
    word.Quit()
    print(f"Saved: {DST}")


if __name__ == "__main__":
    main()
