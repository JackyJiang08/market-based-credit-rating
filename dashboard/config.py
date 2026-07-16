"""Layer 4 configuration: published artifact paths."""

from __future__ import annotations

import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "dashboard", "output")
