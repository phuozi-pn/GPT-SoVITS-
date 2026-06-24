# -*- coding: utf-8 -*-
"""Fill 实训工作日志 + 实训个人周报 templates via Word COM (preserve .doc format)."""
from __future__ import annotations

import shutil
from pathlib import Path

import win32com.client

BASE = Path(
    r"c:\Users\panta\Downloads\项目序号_项目名称_交付物\项目序号_项目名称_交付物\07_日常报告"
)
WORK_LOG_SRC = BASE / "工作日志-模版(1).doc"
WEEKLY_SRC = BASE / "实训个人周报--模版.doc"
WORK_LOG_DST = BASE / "工作日志-陶攀-U202317278.doc"
WEEKLY_DST = BASE / "实训个人周报-陶攀-U202317278.doc"

META = {
    "name": "陶攀",
    "student_id": "U202317278",
    "class": "2302班",
    "project": "GPT-SoVITS语音克隆及合成系统（短剧向工作台）",
    "teacher": "王文鑫",
}

# 15 个工作日，对齐项目 2026-06-02 起（跳过周末）
WORK_LOG_DAYS: list[tuple[str, str, str]] = [
    (
        "第1天\n（2026.6.2）",
        "【项目启动与范围冻结】\n"
        "1. 研读短剧配音调研报告，明确用户痛点：改词重录成本高、角色音色不一致、合规过审风险。\n"
        "2. 完成《立项报告》：定义 4 周 MVP-0 目标——授权→素材质检→训练→合成→合规导出闭环。\n"
        "3. 编写《项目计划（简版）》：WBS 分解 12 个工作包、75 人天估算；甘特图对齐 W1 Core / W2 Workflow / W3 Export / W4 加固。\n"
        "4. 完成《需求分析文档》v1.1：六大功能域、用例图、数据字典；冻结 14 条 P0 需求（REQ-003~014 等）。\n"
        "5. 编写 PROJECT_CHARTER.md，明确禁止项：未授权克隆、名人仿声、Gradio 作生产 UI。\n"
        "6. 与指导老师王文鑫评审范围，确认 MVP+1 音色市场不纳入 4 周交付。",
        "立项三件套（立项/计划/需求分析）定稿；宪章与 P0 清单评审通过；Git 仓库初始化完成。",
    ),
    (
        "第2天\n（2026.6.3）",
        "【需求规格与子模块细化】\n"
        "1. 编写实现向 SRS v1.2：逐条 P0 写清验收标准、API 契约、异常码与 NFR（性能/可用性）。\n"
        "2. 拆分子模块 A–G 规格：账号(A)、合规(B)、素材(C)、训练(D)、合成(E)、项目/CSV(F)、导出(G)。\n"
        "3. 每子模块采用「介绍/输入/处理/输出/异常/验收」六段式，与 WBS 任务包一一映射。\n"
        "4. 整理 docs 目录：research/（调研）、requirements/（SRS+modules）、pm/（出版向）、architecture/（设计）。\n"
        "5. 绘制系统用例图、功能结构图（PlantUML），在需求分析文档中补充 Mermaid 功能结构图。\n"
        "6. 新增 .cursor/rules 文档版本规范，约定 Markdown 为单一事实来源、Word 为导出物。",
        "SRS v1.2 与子模块 A–G 全文落盘；docs 索引 README 更新；需求与 P0 追溯矩阵可追溯。",
    ),
    (
        "第3天\n（2026.6.4）",
        "【系统架构设计】\n"
        "1. 完成架构设计分章文档 v2.0：01 背景与原则（P1–P5）、02 逻辑/部署视图、03 领域分层。\n"
        "2. 编写 04 运行时与集成：业务流时序图、ER 模型、Job 状态机、ComplianceGateway 契约。\n"
        "3. 撰写 ADR-001~004：选定 v2Pro（非 v3/v4 首发）、不用 Gradio 作生产 UI、导出单通道、Docker Hub 镜像。\n"
        "4. 确定引擎基线：GPT-SoVITS tag 20250606v2pro，model_tag=gsv-v2pro-20250606。\n"
        "5. 定义六层架构：Presentation → Platform API → Compliance → Job Queue → GPU Worker → v2Pro Engine。\n"
        "6. 架构评审结论「有条件通过」：W1 须闭合 Spike、TBD 项与测试计划。",
        "架构导读 + 7 章 sections 完成；ADR 与引擎版本决策记录；PlantUML 部署图初稿完成。",
    ),
    (
        "第4天\n（2026.6.5）",
        "【W1 Spike 引擎验证】\n"
        "1. 编写《W1 Spike 快速验证指南》：clone pinned tag → venv → 预训练权重目录结构说明。\n"
        "2. 本机 Windows + RTX 5080（16GB）搭建上游 GPT-SoVITS：WebUI 9874、api_v2 合成 9880。\n"
        "3. 解决 Python 3.12 依赖兼容：部分包装 3.11 venv；验证 torch.cuda.is_available()。\n"
        "4. 完成零样本（zero-shot）试听 Spike：3–10s 参考音频 + 目标文本 → wav 输出。\n"
        "5. 记录 Spike 指标：合成延迟、VRAM 占用约 6–8GB、api_v2 请求 JSON 格式。\n"
        "6. 编写 infra/engine/README.md，约定引擎与平台仓库分离、升级 = 换镜像 tag。",
        "零样本合成 Spike 通过；引擎 api_v2 可在 9880 稳定响应；Spike 指标回填架构 TBD 表。",
    ),
    (
        "第5天\n（2026.6.6）",
        "【平台工程骨架搭建】\n"
        "1. 初始化 monorepo：apps/api（FastAPI）、apps/web（Vue3+Vite）、domains/、voice_platform/、workers/。\n"
        "2. voice_platform 共享内核：config.py、JWT 鉴权、Job models/schemas/repository、存储 resolve。\n"
        "3. infra/docker：PostgreSQL + Redis docker-compose；编写 SQL 迁移 001~021 增量脚本。\n"
        "4. apps/api 模块化路由注册（architecture/modules.py）；OpenAPI /api/v1/docs 可访问。\n"
        "5. 配置 .env.example：DATABASE_URL、REDIS_URL、ENGINE_TTS_URL、TRAIN_MOCK 等环境变量说明。\n"
        "6. 编写 apps/api/README.md 与 scripts/platform_start.ps1 一键启动脚本。",
        "monorepo 目录结构定型；docker compose 可拉起 PG+Redis；API 健康检查 /health 返回 200。",
    ),
    (
        "第6天\n（2026.6.9）",
        "【Job 队列与 Worker 进程】\n"
        "1. 实现统一 Job 模型：queued → running → succeeded/failed/cancelled；hyperparams JSON 透传。\n"
        "2. voice_platform/job/repository.py：Job 入队、认领、状态更新、进度字段 progress_pct/message。\n"
        "3. workers/train/runner.py：Train Worker 轮询 train 类型 Job，调用 EngineTrainAdapter。\n"
        "4. workers/infer/runner.py：Infer Worker 处理 synthesis/batch 类型 Job。\n"
        "5. workers/base.py 抽象公共逻辑：DB 连接、日志、优雅退出；scripts/platform_status.ps1 查看进程。\n"
        "6. 编写 tests/test_train_dataset.py 等基础单测；REQ-005/022 训练可观测性初步满足。",
        "train/infer worker 可独立拉起并消费 Redis 队列；Job 状态可在 API GET /jobs/{id} 轮询。",
    ),
    (
        "第7天\n（2026.6.10）",
        "【素材上传与质检 QC】\n"
        "1. domains/assets/service.py：multipart 上传、wav 转码（ffmpeg）、storage_uri 写入 local:// 路径。\n"
        "2. domains/assets/qc.py：时长检测（8min~1h）、采样率、信噪比粗检、静音段比例；输出 qc_result JSON。\n"
        "3. API：POST /voices/assets 上传、GET .../qc 查报告、POST .../confirm 锁定素材。\n"
        "4. 授权流 domains/consents/service.py：POST /consents；dev 模式 CONSENT_AUTO_APPROVE=true 自动通过。\n"
        "5. POST /voices/{id}/train 创建训练 Job；Train Worker 解析 storage_uri 定位 data/storage/ 文件。\n"
        "6. 编写 scripts/smoke_w2_upload_train.py 冒烟脚本，验证上传→QC→训练 Mock 全链路。",
        "W2 上传训练闭环后端打通；smoke_w2_upload_train.py 本地执行通过（TRAIN_MOCK=true）。",
    ),
    (
        "第8天\n（2026.6.11）",
        "【推理引擎对接与单条合成】\n"
        "1. workers/infer/runner.py 对接 GPT-SoVITS api_v2（9880）：text、ref_audio、speed 等参数映射。\n"
        "2. voice_platform/engine/infer_weights.py：解析 .ckpt/.pth 路径，支持完整微调权重与快速克隆模式。\n"
        "3. domains/voices/service.py：VoiceVersion 注册；训练完成后写入 weight_path、model_tag。\n"
        "4. POST /api/v1/synthesis 单条合成 API；返回 audio_url 与用量扣减（配额 REQ-023）。\n"
        "5. .env 设置 ENGINE_MOCK=false、ENGINE_TTS_URL=http://127.0.0.1:9880 跑真实合成。\n"
        "6. tests/test_infer_engine_adapter.py 补充引擎适配器单测；记录 9880 超时与重试策略。",
        "ENGINE_MOCK=false 下真实 TTS 合成成功；单条合成 API 返回可播放 wav；配额扣减逻辑可用。",
    ),
    (
        "第9天\n（2026.6.12）",
        "【Web 工作台 Studio / Library】\n"
        "1. apps/web Vue3 项目：Vite + TypeScript + Tailwind；复古录音室 UI 规范（gallery.css/shell.css）。\n"
        "2. StudioView.vue：上传干声、授权勾选、QC 结果展示、触发训练、TapePlayer 试听组件。\n"
        "3. LibraryView.vue：音色列表、权重导入入口、版本切换、在线试听。\n"
        "4. api/client.ts 统一 fetch 封装；X-User-Id dev 头切换多用户；apiErrors.ts 错误码映射中文。\n"
        "5. 路由：/studio、/library、/projects；AppLayout.vue 侧边栏导航。\n"
        "6. 编写《复古录音室页面规范》与 Web 前端验收清单初稿。",
        "http://127.0.0.1:5173/studio 与 /library 可访问；上传→训练→试听 UI 链路打通。",
    ),
    (
        "第10天\n（2026.6.13）",
        "【W2 CSV 批量配音工作流】\n"
        "1. domains/projects/service.py：项目 Project、角色 Role、台词 Script 数据模型与 CRUD API。\n"
        "2. CSV 导入解析：角色名、台词文本、情感标签列；校验角色与音色绑定关系（REQ-012–014）。\n"
        "3. workers/batch/runner.py：批量合成 Job，逐条调用 infer adapter，汇总分轨 wav。\n"
        "4. 导出 ZIP：按角色名分目录打包；ComplianceGateway 前置校验（授权+敏感词扫描）。\n"
        "5. MakeWorkspace.vue / ScriptEditor.vue / SegmentBlock.vue：制作页分镜编辑、逐段试听、批量生成。\n"
        "6. 提交 commit「MVP-0 平台工程 — API/Web/Worker 与 W2 工作流」；batch_template.csv 样例更新。",
        "项目→角色→CSV→批量合成→分轨 ZIP 端到端跑通；W2 核心验收项全部可演示。",
    ),
    (
        "第11天\n（2026.6.16）",
        "【云端训练与权重导入】\n"
        "1. 编写《云端 GPU 训练指南》：AutoDL 租 GPU、clone 引擎、bash infra/engine/cloud/train.sh 一键微调。\n"
        "2. train.sh 流程：音频切分 → FunASR 对齐 → v2Pro 4+4 epoch spike 训练 → 输出 .ckpt/.pth。\n"
        "3. scripts/import_engine_weights.py：扫描 ENGINE_TRAIN_ROOT，注册 VoiceVersion 到平台 DB。\n"
        "4. 编写《云端权重接入 Web 合成》：scp 回本机 → import → Library 试听 → 批量配音。\n"
        "5. voice_platform/engine/ref_audio.py：参考音频路径解析；快速克隆 long audio 切片逻辑。\n"
        "6. scripts/prep_bilibili_studio_wav.py：B 站素材下载预处理，生成 studio 测试样本。",
        "云端训练→本机导入→Web 合成闭环文档与脚本齐全；蛊真人等测试音色可 Library 试听。",
    ),
    (
        "第12天\n（2026.6.17）",
        "【W3 合规导出模块】\n"
        "1. domains/compliance/export.py：ComplianceGateway 统一门禁——授权书、敏感词、AI 告知三项校验。\n"
        "2. 敏感词库扫描：命中记录写入审计日志，不阻断合成主路径（REQ-009）；仅导出时强制拦截。\n"
        "3. 显式标识导出：ffmpeg 在音频首尾插入 beep 水印 + metadata 写入 AI 合成标识（REQ-010）。\n"
        "4. 授权书 PDF 生成 voice_platform/licensing/certificate_pdf.py；授权流转 API 完善。\n"
        "5. 导出 API 单通道：对外下载仅走 /compliance/export，禁止直接访问原始 storage。\n"
        "6. tests/test_compliance_watermark_meta.py、test_quality_and_pdf.py 补充合规单测。",
        "合规导出单通道上线；敏感词/授权/水印三项门禁服务端强制；W3 验收项可演示。",
    ),
    (
        "第13天\n（2026.6.18）",
        "【MVP+1 音色馆与 VoiceGrant】\n"
        "1. domains/marketplace/service.py + voice_platform/marketplace/：Catalog 发布、审核、标签索引。\n"
        "2. API：GET /catalog/voices 公开列表、POST 发布、运营 POST approve/reject、VoiceGrant 跨用户授权。\n"
        "3. 迁移 022_marketplace_invites.sql：邀请码 + waitlist；023 授权书驳回原因字段。\n"
        "4. CatalogView.vue / CatalogVoiceGrid.vue：音色馆浏览、发布、精选试听、授权他人合成。\n"
        "5. domains/licensing/service.py：VoiceGrant 有效期、撤销；合成门禁校验 owner/公开/Grant。\n"
        "6. 编写《MVP+1 音色馆与 VoiceGrant》架构文档；tests/test_marketplace_invite.py。",
        "音色馆第一切片完成：发布→审核→公开展示→VoiceGrant 授权；/catalog 页面可演示。",
    ),
    (
        "第14天\n（2026.6.19）",
        "【前端模块化与演示路径冻结】\n"
        "1. Web 路由模块化：modules/voice、produce、social、ops 四大域；router/modules/*.routes.ts 拆分。\n"
        "2. 编写《展示站与工作台 IA》《Web 模块化 IA》《全栈模块化架构》三份 IA 文档。\n"
        "3. 制作场景三分法：短剧/情景/演唱 ProduceSceneGuide.vue；EditorToolbar 与 PartialAdjustBar 优化。\n"
        "4. 《对外演示路径冻结》：Studio 上传→训练→Library 导入→Projects 批量→Catalog 发布 固定演示脚本。\n"
        "5. 《MVP-0 E2E 验收记录》：逐条 P0 打勾；W4 CI/部署文档与生产认证部署清单初稿。\n"
        "6. 提交 commit「W3 合规 + W4 CI/部署 + MVP+1 音色馆」大版本合并。",
        "页面地图与演示路径文档定稿；E2E 验收记录 14 条 P0 全部有对应演示步骤。",
    ),
    (
        "第15天\n（2026.6.24）",
        "【云端一键编排与 MVP+1 扩展】\n"
        "1. voice_platform/cloud_train/：SSH 客户端、orchestrator 编排器、profile_repository 用户 GPU 凭证加密存储。\n"
        "2. CloudTrainAdapter + train_from_dataset.sh：本机 dataset 预处理（faster-whisper ASR）→ SCP 上传 → 远端微调 → 拉回权重。\n"
        "3. StudioView.vue + CloudGpuConnectForm.vue：用户填写 AutoDL SSH、连接自检、训练进度横幅 StudioJobBanner。\n"
        "4. 支付 Provider 抽象：payment/providers/alipay.py 沙箱、wechat/mock；scripts/smoke_alipay_sandbox_checkout.py。\n"
        "5. 开发者 Webhook 可靠投递 voice_platform/webhook/delivery.py；KYC providers/saas.py 多提供商抽象。\n"
        "6. 指纹模块 fingerprint/encoder.py + 迁移 024；水印 MOS Spike 调研；补充 20+ pytest 用例。\n"
        "7. 编写《云端训练一键编排 MVP》《支付宝沙箱联调》《本地用户自训练指南》架构文档。",
        "云端训练编排核心代码与文档已落地；支付/KYC/Webhook 骨架可单元测试；AutoDL 端到端联调进行中。",
    ),
]

