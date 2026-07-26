Golden files for the workbook. `cost_asset_row.csv` is the Asset row the
committed COST fixture must produce (deterministic: fixed fixture data,
deterministic EM, seeded bootstrap). Regenerate only for a deliberate model
change, and say why in the commit:

    python -c "import sys; sys.path.insert(0,'packages/core'); \
      from creditrating.data import cache; \
      from creditrating.data.pipeline import RunConfig, fetch_company; \
      from creditrating.io import records; \
      c = fetch_company('COST', RunConfig(tickers=['COST']), cache.load_rates()); \
      records.asset_frame([c]).to_csv('tests/golden/cost_asset_row.csv', index=False)"
