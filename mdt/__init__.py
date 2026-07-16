"""One-click command-line interface for the PFPA credit-rating pipeline.

    python -m mdt rate AAPL                    # one company -> table + report
    python -m mdt batch config/companies.yaml  # the assignment batch

The entry point lives in ``mdt.__main__:main`` (used by both ``python -m mdt``
and the installed ``mdt`` console script).
"""
