# Development Log

Last updated: 2026-07-09

This file under `docs/` is the shared, human-readable status record for the repository. It
must be updated as part of every push so contributors can understand what
changed, what was verified, and what remains open without reconstructing the
history from individual commits.

## Push rule

Before every push:

1. Add or update the newest entry under **Recent changes**.
2. Describe the pushed scope, important file or contract changes, and any
   breaking behavior.
3. Record the validation actually run; do not list checks that were skipped.
4. List unresolved follow-ups or explicitly write `None`.
5. Include the `DEVLOG.md` update in the same commit or push batch.

Entries are ordered newest first. One entry may summarize multiple commits in a
single push when they represent the same unit of work.

## Current project status

- Repository root: `PFPA_Intern_Project/`.
- Active implementation scope: Layer 1 Raw Data Architecture and Layer 2 Data
  Cleaning.
- Retained prototypes: Layer 3 Signal Construction and Layer 4 Dashboard.
- Current data path is still in memory; immutable raw and clean Parquet
  boundaries have not yet been implemented.
- Current timing gap: statement period-end is still used in alignment instead
  of a true publication-time `available_at` field.

## Recent changes

### 2026-07-09 - Repository architecture unification

- **Scope:** repository structure, documentation, and dependency ownership.
- **Summary:**
  - Moved the Git repository contents to the `PFPA_Intern_Project` root.
  - Reorganized code into the four workflow layer directories.
  - Split configuration ownership across the four layers.
  - Archived the original assignment and glossary documents.
  - Added code, runtime, data-artifact, and package dependency maps.
  - Added this push-update development log under `docs/`.
  - Added the mandatory point-in-time timing protocol and no-look-ahead rules.
  - Added mandatory agent startup and push gates: read the root README and
    current docs before work, and synchronize DEVLOG before every push.
  - Kept `pyproject.toml` at the repository root because Python build tools
    discover it there by default.
  - Moved the MIT license to `docs/LICENSE`.
- **Breaking changes:** imports from the former `mdtoolkit` package must use the
  new layer package paths.
- **Validation:** CLI help, layer imports, synthetic alignment smoke test,
  Python compilation, and `git diff --check`.
- **Follow-ups:** implement raw/clean Parquet persistence, add timing contracts,
  and remove the compatibility workflow's backward dependencies.

## Entry template

Copy this section to the top of **Recent changes** before pushing:

```markdown
### YYYY-MM-DD - Short change title

- **Scope:** layer, feature, fix, documentation, or infrastructure.
- **Summary:** what changed and why.
- **Breaking changes:** migration requirement, or `None`.
- **Validation:** commands or checks actually completed.
- **Follow-ups:** unresolved work, risks, or `None`.
```
