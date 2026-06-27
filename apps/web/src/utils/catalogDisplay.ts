/**
 * 音色馆标签逻辑（分层、互斥、校验）
 *
 * 打标顺序：① 性别（1 个）→ ② 适配音色（1–4）→ ③ 声线质感（2–3）→ ④ 场景（0–2）
 * 展示与入库均按此顺序；不猜测填充未标注的层级。
 */
import type { CatalogEntry } from "@/api/catalog";
import { resolveMediaUrl } from "@/config";
import { LICENSE_TYPES } from "@/api/catalog";

export type CatalogAccessTone = "ok" | "warn" | "muted";

export type VoiceTagBuckets = {
  gender: string[];
  roles: string[];
  traits: string[];
  scenes: string[];
};

export type CatalogTagValidation = {
  ok: boolean;
  errors: string[];
  warnings: string[];
};

export const TAG_TIER_LIMITS = {
  gender: 1,
  roles: 4,
  traits: 3,
  scenes: 2,
} as const;

/** 性别 — 第 1 层，必选 1 个 */
export const VOICE_GENDER_TAG_PRESETS = ["男声", "女声", "童声", "中性声"] as const;

/** 适配音色 — 第 2 层，须与性别兼容 */
export const VOICE_ROLE_TAG_PRESETS = [
  "男主",
  "女主",
  "男配",
  "女配",
  "反派",
  "路人",
  "龙套",
  "和尚",
  "道士",
  "老人",
  "少年",
  "少女",
  "旁白",
  "解说",
  "霸总",
  "母亲",
  "父亲",
  "丫鬟",
  "太监",
  "萌娃",
] as const;

/** 声线质感 — 第 3 层 */
export const VOICE_TRAIT_TAG_PRESETS = [
  "温柔",
  "豪放",
  "细腻",
  "甜美",
  "御姐",
  "成熟",
  "低沉",
  "清亮",
  "磁性",
  "沙哑",
  "慵懒",
  "知性",
  "元气",
  "霸气",
  "洒脱",
  "沉稳",
  "俏皮",
  "冷艳",
  "温润",
  "凌厉",
  "深情",
  "克制",
  "厚重",
  "空灵",
  "邪魅",
  "坚毅",
  "软糯",
  "少年感",
] as const;

/** 适用场景 — 第 4 层 */
export const VOICE_SCENE_TAG_PRESETS = [
  "短剧",
  "有声书",
  "广告",
  "新闻",
  "古风",
  "二次元",
  "喜剧",
  "悬疑",
  "情感",
] as const;

/** 角色 → 允许的性别；未列出者为通用角色 */
export const ROLE_GENDER_RULES: Record<string, readonly string[]> = {
  男主: ["男声"],
  男配: ["男声"],
  霸总: ["男声"],
  父亲: ["男声"],
  太监: ["男声"],
  女主: ["女声"],
  女配: ["女声"],
  母亲: ["女声"],
  丫鬟: ["女声"],
  萌娃: ["童声"],
  少女: ["女声", "童声"],
  少年: ["男声", "童声"],
};

/** 选角色时若未选性别，自动补全 */
export const ROLE_IMPLIES_GENDER: Record<string, string> = {
  男主: "男声",
  男配: "男声",
  霸总: "男声",
  父亲: "男声",
  太监: "男声",
  女主: "女声",
  女配: "女声",
  母亲: "女声",
  丫鬟: "女声",
  萌娃: "童声",
};

/** 角色 → 推荐声线质感（上架提示用） */
export const ROLE_TRAIT_HINTS: Record<string, readonly string[]> = {
  男主: ["磁性", "深情", "沉稳"],
  女主: ["温柔", "细腻", "甜美"],
  反派: ["凌厉", "邪魅", "低沉"],
  路人: ["克制", "沉稳"],
  龙套: ["克制", "沉稳"],
  和尚: ["温润", "沉稳", "空灵"],
  道士: ["空灵", "沉稳", "克制"],
  老人: ["沙哑", "厚重", "温润"],
  少年: ["清亮", "少年感", "元气"],
  少女: ["甜美", "软糯", "俏皮"],
  旁白: ["知性", "温润", "沉稳"],
  解说: ["清亮", "明快", "知性"],
  霸总: ["低沉", "霸气", "磁性"],
};

