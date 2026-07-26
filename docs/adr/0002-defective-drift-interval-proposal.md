# ADR 0002 — Rating interval for a defective drift regime (PROPOSAL)

- **Status:** proposed, not implemented
- **Date:** 2026-07-25
- **Relates to:** #3, `docs/adr/0001-drift-estimation.md`

## Question

INTU and KHC report `NOT_APPLICABLE` because their drift is negative, so Prop. 4.4.1's
precondition fails and `µ = E[τ]` diverges. Both drifts sit inside one standard error of
zero. A point estimate is unsupportable — but is a **bounded** one?

The proposal: report the rating interval implied by `η ∈ [η̂ − SE, η̂ + SE]`, labelled a range
rather than a rating, retaining `NOT_APPLICABLE` whenever the interval spans the defective
boundary.

## What the two companies would actually look like

Computed against the current run (drift span 3.3–3.5y).

### INTU — σ_A = 0.4402, η̂ = −0.0022, SE = 0.2351, span 3.5y

| Bound | η | drift `η − σ²/2` | Regime | µ | CCM | TTC PD | Rating |
|---|---:|---:|---|---:|---:|---:|---|
| η̂ − 1·SE | −0.2374 | −0.3343 | DEFECTIVE | — | — | — | NOT_APPLICABLE |
| η̂ | −0.0022 | −0.0991 | DEFECTIVE | — | — | — | NOT_APPLICABLE |
| η̂ + 1·SE | +0.2329 | **+0.1360** | VALID | 23.18 | 0.4518 | 0.000234 | **AAA-** |

Interval on the drift: **[−0.3343, +0.1360] — spans the boundary.**

### KHC — σ_A = 0.1514, η̂ = −0.0416, SE = 0.0830, span 3.3y

| Bound | η | drift `η − σ²/2` | Regime | µ | CCM | TTC PD | Rating |
|---|---:|---:|---|---:|---:|---:|---|
| η̂ − 1·SE | −0.1246 | −0.1361 | DEFECTIVE | — | — | — | NOT_APPLICABLE |
| η̂ | −0.0416 | −0.0530 | DEFECTIVE | — | — | — | NOT_APPLICABLE |
| η̂ + 1·SE | +0.0414 | **+0.0300** | VALID | 50.82 | 0.5016 | 0.000200 | **AAA-** |

Interval on the drift: **[−0.1361, +0.0300] — spans the boundary.**

## Finding

**Under the proposed rule, both companies retain `NOT_APPLICABLE`.** Both intervals straddle
zero drift, which is the stated retention condition. The proposal, applied as specified,
un-blanks nothing in the current universe.

That is not an argument against the rule — it is the rule working. The more informative
result is *how wide* the interval is. For both names it runs from "the first-passage time is
defective and the firm cannot be rated at all" to **AAA-**, the top of the scale. That is not
a range a reader can act on; it is a statement that the drift estimate carries no
information, which is exactly what `SE > |η̂|` already says more compactly.

## Assessment

**Against implementing it as specified:**

1. It changes nothing today. Both names still blank, at the cost of a new output concept.
2. The interval it would produce elsewhere spans ~20 notches. A "range" that wide invites
   readers to anchor on its favourable end.
3. `η̂ ± 1·SE` is a 68% interval. Nothing in the methodology text motivates one standard error, and the
   choice silently sets how often a company is rated.
4. It measures only drift uncertainty. σ_A, the default point `D`, and the reference share
   count all carry their own error and would remain point estimates, so the interval would
   understate total uncertainty while looking rigorous.

**For a narrower version:**

The useful signal here is not the interval — it is `SE`, which the pipeline already computes
and publishes on the validation sheet but nothing consumes. A cheaper change with most of
the value: widen `DEFECTIVE` from `drift ≤ 0` to **"not significantly positive"**, i.e.
`drift ≤ 0` **or** `drift < k·SE`. That is a one-line change to `drift_regime()`, needs no new
output concept, and makes the honesty explicit rather than implied.

On today's numbers with `k = 1` it would additionally suppress any company whose drift is
inside one SE of zero. It is worth checking which of the eight currently-rated names that
catches before adopting it — several have `SE` of the same order as their drift.

