"""PIT -> TTC -> S&P conversion tests.

Analytical no-arbitrage checks run everywhere. Grid/lookup checks need the
conversion workbook (proprietary, kept under local/) and are skipped when
it is absent, so a fresh clone still runs green.
"""

from __future__ import annotations

import math
import os

import pytest
from scipy.stats import norm

from creditrating.model import conversion

HAS_TABLES = os.path.exists(conversion.DEFAULT_XLSX)
needs_tables = pytest.mark.skipif(not HAS_TABLES,
                                  reason="conversion workbook (proprietary) not present")


# --- Analytical no-regulatory-arbitrage (Section 5.3) -----------------------
def test_alpha_first_hitting_matches_paper():
    assert conversion.alpha_first_hitting(1.5) == pytest.approx(0.91906, abs=1e-4)


def test_no_arb_ccm_star_matches_paper():
    assert conversion.no_arb_ccm_star(1.5) == pytest.approx(1.35373, abs=1e-4)


# --- Outlook direction (Prop. 5.3, Eq. 28) ----------------------------------
# Eq. (28) reads `Outlook = PD_FH - S&P TTC`, i.e. PIT - TTC. The prose above it
# in the paper reads in the opposite order and has already prompted one proposal
# to invert this. These tests exist to make that inversion fail loudly.
def test_outlook_is_pit_minus_ttc_not_the_reverse():
    assert conversion.outlook(0.30, 0.10) == pytest.approx(0.20)
    assert conversion.outlook(0.10, 0.30) == pytest.approx(-0.20)
    # Asymmetric inputs: an inverted implementation returns the negation, so a
    # symmetric pair would pass either way. This pair cannot.
    assert conversion.outlook(0.75, 0.25) == pytest.approx(0.50)


def test_outlook_sign_matches_the_papers_trend_reading():
    """`Outlook > 0` must mean PIT above TTC (elevated short-term risk)."""
    # Prop. 5.3: "If Outlook>0, then the future trend is positive" -- short-term
    # risk exceeds through-the-cycle, so reversion to TTC is an improvement.
    assert conversion.outlook(0.20, 0.05) > 0      # PIT > TTC -> positive trend
    assert conversion.outlook(0.05, 0.20) < 0      # PIT < TTC -> negative trend
    assert conversion.outlook(0.10, 0.10) == 0.0   # neutral


def test_outlook_reproduces_the_delivered_asset_sheet_value():
    """The delivered sheet shows -0.0002 at PIT=0, TTC=0.0002 (the 2bp floor).

    That value is correct per Eq. (28). It is negative only because the TTC grid
    floors at 2bp while PIT underflows to 0 -- a floor artifact, not a signal.
    See the `rating_basis` / floor-determined reporting for the interpretation.
    """
    assert conversion.outlook(0.0, 0.0002) == pytest.approx(-0.0002)


# --- Grid reproduces the paper's S&P TTC (Tables 13-14) ---------------------
@needs_tables
def test_ttc_grid_reproduces_paper_sp_ttc():
    t = conversion.load_tables()
    assert conversion.ttc_pd(t, 1.5, 1).value == pytest.approx(0.237, abs=2e-3)
    assert conversion.ttc_pd(t, 1.5, 5).value == pytest.approx(0.047, abs=2e-3)
    assert conversion.ttc_pd(t, 5.0, 1).value == pytest.approx(1.000, abs=2e-3)
    assert conversion.ttc_pd(t, 5.0, 5).value == pytest.approx(0.188, abs=2e-3)


@needs_tables
def test_sp_rating_thresholds():
    t = conversion.load_tables()
    assert conversion.sp_rating(t, 0.0) == "AAA"
    assert conversion.sp_rating(t, 0.05) == "B"          # in [0.0441, 0.0765)
    assert conversion.sp_rating(t, 1.0) == "D"           # beyond the worst band


@needs_tables
def test_off_grid_is_flagged():
    t = conversion.load_tables()
    assert conversion.ttc_pd(t, 0.05, 1.0).off_grid       # CCM below grid min 0.1
    assert conversion.ttc_pd(t, 1.0, 500.0).off_grid      # mu above grid max 160
    assert not conversion.ttc_pd(t, 1.5, 5.0).off_grid    # inside the grid