/** @deprecated */
export const VOICE_STYLE_TAG_PRESETS = [
  ...VOICE_GENDER_TAG_PRESETS,
  ...VOICE_ROLE_TAG_PRESETS,
  ...VOICE_TRAIT_TAG_PRESETS,
  ...VOICE_SCENE_TAG_PRESETS,
] as const;

export const VOICE_GENDER_TAGS = new Set<string>(VOICE_GENDER_TAG_PRESETS);
export const VOICE_ROLE_TAGS = new Set<string>(VOICE_ROLE_TAG_PRESETS);
export const VOICE_TRAIT_TAGS = new Set<string>(VOICE_TRAIT_TAG_PRESETS);
export const VOICE_SCENE_TAGS = new Set<string>([...VOICE_SCENE_TAG_PRESETS, "演示", "demo", "smoke"]);

export const GENDER_DISPLAY_LABEL: Record<string, string> = {
  男声: "男生",
  女声: "女生",
  童声: "童声",
  中性声: "中性",
};

// ── 基础工具 ──────────────────────────────────────────────

export function catalogAccessStatus(
  entry: Pick<CatalogEntry, "can_use" | "purchased" | "price_cents" | "owner_user_id">,
  viewerUserId: string,
): { label: string; tone: CatalogAccessTone } {
  if (entry.owner_user_id === viewerUserId) return { label: "我的音色", tone: "muted" };
  if (entry.purchased) return { label: "已购买", tone: "ok" };
  if (!entry.can_use && entry.price_cents > 0) return { label: "需购买", tone: "warn" };
  if (entry.can_use && entry.price_cents === 0) return { label: "免费可用", tone: "ok" };
  if (entry.can_use) return { label: "已授权", tone: "ok" };
  return { label: "不可用", tone: "warn" };
}

export function catalogAccessPillClass(tone: CatalogAccessTone): string {
  if (tone === "warn") return "pill pill--warn";
  if (tone === "muted") return "pill pill--muted";
  return "pill pill--ok";
}

export function parseCatalogTags(raw: string): string[] {
  return raw
    .split(/[,，]/)
    .map((t) => t.trim())
    .filter(Boolean);
}

export function licenseLabel(id: string): string {
  return LICENSE_TYPES.find((t) => t.id === id)?.label ?? id;
}

export function catalogStatusLabel(status: string): string {
  if (status === "pending") return "待审核";
  if (status === "published") return "已上架";
  if (status === "rejected") return "已驳回";
  return status;
}

export function avatarInitial(title: string): string {
  return title.trim().charAt(0) || "音";
}

export function shortUserId(id: string): string {
  return id.length > 8 ? `${id.slice(0, 8)}…` : id;
}

export function isVoiceGenderTag(tag: string): boolean {
  return VOICE_GENDER_TAGS.has(tag);
}

export function isVoiceRoleTag(tag: string): boolean {
  return VOICE_ROLE_TAGS.has(tag);
}

export function isVoiceTraitTag(tag: string): boolean {
  return VOICE_TRAIT_TAGS.has(tag);
}

export function isVoiceSceneTag(tag: string): boolean {
  if (isVoiceGenderTag(tag) || isVoiceRoleTag(tag) || isVoiceTraitTag(tag)) return false;
  return VOICE_SCENE_TAGS.has(tag);
}

export function isRoleAllowedForGender(role: string, gender: string | null): boolean {
  const rule = ROLE_GENDER_RULES[role];
  if (!rule) return true;
  if (!gender) return true;
  return rule.includes(gender);
}

/** 当前性别下可选的适配音色 */
export function rolesForGender(gender: string | null): readonly string[] {
  if (!gender) return VOICE_ROLE_TAG_PRESETS;
  return VOICE_ROLE_TAG_PRESETS.filter((r) => isRoleAllowedForGender(r, gender));
}

