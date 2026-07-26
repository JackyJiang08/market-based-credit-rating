# Changelog

Notable changes to the model and the delivered artifacts. Newest first.

Entries reference the GitHub issue they close. Detailed rationale lives in
`docs/DEVLOG.md`; architectural decisions live in `docs/adr/`.

## Unreleased

### Fixed

- **#14** Pinned the `Outlook` direction with regression tests. Eq. (28) is
  `PD_FH − S&P TTC` (PIT − TTC), which is what the code already computed; the
  delivered Asset sheet was correct. Three tests now fail loudly on an inversion.

- **#3** Removed every `abs()` on the drift `η − σ_A²/2`; Eq. (11) uses the signed
  value. Split the estimation windows: σ_A on the trailing 252 days, η on the full
  ~5-year span. Added a `DriftRegime` (VALID/DEFECTIVE) classification so a
  defective first-passage regime reports NOT_APPLICABLE instead of a substituted
  magnitude. ORCL and T move from defective to valid; INTU and KHC remain defective
  and are no longer rated. See `docs/adr/0001-drift-estimation.md`.
- **#3** (root cause) `default_point_debt()` filled missing debt with `0` rather than
  `NaN`, asserting "no debt" on every day before the earliest statement. Because EM
  filters on `D > 0` this silently truncated the drift span to ~1.2 years. Fixed;
  spans are now 2.7–4.9 years and `SE(η)` falls from 15–52% to 7.8–33%.
- **#3** `mdt --years` no longer hard-codes a default of 2, which shadowed
  `DEFAULT_YEARS`. Balance-sheet history now unions quarterly and annual statements
  instead of using one or the other.
- **#12** Every rating now carries a `rating_basis`: `GRID_INTERIOR`,
  `ANALYTICAL`, `OFF_GRID` or `NOT_APPLICABLE`. Clamped edge values are no longer
  published as ratings — an off-grid `(CCM, µ)` reports no letter instead of one
  chosen by the grid boundary. Added `ttc_at_floor`, which marks a TTC PD sitting
  in the grid's 2bp floor band as floor-determined rather than model-determined.
  COST, KO and WMT are now unrated (OFF_GRID); of the 5 remaining ratings, 3
  (PNC, AMZN, T — all AAA-) are floor-determined and only DELL and ORCL are
  model-determined.
