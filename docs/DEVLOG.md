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
