"""Typed data-acquisition errors (#9).

The distinction that matters: a company that genuinely has no data must be
visibly different in the output from a fetch we failed to make. The first is a
fact about the company; the second is a fact about us.
"""

from __future__ import annotations

import pytest
import requests
from creditrating.data import errors


class _Resp:
    def __init__(self, status_code):
        self.status_code = status_code


def _http(status_code):
    exc = requests.exceptions.HTTPError(f"HTTP {status_code}")
    exc.response = _Resp(status_code)
    return exc


# --- classification ---------------------------------------------------------
def test_http_429_is_a_rate_limit():
    err = errors.classify(_http(429))
    assert isinstance(err, errors.RateLimitedError)
    assert err.status is errors.DataStatus.RATE_LIMITED


def test_http_404_is_delisted():
    err = errors.classify(_http(404))
    assert isinstance(err, errors.DelistedError)
    assert err.status is errors.DataStatus.DELISTED


@pytest.mark.parametrize(
    "message",
    [
        "Too Many Requests",
        "429 Client Error",
        "rate limit exceeded",
        "You are being throttled",
        "quota exceeded",
    ],
)
def test_rate_limit_recognised_from_the_message(message):
    assert isinstance(errors.classify(RuntimeError(message)), errors.RateLimitedError)


@pytest.mark.parametrize(
    "message",
    [
        "XYZ: possibly delisted; no timezone found",
        "symbol may be delisted",
        "ticker no longer traded",
    ],
)
def test_delisting_recognised_from_the_message(message):
    assert isinstance(errors.classify(RuntimeError(message)), errors.DelistedError)


@pytest.mark.parametrize(
    "message",
    [
        "no price data found for this range",
        "empty response",
    ],
)
def test_empty_result_recognised_from_the_message(message):
    assert isinstance(errors.classify(RuntimeError(message)), errors.NoDataError)


def test_unknown_failure_is_source_error_never_no_data():
    """SOURCE_ERROR is the honest 'we do not know' bucket."""
    err = errors.classify(ValueError("something entirely unexpected"))
    assert isinstance(err, errors.SourceUnavailableError)
    assert err.status is errors.DataStatus.SOURCE_ERROR
    assert not isinstance(err, errors.NoDataError)


def test_classify_is_idempotent_on_our_own_errors():
    original = errors.RateLimitedError("already typed")
    assert errors.classify(original) is original


# --- the distinction the issue was opened for -------------------------------
def test_no_data_is_a_distinct_status_from_every_failure():
    """A dataless company and a failed fetch must not share a status."""
    dataless = errors.NoDataError("source returned nothing").status
    failures = {
        errors.RateLimitedError("x").status,
        errors.DelistedError("x").status,
        errors.SourceUnavailableError("x").status,
    }
    assert dataless is errors.DataStatus.NO_DATA
    assert dataless not in failures
    assert len(failures) == 3, "each failure mode keeps its own status"


def test_every_status_is_distinct():
    values = [s.value for s in errors.DataStatus]
    assert len(values) == len(set(values))


# --- retry policy -----------------------------------------------------------
def test_only_throttling_and_transport_failures_are_retryable():
    from creditrating.data import providers as sources

    assert isinstance(errors.RateLimitedError("x"), sources.RETRYABLE)
    assert isinstance(errors.SourceUnavailableError("x"), sources.RETRYABLE)
    # Waiting cannot make these succeed.
    assert not isinstance(errors.DelistedError("x"), sources.RETRYABLE)
    assert not isinstance(errors.NoDataError("x"), sources.RETRYABLE)


def test_retry_decorator_does_not_retry_a_delisted_symbol(monkeypatch):
    from creditrating.data import provider_config as config
    from creditrating.data import providers as sources

    monkeypatch.setattr(config, "MAX_RETRIES", 4)
    monkeypatch.setattr(config, "BACKOFF_BASE_SECONDS", 0)
    calls = []

    @sources.with_retry("probe")
    def always_delisted():
        calls.append(1)
        raise RuntimeError("possibly delisted; no timezone found")

    with pytest.raises(errors.DelistedError):
        always_delisted()
    assert len(calls) == 1, "a delisted symbol must not be retried"


