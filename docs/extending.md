# Extending the research

## A new league

The collection registry defines NBA, MLB, NFL and NHL winner series. Start with a small collection and manually inspect event matching, home/away identifiers and settlement rules before analyzing the new league. Keep league results separate until cross-league pooling has a stated statistical justification.

## A new market type

1. Add an `OutcomeAdapter` implementation in `markets.py`. Define valid contract count, outcome semantics and exclusions for ties, pushes, cancellations and unusual payouts.
2. Add fixture tests using actual observed API structures with non-sensitive data.
3. Extend collection to select the relevant contract and threshold; do not reuse winner home/away pairing blindly.
4. Add dimensions such as `market_type`, player identity and line value to the warehouse. Several contracts from the same game are dependent: group their evaluation and bootstrap units accordingly.
5. Decide the probability target before looking at test results. A continuous scoring model for totals or props is a different model from this winner calibration.

## An independent team-strength model

The current logistic model recalibrates market probabilities. It does not independently forecast basketball from team statistics. A future Elo or team-feature model needs timestamped pregame inputs, an independent schedule source, training confined to past games and comparison against the same market snapshots. Never use final-season rankings or postgame injury annotations as pregame features.

## Prospective validation

Record schedule snapshots and bid/ask quotes as they occur, including retrieval time, market status and available depth. Freeze the research specification and scoring code before accumulating a new test period. Add fees and conservative fill assumptions only in a separately labelled execution study. Probability calibration alone cannot establish a profitable strategy.