WEEKLY = {
    "week": "2026.06.17—2026.06.23（项目第3周 / W3）",
    "practice": """一、本周主要学习内容

1. 合规网关（ComplianceGateway）设计模式
   学习如何将授权书校验、敏感词扫描、AI 告知确认三类合规检查收敛到统一服务端门禁，而非分散在各 API 路由中。理解「合成主路径不阻断、导出单通道强制」的产品策略——用户可边配边试，但对外交付必须带显式标识。

2. GPT-SoVITS v2Pro 云端微调完整链路
   深入学习两阶段训练（GPT s1 + SoVITS s2）、SV 说话人嵌入、4+4 epoch spike 配置；掌握 AutoDL 租 GPU → train.sh 切分/FunASR 对齐/微调 → scp 权重回本机 → import_engine_weights 注册的端到端流程。

3. MVP+1 音色市场 Phase 1–3 产品设计
   学习 Catalog 发布审核流、VoiceGrant 跨用户授权模型、waitlist 邀请码机制；理解「owner / 公开馆 / 有效 Grant」三态合成权限判定逻辑。

4. 全栈模块化架构与 IA 设计
   学习如何将 Vue 前端按 voice/produce/social/ops 四域拆分，后端 domains/ 与 voice_platform/ 横切层对齐；掌握展示站（获客）与工作台（生产）双层 IA 的信息架构方法。

5. 支付/KYC/Webhook 可插拔 Provider 模式
   学习 Provider 抽象层设计：alipay/wechat/mock 支付、saas/manual KYC、Webhook 可靠投递（重试+审计），为生产化预留扩展点而不阻塞 MVP 演示。

二、项目实践内容（按时间线）

【6月17日 · 合规模块】
1. 实现 domains/compliance/export.py：ComplianceGateway 三类校验（授权/敏感词/告知）。
2. ffmpeg 显式标识：音频首尾 beep 水印 + metadata 写入「本音频由 AI 合成」字段。
3. 敏感词命中写审计日志但不阻断 POST /synthesis；仅 POST /compliance/export 强制拦截。
4. 授权书 PDF 生成与流转；补充 test_compliance_watermark_meta.py 单测。

【6月18日 · 音色馆 MVP+1】
1. 新增 voice_catalog_entries、voice_grants 数据表（迁移 022/023）。
2. 实现 Catalog API 全套：发布/审核/标签/精选/样音重生成；VoiceGrant 授权/撤销/列表。
3. 前端 CatalogView.vue：音色馆浏览、发布表单、授权弹窗、管理员审核面板。
4. 合成门禁：owner 或公开馆或有效 Grant 三者满足其一方可合成。

【6月19日 · 模块化与验收】
1. Web 路由拆分为 modules/voice、produce、social、ops；Ops 含 AdminView、DeveloperView。
2. 制作场景三分法落地：短剧/情景/演唱引导文案与参数预设。
3. 编写《对外演示路径冻结》与《MVP-0 E2E 验收记录》，14 条 P0 逐条对应演示步骤。
4. 提交大版本 commit：W3 合规 + W4 CI/部署 + MVP+1 音色馆。

【6月20日 · 架构加固】
1. 提交 commit「MVP+1 架构改进」：模块分层、错误响应格式统一、测试补充。
2. apps/api/architecture/modules.py 模块注册规范化；apiErrors.ts 前端错误码中文映射。
3. 补充 tests/test_api_module_registry.py 等回归测试。

【6月21–23日 · 云端编排与扩展】
1. voice_platform/cloud_train/ 包：ssh_client、orchestrator、local_dataset（faster-whisper ASR）、credentials 加密。
2. workers/train/cloud_adapter.py：CloudTrainAdapter 替换 MockTrainAdapter，支持 train_backend=cloud。
3. Studio CloudGpuConnectForm.vue：用户 SSH 凭证表单、连接自检 API、训练进度 StudioJobBanner。
4. 支付 providers（alipay 沙箱/mock/wechat）、Webhook delivery、KYC saas/manual providers 骨架。
5. 指纹 encoder + 迁移 024_audio_fingerprints.sql；水印 MOS Spike 调研文档。
6. 新增 20+ pytest：test_cloud_train、test_marketplace_invite、test_payment_checkout、test_webhook_delivery 等。

三、本周代码与文档产出统计

· 后端新增/修改：约 40+ 文件（domains/、voice_platform/、apps/api/routes/、workers/）
· 前端新增/修改：约 25+ 文件（Studio、Catalog、Produce、Ops 模块）
· 数据库迁移：022~027（marketplace、webhook、waitlist、cloud_gpu_profiles）
· 架构文档：6 篇（云端编排、沙箱联调、自训练指南、水印 Spike、音色馆、E2E 验收）
· 单元测试：新增/补充 20+ 用例，pytest 本地通过""",
    "problems": """一、本周遇到的问题（详细描述）

1. 本机 Windows 难以承载完整 v2Pro 微调
   现象：RTX 5080（16GB）跑 9880 合成仅需 6–8GB VRAM，但 4+4 epoch 微调需 12GB+ 且耗时 30–60 分钟；微调期间 API Worker 与引擎争抢 GPU，平台开发调试被迫中断。
   影响：无法在本机演示「上传→完整微调→合成」一站式闭环，W1 Spike 只能验证零样本。

2. 云端训练链路环节多、失败点分散
   现象：本机转码 → SCP 上传 → 远端 train.sh（切分/ASR/训练）→ SCP 拉回 .ckpt/.pth → import_engine_weights 注册，共 6 个环节；任一环节 SSH 超时（默认 7200s）、远端路径不一致（ENGINE_ROOT vs PLATFORM_ROOT）、FunASR 未安装都会导致 Job failed，且早期日志只有一行 stderr。
   影响：用户在前端只看到「训练失败」，无法自助排查。

3. 合规与主流程的状态同步
   现象：授权书可在 Studio 勾选「已获授权」，但导出时 ComplianceGateway 还需校验 consent 记录是否 approved；前端勾选与后端 DB 状态偶发不同步，导致「能合成但不能导出」的困惑。
   影响：演示时需在 Studio 和 Admin 两处确认授权状态。

4. MVP+1 并行开发导致迁移顺序敏感
   现象：022（marketplace）→ 023（catalog reject）→ 024（fingerprint）→ 025（webhook）→ 026（waitlist）→ 027（cloud_gpu_profiles）迁移有外键依赖；漏跑某条迁移会导致 API 500。
   影响：新机器部署需严格按序执行 migrate，README 需明确说明。

5. 支付宝沙箱与 Webhook 回调无公网域名
   现象：沙箱支付需回调 URL，本机开发环境无固定公网 IP；Webhook 投递目标也需可达地址。
   影响：只能先用 mock provider 跑通 checkout 流程，沙箱联调需 ngrok 或部署到测试服务器。

二、思考过程与解决方法

1. 训练与合成分离部署（针对问题 1）
   思考：平台核心价值在「工作流编排 + 合规门禁」，不应强求本机 GPU 同时承担微调与实时合成。行业惯例也是「云端训练 + 边缘/本机推理」。
   方法：
   · 约定标准路径：「本机平台 + 云端 GPU 微调 + 本机 9880 合成」。
   · 编写《云端 GPU 训练指南》与 train.sh 一键脚本，降低用户租 GPU 门槛。
   · Studio 步骤 ③ 提供三选一：Mock 训练（开发）、快速克隆（zero-shot）、云端完整微调（生产）。
   · 本机 .env 默认 TRAIN_MOCK=true，不抢占 GPU。

2. 云端编排可观测性（针对问题 2）
   思考：长链路 Job 必须分阶段上报进度，否则用户焦虑且无法定位失败环节。
   方法：
   · cloud_train/progress.py 定义 6 阶段：prep → upload → remote_train → download → register → done。
   · StudioJobBanner.vue 轮询 Job progress_pct + message，展示「正在上传 dataset…」等中文提示。
   · POST /cloud-gpu/profile/test 连接自检：SSH 握手 + 远端目录存在性 + Python/CUDA 版本。
   · 支持 CLOUD_TRAIN_LOCAL_DATASET_PREP=true：本机 faster-whisper 切分+ASR 后只上传 segments/，减少远端依赖。
   · train.sh 与 train_from_dataset.sh 分离：前者全量处理，后者仅 spike 训练。

3. 合规单通道与服务端强制（针对问题 3）
   思考：合规不能靠前端按钮「自觉」，必须在服务端 export 路由强制校验；合成与导出策略应分离。
   方法：
   · ComplianceGateway 独立模块，export API 唯一入口。
   · 合成 API 仅做敏感词「记录不阻断」；导出 API 做「命中即拒绝」。
   · 授权书：POST /consents 写 DB → Studio 轮询 consent status → 通过后 unlock 训练按钮。
   · 导出 ZIP 内附 compliance_manifest.json 记录水印参数与校验时间戳。

4. MVP+1 切片交付与迁移规范（针对问题 4）
   思考：市场能力不能一次做完，须与 MVP-0 演示路径解耦，按 Phase 递增合入。
   方法：
   · Phase 1–3（邀请码/Catalog/VoiceGrant）先合入；Phase 4–5（支付/KYC）用 mock provider；Phase 6（Webhook）独立模块。
   · 每条迁移文件头部注释依赖关系；platform_start.ps1 自动跑 migrate。
   · tests/ 每个 Phase 至少 2 个单测，CI 回归防遗漏。

5. 沙箱联调降级策略（针对问题 5）
   思考：无公网域名是开发期常态，不应阻塞 checkout 流程开发与演示。
   方法：
   · payment/providers/mock.py 作为默认 provider，返回假 QR + 自动成功。
   · alipay.py 沙箱实现预留，编写 scripts/smoke_alipay_sandbox_checkout.py 可在有 ngrok 时手动验证。
   · 文档《支付宝沙箱联调（无域名）》记录 ngrok 方案与限制。

三、收获与反思

1. 复杂链路必须「文档 + 脚本 + 测试」三件套：云端训练若只有代码没有 train.sh 和冒烟脚本，只有自己能复现，无法交付。
2. 合规设计要「对用户友好、对监管严格」：合成时不打断创作流，导出时强制门禁，两者策略不同但逻辑自洽。
3. Provider 抽象层让 MVP+1 功能可并行：支付/KYC/Webhook 互不阻塞，mock 即可演示完整 UI 流程。
4. 联调宜早：SSH 凭证、远端目录、.env 变量应在 UI 上线前用 POST /cloud-gpu/profile/test 验证，而非等用户报错。
5. 模块化 IA 降低认知负担：voice/produce/social/ops 四域拆分后，新功能有明确归属，Code Review 更高效。

四、下周计划（W4 收尾）

1. 云端训练一键编排 AutoDL 端到端冒烟：上传 10min 干声 → 远端微调 → 拉回权重 → Studio 试听，记录耗时写入文档。
2. 支付宝沙箱 checkout 全链路联调（ngrok 回调）；音色馆 waitlist 管理员审核流程验收。
3. 整理答辩 PPT（演示路径：Studio→Library→Projects→Catalog→合规导出）与 5 分钟演示录屏。
4. 补齐项目关闭报告、实训个人总结；清理 .env 敏感信息与开发用 Mock 数据。""",
}


