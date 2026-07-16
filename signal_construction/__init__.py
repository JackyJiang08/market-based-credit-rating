"""Layer 3: credit-risk modelling.

The EM asset-value estimator (``em``), the TiC first-passage measures
(``measures``), and the PIT->TTC->S&P conversion (``conversion``) live here.
They are intentionally not imported at package import time so Layers 1-2 and the
CLI help stay usable without loading the numeric stack (SciPy); import the
submodules explicitly when needed.
"""
