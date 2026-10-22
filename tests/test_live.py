import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from kalshi_lab.live import (
    DASHBOARD_SNAPSHOTS,
    capture,
    dashboard_payload,
    load_dashboard,
    merge_history,
    normalize_event,
    normalize_market,
    payload_from_prior,
    refresh_due,
)


def market(ticker, team, bid="0.40", ask="0.44"):
    return {
        "ticker": ticker,
        "yes_sub_title": team,
        "status": "active",
        "yes_bid_dollars": bid,
        "yes_ask_dollars": ask,
        "yes_bid_size_fp": "12.50",
        "yes_ask_size_fp": "8.25",
        "last_price_dollars": "0.41",
        "volume_fp": "100.50",
        "volume_24h_fp": "25.25",
        "open_interest_fp": "80.00",
        "occurrence_datetime": "2026-10-22T00:00:00Z",
    }


class FakeClient:
    def __init__(self, events):
        self.events = events
        self.calls = []

    def get(self, path, **params):
        self.calls.append((path, params))
        return {"events": self.events, "cursor": ""}


class LiveMarketTests(unittest.TestCase):
    def test_market_normalization_and_quote_quality(self):
        row = normalize_market(market("A", "Boston"))
        self.assertEqual(row["probability"], 0.42)
        self.assertEqual(row["spread"], 0.04)
        self.assertEqual(row["volume"], 100.5)
        crossed = normalize_market(market("B", "New York", bid="0.60", ask="0.50"))
        self.assertIsNone(crossed["probability"])
        self.assertIsNone(crossed["spread"])

    def test_event_requires_exactly_two_contracts(self):
        event = {"event_ticker": "GAME", "title": "Boston vs New York", "markets": [market("A", "Boston"), market("B", "New York")]}
        row = normalize_event(event)
        self.assertEqual(row["start_at"], "2026-10-22T00:00:00Z")
        self.assertEqual([m["team"] for m in row["markets"]], ["Boston", "New York"])
        self.assertIsNone(normalize_event({**event, "markets": event["markets"][:1]}))

    def test_capture_is_public_uncached_and_sorted(self):
        events = [
            {"event_ticker": "LATE", "title": "C vs D", "markets": [market("C", "C"), market("D", "D")]},
            {"event_ticker": "EARLY", "title": "A vs B", "markets": [market("A", "A"), market("B", "B")]},
        ]
        for item in events[0]["markets"]:
            item["occurrence_datetime"] = "2026-10-23T00:00:00Z"
        client = FakeClient(events)
        now = datetime(2026, 10, 21, tzinfo=timezone.utc)
        snapshot = capture(client, now)
        self.assertEqual([event["event_ticker"] for event in snapshot["events"]], ["EARLY", "LATE"])
        path, params = client.calls[0]
        self.assertEqual(path, "/events")
        self.assertFalse(params["cache_response"])
        self.assertEqual(params["status"], "open")
        self.assertEqual(params["series_ticker"], "KXNBAGAME")

    def test_history_retention_deduplication_and_dashboard_bound(self):
        now = datetime(2026, 10, 21, tzinfo=timezone.utc)
        rows = []
        for hours in range(200):
            stamp = now - timedelta(hours=hours)
            rows.append({"captured_at": stamp.isoformat().replace("+00:00", "Z"), "series_ticker": "KXNBAGAME", "events": []})
        current = rows[0]
        history = merge_history({"schema_version": 1, "snapshots": rows}, current, now)
        self.assertEqual(len({row["captured_at"] for row in history["snapshots"]}), len(history["snapshots"]))
        self.assertTrue(all(datetime.fromisoformat(row["captured_at"].replace("Z", "+00:00")) >= now - timedelta(days=7) for row in history["snapshots"]))
        payload = dashboard_payload(history)
        self.assertLessEqual(len(payload["history"]), DASHBOARD_SNAPSHOTS)
        self.assertEqual(payload["latest"]["captured_at"], current["captured_at"])

    def test_deployment_recovers_compact_history_without_evaluating_javascript(self):
        older = {"captured_at": "2026-10-20T23:45:00Z", "markets": [{"ticker": "A", "probability": 0.40}]}
        prior = {"schema_version": 1, "history": [older], "latest": None}
        snapshot = {"captured_at": "2026-10-21T00:00:00Z", "series_ticker": "KXNBAGAME", "events": []}
        payload = payload_from_prior(prior, snapshot)
        self.assertEqual([row["captured_at"] for row in payload["history"]], [older["captured_at"], snapshot["captured_at"]])
        with TemporaryDirectory() as folder:
            path = Path(folder) / "live-data.js"
            import json
            path.write_text("window.LIVE_MARKET_DATA = " + json.dumps(payload) + ";\n")
            self.assertEqual(load_dashboard(path), payload)
            path.write_text("alert('not JSON')")
            with self.assertRaisesRegex(ValueError, "unexpected format"):
                load_dashboard(path)

    def test_scheduled_retry_only_refreshes_stale_dashboard(self):
        now = datetime(2026, 10, 22, 4, 30, tzinfo=timezone.utc)
        recent = {"generated_at": "2026-10-22T04:16:00Z"}
        due = {"generated_at": "2026-10-22T04:15:00Z"}
        self.assertFalse(refresh_due(recent, now=now, min_age_minutes=15))
        self.assertTrue(refresh_due(due, now=now, min_age_minutes=15))
        self.assertTrue(refresh_due(None, now=now, min_age_minutes=15))
        self.assertTrue(refresh_due({"generated_at": "invalid"}, now=now, min_age_minutes=15))

    def test_refresh_due_requires_timezone_aware_clock(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            refresh_due({"generated_at": "2026-10-22T04:00:00Z"}, now=datetime(2026, 10, 22, 4, 30))


if __name__ == "__main__":
    unittest.main()
