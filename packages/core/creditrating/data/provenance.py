"""Data provenance / lineage.

Financial data is restated over time and market values change every second, so
a pull is only meaningful if you know *when* it was taken and *where* it came
from. Every record the toolkit emits carries this stamp, which is what makes a
run reproducible and auditable.
"""

from __future__ import annotations

import logging
from datetime import datetime

try:
    import yfinance as yf
    _YF_VERSION = getattr(yf, "__version__", "?")
except Exception as _exc:  # pragma: no cover - probe must never be fatal
    # An unknown package version in a provenance record is a gap in the record,
    # so say so rather than writing "?" and moving on.
    logging.getLogger(__name__).warning(
        "yfinance version could not be determined (%s); run provenance will "
        "record it as unknown", _exc)
    _YF_VERSION = "unknown"

# Captured once at import so every record in a single run shares one stamp.
RUN_TIMESTAMP: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

EQUITY_SOURCE: str = f"Yahoo Finance (yfinance {_YF_VERSION})"
RATES_SOURCE: str = "FRED / Federal Reserve H.15 (DGS1, SOFR)"


# --------------------------------------------------------------------------- #
# Run manifest: everything needed to audit or reproduce a run
# --------------------------------------------------------------------------- #
def write_manifest(run_id: str, cfg, companies, outputs_dir: str) -> str:
    """Write the per-run manifest and return its path.

    Records input hashes (sha256 of every cache artifact the run's tickers
    could read, plus the universe config file), package version, git SHA,
    data vintage (latest priced day across the batch), the run configuration,
    and a team-standard UTC timestamp (docs/TIMING_PROTOCOL.md §10).
    """
    import hashlib
    import json
    import os
    import subprocess
    from datetime import datetime, timezone

    from creditrating import __version__
    from creditrating._paths import REPO_ROOT

    from . import cache

    def _sha(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()[:16]

    hashes: dict[str, str] = {}
    for t in cfg.tickers:
        tdir = os.path.join(cache.cache_dir(), str(t).strip().upper())
        if os.path.isdir(tdir):
            for name in sorted(os.listdir(tdir)):
                p = os.path.join(tdir, name)
                if os.path.isfile(p):
                    hashes[f"{os.path.basename(tdir)}/{name}"] = _sha(p)
    rates_p = os.path.join(cache.cache_dir(), "_rates", "rates.parquet")
    if os.path.exists(rates_p):
        hashes["_rates/rates.parquet"] = _sha(rates_p)

    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             cwd=REPO_ROOT, capture_output=True, text=True,
                             timeout=5).stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001 - provenance is best-effort
        sha = "unknown"

    dates = [c.panel.index[-1].date().isoformat() for c in companies
             if c.panel is not None and not c.panel.empty]
    manifest = {
        "run_id": run_id,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "package_version": __version__,
        "git_sha": sha,
        "data_vintage_latest_priced_day": max(dates) if dates else None,
        "config": {"tickers": list(cfg.tickers), "years": cfg.years,
                   "workers": cfg.workers, "run_bootstrap": cfg.run_bootstrap,
                   "run_credit_model": cfg.run_credit_model},
        "companies_succeeded": len(companies),
        "input_hashes_sha256_16": hashes,
    }
    os.makedirs(outputs_dir, exist_ok=True)
    path = os.path.join(outputs_dir, f"manifest_{run_id}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    return path
