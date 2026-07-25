# Three-way reconciliation: our submission, a peer implementation, and the screenshot figures

Read-only analysis. No file under the four workflow layers was changed by this work.

Generated 2026-07-25 from `crossover.py`. Sources:

| Source | What it is | Available here |
|---|---|---|
| **Ours** | our pipeline, recomputed from the cached run of 2026-07-25 | inputs + code |
| **Theirs** | `other_answer.xlsx`, `Asset` sheet — a peer implementation of the same spec | outputs only |
| **Screenshot** | hand-transcribed `A`/`σ`/`DD` table, `screenshot_figures.md` | 3 columns, no inputs |

---

# Executive summary

## The headline

**Neither workbook implements the model the paper defines.** Both take `|η − σ²/2|` when the
drift is negative, in **4 of 10** companies for us and **5 of 10** for the peer. Proposition
4.4.1 states the assumption explicitly — *"Assume η − σ_A²/2 > 0 and D < A₀"* — and defines
`µ` and `CCM` (Eq. 11) with the **signed** drift in the denominator. Where the drift is
negative the first-passage time is defective and `µ = E[τ]` does not exist; the number both
workbooks print is not the quantity the paper defines. This is the finding that should lead
the deliverable, and it is not a coding bug in either implementation — it is an undeclared
modelling substitution.

## One pre-computed finding is wrong

**B2 is refuted.** The paper's Eq. (28) reads `Outlook = PD_FH − S&P TTC`, i.e. **PIT − TTC**,
which is exactly what this repo computes. The proposed "one-line fix" would have inverted a
correct implementation. Do not change it. Evidence in §B2.

## Classification

