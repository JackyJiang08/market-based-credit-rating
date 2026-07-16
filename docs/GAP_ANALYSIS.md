# Gap Analysis — Branch vs. TiC / Market-Based Credit Rating Methodology

**Phase 0 audit.** This document maps the credit-rating methodology (Yimin Yang,
*Universal Time-Consistent (TiC) Credit Rating*, and the PFPA *Market-Based
Credit Risk Rating Model for Public Companies* deck) to the current code on
branch `agent/unify-four-layer-architecture`, and records status per concept.

> **IP notice.** The TiC / market-based methodology is the instructor's
> intellectual property. This file cites equations by number only; it does not
> reproduce the proprietary derivations or the conversion lookup tables. The
> source PDFs and the `TiC_TTC_conversion.xlsx` workbook are kept local (see
> `.gitignore`) and are **not** committed. This code is for coursework and
> portfolio demonstration only and must not be presented to third parties
> (e.g., banks) as our own work.

## Resolved conventions (confirmed with project owner)

| Question | Decision |
| --- | --- |
| Risk-free rate | **1-year** (FRED `DGS1`); horizon `T = 1yr`. Matches the deck ("Risk-free interest rate (1 year)") and existing code. Overrides the 3M T-bill wording in the task prompt. |
| `R_A` / asset return | Use the deck's **η_A** ("Asset Return"), estimated jointly in the EM M-step; `DD = [ln(A/D) + (η_A − σ_A²/2)] / σ_A`. |
| EM estimation window | Trailing **~252 trading days** (1 year daily), per the deck's "recent 1 year". |
| Repo visibility / IP | Repo stays public; **instructor IP is git-ignored** (PDFs, xlsx, derived tables kept in `local/`). |
| `Asset` sheet `R` vs `eta` columns | `eta = eta_A` (EM asset return); `R = eta_A - sigma_A^2/2` (the realized drift term inside DD). This reconciles the deck's DD with the prompt's `DD=[ln(A/D)+R]/sigma`. **Pending instructor confirmation** vs the prompt's alternative `R=(A_hat-1)/sigma^2`. |
| Trading days per year | **250** (deck: "each day is about 1/250 years"), not 252. |

## Canonical pipeline (deck slides 52–69, paper §4.4)

1. Asset GBM `A_t = A₀·exp((η_A − σ_A²/2)t + σ_A W_t)`; equity = call on assets,
   strike `D` (function `g`).
2. Inputs: `D = short-term debt + 0.5·long-term debt`; `Equity = Price × Shares`
   with dividends added back; risk-free = 1-year; per-day `τ = 1/250`; each
   trading day uses its **prior-quarter** balance sheet and rate (as-of).
3. **EM:** E-step inverts `g` (bisection) → asset `A` given `σ_A`; M-step
   recomputes `σ_A` from asset log-returns; **η_A estimated simultaneously**;
   iterate. Outputs: `σ_A`, `A`, `η_A`.
4. `DD = [ln(A/D) + (η_A − σ_A²/2)] / σ_A`; `EDF = Φ(−DD)`.
5. `TiC = σ_A²/ln²(A/D)` (Eq. 12, Q=1); `RiskScore = 100·TiC`; `μ`, `CCM`
   (Eq. 11); **PIT PD** via inverse-Gaussian first-hitting (Eq. 13);
   **TTC PD → S&P letter** via the conversion grids; `Outlook = S&P TTC − PIT PD`.

## Gap table

