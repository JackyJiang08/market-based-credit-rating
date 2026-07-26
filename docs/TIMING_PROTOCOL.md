# Timing Protocol

## Purpose

This project uses information available up to a decision time `t` to predict an
outcome after `t`. Unless a task explicitly declares otherwise, no data that
became available after `t` may influence features, transformations, model
parameters, signal construction, ranking, or evaluation inputs.

The default invariant is:

```text
max(feature.available_at) <= decision_time_t
```

Future observations may appear only as prediction targets or evaluation labels.
They must never leak into the feature pipeline.

## 1. Time fields

Every time-dependent dataset should carry enough metadata to distinguish these
timestamps:

| Field | Meaning |
| --- | --- |
| `event_time` | When the underlying economic or market event occurred |
| `period_end` | End of the accounting period described by a statement |
| `available_at` | Earliest time the project could legitimately know the value |
| `ingested_at` | When this system downloaded or received the value |
| `decision_time` | The cutoff `t` at which a prediction is formed |
| `target_time` | Future time whose outcome is being predicted |
| `vintage` | Source revision or snapshot identity, when values can be revised |

`event_time` and `period_end` are not substitutes for `available_at`.

## 2. Default eligibility rule

A record is eligible for a feature at time `t` only when:

```text
record.available_at <= t
```

Required behavior:

- Join asynchronous data on `available_at`, not merely on event or period date.
- Use backward as-of joins for point-in-time feature construction.
- Forward-fill only from an observation already available at `t`.
- Never backfill a missing historical value from a later observation.
- Store `decision_time` and `max_input_available_at` with every model panel or
  signal output.

## 3. Source-specific rules

### Market prices

- An intraday decision may use only trades or quotes timestamped at or before
  `t`.
- A daily closing price for date `d` is available only after that market close.
- A signal using the close of `d` must not be represented as tradable before
  the close. For next-open strategies, its earliest execution belongs to the
  next trading session.
- Adjusted-close histories may change after corporate actions. Historical
  research should retain the downloaded vintage or document that it uses a
  retrospectively adjusted series.

### Financial statements

- `period_end` is not the information-availability date.
- A statement value becomes eligible on its public filing or publication time.
- If the true filing time is unavailable, use a documented conservative lag
  and set an explicit flag such as `availability_method="estimated_lag"`.
- Restated values must not overwrite the value that was known at an earlier
  decision time. Preserve the original vintage when point-in-time analysis is
  required.

### FRED and macroeconomic data

- The observation date is not automatically the publication time.
- Use the source release/publication timestamp or a documented conservative
  availability lag.
- Revised macro series require vintage-aware data for strict historical
  backtests. A latest-vintage download must be labeled as retrospective.

### Shares and company metadata

- Current shares outstanding, market capitalization, sector, or other company
  metadata must not be applied backward as if they were historically known.
- A constant reference-share assumption is allowed only when it is explicitly
  identified as a modelling assumption and its reference date is stored.
- A latest-date share estimate is not backtest-safe for dates before its
  `available_at`.

## 4. Feature windows

For a feature calculated at `t`:

- Every raw observation in the rolling or expanding window must satisfy
  `available_at <= t`.
- Window endpoints must be explicit about whether an observation exactly at
  `t` is included.
- If a decision occurs before the daily close, that day's close is excluded.
- Imputation, normalization, winsorization, PCA, feature selection, and similar
  fitted transformations must be trained only on data available within the
  training interval.
- Cross-sectional features at `t` may use other entities only when each entity's
  input was available by the same cutoff.

## 5. Targets and model evaluation

Future values after `t` are allowed only in the target and evaluation path.

For horizon `h`:

```text
features = information available at or before t
target   = outcome over (t, t + h]
```

The target path must remain separate from feature construction:

- Do not calculate features from future returns, future defaults, or future
  statement values.
- Do not fit scalers or transformations on the combined train and test periods.
- Use chronological train/validation/test splits.
- If labels overlap in time, apply an appropriate gap, purge, or embargo when
  leakage between samples is possible.
