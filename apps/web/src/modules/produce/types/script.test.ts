import { describe, expect, it } from "vitest";
import {
  autoAssignCast,
  autoSegmentText,
  buildSynthesisPayload,
  looksLikeScreenplay,
  newSegment,
  parseScreenplayScript,
  segmentsFromScreenplay,
  splitSegmentWithTune,
  uniqueCharacters,
  validateSynthesisScript,
  SYNTH_LIMITS,
} from "./script";

describe("buildSynthesisPayload", () => {
  it("single segment uses flat API body", () => {
    const seg = newSegment("voice-a", "你好");
    const body = buildSynthesisPayload([seg], { speed: 1.05, temperature: 0.78 });
    expect(body.voice_version_id).toBe("voice-a");
    expect(body.text).toBe("你好");
    expect(body.speed_factor).toBe(1.05);
    expect(body.segments).toBeUndefined();
  });

  it("fills missing segment voice from fallback", () => {
    const seg = newSegment("", "你好");
    const body = buildSynthesisPayload([seg], { speed: 1, temperature: 0.78 }, "voice-fallback");
    expect(body.voice_version_id).toBe("voice-fallback");
  });

  it("multi voice uses segments array", () => {
    const a = newSegment("voice-a", "甲");
    const b = newSegment("voice-b", "乙");
    const body = buildSynthesisPayload([a, b], { speed: 1, temperature: 0.8 });
    expect(body.segments?.length).toBe(2);
    expect(body.segments?.[1].voice_version_id).toBe("voice-b");
  });

  it("local pitch triggers segments mode", () => {
    const seg = { ...newSegment("voice-a", "一句"), pitch: 1.1 };
    const body = buildSynthesisPayload([seg], { speed: 1, temperature: 0.78 });
    expect(body.segments?.[0].pitch_factor).toBe(1.1);
  });
});

describe("splitSegmentWithTune", () => {
  it("splits middle with tune", () => {
    const seg = newSegment("v1", "你好世界");
    const next = splitSegmentWithTune([seg], seg.id, 1, 3, { speed: 0.9, pitch: 1.05 });
    expect(next.length).toBe(3);
    expect(next[1].text).toBe("好世");
    expect(next[1].speed).toBe(0.9);
  });
});

describe("parseScreenplayScript", () => {
  it("parses colon and bracket formats", () => {
    const lines = parseScreenplayScript(`方源：你给我出来！
【白凝冰】你以为逃得掉吗？`);
    expect(lines).toEqual([
      { character: "方源", text: "你给我出来！" },
      { character: "白凝冰", text: "你以为逃得掉吗？" },
    ]);
  });

  it("merges continuation lines", () => {
    const lines = parseScreenplayScript(`方源：第一句
第二句续行`);
    expect(lines[0].text).toBe("第一句\n第二句续行");
  });

  it("assigns narration for bare lines", () => {
    const lines = parseScreenplayScript("夜色渐深。");
    expect(lines[0].character).toBe("旁白");
  });
});

describe("segmentsFromScreenplay", () => {
  it("builds segments with character names", () => {
    const lines = parseScreenplayScript("甲：你好\n乙：再见");
    const cast = autoAssignCast(uniqueCharacters(lines), ["v1", "v2"]);
    const segs = segmentsFromScreenplay(lines, cast, "v1");
    expect(segs.length).toBe(2);
    expect(segs[0].characterName).toBe("甲");
    expect(segs[1].voiceVersionId).toBe("v2");
  });
});

describe("autoSegmentText", () => {
  it("detects screenplay format", () => {
    expect(looksLikeScreenplay("方源：甲\n白凝冰：乙")).toBe(true);
    expect(looksLikeScreenplay("一句普通台词")).toBe(false);
  });

  it("segments screenplay with cast", () => {
    const result = autoSegmentText(
      "方源：出来！\n白凝冰：休想！",
      "v-default",
      ["v1", "v2"],
      { 方源: "v1" },
    );
    expect(result.mode).toBe("screenplay");
    expect(result.characterCount).toBe(2);
    expect(result.segments[0].voiceVersionId).toBe("v1");
    expect(result.segments[1].voiceVersionId).toBe("v2");
  });

  it("segments plain text by blank lines", () => {
    const result = autoSegmentText("第一段\n\n第二段", "v1", ["v1", "v2"]);
    expect(result.mode).toBe("paragraph");
    expect(result.segments.length).toBe(2);
    expect(result.segments[0].voiceVersionId).toBe("v1");
    expect(result.segments[1].voiceVersionId).toBe("v1");
  });

  it("does not treat narration colon as screenplay", () => {
    const line = "茶凉了。我合上书本，在心里默默说了一句：今天，也要好好过。";
    expect(looksLikeScreenplay(line)).toBe(false);
    const lines = parseScreenplayScript(line);
    expect(lines.length).toBe(1);
    expect(lines[0].character).toBe("旁白");
    expect(lines[0].text).toBe(line);
  });

  it("keeps short plain text as single segment", () => {
    const result = autoSegmentText("你好世界", "v1", ["v1", "v2"]);
    expect(result.mode).toBe("single");
    expect(result.segments.length).toBe(1);
  });
});

describe("validateSynthesisScript", () => {
  const global = { speed: 1, temperature: 0.78 };

  it("rejects empty script", () => {
    const r = validateSynthesisScript([newSegment("v1", "  ")], global);
    expect(r.ok).toBe(false);
  });

  it("rejects single text over 5000", () => {
    const r = validateSynthesisScript([newSegment("v1", "a".repeat(5001))], global);
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.message).toContain("5000");
  });

  it("rejects segment over 2000 in multi mode", () => {
    const a = newSegment("v1", "短");
    const b = newSegment("v1", "x".repeat(2001));
    const r = validateSynthesisScript([a, b], global);
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.message).toContain("2000");
  });
});
