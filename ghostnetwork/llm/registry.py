from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path

from .policies.chaos_local_narrator_v1 import (
    MODEL_DIGEST,
    MODEL_NAME,
    MODEL_POLICY_VERSION,
)


ROOT = Path(__file__).resolve().parent
SYSTEM_PROMPT_VERSION = "chaos-narrator-system-v1"
OUTPUT_SCHEMA_VERSION = "chaos-narrative-output-v1"
ASSET_OUTPUT_SCHEMA_V1_VERSION = "chaos-narrative-output-assets-v1"
ASSET_OUTPUT_SCHEMA_VERSION = "chaos-narrative-output-assets-v2"
SYSTEM_PROMPT_PATH = ROOT / "prompts" / "system" / "chaos-narrator-v1.md"
SCHEMA_PATH = ROOT / "schemas" / "chaos-narrative-output-v1.json"
ASSET_SCHEMA_V1_PATH = ROOT / "schemas" / "chaos-narrative-output-assets-v1.json"
ASSET_SCHEMA_PATH = ROOT / "schemas" / "chaos-narrative-output-assets-v2.json"


@dataclass(frozen=True)
class OllamaTaskPolicy:
    source_scope: str
    task_variant: str
    target_medium: str
    prompt_version: str
    prompt_path: Path
    output_schema_version: str = OUTPUT_SCHEMA_VERSION
    model_policy_version: str = MODEL_POLICY_VERSION
    model_name: str = MODEL_NAME
    model_digest: str = MODEL_DIGEST

    def eligibility_tuple(self):
        return (
            self.source_scope,
            self.task_variant,
            self.target_medium,
            self.prompt_version,
            self.output_schema_version,
            self.model_policy_version,
        )


GHOSTNETWORK_BLACKNET_VARIANTS = frozenset({
    "part_discovered", "part_contained", "part_activated", "part_contested",
    "part_conflict_resolved", "part_deactivated", "part_revealed",
    "part_recovered", "part_defended", "machine_online", "machine_offline",
    "machine_progress_changed", "connection_completed", "cycle_locked",
    "version_changed", "stabilization_started", "signal_sent",
})
GHOSTNETWORK_CYBERNER_VARIANTS = frozenset({
    "part_discovered", "machine_online", "connection_completed", "cycle_locked",
    "signal_sent",
})


def _policy(source, variant, medium, version, relative_path, output_schema_version=OUTPUT_SCHEMA_VERSION):
    return OllamaTaskPolicy(
        source_scope=source,
        task_variant=variant,
        target_medium=medium,
        prompt_version=version,
        prompt_path=ROOT / "prompts" / relative_path,
        output_schema_version=output_schema_version,
    )


def _build_registry():
    policies = [_policy(
        "blacknet_world", "world_digest", "blacknet",
        "blacknet-world-prompt-v2", Path("blacknet") / "world-digest-v2.md",
    )]
    policies.append(_policy(
        "blacknet_world", "world_digest", "googleplex_news",
        "googleplex-news-assets-prompt-v8", Path("googleplex") / "news-digest-assets-v8.md",
        ASSET_OUTPUT_SCHEMA_VERSION,
    ))
    for variant in sorted(GHOSTNETWORK_BLACKNET_VARIANTS):
        is_signal = variant == "signal_sent"
        policies.append(_policy(
            "ghostnetwork", variant, "blacknet",
            "ghostsignal-prompt-v1" if is_signal else "ghostnetwork-event-prompt-v1",
            (Path("ghostsignal") / "signal-v1.md") if is_signal
            else (Path("ghostnetwork") / "event-v1.md"),
        ))
    for variant in sorted(GHOSTNETWORK_CYBERNER_VARIANTS):
        is_signal = variant == "signal_sent"
        policies.append(_policy(
            "ghostnetwork", variant, "cyberner",
            "ghostsignal-prompt-v1" if is_signal else "ghostnetwork-event-prompt-v1",
            (Path("ghostsignal") / "signal-v1.md") if is_signal
            else (Path("ghostnetwork") / "event-v1.md"),
        ))
    policies.append(_policy(
        "ghostnetwork", "signal_sent", "radio", "ghostsignal-prompt-v1",
        Path("ghostsignal") / "signal-v1.md",
    ))
    policies.append(_policy(
        "googleplex_app", "owner-analysis", "cyberner",
        "cyberner-agi-2108-prompt-v2", Path("cyberner") / "agi-2108-v2.md",
    ))
    return {(p.source_scope, p.task_variant, p.target_medium): p for p in policies}


OLLAMA_TASK_POLICY_REGISTRY = _build_registry()


def registered_ollama_policies():
    return tuple(OLLAMA_TASK_POLICY_REGISTRY.values())


def resolve_ollama_task_policy(source_scope, task_variant, target_medium):
    return OLLAMA_TASK_POLICY_REGISTRY.get((
        str(source_scope or "").strip(),
        str(task_variant or "").strip(),
        str(target_medium or "").strip(),
    ))


def _read_versioned_prompt(path, expected_version):
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"prompt_missing:{expected_version}") from exc
    first_line = text.splitlines()[0].strip() if text.splitlines() else ""
    if first_line != f"prompt-version: {expected_version}":
        raise ValueError(f"prompt_version_mismatch:{expected_version}")
    content = "\n".join(text.splitlines()[2:]).strip()
    if not content:
        raise ValueError(f"prompt_empty:{expected_version}")
    return content


def load_prompt_layers(policy):
    return (
        _read_versioned_prompt(SYSTEM_PROMPT_PATH, SYSTEM_PROMPT_VERSION),
        _read_versioned_prompt(policy.prompt_path, policy.prompt_version),
    )


def load_output_schema(version=OUTPUT_SCHEMA_VERSION):
    paths = {
        OUTPUT_SCHEMA_VERSION: SCHEMA_PATH,
        ASSET_OUTPUT_SCHEMA_V1_VERSION: ASSET_SCHEMA_V1_PATH,
        ASSET_OUTPUT_SCHEMA_VERSION: ASSET_SCHEMA_PATH,
    }
    if version not in paths:
        raise ValueError(f"schema_version_not_registered:{version}")
    try:
        schema = json.loads(paths[version].read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"schema_missing_or_invalid:{version}") from exc
    if schema.get("$id") != version:
        raise ValueError(f"schema_version_mismatch:{version}")
    return copy.deepcopy(schema)


def verify_prompt_registry():
    errors = []
    seen = set()
    for key, policy in OLLAMA_TASK_POLICY_REGISTRY.items():
        if key in seen:
            errors.append(f"duplicate_policy:{key}")
        seen.add(key)
        try:
            load_prompt_layers(policy)
            load_output_schema(policy.output_schema_version)
        except ValueError as exc:
            errors.append(str(exc))
    return {"ok": not errors, "errors": sorted(set(errors)), "policies": len(seen)}
