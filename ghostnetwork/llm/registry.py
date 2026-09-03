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
SEMANTIC_SYSTEM_PROMPT_VERSION = "chaos-semantic-narrator-system-v1"
OUTPUT_SCHEMA_VERSION = "chaos-narrative-output-v1"
ASSET_OUTPUT_SCHEMA_V1_VERSION = "chaos-narrative-output-assets-v1"
ASSET_OUTPUT_SCHEMA_VERSION = "chaos-narrative-output-assets-v2"
ROLE_OUTPUT_SCHEMA_VERSION = "chaos-narrative-output-role-v1"
SYSTEM_PROMPT_PATH = ROOT / "prompts" / "system" / "chaos-narrator-v1.md"
SEMANTIC_SYSTEM_PROMPT_PATH = ROOT / "prompts" / "system" / "chaos-semantic-narrator-v1.md"
SCHEMA_PATH = ROOT / "schemas" / "chaos-narrative-output-v1.json"
ASSET_SCHEMA_V1_PATH = ROOT / "schemas" / "chaos-narrative-output-assets-v1.json"
ASSET_SCHEMA_PATH = ROOT / "schemas" / "chaos-narrative-output-assets-v2.json"
ROLE_SCHEMA_PATH = ROOT / "schemas" / "chaos-narrative-output-role-v1.json"


@dataclass(frozen=True)
class OllamaTaskPolicy:
    source_scope: str
    task_variant: str
    target_medium: str
    prompt_version: str
    prompt_path: Path
    system_prompt_version: str = SYSTEM_PROMPT_VERSION
    system_prompt_path: Path = SYSTEM_PROMPT_PATH
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
    "machine_progress_changed", "connection_created", "cycle_locked",
    "version_changed", "stabilization_started", "cycle_activated", "signal_sent",
})
GHOSTNETWORK_CYBERNER_VARIANTS = frozenset({
    "part_discovered", "machine_online", "connection_created", "cycle_locked",
    "signal_sent",
})
GHOSTNETWORK_EVENT_PROMPT_VERSION = "ghostnetwork-event-prompt-v6"
GHOSTNETWORK_SIGNAL_PROMPT_VERSION = "ghostsignal-prompt-v6"
GHOSTNETWORK_GOOGLEPLEX_PROMPT_VERSION = "ghostnetwork-googleplex-prompt-v6"


