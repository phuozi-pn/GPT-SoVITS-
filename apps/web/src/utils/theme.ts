export type ThemeMode = "dark" | "light" | "warm" | "custom";

export interface ThemeState {
  mode: ThemeMode;
  customBg: string;
}

export const THEME_STORAGE_KEY = "phonia-theme";
export const DEFAULT_CUSTOM_BG = "#FAFAF8";

export const THEME_PRESETS: { id: ThemeMode; label: string }[] = [
  { id: "dark", label: "深色" },
  { id: "light", label: "浅色" },
  { id: "warm", label: "暖白" },
  { id: "custom", label: "自定义" },
];

/** 由 JS 写入、离开自定义主题时需清理的变量 */
export const CUSTOM_THEME_VAR_KEYS = [
  "--user-bg-primary",
  "--bg-primary",
  "--bg-secondary",
  "--bg-tertiary",
  "--bg-surface",
  "--bg-surface-raised",
  "--bg-surface-glass",
  "--bg-surface-muted",
  "--color-ink",
  "--color-ink-muted",
  "--color-ink-faint",
  "--color-pine-ink",
  "--color-brushed",
  "--color-brushed-dark",
  "--color-xuan",
  "--color-xuan-light",
  "--color-xuan-warm",
  "--color-paper",
  "--color-paper-dark",
  "--color-surface",
  "--color-surface-raised",
  "--border-glow",
  "--border-subtle",
  "--border-strong",
  "--color-line",
  "--color-line-strong",
  "--surface-line",
  "--surface-muted",
  "--shadow-soft",
  "--shadow-card",
] as const;

