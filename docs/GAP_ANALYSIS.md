# Methodology Coverage — TiC / Market-Based Credit Rating

This document maps the credit-rating methodology (*Universal Time-Consistent (TiC) Credit
Rating* and the *Market-Based Credit Risk Rating Model for Public Companies* deck) to the
code on `main`, and records the conventions chosen where the references allowed more than
one reading.

Refreshed 2026-07-25 from a full read of every file in the repository, with each equation
re-checked against the paper rather than against the previous revision of this document.
Findings that need work are filed as GitHub issues and referenced by number below.

> **Note.** This file cites equations by number only; it does not reproduce derivations or
> the conversion lookup tables. The reference PDFs and the `TiC_TTC_conversion.xlsx`
> workbook are kept under `local/` (see `.gitignore`) and are **not** committed.

## Status vocabulary

| Status | Meaning |
|---|---|
| **correct** | Implemented, matches the reference, and a test pins it |
| **partial** | Implemented for the case we use, but narrower than the reference result |
| **missing** | Not implemented anywhere |
| **wrong** | Implemented in a way that contradicts the reference |

---

## Coverage table

| # | Concept | Reference | Implementation | Status |
|---|---|---|---|---|
| 1 | `µ = E[τ]` | Eq. (1) | `signal_construction/measures.py::compute` (first-passage closed form only) | **partial** — the Eq. (11) closed form exists; `E[τ]` as a functional of a default-time distribution does not, and no test ties the two together. #11 |
| 2 | `CCM = E[τ]·E[1/τ] − 1` | Eq. (2) | — | **missing** — only the first-passage special case (Eq. 11) exists. The definitional identity is what generalizes `CCM` beyond first passage. The previous revision of this file listed Eq. (1)–(2) as "implemented"; that was wrong. #11 |
| 3 | Default peak `λ = mode(τ)/E[τ]` | Eq. (3), (6) | `measures.py:88` — `lam = (ccm + 1.0) ** -1.5` | **partial** — the Eq. (6) inversion `CCM = λ^(−2/3) − 1` is correct and tested, but `lam` reaches **no output**: not the Asset sheet, not the master workbook, not the long table. #8 |
| 4 | `TiC = CCM/µ^Q`, `RiskScore = 100·TiC` | Eq. (4)–(5) | `measures.py:86-87` | **partial** — computed only at `Q = 1`, via the Eq. (12) identity. General `Q` is never exercised, so the agency-`Q` cases of Prop. 4.2 cannot be produced. #11 |
| 5 | First-passage `µ`, `CCM` from `σ_A`, `A₀/D`, `η` | Prop. 4.4.1, Eq. (11) | `measures.py:74-83` | **wrong** — Eq. (11) uses the **signed** drift and Prop. 4.4.1 assumes `η − σ_A²/2 > 0`. The code substitutes `abs(drift)`, silently, affecting 4 of 10 companies. **Headline finding.** #3 |
| 6 | `TiC_FH = σ_A²/ln²(A₀/D)`, `Q = 1`, Girsanov-invariant | Eq. (12), Prop. 4.4.2 | `measures.py:86`; invariance tested at `test_measures.py:49` | **partial** — Eq. (12) is correct and its η-independence is tested. Prop. 4.4.2's actual content, the empirical↔risk-neutral bridge `1/µ − 1/µ_RN = TiC·MPR` (Eq. 15), is **missing**. #11 |
| 7 | PIT PD (inverse-Gaussian first-hitting) | Eq. (13) | `measures.py::pit_pd_first_hitting`; reproduces the Tables 13–14 anchors | **partial** — correct on the tested range. For `CCM < 0.00276` the `exp(2/CCM)` term overflows and the `except OverflowError` branch drops the second term entirely, understating PD by up to 0.9pp. The comment claims log space; the code is linear space. #4, #5 |
| 8 | `DD`, `EDF = Φ(−DD)` | Eq. (14) | `measures.py:92-93` | **correct** — matches the paper, tested against hand values. Caveat: `norm.cdf(-DD)` returns exactly `0.0` for `DD ≥ 38`, and at our current maximum (`COST DD = 24.6`) reports `EDF = 6.3e-134`, a true value with no meaning as a probability. #5 |
| 9 | Capital confidence level `α(CCM)`, `CML = e^1.35`, `θ = 1` | Prop. 4.5.2 Eq. (22), Prop. 4.5.3 | `conversion.py::alpha_first_hitting`; `CML`, `SQRT_CML` at `:37-38` | **correct** — reproduces `α_FH(1.5) = 0.91906`. Only the inverse-Gaussian branch of Eq. (22) is implemented; the log-normal and log-logistic branches are not needed on the first-passage path. The `exp(2/ccm)` term here has **no** overflow guard and will raise rather than degrade. #5 |
| 10 | No-Regulatory-Arbitrage conversion `CL_B(CCM*) = CL_A(CCM_A)` | Prop. 5.2.1 Eq. (26)–(27) | `conversion.py::no_arb_ccm_star` | **partial** — Eq. (26) is implemented and reproduces `CCM* = 1.35373`. Eq. (27) (`RS_B = TiC_B(PD_A, CCM*)`) is **missing**, so the analytical route cannot emit a rating. `no_arb_ccm_star` is therefore reachable **only from tests**, while the module docstring claims it "extends past the grid edges". #6, #11 |
| 11 | S&P TiC rating formula, `Q_S&P = 0.625913` | Prop. 4.5.4 Eq. (24) | `conversion.py::alpha_sp` (confidence-level half only) | **partial** — the α half is **correct**: `(1.35 − (1/Q)·ln CCM + ln(CCM+1)/2) / √(ln(CCM+1))`, verified through the `CCM*` anchor. ⚠️ In the PDF this renders as a stacked fraction that reads like `0.625913 · ln CCM`; the coefficient is `1/0.625913`. Do not "correct" it. The rating half, `ln(TiC_SP) = Q·Φ⁻¹(PD)·√(ln(CCM+1)) − (Q/2)·ln(CCM+1) + ln(CCM)`, is **missing**. #11 |
| 12 | PIT → S&P conversion tables (`CCM = 1.5` and `5`) | Tables 13–14 | `conversion.py::load_tables`, `ttc_pd`, `sp_rating`; grids read from `local/` at runtime | **correct** — four grid anchors plus the PIT PD anchors are tested; tests skip cleanly when `local/` is absent. Caveat: off-grid inputs are edge-clamped and still produce a letter, for 5 of 10 companies. #12 |
| 13 | `Outlook` | Prop. 5.3 Eq. (28) | `conversion.py::outlook:151` — `pit_pd - ttc_pd_value` | **correct**, and note the direction. Eq. (28) reads `Outlook = PD_FH − S&P TTC`, i.e. **PIT − TTC**, which is what the code does. The previous revision of this file stated `Outlook = S&P TTC − PIT PD` in two places — wrong, corrected here. The prose above Eq. (28) reads in the opposite order and has already prompted one proposal to invert working code. **No test covers `outlook`.** #14, #13 |
| 14 | Agency `Q` values: Moody's `0.746`, S&P `0.626` | Prop. 4.2 | `conversion.py:39` — `Q_SP = 0.625913` only | **partial** — the S&P constant is present (§5.3's precise value; Prop. 4.2 quotes `0.626`). Moody's `Q = 0.746` is **not defined anywhere**, so no Moody's-side conversion and no Table 12 reproduction is possible. #11 |