# --- Rating basis: a clamped value is never reported as a rating (#12) -------
@needs_tables
def test_off_grid_returns_no_value_and_the_off_grid_basis():
    t = conversion.load_tables()
    for ccm, mu in [(0.05, 1.0), (1.0, 500.0), (0.05, 500.0)]:
        look = conversion.ttc_pd(t, ccm, mu)
        assert look.basis is conversion.RatingBasis.OFF_GRID
        assert math.isnan(look.value), "off-grid must not return the clamped edge value"
        assert not look.at_floor


@needs_tables
def test_grid_interior_carries_the_interior_basis():
    t = conversion.load_tables()
    look = conversion.ttc_pd(t, 1.5, 5.0)
    assert look.basis is conversion.RatingBasis.GRID_INTERIOR
    assert math.isfinite(look.value)


@needs_tables
def test_defective_regime_is_not_applicable_not_off_grid():
    """NaN (CCM, mu) means the drift regime failed, which is a distinct state."""
    t = conversion.load_tables()
    look = conversion.ttc_pd(t, float("nan"), float("nan"))
    assert look.basis is conversion.RatingBasis.NOT_APPLICABLE
    assert math.isnan(look.value)
    assert not look.off_grid       # it is not off the grid; it never reached it


@needs_tables
def test_floor_determined_values_are_flagged():
    """A TTC PD on the grid's smallest expressible value is floor-determined."""
    t = conversion.load_tables()
    floor = conversion.ttc_floor(t)
    assert floor == pytest.approx(2e-4, abs=1e-6), "shipped grid floors at 2bp"
    # Exactly at the floor, and inside the saturation band just above it.
    assert conversion.is_floor_determined(t, floor)
    assert conversion.is_floor_determined(t, floor * 1.04)
    # Clearly resolved values are not floor-determined.
    assert not conversion.is_floor_determined(t, floor * 1.06)
    assert not conversion.is_floor_determined(t, 0.0014)   # DELL
    assert not conversion.is_floor_determined(t, 0.0109)   # ORCL
    assert not conversion.is_floor_determined(t, float("nan"))
    # A very safe interior point saturates; a risky one does not.
    assert conversion.ttc_pd(t, 0.5, 150.0).at_floor
    assert not conversion.ttc_pd(t, 5.0, 1.0).at_floor


def test_sp_rating_refuses_a_non_finite_pd():
    class _T:
        sp_thresholds = None
        sp_labels = None
    assert conversion.sp_rating(_T(), float("nan")) == "n/a"
    assert conversion.sp_rating(_T(), None) == "n/a"


# --- alpha_sp directly (Eq. 24 confidence-level half) -----------------------
def test_alpha_sp_uses_one_over_q_not_q():
    """The paper's stacked fraction reads as `0.625913 * ln CCM`; it is 1/Q.

    Only exercised indirectly through no_arb_ccm_star until now, so a Q vs 1/Q
    regression would have surfaced as a confusing CCM* drift rather than here.
    """
    ccm = 1.35373
    L = math.log(ccm + 1.0)
    expected = norm.cdf((1.35 - (1.0 / conversion.Q_SP) * math.log(ccm) + L / 2.0)
                        / math.sqrt(L))
    assert conversion.alpha_sp(ccm) == pytest.approx(expected, rel=1e-12)

    # The wrong reading (Q instead of 1/Q) gives a materially different number.
    wrong = norm.cdf((1.35 - conversion.Q_SP * math.log(ccm) + L / 2.0)
                     / math.sqrt(L))
    assert abs(conversion.alpha_sp(ccm) - wrong) > 1e-3


def test_alpha_sp_closes_the_loop_on_the_papers_anchor():
    """CL_SP(CCM*) must equal alpha_FH(1.5) at the paper's CCM* = 1.35373."""
    assert conversion.alpha_sp(1.35373) == pytest.approx(
        conversion.alpha_first_hitting(1.5), abs=1e-5)


