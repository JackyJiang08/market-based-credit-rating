"""Repository-root anchor for runtime artifact paths.

The pipeline's artifact directories (outputs/, data/cache/, the per-company
data trees, local/) live at the repository root, not inside the package.
Before the package move every module derived the root from its own __file__;
this module is now the single place that knowledge lives. Override with
CREDITRATING_ROOT for installed (non-repo) deployments.
"""

from __future__ import annotations

import os

REPO_ROOT = os.environ.get(
    "CREDITRATING_ROOT",
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))),
)
