import { describe, expect, it } from "vitest";

import {
  resolveVoiceOrigin,
  versionDefaultDisplayName,
  voiceOriginLabel,
  voicePickerBadge,
} from "@/utils/voiceOriginDisplay";

describe("voiceOriginDisplay", () => {
  it("labels quick clone vs cloud train", () => {
    expect(voiceOriginLabel("quick_clone")).toBe("快速克隆");
    expect(voiceOriginLabel("cloud")).toBe("云端微调");
    expect(voiceOriginLabel("engine")).toBe("本地微调");
  });

  it("labels imported versions", () => {
    expect(resolveVoiceOrigin("import_upload", true).label).toBe("导入权重");
    expect(voicePickerBadge({ imported: true })).toBe("导入");
  });

  it("builds default version names", () => {
    expect(
      versionDefaultDisplayName({ version: 2, train_mode: "quick_clone" }),
    ).toBe("快速克隆 v2");
    expect(
      versionDefaultDisplayName({ version: 1, label: "旁白", train_mode: "cloud" }),
    ).toBe("旁白");
  });

  it("picker badge distinguishes clone and train", () => {
    expect(voicePickerBadge({ train_mode: "quick_clone" })).toBe("快速克隆");
    expect(voicePickerBadge({ train_mode: "cloud" })).toBe("云端微调");
    expect(voicePickerBadge({ granted: true, train_mode: "quick_clone" })).toBe("已购授权");
  });
});
