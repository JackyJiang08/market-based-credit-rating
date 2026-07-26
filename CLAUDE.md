# CLAUDE.md

Project context for Claude Code sessions. Read this before doing anything.
Precedence: `.agents/` protocols > this file > your defaults. Flag conflicts; don't resolve
them silently.

---

## What this project is

`market-based-credit-rating` — a market-based credit rating pipeline, implemented end to
end across four workflow layers:

```
raw_data_architecture  →  data_cleaning   →  signal_construction   →  dashboard
(Yahoo prices/            (dividend            (EM: σ_A, A, η_A;       (submission
 financials, FRED          add-back,            CCM, µ, TiC, DD,        workbook,
 DGS1; provenance)         D = ST+0.5·LT,       EDF, PIT PD;            per-company
                           as-of panel)         PIT→TTC→S&P)            Excel, long table)
```

Methodology basis: the Time-Consistent (TiC) credit rating framework (Yimin Yang, Duke).

**The reference materials and the conversion grids are licensed third-party material and are NOT in this repository.** They
live in a git-ignored `local/` tree that each contributor supplies:

- `local/TiC_paper.pdf`
- `local/Market_Based_Credit_Risk_deck.pdf`
- `local/TiC_TTC_conversion.xlsx` — read at runtime by `signal_construction/conversion.py`
- `local/tables/` — CSV caches derived from the workbook (e.g. `sp_thresholds.csv`)

**Red line:** this repository is PUBLIC. Never commit, push, stage, or copy anything from
`local/` into a tracked path, and never paste its contents into code, docs, or commit
messages. With trunk-based pushes going straight to a public `main`, there is no review step
to catch this — check before you push, not after. `.gitignore` blocks `local/`, `*.pdf`, `*.xlsx`, `*.csv`, `*.parquet` —
check `git ls-files --cached` for those extensions before every push.

**Attribution / IP:** the TiC methodology is not ours. It may be implemented and
demonstrated, with citation, as an independent implementation. It must never be presented to
third parties as original methodology. Keep the attribution/IP notice in `README.md`, and
cite the methodology by equation number in the docstring of every module implementing a TiC
formula (`signal_construction/em.py`, `measures.py`, `conversion.py` already do this).

**Positioning:** all public-facing material (README, docs, commit messages) reads as
professional engineering work. Do not frame it as a class assignment.

---

## TIME PROTOCOL

Source of truth: [`docs/TIMING_PROTOCOL.md`](docs/TIMING_PROTOCOL.md), made mandatory by
[`.agents/README.md`](.agents/README.md). It is a **point-in-time / no-look-ahead protocol**.
It does not define a team timezone or a timestamp string format — see "Timestamp formats"
below before emitting one.

The default invariant, quoted verbatim:

```text
max(feature.available_at) <= decision_time_t
```

> "Unless a task explicitly declares otherwise, no data that became available after `t` may
> influence features, transformations, model parameters, signal construction, ranking, or
> evaluation inputs." — `docs/TIMING_PROTOCOL.md` §Purpose

Rules that bind every time-dependent change:

- Seven distinct time fields, never substituted for one another: `event_time`, `period_end`,
  `available_at`, `ingested_at`, `decision_time`, `target_time`, `vintage`. "`event_time`
  and `period_end` are not substitutes for `available_at`."
- Eligibility: a record may feed a feature at `t` only when `record.available_at <= t`. Join
  on `available_at` with backward as-of joins. Forward-fill only from an observation already
  available at `t`. **Never backfill a missing historical value from a later observation.**
- Source rules: a daily close for date `d` is available only after that close; a statement
  becomes eligible at its filing/publication time, not `period_end` (if the filing time is
  unknown, use a documented conservative lag and set
  `availability_method="estimated_lag"`); FRED observation date ≠ publication time; current
  shares/market-cap/sector must not be applied backward.
- Fitted transforms (imputation, normalization, winsorization, PCA, feature selection) train
  only on data inside the training interval. Chronological train/val/test splits; purge or
  embargo overlapping labels.
- Look-ahead is prohibited **by default**. An exception requires an explicit task
  authorization, `lookahead_allowed=true`, outputs labelled `NON_CAUSAL` or `RETROSPECTIVE`,
  isolation from production signals, and a `docs/DEVLOG.md` record. "Silence or ambiguity is
  not permission to use data after `t`."
- Any change to alignment, feature windows, source timestamps, model training, or target
  construction **must add or update a no-look-ahead test** (`tests/test_no_lookahead.py`).
  Also required by `.agents/README.md`: "Any date alignment change must include a
  no-look-ahead test."
