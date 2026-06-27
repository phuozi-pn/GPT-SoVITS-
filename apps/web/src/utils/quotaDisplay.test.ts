import { describe, expect, it } from "vitest";

import { formatTokenVolume, formatTokenVolumeWithUnit, usagePercent, usageTone } from "@/utils/quotaDisplay";

describe("quotaDisplay", () => {
  it("formats large token volumes in 万", () => {
    expect(formatTokenVolume(50_000)).toBe("5 万");
    expect(formatTokenVolume(12_400)).toBe("1.24 万");
  });

  it("formats token volume with unit", () => {
    expect(formatTokenVolumeWithUnit(820)).toBe("820 Token");
    expect(formatTokenVolumeWithUnit(12_400)).toBe("1.24 万 Token");
  });

  it("computes usage percent and tone", () => {
    expect(usagePercent(8_000, 10_000)).toBe(80);
    expect(usageTone(8_000, 10_000)).toBe("warn");
    expect(usageTone(10_000, 10_000)).toBe("danger");
  });
});
