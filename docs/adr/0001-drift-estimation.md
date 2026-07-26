# ADR 0001 — Drift estimation and the Prop. 4.4.1 precondition

- **Status:** accepted
- **Date:** 2026-07-25
- **Closes:** #3 (parts a and b). Part c (`DriftRegime` propagation to outputs) is
  implemented alongside this.

## Context

Prop. 4.4.1 states its precondition explicitly — *"Assume η − σ_A²/2 > 0 and D < A₀"* — and
Eq. (11) defines both driving factors with the **signed** drift in the denominator:

```
CCM = σ_A² / (ln(A₀/D) · (η − σ_A²/2))
µ   = ln(A₀/D) / (η − σ_A²/2)
```

`measures.py` substituted `abs(η − σ_A²/2)`. Where the drift was negative this produced a
finite `µ` and `CCM` that are **not** the methodology's quantities — the first-passage time is
defective there, default occurs almost surely, and `E[τ]` diverges. Nothing on the output
said so. Four of ten companies were affected (ORCL, INTU, T, KHC).

The substitution was hiding a second problem. At a one-year estimation window the drift is
noise-dominated: the standard error of a mean log-return over a span of `y` years is
`σ_A/√y`, **independent of sampling frequency**. At `y = 1` that makes `SE(η) ≈ σ_A`, so the
estimate is the same size as its own error. ORCL at −58% and INTU at −91% were not asset
dynamics; they were noise.

## Decision

**1. Remove every `abs()` on `η − σ_A²/2`.** Eq. (11) uses the signed drift. There is no
regime in which taking the magnitude is correct.

**2. Estimate σ_A and η on different windows.** Volatility is a high-frequency quantity
recovered from the quadratic variation of the path — 252 daily observations already give a
tight estimate, and a longer span would blend distinct volatility regimes. The drift is not:
only calendar span reduces its error. `em.estimate` now takes σ_A from the trailing
`EM_WINDOW_DAYS = 252` and η from the full `DRIFT_WINDOW_DAYS = 1260` (~5y) span, inverting
the longer asset path with the converged σ_A.

**3. Classify rather than substitute.** `DriftRegime` is `VALID` or `DEFECTIVE`. In the
defective case `µ`, `CCM`, `PIT PD`, `TTC PD` and the letter rating are `NOT_APPLICABLE`,
carried as `NaN` with a visible `drift_regime` flag. `DD`, `EDF`, `TiC` and `RiskScore`
survive: Eq. (14) uses the signed drift directly and stays meaningful, and Eq. (12) is
drift-free by Prop. 4.4.2. No alternative estimator is silently swapped in.

**4. Report `drift_se` and `drift_span_years`** on every result, so a reader can see when η
is indistinguishable from zero.

## What actually blocked the 5-year window

The first attempt produced drift spans of **1.1–1.3 years**, not 5, on every company. The
cause was not the window setting. `default_point_debt()` applied `.fillna(0)` to both debt
legs, so every trading day *before the earliest statement we hold* got `D = 0` rather than
`NaN` — asserting the firm had no debt. The EM step filters on `D > 0`, so those rows were
dropped, silently truncating the estimation window to the balance-sheet history.

Three defects, all fixed here:

| Defect | Effect |
|---|---|
| `default_point_debt` filled missing debt with `0` | Fabricated "no debt" (engineering rule 2) and truncated the drift span to ~1.2y |
| `mdt/__main__.py` hard-coded `--years` default of `2` | Shadowed `DEFAULT_YEARS`; capped price history at 2y regardless of config |
| `workflow` used quarterly **or** annual statements, never both | Discarded annual periods reaching further back than the ~5–7 quarters the free tier returns |

Missing debt is now `NaN`. Backfilling it from the earliest statement was rejected: that is a
later observation, forbidden by `docs/TIMING_PROTOCOL.md` §2.

After the fixes the achieved drift spans are **2.7–4.9 years** (COST 4.9y, ORCL 2.7y), and
`SE(η)` falls from 15–52% to 7.8–33%.

## Before / after

Drift `η − σ_A²/2`. "Before" is the 252-day single-window estimator with `abs()`; "after" is
the split-window estimator without it.

| Ticker | σ_A before | σ_A after | drift before | drift after | Regime before¹ | Regime after |
|---|---:|---:|---:|---:|---|---|
| COST | 0.1899 | 0.1861 | +0.0082 | **+0.1522** | VALID (barely) | VALID |
| KO | 0.1570 | 0.1481 | +0.1694 | +0.0959 | VALID | VALID |
| DELL | 0.5667 | 0.5629 | +1.0957 | +0.6465 | VALID | VALID |
| **ORCL** | 0.5565 | 0.5447 | **−0.5822** | **+0.0854** | DEFECTIVE | **VALID** ✅ |
| PNC | 0.1656 | 0.1574 | +0.2195 | +0.1251 | VALID | VALID |
| WMT | 0.2307 | 0.2266 | +0.1316 | +0.2674 | VALID | VALID |
| **INTU** | 0.4487 | 0.4402 | **−0.9080** | **−0.0991** | DEFECTIVE | DEFECTIVE |
| AMZN | 0.3057 | 0.3057 | +0.0136 | +0.2902 | VALID | VALID |
| **T** | 0.1542 | 0.1367 | **−0.0439** | **+0.0784** | DEFECTIVE | **VALID** ✅ |
| **KHC** | 0.1705 | 0.1514 | **−0.0379** | **−0.0530** | DEFECTIVE | DEFECTIVE |

