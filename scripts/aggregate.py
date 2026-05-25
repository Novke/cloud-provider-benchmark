"""DuckDB aggregator: scan k6/results/**/analysis.json -> jedna queryable tabela.

Phase 2 deliverable. Cita rekurzivno sve `analysis.json` rezultate, parsira metadata
i metrike, ubacuje u DuckDB tabelu `runs`. Idempotentno: ponovni run ne duplira
postojece zapise (kljuc je `source_path`).

Iz orkestrator-tagovanog rezultata (`<ts>__s<session>_n<iter>` ili `_warmup`)
parsira `session_id`, `iteration_number` i `is_warmup`. Iz rezultata bez tih tag-ova
(stari ad-hoc runovi pre Phase 1) markira `session_id='legacy'` i `iteration_number=NULL`.

Dodaje derivane kolone za stratified analizu:
  * `time_of_day_slot`: morning (06-11) | afternoon (12-17) | evening (18-22) | night (23-05)
  * `day_of_week`: 0..6 (Monday=0)
  * `is_weekend`: bool

Usage:
    python scripts/aggregate.py                       # default: ./benchmark.duckdb
    python scripts/aggregate.py --db /path/to.duckdb --results k6/results
    python scripts/aggregate.py --rebuild              # drop+recreate runs table
    python scripts/aggregate.py --print-schema
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import duckdb
except ImportError:
    sys.stderr.write("ERROR: duckdb not installed. Run: pip install -r scripts/requirements.txt\n")
    sys.exit(1)


logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger("aggregate")


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    source_path           VARCHAR PRIMARY KEY,
    imported_at           TIMESTAMP,

    -- Metadata
    provider              VARCHAR,
    arch                  VARCHAR,
    scenario              VARCHAR,
    region                VARCHAR,
    timestamp_utc         TIMESTAMP,
    session_id            VARCHAR,
    session_timestamp     VARCHAR,
    iteration_number      INTEGER,
    is_warmup             BOOLEAN,
    profile               VARCHAR,
    base_url              VARCHAR,
    test_duration_seconds INTEGER,
    k6_version            VARCHAR,

    -- Time-of-day stratification (derivano iz timestamp_utc)
    time_of_day_slot      VARCHAR,
    day_of_week           INTEGER,
    is_weekend            BOOLEAN,

    -- Top-level metrike
    total_requests        BIGINT,
    throughput_rps        DOUBLE,
    error_rate            DOUBLE,
    cold_starts_detected  BIGINT,

    -- TTFB (http_req_waiting) — koristi se u 'mixed', 'high-traffic', 'low-traffic'
    ttfb_avg              DOUBLE,
    ttfb_med              DOUBLE,
    ttfb_p50              DOUBLE,
    ttfb_p90              DOUBLE,
    ttfb_p95              DOUBLE,
    ttfb_p99              DOUBLE,
    ttfb_min              DOUBLE,
    ttfb_max              DOUBLE,

    -- Connection timing breakdown
    conn_connecting_avg   DOUBLE,
    conn_tls_avg          DOUBLE,
    conn_sending_avg      DOUBLE,
    conn_receiving_avg    DOUBLE,

    -- Cold-start scenario specificni
    first_request_avg     DOUBLE,
    first_request_p95     DOUBLE,
    first_request_p99     DOUBLE,
    first_request_max     DOUBLE,
    warm_request_avg      DOUBLE,
    warm_request_p95      DOUBLE,
    warm_request_p99      DOUBLE,

    -- Endpoint-level (mixed scenario) — per-endpoint p95 + avg
    endpoint_quick_avg       DOUBLE,
    endpoint_quick_p95       DOUBLE,
    endpoint_health_avg      DOUBLE,
    endpoint_health_p95      DOUBLE,
    endpoint_compute_avg     DOUBLE,
    endpoint_compute_p95     DOUBLE,
    endpoint_io_native_avg   DOUBLE,
    endpoint_io_native_p95   DOUBLE,
    endpoint_io_neutral_avg  DOUBLE,
    endpoint_io_neutral_p95  DOUBLE,

    -- Raw JSON za fallback (rare/custom queries)
    raw_analysis         JSON
);
"""


