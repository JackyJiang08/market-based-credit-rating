"""Validation study: the model against actual agency ratings (n = 150 universe).

Inputs (all committed):
    docs/analysis/agency_ratings.csv              sourced agency ratings
    docs/reconciliation/universe/taxonomy.csv     per-name pipeline outcomes
    docs/reconciliation/history/15_universe_150.csv  the run of record

Discrimination first (rank ordering vs the agency ordering), stratified three
ways -- all names with estimates / rated only / SCALE_RESOLVED only -- because
a correlation carried by pinned names is not a model result. Calibration
second, framed as a property of the letter conversion. Baselines third:
leverage D/A alone and DD alone against the same agency ordering.

Writes docs/analysis/data/*.csv, renders docs/analysis/*.svg, prints the
report. Charts follow the same validated palette and mark specs as
docs/figures/make_figures.py.

Usage:  python docs/analysis/validation_study.py
"""

from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np               # noqa: E402
import pandas as pd              # noqa: E402
from scipy import stats          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(HERE, "data")

SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, BASE, ACCENT, ORANGE = "#e1e0d9", "#c3c2b7", "#2a78d6", "#eb6834"

plt.rcParams.update({
    "svg.fonttype": "none", "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "sans-serif"],
    "font.size": 10, "text.color": INK, "axes.edgecolor": BASE,
    "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
})

# The model's letter scale (includes the grid's AAA-); agency letters map onto
# the same index scale, AAA- simply unused by agencies.
NOTCHES = ["AAA", "AAA-", "AA+", "AA", "AA-", "A+", "A", "A-",
           "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-", "B+", "B", "B-",
           "CCC+", "CCC", "CCC-"]
IDX = {s: i for i, s in enumerate(NOTCHES)}
BANDS = [("AAA/AA", {"AAA", "AAA-", "AA+", "AA", "AA-"}),
         ("A", {"A+", "A", "A-"}), ("BBB", {"BBB+", "BBB", "BBB-"}),
         ("BB", {"BB+", "BB", "BB-"}), ("B", {"B+", "B", "B-"}),
         ("CCC", {"CCC+", "CCC", "CCC-"})]


def band(letter: str) -> str:
    for name, members in BANDS:
        if letter in members:
            return name
    return "?"


