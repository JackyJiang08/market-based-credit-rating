# Reference-convention reconciliation

**Orientation:** the team's reference implementation computes the credit
measures under three conventions that differ from the documented run of
record. This document reproduces its results under the switchable
`REFERENCE` convention, attributes every residual to a named input, and
answers "which switch explains the gap" with an ablation. Regenerate with
[`run_reference_reconciliation.py`](run_reference_reconciliation.py); the
formula layer is locked by `tests/test_reference_convention.py`, so any
end-to-end residual here is an input difference by construction.

Data: live refresh pinned to the **2026-07-27 close** (`--as-of`), in a
separate cache so the committed fixtures (the site's run of record, prices
through 2026-07-24) stay untouched. Reference values are quoted from the team
reference implementation, 2026-07-27 vintage; "n.p." marks names whose
reference inputs were **not provided** — DELL, KHC, KO, PNC are reported
one-sided and must be completed when their reference inputs arrive, never
guessed.

## The three switches

| Switch | DOCUMENTED (run of record) | REFERENCE |
|---|---|---|
| µ denominator | η − σ²/2 (Ito drift) | raw η (no Ito adjustment) |
| negative drift | `NOT_RATED` (defective regime suppresses µ/CCM) | abs(η), flagged `MU_USES_ABS_DRIFT` |
| drift window | ~5y (vol 252d separate) | 250 trading days, one span for both |
| barrier field | D = 1.0·ST + 0.5·LT | Total Liabilities (matched row recorded; team-confirmed 2026-07-29) |

Gate interaction: the financial-firm gate exists because ST+0.5·LT ignores
deposits; under a total-liabilities barrier that rationale changes, so under
REFERENCE the applicability gates classify and **annotate** rather than
suppress (the reporting-currency gate still suppresses — mixed units are data
corruption, not a convention).

## Reconciliation at the 2026-07-27 close (extended REFERENCE, TL barrier)

Ours computed under the full `REFERENCE` preset — including the
team-confirmed total-liabilities barrier; the reference implementation's
values after the slash.

| Name | σ_A ours/ref | η ours/ref | µ ours/ref | CCM ours/ref | RiskScore ours/ref |
|---|---|---|---|---|---|
| AMZN | 0.2754 / 0.2653 | 0.0853 / 0.1078 | 21.41 / 16.96 | 0.4874 / 0.3569 | 2.277 / 2.104 |
| COST | 0.1789 / 0.1882 | 0.0481 / 0.1623 | 45.56 / 13.50 | 0.3041 / n.p. | 0.667 / 0.737 |
| DELL | 0.4107 / n.p. | 0.9085 / n.p. | 1.32 / n.p. | 0.1543 / n.p. | 11.653 / n.p. |
| INTU | 0.4252 / n.p.¹ | −0.7519 / −1.1008 | 2.24 / 1.55 | 0.1425 / n.p. | 6.350 / 8.687 |
| KHC | 0.1137 / n.p. | −0.0131 / n.p. | 42.28 / n.p. | 1.7923 / n.p. | 4.240 / n.p. |
| KO | 0.1478 / n.p. | 0.1798 / n.p. | 10.19 / n.p. | 0.0663 / n.p. | 0.651 / n.p. |
| ORCL | 0.5012 / 0.4315 | −0.3091 / −0.3387 | 3.00 / 2.76 | 0.8753 / 0.5883 | 29.135 / 21.330 |
| PNC | 0.0554 / n.p. | 0.1115 / n.p. | 1.21 / n.p. | 0.2044 / n.p. | 16.927 / n.p. |

**The leverage now matches.** Implied ln(A/D) = µ·|η|, ours vs reference:
AMZN 1.826 / 1.829 · COST 2.1913 / 2.1909 · INTU 1.687 / 1.704 ·
ORCL 0.929 / 0.934 — within 0.2–1.0% on every reference-valued name, which is
input-vintage noise. The barrier was the input gap, as the forensics below
predicted and the team confirmed. KHC now carries the abs-drift flag too
(its 250-day η is −0.013), and PNC produces measures against its whole
liability side with the deposit-funded classification annotating rather than
suppressing.

**What is still off, attributed:** the remaining residuals live entirely in
the estimated (σ_A, η) pair, not in leverage or formulas. (1) The η gaps
(largest: COST 0.048 vs 0.162) are **within one standard error of drift
estimation** on a ~1-year window — SE ≈ σ_A/√1y is 0.18 for COST, 0.27 for
AMZN, 0.43 for INTU — the well-documented drift-noise problem, not an
identifiable input difference. (2) The σ_A gaps (4–16%; largest ORCL
0.50 vs 0.43, INTU 0.43 vs 0.50) exceed sampling noise for daily volatility
and point to a different **estimation scheme** (our full EM iteration on the
inverted asset path vs whatever one-pass or delevering scheme the reference
uses) — not identifiable from displayed values alone; the reference's asset
path or scheme description would settle it. RiskScore ratios (0.73–1.37)
follow mechanically from σ² with matching ln(A/D).

¹ the reference σ for INTU was not provided; the formula lock derives it from
the reference RiskScore.

## Barrier forensics (how the field was identified — since confirmed)

The formula layer reproduces the reference outputs exactly given the
reference inputs (locked to the displayable precision in
`tests/test_reference_convention.py`), so the µ/CCM/RiskScore residuals above
are input differences. They are all one input.

