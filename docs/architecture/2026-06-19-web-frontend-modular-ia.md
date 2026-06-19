# Web 前端模块化信息架构（重构）

版本：v1.0 · 2026-06-19

## 背景

此前「三卷画卷」视觉方案导致页面层级重叠、导航上下文重复。本次重构**以功能逻辑清晰为首要目标**，按「模块化分析 → 壳层与路由 → 页面骨架 → 轻量样式」推进，摒弃画卷式装饰与绝对定位叠压。

## 三层壳（App Shell）

| 壳 | `meta.shell` | 布局 | 典型路由 |
|----|--------------|------|----------|
| 访客站 | `public` | `PublicLayout` | `/` `/browse` `/updates` `/creator/:id` |
| 工作台 | `workbench` | `AppLayout` | `/library` `/studio` `/discover/*` … |
| 无壳 | `bare` | 无 | `/login` `/verify/:id` |

判定：`useAppShell()` 读取路由 `meta.shell`；兼容旧逻辑 `meta.public && !session` → `public`。

入口：`App.vue` 三分支渲染，不再使用 `ShowcaseLayout`。

## 五大业务模块

单一数据源：`apps/web/src/architecture/modules.ts`

| 模块 id | 侧栏分组 | 核心路由 |
|---------|----------|----------|
| `produce` | 制作 | `/library` `/projects` |
| `voice` | 音色 | `/studio` `/voices` `/catalog`；公开镜像 `/browse` |
| `social` | 社区 | `/discover/*` `/community`；公开镜像 `/updates` |
| `ops` | 运营 | `/admin`（admin + labs） |
| `public` | 访客顶栏 | `/` `/browse` `/updates` |

默认工作台落地：`DEFAULT_WORKBENCH_ROUTE = /library`

## 路由拆分

```
apps/web/src/router/
├── index.ts              # 合并 + 注册守卫
├── guards.ts             # 鉴权 / admin / labs
└── modules/
    ├── public.routes.ts
    ├── produce.routes.ts
    ├── voice.routes.ts
    ├── social.routes.ts
    └── ops.routes.ts
```

每条路由显式标注 `meta.shell`、`requiresAuth`、`adminOnly`、`labs`。

## 导航与页面元数据

| 文件 | 职责 |
|------|------|
| `architecture/modules.ts` | 模块注册表、访客顶栏 `PUBLIC_NAV`、默认路由常量 |
| `config/navigation.ts` | 侧栏 `NAV_GROUPS`、`PAGE_META`、`getPageMeta()`、`SOCIAL_TABS` |

`DEFAULT_ROUTE` / `PUBLIC_SITE_ROUTE` 从 `architecture/modules` 再导出，避免双份常量。

## 页面布局约定

1. **访客首页**：`modules/public/views/HomeView.vue` — 工作流三步 + 模块入口卡片（功能说明型，非画卷）。
2. **工作台页**：侧栏分组 + `AppTopBar`（分组名 / 页名 / workflow 一句）；页面内用 `PageHero` 或业务组件自带标题，**禁止**重复三层说明。
3. **社区动态**：`DiscoverFeedView` / `PublicDiscoverView` — 标题 + 筛选侧栏 + 列表，无 `PageSection` / 画卷动效。
4. **合成工作台**：`MakeWorkspace` 保留 `FlowPipeline` 四步（选音色 → 文稿 → 参数 → 合成），左栏音色、右栏文稿、底栏操作。

## 样式策略

- `tokens.css`：设计变量
- `shell.css`：壳层通用组件（按钮、社区布局、流程条、分区面板）
- `showcase.css`：公开音色馆等展示页
- **已停用 import**：`scroll.css` `layout.css` `workshop.css` `gallery.css`（文件可保留作参考，不再全局加载）

原则：栅格与边框分区，无错位叠压、无视差装饰。

## 与旧文档关系

- [展示站与工作台 IA](./2026-06-19-展示站与工作台IA.md) 中的 `ShowcaseLayout` / `meta.layout=showcase` 已由本文 **`public` 壳 + `PublicLayout`** 替代。
- [工作流与页面地图](./2026-06-16-web-frontend-工作流与页面地图.md) 中的业务流仍有效，壳层与路由以本文为准。

## 后续（美化阶段）

架构稳定后再做：统一 `PageFrame` 包装器、收敛 `MakeWorkspace` 工作室视觉、清理未接线旧组件（画卷 `scroll/`、`workshop/` 装饰组件可逐步移除）。

## 目录结构（2026-06-19 更新）

```
apps/web/src/
├── architecture/          # modules.ts · registry.ts（注册表）
├── modules/
│   ├── public/views/      # 首页、登录、验真
│   ├── produce/           # views · components · types/script · utils
│   ├── voice/             # views · components/catalog · composables
│   ├── social/            # views · components/community · composables
│   └── ops/views/         # 运营台
├── router/modules/        # 路由按模块拆分
├── api/modules/           # API 客户端按模块 barrel
└── components/            # 跨模块共享：AppLayout、Page*、studio/
```