- **(planned)** Panels/signals should expose the audit fields listed in §8 (`run_id`,
  `source_snapshot_id`, `decision_time`, `max_input_available_at`, `feature_window_start/end`,
  `target_start/end`, `availability_method`, `lookahead_allowed`,
  `timing_validation_status`). None of these fields exist in the pipeline today —
  `decision_time` and `available_at` appear only in `tests/test_no_lookahead.py`, and run
  provenance is limited to `raw_data_architecture/lineage.py` (`RUN_TIMESTAMP`,
  `EQUITY_SOURCE`, `RATES_SOURCE`). Treat §8 as the target, not a description of the output.
- Known non-compliance, per §9 — existing aligned panels are **research prototypes, not
  backtest-safe datasets**: `data_cleaning/alignment.py` aligns statements on period end
  rather than `available_at`; the reference-share method can apply a latest-date estimate
  across earlier history; raw/clean point-in-time vintages are not persisted as immutable
  Parquet snapshots. Do not describe outputs as backtest-safe until these are fixed and
  tested.

Use the §Contributor checklist at the end of `docs/TIMING_PROTOCOL.md` before pushing any
time-dependent change.

### Timestamp formats — team standard adopted 2026-07-26 for NEW artifact stamps

`docs/TIMING_PROTOCOL.md` §10 (adopted 2026-07-26, owner-directed, for the deliverable-v1
freeze): **new artifact stamps are timezone-aware UTC, ISO 8601** — `YYYY-MM-DDTHH:MM:SSZ`
human-readable, `YYYYMMDDTHHMMSSZ` in filenames. First applied to the submission workbook
filename and its README-sheet `Generated (UTC)` field.

Formats still in force elsewhere (existing artifacts are not renamed or restamped):

| Use | Format | Where |
|---|---|---|
| DEVLOG entry headings | `YYYY-MM-DD` (date only) | `docs/DEVLOG.md` entry template |
| Output workbook filename | `submission_%Y%m%dT%H%M%SZ.xlsx` (UTC, §10) | `dashboard/submission.py` |
| Run provenance stamp | `%Y-%m-%d %H:%M:%S` naive local (**pre-standard; migrate when touched**) | `raw_data_architecture/lineage.py:20` |
| Panel/period columns | `%Y-%m-%d` (calendar dates, not instants — stays) | `data_cleaning/transforms.py:66`, `dashboard/longtable.py` |

When touching a writer that still stamps naive local time, migrate it to §10 in that
change; do not add new naive-local stamps anywhere.

## AGENT PROTOCOL

Source of truth: [`.agents/README.md`](.agents/README.md) (note: `.agents/`, not `.agent/`).

**Mandatory startup gate** — complete *before* inspecting implementation details, editing
files, running project commands, or proposing changes. "This is a hard prerequisite, not an
optional orientation step."

1. Read `README.md` completely.
2. Read `docs/README.md` completely.
3. Read the documentation set referenced there, at minimum: `docs/DEVLOG.md`,
   `docs/TIMING_PROTOCOL.md`, `docs/DEPENDENCY_MAPS.md`, `docs/GAP_ANALYSIS.md`.

If any required document changes during the task, re-read the changed sections before
continuing.

**Mandatory push gate** — before *every* `git push`:

1. Update `docs/DEVLOG.md` with the exact push scope.
2. Record breaking changes, validation actually performed, and unresolved follow-ups.
3. Include the DEVLOG update in the same commit or push batch.
4. Confirm the DEVLOG change is part of the outgoing diff.

"An agent must not push when `docs/DEVLOG.md` has not been synchronized for that push. This
requirement applies even when the pushed change is documentation, configuration, or
repository maintenance rather than application code." Entries go newest-first under **Recent
changes**, using the template at the bottom of `docs/DEVLOG.md`.

**Repository rules** (`.agents/README.md`):

- Preserve the four top-level workflow layers.
- Put new code in the layer that owns its output contract.
- No backward imports from an earlier layer to a later layer.
- Layer 1 and Layer 2 are the **only active implementation scope** until the project owner
  explicitly activates signal-construction or dashboard work. **Conflict — do not resolve
  silently:** Layers 3 and 4 are fully implemented, and `docs/DEPENDENCY_MAPS.md:12-15`
  marks all four layers `ACTIVE`. Read this as already activated in practice, but confirm
  with the owner before starting new Layer 3/4 work, and get `.agents/README.md` updated.
