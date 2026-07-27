# Development Log

Last updated: 2026-07-25

This file under `docs/` is the shared, human-readable status record for the repository. It
must be updated as part of every push so contributors can understand what
changed, what was verified, and what remains open without reconstructing the
history from individual commits.

## Push rule

Before every push:

1. Add or update the newest entry under **Recent changes**.
2. Describe the pushed scope, important file or contract changes, and any
   breaking behavior.
3. Record the validation actually run; do not list checks that were skipped.
4. List unresolved follow-ups or explicitly write `None`.
5. Include the `DEVLOG.md` update in the same commit or push batch.

Entries are ordered newest first. One entry may summarize multiple commits in a
single push when they represent the same unit of work.

## Current project status

- All four layers are implemented end to end: raw acquisition (Layer 1),
  cleaning/alignment (Layer 2), EM + TiC measures + PIT/TTC/S&P conversion
  (Layer 3), and Excel/long-table/submission reporting (Layer 4).
- The credit chain is verified against the TiC paper (PIT PD Tables 13-14,
  alpha_FH(1.5)=0.91906, CCM*=1.35373) with a 24-test offline suite.
- Data path is still in memory; immutable raw/clean Parquet boundaries are a
  future milestone.
- Timing: alignment uses statement period-end as the as-of key rather than a
  true publication-time `available_at` field (documented limitation).

## Recent changes

### 2026-07-26 - House style, sensitivity playground, E2E, public deployment

- **House style:** phase wording now lives only in this log (grep-verified);
  DEPENDENCY_MAPS.md replaced by docs/ARCHITECTURE.md (three current
  diagrams + a CI staleness guard that fails on drift); README gains a
  one-diagram Architecture section; headings across README/docs are short
  noun phrases with the vivid phrasing kept in body text; GAP_ANALYSIS and
  reconciliation/REPORT open with two-sentence orientation.
- **Sensitivity playground (/sensitivity):** the published formulas
  client-side (Eq. 11-14, 22, 26/27 and the published Table-8 seven-grade
  scale -- the licensed grids that notch it are not involved), anchored in
  vitest to alpha_FH(1.5)=0.91906 / alpha_FH(5.0)=0.72749 / CCM*=1.35373.
  Sliders for sigma, the LT-debt weight w, eta, T; every output labels which
  sliders move it, and the eta slider visibly NOT moving RiskScore -- with a
  Prop. 4.4.2 callout when touched -- is the lesson. Company presets, URL
  state, and a live trace on the mu-CCM plane. A is held at the EM point
  estimate, stated on the page.
- **E2E (Playwright + axe):** command-bar flow, the interval-attached letter
  on the company view, all chart panels, URL-state filters, the
  drift-does-not-move-RiskScore interaction, and axe on four pages with
  zero serious/critical violations -- which required real fixes: 72
  text-zinc-500 contrast failures brightened to AA, chart SVGs with
  focusable points re-roled from img to group, and cmdk (which crashed the
  page under this React runtime) replaced by a self-contained accessible
  combobox. 9/9 passing; new e2e CI cell.
- **Public deployment (GitHub Pages):** deploy job runs only after every
  other cell is green and re-runs the bundle-safety gate itself; project
  base path via NEXT_PUBLIC_BASE_PATH; SEO/OG (mu-CCM card, favicon);
  /about carries the two central findings, attribution and links.
  Lighthouse gate >= 90 asserted in CI; measured home 92/100/100/100 and
  about 98/100/100/100 (LCP fixed by preloading universe.json). README:
  live-demo link + demo GIF above the fold + pages badge.
- **Validation:** python 370 passed; vitest 18; E2E 9/9; lighthouse as
  above; CI watched to green including the three new cells and the deploy.

### 2026-07-26 - Terminal chart layer: the mu-CCM plane and friends

- **Scope:** apps/terminal charts + export additions; two screenshots under
  docs/figures. No pipeline behavior changes.
- **mu-CCM plane** (the signature visual): ln-ln plane, iso-rating lines of
  slope Q at the published Table-8 RiskScores, published grid-domain box,
  scale-top labelling -- pinned names visibly cluster on the AAA iso line.
  Shape + colour encoding (never colour alone), hover/focus company card,
  ?focus= overlays the 250-point bootstrap cloud from the static JSON.
- **Amplification ladder** (per company vs universe median, log dot ladder)
  and **rating bridge** (PIT -> TTC -> letter with explicit floor/scale-top
  binding) as company panels behind ?panel= deep links.
- **Universe view:** URL-state filters, model-vs-agency two-histogram, rank
  scatter with SCALE_RESOLVED emphasis, notch-error distribution.
- Export gains bootstrap_cloud + per-company interval widths +
  at_floor/at_scale_top + mu/ccm universe columns + universe-median widths;
  bundle-safety unchanged and green (zero licensed matches).
- Charts are hand-rolled SVG on the docs/figures dark palette --
  visx/recharts were offered "as needed" and were not needed at these forms.
- **Validation:** tsc/eslint/vitest/next build green; python 368 passed;
  bundle safety OK; CI (incl. the frontend cell) watched to green.

### 2026-07-26 - Phase 12: the terminal (Next.js 15) + enforced bundle safety

- **Scope:** apps/terminal (app, tests, static-data pipeline, bundle-safety
  gate), frontend CI cells, docs/figures/terminal_company_orcl.png.
- **Static data first:** make build-site-data exports universe.json (150),
  147 per-company detail files (measures, intervals, flags, provenance,
  downsampled EM path, bootstrap) and validation.json, every file stamped
  with the producing git SHA + data vintage. The HARD CONSTRAINT is a gate,
  not a promise: check_bundle_safety.py fails the export on any licensed-
  grid content -- path, value (8,993 licensed reference values, zero matches
  at 1e-12; single documented exception: the publicly-stated 2bp floor) and
  shape (no grid-scale matrix) checks. It caught two floored-TTC
  coincidences during development before the exception was justified in
  writing; degraded mode without local/ states itself.
- **App:** Next 15 App Router, TS strict, Tailwind, shadcn/ui (Base UI),
  TanStack Query/Table, Zod on every load. Cmd+K / '/' command bar with
  fuzzy universe search (the one-click requirement). Company view:
  RiskScore + rank first, letter ONLY with its interval attached and a
  derived-conversion badge, provenance popovers per input, flags as
  first-class chips, EM sparkline, applicability/determination badges.
  Dark, dense, tabular-nums, keyboard navigable, skeletons, explicit
  error/empty states, and the site-wide footer (fixture-backed demo,
  as-of date, not investment advice, methodology attribution).
- **CI:** new frontend job = typecheck, lint, vitest, bundle-safety
  (degraded, stated), build -- wired into ci.yml; GREEN MEANS CI GREEN
  applies to these cells and this push was watched to green.
- **Validation:** vitest 10/10 (schemas parse the real export; the
  presentation rule; RatingCell renders 'BB (BBB-..BB-)'); tsc/eslint
  clean; next build -> 150 SSG pages; Playwright screenshot of
  /company/ORCL committed to docs/figures/ showing the interval-attached
  letter; python suite 368 passed (unchanged).
- **Follow-ups:** universe filters UI; validation-study page rendering
  validation.json; deploy target for the static export.

### 2026-07-26 - Phase 11: the FastAPI service (offline-first, caveats mandatory)

- **Scope:** services/api (creditrating_api package, Dockerfile, compose),
  tests/api, Makefile serve targets, dev-deps additions, READMEs.
