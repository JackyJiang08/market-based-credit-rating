# Deliverable archive — what changed between the frozen versions

| File | Role |
|---|---|
| `submission_20260725_234922.xlsx` | **Pre-look-ahead version.** Generated 2026-07-25 23:49 (naive local time, pre-standard), from the code *before* the `available_at` alignment fix (`03a0bf8`). Identified by content match against `docs/reconciliation/history/07_after_15_totalreturn.csv`. |
| `submission_20260726T071503Z.xlsx` | **Deliverable v1.** Generated from freeze commit `0eda3ce` (clean tree — the code the `deliverable-v1` tag ships) under the team timestamp standard (UTC, `docs/TIMING_PROTOCOL.md` §10). Standing matches `history/14`. |

Both runs price through the **2026-07-24 close** — the same trading history — so every
difference below is a code or convention change, not a data change. Sub-0.5% drifts in
σ/DD for non-highlighted names are vendor-side revisions of the same history.

## Structural changes

- **Sheets 2 → 4.** The pre version has `Asset` + `validation` only. v1 adds `README`
  (provenance: model version, git SHA, data vintage; every convention in force with its
  sweep range; how to read the flags; the canonical-columns deviation note) and `Ratings`
  (the presentation rule: sorted by RiskScore, letter only with its interval attached).
- **Asset sheet 25 → 35 columns.** The canonical 23 + `lambda` + `Rating Basis` are
  unchanged and in the same order. v1 appends: `Rating Determination`, `Firm Type`,
  `Model Applicable`, `Applicability Reason`, `Drift SE`, `Drift t`, `Weakly Identified`,
  `Rating Interval Low/High/Notches`.
- **Validation sheet** extended with drift regime/t, bootstrap rating interval,
  convention span (2026-07-26 sweep), `TTC at floor` / `At scale top` flags, EM
  iterations, and debt field provenance.
- **Timestamps.** Pre: naive local `%Y%m%d_%H%M%S`. v1: tz-aware UTC `%Y%m%dT%H%M%SZ`.

## Per-company changes

| | σ_A pre → v1 | Rating pre → v1 | Why |
|---|---|---|---|
| **T** | 0.165 → **0.192** | **AA → A+** | **The look-ahead fix, visible.** The pre version valued T against the 2026-06-30 statement — which had not been filed on the valuation date. v1 joins on `available_at` and correctly sees 2026-03-31. RiskScore 2.43 → 3.09, DD 7.03 → 6.19. |
| **PNC** | 0.174 → 0.166 | **AA+ → no letter** | `MODEL_NOT_APPLICABLE (BANK_DEPOSIT_FUNDED)`, ADR 0003: the standard barrier is 6% of what PNC owes; conventions span AAA→BB around an actual A/A2. Measures still reported. |
| **DELL** | 0.578 → 0.579 | A− → A− | Same letter, honestly framed: `SCALE_RESOLVED`, drift t = 2.01, interval AAA..BBB (10 notches). DELL was briefly gated for negative book equity; that spec was revised (ADR 0003, rev 1) — the market-based test `A > ST + 1.0·LT` passes it with A ≈ $301bn vs ≈ $31bn. |
| COST / KO / WMT | unchanged | AAA → AAA | Now labelled `PINNED_AT_SCALE_TOP`, span 1 under every debt weight — a pinned letter carries no information. |
| AMZN | 0.306 → 0.305 | AAA− → AAA− | Now labelled `PINNED_AT_FLOOR` (TTC PD at the grid's 2bp floor). |
| INTU / KHC | unchanged | not rated → `NOT_RATED` | Defective drift regime (Prop. 4.4.1), now stated as a determination class rather than a blank cell. |
| ORCL | 0.566 → 0.569 | BB → BB | Now carries its honest framing: weakly identified (t = 0.08), interval BBB−..BB−, unrateable in ~39% of replicates, convention span 5. |

## What v1 knows that the pre version could not say

The pre version printed a bare letter per company. v1 attaches, for every letter: the
**bootstrap interval** (parameter uncertainty — a lower bound), the **convention span**
(the debt-weight sweep — for ORCL, PNC and T it equals or exceeds the bootstrap span),
the **determination class** (whether the scale resolved the value at all), the
**drift t** (whether the estimate is identified), and the **applicability gates**
(whether the model should be speaking). The presentation rule follows: RiskScore first,
letter never bare. See `docs/UNCERTAINTY.md` and the README results section.