## Recommendation

Do **not** implement the interval as specified. Instead:

1. Adopt the significance test in `drift_regime()` (`k` configurable, default 1), and report
   which companies it removes before turning it on.
2. Publish `drift_se` and `drift_span_years` on the **Asset** sheet, not only on validation,
   so the uncertainty travels with the rating.
3. Revisit intervals only if uncertainty is propagated through σ_A and `D` as well, at which
   point the honest artifact is a distribution over ratings, not a two-point range.

Awaiting a decision. Nothing in this ADR is implemented.

---

# Addendum — 2026-07-25: the k·SE rule measured against real numbers

The recommendation above (a significance test instead of an interval) has now been
evaluated on the current run. **Still not implemented — this is the table to decide from.**

`t = drift / SE`. A company is DEFECTIVE under the rule when `drift ≤ k·SE`.

| Ticker | drift | SE | t | Today | k = 1 | k = 1.645 | Rating | Determination |
|---|---:|---:|---:|---|---|---|---|---|
| COST | +0.1243 | 0.0904 | 1.37 | VALID | VALID | **DEFECTIVE** | AAA | scale-top |
| KO | +0.1180 | 0.0949 | 1.24 | VALID | VALID | **DEFECTIVE** | AAA | scale-top |
| DELL | +0.7048 | 0.3490 | **2.02** | VALID | VALID | VALID | A- | model |
| ORCL | +0.0309 | 0.3661 | **0.08** | VALID | **DEFECTIVE** | **DEFECTIVE** | BB | model |
| PNC | +0.1961 | 0.0948 | **2.07** | VALID | VALID | VALID | AAA- | model |
| WMT | +0.2843 | 0.1417 | 2.01 | VALID | VALID | VALID | AAA | scale-top |
| INTU | −0.1005 | 0.2555 | −0.39 | DEFECTIVE | DEFECTIVE | DEFECTIVE | — | not rated |
| AMZN | +0.2574 | 0.1738 | 1.48 | VALID | VALID | **DEFECTIVE** | AAA- | floor |
| T | +0.0952 | 0.1140 | **0.84** | VALID | **DEFECTIVE** | **DEFECTIVE** | A+ | model |
| KHC | −0.0516 | 0.1081 | −0.48 | DEFECTIVE | DEFECTIVE | DEFECTIVE | — | not rated |

## Impact

| | Rated | Model-determined |
|---|---:|---:|
| Today | 8 / 10 | 4 |
| k = 1 | **6 / 10** (−ORCL, −T) | **2** (DELL, PNC) |
| k = 1.645 | **3 / 10** (−ORCL, −T, −COST, −KO, −AMZN) | **2** (DELL, PNC) |

## Reading it

**ORCL is the case that decides this.** Its `t = 0.08` — the drift is eight percent of one
standard error, i.e. indistinguishable from zero by any standard. It is also our **only
sub-investment-grade rating** and one of only four model-determined ones. A BB call resting
on a drift that cannot be distinguished from zero is precisely the class of
confident-but-unsupported output this audit has spent its time removing.

T is the same problem less starkly (`t = 0.84`).

The two that survive at either `k` are the two with real signal: DELL `t = 2.02` and PNC
`t = 2.07`.

`k = 1.645` (a one-sided 95% test) costs three more names — COST, KO and AMZN — but all
three are pinned at a scale edge anyway, so removing them subtracts presentation without
subtracting information. It does not improve model-determined coverage over `k = 1`.

## Recommendation

**Adopt `k = 1`.** It removes exactly the two ratings that cannot support their own drift
and keeps the two that can. It halves model-determined coverage from 4 to 2, which is the
real cost and should be stated plainly rather than absorbed quietly — but a coverage number
that counts ORCL's BB is not measuring what it claims to.

Make `k` configurable and record it in the run manifest, so the threshold is a documented
choice rather than a constant.

**Not switched on.** Awaiting a decision on the coverage trade-off.

---

# Decision — 2026-07-26: no fixed `k`; annotate instead of suppress

**Status: accepted and implemented.** A fixed `k·SE` threshold on `DEFECTIVE` was
considered and **rejected**. Recording why, because the addendum above recommended it.

