"""Structural validation for the loaded conversion tables.

Checks the *shape* of what was parsed (axes strictly ascending, grids finite
where defined, thresholds ascending) and the methodology's published anchors.
Used by the test suite and the CI acceptance job; safe to call in production
because it needs nothing but an already-loaded ``ConversionTables``.
"""

from __future__ import annotations

import numpy as np

from .loader import ConversionTables

# Published anchors (methodology Prop. 4.5.2 / Section 5.3).
ALPHA_FH_AT_1_5 = 0.91906
CCM_STAR = 1.35373


def validate(tables: ConversionTables) -> list[str]:
    """Return a list of structural problems; empty means the tables are sound."""
    problems: list[str] = []
    for name, axis in (("ccm_axis", tables.ccm_axis), ("mu_axis", tables.mu_axis)):
        finite = axis[np.isfinite(axis)]
        if finite.size < 2:
            problems.append(f"{name}: fewer than 2 finite points")
        elif not (np.diff(finite) > 0).all():
            problems.append(f"{name}: not strictly ascending")
    for name, grid in (("ttc_grid", tables.ttc_grid), ("pit_grid", tables.pit_grid)):
        vals = grid[np.isfinite(grid)]
        if vals.size == 0:
            problems.append(f"{name}: no finite values")
        elif ((vals < 0) | (vals > 1)).any():
            problems.append(f"{name}: values outside [0, 1]")
    if len(tables.sp_labels) != len(tables.sp_thresholds):
        problems.append("sp label/threshold length mismatch")
    elif not (np.diff(tables.sp_thresholds) > 0).all():
        problems.append("sp_thresholds: not strictly ascending")
    return problems