- Any date alignment change must include a no-look-ahead test.
- Follow `docs/TIMING_PROTOCOL.md` for every time-dependent task.
- Known deviation: `docs/DEPENDENCY_MAPS.md:27-28` records two temporary Layer 2 → Layer 3/4
  compatibility edges that violate the no-backward-import rule. Don't add more.

---

## Git rules (non-negotiable) — trunk-based

This repository is trunk-based as of 2026-07-25. There are no feature branches and no
review gate, so the discipline that a PR used to provide now lives in the commit itself.

- **Work directly on `main`.** Never create a feature branch. Never open a PR. Push with
  `git push origin main` after each sub-task, not just at the end of a session.
- Confirm `git branch --show-current` is `main` before the first commit of any task.
  (This machine's system git is 2.15, which predates that flag — use
  `git rev-parse --abbrev-ref HEAD` here. Likewise `git restore` does not exist; use
  `git checkout --`.)
- **`main` must be green at every commit.** Run the full test suite *before* every push.
  Never push a commit you have not run. If the suite is red, fix it or revert before
  pushing — do not push and follow up.
- **GREEN MEANS CI GREEN: you may not end a session, or start a dependent task, while
  the pushed HEAD's CI is failing or unknown.** Watch the run after every push
  (`gh run list`); a red or unknown HEAD is unfinished work.
- Atomic conventional commits: `feat(model):`, `fix(data):`, `test:`, `docs:`, `refactor:`,
  `chore:`, `ci:`. Never mix a refactor with a behaviour change in one commit.
- **The commit message body replaces the PR description.** It states what changed, why, how
  it was verified (the commands actually run), and which output numbers moved. Write `None`
  rather than omitting a section.
- **Never rewrite published history.** No force-push. No rebase or amend of any commit that
  has been pushed. Undo with `git revert`, which is itself a normal commit and needs the
  same message discipline.
- No changes to remotes, git config, or branch protection.
- **Never delete a branch** — local or remote — unless explicitly told to.
- Every push still carries its `docs/DEVLOG.md` update (see AGENT PROTOCOL). With no PR to
  read, DEVLOG plus the commit body are the only record of a change.
- Commit messages stay generic and professional: no organization name, no instructor, no
  coursework framing.

---

## Engineering rules

1. **Cite the maths.** Every formula carries a comment with its paper reference:
   `# Eq. (13)` or `# Prop. 4.5.2`. If code and the reference disagree,
   record it in `docs/GAP_ANALYSIS.md` and raise it — never silently "fix" a number.

2. **No fabricated data, ever.** If a source fails, the output says so. No interpolation to
   fill a gap, no plausible-looking placeholder, no backfilled figure. A visible "not
   available" beats a confident wrong number. (Backfilling is also a TIMING_PROTOCOL
   violation.)

3. **No silent fallbacks.** Every clamp, default, `abs()`, or estimator substitution should
   set a provenance flag that reaches the output workbook. If the reader can't tell the
   model did something unusual, it's a bug. Today only grid clamping carries such a flag
   (`rating_off_grid` → `validation` sheet in `dashboard/submission.py`); **(planned)** full
   coverage of the remaining substitutions, starting with the `abs(drift)` in
   `signal_construction/measures.py:75`, which has no flag. Adding flags is welcome work;
   removing one is not. There is no UI in this repo — the `validation` sheet and the CLI
   output are where a flag has to surface.

4. **Invariants.** `A > D > 0` is asserted in `signal_construction/measures.py:71` (raises).
   `EM_MAX_ITER = 20` is enforced in `signal_construction/config.py`. PD is clamped to
   `[0, 1]` in `pit_pd_first_hitting()`. σ_A currently only warns outside `[0.10, 0.60]`
   (`SIGMA_A_WARN_LOW/HIGH`). **(planned)** a hard assert that no `NaN` reaches an output
   file, and **(planned)** promoting the σ_A range from a warning to an asserted bound.

5. **No bare `.iloc[-1]`** on a price/financial series without first dropping missing rows —
   this class of bug produced the KHC NaN cascade (fixed in `6eb9826`). There is no shared
   `clean_price_series()` helper; each call site guards with `.dropna()` before `.iloc[-1]`
   (see `dashboard/submission.py:40`, `mdt/__main__.py:56`, `dashboard/excel.py:142`). If you
   add a fourth call site, factor the helper out rather than copying the guard again.

