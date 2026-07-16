"""Per-company persistence of raw and cleaned datasets.

Raw acquisitions land under ``raw_data_architecture/data/{TICKER}/`` and the
cleaned/aligned panel under ``data_cleaning/data/{TICKER}/``, each written as
both CSV (diff-friendly) and XLSX (analyst-friendly). Both trees are
git-ignored, so downloaded data never enters version control.
"""

from __future__ import annotations

import logging
import os

import pandas as pd

from . import config
from .company import CompanyData

LOG = logging.getLogger("pfpa.persistence")


def _write(df: pd.DataFrame, directory: str, name: str, index: bool = True) -> None:
    if df is None or df.empty:
        return
    os.makedirs(directory, exist_ok=True)
    df.to_csv(os.path.join(directory, f"{name}.csv"), index=index)
    try:
        df.to_excel(os.path.join(directory, f"{name}.xlsx"), index=index)
    except Exception as exc:  # noqa: BLE001 - xlsx optional, csv is canonical
        LOG.debug("xlsx write skipped for %s/%s: %s", directory, name, exc)


def save_company(data: CompanyData) -> dict[str, str]:
    """Persist a company's raw and cleaned datasets. Returns the two dirs."""
    raw_dir = os.path.join(config.RAW_DATA_DIR, data.ticker)
    clean_dir = os.path.join(config.CLEAN_DATA_DIR, data.ticker)

    # Raw acquisitions
    _write(data.prices, raw_dir, "prices")
    _write(data.q_balance, raw_dir, "quarterly_balance_sheet")
    _write(data.a_balance, raw_dir, "annual_balance_sheet")

    # Cleaned / aligned outputs
    _write(data.panel, clean_dir, "aligned_panel")
    _write(data.debt_schedule, clean_dir, "debt_schedule")

    LOG.info("  saved raw -> %s | clean -> %s",
             os.path.relpath(raw_dir, config.PROJECT_ROOT),
             os.path.relpath(clean_dir, config.PROJECT_ROOT))
    return {"raw": raw_dir, "clean": clean_dir}