## Why a fixed `k` was rejected

The impact table showed `k = 1` removing only ORCL, and `k = 1.645` additionally removing
COST, KO and AMZN. Those three are `PINNED_AT_SCALE_TOP` or `PINNED_AT_FLOOR` — their
letters are set by the edge of a scale, so losing them costs nothing informative. Stripping
that away, **the parameter's entire practical effect is to decide the fate of ORCL**, the
one result anybody cares about: our only sub-investment-grade rating.

A parameter whose visible range only ever toggles a single company is not a threshold, it is
a switch with a number written on it. Choosing `k` would have been choosing ORCL's fate
while appearing to apply a general rule.

It also conflates two different failures:

- **`drift ≤ 0`** is an *assumption violation*. Prop. 4.4.1 requires the drift positive; when
  it is not, `µ = E[τ]` diverges and Eq. (11) has no value. There is nothing to report.
- **`|t| < 2`** is a *precision* problem. `µ` and `CCM` exist, but they divide by a quantity
  the data cannot pin down. There is something to report — with a warning attached.

Suppressing the second because it resembles the first discards information and hides the
uncertainty behind a blank cell.

## What was implemented instead

1. **`DEFECTIVE` keeps its original meaning**: `drift ≤ 0`, the genuine assumption failure.
   `signal_construction/measures.py::drift_regime` is unchanged.
2. **`WEAKLY_IDENTIFIED`** (`measures.is_weakly_identified`, `|t| < 2.0`) **annotates** a
   rating and never suppresses one. It travels into the workbook as a `Weakly Identified`
   column on the Asset sheet, a warning on the validation sheet, and a log line — so it
   reaches the API and the UI by construction rather than needing to be re-derived.
3. **`t` and a bootstrap rating interval are published alongside every rating**
   (`Drift SE`, `Drift t`, `Rating Interval Low/High/Notches`), so a reader sees the
   precision without having to ask for it.

## Standing, 2026-07-26

**7 of 10 companies carry `WEAKLY_IDENTIFIED`.** Only DELL (`t = 2.01`), PNC (`t = 2.07`)
and WMT (`t = 2.01`) clear it — and all three sit within 0.1 of the threshold, which is
itself a reason not to have made the threshold load-bearing for suppression.

| Ticker | t | Weak | Determination | Bootstrap interval | Notches | Defective in |
|---|---:|---|---|---|---:|---:|
| COST | 1.37 | **yes** | scale-top | AAA..AAA- | 2 | 11.8% |
| KO | 1.24 | **yes** | scale-top | AAA..AAA- | 2 | 7.4% |
| DELL | 2.01 | no | **model** | AAA..A- | **8** | 0.8% |
| **ORCL** | **0.08** | **yes** | **model** | **BBB..BB** | **4** | **40.6%** |
| PNC | 2.07 | no | **model** | AAA..AA | 4 | 3.8% |
| WMT | 2.01 | no | scale-top | AAA..AAA | 1 | 0.4% |
| INTU | −0.39 | **yes** | not rated | — | — | 64.6% |
| AMZN | 1.48 | **yes** | floor | AAA..AAA- | 2 | 4.0% |
| T | 0.84 | **yes** | **model** | AAA..AA- | **5** | 23.6% |
| KHC | −0.48 | **yes** | not rated | — | — | 77.2% |

## The finding this produced

**ORCL's BB is not supportable as a point rating.** In **40.6% of bootstrap replicates the
drift goes negative**, so the company cannot be rated at all; in the 59% where it can, the
rating spans **BBB to BB, four notches**. The point estimate is one draw from a distribution
that is nearly half "unrateable" and otherwise smeared across investment grade and junk.

The README must not present it as a model result. It should be shown with its interval and
its `WEAKLY_IDENTIFIED` flag, or not shown as a letter at all.

**None of the four model-determined names survives uncertainty as a point rating.** DELL has
the strongest `t` in the set and the *widest* interval (8 notches, AAA..A-), because it sits
where the S&P scale is finely notched. T spans 5, PNC 4. The `MODEL_DETERMINED` count of 4
describes which ratings the scale can resolve — it says nothing about whether the estimate
behind them is precise, and on this evidence none of them is.
