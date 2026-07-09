# PFPA Market Data Workflow

The project is organized around four explicit workflow layers. Each layer owns
one kind of responsibility and communicates with the next layer through pandas
DataFrames today and versioned Parquet contracts in the target architecture.

## Project structure

```text
PFPA_Intern_Project/
|-- raw_data_architecture/  # Layer 1: Yahoo/FRED acquisition and lineage
|-- data_cleaning/          # Layer 2: normalization and time alignment
|-- signal_construction/    # Layer 3: model prototype
|-- dashboard/              # Layer 4: publishing prototype
|-- docs/                   # Project metadata and supporting documentation
|   |-- DEVLOG.md           # Required update for every push
|   |-- TIMING_PROTOCOL.md  # Mandatory no-look-ahead contract
|   |-- DEPENDENCY_MAPS.md
|   `-- LICENSE
|-- .agents/                # Repository guidance for coding agents
|-- run.py                  # Backward-compatible CLI entry point
|-- pyproject.toml          # Python build and package metadata
`-- requirements.txt
```

## Current status

Only the first two layers are considered active project scope:

1. **Raw Data Architecture** downloads company data from Yahoo Finance and
   rates from FRED, with retry/backoff and run-level provenance.
2. **Data Cleaning** normalizes statements, constructs the debt schedule, and
   aligns prices, debt, and rates into a daily panel.

The existing Merton/KMV code and Excel/long-table exporters are retained inside
Layers 3 and 4 as prototypes. They are not evidence that signal construction or
the dashboard is complete.

## Workflow and dependency rule

```text
raw_data_architecture -> data_cleaning -> signal_construction -> dashboard
```

A layer may consume contracts from a preceding layer. Raw acquisition and
cleaning must never import dashboard code. The temporary compatibility workflow
in `data_cleaning/workflow.py` still invokes the two prototypes and should be
split into stage commands when raw/clean Parquet persistence is implemented.

## Development workflow

Update [`docs/DEVLOG.md`](docs/DEVLOG.md) as part of every push. The newest entry must
summarize the pushed scope, breaking changes, validation, and follow-up work.

## Run the compatibility workflow

```bash
pip install -r requirements.txt
python run.py AAPL --years 2
```

Generated compatibility outputs are written to `dashboard/output/`.

## Next architecture milestone

- Persist immutable source snapshots under `raw_data_architecture/data/`.
- Publish validated model panels under `data_cleaning/data/`.
- Add `event_date`, `available_at`, `ingested_at`, and `decision_at` contracts.
- Add offline fixtures and tests before building Layer 3.

See each layer README for its boundary and maturity. Current code, runtime, and
data dependencies are documented in
[`docs/DEPENDENCY_MAPS.md`](docs/DEPENDENCY_MAPS.md). All time-dependent work
must follow [`docs/TIMING_PROTOCOL.md`](docs/TIMING_PROTOCOL.md).