| # | Disagreement | Verdict | Class |
|---|---|---|---|
| B5 | `abs()` on negative drift | **CONFIRMED** — 4/10 ours, 5/10 theirs | **DECIDABLE-BY-PAPER** (violation is provable) → **OPEN** (remedy is the owner's call) |
| B6 | Grid clamping | **CONFIRMED and widened** — 5/10 ours, 3/10 theirs | DECIDABLE-BY-PAPER (clamping is not a rating) → OPEN |
| B3 | Long-term debt field | **CONFIRMED, cause identified per name** | DECIDABLE-BY-SPEC (ORCL, AMZN); NOT COMPARABLE (PNC, COST) |
| B1 | `Total Debt` column semantics | **CONFIRMED** — reporting only, model is correct | **DECIDABLE-BY-SPEC** → OPEN (which semantics the deliverable wants) |
| B4 | Fractional shares | **REFINED** — by design, agrees to rounding on 8/10 | DECIDABLE-BY-SPEC (ours is defensible) |
| B2 | Outlook sign | **REFUTED** — ours matches Eq. (28) | **DECIDABLE-BY-PAPER** (closed) |
| — | Screenshot figures | irreconcilable with either workbook | **NOT COMPARABLE** |

## Are they comparable?

**Ours vs. theirs: yes, conditionally.** Same universe, same source (Yahoo + FRED), same
horizon. Inputs agree closely on 6 of 10 names and diverge materially on 4 (ORCL, AMZN, PNC,
T). The 2×2 crossover shows that **inputs and conventions explain most of the DD gap**: after
re-running our model on their inputs, the residual DD difference is ≤ 0.4 on 5 of 10 names.
The two implementations are close; the inputs are not.

**Screenshot vs. anything: no.** Its `A` values sit within a few percent of both workbooks,
but its `σ` diverges from our realized equity volatility by factors of **0.48× to 3.98×** with
no consistent relationship, and its `DD` cannot be reproduced from any debt definition
available here. Without its inputs, no correctness claim is possible in either direction.

## Ranked fix list, by impact on the final rating

1. **Negative drift (B5)** — decides `µ`, `CCM`, `PIT PD` and therefore the letter for ORCL,
   INTU, T, KHC. ORCL is our only sub-investment-grade name and it is a negative-drift name.
2. **Grid clamping (B6)** — 5 of our 10 clamp. Every clamped name lands on the TTC floor and
   prints `AAA-`. The rating is being set by the edge of a lookup table, not by the model.
3. **Long-term debt field (B3)** — changes `D` by up to 1.76× (AMZN 209.9bn → 119.1bn). Moves
   DD by 1.7–2.7 on COST, AMZN, WMT.
4. **`Total Debt` column semantics (B1)** — presentation only; zero model impact, but it makes
   the two workbooks look irreconcilable at a glance when they are not.
5. **Shares (B4)** — ≤ 1.4% on two names (PNC, T), nil elsewhere. Lowest priority.
6. **Outlook sign (B2)** — no action. Already correct.

## What needs a decision from you

- **B5:** flag-and-report, refuse to rate, or keep `abs()` with a documented deviation?
- **B6:** return `OFF_GRID`, extend via the analytical no-arbitrage route, or keep clamping?
- **B1:** should the `Total Debt` column carry gross debt or the default point `D`?
- **B3:** is `Long Term Debt And Capital Lease Obligation` (ours) or plain `Long Term Debt`
  (theirs) the intended field? Post-ASC 842 the lease obligation is real debt, which argues
  for ours — but the reference deck should settle it.

---

# A. Are they comparable?

## A.1 Input provenance

Debt in USD millions. "Ours" is the cached run of 2026-07-25; "theirs" is read from their
`Asset` sheet.

| Ticker | As-of (ours / theirs) | Statement (ours / theirs) | Shares (ours / theirs) | ST debt | LT debt | r_f |
|---|---|---|---|---|---|---|
| COST | 2026-07-24 / 2026-06-30 | 2026-05-31 / 2026-05-10 | 443,478,803.19 / 443,478,804 | 0 / 0 | 8,136 / 5,670 | .0415 / .0397 |
| KO | 2026-07-24 / 2026-06-30 | 2026-03-31 / 2026-04-03 | 4,302,482,621.86 / 4,302,482,418 | 4,825 / 4,825 | 39,065 / 39,065 | .0415 / .0397 |
| DELL | 2026-07-24 / 2026-06-30 | 2026-04-30 / 2026-05-01 | 646,142,417.77 / 646,142,428 | 7,550 / 7,550 | 23,611 / 23,611 | .0415 / .0397 |
| ORCL | 2026-07-24 / 2026-06-30 | 2026-05-31 / 2026-05-31 | 2,880,471,107.76 / 2,880,471,000 | 7,199 / 7,199 | **148,990 / 122,342** | .0415 / .0397 |
| PNC | 2026-07-24 / 2026-06-30 | 2026-03-31 / 2026-03-31 | 399,000,002.17 / 401,564,632 | **0 / 24,143** | **66,666 / 42,523** | .0415 / .0397 |
| WMT | 2026-07-24 / 2026-06-30 | 2026-04-30 / 2026-04-30 | 7,958,078,836.70 / 7,958,079,155 | 17,082 / 15,420 | 57,097 / 42,709 | .0415 / .0397 |
| INTU | 2026-07-24 / 2026-06-30 | 2026-04-30 / 2026-04-30 | 273,536,982.56 / 273,537,000 | 833 / 750 | 6,067 / 5,412 | .0415 / .0397 |
| AMZN | 2026-07-24 / 2026-06-30 | 2026-03-31 / 2026-03-31 | 10,757,109,674.80 / 10,757,109,436 | 0 / 0 | **209,888 / 119,074** | .0415 / .0397 |
| T | 2026-07-24 / 2026-06-30 | **2026-06-30 / 2026-03-31** | 6,852,385,869.49 / 6,948,338,835 | 9,323 / 6,818 | **153,565 / 131,589** | .0415 / .0397 |
| KHC | 2026-07-24 / 2026-06-30 | 2026-03-31 / 2026-03-28 | 1,185,777,635.74 / 1,185,777,638 | 1,910 / 2,204 | 19,223 / 19,223 | .0415 / .0397 |

EM window: **252 trailing daily observations** on our side (`EM_WINDOW_DAYS`), with a year
sized at 250 trading days (`TRADING_DAYS_PER_YEAR`). The peer publishes no window length —
this is an unobservable, and it is one of the things the residual term absorbs.

Structural differences visible immediately:

- **As-of date differs by 24 calendar days** (2026-07-24 vs 2026-06-30) on every name. The EM
  windows therefore overlap but are not the same window.
- **Risk-free rate differs**: 4.15% vs 3.97%, consistent with the as-of gap on DGS1.
- Statement dates agree on 5 names, differ by days on 4 (a "latest available" tie-break), and
  differ by a full quarter on **T** (2026-06-30 vs 2026-03-31).

## A.2 The 2×2 crossover

`crossover.py` runs four cells. Cell D is **read**, not recomputed: the peer published a
workbook, not code, so "their model" is not executable. The residual is therefore an *upper
bound* on genuine implementation difference — it also absorbs their unknown EM window and
their unpublished price series.

| Cell | Inputs | Conventions | Model |
|---|---|---|---|
| A `ours` | ours | ours | ours (recomputed) |
| B `our_model_their_inputs` | theirs | ours | ours (recomputed) |
| C `their_conv_our_inputs` | ours | theirs (plain `Long Term Debt`) | ours (recomputed) |
| D `theirs_reported` | theirs | theirs | theirs (read) |

Decomposition on **DD**:

| Ticker | A ours | B their inputs | C their conv | D theirs | Screenshot | Input effect (B−A) | Convention effect (C−A) | Residual (D−B) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| COST | 24.62 | 27.29 | 26.44 | 25.95 | 22.43 | +2.67 | +1.82 | −1.34 |
| KO | 18.95 | 19.92 | 18.95 | 18.66 | 18.92 | +0.98 | +0.01 | −1.27 |
| DELL | 6.80 | 7.17 | 6.81 | 7.25 | 5.42 | +0.36 | +0.01 | **+0.08** |
| ORCL | 1.92 | 3.02 | 2.11 | 3.42 | 6.25 | +1.10 | +0.19 | **+0.40** |
| PNC | 9.99 | 10.18 | 10.85 | 8.03 | 7.77 | +0.19 | +0.86 | −2.15 |
| WMT | 13.67 | 15.10 | 14.59 | 15.06 | 7.34 | +1.44 | +0.92 | **−0.05** |
| INTU | 4.95 | 4.74 | 5.12 | 4.95 | 8.50 | −0.20 | +0.17 | **+0.21** |
| AMZN | 10.54 | 12.79 | 12.26 | 13.10 | 2.47 | +2.25 | +1.72 | **+0.31** |
| T | 7.15 | 6.32 | 7.43 | 5.69 | 3.01 | −0.82 | +0.28 | −0.64 |
| KHC | 8.05 | 7.75 | 8.05 | 6.51 | 5.04 | −0.30 | −0.00 | −1.25 |

**Reading it:**

- **Inputs dominate.** Feeding their inputs into our model moves DD by up to +2.67 (COST) and
  +2.25 (AMZN) and reverses sign on three names.
- **The two implementations are close.** On DELL, WMT, INTU, AMZN and ORCL the residual is
  ≤ 0.40 DD — i.e. inputs and conventions explain essentially the whole gap. There is no
  evidence of a materially different estimator on those names.
- **PNC is the outlier** (residual −2.15) and it is explained in §B3: their short-term /
  long-term split is not obtainable from the data source we both use.
- **COST, KO and KHC carry residuals of −1.2 to −1.3** in the same direction, which is the
  signature of a different EM window or price series rather than a different formula.
- The convention effect is near zero (≤ 0.02) on KO, DELL and KHC — exactly the names where
  the plain and lease-inclusive long-term debt rows coincide.

## A.3 The screenshot source

The screenshot publishes `A`, `σ`, `DD` and nothing else. Two diagnostics, both in
`crossover_results.csv`:

| Ticker | Screenshot σ | Our realized equity vol σ_E | Ratio | D implied by (A, σ, DD) | Our D |
|---|---:|---:|---:|---:|---:|
| COST | 0.2222 | 0.1916 | 1.16 | 2.79bn | 4.07bn |
| KO | 0.1508 | 0.1678 | 0.90 | 21.74bn | 24.36bn |
| DELL | 0.3092 | 0.6421 | **0.48** | 86.99bn | 19.36bn |
| ORCL | 0.3774 | 0.6149 | 0.61 | 43.06bn | 81.69bn |
| PNC | 0.1810 | 0.2032 | 0.89 | 32.54bn | 33.33bn |
| WMT | 0.4613 | 0.2401 | **1.92** | 31.17bn | 45.63bn |
| INTU | 0.3639 | 0.4635 | 0.79 | 3.54bn | 3.87bn |
| AMZN | 1.2474 | 0.3137 | **3.98** | 124.63bn | 104.94bn |
| T | 0.4312 | 0.2191 | **1.97** | 53.15bn | 86.11bn |
| KHC | 0.2862 | 0.2261 | 1.27 | 8.93bn | 11.52bn |

The ratio spans 0.48× to 3.98×. The screenshot's σ is therefore **not** asset volatility, not
equity volatility, and not a fixed transform of either. `AMZN σ = 1.2474` is not a plausible
annualized asset volatility for a mega-cap under any window. The implied-debt column
reconciles to a sensible figure on about half the names (COST, KO, PNC, INTU) and is absurd on
DELL (4.5× our D) and T.

**Verdict: NOT COMPARABLE.** No correctness claim can be made about the screenshot or against
it. It should not be used as a tie-breaker between the two workbooks. If it is meant to be
authoritative, we need its inputs and its as-of date.

---

# B. Verification of the pre-computed findings

## B1 — Default point `D` vs. the `Total Debt` column — **CONFIRMED**

**Their column is the default point.** KO: `4,825 + 0.5 × 39,065 = 24,357.5` — their reported
`Total Debt` is exactly 24,357,500,000. ✅

**Our column is the as-reported gross figure.** `dashboard/submission.py:44-46`:

> `"""Latest reported Total Debt, else short-term + long-term as a fallback."""`
> reads the `Total Debt` **row of the balance sheet**, not the model's default point.

KO: our reported 43,890 = the source's `Total Debt` row = 4,825 + 39,065. ✅

**The model is correct.** Our COST panel carries `DefaultPointDebt_D = 4.068bn`, which is
`0 + 0.5 × 8.136bn`. The back-solve in the premise checks out:

```
ln(432.2bn / 4.068bn) / 0.1899 = 24.63     our recomputed DD = 24.62   ✅
```

(exact recomputed values: A = 432.25bn, σ_A = 0.189858, DD = 24.6188)

`data_cleaning/transforms.py` `default_point_debt()` applies
`SHORT_TERM_DEBT_WEIGHT = 1.0`, `LONG_TERM_DEBT_WEIGHT = 0.5` throughout. There is **no model
bug** — the two workbooks put different quantities in a column with the same name.

**Class: DECIDABLE-BY-SPEC, then OPEN.** The deck fixes `D = ST + 0.5·LT` for the *model*.
It does not fix what the deliverable's `Total Debt` column should display. Needs your call —
my recommendation is to publish both (`Total Debt` gross **and** `Default Point D`), since
dropping either loses information a reviewer needs.

## B2 — Outlook sign — **REFUTED**

The premise states the paper defines `Outlook = S&P TTC − PD_FH`. It does not.

Proposition 5.3, Eq. (28), verbatim from `local/TiC_paper.pdf`:

```
PROPOSITION 5.3 (Credit Risk Outlook) Let us define
Outlook
= PDFH − S&P TTC
(28)
If Outlook>0, then the future trend is positive; if Outlook<0, then the trend is negative
```

So `Outlook = PD_FH − S&P TTC` = **PIT − TTC**, which is what `conversion.outlook(pit, ttc)`
computes and what the CLI labels `Outlook (PIT-TTC)`.

The sign convention is internally consistent: `Outlook > 0` means PIT exceeds TTC, i.e.
short-term risk is elevated relative to through-the-cycle, so mean reversion implies
improvement — "the future trend is positive". Inverting it would make the paper's own
interpretation of the sign wrong.

The prose paragraph immediately above Eq. (28) says "the difference between S&P TTC and
PDFH", which reads in the opposite order and is very likely what the premise was drawn from.
The displayed equation governs.

**No change. No regression test needed. Class: DECIDABLE-BY-PAPER, closed.**

⚠️ Had this been applied as specified, it would have inverted a correct implementation and the
regression test would have locked the error in.

## B3 — Long-term debt divergence — **CONFIRMED, cause identified per name**

Our field preference (`data_cleaning/config.py`, `BALANCE_SHEET_MAP["Long-term Debt"]`):

```python
"Long-term Debt": (
    "Long Term Debt And Capital Lease Obligation",   # ← we take this first
    "Long Term Debt",
),
```

The peer takes the plain `Long Term Debt` row. From our cached raw balance sheets (USD
millions, at each side's own statement date):

| Ticker | Ours | Theirs | Difference | Cause |
|---|---:|---:|---:|---|
| ORCL | 148,990 | 122,342 | 26,648 | **(iii) field selection.** Identical statement date (2026-05-31). The difference equals `Long Term Capital Lease Obligation` = 26,648 **exactly**. |
| AMZN | 209,888 | 119,074 | 90,814 | **(iii) field selection.** Identical statement date (2026-03-31). Difference equals `Long Term Capital Lease Obligation` = 90,814 **exactly**. |
| T | 153,565 | 131,589 | 21,976 | **(i) + (iii), both.** Theirs is plain `Long Term Debt` at 2026-03-31 = 131,589 exactly. Ours is lease-inclusive at 2026-06-30. Decomposes as −18,907 (leases, at 03-31) then +3,042 (one quarter of vintage). |
| PNC | ST 0 / LT 66,666 | ST 24,143 / LT 42,523 | — | **Neither (i), (ii) nor (iii).** Their split sums to 66,666 — *our exact total*. But the source reports **no current-debt row at all** for PNC, and `Long Term Debt` = `Long Term Debt And Capital Lease Obligation` = `Total Debt` = 66,666 in both the quarterly and annual sheets. Their ST/LT split is **not obtainable from the data source we share**; it must come from filing detail. |

Ours is not wrong for PNC so much as blind: `transforms.split_term_debt()` finds no
short-term row, falls back to `max(Total − LT, 0) = 0`, and the whole 66,666 is halved. Their
`D` = 45,404.5 vs our `D` = 33,333 — a **36% difference in the default point** on a bank,
which is also the name our own limitations section already flags as structurally unsuitable.

**The exact field we use:** first match in `("Long Term Debt And Capital Lease Obligation",
"Long Term Debt")` from the quarterly balance sheet, falling back to the annual sheet when
quarterly is empty (`data_cleaning/workflow.py:111`).

**Defensible alternative:** plain `Long Term Debt`, matching the peer. Argument for ours:
post-ASC 842 finance-lease obligations are contractual fixed claims that trigger default, so
they belong in the default point. Argument for theirs: the reference deck's default point is
described in terms of short- and long-term *debt*, and lease capitalization is an accounting
convention the KMV/Merton literature predates. **Class: DECIDABLE-BY-SPEC** for ORCL/AMZN/T
once the deck is consulted; **NOT COMPARABLE** for PNC, where their input is not reproducible
from our source.

## B4 — Fractional shares outstanding — **REFINED, not an error**

`data_cleaning/transforms.py` `reference_shares()`:

> `"""Shares outstanding via the one-day method (market cap / price). [...] For dual-class
> names (e.g. DELL) this recovers the *total* shares so market cap reconciles, which a single
> share-class figure would not."""`

So the fractional path is **deliberate and documented**, not an accident, and it is the
*authoritative* one for our pipeline — `sharesOutstanding` is only the fallback
(`workflow.py:58-59, 88-90`).

Does it introduce error? Compare the two workbooks:

| Ticker | Ours | Theirs | Relative difference |
|---|---:|---:|---:|
| COST | 443,478,803.1865 | 443,478,804 | 1.8 × 10⁻⁹ |
| KO | 4,302,482,621.8602 | 4,302,482,418 | 4.7 × 10⁻⁸ |
| DELL | 646,142,417.7737 | 646,142,428 | 1.6 × 10⁻⁸ |
| ORCL | 2,880,471,107.7602 | 2,880,471,000 | 3.7 × 10⁻⁸ |
| WMT | 7,958,078,836.7000 | 7,958,079,155 | 4.0 × 10⁻⁸ |
| INTU | 273,536,982.5565 | 273,537,000 | 6.4 × 10⁻⁸ |
| AMZN | 10,757,109,674.8024 | 10,757,109,436 | 2.2 × 10⁻⁸ |
| KHC | 1,185,777,635.7434 | 1,185,777,638 | 1.9 × 10⁻⁹ |
| **PNC** | **399,000,002.1683** | **401,564,632** | **6.4 × 10⁻³** |
| **T** | **6,852,385,869.4882** | **6,948,338,835** | **1.4 × 10⁻²** |

On 8 of 10 names the two agree to within 10⁻⁷ — they are **the same number**, ours unrounded
and theirs rounded to a whole share. The fractional representation contributes no error;
rounding to an integer would change equity by less than one part in ten million.

The two that genuinely differ (PNC 0.64%, T 1.4%) differ because the *method* is
date-sensitive — market cap ÷ price on 2026-07-24 vs. on 2026-06-30, plus provider staleness
in `marketCap` — not because the result is fractional. That sensitivity is a real weakness of
the one-day method, and it is the one worth documenting; the decimal point is not.

**Ours is authoritative for our pipeline. Class: DECIDABLE-BY-SPEC.** Recommend keeping the
method and storing its reference date, which `docs/TIMING_PROTOCOL.md` §3 already requires
("A constant reference-share assumption is allowed only when it is explicitly identified as a
modelling assumption and its reference date is stored") — and which we do not currently do.

## B5 — Negative drift and `abs()` — **CONFIRMED — headline finding**

Proposition 4.4.1, verbatim:

> `Assume η − σ_A²/2 > 0 and D < A_0, then the first-passage default process τ has the
> following properties.`

Eq. (11) then defines `CCM = σ_A² / (ln(A₀/D) · (η − σ_A²/2))` and `µ = ln(A₀/D) / (η − σ_A²/2)`
with the **signed** drift.

Our code, `signal_construction/measures.py:74-75`:

```python
drift = eta_A - 0.5 * sigma_A ** 2          # signed (for DD)
abs_drift = abs(drift)                       # |eta - sigma^2/2| (for mu, CCM)
```

**Counts (recomputed for ours, read from the `R` column for theirs):**

| | Negative-drift names | Count |
|---|---|---:|
| **Ours** | ORCL, INTU, T, KHC | **4 / 10** |
| **Theirs** | COST, ORCL, INTU, T, KHC | **5 / 10** |

The premise's per-name signs for our workbook (`COST +, KO +, WMT +, AMZN +, T −, PNC +,
INTU −, DELL +, KHC −, ORCL −`) are **confirmed exactly**. The peer additionally has COST
negative (`R = −0.071393`) where ours is marginally positive (`+0.008228`) — a sign flip on a
drift indistinguishable from zero, which is itself evidence for how unstable this estimate is.

**Why it matters, concretely.** COST is positive-drift for us by `+0.0082`. Because
`µ = ln(A/D)/|drift|`, that near-zero denominator gives `µ = 567.1` — off the top of the grid
(§B6) — where the peer's `−0.0714` gives `µ = 69.93`, comfortably on-grid. The same company,
the same model, opposite sides of a lookup-table boundary, driven entirely by the sign and
magnitude of a statistically insignificant drift estimate.

**This is a modelling violation, not a bug.** Taking the absolute value silently converts a
defective first-passage problem (default almost surely, infinite mean hitting time) into a
finite `µ` and prints it as if the paper's quantity had been computed. Rule 3 of `CLAUDE.md`
requires a provenance flag on exactly this kind of substitution, and there is none — the flag
does not reach the `validation` sheet or the CLI.

**Class: DECIDABLE-BY-PAPER** that the current output is not the paper's quantity;
**OPEN** on the remedy. Options, in my order of preference:

1. Flag it — emit `µ`/`CCM` with a `drift_negative` provenance flag reaching the workbook, and
   state in the deliverable that those four names violate Prop. 4.4.1.
2. Refuse to rate negative-drift names (`NOT_AVAILABLE` rather than a defective number).
3. Keep `abs()` as an explicitly documented deviation.

Option 1 is the minimum that makes the output honest. Note the peer has the same problem, so
this is not a competitive disadvantage — it is a finding about the spec.

## B6 — Grid coverage — **CONFIRMED and wider than stated**

Grid axes read from the conversion workbook at runtime: **CCM ∈ [0.1, 540]** (154 points),
**µ ∈ [1, 160]** (93 points). ✅ exactly as the premise states.

| Ticker | Our CCM | Our µ | Our status | Their CCM | Their µ | Their status |
|---|---:|---:|---|---:|---:|---|
| COST | 0.939 | **567.1** | **off — µ above 160** | 0.101 | 69.93 | on |
| KO | **0.052** | 16.56 | **off — CCM below 0.1** | **0.067** | 21.41 | **off — CCM low** |
| DELL | 0.106 | 2.52 | on | **0.093** | 2.48 | **off — CCM low** |
| ORCL | 0.322 | 2.83 | on | 3.611 | 44.34 | on |
| PNC | **0.087** | 6.54 | **off — CCM below 0.1** | 0.105 | 4.51 | on |
| WMT | 0.134 | 22.95 | on | 0.109 | 22.57 | on |
| INTU | **0.071** | 3.44 | **off — CCM below 0.1** | **0.065** | 3.30 | **off — CCM low** |
| AMZN | 2.149 | **236.7** | **off — µ above 160** | 0.166 | 26.51 | on |
| T | 0.472 | 26.09 | on | 0.196 | 8.22 | on |
| KHC | 0.544 | 37.19 | on | 1.278 | 56.09 | on |

**Ours: 5 of 10 off-grid** — the premise named COST and AMZN (µ high, ✅ confirmed: 567.1 and
236.7) but **missed three more** that fall off the *CCM floor*: KO (0.052), PNC (0.087) and
INTU (0.071). **Theirs: 3 of 10**, all on the CCM floor (KO, DELL, INTU).

**What clamping does.** `conversion.ttc_pd()` clamps to the nearest edge and sets
`off_grid = True`; the rating is then read from the clamped cell. Every one of our five
clamped names lands on the TTC floor of 0.0002 and prints **`AAA-`** — COST, KO, PNC and AMZN
all receive the same top rating by virtue of hitting the same table edge. PNC in particular
is rated `AAA-` by us and `A` by the peer, and PNC is a bank whose default point we already
know to be mis-specified (§B3).

A clamped lookup is not a rating. `CLAUDE.md` already records the analytical no-arbitrage
route (`no_arb_ccm_star`) as the way past the grid edges; it is implemented and unused here.

**Class: DECIDABLE-BY-PAPER** (an edge-clamped value is not the model's output) → **OPEN** on
whether to return `OFF_GRID`, fall back to the analytical route, or keep clamping with a
louder flag.

---

# C. Who is right — summary of disagreements

| Disagreement | Ours | Theirs | Who is right | Class |
|---|---|---|---|---|
| Outlook sign | PIT − TTC | categorical label only | **Ours** — Eq. (28) | DECIDABLE-BY-PAPER |
| `abs()` on negative drift | yes (4 names) | yes (5 names) | **Neither** — both violate Prop. 4.4.1 | DECIDABLE-BY-PAPER → OPEN |
| Off-grid handling | clamp + flag (5 names) | clamp, no flag visible (3 names) | **Ours marginally** — at least the flag exists | DECIDABLE-BY-PAPER → OPEN |
| LT debt field | incl. capital leases | plain `Long Term Debt` | **Undecided** — needs the deck | DECIDABLE-BY-SPEC |
| PNC ST/LT split | 0 / 66,666 | 24,143 / 42,523 | **Theirs** — better decomposition, unreproducible source | NOT COMPARABLE |
| `Total Debt` column | gross reported | default point `D` | **Undecided** — presentation | DECIDABLE-BY-SPEC → OPEN |
| Shares method | market cap ÷ price | share count | **Ours defensible** — same to 10⁻⁷ on 8/10 | DECIDABLE-BY-SPEC |
| As-of date, r_f | 2026-07-24, 4.15% | 2026-06-30, 3.97% | **Neither** — different vintage | NOT COMPARABLE |
| Screenshot figures | — | — | **No claim possible** | NOT COMPARABLE |

---

# D. Reproducing this

```bash
python docs/reconciliation/crossover.py
```

Writes `docs/reconciliation/crossover_results.csv` (50 rows: 4 cells × 10 companies + 10
screenshot rows) and prints the DD decomposition and negative-drift counts.

**Reproducibility caveats — read before trusting a re-run:**

1. **The inputs are not committed.** `.gitignore` blocks `*.xlsx` and `*.csv` repo-wide, so
   `other_answer.xlsx`, `crossover_results.csv` and the cached data trees this script reads
   are all local-only. That rule is deliberate — the peer workbook embeds the proprietary
   TTC/PIT/RS/SP grids on four extra sheets, and this repository is public. **Do not add an
   un-ignore rule for this directory.** The tables above are the committed record.
2. **It reads a cached run, not a live one.** The script depends on
   `data_cleaning/data/<T>/aligned_panel.csv` and
   `raw_data_architecture/data/<T>/quarterly_balance_sheet.csv` from the run of 2026-07-25.
   Re-running `python -m mdt batch` will refresh those to a *later* vintage and the numbers
   above will move. This is the point-in-time problem `docs/TIMING_PROTOCOL.md` §9 describes:
   we do not persist immutable vintages, so this reconciliation is not re-derivable from the
   repository at a fixed date.
3. **Cell D is read, not computed.** The residual column bounds implementation difference from
   above; it also contains their unknown EM window and unpublished price series.
4. **Conversion needs `local/TiC_TTC_conversion.xlsx`.** Without it the TTC/rating columns come
   back empty and only the EM/measures half of the study runs.
