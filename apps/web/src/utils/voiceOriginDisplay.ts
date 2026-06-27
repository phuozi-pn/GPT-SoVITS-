export type VoiceOriginKind = "clone" | "train" | "import" | "dev" | "unknown";

export type VoiceOriginMeta = {
  label: string;
  kind: VoiceOriginKind;
  glyph: string;
  hint: string;
  pillClass: string;
  rowClass: string;
  badgeClass: string;
  badgeLabel: string;
};

const IMPORT_MODES = new Set([
  "import",
  "import_upload",
  "import_result_json",
  "import_host_path",
]);

function isImportMode(trainMode?: string | null, imported?: boolean): boolean {
  if (imported) return true;
  if (!trainMode) return false;
  return IMPORT_MODES.has(trainMode) || trainMode.startsWith("import");
}

function trainHint(trainMode?: string | null): string {
  if (trainMode === "cloud") return "完整 GPU 微调 · 专属权重";
  if (trainMode === "engine") return "本地 GPU 微调 · 专属权重";
  return "完整微调 · 专属权重";
}

/** 将 API train_mode 映射为产品向标签与样式 */
export function resolveVoiceOrigin(
  trainMode?: string | null,
  imported?: boolean,
): VoiceOriginMeta {
  if (isImportMode(trainMode, imported)) {
    return {
      label: "导入权重",
      kind: "import",
      glyph: "导",
      hint: "外部引擎权重 · 非平台训练",
      pillClass: "pill--import",
      rowClass: "voice-origin-row--import",
      badgeClass: "voice-origin-badge--import",
      badgeLabel: "导入",
    };
  }
  switch (trainMode) {
    case "quick_clone":
      return {
        label: "快速克隆",
        kind: "clone",
        glyph: "克",
        hint: "参考干声 · Zero-shot · 无专属权重",
        pillClass: "pill--clone",
        rowClass: "voice-origin-row--clone",
        badgeClass: "voice-origin-badge--clone",
        badgeLabel: "快速克隆",
      };
    case "cloud":
      return {
        label: "云端微调",
        kind: "train",
        glyph: "训",
        hint: trainHint(trainMode),
        pillClass: "pill--train",
        rowClass: "voice-origin-row--train",
        badgeClass: "voice-origin-badge--train",
        badgeLabel: "云端微调",
      };
    case "engine":
      return {
        label: "本地微调",
        kind: "train",
        glyph: "训",
        hint: trainHint(trainMode),
        pillClass: "pill--train",
        rowClass: "voice-origin-row--train",
        badgeClass: "voice-origin-badge--train",
        badgeLabel: "本地微调",
      };
    case "mock":
      return {
        label: "占位",
        kind: "dev",
        glyph: "测",
        hint: "开发占位 · 非真实音色",
        pillClass: "pill--warn",
        rowClass: "voice-origin-row--dev",
        badgeClass: "voice-origin-badge--dev",
        badgeLabel: "占位",
      };
    case "unknown":
    case undefined:
    case null:
    case "":
      return {
        label: "微调训练",
        kind: "unknown",
        glyph: "训",
        hint: trainHint(trainMode),
        pillClass: "pill--train",
        rowClass: "voice-origin-row--train",
        badgeClass: "voice-origin-badge--train",
        badgeLabel: "微调",
      };
    default:
      return {
        label: "微调训练",
        kind: "train",
        glyph: "训",
        hint: trainHint(trainMode),
        pillClass: "pill--train",
        rowClass: "voice-origin-row--train",
        badgeClass: "voice-origin-badge--train",
        badgeLabel: "微调",
      };
  }
}

export function voiceOriginLabel(trainMode?: string | null, imported?: boolean): string {
  return resolveVoiceOrigin(trainMode, imported).label;
}

export function versionDefaultDisplayName(v: {
  version: number;
  label?: string | null;
  train_mode?: string | null;
  imported?: boolean;
}): string {
  const custom = v.label?.trim();
  if (custom) return custom;
  return `${voiceOriginLabel(v.train_mode, v.imported)} v${v.version}`;
}

export function voicePickerBadge(v: {
  granted?: boolean;
  train_mode?: string | null;
  imported?: boolean;
}): string | undefined {
  if (v.granted) return "已购授权";
  return resolveVoiceOrigin(v.train_mode, v.imported).badgeLabel;
}

export function voicePickerOriginKind(
  trainMode?: string | null,
  imported?: boolean,
): VoiceOriginKind {
  return resolveVoiceOrigin(trainMode, imported).kind;
}
