"""Render docs/figures/*.svg from the CSVs under docs/figures/data/.

Pure presentation: every number is read from the committed data files, which
`make_figure_data.py` regenerates (live run) and `convention_sweep_letters.csv`
records from the 2026-07-26 sweep. No proprietary content -- letter scales and
our own computed outputs only.

Style follows a validated palette (accent #2a78d6 / #eb6834, ΔE-checked): thin
marks, 2px lines, >=8px markers, hairline #e1e0d9 grid, ink #0b0b0b/#52514e,
surface #fcfcfb, one hue per job (sequential blues for magnitude, emphasis
accent + gray for the sweep).

Usage:  python docs/figures/make_figures.py     (requires matplotlib)
"""

from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np               # noqa: E402
import pandas as pd              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASE = "#c3c2b7"
ACCENT = "#2a78d6"
RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
        "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281",
        "#0d366b"]

# Letter scale used by the conversion grid, best first.
NOTCHES = ["AAA", "AAA-", "AA+", "AA", "AA-", "A+", "A", "A-",
           "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-", "B+"]
IDX = {s: i for i, s in enumerate(NOTCHES)}

plt.rcParams.update({
    "svg.fonttype": "none",
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "sans-serif"],
    "font.size": 10,
    "text.color": INK,
    "axes.edgecolor": BASE,
    "axes.labelcolor": INK2,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
})


def _ax(fig_w, fig_h):
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(length=0)
    return fig, ax


def _save(fig, name):
    path = os.path.join(HERE, name)
    fig.savefig(path, format="svg", facecolor=SURFACE, bbox_inches="tight",
                metadata={"Date": None})   # deterministic output, no timestamp
    plt.close(fig)
    print("wrote", path)


def amplification() -> None:
    df = pd.read_csv(os.path.join(DATA, "amplification.csv"))
    labels = {"sigma_A": "σ_A  (the input)", "risk_score": "RiskScore  (Eq. 12, drift-free)",
              "dd": "DD  (Eq. 14)", "ttc_pd": "TTC PD", "pit_pd": "PIT PD  (Eq. 13)"}
    order = ["sigma_A", "risk_score", "dd", "ttc_pd", "pit_pd"]
    w = df.set_index("quantity")["median_relative_width"]
    y = np.arange(len(order))[::-1]

    fig, ax = _ax(8.4, 3.1)
    ax.set_xscale("log")
    ax.set_xlim(0.12, 8e3)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for yi, q in zip(y, order):
        ax.plot([0.1, w[q]], [yi, yi], color=GRID, linewidth=1, zorder=1)
        ax.plot(w[q], yi, "o", markersize=9, color=ACCENT,
                markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
        val = f"{w[q]:,.3f}" if w[q] < 10 else f"~{w[q]:,.0f}"
        ax.annotate(val, (w[q], yi), xytext=(9, -3.5),
                    textcoords="offset points", color=INK2, fontsize=9)
    ax.set_yticks(y)
    ax.set_yticklabels([labels[q] for q in order], color=INK)
    ax.set_xlabel("median relative 5–95% bootstrap interval width  (log scale)")
    amp = w["pit_pd"] / w["risk_score"]
    ax.annotate(f"×{amp:,.0f} amplification,\nintroduced entirely by the\n"
                "PD-based conversion layer",
                xy=(w["pit_pd"], y[-1]), xytext=(0.62, 0.30),
                textcoords="axes fraction", color=INK, fontsize=9.5,
                ha="left", va="top")
    ax.set_title("What the conversion layer does to uncertainty",
                 loc="left", color=INK, fontsize=12, pad=12)
    _save(fig, "amplification_ladder.svg")


def rank_heatmap() -> None:
    df = pd.read_csv(os.path.join(DATA, "rank_distribution.csv"))
    stab = pd.read_csv(os.path.join(DATA, "rank_stability.csv")).iloc[0]
    companies = (df.drop_duplicates("symbol").sort_values("point_rank")
                 ["symbol"].tolist())
    n = len(companies)
    mat = np.zeros((n, n))
    for _, r in df.iterrows():
        mat[companies.index(r["symbol"]), int(r["rank"]) - 1] = r["fraction"]

    fig, ax = _ax(7.4, 4.6)
    for i in range(n):
        for j in range(n):
            f = mat[i, j]
            color = SURFACE if f == 0 else RAMP[min(len(RAMP) - 1,
                                                    int(round(f * (len(RAMP) - 1))))]
            ax.add_patch(plt.Rectangle((j + 0.06, n - 1 - i + 0.06), 0.88, 0.88,
                                       facecolor=color, edgecolor="none"))
            if f >= 0.10:
                ax.text(j + 0.5, n - 1 - i + 0.5, f"{f*100:.0f}",
                        ha="center", va="center", fontsize=8,
                        color="#ffffff" if f > 0.55 else INK)
    ax.set_xlim(0, n)
    ax.set_ylim(0, n)
    ax.set_xticks(np.arange(n) + 0.5)
    ax.set_xticklabels([str(k + 1) for k in range(n)])
    ax.set_yticks(np.arange(n) + 0.5)
    ax.set_yticklabels(companies[::-1], color=INK)
    ax.set_xlabel("RiskScore rank across bootstrap replicates (1 = safest)")
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(f"Rank ordering is stable at the extremes  "
                 f"(Kendall’s τ median {stab['tau_median']:.3f}, "
                 f"{stab['share_tau_ge_0.8']*100:.1f}% of replicates ≥ 0.8)",
                 loc="left", color=INK, fontsize=12, pad=12)
    ax.text(0, -1.35, "cell = share of replicates (%, labelled when ≥ 10) · "
            "rows ordered by point rank · darker = more of the distribution",
            color=MUTED, fontsize=8.5)
    _save(fig, "rank_stability_heatmap.svg")


def convention_sweep() -> None:
    df = pd.read_csv(os.path.join(DATA, "convention_sweep_letters.csv"))
    weights = [0.0, 0.25, 0.5, 0.75, 1.0]
    cols = ["w0", "w25", "w50", "w75", "w100"]

    fig, ax = _ax(8.4, 4.8)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)

    flat_aaa, drawn = [], []
    for _, r in df.iterrows():
        letters = [r[c] if isinstance(r[c], str) else None for c in cols]
        if all(x is None for x in letters):
            continue                              # INTU, KHC: unrated everywhere
        if all(x == "AAA" for x in letters if x is not None) \
                and letters.count("AAA") == 5:
            flat_aaa.append(r["symbol"])
            continue
        xs = [w for w, s in zip(weights, letters) if s]
        ys = [IDX[s] for s in letters if s]
        drawn.append((r["symbol"], xs, ys))

    # One gray line for the three identical pinned names.
    ax.plot(weights, [IDX["AAA"]] * 5, color=BASE, linewidth=2,
            solid_capstyle="round", zorder=2)
    ax.annotate(" · ".join(flat_aaa) + "  (pinned)", (1.0, IDX["AAA"]),
                xytext=(8, 0), textcoords="offset points",
                color=INK2, fontsize=9, va="center")
    for sym, xs, ys in drawn:
        emph = sym == "T"
        ax.plot(xs, ys, color=ACCENT if emph else BASE, linewidth=2,
                solid_capstyle="round", zorder=4 if emph else 2,
                marker="o", markersize=8 if emph else 0,
                markeredgecolor=SURFACE, markeredgewidth=2)
        ax.annotate(sym, (xs[-1], ys[-1]), xytext=(8, 0),
                    textcoords="offset points", va="center", fontsize=9,
                    color=INK if emph else INK2,
                    fontweight="bold" if emph else "normal")
    ax.annotate("7 notches on the\ndebt weight alone", xy=(0.42, IDX["AA"]),
                color=ACCENT, fontsize=9.5, ha="left")

    ax.set_xlim(-0.03, 1.22)
    ax.set_xticks(weights)
    ax.set_xticklabels(["0", "0.25", "0.5\n(shipped)", "0.75", "1.0"])
    ax.set_ylim(IDX["B+"] + 0.5, -0.5)
    ax.set_yticks(range(len(NOTCHES)))
    ax.set_yticklabels(NOTCHES, color=INK, fontsize=8.5)
    ax.set_xlabel("weight w on long-term debt in the barrier  D = ST + w·LT")
    ax.set_title("The letter moves with an unargued convention",
                 loc="left", color=INK, fontsize=12, pad=12)
    ax.annotate("recorded 2026-07-26 sweep · INTU and KHC are unrated under "
                "every weight (defective drift) · PNC and AMZN have D = 0 at "
                "w = 0", xy=(0, -0.21), xycoords="axes fraction", va="top",
                color=MUTED, fontsize=8.5)
    _save(fig, "convention_sweep.svg")


