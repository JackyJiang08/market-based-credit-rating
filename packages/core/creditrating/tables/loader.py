"""Conversion-grid loading: the one place the reference workbook is parsed.

The grids themselves are licensed reference material and are NEVER committed;
they live in the git-ignored ``local/`` tree (see NOTICE). This module owns
parsing, CSV caching under ``local/tables/``, and the structural validation
of what was parsed. The model layer consumes ``ConversionTables`` and never
touches the workbook.
"""

from __future__ import annotations

import functools
import logging
import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .._paths import REPO_ROOT as _PROJECT_ROOT

LOG = logging.getLogger(__name__)

DEFAULT_XLSX = os.path.join(_PROJECT_ROOT, "local", "TiC_TTC_conversion.xlsx")
CACHE_DIR = os.path.join(_PROJECT_ROOT, "local", "tables")


@dataclass
class ConversionTables:
    ccm_axis: np.ndarray          # grid rows, ascending
    mu_axis: np.ndarray           # grid columns, ascending
    ttc_grid: np.ndarray          # TTC (S&P-equivalent) PD by [CCM, mu]
    pit_grid: np.ndarray          # PIT PD by [CCM, mu] (cross-check)
    sp_labels: list[str]          # S&P letters, best -> worst
    sp_thresholds: np.ndarray     # ascending lower-bound PD per label



def _axis(series: pd.Series) -> np.ndarray:
    return pd.to_numeric(series, errors="coerce").to_numpy()


def _grid(block: pd.DataFrame) -> np.ndarray:
    return block.apply(pd.to_numeric, errors="coerce").to_numpy()


@functools.lru_cache(maxsize=1)
def load_tables(xlsx_path: str = DEFAULT_XLSX) -> ConversionTables:
    """Parse the conversion workbook and cache CSV copies under local/tables."""
    if not os.path.exists(xlsx_path):
        raise FileNotFoundError(
            f"Conversion workbook not found at {xlsx_path}. It is proprietary "
            "reference data kept out of git; place it under local/ to enable "
            "the grid route.")
    xl = pd.ExcelFile(xlsx_path)

    def parse_grid(sheet: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        raw = pd.read_excel(xl, sheet, header=None)
        ccm_axis = _axis(raw.iloc[2:, 0])      # rows = CCM
        mu_axis = _axis(raw.iloc[1, 1:])       # cols = mu
        grid = _grid(raw.iloc[2:, 1:])
        return ccm_axis, mu_axis, grid

    ccm_axis, mu_axis, ttc = parse_grid("TTC")
    _, _, pit = parse_grid("PIT")

    sp_raw = pd.read_excel(xl, "SP", header=None)
    labels, thresholds = [], []
    for _, row in sp_raw.iterrows():
        label, thr = row.iloc[0], pd.to_numeric(row.iloc[1], errors="coerce")
        if isinstance(label, str) and label.strip() and pd.notna(thr):
            labels.append(label.strip())
            thresholds.append(float(thr))

    tables = ConversionTables(ccm_axis, mu_axis, ttc, pit,
                              labels, np.asarray(thresholds))
    _cache_csv(tables)
    return tables


def _cache_csv(tables: ConversionTables) -> None:
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        pd.DataFrame(tables.ttc_grid, index=tables.ccm_axis,
                     columns=tables.mu_axis).to_csv(os.path.join(CACHE_DIR, "ttc.csv"))
        pd.DataFrame({"SP": tables.sp_labels,
                      "PD_threshold": tables.sp_thresholds}).to_csv(
            os.path.join(CACHE_DIR, "sp_thresholds.csv"), index=False)
    except OSError as exc:
        # Caching is best-effort, but a read-only disk or a permissions problem
        # should not be invisible -- it was silently swallowed before.
        LOG.warning("conversion table cache not written to %s: %s", CACHE_DIR, exc)