Inverting the reference's own numbers gives its leverage:
`ln(A/D)_ref = µ_ref × |η_ref|`. Solving `ln((E+D*)/D*) = ln(A/D)_ref` with
our observed market cap E yields the barrier the reference must have used —
and it is our balance sheet's **Total Liabilities Net Minority Interest**
line, on every name for which reference values exist:

| Name | D ours (ST + 0.5·LT) | D* implied by the reference | Total Liabilities | TL / D* |
|---|---|---|---|---|
| AMZN | 1.049e+11 | 4.763e+11 | 4.747e+11 | **1.00** |
| COST | 4.068e+09 | 5.313e+10 | 5.292e+10 | **1.00** |
| INTU | 3.866e+09 | 1.850e+10 | 1.870e+10 | **1.01** |
| ORCL | 8.169e+10 | 2.235e+11 | 2.187e+11 | **0.98** |

**Named attribution — team-confirmed 2026-07-29, now the REFERENCE preset's
`barrier_field`: the reference implementation's default point is total
liabilities; the documented convention keeps `ST + 0.5·LT`.** The σ_A and η residuals are downstream
of the same field, not independent culprits: the EM inversion delevers equity
against the barrier, so a ~2.7–13× larger D produces a different asset path
and with it the different σ_A and η. Dividend construction and the shares
method — the other suspected culprits — are not needed: one field closes the
books on all four names. (AMZN's "LT debt differing >2×" shows up here as the
larger pattern: the whole liability side, not a debt line, is the barrier.)

## Ablation: was it the 250-day window?

One switch at a time, starting from DOCUMENTED, same 2026-07-27 data. Cells
are µ / RiskScore; "—" is a defective regime with no value (documented
suppression).

| Name | DOCUMENTED | (a) window 250d | (b) + raw η | (c) + abs | (d) + TL barrier = REFERENCE | reference |
|---|---|---|---|---|---|---|
| AMZN | 12.52 / 0.903 | 201.03 / 0.909 | 51.15 / 0.909 | 51.15 / 0.909 | 21.41 / 2.277 | 16.96 / 2.104 |
| COST | 36.37 / 0.178 | 185.75 / 0.179 | 104.75 / 0.179 | 104.75 / 0.179 | 45.56 / 0.667 | 13.50 / 0.737 |
| DELL | 3.93 / 4.524 | 2.54 / 4.558 | 2.20 / 4.558 | 2.20 / 4.558 | 1.32 / 11.653 | n.p. |
| INTU | — / 2.195 | — / 2.207 | — / 2.207 | 3.73 / 2.207 | 2.24 / 6.350 | 1.55 / 8.687 |
| KHC | — / 2.148 | — / 2.153 | 127.20 / 2.153 | 127.20 / 2.153 | 42.28 / 4.240 | n.p. |
| KO | 22.17 / 0.368 | 14.02 / 0.365 | 13.09 / 0.365 | 13.09 / 0.365 | 10.19 / 0.651 | n.p. |
| ORCL | 36.68 / 11.973 | — / 12.059 | — / 12.059 | 3.82 / 12.059 | 3.00 / 29.135 | 2.76 / 21.330 |
| PNC | 7.06 / 1.466 | 5.78 / 1.473 | 5.46 / 1.473 | 5.46 / 1.473 | 1.21 / 16.927 | n.p. |

Per-switch reading, per company — the answer differs by name exactly as
expected:

- **The window is decisive only where 5y and 1y drift diverge, and there it
  acts by flipping the sign.** ORCL: the 5y drift is +0.21, the 250-day drift
  is −0.43 — step (a) sends ORCL from µ = 36.7 into the defective regime, and
  only abs (c) brings a value back. INTU is defective at both windows; KHC is
  defective at 5y and only the raw-η denominator (b) revives it. For the
  positive-drift names the 250-day window moves µ **away** from the reference
  (AMZN 12.5 → 201.0 vs reference 17.0): our 250-day drift is much smaller
  than our 5y drift, so shortening the window alone widens the gap.
- **Dropping the Ito term closes roughly half the remaining log-gap for the
  positive-drift names** (AMZN 201 → 51; COST 186 → 105) because σ²/2 is
  material against small drifts.
- **abs() is binary**: it is the entire difference between "no value" and "a
  value" for ORCL and INTU, and a no-op for everyone else.
- **The barrier (d) is the dominant switch**: it moves RiskScore for the
  first time (RiskScore is invariant to (a)–(c) by construction) and closes
  the bulk of the remaining µ gap — AMZN 51.1 → 21.4 vs reference 17.0,
  COST 104.8 → 45.6, ORCL 3.82 → 3.00 vs 2.76 — bringing implied leverage
  within 0.2–1.0% of the reference on every reference-valued name.

**So: no — the 250-day window alone was not the explanation.** It explains
the sign flips on the negative-drift names (jointly with abs) and worsens the
positive-drift names; the dominant switch is the barrier field (total
liabilities vs `ST + 0.5·LT`, since confirmed and folded into the preset),
with the Ito term second. What remains after all four switches is (σ, η)
estimation noise/scheme, attributed above.

## Follow-ups

- DELL, KHC, KO, PNC reference inputs: not provided; the one-sided rows above
  and the formula-lock test both mark them for completion, never guessing.
- The remaining σ_A offsets (4–16%) point at the reference's estimation
  scheme; its asset-path or scheme description would settle whether it
  iterates an EM loop or delevers once.
- The live-refresh path surfaced (and fixed) a real bug: fresh vendor frames
  arrived in mixed datetime units under pandas 3 and the as-of join refused
  them; live acquisition now routes through the cache's canonical-[ns]
  chokepoint (`tests/test_live_normalization.py`).
