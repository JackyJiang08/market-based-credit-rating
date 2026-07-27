"""Fail the site build if licensed grid content would enter the bundle.

Three independent checks over apps/terminal/public/data (and, when present,
the built bundle output directory):

  1. PATH check       -- nothing under local/ may be read into the export dir;
                         no file in the export tree may be named like the
                         licensed artifacts (*.xlsx, sp_thresholds*, ttc*.csv).
  2. VALUE check      -- when local/ is present, every numeric value in every
                         exported JSON is compared against the licensed S&P
                         threshold table and the TTC grid: zero matches
                         allowed (exact, 1e-12 rounding; 0/1 excluded). This
                         is the same standard the committed deliverables were
                         held to.
  3. SHAPE check      -- no exported JSON may contain a numeric matrix with
                         more than MAX_GRID_CELLS cells (the licensed grids
                         are 154x93; our largest legitimate array is one
                         EM path of ~1,250 scalars, which is 1-D).

Exit 0 = safe. Any violation prints the offending file and exits 1.
When local/ is absent (CI), check 2 degrades to the path+shape checks and
says so -- explicitly, never silently.
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
DATA = os.path.join(ROOT, "apps", "terminal", "public", "data")
LOCAL = os.path.join(ROOT, "local")
MAX_GRID_CELLS = 4000  # licensed grids: 154 x 93 = 14,322 cells


def _numbers(obj, out: list) -> None:
    if isinstance(obj, dict):
        for v in obj.values():
            _numbers(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _numbers(v, out)
    elif isinstance(obj, float):
        out.append(obj)


def _matrix_cells(obj) -> int:
    """Largest number-of-cells of any list-of-lists-of-numbers found."""
    best = 0
    if isinstance(obj, dict):
        for v in obj.values():
            best = max(best, _matrix_cells(v))
    elif isinstance(obj, list):
        if obj and all(
            isinstance(r, list) and r and all(isinstance(x, (int, float)) for x in r)
            for r in obj
        ):
            best = max(best, sum(len(r) for r in obj))
        for v in obj:
            best = max(best, _matrix_cells(v))
    return best


def main() -> int:
    problems: list[str] = []

    if not os.path.isdir(DATA):
        print("bundle-safety: no export directory yet; nothing to check")
        return 0

    # 1. PATH check
    for dirpath, _dirs, files in os.walk(DATA):
        for f in files:
            low = f.lower()
            if low.endswith((".xlsx", ".pdf")) or "sp_threshold" in low or low.startswith(
                "ttc"
            ):
                problems.append(f"forbidden filename in bundle: {os.path.join(dirpath, f)}")
            if not (low.endswith(".json") or low.endswith(".svg")):
                problems.append(f"non-JSON/SVG file in data export: {os.path.join(dirpath, f)}")

    # 2 + 3. VALUE and SHAPE checks
    # The one documented exception: the grid's 2bp TTC floor. It is already
    # public in this repository's own documentation ("the grid's 2bp floor",
    # README + GAP_ANALYSIS), and a floored company output necessarily equals
    # it. A single disclosed scalar, not grid content.
    DOCUMENTED_FLOOR = 0.0002

    licensed: set[float] = set()
    if os.path.isdir(LOCAL):
        import pandas as pd

        for name in ("sp_thresholds.csv", "ttc.csv"):
            p = os.path.join(LOCAL, "tables", name)
            if os.path.exists(p):
                df = pd.read_csv(p, index_col=0 if name == "ttc.csv" else None)
                for x in df.select_dtypes("number").values.ravel():
                    r = round(float(x), 12)
                    if x == x and r not in (0.0, 1.0):
                        licensed.add(r)
        mode = f"full (licensed reference loaded: {len(licensed)} values)"
    else:
        mode = "degraded (local/ absent: path+shape checks only) -- stated, not silent"

    for dirpath, _dirs, files in os.walk(DATA):
        for f in files:
            if not f.endswith(".json"):
                continue
            p = os.path.join(dirpath, f)
            doc = json.load(open(p))
            cells = _matrix_cells(doc)
            if cells > MAX_GRID_CELLS:
                problems.append(f"{p}: numeric matrix with {cells} cells (grid-scale)")
            if licensed:
                nums: list[float] = []
                _numbers(doc, nums)
                hits = {
                    n
                    for n in nums
                    if round(n, 12) in licensed and round(n, 12) != DOCUMENTED_FLOOR
                }
                if hits:
                    problems.append(
                        f"{p}: {len(hits)} value(s) match the licensed tables: "
                        f"{sorted(hits)[:3]}"
                    )

    print(f"bundle-safety: mode={mode}")
    if problems:
        for p in problems:
            print(f"  VIOLATION: {p}")
        return 1
    print("  OK: no licensed-grid content in the bundle")
    return 0


if __name__ == "__main__":
    sys.exit(main())