def test_alpha_is_decreasing_in_ccm():
    """Eq. (22) part 3: alpha(CCM) is a decreasing function of CCM."""
    vals = [conversion.alpha_first_hitting(c) for c in (0.5, 1.0, 1.5, 5.0, 50.0)]
    assert all(a > b for a, b in zip(vals, vals[1:]))
    vals = [conversion.alpha_sp(c) for c in (0.5, 1.0, 1.5, 5.0, 50.0)]
    assert all(a > b for a, b in zip(vals, vals[1:]))


# ===========================================================================
# #11: the analytical no-arbitrage conversion, Eq. (24) rating half + Eq. (27)
# ===========================================================================

# --- Table 12: Moody's -> S&P (Prop. 5.2.2) ---------------------------------
# Columns: grade, Moody's CCM, published alpha, published CCM*, published S&P
# RiskScore, and the log-normal PD the paper uses (Table 11, not the observed
# PD1 -- the paper states "we use the log-normal default probability in the
# conversion").
TABLE_12 = [
    ("Aaa",   0.57, 0.9998,  0.60,   2.81, 0.0000001),
    ("Aa",    0.72, 0.9975,  0.75,   3.78, 0.0000015),
    ("A",     1.01, 0.9782,  1.01,   5.72, 0.0000180),
    ("Baa",   1.79, 0.8581,  1.63,  11.33, 0.0000620),
    ("Ba",    2.75, 0.7154,  2.29,  21.73, 0.0018540),
    ("B",     4.25, 0.5736,  3.17,  45.43, 0.0227970),
    ("Caa-C", 8.08, 0.4075,  4.94, 120.81, 0.1541870),
]


@pytest.mark.parametrize("grade, ccm_md, alpha_pub, ccm_star_pub, rs_pub, pd_ln",
                         TABLE_12)
def test_table_12_alpha_and_ccm_star(grade, ccm_md, alpha_pub, ccm_star_pub,
                                     rs_pub, pd_ln):
    """Eq. (26): matching confidence levels reproduces the published CCM*."""
    assert conversion.alpha_moodys(ccm_md) == pytest.approx(alpha_pub, abs=1e-3)
    ccm_star = conversion.no_arb_ccm_star_from_agency(ccm_md, conversion.Q_MOODYS)
    assert ccm_star == pytest.approx(ccm_star_pub, abs=1e-2)


# Table 11's log-normal PDs are printed to two decimal places, which is not
# enough precision to reproduce the RiskScore column for the high grades: Aaa,
# Aa and A all print as 0.00%, and Baa's 0.01% is really 0.0062%. Only the
# grades whose printed PD carries enough significant figures are asserted; the
# tolerance for each is set by the rounding of its own printed PD.
TABLE_12_RS = [
    ("Baa", 1.79, 0.0001, 11.33, 1.0),      # 0.01% -> 1 s.f., loose
    ("Ba",  2.75, 0.0019, 21.73, 0.15),     # 0.19% -> 2 s.f.
    ("B",   4.25, 0.0228, 45.43, 0.02),     # 2.28% -> 3 s.f.
    ("Caa-C", 8.08, 0.1541, 120.81, 0.05),  # 15.41% -> 4 s.f.
]


@pytest.mark.parametrize("grade, ccm_md, pd_ln, rs_pub, tol", TABLE_12_RS)
def test_table_12_sp_risk_score(grade, ccm_md, pd_ln, rs_pub, tol):
    """Eq. (27): substituting the source PD and CCM* gives the S&P RiskScore."""
    ccm_star = conversion.no_arb_ccm_star_from_agency(ccm_md, conversion.Q_MOODYS)
    assert conversion.risk_score_sp(pd_ln, ccm_star) == pytest.approx(rs_pub, abs=tol)


# --- Tables 13 and 14: first-passage -> S&P ---------------------------------
# (mu, published S&P RiskScore) at the table's CCM.
TABLE_13 = [(1, 139.00), (5, 53.35), (10, 30.99), (15, 21.08), (20, 15.41),
            (25, 11.75), (30, 9.23), (35, 7.41), (50, 4.18), (75, 1.93),
            (100, 1.01), (150, 0.34)]
TABLE_14 = [(1, 258.78), (5, 126.37), (10, 85.40), (15, 65.12), (20, 52.41),
            (25, 43.55), (30, 36.97), (35, 31.87), (50, 21.75), (75, 13.02),
            (100, 8.51), (150, 4.21)]


