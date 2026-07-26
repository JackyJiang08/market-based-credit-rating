# Changelog

Notable changes to the model and the delivered artifacts. Newest first.

Entries reference the GitHub issue they close. Detailed rationale lives in
`docs/DEVLOG.md`; architectural decisions live in `docs/adr/`.

## Unreleased

### Fixed

- **#14** Pinned the `Outlook` direction with regression tests. Eq. (28) is
  `PD_FH − S&P TTC` (PIT − TTC), which is what the code already computed; the
  delivered Asset sheet was correct. Three tests now fail loudly on an inversion.
