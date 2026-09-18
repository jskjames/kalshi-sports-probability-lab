# COURTSIDE · Kalshi Sports Market Intelligence

**When a sports market implies a 70% win probability, how often does that team win?**

An auditable probability-calibration study of NBA winner contracts using real public Kalshi market, settlement, milestone and minute-candlestick data. Built for research, with an interactive dashboard and a reproducible Python/SQL pipeline.

## View the project

Open **docs/index.html** in a browser. The dashboard uses bundled data and needs no API key, Python installation, account or backend. Start with the one-hour horizon, inspect the calibration curve, then read the chronological holdout comparison and the game ledger.

- [Findings](docs/findings.md)
- [Methodology and limitations](docs/methodology.md)
- [Extension guide](docs/extending.md)
- [SQL analysis](sql/research_queries.sql)

## What this demonstrates

- **Data engineering:** paced public-API ingestion, cached responses, historical/live routing, event-to-schedule joins, schema normalization and indexed SQLite tables.
- **Statistical analysis:** Brier score, log loss, Wilson intervals, paired date-block bootstrap and matched-game horizon comparisons.
- **Machine learning:** regularized logistic probability calibration selected on validation data, with outcome-resolution purging before held-out evaluation.
- **Product analytics:** interactive filters, transparent exclusions, sensitivity analysis and a searchable evidence ledger.

A market quote is an implied probability, not a verified true probability. The project tests that distinction. It does not estimate trading profits or claim to beat a bookmaker.

## Reproduce

Python 3.10+ recommended. From the extracted project directory:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/restore_sample.py
python -m kalshi_lab.analysis --root . --league NBA
```

The research bundle includes compressed minute observations so the last command rebuilds the results offline. To collect a new bounded sample instead:

```bash
python -m kalshi_lab.collect --root . --league NBA --max-games 500
python -m kalshi_lab.analysis --root . --league NBA
```

Collection can take many minutes. GET requests are cached and paced; repeating the collection reuses cached responses. Remove or relocate `data/cache` if intentionally collecting a fresh snapshot. Updated API data can change results. The collector caps discovery to one page per storage tier and the newest requested number of settled events **before** exclusions; this is not a complete season or a random sample.

## Repository map

```text
src/kalshi_lab/   API client, market adapters, collection and analysis
sql/             Reusable research queries
outputs/         Game/snapshot CSVs, holdout predictions and result JSON
sample/          Frozen compressed observations and collection metadata
scripts/         Offline sample restoration
docs/           Static interactive dashboard and research documentation
tests/          Data-leakage, schema, scoring and outcome-rule tests
```

`analysis` writes `data/warehouse.sqlite` with indexed `games`, `bars`, `snapshots` and `snapshot_audit` tables. Large raw API responses and the generated database are excluded from Git. Source request hashes and timestamps are provided in `outputs/provenance.json`. `sample/` contains the frozen original candle records (compressed) and linked game metadata, so the study can be rebuilt without another API call. These source records are not covered by the code license.

## Scope and limitations

- NBA, game-winner contracts, one home-team outcome per game; 24h, 6h, 1h and 5m before the recorded scheduled start.
- Schedule timestamps are retrospective Kalshi milestones. Actual tipoff and historical schedule revisions have not been independently verified.
- Minute bar age does not establish the age of the underlying quote. Historical depth and executable size are unavailable here.
- Capped recent data can cross regular-season/playoff regimes. Small holdout samples limit claims about generalization.
- Isotonic calibration is intentionally gated until at least 1,000 training games; it is not fitted to this small study.
- No account credentials, order placement, betting automation or user transaction data are used.

## Publication

For GitHub Pages, publish the `docs` directory from the default branch. This package has not yet been uploaded to a repository or deployed. See `START_HERE.md` for local review first.

## Data attribution

Source: Kalshi public market-data API, retrieved for this research snapshot. Original data retain their source terms. This is an independent portfolio study, unaffiliated with Kalshi or the NBA. Code is provided under the MIT license.

## Verification

After restoring the sample and running analysis:

```bash
python -m unittest discover -s tests -v
python scripts/verify_sql.py
# Optional controller check, requires Node.js:
node tests/dashboard_smoke.cjs
```

These checks validate timestamp cutoffs, settlement rules, score formulas, date splits, output consistency, SQL parity and dashboard controller behavior. They do not substitute for checking desktop and mobile appearance in a real browser.