export function partitionVoiceTags(tags: string[]): VoiceTagBuckets {
  const buckets: VoiceTagBuckets = { gender: [], roles: [], traits: [], scenes: [] };
  for (const tag of tags) {
    if (isVoiceGenderTag(tag)) buckets.gender.push(tag);
    else if (isVoiceRoleTag(tag)) buckets.roles.push(tag);
    else if (isVoiceTraitTag(tag)) buckets.traits.push(tag);
    else if (tag) buckets.scenes.push(tag);
  }
  return buckets;
}

/** 按逻辑分层、去重、截断、剔除冲突角色 */
export function normalizeCatalogTags(input: string[]): string[] {
  const raw = partitionVoiceTags(input);

  let gender = raw.gender[0] ?? null;
  if (!gender) {
    for (const role of raw.roles) {
      const implied = ROLE_IMPLIES_GENDER[role];
      if (implied) {
        gender = implied;
        break;
      }
    }
  }

  const roles = [...new Set(raw.roles)]
    .filter((r) => isRoleAllowedForGender(r, gender))
    .slice(0, TAG_TIER_LIMITS.roles);

  const traits = [...new Set(raw.traits)].slice(0, TAG_TIER_LIMITS.traits);
  const scenes = [...new Set(raw.scenes)].slice(0, TAG_TIER_LIMITS.scenes);

  const ordered: string[] = [];
  if (gender) ordered.push(gender);
  ordered.push(...roles, ...traits, ...scenes);
  return ordered.slice(0, 10);
}

export function catalogTagsToString(tags: string[]): string {
  return normalizeCatalogTags(tags).join(", ");
}

export function validateCatalogTags(tags: string[]): CatalogTagValidation {
  const normalized = normalizeCatalogTags(tags);
  const b = partitionVoiceTags(normalized);
  const errors: string[] = [];
  const warnings: string[] = [];

  if (b.gender.length !== 1) {
    errors.push("第 1 步：请选择 1 个性别（男声 / 女声 / 童声）");
  }
  if (b.roles.length < 1) {
    errors.push("第 2 步：请至少选 1 个适配音色（如男主、反派、路人）");
  }
  if (b.traits.length < 2) {
    warnings.push("第 3 步：建议补充 2–3 个声线质感（如温柔、细腻、磁性）");
  }
  if (b.scenes.length < 1) {
    warnings.push("第 4 步：可选 1–2 个适用场景（如短剧），便于买家筛选");
  }

  const incompatible = partitionVoiceTags(tags).roles.filter(
    (r) => b.gender[0] && !isRoleAllowedForGender(r, b.gender[0]),
  );
  if (incompatible.length) {
    warnings.push(`已移除与性别冲突的角色：${incompatible.join("、")}`);
  }

  return { ok: errors.length === 0, errors, warnings };
}

/** 智能切换：互斥性别、角色上限、自动补性别、规范化顺序 */
export function toggleCatalogTagLogical(current: string[], tag: string): string[] {
  let tags = [...current];

  if (isVoiceGenderTag(tag)) {
    if (tags.includes(tag)) {
      tags = tags.filter((t) => t !== tag);
    } else {
      tags = tags.filter((t) => !isVoiceGenderTag(t));
      tags.push(tag);
      const gender = tag;
      tags = tags.filter((t) => !isVoiceRoleTag(t) || isRoleAllowedForGender(t, gender));
    }
    return normalizeCatalogTags(tags);
  }

  if (isVoiceRoleTag(tag)) {
    if (tags.includes(tag)) {
      tags = tags.filter((t) => t !== tag);
    } else {
      let gender = resolveGenderTag(tags);
      if (!gender && ROLE_IMPLIES_GENDER[tag]) {
        tags = tags.filter((t) => !isVoiceGenderTag(t));
        tags.push(ROLE_IMPLIES_GENDER[tag]);
        gender = ROLE_IMPLIES_GENDER[tag];
      }
      if (gender && !isRoleAllowedForGender(tag, gender)) {
        return normalizeCatalogTags(tags);
      }
      const roles = tags.filter(isVoiceRoleTag);
      if (roles.length >= TAG_TIER_LIMITS.roles) {
        tags = tags.filter((t) => t !== roles[0]);
      }
      tags.push(tag);
    }
    return normalizeCatalogTags(tags);
  }

  if (isVoiceTraitTag(tag)) {
    if (tags.includes(tag)) {
      tags = tags.filter((t) => t !== tag);
    } else {
      const traits = tags.filter(isVoiceTraitTag);
      if (traits.length >= TAG_TIER_LIMITS.traits) {
        tags = tags.filter((t) => t !== traits[0]);
      }
      tags.push(tag);
    }
    return normalizeCatalogTags(tags);
  }

  if (isVoiceSceneTag(tag) || !isVoiceGenderTag(tag)) {
    if (tags.includes(tag)) {
      tags = tags.filter((t) => t !== tag);
    } else {
      const scenes = tags.filter((t) => !isVoiceGenderTag(t) && !isVoiceRoleTag(t) && !isVoiceTraitTag(t));
      if (scenes.length >= TAG_TIER_LIMITS.scenes) {
        tags = tags.filter((t) => t !== scenes[0]);
      }
      tags.push(tag);
    }
    return normalizeCatalogTags(tags);
  }

  return normalizeCatalogTags(tags);
}

