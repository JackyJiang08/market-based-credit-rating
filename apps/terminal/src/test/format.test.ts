import { describe, expect, it } from "vitest";
import { fuzzyScore, letterWithInterval } from "@/lib/format";

describe("the presentation rule", () => {
  it("attaches the interval to the letter", () => {
    expect(letterWithInterval("BB", "BBB-", "BB-")).toBe("BB (BBB-..BB-)");
  });
  it("never renders a bare letter silently", () => {
    expect(letterWithInterval("AAA", null, null)).toBe("AAA (interval unavailable)");
  });
  it("renders a dash for no letter", () => {
    expect(letterWithInterval(null, null, null)).toBe("—");
  });
});

describe("fuzzy match", () => {
  it("prefers ticker prefix", () => {
    expect(fuzzyScore("orc", "ORCL")).toBeGreaterThan(fuzzyScore("orc", "Oracle Corporation"));
  });
  it("rejects non-matches", () => {
    expect(fuzzyScore("zzz", "ORCL")).toBeLessThan(0);
  });
});