function hexToRgb(hex: string): [number, number, number] | null {
  const normalized = hex.trim().replace(/^#/, "");
  if (!/^[0-9a-f]{3}$|^[0-9a-f]{6}$/i.test(normalized)) return null;
  const full =
    normalized.length === 3
      ? normalized
          .split("")
          .map((c) => c + c)
          .join("")
      : normalized;
  return [
    parseInt(full.slice(0, 2), 16),
    parseInt(full.slice(2, 4), 16),
    parseInt(full.slice(4, 6), 16),
  ];
}

function clampByte(value: number): number {
  return Math.max(0, Math.min(255, Math.round(value)));
}

function rgbToHex(r: number, g: number, b: number): string {
  return `#${[r, g, b].map((c) => clampByte(c).toString(16).padStart(2, "0")).join("")}`;
}

function mixHex(a: string, b: string, weightA: number): string {
  const rgbA = hexToRgb(a);
  const rgbB = hexToRgb(b);
  if (!rgbA || !rgbB) return a;
  const w = Math.max(0, Math.min(1, weightA));
  return rgbToHex(
    rgbA[0] * w + rgbB[0] * (1 - w),
    rgbA[1] * w + rgbB[1] * (1 - w),
    rgbA[2] * w + rgbB[2] * (1 - w),
  );
}

/** 相对亮度 0–1 */
export function relativeLuminance(hex: string): number {
  const rgb = hexToRgb(hex);
  if (!rgb) return 1;
  const [r, g, b] = rgb.map((c) => {
    const v = c / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrastRatio(fg: string, bg: string): number {
  const l1 = relativeLuminance(fg);
  const l2 = relativeLuminance(bg);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

function adjustForContrast(fg: string, bg: string, target = 4.5): string {
  const toward = relativeLuminance(bg) > 0.45 ? "#000000" : "#FFFFFF";
  let current = fg;
  for (let i = 0; i < 28; i += 1) {
    if (contrastRatio(current, bg) >= target) return current;
    current = mixHex(current, toward, 0.14);
  }
  return toward;
}

function rgbAlpha(hex: string, alpha: number): string {
  const rgb = hexToRgb(hex);
  if (!rgb) return `rgb(0 0 0 / ${alpha})`;
  return `rgb(${rgb[0]} ${rgb[1]} ${rgb[2]} / ${alpha})`;
}

export function isLightBackground(hex: string): boolean {
  return relativeLuminance(hex) > 0.45;
}

export function buildCustomThemeVars(bg: string): Record<string, string> {
  const safeBg = hexToRgb(bg) ? bg : DEFAULT_CUSTOM_BG;
  const lightBg = isLightBackground(safeBg);
  const inkBase = lightBg ? "#1C1B19" : "#F5F3EF";
  const ink = adjustForContrast(inkBase, safeBg, 7);
  const inkMuted = adjustForContrast(mixHex(ink, safeBg, 0.42), safeBg, 4.6);
  const inkFaint = adjustForContrast(mixHex(ink, safeBg, 0.62), safeBg, 3.4);

  const secondary = mixHex(safeBg, lightBg ? "#141312" : "#000000", lightBg ? 0.9 : 0.86);
  const tertiary = mixHex(safeBg, "#FFFFFF", lightBg ? 0.84 : 0.8);
  const surface = mixHex(safeBg, "#FFFFFF", lightBg ? 0.78 : 0.74);
  const surfaceRaised = mixHex(surface, "#FFFFFF", 0.55);
  const surfaceMuted = mixHex(safeBg, lightBg ? "#E8E6E1" : "#000000", lightBg ? 0.9 : 0.88);

  const borderInk = lightBg ? "#141312" : "#FFFFFF";

  return {
    "--user-bg-primary": safeBg,
    "--bg-primary": safeBg,
    "--bg-secondary": secondary,
    "--bg-tertiary": tertiary,
    "--bg-surface": surface,
    "--bg-surface-raised": surfaceRaised,
    "--bg-surface-glass": rgbAlpha(surface, 0.94),
    "--bg-surface-muted": rgbAlpha(surfaceMuted, 0.96),
    "--color-ink": ink,
    "--color-ink-muted": inkMuted,
    "--color-ink-faint": inkFaint,
    "--color-pine-ink": rgbAlpha(ink, 0.9),
    "--color-brushed": mixHex(surface, borderInk, lightBg ? 0.12 : 0.18),
    "--color-brushed-dark": inkMuted,
    "--color-xuan": safeBg,
    "--color-xuan-light": surface,
    "--color-xuan-warm": secondary,
    "--color-paper": safeBg,
    "--color-paper-dark": secondary,
    "--color-surface": surface,
    "--color-surface-raised": surfaceRaised,
    "--border-glow": rgbAlpha(borderInk, lightBg ? 0.12 : 0.14),
    "--border-subtle": rgbAlpha(borderInk, lightBg ? 0.08 : 0.1),
    "--border-strong": rgbAlpha(borderInk, lightBg ? 0.16 : 0.18),
    "--color-line": rgbAlpha(borderInk, lightBg ? 0.1 : 0.12),
    "--color-line-strong": rgbAlpha(borderInk, lightBg ? 0.16 : 0.18),
    "--surface-line": rgbAlpha(borderInk, lightBg ? 0.1 : 0.12),
    "--surface-muted": rgbAlpha(surfaceMuted, 0.96),
    "--shadow-soft": lightBg
      ? "0 1px 2px rgb(0 0 0 / 0.06), 0 8px 24px rgb(0 0 0 / 0.08)"
      : "0 1px 2px rgb(0 0 0 / 0.25), 0 8px 32px rgb(0 0 0 / 0.4)",
    "--shadow-card": lightBg
      ? "0 1px 3px rgb(0 0 0 / 0.06), 0 4px 12px rgb(0 0 0 / 0.05)"
      : "0 1px 3px rgb(0 0 0 / 0.25), 0 4px 16px rgb(0 0 0 / 0.2)",
  };
}

export function loadThemeState(): ThemeState {
  if (typeof localStorage === "undefined") {
    return { mode: "dark", customBg: DEFAULT_CUSTOM_BG };
  }
  try {
    const raw = localStorage.getItem(THEME_STORAGE_KEY);
    if (!raw) return { mode: "dark", customBg: DEFAULT_CUSTOM_BG };
    const parsed = JSON.parse(raw) as Partial<ThemeState>;
    const mode = parsed.mode;
    if (mode !== "dark" && mode !== "light" && mode !== "warm" && mode !== "custom") {
      return { mode: "dark", customBg: DEFAULT_CUSTOM_BG };
    }
    return {
      mode,
      customBg: typeof parsed.customBg === "string" ? parsed.customBg : DEFAULT_CUSTOM_BG,
    };
  } catch {
    return { mode: "dark", customBg: DEFAULT_CUSTOM_BG };
  }
}

export function saveThemeState(state: ThemeState): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(THEME_STORAGE_KEY, JSON.stringify(state));
}

function clearCustomThemeVars(html: HTMLElement): void {
  for (const key of CUSTOM_THEME_VAR_KEYS) {
    html.style.removeProperty(key);
  }
}

export function applyThemeState(state: ThemeState): void {
  if (typeof document === "undefined") return;
  const html = document.documentElement;
  html.setAttribute("data-theme", state.mode);
  clearCustomThemeVars(html);

  if (state.mode === "custom") {
    const vars = buildCustomThemeVars(state.customBg);
    const tone = isLightBackground(vars["--bg-primary"] ?? state.customBg) ? "light" : "dark";
    html.setAttribute("data-bg-tone", tone);
    html.style.colorScheme = tone;
    for (const [key, value] of Object.entries(vars)) {
      html.style.setProperty(key, value);
    }
    return;
  }

  html.removeAttribute("data-bg-tone");
  html.style.colorScheme = state.mode === "dark" ? "dark" : "light";
}