def set_cell(table, row: int, col: int, text: str) -> None:
    cell = table.Cell(row, col)
    rng = cell.Range
    rng.Text = text
    if rng.Text.endswith("\r\x07"):
        rng.End = rng.End - 1


def fill_work_log(word) -> None:
    word.Visible = False
    shutil.copy2(WORK_LOG_SRC, WORK_LOG_DST)
    doc = word.Documents.Open(str(WORK_LOG_DST.resolve()))
    t = doc.Tables(1)

    set_cell(t, 1, 2, META["name"])
    set_cell(t, 1, 4, META["student_id"])
    set_cell(t, 1, 6, META["class"])
    set_cell(t, 2, 2, META["project"])
    set_cell(t, 2, 4, META["teacher"])

    for i, (day_label, work, status) in enumerate(WORK_LOG_DAYS, start=4):
        set_cell(t, i, 1, day_label)
        set_cell(t, i, 2, work)
        set_cell(t, i, 3, status)

    doc.Save()
    doc.Close(False)
    print(f"Saved: {WORK_LOG_DST}")


def fill_weekly(word) -> None:
    word.Visible = False
    shutil.copy2(WEEKLY_SRC, WEEKLY_DST)
    doc = word.Documents.Open(str(WEEKLY_DST.resolve()))
    t = doc.Tables(1)

    set_cell(t, 1, 2, META["name"])
    set_cell(t, 1, 4, META["student_id"])
    set_cell(t, 1, 6, META["class"])
    set_cell(t, 2, 2, META["project"])
    set_cell(t, 2, 4, WEEKLY["week"])
    set_cell(t, 3, 2, WEEKLY["practice"])
    set_cell(t, 4, 2, WEEKLY["problems"])

    doc.Save()
    doc.Close(False)
    print(f"Saved: {WEEKLY_DST}")


def main() -> None:
    _run_fill(win32com.client.Dispatch("Word.Application"), fill_work_log)
    _run_fill(win32com.client.Dispatch("Word.Application"), fill_weekly)


def _run_fill(word, fn) -> None:
    word.Visible = False
    try:
        fn(word)
    finally:
        try:
            word.Quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
