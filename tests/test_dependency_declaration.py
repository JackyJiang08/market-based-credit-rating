"""Canary: every third-party import in the package is a declared dependency.

The refactor push shipped with pydantic/structlog/typer imported but never
added to requirements.txt -- the fresh-clone install story was false and CI
only half-worked because workflows installed packages ad hoc. This test
makes that class of defect impossible to ship quietly: it walks every import
in packages/core/creditrating and asserts the distribution is declared in
requirements.txt (runtime code must never depend on dev-only tooling).
"""

from __future__ import annotations

import ast
import os
import sys

STDLIB = getattr(sys, "stdlib_module_names", set())
# import name -> distribution name where they differ
DIST = {"yaml": "PyYAML", "sklearn": "scikit-learn"}
PKG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "packages",
    "core",
    "creditrating",
)


def _imports(path: str) -> set[str]:
    tree = ast.parse(open(path, encoding="utf-8").read())
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out.add(node.module.split(".")[0])
    return out


def test_every_runtime_import_is_declared_in_requirements():
    declared = ""
    root = os.path.dirname(PKG.rsplit(os.sep + "packages", 1)[0] + os.sep + "x")
    with open(os.path.join(root, "requirements.txt"), encoding="utf-8") as fh:
        declared = fh.read().lower()

    third_party: set[str] = set()
    for dirpath, _dirs, files in os.walk(PKG):
        for f in files:
            if f.endswith(".py"):
                third_party |= _imports(os.path.join(dirpath, f))

    missing = []
    for mod in sorted(third_party):
        if mod in ("creditrating",) or mod in STDLIB:
            continue
        # stdlib fallback for interpreters without stdlib_module_names (<3.10)
        if not STDLIB:
            try:
                origin = __import__(mod).__file__ or ""
            except Exception:
                origin = ""
            if "site-packages" not in origin:
                continue
        dist = DIST.get(mod, mod).lower().replace("_", "-")
        if dist not in declared.replace("_", "-"):
            missing.append(f"{mod} (declare as {DIST.get(mod, mod)})")
    assert not missing, f"undeclared runtime dependencies: {missing}"
