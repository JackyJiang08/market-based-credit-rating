# Layer 1 — Raw Data Architecture

**Status: active.**

This layer owns external acquisition and source-level provenance. It may talk
to Yahoo Finance and FRED, but it must not perform credit modelling or format
dashboard output.

## Current modules

- `config.py`: source parameters, universe, and raw-data paths.
- `lineage.py`: extraction timestamp and source identity.
- `sources.py`: Yahoo/FRED adapters with retry and backoff.

## Contract

Input: ticker universe, date window, and source configuration.

Output today: source-shaped pandas DataFrames.

Target output: immutable Parquet snapshots plus a run manifest containing
`run_id`, request parameters, source, schema version, row count, and
`ingested_at`.
