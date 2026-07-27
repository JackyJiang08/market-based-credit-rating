"""Headline numbers cannot drift.

The four numbers this project leads with (the amplification factor, the
agency rank correlation, the bootstrap ordering stability, and the median
notch optimism) live in exactly one place —
``docs/analysis/data/headline.json`` — and every user-facing surface must
display them. Two guards:

1. the JSON itself must match a recomputation from the committed
   run-of-record CSVs, so the source of truth cannot go stale;
2. each display string must appear in every surface that cites it, and the
   superseded value (×4,077, from before the recorded re-run) must appear
   in none of them.
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HEADLINE = json.loads((REPO / "docs" / "analysis" / "data" / "headline.json").read_text())

# Every user-facing text surface. DEVLOG is deliberately absent: it is a
# history and may cite superseded values in past entries.
SURFACES = [
    "README.md",
    "docs/UNCERTAINTY.md",
    "docs/PROJECT_SUMMARY.md",
    "docs/analysis/VALIDATION.md",
    "apps/terminal/src/app/page.tsx",
    "apps/terminal/src/app/layout.tsx",
    "apps/terminal/src/app/about/page.tsx",
]

# display string -> surfaces that must show it (subset of SURFACES)
CITATIONS = {
    "amplification_display": [
        "README.md",
        "docs/UNCERTAINTY.md",
        "docs/PROJECT_SUMMARY.md",
        "docs/analysis/VALIDATION.md",
        "apps/terminal/src/app/page.tsx",
        "apps/terminal/src/app/layout.tsx",
        "apps/terminal/src/app/about/page.tsx",
    ],
    "spearman_display": [
        "README.md",
        "docs/PROJECT_SUMMARY.md",
        "apps/terminal/src/app/page.tsx",
    ],
    "tau_display": [
        "README.md",
        "docs/PROJECT_SUMMARY.md",
        "apps/terminal/src/app/page.tsx",
    ],
    "notch_display": [
        "README.md",
        "docs/PROJECT_SUMMARY.md",
        "apps/terminal/src/app/page.tsx",
    ],
}


def _existing(paths: list[str]) -> list[Path]:
    out = [REPO / p for p in paths]
    missing = [p for p in out if not p.exists()]
    assert not missing, f"cited surfaces missing from the tree: {missing}"
    return out


def test_headline_json_matches_run_of_record_data() -> None:
    amp = {
        r["quantity"]: float(r["median_relative_width"])
        for r in csv.DictReader(open(REPO / "docs/figures/data/amplification.csv"))
    }
    assert HEADLINE["amplification_pit_vs_riskscore"] == round(
        amp["pit_pd"] / amp["risk_score"]
    )

    disc = {
        r["stratum"]: r
        for r in csv.DictReader(open(REPO / "docs/analysis/data/discrimination.csv"))
    }
    assert HEADLINE["spearman_all_names"] == round(
        float(disc["all names with estimates"]["spearman"]), 2
    )
    assert HEADLINE["spearman_scale_resolved"] == round(
        float(disc["SCALE_RESOLVED only"]["spearman"]), 2
    )

    stab = next(csv.DictReader(open(REPO / "docs/figures/data/rank_stability.csv")))
    assert HEADLINE["tau_median"] == round(float(stab["tau_median"]), 3)

    notch = [
        float(r["notch_error"])
        for r in csv.DictReader(open(REPO / "docs/analysis/data/notch_errors.csv"))
    ]
    assert HEADLINE["median_notch_error"] == int(statistics.median(notch))


def test_display_strings_are_consistent_with_values() -> None:
    n = HEADLINE["amplification_pit_vs_riskscore"]
    assert HEADLINE["amplification_display"] == f"×{n:,}"
    assert str(HEADLINE["spearman_all_names"]) in HEADLINE["spearman_display"]
    assert str(HEADLINE["tau_median"]) in HEADLINE["tau_display"]
    assert str(HEADLINE["median_notch_error"]) in HEADLINE["notch_display"]


@pytest.mark.parametrize("key", sorted(CITATIONS))
def test_every_surface_cites_the_current_value(key: str) -> None:
    display = HEADLINE[key]
    for path in _existing(CITATIONS[key]):
        assert display in path.read_text(), (
            f"{path.relative_to(REPO)} must cite {display!r} "
            f"(source of truth: docs/analysis/data/headline.json)"
        )


def test_superseded_values_appear_nowhere() -> None:
    for stale in HEADLINE["superseded_values"]:
        for path in _existing(SURFACES):
            assert stale not in path.read_text(), (
                f"{path.relative_to(REPO)} still cites the superseded {stale!r}; "
                f"current values live in docs/analysis/data/headline.json"
            )