def _safe_get(d: Any, *path: str, default=None) -> Any:
    """Bezbedan nested dict accessor."""
    cur = d
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
        if cur is None:
            return default
    return cur


def _time_of_day_slot(ts: datetime) -> str:
    h = ts.hour
    if 6 <= h <= 11:
        return "morning"
    if 12 <= h <= 17:
        return "afternoon"
    if 18 <= h <= 22:
        return "evening"
    return "night"


# Path patterni: posle orchestrator-a izgleda kao:
#   k6/results/<provider>/<arch>/<scenario>/<sessionTs>__s<session>_n<iter>/analysis.json
#   k6/results/<provider>/<arch>/<scenario>/<sessionTs>__s<session>_warmup/analysis.json
# Legacy (bez orchestrator-a):
#   k6/results/<provider>/<arch>/<scenario>/<date>/analysis.json
#   k6/results/<provider>/<scenario>/<date>/analysis.json    (jos stariji, bez ARCH)
SESSION_RUN_RE = re.compile(r"^(?P<ts>[^_]+)__s(?P<session>[^_]+)_n(?P<iter>\d+)$")
SESSION_WARMUP_RE = re.compile(r"^(?P<ts>[^_]+)__s(?P<session>[^_]+)_warmup$")


def parse_run_dir_name(name: str) -> tuple[str | None, str, int | None, bool]:
    """Vraca (session_timestamp, session_id, iteration_number, is_warmup)."""
    m = SESSION_RUN_RE.match(name)
    if m:
        return m.group("ts"), m.group("session"), int(m.group("iter")), False
    m = SESSION_WARMUP_RE.match(name)
    if m:
        return m.group("ts"), m.group("session"), None, True
    return None, "legacy", None, False