| Concept | Paper/deck ref | Repo location | Status |
| --- | --- | --- | --- |
| μ = E[τ] | Eq. (1) | — | **missing** |
| CCM = E[τ]·E[1/τ] − 1 | Eq. (2) | — | **missing** |
| Default peak λ = mode(τ)/E[τ] | Eq. (3) | — | **missing** |
| TiC = CCM/μ^Q, RiskScore = 100·TiC | Eq. (4)–(5) | `signal_construction/credit.py::TICModel` is a `NotImplementedError` stub | **missing** |
| First-passage μ, CCM | Eq. (11) | — | **missing** |
| TiC (first-passage, Q=1) = σ_A²/ln²(A/D) | Eq. (12) | — | **missing** |
| PIT PD (inverse-Gaussian first-hitting) | Eq. (13) | `credit.py` computes `Φ(−DD)` (an EDF), not Eq. 13 | **incorrect** |
| DD, EDF = Φ(−DD) | Eq. (14) | `MertonKMVModel` uses **risk-neutral r** as drift, not η_A | **differs** |
| EM: joint σ_A **and** η_A via g-inverse (bisection) | deck 56–68 | `MertonKMVModel` iterates σ only; **no η_A**, no bisection-g, no per-day τ | **partial/incorrect** |
| D = ST + 0.5·LT | deck 55 | `data_cleaning/transforms.py::default_point_debt` | implemented |
| Equity = Price × Shares (constant, one-day method) | deck 61 | `alignment.build_panel` (`MarketCap_E`) | implemented |
| Dividends added back to equity return | deck 61 | AdjClose used for return, but raw close for E; **not per deck's add-back** | partial |
| Prior-quarter as-of join (no look-ahead) | deck 62 | `alignment.build_panel` `merge_asof(..., "backward")` | implemented |
| Capital confidence α(CCM), CML=e^1.35, θ=1 | Eq. (22), Prop. 4.5.3 | — | missing |
| No-Reg-Arbitrage conversion (match α → CCM*) | Prop. 5.2.1–5.2.2 | — | missing |
| PIT → TTC → S&P mapping (grids) | §5.3, Tables 13–14 | conversion `xlsx` not integrated | missing |
| Outlook = S&P TTC − PIT PD | Prop. 5.3 | — | missing |
| Submission workbook (Asset sheet schema) | conversion xlsx | — | missing |

## Conversion workbook (`local/TiC_TTC_conversion.xlsx`)

Sheets and roles (kept local; not committed):

| Sheet | Shape | Role |
| --- | --- | --- |
| `Asset` | 1 × 23 | **Submission form**: Symbol, Shares, Last Price/Date, statement date, ST/LT/Total Debt, Interest Rate, σ_A, R, η, CCM, µ, TiC, RiskScore, DD, EDF, PIT PD, TTC PD, SP Rating, Outlook |
| `RS` | 156 × 94 | Lookup grid: rows µ × cols CCM → TiC (= CCM/µ) |
| `PIT` | 156 × 94 | Lookup grid: (µ, CCM) → PIT PD (Eq. 13) |
| `TTC` | 156 × 94 | Lookup grid: (µ, CCM) → TTC PD (no-arb), floored at 2 bp |
| `SP` | 29 × 3 | S&P letter → PD threshold ("if PD < next threshold") |

The repo does **not** currently reproduce any of this lookup logic.

## Assessment & plan

The branch provides a sound **data + baseline-Merton** foundation (Layers 1–2
solid; debt rule, as-of alignment, constant-share equity all correct). The
**entire TiC / EM / PIT→TTC rating layer is missing or differs** from the
instructor's method and is the substance of the remaining work.

No blocking architectural conflict prevents proceeding: the missing pieces slot
cleanly into `signal_construction` (Layer 3) behind the existing `CreditModel`
interface, feeding the `dashboard` (Layer 4) submission workbook. Planned order:

1. **Phase 1** — complete the data layer (dividend add-back, name→ticker,
   per-company `data/{TICKER}/` csv+xlsx, no-look-ahead canary test).
2. **Phase 2** — EM (joint σ_A, η_A via bisection g-inverse) with sanity checks.
3. **Phase 3** — RiskScore/CCM/µ/λ/DD/EDF/PIT-PD (Eq. 11–14).
4. **Phase 4** — PIT→TTC→S&P via local lookup tables + no-arb conversion; reproduce Tables 12–14 as regression tests.
5. **Phase 5** — batch run for the 10 companies → timestamped submission workbook.
6. **Phase 6** — one-click CLI + docs.

**Deviation flagged:** the task prompt asked for the conversion lookup tables to
be versioned under `src/.../tables/`. Per the IP decision they are kept in
`local/tables/` and git-ignored instead.
