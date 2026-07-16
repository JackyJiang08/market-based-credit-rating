# Market-Based Credit-Rating Pipeline

A market-based credit-rating project for public companies: download equity and
interest-rate data, estimate a **KMV/Merton** structural model, and derive
credit measures (distance to default, probability of default) that feed a
**Time-Consistent (TiC)** credit rating. A PFPA intern project.

> **Status.** The complete four-layer pipeline — EM asset estimation, the full
> TiC measures (RiskScore / CCM / µ / DD / EDF / PIT PD), the
> no-regulatory-arbitrage **PIT → TTC → S&P** conversion, and the submission
> workbook — lives on the branch
> [`agent/unify-four-layer-architecture`](https://github.com/JackyJiang08/market-based-credit-rating/tree/agent/unify-four-layer-architecture)
> and is pending merge into `main`. This `main` branch currently holds the
> earlier equity/rates data pipeline with a Merton/KMV baseline, described below.
>
> Reference PDFs and the conversion workbook are proprietary PFPA material kept
> out of the repository.

---

## What `main` produces today

For any set of tickers (default: `COST KO DELL ORCL PNC WMT INTU AMZN T KHC`)
over a trailing window (default 2 years):

- **Per-company workbook** `output/<TICKER>_data.xlsx` — summary, the
  date-aligned daily panel (price + debt + rate, no look-ahead), the debt &
  liabilities schedule, price history with adjusted close, dividends, and
  quarterly/annual statements.
- **Master workbook** `output/_MASTER_summary.xlsx` — company summary, a ranked
  credit summary, latest debt snapshot, and macro rates.
- **Tidy long table** `output/all_companies_long.{csv,parquet}` for databases/BI.

Key conventions (shared with the full pipeline on the branch):

| Requirement | Implementation |
| --- | --- |
| Shares outstanding — one-day `mktcap / price`, held constant | `mdtoolkit/transforms.py` |
| Adjusted close (dividends & splits) | Yahoo `Adj Close` |
| Default-point debt `D = 100% short-term + 50% long-term` | `mdtoolkit/transforms.py` |
| Risk-free = **1-Year Treasury** (`DGS1`), 1-year horizon | FRED |
| Date alignment (as-of, no look-ahead) | `mdtoolkit/alignment.py` |

## Installation & usage

```bash
pip3 install -r requirements.txt      # Python 3.8+

python3 run.py                        # default universe, 2y
python3 run.py AAPL MSFT --years 3    # custom tickers / window
python3 run.py --no-credit-model      # data only
```

macOS users can double-click **`Download Stocks.command`**.

## Data sources

| Data | Source |
| --- | --- |
| Prices, financials, market cap, dividends | Yahoo Finance (`yfinance`) |
| 1-Year Treasury (`DGS1`), SOFR | FRED (Federal Reserve H.15) |

## Known limitations

- Non-dividend payers (e.g. **AMZN**) have blank dividend fields.
- Banks (e.g. **PNC**) omit a clean current/non-current split (debt fallback used).
- Yahoo's free tier returns ~5–7 quarters of quarterly statements.
- Dual-class names (e.g. **DELL**): the one-day reference-share method recovers
  the total share count so market cap reconciles.
- For large investment-grade firms, market-based PD is legitimately ~0; compare
  by **distance to default** and **RiskScore** instead.

## License

Project code: [MIT](LICENSE). Reference PDFs and the conversion workbook are
proprietary PFPA material and are kept out of the repository.
