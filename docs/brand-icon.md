# Phonia 品牌图标 · 螺旋钻纹

> 设计定稿日期：2026-06-18
> 方向：钻石极简 · 旋转感 · 声波扩散

---

## 概念

**钻石即声源，旋转的波纹即声音本身。**

- 中心钻石旋转 12° — 晶体振动的瞬间
- 两道金色螺旋线从中心向外扩散 — 声波传播、旋转、共振
- 金色渐变（#f0d080 → #c4923a）— 温暖、精密、高端

## 使用位置

| 场景 | 文件 | 尺寸 | 容器样式 |
|------|------|------|---------|
| 启动序章 (Splash) | `apps/web/src/modules/public/views/SplashView.vue` | 80×80px | 半透明浮现，动画入场 |
| 公开导航栏 (PublicLayout) | `apps/web/src/layouts/PublicLayout.vue` | 18×18px | 32px 白色方块底，朱砂边框 |
| 工作台侧栏 (AppLayout) | `apps/web/src/components/AppLayout.vue` | 22×22px | 40px 金色渐变底方块 |

## SVG 原始设计

### 大图标 (Splash, 80×80)

```svg
<svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M40 30c0-6 4-10 10-8s10 8 6 14-12 8-16 2-2-12 6-14 14 0 14 8"
    stroke="rgb(200 160 100 / 0.15)" stroke-width="0.6" fill="none"/>
  <path d="M40 28c0-5 3-8 8-6s8 6 4 11-10 6-13 1-1-10 5-11 11 0 11 6"
    stroke="rgb(200 160 100 / 0.3)" stroke-width="0.8" fill="none"/>
  <path d="M40 22L52 40L40 58L28 40Z"
    fill="url(#diamond-f)" stroke="url(#diamond-s)" stroke-width="1.2"
    transform="rotate(12, 40, 40)"/>
  <path d="M40 22L40 58"
    stroke="rgb(255 255 255 / 0.07)" stroke-width="0.5"
    transform="rotate(12, 40, 40)"/>
  <defs>
    <linearGradient id="diamond-f" x1="28" y1="40" x2="52" y2="40">
      <stop stop-color="#e8c870"/><stop offset="1" stop-color="#c4923a"/>
    </linearGradient>
    <linearGradient id="diamond-s" x1="28" y1="40" x2="52" y2="40">
      <stop stop-color="#f0d080"/><stop offset="1" stop-color="#b08020"/>
    </linearGradient>
  </defs>
</svg>
```

### 小图标 (导航栏, 32×32)

```svg
<svg viewBox="0 0 32 32" fill="none">
  <path d="M16 12c0-2 1.5-3.5 4-3s4 3 2.5 5.5-5 3-6.5 1-1-5 2.5-5.5 5.5 0 5.5 3"
    stroke="rgb(196 146 58 / 0.3)" stroke-width="0.6" fill="none"/>
  <path d="M16 9L20 16L16 23L12 16Z"
    fill="#c4923a" stroke="#b08020" stroke-width="0.5"
    transform="rotate(12, 16, 16)"/>
</svg>
```

### 侧栏图标 (工作台, 40×40)

```svg
<svg viewBox="0 0 40 40" fill="none">
  <path d="M20 15c0-2.5 2-4.5 5-3.5s5 4 3 7-6 4-8 1-1-6 3-7 7 0 7 4"
    stroke="rgb(255 255 255 / 0.15)" stroke-width="0.7" fill="none"/>
  <path d="M20 11L26 20L20 29L14 20Z"
    fill="url(#diamond-f)" stroke="rgb(255 255 255 / 0.5)" stroke-width="1"
    transform="rotate(12, 20, 20)"/>
  <defs>
    <linearGradient id="diamond-f" x1="14" y1="20" x2="26" y2="20">
      <stop stop-color="#f0d080"/><stop offset="1" stop-color="#c4923a"/>
    </linearGradient>
  </defs>
</svg>
```

## 设计决策记录

- **方向选择**：从 8 个方向 → 钻石极简 → 6 个旋转变体 → **螺旋钻纹**
- **替代原因**：原 φ 符号偏学术/数学感，螺旋钻纹更直观表达"声源 + 旋转扩散"的品牌意象
- **颜色**：沿用项目金色系（#c4923a 为主），与朱砂红、宣纸白构成完整品牌色板
