# Web 前端验收清单

版本：v1.0 · 2026-06-10  
对应页面规范：[复古录音室页面规范](./2026-06-10-web-ui-page-spec-复古录音室页面规范.md)

## 任务 6 · 短剧批量工作流（W2/W3）

- [x] `/projects` 三步机架：项目 → 角色绑定 → CSV 上传
- [x] 批量进度轮询 + 成功/失败行数展示
- [x] 合规 ZIP 导出（`GET /api/v1/exports/{job_id}/download`）
- [x] CSV 模板 `public/samples/batch_template.csv`
- [x] 本地端到端：`python scripts/smoke_e2e_guzhenren.py`（2026-06-10 实测 20/20 通过，见 [MVP-0 E2E 验收记录](./2026-06-10-mvp0-e2e-验收记录.md)）
- [x] 行级失败隔离：`python scripts/smoke_e2e_batch_mixed.py`（1 行敏感词 + 其余成功）

手动冒烟（批量）：

1. `/library` 导入音色权重
2. `/projects` 创建项目 → 绑定角色「龙宫」→ 上传 `scripts/fixtures/guzhenren_batch_20.csv`
3. 等待 batch worker 完成 → 下载合规 ZIP → 解压核对 manifest 与 wav 前缀标识

## 任务 1 · UI 与页面规范

- [x] 复古 token 落盘（`tailwind.css` `@theme`）
- [x] 制作台三栏布局 `/library`
- [x] 机架侧栏导航 `AppLayout`
- [x] 页面规范文档（本文档体系）

## 任务 2 · 核心功能

- [x] 单段合成 + 语速/温度透传 API
- [x] 多主播 `segments[]` 分段合成拼接
- [x] 局部变速/变调（选区拆分 + `pitch_factor`）
- [x] 示波器真实音频（解码峰值 + 播放 Analyser）
- [x] 训练闭环 `/studio`（步骤 1–4）
- [x] 音色馆试听 `/catalog`

## 任务 3 · 测试用例

| 范围 | 文件 | 命令 |
|------|------|------|
| 台本 payload | `apps/web/src/types/script.test.ts` | `cd apps/web && npm test` |
| 合规多段 | `tests/test_compliance_gateway.py` | `pytest tests/test_compliance_gateway.py` |
| 合成 API | `tests/test_synthesis_api.py` | `pytest tests/test_synthesis_api.py` |
| 多段 worker | `tests/test_infer_multi_segment.py` | `pytest tests/test_infer_multi_segment.py` |
| 音频工具 | `tests/test_audio_util.py` | `pytest tests/test_audio_util.py` |

## 任务 4 · 联调与鉴权

- [x] `SynthesisBody` 与后端 `SynthesisRequest` 字段对齐
- [x] `resolveMediaUrl()` 开发环境 `/files` 代理，避免 CORS 解码失败
- [x] `formatApiError()` 映射 `VOICE_NOT_GRANTED` / `AI_DISCLOSURE_REQUIRED` 等
- [x] 开发模式 `X-User-Id` 与 `dev_user_id` localStorage

常见问题：

| 现象 | 处理 |
|------|------|
| 示波器平线 | 确认 `/files/...` 200；刷新后重新合成 |
| 403 音色无权 | 音色库导入权重或切换调试用户 |
| 合成超时 | 启动引擎 `.\scripts\engine_api_v2.ps1 -Action start` |

## 任务 5 · 交互与空状态

| 页面 | 空状态文案 |
|------|------------|
| `/library` 音色 | 「还没有音色——请先在下方导入引擎权重」 |
| `/library` 历史 | 「还没有录音——输入台词并按下开始生成语音」 |
| `/catalog` 列表 | 「还没有公开音色——在上方发布你的版本」 |
| `/projects` 项目 | 「还没有项目——输入名称后点创建项目」 |
| `/projects` 音色 | 「还没有音色版本——请先到音色库导入权重」 |
| 多主播 | 工具栏切换「多主播」→「+ 添加主播段落」 |

手动冒烟：

1. `/library` 输入台词 → 调旋钮 → 生成 → 返听示波器有波形
2. 选中文字 → 局部调节 → 应用到选区 → 多段生成
3. 工具栏「多主播」→ 两段不同主播 → 生成一条拼接音频
4. `/login` 开发模式进入 → 右上角切换用户 A/B
