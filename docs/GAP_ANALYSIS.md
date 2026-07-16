# Methodology Coverage — TiC / Market-Based Credit Rating

This document maps the credit-rating methodology (*Universal Time-Consistent
(TiC) Credit Rating* and the *Market-Based Credit Risk Rating Model for Public
Companies* deck) to the code on `main`, and records the conventions chosen
where the references allowed more than one reading.

It began as a pre-implementation gap audit; the status column below reflects
the code after the four-layer pipeline was merged. Everything is covered by the
offline test suite (`pytest`).

> **Note.** This file cites equations by number only; it does not reproduce the
> derivations or the conversion lookup tables. The reference PDFs and the
> `TiC_TTC_conversion.xlsx` workbook are kept under `local/` (see `.gitignore`)
> and are **not** committed.

## Resolved conventions

| Question | Decision |
| --- | --- |
| Risk-free rate | **1-year** (FRED `DGS1`); horizon `T = 1yr`. Matches the deck ("Risk-free interest rate (1 year)") and existing code. |
| `R_A` / asset return | Use the deck's **η_A** ("Asset Return"), estimated jointly in the EM M-step; `DD = [ln(A/D) + (η_A − σ_A²/2)] / σ_A`. |
| EM estimation window | Trailing **~252 trading days** (1 year daily), per the deck's "recent 1 year". |
| Repo visibility | Repo stays public; **proprietary material is git-ignored** (PDFs, xlsx, derived tables kept in `local/`). |
| `Asset` sheet `R` vs `eta` columns | `eta = eta_A` (EM asset return); `R = eta_A - sigma_A^2/2` (the realized drift term inside DD). This reconciles the deck's DD with the alternative `DD=[ln(A/D)+R]/sigma`. **Pending confirmation** vs the alternative `R=(A_hat-1)/sigma^2`. |
| Trading days per year | **250** (deck: "each day is about 1/250 years"), not 252. |
| Conversion lookup tables | Kept in `local/tables/` and git-ignored (not versioned in-repo); conversion tests skip when absent. |

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

## Coverage table

| Concept | Paper/deck ref | Implementation | Status |
| --- | --- | --- | --- |
| μ = E[τ], CCM = E[τ]·E[1/τ] − 1 | Eq. (1)–(2), (11) | `signal_construction/measures.py` | implemented |
| Default peak λ | Eq. (3) | `signal_construction/measures.py` | implemented |
| TiC = CCM/μ^Q, RiskScore = 100·TiC | Eq. (4)–(5), (12) | `signal_construction/measures.py` | implemented |
| PIT PD (inverse-Gaussian first-hitting) | Eq. (13) | `signal_construction/measures.py`; reproduces the paper's Tables 13–14 | implemented |
| DD, EDF = Φ(−DD), drift η_A | Eq. (14) | `signal_construction/measures.py` | implemented |
| EM: joint σ_A **and** η_A via g-inverse (bisection), per-day τ | deck 56–68 | `signal_construction/em.py`; recovery of a known σ_A tested | implemented |
| D = ST + 0.5·LT | deck 55 | `data_cleaning/transforms.py::default_point_debt` | implemented |
| Equity = Price × Shares (constant, one-day method) | deck 61 | `data_cleaning/alignment.py` (`MarketCap_E`) | implemented |
| Dividends added back to equity | deck 61 | `data_cleaning/alignment.py` | implemented |
| Prior-quarter as-of join (no look-ahead) | deck 62 | `data_cleaning/alignment.py` `merge_asof(..., "backward")`; canary test | implemented |
| No-reg-arbitrage conversion (match α → CCM*) | Prop. 5.2.1–5.2.2 | `signal_construction/conversion.py`; `alpha_FH(1.5)=0.91906`, `CCM*=1.35373` verified | implemented |
| PIT → TTC → S&P mapping (lookup grids) | §5.3, Tables 13–14 | `signal_construction/conversion.py` (grids read from `local/`; skipped gracefully when absent) | implemented |
| Outlook = S&P TTC − PIT PD | Prop. 5.3 | `signal_construction/conversion.py` | implemented |
| Submission workbook (`Asset` sheet schema) | conversion xlsx | `dashboard/submission.py` (+ `validation` sheet) | implemented |

Open item: the `Asset` sheet `R` column definition (see the convention above) is
pending confirmation; the current choice is the realized drift `η_A − σ_A²/2`.

## Conversion workbook (`local/TiC_TTC_conversion.xlsx`)

Sheets and roles (kept local; not committed):

| Sheet | Shape | Role |
| --- | --- | --- |
| `Asset` | 1 × 23 | **Submission form**: Symbol, Shares, Last Price/Date, statement date, ST/LT/Total Debt, Interest Rate, σ_A, R, η, CCM, µ, TiC, RiskScore, DD, EDF, PIT PD, TTC PD, SP Rating, Outlook |
| `RS` | 156 × 94 | Lookup grid: rows µ × cols CCM → TiC (= CCM/µ) |
| `PIT` | 156 × 94 | Lookup grid: (µ, CCM) → PIT PD (Eq. 13) |
| `TTC` | 156 × 94 | Lookup grid: (µ, CCM) → TTC PD (no-arb), floored at 2 bp |
| `SP` | 29 × 3 | S&P letter → PD threshold ("if PD < next threshold") |