def test_retry_decorator_retries_a_rate_limit_then_raises_it_typed(monkeypatch):
    from creditrating.data import provider_config as config
    from creditrating.data import providers as sources

    monkeypatch.setattr(config, "MAX_RETRIES", 3)
    monkeypatch.setattr(config, "BACKOFF_BASE_SECONDS", 0)
    calls = []

    @sources.with_retry("probe")
    def always_throttled():
        calls.append(1)
        raise RuntimeError("Too Many Requests")

    with pytest.raises(errors.RateLimitedError):
        always_throttled()
    assert len(calls) == 3, "a rate limit is retried up to MAX_RETRIES"


def test_retry_decorator_returns_on_success(monkeypatch):
    from creditrating.data import provider_config as config
    from creditrating.data import providers as sources

    monkeypatch.setattr(config, "MAX_RETRIES", 3)
    monkeypatch.setattr(config, "BACKOFF_BASE_SECONDS", 0)

    @sources.with_retry("probe")
    def ok():
        return "value"

    assert ok() == "value"


# ===========================================================================
# Unit and shape assumptions (#18) and provenance (#17)
# ===========================================================================
def test_risk_free_rate_outside_the_plausible_band_raises():
    """A units change at the source must fail loudly, not scale everything."""
    import pandas as pd
    from creditrating.data.alignment import build_panel

    idx = pd.bdate_range("2024-01-02", periods=40)
    prices = pd.DataFrame({"Close": 100.0, "Dividends": 0.0}, index=idx)
    # A series arriving 100x too large is caught hard.
    too_large = pd.Series([500.0], index=[pd.Timestamp("2024-01-01")])
    with pytest.raises(ValueError, match="outside the plausible band"):
        build_panel(prices, 1000.0, pd.DataFrame(), too_large)

    # Percent input is accepted.
    percent = pd.Series([5.0], index=[pd.Timestamp("2024-01-01")])
    panel = build_panel(prices, 1000.0, pd.DataFrame(), percent)
    assert panel["RiskFree_R"].dropna().iloc[0] == pytest.approx(0.05)


def test_already_decimal_rate_warns_because_it_cannot_be_caught_by_a_band(caplog):
    """The opposite units error is only detectable as 'suspiciously low'.

    0.05 / 100 = 0.05% is a rate the 1-year Treasury has genuinely printed, so
    no band can separate it from a real near-zero rate. It warns instead, and
    this test pins that we do not pretend otherwise.
    """
    import logging

    import pandas as pd
    from creditrating.data.alignment import build_panel

    idx = pd.bdate_range("2024-01-02", periods=40)
    prices = pd.DataFrame({"Close": 100.0, "Dividends": 0.0}, index=idx)
    already_decimal = pd.Series([0.05], index=[pd.Timestamp("2024-01-01")])

    with caplog.at_level(logging.WARNING):
        panel = build_panel(prices, 1000.0, pd.DataFrame(), already_decimal)
    assert "may already be in decimals" in caplog.text or "switched to decimals" in caplog.text
    assert panel["RiskFree_R"].notna().any()


def test_missing_adj_close_is_nan_not_silently_the_close():
    import pandas as pd
    from creditrating.data.alignment import build_panel

    idx = pd.bdate_range("2024-01-02", periods=20)
    prices = pd.DataFrame({"Close": 100.0, "Dividends": 0.0}, index=idx)
    panel = build_panel(prices, 1000.0, pd.DataFrame(), None)
    assert (
        panel["AdjClose"].isna().all()
    ), "Adj Close and Close differ across a split; do not substitute"


def test_reference_shares_reports_which_method_it_used():
    from creditrating.data import cleaning as transforms

    shares, method = transforms.reference_shares(1_000_000.0, 50.0, 12_345.0)
    assert shares == pytest.approx(20_000.0)
    assert method == "market_cap_over_price"

    # The fallback is a single share class -- a different quantity for a
    # dual-class issuer, so it must be labelled distinctly.
    shares, method = transforms.reference_shares(None, 50.0, 12_345.0)
    assert shares == 12_345.0
    assert method == "shares_outstanding_single_class"

    shares, method = transforms.reference_shares(None, None, None)
    assert shares is None
    assert method == "unavailable"
