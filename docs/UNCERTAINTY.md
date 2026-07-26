# Uncertainty propagation: method, findings, and the bugs it took to get here

How `signal_construction/bootstrap.py` works, what it established, and — because the
process matters as much as the result — the episode in which testing an algebraic
prediction found two bugs in the bootstrap itself.

## Method

A **moving-block bootstrap** over the EM-recovered **asset** log-returns.

- **Asset, not equity, returns.** The model's parameters are defined on the asset process.
- **Blocks, not i.i.d. draws.** Daily returns carry volatility clustering; resampling
  single days destroys it and understates the variance of the volatility estimator. Block
  length `n^(1/3)`, the standard moving-block rate for a mean-like statistic under weak
  dependence.
- **Each parameter is resampled from the window its own estimator uses.** `σ_A` from the
  trailing `EM_WINDOW_DAYS`, the drift from the full `DRIFT_WINDOW_DAYS` span, matching
  `em.estimate` exactly.
- **`A₀` and `D` are held fixed.** They are observations — `A₀` from inverting the
  observed market capitalisation, `D` from a filed balance sheet. Resampling them would
  model a different kind of uncertainty.

### Stated limits

1. **These are parameter-estimation intervals, and a lower bound on total uncertainty.**
   Convention uncertainty — the 0.5 weight on long-term debt, the field choice, the
   statement vintage — is not in them. `D` is a *choice* as much as an observation.
2. **The two resamples are drawn independently**, while the real estimators share the
   trailing year of data and are slightly dependent. Each marginal sampling distribution
   is right; their joint dependence is not modelled.
3. **Stationarity is assumed within each window.** A moving-block resample draws blocks
   uniformly, so a genuine volatility regime change inside a window is smeared.

## Findings

### RiskScore is unamplified; the letter is not

| Quantity | Median relative width | Amplification |
|---|---:|---|
| σ_A | 0.239 | — |
| RiskScore (drift-free) | 0.479 | **×2.00 vs σ_A** |
| DD | 0.317 | ×1.3 |
| TTC PD | 1.512 | ×3.2 vs RiskScore |
| PIT PD | ~1,960 | **×4,077 vs RiskScore** |

×2.00 is the square, exactly: `RiskScore ∝ σ_A²`, so `d(RS)/RS = 2·dσ/σ`. RiskScore
inherits σ's uncertainty and nothing else.

This is what Prop. 4.4.2 predicts. `TiC = σ_A²/ln²(A₀/D)` is Girsanov-invariant because
the `(η − σ_A²/2)` terms cancel between Eq. (11) and Eq. (12). `µ` and `CCM` keep the
drift in the denominator, and Eq. (13) exponentiates it.

**RiskScore at 48% is unamplified, not tight.** ±24% is material. The claim is that no
instability enters before the conversion, not that the number is precise.

### Discrimination survives; calibration does not

Kendall's τ between each replicate's ordering and the point ordering, on RiskScore:
**median 0.956**, 5th percentile 0.867, minimum 0.778; 99.9% of replicates ≥ 0.8.

| | Point rank | Modal | 5–95 | P(exact) |
|---|---:|---:|---|---:|
| COST | 1 | 1 | 1–1 | 100.0% |
| KO | 2 | 2 | 2–2 | 99.8% |
| WMT | 3 | 3 | 3–3 | 96.7% |
| AMZN | 4 | 4 | 4–4 | 96.2% |
| PNC | 5 | 5 | 5–6 | 90.8% |
| KHC | 6 | 7 | 6–8 | 44.0% |
| INTU | 7 | 6 | 5–8 | 35.0% |
| T | 8 | 8 | 6–9 | 62.3% |
| DELL | 9 | 9 | 8–9 | 85.8% |
| ORCL | 10 | 10 | 10–10 | 99.7% |

The extremes are essentially never misordered; the shuffling is confined to ranks 5–9,
where the companies are genuinely close. DD ordering is weaker (τ median 0.867) because DD
carries the drift term.

**A model whose levels are uncertain but whose ordering is stable is a useful model used
the wrong way.** This is how KMV is used in practice: DD is mapped to an *empirical*
default frequency, not to a theoretical PD.

## The episode: testing a prediction found two bugs in the test

Worth recording as it happened, because the workflow is the transferable part.

**The prediction.** The algebra says `TiC = CCM/µ = σ_A²/ln²(A₀/D)`. RiskScore is
therefore drift-free, and its bootstrap interval should be exactly what σ implies — no
more. That is falsifiable. If RiskScore came back as wide as the letter, something was
wrong, because the algebra says it cannot be.

**It failed, and the failure was ours.** Two bugs, both in `bootstrap.py`:

1. **Drift-conditioned selection on a drift-free quantity.** `risk_score` was recorded
   *after* the `continue` on a DEFECTIVE replicate, so its distribution was conditioned on
   `drift > 0`. Not a neutral filter: `drift = η − σ_A²/2`, so a larger σ makes DEFECTIVE
   more likely and the survivors were a **σ-truncated sample**. Worst precisely where it
   mattered — ORCL 44% defective, KHC 73%.
2. **The bootstrap did not mirror the estimator.** It resampled the full ~5-year span and
   computed σ from all of it, while the pipeline takes σ from the trailing 252 days. For
   COST: 0.231 against the pipeline's 0.195. Taking a trailing slice of a full-span
   resample does not fix it — a moving-block resample draws blocks uniformly, so every
   slice is the same regime-mixture. Each parameter now resamples from its own window.

**What was wrong in the record.** The previous session reported these intervals as fact and
claimed calibration had been checked. It had not: the check compared a full-span σ median
(0.2288) against a trailing-252 point estimate (0.1952) and read the gap as agreement. The
published intervals were too narrow — **DELL's letter span was reported as 8 notches and is
10**; ORCL was 4 notches but shifted to BBB−..BB−.

**What survived.** The qualitative conclusion did not change: RiskScore unamplified, letter
amplified, ordering stable. The corrected numbers are stronger, not weaker — the ×2.00
ratio is exact only after the selection bug is removed.

**The transferable part.** An algebraic identity is a free test oracle. `TiC = CCM/µ` is
provable on paper, so any implementation that violates it is wrong without needing a
reference dataset. Both bugs were invisible to a 267-test suite and to eyeballing the
output; they surfaced in minutes once a prediction was written down and checked. Two
regression tests now pin them:
`test_bootstrap_sigma_is_centred_on_the_pipeline_sigma` and
`test_bootstrap_records_drift_free_quantities_for_defective_replicates`.

Prediction-testing stays in the workflow. Where the maths implies a relationship the code
must satisfy, assert it.

## Consequences

- Lead with RiskScore and the rank ordering. They are what the evidence supports.
- A letter is a derived, wide-interval conversion — never a headline, always with its
  interval and flags. ORCL is written `BB (BBB−..BB−, unrateable in ~44% of replicates,
  weakly identified: t = 0.08)`, never bare.
- `SCALE_RESOLVED` answers whether the scale could resolve a value. `Drift t` and the
  rating interval answer whether the estimate is precise. Do not read either for the other.
