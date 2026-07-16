"""Submission workbook schema test (offline; writes to a temp dir)."""

from __future__ import annotations

import pandas as pd

from data_cleaning.company import CompanyData
from dashboard import submission


def _minimal_company() -> CompanyData:
    idx = pd.bdate_range("2024-01-02", periods=60)
    panel = pd.DataFrame(
        {"ShortTermDebt": 100.0, "LongTermDebt": 200.0, "RiskFree_R": 0.04},
        index=idx)
    c = CompanyData(ticker="TST", name="Test Co")
    c.panel = panel
    c.debt_schedule = pd.DataFrame({"2024-06-30": [300.0]}, index=["Total Debt"])
    c.reference_shares, c.last_close = 1000.0, 50.0
    c.sigma_A, c.eta_A, c.asset_value = 0.25, 0.08, 2.5e5
    c.em_iters, c.em_converged = 3, True
    c.mu, c.ccm, c.tic, c.risk_score = 12.0, 1.5, 0.12, 12.0
    c.dd, c.edf, c.pit_pd = 2.5, 0.006, 0.05
    c.ttc_pd, c.sp_rating, c.outlook, c.rating_off_grid = 0.01, "BB", 0.04, False
    return c


def test_submission_schema(tmp_path, monkeypatch):
    monkeypatch.setattr(submission, "OUTPUT_DIR", str(tmp_path))
    path = submission.write_submission([_minimal_company()])

    asset = pd.read_excel(path, "Asset")
    for col in ["Company", "Symbol", "sigma A", "R", "eta", "CCM", "mu", "TiC",
                "Risk Score", "DD", "EDF", "PIT PD", "TTC PD", "SP Rating", "Outlook"]:
        assert col in asset.columns
    assert asset.loc[0, "Symbol"] == "TST"
    assert asset.loc[0, "Total Debt"] == 300.0
    # R is the realized drift = eta - sigma^2/2 (drives DD).
    assert abs(asset.loc[0, "R"] - (0.08 - 0.5 * 0.25 ** 2)) < 1e-9

    validation = pd.read_excel(path, "validation")
    assert "Warnings" in validation.columns
    assert validation.loc[0, "EM converged"] in (True, "True")
