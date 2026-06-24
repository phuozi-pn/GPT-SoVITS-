/** Studio 右侧日志：短 ID、中文状态、Worker 错误摘要 */

const STATUS_ZH: Record<string, string> = {
  queued: "排队中",
  running: "进行中",
  succeeded: "完成",
  failed: "失败",
  approved: "已通过",
};

const TRAIN_PHASE_ZH: Record<string, string> = {
  starting: "准备训练",
  upload_done: "数据已上传远端",
  preprocess_running: "预处理中",
  preprocess_done: "预处理完成",
  gpt_running: "GPT 微调中",
  gpt_done: "GPT 完成",
  sovits_running: "SoVITS 微调中",
  sovits_done: "SoVITS 完成",
  done: "远端训练结束",
  // legacy
  preprocess: "预处理中",
  gpt_train: "GPT 微调中",
  sovits_train: "SoVITS 微调中",
};

export function formatDurationSec(sec: number): string {
  if (sec < 60) return `${Math.round(sec)}s`;
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return s > 0 ? `${m}m${s}s` : `${m}m`;
}

/** Human-friendly duration for Studio UI (中文) */
export function formatAssetDurationZh(sec: number): string {
  if (sec < 60) return `${Math.round(sec)} 秒`;
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return s > 0 ? `${m} 分 ${s} 秒` : `${m} 分钟`;
}

export function shortId(id: string): string {
  const s = id.trim();
  return s.length > 8 ? s.slice(0, 8) : s;
}

export function jobStatusZh(status: string): string {
  return STATUS_ZH[status] ?? status;
}

export function trainPhaseLabel(phase: string, fallback?: string): string {
  return TRAIN_PHASE_ZH[phase] ?? fallback ?? phase;
}

/** 从 Worker / SSH 长错误里提取一行可读摘要 */
export function sanitizeWorkerError(raw: string | null | undefined): string {
  if (!raw?.trim()) return "未知错误";

  let s = raw.trim().replace(/^SSH failed \(\d+\):\s*/i, "");

  const patterns = [
    /\[spike_train\]\s*ERROR:\s*(.+?)(?:\n|Traceback|$)/i,
    /(?:NameError|RuntimeError|CloudTrainError):\s*(.+)/,
    /远端训练失败[^:]*:\s*(.+)/,
  ];
  for (const re of patterns) {
    const m = re.exec(s);
    if (m?.[1]?.trim()) return _clip(m[1].trim());
  }

  const line = s
    .split("\n")
    .map((l) => l.trim())
    .find((l) => l && !l.startsWith("Traceback") && !l.startsWith("File ")) ?? s;

  return _clip(line.replace(/\s+/g, " "));
}

function _clip(text: string, max = 160): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}