def _ax(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(length=0)
    return fig, ax


def _save(fig, name):
    path = os.path.join(HERE, name)
    fig.savefig(path, format="svg", facecolor=SURFACE, bbox_inches="tight",
                metadata={"Date": None})
    plt.close(fig)
    print("wrote", path)


def boot_ci(x, y, fn, n=5000, seed=20260726):
    rng = np.random.default_rng(seed)
    x, y = np.asarray(x, float), np.asarray(y, float)
    outs = []
    for _ in range(n):
        i = rng.integers(0, len(x), len(x))
        if len(set(y[i])) < 2 or len(set(x[i])) < 2:
            continue
        outs.append(fn(x[i], y[i]))
    return float(np.quantile(outs, 0.05)), float(np.quantile(outs, 0.95))


def somers_d(agency, score):
    """Somers' D of the score against the ordinal agency truth (AR analogue)."""
    try:
        return float(stats.somersd(agency, score).statistic)
    except AttributeError:                     # very old scipy
        a, s = np.asarray(agency), np.asarray(score)
        conc = disc = 0
        for i in range(len(a)):
            for j in range(i + 1, len(a)):
                if a[i] == a[j]:
                    continue
                pair = (a[i] - a[j]) * (s[i] - s[j])
                conc += pair > 0
                disc += pair < 0
        return (conc - disc) / max(1, conc + disc)


def correlations(df, score_col, label):
    x, y = df[score_col].to_numpy(float), df["agency_idx"].to_numpy(float)
    rho = float(stats.spearmanr(x, y).correlation)
    lo, hi = boot_ci(x, y, lambda a, b: stats.spearmanr(a, b).correlation)
    tau = float(stats.kendalltau(x, y).correlation)
    d = somers_d(y, x)
    return {"stratum": label, "n": len(df), "spearman": rho,
            "spearman_ci05": lo, "spearman_ci95": hi, "kendall": tau,
            "somers_d": d}


def main() -> None:
    os.makedirs(DATA, exist_ok=True)
    agency = pd.read_csv(os.path.join(HERE, "agency_ratings.csv"))
    tax = pd.read_csv(os.path.join(
        ROOT, "docs", "reconciliation", "universe", "taxonomy.csv"))
    hist = pd.read_csv(os.path.join(
        ROOT, "docs", "reconciliation", "history", "15_universe_150.csv"))

    df = (tax.merge(agency[["symbol", "sp", "verified"]], on="symbol")
             .merge(hist[["Symbol", "TiC Risk Score", "DD",
                          "Debt/Short Term", "Debt/Long Term", "A"]],
                    left_on="symbol", right_on="Symbol", how="left"))
    df["agency_idx"] = df["sp"].map(IDX)
    df = df[df["agency_idx"].notna()].copy()
    df["risk_score"] = df["TiC Risk Score"]
    df["neg_dd"] = -df["DD"]
    df["leverage"] = ((df["Debt/Short Term"].fillna(0)
                       + 0.5 * df["Debt/Long Term"].fillna(0)) / df["A"])

    # --- discrimination, three strata --------------------------------------
    est = df[df["risk_score"].notna()].copy()
    rated = est[est["model_letter"].notna()].copy()
    resolved = est[est["determination"] == "SCALE_RESOLVED"].copy()
    strata = [("all names with estimates", est), ("rated only", rated),
              ("SCALE_RESOLVED only", resolved)]
    disc = pd.DataFrame([correlations(s, "risk_score", lab)
                         for lab, s in strata])
    disc.to_csv(os.path.join(DATA, "discrimination.csv"), index=False)
    print("\n=== DISCRIMINATION: RiskScore vs agency ordering ===")
    print(disc.to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    # --- baselines ---------------------------------------------------------
    rows = []
    for lab, s in strata:
        for pred, col in (("TiC RiskScore", "risk_score"),
                          ("DD alone (neg)", "neg_dd"),
                          ("leverage D/A alone", "leverage")):
            ss = s[s[col].notna()]
            rho = float(stats.spearmanr(ss[col], ss["agency_idx"]).correlation)
            rows.append({"stratum": lab, "predictor": pred, "n": len(ss),
                         "spearman": rho})
    base = pd.DataFrame(rows)
    base.to_csv(os.path.join(DATA, "baselines.csv"), index=False)
    print("\n=== BASELINES (Spearman vs agency) ===")
    print(base.pivot(index="predictor", columns="stratum",
                     values="spearman").to_string(
        float_format=lambda v: f"{v:.3f}"))

    # --- sector-stratified -------------------------------------------------
    rows = []
    for sec, g in est.groupby("sector"):
        if len(g) >= 8 and g["agency_idx"].nunique() >= 3:
            rho = float(stats.spearmanr(g["risk_score"],
                                        g["agency_idx"]).correlation)
            rows.append({"sector": sec, "n": len(g), "spearman": rho})
    sec = pd.DataFrame(rows).sort_values("spearman", ascending=False)
    sec.to_csv(os.path.join(DATA, "sector_correlations.csv"), index=False)
    print("\n=== WITHIN-SECTOR Spearman (n >= 8) ===")
    print(sec.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"mean within-sector: {sec['spearman'].mean():.3f}")

    # --- calibration -------------------------------------------------------
    cal = rated.copy()
    cal["model_idx"] = cal["model_letter"].map(IDX)
    cal["notch_error"] = cal["agency_idx"] - cal["model_idx"]  # + = optimistic
    cal[["symbol", "model_letter", "sp", "notch_error", "determination",
         "verified"]].to_csv(os.path.join(DATA, "notch_errors.csv"),
                             index=False)
    e = cal["notch_error"]
    print("\n=== CALIBRATION (rated ∩ agency, n=%d) ===" % len(cal))
    print(f"median error {e.median():+.0f} notches (+ = model optimistic), "
          f"IQR [{e.quantile(.25):.0f}, {e.quantile(.75):.0f}], "
          f"|e|<=1: {(e.abs() <= 1).mean() * 100:.0f}%, "
          f"|e|<=2: {(e.abs() <= 2).mean() * 100:.0f}%")
    cm = pd.crosstab(cal["model_letter"].map(band), cal["sp"].map(band))
    order = [b for b, _ in BANDS]
    cm = cm.reindex(index=order, columns=order).fillna(0).astype(int)
    cm.to_csv(os.path.join(DATA, "confusion_broad_grades.csv"))
    print("\nconfusion (rows=model, cols=agency):")
    print(cm.to_string())

    # --- charts ------------------------------------------------------------
    # (1) the money chart: two letter histograms side by side, by band
    counts = pd.DataFrame({
        "model": cal["model_letter"].map(band).value_counts(),
        "agency": df["sp"].map(band).value_counts(),
    }).reindex(order).fillna(0)
    fig, ax = _ax(8.4, 3.6)
    xs = np.arange(len(order))
    w = 0.38
    ax.bar(xs - w / 2, counts["model"].to_numpy(), width=w, color=ACCENT,
           label="model letters (85 rated)", zorder=3)
    ax.bar(xs + w / 2, counts["agency"].to_numpy(), width=w, color=ORANGE,
           label="agency letters (137 sourced)", zorder=3)
    for i, (m, a) in enumerate(zip(counts["model"], counts["agency"])):
        if m:
            ax.annotate(f"{m:.0f}", (i - w / 2, m), xytext=(0, 4),
                        textcoords="offset points", ha="center",
                        color=INK2, fontsize=9)
        if a:
            ax.annotate(f"{a:.0f}", (i + w / 2, a), xytext=(0, 4),
                        textcoords="offset points", ha="center",
                        color=INK2, fontsize=9)
    ax.set_xticks(xs)
    ax.set_xticklabels(order)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper right")
    ax.set_title("The letter conversion saturates at the top of the scale",
                 loc="left", color=INK, fontsize=12, pad=12)
    ax.set_ylabel("companies")
    _save(fig, "letters_model_vs_agency.svg")

    # (2) rank scatter, emphasis on SCALE_RESOLVED
    fig, ax = _ax(6.4, 5.6)
    est2 = est.copy()
    est2["mrank"] = est2["risk_score"].rank()
    est2["arank"] = est2["agency_idx"].rank()
    pin = est2[est2["determination"] != "SCALE_RESOLVED"]
    res = est2[est2["determination"] == "SCALE_RESOLVED"]
    lim = max(est2["mrank"].max(), est2["arank"].max())
    ax.plot([0, lim], [0, lim], color=GRID, linewidth=1, zorder=1)
    ax.plot(pin["mrank"].to_numpy(), pin["arank"].to_numpy(), "o", markersize=6, color=BASE,
            markeredgecolor=SURFACE, markeredgewidth=1.5,
            label="pinned / gated / defective", zorder=2)
    ax.plot(res["mrank"].to_numpy(), res["arank"].to_numpy(), "o", markersize=8, color=ACCENT,
            markeredgecolor=SURFACE, markeredgewidth=2,
            label="SCALE_RESOLVED", zorder=3)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left")
    ax.set_xlabel("RiskScore rank (safe → risky)")
    ax.set_ylabel("agency rank (safe → risky)")
    rho_all = disc.loc[disc["stratum"] == "all names with estimates",
                       "spearman"].iloc[0]
    rho_res = disc.loc[disc["stratum"] == "SCALE_RESOLVED only",
                       "spearman"].iloc[0]
    ax.set_title(f"Discrimination: ρ = {rho_all:.2f} overall, "
                 f"{rho_res:.2f} where the scale resolved",
                 loc="left", color=INK, fontsize=12, pad=12)
    _save(fig, "rank_scatter.svg")

    # (3) notch-error distribution
    fig, ax = _ax(8.4, 3.2)
    lo_e, hi_e = int(e.min()), int(e.max())
    span = np.arange(lo_e, hi_e + 1)
    counts_e = e.value_counts().reindex(span).fillna(0)
    ax.bar(span, counts_e.to_numpy(), width=0.8, color=ACCENT, zorder=3)
    ax.axvline(0, color=INK2, linewidth=1)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xlabel("notch error (agency − model; positive = model optimistic)")
    ax.set_ylabel("companies")
    ax.set_title(f"Letter calibration: median {e.median():+.0f} notches "
                 f"optimistic, {(e.abs() <= 2).mean() * 100:.0f}% within 2",
                 loc="left", color=INK, fontsize=12, pad=12)
    _save(fig, "notch_errors.svg")

    # (4) baseline comparison
    fig, ax = _ax(8.4, 3.4)
    piv = base.pivot(index="predictor", columns="stratum", values="spearman")
    piv = piv.reindex(["TiC RiskScore", "DD alone (neg)",
                       "leverage D/A alone"])
    labs = ["all names with estimates", "SCALE_RESOLVED only"]
    xs = np.arange(len(piv))
    w = 0.38
    ax.bar(xs - w / 2, piv[labs[0]].to_numpy(), width=w, color=ACCENT,
           label=f"{labs[0]}", zorder=3)
    ax.bar(xs + w / 2, piv[labs[1]].to_numpy(), width=w, color=ORANGE,
           label=f"{labs[1]}", zorder=3)
    for i, p in enumerate(piv.index):
        for off, lab in ((-w / 2, labs[0]), (w / 2, labs[1])):
            v = piv.loc[p, lab]
            ax.annotate(f"{v:.2f}", (i + off, v), xytext=(0, 4),
                        textcoords="offset points", ha="center",
                        color=INK2, fontsize=9)
    ax.set_xticks(xs)
    ax.set_xticklabels(piv.index)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_ylabel("Spearman ρ vs agency ordering")
    ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1.0, 1.02))
    ax.set_title("Does the TiC RiskScore beat its own ingredients?",
                 loc="left", color=INK, fontsize=12, pad=12)
    _save(fig, "baseline_comparison.svg")


if __name__ == "__main__":
    main()
