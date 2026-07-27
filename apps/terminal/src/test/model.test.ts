/** The client-side formulas against the methodology's published anchors. */
import { describe, expect, it } from "vitest";
import { alphaFH, ccmStar, compute, normInv, ticLognormal } from "@/lib/model";

describe("published anchors", () => {
  it("alpha_FH(1.5) = 0.91906", () => {
    expect(alphaFH(1.5)).toBeCloseTo(0.91906, 4);
  });
  it("alpha_FH(5.0) = 0.72749", () => {
    expect(alphaFH(5.0)).toBeCloseTo(0.72749, 4);
  });
  it("CCM* = 1.35373 at CCM = 1.5", () => {
    expect(ccmStar(1.5)).toBeCloseTo(1.35373, 3);
  });
  it("norm inverse round-trips", () => {
    expect(normInv(0.975)).toBeCloseTo(1.95996, 4);
  });
  it("Eq. 27 is finite and positive on sane inputs", () => {
    expect(ticLognormal(0.001, 1.35, 0.625913)).toBeGreaterThan(0);
  });
});

describe("the lesson", () => {
  const base = { sigma: 0.3, assetValue: 2e11, stDebt: 1e10, ltDebt: 6e10, w: 0.5, T: 1 };
  it("drift does not move RiskScore (Prop. 4.4.2)", () => {
    const a = compute({ ...base, eta: 0.05 });
    const b = compute({ ...base, eta: 0.45 });
    expect(a.riskScore).toBe(b.riskScore);
    expect(a.dd).not.toBe(b.dd);
  });
  it("the w slider moves the letter (the 7-notch experience)", () => {
    const w0 = compute({ ...base, eta: 0.12, w: 0.0 });
    const w1 = compute({ ...base, eta: 0.12, w: 1.0 });
    expect(w0.riskScore).not.toBe(w1.riskScore);
  });
  it("negative drift regime reports DEFECTIVE, never a letter", () => {
    const d = compute({ ...base, eta: -0.2 });
    expect(d.regime).toBe("DEFECTIVE");
    expect(d.letter).toBeNull();
    expect(d.riskScore).not.toBeNull();
  });
});
