"""Typed data-acquisition failures.

Layer 1 previously let every failure surface as a bare ``Exception``, which
Layer 2 caught and turned into an empty frame. A rate limit, a delisted ticker
and a company that genuinely has no statements were therefore indistinguishable
downstream: all three produced a row with blank measures and a validation note
saying only "EM/measures did not run".

They call for different responses -- retry later, drop the ticker, or accept the
gap -- so they are different exceptions, and the reason reaches the output as
``CompanyData.data_status``.
"""

from __future__ import annotations

import enum
import re


class DataStatus(enum.Enum):
    """Why a company's data is (in)complete. Reaches the validation sheet.

    OK            everything requested was returned.
    NO_DATA       the source answered, and the answer was empty. The ticker is
                  valid; there is simply nothing to model. **Not an error.**
    DELISTED      the symbol is no longer traded, so no current data exists.
    RATE_LIMITED  the source refused us, not the ticker. Retry later; the
                  absence of data says nothing about the company.
    SOURCE_ERROR  transport or parsing failure. Unknown whether data exists.
    """

    OK = "OK"
    NO_DATA = "NO_DATA"
    DELISTED = "DELISTED"
    RATE_LIMITED = "RATE_LIMITED"
    SOURCE_ERROR = "SOURCE_ERROR"


class DataSourceError(RuntimeError):
    """Base for every Layer 1 acquisition failure."""

    status = DataStatus.SOURCE_ERROR


class RateLimitedError(DataSourceError):
    """The source throttled or refused us. Says nothing about the company."""

    status = DataStatus.RATE_LIMITED


class DelistedError(DataSourceError):
    """The symbol is not (or no longer) traded."""

    status = DataStatus.DELISTED


class NoDataError(DataSourceError):
    """The source answered successfully with an empty result.

    Distinct from every other member of this hierarchy: nothing failed. A
    company can legitimately have no quarterly statements on the free tier.
    """

    status = DataStatus.NO_DATA


class SourceUnavailableError(DataSourceError):
    """Transport, timeout or parse failure. Whether data exists is unknown."""

    status = DataStatus.SOURCE_ERROR


# Vendors signal these in prose rather than in types, so classification is
# necessarily textual. Ordered most specific first.
_RATE_LIMIT_PATTERNS = (
    r"\b429\b",
    r"too\s+many\s+requests",
    r"rate\s*limit",
    r"\bthrottl",
    r"temporarily\s+blocked",
    r"\bquota\b",
)
_DELISTED_PATTERNS = (
    r"delisted",
    r"no\s+longer\s+(?:traded|listed)",
    r"symbol\s+may\s+be\s+delisted",
    r"\b404\b",
    r"not\s+found",
)
_NO_DATA_PATTERNS = (
    r"no\s+(?:price\s+)?data\s+found",
    r"empty\s+(?:data|response)",
    r"no\s+timezone\s+found",
)


def _matches(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def classify(exc: BaseException) -> DataSourceError:
    """Map a vendor exception onto this hierarchy.

    Inspects the HTTP status code where one is available and falls back to the
    message text, which is how yfinance reports delisting and empty results.
    Anything unrecognised becomes `SourceUnavailableError` -- SOURCE_ERROR is
    the honest "we do not know" bucket, never a silent OK.
    """
    if isinstance(exc, DataSourceError):
        return exc

    status_code = None
    response = getattr(exc, "response", None)
    if response is not None:
        status_code = getattr(response, "status_code", None)

    if status_code == 429:
        return RateLimitedError(f"rate limited by the data source: {exc}")
    if status_code == 404:
        return DelistedError(f"symbol not found at the data source: {exc}")

    text = f"{type(exc).__name__}: {exc}"
    if _matches(text, _RATE_LIMIT_PATTERNS):
        return RateLimitedError(f"rate limited by the data source: {exc}")
    if _matches(text, _DELISTED_PATTERNS):
        return DelistedError(f"symbol appears delisted: {exc}")
    if _matches(text, _NO_DATA_PATTERNS):
        return NoDataError(f"source returned no data: {exc}")
    return SourceUnavailableError(f"data source unavailable: {exc}")
