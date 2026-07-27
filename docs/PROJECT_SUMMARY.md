# Project summary — market-based credit ratings with honest uncertainty

**Orientation:** the two-page register write-up of the whole project — what
was built, what it found, and what it cannot claim. Everything here is
reproducible from the repository; the interactive version is the
[live terminal](https://jackyjiang08.github.io/market-based-credit-rating/).

## Abstract

We implement a market-based credit-rating pipeline — a KMV/Merton structural
model estimated by EM, feeding Time-Consistent (TiC) credit measures and an
S&P-equivalent letter conversion — and run it over 150 public companies. The
contribution is not the letter; it is the measurement of how much of each
output survives its own uncertainty. A moving-block bootstrap shows the
PD-based letter chain amplifies parameter noise **×4,073** relative to the
drift-free RiskScore, exactly as the framework's invariance result predicts,
while the risk *ordering* is stable (median Kendall's **τ = 0.956** across
2,000 replicates) and validates against sourced agency ratings
(Spearman **ρ = 0.79**; 0.73 restricted to scale-resolved names). The letter
conversion itself runs a median **+5 notches optimistic** — so the pipeline
leads with RiskScore and the rank ordering, and never publishes a letter
without its bootstrap interval. Every non-rating in the universe is
classified, every silent modelling substitution carries a flag, and the
licensed conversion grids never enter the public repository.

## Problem

Structural credit models promise a market-implied default probability, but a
published letter rating hides three uncertainties of comparable size: sampling
noise in the estimated drift, an unargued debt-weight convention inside the
default point, and the possibility that the barrier specification is wrong for
the firm entirely. The question this project answers quantitatively: **which
outputs of the chain are worth publishing, given what they inherit from their
inputs?**

## Data

Daily prices, shares, dividends and quarterly/annual balance sheets from Yahoo
Finance; the 1-year Treasury rate (FRED `DGS1`) matching the 1-year horizon.
Alignment is point-in-time as-of with a documented limitation: statements key
on period-end, not publication time, so panels are research prototypes rather
than backtest-safe datasets (`docs/TIMING_PROTOCOL.md`). Committed cache
fixtures make the demo and the full test suite run offline on a fresh clone.

## Method

Equity is a call on assets: EM inversion recovers asset value, volatility and
drift (Eq. 10); first-passage factors µ and CCM (Eq. 11) give the TiC measures
— `RiskScore = 100·σ_A²/ln²(A/D)` (Eq. 12, drift-free by Prop. 4.4.2), DD
(Eq. 14), an inverse-Gaussian PIT PD (Eq. 13) — and a no-arbitrage match
(Prop. 5.2) converts to a TTC PD and an S&P-equivalent letter. The
implementation reproduces the methodology's published anchors (PIT PD Tables
13–14, `alpha_FH(1.5) = 0.91906`, `CCM* = 1.35373`). Firms the model cannot
describe are gated, not mis-rated: deposit-funded banks, insurers, REITs,
foreign-currency filers, and firms whose market assets do not clear the most
conservative barrier (ADR 0003).

## Central results

**1. The letter layer amplifies uncertainty ×4,073; the RiskScore layer does
not.** Bootstrapping the EM-recovered asset returns (2,000 replicates), the
median relative 5–95 interval width is 0.48 for RiskScore — exactly 2× the
σ_A width, the differential of a square, and nothing more — versus ~1,955 for
the PIT PD that feeds the letter. The amplification is introduced entirely by
the PD-based conversion layer; the framework's Girsanov-invariance argument
predicts the direction, and this project measures the magnitude on real
companies. A convention sweep puts the unargued 0.5 long-term-debt weight on
the same notch scale: one company's letter moves seven notches on that choice
alone, so the bootstrap interval is a lower bound on honest letter
uncertainty.

**2. The ordering is publishable; the letter is not.** The RiskScore rank
ordering holds a median Kendall's τ = 0.956 across replicates, is invariant to
the debt-weight convention, and correlates ρ = 0.79 with sourced agency
ratings (0.73 restricted to the 36 scale-resolved names — the signal is not
carried by scale-pinned letters). The letter conversion runs a median +5
notches optimistic. Honest baseline: plain distance-to-default ties RiskScore
on discrimination (0.78 vs 0.79) — the TiC construction's advantage is
stability, not ranking power.

## Validation

A sourced agency-ratings study (stratified Spearman/Kendall with bootstrap
CIs, calibration, baselines, sector stratification; `docs/analysis/VALIDATION.md`),
plus reproduction of every published methodology anchor, golden-file
regression tests, and a 150-name universe run with **zero unexplained
failures** — every non-rating is classified as a gate, defective drift, or a
data failure, and the run surfaced two real model bugs that were fixed with
regression fixtures. Headline numbers have a single committed source of truth
(`docs/analysis/data/headline.json`) that CI recomputes from run-of-record
data and greps across every user-facing surface.

## Limitations

Market-implied PIT PDs are liquidity-sensitive and legitimately ~0 for large
liquid names — comparison belongs to DD and RiskScore. The drift is
noise-dominated at feasible estimation windows; that noise is quantified, not
removed. The letter's +5-notch optimism is published as a finding, not
refitted away. Statement alignment keys on period-end, not availability time.
Off-grid conversions are edge-clamped and flagged. The barrier specification
is gated rather than solved for financial firms.

## What I would do next

Publication-time (`available_at`) alignment with immutable point-in-time
snapshots, promoting the panels to backtest-safe; a calibrated (rather than
no-arbitrage-anchored) letter conversion with the optimism decomposed by
sector; sector-specific default points for the gated financial firms; and a
time-series extension — rolling the 150-name universe through history to test
whether the ordering's stability holds out of sample.

## Artifacts

| | |
|---|---|
| Live terminal | <https://jackyjiang08.github.io/market-based-credit-rating/> |
| Repository | <https://github.com/JackyJiang08/market-based-credit-rating> |
| Validation study | [`docs/analysis/VALIDATION.md`](analysis/VALIDATION.md) |
| Uncertainty method | [`docs/UNCERTAINTY.md`](UNCERTAINTY.md) |
| Universe & failure taxonomy | [`docs/UNIVERSE.md`](UNIVERSE.md) |
| Architecture | [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) |
