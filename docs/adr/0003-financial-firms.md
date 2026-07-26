# ADR 0003 — Financial firms, default-point variants, and the applicability gate

- **Status:** accepted and implemented
- **Date:** 2026-07-26
- **Closes:** #16. Relates to `docs/adr/0001`, `docs/UNCERTAINTY.md`.

## Context

The first-passage model prices equity as a call on assets struck at a **debt** barrier. That
construction assumes the barrier is debt: a fixed claim whose non-payment triggers default.

For a deposit-funded bank it is not. Deposits are a funding input, not a default trigger,
and the regulatory failure point is a capital ratio, not asset value crossing debt.

PNC makes the gap measurable:

| | Value | As % of total liabilities |
|---|---:|---:|
| Default point under the shipped rule (`ST + 0.5·LT`) | **$33.3bn** | **6.2%** |
| Total liabilities | $539.4bn | 100% |

**The model was looking at about 6% of what PNC owes** — and returning `SCALE_RESOLVED` with
an investment-grade letter. A confident-looking output on a barrier that is almost entirely
absent is worse than no output.

PNC also carries the #16 defect at its extreme. Its short-term debt is `0`, not because it
has none but because the source publishes no current-debt row and `split_term_debt` imputed
the complement. So **PNC's entire default point was a function of the long-term weight** —
which `docs/reconciliation/convention_sweep.py` confirmed: at `w = 0` its default point is
literally zero and the model cannot run.

## Decision

### 1. Surface the field provenance instead of hiding it (#16)

`pick_row_named` returns which candidate label matched. `split_term_debt` now emits four
provenance columns alongside the two debt legs:

- `ShortTermDebtSource`, `LongTermDebtSource` — the matched line item, or
  `imputed:Total-LongTerm` when the leg came from the complement
- `TotalDebtSource`
- `DebtSourceContradictory` — **true when the complement was negative**, i.e. `Total < LT`,
  meaning the source disagrees with itself

The `.clip(lower=0)` stays, because the alternative is a negative debt figure. What changes
is that it no longer hides anything: a contradictory source is now a flag rather than a
silent zero.

### 2. Default-point variants, reported side by side

`transforms.default_point_variants` returns every definition it can compute:

| Variant | Definition |
|---|---|
| `standard` | `1.0·ST + 0.5·LT` — the deck's rule |
| `total_liabilities` | all liabilities treated as the barrier |
| `total_liabilities_ex_deposits` | liabilities less deposits |

`DEFAULT_POINT_VARIANT` in `data_cleaning/config.py` selects which one the pipeline rates on;
it stays `standard`.

**A variant that cannot be computed is absent from the mapping, never silently substituted.**
The free-tier balance sheet publishes no deposits row for PNC, so
`total_liabilities_ex_deposits` is genuinely not computable there — which is itself worth
knowing, since it is the variant most likely to be *right* for a bank.

### 3. Applicability gate

`sectors.classify` resolves a firm type from a manual override map, then industry, then
sector — in that order, because "Financial Services" covers banks, insurers, asset managers
and payment processors, which do not share a balance-sheet shape.

`sectors.applicability` gates `BANK`, `INSURER`, `REIT` and negative book equity, returning a
**machine-readable reason code** (not prose, which callers cannot branch on):

| Code | Firm type |
|---|---|
| `BANK_DEPOSIT_FUNDED` | deposits dominate; failure point is a capital ratio |
| `INSURER_RESERVE_LIABILITIES` | policy reserves are contingent, not fixed claims |
| `REIT_ASSET_STRUCTURE` | appraisal-driven assets, distribution-shaped capital structure |
| `NEGATIVE_BOOK_EQUITY` | capital structure the barrier construction handles badly |

**The gate suppresses the rating, not the measures.** σ_A, A, DD, RiskScore and the drift
diagnostics are still computed and published — they are informative — but no letter is
emitted and `Rating Determination` reads `MODEL_NOT_APPLICABLE`.

A firm we cannot classify is `UNKNOWN` and is **not** gated. Silently refusing to rate a
company on a missing metadata field would be its own failure mode.

## Evidence: PNC under each variant

Against PNC's actual senior-unsecured agency rating of **A (S&P) / A2 (Moody's)**:

| Variant | D | % of liabilities | σ_A | DD | Model letter | vs agency |
|---|---:|---:|---:|---:|---|---|
| `standard` | $33.3bn | 6.2% | 0.174 | 9.31 | **AAA** | ~4 notches optimistic |
| `total_liabilities` | $539.4bn | 100% | 0.059 | 3.93 | **BB** | ~6 notches pessimistic |
| `total_liabilities_ex_deposits` | — | — | — | — | *not computable* | — |

**The convention choice spans AAA to BB — more than ten notches — and brackets the true
rating without landing on it.** Neither variant is right. That is the case for the gate: the
answer is not "pick a better default point", it is "this model does not apply to this firm,
and no choice of barrier rescues it".

## Consequences

Standing after the gate, of ten companies:

| | Before | After |
|---|---|---|
| `SCALE_RESOLVED` | 4 (DELL, ORCL, T, PNC) | **2** (ORCL, T) |
| `MODEL_NOT_APPLICABLE` | — | **2** (DELL, PNC) |
| `PINNED_AT_SCALE_TOP` | 3 | 3 |
| `PINNED_AT_FLOOR` | 1 | 1 |
| `NOT_RATED` | 2 | 2 |

Rated coverage falls from 8/10 to 6/10, and scale-resolved from 4 to 2.

### Open question: negative book equity is too blunt

**DELL is gated for `NEGATIVE_BOOK_EQUITY`, and that is probably wrong.** Dell's negative
book equity is an artifact of the post-EMC buyback programme, not distress — the same is true
of McDonald's, Starbucks and Home Depot. The model uses *market*-implied asset value, and
`A > D` holds comfortably; book equity does not enter the calculation at all.

Gating on it removes healthy companies for an accounting artifact. It was implemented as
specified, and it is flagged here rather than quietly softened, but the threshold wants
revisiting — likely replaced by a market-based test (`A > D` with a margin) or dropped
entirely in favour of the firm-type gate alone.

Note that DELL was the name with the **strongest drift t-statistic in the universe** (2.01),
so this gate removed the best-identified estimate we had.

### Also open

- `total_liabilities_ex_deposits` needs a data source that publishes deposits.
- The manual override map covers ~20 large-cap financials. It is a stopgap; a proper
  GICS/SIC feed would replace it.
- The gate is per-firm-type, not per-metric. A bank's `RiskScore` may still be comparable
  across banks even though its letter is not — untested.