/** @deprecated 请用 toggleCatalogTagLogical */
export function toggleCatalogTagString(raw: string, tag: string): string {
  return catalogTagsToString(toggleCatalogTagLogical(parseCatalogTags(raw), tag));
}

// ── 展示（仅显式标签，按层顺序，不猜测） ─────────────────

export function voiceTraitTags(tags: string[], limit = TAG_TIER_LIMITS.traits): string[] {
  return partitionVoiceTags(tags).traits.slice(0, limit);
}

export function voiceRoleTags(tags: string[], limit = TAG_TIER_LIMITS.roles): string[] {
  return partitionVoiceTags(tags).roles.slice(0, limit);
}

export function resolveGenderTag(tags: string[]): string | null {
  const { gender, roles } = partitionVoiceTags(tags);
  if (gender[0]) return gender[0];
  for (const role of roles) {
    const implied = ROLE_IMPLIES_GENDER[role];
    if (implied) return implied;
  }
  return null;
}

export function displayVoiceGender(tags: string[]): string | null {
  const raw = partitionVoiceTags(tags).gender[0] ?? resolveGenderTag(tags);
  return raw ? (GENDER_DISPLAY_LABEL[raw] ?? raw) : null;
}

export function displayVoiceRoles(tags: string[], limit = TAG_TIER_LIMITS.roles): string[] {
  return voiceRoleTags(tags, limit);
}

export function displayVoiceTraits(tags: string[], limit = TAG_TIER_LIMITS.traits): string[] {
  return voiceTraitTags(tags, limit);
}

export function displayVoiceCastLine(tags: string[]): string {
  const gender = displayVoiceGender(tags);
  const role = displayVoiceRoles(tags, 1)[0];
  if (gender && role) return `${gender}·${role}`;
  return gender || role || displayVoiceTraits(tags, 1)[0] || "";
}

export function catalogOwnerLabel(entry: Pick<CatalogEntry, "owner_display_name" | "owner_user_id">): string {
  const name = entry.owner_display_name?.trim();
  if (name && !/^00000000/.test(name)) return name.replace(/^创作者\s*·\s*/, "");
  return "认证创作者";
}

/** 对外展示描述：过滤测试/开发文案 */
const INTERNAL_DESC_PATTERN =
  /playwright|mock|e2e|金路径|dev-zero|smoke|test|演示流程|00000000/i;

export function catalogPublicDescription(
  entry: Pick<CatalogEntry, "description" | "voice_name">,
): string {
  const desc = entry.description?.trim() ?? "";
  if (desc && !INTERNAL_DESC_PATTERN.test(desc)) return desc;
  const voice = entry.voice_name?.trim() ?? "";
  if (voice && !INTERNAL_DESC_PATTERN.test(voice)) return voice;
  return "";
}

