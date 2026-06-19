export type ScriptSegment = {
  id: string;
  voiceVersionId: string;
  text: string;
  /** 情景配音：角色名（如 方源、旁白） */
  characterName?: string;
  /** Per-segment override; null = use global */
  speed: number | null;
  temperature: number | null;
  pitch: number;
  /** 情感标签：neutral / happy / angry / sad / fearful / calm */
  emotion: string | null;
  emotionStrength: number;
  /** Inter-segment pause in seconds (0-5) */
  pauseDuration: number;
};

export type ScreenplayLine = {
  character: string;
  text: string;
};

export type CharacterCast = Record<string, string>;

export type AutoSegmentMode = "screenplay" | "paragraph" | "single" | "lyrics";

export type ProduceWorkMode = "single" | "dialogue" | "vocal";

export type AutoSegmentResult = {
  segments: ScriptSegment[];
  mode: AutoSegmentMode;
  characterCount: number;
  lineCount: number;
};

export type SynthesisSegmentInput = {
  voice_version_id: string;
  text: string;
  speed_factor?: number;
  temperature?: number;
  pitch_factor?: number;
  emotion?: string | null;
  emotion_strength?: number;
  pause_duration?: number;
};

export type SynthesisOptions = {
  voice_version_id?: string;
  text?: string;
  temperature?: number;
  speed_factor?: number;
  top_p?: number;
  emotion?: string | null;
  emotion_strength?: number;
  segments?: SynthesisSegmentInput[];
};

export function newSegment(voiceVersionId: string, text = "", characterName?: string): ScriptSegment {
  return {
    id: crypto.randomUUID(),
    voiceVersionId,
    text,
    characterName,
    speed: null,
    temperature: null,
    pitch: 1,
    emotion: null,
    emotionStrength: 0.5,
    pauseDuration: 0,
  };
}

export function segmentCharCount(segments: ScriptSegment[]): number {
  return segments.reduce((n, s) => n + s.text.length, 0);
}

export function buildSynthesisPayload(
  segments: ScriptSegment[],
  global: { speed: number; temperature: number; topP?: number; emotion?: string | null; emotionStrength?: number },
): SynthesisOptions {
  const nonEmpty = segments.filter((s) => s.text.trim());
  if (!nonEmpty.length) {
    throw new Error("台本为空");
  }

  const globalEmotion = global.emotion ?? null;
  const globalEmotionStrength = global.emotionStrength ?? 0.5;

  const hasMultiVoice = new Set(nonEmpty.map((s) => s.voiceVersionId)).size > 1;
  const hasLocalTune = nonEmpty.some(
    (s) =>
      s.pitch !== 1 ||
      (s.emotion != null && s.emotion !== globalEmotion) ||
      s.emotionStrength !== globalEmotionStrength ||
      s.pauseDuration > 0 ||
      (s.speed != null && Math.abs(s.speed - global.speed) > 0.001) ||
      (s.temperature != null && Math.abs(s.temperature - global.temperature) > 0.001),
  );

  if (nonEmpty.length === 1 && !hasMultiVoice && !hasLocalTune) {
    const only = nonEmpty[0];
    return {
      voice_version_id: only.voiceVersionId,
      text: only.text.trim(),
      speed_factor: global.speed,
      temperature: global.temperature,
      top_p: global.topP ?? 1,
      emotion: globalEmotion,
      emotion_strength: globalEmotionStrength,
    };
  }

  return {
    temperature: global.temperature,
    speed_factor: global.speed,
    top_p: global.topP ?? 1,
    emotion: globalEmotion,
    emotion_strength: globalEmotionStrength,
    segments: nonEmpty.map((s) => ({
      voice_version_id: s.voiceVersionId,
      text: s.text.trim(),
      speed_factor: s.speed ?? global.speed,
      temperature: s.temperature ?? global.temperature,
      pitch_factor: s.pitch,
      emotion: s.emotion ?? globalEmotion,
      emotion_strength: s.emotionStrength,
      pause_duration: s.pauseDuration,
    })),
  };
}

const SCREENPLAY_LINE_PATTERNS: RegExp[] = [
  /^【([^】]{1,20})】\s*(.+)$/,
  /^[\(（]([^)）]{1,20})[\)）]\s*(.+)$/,
  /^([^：:|\s]{1,20})[：:]\s*(.+)$/,
  /^([^|]{1,20})\|(.+)$/,
];

