#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ghostnetwork.ollama_client import ChaosOllamaClient, OllamaClientConfig, OllamaClientError
from ghostnetwork.ollama_policy import (
    assign_ollama_task_policy,
    build_ollama_task_package,
    parse_and_validate_ollama_content,
    resolve_ollama_task_policy,
)
from ghostnetwork.ollama_worker import OllamaNarrativeWorker, OllamaWorkerConfig
from ghostnetwork.repository import GhostNetworkRepository


def _print(payload):
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True), flush=True)


def _worker():
    return OllamaNarrativeWorker(
        repository=GhostNetworkRepository(),
        client=ChaosOllamaClient(OllamaClientConfig.from_env()),
        config=OllamaWorkerConfig.from_env(),
    )


def _dry_run(client):
    task = assign_ollama_task_policy({
        "source_scope": "blacknet_world",
        "task_variant": "world_digest",
        "target_medium": "blacknet",
        "audience_scope": "public",
        "truth_class_policy": "canonical_facts_only",
        "facts": [{
            "fact_id": "dry-run:ollama-runtime",
            "fact_type": "runtime_probe",
            "value": "Transport diagnostyczny jest gotowy.",
        }],
        "allowed_actions": [],
    })
    policy = resolve_ollama_task_policy(
        task["source_scope"], task["task_variant"], task["target_medium"]
    )
    package = build_ollama_task_package(task, policy)
    generation = client.generate(package, policy)
    validation = parse_and_validate_ollama_content(generation.content, package)
    return {
        "ok": validation["status"] == "accepted",
        "validation_status": validation["status"],
        "validation_errors": validation["errors"],
        "request_hash": package["request_hash"],
        "response_hash": generation.raw_response_hash,
        "input_bytes": package["input_bytes"],
        "estimated_input_tokens": package["estimated_input_tokens"],
        "fact_count": package["fact_count"],
        "prompt_eval_count": generation.prompt_eval_count,
        "eval_count": generation.eval_count,
        "persisted": False,
        "claimed": False,
        "published": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Canonical CHAOS Ollama narrative worker")
    parser.add_argument("command", choices=("status", "verify", "dry-run", "run-once", "run"))
    parser.add_argument(
        "--target-medium",
        choices=("blacknet", "googleplex_news", "cyberner"),
        default=None,
        help="Claim one task for controlled medium-specific run-once validation.",
    )
    args = parser.parse_args(argv)
    if args.target_medium and args.command != "run-once":
        parser.error("--target-medium is available only with run-once")
    worker = _worker()
    try:
        if args.command == "status":
            _print(worker.status())
            return 0
        if args.command == "verify":
            result = worker.verify()
            _print(result)
            return 0 if result.get("ok") else 2
        if args.command == "dry-run":
            result = _dry_run(worker.client)
            _print(result)
            return 0 if result.get("ok") else 3
        if args.command == "run-once" and not worker.config.enabled:
            _print({"ok": False, "error": "ollama_worker_disabled"})
            return 4
        if args.command == "run-once":
            result = worker.process_once(target_medium=args.target_medium)
            _print(result)
            return 0 if result.get("result") not in {"invalid_worker_config"} else 5

        stop_event = threading.Event()
        signal.signal(signal.SIGTERM, lambda *_args: stop_event.set())
        signal.signal(signal.SIGINT, lambda *_args: stop_event.set())
        _print({"ok": True, "status": "started", "worker_id": worker.worker_id})
        worker.run(stop_event, on_result=_print)
        _print({"ok": True, "status": "stopped", "worker_id": worker.worker_id})
        return 0
    except OllamaClientError as exc:
        _print({"ok": False, "error": exc.code, "retryable": exc.retryable})
        return 6


if __name__ == "__main__":
    raise SystemExit(main())
