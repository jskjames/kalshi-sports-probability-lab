-- One contract / game / horizon. Equal weight per game.
SELECT s.horizon, COUNT(*) AS games,
       AVG((s.p-g.result)*(s.p-g.result)) AS brier_score,
       AVG(s.spread) AS average_spread_dollars
FROM snapshots s JOIN games g USING(event)
GROUP BY s.horizon;

-- Exact common cohort for timing comparisons.
WITH common AS (
  SELECT event FROM snapshots GROUP BY event HAVING COUNT(DISTINCT horizon)=4
)
SELECT s.horizon, COUNT(*) AS games,
       AVG((s.p-g.result)*(s.p-g.result)) AS brier_score
FROM snapshots s JOIN common USING(event) JOIN games g USING(event)
GROUP BY s.horizon;

-- Reliability diagram with per-bin sample sizes; source is home-team contracts.
SELECT CAST(s.p*10 AS INTEGER) AS probability_bucket,
       COUNT(*) AS games, AVG(s.p) AS mean_probability,
       AVG(g.result) AS observed_home_win_rate
FROM snapshots s JOIN games g USING(event)
WHERE s.horizon='1h'
GROUP BY probability_bucket;

-- Data quality must be visible, including excluded snapshots.
SELECT horizon, reason, COUNT(*) AS snapshots
FROM snapshot_audit GROUP BY horizon, reason;

-- This query must return zero.
SELECT COUNT(*) AS future_observations
FROM snapshots WHERE bar_ts > target_ts;