def row_from_analysis(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("Skip %s — parse error: %s", path, e)
        return None

    meta = data.get("run_metadata", {})
    cfg = data.get("config", {})
    metrics = data.get("metrics", {})
    endpoints = metrics.get("endpoints", {}) or {}

    # Datum/vreme — biraj iz metadata pa fallback na timestamp parent foldera
    ts_str = meta.get("timestamp")
    if ts_str:
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            ts = None
    else:
        ts = None

    # Path parsing za session/iteration
    run_dir = path.parent.name
    session_ts, session_id, iteration, is_warmup = parse_run_dir_name(run_dir)

    # Fallback na datetime iz foldera ako metadata nema
    if ts is None:
        try:
            # Probaj orchestrator format: 2026-05-25T19-25-04
            ts = datetime.strptime(session_ts or run_dir.split("__")[0], "%Y-%m-%dT%H-%M-%S").replace(tzinfo=timezone.utc)
        except Exception:
            try:
                # Legacy format: 2026-05-25_21-12
                ts = datetime.strptime(run_dir, "%Y-%m-%d_%H-%M").replace(tzinfo=timezone.utc)
            except Exception:
                ts = None

    # Arch fallback — neke legacy putanje nemaju arch direktorijum
    parts = path.parts
    arch = meta.get("architecture") or "unknown"

    return {
        "source_path": str(path).replace("\\", "/"),
        "imported_at": datetime.now(timezone.utc),
        "provider": meta.get("provider") or "unknown",
        "arch": arch,
        "scenario": data.get("scenario") or "unknown",
        "region": meta.get("region") or "unknown",
        "timestamp_utc": ts,
        "session_id": session_id,
        "session_timestamp": session_ts,
        "iteration_number": iteration,
        "is_warmup": is_warmup,
        "profile": meta.get("profile") or cfg.get("profile"),
        "base_url": meta.get("base_url") or cfg.get("baseUrl"),
        "test_duration_seconds": meta.get("test_duration_seconds"),
        "k6_version": meta.get("k6_version"),
        "time_of_day_slot": _time_of_day_slot(ts) if ts else None,
        "day_of_week": ts.weekday() if ts else None,
        "is_weekend": (ts.weekday() >= 5) if ts else None,
        "total_requests": metrics.get("total_requests"),
        "throughput_rps": metrics.get("throughput_rps"),
        "error_rate": metrics.get("error_rate"),
        "cold_starts_detected": metrics.get("cold_starts_detected"),
        "ttfb_avg": _safe_get(metrics, "ttfb", "avg"),
        "ttfb_med": _safe_get(metrics, "ttfb", "med"),
        "ttfb_p50": _safe_get(metrics, "ttfb", "p50"),
        "ttfb_p90": _safe_get(metrics, "ttfb", "p90"),
        "ttfb_p95": _safe_get(metrics, "ttfb", "p95"),
        "ttfb_p99": _safe_get(metrics, "ttfb", "p99"),
        "ttfb_min": _safe_get(metrics, "ttfb", "min"),
        "ttfb_max": _safe_get(metrics, "ttfb", "max"),
        "conn_connecting_avg": _safe_get(metrics, "connection", "connecting", "avg"),
        "conn_tls_avg": _safe_get(metrics, "connection", "tls_handshaking", "avg"),
        "conn_sending_avg": _safe_get(metrics, "connection", "sending", "avg"),
        "conn_receiving_avg": _safe_get(metrics, "connection", "receiving", "avg"),
        "first_request_avg": _safe_get(metrics, "first_request_latency", "avg"),
        "first_request_p95": _safe_get(metrics, "first_request_latency", "p95"),
        "first_request_p99": _safe_get(metrics, "first_request_latency", "p99"),
        "first_request_max": _safe_get(metrics, "first_request_latency", "max"),
        "warm_request_avg": _safe_get(metrics, "warm_request_latency", "avg"),
        "warm_request_p95": _safe_get(metrics, "warm_request_latency", "p95"),
        "warm_request_p99": _safe_get(metrics, "warm_request_latency", "p99"),
        "endpoint_quick_avg": _safe_get(endpoints, "quick", "avg"),
        "endpoint_quick_p95": _safe_get(endpoints, "quick", "p95"),
        "endpoint_health_avg": _safe_get(endpoints, "health", "avg"),
        "endpoint_health_p95": _safe_get(endpoints, "health", "p95"),
        "endpoint_compute_avg": _safe_get(endpoints, "compute", "avg"),
        "endpoint_compute_p95": _safe_get(endpoints, "compute", "p95"),
        "endpoint_io_native_avg": _safe_get(endpoints, "io_native", "avg"),
        "endpoint_io_native_p95": _safe_get(endpoints, "io_native", "p95"),
        "endpoint_io_neutral_avg": _safe_get(endpoints, "io_neutral", "avg"),
        "endpoint_io_neutral_p95": _safe_get(endpoints, "io_neutral", "p95"),
        "raw_analysis": json.dumps(data),
    }


def upsert(conn: duckdb.DuckDBPyConnection, rows: list[dict]) -> int:
    if not rows:
        return 0
    cols = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in cols)
    sql = f"""
        INSERT OR REPLACE INTO runs ({", ".join(cols)})
        VALUES ({placeholders})
    """
    conn.executemany(sql, [[r[c] for c in cols] for r in rows])
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, default=Path("benchmark.duckdb"))
    parser.add_argument("--results", type=Path, default=Path("k6/results"))
    parser.add_argument("--rebuild", action="store_true", help="drop+recreate runs table")
    parser.add_argument("--print-schema", action="store_true", help="print CREATE TABLE and exit")
    args = parser.parse_args(argv)

    if args.print_schema:
        print(SCHEMA)
        return 0

    if not args.results.exists():
        log.error("Results directory not found: %s", args.results)
        return 2

    conn = duckdb.connect(str(args.db))
    if args.rebuild:
        conn.execute("DROP TABLE IF EXISTS runs")
        log.info("Dropped existing runs table")
    conn.execute(SCHEMA)

    analysis_paths = list(args.results.rglob("analysis.json"))
    log.info("Scanning %d analysis.json files under %s", len(analysis_paths), args.results)

    rows = []
    skipped = 0
    for p in analysis_paths:
        row = row_from_analysis(p)
        if row is None:
            skipped += 1
            continue
        rows.append(row)

    inserted = upsert(conn, rows)
    log.info("Inserted/replaced: %d | Skipped: %d", inserted, skipped)

    summary = conn.execute(
        "SELECT provider, arch, scenario, COUNT(*) AS n FROM runs GROUP BY 1,2,3 ORDER BY 1,2,3"
    ).fetchall()
    if summary:
        log.info("Coverage:")
        for row in summary:
            log.info("  %s/%s/%s: N=%d", *row)

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