### Supporting pipeline (deck, not the paper)

| Concept | Reference | Implementation | Status |
|---|---|---|---|
| Asset GBM; equity as a call on assets | Eq. (10); deck 52–68 | `signal_construction/em.py` | **correct** — σ_A recovery from synthetic data tested |
| EM: E-step bisection inverse, M-step σ_A and η_A | deck 56–68 | `em.py::estimate` | **correct** — converges within `EM_MAX_ITER = 20`; the `A > D` and `A > E` invariants raise. The bracket-expansion loop can exit without raising. #10 |
| `D = 1.0·ST + 0.5·LT` | deck 55 | `data_cleaning/transforms.py::default_point_debt` | **correct** |
| ST/LT split with fallbacks | — | `transforms.py::split_term_debt` | **partial** — the `max(Total − LT, 0)` fallback yields `ST = 0` for banks, a 36% default-point difference on PNC. Untested. #13 |
| Equity = shares × price, dividends added back | deck 61 | `data_cleaning/alignment.py` | **correct** — tested |
| Prior-quarter as-of join (no look-ahead) | deck 62 | `alignment.py`, `merge_asof(..., "backward")` | **correct** — canary tested. Aligns on `period_end`, not publication-time `available_at`; see `docs/TIMING_PROTOCOL.md` §9 |
| Submission `Asset` sheet | conversion workbook `Asset` sheet, 1 × 23 | `dashboard/submission.py` | **wrong** — omits `A`, splits `TiC Risk Score` into two columns, adds `EM iters`, renames four headers, and declares no schema constant. #7 |

