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
3. `η̂ ± 1·SE` is a 68% interval. Nothing in the paper motivates one standard error, and the
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
