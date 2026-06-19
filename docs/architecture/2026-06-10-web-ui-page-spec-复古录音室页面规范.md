# Web 前端 · 复古录音室页面规范

版本：v1.0 · 2026-06-10  
适用范围：`apps/web`（Vue 3 + Tailwind v4）

## 1. 设计基调

温暖、精密、带物理仪器触感——VU 表、磁带卷盘、调音台旋钮，避免黑底霓虹与玻璃拟态。

## 2. 设计 Token

| Token | 值 | 用途 |
|-------|-----|------|
| `--paper` | `#F2EBE1` | 主背景（叠加 3–5% 噪点） |
| `--ink` | `#2A2520` | 主文字 |
| `--vu-amber` | `#E8A050` | 强调 / 已播放波形 |
| `--peak-red` | `#C75D4D` | 录制键 / 过载 |
| `--brushed` | `#B8B2A8` | 面板边框 / 分割线 |

字体：标题 **Fraunces** · 正文 **Inter** · 读数 **IBM Plex Mono**（12px 大写 + 0.05em 字间距）

间距：8px 网格 · 圆角：按钮/输入 `4px` · 模块 `8px`

## 3. 页面地图

| 路由 | 布局 | 核心组件 |
|------|------|----------|
| `/library` | 三栏制作台 | `MakeWorkspace` · `ScriptEditor` · `VoicePicker` · `VoiceParamsPanel` |
| `/studio` | 步骤条 + 主区/侧栏 | `StepTabs` · `RackPanel`（①–③）· `MakeWorkspace`（④ studio）· 日志侧栏 |
| `/catalog` | 机架区块 + 精选网格 + 侧栏制作台 | `RackPanel` · `TapePlayer` · `MakeWorkspace`（studio） |
| `/projects` | 三步机架面板 | `RackPanel` — 项目 / 角色 / CSV |
| `/login` | 分栏 | `RackPanel` · `VUMeter` 装饰 |

### 3.1 展示站（访客壳 `ShowcaseLayout`）

| 路由 | 核心组件 / 样式 |
|------|-----------------|
| `/` | `ShowcaseHomeView` · `showcase-hero` · `page-metrics` |
| `/browse` | `PublicCatalogView` · `ShowcasePageHead` · `showcase-voice-tile` |
| `/updates` | `PublicDiscoverView` · `feed-card--stream` |
| `/verify/:id` | `VerifyView` · `showcase-verify__card` |
| `/creator/:id`（访客） | `CreatorView` 展示模板 · `creator-profile-hero--showcase` |

样式拆分：`styles/tokens.css` · `styles/showcase.css` · `styles/tailwind.css`

指标统一用 `.page-metrics`（行内 **数字**），禁止页面顶部 `stat-chip` 墙。

## 4. 核心可视化（禁止通用竖条波形）

- **VU 表**：`VUMeter.vue` — spring 指针，-20~+3 dB，超 0 dB 变红
- **示波器**：`OscilloscopeDisplay` / `TapePlayer` — **真实音频**峰值 + 播放时 Analyser 时域
- **进度**：`TapeReel` — 播放匀速转，暂停 0.6s 惯性减速
- **参数**：`DialKnob` — 语速 / 温度 / 音调

## 5. 制作台信息架构（对标讯飞智作）

```
┌─────────────────────────────────────────────────────────────┐
│ 工具栏：模式 · 清空 · 停顿 · 示例台词                        │
├──────────────────┬──────────────┬───────────────────────────┤
│ 台本编辑区        │ 主播选择      │ 调音台（旋钮+VU+返听）     │
│ 单人/多主播       │ 搜索+标签     │ 全局语速/温度              │
│ 局部变速/变调     │ 圆形头像卡片  │ 示波器真实波形             │
├──────────────────┴──────────────┴───────────────────────────┤
│ 底栏：合规勾选 + 「开始生成语音」录制键                        │
└─────────────────────────────────────────────────────────────┘
```

## 6. 文案规范

- 按钮：说明操作结果（「开始生成语音」而非「提交」）
- 空状态：引导式（「还没有录音——点击下方按钮开始」）
- 错误：说明原因 + 如何解决（见 `utils/apiErrors.ts`）

## 7. API 字段对照（前后端）

| 前端 | 后端 `SynthesisRequest` | 说明 |
|------|-------------------------|------|
| `voice_version_id` | `voice_version_id` | 单段合成 |
| `speed_factor` | `speed_factor` | 0.5–2.0 |
| `temperature` | `temperature` | 0.1–2.0 |
| `segments[].pitch_factor` | `segments[].pitch_factor` | worker 后处理变调 |
| `ai_disclosure_ack` | `ai_disclosure_ack` | 未勾选 → 403 |

构建 payload：`types/script.ts` → `buildSynthesisPayload()`

## 8. 组件目录

```
apps/web/src/components/
├── make/          # 制作台（Library 主流程）
├── studio/        # VU / 示波器 / 磁带 / 旋钮 / 机架面板
└── *.vue          # 布局与共享
```

## 9. 本地开发

```powershell
.\scripts\platform_start.ps1
.\scripts\web_dev.ps1
# http://127.0.0.1:5173/library
```

验收清单见 [2026-06-10-web-frontend-验收清单.md](./2026-06-10-web-frontend-验收清单.md)