def test_table_13_and_14_ccm_star_anchors():
    assert conversion.no_arb_ccm_star(1.5) == pytest.approx(1.35373, abs=1e-4)
    assert conversion.no_arb_ccm_star(5.0) == pytest.approx(2.22928, abs=1e-4)
    assert conversion.alpha_first_hitting(1.5) == pytest.approx(0.91906, abs=1e-5)
    assert conversion.alpha_first_hitting(5.0) == pytest.approx(0.72749, abs=1e-5)


@pytest.mark.parametrize("mu, rs_pub", TABLE_13)
def test_table_13_sp_risk_score_reproduces(mu, rs_pub):
    from creditrating.model import tic as measures

    pit = measures.pit_pd_first_hitting(mu, 1.5)
    got = conversion.no_arb_convert(pit, 1.5).risk_score
    assert got == pytest.approx(rs_pub, abs=0.01)


@pytest.mark.parametrize("mu, rs_pub", TABLE_14)
def test_table_14_sp_risk_score_reproduces(mu, rs_pub):
    from creditrating.model import tic as measures

    pit = measures.pit_pd_first_hitting(mu, 5.0)
    got = conversion.no_arb_convert(pit, 5.0).risk_score
    assert got == pytest.approx(rs_pub, abs=0.01)


# --- The Table 8 RiskScore -> TTC PD scale ----------------------------------
def test_ttc_scale_reproduces_the_published_grades():
    for rs, pd1 in zip(conversion.SP_TTC_RISK_SCORES, conversion.SP_TTC_PD1):
        assert conversion.ttc_pd_from_risk_score(rs) == pytest.approx(pd1, rel=1e-9)


def test_ttc_scale_is_monotone_and_bounded():
    prev = 0.0
    for rs in (1.0, 2.7, 5.0, 10.0, 25.0, 60.0, 154.8, 500.0):
        v = conversion.ttc_pd_from_risk_score(rs)
        assert v >= prev, "TTC PD must increase with RiskScore"
        assert 0.0 < v <= 1.0
        prev = v
    assert math.isnan(conversion.ttc_pd_from_risk_score(float("nan")))
    assert math.isnan(conversion.ttc_pd_from_risk_score(-1.0))


@pytest.mark.parametrize("rs, ttc_pub", [
    (53.35, 0.047), (30.99, 0.019), (21.08, 0.009), (15.41, 0.005),
    (11.75, 0.003), (9.23, 0.002),
])
def test_ttc_scale_tracks_the_published_column_outside_ccc(rs, ttc_pub):
    """Agreement is within 0.25pp from AAA through B.

    Inside the CCC/C band the published column uses a finer notching than the
    paper prints, and the gap widens to ~4pp; that limit is documented on
    ttc_pd_from_risk_score rather than papered over with a loose tolerance.
    """
    assert conversion.ttc_pd_from_risk_score(rs) == pytest.approx(ttc_pub, abs=2.5e-3)


# --- The grid as an oracle for the analytical route -------------------------
@needs_tables
@pytest.mark.parametrize("ccm, mu", [
    (1.5, 5.0), (1.5, 10.0), (1.5, 15.0), (2.0, 20.0), (3.0, 15.0), (1.0, 25.0),
])
def test_analytical_agrees_with_the_grid_where_the_scale_resolves(ccm, mu):
    """Both routes are defined here and must agree to within one notch.

    The grid interpolates a proprietary table; the analytical route evaluates a
    closed form and maps it through the seven-point Table 8 scale. Exact
    equality is not expected, but a disagreement wide enough to move the letter
    by more than one notch would mean one of them is wrong.
    """
    from creditrating.model import tic as measures

    t = conversion.load_tables()
    grid = conversion.ttc_pd(t, ccm, mu)
    assert grid.basis is conversion.RatingBasis.GRID_INTERIOR

    pit = measures.pit_pd_first_hitting(mu, ccm)
    analytical = conversion.no_arb_convert(pit, ccm)

    # Relative agreement loosens at very small PDs, where a 30% relative gap is
    # 3 basis points; the absolute term carries those. The letter is the
    # binding assertion.
    assert analytical.ttc_pd == pytest.approx(grid.value, rel=0.4, abs=5e-4)
    labels = list(t.sp_labels)
    i = labels.index(conversion.sp_rating(t, analytical.ttc_pd))
    j = labels.index(conversion.sp_rating(t, grid.value))
    assert abs(i - j) <= 1, "letters differ by more than one notch"