---

## Resolved conventions

| Question | Decision |
|---|---|
| Risk-free rate | **1-year** (FRED `DGS1`); horizon `T = 1yr`, per the deck |
| `R_A` / asset return | The deck's **η_A**, estimated jointly in the EM M-step; `DD = [ln(A/D) + (η_A − σ_A²/2)T]/(σ_A√T)` |
| EM estimation window | Trailing **252** trading days; a year is sized at **250** days (`TRADING_DAYS_PER_YEAR`), per the deck's "about 1/250 years" |
| `Asset` sheet `R` vs `eta` | `eta = η_A`; `R = η_A − σ_A²/2`, the drift term inside DD |
| `Total Debt` column | Currently the **as-reported gross** balance-sheet row, not the default point `D`. The peer implementation puts `D` in the same column. **Open** — `docs/reconciliation/REPORT.md` §B1 |
| Long-term debt field | `Long Term Debt And Capital Lease Obligation` in preference to plain `Long Term Debt`. **Open** — `REPORT.md` §B3 |
| Shares outstanding | Market cap ÷ price ("one-day method"), deliberately, so dual-class names reconcile |
| Repo visibility | Public; proprietary material git-ignored under `local/` |
| Conversion lookup tables | `local/tables/`, git-ignored; conversion tests skip when absent |

## Conversion workbook (`local/TiC_TTC_conversion.xlsx`)

Sheets and roles (kept local; not committed):

