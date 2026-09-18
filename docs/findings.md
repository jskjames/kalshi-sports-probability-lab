# Research findings

## Study population

Collected 500 candidate NBA winner events; linked 499 eligible events to recorded schedules and complementary settlements. The observed window is 2026-02-13 to 2026-06-14 (UTC scheduled game dates).

The frozen extract contains **553,791 minute observations**, **1,877 eligible snapshots**, and **382 games eligible at all four horizons**. These are dependent observations of games, not independent training examples.

## Market probability scores

Lower scores are better. Available-case samples can differ. The matched cohort is the same at every horizon.

| Horizon | Available games | Brier | Matched games | Matched Brier |
|---|---:|---:|---:|---:|
| 24h | 387 | 0.1749 | 382 | 0.1738 |
| 6h | 493 | 0.1686 | 382 | 0.1715 |
| 1h | 498 | 0.1690 | 382 | 0.1705 |
| 5m | 499 | 0.1684 | 382 | 0.1706 |

A forecast of 50% on every game has Brier 0.25. Beating this simple reference does not establish market efficiency or profitable trading. Horizon differences are descriptive; no causal interpretation is intended.

## Frozen one-hour model comparison

Validation selected **market** using the declared 0.002 Brier improvement rule. The eligible sample had 420 training games, 56 validation games and 21 test games across 20 UTC dates. Final refitting used 477 games after resolution-time purging.

| Model | Validation Brier | Test Brier | Test log loss | Test Δ Brier vs market | Paired 95% interval |
|---|---:|---:|---:|---:|---|
| market | 0.2371 | 0.2384 | 0.6659 | 0.0000 | 0.0000 to 0.0000 |
| logistic | 0.2477 | 0.2484 | 0.6865 | 0.0100 | -0.0065 to 0.0282 |

The paired interval does not establish a reliable improvement from logistic recalibration. Do not claim that the model beats the market.

Unavailable candidates: isotonic: Isotonic requires at least 1000 training games by project policy.

## What the project demonstrates

The contribution is an auditable probability study: joining market contracts to schedules, respecting forecast cutoffs, checking outcomes, separating descriptive from held-out evaluation, and making exclusions inspectable. A null or negative recalibration result is a valid finding.

## Remaining uncertainty

- Retrospective milestone start dates; actual tipoff and schedule revision history not independently verified.
- Minute bars provide quote observations, not true last quote-update timestamps or historical depth.
- Capped recent settled cohort, not full-season or random sampling.
- Calibration uses home-team win outcomes. No user P&L, fees, execution, or profitability is estimated.
- Intervals resample UTC dates; dependence across dates or recurring teams may remain.
- Date-blocked validation can cross regular-season/playoff regimes; performance is not guaranteed to generalize.

## Next research decision

Before presenting results as a verified pre-tipoff study, cross-check scheduled starts against an independent historical schedule or actual-start source. For a stronger out-of-sample claim, freeze this specification and collect a new period prospectively. Adding team-strength predictors should be a separately evaluated extension.

## Resume wording after reviewing and understanding the work

- Built a Python/SQL pipeline analyzing 553,791 Kalshi minute observations across 499 NBA games, with timestamp-based quality checks and an interactive probability dashboard.
- Evaluated winner-market calibration across four forecast horizons using Brier score, log loss, chronological holdouts, and paired date-block bootstrap intervals.
