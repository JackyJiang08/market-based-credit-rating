/** The published formulas, client-side, for the sensitivity playground.
 *
 * Everything here is public: the TiC equations by number (Eq. 11–14, 22, 26)
 * and the published Table-8 seven-grade scale — the same constants committed
 * in creditrating/model/conversion.py. Nothing from the licensed lookup
 * grids is used; the letter comes from the ANALYTICAL route on the
 * seven-grade scale (no notches — the grids that notch it are licensed).
 *
 * Anchors unit-tested against the methodology: alpha_FH(1.5) = 0.91906,
 * CCM* = 1.35373.
 */

export const Q_SP = 0.625913;
const CML_LN = 1.35; // ln(CML)

/** Published Table-8 scale: RiskScore and one-year TTC PD per grade. */
export const TABLE8 = [
  { letter: "AAA", rs: 2.7, pd: 0.0001 },
  { letter: "AA", rs: 3.5, pd: 0.0003 },
  { letter: "A", rs: 5.2, pd: 0.0007 },
  { letter: "BBB", rs: 9.9, pd: 0.0023 },
  { letter: "BB", rs: 22.2, pd: 0.0088 },
  { letter: "B", rs: 50.7, pd: 0.0441 },
  { letter: "CCC", rs: 154.8, pd: 0.3359 },
] as const;

/** Φ via Abramowitz–Stegun 7.1.26 erf approximation (|ε| < 1.5e-7). */
export function normCdf(x: number): number {
  const t = 1 / (1 + 0.3275911 * Math.abs(x) / Math.SQRT2);
  const erf =
    1 -
    t *
      (0.254829592 +
        t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429)))) *
      Math.exp((-x * x) / 2);
  return x >= 0 ? 0.5 * (1 + erf) : 0.5 * (1 - erf);
}

export interface Inputs {
  sigma: number; // annualized asset volatility
  assetValue: number; // A (held at the EM point estimate)
  stDebt: number;
  ltDebt: number;
  w: number; // long-term debt weight in the barrier
  eta: number; // asset drift
  T: number; // horizon in years
}

export interface Outputs {
  d: number;
  lnAD: number | null;
  riskScore: number | null;
  dd: number | null;
  edf: number | null;
  pitPd: number | null;
  mu: number | null;
  ccm: number | null;
  regime: "VALID" | "DEFECTIVE" | "INVALID";
  letter: string | null; // seven-grade analytical scale
  atScaleTop: boolean;
}

