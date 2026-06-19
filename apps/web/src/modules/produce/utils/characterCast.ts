import { autoAssignCast, type CharacterCast } from "@/modules/produce/types/script";

export const DEFAULT_CAST_PROFILE = "默认";
export const CAST_EXPORT_VERSION = 1 as const;

export type CastExportFile = {
  version: typeof CAST_EXPORT_VERSION;
  profile: string;
  exportedAt: string;
  cast: CharacterCast;
};

export type CastProfileStore = {
  active: string;
  profiles: Record<string, CharacterCast>;
};

const LEGACY_CAST_PREFIX = "voice_character_cast:";
const PROFILES_PREFIX = "voice_cast_profiles:";

function castUserScope(): string {
  const devUser = localStorage.getItem("dev_user_id");
  if (devUser) return devUser;
  const phone = localStorage.getItem("user_phone");
  if (phone) return phone;
  return "default";
}

function legacyStorageKey(): string {
  return `${LEGACY_CAST_PREFIX}${castUserScope()}`;
}

function profilesStorageKey(): string {
  return `${PROFILES_PREFIX}${castUserScope()}`;
}

function normalizeCast(raw: unknown): CharacterCast {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return {};

  const out: CharacterCast = {};
  for (const [name, voiceId] of Object.entries(raw as Record<string, unknown>)) {
    if (typeof name !== "string" || typeof voiceId !== "string") continue;
    const trimmedName = name.trim();
    const trimmedVoice = voiceId.trim();
    if (trimmedName && trimmedVoice) out[trimmedName] = trimmedVoice;
  }
  return out;
}

function isProfileStore(raw: unknown): raw is CastProfileStore {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return false;
  const obj = raw as Record<string, unknown>;
  if (typeof obj.active !== "string" || !obj.profiles || typeof obj.profiles !== "object" || Array.isArray(obj.profiles)) {
    return false;
  }
  return true;
}

function isLegacyFlatCast(raw: unknown): boolean {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return false;
  const obj = raw as Record<string, unknown>;
  if ("active" in obj || "profiles" in obj || "version" in obj) return false;
  return Object.values(obj).every((v) => typeof v === "string");
}

function emptyProfileStore(): CastProfileStore {
  return { active: DEFAULT_CAST_PROFILE, profiles: { [DEFAULT_CAST_PROFILE]: {} } };
}

function saveProfileStore(store: CastProfileStore): void {
  try {
    localStorage.setItem(profilesStorageKey(), JSON.stringify(store));
  } catch {
    // private mode / quota
  }
}

function loadProfileStore(): CastProfileStore {
  try {
    const raw = localStorage.getItem(profilesStorageKey());
    if (raw) {
      const parsed: unknown = JSON.parse(raw);
      if (isProfileStore(parsed)) {
        const profiles: Record<string, CharacterCast> = {};
        for (const [name, cast] of Object.entries(parsed.profiles)) {
          const trimmed = name.trim();
          if (!trimmed) continue;
          profiles[trimmed] = normalizeCast(cast);
        }
        if (!Object.keys(profiles).length) {
          profiles[DEFAULT_CAST_PROFILE] = {};
        }
        const active = parsed.active.trim();
        return {
          active: active && profiles[active] ? active : Object.keys(profiles)[0],
          profiles,
        };
      }
    }

    const legacyRaw = localStorage.getItem(legacyStorageKey());
    if (legacyRaw) {
      const parsed: unknown = JSON.parse(legacyRaw);
      if (isLegacyFlatCast(parsed)) {
        const store: CastProfileStore = {
          active: DEFAULT_CAST_PROFILE,
          profiles: { [DEFAULT_CAST_PROFILE]: normalizeCast(parsed) },
        };
        saveProfileStore(store);
        localStorage.removeItem(legacyStorageKey());
        return store;
      }
    }
  } catch {
    // fall through
  }

  return emptyProfileStore();
}

export function listCastProfiles(): string[] {
  return Object.keys(loadProfileStore().profiles);
}

export function getActiveCastProfile(): string {
  return loadProfileStore().active;
}

export function loadCharacterCast(): CharacterCast {
  const store = loadProfileStore();
  return { ...(store.profiles[store.active] ?? {}) };
}