6. **Small-probability arithmetic must not silently overflow.** `exp(2/CCM)` in
   `pit_pd_first_hitting()` overflows for tiny CCM and is currently guarded by
   `try/except OverflowError` (`signal_construction/measures.py`). **(planned)** move this
   to log space (`scipy.special.log_ndtr` / `logsumexp`) with a finiteness assert — neither
   is imported anywhere today. Do not remove the existing guard without replacing it.

7. **One writer per artifact.** Exactly one module writes the deliverable workbook
   (`dashboard/submission.py`), driven by a declared schema constant. No hand-written sheets,
   ever.

8. **Reproducibility.** `raw_data_architecture/lineage.py` records run provenance today:
   `RUN_TIMESTAMP`, `EQUITY_SOURCE`, `RATES_SOURCE`. **(planned)** a full run manifest (git
   SHA, package version, input hashes, data vintage, config) — extend `lineage.py` rather
   than starting a parallel mechanism. Offline cache fixtures ARE committed under `data/cache/` (the original
   10-name universe, TM as the currency-gate regression case, and the FRED rates frame),
   so the demo and `tests/test_offline_fixture.py` run with no network. Tests needing the
   proprietary workbook still skip via `needs_tables` (`tests/test_conversion.py:17`) so a
   fresh clone stays green. Keep both behaviours working.

9. **Ask, don't assume.** Ambiguity in a convention (drift definition, debt fields, EM
   window, rate series) → stop and ask. Assumptions get written into `docs/GAP_ANALYSIS.md`
   and `docs/DEVLOG.md`, not into code comments.

---

## Conventions already decided (don't relitigate without raising it)

| Choice | Value | Where |
|---|---|---|
| Risk-free rate | FRED `DGS1` (1-year), horizon T = 1yr | `data_cleaning/config.py`, `HORIZON_YEARS = 1.0` |
| Asset drift | `η_A` from EM M-step; `DD = [ln(A/D) + (η_A − σ_A²/2)·T] / (σ_A·√T)` | `signal_construction/measures.py:89` |
| `R` column | `η_A − σ_A²/2` (signed) | `dashboard/submission.py:59-61` |
| EM window | `EM_WINDOW_DAYS = 252` trailing daily obs; `TRADING_DAYS_PER_YEAR = 250` | `signal_construction/config.py` |
| EM convergence | `EM_MAX_ITER = 20`, `EM_TOL = 1e-5` on σ_A | `signal_construction/config.py` |
| Default point `D` | `1.0·ShortTermDebt + 0.5·LongTermDebt` | `data_cleaning/transforms.py` |
| Analytical constants | `CML = e^1.35`, `Q_SP = 0.625913`, θ = 1 | `signal_construction/conversion.py:37-39` |
| Verification anchors | `alpha_FH(1.5) = 0.91906`, `CCM* = 1.35373`, paper Tables 13–14 | `conversion.py`, `measures.py` docstrings |
| Outlook | `PIT PD − TTC PD` | `README.md`, `mdt/__main__.py` ("Outlook (PIT-TTC)") |
| Batch universe | 10 tickers | `config/companies.yaml` |

Moody's `Q = 0.746` is *not* implemented anywhere in the code — only the S&P constant is. If
you need it, add it with its proposition reference rather than assuming it exists.

---

## Known model limitations (state them, don't paper over them)

- **Drift is noise-dominated.** `η_A` from ~252 daily returns is noisy (the well-known
  short-window drift-estimation problem); since `µ = ln(A/D)/|η_A − σ_A²/2|`, µ and CCM inherit that noise.
  The RiskScore (`100·σ_A²/ln²(A/D)`, Eq. 12/5) is η-independent and therefore stable.
- **Negative-drift regime.** `signal_construction/measures.py:75` currently takes
  `abs(drift)` for µ and CCM, with no flag on the output. When `η_A − σ_A²/2 ≤ 0` the
  first-passage time is defective and `µ = E[τ]` is not meaningful. This is a known
  deviation from rule 3 — flag it, don't extend it.
- **Off-grid conversions are edge-clamped, not refused.** `(CCM, µ)` outside the lookup grid
  is clamped to the grid edge and marked `off_grid` / `rating_off_grid`, surfaced in the
  `validation` sheet and in the CLI note. The analytical no-arbitrage route
  (`no_arb_ccm_star`) extends past the edges. Grid bounds come from the workbook axes at
  runtime, not from constants in the repo.
- **Banks (e.g. PNC).** `ST + 0.5·LT` ignores deposits, so the structural model is not
  meaningful for banks without a sector-specific default point. Yahoo also omits a clean
  current/non-current split for them (handled by a debt fallback).
