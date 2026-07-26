"""One-click command-line interface for the market-based credit-rating pipeline.

    python -m mdt rate AAPL                    # one company -> table + report
    python -m mdt batch config/companies.yaml  # the batch run

The entry point lives in ``mdt.__main__:main`` (used by both ``python -m mdt``
and the installed ``mdt`` console script).
"""