/** 解析「角色：台词」格式剧本为分段列表 */
export function parseScreenplayScript(raw: string): ScreenplayLine[] {
  const lines = raw
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);

  const out: ScreenplayLine[] = [];

  for (const line of lines) {
    let matched = false;
    for (const re of SCREENPLAY_LINE_PATTERNS) {
      const m = line.match(re);
      if (!m) continue;
      out.push({ character: m[1].trim(), text: m[2].trim() });
      matched = true;
      break;
    }
    if (matched) continue;

    if (out.length && !/[：:]|^【/.test(line)) {
      out[out.length - 1].text += `\n${line}`;
      continue;
    }

    const narration = line.match(/^旁白[：:]\s*(.+)$/);
    if (narration) {
      out.push({ character: "旁白", text: narration[1].trim() });
      continue;
    }

    out.push({ character: "旁白", text: line });
  }

  return out;
}

export function uniqueCharacters(lines: ScreenplayLine[]): string[] {
  const seen = new Set<string>();
  const order: string[] = [];
  for (const line of lines) {
    if (seen.has(line.character)) continue;
    seen.add(line.character);
    order.push(line.character);
  }
  return order;
}

/** 为角色自动分配音色（保留已有映射，新角色优先用未占用音色） */
export function autoAssignCast(
  characters: string[],
  voiceIds: string[],
  existing: CharacterCast = {},
): CharacterCast {
  const cast: CharacterCast = { ...existing };
  if (!voiceIds.length) return cast;

  const used = new Set(Object.values(cast));
  let poolIdx = 0;

  for (const name of characters) {
    if (cast[name]) continue;

    let assigned = voiceIds[poolIdx % voiceIds.length];
    let attempts = 0;
    while (used.has(assigned) && attempts < voiceIds.length) {
      poolIdx += 1;
      assigned = voiceIds[poolIdx % voiceIds.length];
      attempts += 1;
    }

    cast[name] = assigned;
    used.add(assigned);
    poolIdx += 1;
  }
  return cast;
}

export function segmentsFromScreenplay(
  lines: ScreenplayLine[],
  cast: CharacterCast,
  defaultVoiceId: string,
): ScriptSegment[] {
  return lines.map((line) =>
    newSegment(cast[line.character] ?? defaultVoiceId, line.text, line.character),
  );
}

/** 是否像「角色：台词」格式剧本（用于粘贴后自动分段） */
export function looksLikeScreenplay(raw: string): boolean {
  const lines = raw
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);
  if (!lines.length) return false;

  let hits = 0;
  for (const line of lines) {
    for (const re of SCREENPLAY_LINE_PATTERNS) {
      if (re.test(line)) {
        hits += 1;
        break;
      }
    }
  }
  return hits >= 2 || (hits === 1 && lines.length >= 2);
}

/**
 * 智能分段：剧本格式 → 按角色拆句并分配音色；纯文本 → 按空行拆段（多音色轮询）。
 */
export function autoSegmentText(
  raw: string,
  defaultVoiceId: string,
  voiceIds: string[],
  cast: CharacterCast = {},
): AutoSegmentResult {
  const text = raw.trim();
  if (!text) {
    return { segments: [newSegment(defaultVoiceId)], mode: "single", characterCount: 0, lineCount: 0 };
  }

  if (looksLikeScreenplay(text)) {
    const lines = parseScreenplayScript(text);
    const characters = uniqueCharacters(lines);
    const resolvedCast = autoAssignCast(characters, voiceIds, cast);
    const segments = segmentsFromScreenplay(lines, resolvedCast, defaultVoiceId);
    return {
      segments,
      mode: "screenplay",
      characterCount: characters.length,
      lineCount: lines.length,
    };
  }

  const paragraphs = text.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
  if (paragraphs.length > 1) {
    const labels = paragraphs.map((_, i) => `段落${i + 1}`);
    const resolvedCast = autoAssignCast(labels, voiceIds, cast);
    const segments = paragraphs.map((p, i) =>
      newSegment(resolvedCast[labels[i]] ?? defaultVoiceId, p, labels[i]),
    );
    return {
      segments,
      mode: "paragraph",
      characterCount: 0,
      lineCount: paragraphs.length,
    };
  }

  return {
    segments: [newSegment(defaultVoiceId, text)],
    mode: "single",
    characterCount: 0,
    lineCount: 1,
  };
}

const LYRICS_SECTION_RE =
  /^\[(主歌|副歌|前奏|间奏|桥段|尾奏|verse|chorus|bridge|intro|outro)[^\]]*\]$/i;

const VOCAL_ROLE_HINT_RE = /主唱|和声|合唱|伴唱|男声|女声|rap/i;

const DEFAULT_VOCAL_ROLE = "主唱";