- **#6** Corrected the `conversion.py` docstring, which claimed the analytical
  no-arbitrage route "extends past the grid edges". It does not: only Eq. (26) is
  implemented, Eq. (27) is not, and the route is reachable only from tests. Chose
  the docstring fix over wiring it in because Eq. (27) depends on the unimplemented
  rating half of Eq. (24) (#11), which is out of scope this week.
- **#4, #5** Eq. (13) and Eq. (22) are now computed in log space with
  `log_ndtr`/`logsumexp`, and EDF via `exp(log_ndtr(-DD))`. The old code claimed
  log space in a comment while computing linearly; `exp(2/CCM)` overflowed below
  CCM ≈ 0.00276 and the `except OverflowError` fallback dropped the second term
  entirely, understating PD by up to 0.9pp. `alpha_first_hitting` had no guard at
  all and raised. Added a 72-cell property test against `scipy.stats.invgauss`
  over CCM ∈ [1e-3, 1e3] × µ ∈ [0.5, 1e4]; the old implementation fails 2 of
  those cells, the new one passes all.
- **#10** `_invert_assets` now raises `EMError` when bracket expansion fails
  instead of falling through and bisecting an interval known not to contain the
  root, which returned a confident wrong asset value with no error. Named the
  estimator's magic numbers: `BRACKET_MAX_DOUBLINGS`, `BISECTION_STEPS`,
  `MIN_OBSERVATIONS`.
- **#7, #8** Declared the deliverable's contract as `dashboard.records.ASSET_SCHEMA`
  and consolidated all three writers onto one `credit_record()`. The Asset sheet now
  carries `A` (previously absent), a single `TiC Risk Score` column (previously split
  into `TiC` + `Risk Score`), and `lambda` (Eq. 3/6, previously computed and reaching
  no output). `EM iters` moved to the validation sheet. Added `Rating Basis` so a
  blank rating is interpretable on the sheet that shows it. Golden-file tests pin
  both schemas exactly.
- **#13** Added the missing regression tests: the Prop. 4.4.1 drift-regime contract
  (including that `|drift|` is never substituted), the `split_term_debt` fallbacks
  that produce `ShortTermDebt = 0` for banks, `default_point_debt` returning NaN
  rather than 0 when both legs are missing, `union_balance_sheets`, a direct
  `alpha_sp` anchor pinning the `1/Q` reading, and monotonicity of α(CCM).
- **#9** Replaced the broad `except Exception` blocks in `workflow.py` with a typed
  hierarchy in `raw_data_architecture/errors.py`: `RateLimitedError`,
  `DelistedError`, `NoDataError`, `SourceUnavailableError`. The outcome reaches the
  validation sheet as `Data Status`, so a company that genuinely has no data
  (`NO_DATA`) is now visibly different from a fetch that failed (`RATE_LIMITED` /
  `DELISTED` / `SOURCE_ERROR`). Retries are limited to throttling and transport
  failures — a delisted symbol is no longer retried four times. An unrecognised
  failure becomes `SOURCE_ERROR`, never `NO_DATA`.
- **#11** Implemented the rating half of Eq. (24) (`tic_lognormal`) and Eq. (27)
  (`no_arb_convert`), added `Q_MOODYS`, and wired the analytical no-arbitrage route
  into the live conversion path. Inside the grid the lookup is authoritative and the
  analytical route is the oracle checking it; outside the grid the analytical route
  produces the rating, labelled `ANALYTICAL`. COST, KO and WMT move from OFF_GRID to
  ANALYTICAL and are rated AAA. Regression tests reproduce Tables 12, 13 and 14.
  Also fixed `no_arb_ccm_star` returning its solver bracket edge when α saturates,
  and made `at_floor` mean scale-floor for analytical ratings rather than grid-floor.

### Proposed (not implemented)

- **ADR 0002** Evaluated reporting a rating interval from `η ∈ [η̂ ± 1·SE]` for the two
  DEFECTIVE names. Both intervals span the defective boundary, so both retain
  `NOT_APPLICABLE` — the proposal un-blanks nothing today, and the interval it would
  produce runs from unrateable to AAA-. Recommends a significance test in
  `drift_regime()` instead. See `docs/adr/0002-defective-drift-interval-proposal.md`.

## Unreleased (data layer)

### Fixed

- **#15** Replaced the additive `Close + Dividends.cumsum()` add-back with a reinvested
  total-return index anchored at the valuation date. The old series' level was `Close`
  plus every dividend paid since the first *downloaded* row, so `σ_A`, `A` and the rating
  depended on `DEFAULT_YEARS`; raising it 2→6 silently moved every number in the batch.
  σ_A and A are now bit-identical across download windows of 2, 4 and 6 years. Removed
  the `.fillna(0.0)` on dividends: a missing dividend is unknown, not zero, and an absent
  dividend column now yields NaN rather than a silently price-only series.
  σ_A rose 0.9–3.8pp for dividend payers and A fell correspondingly; AMZN, which pays no
  dividend, is unchanged to every digit. PNC AAA-→AA+, T AAA-→AA.
- **#19** Statements are now aligned on `available_at` (period end + a conservative
  filing lag: 45 days for a 10-Q, 90 for a 10-K) rather than on `period_end`, per
  TIMING_PROTOCOL §3, with `availability_method = "estimated_lag"` recorded. Added the
  canary test: no row may use a statement whose `available_at` exceeds that row's date.
  The panel now carries `StatementPeriodEnd` and `StatementAvailableAt` audit fields, and
  `Last Statement Date` reports the statement the model actually used rather than the
  latest one downloaded. On the valuation date only T is affected — its 2026-06-30
  statement is 25 days old and therefore not yet public — moving D by −4.69% and its
  rating AA→A+; PNC moves AA+→AAA- from the historical panel change.
