"""Compatibility shim: the CLI moved to creditrating.cli.

`python -m mdt` and the `mdt` console script keep working; new code should
call `creditrating.cli` (or the `creditrating` console script) directly.
The sys.path insert keeps the zero-install story true from a fresh clone;
an installed wheel imports creditrating directly and never touches this.
"""

import os
import sys

_PKG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "packages", "core")
if _PKG not in sys.path:
    sys.path.insert(0, _PKG)

from creditrating.cli import main  # noqa: E402,F401