def _policy(
    source, variant, medium, version, relative_path,
    output_schema_version=OUTPUT_SCHEMA_VERSION, semantic_input=False,
):
    return OllamaTaskPolicy(
        source_scope=source,
        task_variant=variant,
        target_medium=medium,
        prompt_version=version,
        prompt_path=ROOT / "prompts" / relative_path,
        system_prompt_version=(
            SEMANTIC_SYSTEM_PROMPT_VERSION if semantic_input else SYSTEM_PROMPT_VERSION
        ),
        system_prompt_path=(
            SEMANTIC_SYSTEM_PROMPT_PATH if semantic_input else SYSTEM_PROMPT_PATH
        ),
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
    policies.append(_policy(
        "blacknet_world", "blacknet_signal_narration", "blacknet",
        "blacknet-signal-prompt-v9", Path("blacknet") / "signal-v9.md",
    ))
    policies.append(_policy(
        "blacknet_world", "googleplex_world_dispatch", "googleplex_news",
        "googleplex-world-hero-prompt-v14", Path("googleplex") / "world-hero-v14.md",
        ASSET_OUTPUT_SCHEMA_VERSION,
    ))
    policies.append(_policy(
        "ghostnetwork", "googleplex_world_dispatch", "googleplex_news",
        GHOSTNETWORK_GOOGLEPLEX_PROMPT_VERSION,
        Path("ghostnetwork") / "googleplex-v6.md",
        ASSET_OUTPUT_SCHEMA_VERSION,
        semantic_input=True,
    ))
    policies.extend((
        _policy(
            "googleplex_editorial", "googleplex_product_promo", "googleplex_news",
            "googleplex-product-promo-v2", Path("googleplex") / "product-promo-v2.md",
            ROLE_OUTPUT_SCHEMA_VERSION,
        ),
        _policy(
            "googleplex_editorial", "googleplex_navigation_promo", "googleplex_news",
            "googleplex-navigation-promo-v1", Path("googleplex") / "navigation-promo-v1.md",
            ROLE_OUTPUT_SCHEMA_VERSION,
        ),
        _policy(
            "googleplex_editorial", "googleplex_capability_card_refresh", "googleplex_news",
            "googleplex-capability-card-v1", Path("googleplex") / "capability-card-v1.md",
            ROLE_OUTPUT_SCHEMA_VERSION,
        ),
    ))
    for variant in sorted(GHOSTNETWORK_BLACKNET_VARIANTS):
        is_signal = variant == "signal_sent"
        policies.append(_policy(
            "ghostnetwork", variant, "blacknet",
            GHOSTNETWORK_SIGNAL_PROMPT_VERSION if is_signal else GHOSTNETWORK_EVENT_PROMPT_VERSION,
            (Path("ghostsignal") / "signal-v6.md") if is_signal
            else (Path("ghostnetwork") / "event-v6.md"),
            semantic_input=True,
        ))
    for variant in sorted(GHOSTNETWORK_CYBERNER_VARIANTS):
        is_signal = variant == "signal_sent"
        policies.append(_policy(
            "ghostnetwork", variant, "cyberner",
            GHOSTNETWORK_SIGNAL_PROMPT_VERSION if is_signal else GHOSTNETWORK_EVENT_PROMPT_VERSION,
            (Path("ghostsignal") / "signal-v6.md") if is_signal
            else (Path("ghostnetwork") / "event-v6.md"),
            semantic_input=True,
        ))
    policies.append(_policy(
        "ghostnetwork", "signal_sent", "radio", GHOSTNETWORK_SIGNAL_PROMPT_VERSION,
        Path("ghostsignal") / "signal-v6.md",
        semantic_input=True,
    ))
    policies.append(_policy(
        "googleplex_app", "owner-analysis", "cyberner",
        "cyberner-agi-2108-prompt-v5", Path("cyberner") / "agi-2108-v5.md",
    ))
    return {(p.source_scope, p.task_variant, p.target_medium): p for p in policies}


OLLAMA_TASK_POLICY_REGISTRY = _build_registry()


def _build_legacy_ghostnetwork_policies(
    event_version, event_path, signal_version, signal_path,
    googleplex_version, googleplex_path, semantic_input=False,
):
    policies = []
    for variant in sorted(GHOSTNETWORK_BLACKNET_VARIANTS):
        is_signal = variant == "signal_sent"
        policies.append(_policy(
            "ghostnetwork", variant, "blacknet",
            signal_version if is_signal else event_version,
            signal_path if is_signal else event_path,
            semantic_input=semantic_input,
        ))
    for variant in sorted(GHOSTNETWORK_CYBERNER_VARIANTS):
        is_signal = variant == "signal_sent"
        policies.append(_policy(
            "ghostnetwork", variant, "cyberner",
            signal_version if is_signal else event_version,
            signal_path if is_signal else event_path,
            semantic_input=semantic_input,
        ))
    policies.extend((
        _policy(
            "ghostnetwork", "signal_sent", "radio", signal_version, signal_path,
            semantic_input=semantic_input,
        ),
        _policy(
            "ghostnetwork", "googleplex_world_dispatch", "googleplex_news",
            googleplex_version, googleplex_path,
            ASSET_OUTPUT_SCHEMA_VERSION,
            semantic_input=semantic_input,
        ),
    ))
    return tuple(policies)


OLLAMA_LEGACY_TASK_POLICIES = (
    _build_legacy_ghostnetwork_policies(
        "ghostnetwork-event-prompt-v1", Path("ghostnetwork") / "event-v1.md",
        "ghostsignal-prompt-v1", Path("ghostsignal") / "signal-v1.md",
        "googleplex-world-hero-prompt-v14", Path("googleplex") / "world-hero-v14.md",
    )
    + _build_legacy_ghostnetwork_policies(
        "ghostnetwork-event-prompt-v2", Path("ghostnetwork") / "event-v2.md",
        "ghostsignal-prompt-v2", Path("ghostsignal") / "signal-v2.md",
        "ghostnetwork-googleplex-prompt-v2", Path("ghostnetwork") / "googleplex-v2.md",
    )
    + _build_legacy_ghostnetwork_policies(
        "ghostnetwork-event-prompt-v3", Path("ghostnetwork") / "event-v3.md",
        "ghostsignal-prompt-v3", Path("ghostsignal") / "signal-v3.md",
        "ghostnetwork-googleplex-prompt-v3", Path("ghostnetwork") / "googleplex-v3.md",
        semantic_input=True,
    )
    + _build_legacy_ghostnetwork_policies(
        "ghostnetwork-event-prompt-v4", Path("ghostnetwork") / "event-v4.md",
        "ghostsignal-prompt-v4", Path("ghostsignal") / "signal-v4.md",
        "ghostnetwork-googleplex-prompt-v4", Path("ghostnetwork") / "googleplex-v4.md",
        semantic_input=True,
    )
    + _build_legacy_ghostnetwork_policies(
        "ghostnetwork-event-prompt-v5", Path("ghostnetwork") / "event-v5.md",
        "ghostsignal-prompt-v5", Path("ghostsignal") / "signal-v5.md",
        "ghostnetwork-googleplex-prompt-v5", Path("ghostnetwork") / "googleplex-v5.md",
        semantic_input=True,
    )
)


def registered_ollama_policies():
    return tuple(OLLAMA_TASK_POLICY_REGISTRY.values()) + OLLAMA_LEGACY_TASK_POLICIES


def resolve_ollama_task_policy(
    source_scope, task_variant, target_medium, prompt_version="",
    output_schema_version="", model_policy_version="",
):
    key = (
        str(source_scope or "").strip(),
        str(task_variant or "").strip(),
        str(target_medium or "").strip(),
    )
    active = OLLAMA_TASK_POLICY_REGISTRY.get(key)
    versions = (
        str(prompt_version or "").strip(),
        str(output_schema_version or "").strip(),
        str(model_policy_version or "").strip(),
    )
    if not any(versions):
        return active
    for policy in (active, *OLLAMA_LEGACY_TASK_POLICIES):
        if policy and policy.eligibility_tuple() == (*key, *versions):
            return policy
    return None


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
        _read_versioned_prompt(
            policy.system_prompt_path, policy.system_prompt_version,
        ),
        _read_versioned_prompt(policy.prompt_path, policy.prompt_version),
    )


def load_output_schema(version=OUTPUT_SCHEMA_VERSION):
    paths = {
        OUTPUT_SCHEMA_VERSION: SCHEMA_PATH,
        ASSET_OUTPUT_SCHEMA_V1_VERSION: ASSET_SCHEMA_V1_PATH,
        ASSET_OUTPUT_SCHEMA_VERSION: ASSET_SCHEMA_PATH,
        ROLE_OUTPUT_SCHEMA_VERSION: ROLE_SCHEMA_PATH,
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
    for policy in registered_ollama_policies():
        identity = policy.eligibility_tuple()
        if identity in seen:
            errors.append(f"duplicate_policy:{identity}")
        seen.add(identity)
        try:
            load_prompt_layers(policy)
            load_output_schema(policy.output_schema_version)
        except ValueError as exc:
            errors.append(str(exc))
    return {
        "ok": not errors,
        "errors": sorted(set(errors)),
        "policies": len(seen),
        "active_policies": len(OLLAMA_TASK_POLICY_REGISTRY),
        "legacy_compatible_policies": len(OLLAMA_LEGACY_TASK_POLICIES),
    }
