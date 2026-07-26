"""Layer 4 configuration: published artifact paths."""

from __future__ import annotations

import os

from creditrating._paths import REPO_ROOT as PROJECT_ROOT  # noqa: E501

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "dashboard", "output")
