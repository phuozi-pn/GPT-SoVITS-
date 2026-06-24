import { describe, expect, it } from "vitest";
import {
  applySmartSynthToSegment,
  semitonesToPitchMultiplier,
} from "@/modules/produce/utils/smartSynth";
import { newSegment } from "@/modules/produce/types/script";

describe("smartSynth utils", () => {
  it("converts semitone offset to pitch multiplier", () => {
    expect(semitonesToPitchMultiplier(0)).toBe(1);
    expect(semitonesToPitchMultiplier(12)).toBe(1.5);
    expect(semitonesToPitchMultiplier(-12)).toBe(0.5);
  });

  it("applies smart synth result to segment", () => {
    const seg = newSegment("voice-a");
    const next = applySmartSynthToSegment(seg, {
      emotion: "angry",
      emotion_label: "怒",
      emotion_strength: 0.8,
      speed_factor: 1.2,
      temperature: 0.75,
      pitch_factor: 2,
      reasoning: "命令语气",
    });
    expect(next.emotion).toBe("angry");
    expect(next.speed).toBe(1.2);
    expect(next.temperature).toBe(0.75);
    expect(next.pitch).toBeGreaterThan(1);
  });
});
