"""Regression lock on the REFERENCE computation convention.

Expected values are INLINED constants sourced by description only: the team
reference implementation, 2026-07-27 vintage. No file from that
implementation enters this repository.

Coverage note (recorded, not hidden):

- Only four of the eight deliverable names (ORCL, INTU, COST, AMZN) had
  reference inputs available when this lock was written; DELL, KHC, KO and
  PNC are absent because their reference (sigma, eta) were not provided --
  they must be added, never guessed.
- The reference implementation's A and D were not provided for any name, so
  ln(A/D) is derived here by inverting the reference's own mu:
  ``ln(A/D) = mu_ref * |eta_ref|``. For INTU the reference sigma was also
  missing and is derived from RiskScore_ref. Derived inputs still
  discriminate between formula candidates: under the documented convention
  (Ito drift in the denominator) the same inputs move mu by 20-60%, far
  outside any tolerance here.
- The reference values are 4-decimal displays of higher-precision
  internals, and they are not mutually consistent at 4 decimals: for ORCL,
  no ln(A/D) reproduces both the displayed mu and the displayed RiskScore
  with the displayed sigma/eta (the implied intervals are disjoint). Exact
  4-decimal assertion on all quantities simultaneously is therefore
  arithmetically impossible from the given digits. mu is asserted to
  4 decimals; CCM and RiskScore are asserted to 2e-3 relative -- an order
  of magnitude tighter than the nearest wrong formula and as tight as
  4-decimal-rounded inputs support.
"""

from __future__ import annotations

import math

import pytest
from creditrating.model import convention as conventions
from creditrating.model import tic

# One row per company: reference inputs and expected outputs
# (team reference implementation, 2026-07-27 vintage; displays at 4 dp).
# ln_ad is derived as mu_ref * |eta_ref| (see module docstring).
REFERENCE_ROWS = {
    "ORCL": {
        "sigma": 0.4315,
        "eta": -0.3387,
        "mu": 2.7583,
        "ccm": 0.5883,
        "risk_score": 21.3296,
        "abs_path": True,
    },
    "INTU": {
        # sigma missing from the provided reference values; derived from
        # RiskScore_ref: sigma = sqrt(RS/100) * ln(A/D).
        "sigma": math.sqrt(8.6867 / 100.0) * (1.5477 * 1.1008),
        "eta": -1.1008,
        "mu": 1.5477,
        "ccm": None,
        "risk_score": 8.6867,
        "abs_path": True,
    },
    "COST": {
        "sigma": 0.1882,
        "eta": 0.1623,
        "mu": 13.4993,
        "ccm": None,
        "risk_score": 0.7372,
        "abs_path": False,
    },
    "AMZN": {
        "sigma": 0.2653,
        "eta": 0.1078,
        "mu": 16.9632,
        "ccm": 0.3569,
        "risk_score": 2.1038,
        "abs_path": False,
    },
}

# Names in the eight-name deliverable set whose reference inputs were NOT
# provided. Listed so the gap is a recorded fact, not an omission.
MISSING_REFERENCE_INPUTS = ("DELL", "KHC", "KO", "PNC")

REL_TOL = 2e-3  # what 4-dp-rounded inputs support; wrong formulas miss by >20%


def _measures(row, convention):
    ln_ad = row["mu"] * abs(row["eta"])
    debt = 1.0
    asset = math.exp(ln_ad) * debt
    return tic.compute(row["sigma"], asset, debt, row["eta"], convention=convention)


@pytest.mark.parametrize("name", sorted(REFERENCE_ROWS))
def test_reference_convention_reproduces_the_reference_values(name):
    row = REFERENCE_ROWS[name]
    m = _measures(row, conventions.REFERENCE)
    assert m.convention == "REFERENCE"
    # mu: the convention-bearing quantity, to 4 decimals.
    assert m.mu == pytest.approx(row["mu"], abs=5e-5), f"{name} mu"
    # CCM / RiskScore: as tight as the rounded inputs support.
    if row["ccm"] is not None:
        assert m.ccm == pytest.approx(row["ccm"], rel=REL_TOL), f"{name} ccm"
    assert m.risk_score == pytest.approx(row["risk_score"], rel=REL_TOL), f"{name} rs"


@pytest.mark.parametrize("name", sorted(REFERENCE_ROWS))
def test_abs_drift_is_flagged_never_silent(name):
    row = REFERENCE_ROWS[name]
    m = _measures(row, conventions.REFERENCE)
    assert m.mu_uses_abs_drift is row["abs_path"], name
    # The regime diagnostic keeps running under REFERENCE: it annotates.
    if row["abs_path"]:
        assert m.regime is tic.DriftRegime.DEFECTIVE
        assert math.isfinite(m.mu)  # annotated, not suppressed


@pytest.mark.parametrize("name", ["ORCL", "INTU"])
def test_documented_convention_still_suppresses_the_negative_drift_names(name):
    """The same inputs under DOCUMENTED: defective regime, mu/CCM NaN.

    This is the discriminating counterpart to the reproduction test -- it
    proves the switch changes behaviour rather than both paths agreeing.
    """
    row = REFERENCE_ROWS[name]
    m = _measures(row, conventions.DOCUMENTED)
    assert m.convention == "DOCUMENTED"
    assert m.regime is tic.DriftRegime.DEFECTIVE
    assert m.mu != m.mu and m.ccm != m.ccm  # NaN
    assert m.mu_uses_abs_drift is False


@pytest.mark.parametrize("name", ["COST", "AMZN"])
def test_the_two_conventions_disagree_where_the_ito_term_matters(name):
    """Positive-drift names: REFERENCE mu differs from DOCUMENTED mu by the
    Ito term, so the lock cannot be satisfied by the documented formula."""
    row = REFERENCE_ROWS[name]
    ref = _measures(row, conventions.REFERENCE)
    doc = _measures(row, conventions.DOCUMENTED)
    assert ref.mu < doc.mu  # raw eta > eta - sigma^2/2 > 0 here
    assert abs(doc.mu - row["mu"]) / row["mu"] > 0.05, "documented mu must NOT match"
    # RiskScore is drift-free and identical under both conventions.
    assert ref.risk_score == pytest.approx(doc.risk_score, rel=1e-12)


def test_the_missing_names_are_a_recorded_fact():
    assert set(MISSING_REFERENCE_INPUTS) == {"DELL", "KHC", "KO", "PNC"}
    assert not set(MISSING_REFERENCE_INPUTS) & set(REFERENCE_ROWS)


def test_convention_presets():
    doc = conventions.get("documented")
    ref = conventions.get("REFERENCE")
    assert doc is conventions.DOCUMENTED and ref is conventions.REFERENCE
    assert doc.drift_window_days > ref.drift_window_days == ref.vol_window_days == 250
    with pytest.raises(ValueError):
        conventions.get("MYSTERY")
    assert conventions.get(None) is conventions.DOCUMENTED