- **TTC grid provenance.** The grid's generating formula was not recovered in closed form
  from the methodology text; it is internally consistent and reproduces Tables 13/14, so it is treated
  as authoritative. Discussed in `docs/GAP_ANALYSIS.md`.
- **Market-implied PIT PDs are liquidity-sensitive.** For large, liquid, investment-grade
  names PIT PD is legitimately ~0 — compare firms by DD and RiskScore instead. Typical asset
  volatilities land in ~10–60%.
- **Data path is in memory.** **(planned)** immutable raw/clean Parquet point-in-time
  boundaries; `data_cleaning/persistence.py` exists but does not yet provide them
  (`docs/DEVLOG.md`, `docs/TIMING_PROTOCOL.md` §9).

---

## Repo map

```
raw_data_architecture/   Layer 1: sources (yfinance, FRED), config, provenance/lineage
data_cleaning/           Layer 2: alignment, transforms, company model, workflow, persistence
signal_construction/     Layer 3: EM, credit measures, PIT→TTC→S&P conversion, config
dashboard/               Layer 4: submission workbook, per-company Excel, long table
mdt/                     CLI entry point (`python -m mdt`)
config/companies.yaml    batch universe
docs/                    DEVLOG, TIMING_PROTOCOL, DEPENDENCY_MAPS, GAP_ANALYSIS, tools/
tests/                   pytest suite (24 tests, offline)
run.py                   legacy/compatibility workflow entry
local/                   licensed reference materials + conversion workbook — GIT-IGNORED
.agents/                 team agent protocol  ← read first
```

Generated artifacts, all git-ignored: `outputs/`, `dashboard/output/`,
`raw_data_architecture/data/`, `data_cleaning/data/`.

## Commands

There is no `Makefile` in this repo. Use these directly:

```bash
pip install -r requirements.txt          # deps (Python 3.11+ recommended)
python -m mdt rate <TICKER>              # one company → rating table + report
python -m mdt batch config/companies.yaml  # batch → outputs/submission_<stamp>.xlsx
python -m mdt batch config/universe.yaml --workers 6  # 150-name universe (docs/UNIVERSE.md)
# Acquisition cache: data/cache/ (MDT_CACHE_DIR / MDT_CACHE_OFF / MDT_CACHE_REFRESH=1);
# committed fixtures make `mdt rate COST` and the suite run offline.
python run.py COST KO --years 2           # legacy workflow entry
pytest                                    # offline suite, 24 tests
```

`mdt` is also installed as a console script (`[project.scripts]` in `pyproject.toml`).
TTC/S&P conversion requires `local/TiC_TTC_conversion.xlsx`; without it the pipeline still
runs and reports σ_A / DD / PIT PD, and the grid tests skip.

## Acceptance gates (run these yourself, before every push)

CI exists (`.github/workflows/ci.yml`: lint+mypy, py3.11/3.12 × pandas 2/3 matrix with a
coverage gate, and the acceptance job; `devlog.yml`: the push gate) and pre-commit runs
ruff/black/mypy locally. CI is the backstop, not the substitute — run these yourself
before pushing, and record in the commit body and `docs/DEVLOG.md` what you actually ran:

- `pytest` is fully green — currently 24 tests. This is the hard gate: never push a commit
  whose suite you have not run.
- Paper Tables 13/14 and the `alpha_FH(1.5) = 0.91906` / `CCM* = 1.35373` anchors still
  reproduce (`tests/test_measures.py`, `tests/test_conversion.py`).
- `tests/test_no_lookahead.py` passes, and any alignment change adds to it.
- `git ls-files --cached` contains no `.pdf`; `.parquet` only under `data/cache/`
  (committed fixtures); `.csv` only under `docs/reconciliation/history/`,
  `docs/reconciliation/universe/`, and `docs/figures/data/`; `.xlsx` only under
  `docs/deliverables/`; and nothing under `local/`. (Every exception is our own
  generated output, negated explicitly in `.gitignore`; everything else with those
  extensions stays out.)
- `docs/DEVLOG.md` is updated in the same push.
- Invariants above hold across the 10-company batch — this needs a live network run
  (`python -m mdt batch config/companies.yaml`), so it is a release check rather than a
  per-commit one. Say so in the commit body when you have not run it.
- **(planned)** the suite is verified green from a fresh clone with `local/` absent. Locally
  `local/` is usually present, so the grid tests run rather than skip; the skip path is only
  exercised on a clean checkout.
- **(planned)** CI, lint, and type checking. Until they exist, do not describe a change as
  "CI-verified" or cite `ruff`/`mypy` results.
