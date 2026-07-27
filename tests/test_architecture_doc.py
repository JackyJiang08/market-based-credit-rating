"""Staleness guard: docs/ARCHITECTURE.md must match the actual tree.

DEPENDENCY_MAPS.md rotted for one restructure too many; this test makes the
replacement incapable of silent drift. If a subpackage is added, removed, or
renamed without the diagram following, CI fails here.
"""

from __future__ import annotations

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs", "ARCHITECTURE.md")
PKG = os.path.join(ROOT, "packages", "core", "creditrating")


def test_package_map_matches_the_tree():
    doc = open(DOC, encoding="utf-8").read()

    subpackages = sorted(
        d
        for d in os.listdir(PKG)
        if os.path.isdir(os.path.join(PKG, d)) and not d.startswith("__")
    )
    assert subpackages, "package tree missing?"
    for sub in subpackages:
        assert f"{sub}/" in doc, (
            f"ARCHITECTURE.md package map is stale: subpackage {sub!r} "
            "is not in the diagram"
        )

    for top in ("services/api", "apps/terminal"):
        assert top in doc, f"ARCHITECTURE.md missing {top}"
        assert os.path.isdir(os.path.join(ROOT, top)), f"{top} gone but documented"

    # The doc must not resurrect the pre-restructure names as live modules.
    for ghost in ("raw_data_architecture", "data_cleaning/", "signal_construction"):
        assert ghost not in doc, f"ARCHITECTURE.md references retired layout: {ghost}"


def test_dependency_maps_is_gone():
    assert not os.path.exists(
        os.path.join(ROOT, "docs", "DEPENDENCY_MAPS.md")
    ), "DEPENDENCY_MAPS.md was replaced by ARCHITECTURE.md; it must not return"
