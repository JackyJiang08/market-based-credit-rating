# The 150-name universe run

Ten hand-picked mega-caps cannot support a statistical claim, and "works for
any company" was an untested assertion. `config/universe.yaml` scales the
test universe to **150 US-listed names** chosen to span the rating spectrum
and to include the hard cases on purpose — dual share classes, negative book
equity, banks/insurers/REITs, ADRs, recent IPOs, distressed and delisted
names. Every entry records why it is in the list.

Run of record: 2026-07-26, prices through the 2026-07-24 close, captured as
`docs/reconciliation/history/15_universe_150.csv`. Analysis:
`docs/reconciliation/universe_taxonomy.py` → `docs/reconciliation/universe/*.csv`.

## Failure taxonomy

Every company that does not produce a rating, classified by exact reason:

| Category | Count | Names / reasons |
|---|---:|---|
| **RATED** | **85** | letter with interval, per the presentation rule |
| **MODEL_NOT_APPLICABLE** | **41** | 12 `BANK_DEPOSIT_FUNDED` · 5 `INSURER_RESERVE_LIABILITIES` · 6 `REIT_ASSET_STRUCTURE` · 11 `ASSETS_BELOW_TOTAL_DEBT` (CYH, KSS, BYND, CHTR, LUMN, XRX, F, AAL, MGM, CZR, AMC) · 7 `REPORTING_CURRENCY_MISMATCH` (TM, TSM, BABA, NVO, SAP, ASML, BIRK) |
| **DEFECTIVE_DRIFT** | **20** | Prop. 4.4.1 fails (η − σ²/2 ≤ 0): CRM, INTU, BA, PYPL, OXY, BTU, RIG, UNH, PFE, MRNA, TGT, NKE, DG, DLTR, KHC, GIS, LCID, KVUE, GEHC, SPWR |
| **DATA_UNAVAILABLE** | **4** | PARA, NKLA, FSR (delisted → `NO_DATA`); SATS (vendor returns one price row — verified live, not a cache artifact) |
| **OFF_SCALE** | **0** | the analytical route (Eq. 26/27) now covers off-grid points |
| **BUG** | **0** | after the two fixes below — the first pass had 1 loud BUG and 5 silent ones |

## Bugs surfaced

1. **Reporting-currency mismatch** (`1661304`). TM files in JPY and prices in
   USD; EM raised `A <= D` because the debt barrier arrived in yen against
   dollar equity. **Worse: TSM, BABA, SAP and ASML were silently RATED on the
   same mismatch** (BIRK and NVO hid in DEFECTIVE_DRIFT). Fixed with a gate:
   `REPORTING_CURRENCY_MISMATCH`, which suppresses measures too — they would
   be unit-corrupt, not merely inapplicable. No FX conversion is attempted
   (a converted statement at a chosen rate is a fabricated input). TM's cache
   entry is the committed regression fixture.
2. **Payment networks misgated as banks** (`7635e18`). The vendor's "Credit
   Services" industry string lumps V/MA/PYPL with deposit-funded lenders;
   they came back `BANK_DEPOSIT_FUNDED`. Pinned `NONFINANCIAL` in the
   override map; ALLY/COF keep gating (genuinely deposit-funded) and AXP
   deliberately stays gated (funds through its own bank charter).
3. **Blank determination on currency-gated names** (follow-on consistency
   fix): the conversion block stamps `Rating Determination`, and gated names
   that skip EM never reach it; now stamped at the gate.

Not bugs, verified as data conditions: SATS (one price row from the vendor,
reproduced live), PARA/NKLA/FSR (delisted — the failure paths those names
were selected to exercise).

## Volatility by sector

Median annualized asset volatility, names with estimates (n = 139):