| Sheet | Shape | Role |
|---|---|---|
| `Asset` | 1 × 23 | **Submission form** — the authoritative schema for `dashboard/submission.py` (#7) |
| `RS` | 156 × 94 | Lookup grid: (µ, CCM) → TiC (= CCM/µ) |
| `PIT` | 156 × 94 | Lookup grid: (µ, CCM) → PIT PD (Eq. 13) |
| `TTC` | 156 × 94 | Lookup grid: (µ, CCM) → TTC PD (no-arbitrage), floored at 2 bp |
| `SP` | 29 × 3 | S&P letter → PD threshold |

Axes used at runtime: **CCM ∈ [0.1, 540]** (154 points), **µ ∈ [1, 160]** (93 points).

---

## Audit findings

| Issue | Label | Title |
|---|---|---|
| [#3](https://github.com/JackyJiang08/market-based-credit-rating/issues/3) | modelling | `abs()` on negative drift violates the Prop. 4.4.1 precondition |
| [#4](https://github.com/JackyJiang08/market-based-credit-rating/issues/4) | bug | `exp(2/CCM)` overflow silently drops the second term of Eq. (13) |
| [#5](https://github.com/JackyJiang08/market-based-credit-rating/issues/5) | bug | CDF evaluated in linear space; `Φ(−DD)` underflows to exactly 0 at `DD ≥ 38` |
| [#6](https://github.com/JackyJiang08/market-based-credit-rating/issues/6) | infra | `no_arb_ccm_star` unreachable from production; module docstring overstates it |
| [#7](https://github.com/JackyJiang08/market-based-credit-rating/issues/7) | bug | Submission `Asset` sheet does not match the required schema; no schema constant |
| [#8](https://github.com/JackyJiang08/market-based-credit-rating/issues/8) | infra | Three writers emit credit measures with three different field sets |
| [#9](https://github.com/JackyJiang08/market-based-credit-rating/issues/9) | bug | Broad `except` blocks let degraded values through silently |
| [#10](https://github.com/JackyJiang08/market-based-credit-rating/issues/10) | infra | Undocumented magic numbers in the estimator and resolver |
| [#11](https://github.com/JackyJiang08/market-based-credit-rating/issues/11) | modelling | Paper results referenced in docs but never implemented |
| [#12](https://github.com/JackyJiang08/market-based-credit-rating/issues/12) | modelling | Off-grid `(CCM, µ)` is edge-clamped and reported as a rating |
| [#13](https://github.com/JackyJiang08/market-based-credit-rating/issues/13) | infra | Propositions with no regression test |
| [#14](https://github.com/JackyJiang08/market-based-credit-rating/issues/14) | documentation | This file previously stated `Outlook = TTC − PIT`, contradicting Eq. (28) |

### Test coverage against the propositions

24 tests, all offline; grid tests skip without `local/`.

| Result | Test | Status |
|---|---|---|
| Eq. (13) PIT PD | `test_pit_pd_matches_paper_tables` | ✅ Tables 13–14 anchors |
| Eq. (11) `µ`, `CCM` | `test_compute_hand_values` | ✅ |
| Eq. (12) + η-independence | `test_tic_is_eta_independent` | ✅ |
| Eq. (5) RiskScore | `test_compute_hand_values` | ✅ |
| Eq. (3)/(6) `λ` | `test_lambda_ccm_relation_matches_agency` | ✅ |
| Eq. (14) DD, EDF | `test_compute_hand_values` | ✅ |
| Eq. (22) `α_FH` | `test_alpha_first_hitting_matches_paper` | ✅ |
| Eq. (26) `CCM*` | `test_no_arb_ccm_star_matches_paper` | ✅ |
| Eq. (10) EM | `test_em_recovers_true_sigma` | ✅ |
| No-look-ahead | `tests/test_no_lookahead.py` | ✅ |
| Grid anchors, S&P thresholds, off-grid flag | `tests/test_conversion.py` | ✅ |
| **Prop. 4.4.1 negative drift** | — | ❌ #3 could be fixed or broken without a test moving |
| **Eq. (28) Outlook** | — | ❌ no test at all |
| Eq. (24) `alpha_sp` directly | — | ❌ only exercised through `CCM*` |
| Eq. (13) small-`CCM` branch | — | ❌ the #4 bug is invisible to the suite |
| Eq. (2), Eq. (15), Table 12 | — | ❌ not implemented (#11) |
| Exact `Asset` schema | `test_submission_schema` | ⚠️ subset of columns only (#7) |
| `split_term_debt` fallbacks | — | ❌ drives the PNC default point |

---

## Not covered here

- **Timing.** Point-in-time compliance is tracked in `docs/TIMING_PROTOCOL.md` §9.
- **Cross-implementation differences.** How our outputs compare with a peer implementation
  and the screenshot figures is in `docs/reconciliation/REPORT.md`.
- **Grid contents.** The conversion grids are proprietary; only their axes and the paper's
  published anchors appear in this repository.
