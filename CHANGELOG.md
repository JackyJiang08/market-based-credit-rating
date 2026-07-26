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
