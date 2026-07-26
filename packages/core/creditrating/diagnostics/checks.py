"""Post-run sanity checks: assert the domain invariants over a finished batch.

Builds the typed domain models (creditrating.domain) from each finished
CompanyData and reports every violation. Deliberately non-fatal in the
pipeline -- a violation is a loud diagnostic, not an abort -- because the
run's isolation contract says one bad company never takes down a batch. The
same models ARE fatal at any service boundary (phase 11).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import ValidationError

from ..domain import AssetEstimates, RatingResult, RiskMeasures

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..data.company import CompanyData

LOG = logging.getLogger(__name__)


def check_company(c: "CompanyData") -> list[str]:
    """Every domain-invariant violation for one finished company."""
    problems: list[str] = []

    if c.sigma_A is not None and c.asset_value is not None:
        try:
            AssetEstimates(
                ticker=c.ticker, asset_value=c.asset_value,
                default_point=(c.panel["DefaultPointDebt_D"].dropna().iloc[-1]
                               if c.panel is not None and not c.panel.empty
                               and "DefaultPointDebt_D" in c.panel else 1e-9),
                sigma_a=c.sigma_A, eta_a=c.eta_A or 0.0,
                em_iterations=c.em_iters or 1,
                em_converged=bool(c.em_converged),
            )
        except ValidationError as exc:
            problems.append(f"{c.ticker}: {exc.errors()[0]['msg']}")

    if c.risk_score is not None:
        try:
            RiskMeasures(
                ticker=c.ticker, risk_score=c.risk_score, dd=c.dd or 0.0,
                edf=c.edf if c.edf is not None else 0.0,
                pit_pd=c.pit_pd if c.pit_pd is not None else 0.0,
                ttc_pd=c.ttc_pd if c.ttc_pd == c.ttc_pd else None,
            )
        except ValidationError as exc:
            problems.append(f"{c.ticker}: {exc.errors()[0]['msg']}")

    try:
        RatingResult(ticker=c.ticker, letter=c.sp_rating,
                     basis=c.rating_basis, determination=c.rating_determination,
                     interval_low=c.rating_interval_low,
                     interval_high=c.rating_interval_high)
    except ValidationError as exc:
        problems.append(f"{c.ticker}: {exc.errors()[0]['msg']}")

    return problems


def check_batch(companies: list["CompanyData"]) -> list[str]:
    """Violations across a batch; logs each one loudly, returns them all."""
    problems: list[str] = []
    for c in companies:
        for p in check_company(c):
            LOG.error("domain invariant violated: %s", p)
            problems.append(p)
    return problems