- **Part B** Added `RatingDetermination` (`MODEL_DETERMINED` / `PINNED_AT_FLOOR` /
  `PINNED_AT_SCALE_TOP` / `NOT_RATED`) as a first-class output: a `Rating Determination`
  column on the Asset sheet, the classification plus the S&P RiskScore on the validation
  sheet, a count in the README, and `docs/RATING_DETERMINATION.md` explaining why the
  pinning is a property of structural models in the investment-grade region. Current
  standing: 4 model-determined, 3 scale-top-pinned, 1 floor-pinned, 2 not rated — the
  analytical route (#11) took rated coverage 5→8 without adding a single
  model-determined name.
- **Part C (partial)** Measured ADR 0002's k·SE rule against the current run: at `k = 1`
  ORCL and T become DEFECTIVE (rated 8→6, model-determined 4→2); at `k = 1.645` COST, KO
  and AMZN also go (rated 8→3, model-determined still 2). ORCL's `t = 0.08` decides it.
  Recommends `k = 1`, configurable. **Not switched on.** The full bootstrap is not built.
- **Part A/B** Added `signal_construction/bootstrap.py`: moving-block bootstrap over
  EM-recovered asset returns, propagated through measures and conversion to give
  distributions of σ_A, µ, CCM, RiskScore, PIT PD, TTC PD and the implied notch. Added
  `WEAKLY_IDENTIFIED` (`|t| < 2`), which **annotates** a rating rather than suppressing
  it — `DEFECTIVE` still means only the Prop. 4.4.1 violation `drift ≤ 0`. A fixed `k·SE`
  threshold was considered and rejected (ADR 0002). The Asset sheet publishes `Drift SE`,
  `Drift t`, `Weakly Identified` and the rating interval. **7 of 10 are weakly identified;
  ORCL is unrateable in 40.6% of replicates and spans BBB..BB where it is rateable.**
- **Part C** The submission workbook now opens on a README sheet: provenance (model
  version, git SHA, data vintage, statement dates used), the conventions in force
  (total-return equity series, NaN-not-zero dividends, `available_at` alignment and its
  lag constants, default point, LT debt field, share method, both estimation windows),
  how to read the rating basis / determination / weak-identification flags, and an
  explicit statement of the Asset sheet's deviation from the reference 23-column layout.
- **Part D** `#17` `reference_shares` returns its method and the workflow stores
  `shares_reference_date`, satisfying TIMING_PROTOCOL §3; the single-share-class fallback
  is labelled and warns. `#18` the risk-free series is range-checked after unit conversion
  and raises outside [0, 0.30]; a missing `Adj Close` is NaN rather than `Close`; the FRED
  date column is found by name. `#20` the remaining silent excepts are narrowed to specific
  exception types and report at WARNING. No rating moved.
- **Part A** Renamed `MODEL_DETERMINED` → `SCALE_RESOLVED` (the label measures scale
  resolution, not estimation precision — DELL has the strongest t and the widest interval).
  Rewrote the README around the decomposition: RiskScore unamplified at ×2.00 of σ and rank
  ordering stable (τ median 0.956) versus PIT PD at ×4,077; framed as a numerical
  demonstration of Prop. 4.4.2. Added the rule that a letter is never a headline and always
  carries its interval and flags. Added `docs/UNCERTAINTY.md` recording the method, its
  limits, and the two bootstrap bugs that testing the algebraic prediction exposed.
- **Part B** Added `docs/reconciliation/convention_sweep.py`, which sweeps the long-term
  debt weight and the statement vintage and reports the rating range per company beside the
  bootstrap interval. **For ORCL, PNC and T the convention span equals or exceeds the
  parameter span** — T moves seven notches on the debt weight alone. Recorded in the README
  results section; the bootstrap is confirmed as a lower bound on total uncertainty.
- **Part C / #16** Added `data_cleaning/sectors.py` (firm-type classification and an
  applicability gate with machine-readable reason codes), default-point variants
  (`standard` / `total_liabilities` / `total_liabilities_ex_deposits`, reported side by
  side, absent when not computable), and field provenance on the debt split so a
  contradictory source is flagged rather than clipped to zero. **PNC: $33.3bn (6.2% of
  liabilities) → AAA under the shipped rule, $539.4bn → BB under total liabilities, against
  an actual A/A2 agency rating** — the convention brackets the truth without hitting it.
  DELL and PNC are now `MODEL_NOT_APPLICABLE`; rated coverage 8/10 → 6/10.