¹ "Regime before" is retrospective — the old code did not classify, it took `abs()`.

**Result: 2 of the 4 negative-drift names turn positive** (ORCL, T). Two remain defective
(INTU, KHC), and both improved by an order of magnitude — INTU from −0.908 to −0.099.

This is short of the "most of them" expectation, and the reason is visible in the numbers:
INTU's drift is −0.099 against `SE = 0.235`, and KHC's is −0.053 against `SE = 0.083`. Both
are **well inside one standard error of zero**. The longer window did not make them
positive; it made them small. They are not distinguishable from zero drift, which is
precisely why we now classify the regime and decline to rate rather than assert a sign.

An intermediate observation worth recording: on the first (broken, 1.2y-span) run COST's
drift *flipped negative* to −0.099 from +0.008. A name flipping sign on a 0.2-year change in
span is the clearest available demonstration that these one-year estimates carry no
information.

## Alternative evaluated and NOT adopted: risk-neutral drift (η = r)

Prop. 4.4.2 Eq. (15)–(16) establish that `TiC = σ_A²/ln²(A₀/D)` is invariant under the
Girsanov change of measure — it is "unchanged under either the Risk-Neutral default
probability or Empirical default probability". That invariance is what makes substituting
`η = r` superficially attractive: the TiC rating itself would not move.

**It does not survive contact with the numbers.** Setting `η = r = 0.0415`, the drift becomes
`r − σ_A²/2`, which is negative for any firm with `σ_A > √(2r) = 0.288`:

| Ticker | σ_A | `r − σ_A²/2` | Regime under η = r |
|---|---:|---:|---|
| COST | 0.1861 | +0.0242 | VALID |
| KO | 0.1481 | +0.0305 | VALID |
| **DELL** | 0.5629 | **−0.1169** | **DEFECTIVE** |
| **ORCL** | 0.5447 | **−0.1068** | **DEFECTIVE** |
| PNC | 0.1574 | +0.0291 | VALID |
| WMT | 0.2266 | +0.0158 | VALID |
| **INTU** | 0.4402 | **−0.0554** | **DEFECTIVE** |
| **AMZN** | 0.3057 | **−0.0052** | **DEFECTIVE** |
| T | 0.1367 | +0.0322 | VALID |
| KHC | 0.1514 | +0.0300 | VALID |

The limit is exactly as anticipated: **when `σ_A²/2 > r` the risk-neutral substitution does
not rescue the sign either.** ORCL is the stated example — `σ_A²/2 = 0.148` against
`r = 0.0415` — and it stays defective. Worse, the substitution would make **four** names
defective where the empirical estimator now makes two, newly breaking DELL and AMZN, both of
which have solidly positive, well-estimated empirical drifts (+0.65 and +0.29 against SEs of
0.33 and 0.17).

There is also a conceptual objection. `µ = E[τ]` is a **real-world** life expectancy. Under
the risk-neutral measure `E[τ]` is not the expected time to default; it is a
discounting-consistent artefact. TiC's Girsanov invariance says the *rating* is measure-free,
not that `µ` and `CCM` individually are — Eq. (15) says the opposite, giving explicit
non-zero differences `1/µ − 1/µ_RN = TiC·MPR` and `1/CCM − 1/CCM_RN = MPR/TiC`.

**Not adopted.** Recorded here so the option is not re-proposed without the counter-example.

## Consequences

- Two companies (INTU, KHC) now report `NOT_APPLICABLE` instead of a fabricated rating. This
  is a visible reduction in coverage and an increase in honesty.
- Ratings moved materially for names whose drift was previously wrong: DELL `BBB → A-`,
  and ORCL is now rated on a valid drift for the first time.
- `DEFAULT_YEARS` rises from 2 to 6, so each run downloads more history. Batch runtime is
  unchanged in practice (~2s per company).
- The `D = NaN` change means a company with no statement history now yields no panel rows
  rather than a panel asserting zero debt. That is the intended failure mode.

## Open

- INTU and KHC are defective by a margin smaller than one standard error. A longer span than
  the free-tier statement history allows would likely resolve them; that needs a data source
  with deeper balance-sheet history, not a code change.
- `drift_se` is reported but nothing consumes it. A natural next step is to widen
  `DEFECTIVE` to "not significantly positive" (e.g. `drift < 0` **or** `|drift| < drift_se`),
  which on today's numbers would also catch COST's earlier +0.008. Deferred: it changes the
  rated universe and is the owner's call.