- **Design:** the pydantic domain models ARE the response models; the
  RatingEnvelope composes them with basis, determination, drift regime,
  applicability (code + prose), flags, reason codes and provenance, so the
  API makes it impossible to render a number without its caveat.
  Offline-first: cached tickers only unless the request sets live=true;
  as_of explicitly rejected (vintage snapshots do not exist yet -- refusing
  is honest, serving today's data as history would not be). Async batch on
  a daemon thread with per-company SSE events carrying EM convergence;
  error envelope {code, message, correlation_id} with the structlog run-id,
  no stack traces. Proprietary-absent contract: TTC fields null WITH
  CONVERSION_TABLES_ABSENT, letter withheld -- contract-tested, and
  verified inside the container where local/ genuinely does not exist.
- **Endpoints:** health, companies/search, rate, batch (+status, +SSE
  events), companies/{t}/diagnostics (EM asset path, bootstrap CIs),
  universe (150-name run + filters), validation (phase-9 study), workbook
  export. OpenAPI contract pinned by tests (all ten paths + domain models
  in components).
- **Container:** multi-stage build (wheels then python:3.12-slim), non-root
  uid 10001, fixtures and study data baked in, .dockerignore excludes
  local/ as a red line. Verified live: image builds, boots as 'app',
  /health OK, rate + error envelope correct, workbook flagged absent
  in-container. make serve = compose; make serve-local = uvicorn.
- **Validation:** full suite 368 passed (12 new API tests, offline);
  ruff/black/mypy clean with services/ in scope; container smoke test as
  above; CI watched to green after this push per the CI-green rule.
- **Follow-ups:** SSE per-iteration EM streaming would need a callback in
  em.estimate (today it streams per-company convergence results); job
  registry is in-memory (fine for the demo deployment, a real deployment
  wants a store); phase 12 terminal app.

### 2026-07-26 - CI made green for real: deps declared, golden made local-aware, gate hardened

- **Scope:** requirements split + constraints regen, CI installs from
  declared files only, column-aware golden test, synthetic-grid mechanism
  tests, repository reformat under the pinned toolchain, CLAUDE.md rule.
- **New git rule (owner-directed):** GREEN MEANS CI GREEN -- no ending a
  session or starting a dependent task while the pushed HEAD's CI is failing
  or unknown. Added to CLAUDE.md's git rules; the stale "there is no CI"
  paragraph replaced.
- **The three defects behind 5/7 red cells:**
  1. pydantic/structlog/typer were imported but never declared;
     requirements.txt + requirements-dev.txt now carry everything,
     constraints.txt regenerated from a clean py3.11 env (also fixing the
     lint job's ancient-black click ImportError), workflows install ONLY
     from the files (the pandas matrix axis is the sole exception), and a
     canary test asserts every package import is declared.
  2. The golden workbook test baked in a grid-dependent value; it is now
     column-aware (grid columns asserted equal with local/, asserted NaN
     without -- both real assertions, absent path also monkeypatch-tested
     everywhere), golden regenerated with a producing-environment MANIFEST.
  3. The no-local coverage gate failed at 75% because the licensed grids
     hid the loader/lookup/floor/letter code from CI entirely; seven
     synthetic-workbook tests now exercise the mechanism with made-up
     numbers, no-local coverage 90.8%.
- **Local reproduction of all seven cells before pushing:** lint (pinned
  venv: ruff, black --check, mypy -- clean), tests py3.11 x pandas 2.3.3 and
  x pandas 3.0.5 in from-files-only venvs with the no-local simulation
  (329 passed, coverage 90.8% each), acceptance in a clean no-local workdir
  (offline fixture batch, panels present, 179 passed with the by-design
  grid skips), DEVLOG gate (this entry). The py3.12 pair could not run
  locally (no working 3.12 interpreter on this machine) and is verified on
  CI after the push -- recorded here rather than glossed.
- **Validation:** full local suite 356 passed (with local/); the no-local
  simulations above; CI watched to green after this push per the new rule.
- **Follow-ups:** phase 11 (services/api) next.

### 2026-07-26 - Restructured into packages/core/creditrating (behavior-identical)

- **Scope:** the whole repository layout; ten commits, every one with the
  suite green. Behavior did not change, and that is now a measured fact, not
  a claim -- see the identity check at the bottom.
- **Layout:** `packages/core/creditrating/` with `data/` (providers,
  cleaning, alignment, sectors, cache, provenance + run manifest, pipeline),
  `model/` (em, tic, conversion, config), `tables/` (grid loader +
  structural validation; the grids themselves remain licensed material under
  git-ignored `local/`), `io/` (records, workbook, excel, export),
  `diagnostics/` (uncertainty, domain checks), `cli.py` (typer), `domain.py`
  (pydantic v2 models). Every file moved with `git mv`; renamed siblings are
  import-aliased so function bodies are untouched. `mdt` remains a
  self-locating shim; runtime artifact paths are unchanged via the single
  `_paths.REPO_ROOT` anchor. `services/api` and `apps/terminal` are
  placeholder READMEs for phases 11/12.
- **Deliberate deviation from the target layout:** no `model/merton.py` --
  the Merton inversion IS the E-step of `em.py`, and splitting one algorithm
  across two files to satisfy a filename would hurt the code. Flagged here
  rather than done silently. `model/drift.py` likewise stays inside `tic.py`
  (the regime enum is one screen of code); both can be split later without
  behavior risk.
- **New machinery:** pydantic v2 domain models (CompanyInputs /
  AssetEstimates / RiskMeasures / RatingResult) encoding A > D,
  0 < sigma_A < 3, PD in [0,1], EM <= 20 iters, letter-never-bare; asserted
  loudly-but-non-fatally over every finished batch and fatally at any future
  service boundary. structlog per-run correlation id; every run writes
  `outputs/manifest_<run_id>.json` (sha256 input hashes, package version,
  git SHA, data vintage, config, TIMING_PROTOCOL-10 timestamp). Typer CLI.
  Hypothesis property tests (TiC identity, alpha monotonicity, probability
  bounds, currency-scale invariance). Golden workbook file for the COST
  fixture. Makefile (setup|test|lint|run|batch|serve|demo); `make demo` is
  offline from committed fixtures. ruff + black clean; mypy strict with
  staged per-module overrides on the legacy pandas modules (the override
  list is the debt register). constraints.txt is the exact-pin lockfile;
  pandas deliberately stays a range because CI tests both majors.
- **CI:** ci.yml supersedes tests.yml -- lint job, tests on py3.11/3.12 x
  pandas 2/3 with a >=85% coverage gate on model/tables/diagnostics
  (currently 91%), and an acceptance job that reproduces the methodology
  anchors (Tables 12-14 columns, alpha_FH, CCM*) and the DEFAULT_YEARS
  window-invariance result offline from fixtures, with a guard that those
  tests run rather than skip.
- **OUTPUT IDENTITY CHECK (the gate for this whole change):** the 150-name
  universe was run offline from the same cache at the pre-move commit
  (482f28f, in a detached worktree) and at the new HEAD. Asset (150x35),
  Ratings (150x9) and validation (150x24) sheets compared column-by-column:
  numerics at rtol 1e-12, strings exactly. **IDENTICAL.** Only provenance
  differs (workbook README sheet stamp/SHA; the new manifest file).
- **Aside:** the first push of this series was rejected by our own DEVLOG
  pre-push hook because a git-2.15 incompatibility (`worktree remove`)
  aborted the chain that wrote this entry. The gate caught it. That is the
  gate doing its job, and this machine's git predating `worktree remove` is
  now a known quirk (use `rm -rf` + `git worktree prune`).
- **Validation:** `python3 -m pytest -q` -> 346 passed at every commit in
  the series; `make lint` clean; `make demo` offline; identity check above.
- **Follow-ups:** annotate legacy modules and shrink the mypy override list;
  split drift.py/merton.py if the files grow; phases 11/12.

### 2026-07-26 - Validation study: the model against sourced agency ratings

- **Scope:** `docs/analysis/` (sourced ratings file, study script, four SVGs,
  data CSVs, VALIDATION.md), README results section, docs index, .gitignore
  negation. No pipeline code.
- **Ground truth:** `agency_ratings.csv`, one row per name with source and
  retrieval date (2026-07-26). 14 anchor names press/agency-verified today
  with citations -- including four live corrections to the indicative seeds
  (ORCL cut to BBB- on 2026-07-09; NVDA raised to AA Jun 2026; LUMN raised
  to B- Feb 2026; CCL restored to investment grade). The rest are labelled
  compiled/unverified; 13 names have no public rating and are excluded, not
  imputed. Comparison set: 137 names, 128 with estimates.
- **Discrimination (stratified -- the stratification is the finding):**
  Spearman rho vs the agency ordering 0.787 [90% CI 0.713-0.843] on all 128
  names with estimates; 0.819 on the 77 rated; **0.726 [0.531-0.860] on the
  36 SCALE_RESOLVED names** -- the correlation is not carried by pinned
  letters. Kendall tau 0.58-0.66; Somers' D 0.61-0.69. Within-sector rho
  mean 0.837 (range 0.73-0.95, every sector with n>=8) -- not riding the
  sector effect.
- **Calibration (a property of the letter conversion):** median error **+5
  notches optimistic**, IQR [+3,+6]; 9% within 1 notch, 16% within 2; 42 of
  77 names sit in the model's AAA/AA band that agencies place at A or BBB.
- **Baselines (the honest one):** **DD alone ties RiskScore** (rho 0.779 vs
  0.787 overall; 0.741 vs 0.726 in the resolved stratum -- nominally ahead).
  The marginal ranking value of the TiC construction over its own DD
  ingredient is ~0 on this universe, and VALIDATION.md says so; both beat
  leverage alone (0.632, collapsing to 0.192 within the resolved stratum).
  RiskScore's real advantages (drift-freeness, Girsanov invariance) are
  stability properties, not discrimination properties.
- **Charts** (regenerable, same validated palette): model-vs-agency letter
  histograms (the money chart), rank scatter with SCALE_RESOLVED emphasis,
  notch-error distribution, baseline comparison. Money chart embedded in the
  README results section with the honest summary.
- **Breaking changes:** None.
- **Validation:** `python3 -m pytest -q` -> 322 passed, run before this
  push. Study regenerated end to end from committed inputs; all four SVGs
  rasterized and visually inspected.
- **Follow-ups:** verify more of the compiled ratings; Moody's column is
  sparse; re-run the study at each future universe refresh.

### 2026-07-26 - pandas-3 dtype fix, CI pandas matrix, final phrasing sweep

- **Scope:** `raw_data_architecture/cache.py`, `tests/test_cache.py`,
  `.github/workflows/tests.yml`, README + docs phrasing sweep. No model code.
- **pandas 3 (suite was red on a fresh clone):** parquet round-trips come
  back `datetime64[us]` on pandas >= 2/3 while fresh downloads are `[ns]`;
  pandas 3 raises MergeError when the as-of join mixes them
  (test_currency_gate, test_offline_fixture). Fixed at the one right place:
  `cache._normalize_datetimes` is the dtype chokepoint -- every datetime
  index/column/column-index leaving the cache is coerced to canonical
  `[ns]`, tz preserved, on every load path. Tests assert the contract (a
  round-trip lands on `[ns]` and is a fixed point) rather than
  source-dtype identity, which pandas 3's `[us]` default construction makes
  unstatable. `requirements.txt` stays `pandas>=1.5` deliberately; the CI
  matrix now runs the suite on `pandas>=2,<3` AND `pandas>=3` forever -- the
  red badge is the regression test.
- **Validation:** pandas 2.3.3 (py3.9): 322 passed. pandas 3.0.5 (py3.11
  venv): 322 passed. Both run before this push.
- **Phrasing sweep:** the README heading "...methodology's own thesis..." is
  now "Why the framework itself predicts this result"; every remaining
  thesis/paper/deck occurrence outside code docstrings swept from README,
  CLAUDE.md, GAP_ANALYSIS, the ADRs and reconciliation REPORT
  ("DECIDABLE-BY-PAPER" -> "DECIDABLE-BY-REFERENCE", slide cites -> "ref
  §NN" with the local/ pointer). DEVLOG history entries keep their original
  wording -- this file is a record, not a shop window. The literal filename
  `Market_Based_Credit_Risk_deck.pdf` stays: it names the actual file.
- **Breaking changes:** None.
- **Follow-ups:** the validation study (Part 1 of the current work order).

### 2026-07-26 - The 150-name universe run: taxonomy, two bugs fixed, fixtures

- **Scope:** this push carries the universe run of record and everything it
  surfaced: two data-layer bug fixes (one commit each, failing company as the
  regression fixture), a determination consistency fix, the committed offline
  fixture subset, the analysis outputs, `docs/UNIVERSE.md`, and history/15.
- **Run of record:** 150/150 companies processed, first run **3m50s**
  (all-network, workers=6), cached rerun with 500-rep bootstrap 4m03s
  (CPU-bound). Captured as `history/15_universe_150.csv`; analysis CSVs under
  `docs/reconciliation/universe/`.
- **Failure taxonomy (final):** RATED 85 / MODEL_NOT_APPLICABLE 41
  (12 bank, 5 insurer, 6 REIT, 11 assets-below-total-debt, 7 currency) /
  DEFECTIVE_DRIFT 20 / DATA_UNAVAILABLE 4 (PARA, NKLA, FSR delisted; SATS --
  vendor returns one price row, verified live, not a cache artifact) /
  OFF_SCALE 0 / **BUG 0** after the fixes below.
- **Bugs found by scale (both fixed with named regression tests):**
  1. `REPORTING_CURRENCY_MISMATCH` -- TM (JPY statements, USD prices) made EM
     raise `A <= D`; TSM/BABA/SAP/ASML were silently RATED on the same
     mismatch. Gated, measures suppressed (unit-corrupt), no FX conversion
     attempted; TM cache entry committed as the fixture.
  2. V/MA/PYPL misgated `BANK_DEPOSIT_FUNDED` via the vendor's 'Credit
     Services' string; pinned NONFINANCIAL, ALLY/COF/AXP stay gated.
  3. (consistency) currency-gated names now carry the MODEL_NOT_APPLICABLE
     determination instead of a blank.
- **Findings** (full tables in `docs/UNIVERSE.md`): sigma_A by sector is
  cleanly ordered (Technology median 0.555 ... Utilities 0.141, n=139);
  drift regime VALID 108 / DEFECTIVE 31 (one in five names has a defective
  first-passage regime -- structural, not a small-sample accident);
  determination split SCALE_RESOLVED 39 / floor 29 / scale-top 17 / gated 41
  / NOT_RATED 20 -- only 26% of the universe gets a scale-resolved letter;
  the model letter distribution saturates at AAA/AAA- (51 of 85 rated)
  against an approximate agency distribution centered on A/BBB -- the
  floor-pinning finding made distributional.
- **Fixtures:** the original 10 names + TM + FRED rates committed under
  `data/cache/` (~1.6MB, our own cached vendor responses); the demo and
  `test_offline_fixture.py` run with no network. CLAUDE.md rule 8 and the
  acceptance-gate extension list updated accordingly.
- **Breaking changes:** ADRs filing in non-USD currencies are no longer
  rated (they were silently wrong); V/MA/PYPL are rated again.
- **Validation:** `python3 -m pytest -q` -> 321 passed, run before this push
  (offline-fixture end-to-end test, TM currency-gate end-to-end test,
  classification both-directions tests, cache and isolation tests). Live
  batch + two offline reruns as above.
- **Follow-ups:** sweep the debt-weight convention across the full universe;
  a proper GICS/SIC feed for classification; FX-converted ADR support would
  need a dated FX series, not a spot guess.

### 2026-07-26 - Acquisition cache, parallel/resumable batch, 150-name universe

- **Scope:** Layer 1 (`raw_data_architecture/cache.py`), Layer 2
  (`workflow.py` cache integration + thread-pool runner), `mdt batch
  --workers`, `config/universe.yaml`, `CompanyData.em_error`, tests.
- **Summary:**
  - **Read-through disk cache** under `data/cache/` (parquet frames, JSON
    dicts, per-artifact meta with UTC `fetched_at`): a batch is resumable (a
    rerun refetches only what is missing), offline-runnable once cached, and
    stale entries WARN so a mixed-vintage batch is visible
    (docs/TIMING_PROTOCOL.md ingestion note). Switches: MDT_CACHE_DIR /
    MDT_CACHE_OFF / MDT_CACHE_REFRESH.
  - **Parallel batch:** `RunConfig.workers` / `mdt batch --workers N`;
    per-company isolation is the contract -- a raising ticker is recorded and
    reported, never propagated (and a raiser is by definition a bug, since
    data problems must degrade to statuses).
  - **Symbol fast-path:** config-file tickers no longer cost one resolver
    network call each; only free-text names hit the search API.
  - `CompanyData.em_error` records why EM/measures failed (previously
    log-only, invisible to a batch post-mortem); surfaced in validation
    Warnings.
  - **`config/universe.yaml`: 150 names**, each with a recorded reason and an
    APPROXIMATE agency rating (S&P scale, mid-2026, indicative only, never a
    model input): rating spectrum AAA..CCC-, dual-class, negative book
    equity, banks/insurers/REITs, utilities, ADRs (reporting-currency risk),
    recent IPOs (short history), distressed, and three bankrupt/delisted
    names to exercise the failure paths on purpose.
- **Breaking changes:** None (workers defaults to 1 = historical behavior).
- **Validation:** `python3 -m pytest -q` -> 311 passed, run before this push
  (new: cache round-trips incl. tz-aware index and Timestamp statement
  columns, cache switches, batch isolation at workers=1 and 4).
- **Follow-ups:** run the 150-name batch; failure taxonomy; fixture subset.

### 2026-07-26 - Repositioned referencing; relicensed Apache-2.0

- **Scope:** README, code comments/loggers, LICENSE/NOTICE, pyproject,
  CHANGELOG, docs/README.md. No behavior change.
- **Repositioning (attribution preserved, consolidated):** methodology
  attribution now lives in ONE README section ("Methodology &
  acknowledgements") stating this is an independent implementation of the
  Time-Consistent (TiC) credit-rating methodology (Y. Yang), with equation and
  proposition numbers retained in code docstrings as the attribution
  mechanism. Slide-number citations are replaced by the conventions they named
  (e.g. "the standard KMV default-point convention"); the method table column
  is now "Reference"; the intern-project framing is removed; the
  proprietary-materials note is reworded neutrally ("licensed material, kept
  out of the repository"). Loggers renamed from `pfpa.*` to
  `logging.getLogger(__name__)`. **Attribution was repositioned, not
  weakened** — the acknowledgement also now ships in NOTICE.
- **Relicense MIT -> Apache-2.0** while sole-authored (no external
  contributions to re-license): canonical LICENSE text, new NOTICE carrying
  the methodology acknowledgement, README badge and license section updated,
  CHANGELOG entry. The reference-materials clause stays: licensed third-party
  material, not covered by the project license.
- **Breaking changes:** log record names change from `pfpa.*` to module paths
  (nothing parses them).
- **Validation:** `python3 -m pytest -q` -> 304 passed, run before this push;
  `grep -rn "pfpa\|deck" --include="*.py"` and README grep both clean.
- **Follow-ups:** universe expansion (Parts 1-6 of the current work order).

### 2026-07-26 - Presentation pass 2: figures and the 90-second README

- **Scope:** `docs/figures/` (two scripts, four SVGs, committed data CSVs),
  README restructure, `.gitignore` exception, current-doc number sync. No
  model or pipeline code.
- **Figures** (all SVG, no proprietary content -- letter scales and our own
  computed outputs only; regenerable):
  - `make_figure_data.py` re-ran the study of record live (2,000 moving-block
    replicates, seed 20260726) and writes the committed data CSVs. It
    **reproduces the documented findings**: sigma 0.240, RiskScore 0.480
    (x2.00 exactly), tau median 0.956, p05 0.867, 99.85% >= 0.8. The headline
    amplification lands at **x4,073** vs the recorded x4,077 and PIT width
    ~1,955 vs ~1,960 -- a 4th-significant-digit vendor-revision effect at the
    same 2026-07-24 close. Current docs (README, UNCERTAINTY.md) are synced to
    the regenerated values so text, figures and committed data agree; the
    original values remain in this log's history.
  - `make_figures.py` renders: amplification ladder (log-scale dot plot -- a
    bar chart would misstate lengths on a log axis), rank-stability heatmap
    (sequential one-hue ramp, selective labels), convention sweep (emphasis
    form: T in accent, rest gray -- eight categorical hues would fail CVD
    separation), and the per-company rating-interval strip. Palette is the
    validated dataviz default (accent #2a78d6; ΔE-checked).
  - `convention_sweep_letters.csv` records the 2026-07-26 sweep table; the
    other three CSVs regenerate live.
- **README:** badges (tests, DEVLOG gate, Python, MIT); a four-number
  results-at-a-glance block on the first screen, each line linking to its full
  section; the money chart directly under it; the abbreviated real output of
  `python -m mdt rate COST` in Quickstart; the full three-uncertainty analysis
  moved under "Findings in depth"; all four figures embedded at their
  sections; Tests states that `pip install -r requirements.txt && pytest` is
  the entire fresh-clone story. All prior content preserved.
- **Breaking changes:** None.
- **Validation:** `python3 -m pytest -q` -> 304 passed, run before this push.
  Figure-data run: 10/10 companies, 2,000 replicates each. All four SVGs
  rasterized and visually inspected (label collisions fixed before commit).
- **Follow-ups:** regenerate `docs/figures/data/` and the SVGs when the data
  vintage moves (both scripts are one command each).

### 2026-07-26 - CI coverage measurement

- **Scope:** `.github/workflows/tests.yml`, `.gitignore`. No code.
- **Summary:** the tests workflow now installs `pytest-cov`, runs the suite
  with coverage over the four layers plus `mdt`, prints term-missing to the
  log, and writes the totals to the Actions run summary. Local measurement:
  **61% total** (model layers 90-95%; the network acquisition modules are the
  low end, as expected for an offline suite). A coverage **badge is skipped**:
  every hosted-badge route (Codecov, gist-backed shields) needs an external
  service or a token secret, which is not "straightforward" -- the number
  lives on each run's summary page instead. `.coverage` added to .gitignore.
- **Breaking changes:** None.
- **Validation:** `python3 -m pytest -q --cov=...` -> 304 passed, 61% total,
  run before this push. Workflow YAML is exercised on this push itself.
- **Follow-ups:** none.

### 2026-07-26 - Presentation pass 1: IP spot-check, CLI rating table, warning fix

- **Scope:** `mdt/__main__.py`, `dashboard/submission.py` (one line),
  `dashboard/records.py` (rename to public), this DEVLOG. No model code.
- **IP SPOT-CHECK of the committed deliverables (result: CLEAN).** Both
  workbooks under `docs/deliverables/` were checked sheet by sheet against the
  proprietary material in `local/`: no sheet is grid-shaped (largest is 36x2;
  the grids are 154x93 and the S&P threshold table 27x2), and **zero numeric
  values in any sheet of either workbook match any value in
  `local/tables/sp_thresholds.csv` or the TTC grid** (exact comparison at
  1e-10 rounding, 0/1 excluded). Contents are exclusively our own computed
  company-level outputs, conventions prose, and provenance. No regeneration
  needed; nothing to revert.
- **CLI:** `python -m mdt rate <TICKER>` now prints a sectioned, aligned table
  (INPUTS / MODEL / CREDIT MEASURES / RATING / FLAGS) that follows the
  presentation rule -- RiskScore leads the credit block, the letter appears
  only with its interval or the reason there is none -- and surfaces every
  flag (weak identification with t, drift regime, applicability with reason
  code, off-grid clamp, floor determination, contradictory debt source). All
  fields project from `dashboard.records` (`rating_with_interval` made public
  for this), so the CLI cannot drift from the workbook. The per-ticker report
  filename now carries a UTC stamp so the never-overwrite guard does not trip
  on a second run.
- **Warnings:** the openpyxl `StyleProxy.copy(**kwargs)` deprecation in
  `submission.py` is fixed by constructing a fresh `Alignment`; the suite now
  passes with that warning escalated to error
  (`-W "error:Call to deprecated function copy:DeprecationWarning"`).
- **Breaking changes:** None (CLI output format changes; no consumer parses it).
- **Validation:** `python3 -m pytest -q` -> 304 passed, run before this push;
  0 occurrences of the deprecated-copy warning (was ~360). Live
  `python3 -m mdt rate COST` run to verify the new table renders.
- **Follow-ups:** presentation pass 2 -- CI coverage, figures, README
  restructure.

### 2026-07-26 - Deliverable v1 frozen

- **Scope:** Layer 4 (submission writer, records), Layer 2 (provenance columns
  through the as-of join), `docs/TIMING_PROTOCOL.md` §10, CLAUDE.md,
  `.gitignore`, CHANGELOG, tests; then the frozen artifact itself under
  `docs/deliverables/` with a DIFF.md, and the `deliverable-v1` tag.
- **Summary:**
  - **Team timestamp standard adopted** (`docs/TIMING_PROTOCOL.md` §10,
    owner-directed): new artifact stamps are tz-aware UTC ISO 8601; filenames
    use the compact `YYYYMMDDTHHMMSSZ` form. First applied to the submission
    filename and the workbook's `Generated (UTC)` field. Existing artifacts
    are not restamped; naive-local writers migrate when next touched.
  - **Writer:** the single writer gains a never-overwrite guard (an existing
    path raises) and a `Ratings` sheet implementing the presentation rule —
    sorted by RiskScore, the letter only ever with its interval attached or
    with the reason there is none.
  - **Validation sheet** now carries drift regime and t, the bootstrap rating
    interval, the convention span from the 2026-07-26 sweep (a dated, recorded
    result — regenerate via the script if the vintage moves; unswept tickers
    report no span), explicit `TTC at floor` / `At scale top` flags, EM
    iterations, and debt field provenance (`ShortTermDebtSource` /
    `LongTermDebtSource` carried through the as-of join, with the
    CONTRADICTORY flag).
  - **README sheet** now states the applicability gates (both of them, with
    reason codes), the sweep range of the debt-weight convention, which
    conventions have NOT been swept, how to read span-vs-interval, and the
    Ratings-sheet reading rule, alongside the existing model version, git SHA,
    data vintage, conventions, and canonical-columns deviation note.
  - **Archive:** `docs/deliverables/` holds the frozen v1 workbook beside the
    pre-look-ahead version (`submission_20260725_234922.xlsx`, identified by
    content match against `history/07`) and a `DIFF.md`. `.gitignore` gains a
    narrow `!docs/deliverables/*.xlsx` exception, mirroring the reconciliation
    CSV one; CLAUDE.md's acceptance-gate line updated to match.
- **Breaking changes:** submission filenames change format
  (`submission_YYYYMMDDTHHMMSSZ.xlsx`); VALIDATION_SCHEMA gains five columns;
  the workbook gains a Ratings sheet. Consumers keyed to the old validation
  layout must re-key.
- **Validation:** `python3 -m pytest -q` -> 304 passed, run before this push
  (new tests: UTC stamp format, overwrite guard raises, Ratings ordering and
  never-bare letters, validation freeze diagnostics). Live batch re-run from
  the freeze commit to generate the artifact; 10/10 succeeded; standing
  unchanged from `history/14` (7/10 rated, 3/10 scale-resolved, PNC gated).
- **Follow-ups:** `lineage.py` still stamps naive local time (migrate on next
  touch); the sweep span constant must be regenerated if the data vintage
  moves; deposits source and GICS/SIC feed remain open from ADR 0003.

### 2026-07-26 - Live batch confirms the revision-1 standing; history/14 captured

- **Scope:** README standings, `docs/reconciliation/history/14_after_dell_market_gate.csv`.
  No code.
- **Summary:** live batch re-run (`python3 -m mdt batch config/companies.yaml`,
  10/10 succeeded, prices through the 2026-07-24 close) confirms the expected
  post-revision standing exactly: **7/10 rated, 3/10 SCALE_RESOLVED (DELL,
  ORCL, T)**, 3 PINNED_AT_SCALE_TOP (COST, KO, WMT), 1 PINNED_AT_FLOOR (AMZN),
  **1 MODEL_NOT_APPLICABLE (PNC, BANK_DEPOSIT_FUNDED)**, 2 NOT_RATED (INTU,
  KHC). DELL rates A- on GRID_INTERIOR with drift t = 2.01 and a 10-notch
  interval (AAA..BBB) — rated again, and still the widest letter interval in
  the universe, which is the scale-vs-precision distinction working as
  documented. The Asset sheet is captured as `history/14`; README standings
  table updated with a note recording the brief DELL gating and pointing to
  ADR 0003 Revision 1.
- **Breaking changes:** None.
- **Validation:** `python3 -m pytest -q` -> 300 passed, 0 skipped (network
  tests ran; `local/` present), run before this push. Live batch run as above;
  invariants held across the 10-company batch.
- **Follow-ups:** deliverable v1 freeze.

### 2026-07-26 - The three uncertainty sources presented side by side

- **Scope:** documentation only — `docs/UNCERTAINTY.md` and the README results
  section. No code, no output changes.
- **Summary:** the second finding is now documented with the same care as the
  first. Both documents present the three uncertainty sources side by side:
  **parameter** (bootstrap; DELL 10 notches, PD chain amplifies drift noise
  ×4,077 vs RiskScore), **convention** (debt-weight sweep; T moves 7 notches on
  the weight alone; convention span >= parameter span for ORCL, PNC and T), and
  **specification** (PNC: AAA under standard D vs BB under total liabilities
  against an actual agency A/A2 — the conventions bracket the truth without
  landing on it; the model was looking at 6% of what PNC owes, and the honest
  output is a gate, not a wider interval). Both state the combined conclusion:
  the letter is dominated by drift noise AND an arbitrary convention; RiskScore
  and the rank ordering are robust to both — and the scale-pinned names
  (COST/KO/WMT, span 1 under every weight) are themselves the demonstration
  that a pinned letter carries no information.
- **Breaking changes:** None.
- **Validation:** `python3 -m pytest -q` -> 270 passed, 30 skipped, run before
  this push. Documentation-only change; the suite guards against accidental
  code edits.
- **Follow-ups:** README standings table still shows the pre-revision counts;
  updated in the next commit alongside the history/14 capture.

### 2026-07-26 - DELL objection accepted: market-based test replaces the negative-equity gate

- **Scope:** Layer 2 (`sectors.py`, `workflow.py`), tests, ADR 0003. Changes
  which companies are rated.
- **Summary:** the project owner accepted the DELL objection recorded in ADR
  0003 — negative book equity is a quantity the market-based model never uses,
  and gating on it removed the best-identified name in the universe (drift
  t = 2.01). `sectors.applicability` now gates on firm type only; the
  capital-structure test is the new `sectors.market_applicability`, run after
  EM: applicable iff `A > ST + 1.0*LT` (strict). The margin is the most
  conservative debt-weight convention, so applicability is invariant to the
  arbitrary long-term weight the convention sweep indicted; the full argument,
  the original spec, the objection and the resolution are in ADR 0003
  "Revision 1". Firm-type gates (BANK/INSURER/REIT) unchanged; PNC stays gated
  as `BANK_DEPOSIT_FUNDED`. Reason code `NEGATIVE_BOOK_EQUITY` is replaced by
  `ASSETS_BELOW_TOTAL_DEBT`.
- **Expected standing** (to be confirmed by the next live batch run): rated
  7/10, scale-resolved 3/10 (DELL, ORCL, T); MODEL_NOT_APPLICABLE 1 (PNC).
  DELL passes the market test with A ≈ $301bn against ≈ $31bn total debt
  (2026-07-26 archived run, `history/13`).
- **Panel reconciliation (housekeeping):** the tracking panel again showed
  Part B and Part C open although both results shipped (pushes of 2026-07-26,
  `history/12`/`history/13`). Cause of the recurring staleness: the panel's
  Part B/C entries are not linked to any repository issue — `gh issue list`
  shows no open issues and no issue titled "Part B"/"Part C" — so no commit,
  close keyword, or automation can ever move them; additionally this agent's
  GitHub token lacks the `project` scope (`gh project list` → "missing
  required scopes [read:project]"), so agent sessions cannot update the board
  even on request. Until the cards are linked to issues (or the scope is
  granted with `gh auth refresh -s project,read:project`), the panel will go
  stale after every push and must be moved by hand.
- **Breaking changes:** DELL is rated again; rated coverage 6/10 -> 7/10. The
  `sectors.applicability` signature drops its `total_equity` parameter.
- **Validation:** `python3 -m pytest -q` -> 270 passed, 30 skipped, run before
  this push (30 skips are network-dependent tests; the grid tests run, since
  `local/` is present in this environment). New/updated tests in
  `tests/test_sectors.py` cover the market test (DELL-shaped pass, in-band
  gate, strict boundary, missing-input non-gating) and the signature change.
  Live batch not yet re-run; standings above are therefore labelled expected.
- **Follow-ups:** live batch re-run to confirm the 7/10 standing and capture
  `history/14`; README standings table update; deliverable v1 freeze.

### 2026-07-26 - README standings updated for the gate

- **Scope:** README only. No code.
- **Summary:** the determination table now shows the post-gate standing (2
  SCALE_RESOLVED, 3 scale-top, 1 floor, 2 MODEL_NOT_APPLICABLE, 2 NOT_RATED)
  and carries the PNC evidence -- $33.3bn against $539.4bn of liabilities,
  AAA under the shipped rule and BB under total liabilities, against an actual
  A/A2 agency rating.
- **Validation:** `python -m pytest -q` -> 294 passed, run before this push.

### 2026-07-26 - Financial firms, default-point variants, applicability gate (#16)

- **Scope:** Layers 1-2 (new `sectors` module, provenance columns, default-point
  variants) and Layer 4 (three new Asset columns). Changes which companies are
  rated. Closes #16.
- **Summary:**
  - #16: `pick_row_named` reports which candidate line item matched;
    `split_term_debt` emits `ShortTermDebtSource`, `LongTermDebtSource`,
    `TotalDebtSource` and `DebtSourceContradictory`. The `.clip(lower=0)` stays
    -- the alternative is negative debt -- but it no longer hides a source that
    disagrees with itself.
  - `transforms.default_point_variants` returns `standard`,
    `total_liabilities` and `total_liabilities_ex_deposits` side by side.
    `DEFAULT_POINT_VARIANT` selects the rated one; it stays `standard`. A
    variant that cannot be computed is **absent**, never silently substituted.
  - `data_cleaning/sectors.py`: firm-type classification (override map, then
    industry, then sector) and an applicability gate returning machine-readable
    reason codes. The gate suppresses the **rating**, not the measures.
- **Evidence of record -- PNC against its actual A / A2 agency rating:**
  - `standard`: D = $33.3bn, 6.2% of liabilities, DD 9.31 -> **AAA**
  - `total_liabilities`: D = $539.4bn, 100%, DD 3.93 -> **BB**
  - `total_liabilities_ex_deposits`: **not computable** -- the free tier has no
    deposits row for PNC, which is the variant most likely to be right.
  - The convention choice spans AAA to BB and brackets the true rating without
    landing on it. No choice of barrier rescues the model here, which is the
    argument for the gate rather than for a better default point.
- **Breaking changes:** DELL and PNC are no longer rated. Rated coverage 8/10 ->
  6/10; scale-resolved 4 -> 2. Asset sheet gains three columns.
- **Validation:** `python -m pytest -q` -> 294 passed, run before this push, of
  which 23 are new in `tests/test_sectors.py` covering classification,
  the gate, PNC under every variant, and the #16 provenance and contradiction
  flags. Live batch re-run, captured to
  `docs/reconciliation/history/13_after_partC_financials.csv`.
- **Flagged, not smoothed over:** DELL is gated for `NEGATIVE_BOOK_EQUITY`, and
  that is probably wrong. Its negative book equity is a post-EMC buyback
  artifact, not distress; the model uses market-implied asset value and book
  equity does not enter the calculation. The gate was implemented as specified
  and the objection is recorded in ADR 0003. Note DELL had the strongest drift
  t-statistic in the universe (2.01), so this removed the best-identified
  estimate we had.
- **Follow-ups:** revisit the negative-equity threshold; find a deposits source;
  replace the ~20-name override map with a GICS/SIC feed.

### 2026-07-26 - Convention uncertainty sweep

- **Scope:** new analysis script under `docs/reconciliation/`; README and
  UNCERTAINTY.md updated with the result. No pipeline code, no model output.
- **Summary:** `docs/reconciliation/convention_sweep.py` sweeps the long-term
  debt weight over {0, 0.25, 0.5, 0.75, 1.0} and the statement vintage, and
  reports the resulting rating range per company on the same notch scale as the
  bootstrap interval.
- **Findings of record:**
  - **For three of the four scale-resolved names -- ORCL, PNC and T -- the
    convention span equals or exceeds the bootstrap span.** T moves seven
    notches (AAA- to A-) on the debt weight alone; ORCL moves from unrateable
    to B+. The published letter is at least as much a statement about the 0.5
    weight as about the company.
  - PNC and AMZN yield `D = 0` at w = 0 because their short-term debt is zero.
    For AMZN that is real; for PNC it is the missing current-debt row (#16), so
    PNC's entire default point is the long-term weight.
  - INTU and KHC are unrated under every convention -- a robustness result,
    since their defective drift is not an artifact of the debt rule.
  - The scale-pinned names (COST, KO, WMT) do not move at all, span 1. A pinned
    letter is insensitive to its inputs, which is why it carries no information.
  - Consequence: total uncertainty on a letter is **wider** than the bootstrap
    interval, and the bootstrap is correctly labelled a lower bound.
- **Validation:** `python -m pytest -q` -> 271 passed, run before this push. The
  sweep itself is an analysis script, not covered by the suite; its output is
  committed as `convention_sweep.csv` is git-ignored, so the table lives in the
  README.
- **Follow-ups:** Part C (financial firms, #16) not started.

### 2026-07-26 - Documentation rewritten around the decomposition finding

- **Scope:** documentation only. No code, no model output.
- **Summary:**
  - `README.md` gained a "Results: what survives uncertainty, and what does
    not" section leading on the two-sided headline: RiskScore's interval is
    exactly 2.00x sigma's (the square, unamplified) and rank ordering is stable
    (Kendall tau median 0.956), while TTC PD is 3.2x RiskScore and PIT PD
    4,077x. Both honesty points are stated in the section rather than in a
    footnote: 48% relative width is unamplified, NOT tight; and the ordering
    shuffles in the genuinely-close middle (INTU holds its exact rank in 35% of
    replicates).
  - Framed as an independent numerical demonstration of the paper's own thesis,
    citing Prop. 4.4.2 and the Eq. (11) -> Eq. (12) cancellation for why TiC is
    Girsanov-invariant, and Eq. (13) for where the amplification enters.
  - Added the presentation rule: a letter is a derived, wide-interval
    conversion, never a headline, and always carries its interval and flags.
    ORCL is written `BB (BBB-..BB-, unrateable in ~44% of replicates, weakly
    identified: t = 0.08)` and never bare. Stated in README,
    RATING_DETERMINATION.md and UNCERTAINTY.md so it binds the API and UI too.
  - Added `docs/UNCERTAINTY.md`: method, stated limits, findings, and the bug
    episode written as it happened.
  - `docs/RATING_DETERMINATION.md` reworked for the rename and to separate three
    questions that were being conflated: which route produced a number (basis),
    whether the scale could resolve it (determination), and whether the estimate
    is precise (drift t and the interval).
- **The episode is recorded, not smoothed over:** the algebraic prediction
  (`TiC = CCM/mu = sigma^2/ln^2(A/D)`, so RiskScore must be drift-free) was
  tested, it failed, and the failure was ours -- drift-conditioned selection on
  a drift-free quantity, and a bootstrap that resampled a different window than
  the estimator uses. The previously published intervals were too narrow; DELL
  was reported as 8 notches and is 10. Prediction-testing stays in the workflow,
  and UNCERTAINTY.md says why: an algebraic identity is a free test oracle that
  needs no reference dataset, and it caught in minutes what a 267-test suite did
  not.
- **Validation:** `python -m pytest -q` -> 271 passed, run before this push.
- **Follow-ups:** Part B (convention uncertainty sweep) and Part C (financial
  firms, #16) not started.

### 2026-07-26 - Rename MODEL_DETERMINED -> SCALE_RESOLVED

- **Scope:** `RatingDetermination` enum value and the docstrings that define
  the vocabulary. No logic changed; the classification function is identical.
- **Why:** the label answers "could the scale tell this value from its
  neighbours?", not "is this estimate precise?". DELL makes the difference
  concrete -- it has the strongest drift t-statistic in the universe (2.01) and
  the *widest* bootstrap letter interval (10 notches), because it sits where the
  S&P scale is finely notched. Calling that MODEL_DETERMINED implied a precision
  claim the classification never made, and the two questions are answered by
  different fields: determination by the scale, precision by `Drift t` and the
  rating interval.
- **Breaking changes:** the `Rating Determination` column now emits
  `SCALE_RESOLVED` where it emitted `MODEL_DETERMINED`. Any consumer matching
  the old string will stop matching. Historical DEVLOG, CHANGELOG and ADR
  entries keep the old name -- they record what was true when written.
- **Validation:** `python -m pytest -q` -> 271 passed, run before this push.
  Two new tests pin the new vocabulary and assert the old attribute is gone.

### 2026-07-26 - Two bootstrap bugs found by decomposing the uncertainty result

- **Scope:** `signal_construction/bootstrap.py`. Changes every interval this
  module reports. No point estimate and no rating moved.
- **Why this was looked at:** "no rating survives uncertainty" is a suspicious
  finding, and the algebra makes a falsifiable prediction -- TiC = CCM/mu =
  sigma^2/ln^2(A/D), so RiskScore is drift-free and its interval should be
  exactly what sigma implies. Checking that prediction found two bugs.
- **Bug 1: drift-conditioned selection on drift-free quantities.** `risk_score`
  was recorded *after* the `continue` on a DEFECTIVE replicate, so its
  distribution was conditioned on `drift > 0`. That is not a neutral filter:
  `drift = eta - sigma^2/2`, so a larger sigma makes DEFECTIVE more likely and
  the surviving replicates were a sigma-truncated sample. Worst for the very
  companies where it matters -- ORCL 44% defective, KHC 73%. `risk_score`,
  `tic`, `dd` and `edf` are now recorded for every replicate.
- **Bug 2: the bootstrap did not mirror the estimator.** It resampled the full
  ~5y span and computed sigma from all of it, while the pipeline estimates
  sigma from the trailing 252 days. For COST that is 0.231 against the
  pipeline's 0.195 -- a different estimator, and a narrower one, since it had
  ~5x the observations. Taking a trailing slice of a full-span resample does
  not fix it either: a moving-block resample draws blocks uniformly, so every
  slice is the same regime-mixture. Each parameter is now resampled from the
  window its own estimator uses.
- **Correction of record:** last session's DEVLOG entry claimed "bootstrap
  calibration checked: replicate medians track the point estimates". That check
  was wrong -- it compared a full-span sigma median (0.2288) against a
  trailing-252 point estimate (0.1952) and read the gap as agreement.
- **Validation:** `python -m pytest -q` -> 269 passed, run before this push.
  Two new tests pin both fixes: one asserts the replicate median tracks the
  pipeline sigma on a path whose recent volatility differs sharply from its
  full-span volatility, the other that RiskScore is recorded in every replicate
  while mu is not.
- **Effect on the reported numbers:** intervals widen. Median relative width on
  RiskScore 0.441 -> 0.479; DELL's letter span 8 -> 10 notches; ORCL 4 notches
  but shifted to BBB-..BB-. The qualitative conclusion is unchanged.
- **Findings:** RiskScore's relative interval width is 2.00x sigma's, exactly as
  differentiating sigma^2 predicts -- no excess instability enters before the
  conversion. PIT PD's is 4077x RiskScore's. Rank ordering on RiskScore is
  stable (Kendall tau median 0.956; 99.9% of replicates >= 0.8).

### 2026-07-26 - Data-layer hardening: #17, #18, #20

- **Scope:** Layers 1-2 defensive changes plus provenance fields. No formula
  changed and no rating moved. Closes #17, #18, #20. #16 deliberately left open.
- **Summary:**
  - #17: `reference_shares` now returns `(shares, method)` and the workflow
    records `shares_reference_date`, satisfying TIMING_PROTOCOL §3's condition
    that a constant-share assumption store its reference date. The
    `sharesOutstanding` fallback is labelled `single_class` and warns, because
    for a dual-class issuer it is a different quantity from market cap / price
    -- the case the primary method exists to handle.
  - #18: the risk-free series is range-checked after unit conversion and raises
    if it lands outside [0, 0.30]; a missing `Adj Close` is NaN rather than the
    unadjusted `Close`; the FRED date column is located by name with a logged
    positional fallback.
  - #20: `_cache_csv`, the parquet write, the xlsx write and the yfinance
    version probe now catch specific exceptions and report at WARNING. The
    version probe records "unknown" rather than "?".
- **Honest limit recorded in code and test:** the *opposite* rate-units error --
  a series already in decimals, divided again -- cannot be caught by a band,
  because 0.05/100 = 0.05% is a rate the 1-year Treasury has genuinely printed.
  It warns as "suspiciously low for a percent series" instead, and a test pins
  that we do not claim to detect it.
- **Breaking changes:** `transforms.reference_shares` returns a tuple.
- **Validation:** `python -m pytest -q` -> 267 passed, run before this push.
  Live batch re-run; all ten ratings, determinations and weak-identification
  flags are byte-identical to the previous run, confirming these are defensive
  changes only. Captured to `docs/reconciliation/history/12_after_partD.csv`.
- **Follow-ups:** #16 (field-selection provenance and the `.clip(lower=0)` that
  hides PNC's contradictory ST = 0) left open for the financial-firms work. The
  README still presents ORCL's BB without its interval.

### 2026-07-26 - Workbook README sheet

- **Scope:** Layer 4 only. No model output changed.
- **Summary:** the submission workbook now opens on a README sheet carrying
  provenance (generation time, model version, git SHA with a `-dirty` marker,
  data vintage, the statement dates actually used), the conventions in force
  (total-return equity construction, NaN-not-zero dividends, `available_at`
  alignment with its lag constants, default point, LT debt field, share method,
  both estimation windows, outlook direction), how to read the four basis and
  four determination values, and an explicit statement of the Asset sheet's
  deviation from the reference 23-column layout.
- **Breaking changes:** the workbook has three sheets rather than two; README
  is first. Anything reading sheet-by-position rather than by name will move.
- **Validation:** `python -m pytest -q` -> 263 passed, run before this push.
  Three new tests assert README is the first sheet, that the provenance and
  convention fields are present, and that both column blocks are listed by
  name. Live batch re-run, captured to
  `docs/reconciliation/history/11_after_partC_readme.csv`.
- **Follow-ups:** Part D (#17, #18, #20) is not started. The README still
  presents ORCL's BB without its interval.

### 2026-07-26 - Bootstrap uncertainty propagation; WEAKLY_IDENTIFIED

- **Scope:** Layer 3 (new `bootstrap` module, weak-identification test) and
  Layer 4 (six new Asset columns, three new validation columns). No formula
  changed; every point estimate is identical.
- **Summary:**
  - Added `signal_construction/bootstrap.py`: a moving-block bootstrap over the
    EM-recovered **asset** returns, block length `n^(1/3)`, propagated through
    measures and conversion to give distributions of sigma_A, eta, drift, mu,
    CCM, RiskScore, PIT PD, TTC PD and the implied notch. `A_0` and `D` are
    held fixed because they are observations, not estimates; the intervals are
    therefore parameter-estimation intervals and a lower bound on total
    uncertainty, which the module docstring states.
  - Added `measures.is_weakly_identified` (`|t| < 2`). It **annotates** a
    rating and never suppresses one. `drift_regime` is unchanged: `DEFECTIVE`
    still means only the Prop. 4.4.1 violation `drift <= 0`.
  - Asset sheet gained `Drift SE`, `Drift t`, `Weakly Identified` and the
    three `Rating Interval` columns; validation gained the bootstrap defective
    share and the sigma 5/95 band.
  - ADR 0002 updated: a fixed `k*SE` threshold was **considered and rejected**,
    with the reasoning recorded.
- **Breaking changes:** the Asset sheet is now 32 columns (23 canonical + 9
  additions) and validation 17. Golden schema tests updated. Batch runtime is
  roughly 4s/company higher from 500 bootstrap replicates; `RunConfig` gained
  `run_bootstrap` to switch it off.
- **Validation:** `python -m pytest -q` -> 260 passed, run before this push.
  Bootstrap calibration checked: replicate medians track the point estimates.
  Live batch re-run and captured to
  `docs/reconciliation/history/10_after_partA_bootstrap.csv`.
- **Findings of record:**
  - **7 of 10 companies are WEAKLY_IDENTIFIED.** Only DELL (2.01), PNC (2.07)
    and WMT (2.01) clear |t| = 2, and all three within 0.1 of it.
  - **ORCL's BB is not supportable as a point rating.** The drift goes negative
    in 40.6% of replicates, so the company is unrateable in nearly half of
    them; where it is rateable the interval spans BBB..BB, four notches.
  - **No model-determined name has a tight interval.** DELL has the strongest
    t and the widest interval (8 notches). T spans 5, PNC 4.
- **Follow-ups:** the README still presents ORCL's BB as a model result and
  needs revising; Part C (workbook README sheet) and Part D (#17, #18, #20)
  are not done.

### 2026-07-26 - Make the push gate enforceable

- **Scope:** repository tooling only. No application code, no model output.
- **Summary:**
  - Added `.githooks/pre-push`, which rejects a push whose outgoing commit
    range does not touch this file. It prints the offending commits and quotes
    the gate from `.agents/README.md`. `ALLOW_MISSING_DEVLOG=1` bypasses it and
    says loudly that it did.
  - Added `scripts/install-hooks.sh`, which copies hooks into `.git/hooks/`
    rather than setting `core.hooksPath` -- changing git config is the owner's
    call under CLAUDE.md's git rules, so the shareable option is documented but
    not applied.
  - Added `.github/workflows/devlog.yml`, the same check server-side so a local
    bypass still surfaces, and `.github/workflows/tests.yml`, which runs the
    offline suite on push and PR. This is the repository's first CI.
- **Motivation, recorded in the hook itself:** the gate existed but was enforced
  by remembering it. Five pushes went out without an entry on 2026-07-25
  (`9447d81`, `03a0bf8`, `75b0373`, `f9deb33`, and one earlier in that session).
  They were recorded after the fact rather than backfilled quietly; this makes
  the failure mode impossible rather than merely noted.
- **Breaking changes:** a push with no DEVLOG entry now fails locally once
  `scripts/install-hooks.sh` has been run, and fails in CI regardless.
- **Validation:** `python -m pytest -q` -> 260 passed. Hook verified by
  attempting a real `git push --dry-run` with a DEVLOG-less commit: rejected
  with a non-zero exit and the commit listed. This entry is the positive case.
- **Follow-ups:** `git config core.hooksPath .githooks` would make the hook
  apply without the install step; left for the owner to decide.

### 2026-07-25 - Data-layer fixes, rating-determination accounting, issue reconciliation

Covers commits `9447d81`, `03a0bf8`, `75b0373`, `f9deb33`. These were pushed
before this entry was written, which is a breach of the push gate in
`.agents/README.md`; recording it here rather than quietly backfilling.

- **Scope:** Layer 2 (equity series, statement alignment) and Layer 4
  (determination reporting). Changes model output. Closes #15 and #19.
- **Summary:**
  - #15: replaced `Close + Dividends.cumsum()` with a reinvested total-return
    index anchored at the valuation date. The old level depended on how far
    back the download reached, so `DEFAULT_YEARS` was silently setting the
    level of the series every EM fit runs on. Removed `.fillna(0.0)` on
    dividends; missing is not zero.
  - #19: statements are aligned on `available_at` (period end + 45d for a 10-Q,
    90d for a 10-K) rather than period end, with
    `availability_method="estimated_lag"`. Added the `StatementPeriodEnd` and
    `StatementAvailableAt` audit fields (TIMING_PROTOCOL §8) and five canary
    tests, including a red-first pin that a period-end join leaks.
  - Part B: added `RatingDetermination` (MODEL_DETERMINED / PINNED_AT_FLOOR /
    PINNED_AT_SCALE_TOP / NOT_RATED) to the Asset and validation sheets, the
    README, and `docs/RATING_DETERMINATION.md`.
  - Measured the ADR 0002 k*SE rule against the run and recorded the coverage
    cost. Not switched on.
  - Closed GitHub issues #3-#14, which had been left open although all twelve
    fixes had landed. Verified each against its commit before closing.
- **Breaking changes:** `build_panel` takes a new `available_at` argument
  (defaults to None, which preserves the old period-end join for callers that
  do not pass it -- the tests rely on that to pin the defect). The Asset sheet
  gained `Rating Determination`; the validation sheet gained four columns.
- **Validation:** `python -m pytest -q` -> 260 passed, run before every push.
  Test count 217 -> 260. Live batch re-run after each fix and captured to
  `docs/reconciliation/history/07`, `08` and `09`.
- **Findings of record:**
  - sigma_A and A are now bit-identical across 2/4/6-year download windows.
    AMZN, which pays no dividend, is unchanged to every digit by #15 -- the
    control that shows the fix does what it claims.
  - The rating is NOT unconditionally window-invariant, and should not be: the
    drift is deliberately estimated over the whole available span. The
    acceptance test therefore compares windows of equal drift span.
  - #19 moves the valuation-date default point for exactly one company (T,
    -4.69%), because only T has a statement inside its filing window today.
  - The analytical route took rated coverage 5 -> 8 and added zero
    model-determined names. All three additions are pinned at the scale top.
- **Follow-ups:**
  - Part C's bootstrap (block-resampled uncertainty propagation) is NOT built;
    only the k*SE table was produced.
  - Part D (#16, #17, #18, #20) is untouched.
  - The workbook README sheet and the canonical-column reordering are not done.

### 2026-07-25 - Rating basis: stop publishing clamped values as ratings

- **Scope:** Layer 3 conversion, Layer 4 validation sheet; changes which
  companies receive a rating. Closes #12.
- **Summary:**
  - Added `RatingBasis` (GRID_INTERIOR / ANALYTICAL / OFF_GRID /
    NOT_APPLICABLE). `conversion.ttc_pd` returns the basis with every lookup.
  - An off-grid `(CCM, mu)` now returns NaN with basis OFF_GRID instead of the
    clamped edge value, and `workflow` reports no letter for it. A defective
    drift regime returns NOT_APPLICABLE, a distinct state from off-grid.
  - Added `ttc_floor`, `is_floor_determined` and the `ttc_at_floor` flag. The
    shipped grid floors at 2bp and its next distinct cells differ only in the
    fifth significant figure, so a 5% band above the floor counts as saturated.
  - The validation sheet now carries drift regime, drift SE, drift span,
    rating basis and the floor flag.
- **Breaking changes:** COST, KO and WMT are no longer rated (OFF_GRID); they
  previously received AAA- from a clamped edge cell.
- **Validation:** `python -m pytest -q` -> 32 passed, run before this push.
  Live batch re-run; Asset sheet captured as
  `docs/reconciliation/history/03_after_12_rating_basis.csv`.
- **Follow-ups:** the ANALYTICAL basis is defined but unreachable until Eq. (27)
  is implemented (#11); until then off-grid points have no rating at all.

### 2026-07-25 - Drift estimation: remove abs(), split the estimation windows

- **Scope:** Layers 1-3 and the CLI; changes model output. Closes #3 (a, b, c).
- **Summary:**
  - Removed every `abs()` on `eta - sigma_A^2/2`. Eq. (11) uses the signed
    drift; Prop. 4.4.1 assumes it is positive.
  - `em.estimate` now takes sigma_A from the trailing `EM_WINDOW_DAYS` (252)
    and eta from the full `DRIFT_WINDOW_DAYS` (1260, ~5y) span, and reports
    `drift_se` and `drift_span_years`.
  - Added `DriftRegime` (VALID / DEFECTIVE). A defective regime emits NaN for
    mu / CCM / PIT / TTC / rating with a `drift_regime` flag on `CompanyData`,
    instead of substituting a magnitude. DD, EDF, TiC and RiskScore survive.
  - Root cause of the short drift span, found while measuring:
    `default_point_debt()` filled missing debt with `0` rather than `NaN`, so
    every day before the earliest statement asserted zero debt; EM filters on
    `D > 0` and dropped them, capping the span at ~1.2y. Fixed.
  - `mdt --years` no longer hard-codes `2` over `DEFAULT_YEARS`; `DEFAULT_YEARS`
    raised 2 -> 6; the debt schedule now unions quarterly and annual balance
    sheets rather than choosing one.
  - Added `docs/adr/0001-drift-estimation.md` with the before/after table and
    the evaluation of the risk-neutral variant (documented, not adopted).
  - Added `docs/reconciliation/history/` with per-fix Asset-sheet snapshots, and
    a narrow `.gitignore` exception so those snapshots are tracked. Everything
    else under `docs/reconciliation/` stays ignored.
- **Breaking changes:** INTU and KHC no longer receive a rating; they report
  NOT_APPLICABLE. Missing debt is now NaN, so a company with no statement
  history produces no panel rows rather than a zero-debt panel.
- **Validation:** `python -m pytest -q` -> 27 passed, run before this push.
  Live 10-company batch run twice (before and after the debt fix) and both
  Asset sheets captured under `docs/reconciliation/history/`. Drift spans
  confirmed at 2.7-4.9y after the fix, against 1.1-1.3y before.
- **Follow-ups:**
  - 2 of the 4 negative-drift names turned positive (ORCL, T). INTU and KHC
    remain negative but within one standard error of zero.
  - `drift_se` is computed and reported but nothing consumes it; widening
    DEFECTIVE to "not significantly positive" is an owner decision.

### 2026-07-25 - Repository audit and issue backlog

- **Scope:** documentation only; `docs/GAP_ANALYSIS.md` rewritten and twelve
  GitHub issues opened. No source file was modified and no behavior changed.
- **Summary:**
  - Rewrote `docs/GAP_ANALYSIS.md` as a concept -> equation -> file:function ->
    status map over the fourteen paper results requested, using an explicit
    correct/partial/missing/wrong vocabulary, after reading every file in the
    repository and re-checking each equation against the paper.
  - Corrected two statements of `Outlook = S&P TTC - PIT PD` in that file:
    Eq. (28) is `PD_FH - S&P TTC`, which is what the code computes.
  - Corrected the Eq. (1)-(2) row, previously marked "implemented". Only the
    first-passage closed form of Eq. (11) exists; the definitional
    `CCM = E[tau]*E[1/tau] - 1` is not implemented anywhere.
  - Opened issues #3-#14 covering the negative-drift violation, the Eq. (13)
    overflow branch, linear-space CDF evaluation, the unreachable analytical
    conversion route, the Asset-sheet schema mismatch, three disagreeing
    credit-measure writers, silent broad excepts, magic numbers, unimplemented
    paper results, off-grid clamping, test-coverage gaps, and the outlook-sign
    documentation error. Added `modelling` and `infra` labels.
- **Breaking changes:** None.
- **Validation:** `python -m pytest -q` -> 24 passed, run before this push. The
  Eq. (13) overflow claim was verified numerically: `exp(2/CCM)` raises above
  CCM ~= 0.00276 and the fallback discards up to 8.9e-3 of absolute PD.
  `norm.cdf(-x)` was confirmed to return exactly 0.0 from x ~= 38 while
  `log_ndtr` still resolves past 39. Equations 1-5, 11-14, 22, 24, 26-28 and
  Prop. 4.2/4.4.1/4.4.2/4.5.2-4.5.4/5.2.1/5.3 were read from the paper text.
- **Follow-ups:**
  - Four owner decisions remain open and block #3, #12, and the two debt
    conventions recorded in `docs/reconciliation/REPORT.md`.
  - `alpha_sp` is correct but visually invites a wrong "fix": the paper's
    stacked fraction reads as `0.625913 * ln CCM` where the coefficient is
    `1/0.625913`. Noted in both `GAP_ANALYSIS.md` and #11.

### 2026-07-25 - Three-way reconciliation of submission workbooks

- **Scope:** documentation and analysis under `docs/reconciliation/`; no change
  to any of the four workflow layers.
- **Summary:**
  - Added `docs/reconciliation/REPORT.md`, a per-company and aggregate
    comparison of our submission, a peer implementation of the same spec, and a
    third set of screenshot figures, with an input-provenance table and a
    classification of every disagreement.
  - Added `docs/reconciliation/crossover.py`, a reproducible 2x2 crossover:
    our model on our inputs, our model on their inputs, their debt-field
    convention on our inputs, and their reported results. Their cell is read
    rather than recomputed because the peer published a workbook, not code, so
    the residual term bounds implementation difference from above.
  - Added `docs/reconciliation/screenshot_figures.md`, the hand transcription
    of the third source with its transcription caveats.
- **Findings of record:**
  - Both workbooks take `abs()` of a negative drift when forming `mu`/`CCM`,
    violating the stated assumption of Prop. 4.4.1 (ours 4/10 companies,
    theirs 5/10). Treated as the headline finding.
  - The reported "Outlook sign is inverted" finding is **refuted**: Eq. (28)
    defines `Outlook = PD_FH - S&P TTC`, which is what the repo computes. No
    change was made; a change here would have inverted correct behavior.
  - Long-term debt divergence traced per name to field selection
    (`Long Term Debt And Capital Lease Obligation` vs `Long Term Debt`),
    with the ORCL and AMZN gaps equal to the capital-lease row exactly.
  - Off-grid coverage is wider than reported: 5 of 10 companies clamp on our
    side, not 2 - KO, PNC and INTU fall off the CCM floor in addition to COST
    and AMZN falling off the mu ceiling.
- **Breaking changes:** None.
- **Validation:** `python -m pytest -q` -> 24 passed, run before this push.
  Equation (28) and Prop. 4.4.1 checked against `local/TiC_paper.pdf` directly.
  Field-level claims checked against the cached raw balance sheets. Confirmed
  `git ls-files --cached` holds no `.pdf`, `.xlsx`, `.csv` or `.parquet`.
- **Follow-ups:**
  - The study's inputs and its results CSV are git-ignored by the repo-wide
    `*.xlsx` / `*.csv` rules, so `REPORT.md` carries the numbers inline. The
    peer workbook embeds proprietary grid sheets; the ignore rule must stay.
  - The reconciliation reads the cached run of 2026-07-25 and is not
    re-derivable at a fixed date, per `docs/TIMING_PROTOCOL.md` §9.
  - Four decisions are open for the project owner: negative-drift handling,
    off-grid handling, `Total Debt` column semantics, and the long-term debt
    field definition.

### 2026-07-25 - Trunk-based workflow; CLAUDE.md accuracy pass

- **Scope:** repository workflow policy and documentation; no code changes.
- **Summary:**
  - Landed `docs/claude-md-project-context` into `main` by fast-forward (no
    history rewritten) and deleted that branch locally and on the remote.
  - Repository is now trunk-based: work happens directly on `main`, no feature
    branches, no pull requests. `CLAUDE.md` "Git rules" rewritten accordingly:
    run the full test suite before every push and never push an unrun commit;
    the commit body now carries what changed, why, how verified, and which
    output numbers moved, replacing the PR description; never rewrite published
    history (no force-push, no rebase or amend of pushed commits — undo with
    `git revert`); no changes to remotes, git config, or branch protection.
  - Marked every forward-looking statement in `CLAUDE.md` `(planned)`: the
    TIMING_PROTOCOL §8 audit fields, full provenance flagging, the NaN and
    sigma_A hard asserts, log-space small-probability arithmetic, the full run
    manifest, immutable Parquet vintages, fresh-clone verification, and CI.
  - Recorded the `.agents/README.md` vs `docs/DEPENDENCY_MAPS.md` conflict over
    whether Layers 3-4 are active, and the two known Layer 2 -> Layer 3/4
    compatibility edges, rather than silently picking a side.
  - Corrected remaining inaccuracies: removed references to a UI and to a demo
    (neither exists), pointed the fixture note at the real `needs_tables` skip
    in `tests/test_conversion.py:17`, and noted that `git branch --show-current`
    is unavailable on this machine's git 2.15.
- **Breaking changes:** workflow policy only. Feature branches and pull
  requests are no longer used; `main` is the working branch.
- **Validation:** `python -m pytest -q` -> 24 passed (run before this push).
  Re-verified every path, module, command, and `file:line` reference in
  `CLAUDE.md` against the working tree. Confirmed `git ls-files --cached` holds
  no `.pdf`, `.xlsx`, `.csv`, or `.parquet` and nothing under `local/`.
- **Follow-ups:**
  - One stray remote branch remains, `agent/unify-four-layer-architecture`
    (fully merged into `main`); awaiting the owner's decision before deletion.
  - Organization-specific wording persists in 13 places across `README.md`,
    module docstrings, an error message in `signal_construction/conversion.py`,
    and the `pfpa.*` logger namespaces, in a public repository.

### 2026-07-25 - Add CLAUDE.md agent context file

- **Scope:** documentation and repository configuration; no code or formula changes.
- **Summary:**
  - Added root `CLAUDE.md`: project context, protocol pointers, git rules,
    engineering rules, resolved conventions, known limitations, repo map, and
    commands, for agent sessions working in this repository.
  - Its TIME PROTOCOL and AGENT PROTOCOL sections summarize
    `docs/TIMING_PROTOCOL.md` and `.agents/README.md` and point at those files
    as the source of truth, rather than restating them as independent rules.
  - Recorded explicitly that no canonical team timezone or timestamp format is
    defined anywhere in the repository, and listed the de-facto formats
    currently produced by the code (`docs/DEVLOG.md` headings `YYYY-MM-DD`,
    `submission_%Y%m%d_%H%M%S.xlsx`, `lineage.RUN_TIMESTAMP`
    `%Y-%m-%d %H:%M:%S`), all naive local time.
  - Ignored `CLAUDE.local.md` so contributors can keep personal overrides
    untracked; `CLAUDE.md` itself is committed.
- **Breaking changes:** None.
- **Validation:** verified every path, module, command, constant, and file:line
  reference in `CLAUDE.md` against the working tree (`git ls-files`, targeted
  greps, and reads of `signal_construction/{config,measures,conversion}.py`,
  `dashboard/submission.py`, `raw_data_architecture/lineage.py`,
  `mdt/__main__.py`, `pyproject.toml`). Confirmed `git check-ignore` covers
  `CLAUDE.local.md` and that no proprietary extension is in the index. No test
  run was required or performed; no source files were modified.
- **Follow-ups:**
  - `signal_construction/measures.py:75` takes `abs(drift)` for `mu`/`CCM`
    with no provenance flag on the output — decide whether to flag or gate it.
  - No canonical timestamp standard exists; if one is wanted, it belongs in
    `docs/TIMING_PROTOCOL.md` before any stamping code changes.
  - `README.md` still carries organization-specific wording in its project
    description and license note; confirm whether that should be genericized.

### 2026-07-15 - Review pass: remove dead code, surface ratings, polish

- **Scope:** enterprise cleanup after the phased build; no formula changes.
- **Summary:**
  - Removed the unused `signal_construction/credit.py` (old Merton baseline /
    CreditModel / TICModel stub) and the never-populated `CompanyData.credit`
    field; the pipeline uses `em` + `measures` + `conversion` directly.
  - `dashboard/excel.py` and `longtable.py` now emit the real credit results
    (sigma_A, CCM, mu, RiskScore, DD, EDF, PIT/TTC PD, S&P, Outlook): a
    per-company "Credit Rating" sheet, a master "Ratings" sheet, and a
    `credit_measures` long-table category. Previously these read the dead
    `credit` object and were empty.
  - Moved `LICENSE` to the repo root (GitHub license detection); pyproject
    description updated to the credit-rating pipeline; version 0.3.0.
  - Refreshed `signal_construction/__init__`, DEVLOG status, and DEPENDENCY_MAPS
    (Layers 3-4 marked ACTIVE).
- **Verified DD** against the paper: `DD = [ln(A/D) + (eta - sigma^2/2)T]/(sigma*sqrt(T))`
  matches `measures.py` exactly.
- **Validation:** `pytest` 24/24; all four layers import cleanly; live run shows
  ratings in the dashboard workbooks.

### 2026-07-15 - Phase 6: one-click CLI + docs

- **Scope:** `mdt` CLI package, README, packaging; final checks.
- **Summary:**
  - `mdt` package: `python -m mdt rate AAPL` (prints the full rating table and
    writes `outputs/<TICKER>_report.xlsx`) and `python -m mdt batch
    config/companies.yaml`. Console script `mdt` registered in pyproject.
  - `submission.write_submission` accepts an optional filename (per-ticker report).
  - README rewritten: pipeline diagram, formula->equation map, data sources,
    quickstart, notice, known limitations.
  - GAP_ANALYSIS updated with the R vs eta and 250-trading-day conventions.
- **Validation:** `pytest` 24/24; `python -m mdt --help` and `rate KO` run
  clean (no double-import warning); fresh-clone quickstart documented.
- **Follow-ups:** confirm the intended `R` column definition; optional
  Layer-1/2 Parquet persistence for the staged-workflow milestone.

### 2026-07-15 - Phase 5: batch run + submission workbook

- **Scope:** Layer 4 (dashboard) + CLI; adds submission output.
- **Summary:**
  - `config/companies.yaml`: the 10 batch tickers (editable; accepts names).
  - `run.py`: `--companies YAML` loads the universe from config.
  - `dashboard/submission.py`: `write_submission` writes a timestamped
    `outputs/submission_{date}.xlsx` (never overwriting) with an `Asset` sheet in
    the submission column layout (Symbol, shares, debts, rate, statement date,
    sigma_A, R=eta-sigma^2/2, eta, CCM, mu, TiC, RiskScore, DD, EDF, PIT PD,
    TTC PD, S&P, Outlook) and a `validation` sheet flagging EM convergence,
    sigma range, and off-grid conversions.
  - `workflow.run` writes the submission after the batch.
  - `tests/test_submission.py`: schema + R=eta-sigma^2/2 check.
- **R vs eta:** the `R` column is the realized drift `eta - sigma_A^2/2` (the
  term in DD), and `eta` is `eta_A`; this reconciles the two DD formulations.
  Flagged as the working interpretation pending confirmation.
- **Validation:** `pytest` 24/24. Live batch writes submission for all 10;
  off-grid flags on KO/PNC/INTU/KHC; outputs git-ignored.
- **Follow-ups:** Phase 6 (one-click CLI `python -m mdt` + README/docs).

### 2026-07-15 - Phase 4: PIT -> TTC -> S&P conversion

- **Scope:** Layer 3 (signal_construction); adds conversion + tests.
- **Summary:**
  - `signal_construction/conversion.py`: loads the conversion
    workbook from the git-ignored `local/` tree (TTC grid = no-arbitrage S&P TTC
    PD by CCM x mu; SP sheet = PD -> letter thresholds), with bilinear
    interpolation + edge-clamp flagging for off-grid inputs. Also implements the
    analytical no-arbitrage conversion (Prop. 5.2): confidence levels
    `alpha_first_hitting` / `alpha_sp` (Eq. 22) and `no_arb_ccm_star`.
  - `workflow`: computes TTC PD, S&P letter, and Outlook (PIT PD - TTC PD) per
    company; `CompanyData` gains those fields.
  - `tests/test_conversion.py`: reproduces paper alpha_FH(1.5)=0.91906 and
    CCM*=1.35373; TTC grid reproduces paper S&P TTC (Tables 13-14); SP threshold
    mapping; off-grid flagging. Grid tests skip when the proprietary workbook is absent.
- **Proprietary:** conversion tables read from `local/` and cached to
  `local/tables/*.csv` (git-ignored); no proprietary numbers are committed.
- **Validation:** `pytest` 23/23 (grid tests active locally). Live 10-company
  ratings: ORCL BB+ (riskiest) ... AAA- for COST/KO/WMT/AMZN; off-grid flags on
  KO/PNC/INTU (CCM<0.1) and KHC (mu>160).
- **Follow-ups:** Phase 5 (companies.yaml + timestamped submission workbook).

### 2026-07-15 - Phase 3: TiC / first-passage credit measures

- **Scope:** Layer 3 (signal_construction); adds measures + tests.
- **Summary:**
  - `signal_construction/measures.py`: from EM outputs (sigma_A, A, eta_A) and
    debt D, computes mu and CCM (Eq. 11), TiC = sigma_A^2/ln^2(A/D) and
    RiskScore = 100*TiC (Eq. 12/5), default peak lambda (Eq. 3/6), DD and
    EDF = Phi(-DD) (Eq. 14), and PIT PD via the inverse-Gaussian first-hitting
    formula (Eq. 13).
  - `workflow`: computes measures after EM; logs RiskScore/CCM/mu/DD/EDF/PIT.
  - `CompanyData`: measure fields.
  - `tests/test_measures.py`: PIT PD matched to paper Tables 13-14
    (CCM=1.5 mu=1 -> 69.40%, CCM=5 mu=1 -> 77.70%, ...); DD/TiC/lambda hand
    values; TiC verified eta-independent.
- **Validation:** `pytest` 18/18 passing. Live 10-company RiskScores rank
  sensibly vs the paper scale (ORCL 10.0 riskiest; COST/KO/WMT < 1). Confirmed
  the eta instability shows up in mu/CCM/PIT but not in RiskScore.
- **Follow-ups:** Phase 4 (PIT -> TTC -> S&P via local lookup tables + no-arb).

### 2026-07-15 - Phase 2: EM asset-value/volatility estimation

- **Scope:** Layer 3 (signal_construction); adds EM estimator + tests.
- **Summary:**
  - `signal_construction/em.py`: Duan-style EM. E-step inverts the Black-Scholes
    equity/option relation by vectorized bisection to get the daily asset path
    `A_t` given `sigma_A`; M-step recomputes `sigma_A` from asset log-returns and
    estimates the real-world drift `eta_A` simultaneously. Hard invariants
    (`A > D`, `A > E`) raise; soft checks (sigma range, slow convergence) warn.
  - `config`: trading days 252 -> 250 (deck), EM window 252d, max-iter 20, tol.
  - `CompanyData`: EM outputs (`sigma_A`, `eta_A`, `asset_value`, iters).
  - `workflow`: runs EM on the trailing window (replaces the old Merton-baseline
    call) and logs a sector asset-volatility cross-check.
  - `tests/test_em.py`: recovers a known sigma_A from a synthetic GBM path;
    enforces `A>D`/`A>E`; short-input guard.
- **Validation:** `pytest` 8/8 passing. Live 10-company batch: all converge in
  2-3 iters; sigma_A ranks Technology (DELL 56%, ORCL 55%, INTU 45%) above
  defensives/financials (KO 15.5%, T 15.6%, PNC 16.8%) -- the expected ordering.
- **Follow-ups:** Phase 3 (RiskScore/CCM/mu/lambda/DD/EDF/PIT-PD from EM outputs).

### 2026-07-15 - Phase 1: data-layer completion

- **Scope:** Layers 1-2 data acquisition/cleaning; adds tests.
- **Summary:**
  - `sources.resolve_ticker`: name/symbol -> ticker via Yahoo search, preferring
    exact/substring name match and primary listings; raises
    `TickerResolutionError` on genuine ambiguity (e.g. Intuit vs Intuitive).
  - `alignment.build_panel`: dividend add-back (deck slide 61) so equity is a
    total-return series (`DivAddBackClose`, `MarketCap_E`, `RawMarketCap`);
    restored `Horizon_T`.
  - `data_cleaning/persistence.py`: per-company raw + aligned datasets written to
    the git-ignored `raw_data_architecture/data/{TICKER}/` and
    `data_cleaning/data/{TICKER}/` trees as CSV + XLSX.
  - `workflow.run`: resolves inputs up front (skips unresolvable with a message)
    and persists each company.
  - `tests/test_no_lookahead.py`: offline canary suite proving no look-ahead in
    debt/rate as-of joins and the dividend add-back.
- **Validation:** `pytest` 4/4 passing; live KO run persists raw+clean data and
  writes the workbook; resolver verified on tickers and names.
- **Follow-ups:** Phase 2 (EM: joint sigma_A + eta_A via bisection g-inverse).

### 2026-07-15 - Phase 0: gap analysis vs TiC methodology

- **Scope:** documentation + proprietary-data handling; no code behavior change.
- **Summary:** added `docs/GAP_ANALYSIS.md` mapping the TiC paper and the
  Market-Based Credit Risk deck (KMV/EM/first-passage) to current branch code,
  with a per-concept status table. Recorded resolved conventions: 1-year
  risk-free (DGS1), η_A from EM for DD, ~252-day EM window, public repo with
  proprietary material git-ignored.
- **Proprietary:** the TiC paper, the market-based deck, and `TiC_TTC_conversion.xlsx`
  are kept under `local/` and git-ignored; lookup tables will be local-only.
- **Validation:** confirmed proprietary artifacts are ignored (`git check-ignore`);
  removed a stray legacy `output/` dir from staging.
- **Follow-ups:** Phase 1 (data-layer completion + no-look-ahead canary test).

### 2026-07-09 - Repository architecture unification

- **Scope:** repository structure, documentation, and dependency ownership.
- **Summary:**
  - Moved the Git repository contents to the `PFPA_Intern_Project` root.
  - Reorganized code into the four workflow layer directories.
  - Split configuration ownership across the four layers.
  - Archived the earlier supporting documents.
  - Added code, runtime, data-artifact, and package dependency maps.
  - Added this push-update development log under `docs/`.
  - Added the mandatory point-in-time timing protocol and no-look-ahead rules.
  - Added mandatory agent startup and push gates: read the root README and
    current docs before work, and synchronize DEVLOG before every push.
  - Kept `pyproject.toml` at the repository root because Python build tools
    discover it there by default.
  - Moved the MIT license to `docs/LICENSE`.
- **Breaking changes:** imports from the former `mdtoolkit` package must use the
  new layer package paths.
- **Validation:** CLI help, layer imports, synthetic alignment smoke test,
  Python compilation, and `git diff --check`.
- **Follow-ups:** implement raw/clean Parquet persistence, add timing contracts,
  and remove the compatibility workflow's backward dependencies.

## Entry template

Copy this section to the top of **Recent changes** before pushing:

```markdown
### YYYY-MM-DD - Short change title

- **Scope:** layer, feature, fix, documentation, or infrastructure.
- **Summary:** what changed and why.
- **Breaking changes:** migration requirement, or `None`.
- **Validation:** commands or checks actually completed.
- **Follow-ups:** unresolved work, risks, or `None`.
```
