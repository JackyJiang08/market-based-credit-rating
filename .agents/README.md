# Agent repository guidance

## Mandatory startup gate

Every agent **MUST** complete the following before inspecting implementation
details, editing files, running project commands, or proposing changes:

1. Read the root [`README.md`](../README.md) completely.
2. Read [`docs/README.md`](../docs/README.md) completely.
3. Read the current documentation set referenced there, including at minimum:
   - [`docs/DEVLOG.md`](../docs/DEVLOG.md)
   - [`docs/TIMING_PROTOCOL.md`](../docs/TIMING_PROTOCOL.md)
   - [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
   - [`docs/GAP_ANALYSIS.md`](../docs/GAP_ANALYSIS.md)

This is a hard prerequisite, not an optional orientation step. If any required
document changes during the task, the agent must re-read the changed sections
before continuing.

## Repository rules

- Preserve the four top-level workflow layers.
- Put new code in the layer that owns its output contract.
- Do not introduce backward imports from an earlier layer to a later layer.
- Treat Layer 1 and Layer 2 as the only active implementation scope until the
  project owner explicitly activates signal construction or dashboard work.
- Any date alignment change must include a no-look-ahead test.
- Follow `docs/TIMING_PROTOCOL.md` for every time-dependent task. Unless the
  user explicitly authorizes a non-causal analysis, no feature or fitted
  transformation may use information with `available_at > decision_time`.

## Mandatory push gate

Before every `git push`, every agent **MUST**:

1. Update [`docs/DEVLOG.md`](../docs/DEVLOG.md) with the exact push scope.
2. Record breaking changes, validation actually performed, and unresolved
   follow-ups.
3. Include the DEVLOG update in the same commit or push batch.
4. Confirm the DEVLOG change is part of the outgoing diff.

An agent must not push when `docs/DEVLOG.md` has not been synchronized for that
push. This requirement applies even when the pushed change is documentation,
configuration, or repository maintenance rather than application code.
