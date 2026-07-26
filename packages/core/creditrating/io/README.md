# Layer 4 — Dashboard

**Status: publishing prototype only; no interactive dashboard yet.**

`config.py` owns publication paths. The existing Excel and tidy-table exporters are retained here. A future
dashboard must consume published Layer 3 signal tables and must not download,
clean, or model data during page rendering.

Generated compatibility artifacts are written under `output/` and are ignored
by Git except for `.gitkeep`.