export function saveCharacterCast(cast: CharacterCast): void {
  const store = loadProfileStore();
  store.profiles[store.active] = { ...cast };
  saveProfileStore(store);
}

export function switchCastProfile(name: string): CharacterCast {
  const trimmed = name.trim();
  const store = loadProfileStore();
  if (!trimmed || !store.profiles[trimmed]) return loadCharacterCast();

  store.active = trimmed;
  saveProfileStore(store);
  return { ...store.profiles[trimmed] };
}

export function createCastProfile(name: string): boolean {
  const trimmed = name.trim();
  if (!trimmed) return false;

  const store = loadProfileStore();
  if (store.profiles[trimmed]) return false;

  store.profiles[trimmed] = {};
  store.active = trimmed;
  saveProfileStore(store);
  return true;
}

export function deleteCastProfile(name: string): boolean {
  const trimmed = name.trim();
  const store = loadProfileStore();
  if (!trimmed || !store.profiles[trimmed]) return false;
  if (Object.keys(store.profiles).length <= 1) return false;

  delete store.profiles[trimmed];
  if (store.active === trimmed) {
    store.active = Object.keys(store.profiles)[0];
  }
  saveProfileStore(store);
  return true;
}

export function pruneCharacterCast(cast: CharacterCast, validVoiceIds: string[]): CharacterCast {
  const valid = new Set(validVoiceIds.filter(Boolean));
  if (!valid.size) return {};

  const out: CharacterCast = {};
  for (const [name, voiceId] of Object.entries(cast)) {
    if (valid.has(voiceId)) out[name] = voiceId;
  }
  return out;
}

export function rememberCastEntry(name: string, voiceId: string): CharacterCast {
  const trimmedName = name.trim();
  const trimmedVoice = voiceId.trim();
  if (!trimmedName || !trimmedVoice) return loadCharacterCast();

  const next = { ...loadCharacterCast(), [trimmedName]: trimmedVoice };
  saveCharacterCast(next);
  return next;
}

export function resolveCharacterCast(
  characters: string[],
  voiceIds: string[],
  saved?: CharacterCast,
): CharacterCast {
  const base = pruneCharacterCast(saved ?? loadCharacterCast(), voiceIds);
  return autoAssignCast(characters, voiceIds, base);
}

export function buildCastExport(profileName?: string, cast?: CharacterCast): CastExportFile {
  const store = loadProfileStore();
  const profile = (profileName ?? store.active).trim() || DEFAULT_CAST_PROFILE;
  const resolvedCast = cast ?? store.profiles[profile] ?? loadCharacterCast();

  return {
    version: CAST_EXPORT_VERSION,
    profile,
    exportedAt: new Date().toISOString(),
    cast: { ...resolvedCast },
  };
}

export function parseCastImport(raw: unknown): { profile: string; cast: CharacterCast } | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;

  const obj = raw as Record<string, unknown>;
  if (obj.version === CAST_EXPORT_VERSION && obj.cast) {
    const profile = typeof obj.profile === "string" && obj.profile.trim() ? obj.profile.trim() : DEFAULT_CAST_PROFILE;
    const cast = normalizeCast(obj.cast);
    return Object.keys(cast).length ? { profile, cast } : null;
  }

  if (isLegacyFlatCast(raw)) {
    const cast = normalizeCast(raw);
    return Object.keys(cast).length ? { profile: DEFAULT_CAST_PROFILE, cast } : null;
  }

  return null;
}

export function importCastFromJson(raw: unknown, asProfile?: string): { profile: string; cast: CharacterCast } | null {
  const parsed = parseCastImport(raw);
  if (!parsed) return null;

  const profileName = (asProfile?.trim() || parsed.profile).trim() || DEFAULT_CAST_PROFILE;
  const store = loadProfileStore();
  store.profiles[profileName] = { ...parsed.cast };
  store.active = profileName;
  saveProfileStore(store);
  return { profile: profileName, cast: parsed.cast };
}

export function downloadCastExport(profileName?: string, cast?: CharacterCast): void {
  const payload = buildCastExport(profileName, cast);
  const safeName = payload.profile.replace(/[^\w\u4e00-\u9fff-]+/g, "_") || "cast";
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `cast-${safeName}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}
