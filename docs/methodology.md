# Methodology and research contract

## Question and scope
Does the probability implied by Kalshi's NBA winner markets align with recorded
contract outcomes? Does a simple recalibration improve unseen chronological
predictions? The research unit is **one home-team YES contract per game**.
This is retrospective research, not a live forecast service or trading strategy.

## Data and sampling
The collector reads the public production Kalshi API. It captures one page of
up to 1,000 settled markets from each of the current and historical market tiers,
combines by ticker, groups by event, orders by settlement timestamp and selects
up to 500 latest events **before** outcome/timing/quote exclusions. This is a
bounded recent cohort, not a random sample or complete season. Discovery cursor
availability and all excluded events are recorded. Increase the configured cap
or implement a declared calendar-period sample before making season-wide claims.

Market metadata are linked to the sole milestone explicitly listing that event.
Home and away participants are matched by structured IDs, not fuzzy team names.
Require exactly two markets, one YES and one NO result, and complementary $1/$0
settlements. Fair-value, tie, void and ambiguous settlements are excluded.
This deliberately does not generalize to three-outcome soccer without a new adapter.

## Timing and remaining uncertainty
Use milestone `start_date` in UTC. Do not use `occurrence_datetime`, market close,
expiration, settlement or last trade as the game start. The inspected source can
put occurrence time hours later than scheduled start.

**Important limitation:** the milestone is a retrospectively retrieved schedule.
It is not an independently verified actual tipoff timestamp and does not include
a complete revision history. The analysis is relative to this recorded scheduled
start. It cannot certify all historical prices as pre-tipoff for rescheduled
matches. Publication should retain this qualification; an independent actual-start
cross-check is the next methodological enhancement.

Milestone injury reports, recent form and status fields may reflect later updates.
They are never included as predictors. Collection timestamps and raw response hashes
are retained in the local cache. No model uses final market volume.

## Price definition
Collect one-minute candlesticks from 25 hours before start until start minus one
second. A snapshot at 24h / 6h / 1h / 5m uses the latest bar with end timestamp
**at or before** its cutoff. Do not select a candle spanning the future cutoff.
Use YES bid/ask close values. Historical API fields such as `close` contain dollar
strings; current fields such as `close_dollars` also contain dollar strings.
Never divide historical dollar values by 100.

Require 0 < bid ≤ ask < 1, spread ≤ $0.10 and bar lag ≤ 120 seconds. An invalid
latest observation is excluded, not silently replaced by an earlier valid quote.
Midpoint p=(bid+ask)/2 is a forecast proxy, not an observed true probability.
Spread is not a probability confidence interval. True quote-update age and
historical depth are unavailable from this analysis. A recently emitted candle
may repeat an older resting quote.

Primary evaluation uses midpoint only. A trade-price sensitivity comparison uses
only the same eligible games with an actual trade in the selected bar. No
`previous` trade is carried forward without a known timestamp. Previous-hour
contract volume and active minute counts only include bars ending by cutoff;
these are descriptive activity indicators, not complete liquidity measurements.

## Forecast scoring and calibration
Brier score = mean((p-y)^2). Log loss = -mean(y log p+(1-y) log(1-p)). Clip p to
[0.000001, 0.999999] only for logarithms and logit inputs; never clip outcomes.
Every game has equal weight. Reliability diagrams use fixed ten probability bins,
plot the actual mean p against the home-win frequency, and display sample sizes.
Wilson intervals are descriptive marginal intervals with an independence
assumption; they are not cluster-robust. Neither low Brier nor low log loss alone
establishes calibration, market efficiency or profitability.

Timing comparisons use the identical intersection of games eligible at all four
horizons. Available-case scores are separately reported. Sensitivity grids vary
spread thresholds (5/10/20 cents) and maximum bar lags (60/120/300 seconds), with
sample sizes. They are not used to optimize filters on observed outcomes.

## Model selection and holdout
Distinct UTC game dates are divided chronologically: first 60% train, next 20%
validate, final 20% test. A date is never split between cohorts. Primary model
comparison is predeclared at **1 hour before start**.

Candidates:
1. Unmodified market midpoint (always available).
2. L2 logistic recalibration: sigmoid(a+b*logit(p)), C=1, no class weighting.
3. Isotonic regression only with at least 1,000 eligible training games. This
   minimum is a conservative project policy, not a mathematical guarantee.

Training needs at least 50 games and both outcomes. Validation and test each
need at least 20 games. Purge training outcomes not settled strictly before the
earliest validation cutoff. Choose on validation Brier; retain the market unless
another candidate improves by more than 0.002. Prefer the simpler candidate
unless the next improves by another 0.002. These thresholds are declared design
choices. Refit eligible candidates on train+validation, again purging outcomes
unresolved before the earliest test cutoff. Freeze selection before scoring test.
The test table includes predeclared comparators, without choosing again from it.

Report a paired day-block bootstrap (2,000 replicates, seed 20260917) for test
Brier and the candidate-minus-market Brier difference. Resample UTC game dates
and keep all games in each sampled date together. Require at least five dates.
An interval spanning zero does not establish superiority. Recurring-team and
cross-date dependence can remain; the interval does not account for every source
of uncertainty. Fixed chronological splits may cross regular-season/playoff
regimes and must not be called proof of future performance.

## Reproduction and extension
`client.py` owns public GETs, cache, provenance, retry and pacing. `collect.py`
owns league/event discovery and schedule links. `markets.py` defines a typed
outcome-adapter boundary. `analysis.py` owns timestamp-safe snapshots, scoring,
quality audit, chronological model comparison and dashboard exports. The static
`docs/` site works locally and can be published through GitHub Pages.

Adding another league uses the existing league registry. Adding total points,
spreads or player props requires a new market adapter and explicit push/tie/void
rules, outcome-grain tests, and a separate cohort. Do not reuse the two-team
winner outcome rule for those products. New metrics should consume normalized
snapshots and declare their eligible cohort and timestamp requirements.

## Sources
- https://docs.kalshi.com/getting_started/historical_data
- https://docs.kalshi.com/api-reference/market/get-market-candlesticks
- https://docs.kalshi.com/api-reference/milestone/get-milestones
- https://docs.kalshi.com/api-reference/historical/get-historical-markets
- https://scikit-learn.org/stable/modules/calibration.html

No causal claims, net-return estimates, live orders or account access are included.
