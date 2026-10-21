"""Periodic, unauthenticated NBA market snapshots for the static dashboard.

The collector reads public market data only. It never accepts credentials and it
does not expose order-entry functionality.
"""
import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .client import Client

SERIES = "KXNBAGAME"
SCHEMA_VERSION = 1
RETENTION_DAYS = 7
MAX_SNAPSHOTS = 700
DASHBOARD_SNAPSHOTS = 97


def money(value):
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def midpoint(bid, ask):
    if bid is None or ask is None or not (0 <= bid <= ask <= 1):
        return None
    return round((bid + ask) / 2, 6)


def normalize_market(market):
    bid = money(market.get("yes_bid_dollars", market.get("yes_bid")))
    ask = money(market.get("yes_ask_dollars", market.get("yes_ask")))
    probability = midpoint(bid, ask)
    return {
        "ticker": market.get("ticker", ""),
        "team": market.get("yes_sub_title") or market.get("title", "").removesuffix(" wins"),
        "status": market.get("status", "unknown"),
        "bid": bid,
        "ask": ask,
        "probability": probability,
        "spread": round(ask - bid, 6) if probability is not None else None,
        "bid_size": money(market.get("yes_bid_size_fp", market.get("yes_bid_size"))),
        "ask_size": money(market.get("yes_ask_size_fp", market.get("yes_ask_size"))),
        "last_price": money(market.get("last_price_dollars", market.get("last_price"))),
        "volume": money(market.get("volume_fp", market.get("volume"))) or 0,
        "volume_24h": money(market.get("volume_24h_fp", market.get("volume_24h"))) or 0,
        "open_interest": money(market.get("open_interest_fp", market.get("open_interest"))) or 0,
    }


def normalize_event(event):
    markets = [normalize_market(m) for m in event.get("markets", []) if m.get("ticker")]
    if len(markets) != 2:
        return None
    markets.sort(key=lambda m: (m["team"], m["ticker"]))
    source_markets = event.get("markets", [])
    starts = [m.get("occurrence_datetime") for m in source_markets if m.get("occurrence_datetime")]
    start_at = min(starts) if starts else None
    return {
        "event_ticker": event.get("event_ticker", ""),
        "title": event.get("title") or " vs ".join(m["team"] for m in markets),
        "sub_title": event.get("sub_title", ""),
        "start_at": start_at,
        "markets": markets,
    }


def fetch_open_events(client, max_pages=5):
    events = []
    cursor = None
    seen = set()
    for _ in range(max_pages):
        response = client.get(
            "/events",
            cache_response=False,
            series_ticker=SERIES,
            status="open",
            with_nested_markets="true",
            limit=200,
            cursor=cursor,
        )
        events.extend(response.get("events", []))
        cursor = response.get("cursor")
        if not cursor:
            break
        if cursor in seen:
            raise ValueError("Repeated live-event pagination cursor")
        seen.add(cursor)
    else:
        raise RuntimeError("Live-event pagination cap reached")
    return events


def capture(client, now=None):
    captured = now or datetime.now(timezone.utc)
    if captured.tzinfo is None:
        raise ValueError("Capture timestamp must be timezone-aware")
    normalized = [normalize_event(event) for event in fetch_open_events(client)]
    normalized = sorted(
        (event for event in normalized if event),
        key=lambda event: (event["start_at"] or "9999", event["event_ticker"]),
    )
    return {
        "captured_at": captured.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "series_ticker": SERIES,
        "events": normalized,
    }


def load_history(path):
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "snapshots": []}
    data = json.loads(path.read_text())
    if data.get("schema_version") != SCHEMA_VERSION or not isinstance(data.get("snapshots"), list):
        raise ValueError("Unsupported live snapshot schema")
    return data


def merge_history(history, snapshot, now=None):
    reference = now or datetime.fromisoformat(snapshot["captured_at"].replace("Z", "+00:00"))
    cutoff = reference.astimezone(timezone.utc) - timedelta(days=RETENTION_DAYS)
    by_time = {row["captured_at"]: row for row in history.get("snapshots", [])}
    by_time[snapshot["captured_at"]] = snapshot
    kept = []
    for stamp, row in sorted(by_time.items()):
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if parsed >= cutoff:
            kept.append(row)
    return {"schema_version": SCHEMA_VERSION, "snapshots": kept[-MAX_SNAPSHOTS:]}


def dashboard_payload(history):
    snapshots = history["snapshots"]
    latest = snapshots[-1] if snapshots else None
    compact = []
    for snapshot in snapshots[-DASHBOARD_SNAPSHOTS:]:
        compact.append({
            "captured_at": snapshot["captured_at"],
            "markets": [
                {
                    "ticker": market["ticker"],
                    "probability": market["probability"],
                }
                for event in snapshot["events"]
                for market in event["markets"]
                if market["probability"] is not None
            ],
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": latest["captured_at"] if latest else None,
        "latest": latest,
        "history": compact,
        "retention_days": RETENTION_DAYS,
        "collection_interval_minutes": 15,
    }


def compact_snapshot(snapshot):
    return {
        "captured_at": snapshot["captured_at"],
        "markets": [
            {"ticker": market["ticker"], "probability": market["probability"]}
            for event in snapshot["events"]
            for market in event["markets"]
            if market["probability"] is not None
        ],
    }


def load_dashboard(path):
    if not path or not Path(path).exists():
        return None
    text = Path(path).read_text().strip()
    prefix = "window.LIVE_MARKET_DATA = "
    if not text.startswith(prefix) or not text.endswith(";"):
        raise ValueError("Prior dashboard data has an unexpected format")
    payload = json.loads(text[len(prefix):-1])
    if payload.get("schema_version") != SCHEMA_VERSION or not isinstance(payload.get("history"), list):
        raise ValueError("Prior dashboard data has an unsupported schema")
    return payload


def payload_from_prior(prior, snapshot):
    history = list((prior or {}).get("history", []))
    history.append(compact_snapshot(snapshot))
    by_time = {row["captured_at"]: row for row in history}
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": snapshot["captured_at"],
        "latest": snapshot,
        "history": [by_time[key] for key in sorted(by_time)][-DASHBOARD_SNAPSHOTS:],
        "retention_days": RETENTION_DAYS,
        "collection_interval_minutes": 15,
    }


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text)
    temporary.replace(path)


def run(root, prior_dashboard=None, deploy_only=False):
    root = Path(root)
    history_path = root / "data" / "live" / "snapshots.json"
    client = Client(root / "data" / "cache")
    snapshot = capture(client)
    prior = load_dashboard(prior_dashboard)
    if prior:
        payload = payload_from_prior(prior, snapshot)
    else:
        history = merge_history(load_history(history_path), snapshot)
        payload = dashboard_payload(history)
    if not deploy_only:
        history = merge_history(load_history(history_path), snapshot)
        atomic_write(history_path, json.dumps(history, indent=2, allow_nan=False) + "\n")
    atomic_write(
        root / "docs" / "live-data.js",
        "window.LIVE_MARKET_DATA = " + json.dumps(payload, allow_nan=False) + ";\n",
    )
    markets = sum(len(event["markets"]) for event in snapshot["events"])
    print(json.dumps({"captured_at": snapshot["captured_at"], "events": len(snapshot["events"]), "markets": markets, "dashboard_snapshots": len(payload["history"])}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--prior-dashboard")
    parser.add_argument("--deploy-only", action="store_true")
    args = parser.parse_args()
    run(args.root, args.prior_dashboard, args.deploy_only)
