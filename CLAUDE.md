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

**The paper and the conversion grids are proprietary and are NOT in this repository.** They
live in a git-ignored `local/` tree that each contributor supplies:

- `local/TiC_paper.pdf`
- `local/Market_Based_Credit_Risk_deck.pdf`
- `local/TiC_TTC_conversion.xlsx` — read at runtime by `signal_construction/conversion.py`
- `local/tables/` — CSV caches derived from the workbook (e.g. `sp_thresholds.csv`)

**Red line:** this repository is PUBLIC. Never commit, push, stage, or copy anything from
`local/` into a tracked path, and never paste its contents into code, docs, commit messages,
or a PR description. `.gitignore` blocks `local/`, `*.pdf`, `*.xlsx`, `*.csv`, `*.parquet` —
check `git ls-files --cached` for those extensions before every push.

**Attribution / IP:** the TiC methodology is not ours. It may be implemented and
demonstrated, with citation, as an independent implementation. It must never be presented to
third parties as original methodology. Keep the attribution/IP notice in `README.md`, and
cite the paper by equation number in the docstring of every module implementing a TiC
formula (`signal_construction/em.py`, `measures.py`, `conversion.py` already do this).

**Positioning:** all public-facing material (README, docs, demo, commit messages) reads as
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
- Panels/signals should expose the audit fields listed in §8 (`run_id`,
  `source_snapshot_id`, `decision_time`, `max_input_available_at`, `feature_window_start/end`,
  `target_start/end`, `availability_method`, `lookahead_allowed`,
  `timing_validation_status`).
- Known non-compliance, per §9 — existing aligned panels are **research prototypes, not
  backtest-safe datasets**: `data_cleaning/alignment.py` aligns statements on period end
  rather than `available_at`; the reference-share method can apply a latest-date estimate
  across earlier history; raw/clean point-in-time vintages are not persisted as immutable
  Parquet snapshots. Do not describe outputs as backtest-safe until these are fixed and
  tested.

Use the §Contributor checklist at the end of `docs/TIMING_PROTOCOL.md` before pushing any
time-dependent change.

### Timestamp formats (no canonical standard is defined — do not invent one)

Neither `.agents/` nor `docs/` specifies a team timezone or a canonical timestamp format.
The de-facto formats in the code today are:

| Use | Format | Where |
|---|---|---|
| DEVLOG entry headings | `YYYY-MM-DD` (date only) | `docs/DEVLOG.md` entry template |
| Output workbook filename | `submission_%Y%m%d_%H%M%S.xlsx` | `dashboard/submission.py:131` |
| Run provenance stamp | `%Y-%m-%d %H:%M:%S` | `raw_data_architecture/lineage.py:20` |
| Panel/period columns | `%Y-%m-%d` | `data_cleaning/transforms.py:66`, `dashboard/longtable.py` |

All of these are **naive local machine time** (`datetime.now()` with no tzinfo), and there is
no `clock.py` helper in this repo. Match the existing format for the artifact you are
touching. If you need a single team standard — a canonical timezone, or tz-aware stamps —
raise it and get it written into `docs/TIMING_PROTOCOL.md` first; do not silently change how
existing artifacts are stamped.

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
  explicitly activates signal-construction or dashboard work.
- Any date alignment change must include a no-look-ahead test.
- Follow `docs/TIMING_PROTOCOL.md` for every time-dependent task.

---

## Git rules (non-negotiable)

- **Never commit or push to `main`.** One feature branch per task: `feat/<slug>`,
  `fix/<slug>`, `docs/<slug>`. Push explicitly: `git push -u origin <branch>`.
- Open a PR against `main` with a filled-out description (what changed, why, how verified,
  which numbers moved). A human merges. You never merge.
- Confirm the current branch before the first commit of any task. System git here is 2.15 —
  `git branch --show-current` and `git restore` do not exist; use
  `git rev-parse --abbrev-ref HEAD` and `git checkout --`.
- No force-push. No changes to remotes, git config, or branch protection.
- **Never delete a branch** — local or remote — unless explicitly told to.
- Atomic conventional commits: `feat(model):`, `fix(data):`, `test:`, `docs:`, `refactor:`,
  `chore:`, `ci:`. Never mix a refactor with a behaviour change in one commit.
- Commit and push after each numbered sub-task, not just at the end of a session. Every push
  carries its `docs/DEVLOG.md` update (see AGENT PROTOCOL).
- Commit messages and PR text stay generic and professional: no organization name, no
  instructor, no coursework framing.

---

## Engineering rules

1. **Cite the maths.** Every formula carries a comment with its paper reference:
   `# Paper Eq. (13)`, `# Prop. 4.5.2`, or a deck slide number. If code and paper disagree,
   record it in `docs/GAP_ANALYSIS.md` and raise it — never silently "fix" a number.