| Sector | n | median σ_A | min | max |
|---|---:|---:|---:|---:|
| Technology | 17 | **0.555** | 0.243 | 0.964 |
| Consumer Cyclical | 24 | 0.294 | 0.138 | 0.587 |
| Communication Services | 11 | 0.284 | 0.158 | 0.680 |
| Energy | 10 | 0.273 | 0.161 | 0.544 |
| Industrials | 13 | 0.261 | 0.191 | 0.394 |
| Consumer Defensive | 11 | 0.254 | 0.166 | 1.471* |
| Healthcare | 16 | 0.251 | 0.098 | 0.658 |
| Financial Services | 24 | 0.218 | 0.137 | 0.636 |
| Real Estate | 6 | 0.198 | 0.131 | 0.269 |
| Utilities | 7 | **0.141** | 0.104 | 0.416 |

The ordering is exactly the cross-sectional intuition — technology ~4× the
asset volatility of regulated utilities, financials and real estate at the
low end. (*the Consumer Defensive max is BYND, a distressed name whose
rating the `ASSETS_BELOW_TOTAL_DEBT` gate suppresses; its measures are still
computed and are legitimately extreme.)

Drift regimes across the 139 names with estimates: **VALID 108, DEFECTIVE
31** — one in five names has η − σ²/2 ≤ 0 over the estimation span, so the
first-passage PD chain is undefined for them. At universe scale this is a
structural property of the drift estimator, not a small-sample accident.

## Determination split

| Determination | Count | Share |
|---|---:|---:|
| SCALE_RESOLVED | 39 | 26% |
| MODEL_NOT_APPLICABLE | 41 | 27% |
| PINNED_AT_FLOOR | 29 | 19% |
| NOT_RATED (defective drift) | 20 | 13% |
| PINNED_AT_SCALE_TOP | 17 | 11% |
| — (no data) | 4 | 3% |

Only **26% of the universe gets a letter the scale actually resolved**; a
further 30% gets a letter pinned by the grid floor or the scale top. The
10-name universe's "7/10 rated, 3/10 scale-resolved" generalizes — the
proportions hold at 15× the sample.

## Letters vs agency ratings

Agency column: APPROXIMATE senior-unsecured ratings recorded in
`config/universe.yaml` (public sources, mid-2026, indicative only, never a
model input). Model column: this pipeline's letters (85 rated names).

| | AAA/AAA- | AA band | A band | BBB band | BB band | B and below |
|---|---:|---:|---:|---:|---:|---:|
| **Model** | **51** | 11 | 7 | 12 | 4 | 0 |
| **Agency (approx)** | 2 | 14 | 43 | 47 | 16 | 15 |

**The model's letter distribution is saturated at the top of the scale**: 60%
of rated names come back AAA or AAA− (the grid's 2bp TTC floor), against an
agency distribution centered on A/BBB. This is the 10-name floor-pinning
finding at scale, and it is the letter-route critique made distributional:
for large liquid names the market-implied PD chain compresses everything
investment-grade into the top notches, while RiskScore and DD still order
the universe sensibly (see the σ_A table). Full per-letter histogram:
`docs/reconciliation/universe/rating_histogram.csv`.

## Performance

| Run | Names | Workers | Wall clock |
|---|---:|---:|---|
| First run (all network, cache cold) | 150 | 6 | **3m 50s** |
| Rerun (cache warm, incl. 500-rep bootstrap × 150) | 150 | 8 | 4m 03s (CPU-bound) |
| Pro-rata for 100 names, cold | 100 | 6 | **~2m 35s** |

Resumability = the cache: a rerun refetches only missing artifacts, and a
company whose fetch failed retries only the failed artifact. Isolation is
the runner's contract: an exception in one company is recorded and reported,
never propagated (`tests/test_cache.py` pins it at workers=1 and 4).

## Caveats

- The agency comparison is against approximate, indicative ratings recorded
  at selection time — good enough for a distribution shape, not for
  per-name scoring.
- The 150 names oversample hard cases by design; the determination split is
  a property of this stress universe, not of "the market".
- Convention spans (the debt-weight sweep) exist only for the original 10
  names; sweeping all 150 is future work and the validation sheet reports
  no span rather than a guess for the rest.
