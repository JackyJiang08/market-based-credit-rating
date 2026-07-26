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

from . import cleaning_config as config
from .company import CompanyData

LOG = logging.getLogger(__name__)


def _write(df: pd.DataFrame, directory: str, name: str, index: bool = True) -> None:
    if df is None or df.empty:
        return
    os.makedirs(directory, exist_ok=True)
    df.to_csv(os.path.join(directory, f"{name}.csv"), index=index)
    try:
        df.to_excel(os.path.join(directory, f"{name}.xlsx"), index=index)
    except (OSError, ImportError, ValueError) as exc:
        # CSV is canonical so this is not fatal, but DEBUG meant nobody ever
        # saw it. A run that silently produced half its artifacts looked clean.
        LOG.warning(
            "xlsx NOT written for %s/%s (%s); CSV is available",
            os.path.basename(directory),
            name,
            exc,
        )


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

    LOG.info(
        "  saved raw -> %s | clean -> %s",
        os.path.relpath(raw_dir, config.PROJECT_ROOT),
        os.path.relpath(clean_dir, config.PROJECT_ROOT),
    )
    return {"raw": raw_dir, "clean": clean_dir}