2. **No fabricated data, ever.** If a source fails, the output says so. No interpolation to
   fill a gap, no plausible-looking placeholder, no backfilled figure. A visible "not
   available" beats a confident wrong number. (Backfilling is also a TIMING_PROTOCOL
   violation.)

3. **No silent fallbacks.** Every clamp, default, `abs()`, or estimator substitution should
   set a provenance flag that reaches the output workbook and the UI. If the reader can't
   tell the model did something unusual, it's a bug. Today only grid clamping carries such a
   flag (`rating_off_grid` → `validation` sheet); the `abs(drift)` substitution in
   `signal_construction/measures.py:75` does not. Adding flags is welcome work; removing one
   is not.

4. **Invariants.** `A > D > 0` is asserted in `signal_construction/measures.py:71` (raises).
   `EM_MAX_ITER = 20` is enforced in `signal_construction/config.py`. PD is clamped to
   `[0, 1]`. σ_A currently only warns outside `[0.10, 0.60]`
   (`SIGMA_A_WARN_LOW/HIGH`). No `NaN` should reach an output file — that one is a goal, not
   yet a hard gate.

5. **No bare `.iloc[-1]`** on a price/financial series without first dropping missing rows —
   this class of bug produced the KHC NaN cascade (fixed in `6eb9826`). There is no shared
   `clean_price_series()` helper; each call site guards with `.dropna()` before `.iloc[-1]`
   (see `dashboard/submission.py:40`, `mdt/__main__.py:56`, `dashboard/excel.py:142`). If you
   add a fourth call site, factor the helper out rather than copying the guard again.

6. **Small-probability arithmetic must not silently overflow.** `exp(2/CCM)` in
   `pit_pd_first_hitting()` overflows for tiny CCM and is currently guarded by
   `try/except OverflowError`. Preferred direction is log space
   (`scipy.special.log_ndtr` / `logsumexp`) with a finiteness assert; do not remove the
   existing guard without replacing it.

7. **One writer per artifact.** Exactly one module writes the deliverable workbook
   (`dashboard/submission.py`), driven by a declared schema constant. No hand-written sheets,
   ever.

8. **Reproducibility.** `raw_data_architecture/lineage.py` records run provenance. A full
   manifest (git SHA, package version, input hashes, data vintage, config, timestamp) is a
   known gap — extend `lineage.py` rather than starting a parallel mechanism. There are no
   committed offline fixtures; tests that need the proprietary workbook skip automatically so
   a fresh clone stays green. Keep that skip behaviour working.

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

- **Drift is noise-dominated.** `η_A` from ~252 daily returns is noisy (the deck says it
  "makes both unstable"); since `µ = ln(A/D)/|η_A − σ_A²/2|`, µ and CCM inherit that noise.
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
  from the paper; it is internally consistent and reproduces Tables 13/14, so it is treated
  as authoritative. Discussed in `docs/GAP_ANALYSIS.md`.
- **Market-implied PIT PDs are liquidity-sensitive.** For large, liquid, investment-grade
  names PIT PD is legitimately ~0 — compare firms by DD and RiskScore instead. Typical asset
  volatilities land in ~10–60%.
- **Data path is in memory.** Immutable raw/clean Parquet boundaries are a future milestone
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
local/                   proprietary paper, deck, conversion workbook — GIT-IGNORED
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
python run.py COST KO --years 2           # legacy workflow entry
pytest                                    # offline suite, 24 tests
```

`mdt` is also installed as a console script (`[project.scripts]` in `pyproject.toml`).
TTC/S&P conversion requires `local/TiC_TTC_conversion.xlsx`; without it the pipeline still
runs and reports σ_A / DD / PIT PD, and the grid tests skip.

## Acceptance gates

There is **no CI in this repo** (no `.github/`, no pre-commit, no ruff/black/mypy config or
dependency). These are the standards a change is held to — enforce them by running them, and
record in `docs/DEVLOG.md` what you actually ran:

- Paper Tables 13/14 and the `alpha_FH(1.5) = 0.91906` / `CCM* = 1.35373` anchors still
  reproduce (`tests/test_measures.py`, `tests/test_conversion.py`).
- `tests/test_no_lookahead.py` passes, and any alignment change adds to it.
- Full `pytest` run is green from a fresh clone **without** `local/` present.
- Invariants above hold across the 10-company batch.
- `git ls-files --cached` contains no `.pdf`, `.xlsx`, `.csv`, or `.parquet`, and nothing
  under `local/`.
- `docs/DEVLOG.md` is updated in the same push.
