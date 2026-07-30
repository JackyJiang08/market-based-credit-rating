"""Switchable computation conventions for the credit measures.

Two presets exist. ``DOCUMENTED`` is the project's run of record and the
default everywhere; its behaviour is exactly the pre-convention code path.
``REFERENCE`` matches the team's reference implementation ("reference
convention"), which differs in three switches:

===============  =============================  ============================
Switch           DOCUMENTED (default)           REFERENCE
===============  =============================  ============================
mu denominator   eta - sigma^2/2 (Ito drift)    raw eta (no Ito adjustment)
negative drift   NOT_RATED (defective regime    abs(eta), flagged
                 suppresses mu/CCM)             MU_USES_ABS_DRIFT
drift window     DRIFT_WINDOW_DAYS (~5y)        250 trading days, same span
                                                as the volatility window
barrier field    D = 1.0*ST + 0.5*LT            Total Liabilities Net
                                                Minority Interest (field
                                                fallback + provenance)
===============  =============================  ============================

Consistent with the mode's philosophy, the applicability gates (financial
firms, market barrier) CLASSIFY under both conventions but suppress the
letter only under DOCUMENTED; REFERENCE annotates. The reporting-currency
gate suppresses under both -- mixed units are data corruption, not a
convention. Note the interaction: the financial-firm gate exists precisely
because ST+0.5*LT ignores deposits; under a total-liabilities barrier that
rationale changes, which is why REFERENCE annotates rather than suppresses.

The regime and weak-identification diagnostics run under both conventions;
under REFERENCE they annotate the output instead of suppressing it. Every
output row carries the convention name so no value travels unlabeled.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import config


@dataclass(frozen=True)
class Convention:
    name: str
    # "ito_drift" -> mu = ln(A/D) / (eta - sigma^2/2);  "raw_eta" -> ln(A/D) / eta
    mu_denominator: str
    # "not_rated" -> a non-positive denominator suppresses mu/CCM (defective
    # regime); "abs" -> divide by |denominator| and set mu_uses_abs_drift.
    negative_drift: str
    drift_window_days: int
    vol_window_days: int
    # "st_plus_half_lt" -> D = 1.0*ST + 0.5*LT ; "total_liabilities" -> the
    # Total Liabilities line (field fallback + provenance, never silent).
    barrier_field: str = "st_plus_half_lt"
    # "suppress" -> an applicability gate suppresses the letter (documented);
    # "annotate" -> the gate classifies and annotates, the letter is produced.
    applicability: str = "suppress"


DOCUMENTED = Convention(
    name="DOCUMENTED",
    mu_denominator="ito_drift",
    negative_drift="not_rated",
    drift_window_days=config.DRIFT_WINDOW_DAYS,
    vol_window_days=config.EM_WINDOW_DAYS,
)

REFERENCE = Convention(
    name="REFERENCE",
    mu_denominator="raw_eta",
    negative_drift="abs",
    drift_window_days=250,
    vol_window_days=250,
    barrier_field="total_liabilities",
    applicability="annotate",
)

_PRESETS = {c.name: c for c in (DOCUMENTED, REFERENCE)}


def get(convention: str | Convention | None) -> Convention:
    """Resolve a preset name (or pass a Convention through). Default DOCUMENTED."""
    if convention is None:
        return DOCUMENTED
    if isinstance(convention, Convention):
        return convention
    try:
        return _PRESETS[convention.upper()]
    except KeyError:
        raise ValueError(
            f"unknown convention {convention!r}; presets: {sorted(_PRESETS)}"
        ) from None
