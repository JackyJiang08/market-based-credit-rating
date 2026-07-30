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

## Reconciliation at the 2026-07-27 close

Ours computed under `REFERENCE`; the reference implementation's values after
the slash.

| Name | σ_A ours/ref | η ours/ref | µ ours/ref | CCM ours/ref | RiskScore ours/ref |
|---|---|---|---|---|---|
| AMZN | 0.3057 / 0.2653 | 0.0627 / 0.1078 | 51.15 / 16.96 | 0.4651 / 0.3569 | 0.909 / 2.104 |
| COST | 0.1968 / 0.1882 | 0.0444 / 0.1623 | 104.75 / 13.50 | 0.1875 / n.p. | 0.179 / 0.737 |
| DELL | 0.5811 / n.p. | 1.2399 / n.p. | 2.20 / n.p. | 0.1001 / n.p. | 4.558 / n.p. |
| INTU | 0.4622 / n.p.¹ | −0.8344 / −1.1008 | 3.73 / 1.55 | 0.0823 / n.p. | 2.207 / 8.687 |
| KHC | 0.1903 / n.p. | 0.0102 / n.p. | 127.20 / n.p. | 2.7389 / n.p. | 2.153 / n.p. |
| KO | 0.1667 / n.p. | 0.2108 / n.p. | 13.09 / n.p. | 0.0477 / n.p. | 0.365 / n.p. |
| ORCL | 0.5716 / 0.4315 | −0.4303 / −0.3387 | 3.82 / 2.76 | 0.4613 / 0.5883 | 12.059 / 21.330 |
| PNC | 0.1667 / n.p. | 0.2515 / n.p. | 5.46 / n.p. | 0.0804 / n.p. | 1.473 / n.p. |

¹ the reference σ for INTU was not provided; the formula lock derives it from
the reference RiskScore.

ORCL and INTU carry `MU_USES_ABS_DRIFT` under REFERENCE (η < 0), on ours and
on the reference alike — annotated, never silent.

## Residual attribution: the barrier field

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

**Named attribution: the reference implementation's default point is total
liabilities; ours is `ST + 0.5·LT`.** The σ_A and η residuals are downstream
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

| Name | DOCUMENTED | (a) window 250d | (b) + raw η | (c) + abs = REFERENCE | reference |
|---|---|---|---|---|---|
| AMZN | 12.52 / 0.903 | 201.03 / 0.909 | 51.15 / 0.909 | 51.15 / 0.909 | 16.96 / 2.104 |
| COST | 36.37 / 0.178 | 185.75 / 0.179 | 104.75 / 0.179 | 104.75 / 0.179 | 13.50 / 0.737 |
| DELL | 3.93 / 4.524 | 2.54 / 4.558 | 2.20 / 4.558 | 2.20 / 4.558 | n.p. |
| INTU | — / 2.195 | — / 2.207 | — / 2.207 | 3.73 / 2.207 | 1.55 / 8.687 |
| KHC | — / 2.148 | — / 2.153 | 127.20 / 2.153 | 127.20 / 2.153 | n.p. |
| KO | 22.17 / 0.368 | 14.02 / 0.365 | 13.09 / 0.365 | 13.09 / 0.365 | n.p. |
| ORCL | 36.68 / 11.973 | — / 12.059 | — / 12.059 | 3.82 / 12.059 | 2.76 / 21.330 |
| PNC | 7.06 / 1.466 | 5.78 / 1.473 | 5.46 / 1.473 | 5.46 / 1.473 | n.p. |

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
- **What no switch closes is the barrier**: after all three switches the
  remaining µ gap is ×1.4 (ORCL) to ×7.8 (COST), and the RiskScore gap
  (convention-invariant by construction) can only come from inputs — both are
  the total-liabilities barrier identified above.

**So: no — the 250-day window alone was not the explanation.** It explains
the sign flips on the negative-drift names (jointly with abs), worsens the
positive-drift names, and the dominant residual on every name is the barrier
field (total liabilities vs `ST + 0.5·LT`), with the Ito term second.

## Follow-ups

- DELL, KHC, KO, PNC reference inputs: not provided; the one-sided rows above
  and the formula-lock test both mark them for completion, never guessing.
- The live-refresh path surfaced (and fixed) a real bug: fresh vendor frames
  arrived in mixed datetime units under pandas 3 and the as-of join refused
  them; live acquisition now routes through the cache's canonical-[ns]
  chokepoint (`tests/test_live_normalization.py`).
