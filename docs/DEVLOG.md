# Development Log

Last updated: 2026-07-09

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

- Repository root: `PFPA_Intern_Project/`.
- Active implementation scope: Layer 1 Raw Data Architecture and Layer 2 Data
  Cleaning.
- Retained prototypes: Layer 3 Signal Construction and Layer 4 Dashboard.
- Current data path is still in memory; immutable raw and clean Parquet
  boundaries have not yet been implemented.
- Current timing gap: statement period-end is still used in alignment instead
  of a true publication-time `available_at` field.

## Recent changes

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

- **Scope:** documentation + IP handling; no code behavior change.
- **Summary:** added `docs/GAP_ANALYSIS.md` mapping the TiC paper and the
  Market-Based Credit Risk deck (KMV/EM/first-passage) to current branch code,
  with a per-concept status table. Recorded resolved conventions: 1-year
  risk-free (DGS1), η_A from EM for DD, ~252-day EM window, public repo with
  instructor IP git-ignored.
- **IP:** the TiC paper, the market-based deck, and `TiC_TTC_conversion.xlsx`
  are kept under `local/` and git-ignored; lookup tables will be local-only.
- **Validation:** confirmed IP artifacts are ignored (`git check-ignore`);
  removed a stray legacy `output/` dir from staging.
- **Follow-ups:** Phase 1 (data-layer completion + no-look-ahead canary test).

### 2026-07-09 - Repository architecture unification

- **Scope:** repository structure, documentation, and dependency ownership.
- **Summary:**
  - Moved the Git repository contents to the `PFPA_Intern_Project` root.
  - Reorganized code into the four workflow layer directories.
  - Split configuration ownership across the four layers.
  - Archived the original assignment and glossary documents.
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
