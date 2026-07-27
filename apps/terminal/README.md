# apps/terminal — the creditrating terminal

Next.js 15 (App Router) + TypeScript strict + Tailwind + shadcn/ui +
TanStack Query/Table + Zod. A **fixture-backed static site**: every number is
computed offline from committed data and exported by
`make build-site-data` into `public/data/*.json`, each file versioned with
the producing git SHA and data vintage. `scripts/check_bundle_safety.py`
fails the build if licensed grid content would enter the bundle.

- **⌘K or `/`** — fuzzy company search over the 150-name universe; enter → company view.
- **Company view** — RiskScore and rank first; the S&P letter only ever with
  its interval attached ("BB (BBB-..BB-)") plus a derived-conversion badge;
  flags (WEAKLY_IDENTIFIED, gates, floors) as first-class chips; provenance
  popovers per input; EM asset-path sparkline.
- Dark, high-density, `tabular-nums`, keyboard navigable, WCAG AA; skeletons
  and explicit error/empty states; site-wide footer: fixture-backed demo,
  data as-of, not investment advice, methodology attribution.

Deployed to GitHub Pages by the `deploy` CI job (after every other cell is
green; the bundle-safety gate runs again inside the job) with
`NEXT_PUBLIC_BASE_PATH=/market-based-credit-rating`. A custom domain is a
documented option: set it in repo Pages settings and drop the base path.

```bash
make build-site-data   # export + bundle-safety check (fails on violation)
cd apps/terminal
npm ci
npm run typecheck && npm run lint && npm test && npm run build   # the CI cells
npx serve out          # static export
```
