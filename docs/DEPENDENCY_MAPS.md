# Dependency Maps

These maps describe the current repository as implemented. Arrows in the code
maps point from a caller or consumer to the module it depends on. Dotted edges
identify optional, type-only, or transitional dependencies.

## 1. Layer dependency map

```mermaid
flowchart LR
    CLI["run.py<br/>CLI entry point"]
    L1["Layer 1<br/>raw_data_architecture<br/>ACTIVE"]
    L2["Layer 2<br/>data_cleaning<br/>ACTIVE"]
    L3["Layer 3<br/>signal_construction<br/>PROTOTYPE"]
    L4["Layer 4<br/>dashboard<br/>PROTOTYPE"]

    CLI -->|configuration| L1
    CLI -->|starts workflow| L2
    L2 -->|source adapters and lineage| L1
    L2 -.->|lazy compatibility call| L3
    L2 -.->|lazy compatibility publisher| L4
    L4 -->|company data types| L2
    L4 -->|lineage and rate labels| L1
    L4 -->|model assumptions only| L3
```

The intended long-term dependency direction is Layer 4 -> Layer 3 -> Layer 2 ->
Layer 1. The two dotted Layer 2 -> Layer 3/4 edges are temporary exceptions in
`data_cleaning/workflow.py`, retained so the old end-to-end CLI still works.

## 2. Python module dependency map

```mermaid
flowchart LR
    RUN["run.py"] --> RW["data_cleaning.workflow"]
    RUN --> RC["raw_data_architecture.config"]

    subgraph RAW["Layer 1 - Raw Data Architecture"]
        RC
        RL["lineage"]
        RS["sources"] --> RC
    end

    subgraph CLEAN["Layer 2 - Data Cleaning"]
        CC["config"]
        CT["transforms"] --> CC
        CA["alignment"] --> CT
        CD["company"] --> RL
        RW --> CA
        RW --> CT
        RW --> CD
        RW --> RS
        RW --> RC
    end

    subgraph SIGNAL["Layer 3 - Signal Construction"]
        SC["config"]
        CR["credit"] --> SC
    end

    subgraph DASH["Layer 4 - Dashboard / Publishing"]
        DC["config"]
        EX["excel"] --> DC
        LT["longtable"] --> DC
        EX --> CD
        EX --> RC
        EX --> RL
        EX --> SC
        LT --> CD
        LT --> RL
    end

    CD -.->|TYPE_CHECKING only| CR
    RW -.->|when credit enabled| CR
    RW -.->|during publishing| EX
    RW -.->|during publishing| LT
```

## 3. Runtime call map

```mermaid
flowchart TD
    START["python run.py"] --> ARGS["Parse tickers, years, feature flags"]
    ARGS --> RUN["data_cleaning.workflow.run"]
    RUN --> RATES["raw.sources.fetch_rates"]
    RUN --> LOOP["For each ticker"]
    LOOP --> TICKER["Create Yahoo Ticker"]
    TICKER --> INFO["raw.sources.get_info"]
    TICKER --> PRICE["raw.sources.get_history"]
    TICKER --> STMT["raw.sources.get_statements"]
    INFO --> COMPANY["CompanyData"]
    PRICE --> COMPANY
    STMT --> TRIM["clean.transforms"]
    TRIM --> DEBT["Debt schedule"]
    COMPANY --> PANEL["clean.alignment.build_panel"]
    DEBT --> PANEL
    RATES --> PANEL
    PANEL -.->|unless --no-credit-model| MODEL["signal.credit.MertonKMVModel"]
    PANEL --> EXPORT["dashboard publishers"]
    MODEL --> EXPORT
    EXPORT --> FILES["dashboard/output<br/>XLSX, CSV, Parquet"]
```

## 4. Data artifact map

```mermaid
flowchart LR
    YF["Yahoo Finance"] --> RAM["Source-shaped DataFrames<br/>in memory"]
    FRED["FRED"] --> RAM
    RAM --> NORMAL["Normalized statements,<br/>prices, debt and rates"]
    NORMAL --> PANEL["Aligned clean panel"]
    PANEL -.-> SIGNALS["Prototype PD / DD estimate"]
    PANEL --> PUBLISH["Compatibility exports"]
    SIGNALS -.-> PUBLISH

    RAM -.->|target; not implemented| RAWPQ["raw_data_architecture/data<br/>immutable Parquet"]
    PANEL -.->|target; not implemented| CLEANPQ["data_cleaning/data<br/>validated Parquet"]
    PUBLISH --> OUT["dashboard/output"]
```

The solid path is implemented today. The dotted Parquet boundaries are the next
architecture milestone and are intentionally shown as missing dependencies.

## 5. External package map

| Layer | Direct packages | Purpose |
| --- | --- | --- |
| Raw Data Architecture | `yfinance`, `requests`, `pandas` | Yahoo/FRED acquisition and source frames |
| Data Cleaning | `pandas`, `numpy`; currently also `yfinance` in `workflow.py` | Transformation, alignment, compatibility orchestration |
| Signal Construction | `pandas`, `numpy`, `scipy` | Merton/KMV numerical model prototype |
| Dashboard | `pandas`, `openpyxl`, `pyarrow` | Excel, CSV, and Parquet publishing |

## Known dependency cleanup

1. Move `yf.Ticker(...)` creation out of `data_cleaning/workflow.py` and behind
   a Layer 1 adapter.
2. Replace the Layer 2 -> Layer 3/4 compatibility calls with a root-level stage
   orchestrator or separate CLI commands.
3. Remove the type-only `CompanyData -> CreditEstimate` reference by publishing
   signal records separately from clean company data.
4. Make Layer 4 consume versioned published tables rather than in-memory
   `CompanyData` objects.

Update these maps whenever a cross-layer import, stage entry point, or persisted
artifact contract changes.
