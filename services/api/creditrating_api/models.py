"""API models: thin composition over the creditrating domain models.

The domain models (creditrating.domain) ARE the response payloads -- there
are no parallel DTOs. The envelopes here only compose them with the context
a caveat-free number would be missing: basis, determination, drift regime,
applicability, reason codes, and provenance. The API is designed so a client
cannot render a number without its caveat riding along.
"""

from __future__ import annotations

from typing import Any, Optional

from creditrating.domain import AssetEstimates, RatingResult, RiskMeasures
from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str
    correlation_id: str


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class RateRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=12)
    as_of: Optional[str] = Field(
        default=None,
        description="NOT SUPPORTED: point-in-time reruns need immutable "
        "vintage snapshots (TIMING_PROTOCOL section 9). Rejected explicitly.",
    )
    config: Optional[dict[str, Any]] = None
    live: bool = Field(
        default=False,
        description="Explicitly allow a network fetch. Default is offline: "
        "only tickers present in the committed/populated cache are served.",
    )


class BatchRequest(BaseModel):
    tickers: list[str] = Field(min_length=1, max_length=200)
    as_of: Optional[str] = None
    live: bool = False


class DriftInfo(BaseModel):
    regime: Optional[str] = None
    t_stat: Optional[float] = None
    se: Optional[float] = None
    weakly_identified: Optional[bool] = None


class ApplicabilityInfo(BaseModel):
    model_applicable: Optional[bool] = None
    reason_code: Optional[str] = None
    reason_text: Optional[str] = None
    firm_type: Optional[str] = None


class Provenance(BaseModel):
    correlation_id: str
    package_version: str
    data_vintage_last_priced_day: Optional[str] = None
    statement_period_end: Optional[str] = None
    cache_hit: bool
    generated_utc: str


class RatingEnvelope(BaseModel):
    """One company's full result. Domain models embedded, never flattened."""

    ticker: str
    company: Optional[str] = None
    estimates: Optional[AssetEstimates] = None
    measures: Optional[RiskMeasures] = None
    rating: RatingResult
    drift: DriftInfo
    applicability: ApplicabilityInfo
    flags: list[str] = []
    reason_codes: list[str] = []
    provenance: Provenance


class BatchStatus(BaseModel):
    job_id: str
    status: str  # queued | running | done | failed
    total: int
    completed: int
    determinations: dict[str, int] = {}
    results: list[RatingEnvelope] = []


class SearchHit(BaseModel):
    ticker: str
    name: Optional[str] = None
    sector: Optional[str] = None
    cached: bool


class HealthStatus(BaseModel):
    status: str
    version: str
    conversion_workbook_present: bool
    cached_tickers: int
    offline_first: bool = True
