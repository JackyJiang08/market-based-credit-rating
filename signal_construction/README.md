# Layer 3 — Signal Construction

**Status: prototype only; outside the current active scope.**

`config.py` owns model-only assumptions. `credit.py` preserves the existing
`CreditModel` interface, Merton/KMV baseline,
and TIC placeholder. Before this layer becomes active it needs a point-in-time
input contract, rolling signal history, model versioning, rating mapping, and
offline tests.

This layer may consume validated Layer 2 panels. It must not download source
data or write presentation-specific dashboard files.