/** 解析「演唱者：歌词」或段落标记格式 */
export function parseLyricsScript(raw: string): ScreenplayLine[] {
  const lines = raw
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);

  const out: ScreenplayLine[] = [];
  let activeRole = DEFAULT_VOCAL_ROLE;

  for (const line of lines) {
    if (LYRICS_SECTION_RE.test(line)) continue;

    let matched = false;
    for (const re of SCREENPLAY_LINE_PATTERNS) {
      const m = line.match(re);
      if (!m) continue;
      activeRole = m[1].trim();
      out.push({ character: activeRole, text: m[2].trim() });
      matched = true;
      break;
    }
    if (matched) continue;

    if (out.length && !/[：:]|^【/.test(line)) {
      out[out.length - 1].text += `\n${line}`;
      continue;
    }

    out.push({ character: activeRole, text: line });
  }

  return out;
}

/** 是否像歌词分段格式（演唱者标记或段落标签） */
export function looksLikeLyrics(raw: string): boolean {
  const lines = raw
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);
  if (!lines.length) return false;

  let roleHits = 0;
  let sectionHits = 0;

  for (const line of lines) {
    if (LYRICS_SECTION_RE.test(line)) {
      sectionHits += 1;
      continue;
    }
    if (!VOCAL_ROLE_HINT_RE.test(line)) continue;
    for (const re of SCREENPLAY_LINE_PATTERNS) {
      if (re.test(line)) {
        roleHits += 1;
        break;
      }
    }
  }

  return (
    roleHits >= 2 ||
    (roleHits >= 1 && sectionHits >= 1) ||
    (roleHits === 1 && lines.length >= 3)
  );
}

/**
 * 歌曲分段：歌词行解析 + 多声线分配。
 * 基于说话合成，默认略抬音高作「实验性念唱」预览。
 */
export function autoSegmentLyrics(
  raw: string,
  defaultVoiceId: string,
  voiceIds: string[],
  cast: CharacterCast = {},
): AutoSegmentResult {
  const text = raw.trim();
  if (!text) {
    return { segments: [newSegment(defaultVoiceId)], mode: "single", characterCount: 0, lineCount: 0 };
  }

  let lines: ScreenplayLine[];

  if (looksLikeLyrics(text)) {
    lines = parseLyricsScript(text);
  } else {
    const plainLines = text
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter((l) => l && !LYRICS_SECTION_RE.test(l));

    if (plainLines.length > 1) {
      lines = plainLines.map((t, i) => ({ character: `段落${i + 1}`, text: t }));
    } else {
      lines = [{ character: DEFAULT_VOCAL_ROLE, text }];
    }
  }

  const characters = uniqueCharacters(lines);
  const resolvedCast = autoAssignCast(characters, voiceIds, cast);
  const segments = segmentsFromScreenplay(lines, resolvedCast, defaultVoiceId).map((seg) => ({
    ...seg,
    pitch: seg.pitch === 1 ? 1.03 : seg.pitch,
  }));

  return {
    segments,
    mode: "lyrics",
    characterCount: characters.length,
    lineCount: lines.length,
  };
}

/** Split one segment into up to three parts with tuned middle. */
export function splitSegmentWithTune(
  segments: ScriptSegment[],
  segmentId: string,
  start: number,
  end: number,
  tune: { speed?: number | null; temperature?: number | null; pitch?: number; emotion?: string | null; emotionStrength?: number },
): ScriptSegment[] {
  const idx = segments.findIndex((s) => s.id === segmentId);
  if (idx < 0) return segments;
  const seg = segments[idx];
  const a = Math.max(0, Math.min(start, end));
  const b = Math.min(seg.text.length, Math.max(start, end));
  if (b <= a) return segments;

  const before = seg.text.slice(0, a);
  const middle = seg.text.slice(a, b);
  const after = seg.text.slice(b);
  const out: ScriptSegment[] = [];

  for (const [i, s] of segments.entries()) {
    if (i !== idx) {
      out.push(s);
      continue;
    }
    if (before.trim()) {
      out.push({ ...seg, id: crypto.randomUUID(), text: before });
    }
    out.push({
      ...seg,
      id: crypto.randomUUID(),
      text: middle,
      speed: tune.speed ?? seg.speed,
      temperature: tune.temperature ?? seg.temperature,
      pitch: tune.pitch ?? seg.pitch,
      emotion: tune.emotion ?? seg.emotion,
      emotionStrength: tune.emotionStrength ?? seg.emotionStrength,
    });
    if (after.trim()) {
      out.push({ ...seg, id: crypto.randomUUID(), text: after });
    }
  }
  return out;
}
