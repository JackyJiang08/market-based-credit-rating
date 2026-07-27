/** The one place machine enums become human labels.
 *
 * No SCREAMING_SNAKE reaches the UI: every rendered chip/badge uses `label`,
 * the tooltip carries `definition` plus the machine constant (kept verbatim
 * for grep-ability against the pipeline code and the workbook).
 *
 * Colour system (never colour alone — every chip also carries its label and
 * tone-specific shape/weight): green = resolved · grey = pinned · amber =
 * weak/estimation caveat · red = gated/not applicable.
 */

export type Tone = "green" | "grey" | "amber" | "red";

export interface EnumLabel {
  label: string;
  tone: Tone;
  definition: string;
}

export const ENUM_LABELS: Record<string, EnumLabel> = {
  // --- determinations -------------------------------------------------------
  SCALE_RESOLVED: {
    label: "Scale resolved",
    tone: "green",
    definition:
      "The rating scale could tell this value from its neighbours. A statement " +
      "about the scale's resolution, not about estimation precision.",
  },
  PINNED_AT_SCALE_TOP: {
    label: "Pinned · scale top",
    tone: "grey",
    definition:
      "RiskScore sits below the best published grade, so the letter is the " +
      "scale's ceiling, not a measurement.",
  },
  PINNED_AT_FLOOR: {
    label: "Pinned · floor",
    tone: "grey",
    definition:
      "TTC PD sits at the conversion grid's smallest expressible value (2bp); " +
      "the letter is floor-determined.",
  },
  NOT_RATED: {
    label: "Not rated",
    tone: "amber",
    definition:
      "No letter was produced: the drift regime is defective (η − σ²/2 ≤ 0, " +
      "Prop. 4.4.1), so the first-passage PD chain is undefined.",
  },
  MODEL_NOT_APPLICABLE: {
    label: "Not applicable",
    tone: "red",
    definition:
      "An applicability gate fired: the structural model does not describe " +
      "this firm. Measures may still be reported; the letter is not.",
  },
  // --- applicability reason codes -------------------------------------------
  BANK_DEPOSIT_FUNDED: {
    label: "Bank (deposit-funded)",
    tone: "red",
    definition:
      "Deposits dominate the liability side and are not a default barrier; " +
      "the failure point is a capital ratio.",
  },
  INSURER_RESERVE_LIABILITIES: {
    label: "Insurer (reserves)",
    tone: "red",
    definition: "Policy reserves are contingent liabilities, not fixed claims.",
  },
  REIT_ASSET_STRUCTURE: {
    label: "REIT structure",
    tone: "red",
    definition:
      "Appraisal-driven assets and distribution-shaped capital structure.",
  },
  ASSETS_BELOW_TOTAL_DEBT: {
    label: "Assets below total debt",
    tone: "red",
    definition:
      "Market-implied assets do not clear the most conservative barrier " +
      "(ST + 1.0·LT); the letter would measure the debt-weight convention, " +
      "not the firm.",
  },
  REPORTING_CURRENCY_MISMATCH: {
    label: "Foreign reporting currency",
    tone: "red",
    definition:
      "Statements report in a different currency than the listed price; " +
      "equity and debt would enter the model in different units.",
  },
  // --- flags ------------------------------------------------------------------
  WEAKLY_IDENTIFIED: {
    label: "Weak drift",
    tone: "amber",
    definition:
      "|drift t| < 2 — µ and CCM divide by a drift statistically " +
      "indistinguishable from zero. Read the interval, not the point letter.",
  },
  DEFECTIVE_DRIFT: {
    label: "Defective drift",
    tone: "amber",
    definition: "η − σ²/2 ≤ 0 (Prop. 4.4.1): the PD chain is undefined.",
  },
  AT_FLOOR: {
    label: "At floor",
    tone: "grey",
    definition: "TTC PD at the grid's smallest value; floor-determined letter.",
  },
  AT_SCALE_TOP: {
    label: "At scale top",
    tone: "grey",
    definition: "RiskScore below the best published grade.",
  },
  OFF_GRID_CLAMPED: {
    label: "Off grid",
    tone: "amber",
    definition: "(CCM, µ) outside the lookup grid; edge-clamped and flagged.",
  },
  // --- rating bases ------------------------------------------------------------
  GRID_INTERIOR: {
    label: "Grid lookup",
    tone: "green",
    definition:
      "TTC PD interpolated inside the conversion grid — the authoritative route.",
  },
  ANALYTICAL: {
    label: "Analytical",
    tone: "green",
    definition:
      "No-arbitrage conversion (Eq. 26/27); used where the grid does not cover.",
  },
  OFF_GRID: {
    label: "Off grid",
    tone: "amber",
    definition: "Outside the grid with no analytical route; no letter reported.",
  },
  NOT_APPLICABLE: {
    label: "Not applicable",
    tone: "red",
    definition: "Defective drift regime: (CCM, µ) do not exist.",
  },
};

export function enumLabel(code: string | null | undefined): EnumLabel & { code: string } {
  const c = code ?? "";
  const hit = ENUM_LABELS[c];
  if (hit) return { ...hit, code: c };
  // Unknown code: humanize mechanically but keep the constant visible.
  return {
    code: c,
    label: c ? c.replaceAll("_", " ").toLowerCase() : "—",
    tone: "grey",
    definition: c ? `Machine code: ${c}` : "",
  };
}

export const TONE_CLASSES: Record<Tone, string> = {
  green: "border-emerald-500/50 bg-emerald-500/10 text-emerald-300",
  grey: "border-zinc-600 bg-zinc-800/70 text-zinc-300",
  amber: "border-amber-500/50 bg-amber-500/10 text-amber-300",
  red: "border-rose-500/50 bg-rose-500/10 text-rose-300",
};
