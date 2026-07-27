# Architecture

The current system, as built. Three diagrams, nothing speculative.
`tests/test_architecture_doc.py` fails CI if the package map below drifts
from the actual tree, so this document cannot silently go stale.

## Package map

```mermaid
flowchart LR
    subgraph core["packages/core/creditrating"]
        data["data/\nproviders · cleaning · alignment\nsectors · cache · provenance · pipeline"]
        model["model/\nem · tic · conversion · config"]
        tables["tables/\nloader · validation"]
        io["io/\nrecords · workbook · excel · export"]
        diagnostics["diagnostics/\nuncertainty · checks"]
        domain["domain.py (pydantic)"]
        cli["cli.py (typer)"]
    end
    api["services/api\nFastAPI, offline-first"]
    terminal["apps/terminal\nNext.js static terminal"]

    data --> model --> io
    model --> tables
    diagnostics --> model
    api --> core
    terminal -->|"static JSON export"| core
```

One installable package owns everything computational; the API and the web
terminal are thin consumers. Import direction is one-way — nothing in
`creditrating` knows the API or the terminal exist.

## Runtime data flow

```mermaid
flowchart LR
    yahoo["Yahoo Finance"] --> cache["data/cache/\nread-through, resumable\n(committed fixture subset)"]
    fred["FRED DGS1"] --> cache
    cache --> pipeline["pipeline.fetch_company\nclean → align → gate"]
    pipeline --> em["EM inversion\nσ_A, A, η_A"]
    em --> measures["TiC measures\nRiskScore · DD · PIT PD"]
    measures --> conv["conversion\nTTC PD → letter"]
    grids[("local/ grids\nLICENSED — never committed,\nnever bundled, never in images")] -.-> conv
    conv --> outputs["io: workbook · exports\n+ per-run manifest"]
```

Every acquisition is cached and hashed into a per-run manifest, so a batch is
resumable, offline-runnable, and auditable. The licensed conversion grids sit
behind a hard boundary: absent on CI and in every artifact, with the
degraded path (`TTC = null` + reason code) tested as a first-class state.

## Static-site data pipeline

```mermaid
flowchart LR
    fixtures["committed fixtures\n+ run-of-record CSVs"] --> export["make build-site-data\n(git SHA + vintage in every file)"]
    export --> check{"check_bundle_safety.py\npath · value · shape"}
    check -->|"violation"| fail["build FAILS"]
    check -->|"clean"| json["apps/terminal/public/data/*.json"]
    json --> site["next build → static export\n→ GitHub Pages"]
```

The terminal never computes: it renders the exported JSON, validated with
Zod at load time. The bundle-safety gate compares every exported numeric
against the licensed tables (zero matches allowed) before any site build.