@needs_tables
@pytest.mark.parametrize("ccm, mu", [(5.0, 5.0), (5.0, 10.0)])
def test_known_divergence_inside_the_ccc_band(ccm, mu):
    """Documented limit, asserted so it cannot widen unnoticed.

    Table 8 has a single anchor (RiskScore 154.8) covering everything from CCC
    to D, so the analytical route cannot resolve notches inside the distress
    band. It reads ~2-5pp riskier than the grid there, which is up to two
    notches. Investment grade through BB is unaffected.
    """
    from creditrating.model import tic as measures

    t = conversion.load_tables()
    grid = conversion.ttc_pd(t, ccm, mu)
    pit = measures.pit_pd_first_hitting(mu, ccm)
    analytical = conversion.no_arb_convert(pit, ccm)

    assert analytical.risk_score > 60.0, "premise: this is the distress band"
    gap = analytical.ttc_pd - grid.value
    assert 0.0 < gap < 0.06, f"divergence outside the documented band: {gap:+.4f}"


@needs_tables
def test_off_grid_now_converts_analytically_instead_of_blanking():
    """The point of #11: a CCM below the grid floor still gets a rating."""
    from creditrating.model import tic as measures

    t = conversion.load_tables()
    ccm, mu = 0.05, 30.0                      # CCM below the grid's 0.1 floor
    pit = measures.pit_pd_first_hitting(mu, ccm)

    without = conversion.ttc_pd(t, ccm, mu)                 # no PIT PD supplied
    assert without.basis is conversion.RatingBasis.OFF_GRID
    assert math.isnan(without.value)

    with_pit = conversion.ttc_pd(t, ccm, mu, pit_pd=pit)
    assert with_pit.basis is conversion.RatingBasis.ANALYTICAL
    assert math.isfinite(with_pit.value)
    assert 0.0 < with_pit.value <= 1.0


def test_analytical_route_refuses_undefined_inputs():
    for pit, ccm in [(float("nan"), 1.5), (0.1, float("nan")), (0.1, 0.0),
                     (0.1, -1.0)]:
        out = conversion.no_arb_convert(pit, ccm)
        assert math.isnan(out.risk_score) and math.isnan(out.ttc_pd)


# --- Rating determination vocabulary ----------------------------------------
def test_scale_resolved_is_the_name_not_model_determined():
    """Renamed 2026-07-26: the label measures the scale, not the estimate.

    DELL has the strongest drift t-statistic in the universe and the widest
    bootstrap letter interval (10 notches). `MODEL_DETERMINED` implied a
    precision claim the classification never made.
    """
    assert conversion.RatingDetermination.SCALE_RESOLVED.value == "SCALE_RESOLVED"
    assert not hasattr(conversion.RatingDetermination, "MODEL_DETERMINED")
    assert {d.value for d in conversion.RatingDetermination} == {
        "SCALE_RESOLVED", "PINNED_AT_FLOOR", "PINNED_AT_SCALE_TOP", "NOT_RATED"}


def test_determination_classification_uses_the_new_name():
    D = conversion.RatingDetermination
    B = conversion.RatingBasis
    assert conversion.classify_determination(B.GRID_INTERIOR, False) is D.SCALE_RESOLVED
    assert conversion.classify_determination(B.GRID_INTERIOR, True) is D.PINNED_AT_FLOOR
    assert conversion.classify_determination(B.ANALYTICAL, False, 50.0) is D.SCALE_RESOLVED
    assert conversion.classify_determination(B.ANALYTICAL, False, 0.5) is D.PINNED_AT_SCALE_TOP
    assert conversion.classify_determination(B.OFF_GRID, False) is D.NOT_RATED
    assert conversion.classify_determination(B.NOT_APPLICABLE, False) is D.NOT_RATED
    assert conversion.classify_determination(None, None) is D.NOT_RATED
