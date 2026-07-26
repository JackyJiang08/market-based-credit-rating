"""`python -m mdt` entry point: `rate` a single company or run a `batch`."""

from __future__ import annotations

import argparse
import logging
from typing import Optional, Sequence

from data_cleaning.company import CompanyData
from data_cleaning.workflow import RunConfig, run
from raw_data_architecture import config as raw_config


def _fmt(x, pct: bool = False, nd: int = 4) -> str:
    if x is None:
        return "n/a"
    try:
        return f"{x*100:.{nd}f}%" if pct else f"{x:,.{nd}f}"
    except (TypeError, ValueError):
        return str(x)


def _print_company(c: CompanyData) -> None:
    """Print the full rating table for one company."""
    rows = [
        ("Company", c.name), ("Symbol", c.ticker),
        ("Last price", _fmt(c.last_close, nd=2)),
        ("Reference shares", _fmt(c.reference_shares, nd=0)),
        ("Default-point debt D", _fmt(_last(c, "DefaultPointDebt_D"), nd=0)),
        ("Risk-free r", _fmt(_last(c, "RiskFree_R"), pct=True, nd=3)),
        ("Asset volatility sigma_A", _fmt(c.sigma_A, pct=True, nd=2)),
        ("Asset value A", _fmt(c.asset_value, nd=0)),
        ("Asset return eta_A", _fmt(c.eta_A, pct=True, nd=2)),
        ("CCM", _fmt(c.ccm)), ("mu (life expectancy)", _fmt(c.mu, nd=2)),
        ("TiC", _fmt(c.tic)), ("RiskScore", _fmt(c.risk_score, nd=2)),
        ("Distance to Default", _fmt(c.dd, nd=2)),
        ("EDF", _fmt(c.edf, pct=True)),
        ("PIT PD", _fmt(c.pit_pd, pct=True)),
        ("TTC PD", _fmt(c.ttc_pd, pct=True)),
        ("S&P rating", c.sp_rating or "n/a"),
        ("Outlook (PIT-TTC)", _fmt(c.outlook, pct=True)),
        ("EM converged / iters", f"{c.em_converged} / {c.em_iters}"),
    ]
    width = max(len(k) for k, _ in rows)
    print("\n" + "=" * (width + 24))
    for k, v in rows:
        print(f"  {k:<{width}} : {v}")
    if c.rating_off_grid:
        print("  NOTE: (CCM, mu) outside the conversion grid -> edge-clamped.")
    print("=" * (width + 24) + "\n")


def _last(c: CompanyData, col: str):
    if c.panel is None or c.panel.empty or col not in c.panel:
        return None
    s = c.panel[col].dropna()
    return None if s.empty else float(s.iloc[-1])


def _rate(args) -> None:
    from dashboard import submission

    companies = run(RunConfig(tickers=[args.company], years=args.years))
    if not companies:
        raise SystemExit(f"Could not process '{args.company}'.")
    c = companies[0]
    _print_company(c)
    path = submission.write_submission(companies, filename=f"{c.ticker}_report.xlsx")
    print(f"Report written: {path}")


def _batch(args) -> None:
    import yaml

    with open(args.config) as fh:
        data = yaml.safe_load(fh) or {}
    tickers = [str(x).strip() for x in (data.get("companies") or [])]
    if not tickers:
        raise SystemExit(f"No 'companies:' list found in {args.config}")
    run(RunConfig(tickers=tickers, years=args.years))


def main(argv: Optional[Sequence[str]] = None) -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)-7s  %(message)s",
                        datefmt="%H:%M:%S")
    p = argparse.ArgumentParser(prog="python -m mdt", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--years", type=int, default=raw_config.DEFAULT_YEARS,
                   help=f"History window in years (default {raw_config.DEFAULT_YEARS})")
    sub = p.add_subparsers(dest="command", required=True)

    pr = sub.add_parser("rate", help="rate one company (ticker or name)")
    pr.add_argument("company")
    pr.set_defaults(func=_rate)

    pb = sub.add_parser("batch", help="run the batch from a companies.yaml")
    pb.add_argument("config")
    pb.set_defaults(func=_batch)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