- Evaluation and dashboard code may read realized future outcomes only after
  predictions have been frozen and identified by model/run version.

## 6. Approved exception process

Using information after `t` is prohibited by default. An exception is valid
only when the task explicitly requests a retrospective, oracle, diagnostic, or
other non-causal analysis.

Every exception must:

1. State why data after `t` is required.
2. Set a visible marker such as `lookahead_allowed=true`.
3. Label all affected outputs `NON_CAUSAL` or `RETROSPECTIVE`.
4. Keep those outputs separate from production signals and backtest results.
5. Record the exception in `docs/DEVLOG.md`.

Silence or ambiguity is not permission to use data after `t`.

## 7. Required validation

Point-in-time pipelines must test at least these invariants:

```python
assert panel["max_input_available_at"].le(panel["decision_time"]).all()
assert features.index.max() <= decision_time
assert target_start > decision_time
```

Additional required tests:

- A statement is unavailable before its filing/publication time.
- A closing price is unavailable before the corresponding close.
- Backward joins never select a future record.
- Missing data is not filled from the future.
- Re-running an old `decision_time` does not use a newer source vintage.
- Train-only transformations cannot observe validation or test rows.

Any change to alignment, feature windows, source timestamps, model training, or
target construction must add or update a no-look-ahead test.

## 8. Output audit fields

Clean panels and signals should expose:

```text
run_id
source_snapshot_id
decision_time
max_input_available_at
feature_window_start
feature_window_end
target_start
target_end
availability_method
lookahead_allowed
timing_validation_status
```

These fields allow another contributor to audit a prediction without relying
on undocumented assumptions.

## 9. Current repository status

The repository does not yet fully satisfy this protocol:

- `data_cleaning/alignment.py` currently aligns statements using their period
  end rather than their publication-time `available_at`.
- The current reference-share method can apply a latest-date estimate across
  earlier history.
- Raw and clean point-in-time vintages are not yet persisted as immutable
  Parquet snapshots.

Until these issues are fixed and covered by tests, existing aligned panels must
be described as research prototypes and not as backtest-safe datasets.

## 10. Team timestamp standard

Adopted 2026-07-26, at the project owner's direction, for the deliverable-v1
freeze. Before this section existed, every artifact stamp in the repository was
naive local machine time in whatever format its writer chose.

- **Timezone: UTC.** All newly generated artifact timestamps are timezone-aware
  UTC (`datetime.now(timezone.utc)`), never naive local time. Local time
  depends on which contributor's machine ran the pipeline; UTC does not.
- **Format: ISO 8601.** Human-readable stamps use `YYYY-MM-DDTHH:MM:SSZ`.
  Filename-embedded stamps use the compact form `YYYYMMDDTHHMMSSZ` (colons are
  not filename-safe).
- **Scope: new stamps only.** Existing artifacts and their historical names are
  not renamed or restamped. DEVLOG entry headings remain date-only
  (`YYYY-MM-DD`). Panel and statement date columns remain calendar dates
  (`%Y-%m-%d`) — they identify trading days and period ends, not instants.
- **First application:** the deliverable workbook filename
  (`outputs/submission_<YYYYMMDDTHHMMSSZ>.xlsx`) and the workbook README
  sheet's `Generated` field, from `dashboard/submission.py` /
  `dashboard/records.py`.

`event_time`, `available_at`, and the other §1 fields are unaffected: they are
data semantics, not artifact stamps, and carry whatever precision and zone
their source defines (documented per source in §3).

## Contributor checklist

Before merging or pushing a time-dependent change, confirm:

- [ ] The decision cutoff `t` is explicit.
- [ ] Every feature input has `available_at <= t`.
- [ ] Future outcomes exist only in the target/evaluation path.
- [ ] Joins and fills cannot select future observations.
- [ ] Fitted transformations use training data only.
- [ ] Output audit fields identify the cutoff and source snapshot.
- [ ] No-look-ahead tests pass.
- [ ] Any approved exception is visible, isolated, and recorded in DEVLOG.
