import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  DEFAULT_CAST_PROFILE,
  createCastProfile,
  getActiveCastProfile,
  importCastFromJson,
  listCastProfiles,
  loadCharacterCast,
  parseCastImport,
  pruneCharacterCast,
  rememberCastEntry,
  resolveCharacterCast,
  saveCharacterCast,
  switchCastProfile,
} from "./characterCast";

function mockLocalStorage() {
  const store: Record<string, string> = {};
  const ls = {
    getItem: (key: string) => (key in store ? store[key] : null),
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      for (const key of Object.keys(store)) delete store[key];
    },
  };
  vi.stubGlobal("localStorage", ls);
  return store;
}

describe("characterCast storage", () => {
  beforeEach(() => {
    mockLocalStorage();
    localStorage.setItem("dev_user_id", "user-a");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("saves and loads cast per user scope", () => {
    saveCharacterCast({ 方源: "v1", 旁白: "v2" });
    expect(loadCharacterCast()).toEqual({ 方源: "v1", 旁白: "v2" });
  });

  it("rememberCastEntry merges single mapping", () => {
    rememberCastEntry("方源", "v1");
    rememberCastEntry("白凝冰", "v2");
    expect(loadCharacterCast()).toEqual({ 方源: "v1", 白凝冰: "v2" });
  });

  it("pruneCharacterCast drops stale voice ids", () => {
    const pruned = pruneCharacterCast({ 方源: "gone", 旁白: "v2" }, ["v2", "v3"]);
    expect(pruned).toEqual({ 旁白: "v2" });
  });

  it("resolveCharacterCast prefers saved mapping then auto-assigns", () => {
    saveCharacterCast({ 方源: "v1" });
    const cast = resolveCharacterCast(["方源", "白凝冰"], ["v1", "v2", "v3"]);
    expect(cast).toEqual({ 方源: "v1", 白凝冰: "v2" });
  });

  it("migrates legacy flat storage into default profile", () => {
    localStorage.setItem("voice_character_cast:user-a", JSON.stringify({ 方源: "v1" }));
    expect(loadCharacterCast()).toEqual({ 方源: "v1" });
    expect(getActiveCastProfile()).toBe(DEFAULT_CAST_PROFILE);
    expect(localStorage.getItem("voice_character_cast:user-a")).toBeNull();
  });

  it("supports multiple named profiles", () => {
    saveCharacterCast({ 方源: "v1" });
    createCastProfile("第二集");
    saveCharacterCast({ 方源: "v2", 旁白: "v3" });

    expect(listCastProfiles()).toEqual([DEFAULT_CAST_PROFILE, "第二集"]);
    expect(loadCharacterCast()).toEqual({ 方源: "v2", 旁白: "v3" });

    switchCastProfile(DEFAULT_CAST_PROFILE);
    expect(loadCharacterCast()).toEqual({ 方源: "v1" });
  });

  it("parses export file and plain cast json", () => {
    const exported = parseCastImport({
      version: 1,
      profile: "蛊真人",
      exportedAt: "2026-06-18T00:00:00.000Z",
      cast: { 方源: "v1" },
    });
    expect(exported).toEqual({ profile: "蛊真人", cast: { 方源: "v1" } });

    const plain = parseCastImport({ 旁白: "v2" });
    expect(plain).toEqual({ profile: DEFAULT_CAST_PROFILE, cast: { 旁白: "v2" } });
  });

  it("imports json into profile store", () => {
    const result = importCastFromJson({
      version: 1,
      profile: "分享卡司",
      exportedAt: "2026-06-18T00:00:00.000Z",
      cast: { 方源: "v1", 白凝冰: "v2" },
    });
    expect(result).toEqual({
      profile: "分享卡司",
      cast: { 方源: "v1", 白凝冰: "v2" },
    });
    expect(getActiveCastProfile()).toBe("分享卡司");
    expect(loadCharacterCast()).toEqual({ 方源: "v1", 白凝冰: "v2" });
  });
});