def interval_strip() -> None:
    df = pd.read_csv(os.path.join(DATA, "rating_intervals.csv"))
    df = df.sort_values("TiC Risk Score").reset_index(drop=True)

    fig, ax = _ax(8.4, 4.6)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    n = len(df)
    for i, r in df.iterrows():
        y = n - 1 - i
        lo, hi = IDX[r["Rating Interval Low"]], IDX[r["Rating Interval High"]]
        rated = isinstance(r["SP Rating"], str)
        ax.plot([lo, hi], [y, y], linewidth=7,
                color="#9ec5f4" if rated else GRID,
                solid_capstyle="round", zorder=2)
        if rated:
            ax.plot(IDX[r["SP Rating"]], y, "o", markersize=9, color=ACCENT,
                    markeredgecolor=SURFACE, markeredgewidth=2, zorder=4)
            ax.annotate(r["SP Rating"], (IDX[r["SP Rating"]], y), xytext=(0, 8),
                        textcoords="offset points", ha="center",
                        color=INK, fontsize=9)
        else:
            why = ("gated: bank" if r["Rating Determination"]
                   == "MODEL_NOT_APPLICABLE" else "defective drift")
            ax.annotate(f"no letter ({why})", (hi, y), xytext=(10, 0),
                        textcoords="offset points", va="center",
                        color=MUTED, fontsize=8.5)
    ax.set_ylim(-0.7, n - 0.3)
    ax.set_yticks(range(n))
    ax.set_yticklabels(df["Symbol"][::-1], color=INK)
    ax.set_xlim(-0.5, len(NOTCHES) - 0.5)
    ax.set_xticks(range(len(NOTCHES)))
    ax.set_xticklabels(NOTCHES, fontsize=8.5)
    ax.set_xlabel("S&P-equivalent letter  ·  bar = 5–95% bootstrap interval, "
                  "dot = point letter")
    ax.set_title("A letter is never published without its interval",
                 loc="left", color=INK, fontsize=12, pad=12)
    ax.text(-0.5, -2.0, "companies ordered by RiskScore (safest first) · "
            "2,000 moving-block replicates · intervals cover parameter "
            "uncertainty only (a lower bound)",
            color=MUTED, fontsize=8.5)
    _save(fig, "rating_intervals.svg")


if __name__ == "__main__":
    amplification()
    rank_heatmap()
    convention_sweep()
    interval_strip()