/** Φ⁻¹ via Acklam's rational approximation (|ε| ~ 1e-9). */
export function normInv(p: number): number {
  if (p <= 0 || p >= 1) return NaN;
  const a = [-39.6968302866538, 220.946098424521, -275.928510446969,
    138.357751867269, -30.6647980661472, 2.50662827745924];
  const b = [-54.4760987982241, 161.585836858041, -155.698979859887,
    66.8013118877197, -13.2806815528857];
  const c = [-0.00778489400243029, -0.322396458041136, -2.40075827716184,
    -2.54973253934373, 4.37466414146497, 2.93816398269878];
  const d = [0.00778469570904146, 0.32246712907004, 2.445134137143, 3.75440866190742];
  const pl = 0.02425;
  let q: number, r: number;
  if (p < pl) {
    q = Math.sqrt(-2 * Math.log(p));
    return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
      ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  if (p <= 1 - pl) {
    q = p - 0.5;
    r = q * q;
    return ((((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q) /
      (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
  }
  q = Math.sqrt(-2 * Math.log(1 - p));
  return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
    ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
}

/** Eq. 22, inverse-Gaussian branch, theta = 1: a = sqrt(CML).
 *  alpha_FH(ccm) = Φ(a/ccm − 1/a) + exp(2/ccm)·Φ(−a/ccm − 1/a).
 *  Mirrors conversion.alpha_first_hitting (log-space there; the playground
 *  clamps ccm ≥ 0.05 so plain space is exact enough). */
export function alphaFH(ccm: number): number {
  const a = Math.exp(CML_LN / 2); // sqrt(CML)
  const first = normCdf(a / ccm - 1 / a);
  const second = ccm > 0.05 ? Math.exp(2 / ccm) * normCdf(-a / ccm - 1 / a) : 0;
  return first + second;
}

/** Eq. 24 rating half: ln TiC_SP = Q·Φ⁻¹(PD)·√L − (Q/2)·L + ln ccm, L = ln(ccm+1). */
export function ticLognormal(pd: number, ccm: number, q: number): number {
  if (!(pd > 0 && pd < 1) || !(ccm > 0)) return NaN;
  const L = Math.log(ccm + 1);
  return Math.exp(q * normInv(pd) * Math.sqrt(L) - (q / 2) * L + Math.log(ccm));
}

/** Eq. 24 (confidence half): alpha_SP(CCM) with the 1/Q coefficient. */
export function alphaSP(ccm: number): number {
  const l = Math.log(ccm + 1);
  return normCdf((CML_LN - Math.log(ccm) / Q_SP + l / 2) / Math.sqrt(l));
}

/** Eq. 26: solve alpha_SP(CCM*) = alpha_FH(CCM) by bisection. */
export function ccmStar(ccmFH: number): number {
  const target = alphaFH(ccmFH);
  let lo = 1e-3;
  let hi = 1e4;
  for (let i = 0; i < 200; i++) {
    const mid = Math.sqrt(lo * hi);
    if (alphaSP(mid) > target) lo = mid;
    else hi = mid;
  }
  return Math.sqrt(lo * hi);
}

export function compute(inp: Inputs): Outputs {
  const d = inp.stDebt + inp.w * inp.ltDebt;
  const base: Outputs = {
    d, lnAD: null, riskScore: null, dd: null, edf: null, pitPd: null,
    mu: null, ccm: null, regime: "INVALID", letter: null, atScaleTop: false,
  };
  if (d <= 0 || inp.assetValue <= d || inp.sigma <= 0 || inp.T <= 0) return base;

  const b = Math.log(inp.assetValue / d);
  const m = inp.eta - (inp.sigma * inp.sigma) / 2; // drift
  const s = inp.sigma;
  const riskScore = (100 * s * s) / (b * b); // Eq. 12 / 5 — drift-free
  const dd = (b + m * inp.T) / (s * Math.sqrt(inp.T)); // Eq. 14
  const edf = normCdf(-dd);
  // Eq. 13: inverse-Gaussian first-hitting PD over horizon T.
  const sT = s * Math.sqrt(inp.T);
  const pit =
    normCdf(-(b + m * inp.T) / sT) +
    Math.exp(Math.max(-700, (-2 * b * m) / (s * s))) * normCdf((-b + m * inp.T) / sT);
  const pitPd = Math.min(1, Math.max(0, pit));

  if (m <= 0)
    return { ...base, lnAD: b, riskScore, dd, edf, pitPd, regime: "DEFECTIVE" };

  const mu = b / m; // Eq. 11
  const ccm = (s * s) / (b * m); // Eq. 11 (TiC identity: ccm/mu = rs/100)
  // Analytical letter (mirrors conversion.no_arb_convert): Eq. 26 matches the
  // confidence level, Eq. 27 substitutes the PIT PD and CCM* into the S&P
  // TiC formula; the published Table-8 scale grades the result.
  const cs = ccmStar(ccm);
  const rsSp = 100 * ticLognormal(pitPd, cs, Q_SP);
  let letter: string | null = null;
  let atScaleTop = false;
  if (rsSp < TABLE8[0].rs) {
    letter = TABLE8[0].letter;
    atScaleTop = true;
  } else {
    for (const g of TABLE8) if (rsSp >= g.rs) letter = g.letter;
  }
  return {
    d, lnAD: b, riskScore, dd, edf, pitPd, mu, ccm,
    regime: "VALID", letter, atScaleTop,
  };
}
