#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import sqlite3
import sys
import threading
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ghostnetwork.publication import NarrativePublicationService
from ghostnetwork.repository import GhostNetworkRepository


def _bool_env(name, default=False):
    value = str(os.getenv(name, "1" if default else "0")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _float_env(name, default, minimum, maximum):
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = float(default)
    return max(minimum, min(maximum, value))


def _int_env(name, default, minimum, maximum):
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = int(default)
    return max(minimum, min(maximum, value))


def _print(payload):
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True), flush=True)


def is_database_contention(error):
    return isinstance(error, sqlite3.OperationalError) and any(
        marker in str(error).lower()
        for marker in ("database is locked", "database table is locked", "database is busy")
    )


def _runtime():
    repository = GhostNetworkRepository()
    service = NarrativePublicationService(repository=repository)
    return repository, service


def _status(repository, service, enabled, poll_seconds, lease_seconds):
    return {
        "ok": True,
        "enabled": enabled,
        "worker_id": service.worker_id,
        "poll_seconds": poll_seconds,
        "lease_seconds": lease_seconds,
        "queue": repository.narrative_publication_queue_counts(),
        "profile_reads": 0,
        "profile_writes": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Canonical CHAOS narrative publication worker")
    parser.add_argument("command", choices=("status", "run-once", "run"))
    args = parser.parse_args(argv)
    enabled = _bool_env("CHAOS_NARRATIVE_PUBLISHER_ENABLED", False)
    poll_seconds = _float_env("CHAOS_NARRATIVE_PUBLISHER_POLL_SECONDS", 1.5, 0.1, 60.0)
    lease_seconds = _int_env("CHAOS_NARRATIVE_PUBLISHER_LEASE_SECONDS", 60, 10, 600)
    repository, service = _runtime()

    if args.command == "status":
        _print(_status(repository, service, enabled, poll_seconds, lease_seconds))
        return 0
    if args.command == "run-once" and not enabled:
        _print({"ok": False, "error": "narrative_publisher_disabled"})
        return 4
    if args.command == "run-once":
        result = service.process_once(lease_seconds=lease_seconds)
        _print(result)
        return 0 if result.get("ok") else 5

    stop_event = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_args: stop_event.set())
    signal.signal(signal.SIGINT, lambda *_args: stop_event.set())
    if not enabled:
        _print({
            "ok": True,
            "status": "disabled",
            "worker_id": service.worker_id,
        })
        stop_event.wait()
        _print({"ok": True, "status": "stopped", "worker_id": service.worker_id})
        return 0
    _print({"ok": True, "status": "started", "worker_id": service.worker_id})
    while not stop_event.is_set():
        try:
            result = service.process_once(lease_seconds=lease_seconds)
        except sqlite3.OperationalError as exc:
            if not is_database_contention(exc):
                raise
            _print({
                "ok": False,
                "result": "database_contention",
                "error_code": "sqlite_busy",
                "retryable": True,
            })
            stop_event.wait(poll_seconds)
            continue
        if result.get("result") != "idle":
            _print(result)
        stop_event.wait(poll_seconds)
    _print({"ok": True, "status": "stopped", "worker_id": service.worker_id})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
