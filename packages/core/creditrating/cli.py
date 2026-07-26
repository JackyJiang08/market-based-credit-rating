"""Command-line interface: `rate` one company or run a `batch`.

Typer-based; `mdt` and `creditrating` console scripts both land here, and
`python -m mdt` still works through the compatibility shim."""

from __future__ import annotations

import logging

import typer

from creditrating.data.company import CompanyData
from creditrating.data.pipeline import RunConfig, run
from creditrating.data import provider_config as raw_config


def _fmt(x, pct: bool = False, nd: int = 4) -> str:
    if x is None:
        return "n/a"
    try:
        return f"{x*100:.{nd}f}%" if pct else f"{x:,.{nd}f}"
    except (TypeError, ValueError):
        return str(x)


def _print_company(c: CompanyData) -> None:
    """Print the full rating table for one company.

    Follows the presentation rule (README, docs/UNCERTAINTY.md): RiskScore
    leads the credit block, and the letter never appears without its interval
    or, failing that, the reason there is none. All fields project from
    dashboard.records so the CLI cannot drift from the workbook.
    """
    from creditrating.io import records

    r = records.credit_record(c)
    letter = records.rating_with_interval(r)

    flags: list[str] = []
    if r["drift_regime"] == "DEFECTIVE":
        flags.append("DEFECTIVE drift regime (Prop. 4.4.1 fails): "
                     "mu/CCM/PIT/TTC/rating not applicable")
    if r["weakly_identified"]:
        flags.append(f"WEAKLY_IDENTIFIED (|t| = {abs(r['drift_t_stat']):.2f} < 2): "
                     "read the interval, not the point rating")
    if r["model_applicable"] is False:
        flags.append(f"MODEL_NOT_APPLICABLE ({r['applicability_reason']})")
    if r["rating_off_grid"]:
        flags.append("(CCM, mu) outside the conversion grid -> edge-clamped")
    if r["ttc_at_floor"]:
        flags.append("TTC PD at the grid's 2bp floor -> letter is floor-determined")
    if r["debt_source_contradictory"]:
        flags.append("debt source CONTRADICTORY (Total < LT in source)")

    t_note = (f"   (t = {r['drift_t_stat']:.2f})"
              if r["drift_t_stat"] is not None
              and r["drift_t_stat"] == r["drift_t_stat"] else "")
    sections = [
        ("INPUTS", [
            ("Last price", _fmt(c.last_close, nd=2)),
            ("Reference shares", _fmt(c.reference_shares, nd=0)),
            ("Default-point debt D", _fmt(_last(c, "DefaultPointDebt_D"), nd=0)),
            ("Risk-free r (DGS1)", _fmt(_last(c, "RiskFree_R"), pct=True, nd=3)),
        ]),
        ("MODEL (EM)", [
            ("Asset value A", _fmt(c.asset_value, nd=0)),
            ("Asset volatility sigma_A", _fmt(c.sigma_A, pct=True, nd=2)),
            ("Asset return eta_A", _fmt(c.eta_A, pct=True, nd=2) + t_note),
            ("EM converged / iters", f"{c.em_converged} / {c.em_iters}"),
        ]),
        ("CREDIT MEASURES", [
            ("RiskScore (Eq. 5/12)", _fmt(c.risk_score, nd=2)),
            ("Distance to Default", _fmt(c.dd, nd=2)),
            ("CCM", _fmt(c.ccm)),
            ("mu (life expectancy)", _fmt(c.mu, nd=2)),
            ("EDF", _fmt(c.edf, pct=True)),
            ("PIT PD", _fmt(c.pit_pd, pct=True)),
            ("TTC PD", _fmt(c.ttc_pd, pct=True)),
        ]),
        ("RATING", [
            ("S&P letter (interval)", letter),
            ("Determination", r["rating_determination"] or "n/a"),
            ("Basis", r["rating_basis"] or "n/a"),
            ("Outlook (PIT-TTC)", _fmt(c.outlook, pct=True)),
        ]),
    ]

    width = max(len(k) for _, rows in sections for k, _ in rows)
    bar = "=" * (width + 30)
    print("\n" + bar)
    print(f"  {c.name} ({c.ticker})")
    print(bar)
    for title, rows in sections:
        print(f"  {title}")
        for k, v in rows:
            print(f"    {k:<{width}} : {v}")
    print("  FLAGS")
    if flags:
        for f in flags:
            print(f"    ! {f}")
    else:
        print("    none")
    print(bar + "\n")


def _last(c: CompanyData, col: str):
    if c.panel is None or c.panel.empty or col not in c.panel:
        return None
    s = c.panel[col].dropna()
    return None if s.empty else float(s.iloc[-1])


def _rate_impl(company: str, years: int) -> None:
    from datetime import datetime, timezone

    from creditrating.io import workbook as submission

    companies = run(RunConfig(tickers=[company], years=years))
    if not companies:
        raise SystemExit(f"Could not process '{company}'.")
    c = companies[0]
    _print_company(c)
    # Stamped per the team standard (TIMING_PROTOCOL §10); a fixed name would
    # trip the writer's never-overwrite guard on the second run.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = submission.write_submission(companies,
                                       filename=f"{c.ticker}_report_{stamp}.xlsx")
    print(f"Report written: {path}")


def _batch_impl(config: str, years: int, workers: int) -> None:
    import yaml

    with open(config) as fh:
        data = yaml.safe_load(fh) or {}
    entries = data.get("companies") or []
    # Accept both the plain list (companies.yaml) and the annotated mapping
    # form (universe.yaml: {ticker: ..., why: ...}).
    tickers = [str(x.get("ticker") if isinstance(x, dict) else x).strip()
               for x in entries]
    if not tickers:
        raise SystemExit(f"No 'companies:' list found in {config}")
    run(RunConfig(tickers=tickers, years=years, workers=workers))


app = typer.Typer(add_completion=False, no_args_is_help=True,
                  help=__doc__)


def _setup_logging() -> None:
    import structlog

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)-7s  %(message)s",
                        datefmt="%H:%M:%S")
    # structlog carries the per-run correlation id (run_id) bound in
    # pipeline.run; stdlib loggers keep their existing format.
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="%H:%M:%S", utc=True),
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )


@app.command()
def rate(company: str = typer.Argument(..., help="ticker or company name"),
         years: int = typer.Option(raw_config.DEFAULT_YEARS, "--years",
                                   help="history window in years")) -> None:
    """Rate one company: full table to stdout + a per-ticker report."""
    _setup_logging()
    _rate_impl(company, years)


@app.command()
def batch(config: str = typer.Argument(..., help="path to a companies.yaml"),
          years: int = typer.Option(raw_config.DEFAULT_YEARS, "--years"),
          workers: int = typer.Option(1, "--workers",
                                      help="concurrent company fetches "
                                           "(cached reruns tolerate more)")) -> None:
    """Run the batch from a YAML universe file."""
    _setup_logging()
    _batch_impl(config, years, workers)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