/** 封面图：优先创作者上传 / AI 生图 URL，否则按性别默认插画 */
export function normalizeMediaUrl(url: string | null | undefined): string {
  const custom = url?.trim();
  if (!custom) return "";
  return resolveMediaUrl(custom);
}

export function catalogAvatarUrl(
  entry: Pick<CatalogEntry, "catalog_id" | "cover_image_url" | "tags">,
): string {
  const custom = normalizeMediaUrl(entry.cover_image_url);
  if (custom) return custom;
  return defaultCatalogCoverForTags(entry.tags ?? []);
}

export const DEFAULT_CATALOG_COVER_MALE = "/catalog/covers/voice-male-01.svg";
export const DEFAULT_CATALOG_COVER_FEMALE = "/catalog/covers/voice-female-01.svg";

export function defaultCatalogCoverForTags(tags: string[]): string {
  const gender = resolveGenderTag(tags);
  if (gender === "女声" || gender === "童声") return DEFAULT_CATALOG_COVER_FEMALE;
  return DEFAULT_CATALOG_COVER_MALE;
}

/** 与后端 build_catalog_cover_prompt 对齐，供封面编辑器「从标签生成提示词」 */
export function suggestCatalogCoverPrompt(title: string, tags: string[]): string {
  const normalized = normalizeCatalogTags(tags);
  const gender = resolveGenderTag(normalized);
  const genderPhrase =
    gender === "男声" ? "男性" : gender === "女声" ? "女性" : gender === "童声" ? "儿童" : gender === "中性声" ? "中性" : "配音角色";
  const roles = voiceRoleTags(normalized);
  const traits = normalized.filter(
    (t) => !VOICE_GENDER_TAG_PRESETS.includes(t as (typeof VOICE_GENDER_TAG_PRESETS)[number]) && !roles.includes(t),
  );
  const rolePhrase = roles.length ? roles.join("、") : "通用配音";
  const traitPhrase = traits.length ? traits.slice(0, 3).join("、") : "沉稳、自然";
  const titleBit = title.trim() ? `作品名《${title.trim()}》，` : "";
  return (
    `${titleBit}简约高级插画风格配音角色头像，正方形构图，${genderPhrase}，` +
    `适合饰演${rolePhrase}，声线气质${traitPhrase}，` +
    `暖金米色背景，柔和光影，无文字无水印，扁平插画，高品质`
  );
}

/** 创作者头像：优先 profile URL，否则按 userId 稳定分配默认插画 */
export function creatorAvatarUrl(
  displayName: string,
  avatarUrl?: string | null,
  userId?: string | null,
): string {
  const custom = normalizeMediaUrl(avatarUrl);
  if (custom) return custom;
  if (userId?.trim()) {
    const compact = userId.replace(/-/g, "");
    let sum = 0;
    for (let i = 0; i < compact.length; i++) sum += compact.charCodeAt(i);
    return sum % 2 === 0 ? "/catalog/covers/voice-female-01.svg" : "/catalog/covers/voice-male-01.svg";
  }
  const code = displayName.trim().charCodeAt(0) || 0;
  return code % 2 === 0 ? "/catalog/covers/voice-female-01.svg" : "/catalog/covers/voice-male-01.svg";
}

/** 上架预览：男声 → 男主·反派 → 沉稳·磁性 → 短剧 */
export function formatCatalogTagTiers(tags: string[]): string {
  const b = partitionVoiceTags(normalizeCatalogTags(tags));
  const parts: string[] = [];
  if (b.gender[0]) parts.push(b.gender[0]);
  if (b.roles.length) parts.push(b.roles.join("·"));
  if (b.traits.length) parts.push(b.traits.join("·"));
  if (b.scenes.length) parts.push(b.scenes.join("·"));
  return parts.join(" → ") || "尚未打标";
}

export function traitHintsForRoles(roles: string[]): string[] {
  const hints = new Set<string>();
  for (const role of roles) {
    for (const t of ROLE_TRAIT_HINTS[role] ?? []) {
      if (isVoiceTraitTag(t)) hints.add(t);
    }
  }
  return [...hints].slice(0, 6);
}
