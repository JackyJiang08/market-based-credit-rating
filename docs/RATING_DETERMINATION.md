# What determines a rating

Every letter this pipeline publishes carries a `Rating Determination` alongside it. This
document explains what the four values mean, why the distinction matters, and why the
pattern it exposes is **a property of market-based structural models in the
investment-grade region — not a defect in this implementation**.

## The four values

| Value | Meaning |
|---|---|
| `MODEL_DETERMINED` | The TTC PD sits strictly inside the range its route can express. The letter moves when the model moves. |
| `PINNED_AT_FLOOR` | The grid lookup returned its smallest expressible value (2bp in the shipped workbook). The model asked for something smaller; the table had nothing left to say. |
| `PINNED_AT_SCALE_TOP` | The analytical route produced a RiskScore below the best published grade of the S&P TTC scale (Table 8, RiskScore 2.7). The TTC PD is that grade's 0.01% whatever the model computed. |
| `NOT_RATED` | No letter was produced: `(CCM, µ)` fell outside every route, or the drift regime is defective (Prop. 4.4.1). |

`Rating Basis` says which *route* produced a number. `Rating Determination` says whether
that number carries information. They are different questions and the deliverable answers
both.

## Current standing

Ten companies, as of the 2026-07-25 run:

| Determination | Count | Companies |
|---|---:|---|
| `MODEL_DETERMINED` | **4** | DELL, ORCL, T, PNC |
| `PINNED_AT_SCALE_TOP` | **3** | COST, KO, WMT |
| `PINNED_AT_FLOOR` | **1** | AMZN |
| `NOT_RATED` | **2** | INTU, KHC |

**Only 4 of 10 published letters are measurements.** Half the rated names are pinned at the
edge of a scale.

One caveat on PNC: its TTC PD is 0.000225 against a 2bp floor, i.e. 1.13× the floor. It
clears the saturation band but not by much, and it should be read as a borderline case
rather than a resolved one. T (0.000643, 3.2× the floor) and DELL and ORCL are clear.

### The analytical route did not add model-determined coverage

Wiring in the Prop. 5.2.1 analytical conversion (#11) took the rated count from 5 to 8 by
rating COST, KO and WMT, which had been `OFF_GRID`. **All three came back
`PINNED_AT_SCALE_TOP`.** Model-determined coverage did not increase by one.

That is worth stating plainly because it is easy to read "5 → 8 rated" as progress in
coverage. It is progress in *honesty* — those three companies now get a letter and an
explicit statement that the letter is the top of the scale rather than a blank cell — but
it bought no new information about them.

## Why this happens, and why it is not a bug

The three scale-pinned companies have these model outputs:

| | CCM | µ | PIT PD | S&P RiskScore |
|---|---:|---:|---:|---:|
| COST | 0.0662 | 37.3 | ~1e-131 | 1.0e-06 |
| KO | 0.0856 | 23.2 | ~1e-77 | 1.0e-06 |
| WMT | 0.0648 | 10.5 | ~1e-34 | 1.0e-06 |

Their RiskScores are ~1e-06 against a scale whose best published grade is **2.7**. They are
six orders of magnitude below the bottom of the ladder.

This follows directly from the structure of a first-passage model, not from any coding
choice:

1. **`ln(A/D)` is large for an investment-grade issuer.** COST carries a default point of
   ~$4bn against an asset value of ~$4.2e11, so `ln(A/D) ≈ 4.6`.
2. **Distance to default scales as `ln(A/D)/σ_A`.** With σ_A ≈ 0.20 that is a DD of ~24.
3. **PD falls off like the Gaussian tail.** `Φ(−24) ≈ 1e-127`. The one-year default
   probability of a firm 24 standard deviations from its barrier is not a small number in
   the ordinary sense; it is a number with no empirical meaning.
4. **Every rating scale is calibrated to observed default rates.** S&P's best published
   grade corresponds to a 0.01% one-year rate — one default in ten thousand issuer-years.
   That is the smallest rate the historical record can support. The model's answer is
   ~1e-127. There is nothing for the scale to resolve.

The same argument applies to the 2bp grid floor: the conversion workbook stops at 0.0002
because that is where the agency data stops.

**So the pinning is the scale's resolution limit meeting a model with unbounded resolution
in the safe direction.** Any structural model — Merton, KMV, first-passage — applied to a
large investment-grade issuer produces the same collision. Reporting `AAA` for all three is
correct; reporting it *without saying it is the top of the scale* would imply the model
distinguished between them, and it did not.

### What the model still says about these names

The pinned letter is uninformative, but the underlying measures are not. `DD`, `RiskScore`
and `TiC` are all defined and all differ across the three, and `TiC` is drift-free by
Prop. 4.4.2 so it is the most stable of them. For an investment-grade comparison, rank on
`DD` and `RiskScore` rather than on the letter — the letter is the coarsest thing the
pipeline produces and, in this region, the least informative.

## Consequences for how the deliverable is read

- The three-way count belongs next to any statement of coverage. "8 of 10 rated" without
  "4 of 10 model-determined" overstates what the model established.
- Comparisons between two pinned names are not meaningful at the letter level.
- A change that moves a pinned name's inputs will usually not move its letter. That is not
  evidence the change had no effect.
- Improving coverage of *model-determined* ratings means either a scale with more
  resolution at the safe end, or accepting that the investment-grade region is where this
  class of model has least to say.
