"""Typed domain models (pydantic v2) encoding the pipeline's invariants.

These are the contracts the engineering rules state in prose, as code:

    CompanyInputs    E > 0, D > 0, r in a sane band
    AssetEstimates   A > D (the model's own precondition), 0 < sigma_A < 3,
                     EM converged within EM_MAX_ITER (= 20)
    RiskMeasures     0 <= PD <= 1 for every probability, RiskScore >= 0
    RatingResult     a letter never appears without basis + determination

The pipeline itself still degrades gracefully (statuses and flags, per
engineering rule 3); these models are the *assertion layer* used by
diagnostics.checks to verify a finished run and by any future service
boundary (phase 11) to refuse malformed payloads at the edge.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

EM_MAX_ITER = 20
SIGMA_MAX = 3.0


class CompanyInputs(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str = Field(min_length=1, max_length=12)
    equity_value: float = Field(gt=0, description="market cap E on the valuation date")
    default_point: float = Field(gt=0, description="D = ST + 0.5*LT")
    risk_free_rate: float = Field(ge=-0.05, le=0.30)
    prices_observations: int = Field(ge=1)


class AssetEstimates(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str
    asset_value: float = Field(gt=0)
    default_point: float = Field(gt=0)
    sigma_a: float = Field(gt=0, lt=SIGMA_MAX)
    eta_a: float
    em_iterations: int = Field(ge=1, le=EM_MAX_ITER)
    em_converged: bool

    @model_validator(mode="after")
    def _asset_clears_barrier(self) -> "AssetEstimates":
        if self.asset_value <= self.default_point:
            raise ValueError(
                f"A ({self.asset_value:.4g}) <= D ({self.default_point:.4g}): "
                "the inversion's own precondition fails")
        return self


class RiskMeasures(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str
    risk_score: float = Field(ge=0)
    dd: float
    edf: float = Field(ge=0, le=1)
    pit_pd: float = Field(ge=0, le=1)
    ttc_pd: Optional[float] = Field(default=None, ge=0, le=1)


class RatingResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str
    letter: Optional[str] = None
    basis: Optional[str] = None
    determination: Optional[str] = None
    interval_low: Optional[str] = None
    interval_high: Optional[str] = None

    @model_validator(mode="after")
    def _letter_never_bare(self) -> "RatingResult":
        if self.letter is not None:
            if not self.basis or not self.determination:
                raise ValueError(
                    f"{self.ticker}: a letter ({self.letter}) must carry its "
                    "basis and determination -- a bare letter is unpublishable")
        return self
