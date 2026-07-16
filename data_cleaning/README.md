# Layer 2 — Data Cleaning

**Status: active.**

This layer converts source-shaped data into normalized, model-ready panels. Its
transformations should remain deterministic and independently testable.

## Current modules

- `transforms.py`: statement parsing, debt schedule, default point, shares.
- `alignment.py`: daily price/debt/rate alignment.
- `config.py`: normalization mappings, debt rules, and clean-data paths.
- `company.py`: transitional in-memory company container.
- `workflow.py`: backward-compatible orchestration entry point.

## Contract

Input: Layer 1 DataFrames or, in the target architecture, raw snapshot IDs.

Output: validated clean DataFrames carrying `event_date`, `available_at`,
`ingested_at`, and the input `run_id`.

## Known timing gap

The current alignment uses statement period-end dates as join dates. A filing
is generally available after its period end, so a true point-in-time panel must
join on publication/availability time instead. Until this is implemented, the
panel must not be described as backtest-safe. All alignment changes must follow
[`../docs/TIMING_PROTOCOL.md`](../docs/TIMING_PROTOCOL.md).
