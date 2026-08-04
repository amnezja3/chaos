from flask import Flask, render_template, request, session, jsonify, redirect, url_for, Response, g
from markupsafe import Markup
from terminals.commands import interpret_command
import folium
from folium.features import DivIcon
import copy
import os
import json
import re
import math
import ipaddress
import html
import subprocess
import time
import threading
from datetime import datetime, timezone, timedelta
from random import random, choice, randint, sample
import random as random_module
import hashlib
from flask_session import Session
# import redis
from poiFetchClass import POIFetcher
import Haversine
from profileManagment import UserProfileManager, authenticate_user
from database import AppActionReceiptStore, JsonResourceStore, MailStore, TerritoryStore, TerritoryConflictStore, UserStore, VulnerabilityStore, WalletStore, PlayerHackAccessStore, DevBugReportStore, GameStateDeltaBus, PlayerTargetRuntimeStore, PlayerPositionStore, PlayerOperationStore, SystemMessageStore, PlayerInventoryStore, WalletBalanceStore
import requests
from config import (
    APP_VERSION,
    DEFAULT_APP_DISK_USAGE_MB,
    DEFAULT_APP_FILE_SIZE_MB,
    DEFAULT_APP_PRICE_HINT_HC,
    DEFAULT_APP_QUALITY_SCORE,
    DEFAULT_APP_RELIABILITY,
    DEFAULT_CREATOR_POWER,
    DEFAULT_STORAGE_CAPACITY_MB,
    FLASK_SESSION_CONFIG,
    PERF_LOG_ENDPOINTS,
    PERF_LOG_MIN_MS,
    PERF_LOG_MIN_SIZE,
    PLAYER_HACK_ACCESS_MINUTES,
    PLAYER_HACK_COOLDOWN_HOURS,
    VULNERABILITY_MAX_ENABLED_SECURITY,
    VULNERABILITY_REPORT_THRESHOLD,
)
from response_network.foundation import (
    build_response_network_safety_snapshot,
    record_response_map_endpoint_measurement,
)
from response_network.incident_initializer import IncidentInitializer
from response_network.incident_store import IncidentStore
from response_network.detection_candidate_store import DetectionCandidateStore
from response_network.detection_validator import DetectionValidator
from response_network.consequence_executor import ConsequenceExecutor
from response_network.consequence_policy import ConsequencePolicy, CONSEQUENCE_MODE_FULL
from response_network.npc_capsule_factory import public_capsule_payload
from response_network.npc_capsule_store import NPCCapsuleStore
from response_network.operation_risk_meter import update_operation_risk_meter
from response_network.response_dispatcher import ResponseDispatcher
from response_network.territory_context_reader import TerritoryContextReader
from response_network.territory_delta import TerritoryDeltaPublisher
from response_network.warning_store import ResponseWarningStore
from ghostnetwork import GhostNetworkDeltaPublisher, GhostNetworkService, normalize_snapshot_view

app = Flask(__name__)

tag_filters = ["shop", "amenity", "office"]
fetcher = POIFetcher(tag_filters=tag_filters)
resources_store = JsonResourceStore()
mail_store = MailStore()
user_store = UserStore()
territory_store = TerritoryStore()
territory_conflict_store = TerritoryConflictStore()
vulnerability_store = VulnerabilityStore()
wallet_store = WalletStore()
player_hack_access_store = PlayerHackAccessStore()
dev_bug_report_store = DevBugReportStore()
delta_bus = GameStateDeltaBus()
app_action_receipt_store = AppActionReceiptStore()
player_target_runtime_store = PlayerTargetRuntimeStore()
player_position_store = PlayerPositionStore()
player_operation_store = PlayerOperationStore()
system_message_store = SystemMessageStore()
player_inventory_store = PlayerInventoryStore()
wallet_balance_store = WalletBalanceStore()
territory_context_reader = TerritoryContextReader(territory_store, territory_conflict_store)
territory_delta_publisher = TerritoryDeltaPublisher(delta_bus, territory_context_reader)
incident_store = IncidentStore()
incident_initializer = IncidentInitializer(incident_store, territory_context_reader)
npc_capsule_store = NPCCapsuleStore()
response_dispatcher = ResponseDispatcher(npc_capsule_store)
detection_candidate_store = DetectionCandidateStore()
detection_validator = DetectionValidator(
    incident_store,
    npc_capsule_store,
    territory_context_reader,
    detection_candidate_store,
)
consequence_policy = ConsequencePolicy(
    mode=CONSEQUENCE_MODE_FULL,
    feature_flags={
        "operation_cancel": True,
        "tool_confiscation": True,
        "hc_confiscation": True,
        "judgment": True,
        "radio_hooks": True,
        "cyberner_hooks": True,
        "incident_history": True,
    },
)
consequence_executor = ConsequenceExecutor()
response_warning_store = ResponseWarningStore()


def record_wallet_balance_delta(username, balance, reason="", entity_id="wallet", dedupe_key=None):
    try:
        balance = int(balance or 0)
    except (TypeError, ValueError):
        balance = 0
    try:
        wallet_balance_store.set_balance(
            username,
            balance,
            transaction_key=dedupe_key or f"wallet:{username}:{reason or 'balance'}:{balance}",
            reason=reason or "wallet_delta",
        )
    except Exception as exc:
        print(f"[wallet balance store] update failed for {username}: {exc}")
    payload = {
        "balance": balance,
        "currency": "HC",
    }
    if reason:
        payload["reason"] = str(reason)
    try:
        return delta_bus.record_change(
            username,
            "wallet",
            "wallet.balance_changed",
            payload,
            entity_id=entity_id,
            dedupe_key=dedupe_key,
        )
    except Exception as exc:
        print(f"[DELTA] wallet.balance_changed failed for {username}: {exc}")
        return None


def storage_delta_snapshot(profile):
    if not isinstance(profile, dict):
        profile = {}
    return {
        "used": profile.get("storage_used"),
        "capacity": profile.get("storage_capacity"),
        "unit": profile.get("storage_unit", "MB"),
        "soft_limit": profile.get("storage_soft_limit") is not False,
        "over_limit": profile.get("storage_over_limit", False) is True,
    }


def profile_has_storage_entitlements(profile):
    if not isinstance(profile, dict):
        return False
    catalog_builder = globals().get("storage_upgrade_products_catalog")
    storage_product_ids = set()
    if callable(catalog_builder):
        try:
            storage_product_ids = {
                str(item.get("id") or "").strip()
                for item in catalog_builder()
                if isinstance(item, dict) and item.get("id")
            }
        except Exception:
            storage_product_ids = set()
    for key in ("storage_upgrades", "googleplex_products", "product_purchases"):
        items = profile.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id") or item.get("product_id") or "").strip()
            if item.get("storage_capacity_bonus") or item.get("product_type") == "storage_upgrade":
                return True
            if item_id and item_id in storage_product_ids:
                return True
    return False


def normalize_profile_storage_capacity(profile):
    if not isinstance(profile, dict):
        return profile
    has_storage_entitlements = profile_has_storage_entitlements(profile)
    reconcile = globals().get("reconcile_googleplex_storage_products")
    if callable(reconcile) and has_storage_entitlements:
        reconcile(profile)
    capacity = clamp_storage_number(
        profile.get("storage_capacity"),
        default=DEFAULT_STORAGE_CAPACITY_MB,
        minimum=DEFAULT_STORAGE_CAPACITY_MB if has_storage_entitlements else 64,
    )
    profile["storage_capacity"] = capacity
    if profile.get("storage_used") is None:
        profile["storage_used"] = calculate_profile_storage_used(profile)
    profile["storage_unit"] = "MB"
    profile["storage_soft_limit"] = True
    profile["storage_over_limit"] = clamp_storage_number(profile.get("storage_used"), default=0, minimum=0) > capacity
    return profile


def record_storage_delta(username, profile, reason="", previous=None, dedupe_key_prefix=None):
    normalize_profile_storage_capacity(profile)
    try:
        player_inventory_store.write_from_profile(username, profile)
    except Exception as exc:
        print(f"[inventory store] storage mirror failed for {username}: {exc}")
    current = storage_delta_snapshot(profile)
    previous = previous if isinstance(previous, dict) else {}
    reason = str(reason or "storage_changed")
    dedupe_key_prefix = str(dedupe_key_prefix or f"storage:{username}:{reason}:{runtime_file_now()}")
    events = []

    def emit(change_type, entity_id, value_key):
        payload = {
            **current,
            "reason": reason,
        }
        try:
            event = delta_bus.record_change(
                username,
                "storage",
                change_type,
                payload,
                entity_id=entity_id,
                dedupe_key=f"{dedupe_key_prefix}:{value_key}:{current.get(value_key)}",
            )
            events.append(event)
        except Exception as exc:
            print(f"[DELTA] {change_type} failed for {username}: {exc}")

    if previous.get("used") != current.get("used"):
        emit("storage.used_changed", "storage", "used")
    if previous.get("capacity") != current.get("capacity"):
        emit("storage.capacity_changed", "storage", "capacity")
    return events


def apps_delta_snapshot(profile):
    if not isinstance(profile, dict):
        profile = {}
    files = profile.get("files", {})
    if not isinstance(files, dict):
        files = {}
    tools = files.get("tools", [])
    if not isinstance(tools, list):
        tools = []
    return {
        "apps": normalize_app_contracts(profile.get("apps", [])),
        "files": {
            "tools": list(tools),
        },
    }


def record_apps_delta(username, profile, change_type, app=None, app_id=None, reason="", dedupe_key=None, extra=None):
    if change_type not in {
        "apps.app_installed",
        "apps.app_uninstalled",
        "apps.status_changed",
        "apps.cooldown_changed",
    }:
        return None
    try:
        player_inventory_store.write_from_profile(username, profile)
    except Exception as exc:
        print(f"[inventory store] apps mirror failed for {username}: {exc}")

    payload = apps_delta_snapshot(profile)
    if app is not None:
        payload["app"] = normalize_app_contract(app)
    if app_id:
        payload["app_id"] = str(app_id)
    if reason:
        payload["reason"] = str(reason)
    if isinstance(extra, dict):
        payload.update(extra)

    entity_id = str(app_id or payload.get("app_id") or "apps")
    dedupe_key = dedupe_key or f"apps:{change_type}:{username}:{entity_id}:{runtime_file_now()}"
    try:
        return delta_bus.record_change(
            username,
            "apps",
            change_type,
            payload,
            entity_id=entity_id,
            dedupe_key=dedupe_key,
        )
    except Exception as exc:
        print(f"[DELTA] {change_type} failed for {username}: {exc}")
        return None


def mail_delta_thread_key(scope, peer_name):
    scope = str(scope or "group")
    peer_name = "global" if scope == "group" else str(peer_name or "")
    return f"{scope}:{peer_name}"


def mail_delta_payload(username, scope=None, peer_name=None, message=None, reason=""):
    unread_counts = mail_store.unread_counts(username)
    payload = {
        "unread_counts": unread_counts,
    }
    if scope:
        payload["scope"] = str(scope)
    if peer_name:
        payload["peer"] = "global" if scope == "group" else str(peer_name)
    if reason:
        payload["reason"] = str(reason)
    if isinstance(message, dict):
        payload["thread"] = {
            "scope": payload.get("scope") or message.get("scope"),
            "peer": payload.get("peer") or message.get("peer_name") or message.get("peer"),
            "sender": message.get("sender"),
            "subject": message.get("subject"),
            "preview": message.get("body") or message.get("preview") or message.get("subject") or "",
            "created_at": message.get("created_at"),
        }
    return payload


def record_mail_delta(username, change_type, scope=None, peer_name=None, message=None, reason="", dedupe_key=None):
    if change_type not in {"mail.unread_changed", "mail.thread_updated"}:
        return None
    payload = mail_delta_payload(username, scope=scope, peer_name=peer_name, message=message, reason=reason)
    entity_id = mail_delta_thread_key(payload.get("scope") or scope, payload.get("peer") or peer_name)
    dedupe_key = dedupe_key or f"mail:{change_type}:{username}:{entity_id}:{runtime_file_now()}"
    try:
        return delta_bus.record_change(
            username,
            "mail",
            change_type,
            payload,
            entity_id=entity_id,
            dedupe_key=dedupe_key,
        )
    except Exception as exc:
        print(f"[DELTA] {change_type} failed for {username}: {exc}")
        return None


def record_mail_thread_update(username, scope, peer_name, message=None, reason=""):
    message_key = ""
    if isinstance(message, dict):
        message_key = str(message.get("id") or message.get("created_at") or "")
    entity_id = mail_delta_thread_key(scope, peer_name)
    return [
        record_mail_delta(
            username,
            "mail.thread_updated",
            scope=scope,
            peer_name=peer_name,
            message=message,
            reason=reason,
            dedupe_key=f"mail:thread:{username}:{entity_id}:{message_key or runtime_file_now()}",
        ),
        record_mail_delta(
            username,
            "mail.unread_changed",
            scope=scope,
            peer_name=peer_name,
            reason=reason,
            dedupe_key=f"mail:unread:{username}:{entity_id}:{message_key or runtime_file_now()}",
        ),
    ]


def latest_mail_message(username, scope, peer_name):
    try:
        messages = mail_store.list_messages(username, scope, "global" if scope == "group" else peer_name)
    except Exception:
        return None
    if not messages:
        return None
    return messages[-1]


def record_ghost_exchange_delta(username, profile, sales=None, reason=""):
    dashboard = build_ghost_exchange_dashboard_payload(profile)
    events = []
    summary = dashboard.get("summary", {})
    summary_signature = hashlib.sha1(
        json.dumps(summary, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()[:16]
    summary_payload = {
        "summary": summary,
        "recent_transactions": dashboard.get("recent_transactions", [])[:8],
        "reason": reason or "ghost_exchange_changed",
    }
    try:
        events.append(delta_bus.record_change(
            username,
            "ghost_exchange",
            "ghost_exchange.summary_changed",
            summary_payload,
            entity_id="ghost_exchange",
            dedupe_key=f"ghost_exchange:summary:{username}:{summary_signature}",
        ))
    except Exception as exc:
        print(f"[DELTA] ghost_exchange.summary_changed failed for {username}: {exc}")

    for sale in sales or []:
        sale_id = str(sale.get("batch_id") or sale.get("id") or "")
        if not sale_id:
            continue
        try:
            events.append(delta_bus.record_change(
                username,
                "ghost_exchange",
                "ghost_exchange.transaction_added",
                {
                    "transaction": normalize_ghost_exchange_transaction(sale) or sale,
                    "summary": dashboard.get("summary", {}),
                    "recent_transactions": dashboard.get("recent_transactions", [])[:8],
                    "reason": reason or "ghost_exchange_transaction",
                },
                entity_id=sale_id,
                dedupe_key=f"ghost_exchange:transaction:{username}:{sale_id}",
            ))
        except Exception as exc:
            print(f"[DELTA] ghost_exchange.transaction_added failed for {username}: {exc}")
    return events


BLACKNET_WORLD_FACTS_SCHEMA = 1
BLACKNET_WORLD_FACTS_TTL_SECONDS = 10 * 60
BLACKNET_WORLD_FACTS_CACHE_SECONDS = 60
BLACKNET_WORLD_SIGNALS_SCHEMA = 1
BLACKNET_WORLD_SIGNALS_LIMIT = 8
BLACKNET_WORLD_SIGNALS_CACHE_SECONDS = 20
BLACKNET_OLLAMA_OUTBOX_SCHEMA_VERSION = "1.0"
BLACKNET_OLLAMA_OUTBOX_TTL_SECONDS = 60 * 60
BLACKNET_OLLAMA_OUTBOX_MAX_FACTS = 32
BLACKNET_OLLAMA_OUTBOX_MAX_SIGNALS = 16
BLACKNET_OLLAMA_OUTBOX_MAX_BYTES = 96 * 1024
BLACKNET_OLLAMA_OUTBOX_DIR = os.path.join(app.instance_path, "blacknet_ollama_outbox")
BLACKNET_WORLD_FACTS_CACHE = {
    "snapshot": None,
    "cached_at": 0.0,
}
BLACKNET_WORLD_SIGNALS_CACHE = {}
BLACKNET_FACT_IMPORTANCE = {
    "low": 25,
    "medium": 50,
    "high": 75,
    "critical": 100,
}
BLACKNET_SIGNAL_RULES = {
    "operations_active_count": {
        "signal_type": "operation_activity",
        "threshold": 1,
        "channel": "PRZECHWYCONY KANAL",
        "title": "HOTSPOT / OPERACJE",
        "label": "AKTYWNE OPERACJE",
        "value_suffix": "x",
        "stat_template": "{value} OPERACJI W TOKU",
        "cta": "OTWORZ MAPE",
        "cta_action": "open_map",
        "cta_target": "map",
        "tone": "lime",
        "layout": 1,
    },
    "operations_top_type": {
        "signal_type": "regional_activity",
        "threshold": 1,
        "channel": "RUCH OPERACYJNY",
        "title_template": "AKTYWNOSC / {category}",
        "label": "NAJCZESTSZY TYP",
        "value_suffix": "x",
        "stat_template": "{category}",
        "cta": "SPRAWDZ MAPE",
        "cta_action": "open_map",
        "cta_target": "map",
        "tone": "cyan",
        "layout": 4,
    },
    "operation_hotspot_activity": {
        "signal_type": "operation_hotspot_activity",
        "threshold": 1,
        "channel": "PRZECHWYCONY KANAL",
        "title_template": "OPERACJE / {category}",
        "label": "AKTYWNY TARGET",
        "value_suffix": "x",
        "stat_template": "{target_label}",
        "cta": "POKAZ NA MAPIE",
        "cta_action": "focus_map_target",
        "cta_target": "map_target",
        "tone": "lime",
        "layout": 1,
    },
    "operation_hotspot_teleport": {
        "signal_type": "teleport_hotspot",
        "threshold": 1,
        "channel": "PRZECHWYCONY KANAL",
        "title_template": "TELEPORT / {category}",
        "label": "SKOK DO TARGETU",
        "value_suffix": "x",
        "stat_template": "{target_label}",
        "cta": "PRZECHWYC TELEPORT",
        "cta_action": "teleport_to_hotspot",
        "cta_target": "map_target",
        "tone": "lime",
        "layout": 2,
    },
    "target_operation_burst": {
        "signal_type": "target_operation_burst",
        "threshold": 2,
        "channel": "RUCH OPERACYJNY",
        "title_template": "HOTSPOT / {category}",
        "label": "WZROST RUCHU",
        "value_suffix": "x",
        "stat_template": "{target_label}",
        "cta": "POKAZ TARGET",
        "cta_action": "focus_map_target",
        "cta_target": "map_target",
        "tone": "cyan",
        "layout": 5,
    },
    "conflict_target_alert": {
        "signal_type": "conflict_target_alert",
        "threshold": 1,
        "channel": "KONFLIKT TERYTORIALNY",
        "title_template": "CONFLICT / {category}",
        "label": "TARGET SPORNY",
        "value_suffix": "x",
        "stat_template": "{target_label}",
        "cta": "POKAZ KONFLIKT",
        "cta_action": "focus_map_target",
        "cta_target": "map_target",
        "tone": "red",
        "layout": 4,
    },
    "contested_area_alert": {
        "signal_type": "contested_area_alert",
        "threshold": 1,
        "channel": "CONTESTED AREA",
        "title": "CONFLICT / OBSZAR",
        "label": "OBSZAR SPORNY",
        "value_suffix": "x",
        "stat_template": "{value} KONFLIKTOW",
        "cta": "OTWORZ MAPE",
        "cta_action": "open_map",
        "cta_target": "map",
        "tone": "red",
        "layout": 3,
    },
    "market_sales_7d": {
        "signal_type": "market_watch",
        "threshold": 100,
        "channel": "GHOST MARKET WATCH",
        "title": "RYNEK DANYCH / 7D",
        "label": "OBROT HC",
        "value_prefix": "+",
        "value_suffix": " HC",
        "stat_template": "{file_count} PLIKOW / {volume_mb} MB",
        "cta": "OTWORZ GHOST EXCHANGE",
        "cta_action": "open_exchange_market",
        "cta_target": "ghost_exchange",
        "tone": "cyan",
        "layout": 2,
    },
    "market_top_sector_7d": {
        "signal_type": "data_demand",
        "threshold": 100,
        "channel": "GHOST MARKET WATCH",
        "title_template": "{category} / POPYT",
        "label": "TOP SEKTOR",
        "value_prefix": "+",
        "value_suffix": " HC",
        "stat_template": "{volume_mb} MB W RUCHU",
        "cta": "OTWORZ GHOST EXCHANGE",
        "cta_action": "open_exchange_category",
        "cta_target": "ghost_exchange",
        "tone": "cyan",
        "layout": 6,
    },
    "googleplex_catalog_size": {
        "signal_type": "product_opportunity",
        "threshold": 1,
        "channel": "NIEZWERYFIKOWANY DROP",
        "title": "GOOGLEPLEX / KATALOG",
        "label": "CENA",
        "value_suffix": " HC",
        "stat_template": "{products} SYSTEM PRODUCT",
        "cta": "SPRAWDZ W GOOGLEPLEX",
        "cta_action": "open_googleplex_search",
        "cta_target": "googleplex",
        "tone": "amber",
        "layout": 3,
    },
    "googleplex_product_signal": {
        "signal_type": "product_opportunity",
        "threshold": 0,
        "channel": "NIEZWERYFIKOWANY DROP",
        "title_template": "GOOGLEPLEX / {product_name}",
        "label": "CENA",
        "value_suffix": " HC",
        "stat_template": "{temperature} TEMP / {downloads} POBRAN",
        "cta": "SPRAWDZ W GOOGLEPLEX",
        "cta_action": "open_googleplex_search",
        "cta_target": "googleplex",
        "tone": "amber",
        "layout": 3,
    },
    "radio_channels_available": {
        "signal_type": "radio_promotion",
        "threshold": 1,
        "channel": "BLACKNET AUDIO",
        "title": "GHOST HACK RADIO",
        "label": "KANALY ONLINE",
        "value_suffix": "",
        "stat_template": "{tracks_total} TRACKOW W ETERZE",
        "cta": "WLACZ RADIO",
        "cta_action": "play_radio_podcast",
        "cta_target": "radio",
        "tone": "lime",
        "layout": 5,
    },
    "system_messages_24h": {
        "signal_type": "system_incident",
        "threshold": 1,
        "channel": "ALERT SYSTEMOWY",
        "title": "SYSTEM / 24H",
        "label": "ZDARZENIA",
        "value_suffix": "",
        "stat_template": "{value} KOMUNIKATOW",
        "cta": "OTWORZ CYBERNER",
        "cta_action": "open_cyberner_thread",
        "cta_target": "world",
        "tone": "red",
        "layout": 4,
    },
    "incident_hotspot_reaction": {
        "signal_type": "incident_hotspot",
        "threshold": 1,
        "channel": "RESPONSE NETWORK",
        "title_template": "INCYDENT / {target_label}",
        "label": "POZIOM REAKCJI",
        "value_prefix": "L",
        "value_suffix": "",
        "stat_template": "{public_state} / {trend}",
        "cta": "TELEPORT W OKOLICE",
        "cta_action": "teleport_to_hotspot",
        "cta_target": "incident",
        "tone": "red",
        "layout": 2,
    },
}
BLACKNET_ALLOWED_CTA_ACTIONS = {
    "accept_blacknet_job",
    "focus_map_target",
    "none",
    "open_blacknet_detail",
    "open_blacknet_dossier",
    "open_blacknet_report",
    "open_cyberner_thread",
    "open_exchange_category",
    "open_exchange_market",
    "open_googleplex_search",
    "open_map_region",
    "open_operation",
    "open_map",
    "open_ghost_exchange",
    "open_googleplex",
    "open_cyberner",
    "open_radio",
    "play_radio_podcast",
    "show_hotspot",
    "start_operation",
    "teleport_to_hotspot",
}
BLACKNET_HOTSPOTS = {
    "mokotow": {
        "id": "mokotow",
        "label": "Mokotow",
        "lat": 52.1934,
        "lng": 21.0348,
        "risk": "high",
    },
    "praga_polnoc": {
        "id": "praga_polnoc",
        "label": "Praga Polnoc",
        "lat": 52.2544,
        "lng": 21.0347,
        "risk": "high",
    },
    "srodmiescie": {
        "id": "srodmiescie",
        "label": "Srodmiescie",
        "lat": 52.2297,
        "lng": 21.0122,
        "risk": "medium",
    },
    "zoliborz": {
        "id": "zoliborz",
        "label": "Zoliborz",
        "lat": 52.2680,
        "lng": 20.9860,
        "risk": "medium",
    },
}
BLACKNET_MARKET_SECTOR_LABELS = {
    "atm": "Bankomaty",
    "audio": "Audio",
    "camera": "Kamery",
    "credentials": "Dane logowania",
    "device": "Dane urzadzen",
    "financial": "Dane finansowe",
    "gps": "GPS",
    "network": "Sieci",
    "personal": "Dane osobowe",
    "vehicle": "Pojazdy",
}
BLACKNET_OLLAMA_OUTBOX_STATUSES = {
    "created",
    "ready",
    "processing",
    "processed",
    "failed",
    "expired",
    "archived",
}
BLACKNET_OLLAMA_AUTHOR_PERSONAS = [
    {
        "id": "ghost_anchor",
        "name": "Ghost Anchor",
        "tone": "zimny, informacyjny, bez obietnic nagrod",
    },
    {
        "id": "market_shade",
        "name": "Market Shade",
        "tone": "rynkowy, podejrzliwy, syntetyczny",
    },
    {
        "id": "signal_witch",
        "name": "Signal Witch",
        "tone": "mistyczny cyberpunk, ale oparty o fakty",
    },
]
BLACKNET_OLLAMA_FORBIDDEN_CLAIMS = [
    "nie wymyslaj cen, wartosci, targetow ani wspolrzednych",
    "nie tworz nowych CTA ani nowych endpointow",
    "nie obiecuj nagrod, teleportow ani zmian profilu",
    "nie ujawniaj prywatnych danych graczy",
    "nie dodawaj zewnetrznych URL",
]


def blacknet_utc_now():
    return datetime.now(timezone.utc)


def blacknet_iso(dt):
    if not isinstance(dt, datetime):
        dt = blacknet_utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def runtime_snapshot_millis(dt):
    if not isinstance(dt, datetime):
        dt = blacknet_utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.astimezone(timezone.utc).timestamp() * 1000)


def attach_profile_snapshot_meta(profile, started_at, finished_at):
    if not isinstance(profile, dict):
        return profile
    started_ms = runtime_snapshot_millis(started_at)
    finished_ms = runtime_snapshot_millis(finished_at)
    profile_version = (
        profile.get("profile_version")
        or profile.get("state_version")
        or profile.get("position_version")
        or profile.get("updated_at")
        or finished_ms
    )
    snapshot_meta = {
        "scope": "profile",
        "snapshot_started_at": blacknet_iso(started_at),
        "snapshot_finished_at": blacknet_iso(finished_at),
        "snapshot_started_ms": started_ms,
        "snapshot_finished_ms": finished_ms,
        "snapshot_duration_ms": max(0, finished_ms - started_ms),
        "profile_version": profile_version,
        "state_version": profile.get("state_version") or 0,
        "app_version": APP_VERSION,
    }
    profile["snapshot_meta"] = snapshot_meta
    profile["snapshot_started_at"] = snapshot_meta["snapshot_started_at"]
    profile["snapshot_finished_at"] = snapshot_meta["snapshot_finished_at"]
    profile["snapshot_started_ms"] = started_ms
    profile["snapshot_finished_ms"] = finished_ms
    profile["profile_snapshot_version"] = profile_version
    return profile


def blacknet_safe_metadata(metadata):
    if not isinstance(metadata, dict):
        return {}
    safe = {}
    for key, value in metadata.items():
        key = str(key or "").strip()
        if not key:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        elif isinstance(value, list):
            safe[key] = [
                item for item in value[:12]
                if isinstance(item, (str, int, float, bool)) or item is None
            ]
        elif isinstance(value, dict):
            safe[key] = blacknet_safe_metadata(value)
    return safe


def blacknet_profile_projection(profile):
    if not isinstance(profile, dict):
        return {}
    files = profile.get("files", {})
    if not isinstance(files, dict):
        files = {}
    market_files = files.get("market", [])
    if not isinstance(market_files, list):
        market_files = []
    operations = profile.get("operations", [])
    if not isinstance(operations, list):
        operations = []
    market_history = profile.get("market_history", [])
    if not isinstance(market_history, list):
        market_history = []
    system_messages = []
    for message in profile.get("system_messages", []) or []:
        if not isinstance(message, dict):
            continue
        system_messages.append({
            "title": message.get("title"),
            "type": message.get("type"),
            "created_at": message.get("created_at") or message.get("timestamp"),
        })
    return {
        "operations": [item for item in operations if isinstance(item, dict)],
        "market_history": [item for item in market_history if isinstance(item, dict)],
        "files": {
            "market": [item for item in market_files if isinstance(item, dict)],
        },
        "system_messages": system_messages,
    }


def blacknet_fact_id(source_system, fact_type, category="", subject_id="", region_id="global"):
    raw = "|".join(str(item or "") for item in (source_system, fact_type, category, region_id, subject_id))
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"bnf:{source_system}:{fact_type}:{digest}"


def build_blacknet_fact(fact_type, source_system, category, value, now_dt,
                        previous_value=None, change_percent=0, importance="medium",
                        confidence=1.0, region_id="global", subject_id=None,
                        ttl_seconds=BLACKNET_WORLD_FACTS_TTL_SECONDS, metadata=None):
    importance_key = str(importance or "medium").lower()
    fact = {
        "fact_id": blacknet_fact_id(source_system, fact_type, category, subject_id, region_id),
        "fact_type": str(fact_type or "unknown"),
        "category": str(category or "general"),
        "region_id": str(region_id or "global"),
        "subject_id": str(subject_id or category or fact_type or "world"),
        "value": value,
        "previous_value": previous_value,
        "change_percent": int(round(float(change_percent or 0))),
        "importance": BLACKNET_FACT_IMPORTANCE.get(importance_key, BLACKNET_FACT_IMPORTANCE["medium"]),
        "importance_label": importance_key if importance_key in BLACKNET_FACT_IMPORTANCE else "medium",
        "confidence": max(0.0, min(1.0, float(confidence or 0.0))),
        "observed_at": blacknet_iso(now_dt),
        "expires_at": blacknet_iso(now_dt + timedelta(seconds=int(ttl_seconds or BLACKNET_WORLD_FACTS_TTL_SECONDS))),
        "source_system": str(source_system or "unknown"),
        "metadata": blacknet_safe_metadata(metadata),
    }
    return fact


def blacknet_target_coordinates(target):
    if not isinstance(target, dict):
        return None
    try:
        lat = float(target.get("lat"))
        lng = float(target.get("lng", target.get("lon")))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(lat) or not math.isfinite(lng):
        return None
    return {
        "lat": lat,
        "lng": lng,
        "label": f"({lat:.5f}, {lng:.5f})",
    }


def blacknet_operation_target_payload(operation):
    if not isinstance(operation, dict):
        return {}
    target = operation.get("target") if isinstance(operation.get("target"), dict) else {}
    merged = dict(target)
    for source_key, target_key in (
        ("lat", "lat"),
        ("lng", "lng"),
        ("lon", "lon"),
        ("latitude", "lat"),
        ("longitude", "lng"),
        ("target_lat", "lat"),
        ("target_lng", "lng"),
        ("target_lon", "lon"),
        ("target_label", "label"),
        ("label", "label"),
        ("name", "name"),
        ("target_type", "target_type"),
        ("target_mode", "target_mode"),
    ):
        if merged.get(target_key) in (None, "") and operation.get(source_key) not in (None, ""):
            merged[target_key] = operation.get(source_key)
    if merged.get("lng") in (None, "") and merged.get("lon") not in (None, ""):
        merged["lng"] = merged.get("lon")
    return merged


def blacknet_operation_target_snapshot(operation):
    if not isinstance(operation, dict):
        return None
    target = blacknet_operation_target_payload(operation)
    if not target:
        return None
    label = display_target_label(target, fallback_prefix="Target")
    if not label:
        label = "Target"
    coords = blacknet_target_coordinates(target)
    explicit_target_id = str(
        operation.get("target_id")
        or target.get("target_id")
        or target.get("id")
        or ""
    ).strip()
    generated_target_id = build_operation_target_id(target) if coords else ""
    target_id = str(explicit_target_id or generated_target_id or "").strip()
    if not target_id:
        return None
    subject_id = target_id or hashlib.sha1(label.encode("utf-8")).hexdigest()[:12]
    return {
        "target_id": target_id,
        "label": label,
        "coords": coords,
        "subject_id": subject_id,
        "target_type": target.get("target_type") or target.get("source_type") or operation.get("target_type") or "",
        "target_mode": target.get("target_mode") or operation.get("target_mode") or "",
    }


def blacknet_conflict_target_snapshot(conflict, target):
    if not isinstance(conflict, dict) or not isinstance(target, dict):
        return None
    target = blacknet_operation_target_payload({
        **conflict,
        "target": target,
    })
    label = display_target_label(target, fallback_prefix="Conflict")
    if not label:
        label = str(conflict.get("conflict_key") or conflict.get("id") or "Conflict")
    coords = blacknet_target_coordinates(target)
    explicit_target_id = str(target.get("target_id") or target.get("id") or "").strip()
    generated_target_id = build_operation_target_id(target) if coords else ""
    target_id = str(explicit_target_id or generated_target_id or "").strip()
    if not target_id:
        return None
    subject_id = target_id or hashlib.sha1(label.encode("utf-8")).hexdigest()[:12]
    participants = conflict.get("participant_usernames") or conflict.get("participants") or []
    if not isinstance(participants, list):
        participants = []
    return {
        "target_id": target_id,
        "label": label,
        "coords": coords,
        "subject_id": subject_id,
        "target_type": target.get("target_type") or target.get("source_type") or "",
        "status": target.get("status") or conflict.get("status") or "",
        "conflict_id": conflict.get("id") or "",
        "stable_conflict_id": conflict.get("conflict_id") or "",
        "conflict_key": conflict.get("conflict_key") or conflict.get("id") or "",
        "participants": [str(item) for item in participants[:8] if item],
    }


def blacknet_incident_trend(public_incident):
    incident = public_incident if isinstance(public_incident, dict) else {}
    status = str(incident.get("status") or "active").strip().lower()
    level = int(incident.get("level") or 0)
    if status == "escalated" or level >= 4:
        return "rosnie"
    if status == "cooling":
        return "spada"
    if status == "candidate":
        return "wykryto"
    return "stabilny"


def blacknet_safe_incident_entry_point(public_incident):
    incident = public_incident if isinstance(public_incident, dict) else {}
    center = incident.get("center") if isinstance(incident.get("center"), dict) else {}
    try:
        lat = float(center.get("lat"))
        lng = float(center.get("lng"))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(lat) or not math.isfinite(lng):
        return None

    radius_m = max(0, int(incident.get("search_radius_m") or 0))
    distance_m = max(220.0, float(radius_m) + 160.0, float(radius_m) * 1.35)
    seed = str(incident.get("incident_id") or "incident")
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    bearing = (int(digest[:8], 16) % 360) * math.pi / 180.0

    meters_per_degree_lat = 111_320.0
    cos_lat = max(0.2, abs(math.cos(math.radians(lat))))
    entry_lat = lat + (math.cos(bearing) * distance_m / meters_per_degree_lat)
    entry_lng = lng + (math.sin(bearing) * distance_m / (meters_per_degree_lat * cos_lat))
    entry_lat = max(-89.999, min(89.999, entry_lat))
    entry_lng = ((entry_lng + 180.0) % 360.0) - 180.0
    return {
        "lat": round(entry_lat, 6),
        "lng": round(entry_lng, 6),
        "center_lat": round(lat, 6),
        "center_lng": round(lng, 6),
        "distance_m": int(round(distance_m)),
        "label": f"{entry_lat:.5f}, {entry_lng:.5f}",
        "center_label": f"{lat:.5f}, {lng:.5f}",
    }


def build_blacknet_operations_facts(profiles, now_dt):
    active_count = 0
    completed_count = 0
    failed_count = 0
    operation_types = {}
    target_labels = {}
    target_activity = {}
    output_mb = 0
    now_ts = now_dt.timestamp() if isinstance(now_dt, datetime) else None

    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        operations = profile.get("operations") or []
        for operation in operations:
            if not isinstance(operation, dict):
                continue
            op_type = str(operation.get("operation_type") or operation.get("map_action_id") or "unknown")
            operation_types[op_type] = operation_types.get(op_type, 0) + 1
            target = operation.get("target") if isinstance(operation.get("target"), dict) else {}
            label = str(target.get("label") or target.get("name") or operation.get("target_id") or "").strip()
            if label:
                target_labels[label] = target_labels.get(label, 0) + 1
            output_mb += operation_output_size_mb(operation)
            status = str(operation.get("status") or "").lower()
            if operation_is_active(operation, now_ts=now_ts):
                active_count += 1
                target_snapshot = blacknet_operation_target_snapshot(operation)
                if target_snapshot:
                    key = target_snapshot["subject_id"]
                    bucket = target_activity.setdefault(key, {
                        "count": 0,
                        "target": target_snapshot,
                        "operation_types": {},
                        "owners": set(),
                        "operation_ids": [],
                    })
                    bucket["count"] += 1
                    bucket["operation_types"][op_type] = bucket["operation_types"].get(op_type, 0) + 1
                    owner = str(operation.get("owner_username") or "").strip()
                    if owner:
                        bucket["owners"].add(owner)
                    operation_id = str(operation.get("operation_id") or "").strip()
                    if operation_id:
                        bucket["operation_ids"].append(operation_id)
            elif status in {"completed", "done", "success"}:
                completed_count += 1
            elif status in {"failed", "timeout", "cancelled", "canceled"}:
                failed_count += 1

    facts = [
        build_blacknet_fact(
            "operations_active_count",
            "operations",
            "operations",
            active_count,
            now_dt,
            importance="high" if active_count >= 10 else "medium",
            confidence=0.95,
            metadata={
                "completed_count": completed_count,
                "failed_count": failed_count,
                "output_mb": output_mb,
                "top_operation_types": sorted(operation_types.items(), key=lambda item: item[1], reverse=True)[:5],
                "top_targets": sorted(target_labels.items(), key=lambda item: item[1], reverse=True)[:5],
            },
        )
    ]
    if operation_types:
        top_type, top_count = sorted(operation_types.items(), key=lambda item: item[1], reverse=True)[0]
        facts.append(build_blacknet_fact(
            "operations_top_type",
            "operations",
            top_type,
            top_count,
            now_dt,
            importance="medium",
            confidence=0.9,
            subject_id=top_type,
            metadata={"operation_type": top_type},
        ))
    if target_activity:
        top_target = sorted(
            target_activity.values(),
            key=lambda item: (
                -int(item.get("count") or 0),
                str((item.get("target") or {}).get("label") or ""),
            ),
        )[0]
        target = top_target.get("target") or {}
        coords = target.get("coords") if isinstance(target.get("coords"), dict) else None
        operation_type_counts = top_target.get("operation_types") or {}
        top_operation_type = ""
        if operation_type_counts:
            top_operation_type = sorted(operation_type_counts.items(), key=lambda item: item[1], reverse=True)[0][0]
        facts.append(build_blacknet_fact(
            "operation_hotspot_activity",
            "operations",
            target.get("label") or "target",
            top_target.get("count") or 0,
            now_dt,
            importance="high" if int(top_target.get("count") or 0) >= 3 else "medium",
            confidence=0.9,
            region_id=target.get("subject_id") or "target",
            subject_id=target.get("subject_id") or target.get("target_id") or target.get("label"),
            metadata={
                "target_id": target.get("target_id"),
                "target_label": target.get("label"),
                "target_type": target.get("target_type"),
                "target_mode": target.get("target_mode"),
                "lat": coords.get("lat") if coords else None,
                "lng": coords.get("lng") if coords else None,
                "coordinates": coords.get("label") if coords else "",
                "operation_count": top_target.get("count") or 0,
                "operation_type": top_operation_type,
                "operation_ids": top_target.get("operation_ids", [])[:8],
                "owners_count": len(top_target.get("owners") or []),
                "cta_target_id": target.get("target_id") or target.get("subject_id"),
            },
        ))
        if coords:
            facts.append(build_blacknet_fact(
                "operation_hotspot_teleport",
                "operations",
                target.get("label") or "target",
                top_target.get("count") or 0,
                now_dt,
                importance="medium",
                confidence=0.84,
                region_id=target.get("subject_id") or "target",
                subject_id=target.get("subject_id") or target.get("target_id") or target.get("label"),
                metadata={
                    "target_id": target.get("target_id"),
                    "target_label": target.get("label"),
                    "target_type": target.get("target_type"),
                    "target_mode": target.get("target_mode"),
                    "lat": coords.get("lat"),
                    "lng": coords.get("lng"),
                    "coordinates": coords.get("label"),
                    "operation_count": top_target.get("count") or 0,
                    "operation_type": top_operation_type,
                    "operation_ids": top_target.get("operation_ids", [])[:8],
                    "owners_count": len(top_target.get("owners") or []),
                    "cta_target_id": target.get("target_id") or target.get("subject_id"),
                },
            ))
        if int(top_target.get("count") or 0) >= 2:
            facts.append(build_blacknet_fact(
                "target_operation_burst",
                "operations",
                target.get("label") or "target",
                top_target.get("count") or 0,
                now_dt,
                importance="high" if int(top_target.get("count") or 0) >= 4 else "medium",
                confidence=0.88,
                region_id=target.get("subject_id") or "target",
                subject_id=target.get("subject_id") or target.get("target_id") or target.get("label"),
                metadata={
                    "target_id": target.get("target_id"),
                    "target_label": target.get("label"),
                    "target_type": target.get("target_type"),
                    "target_mode": target.get("target_mode"),
                    "lat": coords.get("lat") if coords else None,
                    "lng": coords.get("lng") if coords else None,
                    "coordinates": coords.get("label") if coords else "",
                    "operation_count": top_target.get("count") or 0,
                    "operation_type": top_operation_type,
                    "operation_ids": top_target.get("operation_ids", [])[:8],
                    "owners_count": len(top_target.get("owners") or []),
                    "cta_target_id": target.get("target_id") or target.get("subject_id"),
                },
            ))
    return facts


def build_blacknet_ghost_exchange_facts(profiles, now_dt):
    sector_hc = {}
    sector_volume = {}
    sector_files = {}
    sector_transactions = {}
    total_hc = 0
    total_files = 0
    total_volume = 0
    transaction_count = 0
    cutoff_ts = (now_dt - timedelta(days=7)).timestamp()

    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        for transaction in collect_ghost_exchange_transactions(profile):
            sold_ts = parse_operation_timestamp(transaction.get("sold_at")) or 0
            if sold_ts and sold_ts < cutoff_ts:
                continue
            sector = str(transaction.get("market_sector") or "unknown")
            price = int(transaction.get("price") or 0)
            volume = clamp_storage_number(transaction.get("volume_mb"), default=0, minimum=0)
            files = int(transaction.get("file_count") or 0)
            sector_hc[sector] = sector_hc.get(sector, 0) + price
            sector_volume[sector] = sector_volume.get(sector, 0) + volume
            sector_files[sector] = sector_files.get(sector, 0) + files
            sector_transactions[sector] = sector_transactions.get(sector, 0) + 1
            total_hc += price
            total_volume += volume
            total_files += files
            transaction_count += 1

    facts = [
        build_blacknet_fact(
            "market_sales_7d",
            "ghost_exchange",
            "market",
            total_hc,
            now_dt,
            importance="high" if total_hc >= 1000 else "medium",
            confidence=0.9,
            metadata={
                "transaction_count": transaction_count,
                "file_count": total_files,
                "volume_mb": total_volume,
                "sector_hc": sector_hc,
                "sector_volume_mb": sector_volume,
                "cta_target_id": "market",
            },
        )
    ]
    if sector_hc:
        known_sectors = set(MARKET_SECTOR_THRESHOLDS.keys())
        ranked_sectors = [
            item for item in sorted(sector_hc.items(), key=lambda item: item[1], reverse=True)
            if item[0] in known_sectors
        ]
        if ranked_sectors:
            top_sector, top_hc = ranked_sectors[0]
            transaction_total = max(1, int(sector_transactions.get(top_sector) or 0))
            facts.append(build_blacknet_fact(
                "market_top_sector_7d",
                "ghost_exchange",
                top_sector,
                top_hc,
                now_dt,
                importance="high" if top_hc >= 1000 else "medium",
                confidence=0.9,
                subject_id=top_sector,
                metadata={
                    "sector": top_sector,
                    "sector_id": top_sector,
                    "sector_key": top_sector,
                    "sector_label": BLACKNET_MARKET_SECTOR_LABELS.get(top_sector, top_sector),
                    "market_category": top_sector,
                    "volume_mb": sector_volume.get(top_sector, 0),
                    "sold_today": sector_files.get(top_sector, 0),
                    "average_price": int(round(top_hc / transaction_total)),
                    "cta_target_id": top_sector,
                    "cta_query": top_sector,
                },
            ))
    return facts


def blacknet_googleplex_item_temperature(item, now_dt):
    item = item if isinstance(item, dict) else {}
    try:
        price = int(item.get("price") or 0)
    except (TypeError, ValueError):
        price = 0
    try:
        downloads = int(item.get("downloads") or 0)
    except (TypeError, ValueError):
        downloads = 0
    product_type = str(item.get("product_type") or "").strip()
    item_type = str(item.get("type") or "").strip()
    freshness_score = 8
    timestamp = (
        item.get("published_at")
        or item.get("updated_at")
        or item.get("created_at")
        or item.get("generated_at")
    )
    parsed_ts = parse_operation_timestamp(timestamp)
    if parsed_ts:
        age_seconds = max(0, int(now_dt.timestamp()) - int(parsed_ts))
        if age_seconds <= 24 * 3600:
            freshness_score = 30
        elif age_seconds <= 7 * 24 * 3600:
            freshness_score = 20
        elif age_seconds <= 30 * 24 * 3600:
            freshness_score = 12
    elif product_type or item_type in {"pro-system-tool", "system_lab"}:
        freshness_score = 18

    class_score = 10
    if product_type == "travel_ticket":
        class_score = 26
    elif product_type:
        class_score = 22
    elif item_type in {"pro-system-tool", "system_lab"}:
        class_score = 24

    return max(1, min(100, class_score + freshness_score + min(28, downloads * 2) + min(20, price // 500)))


def blacknet_googleplex_importance(temperature):
    try:
        temperature = int(temperature or 0)
    except (TypeError, ValueError):
        temperature = 0
    if temperature >= 70:
        return "high"
    if temperature >= 35:
        return "medium"
    return "low"


def build_blacknet_googleplex_facts(now_dt):
    catalog = get_app_catalog()
    facts = []
    for item in catalog:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip()
        item_name = str(item.get("name") or item_id).strip()
        if not item_id or not item_name:
            continue
        if item.get("published") is False:
            continue
        product_type = str(item.get("product_type") or "").strip()
        item_type = str(item.get("type") or "").strip()
        category = str(item.get("category") or product_type or item_type or "googleplex").strip()
        try:
            price = int(item.get("price") or 0)
        except (TypeError, ValueError):
            price = 0
        try:
            downloads = int(item.get("downloads") or 0)
        except (TypeError, ValueError):
            downloads = 0
        temperature = blacknet_googleplex_item_temperature(item, now_dt)
        product_kind = product_type or item_type or "app"
        facts.append(build_blacknet_fact(
            "googleplex_product_signal",
            "googleplex",
            category,
            price,
            now_dt,
            importance=blacknet_googleplex_importance(temperature),
            confidence=0.95,
            subject_id=item_id,
            metadata={
                "product_id": item_id,
                "product_name": item_name,
                "product_type": product_kind,
                "price": price,
                "downloads": downloads,
                "temperature": temperature,
                "category": category,
                "travel_city": item.get("travel_city") or "",
                "cta_target_id": item_id,
                "cta_query": item_name,
            },
        ))
    return facts


def build_blacknet_radio_facts(now_dt):
    radio_root = os.path.abspath(os.path.join(app.static_folder, "mp3", "radio", "channel"))
    channels = []
    tracks_total = 0
    try:
        channel_ids = sorted(
            name for name in os.listdir(radio_root)
            if re.match(r"^[a-zA-Z0-9_\-]+$", name)
            and os.path.isdir(os.path.join(radio_root, name))
        )
    except OSError:
        channel_ids = []
    for channel_id in channel_ids:
        meta_path = os.path.join(radio_root, channel_id, "meta.channel")
        if not os.path.isfile(meta_path):
            continue
        try:
            with open(meta_path, "r", encoding="utf-8") as handle:
                channel = json.load(handle)
            excluded = {
                str(item or "").strip()
                for item in (channel.get("exclude") if isinstance(channel.get("exclude"), list) else [])
            }
            tracks = sorted([
                filename for filename in os.listdir(os.path.join(radio_root, channel_id))
                if filename.lower().endswith(".mp3") and filename not in excluded
            ])
            track_count = len(tracks)
        except (OSError, json.JSONDecodeError):
            continue
        channels.append({
            "id": channel.get("id") or channel_id,
            "path_id": channel_id,
            "slug": channel.get("slug") or channel_id,
            "name": channel.get("name") or channel_id,
            "source": channel.get("source") or "unknown",
            "tracks": track_count,
            "track_files": tracks[:24],
        })
        tracks_total += track_count
    preferred_channel = next(
        (item for item in channels if str(item.get("source") or "").lower().startswith("blacknet")),
        None,
    ) or (channels[0] if channels else {})
    preferred_tracks = preferred_channel.get("track_files") if isinstance(preferred_channel.get("track_files"), list) else []
    track_count = len(preferred_tracks)
    track_index = 0
    if track_count:
        track_index = int(now_dt.strftime("%j%H")) % track_count
    track_file = preferred_tracks[track_index] if track_count else ""
    track_title = re.sub(r"\.mp3$", "", track_file, flags=re.IGNORECASE).replace("_", " ").replace("-", " ").strip()
    return [
        build_blacknet_fact(
            "radio_channels_available",
            "radio",
            track_title or "radio",
            track_index + 1 if track_count else 0,
            now_dt,
            importance="low" if channels else "medium",
            confidence=0.9,
            metadata={
                "channel_ids": [str(item.get("id") or "") for item in channels[:10] if item.get("id")],
                "tracks_total": tracks_total,
                "channel_id": preferred_channel.get("path_id") or preferred_channel.get("id") or "",
                "channel_path_id": preferred_channel.get("path_id") or preferred_channel.get("id") or "",
                "channel_meta_id": preferred_channel.get("id") or "",
                "channel_name": preferred_channel.get("name") or "",
                "track_file": track_file,
                "track_title": track_title,
                "track_index": track_index + 1 if track_count else 0,
                "track_count": track_count,
                "cta_target_id": preferred_channel.get("path_id") or preferred_channel.get("id") or "",
                "cta_query": track_title or preferred_channel.get("name") or preferred_channel.get("id") or "",
            },
        )
    ]


def build_blacknet_system_facts(profiles, now_dt):
    total_messages = 0
    title_counts = {}
    cutoff_ts = (now_dt - timedelta(days=1)).timestamp()
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        for message in profile.get("system_messages", []) or []:
            if not isinstance(message, dict):
                continue
            ts = parse_operation_timestamp(message.get("created_at") or message.get("timestamp")) or now_dt.timestamp()
            if ts < cutoff_ts:
                continue
            total_messages += 1
            title = str(message.get("title") or message.get("type") or "System").strip()[:60]
            title_counts[title] = title_counts.get(title, 0) + 1
    return [
        build_blacknet_fact(
            "system_messages_24h",
            "system",
            "system",
            total_messages,
            now_dt,
            importance="medium" if total_messages else "low",
            confidence=0.8,
            metadata={
                "top_titles": sorted(title_counts.items(), key=lambda item: item[1], reverse=True)[:5],
                "thread_scope": "group",
                "thread_peer": "global",
                "thread_channel": "world",
                "thread_title": "WORLD",
                "cta_target_id": "global",
                "cta_query": "WORLD",
            },
        )
    ]


def build_blacknet_conflict_activity_facts(now_dt):
    try:
        conflicts = territory_conflict_store.list_active()
        if not isinstance(conflicts, list):
            conflicts = []
    except Exception:
        raise

    active_conflicts = [item for item in conflicts if isinstance(item, dict)]
    target_activity = {}
    target_count = sum(
        len([target for target in (conflict.get("targets") or []) if isinstance(target, dict)])
        for conflict in active_conflicts
    )
    for conflict in active_conflicts:
        targets = conflict.get("targets") or []
        if not isinstance(targets, list):
            continue
        for target in targets:
            if not isinstance(target, dict):
                continue
            target_snapshot = blacknet_conflict_target_snapshot(conflict, target)
            if not target_snapshot:
                continue
            key = target_snapshot["subject_id"]
            bucket = target_activity.setdefault(key, {
                "count": 0,
                "target": target_snapshot,
                "conflict_keys": set(),
                "statuses": {},
                "participants": set(),
            })
            bucket["count"] += 1
            conflict_key = str(target_snapshot.get("conflict_key") or "").strip()
            if conflict_key:
                bucket["conflict_keys"].add(conflict_key)
            status = str(target_snapshot.get("status") or "active").strip() or "active"
            bucket["statuses"][status] = bucket["statuses"].get(status, 0) + 1
            for participant in target_snapshot.get("participants") or []:
                bucket["participants"].add(participant)
    if not active_conflicts:
        return []
    facts = [
        build_blacknet_fact(
            "conflicts_active_count",
            "conflicts",
            "conflicts",
            len(active_conflicts),
            now_dt,
            importance="high",
            confidence=0.85,
            metadata={
                "conflict_count": len(active_conflicts),
                "target_count": target_count,
                "conflict_keys": [
                    str(conflict.get("conflict_key") or conflict.get("id") or "")
                    for conflict in active_conflicts[:8]
                ],
            },
        )
    ]
    if target_activity:
        top_target = sorted(
            target_activity.values(),
            key=lambda item: (
                -int(item.get("count") or 0),
                str((item.get("target") or {}).get("label") or ""),
            ),
        )[0]
        target = top_target.get("target") or {}
        coords = target.get("coords") if isinstance(target.get("coords"), dict) else None
        status_counts = top_target.get("statuses") or {}
        top_status = ""
        if status_counts:
            top_status = sorted(status_counts.items(), key=lambda item: item[1], reverse=True)[0][0]
        facts.append(build_blacknet_fact(
            "conflict_target_alert",
            "conflicts",
            target.get("label") or "target",
            top_target.get("count") or 0,
            now_dt,
            importance="critical" if int(top_target.get("count") or 0) >= 3 else "high",
            confidence=0.86,
            region_id=target.get("subject_id") or "conflict",
            subject_id=target.get("subject_id") or target.get("target_id") or target.get("label"),
            metadata={
                "target_id": target.get("target_id"),
                "target_label": target.get("label"),
                "target_type": target.get("target_type"),
                "lat": coords.get("lat") if coords else None,
                "lng": coords.get("lng") if coords else None,
                "coordinates": coords.get("label") if coords else "",
                "conflict_target_count": top_target.get("count") or 0,
                "conflict_keys": sorted(top_target.get("conflict_keys") or [])[:8],
                "participants": sorted(top_target.get("participants") or [])[:8],
                "participants_count": len(top_target.get("participants") or []),
                "status": top_status,
                "cta_target_id": target.get("target_id") or target.get("subject_id"),
            },
        ))
    else:
        facts.append(build_blacknet_fact(
            "contested_area_alert",
            "conflicts",
            "conflicts",
            len(active_conflicts),
            now_dt,
            importance="high",
            confidence=0.78,
            subject_id="conflicts",
            metadata={
                "conflict_count": len(active_conflicts),
                "target_count": target_count,
                "conflict_keys": [
                    str(conflict.get("conflict_key") or conflict.get("id") or "")
                    for conflict in active_conflicts[:8]
                ],
            },
        ))
    return facts


def build_blacknet_incident_facts(now_dt):
    public_incidents = incident_store.list_public()
    if not isinstance(public_incidents, list):
        public_incidents = []
    facts = []
    for incident in public_incidents:
        if not isinstance(incident, dict):
            continue
        incident_id = str(incident.get("incident_id") or "").strip()
        if not incident_id:
            continue
        status = str(incident.get("status") or "active").strip().lower()
        if status in {"resolved", "cancelled", "archived"}:
            continue
        entry = blacknet_safe_incident_entry_point(incident)
        if not entry:
            continue
        level = max(1, int(incident.get("level") or 1))
        radius_m = max(0, int(incident.get("search_radius_m") or 0))
        trend = blacknet_incident_trend(incident)
        location_label = f"INCYDENT {entry['center_label']}"
        expires_at = parse_operation_timestamp(incident.get("expires_at"))
        ttl_seconds = BLACKNET_WORLD_FACTS_TTL_SECONDS
        if expires_at:
            now_ts = now_dt.timestamp() if isinstance(now_dt, datetime) else blacknet_utc_now().timestamp()
            if expires_at <= now_ts:
                continue
            ttl_seconds = max(1, int(round(expires_at - now_ts)))
        facts.append(build_blacknet_fact(
            "incident_hotspot_reaction",
            "incidents",
            "incident",
            level,
            now_dt,
            importance="critical" if level >= 4 else "high",
            confidence=0.9,
            region_id=f"incident:{incident_id}",
            subject_id=incident_id,
            ttl_seconds=ttl_seconds,
            metadata={
                "incident_id": incident_id,
                "entity_id": incident_id,
                "cta_target_id": incident_id,
                "hotspot_id": incident_id,
                "target_label": f"L{level} {status.upper()}",
                "location_label": location_label,
                "public_state": status,
                "status": status,
                "trend": trend,
                "incident_level": level,
                "response_level": f"L{level}",
                "search_radius_m": radius_m,
                "radius_m": radius_m,
                "incident_lat": entry["center_lat"],
                "incident_lng": entry["center_lng"],
                "incident_coordinates": entry["center_label"],
                "lat": entry["lat"],
                "lng": entry["lng"],
                "coordinates": entry["label"],
                "entry_distance_m": entry["distance_m"],
                "expires_at": incident.get("expires_at"),
            },
        ))
    return facts


def build_blacknet_world_facts_snapshot(now=None, use_cache=True):
    if now is None and use_cache:
        cached = BLACKNET_WORLD_FACTS_CACHE.get("snapshot")
        cached_at = float(BLACKNET_WORLD_FACTS_CACHE.get("cached_at") or 0.0)
        if isinstance(cached, dict) and time.time() - cached_at < BLACKNET_WORLD_FACTS_CACHE_SECONDS:
            snapshot = copy.deepcopy(cached)
            diagnostics = snapshot.setdefault("diagnostics", {})
            diagnostics["cache"] = {
                "hit": True,
                "ttl_seconds": BLACKNET_WORLD_FACTS_CACHE_SECONDS,
                "age_ms": int(round((time.time() - cached_at) * 1000)),
            }
            return snapshot

    started = time.perf_counter()
    now_dt = now if isinstance(now, datetime) else blacknet_utc_now()
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    sources = {}
    facts = []

    try:
        raw_profiles = user_store.list_profiles()
        if not isinstance(raw_profiles, list):
            raw_profiles = []
        profiles = [
            blacknet_profile_projection(profile)
            for profile in raw_profiles
            if isinstance(profile, dict)
        ]
        sources["profiles"] = {"ok": True, "count": len(profiles)}
    except Exception as exc:
        profiles = []
        sources["profiles"] = {"ok": False, "error": str(exc)}

    aggregators = [
        ("operations", lambda: build_blacknet_operations_facts(profiles, now_dt)),
        ("ghost_exchange", lambda: build_blacknet_ghost_exchange_facts(profiles, now_dt)),
        ("googleplex", lambda: build_blacknet_googleplex_facts(now_dt)),
        ("radio", lambda: build_blacknet_radio_facts(now_dt)),
        ("system", lambda: build_blacknet_system_facts(profiles, now_dt)),
        ("conflicts", lambda: build_blacknet_conflict_activity_facts(now_dt)),
        ("incidents", lambda: build_blacknet_incident_facts(now_dt)),
    ]
    for source_name, aggregator in aggregators:
        source_started = time.perf_counter()
        try:
            source_facts = aggregator()
            if not isinstance(source_facts, list):
                source_facts = []
            facts.extend(source_facts)
            sources[source_name] = {
                "ok": True,
                "facts": len(source_facts),
                "duration_ms": int(round((time.perf_counter() - source_started) * 1000)),
            }
        except Exception as exc:
            sources[source_name] = {
                "ok": False,
                "error": str(exc),
                "duration_ms": int(round((time.perf_counter() - source_started) * 1000)),
            }

    facts.sort(key=lambda item: (item.get("source_system", ""), item.get("fact_type", ""), item.get("subject_id", "")))
    version_payload = [
        {
            "fact_id": item.get("fact_id"),
            "value": item.get("value"),
            "previous_value": item.get("previous_value"),
            "change_percent": item.get("change_percent"),
            "source_system": item.get("source_system"),
        }
        for item in facts
    ]
    version = hashlib.sha1(
        json.dumps(version_payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()[:16]
    snapshot = {
        "schema": BLACKNET_WORLD_FACTS_SCHEMA,
        "snapshot_type": "blacknet_world_facts",
        "version": version,
        "generated_at": blacknet_iso(now_dt),
        "expires_at": blacknet_iso(now_dt + timedelta(seconds=BLACKNET_WORLD_FACTS_TTL_SECONDS)),
        "source_versions": {
            "profiles": sources.get("profiles", {}).get("count", 0),
            "operations": sum(1 for item in facts if item.get("source_system") == "operations"),
            "ghost_exchange": sum(1 for item in facts if item.get("source_system") == "ghost_exchange"),
            "googleplex": sum(1 for item in facts if item.get("source_system") == "googleplex"),
            "radio": sum(1 for item in facts if item.get("source_system") == "radio"),
            "system": sum(1 for item in facts if item.get("source_system") == "system"),
            "conflicts": sum(1 for item in facts if item.get("source_system") == "conflicts"),
            "incidents": sum(1 for item in facts if item.get("source_system") == "incidents"),
        },
        "facts": facts,
        "diagnostics": {
            "duration_ms": int(round((time.perf_counter() - started) * 1000)),
            "sources": sources,
            "fact_count": len(facts),
            "cache": {
                "hit": False,
                "ttl_seconds": BLACKNET_WORLD_FACTS_CACHE_SECONDS,
            },
        },
    }
    if now is None and use_cache:
        BLACKNET_WORLD_FACTS_CACHE["snapshot"] = copy.deepcopy(snapshot)
        BLACKNET_WORLD_FACTS_CACHE["cached_at"] = time.time()
    print(f"[BLACKNET_FACTS] version={version} facts={len(facts)} ms={snapshot['diagnostics']['duration_ms']}")
    return snapshot


def blacknet_fact_number(fact):
    if not isinstance(fact, dict):
        return 0
    try:
        return int(round(float(fact.get("value") or 0)))
    except (TypeError, ValueError):
        return 0


def blacknet_minutes_until(expires_at, now_dt):
    expires_ts = parse_operation_timestamp(expires_at)
    now_ts = now_dt.timestamp() if isinstance(now_dt, datetime) else blacknet_utc_now().timestamp()
    if not expires_ts:
        return 0
    return max(0, int(round((expires_ts - now_ts) / 60)))


def blacknet_timer_text(fact, now_dt):
    minutes = blacknet_minutes_until(fact.get("expires_at"), now_dt)
    if minutes <= 0:
        return "00:00"
    minutes = min(minutes, 99 * 60 + 59)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def blacknet_format_category(category):
    label = str(category or "world").replace("_", " ").replace("-", " ").strip()
    return re.sub(r"\s+", " ", label).upper()[:32] or "WORLD"


def blacknet_format_signal_value(value, rule):
    prefix = str(rule.get("value_prefix") or "")
    suffix = str(rule.get("value_suffix") or "")
    try:
        number = int(round(float(value or 0)))
    except (TypeError, ValueError):
        number = 0
    return f"{prefix}{number}{suffix}"


def blacknet_format_signal_stat(rule, fact, value):
    metadata = fact.get("metadata") if isinstance(fact.get("metadata"), dict) else {}
    template_values = {
        "value": value,
        "category": blacknet_format_category(fact.get("category")),
        "target_label": str(metadata.get("target_label") or blacknet_format_category(fact.get("category"))),
        "file_count": int(metadata.get("file_count") or 0),
        "volume_mb": int(metadata.get("volume_mb") or 0),
        "products": int(metadata.get("products") or 0),
        "tracks_total": int(metadata.get("tracks_total") or 0),
        "downloads": int(metadata.get("downloads") or 0),
        "temperature": int(metadata.get("temperature") or 0),
        "product_name": str(metadata.get("product_name") or blacknet_format_category(fact.get("category"))),
        "product_type": str(metadata.get("product_type") or ""),
        "incident_level": int(metadata.get("incident_level") or 0),
        "response_level": str(metadata.get("response_level") or ""),
        "public_state": str(metadata.get("public_state") or metadata.get("status") or ""),
        "trend": str(metadata.get("trend") or ""),
        "radius_m": int(metadata.get("radius_m") or metadata.get("search_radius_m") or 0),
        "location_label": str(metadata.get("location_label") or metadata.get("incident_coordinates") or ""),
    }
    template = str(rule.get("stat_template") or "{value}")
    try:
        return template.format(**template_values)[:48]
    except (KeyError, ValueError):
        return str(value)[:48]


def blacknet_signal_id(fact, rule):
    raw = "|".join([
        str(rule.get("signal_type") or "world_alert"),
        str(fact.get("fact_id") or ""),
        str(fact.get("category") or ""),
        str(fact.get("region_id") or "global"),
    ])
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"world-{digest}"


def blacknet_radar_from_seed(seed, sides=0):
    digest = hashlib.sha1(str(seed or "blacknet").encode("utf-8")).hexdigest()
    nodes = []
    for index in range(6):
        base = index * 6
        x = 14 + (int(digest[base:base + 2], 16) % 72)
        y = 16 + (int(digest[base + 2:base + 4], 16) % 68)
        r = 2 + (int(digest[base + 4:base + 6], 16) % 3)
        nodes.append([x, y, r])
    return {
        "sides": max(0, min(12, int(sides or 0))),
        "nodes": nodes,
    }


def blacknet_out_of_signal(now_dt, world_version="", reason="no_real_facts"):
    return {
        "id": f"world-out-of-signal-{world_version or 'none'}",
        "source": "world_generated",
        "signal_type": "out_of_signal",
        "fact_id": "",
        "world_version": world_version or "",
        "channel": "BLACKNET SIGNAL BUS",
        "title": "OUT OF SIGNAL",
        "label": "BRAK RUCHU",
        "value": "0",
        "stat": "OCZEKIWANIE NA RUCH SWIATA",
        "timer": "00:00",
        "tone": "lime",
        "layout": 1,
        "cta": "SYGNAL WYCISZONY",
        "cta_action": "none",
        "cta_target": "",
        "cta_target_id": "",
        "cta_query": "",
        "radar": blacknet_radar_from_seed(f"out_of_signal:{world_version}", sides=1),
        "importance": 0,
        "generated_at": blacknet_iso(now_dt),
        "valid_until": blacknet_iso(now_dt + timedelta(seconds=BLACKNET_WORLD_FACTS_CACHE_SECONDS)),
        "observed_at": blacknet_iso(now_dt),
        "category": "out_of_signal",
        "region_id": "global",
        "metadata": {
            "reason": reason,
            "out_of_signal": True,
        },
    }


def blacknet_signal_from_fact(fact, now_dt):
    if not isinstance(fact, dict):
        return None
    rule = BLACKNET_SIGNAL_RULES.get(str(fact.get("fact_type") or ""))
    if not rule:
        return None
    value = blacknet_fact_number(fact)
    if value < int(rule.get("threshold") or 0):
        return None
    if blacknet_minutes_until(fact.get("expires_at"), now_dt) <= 0:
        return None

    metadata = fact.get("metadata") if isinstance(fact.get("metadata"), dict) else {}
    cta_action = str(rule.get("cta_action") or "").strip()
    if cta_action not in BLACKNET_ALLOWED_CTA_ACTIONS:
        return None
    category_label = blacknet_format_category(fact.get("category"))
    title_values = {
        "category": category_label,
        "value": value,
        "product_name": str(metadata.get("product_name") or category_label),
        "product_type": str(metadata.get("product_type") or ""),
        "target_label": str(metadata.get("target_label") or category_label),
    }
    title = str(rule.get("title_template") or rule.get("title") or "WORLD SIGNAL").format(**title_values)
    signal_type = str(rule.get("signal_type") or "world_alert")
    cta_target_id = str(
        metadata.get("cta_target_id")
        or metadata.get("product_id")
        or metadata.get("channel_id")
        or metadata.get("sector")
        or metadata.get("hotspot_id")
        or fact.get("subject_id")
        or ""
    )
    if cta_action == "open_map" and not any(
        metadata.get(key) not in (None, "")
        for key in ("target_id", "cta_target_id", "lat", "lng", "lon", "latitude", "longitude", "hotspot_id")
    ):
        cta_target_id = ""
    signal = {
        "id": blacknet_signal_id(fact, rule),
        "source": "world_generated",
        "signal_type": signal_type,
        "fact_id": fact.get("fact_id"),
        "world_version": fact.get("world_version"),
        "entity_id": str(
            metadata.get("entity_id")
            or metadata.get("cta_target_id")
            or metadata.get("target_id")
            or metadata.get("product_id")
            or metadata.get("channel_id")
            or metadata.get("sector_key")
            or fact.get("subject_id")
            or ""
        ),
        "channel": str(rule.get("channel") or "BLACKNET SIGNAL"),
        "title": title[:48],
        "label": str(rule.get("label") or "STATUS")[:32],
        "value": blacknet_format_signal_value(value, rule)[:24],
        "stat": blacknet_format_signal_stat(rule, fact, value),
        "timer": blacknet_timer_text(fact, now_dt),
        "tone": str(rule.get("tone") or "lime"),
        "layout": int(rule.get("layout") or 1),
        "cta": str(rule.get("cta") or "OTWORZ")[:40],
        "cta_action": cta_action,
        "cta_target": str(rule.get("cta_target") or ""),
        "cta_target_id": cta_target_id,
        "cta_query": str(metadata.get("cta_query") or metadata.get("product_name") or ""),
        "radar": blacknet_radar_from_seed(fact.get("fact_id"), sides=rule.get("layout")),
        "importance": int(fact.get("importance") or 0),
        "generated_at": blacknet_iso(now_dt),
        "valid_until": fact.get("expires_at"),
        "observed_at": fact.get("observed_at"),
        "category": str(fact.get("category") or "general"),
        "region_id": str(fact.get("region_id") or "global"),
        "metadata": blacknet_safe_metadata(metadata),
    }
    return signal


def build_blacknet_world_signals(snapshot=None, now=None, limit=BLACKNET_WORLD_SIGNALS_LIMIT, exclude_ids=None):
    started = time.perf_counter()
    try:
        requested_limit = int(limit or BLACKNET_WORLD_SIGNALS_LIMIT)
    except (TypeError, ValueError):
        requested_limit = BLACKNET_WORLD_SIGNALS_LIMIT
    requested_limit = max(1, min(32, requested_limit))
    exclude_key = tuple(sorted({
        str(item).strip()
        for item in (exclude_ids or [])
        if str(item or "").strip()
    }))
    can_use_cache = snapshot is None and now is None
    cache_key = (requested_limit, exclude_key)
    if can_use_cache:
        cached_entry = BLACKNET_WORLD_SIGNALS_CACHE.get(cache_key)
        cached_at = float((cached_entry or {}).get("cached_at") or 0.0)
        cached_snapshot = (cached_entry or {}).get("snapshot")
        if isinstance(cached_snapshot, dict) and time.time() - cached_at < BLACKNET_WORLD_SIGNALS_CACHE_SECONDS:
            result = copy.deepcopy(cached_snapshot)
            diagnostics = result.setdefault("diagnostics", {})
            diagnostics["cache"] = {
                "hit": True,
                "ttl_seconds": BLACKNET_WORLD_SIGNALS_CACHE_SECONDS,
                "age_ms": int(round((time.time() - cached_at) * 1000)),
            }
            return result

    now_dt = now if isinstance(now, datetime) else blacknet_utc_now()
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    exclude_set = {
        str(item).strip()
        for item in (exclude_ids or [])
        if str(item or "").strip()
    }
    if not isinstance(snapshot, dict):
        snapshot = build_blacknet_world_facts_snapshot()
    facts = snapshot.get("facts") if isinstance(snapshot.get("facts"), list) else []
    candidates = []
    rejected = []
    excluded = []
    for fact in facts:
        signal = blacknet_signal_from_fact(fact, now_dt)
        if signal:
            signal["world_version"] = snapshot.get("version")
            candidates.append(signal)
        else:
            rejected.append({
                "fact_id": fact.get("fact_id") if isinstance(fact, dict) else None,
                "fact_type": fact.get("fact_type") if isinstance(fact, dict) else None,
            })

    candidates.sort(key=lambda item: (
        -int(item.get("importance") or 0),
        str(item.get("signal_type") or ""),
        str(item.get("fact_id") or ""),
    ))
    selected = []
    seen_signal_ids = set()
    seen_combinations = set()
    seen_families = set()

    def try_select_signal(signal, require_new_family=False):
        signal_family = str(signal.get("signal_type") or "").strip()
        if require_new_family and signal_family in seen_families:
            return False
        signal_keys = {
            str(signal.get("id") or "").strip(),
            str(signal.get("fact_id") or "").strip(),
            str(signal.get("entity_id") or "").strip(),
            str(signal.get("cta_target_id") or "").strip(),
        }
        signal_keys.discard("")
        if exclude_set.intersection(signal_keys):
            excluded.append(signal.get("id"))
            return False
        if signal["id"] in seen_signal_ids:
            return False
        combination = (
            signal.get("signal_type"),
            signal.get("layout"),
            signal.get("tone"),
            signal.get("cta_action"),
            signal.get("region_id"),
            signal.get("category"),
        )
        if combination in seen_combinations:
            return False
        seen_signal_ids.add(signal["id"])
        seen_combinations.add(combination)
        if signal_family:
            seen_families.add(signal_family)
        selected.append(signal)
        return True

    for signal in candidates:
        try_select_signal(signal, require_new_family=True)
        if len(selected) >= requested_limit:
            break

    if len(selected) < requested_limit:
        for signal in candidates:
            try_select_signal(signal, require_new_family=False)
            if len(selected) >= requested_limit:
                break

    out_of_signal = False
    if not selected:
        out_of_signal = True
        selected.append(blacknet_out_of_signal(
            now_dt,
            world_version=str(snapshot.get("version") or ""),
            reason="no_publishable_real_facts" if facts else "empty_world_facts",
        ))

    version_payload = [
        {
            "id": signal.get("id"),
            "fact_id": signal.get("fact_id"),
            "value": signal.get("value"),
            "timer": signal.get("timer"),
            "cta_action": signal.get("cta_action"),
        }
        for signal in selected
    ]
    version = hashlib.sha1(
        json.dumps(version_payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()[:16]
    result = {
        "schema": BLACKNET_WORLD_SIGNALS_SCHEMA,
        "snapshot_type": "blacknet_world_signals",
        "source": "world_generated",
        "version": version,
        "world_facts_version": snapshot.get("version"),
        "generated_at": blacknet_iso(now_dt),
        "signals": selected,
        "diagnostics": {
            "duration_ms": int(round((time.perf_counter() - started) * 1000)),
            "facts_seen": len(facts),
            "candidates": len(candidates),
            "published": len(selected),
            "rejected": len(rejected),
            "excluded": len(excluded),
            "out_of_signal": out_of_signal,
            "local_static_allowed": False,
            "local_static_policy": "dev_flag_only",
            "ollama_used": False,
            "cache": {
                "hit": False,
                "ttl_seconds": BLACKNET_WORLD_SIGNALS_CACHE_SECONDS,
            },
        },
    }
    if can_use_cache:
        if len(BLACKNET_WORLD_SIGNALS_CACHE) > 64:
            BLACKNET_WORLD_SIGNALS_CACHE.clear()
        BLACKNET_WORLD_SIGNALS_CACHE[cache_key] = {
            "snapshot": copy.deepcopy(result),
            "cached_at": time.time(),
        }
    return result


def blacknet_ollama_text(value, limit=160):
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > limit:
        return text[:max(0, limit - 3)].rstrip() + "..."
    return text


def blacknet_ollama_public_metadata(metadata, max_items=12):
    if not isinstance(metadata, dict):
        return {}
    blocked_fragments = {
        "username",
        "user_name",
        "player",
        "owner",
        "password",
        "email",
        "session",
        "token",
        "secret",
        "participants",
        "profile",
    }
    public = {}
    for key, value in metadata.items():
        key = str(key or "").strip()
        if not key:
            continue
        lowered = key.lower()
        if any(fragment in lowered for fragment in blocked_fragments):
            continue
        if isinstance(value, str):
            public[key] = blacknet_ollama_text(value, 120)
        elif isinstance(value, (int, float, bool)) or value is None:
            public[key] = value
        elif isinstance(value, list):
            public[key] = [
                blacknet_ollama_text(item, 80) if isinstance(item, str) else item
                for item in value[:max_items]
                if isinstance(item, (str, int, float, bool)) or item is None
            ]
        elif isinstance(value, dict):
            nested = blacknet_ollama_public_metadata(value, max_items=max_items)
            if nested:
                public[key] = nested
    return public


def blacknet_ollama_safe_fact(fact):
    if not isinstance(fact, dict):
        return None
    fact_id = blacknet_ollama_text(fact.get("fact_id"), 96)
    if not fact_id:
        return None
    safe = {
        "fact_id": fact_id,
        "fact_type": blacknet_ollama_text(fact.get("fact_type"), 64),
        "source_system": blacknet_ollama_text(fact.get("source_system"), 64),
        "category": blacknet_ollama_text(fact.get("category"), 80),
        "region_id": blacknet_ollama_text(fact.get("region_id"), 80),
        "subject_id": blacknet_ollama_text(fact.get("subject_id"), 96),
        "value": fact.get("value"),
        "previous_value": fact.get("previous_value"),
        "change_percent": fact.get("change_percent"),
        "importance": fact.get("importance"),
        "importance_label": blacknet_ollama_text(fact.get("importance_label"), 32),
        "confidence": fact.get("confidence"),
        "observed_at": blacknet_ollama_text(fact.get("observed_at"), 40),
        "expires_at": blacknet_ollama_text(fact.get("expires_at"), 40),
        "metadata": blacknet_ollama_public_metadata(fact.get("metadata")),
    }
    return {key: value for key, value in safe.items() if value not in (None, "", {})}


def blacknet_ollama_safe_signal(signal):
    if not isinstance(signal, dict):
        return None
    signal_id = blacknet_ollama_text(signal.get("id"), 96)
    if not signal_id:
        return None
    safe = {
        "id": signal_id,
        "fact_id": blacknet_ollama_text(signal.get("fact_id"), 96),
        "source": blacknet_ollama_text(signal.get("source"), 64),
        "signal_type": blacknet_ollama_text(signal.get("signal_type"), 64),
        "channel": blacknet_ollama_text(signal.get("channel"), 64),
        "title": blacknet_ollama_text(signal.get("title"), 80),
        "label": blacknet_ollama_text(signal.get("label"), 48),
        "value": blacknet_ollama_text(signal.get("value"), 40),
        "stat": blacknet_ollama_text(signal.get("stat"), 80),
        "timer": blacknet_ollama_text(signal.get("timer"), 16),
        "tone": blacknet_ollama_text(signal.get("tone"), 16),
        "layout": signal.get("layout"),
        "world_version": blacknet_ollama_text(signal.get("world_version"), 96),
        "cta_action": blacknet_ollama_text(signal.get("cta_action"), 64),
        "cta_target": blacknet_ollama_text(signal.get("cta_target"), 80),
        "cta_target_id": blacknet_ollama_text(signal.get("cta_target_id"), 96),
        "cta_query": blacknet_ollama_text(signal.get("cta_query"), 96),
        "entity_id": blacknet_ollama_text(signal.get("entity_id"), 96),
        "metadata": blacknet_ollama_public_metadata(signal.get("metadata"), max_items=16),
    }
    return {key: value for key, value in safe.items() if value not in (None, "", {})}


def blacknet_ollama_allowed_signal_types():
    signal_types = {
        str(rule.get("signal_type") or "").strip()
        for rule in BLACKNET_SIGNAL_RULES.values()
        if str(rule.get("signal_type") or "").strip()
    }
    signal_types.add("out_of_signal")
    return sorted(signal_types)


def blacknet_ollama_existing_identifiers(facts, signals):
    identifiers = {
        "fact_ids": [],
        "target_ids": [],
        "product_ids": [],
        "market_sectors": [],
        "radio_channels": [],
        "cyberner_channels": ["world"],
    }
    for fact in facts:
        identifiers["fact_ids"].append(fact.get("fact_id"))
        metadata = fact.get("metadata") if isinstance(fact.get("metadata"), dict) else {}
        for source_key, target_key in (
            ("target_id", "target_ids"),
            ("cta_target_id", "target_ids"),
            ("product_id", "product_ids"),
            ("sector_key", "market_sectors"),
            ("market_category", "market_sectors"),
            ("channel_id", "radio_channels"),
            ("thread_channel", "cyberner_channels"),
        ):
            value = metadata.get(source_key)
            if value:
                identifiers[target_key].append(str(value))
    for signal in signals:
        if signal.get("cta_target_id"):
            identifiers["target_ids"].append(str(signal.get("cta_target_id")))
        if signal.get("entity_id"):
            identifiers["target_ids"].append(str(signal.get("entity_id")))
    return {
        key: sorted({blacknet_ollama_text(item, 96) for item in values if item})
        for key, values in identifiers.items()
    }


def blacknet_ollama_trends(facts):
    source_counts = {}
    top_facts = []
    for fact in facts:
        source = str(fact.get("source_system") or "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1
        top_facts.append({
            "fact_id": fact.get("fact_id"),
            "fact_type": fact.get("fact_type"),
            "source_system": source,
            "category": fact.get("category"),
            "value": fact.get("value"),
            "importance": fact.get("importance", 0),
        })
    top_facts.sort(key=lambda item: (-int(item.get("importance") or 0), str(item.get("fact_id") or "")))
    return {
        "source_counts": source_counts,
        "top_facts": top_facts[:8],
    }


def validate_blacknet_ollama_outbox(package):
    errors = []
    if not isinstance(package, dict):
        return ["package_not_object"]
    if package.get("schema_version") != BLACKNET_OLLAMA_OUTBOX_SCHEMA_VERSION:
        errors.append("invalid_schema_version")
    if not package.get("digest_id"):
        errors.append("missing_digest_id")
    facts = package.get("facts")
    if not isinstance(facts, list):
        errors.append("facts_not_list")
        facts = []
    if not facts:
        errors.append("no_facts")
    allowed_actions = set(package.get("allowed_actions") or [])
    if not allowed_actions.issubset(BLACKNET_ALLOWED_CTA_ACTIONS):
        errors.append("unknown_allowed_action")
    for fact in facts:
        if not isinstance(fact, dict) or not fact.get("fact_id"):
            errors.append("fact_without_fact_id")
            break
    payload_size = len(json.dumps(package, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    if payload_size > BLACKNET_OLLAMA_OUTBOX_MAX_BYTES:
        errors.append("payload_too_large")
    return errors


def build_blacknet_ollama_outbox(facts_snapshot=None, signal_snapshot=None, now=None, status=None):
    now_dt = now if isinstance(now, datetime) else blacknet_utc_now()
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    if not isinstance(facts_snapshot, dict):
        facts_snapshot = build_blacknet_world_facts_snapshot(now=now_dt)
    if not isinstance(signal_snapshot, dict):
        signal_snapshot = build_blacknet_world_signals(facts_snapshot, now=now_dt)

    safe_facts = [
        item for item in (
            blacknet_ollama_safe_fact(fact)
            for fact in (facts_snapshot.get("facts") or [])[:BLACKNET_OLLAMA_OUTBOX_MAX_FACTS]
        )
        if item
    ]
    safe_signals = [
        item for item in (
            blacknet_ollama_safe_signal(signal)
            for signal in (signal_snapshot.get("signals") or [])[:BLACKNET_OLLAMA_OUTBOX_MAX_SIGNALS]
        )
        if item
    ]
    world_version = str(facts_snapshot.get("version") or "")
    digest_seed = {
        "world_version": world_version,
        "generated_at": blacknet_iso(now_dt),
        "facts": [fact.get("fact_id") for fact in safe_facts],
    }
    digest_hash = hashlib.sha1(
        json.dumps(digest_seed, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()[:12]
    digest_id = f"digest_{now_dt.strftime('%Y%m%d_%H%M%S')}_{digest_hash}"
    package = {
        "schema_version": BLACKNET_OLLAMA_OUTBOX_SCHEMA_VERSION,
        "digest_id": digest_id,
        "status": "created",
        "world_version": world_version,
        "world_signals_version": signal_snapshot.get("version"),
        "generated_at": blacknet_iso(now_dt),
        "valid_until": blacknet_iso(now_dt + timedelta(seconds=BLACKNET_OLLAMA_OUTBOX_TTL_SECONDS)),
        "facts": safe_facts,
        "selected_signals": safe_signals,
        "trends": blacknet_ollama_trends(safe_facts),
        "important_regions": sorted({
            fact.get("region_id") for fact in safe_facts
            if fact.get("region_id") and fact.get("region_id") != "global"
        })[:12],
        "available_products_and_markets": {
            "market_sectors": sorted(BLACKNET_MARKET_SECTOR_LABELS.keys()),
            "products_from_facts": sorted({
                fact.get("metadata", {}).get("product_id")
                for fact in safe_facts
                if isinstance(fact.get("metadata"), dict) and fact.get("metadata", {}).get("product_id")
            })[:12],
        },
        "allowed_signal_types": blacknet_ollama_allowed_signal_types(),
        "allowed_actions": sorted(BLACKNET_ALLOWED_CTA_ACTIONS),
        "existing_identifiers": blacknet_ollama_existing_identifiers(safe_facts, safe_signals),
        "author_personas": BLACKNET_OLLAMA_AUTHOR_PERSONAS,
        "limits": {
            "title_max_chars": 48,
            "channel_max_chars": 64,
            "label_max_chars": 32,
            "stat_max_chars": 48,
            "body_max_chars": 240,
            "signals_max": 8,
        },
        "language": "pl",
        "world_tone": "cyberpunkowy, nerwowy, rzeczowy, bez marketingowego lania wody",
        "forbidden_claims": BLACKNET_OLLAMA_FORBIDDEN_CLAIMS,
        "editorial_rules": {
            "must_reference_fact_ids": True,
            "must_keep_mechanical_values": True,
            "must_use_allowed_actions_only": True,
            "must_not_create_urls": True,
            "must_not_create_new_entities": True,
        },
        "recent_publications": [],
        "diagnostics": {
            "facts_seen": len(facts_snapshot.get("facts") or []),
            "facts_exported": len(safe_facts),
            "signals_exported": len(safe_signals),
            "source": "blacknet_world_facts",
            "ollama_executed": False,
        },
    }
    errors = validate_blacknet_ollama_outbox(package)
    package["validation"] = {
        "ok": not errors,
        "errors": errors,
    }
    package["status"] = status if status in BLACKNET_OLLAMA_OUTBOX_STATUSES else ("ready" if not errors else "failed")
    return package


def blacknet_ollama_outbox_dir():
    return BLACKNET_OLLAMA_OUTBOX_DIR


def blacknet_ollama_outbox_path(digest_id):
    safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", str(digest_id or ""))
    if not safe_id:
        safe_id = "digest"
    return os.path.join(blacknet_ollama_outbox_dir(), f"{safe_id}.json")


def write_blacknet_ollama_outbox(package):
    if not isinstance(package, dict):
        raise ValueError("outbox_package_not_object")
    digest_id = package.get("digest_id")
    if not digest_id:
        raise ValueError("outbox_missing_digest_id")
    os.makedirs(blacknet_ollama_outbox_dir(), exist_ok=True)
    path = blacknet_ollama_outbox_path(digest_id)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(package, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp_path, path)
    return path


def read_blacknet_ollama_outbox(digest_id):
    path = blacknet_ollama_outbox_path(digest_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def list_blacknet_ollama_outboxes():
    directory = blacknet_ollama_outbox_dir()
    if not os.path.isdir(directory):
        return []
    packages = []
    for filename in os.listdir(directory):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(directory, filename)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                package = json.load(handle)
            if isinstance(package, dict):
                packages.append(package)
        except Exception as exc:
            print(f"[BLACKNET_OLLAMA] cannot read outbox {filename}: {exc}")
    packages.sort(key=lambda item: str(item.get("generated_at") or ""), reverse=True)
    return packages


def latest_blacknet_ollama_outbox(status="ready"):
    wanted_status = str(status or "ready")
    for package in list_blacknet_ollama_outboxes():
        if not wanted_status or package.get("status") == wanted_status:
            return package
    return None


def update_blacknet_ollama_outbox_status(digest_id, status, message=""):
    status = str(status or "").strip()
    if status not in BLACKNET_OLLAMA_OUTBOX_STATUSES:
        return None, "invalid_status"
    package = read_blacknet_ollama_outbox(digest_id)
    if not isinstance(package, dict):
        return None, "not_found"
    if status == "ready" and not package.get("validation", {}).get("ok"):
        return None, "validation_failed"
    package["status"] = status
    package["status_updated_at"] = blacknet_iso(blacknet_utc_now())
    if message:
        package["status_message"] = blacknet_ollama_text(message, 240)
    write_blacknet_ollama_outbox(package)
    return package, ""


def build_map_player_actor_delta_payload(viewer_username, actor_profile, context=None, lat=None, lng=None):
    if not viewer_username or not isinstance(actor_profile, dict):
        return None
    actor_username = actor_profile.get("username")
    if not actor_username or actor_username == viewer_username:
        return None

    try:
        position = player_position_store.get_position(actor_username) or {}
    except Exception:
        position = {}
    if not position:
        position = actor_profile.get("curently_possition", {}) or actor_profile.get("current_position", {}) or {}
    lat = position.get("lat") if lat is None else lat
    lng = position.get("lng") if lng is None else lng
    if lat in (None, 0, 0.0) or lng in (None, 0, 0.0):
        return None

    viewer_profile = user_store.get_profile(viewer_username) or {}
    context = dict(context or {})
    aimed_target = viewer_profile.get("aimed_target") or {}
    if aimed_target.get("target_mode") == "player" and aimed_target.get("target_username") == actor_username:
        context["is_marked_target"] = True
        context["target_status"] = "aimed"

    actor_clan = get_profile_clan(actor_profile)
    if actor_clan:
        context["clan"] = actor_clan
    context["level"] = actor_profile.get("level", context.get("level"))

    try:
        territory_count = 0
        for area in territory_store.list_player_areas():
            owner_username = area.get("owner_username") or area.get("login")
            if owner_username == actor_username:
                territory_count += 1
        context["territory_count"] = territory_count
    except Exception as exc:
        print(f"Nie udalo sie policzyc terytoriow player_actor delta: {exc}")

    profession = (
        actor_profile.get("profession")
        or actor_profile.get("role")
        or (actor_profile.get("fraction") or {}).get("role")
        or (actor_profile.get("operator") or {}).get("profession")
        or ""
    )
    if profession:
        context["profession"] = profession

    actor_data = {
        "username": actor_username,
        "nick": actor_profile.get("nick") or actor_username,
        "avatar": actor_profile.get("avatar", ""),
        "lat": lat,
        "lng": lng,
        "status": context.get("contact_status", ""),
        "clan": context.get("clan", ""),
        "level": context.get("level"),
        "profession": context.get("profession", ""),
        "territory_count": context.get("territory_count", 0),
        "is_pending_contact": context.get("is_pending_contact", False),
        "is_marked_target": context.get("is_marked_target", False),
        "target_status": context.get("target_status", ""),
    }
    relation = resolve_player_actor_relation(viewer_profile, actor_profile, context)
    return build_player_actor(
        viewer_username,
        actor_data,
        relation=relation,
        context=context,
    )


def record_map_player_actor_delta(actor_username, actor_profile=None, change_type="map.player_moved",
                                  reason="", intrusion_area=None, viewer_contexts=None,
                                  dedupe_key_prefix=None):
    actor_username = str(actor_username or "").strip()
    if not actor_username:
        return []
    actor_profile = actor_profile if isinstance(actor_profile, dict) else (user_store.get_profile(actor_username) or {})
    if not actor_profile:
        return []

    viewer_contexts = dict(viewer_contexts or {})
    for contact in mail_store.list_accepted_contacts(actor_username):
        viewer_username = str(contact.get("name") or "").strip()
        if not viewer_username or viewer_username == actor_username:
            continue
        viewer_contexts.setdefault(viewer_username, {})
        viewer_contexts[viewer_username].update({
            "is_friend": True,
            "contact_status": contact.get("status", "offline"),
        })

    if isinstance(intrusion_area, dict):
        owner_username = str(intrusion_area.get("owner_username") or "").strip()
        if owner_username and owner_username != actor_username:
            viewer_contexts.setdefault(owner_username, {})
            viewer_contexts[owner_username].update({
                "is_intruder": True,
                "area_id": intrusion_area.get("id"),
            })

    if not viewer_contexts:
        return []

    try:
        position = player_position_store.get_position(actor_username) or {}
    except Exception:
        position = {}
    if not position:
        position = actor_profile.get("curently_possition", {}) or actor_profile.get("current_position", {}) or {}
    lat = position.get("lat")
    lng = position.get("lng")
    reason = str(reason or "player_actor_changed")
    dedupe_key_prefix = str(
        dedupe_key_prefix
        or f"map:player_actor:{actor_username}:{change_type}:{lat}:{lng}:{runtime_file_now()}"
    )
    events = []

    for viewer_username, context in viewer_contexts.items():
        actor_payload = build_map_player_actor_delta_payload(
            viewer_username,
            actor_profile,
            context=context,
            lat=lat,
            lng=lng,
        )
        if not actor_payload and change_type != "map.player_actor_removed":
            continue
        payload = {
            "username": actor_username,
            "reason": reason,
        }
        if actor_payload:
            payload["actor"] = actor_payload
            payload["lat"] = actor_payload.get("lat")
            payload["lng"] = actor_payload.get("lng")
        if change_type == "map.player_actor_removed":
            payload["removed"] = True
        try:
            events.append(delta_bus.record_change(
                viewer_username,
                "map",
                change_type,
                payload,
                entity_id=actor_username,
                dedupe_key=f"{dedupe_key_prefix}:{viewer_username}",
            ))
        except Exception as exc:
            print(f"[DELTA] {change_type} failed for {viewer_username}/{actor_username}: {exc}")

    return events


def record_map_target_delta(username, target, change_type="map.target_updated", reason="", dedupe_key=None):
    username = str(username or "").strip()
    if not username or not isinstance(target, dict):
        return None
    target_id = build_operation_target_id(target)
    payload = {
        "target_id": target_id,
        "target": dict(target),
        "reason": reason or "target_changed",
    }
    if change_type == "map.target_captured":
        payload["captured"] = True
    if change_type == "map.target_removed":
        payload["removed"] = True
    try:
        return delta_bus.record_change(
            username,
            "map",
            change_type,
            payload,
            entity_id=target_id,
            dedupe_key=dedupe_key or f"map:target:{username}:{change_type}:{target_id}:{runtime_file_now()}",
        )
    except Exception as exc:
        print(f"[DELTA] {change_type} failed for {username}/{target_id}: {exc}")
        return None


def record_territory_areas_delta(username, areas, reason="territory_rebuild"):
    try:
        return territory_delta_publisher.record_areas_updated(username, areas, reason=reason)
    except Exception as exc:
        print(f"[DELTA] territory.updated failed for {username}: {exc}", flush=True)
        return []


def record_territory_conflict_delta(conflict, reason="territory_conflict"):
    try:
        reference = (conflict or {}).get("conflict_id") or (conflict or {}).get("conflict_key")
        snapshot = territory_conflict_store.latest_snapshot_state(reference) if reference else None
        return territory_delta_publisher.record_conflict_changed(
            snapshot if isinstance(snapshot, dict) else conflict,
            reason=reason,
        )
    except Exception as exc:
        conflict_key = (conflict or {}).get("conflict_key") if isinstance(conflict, dict) else "-"
        print(f"[DELTA] territory.conflict_changed failed for {conflict_key}: {exc}", flush=True)
        return []


def is_territory_conflict_snapshot_read_enabled():
    value = os.environ.get("CHAOS_TERRITORY_CONFLICT_SNAPSHOT_READ")
    if value is None:
        return True
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def project_territory_conflict_snapshot(snapshot):
    """Expose the immutable conflict snapshot without rebuilding live geometry."""
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    conflict = dict(snapshot.get("conflict") or {})
    conflict_id = str(conflict.get("conflict_id") or conflict.get("id") or "").strip()
    if not conflict_id:
        return None
    fronts = []
    for index, source in enumerate(snapshot.get("fronts") or []):
        if not isinstance(source, dict):
            continue
        front = dict(source)
        front["front_id"] = str(front.get("front_id") or f"{conflict_id}:front:{index}")
        front["geometry"] = front.get("geometry") or []
        fronts.append(front)
    pillars = []
    for source in snapshot.get("pillars") or []:
        if not isinstance(source, dict):
            continue
        pillar = dict(source)
        public_target = pillar.get("public_target")
        if not isinstance(public_target, dict):
            public_target = {}
        target = pillar.get("target")
        if not isinstance(target, dict):
            nested_target = public_target.get("target")
            target = nested_target if isinstance(nested_target, dict) else public_target
        pillar["target"] = dict(target)
        pillar["target"].setdefault("target_id", pillar.get("target_id"))
        pillars.append(pillar)
    version = int(snapshot.get("snapshot_version") or snapshot.get("geometry_version") or 0)
    geometry_status = str(
        snapshot.get("geometry_status") or conflict.get("geometry_status") or "unknown"
    ).lower()
    snapshot_conflict_version = int(snapshot.get("conflict_version") or 0)
    current_conflict_version = max(
        int(conflict.get("conflict_version") or 0),
        snapshot_conflict_version,
    )
    complete = snapshot.get("complete")
    if complete is None:
        complete = (
            geometry_status in {"clean", "published"}
            and version > 0
            and snapshot_conflict_version >= current_conflict_version
        )
    return {
        "conflict_id": conflict_id,
        "conflict_key": conflict.get("conflict_key") or conflict_id,
        "status": conflict.get("status") or "active",
        "participants": conflict.get("participants") or conflict.get("participant_usernames") or [],
        "conflict": conflict,
        "fronts": fronts,
        "pillars": pillars,
        "snapshot_version": version,
        "conflict_version": current_conflict_version,
        "geometry_version": int(snapshot.get("geometry_version") or version),
        "generated_at": snapshot.get("generated_at") or conflict.get("updated_at"),
        "geometry_status": geometry_status,
        "complete": bool(complete),
        "recovery_required": bool(snapshot.get("recovery_required", False)),
    }


def legacy_conflict_fields_from_snapshots(snapshots):
    """Derive transitional map fields from the same canonical snapshots."""
    conflicts = []
    conflict_areas = []
    targets = []
    captured = []
    for snapshot in snapshots or []:
        conflict = dict(snapshot.get("conflict") or {})
        conflict_id = snapshot.get("conflict_id")
        fronts = snapshot.get("fronts") or []
        intersections = [front.get("geometry") or [] for front in fronts if isinstance(front, dict)]
        conflict.update({
            "conflict_id": conflict_id,
            "conflict_key": snapshot.get("conflict_key"),
            "intersections": intersections,
            "intersection": intersections[0] if intersections else [],
            "snapshot_version": snapshot.get("snapshot_version"),
            "geometry_version": snapshot.get("geometry_version"),
        })
        conflict_targets = []
        for pillar in snapshot.get("pillars") or []:
            item = {**pillar, "conflict_id": conflict_id, "conflict_key": snapshot.get("conflict_key")}
            targets.append(item)
            conflict_targets.append(item)
            if item.get("captured") or item.get("status") == "captured":
                captured.append(item)
        conflict["targets"] = conflict_targets
        conflicts.append(conflict)
        conflict_areas.append(conflict)
    return conflicts, conflict_areas, targets, captured


def record_territory_encirclement_delta(attacker_username, defender_username, payload, dedupe_key):
    payload = dict(payload or {})
    users = sorted({
        str(attacker_username or "").strip(),
        str(defender_username or "").strip(),
    } - {""})
    events = []
    for username in users:
        try:
            events.append(delta_bus.record_change(
                username,
                "territory",
                "territory.encirclement_resolved",
                payload,
                entity_id=str(payload.get("defender_cluster_id") or "territory_encirclement"),
                dedupe_key=f"{dedupe_key}:{username}",
            ))
        except Exception as exc:
            print(f"[DELTA] territory.encirclement_resolved failed for {username}: {exc}", flush=True)
    return events


def record_incident_delta(username, incident, change_type="incident.updated", reason="incident_changed"):
    username = str(username or "").strip()
    if not username or not isinstance(incident, dict):
        return None
    payload = IncidentStore.public_payload(incident)
    incident_id = str(payload.get("incident_id") or "").strip()
    if not incident_id:
        return None
    if change_type == "incident.resolved":
        payload["removed"] = True
        payload["status"] = "resolved"
    payload["reason"] = reason or "incident_changed"
    try:
        return delta_bus.record_change(
            username,
            "incident",
            change_type,
            payload,
            entity_id=incident_id,
            dedupe_key=f"incident:{username}:{change_type}:{incident_id}:{payload.get('version')}",
        )
    except Exception as exc:
        print(f"[DELTA] {change_type} failed for {username}/{incident_id}: {exc}", flush=True)
        return None


def record_npc_capsule_delta(username, capsule, change_type="npc.updated", reason="npc_capsule_changed"):
    username = str(username or "").strip()
    if not username or not isinstance(capsule, dict):
        return None
    payload = public_capsule_payload(capsule)
    capsule_id = str(payload.get("capsule_id") or "").strip()
    if not capsule_id:
        return None
    if change_type == "npc.removed":
        payload["removed"] = True
        payload["status"] = "removed"
    payload["reason"] = reason or "npc_capsule_changed"
    try:
        return delta_bus.record_change(
            username,
            "npc",
            change_type,
            payload,
            entity_id=capsule_id,
            dedupe_key=f"npc:{username}:{change_type}:{capsule_id}:{payload.get('version')}",
        )
    except Exception as exc:
        print(f"[DELTA] {change_type} failed for {username}/{capsule_id}: {exc}", flush=True)
        return None


def publish_npc_capsule_actions(username, actions):
    username = str(username or "").strip()
    if not username:
        return []
    events = []
    for action in actions or []:
        if not isinstance(action, dict):
            continue
        action_type = str(action.get("action") or "").strip()
        capsule = action.get("capsule") if isinstance(action.get("capsule"), dict) else {}
        if action_type == "spawned":
            event_type = "npc.spawned"
        elif action_type == "updated":
            event_type = "npc.updated"
        elif action_type == "removed":
            event_type = "npc.removed"
        else:
            continue
        event = record_npc_capsule_delta(username, capsule, event_type, reason=action_type)
        if event:
            events.append(event)
    return events


def publish_incident_actions(username, actions):
    username = str(username or "").strip()
    if not username:
        return []
    events = []
    blacknet_invalidated = False
    for action in actions or []:
        if not isinstance(action, dict):
            continue
        action_type = str(action.get("action") or "").strip()
        incident_id = str(action.get("incident_id") or "").strip()
        if not incident_id:
            continue
        incident = incident_store.get(incident_id)
        if not incident:
            continue
        capsule_actions = []
        if action_type == "created":
            event_type = "incident.created"
            capsule_actions = response_dispatcher.dispatch_incident(incident)
        elif action_type == "cancelled":
            event_type = "incident.resolved"
            capsule_actions = response_dispatcher.cancel_incident(incident_id, reason="incident_resolved")
        elif action_type == "recalculated":
            event_type = "incident.updated"
            capsule_actions = response_dispatcher.dispatch_incident(incident)
        else:
            continue
        if event_type == "incident.resolved":
            events.extend(publish_npc_capsule_actions(username, capsule_actions))
        event = record_incident_delta(username, incident, event_type, reason=action_type)
        if event:
            events.append(event)
            blacknet_invalidated = True
        if event_type != "incident.resolved":
            events.extend(publish_npc_capsule_actions(username, capsule_actions))
    if blacknet_invalidated:
        BLACKNET_WORLD_FACTS_CACHE["snapshot"] = None
        BLACKNET_WORLD_FACTS_CACHE["cached_at"] = 0.0
        BLACKNET_WORLD_SIGNALS_CACHE.clear()
    return events


def response_npc_runtime_iso(now=None):
    now_dt = now if isinstance(now, datetime) else datetime.now(timezone.utc)
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    return now_dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def response_npc_parse_iso(value):
    if not value:
        return None
    try:
        raw = str(value).strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def response_npc_capsule_runtime_active(capsule, now=None):
    capsule = capsule if isinstance(capsule, dict) else {}
    status = str(capsule.get("status") or "").strip().lower()
    if status not in {"active", "updated"}:
        return False
    now_dt = now if isinstance(now, datetime) else datetime.now(timezone.utc)
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    expires_at = response_npc_parse_iso(capsule.get("expires_at"))
    return bool(expires_at and expires_at > now_dt.astimezone(timezone.utc))


def response_npc_public_capsule_debug(capsule, now=None):
    capsule = capsule if isinstance(capsule, dict) else {}
    now_dt = now if isinstance(now, datetime) else datetime.now(timezone.utc)
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    now_dt = now_dt.astimezone(timezone.utc)
    spawn_at = response_npc_parse_iso(capsule.get("spawn_at"))
    expires_at = response_npc_parse_iso(capsule.get("expires_at"))
    return {
        "capsule_id": str(capsule.get("capsule_id") or ""),
        "incident_id": str(capsule.get("incident_id") or ""),
        "status": str(capsule.get("status") or ""),
        "spawn_at": capsule.get("spawn_at"),
        "expires_at": capsule.get("expires_at"),
        "spawned": bool(spawn_at and spawn_at <= now_dt),
        "runtime_active": response_npc_capsule_runtime_active(capsule, now_dt),
    }


def incident_for_response_npc_dispatch(incident, now=None):
    incident = copy.deepcopy(incident if isinstance(incident, dict) else {})
    now_dt = now if isinstance(now, datetime) else datetime.now(timezone.utc)
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    now_dt = now_dt.astimezone(timezone.utc)
    expires_at = response_npc_parse_iso(incident.get("expires_at"))
    if not expires_at or expires_at <= now_dt + timedelta(seconds=30):
        incident["expires_at"] = response_npc_runtime_iso(now_dt + timedelta(minutes=12))
    return incident


def ensure_response_npc_capsules_for_active_incidents(username=None):
    """Backfill NPC capsules for active incidents that predate dispatcher output."""
    username = str(username or "").strip()
    materialized_actions = []
    now_dt = datetime.now(timezone.utc)
    try:
        active_incidents = incident_store.list_active()
    except Exception as exc:
        print(f"[RESPONSE_NPC] active incident recovery failed: {exc}", flush=True)
        return materialized_actions

    for incident in active_incidents:
        if not isinstance(incident, dict):
            continue
        incident_id = str(incident.get("incident_id") or "").strip()
        if not incident_id:
            continue
        try:
            existing_capsules = npc_capsule_store.list_by_incident(incident_id)
            if any(response_npc_capsule_runtime_active(capsule, now_dt) for capsule in existing_capsules):
                continue
            runtime_incident = incident_for_response_npc_dispatch(incident, now_dt)
            actions = response_dispatcher.dispatch_incident(runtime_incident, now=response_npc_runtime_iso(now_dt))
            if actions:
                materialized_actions.extend(actions)
        except Exception as exc:
            print(f"[RESPONSE_NPC] capsule recovery failed for {incident_id}: {exc}", flush=True)

    if username and materialized_actions:
        publish_npc_capsule_actions(username, materialized_actions)
    return materialized_actions


def response_warning_system_text(operation, warning):
    target = operation.get("target") if isinstance(operation.get("target"), dict) else {}
    target_label = (
        target.get("label")
        or target.get("name")
        or operation.get("target_id")
        or warning.get("target_id")
        or "cel operacji"
    )
    arrival_at = warning.get("arrival_at") or "-"
    heat = warning.get("heat") or 0
    return (
        f"Response Network wykryl aktywnosc przy {target_label}. "
        f"Poziom ryzyka: {heat}. Sluzby sa w drodze. ETA: {arrival_at}. "
        "Tryb visible_safe: brak kar, brak przerwania operacji."
    )


def sync_response_warnings(username, profile, operations, now_iso=None):
    username = str(username or "").strip()
    if not username:
        return []
    now_iso = now_iso or operation_iso_from_ts(datetime.now(timezone.utc).timestamp())
    actions = []
    for operation in operations or []:
        if not isinstance(operation, dict):
            continue
        operation_id = str(operation.get("operation_id") or operation.get("id") or "").strip()
        if not operation_id:
            continue
        meter = operation.get("operation_risk_meter") if isinstance(operation.get("operation_risk_meter"), dict) else {}
        if meter.get("warning_cancelled") or meter.get("cancelled"):
            cancelled = response_warning_store.cancel_for_operation(
                operation_id,
                reason="operation_cancelled",
                now=now_iso,
            )
            if cancelled:
                actions.extend({"action": "cancelled", "warning": item} for item in cancelled)
            continue

        if not meter.get("warning_crossed"):
            continue
        try:
            active_contribution = int(meter.get("active_contribution") or 0)
        except (TypeError, ValueError):
            active_contribution = 0
        if active_contribution <= 0:
            continue

        actor = str(meter.get("actor_id") or operation.get("owner_username") or username).strip()
        incident = incident_store.get(meter.get("incident_id")) if meter.get("incident_id") else None
        warning, created = response_warning_store.issue_warning(
            actor,
            operation,
            incident=incident,
            now=now_iso,
        )
        if not warning:
            continue
        meter["mode"] = "visible_safe"
        meter["warning_issued_at"] = meter.get("warning_issued_at") or warning.get("issued_at")
        meter["warning_id"] = warning.get("warning_id")
        meter["warning_arrival_at"] = warning.get("arrival_at")
        operation["operation_risk_meter"] = meter
        actions.append({"action": "issued" if created else "existing", "warning": warning})

        if created:
            title = "Response Network: ostrzezenie"
            text = response_warning_system_text(operation, warning)
            if actor == username and isinstance(profile, dict):
                append_profile_system_message(profile, "warning", title, text)
            else:
                add_system_message_to_user(actor, "warning", title, text)
    return actions


def _profile_map_position(profile):
    if not isinstance(profile, dict):
        return None
    position = (
        profile.get("curently_possition")
        or profile.get("current_position")
        or profile.get("position")
        or {}
    )
    try:
        lat = float(position.get("lat"))
        lng = float(position.get("lng", position.get("lon")))
    except (AttributeError, TypeError, ValueError):
        return None
    if lat in (0, 0.0) or lng in (0, 0.0):
        return None
    return {"lat": lat, "lng": lng}


def sync_static_area_intruders_for_owner(owner_username, areas=None, reason="territory_rebuild"):
    owner_username = str(owner_username or "").strip()
    if not owner_username:
        return []

    try:
        source_areas = areas if areas is not None else territory_store.list_player_areas()
        owner_areas = [
            area for area in safe_player_areas(source_areas)
            if area.get("owner_username") == owner_username
            and area.get("status", "active") == "active"
        ]
    except Exception as exc:
        print(f"[TERRITORY] static intruder area scan failed for {owner_username}: {exc}", flush=True)
        return []

    if not owner_areas:
        return []

    try:
        profiles = user_store.list_profiles()
    except Exception as exc:
        print(f"[TERRITORY] static intruder profile scan failed for {owner_username}: {exc}", flush=True)
        return []

    synced = []
    for actor_profile in profiles or []:
        actor_username = str((actor_profile or {}).get("username") or "").strip()
        if not actor_username or actor_username == owner_username:
            continue
        position = _profile_map_position(actor_profile)
        if not position:
            continue
        for area in owner_areas:
            if not territory_point_in_polygon_or_boundary(position, area.get("vertices") or []):
                continue
            area_id = area.get("id")
            if territory_store.recent_area_event_exists(
                owner_username,
                actor_username,
                "intruder_enter",
                area_id=area_id,
                seconds=60,
            ):
                break
            actor_name = actor_profile.get("nick") or actor_username
            territory_store.add_area_event(
                owner_username=owner_username,
                actor_username=actor_username,
                event_type="intruder_enter",
                area_id=area_id,
                lat=position["lat"],
                lng=position["lng"],
                payload={
                    "actor_nick": actor_name,
                    "area_status": area.get("status", "active"),
                    "source": reason,
                    "static_sync": True,
                },
            )
            record_map_player_actor_delta(
                actor_username,
                actor_profile,
                change_type="map.player_moved",
                reason=reason or "territory_static_intruder_sync",
                intrusion_area=area,
                dedupe_key_prefix=(
                    f"map:player_actor:{actor_username}:territory_intruder:"
                    f"{owner_username}:{area_id}:{runtime_file_now()}"
                ),
            )
            synced.append({
                "username": actor_username,
                "area_id": area_id,
                "lat": position["lat"],
                "lng": position["lng"],
            })
            break
    if synced:
        print(
            f"[TERRITORY] static intruders synced owner={owner_username} count={len(synced)} reason={reason}",
            flush=True,
        )
    return synced


def rebuild_player_areas_with_territory_delta(username, player_level=1, reason="territory_rebuild",
                                               resolve_encirclements=True):
    areas = territory_store.rebuild_player_areas(username, player_level)
    record_territory_areas_delta(username, areas, reason=reason)
    sync_static_area_intruders_for_owner(username, areas, reason=reason)
    if resolve_encirclements and not str(reason or "").startswith("territory_encirclement"):
        try:
            resolve_territory_encirclements_after_change(
                actor_username=username,
                changed_territory_id=None,
                reason=reason,
            )
        except Exception as exc:
            print(f"[TERRITORY] encirclement resolver failed after {reason}: {exc}", flush=True)
    return areas


_GIT_COMMIT_HASH = None
_GIT_BUILD_TAG = None


def is_perf_log_enabled():
    value = (os.environ.get("CHAOS_PERF_LOG") or "").strip().lower()
    return value in {"1", "true", "yes", "on"}


@app.before_request
def start_perf_timer():
    if is_perf_log_enabled() and request.path in PERF_LOG_ENDPOINTS:
        g.perf_log_started_at = time.perf_counter()


@app.after_request
def log_slow_or_large_response(response):
    started_at = getattr(g, "perf_log_started_at", None)
    if started_at is None:
        return response

    elapsed_ms = int(round((time.perf_counter() - started_at) * 1000))
    try:
        size = response.calculate_content_length()
    except Exception:
        size = response.content_length
    size = int(size or 0)

    if elapsed_ms >= PERF_LOG_MIN_MS or size >= PERF_LOG_MIN_SIZE:
        user = session.get("user") or "-"
        print(
            f"[PERF] {request.method} {request.path} "
            f"status={response.status_code} ms={elapsed_ms} size={size} user={user}",
            flush=True,
        )

    record_response_map_endpoint_measurement(
        request.path,
        elapsed_ms,
        status_code=response.status_code,
        payload_size=size,
        method=request.method,
    )

    return response


def is_dev_mode_enabled():
    env = (os.environ.get("APP_ENV") or os.environ.get("FLASK_ENV") or "development").strip().lower()
    explicit = (os.environ.get("CHAOS_DEV_MODE") or os.environ.get("DEV_MODE") or "").strip().lower()
    if explicit in {"1", "true", "yes", "on"}:
        return True
    if explicit in {"0", "false", "no", "off"}:
        return False
    return env in {"dev", "development", "staging", "test", "local"}


def require_dev_mode():
    if not is_dev_mode_enabled():
        return jsonify({"success": False, "message": "Dev Bug Reporter jest dostepny tylko w dev/staging."}), 403
    if "user" not in session:
        return jsonify({"success": False, "message": "Brak danych uzytkownika."}), 401
    return None


def get_git_commit_hash():
    global _GIT_COMMIT_HASH
    if _GIT_COMMIT_HASH is not None:
        return _GIT_COMMIT_HASH
    env_hash = os.environ.get("GIT_COMMIT") or os.environ.get("COMMIT_HASH") or os.environ.get("SOURCE_VERSION")
    if env_hash:
        _GIT_COMMIT_HASH = env_hash.strip()
        return _GIT_COMMIT_HASH
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
        _GIT_COMMIT_HASH = result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        _GIT_COMMIT_HASH = ""
    return _GIT_COMMIT_HASH


def get_git_build_tag():
    global _GIT_BUILD_TAG
    if _GIT_BUILD_TAG is not None:
        return _GIT_BUILD_TAG
    env_tag = os.environ.get("BUILD_TAG") or os.environ.get("APP_VERSION") or ""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always", "--dirty"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
        _GIT_BUILD_TAG = result.stdout.strip() if result.returncode == 0 else env_tag.strip()
    except Exception:
        _GIT_BUILD_TAG = env_tag.strip()
    return _GIT_BUILD_TAG


def build_dev_bug_server_context(username, client_context=None):
    client_context = client_context if isinstance(client_context, dict) else {}
    env = (os.environ.get("APP_ENV") or os.environ.get("FLASK_ENV") or "development").strip().lower()
    profile = user_store.get_profile(username) or {}
    operations = profile.get("operations", []) or []
    active_ops = active_operations_from_operations(operations) if operations else []
    aimed_target = profile.get("aimed_target") or {}
    return {
        **client_context,
        "server_timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "server": {
            "app_version": APP_VERSION,
            "git_tag": get_git_build_tag(),
            "commit_hash": get_git_commit_hash(),
            "app_env": env,
            "dev_mode": is_dev_mode_enabled(),
        },
        "session": {
            "username": username,
            "level": profile.get("level"),
            "hackcoins": profile.get("hackcoins"),
            "respect": profile.get("respect"),
        },
        "profile_snapshot": {
            "username": username,
            "nick": profile.get("nick"),
            "clan": profile.get("clan"),
            "level": profile.get("level"),
            "hackcoins": profile.get("hackcoins"),
            "respect": profile.get("respect"),
        },
        "active_operations_summary": [
            {
                "operation_id": op.get("operation_id"),
                "operation_type": op.get("operation_type"),
                "status": op.get("status"),
                "target_label": (op.get("target") or {}).get("label") or (op.get("target") or {}).get("name"),
                "expires_at": op.get("expires_at"),
                "remaining_seconds": op.get("remaining_seconds"),
            }
            for op in active_ops[:20]
        ],
        "aimed_target": {
            "label": aimed_target.get("label") or aimed_target.get("name"),
            "source_type": aimed_target.get("source_type"),
            "target_mode": aimed_target.get("target_mode"),
            "target_username": aimed_target.get("target_username"),
            "lat": aimed_target.get("lat"),
            "lng": aimed_target.get("lng"),
        } if aimed_target else {},
    }

PRO_SYSTEM_TOOLS = [
    {
        "id": "financialSniffer",
        "name": "Financial Sniffer",
        "icon": "\U0001F4B8",
        "category": "pro-system-tools",
        "type": "pro-system-tool",
        "description": "Jednorazowa proba drobnego sniffingu finansowego podczas aktywnego hacku gracza.",
        "price": 2500,
        "required_level": 8,
        "required_respect": 120,
        "allowed_fractions": [],
        "risk_level": 2,
        "purchase_account": "admin",
        "interface": "terminal",
        "levels": [{
            "title": "Financial Sniffer",
            "command": "financialSniffer --player-access",
            "logs": ["Uruchamiaj z panelu PLAYER ACCESS po shackowaniu gracza."]
        }],
    },
    {
        "id": "friendKicker",
        "name": "Friend Kicker",
        "icon": "\U0001F465",
        "category": "pro-system-tools",
        "type": "pro-system-tool",
        "description": "Losowa proba wypchniecia jednego kontaktu ofiary podczas aktywnego hacku gracza.",
        "price": 2200,
        "required_level": 7,
        "required_respect": 100,
        "allowed_fractions": [],
        "risk_level": 3,
        "purchase_account": "admin",
        "interface": "terminal",
        "levels": [{
            "title": "Friend Kicker",
            "command": "friendKicker --player-access",
            "logs": ["Uruchamiaj z panelu PLAYER ACCESS po shackowaniu gracza."]
        }],
    },
    {
        "id": "systemLogReader",
        "name": "System Log Reader",
        "icon": "\U0001F4DC",
        "category": "pro-system-tools",
        "type": "pro-system-tool",
        "description": "Odczyt ostatnich komunikatow systemowych ofiary podczas aktywnego hacku gracza.",
        "price": 900,
        "required_level": 2,
        "required_respect": 20,
        "allowed_fractions": [],
        "risk_level": 1,
        "purchase_account": "admin",
        "interface": "terminal",
        "levels": [{
            "title": "System Log Reader",
            "command": "systemLogReader --player-access",
            "logs": ["Uruchamiaj z panelu PLAYER ACCESS po shackowaniu gracza."]
        }],
    },
    {
        "id": "arsenalCleaner",
        "name": "Arsenal Cleaner",
        "icon": "\U0001F9F9",
        "category": "pro-system-tools",
        "type": "pro-system-tool",
        "description": "Losowa proba usuniecia jednej aplikacji z arsenalu ofiary podczas aktywnego hacku.",
        "price": 3500,
        "required_level": 12,
        "required_respect": 220,
        "allowed_fractions": [],
        "risk_level": 4,
        "purchase_account": "admin",
        "interface": "terminal",
        "levels": [{
            "title": "Arsenal Cleaner",
            "command": "arsenalCleaner --player-access",
            "logs": ["Uruchamiaj z panelu PLAYER ACCESS po shackowaniu gracza."]
        }],
    },
    {
        "id": "securityPanelProxy",
        "name": "Security Panel Proxy",
        "icon": "\U0001F6E1",
        "category": "pro-system-tools",
        "type": "pro-system-tool",
        "description": "Zdalny panel konfiguracji zabezpieczen profilu ofiary podczas aktywnego hacku.",
        "price": 3000,
        "required_level": 10,
        "required_respect": 180,
        "allowed_fractions": [],
        "risk_level": 5,
        "purchase_account": "admin",
        "interface": "terminal",
        "levels": [{
            "title": "Security Panel Proxy",
            "command": "securityPanelProxy --player-access",
            "logs": ["Uruchamiaj z panelu PLAYER ACCESS po shackowaniu gracza."]
        }],
    },
    {
        "id": "victimPicker",
        "name": "Victim Picker",
        "icon": "\u2316",
        "category": "pro-system-tools",
        "type": "pro-system-tool",
        "family_id": "ghost_control_suite",
        "icon_pack": "ghost_control",
        "description": "Lekki selektor celow z istniejacych zrodel mapy: oznaczone POI, gracze, podatnosci i konflikty.",
        "price": 100000,
        "required_level": 1,
        "required_respect": 0,
        "allowed_fractions": [],
        "risk_level": 0,
        "purchase_account": "admin",
        "interface": "system_launcher",
        "system_launcher": "createVictimPickerApp",
        "levels": [{
            "title": "Victim Picker",
            "command": "victim-picker --open",
            "logs": ["Victim Picker wymaga pulpitu systemowego. Uruchom z ikony aplikacji."]
        }],
    },
    {
        "id": "territoryControl",
        "name": "Territory Control",
        "icon": "\U0001F5FA",
        "category": "pro-system-tools",
        "type": "pro-system-tool",
        "family_id": "ghost_control_suite",
        "icon_pack": "ghost_control",
        "description": "Lekka konsola zarzadzania wlasnymi klastrami, filarami i zabezpieczeniami przejetych obiektow bez uruchamiania pelnej mapy.",
        "price": 50000,
        "required_level": 1,
        "required_respect": 0,
        "allowed_fractions": [],
        "risk_level": 0,
        "purchase_account": "admin",
        "interface": "system_launcher",
        "system_launcher": "territory_control",
        "levels": [{
            "title": "Territory Control",
            "command": "territory-control --open",
            "logs": ["Territory Control wymaga pulpitu systemowego. Uruchom z ikony aplikacji."]
        }],
    },
    {
        "id": "operationControl",
        "name": "Operation Control",
        "icon": "\U0001F4DF",
        "category": "pro-system-tools",
        "type": "pro-system-tool",
        "family_id": "ghost_control_suite",
        "icon_pack": "ghost_control",
        "description": "Konsola aktywnych operacji, generowanych plikow i incydentow Response Network z kontrola pojedynczego oraz grupowego anulowania.",
        "price": 20000,
        "required_level": 1,
        "required_respect": 0,
        "allowed_fractions": [],
        "risk_level": 0,
        "purchase_account": "admin",
        "interface": "system_launcher",
        "system_launcher": "operation_control",
        "levels": [{
            "title": "Operation Control",
            "command": "operation-control --open",
            "logs": ["Operation Control wymaga pulpitu systemowego. Uruchom z ikony aplikacji."]
        }],
    },
]

CREATOR_SYSTEM_APPS = [
    {
        "id": "buttonmaker",
        "name": "ButtonMaker",
        "icon": "\U0001F518",
        "type": "creator",
        "category": "creators",
        "description": "Warsztat do budowania aplikacji typu button_choices i publikacji w Googleplex.",
        "price": 800,
        "required_level": 3,
        "required_respect": 40,
        "allowed_fractions": [],
        "risk_level": 0,
        "purchase_account": "admin",
        "interface": "button_choices",
        "system_launcher": "createButtonMaker",
        "levels": [{
            "title": "ButtonMaker",
            "text": "Uruchamianie warsztatu ButtonMaker.",
            "options": []
        }],
    },
    {
        "id": "termcreator",
        "name": "TermCreator",
        "icon": "\u2328\uFE0F",
        "type": "creator",
        "category": "creators",
        "description": "Warsztat do budowania aplikacji terminalowych i publikacji w Googleplex.",
        "price": 1400,
        "required_level": 5,
        "required_respect": 80,
        "allowed_fractions": [],
        "risk_level": 0,
        "purchase_account": "admin",
        "interface": "terminal",
        "system_launcher": "createTermCreator",
        "levels": [{
            "title": "TermCreator",
            "command": "termcreator --forge",
            "logs": ["Uruchamianie warsztatu TermCreator."]
        }],
    },
    {
        "id": "windowmaker",
        "name": "WindowMaker",
        "icon": "\U0001FA9F",
        "type": "creator",
        "category": "creators",
        "description": "Warsztat do budowania aplikacji okienkowych i publikacji w Googleplex.",
        "price": 2200,
        "required_level": 7,
        "required_respect": 120,
        "allowed_fractions": [],
        "risk_level": 0,
        "purchase_account": "admin",
        "interface": "window",
        "system_launcher": "createWindowMaker",
        "levels": [{
            "title": "WindowMaker",
            "list": ["Uruchamianie warsztatu WindowMaker."],
            "buttons": []
        }],
    },
    {
        "id": "appforge",
        "name": "AppForge",
        "icon": "\U0001F6E0\uFE0F",
        "type": "creator",
        "category": "creators",
        "description": "Zaawansowany warsztat AppForge do publikowania aplikacji progressbar_random.",
        "price": 3500,
        "required_level": 9,
        "required_respect": 170,
        "allowed_fractions": [],
        "risk_level": 0,
        "purchase_account": "admin",
        "interface": "progressbar_random",
        "system_launcher": "createAppForge",
        "levels": [{
            "title": "AppForge",
            "steps": ["Uruchamianie kuznicy aplikacji..."],
            "result_success": "AppForge gotowy.",
            "result_failure": "AppForge niedostepny."
        }],
    },
    {
        "id": "ghost_lab",
        "name": "GhostLab",
        "icon": "\U0001F9EA",
        "type": "system_lab",
        "category": "pro-system-lab",
        "description": "Eksperymentalny hub GhostLab / ghost_lab / pro-system-lab do przyszlego projektowania narzedzi pro-system-tools.",
        "price": 7000,
        "required_level": 15,
        "required_respect": 350,
        "allowed_fractions": [],
        "risk_level": 0,
        "purchase_account": "admin",
        "interface": "system_launcher",
        "system_launcher": "ghost_lab",
        "levels": [{
            "title": "GhostLab",
            "command": "ghost_lab --hub",
            "logs": ["GhostLab Hub aktywny. Moduly projektowania pro-system-tools zostana odblokowane w kolejnym sprincie."]
        }],
    },
]

FACTION_NAMES = {
    "1": "Straznicy Ladu",
    "2": "Echo Wolnosci",
    "3": "VIREX",
    "4": "Siatka Widmo",
}

HACK_ACTION_STEP_ALIASES = {
    "scan_ports": "scan_ports",
    "exploit": "exploit",
    "sniff": "sniff",
    "trace": "trace",
    "camera_stream": "scan_ports",
    "camera_shutdown": "exploit",
    "trace_device": "trace",
    "mic_sniff": "sniff",
    "car_hack": "exploit",
    "trace_gps": "trace",
    "atm_logs": "sniff",
    "install_sniffer": "exploit",
    "scan_hotspots": "scan_ports",
    "audio_hack": "exploit",
}

MAP_ACTION_OPERATION_TYPES = {
    "trace": ["generic_trace"],
    "trace_gps": ["vehicle_tracking"],
    "trace_device": ["device_tracking"],
    "mic_sniff": ["microphone_sniffer"],
    "camera_stream": ["camera_stream"],
    "camera_shutdown": ["camera_shutdown"],
    "atm_logs": ["atm_log_extraction"],
    "install_sniffer": ["persistent_sniffer"],
    "scan_hotspots": ["wifi_scanner"],
    "audio_hack": ["audio_interference"],
    "car_hack": ["vehicle_ecu"],
}

DEFAULT_OPERATION_DURATIONS_SECONDS = {
    "vehicle_tracking": 2 * 60 * 60,
    "device_tracking": 60 * 60,
    "microphone_sniffer": 20 * 60,
    "camera_stream": 30 * 60,
    "camera_shutdown": 15 * 60,
    "atm_log_extraction": 10 * 60,
    "persistent_sniffer": 3 * 60 * 60,
    "wifi_scanner": 10 * 60,
    "audio_interference": 20 * 60,
    "vehicle_ecu": 10 * 60,
    "generic_trace": 60 * 60,
}

OPERATION_MOVEMENT_MODELS = {
    "vehicle_tracking": "road_movement",
    "vehicle_ecu": "road_movement",
    "device_tracking": "local_walk",
    "generic_trace": "local_walk",
    "camera_stream": "static_active_timer",
    "camera_shutdown": "static_active_timer",
    "persistent_sniffer": "implant_timer",
    "microphone_sniffer": "local_walk",
    "atm_log_extraction": "none",
    "wifi_scanner": "none",
    "audio_interference": "static_active_timer",
}

VEHICLE_TRACKING_CHECKPOINT_INTERVAL_SECONDS = 15 * 60
CAMERA_STREAM_FRAGMENT_INTERVAL_SECONDS = 5 * 60

SOURCE_TYPE_TARGET_TYPES = {
    "camera": "camera",
    "person": "person",
    "atm": "atm",
    "car": "vehicle",
    "vehicle": "vehicle",
    "parking": "vehicle_source",
    "restaurant": "venue",
    "bar": "venue",
    "cafe": "venue",
    "fast_food": "venue",
    "manual": "poi",
    "generated": "poi",
    "player": "player",
    "vulnerability": "pillar",
    "conflict_pillar": "pillar",
}

TERRITORY_REBUILD_CACHE = {}
TERRITORY_REBUILD_CACHE_SECONDS = 60

SECURITY_CONFLICTS = {
    "vpn_enabled": ["vpn_blocker"],
    "vpn_blocker": ["vpn_enabled"],
    "stealth_mode": ["activity_monitor", "player_tracking", "system_visibility"],
    "activity_monitor": ["stealth_mode"],
    "player_tracking": ["stealth_mode"],
    "system_visibility": ["stealth_mode"],
    "memory_lock": ["background_injection", "unencrypted_access"],
    "background_injection": ["memory_lock"],
    "unencrypted_access": ["memory_lock", "firewall"],
    "firewall": ["unencrypted_access"],
    "browser_protection": ["browser_history_log"],
    "browser_history_log": ["browser_protection"],
}

START_CITY_FALLBACKS = [
    {"city": "Warszawa", "lat": 52.2297, "lng": 21.0122},
    {"city": "Krakow", "lat": 50.0647, "lng": 19.9450},
    {"city": "Wroclaw", "lat": 51.1079, "lng": 17.0385},
    {"city": "Gdansk", "lat": 54.3520, "lng": 18.6466},
    {"city": "Poznan", "lat": 52.4064, "lng": 16.9252},
    {"city": "Lodz", "lat": 51.7592, "lng": 19.4560},
    {"city": "Berlin", "lat": 52.5200, "lng": 13.4050},
    {"city": "Prague", "lat": 50.0755, "lng": 14.4378},
    {"city": "London", "lat": 51.5074, "lng": -0.1278},
    {"city": "Paris", "lat": 48.8566, "lng": 2.3522},
    {"city": "Amsterdam", "lat": 52.3676, "lng": 4.9041},
    {"city": "Madrid", "lat": 40.4168, "lng": -3.7038},
    {"city": "Rome", "lat": 41.9028, "lng": 12.4964},
    {"city": "New York", "lat": 40.7128, "lng": -74.0060},
    {"city": "Toronto", "lat": 43.6532, "lng": -79.3832},
    {"city": "Sao Paulo", "lat": -23.5505, "lng": -46.6333},
    {"city": "Tokyo", "lat": 35.6762, "lng": 139.6503},
    {"city": "Seoul", "lat": 37.5665, "lng": 126.9780},
    {"city": "Singapore", "lat": 1.3521, "lng": 103.8198},
    {"city": "Sydney", "lat": -33.8688, "lng": 151.2093},
]


def point_in_polygon(lat, lng, vertices):
    if len(vertices or []) < 3:
        return False

    inside = False
    j = len(vertices) - 1
    for i, vertex in enumerate(vertices):
        yi = float(vertex.get("lat"))
        xi = float(vertex.get("lng"))
        yj = float(vertices[j].get("lat"))
        xj = float(vertices[j].get("lng"))
        crosses = (xi > lng) != (xj > lng)
        if crosses:
            slope_lat = (yj - yi) * (lng - xi) / ((xj - xi) or 1e-12) + yi
            if lat < slope_lat:
                inside = not inside
        j = i
    return inside


def _segment_orientation(a, b, c):
    value = (
        (float(b["lng"]) - float(a["lng"])) * (float(c["lat"]) - float(a["lat"]))
        - (float(b["lat"]) - float(a["lat"])) * (float(c["lng"]) - float(a["lng"]))
    )
    if abs(value) < 1e-12:
        return 0
    return 1 if value > 0 else -1


def _point_on_segment(a, b, c):
    return (
        min(float(a["lng"]), float(b["lng"])) - 1e-12 <= float(c["lng"]) <= max(float(a["lng"]), float(b["lng"])) + 1e-12
        and min(float(a["lat"]), float(b["lat"])) - 1e-12 <= float(c["lat"]) <= max(float(a["lat"]), float(b["lat"])) + 1e-12
    )


def _segments_intersect(a, b, c, d):
    o1 = _segment_orientation(a, b, c)
    o2 = _segment_orientation(a, b, d)
    o3 = _segment_orientation(c, d, a)
    o4 = _segment_orientation(c, d, b)

    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _point_on_segment(a, b, c):
        return True
    if o2 == 0 and _point_on_segment(a, b, d):
        return True
    if o3 == 0 and _point_on_segment(c, d, a):
        return True
    if o4 == 0 and _point_on_segment(c, d, b):
        return True
    return False


def _segment_intersection_point(a, b, c, d):
    x1, y1 = float(a["lng"]), float(a["lat"])
    x2, y2 = float(b["lng"]), float(b["lat"])
    x3, y3 = float(c["lng"]), float(c["lat"])
    x4, y4 = float(d["lng"]), float(d["lat"])
    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denominator) < 1e-12:
        return None
    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denominator
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denominator
    return {"lat": py, "lng": px, "label": "punkt styczny", "source_type": "intersection"}


def _dedupe_polygon_vertices(vertices, precision=7):
    unique = {}
    for vertex in vertices or []:
        try:
            key = (round(float(vertex["lat"]), precision), round(float(vertex["lng"]), precision))
        except (KeyError, TypeError, ValueError):
            continue
        unique[key] = {
            **vertex,
            "lat": float(vertex["lat"]),
            "lng": float(vertex["lng"]),
        }
    return list(unique.values())


def _hull_vertices(vertices):
    points = _dedupe_polygon_vertices(vertices)
    if len(points) <= 3:
        return points

    unique = {}
    for vertex in points:
        key = (round(float(vertex["lng"]), 7), round(float(vertex["lat"]), 7))
        unique[key] = vertex
    sorted_points = sorted(unique.items())

    def cross(origin, a, b):
        return (
            (a[0][0] - origin[0][0]) * (b[0][1] - origin[0][1])
            - (a[0][1] - origin[0][1]) * (b[0][0] - origin[0][0])
        )

    lower = []
    for point in sorted_points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)

    upper = []
    for point in reversed(sorted_points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)

    return [vertex for _, vertex in lower[:-1] + upper[:-1]]


def polygons_intersect(a_vertices, b_vertices):
    if len(a_vertices or []) < 3 or len(b_vertices or []) < 3:
        return False

    if any(point_in_polygon(float(v["lat"]), float(v["lng"]), b_vertices) for v in a_vertices):
        return True
    if any(point_in_polygon(float(v["lat"]), float(v["lng"]), a_vertices) for v in b_vertices):
        return True

    for i, a_start in enumerate(a_vertices):
        a_end = a_vertices[(i + 1) % len(a_vertices)]
        for j, b_start in enumerate(b_vertices):
            b_end = b_vertices[(j + 1) % len(b_vertices)]
            if _segments_intersect(a_start, a_end, b_start, b_end):
                return True
    return False


def target_coord_key(target):
    try:
        return (
            round(float(target.get("lat")), 5),
            round(float(target.get("lng", target.get("lon"))), 5),
            str(target.get("label") or target.get("name") or "")
        )
    except (TypeError, ValueError):
        return None


def conflict_area_key(area):
    vertices = area.get("vertices", []) or []
    vertex_key = "|".join(
        f"{round(float(vertex.get('lat')), 5)}:{round(float(vertex.get('lng')), 5)}"
        for vertex in vertices
        if vertex.get("lat") is not None and vertex.get("lng") is not None
    )
    return f"{area.get('owner_username')}:{vertex_key}"


def normalize_player_area(area):
    if not isinstance(area, dict):
        return None
    owner_username = str(area.get("owner_username") or area.get("owner") or area.get("login") or "").strip()
    if not owner_username:
        return None
    vertices = []
    for vertex in area.get("vertices") or []:
        if isinstance(vertex, dict):
            lat = vertex.get("lat")
            lng = vertex.get("lng", vertex.get("lon"))
        elif isinstance(vertex, (list, tuple)) and len(vertex) >= 2:
            lat, lng = vertex[0], vertex[1]
        else:
            continue
        try:
            lat = float(lat)
            lng = float(lng)
        except (TypeError, ValueError):
            continue
        vertices.append({"lat": lat, "lng": lng})
    if len(vertices) < 3:
        return None
    status = str(area.get("status") or "active").strip() or "active"
    normalized = dict(area)
    normalized["owner_username"] = owner_username
    normalized["vertices"] = vertices
    normalized["status"] = status
    if normalized.get("centroid_lat") is None:
        normalized["centroid_lat"] = sum(vertex["lat"] for vertex in vertices) / len(vertices)
    if normalized.get("centroid_lng") is None:
        normalized["centroid_lng"] = sum(vertex["lng"] for vertex in vertices) / len(vertices)
    return normalized


def safe_player_areas(areas):
    normalized = []
    skipped = 0
    for area in areas or []:
        clean = normalize_player_area(area)
        if clean:
            normalized.append(clean)
        else:
            skipped += 1
    if skipped:
        print(f"[WARN] skipped invalid territory areas: {skipped}", flush=True)
    return normalized


def territory_conflict_key(*areas):
    keys = sorted(conflict_area_key(area) for area in areas if area)
    return "::".join(keys)


def build_contested_area(area_a, area_b):
    vertices_a = area_a.get("vertices", []) or []
    vertices_b = area_b.get("vertices", []) or []
    if len(vertices_a) < 3 or len(vertices_b) < 3:
        return []
    if not polygons_intersect(vertices_a, vertices_b):
        return []

    points = []
    for vertex in vertices_a:
        if point_in_polygon(float(vertex["lat"]), float(vertex["lng"]), vertices_b):
            points.append({**vertex, "source_type": vertex.get("source_type") or "area_a"})
    for vertex in vertices_b:
        if point_in_polygon(float(vertex["lat"]), float(vertex["lng"]), vertices_a):
            points.append({**vertex, "source_type": vertex.get("source_type") or "area_b"})

    for i, start_a in enumerate(vertices_a):
        end_a = vertices_a[(i + 1) % len(vertices_a)]
        for j, start_b in enumerate(vertices_b):
            end_b = vertices_b[(j + 1) % len(vertices_b)]
            if not _segments_intersect(start_a, end_a, start_b, end_b):
                continue
            intersection = _segment_intersection_point(start_a, end_a, start_b, end_b)
            if intersection:
                points.append(intersection)

    return _hull_vertices(points)


def reveal_conflict_targets(area_a, area_b, contested_area):
    if len(contested_area or []) < 3:
        return []

    revealed = {}
    participants = [area_a.get("owner_username"), area_b.get("owner_username")]
    for owner in participants:
        if not owner:
            continue
        for target in territory_store.list_captured_targets(owner, stationary=True):
            key = target_coord_key(target)
            if not key or key in revealed:
                continue
            try:
                lat = float(target.get("lat"))
                lng = float(target.get("lng", target.get("lon")))
            except (TypeError, ValueError):
                continue
            if not point_in_polygon(lat, lng, contested_area):
                continue

            previous_owner = target.get("previous_owner_username")
            is_captured_conflict_target = bool(previous_owner and previous_owner != owner)
            revealed[key] = {
                "owner": owner,
                "owner_username": owner,
                "previous_owner": previous_owner,
                "status": "captured" if is_captured_conflict_target else "contested",
                "captured": is_captured_conflict_target,
                "captured_by": owner if is_captured_conflict_target else None,
                "hacked_by": owner if is_captured_conflict_target else None,
                "target": {
                    **target,
                    "lat": lat,
                    "lng": lng,
                    "lon": lng,
                },
            }

    return list(revealed.values())


def reveal_conflict_targets_for_group(areas, intersections):
    if not areas or not intersections:
        return []

    participants = sorted({
        area.get("owner_username")
        for area in areas
        if area.get("owner_username")
    })
    revealed = {}
    for owner in participants:
        for target in territory_store.list_captured_targets(owner, stationary=True):
            key = territory_conflict_store.stable_target_id(target)
            if not key or key in revealed:
                continue
            try:
                lat = float(target.get("lat"))
                lng = float(target.get("lng", target.get("lon")))
            except (TypeError, ValueError):
                continue
            if not any(point_in_polygon(lat, lng, intersection) for intersection in intersections if len(intersection or []) >= 3):
                continue

            previous_owner = target.get("previous_owner_username")
            is_captured_conflict_target = bool(previous_owner and previous_owner != owner)
            revealed[key] = {
                "target_id": key,
                "owner": owner,
                "owner_username": owner,
                "previous_owner": previous_owner,
                "status": "captured" if is_captured_conflict_target else "contested",
                "captured": is_captured_conflict_target,
                "captured_by": owner if is_captured_conflict_target else None,
                "hacked_by": owner if is_captured_conflict_target else None,
                "target": {
                    **target,
                    "target_id": key,
                    "lat": lat,
                    "lng": lng,
                    "lon": lng,
                },
            }

    return list(revealed.values())


def merge_conflict_target_statuses(conflict_reference, targets):
    existing_conflict = (
        conflict_reference
        if isinstance(conflict_reference, dict)
        else territory_conflict_store.get_by_key(conflict_reference)
    )
    if not existing_conflict:
        return targets

    existing_targets = existing_conflict.get("targets") or []
    existing_by_id = {
        territory_conflict_store.stable_target_id(item): item
        for item in existing_targets
    }
    merged = []
    used_existing_ids = set()

    for item in targets or []:
        target_id = territory_conflict_store.stable_target_id(item)
        target = item.get("target") or {}
        matched_item = existing_by_id.get(target_id)
        normalized = {
            **item,
            "target_id": target_id,
            "target": {**target, "target_id": target_id},
        }

        if matched_item and (matched_item.get("captured") or matched_item.get("status") == "captured"):
            preserved = dict(normalized)
            for key in ("previous_owner", "captured", "captured_by", "hacked_by", "status"):
                if key in matched_item:
                    preserved[key] = matched_item.get(key)
            preserved["owner"] = matched_item.get("owner") or matched_item.get("owner_username") or preserved.get("owner")
            preserved["owner_username"] = matched_item.get("owner_username") or matched_item.get("owner") or preserved.get("owner_username")
            preserved["target"] = {
                **(matched_item.get("target") or {}),
                **target,
                "target_id": target_id,
                "owner_username": preserved["owner_username"],
            }
            merged.append(preserved)
            used_existing_ids.add(target_id)
        else:
            merged.append(normalized)
            if matched_item is not None:
                used_existing_ids.add(target_id)

    for existing_item in existing_targets:
        existing_id = territory_conflict_store.stable_target_id(existing_item)
        if existing_id in used_existing_ids:
            continue
        if existing_item.get("captured") or existing_item.get("status") == "captured":
            merged.append(existing_item)

    return merged


def build_territory_conflict_detection_plan(areas, actor_username=None):
    """Build conflict components and fronts without mutating domain state."""
    areas = list(areas or [])
    active_areas = [area for area in areas if area.get("status", "active") == "active"]
    overlap_graph = {index: set() for index in range(len(active_areas))}
    pair_intersections = {}
    for index_a, area_a in enumerate(active_areas):
        for index_b in range(index_a + 1, len(active_areas)):
            area_b = active_areas[index_b]
            if area_a.get("owner_username") == area_b.get("owner_username"):
                continue
            if actor_username and actor_username not in {
                area_a.get("owner_username"),
                area_b.get("owner_username"),
            }:
                continue

            contested_area = build_contested_area(area_a, area_b)
            if len(contested_area) < 3:
                continue

            overlap_graph[index_a].add(index_b)
            overlap_graph[index_b].add(index_a)
            pair_intersections[(index_a, index_b)] = contested_area

    plans = []
    visited = set()
    for start_index, linked_indexes in overlap_graph.items():
        if start_index in visited or not linked_indexes:
            continue
        stack = [start_index]
        component = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(overlap_graph[current] - component)
        visited.update(component)

        component_areas = [active_areas[index] for index in sorted(component)]
        participants = sorted({
            area.get("owner_username")
            for area in component_areas
            if area.get("owner_username")
        })
        if len(participants) < 2:
            continue

        intersections = []
        fronts = []
        for index_a in component:
            for index_b in overlap_graph[index_a]:
                if index_b not in component or index_a > index_b:
                    continue
                intersection = pair_intersections.get((index_a, index_b))
                if intersection:
                    intersections.append(intersection)
                    pair_areas = [active_areas[index_a], active_areas[index_b]]
                    pair_participants = sorted({
                        area.get("owner_username") for area in pair_areas
                        if area.get("owner_username")
                    })
                    fronts.append({
                        "participant_key": territory_conflict_store.participant_key(pair_participants),
                        "area_ids": sorted(str(area.get("id")) for area in pair_areas
                                           if area.get("id") is not None),
                        "geometry": intersection,
                    })

        if not intersections:
            continue

        plans.append({
            "participants": participants,
            "participant_key": territory_conflict_store.participant_key(participants),
            "geometry_conflict_key": territory_conflict_key(*component_areas),
            "area_ids": [area.get("id") for area in component_areas if area.get("id") is not None],
            "component_areas": component_areas,
            "intersections": intersections,
            "fronts": fronts,
        })

    return plans


def materialize_territory_conflict_plans(plans, actor_username=None,
                                         source_event="territory_rebuild",
                                         publish_deltas=True):
    """Attach pure detection plans to durable conflict cycles."""
    conflicts = []
    for plan in plans or []:
        participants = plan["participants"]
        geometry_conflict_key = plan["geometry_conflict_key"]
        participant_key = plan["participant_key"]
        component_area_ids = plan["area_ids"]
        component_areas = plan["component_areas"]
        intersections = plan["intersections"]
        existing_conflict = territory_conflict_store.select_open_conflict(
            participant_key,
            conflict_key=geometry_conflict_key,
            area_ids=component_area_ids,
        )
        targets = merge_conflict_target_statuses(
            existing_conflict or geometry_conflict_key,
            reveal_conflict_targets_for_group(component_areas, intersections)
        )

        previous_conflict_version = int((existing_conflict or {}).get("conflict_version") or 0)
        previous_geometry_version = int((existing_conflict or {}).get("geometry_version") or 0)
        conflict = territory_conflict_store.upsert_conflict({
            "conflict_id": (existing_conflict or {}).get("conflict_id"),
            "conflict_key": geometry_conflict_key,
            "legacy_conflict_key": geometry_conflict_key,
            "participants": participants,
            "area_ids": component_area_ids,
            "intersection": intersections[0],
            "intersections": intersections,
            "targets": targets,
            "status": "active",
            "last_actor_username": actor_username or "",
            "source_event": source_event,
        })
        conflicts.append(conflict)
        if publish_deltas and (
            int(conflict.get("conflict_version") or 0) != previous_conflict_version
            or int(conflict.get("geometry_version") or 0) != previous_geometry_version
        ):
            record_territory_conflict_delta(conflict, reason=source_event)

    return conflicts


def detect_territory_conflicts(actor_username=None, source_event="territory_rebuild", areas=None):
    """Compatibility publisher built on top of the pure detection plan."""
    areas = areas or territory_store.list_player_areas()
    plans = build_territory_conflict_detection_plan(areas, actor_username=actor_username)
    conflicts = materialize_territory_conflict_plans(
        plans,
        actor_username=actor_username,
        source_event=source_event,
        publish_deltas=True,
    )
    active_conflict_keys = {
        str(conflict.get("conflict_id") or conflict.get("id"))
        for conflict in conflicts
    }
    touched_participants = {actor_username} if actor_username else set()
    for plan in plans:
        touched_participants.update(plan.get("participants") or [])

    if touched_participants:
        resolved_conflicts = territory_conflict_store.deactivate_stale_for_participants(
            touched_participants,
            active_conflict_keys,
            source_event=f"{source_event}:stale_resolved"
        )
        for resolved_conflict in resolved_conflicts:
            record_territory_conflict_delta(
                resolved_conflict,
                reason=f"{source_event}:stale_resolved",
            )

    return conflicts


def get_active_conflicts_for_player(username):
    return territory_conflict_store.list_active_for_player(username)


def build_conflict_participant_payload(conflict):
    usernames = [
        str(username)
        for username in (conflict.get("participants") or [])
        if username
    ]
    profiles = []
    names = []
    for participant_username in usernames:
        participant_profile = user_store.get_profile(participant_username) or {}
        participant_nick = participant_profile.get("nick") or participant_username
        names.append(participant_nick)
        profiles.append({
            "username": participant_username,
            "nick": participant_nick,
            "clan": get_profile_clan(participant_profile),
        })

    return {
        "participant_usernames": usernames,
        "participant_names": names,
        "participant_profiles": profiles,
        "participants_display": ", ".join(names),
    }


def enrich_conflict_payload(conflict):
    participant_payload = build_conflict_participant_payload(conflict)
    return {
        **conflict,
        **participant_payload,
        "participants": participant_payload["participant_usernames"],
    }


def request_conflict_rebuild(conflict_id, reason, requested_version=None):
    """Persist a rebuild request while retaining the highest input version."""
    conflict = territory_conflict_store.get_by_key(conflict_id)
    if not conflict:
        return None
    version = requested_version
    if version is None:
        version = conflict.get("conflict_version") or 1
    return territory_conflict_store.request_rebuild(
        conflict.get("conflict_id") or conflict_id,
        reason=reason,
        requested_version=version,
    )


def _conflict_front_plans(conflict, detection_plans):
    conflict_participants = set(conflict.get("participants") or [])
    conflict_area_ids = {str(item) for item in (conflict.get("area_ids") or [])}
    pillars = territory_conflict_store.list_pillars(conflict.get("conflict_id"))
    pillar_ids = sorted(str(pillar.get("target_id")) for pillar in pillars if pillar.get("target_id"))
    selected = []
    for plan in detection_plans:
        plan_participants = set(plan.get("participants") or [])
        plan_area_ids = {str(item) for item in (plan.get("area_ids") or [])}
        if plan_participants != conflict_participants and not (plan_area_ids & conflict_area_ids):
            continue
        for front in plan.get("fronts") or []:
            selected.append({**front, "pillar_ids": pillar_ids})
    return selected


def consolidate_conflict_rebuild(conflict_id, prebuilt_areas=None,
                                 prebuilt_detection_plans=None,
                                 rebuild_participants=True, run_encirclement=True,
                                 lease_seconds=180):
    """Run one durable, version-aware conflict geometry consolidation."""
    lease_owner = f"{os.getpid()}:{threading.get_ident()}:{time.time_ns()}"
    results = []
    for _pass_index in range(4):
        claim = territory_conflict_store.claim_rebuild(
            conflict_id, lease_owner=lease_owner, lease_seconds=lease_seconds
        )
        if not claim:
            return results[-1] if results else {"ok": False, "reason": "lease_unavailable"}
        conflict = claim["conflict"]
        started = time.perf_counter()
        timings = {
            "participant_rebuild": 0,
            "area_fetch": 0,
            "detection": 0,
            "front_plan": 0,
            "publication": 0,
        }
        try:
            phase_started = time.perf_counter()
            if rebuild_participants:
                for participant in sorted(set(conflict.get("participants") or [])):
                    profile = user_store.get_profile(participant) or {}
                    if not profile:
                        continue
                    rebuild_player_areas_with_territory_delta(
                        participant,
                        profile.get("level", 1),
                        reason=f"conflict_consolidation:{conflict.get('conflict_id')}",
                        resolve_encirclements=False,
                    )
            timings["participant_rebuild"] = int((time.perf_counter() - phase_started) * 1000)

            phase_started = time.perf_counter()
            areas = list(prebuilt_areas) if prebuilt_areas is not None else territory_store.list_player_areas()
            timings["area_fetch"] = int((time.perf_counter() - phase_started) * 1000)

            phase_started = time.perf_counter()
            detection_plans = (
                list(prebuilt_detection_plans)
                if prebuilt_detection_plans is not None
                else build_territory_conflict_detection_plan(areas)
            )
            timings["detection"] = int((time.perf_counter() - phase_started) * 1000)

            phase_started = time.perf_counter()
            front_plans = _conflict_front_plans(conflict, detection_plans)
            timings["front_plan"] = int((time.perf_counter() - phase_started) * 1000)

            phase_started = time.perf_counter()
            published = territory_conflict_store.publish_rebuild(
                conflict.get("conflict_id"),
                lease_owner=lease_owner,
                processing_version=claim["processing_version"],
                front_plans=front_plans,
                resolve=not bool(front_plans),
                resolution_reason="no_active_fronts" if not front_plans else "",
            )
            timings["publication"] = int((time.perf_counter() - phase_started) * 1000)
            published["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
            published["timings_ms"] = {**timings, "total": published["elapsed_ms"]}
            results.append(published)
            if published.get("ok") and published.get("changed"):
                snapshot = published.get("snapshot") or {}
                snapshot_conflict = snapshot.get("conflict") or conflict
                record_territory_conflict_delta(snapshot_conflict, reason="conflict_consolidated")
            if not published.get("pending_newer"):
                if run_encirclement and published.get("ok"):
                    resolve_territory_encirclements_after_change(
                        actor_username=(conflict.get("last_actor_username") or None),
                        changed_territory_id=None,
                        reason="conflict_consolidated",
                    )
                return published
            prebuilt_areas = None
            prebuilt_detection_plans = None
            rebuild_participants = True
        except Exception as exc:
            territory_conflict_store.fail_rebuild(
                conflict.get("conflict_id"), lease_owner,
                claim["processing_version"], exc,
            )
            return {
                "ok": False,
                "reason": "rebuild_failed",
                "error": str(exc),
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
                "timings_ms": {
                    **timings,
                    "total": int((time.perf_counter() - started) * 1000),
                },
            }
    return results[-1] if results else {"ok": False, "reason": "pass_limit"}


def rebuild_conflict_polygons(participants, actor_username=None, source_event="conflict_rebuild"):
    rebuilt = {}
    for participant in sorted({name for name in (participants or []) if name}):
        participant_profile = user_store.get_profile(participant) or {}
        if not participant_profile:
            continue
        rebuilt[participant] = rebuild_player_areas_with_territory_delta(
            participant,
            participant_profile.get("level", 1),
            reason=source_event,
            resolve_encirclements=False,
        )

    all_areas = territory_store.list_player_areas()
    detection_plans = build_territory_conflict_detection_plan(
        all_areas,
        actor_username=actor_username,
    )
    detected_conflicts = materialize_territory_conflict_plans(
        detection_plans,
        actor_username=actor_username,
        source_event=source_event,
        publish_deltas=False,
    )
    conflicts_by_id = {
        str(conflict.get("conflict_id") or conflict.get("id")): conflict
        for conflict in detected_conflicts
    }
    # Existing cycles missing from the new plan must be consolidated to a
    # successful no-front snapshot instead of being resolved speculatively.
    for participant in sorted({name for name in (participants or []) if name}):
        for conflict in territory_conflict_store.list_active_for_player(participant):
            conflict_id = str(conflict.get("conflict_id") or conflict.get("id"))
            conflicts_by_id.setdefault(conflict_id, conflict)

    for conflict in conflicts_by_id.values():
        conflict_id = conflict.get("conflict_id") or conflict.get("id")
        request_conflict_rebuild(
            conflict_id,
            reason=source_event,
            requested_version=conflict.get("conflict_version"),
        )
        consolidate_conflict_rebuild(
            conflict_id,
            prebuilt_areas=all_areas,
            prebuilt_detection_plans=detection_plans,
            rebuild_participants=False,
            run_encirclement=False,
        )
    if rebuilt:
        resolve_territory_encirclements_after_change(
            actor_username=actor_username,
            changed_territory_id=None,
            reason=source_event,
        )

    return rebuilt


def capture_conflict_pillar(captured_target, captured_by_username,
                            previous_owner_username=None, action_id=None):
    if not captured_target or not captured_by_username:
        return []

    captured_conflict_id = (
        captured_target.get("stable_conflict_id")
        or captured_target.get("conflict_id")
        or captured_target.get("legacy_conflict_id")
    )
    target_id = territory_conflict_store.stable_target_id(captured_target)
    conflict_reference = captured_conflict_id

    if conflict_reference in (None, ""):
        for conflict in territory_conflict_store.list_active():
            pillar_ids = {
                pillar.get("target_id")
                for pillar in territory_conflict_store.list_pillars(
                    conflict.get("conflict_id") or conflict.get("id")
                )
            }
            if target_id in pillar_ids:
                conflict_reference = conflict.get("conflict_id") or conflict.get("id")
                break
    if conflict_reference in (None, ""):
        return []

    result = territory_conflict_store.capture_pillar(
        conflict_reference,
        target_id,
        captured_target,
        captured_by_username,
        previous_owner_username=previous_owner_username,
        action_id=action_id,
    )
    conflict = result.get("conflict") if isinstance(result, dict) else None
    if isinstance(result, dict) and result.get("ok") and result.get("changed") and conflict:
        record_territory_conflict_delta(conflict, reason="pillar_captured")
        return [conflict]
    return []


def target_position_key(target, precision=5):
    try:
        return (
            round(float(target.get("lat")), precision),
            round(float(target.get("lng", target.get("lon"))), precision),
        )
    except (AttributeError, TypeError, ValueError):
        return None


def targets_share_position(left, right, precision=5):
    left_key = target_position_key(left, precision=precision)
    right_key = target_position_key(right, precision=precision)
    return bool(left_key and right_key and left_key == right_key)


def targets_share_runtime_identity(left, right):
    """Return true when two target snapshots point at the same gameplay object."""
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False

    left_mode = str(left.get("target_mode") or "").strip()
    right_mode = str(right.get("target_mode") or "").strip()

    if left_mode == "player" or right_mode == "player":
        return (
            left_mode == right_mode == "player"
            and str(left.get("target_username") or left.get("username") or "").strip()
            and str(left.get("target_username") or left.get("username") or "").strip()
            == str(right.get("target_username") or right.get("username") or "").strip()
        )

    left_vulnerability = str(left.get("vulnerability_id") or "").strip()
    right_vulnerability = str(right.get("vulnerability_id") or "").strip()
    if left_vulnerability or right_vulnerability:
        return bool(left_vulnerability and left_vulnerability == right_vulnerability)

    left_area = str(left.get("foreign_area_id") or "").strip()
    right_area = str(right.get("foreign_area_id") or "").strip()
    if left_area or right_area:
        return bool(left_area and left_area == right_area and targets_share_position(left, right, precision=5))

    if build_operation_target_id(left) == build_operation_target_id(right):
        return True

    # Map, terminal and desktop flows may carry different display labels for the
    # same POI. Coordinates are the stable runtime identity for this fallback.
    return targets_share_position(left, right, precision=5)


def is_generic_target_runtime_id(value):
    target_id = str(value or "").strip().lower()
    return (
        not target_id
        or target_id == "target"
        or target_id == "map:0.0.0.0:target"
        or "0.0.0.0" in target_id
    )


def targets_share_selection_identity(left, right):
    """Return true only when two targets represent the same current player selection."""
    if not isinstance(left, dict) or not isinstance(right, dict) or not left or not right:
        return False

    left_mode = str(left.get("target_mode") or "").strip()
    right_mode = str(right.get("target_mode") or "").strip()
    if left_mode == "player" or right_mode == "player":
        return (
            left_mode == right_mode == "player"
            and str(left.get("target_username") or left.get("username") or "").strip()
            and str(left.get("target_username") or left.get("username") or "").strip()
            == str(right.get("target_username") or right.get("username") or "").strip()
        )

    left_key = target_position_key(left)
    right_key = target_position_key(right)
    if left_key and right_key and left_key != right_key:
        return False

    left_label = target_label_value(left)
    right_label = target_label_value(right)
    if left_label and right_label and left_label != right_label:
        return False

    left_vulnerability = str(left.get("vulnerability_id") or "").strip()
    right_vulnerability = str(right.get("vulnerability_id") or "").strip()
    if left_vulnerability or right_vulnerability:
        return bool(left_vulnerability and left_vulnerability == right_vulnerability)

    left_area = str(left.get("foreign_area_id") or "").strip()
    right_area = str(right.get("foreign_area_id") or "").strip()
    if left_area or right_area:
        return bool(left_area and left_area == right_area and left_key and left_key == right_key)

    left_id = str(left.get("target_id") or left.get("id") or "").strip()
    right_id = str(right.get("target_id") or right.get("id") or "").strip()
    if left_id and right_id and left_id == right_id and not is_generic_target_runtime_id(left_id):
        return True

    return bool(left_key and right_key and left_key == right_key)


TERRITORY_ENCIRCLEMENT_EVENT_TYPE = "territory_encirclement_resolved"
TERRITORY_ENCIRCLEMENT_TOLERANCE_DEGREES = 1e-9


def _territory_point_on_segment(point, a, b, tolerance=TERRITORY_ENCIRCLEMENT_TOLERANCE_DEGREES):
    try:
        px = float(point.get("lng", point.get("lon")))
        py = float(point.get("lat"))
        ax = float(a.get("lng", a.get("lon")))
        ay = float(a.get("lat"))
        bx = float(b.get("lng", b.get("lon")))
        by = float(b.get("lat"))
    except (AttributeError, TypeError, ValueError):
        return False

    dx = bx - ax
    dy = by - ay
    length_sq = dx * dx + dy * dy
    if length_sq <= tolerance:
        return abs(px - ax) <= tolerance and abs(py - ay) <= tolerance
    projection = ((px - ax) * dx + (py - ay) * dy) / length_sq
    if projection < -tolerance or projection > 1 + tolerance:
        return False
    closest_x = ax + max(0, min(1, projection)) * dx
    closest_y = ay + max(0, min(1, projection)) * dy
    return abs(px - closest_x) <= tolerance and abs(py - closest_y) <= tolerance


def territory_point_in_polygon_or_boundary(point, vertices, tolerance=TERRITORY_ENCIRCLEMENT_TOLERANCE_DEGREES):
    if len(vertices or []) < 3:
        return False
    try:
        lat = float(point.get("lat"))
        lng = float(point.get("lng", point.get("lon")))
    except (AttributeError, TypeError, ValueError):
        return False
    if point_in_polygon(lat, lng, vertices):
        return True
    point_payload = {"lat": lat, "lng": lng}
    for index, start in enumerate(vertices):
        end = vertices[(index + 1) % len(vertices)]
        if _territory_point_on_segment(point_payload, start, end, tolerance=tolerance):
            return True
    return False


def territory_area_by_id(areas, area_id):
    area_id = str(area_id or "").strip()
    for area in areas or []:
        if str(area.get("id") or "") == area_id:
            return area
    return None


def territory_area_cluster_members(store, area):
    owner = str((area or {}).get("owner_username") or "").strip()
    vertices = (area or {}).get("vertices") or []
    if not owner or len(vertices) < 3:
        return {"pillars": [], "inners": [], "objects": [], "valid": False}

    vertex_keys = {target_position_key(vertex) for vertex in vertices}
    vertex_keys.discard(None)
    pillars = []
    inners = []
    for target in store.list_captured_targets(owner):
        key = target_position_key(target)
        if not key:
            continue
        if key in vertex_keys:
            pillars.append(target)
        elif territory_point_in_polygon_or_boundary(target, vertices):
            inners.append(target)
    objects = pillars + inners
    return {
        "pillars": pillars,
        "inners": inners,
        "objects": objects,
        "valid": len(pillars) >= 3,
    }


def _territory_relation_profile(username, profile_cache=None):
    username = str(username or "").strip()
    if not username:
        return {}
    if profile_cache is not None and username in profile_cache:
        return profile_cache.get(username) or {}
    try:
        profile = user_store.get_profile(username) or {}
    except Exception:
        profile = {}
    if profile_cache is not None:
        profile_cache[username] = profile
    return profile


def territory_owners_are_protected_relation(username_a, username_b, profile_cache=None):
    username_a = str(username_a or "").strip()
    username_b = str(username_b or "").strip()
    if not username_a or not username_b or username_a == username_b:
        return False

    profile_a = _territory_relation_profile(username_a, profile_cache=profile_cache)
    profile_b = _territory_relation_profile(username_b, profile_cache=profile_cache)
    clan_a = get_profile_clan(profile_a)
    clan_b = get_profile_clan(profile_b)
    if clan_a and clan_b and clan_a == clan_b:
        return True

    try:
        return bool(
            mail_store.is_accepted_contact(username_a, username_b)
            or mail_store.is_accepted_contact(username_b, username_a)
        )
    except Exception:
        return False


def territory_area_inside_area(inner_area, outer_area):
    inner_vertices = (inner_area or {}).get("vertices") or []
    outer_vertices = (outer_area or {}).get("vertices") or []
    if len(inner_vertices) < 3 or len(outer_vertices) < 3:
        return False
    return all(
        territory_point_in_polygon_or_boundary(vertex, outer_vertices)
        for vertex in inner_vertices
    )


def territory_area_size_value(area):
    try:
        return float((area or {}).get("area_size") or 0)
    except (TypeError, ValueError):
        return 0


def territory_area_encircled_by_protected_owner(area, all_areas, profile_cache=None):
    owner_username = str((area or {}).get("owner_username") or "").strip()
    if not owner_username:
        return False
    area_size = territory_area_size_value(area)
    for other_area in all_areas or []:
        if str(other_area.get("id") or "") == str((area or {}).get("id") or ""):
            continue
        other_owner = str(other_area.get("owner_username") or "").strip()
        if not territory_owners_are_protected_relation(owner_username, other_owner, profile_cache=profile_cache):
            continue
        other_size = territory_area_size_value(other_area)
        if other_size <= area_size:
            continue
        if territory_area_inside_area(area, other_area):
            return True
    return False


class TerritoryEncirclementResolver:
    """Resolves full cluster encirclement without becoming a new territory store."""

    def __init__(self, store=None, conflict_store=None):
        self.store = store or territory_store
        self.conflict_store = conflict_store or territory_conflict_store

    def detect_encircled_clusters(self, changed_territory_id=None, actor_username=None, apply=False, reason="territory_rebuild"):
        areas = safe_player_areas(self.store.list_player_areas())
        changed_id = str(changed_territory_id or "").strip()
        results = []
        for defender in areas:
            if changed_id and str(defender.get("id") or "") != changed_id:
                # A changed attacker can also close a ring, so only skip after
                # testing attackers below.
                pass
            for attacker in areas:
                if attacker.get("id") == defender.get("id"):
                    continue
                if changed_id and changed_id not in {str(attacker.get("id") or ""), str(defender.get("id") or "")}:
                    continue
                if not self.is_cluster_fully_encircled(attacker, defender):
                    continue
                snapshot = self.build_encirclement_snapshot(
                    attacker,
                    defender,
                    actor_username=actor_username,
                    reason=reason,
                )
                if apply:
                    snapshot = self.resolve_encirclement(
                        attacker.get("id"),
                        defender.get("id"),
                        actor_username=actor_username,
                        reason=reason,
                    )
                    if not snapshot:
                        continue
                results.append(snapshot)
        return results

    def is_cluster_fully_encircled(self, attacker, defender):
        attacker_owner = str((attacker or {}).get("owner_username") or "").strip()
        defender_owner = str((defender or {}).get("owner_username") or "").strip()
        if not attacker_owner or not defender_owner or attacker_owner == defender_owner:
            return False
        if territory_owners_are_protected_relation(attacker_owner, defender_owner):
            return False
        attacker_vertices = (attacker or {}).get("vertices") or []
        defender_vertices = (defender or {}).get("vertices") or []
        if len(attacker_vertices) < 3 or len(defender_vertices) < 3:
            return False

        attacker_members = territory_area_cluster_members(self.store, attacker)
        defender_members = territory_area_cluster_members(self.store, defender)
        if not attacker_members["valid"] or not defender_members["valid"]:
            return False

        for vertex in defender_vertices:
            if not territory_point_in_polygon_or_boundary(vertex, attacker_vertices):
                return False
        for target in defender_members["objects"]:
            if not territory_point_in_polygon_or_boundary(target, attacker_vertices):
                return False
        return True

    def build_encirclement_snapshot(self, attacker, defender, actor_username=None, reason="territory_rebuild"):
        attacker_members = territory_area_cluster_members(self.store, attacker)
        defender_members = territory_area_cluster_members(self.store, defender)
        now = runtime_file_now()
        return {
            "attacker_username": attacker.get("owner_username"),
            "defender_username": defender.get("owner_username"),
            "attacker_cluster_id": str(attacker.get("id")),
            "defender_cluster_id": str(defender.get("id")),
            "closing_player_id": actor_username or attacker.get("owner_username"),
            "closing_node_id": None,
            "territory_state_version": str(defender.get("updated_at") or defender.get("id") or now),
            "encircled_at": now,
            "reason": reason or "territory_rebuild",
            "captured_objects": [
                {
                    "lat": target.get("lat"),
                    "lng": target.get("lng", target.get("lon")),
                    "label": target.get("label") or target.get("name") or "",
                    "node_role": "pillar" if target in defender_members["pillars"] else "inner",
                }
                for target in defender_members["objects"]
            ],
            "attacker_snapshot": {
                "area_id": attacker.get("id"),
                "owner_username": attacker.get("owner_username"),
                "vertices": copy.deepcopy(attacker.get("vertices") or []),
                "object_count": len(attacker_members["objects"]),
            },
            "defender_snapshot": {
                "area_id": defender.get("id"),
                "owner_username": defender.get("owner_username"),
                "vertices": copy.deepcopy(defender.get("vertices") or []),
                "object_count": len(defender_members["objects"]),
            },
        }

    def resolve_encirclement(self, attacker_id, defender_id, actor_username=None, reason="territory_rebuild"):
        areas = safe_player_areas(self.store.list_player_areas())
        attacker = territory_area_by_id(areas, attacker_id)
        defender = territory_area_by_id(areas, defender_id)
        if not attacker or not defender or not self.is_cluster_fully_encircled(attacker, defender):
            return None

        snapshot = self.build_encirclement_snapshot(
            attacker,
            defender,
            actor_username=actor_username,
            reason=reason,
        )
        attacker_username = snapshot["attacker_username"]
        defender_username = snapshot["defender_username"]
        dedupe_key = (
            f"encirclement:{snapshot['attacker_cluster_id']}:"
            f"{snapshot['defender_cluster_id']}:{snapshot['territory_state_version']}"
        )
        if self.store.area_event_exists_with_payload_key(
            defender_username,
            attacker_username,
            TERRITORY_ENCIRCLEMENT_EVENT_TYPE,
            "dedupe_key",
            dedupe_key,
        ):
            snapshot["status"] = "deduped"
            return snapshot

        defender_members = territory_area_cluster_members(self.store, defender)
        captured_objects = []
        for target in defender_members["objects"]:
            transferred = copy.deepcopy(target)
            transferred["owner_username"] = attacker_username
            transferred["owner"] = attacker_username
            transferred["captured_by"] = attacker_username
            transferred["previous_owner"] = defender_username
            transferred["capture_reason"] = "territory_encirclement"
            transferred["territory_encirclement"] = {
                "attacker_cluster_id": snapshot["attacker_cluster_id"],
                "defender_cluster_id": snapshot["defender_cluster_id"],
                "dedupe_key": dedupe_key,
            }
            self.store.remove_captured_target(
                defender_username,
                transferred.get("lat"),
                transferred.get("lng", transferred.get("lon")),
                transferred.get("label"),
            )
            captured_objects.append(self.store.save_captured_target(attacker_username, transferred))

        attacker_level = territory_player_level(attacker_username)
        defender_level = territory_player_level(defender_username)
        attacker_areas = self.store.rebuild_player_areas(attacker_username, attacker_level)
        defender_areas = self.store.rebuild_player_areas(defender_username, defender_level)
        record_territory_areas_delta(attacker_username, attacker_areas, reason="territory_encirclement_attacker")
        record_territory_areas_delta(defender_username, defender_areas, reason="territory_encirclement_defender")
        sync_static_area_intruders_for_owner(
            attacker_username,
            attacker_areas,
            reason="territory_encirclement_attacker",
        )
        sync_static_area_intruders_for_owner(
            defender_username,
            defender_areas,
            reason="territory_encirclement_defender",
        )
        self._sync_profile_captured_targets(attacker_username)
        self._sync_profile_captured_targets(defender_username)

        closed_conflicts = self._close_conflicts(attacker, defender, captured_objects)
        snapshot["status"] = "resolved"
        snapshot["captured_count"] = len(captured_objects)
        snapshot["closed_conflict_count"] = len(closed_conflicts)
        snapshot["dedupe_key"] = dedupe_key
        self.store.add_area_event(
            defender_username,
            attacker_username,
            TERRITORY_ENCIRCLEMENT_EVENT_TYPE,
            area_id=defender.get("id"),
            payload={
                "dedupe_key": dedupe_key,
                "snapshot": snapshot,
            },
        )
        record_territory_encirclement_delta(
            attacker_username,
            defender_username,
            snapshot,
            dedupe_key=dedupe_key,
        )
        return snapshot

    def _sync_profile_captured_targets(self, username):
        try:
            profile = user_store.get_profile(username) or {}
        except Exception:
            return False
        if not isinstance(profile, dict):
            return False
        profile["hacked"] = self.store.list_captured_targets(username)
        profile["captured_targets_source"] = "sqlite"
        try:
            user_store.save_profile(profile)
            return True
        except Exception:
            return False

    def _close_conflicts(self, attacker, defender, captured_objects):
        closed = []
        attacker_id = attacker.get("id")
        defender_id = defender.get("id")
        captured_keys = {target_position_key(target) for target in captured_objects}
        captured_keys.discard(None)
        for conflict in self.conflict_store.list_active():
            area_ids = {str(item) for item in (conflict.get("area_ids") or []) if item is not None}
            should_close = str(attacker_id) in area_ids or str(defender_id) in area_ids
            if not should_close:
                for item in conflict.get("targets") or []:
                    if target_position_key(item.get("target") or {}) in captured_keys:
                        should_close = True
                        break
            if not should_close:
                continue
            updated = self.conflict_store.upsert_conflict({
                **conflict,
                "status": "resolved",
                "resolution_reason": "encirclement",
                "source_event": "territory_encirclement",
                "last_actor_username": attacker.get("owner_username") or "",
            })
            closed.append(updated)
            record_territory_conflict_delta(updated, reason="territory_encirclement")
        return closed


def territory_player_level(username):
    try:
        profile = load_profile_readonly(
            username,
            strip_sensitive=True,
            normalize_apps=False,
            normalize_files=False,
        )
    except Exception:
        profile = None
    if not isinstance(profile, dict):
        try:
            profile = user_store.get_profile(username) or {}
        except Exception:
            profile = {}
    try:
        return max(1, int((profile or {}).get("level") or 1))
    except (TypeError, ValueError):
        return 1


def resolve_territory_encirclements_after_change(actor_username=None, changed_territory_id=None, reason="territory_rebuild"):
    resolver = TerritoryEncirclementResolver(territory_store, territory_conflict_store)
    return resolver.detect_encircled_clusters(
        changed_territory_id=changed_territory_id,
        actor_username=actor_username,
        apply=True,
        reason=reason,
    )


def reconcile_territory_encirclements():
    resolver = TerritoryEncirclementResolver(territory_store, territory_conflict_store)
    return resolver.detect_encircled_clusters(apply=False, reason="reconcile")


def target_label_value(target):
    if not isinstance(target, dict):
        return ""
    return display_target_label(target)


UNNAMED_TARGET_VALUES = {
    "",
    "brak",
    "brak nazwy",
    "brak_nazwy",
    "no name",
    "unnamed",
    "unnamed target",
    "unknown",
    "none",
    "null",
}


def is_missing_target_name(value):
    if value is None:
        return True
    normalized = str(value).strip().lower()
    return normalized in UNNAMED_TARGET_VALUES


def target_fallback_prefix(target):
    target = target or {}
    target_type = str(target.get("target_type") or infer_target_type_from_target(target) or "").strip().lower()
    source_type = str(target.get("source_type") or "").strip().lower()

    if target_type in {"vehicle", "vehicle_source"} or source_type in {"car", "vehicle"}:
        return "ECU"
    if target_type in {"person", "player"} or source_type in {"person", "player"}:
        return "SUBJECT"
    if target_type == "phone" or source_type == "phone":
        return "DEVICE"
    if target_type == "camera" or source_type == "camera":
        return "CAM"
    if target_type == "atm" or source_type == "atm":
        return "ATM"
    if target_type in {"router", "server"} or source_type in {"router", "server", "hotspot"}:
        return "NET"
    if source_type in {"shop", "amenity", "restaurant", "bar", "cafe", "fast_food", "parking", "office"}:
        return "NODE"
    if target_type == "poi":
        return "POI"
    return "TARGET"


def deterministic_target_code(target):
    target = target or {}
    seed_parts = []
    for key in ("osm_id", "node_id", "id", "lat", "lng", "lon", "source_type", "target_type", "procedural_seed"):
        value = target.get(key)
        if value is not None and str(value).strip():
            seed_parts.append(f"{key}:{value}")
    if not seed_parts:
        seed_parts.append(json.dumps(target, sort_keys=True, default=str))
    digest = hashlib.sha1("|".join(seed_parts).encode("utf-8")).hexdigest()
    return digest[:6].upper()


def display_target_label(target, fallback_prefix=None):
    if not isinstance(target, dict):
        return "TARGET-000000"
    for key in ("display_label", "label", "name", "title"):
        value = target.get(key)
        if not is_missing_target_name(value):
            return str(value).strip()
    prefix = fallback_prefix or target_fallback_prefix(target)
    return f"{prefix}-{deterministic_target_code(target)}"


def apply_target_display_label(target):
    if not isinstance(target, dict):
        return target
    display_label = display_target_label(target)
    target["display_label"] = display_label
    if is_missing_target_name(target.get("label")):
        target["label"] = display_label
    if is_missing_target_name(target.get("name")):
        target["name"] = display_label
    return target


def filter_targets_by_position(targets, reference_target, match_label=False):
    reference_key = target_position_key(reference_target)
    if not reference_key:
        return list(targets or []), 0

    reference_label = target_label_value(reference_target)
    filtered = []
    removed = 0
    for target in targets or []:
        if target_position_key(target) != reference_key:
            filtered.append(target)
            continue
        if match_label and target_label_value(target) != reference_label:
            filtered.append(target)
            continue
        removed += 1
    return filtered, removed


def clear_aimed_target_if_matches(username, reference_target):
    runtime_cleared = False
    try:
        if player_target_runtime_store.clear_if_matches(username, reference_target, source="clear_aimed_target"):
            runtime_cleared = True
    except Exception as exc:
        print(f"[target runtime] clear failed user={username} error={exc}", flush=True)
    profile = user_store.get_profile(username) or {}
    aimed = profile.get("aimed_target") or {}
    if not aimed or not targets_share_selection_identity(aimed, reference_target):
        return bool(runtime_cleared)
    profile["aimed_target"] = {}
    user_store.save_profile(profile)
    return True


def infer_target_type_from_target(target):
    target = target or {}
    target_mode = str(target.get("target_mode") or "").strip()
    if target_mode == "player":
        return "player"
    if target_mode in {"territory_contest", "vulnerability"}:
        return "pillar"

    source_type = str(target.get("source_type") or "").strip()
    if source_type.startswith("shop"):
        return "venue"
    return SOURCE_TYPE_TARGET_TYPES.get(source_type, "poi")


def build_operation_target_id(target):
    target = target or {}
    if target.get("target_mode") == "player" and target.get("target_username"):
        return f"player:{target.get('target_username')}"
    if target.get("vulnerability_id"):
        return f"vulnerability:{target.get('vulnerability_id')}"
    if target.get("foreign_area_id"):
        key = target_position_key(target) or ("unknown", "unknown")
        return f"territory_contest:{target.get('foreign_area_id')}:{key[0]}:{key[1]}"
    key = target_position_key(target) or ("unknown", "unknown")
    label = target_label_value(target) or target.get("source_type") or "target"
    return f"map:{key[0]}:{key[1]}:{label}"


def target_has_stable_runtime_identity(target):
    """Return true only for targets that are safe to mutate/start operations for."""
    if not isinstance(target, dict) or not target:
        return False
    if str(target.get("target_mode") or "").strip() == "player":
        return bool(str(target.get("target_username") or target.get("username") or "").strip())
    if str(target.get("vulnerability_id") or "").strip():
        return True
    key = target_position_key(target)
    if not key:
        return False
    try:
        lat = float(key[0])
        lng = float(key[1])
    except (TypeError, ValueError):
        return False
    # 0,0 is a fallback sentinel in broken map/app flows, not a valid CHAOS POI.
    if abs(lat) < 1e-9 and abs(lng) < 1e-9:
        return False
    return True


def ghostnetwork_player_payload(username, profile):
    profile = profile if isinstance(profile, dict) else {}
    return {
        "player_id": username,
        "username": username,
        "clan_code": (
            profile.get("ghost_clan_code")
            or profile.get("clan_code")
            or profile.get("clan")
            or profile.get("fraction")
            or profile.get("faction")
            or ""
        ),
        "ghost_clan": profile.get("ghost_clan") or profile.get("clan") or "",
        "ghost_profession": profile.get("ghost_profession") or profile.get("profession") or "",
    }


def collect_ghostnetwork_domain_events(value):
    events = []
    if isinstance(value, dict):
        if value.get("event_id") and (value.get("event_type") or value.get("type")):
            events.append(value)
        for item in value.values():
            events.extend(collect_ghostnetwork_domain_events(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            events.extend(collect_ghostnetwork_domain_events(item))
    return events


def publish_ghostnetwork_delta_result(username, profile, result):
    events = collect_ghostnetwork_domain_events(result)
    if not events:
        return []
    viewer = ghostnetwork_player_payload(username, profile)
    viewer.update({
        "viewer_id": username,
        "viewer_clan": viewer.get("clan_code") or "",
        "viewer_profession": viewer.get("ghost_profession") or profile.get("profession") or "",
        "audience_scope": "player",
        "is_authenticated": True,
    })
    transaction_id = ""
    if len(events) > 1:
        seed = ":".join(str(event.get("event_id") or "") for event in events)
        transaction_id = f"ghostnetwork:{hashlib.sha1(seed.encode('utf-8')).hexdigest()[:16]}"
    publisher = GhostNetworkDeltaPublisher(delta_bus=delta_bus)
    published = []
    for index, event in enumerate(events):
        transaction = None
        if transaction_id:
            transaction = {
                "transaction_id": transaction_id,
                "transaction_index": index,
                "transaction_size": len(events),
            }
        published.extend(publisher.publish_event(event, [viewer], transaction=transaction))
    return published


def safe_ghostnetwork_on_target_aimed(username, profile, target, reason="aimed_target"):
    target = target if isinstance(target, dict) else {}
    target_id = str(target.get("target_id") or build_operation_target_id(target) or "").strip()
    cycle_id = "unknown"
    try:
        service = GhostNetworkService()
        active_cycle = service.get_active_cycle()
        cycle_id = (active_cycle or {}).get("cycle_id") or "none"
        return service.on_target_aimed(
            ghostnetwork_player_payload(username, profile),
            target,
            context={"reason": str(reason or "aimed_target")},
        )
    except Exception as exc:
        print(
            f"[ghostnetwork] on_target_aimed failed cycle_id={cycle_id} "
            f"player={username} target_id={target_id} error={exc}",
            flush=True,
        )
        return {"ok": False, "status": "hook_failed", "cycle_id": cycle_id}


def safe_ghostnetwork_on_target_hacked(username, profile, target, operation=None, result=None, reason="target_hacked"):
    target = dict(target or {}) if isinstance(target, dict) else {}
    if target and not target.get("target_id"):
        target["target_id"] = build_operation_target_id(target)
    target_id = str(target.get("target_id") or "").strip()
    cycle_id = "unknown"
    try:
        service = GhostNetworkService()
        active_cycle = service.get_active_cycle()
        cycle_id = (active_cycle or {}).get("cycle_id") or "none"
        result_payload = service.on_target_hacked(
            ghostnetwork_player_payload(username, profile),
            target,
            operation=operation,
            result=result or {"target_captured": True},
            context={"reason": str(reason or "target_hacked"), "target_captured": True},
        )
        publish_ghostnetwork_delta_result(username, profile, result_payload)
        return result_payload
    except Exception as exc:
        print(
            f"[ghostnetwork] on_target_hacked failed cycle_id={cycle_id} "
            f"player={username} target_id={target_id} error={exc}",
            flush=True,
        )
        return {"ok": False, "status": "hook_failed", "cycle_id": cycle_id}


def set_player_aimed_target(username, profile, aimed_target, update_fields=None, reason="aimed_target"):
    profile = profile if isinstance(profile, dict) else {}
    aimed_target = dict(aimed_target or {})
    if aimed_target and not aimed_target.get("target_id"):
        aimed_target["target_id"] = build_operation_target_id(aimed_target)
    if find_owned_captured_target_for_runtime_target(username, aimed_target):
        try:
            player_target_runtime_store.mark_captured(username, aimed_target, source=f"{reason}:already_captured")
        except Exception as exc:
            print(f"[target runtime] captured mark failed user={username} error={exc}", flush=True)
        aimed_target = {}
    elif aimed_target:
        try:
            result = player_target_runtime_store.upsert_aimed(username, aimed_target, source=reason)
            aimed_target = dict(result.get("target") or aimed_target)
        except Exception as exc:
            print(f"[target runtime] upsert failed user={username} reason={reason} error={exc}", flush=True)
    fields = dict(update_fields or {})
    fields = merge_latest_profile_runtime_fields(username, fields)
    fields["aimed_target"] = aimed_target
    UserProfileManager(username).update_profile(fields)
    for key, value in fields.items():
        profile[key] = value
    profile["aimed_target"] = aimed_target
    if aimed_target:
        safe_ghostnetwork_on_target_aimed(username, profile, aimed_target, reason=reason)
    return aimed_target


def _operation_is_terminal_for_merge(operation):
    status = str((operation or {}).get("status") or "").strip().lower()
    return status in {"cancelled", "canceled", "done", "completed", "failed", "expired", "timeout", "resolved", "detected"}


def _operation_logical_merge_key(operation):
    operation = operation if isinstance(operation, dict) else {}
    if _operation_is_terminal_for_merge(operation):
        operation_id = str(operation.get("operation_id") or operation.get("id") or "").strip()
        return ("terminal", operation_id) if operation_id else None
    parts = (
        str(operation.get("target_id") or "").strip(),
        str(operation.get("map_action_id") or "").strip(),
        str(operation.get("operation_type") or "").strip(),
        str(operation.get("source_app_id") or operation.get("source_app_name") or "").strip(),
    )
    return ("active", *parts) if any(parts) else None


def merge_operations_monotonic(latest_operations, incoming_operations):
    """Merge operation runtime lists without letting a stale request drop newer work."""
    merged = []
    ids = {}
    logical = {}

    def add(operation, prefer_update=False):
        if not isinstance(operation, dict):
            return
        operation_id = str(operation.get("operation_id") or operation.get("id") or "").strip()
        if operation_id and operation_id in ids:
            if prefer_update:
                index = ids[operation_id]
                current = dict(merged[index])
                current.update(operation)
                merged[index] = current
            return

        logical_key = _operation_logical_merge_key(operation)
        if logical_key and logical_key in logical:
            return

        index = len(merged)
        merged.append(dict(operation))
        if operation_id:
            ids[operation_id] = index
        if logical_key:
            logical[logical_key] = index

    for operation in latest_operations or []:
        add(operation)
    for operation in incoming_operations or []:
        add(operation, prefer_update=True)
    return merged


def merge_launch_queue_monotonic(latest_queue, incoming_queue):
    merged = []
    seen = set()
    for item in list(latest_queue or []) + list(incoming_queue or []):
        if isinstance(item, dict):
            value = str(
                item.get("receipt")
                or item.get("launch_receipt")
                or item.get("launch_key")
                or item.get("name")
                or item.get("app_name")
                or ""
            ).strip()
        else:
            value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        merged.append(item)
    return merged


def filter_accepted_created_operations(profile, created_operations):
    """Return only operations that survived the latest runtime merge/write."""
    if not isinstance(profile, dict) or not created_operations:
        return []
    accepted_ids = {
        str(operation.get("operation_id") or operation.get("id") or "").strip()
        for operation in profile.get("operations", []) or []
        if isinstance(operation, dict)
    }
    if not accepted_ids:
        return []
    return [
        operation
        for operation in created_operations or []
        if isinstance(operation, dict)
        and str(operation.get("operation_id") or operation.get("id") or "").strip() in accepted_ids
    ]


def operations_from_store_or_profile(username, profile, refresh=False, include_terminal=True):
    profile = profile if isinstance(profile, dict) else {}
    stored_operations = []
    if username:
        try:
            stored_operations = player_operation_store.list_operations(username, include_terminal=include_terminal)
            if not stored_operations and profile.get("operations"):
                stored_operations = player_operation_store.seed_from_profile(username, profile)
        except Exception as exc:
            print(f"[OPERATIONS] store read skipped: {exc}")

    operations = stored_operations or profile.get("operations", []) or []
    if refresh:
        working_profile = dict(profile)
        working_profile["operations"] = list(operations)
        operations, changed = refresh_operations_runtime(working_profile, persist_timeouts=False, username=username)
        if changed and username:
            try:
                player_operation_store.upsert_operations(
                    username,
                    operations,
                    event_type="operation.refresh",
                    source="runtime_refresh",
                )
            except Exception as exc:
                print(f"[OPERATIONS] store refresh skipped: {exc}")
        profile["operations"] = operations
    return operations


def merge_latest_profile_runtime_fields(username, fields):
    """Protect runtime fields from last-write-wins races across gunicorn workers."""
    if not username or not isinstance(fields, dict):
        return fields
    needs_latest = any(key in fields for key in ("operations", "launch_queue"))
    if not needs_latest:
        return fields
    try:
        latest_profile = user_store.get_profile(username) or {}
    except Exception:
        return fields
    merged = dict(fields)
    if "operations" in merged:
        merged["operations"] = merge_operations_monotonic(
            latest_profile.get("operations", []),
            merged.get("operations", []),
        )
    if "launch_queue" in merged:
        incoming_queue = merged.get("launch_queue", [])
        if isinstance(incoming_queue, list) and not incoming_queue:
            # Empty list is an intentional consume/clear from /launch-queue.
            # Do not resurrect already delivered apps from the latest profile.
            merged["launch_queue"] = []
        else:
            merged["launch_queue"] = merge_launch_queue_monotonic(
                latest_profile.get("launch_queue", []),
                incoming_queue,
            )
    return merged


def normalize_profile_position_update(position, username=None, source="runtime"):
    """Keep legacy and canonical position fields in sync during partial updates."""
    if not isinstance(position, dict):
        return {}
    try:
        lat = float(position.get("lat"))
        lng = float(position.get("lng", position.get("lon")))
    except (TypeError, ValueError):
        return {}
    normalized = {"lat": lat, "lng": lng}
    position_meta = {}
    if username:
        try:
            store_result = player_position_store.upsert(username, normalized, source=source)
            stored = store_result.get("position") or normalized
            normalized = {"lat": float(stored["lat"]), "lng": float(stored["lng"])}
            position_meta = {
                "position_version": store_result.get("version"),
                "position_updated_at": store_result.get("updated_at"),
            }
        except Exception as exc:
            print(f"[position runtime] store update failed user={username} source={source} error={exc}", flush=True)
    result = {
        "curently_possition": dict(normalized),
        "current_position": dict(normalized),
    }
    result.update({key: value for key, value in position_meta.items() if value is not None})
    return result


def apply_runtime_stores_to_profile(username, profile):
    profile = profile if isinstance(profile, dict) else {}
    if not username:
        return profile

    try:
        position_payload = player_position_store.get(username)
        if not position_payload:
            player_position_store.seed_from_profile(username, profile)
            position_payload = player_position_store.get(username)
        if position_payload:
            position = {"lat": position_payload.get("lat"), "lng": position_payload.get("lng")}
            profile.update(normalize_profile_position_update(position))
            profile["position_version"] = position_payload.get("version")
            profile["position_updated_at"] = position_payload.get("updated_at")
    except Exception as exc:
        print(f"[position runtime] profile overlay failed user={username} error={exc}", flush=True)

    try:
        target = player_target_runtime_store.get_active_target(username)
        if not target:
            target = player_target_runtime_store.seed_from_profile(username, profile)
        if target:
            profile["aimed_target"] = target
        else:
            runtime = player_target_runtime_store.get(username)
            if runtime and runtime.get("status") in {"cleared", "captured"}:
                profile["aimed_target"] = {}
    except Exception as exc:
        print(f"[target runtime] profile overlay failed user={username} error={exc}", flush=True)

    try:
        player_inventory_store.mirror_profile(username, profile)
        mirrored_storage = storage_delta_snapshot(profile)
        normalize_profile_storage(profile)
        if storage_delta_snapshot(profile) != mirrored_storage:
            try:
                player_inventory_store.write_from_profile(username, profile)
            except Exception as repair_exc:
                print(f"[inventory runtime] storage repair failed user={username} error={repair_exc}", flush=True)
    except Exception as exc:
        print(f"[inventory runtime] profile overlay failed user={username} error={exc}", flush=True)

    try:
        wallet_balance_store.mirror_profile(username, profile)
    except Exception as exc:
        print(f"[wallet runtime] profile overlay failed user={username} error={exc}", flush=True)
    return profile


def operation_utc_iso(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def operation_expiry_iso(now, operation_type):
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)
    duration = DEFAULT_OPERATION_DURATIONS_SECONDS.get(operation_type, 10 * 60)
    expires_at = now + timedelta(seconds=duration)
    return operation_utc_iso(expires_at)


def operation_duration_seconds(operation_type):
    return DEFAULT_OPERATION_DURATIONS_SECONDS.get(operation_type, 10 * 60)


OPERATION_ACTIVE_STATUSES = {"start", "running"}
OPERATION_TERMINAL_STATUSES = {"completed", "failed", "detected", "cancelled", "timeout"}
OPERATION_FINALIZABLE_STATUSES = {"completed", "timeout"}
OPERATION_RISK_ASSESSABLE_STATUSES = {"completed", "timeout", "cancelled", "detected"}


def movement_model_for_operation(operation_type, target_type):
    operation_type = str(operation_type or "").strip()
    target_type = str(target_type or "").strip()
    if target_type == "player":
        return "player_position"
    if operation_type in OPERATION_MOVEMENT_MODELS:
        return OPERATION_MOVEMENT_MODELS[operation_type]
    if target_type == "vehicle":
        return "road_movement"
    if target_type in {"person", "phone"}:
        return "local_walk"
    return "none"


def stable_procedural_seed(*parts):
    seed_source = "|".join(str(part or "") for part in parts)
    digest = hashlib.sha256(seed_source.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def initial_risk_state_for_operation(operation_type):
    if operation_type == "atm_log_extraction":
        return {
            "level": "high",
            "events": ["atm_alarm"],
            "score": 70,
            "hint": "high-value/high-risk financial terminal operation",
            "consequences_enabled": False,
        }
    if operation_type == "persistent_sniffer":
        return {
            "level": "medium",
            "events": ["long_operation_detected", "sniffer_detected"],
            "score": 55,
            "hint": "long-operation implant/high-value data risk",
            "consequences_enabled": False,
        }
    return {
        "level": "none",
        "events": [],
        "score": 0,
    }


RISK_EVENT_BASE_SCORES = {
    "suspicious_network_activity": 35,
    "long_operation_detected": 45,
    "atm_alarm": 72,
    "camera_detected": 46,
    "sniffer_detected": 58,
    "abandoned_operation": 38,
}

RISK_EVENT_MESSAGES = {
    "suspicious_network_activity": "Podejrzana aktywnosc sieciowa zostawila slad w systemie.",
    "long_operation_detected": "Dluga operacja zwiekszyla widocznosc Twojej aktywnosci.",
    "atm_alarm": "Terminal finansowy wykryl nietypowa probe odczytu danych.",
    "camera_detected": "System obserwacji zarejestrowal anomalie przy kamerze.",
    "sniffer_detected": "Implant/sniffer zostawil sygnature w monitoringu celu.",
    "abandoned_operation": "Porzucona operacja zostawila slaby slad w systemie.",
}


def risk_consequences_for_score(score):
    if score >= 70:
        return ["warning", "partial_detection", "cooldown_placeholder"]
    if score >= 45:
        return ["warning", "partial_detection"]
    return ["warning"]


def risk_level_for_score(score):
    if score >= 85:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 45:
        return "medium"
    if score > 0:
        return "low"
    return "none"


def append_profile_system_message(profile, msg_type, title, text):
    messages = profile.setdefault("system_messages", [])
    if not isinstance(messages, list):
        messages = []
        profile["system_messages"] = messages
    numeric_ids = [
        int(item.get("id", 0))
        for item in messages
        if isinstance(item, dict) and str(item.get("id", "")).isdigit()
    ]
    messages.append({
        "id": max(numeric_ids, default=0) + 1,
        "type": msg_type,
        "title": title,
        "text": text,
        "status": "new",
        "created_at": runtime_file_now(),
    })


def append_risk_event(
    profile,
    event_type,
    source,
    score,
    operation=None,
    action=None,
    dedupe_key=None,
    modifiers=None,
    base_score=None,
):
    event_type = str(event_type or "").strip()
    if event_type not in RISK_EVENT_BASE_SCORES:
        return None

    risk_events = profile.setdefault("risk_events", [])
    if not isinstance(risk_events, list):
        risk_events = []
        profile["risk_events"] = risk_events
    if dedupe_key and any(isinstance(item, dict) and item.get("dedupe_key") == dedupe_key for item in risk_events):
        return None

    score = max(0, min(100, int(score or RISK_EVENT_BASE_SCORES.get(event_type, 0))))
    base_score = score if base_score is None else max(0, min(100, int(base_score or 0)))
    modifiers = [item for item in (modifiers or []) if isinstance(item, dict)]
    consequences = risk_consequences_for_score(score)
    created_at = runtime_file_now()
    operation = operation or {}
    target = operation.get("target") if isinstance(operation.get("target"), dict) else {}
    record = {
        "id": f"risk_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{randint(100000, 999999)}",
        "event_type": event_type,
        "risk_event": event_type,
        "source": source,
        "risk_signal": event_type,
        "base_risk_score": base_score,
        "risk_score": score,
        "risk_level": risk_level_for_score(score),
        "modifiers": modifiers,
        "modifier_summary": [
            item.get("modifier")
            for item in modifiers
            if item.get("modifier")
        ],
        "consequences": consequences,
        "primary_consequence": consequences[-1] if consequences else "warning",
        "operation_id": operation.get("operation_id"),
        "operation_type": operation.get("operation_type"),
        "map_action_id": action or operation.get("map_action_id"),
        "target_id": operation.get("target_id"),
        "target_label": target.get("label") or target.get("name") or "",
        "created_at": created_at,
        "status": "new",
        "dedupe_key": dedupe_key or "",
    }
    risk_events.append(record)
    modifier_text = ""
    if modifiers:
        modifier_text = " Modifier: " + ", ".join(
            str(item.get("message") or item.get("modifier"))
            for item in modifiers
            if item.get("message") or item.get("modifier")
        )
    append_profile_system_message(
        profile,
        "warning",
        "Risk event",
        f"{event_type}: {RISK_EVENT_MESSAGES.get(event_type, 'Operacja wygenerowala ryzyko.')}{modifier_text}",
    )
    return record


def operation_time_window(operation):
    started_ts = parse_operation_timestamp(operation.get("started_at"))
    expires_ts = parse_operation_timestamp(operation.get("expires_at"))
    ended_ts = parse_operation_timestamp(operation.get("ended_at"))
    if started_ts is None:
        return None
    end_ts = ended_ts or expires_ts
    if end_ts is None:
        end_ts = datetime.now(timezone.utc).timestamp()
    return started_ts, end_ts


def operation_windows_overlap(left, right):
    left_window = operation_time_window(left)
    right_window = operation_time_window(right)
    if not left_window or not right_window:
        return False
    return max(left_window[0], right_window[0]) <= min(left_window[1], right_window[1])


def operation_target_distance_m(left, right):
    left_pos = operation_base_position(left)
    right_pos = operation_base_position(right)
    if not left_pos or not right_pos:
        return None
    try:
        return Haversine.haversine_distance(left_pos[0], left_pos[1], right_pos[0], right_pos[1])
    except (TypeError, ValueError):
        return None


def support_operation_matches_target(operation, support_operation, max_distance_m=80):
    if operation.get("target_id") and operation.get("target_id") == support_operation.get("target_id"):
        return True, 0
    target = operation.get("target") if isinstance(operation.get("target"), dict) else {}
    support_target = support_operation.get("target") if isinstance(support_operation.get("target"), dict) else {}
    if target and support_target and targets_share_position(target, support_target):
        return True, 0
    distance = operation_target_distance_m(operation, support_operation)
    if distance is not None and distance <= max_distance_m:
        return True, round(distance, 2)
    return False, distance


def operation_is_active(operation, now_ts=None):
    if not isinstance(operation, dict):
        return False
    if operation.get("status") not in OPERATION_ACTIVE_STATUSES:
        return False
    try:
        now_ts = now_ts if now_ts is not None else datetime.now(timezone.utc).timestamp()
        remaining = operation_remaining_seconds(operation, now_ts)
    except Exception:
        remaining = None
    return remaining is None or remaining > 0


def support_operation_is_active_for_modifier(operation, now_ts=None):
    if not operation_is_active(operation, now_ts=now_ts):
        return False
    support_state = operation.get("support_state") if isinstance(operation.get("support_state"), dict) else {}
    if support_state and support_state.get("active") is False:
        return False
    return True


def find_risk_modifiers(profile, operation, event_type):
    if event_type != "camera_detected":
        return []
    if operation.get("operation_type") == "camera_shutdown":
        return []

    modifiers = []
    for support_operation in profile.get("operations", []) or []:
        if not isinstance(support_operation, dict):
            continue
        if support_operation is operation:
            continue
        if support_operation.get("operation_type") != "camera_shutdown":
            continue
        if not support_operation_is_active_for_modifier(support_operation):
            continue
        if not operation_windows_overlap(operation, support_operation):
            continue

        matches_target, distance = support_operation_matches_target(operation, support_operation)
        if not matches_target:
            continue

        modifiers.append({
            "modifier": "camera_shutdown",
            "effect": "risk_reducer",
            "event_type": "camera_detected",
            "reduction": 18,
            "support_operation_id": support_operation.get("operation_id"),
            "distance_m": distance,
            "message": "protected_by_camera_shutdown",
        })

    if not modifiers:
        return []
    modifiers.sort(key=lambda item: (
        999999 if item.get("distance_m") is None else item.get("distance_m"),
        str(item.get("support_operation_id") or ""),
    ))
    return [modifiers[0]]


def apply_risk_modifiers(profile, operation, event_type, score):
    base_score = max(0, min(100, int(score or 0)))
    modifiers = find_risk_modifiers(profile, operation, event_type)
    final_score = base_score
    for modifier in modifiers:
        final_score -= int(modifier.get("reduction") or 0)
    final_score = max(0, min(100, final_score))
    if modifiers:
        risk_state = operation.setdefault("risk_state", initial_risk_state_for_operation(operation.get("operation_type")))
        support_effects = risk_state.setdefault("support_effects", [])
        for modifier in modifiers:
            if not any(
                existing.get("support_operation_id") == modifier.get("support_operation_id")
                and existing.get("event_type") == modifier.get("event_type")
                for existing in support_effects
                if isinstance(existing, dict)
            ):
                support_effects.append(modifier)
    return final_score, modifiers, base_score


def risk_events_for_operation(operation):
    if operation.get("status") == "cancelled":
        return ["abandoned_operation"]

    operation_type = str(operation.get("operation_type") or "")
    risk_state = operation.get("risk_state") if isinstance(operation.get("risk_state"), dict) else {}
    events = [
        str(event).strip()
        for event in risk_state.get("events", [])
        if str(event).strip() in RISK_EVENT_BASE_SCORES
    ]

    derived = {
        "atm_log_extraction": ["atm_alarm"],
        "persistent_sniffer": ["long_operation_detected", "sniffer_detected"],
        "camera_stream": ["camera_detected", "long_operation_detected"],
        "camera_shutdown": ["camera_detected"],
        "vehicle_tracking": ["long_operation_detected"],
        "device_tracking": ["long_operation_detected"],
        "generic_trace": ["long_operation_detected"],
        "wifi_scanner": ["suspicious_network_activity"],
        "microphone_sniffer": ["long_operation_detected"],
    }.get(operation_type, [])
    for event in derived:
        if event not in events:
            events.append(event)
    return events


def assess_operation_risk(profile, operation):
    risk_state = operation.setdefault("risk_state", initial_risk_state_for_operation(operation.get("operation_type")))
    if risk_state.get("assessed"):
        return False
    if operation.get("status") not in OPERATION_RISK_ASSESSABLE_STATUSES:
        return False

    events = risk_events_for_operation(operation)
    if not events:
        risk_state["assessed"] = True
        return True

    base_score = int(risk_state.get("score") or 0)
    changed = False
    for event_type in events:
        score = max(base_score, RISK_EVENT_BASE_SCORES.get(event_type, 25))
        if event_type == "long_operation_detected" and operation.get("status") == "timeout":
            score += 8
        if event_type == "atm_alarm":
            score = max(score, 72)
        if event_type == "sniffer_detected":
            score = max(score, 58)
        score = min(100, score)
        score, modifiers, base_score = apply_risk_modifiers(profile, operation, event_type, score)
        created = append_risk_event(
            profile,
            event_type,
            "operation",
            score,
            operation=operation,
            dedupe_key=f"operation:{operation.get('operation_id')}:{event_type}",
            modifiers=modifiers,
            base_score=base_score,
        )
        changed = bool(created) or changed

    risk_state["assessed"] = True
    risk_state["last_assessed_at"] = runtime_file_now()
    risk_state["consequences_enabled"] = True
    return True


def risk_scan_action_dedupe_key(username, action, lat, lng):
    minute_bucket = datetime.utcnow().strftime("%Y%m%d%H%M")
    try:
        lat_key = round(float(lat), 5)
        lng_key = round(float(lng), 5)
    except (TypeError, ValueError):
        lat_key = lat
        lng_key = lng
    return f"action:{username}:{action}:{lat_key}:{lng_key}:{minute_bucket}"


HACK_ACTION_IDEMPOTENCY_TTL_SECONDS = 90
HACK_ACTION_IDEMPOTENCY_MAX = 512
_hack_action_idempotency_cache = {}
_hack_action_idempotency_lock = threading.Lock()


def build_hack_action_idempotency_key(username, flow_id, action, app, client_action_key=""):
    username = str(username or "").strip()
    action = str(action or "").strip()
    flow_id = str(flow_id or "").strip()[:96]
    client_action_key = str(client_action_key or "").strip()[:160]
    app_id = str((app or {}).get("id") or (app or {}).get("name") or "direct").strip()
    if not username or not action or (not flow_id and not client_action_key):
        return ""
    # The flow id is diagnostic and can change when the map retries/reopens a
    # UI flow. The client action key describes the actual gameplay intent:
    # action + target + mode. Prefer it so repeated map submissions do not
    # enqueue/open the same tool multiple times under different flow ids.
    request_key = client_action_key or flow_id
    return f"{username}:{request_key}:{action}:{app_id}"


def _cache_hack_action_idempotency_receipt(key, state, receipt=None):
    if not key:
        return
    now_ts = time.monotonic()
    cached = {
        "state": state,
        "expires_at": now_ts + HACK_ACTION_IDEMPOTENCY_TTL_SECONDS,
        "payload": None,
        "status_code": 202,
    }
    if isinstance(receipt, dict):
        cached.update(copy.deepcopy(receipt))
        cached["state"] = state
        cached["expires_at"] = now_ts + HACK_ACTION_IDEMPOTENCY_TTL_SECONDS
    _hack_action_idempotency_cache[key] = cached


def build_hack_action_receipt_metadata(username, action, app, data=None):
    data = data or {}
    app = app or {}
    return {
        "username": str(username or "").strip(),
        "app_id": str(app.get("id") or app.get("name") or "direct").strip(),
        "action": str(action or "").strip(),
        "target_key": str(
            data.get("_client_action_key")
            or data.get("target_key")
            or "|".join([
                str(data.get("lat") or ""),
                str(data.get("lng") or ""),
                str(data.get("label") or ""),
                str(data.get("target_mode") or ""),
            ])
        ).strip()[:220],
        "source": str(data.get("_source") or data.get("source") or "hack_action").strip(),
    }


def begin_hack_action_idempotency(key, metadata=None):
    if not key:
        return "new", None

    metadata = metadata or {}
    try:
        state, receipt = app_action_receipt_store.begin(
            key,
            username=metadata.get("username", ""),
            app_id=metadata.get("app_id", ""),
            action=metadata.get("action", ""),
            target_key=metadata.get("target_key", ""),
            source=metadata.get("source", ""),
            ttl_seconds=HACK_ACTION_IDEMPOTENCY_TTL_SECONDS,
        )
        with _hack_action_idempotency_lock:
            _cache_hack_action_idempotency_receipt(key, "in_flight" if state == "new" else state, receipt)
        return state, copy.deepcopy(receipt) if receipt else None
    except Exception as exc:
        hack_flow_debug(
            metadata.get("flow_id") or "",
            "idempotency_store_fallback",
            key=key,
            error=exc,
        )

    now_ts = time.monotonic()
    with _hack_action_idempotency_lock:
        expired_keys = [
            cached_key
            for cached_key, receipt in _hack_action_idempotency_cache.items()
            if float(receipt.get("expires_at") or 0) <= now_ts
        ]
        for cached_key in expired_keys:
            _hack_action_idempotency_cache.pop(cached_key, None)
        if len(_hack_action_idempotency_cache) > HACK_ACTION_IDEMPOTENCY_MAX:
            oldest = sorted(
                _hack_action_idempotency_cache.items(),
                key=lambda item: float(item[1].get("expires_at") or 0),
            )
            for cached_key, _receipt in oldest[:64]:
                _hack_action_idempotency_cache.pop(cached_key, None)

        receipt = _hack_action_idempotency_cache.get(key)
        if receipt:
            return str(receipt.get("state") or "in_flight"), copy.deepcopy(receipt)

        _cache_hack_action_idempotency_receipt(key, "in_flight")
    return "new", None


def finish_hack_action_idempotency(key, payload, status_code=200):
    if not key:
        return
    try:
        app_action_receipt_store.finish(
            key,
            payload,
            status_code,
            ttl_seconds=HACK_ACTION_IDEMPOTENCY_TTL_SECONDS,
        )
    except Exception as exc:
        hack_flow_debug("", "idempotency_store_finish_failed", key=key, error=exc)
    with _hack_action_idempotency_lock:
        _cache_hack_action_idempotency_receipt(
            key,
            "completed",
            {
                "payload": copy.deepcopy(payload or {}),
                "status_code": int(status_code or 200),
            },
        )


HACK_FLOW_DEBUG_ENABLED = os.environ.get("CHAOS_HACK_FLOW_DEBUG", "0").strip().lower() not in {"0", "false", "no", "off"}
APP_FLOW_DEBUG_ENABLED = os.environ.get("CHAOS_APP_FLOW_DEBUG", "1").strip().lower() not in {"0", "false", "no", "off"}
BACKEND_DEBUG_LOG_PATH = os.environ.get(
    "CHAOS_BACKEND_DEBUG_LOG",
    os.path.join("data", "logs", "backend_debug.log"),
)
BACKEND_DEBUG_STDOUT_ENABLED = os.environ.get("CHAOS_BACKEND_DEBUG_STDOUT", "0").strip().lower() in {"1", "true", "yes", "on"}
BACKEND_DEBUG_LOG_MAX_BYTES = int(os.environ.get("CHAOS_BACKEND_DEBUG_LOG_MAX_BYTES", str(5 * 1024 * 1024)))
_backend_debug_log_lock = threading.Lock()


def backend_debug_log(line):
    if not line:
        return
    timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    entry = f"{timestamp} {line}"
    if BACKEND_DEBUG_STDOUT_ENABLED:
        print(entry, flush=True)
    try:
        log_dir = os.path.dirname(BACKEND_DEBUG_LOG_PATH)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        with _backend_debug_log_lock:
            if BACKEND_DEBUG_LOG_MAX_BYTES > 0 and os.path.exists(BACKEND_DEBUG_LOG_PATH):
                try:
                    if os.path.getsize(BACKEND_DEBUG_LOG_PATH) >= BACKEND_DEBUG_LOG_MAX_BYTES:
                        rotated_path = f"{BACKEND_DEBUG_LOG_PATH}.1"
                        if os.path.exists(rotated_path):
                            os.remove(rotated_path)
                        os.replace(BACKEND_DEBUG_LOG_PATH, rotated_path)
                except Exception:
                    pass
            with open(BACKEND_DEBUG_LOG_PATH, "a", encoding="utf-8") as handle:
                handle.write(entry + "\n")
    except Exception:
        pass


def hack_flow_debug(flow_id, step, **fields):
    if not HACK_FLOW_DEBUG_ENABLED:
        return
    safe_fields = {
        "pid": os.getpid(),
        "thread": threading.get_ident(),
    }
    safe_fields.update(fields)
    parts = []
    for key, value in safe_fields.items():
        if isinstance(value, (dict, list, tuple, set)):
            try:
                value = json.dumps(value, ensure_ascii=False, sort_keys=True)[:700]
            except Exception:
                value = repr(value)[:700]
        else:
            value = str(value)[:220]
        parts.append(f"{key}={value}")
    backend_debug_log(f"[HACK_FLOW_DEBUG {flow_id or '-'}] step={step} " + " ".join(parts))


def app_flow_debug(flow_id, step, started_at=None, **fields):
    if not APP_FLOW_DEBUG_ENABLED:
        return
    safe_fields = {
        "pid": os.getpid(),
        "thread": threading.get_ident(),
    }
    if started_at is not None:
        try:
            safe_fields["elapsed_ms"] = int((time.perf_counter() - started_at) * 1000)
        except Exception:
            pass
    safe_fields.update(fields)
    parts = []
    for key, value in safe_fields.items():
        if isinstance(value, (dict, list, tuple, set)):
            try:
                value = json.dumps(value, ensure_ascii=False, sort_keys=True)[:700]
            except Exception:
                value = repr(value)[:700]
        else:
            value = str(value)[:220]
        parts.append(f"{key}={value}")
    backend_debug_log(f"[APP_FLOW_BE {flow_id or '-'}] step={step} " + " ".join(parts))


def app_flow_debug_timed(flow_id, step, flow_started_at, step_started_at, **fields):
    try:
        fields["step_ms"] = int((time.perf_counter() - step_started_at) * 1000)
    except Exception:
        pass
    app_flow_debug(flow_id, step, started_at=flow_started_at, **fields)


def build_operation_instance(username, app, map_action_id, operation_type, target):
    now = datetime.now(timezone.utc)
    operation_id = f"op_{now.strftime('%Y%m%d%H%M%S')}_{randint(100000, 999999)}"
    target_snapshot = dict(target or {})
    apply_target_display_label(target_snapshot)
    target_type = infer_target_type_from_target(target_snapshot)
    target_mode = str(target_snapshot.get("target_mode") or "standard")
    target_id = build_operation_target_id(target_snapshot)
    duration_seconds = operation_duration_seconds(operation_type)
    movement_model = movement_model_for_operation(operation_type, target_type)
    procedural_seed = stable_procedural_seed(operation_id, username, target_id, operation_type)
    operation = {
        "operation_id": operation_id,
        "operation_type": operation_type,
        "owner_username": username,
        "source_app_id": app.get("id") or app.get("name") or "",
        "source_app_name": app.get("name") or app.get("id") or "",
        "map_action_id": map_action_id,
        "target_id": target_id,
        "target": target_snapshot,
        "target_type": target_type,
        "target_mode": target_mode,
        "status": "running",
        "started_at": operation_utc_iso(now),
        "expires_at": operation_expiry_iso(now, operation_type),
        "duration_seconds": duration_seconds,
        "movement_model": movement_model,
        "procedural_seed": procedural_seed,
        "source_app_quality": {
            "creator_power": clamp_percent(app.get("creator_power"), default=DEFAULT_CREATOR_POWER),
            "quality_score": clamp_percent(app.get("quality_score"), default=DEFAULT_APP_QUALITY_SCORE),
            "reliability": clamp_percent(app.get("reliability"), default=DEFAULT_APP_RELIABILITY),
        },
        "resource_buffer": {
            "resource_types": [
                str(resource_type).strip()
                for resource_type in as_list(app.get("resource_types"))
                if str(resource_type).strip()
            ],
            "items": [],
            "quality_score": clamp_percent(app.get("quality_score"), default=DEFAULT_APP_QUALITY_SCORE),
            "reliability": clamp_percent(app.get("reliability"), default=DEFAULT_APP_RELIABILITY),
        },
        "risk_state": initial_risk_state_for_operation(operation_type),
    }
    update_operation_risk_meter(operation, tool=app or {}, target=target_snapshot, now_ts=now)
    return operation


def create_operations_for_app_action(profile, username, app, map_action_id, target):
    normalized_app = normalize_app_contract(app or {})
    operation_types = [
        str(operation_type).strip()
        for operation_type in as_list(normalized_app.get("operation_types"))
        if str(operation_type).strip()
    ]
    if not operation_types:
        return []

    target_id = build_operation_target_id(target)
    terminal_statuses = {"cancelled", "canceled", "done", "completed", "failed", "expired", "timeout", "resolved"}
    operations = profile.setdefault("operations", [])
    created = []
    app_id = str(normalized_app.get("id") or normalized_app.get("name") or "").strip()
    app_name = str(normalized_app.get("name") or normalized_app.get("id") or "").strip()

    for operation_type in dict.fromkeys(operation_types):
        exists = False
        for existing_operation in operations:
            if not isinstance(existing_operation, dict):
                continue
            status = str(existing_operation.get("status") or "").strip().lower()
            if status in terminal_statuses:
                continue
            if str(existing_operation.get("target_id") or "") != str(target_id):
                continue
            if str(existing_operation.get("map_action_id") or "") != str(map_action_id):
                continue
            if str(existing_operation.get("operation_type") or "") != str(operation_type):
                continue
            existing_app_id = str(existing_operation.get("source_app_id") or "").strip()
            existing_app_name = str(existing_operation.get("source_app_name") or "").strip()
            if app_id and existing_app_id == app_id:
                exists = True
                break
            if app_name and existing_app_name == app_name:
                exists = True
                break
        if exists:
            continue

        operation = build_operation_instance(username, normalized_app, map_action_id, operation_type, target)
        update_operation_risk_meter(operation, tool=normalized_app, target=target)
        try:
            accepted = player_operation_store.upsert_operations(
                username,
                [operation],
                event_type="operation.started",
                source="map_action",
                dedupe_key_prefix=f"start:{username}:{target_id}:{map_action_id}:{operation_type}:{app_id or app_name}",
            )
            if not accepted:
                continue
            operation = accepted[0]
        except Exception as exc:
            print(f"[OPERATIONS] store start skipped: {exc}")
        operations.append(operation)
        created.append(operation)
    return created


def create_missing_operations_for_app_target(profile, username, app, target):
    """Start map operation runtime for desktop/terminal-launched tools, without duplicates."""
    if not isinstance(profile, dict) or not username or not isinstance(target, dict) or not target:
        return []
    if not target_has_stable_runtime_identity(target):
        return []

    normalized_app = normalize_app_contract(app or {})
    map_actions = [
        str(action).strip()
        for action in as_list(normalized_app.get("map_actions"))
        if str(action).strip()
    ]
    operation_types = [
        str(operation_type).strip()
        for operation_type in as_list(normalized_app.get("operation_types"))
        if str(operation_type).strip()
    ]
    if not map_actions or not operation_types:
        return []

    target_id = build_operation_target_id(target)
    if not target_id:
        return []

    terminal_statuses = {"cancelled", "canceled", "done", "completed", "failed", "expired", "timeout", "resolved"}
    operations = profile.setdefault("operations", [])
    created = []
    app_id = str(normalized_app.get("id") or normalized_app.get("name") or "").strip()
    app_name = str(normalized_app.get("name") or normalized_app.get("id") or "").strip()

    map_action_id = map_actions[0]
    for operation_type in dict.fromkeys(operation_types):
        exists = False
        for operation in operations:
            if not isinstance(operation, dict):
                continue
            status = str(operation.get("status") or "").strip().lower()
            if status in terminal_statuses:
                continue
            if str(operation.get("target_id") or "") != str(target_id):
                continue
            if str(operation.get("map_action_id") or "") != str(map_action_id):
                continue
            if str(operation.get("operation_type") or "") != str(operation_type):
                continue
            operation_app_id = str(operation.get("source_app_id") or "").strip()
            operation_app_name = str(operation.get("source_app_name") or "").strip()
            if app_id and operation_app_id == app_id:
                exists = True
                break
            if app_name and operation_app_name == app_name:
                exists = True
                break
        if exists:
            continue

        operation = build_operation_instance(username, normalized_app, map_action_id, operation_type, target)
        update_operation_risk_meter(operation, tool=normalized_app, target=target)
        try:
            accepted = player_operation_store.upsert_operations(
                username,
                [operation],
                event_type="operation.started",
                source="desktop_terminal",
                dedupe_key_prefix=f"start:{username}:{target_id}:{map_action_id}:{operation_type}:{app_id or app_name}",
            )
            if not accepted:
                continue
            operation = accepted[0]
        except Exception as exc:
            print(f"[OPERATIONS] store start skipped: {exc}")
        operations.append(operation)
        created.append(operation)

    return created


def parse_operation_timestamp(value):
    if not value:
        return None
    try:
        raw = str(value)
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except (TypeError, ValueError):
        return None


def operation_elapsed_ratio(operation, now_ts):
    started_ts = parse_operation_timestamp(operation.get("started_at"))
    expires_ts = parse_operation_timestamp(operation.get("expires_at"))
    if started_ts is None or expires_ts is None or expires_ts <= started_ts:
        return 0.0
    return max(0.0, min(1.0, (now_ts - started_ts) / (expires_ts - started_ts)))


def operation_remaining_seconds(operation, now_ts):
    expires_ts = parse_operation_timestamp(operation.get("expires_at"))
    if expires_ts is None:
        return None
    return max(0, int(expires_ts - now_ts))


def operation_base_position(operation):
    target = operation.get("target") or {}
    try:
        lat = float(target.get("lat"))
        lng = float(target.get("lng", target.get("lon")))
    except (TypeError, ValueError):
        return None
    if math.isnan(lat) or math.isnan(lng):
        return None
    return lat, lng


def offset_position(lat, lng, distance_m, angle_rad):
    earth_lat_m = 111_320.0
    cos_lat = max(0.2, abs(math.cos(math.radians(lat))))
    d_lat = (math.sin(angle_rad) * distance_m) / earth_lat_m
    d_lng = (math.cos(angle_rad) * distance_m) / (earth_lat_m * cos_lat)
    return {
        "lat": round(lat + d_lat, 7),
        "lng": round(lng + d_lng, 7),
    }


def compute_operation_position(operation, now_ts):
    base = operation_base_position(operation)
    if not base:
        return None

    lat, lng = base
    movement_model = operation.get("movement_model") or movement_model_for_operation(
        operation.get("operation_type"),
        operation.get("target_type"),
    )
    if movement_model in {"none", "static_active_timer", "implant_timer"}:
        return {"lat": round(lat, 7), "lng": round(lng, 7)}

    seed = int(operation.get("procedural_seed") or stable_procedural_seed(operation.get("operation_id")))
    rng = random_module.Random(seed)
    ratio = operation_elapsed_ratio(operation, now_ts)
    angle = rng.random() * math.tau

    if movement_model == "road_movement":
        speed_mps = 3.0 + rng.random() * 6.0
        duration = int(operation.get("duration_seconds") or operation_duration_seconds(operation.get("operation_type")))
        elapsed = max(0, min(duration, int(duration * ratio)))
        distance = min(2500.0, elapsed * speed_mps)
        return offset_position(lat, lng, distance, angle)

    if movement_model in {"local_walk", "carrier_movement", "player_position"}:
        radius = 18.0 + rng.random() * 42.0
        phase = ratio * math.tau * (1.0 + rng.random())
        distance = radius * (0.35 + 0.65 * abs(math.sin(phase)))
        return offset_position(lat, lng, distance, angle + phase)

    return {"lat": round(lat, 7), "lng": round(lng, 7)}


def operation_filename_slug(value):
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value or "target")).strip("_")
    return slug[:48] or "target"


def operation_iso_from_ts(timestamp):
    return datetime.utcfromtimestamp(timestamp).isoformat(timespec="seconds") + "Z"


def ensure_vehicle_tracking_checkpoints(operation, now_ts):
    if operation.get("operation_type") != "vehicle_tracking":
        return False
    if operation.get("status") not in (OPERATION_ACTIVE_STATUSES | OPERATION_FINALIZABLE_STATUSES):
        return False

    started_ts = parse_operation_timestamp(operation.get("started_at"))
    expires_ts = parse_operation_timestamp(operation.get("expires_at"))
    if started_ts is None or expires_ts is None or expires_ts <= started_ts:
        return False

    observed_ts = min(now_ts, expires_ts)
    interval = VEHICLE_TRACKING_CHECKPOINT_INTERVAL_SECONDS
    target_count = int(max(0, observed_ts - started_ts) // interval)
    if observed_ts >= expires_ts:
        duration = max(0, expires_ts - started_ts)
        target_count = int(duration // interval)
        if duration % interval:
            target_count += 1

    checkpoints = operation.setdefault("checkpoints", [])
    changed = False
    while len(checkpoints) < target_count:
        index = len(checkpoints) + 1
        checkpoint_ts = min(started_ts + index * interval, expires_ts)
        position = compute_operation_position(operation, checkpoint_ts)
        if not position:
            break
        checkpoints.append({
            "index": index,
            "created_at": operation_iso_from_ts(checkpoint_ts),
            "lat": position["lat"],
            "lng": position["lng"],
            "event_type": "vehicle_tracking_checkpoint",
        })
        changed = True

    return changed


GAMEPLAY_FILE_FOLDERS = [
    "tools",
    "gps",
    "device",
    "audio",
    "camera",
    "atm",
    "credentials",
    "financial",
    "personal",
    "network",
    "vehicle",
    "system",
    "market",
    "projects",
]

LEGACY_FILE_FOLDERS = [
    "download",
    "pictures",
    "social-media",
    "pro_system_projects",
]

DATA_FILE_FOLDERS = [
    "gps",
    "device",
    "audio",
    "camera",
    "atm",
    "credentials",
    "financial",
    "personal",
    "network",
    "vehicle",
    "system",
    "market",
]

FILE_CATEGORY_DEFAULTS = {
    "gps": {
        "directory": "/data/gps",
        "preview_mode": "table",
        "resource_types": ["gps_logs", "location_history"],
    },
    "device": {
        "directory": "/data/device",
        "preview_mode": "card",
        "resource_types": ["device_logs"],
    },
    "audio": {
        "directory": "/data/audio",
        "preview_mode": "transcript",
        "resource_types": ["audio_transcript"],
    },
    "camera": {
        "directory": "/data/camera",
        "preview_mode": "media_placeholder",
        "resource_types": ["camera_dump"],
    },
    "atm": {
        "directory": "/data/atm",
        "preview_mode": "table",
        "resource_types": ["atm_dump"],
    },
    "credentials": {
        "directory": "/data/credentials",
        "preview_mode": "encrypted_blob",
        "resource_types": ["credentials"],
    },
    "financial": {
        "directory": "/data/financial",
        "preview_mode": "table",
        "resource_types": ["financial_records"],
    },
    "personal": {
        "directory": "/data/personal",
        "preview_mode": "card",
        "resource_types": ["personal_records"],
    },
    "network": {
        "directory": "/data/network",
        "preview_mode": "table",
        "resource_types": ["wifi_networks"],
    },
    "vehicle": {
        "directory": "/data/vehicle",
        "preview_mode": "table",
        "resource_types": ["vehicle_diagnostics"],
    },
    "system": {
        "directory": "/system",
        "preview_mode": "operation_state",
        "resource_types": ["internal_recon_state"],
    },
    "market": {
        "directory": "/market",
        "preview_mode": "table",
        "resource_types": [],
    },
}

TRAVEL_CITIES = {
    "Warszawa": {"name": "Warszawa", "country": "Polska", "lat": 52.2297, "lng": 21.0122},
    "Krakow": {"name": "Krakow", "country": "Polska", "lat": 50.0647, "lng": 19.9450},
    "Gdansk": {"name": "Gdansk", "country": "Polska", "lat": 54.3520, "lng": 18.6466},
    "Wroclaw": {"name": "Wroclaw", "country": "Polska", "lat": 51.1079, "lng": 17.0385},
    "Poznan": {"name": "Poznan", "country": "Polska", "lat": 52.4064, "lng": 16.9252},
    "Lodz": {"name": "Lodz", "country": "Polska", "lat": 51.7592, "lng": 19.4560},
    "Katowice": {"name": "Katowice", "country": "Polska", "lat": 50.2649, "lng": 19.0238},
    "Szczecin": {"name": "Szczecin", "country": "Polska", "lat": 53.4285, "lng": 14.5528},
    "Lublin": {"name": "Lublin", "country": "Polska", "lat": 51.2465, "lng": 22.5684},
    "Bialystok": {"name": "Bialystok", "country": "Polska", "lat": 53.1325, "lng": 23.1688},
    "Rzeszow": {"name": "Rzeszow", "country": "Polska", "lat": 50.0412, "lng": 21.9991},
    "Olsztyn": {"name": "Olsztyn", "country": "Polska", "lat": 53.7784, "lng": 20.4801},
    "Berlin": {"name": "Berlin", "country": "Niemcy", "lat": 52.5200, "lng": 13.4050},
    "Praga": {"name": "Praga", "country": "Czechy", "lat": 50.0755, "lng": 14.4378},
    "Wieden": {"name": "Wieden", "country": "Austria", "lat": 48.2082, "lng": 16.3738},
    "Bratyslawa": {"name": "Bratyslawa", "country": "Slowacja", "lat": 48.1486, "lng": 17.1077},
    "Budapeszt": {"name": "Budapeszt", "country": "Wegry", "lat": 47.4979, "lng": 19.0402},
    "Amsterdam": {"name": "Amsterdam", "country": "Holandia", "lat": 52.3676, "lng": 4.9041},
    "Bruksela": {"name": "Bruksela", "country": "Belgia", "lat": 50.8503, "lng": 4.3517},
    "Paryz": {"name": "Paryz", "country": "Francja", "lat": 48.8566, "lng": 2.3522},
    "Londyn": {"name": "Londyn", "country": "Wielka Brytania", "lat": 51.5072, "lng": -0.1276},
    "Dublin": {"name": "Dublin", "country": "Irlandia", "lat": 53.3498, "lng": -6.2603},
    "Madryt": {"name": "Madryt", "country": "Hiszpania", "lat": 40.4168, "lng": -3.7038},
    "Barcelona": {"name": "Barcelona", "country": "Hiszpania", "lat": 41.3874, "lng": 2.1686},
    "Lizbona": {"name": "Lizbona", "country": "Portugalia", "lat": 38.7223, "lng": -9.1393},
    "Rzym": {"name": "Rzym", "country": "Wlochy", "lat": 41.9028, "lng": 12.4964},
    "Mediolan": {"name": "Mediolan", "country": "Wlochy", "lat": 45.4642, "lng": 9.1900},
    "Zurych": {"name": "Zurych", "country": "Szwajcaria", "lat": 47.3769, "lng": 8.5417},
    "Oslo": {"name": "Oslo", "country": "Norwegia", "lat": 59.9139, "lng": 10.7522},
    "Sztokholm": {"name": "Sztokholm", "country": "Szwecja", "lat": 59.3293, "lng": 18.0686},
    "Helsinki": {"name": "Helsinki", "country": "Finlandia", "lat": 60.1699, "lng": 24.9384},
    "Kopenhaga": {"name": "Kopenhaga", "country": "Dania", "lat": 55.6761, "lng": 12.5683},
    "Nowy Jork": {"name": "Nowy Jork", "country": "USA", "lat": 40.7128, "lng": -74.0060},
    "Los Angeles": {"name": "Los Angeles", "country": "USA", "lat": 34.0522, "lng": -118.2437},
    "Chicago": {"name": "Chicago", "country": "USA", "lat": 41.8781, "lng": -87.6298},
    "Toronto": {"name": "Toronto", "country": "Kanada", "lat": 43.6532, "lng": -79.3832},
    "Meksyk": {"name": "Meksyk", "country": "Meksyk", "lat": 19.4326, "lng": -99.1332},
    "Rio de Janeiro": {"name": "Rio de Janeiro", "country": "Brazylia", "lat": -22.9068, "lng": -43.1729},
    "Buenos Aires": {"name": "Buenos Aires", "country": "Argentyna", "lat": -34.6037, "lng": -58.3816},
    "Dubaj": {"name": "Dubaj", "country": "ZEA", "lat": 25.2048, "lng": 55.2708},
    "Kair": {"name": "Kair", "country": "Egipt", "lat": 30.0444, "lng": 31.2357},
    "Kapsztad": {"name": "Kapsztad", "country": "RPA", "lat": -33.9249, "lng": 18.4241},
    "Delhi": {"name": "Delhi", "country": "Indie", "lat": 28.6139, "lng": 77.2090},
    "Bangkok": {"name": "Bangkok", "country": "Tajlandia", "lat": 13.7563, "lng": 100.5018},
    "Singapur": {"name": "Singapur", "country": "Singapur", "lat": 1.3521, "lng": 103.8198},
    "Seul": {"name": "Seul", "country": "Korea Poludniowa", "lat": 37.5665, "lng": 126.9780},
    "Tokio": {"name": "Tokio", "country": "Japonia", "lat": 35.6762, "lng": 139.6503},
    "Pekin": {"name": "Pekin", "country": "Chiny", "lat": 39.9042, "lng": 116.4074},
    "Sydney": {"name": "Sydney", "country": "Australia", "lat": -33.8688, "lng": 151.2093},
    "Auckland": {"name": "Auckland", "country": "Nowa Zelandia", "lat": -36.8509, "lng": 174.7645},
}

def googleplex_product_base(product_id, name, description, product_type, category, price, effects, **extra):
    product = {
        "id": product_id,
        "name": name,
        "description": description,
        "icon": extra.pop("icon", "+"),
        "type": "system_product",
        "product_type": product_type,
        "category": category,
        "effects": effects,
        "price": price,
        "purchase_account": "admin",
        "creator_username": "admin",
        "creator_nick": "CyberPhoenix",
        "required_level": extra.pop("required_level", 1),
        "required_respect": extra.pop("required_respect", 0),
        "published": True,
        "generated": False,
        "system_catalog": True,
        "consumable": extra.pop("consumable", False),
        "balance_tier": extra.pop("balance_tier", "Basic"),
    }
    product.update(extra)
    return product

STORAGE_UPGRADE_PRODUCTS = [
    googleplex_product_base(
        "storage_ghost_vault_basic",
        "Ghost Vault Basic",
        "Podstawowe rozszerzenie pojemnosci dysku danych.",
        "storage_upgrade",
        "storage",
        650,
        [{"type": "storage_capacity_bonus", "value": 256}],
        icon="+",
        storage_capacity_bonus=256,
    ),
    googleplex_product_base(
        "storage_ghost_vault_plus",
        "Ghost Vault Plus",
        "Wiekszy bufor danych pod dluzsze operacje i paczki rynku.",
        "storage_upgrade",
        "storage",
        1450,
        [{"type": "storage_capacity_bonus", "value": 512}],
        icon="+",
        storage_capacity_bonus=512,
        required_level=3,
        required_respect=15,
        balance_tier="Advanced",
    ),
    googleplex_product_base(
        "storage_data_vault",
        "Data Vault",
        "Magazyn danych dla graczy aktywnie pracujacych z Ghost Exchange.",
        "storage_upgrade",
        "storage",
        3200,
        [{"type": "storage_capacity_bonus", "value": 1024}],
        icon="+",
        storage_capacity_bonus=1024,
        required_level=6,
        required_respect=40,
        balance_tier="Pro",
    ),
    googleplex_product_base(
        "storage_blackvault",
        "BlackVault",
        "Ciezki magazyn danych dla duzych paczek sektorowych.",
        "storage_upgrade",
        "storage",
        7600,
        [{"type": "storage_capacity_bonus", "value": 2048}],
        icon="+",
        storage_capacity_bonus=2048,
        required_level=10,
        required_respect=90,
        balance_tier="Pro",
    ),
    googleplex_product_base(
        "storage_encrypted_cluster",
        "Encrypted Cluster",
        "Najwiekszy seedowy upgrade pojemnosci pod endgame rynku danych.",
        "storage_upgrade",
        "storage",
        14800,
        [{"type": "storage_capacity_bonus", "value": 4096}],
        icon="+",
        storage_capacity_bonus=4096,
        required_level=16,
        required_respect=160,
        balance_tier="Elite",
    ),
]

GOOGLEPLEX_EFFECT_PRODUCTS = [
    *STORAGE_UPGRADE_PRODUCTS,
    googleplex_product_base(
        "ticket_warszawa",
        "Bilet: Warszawa",
        "Powrot do miasta startowego.",
        "travel_ticket",
        "travel",
        60,
        [{"type": "travel_city", "city": "Warszawa"}],
        icon=">",
        travel_city="Warszawa",
        consumable=True,
    ),
    googleplex_product_base(
        "ticket_krakow",
        "Bilet: Krakow",
        "Jednorazowy przejazd do Krakowa.",
        "travel_ticket",
        "travel",
        95,
        [{"type": "travel_city", "city": "Krakow"}],
        icon=">",
        travel_city="Krakow",
        consumable=True,
        required_level=2,
    ),
    googleplex_product_base(
        "ticket_berlin",
        "Bilet: Berlin",
        "Jednorazowy przejazd do Berlina.",
        "travel_ticket",
        "travel",
        180,
        [{"type": "travel_city", "city": "Berlin"}],
        icon=">",
        travel_city="Berlin",
        consumable=True,
        required_level=3,
        required_respect=10,
    ),
    googleplex_product_base(
        "ticket_londyn",
        "Bilet: Londyn",
        "Jednorazowy przejazd do Londynu.",
        "travel_ticket",
        "travel",
        260,
        [{"type": "travel_city", "city": "Londyn"}],
        icon=">",
        travel_city="Londyn",
        consumable=True,
        required_level=4,
        required_respect=20,
    ),
    googleplex_product_base(
        "ticket_tokio",
        "Bilet: Tokio",
        "Jednorazowy przejazd do Tokio.",
        "travel_ticket",
        "travel",
        520,
        [{"type": "travel_city", "city": "Tokio"}],
        icon=">",
        travel_city="Tokio",
        consumable=True,
        required_level=7,
        required_respect=45,
    ),
    googleplex_product_base(
        "ticket_nowy_jork",
        "Bilet: Nowy Jork",
        "Jednorazowy przejazd do Nowego Jorku.",
        "travel_ticket",
        "travel",
        520,
        [{"type": "travel_city", "city": "Nowy Jork"}],
        icon=">",
        travel_city="Nowy Jork",
        consumable=True,
        required_level=7,
        required_respect=45,
    ),
    googleplex_product_base(
        "map_zoom_plus_1",
        "Map Zoom +1",
        "Lepsze przyblizenie mapy operacyjnej.",
        "map_upgrade",
        "map",
        800,
        [{"type": "map_zoom_bonus", "value": 1}],
        icon="^",
        required_level=2,
        required_respect=10,
    ),
    googleplex_product_base(
        "map_zoom_plus_2",
        "Map Zoom +2",
        "Zaawansowane przyblizenie mapy operacyjnej.",
        "map_upgrade",
        "map",
        1900,
        [{"type": "map_zoom_bonus", "value": 2}],
        icon="^",
        required_level=6,
        required_respect=45,
        balance_tier="Advanced",
    ),
    googleplex_product_base(
        "map_zoom_plus_3",
        "Map Zoom +3",
        "Najwyzszy seedowy zoom mapy.",
        "map_upgrade",
        "map",
        4200,
        [{"type": "map_zoom_bonus", "value": 3}],
        icon="^",
        required_level=11,
        required_respect=100,
        balance_tier="Pro",
    ),
    googleplex_product_base(
        "scan_range_100",
        "Scan Range +100 m",
        "Maly wzrost zasiegu rozpoznania.",
        "scan_upgrade",
        "map",
        700,
        [{"type": "scan_range_bonus", "value": 100}],
        icon="~",
        required_level=2,
        required_respect=10,
    ),
    googleplex_product_base(
        "scan_range_300",
        "Scan Range +300 m",
        "Sredni wzrost zasiegu rozpoznania.",
        "scan_upgrade",
        "map",
        1700,
        [{"type": "scan_range_bonus", "value": 300}],
        icon="~",
        required_level=5,
        required_respect=35,
        balance_tier="Advanced",
    ),
    googleplex_product_base(
        "scan_range_500",
        "Scan Range +500 m",
        "Duzy wzrost zasiegu rozpoznania.",
        "scan_upgrade",
        "map",
        3100,
        [{"type": "scan_range_bonus", "value": 500}],
        icon="~",
        required_level=8,
        required_respect=70,
        balance_tier="Pro",
    ),
    googleplex_product_base(
        "scan_range_1000",
        "Scan Range +1000 m",
        "Endgameowy wzrost zasiegu rozpoznania.",
        "scan_upgrade",
        "map",
        6800,
        [{"type": "scan_range_bonus", "value": 1000}],
        icon="~",
        required_level=14,
        required_respect=140,
        balance_tier="Elite",
    ),
    googleplex_product_base(
        "bike_range_100",
        "Bike Range +100 m",
        "Maly wzrost zasiegu roweru.",
        "bike_upgrade",
        "travel",
        500,
        [{"type": "bike_range_bonus", "value": 100}],
        icon=">",
        required_level=1,
        required_respect=5,
    ),
    googleplex_product_base(
        "bike_range_300",
        "Bike Range +300 m",
        "Sredni wzrost zasiegu roweru.",
        "bike_upgrade",
        "travel",
        1300,
        [{"type": "bike_range_bonus", "value": 300}],
        icon=">",
        required_level=4,
        required_respect=25,
        balance_tier="Advanced",
    ),
    googleplex_product_base(
        "bike_range_500",
        "Bike Range +500 m",
        "Duzy wzrost zasiegu roweru.",
        "bike_upgrade",
        "travel",
        2600,
        [{"type": "bike_range_bonus", "value": 500}],
        icon=">",
        required_level=7,
        required_respect=55,
        balance_tier="Pro",
    ),
    googleplex_product_base(
        "bike_range_1000",
        "Bike Range +1000 m",
        "Endgameowy wzrost zasiegu roweru.",
        "bike_upgrade",
        "travel",
        5600,
        [{"type": "bike_range_bonus", "value": 1000}],
        icon=">",
        required_level=12,
        required_respect=120,
        balance_tier="Elite",
    ),
]

LEGACY_STORAGE_UPGRADE_PRODUCTS = [
    {
        "id": "storage_ghost_vault_basic",
        "name": "Ghost Vault Basic",
        "description": "Podstawowe rozszerzenie pojemnosci dysku danych.",
        "icon": "▣",
        "product_type": "storage_upgrade",
        "storage_capacity_bonus": 256,
        "price": 650,
        "purchase_account": "admin",
        "creator_username": "admin",
        "creator_nick": "CyberPhoenix",
        "required_level": 1,
        "required_respect": 0,
        "published": True,
        "generated": False,
        "system_catalog": True,
        "balance_tier": "Basic",
    },
    {
        "id": "storage_ghost_vault_plus",
        "name": "Ghost Vault Plus",
        "description": "Wiekszy bufor danych pod dluzsze operacje i paczki rynku.",
        "icon": "▣",
        "product_type": "storage_upgrade",
        "storage_capacity_bonus": 512,
        "price": 1450,
        "purchase_account": "admin",
        "creator_username": "admin",
        "creator_nick": "CyberPhoenix",
        "required_level": 3,
        "required_respect": 15,
        "published": True,
        "generated": False,
        "system_catalog": True,
        "balance_tier": "Advanced",
    },
    {
        "id": "storage_data_vault",
        "name": "Data Vault",
        "description": "Magazyn danych dla graczy aktywnie pracujacych z Ghost Exchange.",
        "icon": "▣",
        "product_type": "storage_upgrade",
        "storage_capacity_bonus": 1024,
        "price": 3200,
        "purchase_account": "admin",
        "creator_username": "admin",
        "creator_nick": "CyberPhoenix",
        "required_level": 6,
        "required_respect": 40,
        "published": True,
        "generated": False,
        "system_catalog": True,
        "balance_tier": "Pro",
    },
    {
        "id": "storage_blackvault",
        "name": "BlackVault",
        "description": "Ciezki magazyn danych dla duzych paczek sektorowych.",
        "icon": "▣",
        "product_type": "storage_upgrade",
        "storage_capacity_bonus": 2048,
        "price": 7600,
        "purchase_account": "admin",
        "creator_username": "admin",
        "creator_nick": "CyberPhoenix",
        "required_level": 10,
        "required_respect": 90,
        "published": True,
        "generated": False,
        "system_catalog": True,
        "balance_tier": "Pro",
    },
    {
        "id": "storage_encrypted_cluster",
        "name": "Encrypted Cluster",
        "description": "Najwiekszy seedowy upgrade pojemnosci pod endgame rynku danych.",
        "icon": "▣",
        "product_type": "storage_upgrade",
        "storage_capacity_bonus": 4096,
        "price": 14800,
        "purchase_account": "admin",
        "creator_username": "admin",
        "creator_nick": "CyberPhoenix",
        "required_level": 16,
        "required_respect": 160,
        "published": True,
        "generated": False,
        "system_catalog": True,
        "balance_tier": "Elite",
    },
]
FILE_CATEGORY_SIZE_HINTS_MB = {
    "gps": 4,
    "device": 8,
    "personal": 9,
    "audio": 6,
    "camera": 14,
    "atm": 10,
    "financial": 12,
    "credentials": 7,
    "network": 6,
    "vehicle": 7,
    "system": 2,
    "market": 1,
    "projects": 16,
    "pro_system_projects": 24,
}


def clamp_storage_number(value, default=0, minimum=0):
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        number = int(default)
    return max(minimum, number)


def estimate_app_file_size(app):
    app = app if isinstance(app, dict) else {}
    explicit = app.get("file_size") or app.get("install_size")
    if explicit is not None:
        return clamp_storage_number(explicit, default=DEFAULT_APP_FILE_SIZE_MB, minimum=1)

    interface = str(app.get("interface") or "").strip()
    action_count = len(as_list(app.get("map_actions")))
    operation_count = len(as_list(app.get("operation_types")))
    resource_count = len(as_list(app.get("resource_types")))
    base = DEFAULT_APP_FILE_SIZE_MB
    if interface in {"window", "system_launcher"}:
        base += 6
    elif interface == "terminal":
        base += 3
    elif interface == "button_choices":
        base += 2
    base += min(12, action_count * 2 + operation_count * 3 + resource_count * 2)
    if str(app.get("type") or "") in {"pro-system-tool", "system_lab"}:
        base += 10
    return clamp_storage_number(base, default=DEFAULT_APP_FILE_SIZE_MB, minimum=1)


def normalize_app_storage_fields(app):
    if not isinstance(app, dict):
        return app
    file_size = estimate_app_file_size(app)
    disk_usage = app.get("disk_usage")
    if disk_usage is None:
        disk_usage = app.get("install_size")
    if disk_usage is None:
        disk_usage = max(file_size, file_size + 4)
    disk_usage = clamp_storage_number(disk_usage, default=max(DEFAULT_APP_DISK_USAGE_MB, file_size), minimum=1)
    app["file_size"] = file_size
    app["install_size"] = disk_usage
    app["disk_usage"] = disk_usage
    return app


def clamp_percent(value, default=0):
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        number = int(default)
    return max(0, min(100, number))


def calculate_creator_power(profile):
    if not isinstance(profile, dict):
        return DEFAULT_CREATOR_POWER
    try:
        level = int(profile.get("level") or 1)
    except (TypeError, ValueError):
        level = 1
    try:
        respect = int(profile.get("respect") or 0)
    except (TypeError, ValueError):
        respect = 0
    try:
        hackcoins = int(profile.get("hackcoins") or 0)
    except (TypeError, ValueError):
        hackcoins = 0
    power = 20 + level * 2 + respect / 25 + min(12, hackcoins / 10000)
    return clamp_percent(power, default=DEFAULT_CREATOR_POWER)


def infer_app_complexity_score(app):
    if not isinstance(app, dict):
        return 0
    action_count = len(as_list(app.get("map_actions")))
    operation_count = len(as_list(app.get("operation_types")))
    resource_count = len(as_list(app.get("resource_types")))
    target_count = len(as_list(app.get("target_types")))
    interface = str(app.get("interface") or "").strip()
    complexity = action_count * 2 + operation_count * 3 + resource_count * 3 + target_count
    if interface in {"window", "system_launcher"}:
        complexity += 4
    if str(app.get("type") or "") in {"pro-system-tool", "system_lab"}:
        complexity += 6
    return min(30, complexity)


def normalize_app_quality_fields(app):
    if not isinstance(app, dict):
        return app
    creator_power = app.get("creator_power")
    if creator_power is None:
        creator_power = DEFAULT_CREATOR_POWER
    creator_power = clamp_percent(creator_power, default=DEFAULT_CREATOR_POWER)
    complexity = infer_app_complexity_score(app)
    quality = app.get("quality_score")
    if quality is None:
        quality = DEFAULT_APP_QUALITY_SCORE + int(round((creator_power - DEFAULT_CREATOR_POWER) * 0.35)) + min(12, complexity // 2)
    reliability = app.get("reliability")
    if reliability is None:
        reliability = DEFAULT_APP_RELIABILITY + int(round((creator_power - DEFAULT_CREATOR_POWER) * 0.25)) - min(8, complexity // 5)
    app["creator_power"] = creator_power
    app["quality_score"] = clamp_percent(quality, default=DEFAULT_APP_QUALITY_SCORE)
    app["reliability"] = clamp_percent(reliability, default=DEFAULT_APP_RELIABILITY)
    return app


def app_is_pro_system_contract(app):
    if not isinstance(app, dict):
        return False
    return (
        str(app.get("type") or "").strip() == "pro-system-tool"
        or str(app.get("category") or "").strip() == "pro-system-tools"
        or bool(app.get("ghostlab_generated"))
    )


def infer_app_power_score(app):
    if not isinstance(app, dict):
        return 0
    quality = clamp_percent(app.get("quality_score"), default=DEFAULT_APP_QUALITY_SCORE)
    reliability = clamp_percent(app.get("reliability"), default=DEFAULT_APP_RELIABILITY)
    disk_usage = clamp_storage_number(
        app.get("disk_usage") or app.get("install_size") or app.get("file_size"),
        default=DEFAULT_APP_DISK_USAGE_MB,
        minimum=1,
    )
    risk_level = clamp_storage_number(app.get("risk_level"), default=0, minimum=0)
    required_level = clamp_storage_number(app.get("required_level"), default=1, minimum=1)
    required_respect = clamp_storage_number(app.get("required_respect"), default=0, minimum=0)
    tool_family = str(app.get("tool_family") or "").strip()
    tool_mode = str(app.get("tool_mode") or app.get("scanner_mode") or "").strip()

    score = 10 + infer_app_complexity_score(app) * 2
    score += max(0, quality - 50) * 0.30
    score += max(0, reliability - 50) * 0.18
    score += min(15, disk_usage / 4)
    score += min(12, risk_level * 2)
    score += min(10, required_level / 2)
    score += min(8, required_respect / 50)
    if tool_mode == "map":
        score += 3
    elif tool_mode == "hybrid":
        score += 7
    if tool_family == "scanner_recon":
        score += 2
    elif tool_family in {"exploit", "sniffer"}:
        score += 6
    elif tool_family == "pro_system_tool":
        score += 12
    if app_is_pro_system_contract(app):
        score += 18
    return clamp_percent(score, default=35)


def infer_app_price_hint(app):
    if not isinstance(app, dict):
        return DEFAULT_APP_PRICE_HINT_HC
    power_score = infer_app_power_score(app)
    disk_usage = clamp_storage_number(
        app.get("disk_usage") or app.get("install_size") or app.get("file_size"),
        default=DEFAULT_APP_DISK_USAGE_MB,
        minimum=1,
    )
    action_count = len(as_list(app.get("map_actions")))
    operation_count = len(as_list(app.get("operation_types")))
    resource_count = len(as_list(app.get("resource_types")))
    tool_mode = str(app.get("tool_mode") or app.get("scanner_mode") or "").strip()

    hint = DEFAULT_APP_PRICE_HINT_HC + power_score * 8 + disk_usage * 3
    hint += action_count * 35 + operation_count * 70 + resource_count * 45
    if tool_mode == "map":
        hint += 60
    elif tool_mode == "hybrid":
        hint += 120
    if str(app.get("tool_family") or "").strip() in {"exploit", "sniffer"}:
        hint += 140
    if app_is_pro_system_contract(app):
        hint += 1800
    return max(5, int(round(hint / 5.0) * 5))


def infer_app_balance_tier(power_score):
    try:
        score = int(power_score)
    except (TypeError, ValueError):
        score = 0
    if score >= 75:
        return "Pro"
    if score >= 50:
        return "Advanced"
    return "Basic"


def infer_app_recommended_requirements(app, power_score=None):
    if not isinstance(app, dict):
        return 1, 0
    if power_score is None:
        power_score = infer_app_power_score(app)
    recommended_level = max(1, int(round(power_score / 10)))
    recommended_respect = max(0, int(round(power_score * 2)))
    if app_is_pro_system_contract(app):
        recommended_level = max(recommended_level, 10)
        recommended_respect = max(recommended_respect, 120)
    return recommended_level, recommended_respect


def normalize_app_balance_fields(app):
    if not isinstance(app, dict):
        return app
    power_score = infer_app_power_score(app)
    price_hint = app.get("price_hint")
    if price_hint is None:
        price_hint = infer_app_price_hint(app)
    price_hint = clamp_storage_number(price_hint, default=DEFAULT_APP_PRICE_HINT_HC, minimum=5)
    recommended_level, recommended_respect = infer_app_recommended_requirements(app, power_score)
    app["power_score"] = power_score
    app["price_hint"] = price_hint
    app["balance_tier"] = infer_app_balance_tier(power_score)
    app["recommended_level"] = max(
        recommended_level,
        clamp_storage_number(app.get("recommended_level"), default=0, minimum=0),
    )
    app["recommended_respect"] = max(
        recommended_respect,
        clamp_storage_number(app.get("recommended_respect"), default=0, minimum=0),
    )
    return app


def enforce_generated_app_price_floor(app):
    if not isinstance(app, dict):
        return app
    normalize_app_balance_fields(app)
    current_price = clamp_storage_number(app.get("price"), default=0, minimum=0)
    price_hint = clamp_storage_number(app.get("price_hint"), default=DEFAULT_APP_PRICE_HINT_HC, minimum=5)
    app["price"] = max(current_price, price_hint)
    return app


def build_generated_app_quality_fields(creator_profile, app_seed=None):
    creator_power = calculate_creator_power(creator_profile)
    complexity = infer_app_complexity_score(app_seed or {})
    quality = clamp_percent(38 + creator_power * 0.48 + complexity * 0.35, default=DEFAULT_APP_QUALITY_SCORE)
    reliability = clamp_percent(48 + creator_power * 0.38 - min(10, complexity / 3), default=DEFAULT_APP_RELIABILITY)
    return {
        "creator_power": creator_power,
        "quality_score": quality,
        "reliability": reliability,
    }


def estimate_runtime_file_size(folder, entry, metadata=None, resource_types=None):
    entry = entry if isinstance(entry, dict) else {}
    metadata = metadata if isinstance(metadata, dict) else {}
    explicit = entry.get("file_size") or metadata.get("file_size")
    if explicit is not None:
        return clamp_storage_number(explicit, default=FILE_CATEGORY_SIZE_HINTS_MB.get(folder, 2), minimum=1)

    base = FILE_CATEGORY_SIZE_HINTS_MB.get(str(folder), 2)
    resources = resource_types if isinstance(resource_types, list) else []
    record_count = (
        metadata.get("record_count")
        or metadata.get("checkpoint_count")
        or metadata.get("collected_count")
        or len(entry.get("records", []) or [])
        or len(entry.get("checkpoints", []) or [])
        or 1
    )
    try:
        record_count = int(record_count)
    except (TypeError, ValueError):
        record_count = 1
    size = base + max(0, len(resources) - 1) * 2 + min(32, max(0, record_count - 1))
    if "video_material" in resources:
        size += 12
    if "credentials" in resources or "financial_records" in resources:
        size += 3
    return clamp_storage_number(size, default=base, minimum=1)


def calculate_profile_storage_used(profile):
    if not isinstance(profile, dict):
        return 0
    total = 0
    for app in normalize_app_contracts(profile.get("apps", [])):
        if isinstance(app, dict):
            total += clamp_storage_number(app.get("disk_usage") or app.get("install_size") or app.get("file_size"), default=0)
    files = profile.get("files") if isinstance(profile.get("files"), dict) else {}
    for folder, items in files.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                total += clamp_storage_number(item.get("file_size"), default=0)
            elif folder in {"projects", "pro_system_projects"}:
                total += FILE_CATEGORY_SIZE_HINTS_MB.get(folder, 8)
    return total


def normalize_profile_storage(profile):
    if not isinstance(profile, dict):
        return profile
    normalize_profile_storage_capacity(profile)
    capacity = profile["storage_capacity"]
    used = calculate_profile_storage_used(profile)
    profile["storage_capacity"] = capacity
    profile["storage_used"] = used
    profile["storage_unit"] = "MB"
    profile["storage_soft_limit"] = True
    profile["storage_over_limit"] = used > capacity
    return profile


def runtime_file_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def runtime_file_created_at(entry):
    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
    return (
        entry.get("created_at")
        or metadata.get("created_at")
        or metadata.get("ended_at")
        or metadata.get("started_at")
        or entry.get("ended_at")
        or entry.get("started_at")
        or runtime_file_now()
    )


def runtime_file_target_snapshot(entry):
    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
    target = entry.get("target_snapshot") or entry.get("target") or metadata.get("target")
    return target if isinstance(target, dict) else {}


def runtime_file_id(folder, entry):
    if entry.get("id"):
        return str(entry["id"])
    name = str(entry.get("name") or entry.get("filename") or "file")
    operation_id = str(entry.get("source_operation_id") or entry.get("operation_id") or "")
    fragment = str(entry.get("fragment_index") or "")
    seed = "_".join(part for part in [folder, operation_id, fragment, name] if part)
    return f"file_{operation_filename_slug(seed)}"


def normalize_runtime_file_entry(entry, folder):
    defaults = FILE_CATEGORY_DEFAULTS.get(folder, {
        "directory": f"/{folder}",
        "preview_mode": "file",
        "resource_types": [],
    })

    if not isinstance(entry, dict):
        entry = {"name": str(entry or "plik")}
    else:
        entry = dict(entry)

    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
    metadata = dict(metadata)

    operation_id = entry.get("operation_id") or entry.get("source_operation_id") or metadata.get("operation_id")
    source_operation_id = entry.get("source_operation_id") or operation_id or ""

    resource_types = entry.get("resource_types")
    if not isinstance(resource_types, list):
        resource_types = list(defaults.get("resource_types", []))
    else:
        resource_types = [str(item) for item in resource_types if str(item).strip()]

    target_snapshot = runtime_file_target_snapshot(entry)

    entry["file_category"] = str(entry.get("file_category") or folder)
    entry["directory"] = str(entry.get("directory") or defaults.get("directory") or f"/{folder}")
    entry["preview_mode"] = str(entry.get("preview_mode") or defaults.get("preview_mode") or "file")
    entry["resource_types"] = resource_types
    entry["source_operation_id"] = source_operation_id
    if operation_id and not entry.get("operation_id"):
        entry["operation_id"] = operation_id
    if operation_id and not metadata.get("operation_id"):
        metadata["operation_id"] = operation_id
    if target_snapshot:
        entry["target_snapshot"] = target_snapshot
        metadata.setdefault("target", target_snapshot)
    file_size = estimate_runtime_file_size(folder, entry, metadata=metadata, resource_types=resource_types)
    entry["file_size"] = file_size
    metadata.setdefault("file_size", file_size)
    entry["market_status"] = str(entry.get("market_status") or "not_listed")
    entry["created_at"] = runtime_file_created_at({**entry, "metadata": metadata})
    entry["sellable"] = is_ghost_exchange_sellable(entry)
    completeness_info = infer_file_completeness(entry, metadata, resource_types)
    metadata["completeness_percent"] = completeness_info["percent"]
    metadata["completeness_tier"] = completeness_info["tier"]
    metadata["missing_fields"] = completeness_info["missing_fields"]
    metadata["quality_score"] = completeness_info["quality_score"]
    metadata.setdefault("completeness", {})
    if isinstance(metadata["completeness"], dict):
        metadata["completeness"]["percent"] = completeness_info["percent"]
        metadata["completeness"]["tier"] = completeness_info["tier"]
        metadata["completeness"]["missing"] = completeness_info["missing_fields"]
        metadata["completeness"]["quality_score"] = completeness_info["quality_score"]
    entry["completeness_percent"] = completeness_info["percent"]
    entry["completeness_tier"] = completeness_info["tier"]
    entry["missing_fields"] = completeness_info["missing_fields"]
    entry["quality_score"] = completeness_info["quality_score"]
    entry["metadata"] = metadata
    entry["id"] = runtime_file_id(folder, entry)
    return entry


def normalize_files_inventory(profile):
    files = profile.setdefault("files", {})
    if not isinstance(files, dict):
        files = {}
        profile["files"] = files
    for folder in GAMEPLAY_FILE_FOLDERS + LEGACY_FILE_FOLDERS:
        if not isinstance(files.get(folder), list):
            files[folder] = []
    for folder in DATA_FILE_FOLDERS:
        normalized = [normalize_runtime_file_entry(item, folder) for item in files.get(folder, [])]
        files[folder] = normalized
    return files


def ensure_files_inventory(profile):
    return normalize_files_inventory(profile)


GHOST_EXCHANGE_FILE_CATEGORIES = {
    "gps",
    "device",
    "personal",
    "camera",
    "atm",
    "financial",
    "credentials",
    "network",
    "vehicle",
    "audio",
}

GHOST_EXCHANGE_BLOCKED_RESOURCES = {"internal_recon_state"}

MARKET_FILE_STATUSES = {
    "created",
    "queued_for_market",
    "listed",
    "sold",
    "archived",
}

LEGACY_MARKET_STATUS_MAP = {
    "ready_to_list": "queued_for_market",
    "listed_preview": "queued_for_market",
    "not_listed": "created",
}

MARKET_SECTOR_BY_FILE_CATEGORY = {
    "gps": "gps",
    "device": "device",
    "personal": "personal",
    "camera": "camera",
    "atm": "atm",
    "financial": "financial",
    "credentials": "credentials",
    "network": "network",
    "audio": "audio",
    "vehicle": "vehicle",
}

MARKET_SECTOR_BY_MARKET_CATEGORY = {
    "location": "gps",
    "device_intelligence": "device",
    "personal": "personal",
    "financial": "financial",
    "credentials": "credentials",
    "surveillance": "camera",
    "audio": "audio",
    "vehicle": "vehicle",
    "network": "network",
}

MARKET_SECTOR_THRESHOLDS = {
    "camera": {"threshold_mb": 50, "threshold_records": 0},
    "atm": {"threshold_mb": 30, "threshold_records": 10},
    "gps": {"threshold_mb": 25, "threshold_records": 0},
    "device": {"threshold_mb": 35, "threshold_records": 0},
    "personal": {"threshold_mb": 30, "threshold_records": 10},
    "credentials": {"threshold_mb": 15, "threshold_records": 5},
    "financial": {"threshold_mb": 25, "threshold_records": 10},
    "network": {"threshold_mb": 30, "threshold_records": 0},
    "audio": {"threshold_mb": 30, "threshold_records": 0},
    "vehicle": {"threshold_mb": 30, "threshold_records": 0},
}

MARKET_SECTOR_DWELL_SECONDS = {
    "camera": 5 * 60,
    "credentials": 3 * 60,
    "financial": 6 * 60,
    "atm": 5 * 60,
    "gps": 5 * 60,
    "device": 5 * 60,
    "personal": 5 * 60,
    "network": 5 * 60,
    "audio": 5 * 60,
    "vehicle": 5 * 60,
}

RESOURCE_MARKET_CATEGORY = {
    "gps_logs": "location",
    "location_history": "location",
    "device_logs": "device_intelligence",
    "personal_records": "personal",
    "financial_records": "financial",
    "credentials": "credentials",
    "email_accounts": "credentials",
    "call_history": "personal",
    "messenger_data": "personal",
    "audio_transcript": "audio",
    "camera_dump": "surveillance",
    "video_material": "surveillance",
    "atm_dump": "financial",
    "vehicle_diagnostics": "vehicle",
    "wifi_networks": "network",
    "hotspot_database": "network",
}

MARKET_CATEGORY_BASE_VALUE = {
    "location": 22,
    "device_intelligence": 42,
    "personal": 48,
    "financial": 75,
    "credentials": 95,
    "surveillance": 38,
    "audio": 36,
    "vehicle": 44,
    "network": 32,
}

RESOURCE_COMPLETENESS_FIELDS = {
    "gps_logs": ["checkpoint_count", "duration", "accuracy", "route_confidence"],
    "location_history": ["checkpoint_count", "time_span", "accuracy", "target_identity_confidence"],
    "device_logs": ["events_count", "time_span", "device_identity", "signal_quality"],
    "personal_records": ["identity_fields", "profile_depth", "confidence", "freshness"],
    "financial_records": ["transactions_count", "time_span", "account_confidence", "amount_visibility"],
    "credentials": ["credential_count", "validity", "scope", "freshness"],
    "email_accounts": ["account_count", "domain_quality", "access_validity", "metadata_depth"],
    "call_history": ["call_count", "time_span", "contact_resolution", "metadata_depth"],
    "messenger_data": ["thread_count", "metadata_depth", "identity_confidence", "freshness"],
    "audio_transcript": ["duration", "speaker_count", "transcript_quality", "keyword_hits"],
    "camera_dump": ["duration", "frame_quality", "angle_quality", "event_hits"],
    "video_material": ["duration", "resolution", "event_hits", "continuity"],
    "atm_dump": ["record_count", "time_span", "account_confidence", "terminal_identity"],
    "vehicle_diagnostics": ["systems_count", "fault_depth", "ecu_access", "telemetry_quality"],
    "wifi_networks": ["network_count", "security_types", "signal_strength", "geo_accuracy"],
    "hotspot_database": ["hotspot_count", "coverage_area", "freshness", "geo_accuracy"],
}

QUALITY_SCORE_BY_LABEL = {
    "placeholder": 52,
    "low": 35,
    "medium": 62,
    "high": 82,
    "sealed": 70,
}


def clamp_int(value, minimum=0, maximum=100, default=0):
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        number = int(default)
    return max(minimum, min(maximum, number))


def completeness_tier_for_percent(percent):
    percent = clamp_int(percent)
    if percent >= 85:
        return "rich"
    if percent >= 60:
        return "enhanced"
    if percent >= 35:
        return "basic"
    return "fragment"


def quality_score_from_metadata(metadata, summary=None):
    summary = summary if isinstance(summary, dict) else {}
    if "quality_score" in metadata:
        return clamp_int(metadata.get("quality_score"), default=50)
    if "quality_score" in summary:
        return clamp_int(summary.get("quality_score"), default=50)
    quality = str(metadata.get("quality") or summary.get("quality") or "").strip().lower()
    frame_quality = str(metadata.get("frame_quality") or "").strip().lower()
    if quality in QUALITY_SCORE_BY_LABEL:
        return QUALITY_SCORE_BY_LABEL[quality]
    if frame_quality in QUALITY_SCORE_BY_LABEL:
        return QUALITY_SCORE_BY_LABEL[frame_quality]
    return 50


def default_missing_fields_for_resources(resource_types, metadata):
    missing = []
    for resource_type in resource_types:
        for field in RESOURCE_COMPLETENESS_FIELDS.get(str(resource_type), []):
            if field not in metadata and field not in missing:
                missing.append(field)
    return missing[:10]


def infer_file_completeness(entry, metadata, resource_types):
    summary = entry.get("summary") if isinstance(entry.get("summary"), dict) else {}
    completeness = metadata.get("completeness") if isinstance(metadata.get("completeness"), dict) else {}
    explicit_percent = (
        entry.get("completeness_percent")
        or summary.get("completeness_percent")
        or completeness.get("percent")
        or metadata.get("completeness_percent")
    )
    quality_score = quality_score_from_metadata(metadata, summary)

    if explicit_percent is not None:
        percent = clamp_int(explicit_percent, default=50)
    else:
        folder = str(entry.get("file_category") or "")
        record_count = (
            metadata.get("record_count")
            or metadata.get("checkpoint_count")
            or metadata.get("collected_count")
            or summary.get("record_count")
            or summary.get("credential_count")
            or len(entry.get("records", []) or [])
            or len(entry.get("checkpoints", []) or [])
            or 1
        )
        try:
            record_count = int(record_count)
        except (TypeError, ValueError):
            record_count = 1
        resource_bonus = max(0, len(resource_types) - 1) * 8
        if folder == "gps":
            percent = 35 + min(45, record_count * 6) + resource_bonus
        elif folder in {"device", "personal"}:
            total = len(DEVICE_INTELLIGENCE_RESOURCE_TYPES)
            known = len([item for item in resource_types if item in DEVICE_INTELLIGENCE_RESOURCE_TYPES])
            percent = int(round((known / total) * 100)) if total else 40
        elif folder == "camera":
            duration = int(metadata.get("duration_seconds") or summary.get("duration_seconds") or 60)
            percent = 30 + min(35, duration // 12) + (20 if "video_material" in resource_types else 0)
        elif folder in {"atm", "financial"}:
            percent = 45 + min(35, record_count * 4) + resource_bonus
        elif folder == "credentials":
            percent = 48 + min(35, record_count * 7)
        else:
            percent = 45 + resource_bonus
        percent = clamp_int(percent, default=50)

    tier = (
        entry.get("completeness_tier")
        or summary.get("tier")
        or completeness.get("tier")
        or metadata.get("completeness_tier")
        or completeness_tier_for_percent(percent)
    )
    missing_fields = (
        entry.get("missing_fields")
        or summary.get("missing_fields")
        or completeness.get("missing")
        or completeness.get("missing_fields")
        or metadata.get("missing_fields")
        or default_missing_fields_for_resources(resource_types, metadata)
    )
    if not isinstance(missing_fields, list):
        missing_fields = [str(missing_fields)]
    missing_fields = [str(item) for item in missing_fields if str(item).strip()]
    return {
        "percent": percent,
        "tier": str(tier),
        "missing_fields": missing_fields,
        "quality_score": quality_score,
    }


def ghost_exchange_market_category(file_entry):
    resources = file_entry.get("resource_types") if isinstance(file_entry.get("resource_types"), list) else []
    for resource_type in resources:
        category = RESOURCE_MARKET_CATEGORY.get(str(resource_type))
        if category:
            return category
    return RESOURCE_MARKET_CATEGORY.get(str(file_entry.get("file_category") or ""), "unknown")


def market_sector_for_file(file_entry):
    if not isinstance(file_entry, dict):
        return "unknown"
    file_category = str(file_entry.get("file_category") or "").strip()
    if file_category in MARKET_SECTOR_BY_FILE_CATEGORY:
        return MARKET_SECTOR_BY_FILE_CATEGORY[file_category]

    market_category = ghost_exchange_market_category(file_entry)
    if market_category in MARKET_SECTOR_BY_MARKET_CATEGORY:
        return MARKET_SECTOR_BY_MARKET_CATEGORY[market_category]
    return "unknown"


def is_ghost_exchange_sellable(file_entry):
    if not isinstance(file_entry, dict):
        return False
    file_category = str(file_entry.get("file_category") or "")
    if file_category not in GHOST_EXCHANGE_FILE_CATEGORIES:
        return False
    resources = [str(item) for item in file_entry.get("resource_types", []) if str(item).strip()]
    if not resources:
        return False
    if all(resource in GHOST_EXCHANGE_BLOCKED_RESOURCES for resource in resources):
        return False
    if str(file_entry.get("market_status") or "not_listed") in {"sold", "deleted", "archived"}:
        return False
    return True


def is_market_eligible_file(file_entry):
    if not isinstance(file_entry, dict):
        return False
    if str(file_entry.get("market_status") or "not_listed") in {"sold", "deleted", "archived"}:
        return False
    if isinstance(file_entry.get("sellable"), bool):
        return file_entry["sellable"] is True
    return is_ghost_exchange_sellable(file_entry)


def normalize_file_market_status(file_entry):
    if not isinstance(file_entry, dict):
        return "created"
    raw_status = str(file_entry.get("market_status") or "not_listed").strip() or "not_listed"
    if raw_status in {"sold", "archived", "listed", "queued_for_market"}:
        return raw_status
    if raw_status == "not_listed" and is_market_eligible_file(file_entry):
        return "queued_for_market"
    return LEGACY_MARKET_STATUS_MAP.get(raw_status, "created")


def can_store_runtime_file(profile, file_entry):
    if not isinstance(profile, dict) or not isinstance(file_entry, dict):
        return False
    normalize_profile_storage_capacity(profile)
    capacity = clamp_storage_number(
        profile.get("storage_capacity"),
        default=DEFAULT_STORAGE_CAPACITY_MB,
        minimum=0,
    )
    current_used = profile.get("storage_used")
    if current_used is None:
        current_used = calculate_profile_storage_used(profile)
    current_used = clamp_storage_number(current_used, default=0, minimum=0)
    file_size = clamp_storage_number(
        file_entry.get("file_size") or (file_entry.get("metadata") or {}).get("file_size"),
        default=estimate_runtime_file_size(file_entry.get("file_category"), file_entry),
        minimum=1,
    )
    return current_used + file_size <= capacity


def build_storage_full_result(profile, operation, file_entry):
    profile = profile if isinstance(profile, dict) else {}
    normalize_profile_storage_capacity(profile)
    operation = operation if isinstance(operation, dict) else {}
    file_entry = file_entry if isinstance(file_entry, dict) else {}
    capacity = clamp_storage_number(
        profile.get("storage_capacity"),
        default=DEFAULT_STORAGE_CAPACITY_MB,
        minimum=0,
    )
    current_used = profile.get("storage_used")
    if current_used is None:
        current_used = calculate_profile_storage_used(profile)
    current_used = clamp_storage_number(current_used, default=0, minimum=0)
    file_size = clamp_storage_number(
        file_entry.get("file_size") or (file_entry.get("metadata") or {}).get("file_size"),
        default=estimate_runtime_file_size(file_entry.get("file_category"), file_entry),
        minimum=1,
    )
    return {
        "status": "storage_full",
        "result": "dropped_no_space",
        "reason": "storage_capacity_exceeded",
        "operation_id": operation.get("operation_id") or operation.get("id"),
        "operation_type": operation.get("operation_type"),
        "file_name": file_entry.get("name") or file_entry.get("filename"),
        "file_category": file_entry.get("file_category"),
        "file_size": file_size,
        "storage_capacity": capacity,
        "storage_used": current_used,
        "storage_required": current_used + file_size,
        "storage_unit": profile.get("storage_unit", "MB"),
    }


def runtime_storage_drop_key(operation, file_entry):
    operation = operation if isinstance(operation, dict) else {}
    file_entry = file_entry if isinstance(file_entry, dict) else {}
    operation_id = operation.get("operation_id") or operation.get("id") or "operation"
    file_name = file_entry.get("name") or file_entry.get("filename") or "file"
    file_category = file_entry.get("file_category") or "data"
    return f"{operation_id}:{file_category}:{file_name}"


def append_storage_full_message(profile, drop_key):
    if not isinstance(profile, dict):
        return False
    messages = profile.setdefault("system_messages", [])
    if not isinstance(messages, list):
        messages = []
        profile["system_messages"] = messages
    if any(isinstance(item, dict) and item.get("storage_drop_key") == drop_key for item in messages):
        return False
    numeric_ids = [
        int(item.get("id", 0))
        for item in messages
        if isinstance(item, dict) and str(item.get("id", "")).isdigit()
    ]
    messages.append({
        "id": max(numeric_ids, default=0) + 1,
        "type": "warning",
        "title": "Brak miejsca",
        "text": "Brak miejsca na zapis danych.",
        "status": "new",
        "created_at": runtime_file_now(),
        "storage_drop_key": drop_key,
    })
    return True


def record_storage_full_drop(profile, operation, file_entry):
    resource_buffer = operation.setdefault("resource_buffer", {}) if isinstance(operation, dict) else {}
    drop_key = runtime_storage_drop_key(operation, file_entry)
    drops = resource_buffer.setdefault("storage_drops", [])
    if not isinstance(drops, list):
        drops = []
        resource_buffer["storage_drops"] = drops
    for item in drops:
        if isinstance(item, dict) and item.get("drop_key") == drop_key:
            return item, False

    result = build_storage_full_result(profile, operation, file_entry)
    result["drop_key"] = drop_key
    drops.append(result)
    resource_buffer["storage_full"] = True
    resource_buffer["last_storage_result"] = result
    append_storage_full_message(profile, drop_key)
    return result, True


def append_runtime_file_if_space(profile, operation, folder, file_entry):
    folder = str(folder or (file_entry or {}).get("file_category") or "").strip()
    if not folder:
        folder = "system"
    candidate = normalize_runtime_file_entry(dict(file_entry or {}), folder)
    candidate_id = str(candidate.get("id") or "")
    if candidate_id and candidate_id in sold_market_file_ids(profile):
        return {
            "stored": False,
            "file": None,
            "result": {
                "status": "already_sold",
                "file_id": candidate_id,
                "file_name": candidate.get("name") or candidate.get("filename"),
            },
            "changed": False,
        }
    if can_store_runtime_file(profile, candidate):
        files = ensure_files_inventory(profile)
        files.setdefault(folder, [])
        files[folder].append(candidate)
        normalize_profile_storage(profile)
        return {
            "stored": True,
            "file": candidate,
            "result": None,
            "changed": True,
        }

    result, changed = record_storage_full_drop(profile, operation, candidate)
    return {
        "stored": False,
        "file": None,
        "result": result,
        "changed": changed,
    }


def runtime_file_record_count(file_entry):
    if not isinstance(file_entry, dict):
        return 0
    metadata = file_entry.get("metadata") if isinstance(file_entry.get("metadata"), dict) else {}
    summary = file_entry.get("summary") if isinstance(file_entry.get("summary"), dict) else {}
    value = (
        metadata.get("record_count")
        or metadata.get("checkpoint_count")
        or metadata.get("collected_count")
        or metadata.get("credential_count")
        or metadata.get("network_count")
        or metadata.get("systems_count")
        or summary.get("record_count")
        or summary.get("credential_count")
        or summary.get("checkpoint_count")
        or len(file_entry.get("records", []) or [])
        or len(file_entry.get("checkpoints", []) or [])
        or 1
    )
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 1


def queue_market_eligible_files(profile):
    if not isinstance(profile, dict):
        return 0
    files = ensure_files_inventory(profile)
    queued_at = runtime_file_now()
    changed = 0
    for folder, items in files.items():
        if not isinstance(items, list):
            continue
        for index, file_entry in enumerate(items):
            if not isinstance(file_entry, dict):
                continue
            status = str(file_entry.get("market_status") or "not_listed")
            if status in {"sold", "deleted", "archived"}:
                continue
            if not is_market_eligible_file(file_entry):
                continue
            if status == "listed":
                sector = market_sector_for_file(file_entry)
                if file_entry.get("market_sector") != sector:
                    file_entry["market_sector"] = sector
                    items[index] = normalize_runtime_file_entry(file_entry, folder)
                    items[index]["market_sector"] = sector
                    changed += 1
                continue

            item_changed = False
            if file_entry.get("market_status") != "queued_for_market":
                file_entry["market_status"] = "queued_for_market"
                item_changed = True
            if not file_entry.get("queued_at"):
                file_entry["queued_at"] = queued_at
                item_changed = True
            sector = market_sector_for_file(file_entry)
            if file_entry.get("market_sector") != sector:
                file_entry["market_sector"] = sector
                item_changed = True
            if item_changed:
                items[index] = normalize_runtime_file_entry(file_entry, folder)
                # normalize_runtime_file_entry preserves queued_at/market_sector through dict copy.
                items[index]["queued_at"] = file_entry.get("queued_at")
                items[index]["market_sector"] = sector
                changed += 1
    return changed


def market_sector_estimated_sale_time(pending_mb, threshold_mb, pending_records, threshold_records):
    missing_mb = max(0, int(threshold_mb or 0) - int(pending_mb or 0))
    missing_records = max(0, int(threshold_records or 0) - int(pending_records or 0))
    if missing_mb == 0 and missing_records == 0:
        return "~5 min"
    estimate = max(5, min(45, missing_mb * 2 + missing_records * 3))
    return f"~{estimate} min"


def market_runtime_now(now=None):
    if isinstance(now, datetime):
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc)
    if isinstance(now, (int, float)):
        return datetime.fromtimestamp(float(now), tz=timezone.utc)
    if isinstance(now, str) and now.strip():
        parsed = parse_operation_timestamp(now)
        if parsed is not None:
            return datetime.fromtimestamp(parsed, tz=timezone.utc)
    return datetime.now(timezone.utc)


def market_runtime_iso(now=None):
    return market_runtime_now(now).isoformat().replace("+00:00", "Z")


def market_oldest_entry_time_iso(entries, now_dt):
    now_dt = market_runtime_now(now_dt)
    timestamps = []
    for item in entries or []:
        if not isinstance(item, dict):
            continue
        for value in (item.get("listed_at"), item.get("queued_at"), item.get("created_at")):
            ts = parse_operation_timestamp(value)
            if ts is not None and ts <= now_dt.timestamp():
                timestamps.append(ts)
                break
    if not timestamps:
        return None
    return market_runtime_iso(min(timestamps))


def market_batch_id(username, sector, file_entries):
    file_ids = sorted(
        str(item.get("id") or item.get("name") or item.get("filename") or "")
        for item in file_entries
        if isinstance(item, dict)
    )
    seed = "|".join([str(username or ""), str(sector or ""), *file_ids])
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"batch_{operation_filename_slug(str(username or 'user'))}_{operation_filename_slug(str(sector or 'market'))}_{digest}"


def market_batch_already_settled(profile, batch_id):
    return market_batch_settlement_record(profile, batch_id) is not None


def market_batch_settlement_record(profile, batch_id):
    if not batch_id:
        return None
    for item in profile.get("market_history", []) or []:
        if isinstance(item, dict) and str(item.get("batch_id") or item.get("id") or "") == str(batch_id):
            return item
    files = ensure_files_inventory(profile)
    for item in files.get("market", []):
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        sale = item.get("sale") if isinstance(item.get("sale"), dict) else {}
        if str(item.get("batch_id") or metadata.get("batch_id") or sale.get("batch_id") or "") == str(batch_id):
            return item
    return None


def sold_market_file_ids(profile):
    sold_ids = set()
    if not isinstance(profile, dict):
        return sold_ids

    for item in profile.get("market_history", []) or []:
        if not isinstance(item, dict):
            continue
        if item.get("file_id"):
            sold_ids.add(str(item.get("file_id")))
        if isinstance(item.get("file_ids"), list):
            sold_ids.update(str(value) for value in item.get("file_ids") if str(value).strip())
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        sale = item.get("sale") if isinstance(item.get("sale"), dict) else {}
        for source in (metadata, sale):
            if source.get("file_id"):
                sold_ids.add(str(source.get("file_id")))
            if isinstance(source.get("file_ids"), list):
                sold_ids.update(str(value) for value in source.get("file_ids") if str(value).strip())

    files = ensure_files_inventory(profile)
    for item in files.get("market", []) or []:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        sale = item.get("sale") if isinstance(item.get("sale"), dict) else {}
        for source in (metadata, sale):
            if source.get("file_id"):
                sold_ids.add(str(source.get("file_id")))
            if isinstance(source.get("file_ids"), list):
                sold_ids.update(str(value) for value in source.get("file_ids") if str(value).strip())
    return sold_ids


def cleanup_already_settled_market_files(profile, files, batch_id, entries):
    settlement = market_batch_settlement_record(profile, batch_id)
    if not settlement:
        return 0

    current_ids = {str(item.get("id") or "") for item in entries if isinstance(item, dict) and item.get("id")}
    if not current_ids:
        return 0

    settled_ids = set()
    if isinstance(settlement.get("file_ids"), list):
        settled_ids.update(str(item) for item in settlement.get("file_ids") if str(item).strip())
    metadata = settlement.get("metadata") if isinstance(settlement.get("metadata"), dict) else {}
    sale = settlement.get("sale") if isinstance(settlement.get("sale"), dict) else {}
    for source in (metadata, sale):
        if isinstance(source.get("file_ids"), list):
            settled_ids.update(str(item) for item in source.get("file_ids") if str(item).strip())

    if settled_ids and not current_ids.issubset(settled_ids):
        return 0

    removed = remove_market_batch_files(files, current_ids)
    if removed:
        normalize_profile_storage(profile)
    return len(removed)


def market_sector_threshold_reached(sector, pending_mb, pending_records):
    threshold = MARKET_SECTOR_THRESHOLDS.get(str(sector or ""), {"threshold_mb": 25, "threshold_records": 0})
    threshold_mb = int(threshold.get("threshold_mb") or 0)
    threshold_records = int(threshold.get("threshold_records") or 0)
    mb_ready = threshold_mb <= 0 or int(pending_mb or 0) >= threshold_mb
    records_ready = threshold_records <= 0 or int(pending_records or 0) >= threshold_records
    return mb_ready and records_ready


def market_batch_price(file_entries):
    total = 0
    for item in file_entries:
        if isinstance(item, dict):
            total += ghost_exchange_price_preview(item)
    file_count = max(1, len(file_entries))
    volume = sum(
        clamp_storage_number(
            item.get("file_size") or (item.get("metadata") or {}).get("file_size"),
            default=estimate_runtime_file_size(item.get("file_category"), item),
            minimum=1,
        )
        for item in file_entries
        if isinstance(item, dict)
    )
    volume_bonus = min(80, volume)
    batch_bonus = min(45, max(0, file_count - 1) * 8)
    return max(5, int(round(total + volume_bonus + batch_bonus)))


def build_ghost_exchange_batch_sale_record(username, sector, batch_id, file_entries, price, sold_at):
    file_names = [item.get("name") or item.get("filename") for item in file_entries if isinstance(item, dict)]
    file_ids = [item.get("id") for item in file_entries if isinstance(item, dict)]
    resource_types = []
    for item in file_entries:
        if isinstance(item, dict):
            resource_types.extend([str(value) for value in item.get("resource_types", []) if str(value).strip()])
    resource_types = list(dict.fromkeys(resource_types))
    volume_mb = sum(
        clamp_storage_number(
            item.get("file_size") or (item.get("metadata") or {}).get("file_size"),
            default=estimate_runtime_file_size(item.get("file_category"), item),
            minimum=1,
        )
        for item in file_entries
        if isinstance(item, dict)
    )
    record_count = sum(runtime_file_record_count(item) for item in file_entries if isinstance(item, dict))
    market_category = ghost_exchange_market_category(file_entries[0]) if file_entries else "unknown"
    return normalize_runtime_file_entry({
        "id": batch_id,
        "batch_id": batch_id,
        "name": f"sold_batch_{sector}_{batch_id}.pkg",
        "file_category": "market",
        "directory": "/market/sold",
        "preview_mode": "table",
        "resource_types": resource_types,
        "status": "sold",
        "sellable": False,
        "market_status": "sold",
        "created_at": sold_at,
        "metadata": {
            "batch_id": batch_id,
            "seller_username": username,
            "market_sector": sector,
            "market_category": market_category,
            "buyer_type": ghost_exchange_buyer_type(market_category),
            "price": price,
            "currency": "HC",
            "sold_at": sold_at,
            "file_ids": file_ids,
            "file_names": file_names,
            "file_count": len(file_entries),
            "volume_mb": volume_mb,
            "record_count": record_count,
        },
        "sale": {
            "batch_id": batch_id,
            "market_sector": sector,
            "market_category": market_category,
            "buyer_type": ghost_exchange_buyer_type(market_category),
            "price": price,
            "currency": "HC",
            "sold_at": sold_at,
            "file_count": len(file_entries),
            "volume_mb": volume_mb,
            "record_count": record_count,
        },
    }, "market")


def remove_market_batch_files(files, file_ids):
    file_ids = {str(item) for item in file_ids if str(item).strip()}
    removed = []
    for folder in list(GHOST_EXCHANGE_FILE_CATEGORIES):
        kept = []
        for item in files.get(folder, []):
            if isinstance(item, dict) and str(item.get("id") or "") in file_ids:
                removed.append(item)
                continue
            kept.append(item)
        files[folder] = kept
    return removed


def market_entries_volume_mb(entries):
    return sum(
        clamp_storage_number(
            item.get("file_size") or (item.get("metadata") or {}).get("file_size"),
            default=estimate_runtime_file_size(item.get("file_category"), item),
            minimum=1,
        )
        for item in entries
        if isinstance(item, dict)
    )


def market_entries_record_count(entries):
    return sum(runtime_file_record_count(item) for item in entries if isinstance(item, dict))


def refresh_market_runtime(username, profile, now=None, persist=False):
    if not isinstance(profile, dict):
        return {"changed": False, "queued": 0, "listed": 0, "settled": 0, "sales": []}

    files = ensure_files_inventory(profile)
    now_dt = market_runtime_now(now)
    now_iso = market_runtime_iso(now_dt)
    changed = False
    queued = queue_market_eligible_files(profile)
    if queued:
        changed = True
    files = ensure_files_inventory(profile)

    sector_entries = {}
    for folder in GHOST_EXCHANGE_FILE_CATEGORIES:
        for file_entry in files.get(folder, []):
            if not isinstance(file_entry, dict):
                continue
            market_status = normalize_file_market_status(file_entry)
            if market_status not in {"queued_for_market", "listed"}:
                continue
            if not is_market_eligible_file(file_entry):
                continue
            sector = file_entry.get("market_sector") or market_sector_for_file(file_entry)
            sector_entries.setdefault(sector, []).append(file_entry)

    listed_count = 0
    sales = []
    for sector, entries in sector_entries.items():
        listed_batches = {}
        legacy_listed_entries = []
        queued_entries = []
        for item in entries:
            batch_id = str(item.get("batch_id") or "").strip()
            if item.get("market_status") == "listed" and batch_id:
                listed_batches.setdefault(batch_id, []).append(item)
            elif item.get("market_status") == "listed":
                legacy_listed_entries.append(item)
            else:
                queued_entries.append(item)

        batches_to_process = list(listed_batches.items())
        if legacy_listed_entries:
            batches_to_process.append((market_batch_id(username, sector, legacy_listed_entries), legacy_listed_entries))
        if queued_entries:
            pending_mb = market_entries_volume_mb(queued_entries)
            pending_records = market_entries_record_count(queued_entries)
            if market_sector_threshold_reached(sector, pending_mb, pending_records):
                batches_to_process.append((market_batch_id(username, sector, queued_entries), queued_entries))

        for batch_id, batch_entries in batches_to_process:
            if market_batch_already_settled(profile, batch_id):
                recovered = cleanup_already_settled_market_files(profile, files, batch_id, batch_entries)
                if recovered:
                    changed = True
                continue

            listed_at = None
            for item in batch_entries:
                if item.get("batch_id") == batch_id and item.get("listed_at"):
                    listed_at = item.get("listed_at")
                    break
            already_listed = any(item.get("market_status") == "listed" for item in batch_entries)
            if not listed_at:
                listed_at = market_oldest_entry_time_iso(batch_entries, now_dt) or now_iso
                entry_ids = {str(item.get("id") or "") for item in batch_entries if isinstance(item, dict)}
                files = ensure_files_inventory(profile)
                for item in batch_entries:
                    item["market_status"] = "listed"
                    item["listed_at"] = listed_at
                    item["batch_id"] = batch_id
                    item["market_sector"] = sector
                for folder in GHOST_EXCHANGE_FILE_CATEGORIES:
                    for item in files.get(folder, []):
                        if isinstance(item, dict) and str(item.get("id") or "") in entry_ids:
                            item["market_status"] = "listed"
                            item["listed_at"] = listed_at
                            item["batch_id"] = batch_id
                            item["market_sector"] = sector
                listed_count += len(batch_entries)
                changed = True

            listed_ts = parse_operation_timestamp(listed_at)
            if listed_ts is None:
                listed_ts = now_dt.timestamp()
            dwell_seconds = MARKET_SECTOR_DWELL_SECONDS.get(sector, 5 * 60)
            if now_dt.timestamp() - listed_ts < dwell_seconds:
                continue

            price = market_batch_price(batch_entries)
            sold_at = now_iso
            sale_record = build_ghost_exchange_batch_sale_record(username, sector, batch_id, batch_entries, price, sold_at)
            file_ids = [item.get("id") for item in batch_entries]
            removed = remove_market_batch_files(files, file_ids)
            if not removed:
                continue
            files.setdefault("market", []).append(sale_record)
            history_entry = {
                "id": batch_id,
                "batch_id": batch_id,
                "market_sector": sector,
                "market_category": sale_record["metadata"].get("market_category"),
                "buyer_type": sale_record["metadata"].get("buyer_type"),
                "price": price,
                "currency": "HC",
                "sold_at": sold_at,
                "status": "sold",
                "file_ids": file_ids,
                "file_names": [item.get("name") or item.get("filename") for item in batch_entries],
                "file_count": len(batch_entries),
                "volume_mb": sale_record["metadata"].get("volume_mb"),
                "record_count": sale_record["metadata"].get("record_count"),
            }
            profile.setdefault("market_history", []).append(history_entry)
            profile["hackcoins"] = int(profile.get("hackcoins", 0) or 0) + price
            profile.setdefault("system_messages", []).append({
                "title": "Ghost Exchange",
                "text": f"Sprzedano paczke danych {sector} za {price} HC.",
                "type": "success",
                "status": "new",
                "created_at": sold_at,
                "batch_id": batch_id,
            })
            add_cyberner_direct_notification(
                username,
                "Ghost Exchange",
                "Ghost Exchange",
                "Sprzedano paczke danych",
                (
                    f"Sektor: {sector}\n"
                    f"Liczba plikow: {len(batch_entries)}\n"
                    f"Wolumen: {sale_record['metadata'].get('volume_mb')} MB\n"
                    f"Cena: {price} HC\n"
                    f"Batch: {batch_id}\n"
                    f"Czas: {sold_at}"
                ),
            )
            normalize_files_inventory(profile)
            normalize_profile_storage(profile)
            sales.append(history_entry)
            changed = True

    if persist and changed:
        UserProfileManager(username).update_profile({
            "files": profile.get("files", {}),
            "market_history": profile.get("market_history", []),
            "hackcoins": profile.get("hackcoins", 0),
            "system_messages": profile.get("system_messages", []),
            "storage_capacity": profile.get("storage_capacity"),
            "storage_used": profile.get("storage_used"),
            "storage_unit": profile.get("storage_unit", "MB"),
            "storage_soft_limit": True,
            "storage_over_limit": profile.get("storage_over_limit", False),
        })
        for sale in sales:
            record_wallet_balance_delta(
                username,
                profile.get("hackcoins", 0),
                reason="ghost_exchange_auto_sale",
                dedupe_key=f"wallet:balance:{username}:ghost_exchange:{sale.get('batch_id') or sale.get('id')}",
            )

    return {
        "changed": changed,
        "queued": queued,
        "listed": listed_count,
        "settled": len(sales),
        "sales": sales,
    }


def build_ghost_exchange_sector_payload(profile):
    files = ensure_files_inventory(profile)
    sectors = {
        sector: {
            "sector": sector,
            "pending_files": 0,
            "pending_mb": 0,
            "pending_records": 0,
            "threshold_mb": values.get("threshold_mb", 0),
            "threshold_records": values.get("threshold_records", 0),
            "missing_mb": values.get("threshold_mb", 0),
            "missing_records": values.get("threshold_records", 0),
            "progress_percent": 0,
            "status": "collecting",
            "listed_at": None,
            "batch_id": None,
            "last_transaction": None,
            "estimated_sale_time": market_sector_estimated_sale_time(
                0,
                values.get("threshold_mb", 0),
                0,
                values.get("threshold_records", 0),
            ),
        }
        for sector, values in MARKET_SECTOR_THRESHOLDS.items()
    }

    for folder in GHOST_EXCHANGE_FILE_CATEGORIES:
        for file_entry in files.get(folder, []):
            if not isinstance(file_entry, dict):
                continue
            market_status = normalize_file_market_status(file_entry)
            if market_status not in {"queued_for_market", "listed"}:
                continue
            if not is_market_eligible_file(file_entry):
                continue
            sector = file_entry.get("market_sector") or market_sector_for_file(file_entry)
            if sector not in sectors:
                sectors[sector] = {
                    "sector": sector,
                    "pending_files": 0,
                    "pending_mb": 0,
                    "pending_records": 0,
                    "threshold_mb": 25,
                    "threshold_records": 0,
                    "missing_mb": 25,
                    "missing_records": 0,
                    "progress_percent": 0,
                    "status": "collecting",
                    "listed_at": None,
                    "batch_id": None,
                    "last_transaction": None,
                    "estimated_sale_time": "~25 min",
                }
            volume = clamp_storage_number(
                file_entry.get("file_size") or (file_entry.get("metadata") or {}).get("file_size"),
                default=estimate_runtime_file_size(folder, file_entry),
                minimum=1,
            )
            sectors[sector]["pending_files"] += 1
            sectors[sector]["pending_mb"] += volume
            sectors[sector]["pending_records"] += runtime_file_record_count(file_entry)
            if market_status == "listed":
                sectors[sector]["status"] = "trading"
                sectors[sector]["listed_at"] = sectors[sector]["listed_at"] or file_entry.get("listed_at")
                sectors[sector]["batch_id"] = sectors[sector]["batch_id"] or file_entry.get("batch_id")

    for sector, payload in sectors.items():
        threshold_mb = int(payload.get("threshold_mb") or 0)
        threshold_records = int(payload.get("threshold_records") or 0)
        pending_mb = int(payload.get("pending_mb") or 0)
        pending_records = int(payload.get("pending_records") or 0)
        payload["missing_mb"] = max(0, threshold_mb - pending_mb)
        payload["missing_records"] = max(0, threshold_records - pending_records)
        mb_progress = 100 if threshold_mb <= 0 else min(100, int(round((pending_mb / threshold_mb) * 100)))
        record_progress = 100 if threshold_records <= 0 else min(100, int(round((pending_records / threshold_records) * 100)))
        payload["progress_percent"] = min(mb_progress, record_progress)
        payload["estimated_sale_time"] = market_sector_estimated_sale_time(
            pending_mb,
            threshold_mb,
            pending_records,
            threshold_records,
        )
        if payload.get("status") != "trading" and payload.get("progress_percent") >= 100:
            payload["status"] = "ready_to_list"

    for entry in reversed(profile.get("market_history", []) or []):
        if not isinstance(entry, dict):
            continue
        sector = entry.get("market_sector")
        if sector in sectors and sectors[sector].get("last_transaction") is None:
            sectors[sector]["last_transaction"] = entry
    return sorted(sectors.values(), key=lambda item: item["sector"])


def ghost_exchange_transaction_timestamp(entry):
    if not isinstance(entry, dict):
        return None
    value = entry.get("sold_at") or entry.get("created_at")
    if not value and isinstance(entry.get("sale"), dict):
        value = entry["sale"].get("sold_at")
    if not value and isinstance(entry.get("metadata"), dict):
        value = entry["metadata"].get("sold_at")
    ts = parse_operation_timestamp(value)
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def normalize_ghost_exchange_transaction(entry):
    if not isinstance(entry, dict):
        return None
    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
    sale = entry.get("sale") if isinstance(entry.get("sale"), dict) else {}
    sector = (
        entry.get("market_sector")
        or metadata.get("market_sector")
        or sale.get("market_sector")
        or MARKET_SECTOR_BY_MARKET_CATEGORY.get(str(entry.get("market_category") or metadata.get("market_category") or sale.get("market_category") or ""))
        or entry.get("source_file_category")
        or "unknown"
    )
    price = entry.get("price") or metadata.get("price") or sale.get("price") or 0
    volume = entry.get("volume_mb") or metadata.get("volume_mb") or sale.get("volume_mb") or 0
    file_count = entry.get("file_count") or metadata.get("file_count") or sale.get("file_count") or 1
    record_count = entry.get("record_count") or metadata.get("record_count") or sale.get("record_count") or 0
    sold_at_dt = ghost_exchange_transaction_timestamp(entry)
    sold_at = sold_at_dt.isoformat().replace("+00:00", "Z") if sold_at_dt else (
        entry.get("sold_at") or metadata.get("sold_at") or sale.get("sold_at") or ""
    )
    return {
        "id": entry.get("batch_id") or entry.get("id") or sale.get("batch_id") or sale.get("file_id"),
        "batch_id": entry.get("batch_id") or metadata.get("batch_id") or sale.get("batch_id"),
        "file_name": entry.get("file_name") or metadata.get("sold_file_name") or sale.get("file_name") or entry.get("name") or "market_batch",
        "market_sector": str(sector or "unknown"),
        "market_category": entry.get("market_category") or metadata.get("market_category") or sale.get("market_category") or "unknown",
        "buyer_type": entry.get("buyer_type") or metadata.get("buyer_type") or sale.get("buyer_type") or "system buyer",
        "price": int(price or 0),
        "currency": entry.get("currency") or metadata.get("currency") or sale.get("currency") or "HC",
        "sold_at": sold_at,
        "status": entry.get("status") or "sold",
        "file_count": int(file_count or 0),
        "volume_mb": clamp_storage_number(volume, default=0, minimum=0),
        "record_count": int(record_count or 0),
    }


def collect_ghost_exchange_transactions(profile):
    transactions = []
    seen = set()
    for entry in profile.get("market_history", []) or []:
        transaction = normalize_ghost_exchange_transaction(entry)
        if not transaction:
            continue
        key = str(transaction.get("batch_id") or transaction.get("id") or "")
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        transactions.append(transaction)
    files = ensure_files_inventory(profile)
    for entry in files.get("market", []):
        transaction = normalize_ghost_exchange_transaction(entry)
        if not transaction:
            continue
        key = str(transaction.get("batch_id") or transaction.get("id") or "")
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        transactions.append(transaction)
    transactions.sort(
        key=lambda item: parse_operation_timestamp(item.get("sold_at")) or 0,
        reverse=True,
    )
    return transactions


def build_ghost_exchange_history_7d(transactions, now=None):
    now_dt = market_runtime_now(now)
    days = []
    for offset in range(6, -1, -1):
        day = (now_dt - timedelta(days=offset)).date()
        days.append({
            "date": day.isoformat(),
            "label": "Dzisiaj" if offset == 0 else ("Wczoraj" if offset == 1 else f"{offset} dni temu"),
            "hc": 0,
            "files": 0,
            "volume_mb": 0,
            "sectors": {sector: 0 for sector in MARKET_SECTOR_THRESHOLDS.keys()},
        })
    by_date = {item["date"]: item for item in days}
    for transaction in transactions:
        sold_at = ghost_exchange_transaction_timestamp(transaction)
        if sold_at is None:
            continue
        bucket = by_date.get(sold_at.date().isoformat())
        if not bucket:
            continue
        sector = str(transaction.get("market_sector") or "unknown")
        bucket["hc"] += int(transaction.get("price") or 0)
        bucket["files"] += int(transaction.get("file_count") or 0)
        bucket["volume_mb"] += clamp_storage_number(transaction.get("volume_mb"), default=0, minimum=0)
        bucket.setdefault("sectors", {})
        bucket["sectors"][sector] = int(bucket["sectors"].get(sector, 0) or 0) + int(transaction.get("price") or 0)
    return days


def build_ghost_exchange_dashboard_payload(profile, sectors=None, now=None):
    sectors = sectors if isinstance(sectors, list) else build_ghost_exchange_sector_payload(profile)
    transactions = collect_ghost_exchange_transactions(profile)
    today = market_runtime_now(now).date()
    history_7d = build_ghost_exchange_history_7d(transactions, now=now)
    for sector in sectors:
        sector_name = str(sector.get("sector") or "unknown")
        sector_transactions = [
            item for item in transactions
            if str(item.get("market_sector") or "unknown") == sector_name
        ]
        today_transactions = [
            item for item in sector_transactions
            if (ghost_exchange_transaction_timestamp(item) or datetime.fromtimestamp(0, tz=timezone.utc)).date() == today
        ]
        sold_today_files = sum(int(item.get("file_count") or 0) for item in today_transactions)
        hc_today = sum(int(item.get("price") or 0) for item in today_transactions)
        hc_total = sum(int(item.get("price") or 0) for item in sector_transactions)
        average_price = int(round(hc_total / len(sector_transactions))) if sector_transactions else 0
        sector["listed_batches"] = 1 if sector.get("status") == "trading" and sector.get("batch_id") else 0
        sector["trading"] = sector.get("status") == "trading"
        sector["sold_today_files"] = sold_today_files
        sector["hc_today"] = hc_today
        sector["hc_total"] = hc_total
        sector["average_price"] = average_price
        sector["sparkline"] = [
            day.get("sectors", {}).get(sector_name, 0)
            for day in history_7d
        ]

    pending_files = sum(int(item.get("pending_files") or 0) for item in sectors)
    pending_mb = sum(clamp_storage_number(item.get("pending_mb"), default=0, minimum=0) for item in sectors)
    listed_batches = sum(int(item.get("listed_batches") or 0) for item in sectors)
    sold_today_files = sum(int(item.get("sold_today_files") or 0) for item in sectors)
    hc_today = sum(int(item.get("hc_today") or 0) for item in sectors)
    hc_total = sum(int(item.get("price") or 0) for item in transactions)
    average_price = int(round(hc_total / len(transactions))) if transactions else 0
    return {
        "summary": {
            "pending_files": pending_files,
            "pending_mb": pending_mb,
            "listed_batches": listed_batches,
            "sold_today_files": sold_today_files,
            "hc_today": hc_today,
            "hc_total": hc_total,
            "average_price": average_price,
            "transaction_count": len(transactions),
        },
        "sectors": sectors,
        "recent_transactions": transactions[:8],
        "history_7d": history_7d,
    }


def ghost_exchange_price_preview(file_entry):
    market_category = ghost_exchange_market_category(file_entry)
    base_value = MARKET_CATEGORY_BASE_VALUE.get(market_category, 20)
    resources = file_entry.get("resource_types") if isinstance(file_entry.get("resource_types"), list) else []
    metadata = file_entry.get("metadata") if isinstance(file_entry.get("metadata"), dict) else {}
    summary = file_entry.get("summary") if isinstance(file_entry.get("summary"), dict) else {}

    resource_count = max(1, len(resources))
    resource_bonus = max(0, resource_count - 1) * 8
    record_count = (
        metadata.get("record_count")
        or metadata.get("checkpoint_count")
        or metadata.get("collected_count")
        or summary.get("record_count")
        or summary.get("credential_count")
        or 1
    )
    try:
        volume_bonus = min(60, int(record_count) * 2)
    except (TypeError, ValueError):
        volume_bonus = 0

    completeness_percent = file_entry.get("completeness_percent") or metadata.get("completeness_percent") or 50
    completeness_percent = clamp_int(completeness_percent, default=50)
    completeness_multiplier = 0.7 + (completeness_percent / 100.0) * 0.85
    quality_score = file_entry.get("quality_score") or metadata.get("quality_score") or quality_score_from_metadata(metadata, summary)
    quality_score = clamp_int(quality_score, default=50)
    quality_multiplier = 0.75 + (quality_score / 100.0) * 0.55
    resource_count_multiplier = 1.0 + min(0.25, max(0, resource_count - 1) * 0.04)

    seed = "|".join([
        str(file_entry.get("id") or ""),
        str(file_entry.get("name") or ""),
        str(file_entry.get("source_operation_id") or file_entry.get("operation_id") or ""),
        market_category,
    ])
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    demand_multiplier = 0.9 + (int(digest[:2], 16) / 255.0) * 0.35
    price = int(round(
        (base_value + resource_bonus + volume_bonus)
        * completeness_multiplier
        * quality_multiplier
        * resource_count_multiplier
        * demand_multiplier
    ))
    return max(5, price)


def ghost_exchange_listing_payload(file_entry):
    raw_market_status = file_entry.get("market_status") or "not_listed"
    market_status = "ready_to_list" if raw_market_status == "not_listed" else raw_market_status
    market_volume_mb = clamp_storage_number(
        file_entry.get("file_size") or (file_entry.get("metadata") or {}).get("file_size"),
        default=estimate_runtime_file_size(file_entry.get("file_category"), file_entry),
        minimum=1,
    )
    return {
        "id": file_entry.get("id"),
        "name": file_entry.get("name") or file_entry.get("filename") or "data_package",
        "file_category": file_entry.get("file_category"),
        "directory": file_entry.get("directory"),
        "resource_types": file_entry.get("resource_types", []),
        "market_category": ghost_exchange_market_category(file_entry),
        "market_sector": market_sector_for_file(file_entry),
        "market_volume_mb": market_volume_mb,
        "price_preview": ghost_exchange_price_preview(file_entry),
        "market_status": market_status,
        "normalized_market_status": normalize_file_market_status(file_entry),
        "market_lifecycle_status": normalize_file_market_status(file_entry),
        "raw_market_status": raw_market_status,
        "preview_mode": file_entry.get("preview_mode") or "file",
        "created_at": file_entry.get("created_at"),
        "source_operation_id": file_entry.get("source_operation_id") or file_entry.get("operation_id"),
        "target_snapshot": file_entry.get("target_snapshot", {}),
        "completeness_percent": file_entry.get("completeness_percent"),
        "completeness_tier": file_entry.get("completeness_tier"),
        "missing_fields": file_entry.get("missing_fields", []),
        "quality_score": file_entry.get("quality_score"),
        "metadata": file_entry.get("metadata", {}),
    }


def collect_ghost_exchange_files(profile):
    files = ensure_files_inventory(profile)
    listings = []
    for folder in GHOST_EXCHANGE_FILE_CATEGORIES:
        for file_entry in files.get(folder, []):
            if is_ghost_exchange_sellable(file_entry):
                listings.append(ghost_exchange_listing_payload(file_entry))
    listings.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return listings


def mark_ghost_exchange_preview(profile, file_id):
    files = ensure_files_inventory(profile)
    for folder in GHOST_EXCHANGE_FILE_CATEGORIES:
        for index, file_entry in enumerate(files.get(folder, [])):
            if not isinstance(file_entry, dict):
                continue
            if str(file_entry.get("id") or "") != str(file_id or ""):
                continue
            if not is_ghost_exchange_sellable(file_entry):
                return None
            file_entry["sellable"] = True
            file_entry["market_status"] = "listed_preview"
            file_entry.setdefault("metadata", {})
            if isinstance(file_entry["metadata"], dict):
                file_entry["metadata"]["price_preview"] = ghost_exchange_price_preview(file_entry)
                file_entry["metadata"]["market_category"] = ghost_exchange_market_category(file_entry)
            files[folder][index] = normalize_runtime_file_entry(file_entry, folder)
            return files[folder][index]
    return None


def ghost_exchange_buyer_type(market_category):
    return {
        "location": "urban data broker",
        "device_intelligence": "device intelligence broker",
        "personal": "profile broker",
        "financial": "financial blacknet buyer",
        "credentials": "access broker",
        "surveillance": "surveillance archive",
        "audio": "signal intelligence buyer",
        "vehicle": "vehicle telemetry buyer",
        "network": "network recon buyer",
    }.get(str(market_category or ""), "system buyer")


def build_ghost_exchange_sale_record(username, file_entry, price, sold_at):
    market_category = ghost_exchange_market_category(file_entry)
    source_file_name = file_entry.get("name") or file_entry.get("filename")
    return normalize_runtime_file_entry({
        "name": f"sold_{source_file_name or 'data_package'}",
        "file_category": "market",
        "directory": "/market/sold",
        "preview_mode": "table",
        "resource_types": list(file_entry.get("resource_types", [])),
        "operation_id": file_entry.get("source_operation_id") or file_entry.get("operation_id") or file_entry.get("id"),
        "source_operation_id": file_entry.get("source_operation_id") or file_entry.get("operation_id") or "",
        "status": "sold",
        "sellable": False,
        "market_status": "sold",
        "created_at": sold_at,
        "metadata": {
            "sold_file_id": file_entry.get("id"),
            "sold_file_name": source_file_name,
            "seller_username": username,
            "market_category": market_category,
            "buyer_type": ghost_exchange_buyer_type(market_category),
            "price": price,
            "currency": "HC",
            "sold_at": sold_at,
            "source_directory": file_entry.get("directory"),
            "source_file_category": file_entry.get("file_category"),
            "target": file_entry.get("target_snapshot") or (file_entry.get("metadata") or {}).get("target", {}),
        },
        "sale": {
            "file_id": file_entry.get("id"),
            "file_name": source_file_name,
            "market_category": market_category,
            "buyer_type": ghost_exchange_buyer_type(market_category),
            "price": price,
            "currency": "HC",
            "sold_at": sold_at,
        },
    }, "market")


def sell_ghost_exchange_file(profile, username, file_id):
    files = ensure_files_inventory(profile)
    for folder in GHOST_EXCHANGE_FILE_CATEGORIES:
        folder_files = files.get(folder, [])
        for index, file_entry in enumerate(folder_files):
            if not isinstance(file_entry, dict):
                continue
            if str(file_entry.get("id") or "") != str(file_id or ""):
                continue
            if not is_ghost_exchange_sellable(file_entry):
                return None

            final_price = ghost_exchange_price_preview(file_entry)
            sold_at = runtime_file_now()
            sale_record = build_ghost_exchange_sale_record(username, file_entry, final_price, sold_at)
            del folder_files[index]
            files.setdefault("market", []).append(sale_record)
            profile.setdefault("market_history", []).append({
                "id": sale_record.get("id"),
                "file_id": file_entry.get("id"),
                "file_name": file_entry.get("name") or file_entry.get("filename"),
                "market_category": sale_record["metadata"]["market_category"],
                "buyer_type": sale_record["metadata"]["buyer_type"],
                "price": final_price,
                "currency": "HC",
                "sold_at": sold_at,
                "status": "sold",
                "source_file_category": file_entry.get("file_category"),
                "source_directory": file_entry.get("directory"),
            })
            normalize_files_inventory(profile)
            return {
                "file": file_entry,
                "sale_record": sale_record,
                "price": final_price,
                "market_category": sale_record["metadata"]["market_category"],
                "buyer_type": sale_record["metadata"]["buyer_type"],
                "sold_at": sold_at,
            }
    return None


def gps_file_exists(files, operation_id):
    return any(
        isinstance(item, dict)
        and (item.get("operation_id") == operation_id or item.get("source_operation_id") == operation_id)
        for item in files.get("gps", [])
    )


def data_file_exists(files, folder, operation_id):
    return any(
        isinstance(item, dict)
        and (item.get("operation_id") == operation_id or item.get("source_operation_id") == operation_id)
        for item in files.get(folder, [])
    )


def operation_file_references(operation):
    resource_buffer = operation.get("resource_buffer") if isinstance(operation.get("resource_buffer"), dict) else {}
    names = {
        str(item.get("name") or "")
        for item in resource_buffer.get("files", [])
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    }
    names.update(
        str(item.get("file_name") or "")
        for item in operation.get("fragments", [])
        if isinstance(item, dict) and str(item.get("file_name") or "").strip()
    )
    return {name for name in names if name}


def apply_operation_quality_to_files(profile, operation):
    operation_id = str(operation.get("operation_id") or "")
    if not operation_id:
        return False
    source_quality = operation.get("source_app_quality") if isinstance(operation.get("source_app_quality"), dict) else {}
    resource_buffer = operation.get("resource_buffer") if isinstance(operation.get("resource_buffer"), dict) else {}
    quality_score = clamp_percent(
        source_quality.get("quality_score") or resource_buffer.get("quality_score"),
        default=DEFAULT_APP_QUALITY_SCORE,
    )
    reliability = clamp_percent(
        source_quality.get("reliability") or resource_buffer.get("reliability"),
        default=DEFAULT_APP_RELIABILITY,
    )
    creator_power = clamp_percent(
        source_quality.get("creator_power"),
        default=DEFAULT_CREATOR_POWER,
    )
    files = ensure_files_inventory(profile)
    changed = False
    for folder in DATA_FILE_FOLDERS:
        if folder == "market":
            continue
        for index, item in enumerate(files.get(folder, [])):
            if not isinstance(item, dict):
                continue
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            item_operation_id = str(item.get("source_operation_id") or item.get("operation_id") or metadata.get("operation_id") or "")
            if item_operation_id != operation_id:
                continue
            metadata = dict(metadata)
            previous_quality = clamp_percent(item.get("quality_score") or metadata.get("quality_score"), default=0)
            blended_quality = max(previous_quality, quality_score)
            if item.get("quality_score") != blended_quality:
                item["quality_score"] = blended_quality
                changed = True
            for key, value in {
                "source_app_quality_score": quality_score,
                "source_app_reliability": reliability,
                "source_app_creator_power": creator_power,
            }.items():
                if metadata.get(key) != value:
                    metadata[key] = value
                    changed = True
            metadata["quality_score"] = blended_quality
            item["metadata"] = metadata
            files[folder][index] = item
    return changed


def operation_artifact_exists(profile, files, folders, operation_id, file_name=None, fragment_index=None):
    operation_id = str(operation_id or "")
    file_name = str(file_name or "")

    def entry_matches(entry):
        if not isinstance(entry, dict):
            return False
        metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
        entry_operation_id = str(
            entry.get("source_operation_id")
            or entry.get("operation_id")
            or metadata.get("operation_id")
            or ""
        )
        entry_name = str(entry.get("name") or entry.get("filename") or metadata.get("sold_file_name") or "")
        sold_file_name = str(metadata.get("sold_file_name") or entry.get("file_name") or "")
        if file_name and file_name not in {entry_name, sold_file_name}:
            return False
        if fragment_index is not None:
            try:
                if int(entry.get("fragment_index") or metadata.get("fragment_index") or -1) != int(fragment_index):
                    return False
            except (TypeError, ValueError):
                return False
        if operation_id and entry_operation_id == operation_id:
            return True
        if operation_id and (operation_id in entry_name or operation_id in sold_file_name):
            return True
        return bool(file_name and file_name in {entry_name, sold_file_name})

    for folder in folders:
        if any(entry_matches(item) for item in files.get(folder, [])):
            return True
    if any(entry_matches(item) for item in files.get("market", [])):
        return True
    if any(entry_matches(item) for item in profile.get("market_history", []) or []):
        return True
    return False


def build_vehicle_tracking_gps_file(operation):
    target = operation.get("target") or {}
    target_label = display_target_label(target, "VEHICLE")
    operation_id = operation.get("operation_id") or "operation"
    started = operation.get("started_at")
    ended = operation.get("ended_at") or operation.get("expires_at")
    checkpoints = list(operation.get("checkpoints") or [])
    completeness_percent = clamp_int(35 + min(45, len(checkpoints) * 6) + 16, default=60)
    quality_score = clamp_int(55 + min(25, len(checkpoints) * 3), default=60)
    slug = operation_filename_slug(target_label)
    filename = f"gps_{slug}_{operation_id}.log"
    return {
        "name": filename,
        "file_category": "gps",
        "directory": "/data/gps",
        "preview_mode": "table",
        "resource_types": ["gps_logs", "location_history"],
        "operation_id": operation_id,
        "source_operation_type": operation.get("operation_type"),
        "status": "stored",
        "sellable": False,
        "market_status": "not_listed",
        "metadata": {
            "operation_id": operation_id,
            "target": target,
            "target_id": operation.get("target_id"),
            "checkpoint_count": len(checkpoints),
            "started_at": started,
            "ended_at": ended,
            "accuracy": "medium",
            "quality": "medium",
            "quality_score": quality_score,
            "completeness_percent": completeness_percent,
            "completeness_tier": completeness_tier_for_percent(completeness_percent),
            "missing_fields": [],
            "completeness": {
                "percent": completeness_percent,
                "tier": completeness_tier_for_percent(completeness_percent),
                "missing": [],
                "quality_score": quality_score,
            },
        },
        "checkpoints": checkpoints,
    }


def finalize_vehicle_tracking_file(profile, operation):
    if operation.get("operation_type") != "vehicle_tracking":
        return False
    if operation.get("status") not in {"completed", "timeout"}:
        return False

    resource_buffer = operation.setdefault("resource_buffer", {})
    files = ensure_files_inventory(profile)
    operation_id = operation.get("operation_id")
    if resource_buffer.get("gps_file_created") and operation_artifact_exists(profile, files, ["gps"], operation_id):
        return False
    if resource_buffer.get("gps_file_created"):
        resource_buffer["gps_file_created"] = False

    if gps_file_exists(files, operation_id):
        resource_buffer["gps_file_created"] = True
        return False

    storage_result = append_runtime_file_if_space(profile, operation, "gps", build_vehicle_tracking_gps_file(operation))
    if not storage_result["stored"]:
        return storage_result["changed"]
    gps_file = storage_result["file"]
    resource_buffer["gps_file_created"] = True
    resource_buffer.setdefault("files", []).append({
        "name": gps_file["name"],
        "directory": gps_file["directory"],
        "file_category": gps_file["file_category"],
    })
    return True


DEVICE_INTELLIGENCE_RESOURCE_TYPES = [
    "location_history",
    "device_logs",
    "personal_records",
    "financial_records",
    "call_history",
    "messenger_data",
]

DEVICE_TRACKING_BASIC_RESOURCES = ["location_history", "device_logs"]


def device_tracking_resource_types(operation):
    resource_buffer = operation.get("resource_buffer") or {}
    declared = [
        str(item).strip()
        for item in resource_buffer.get("resource_types", [])
        if str(item).strip() in DEVICE_INTELLIGENCE_RESOURCE_TYPES
    ]
    if not declared:
        declared = list(DEVICE_TRACKING_BASIC_RESOURCES)
    return list(dict.fromkeys(declared))


def device_package_completeness(resource_types):
    total = len(DEVICE_INTELLIGENCE_RESOURCE_TYPES)
    count = len([item for item in resource_types if item in DEVICE_INTELLIGENCE_RESOURCE_TYPES])
    percent = int(round((count / total) * 100)) if total else 0
    if count <= 2:
        tier = "basic"
    elif count <= 4:
        tier = "enhanced"
    else:
        tier = "rich"
    return {
        "resource_count": count,
        "max_resource_count": total,
        "percent": percent,
        "tier": tier,
        "missing": [item for item in DEVICE_INTELLIGENCE_RESOURCE_TYPES if item not in resource_types],
    }


def build_device_intelligence_file(operation):
    target = operation.get("target") or {}
    target_label = display_target_label(target, "DEVICE")
    operation_id = operation.get("operation_id") or "operation"
    resources = device_tracking_resource_types(operation)
    completeness = device_package_completeness(resources)
    quality_score = clamp_int(45 + completeness["resource_count"] * 8, default=55)
    folder = "personal" if any(item in resources for item in ["personal_records", "financial_records", "call_history", "messenger_data"]) else "device"
    directory = "/data/personal" if folder == "personal" else "/data/device"
    filename = f"device_{operation_filename_slug(target_label)}_{operation_id}.pkg"
    return folder, {
        "name": filename,
        "file_category": folder,
        "directory": directory,
        "preview_mode": "card",
        "resource_types": resources,
        "operation_id": operation_id,
        "source_operation_type": operation.get("operation_type"),
        "status": "stored",
        "sellable": False,
        "market_status": "not_listed",
        "metadata": {
            "operation_id": operation_id,
            "target": target,
            "target_id": operation.get("target_id"),
            "started_at": operation.get("started_at"),
            "ended_at": operation.get("ended_at") or operation.get("expires_at"),
            "completeness": completeness,
            "quality": "medium" if completeness["resource_count"] <= 4 else "high",
            "quality_score": quality_score,
            "completeness_percent": completeness["percent"],
            "completeness_tier": completeness["tier"],
            "missing_fields": completeness.get("missing", []),
        },
        "summary": {
            "label": "Device Intelligence",
            "tier": completeness["tier"],
            "completeness_percent": completeness["percent"],
            "quality_score": quality_score,
            "missing_fields": completeness.get("missing", []),
            "included": resources,
        },
    }


def finalize_device_tracking_file(profile, operation):
    if operation.get("operation_type") != "device_tracking":
        return False
    if operation.get("status") not in {"completed", "timeout"}:
        return False

    resource_buffer = operation.setdefault("resource_buffer", {})
    files = ensure_files_inventory(profile)
    folder, device_file = build_device_intelligence_file(operation)
    operation_id = operation.get("operation_id")
    if resource_buffer.get("device_file_created") and operation_artifact_exists(profile, files, [folder], operation_id):
        return False
    if resource_buffer.get("device_file_created"):
        resource_buffer["device_file_created"] = False

    if data_file_exists(files, folder, operation_id):
        resource_buffer["device_file_created"] = True
        return False

    storage_result = append_runtime_file_if_space(profile, operation, folder, device_file)
    if not storage_result["stored"]:
        return storage_result["changed"]
    device_file = storage_result["file"]
    resource_buffer["device_file_created"] = True
    resource_buffer.setdefault("files", []).append({
        "name": device_file["name"],
        "directory": device_file["directory"],
        "file_category": device_file["file_category"],
    })
    return True


def camera_stream_resource_types(operation):
    resource_buffer = operation.get("resource_buffer") or {}
    declared = [
        str(item).strip()
        for item in resource_buffer.get("resource_types", [])
        if str(item).strip() in {"camera_dump", "video_material"}
    ]
    if not declared:
        declared = ["camera_dump"]
    if "video_material" in declared and "camera_dump" not in declared:
        declared.insert(0, "camera_dump")
    return list(dict.fromkeys(declared))


def camera_file_exists(files, operation_id, fragment_index):
    return any(
        isinstance(item, dict)
        and item.get("operation_id") == operation_id
        and item.get("fragment_index") == fragment_index
        for item in files.get("camera", [])
    )


def build_camera_fragment_file(operation, fragment_index, fragment_start_ts, fragment_end_ts):
    target = operation.get("target") or {}
    target_label = display_target_label(target, "CAM")
    operation_id = operation.get("operation_id") or "operation"
    resources = camera_stream_resource_types(operation)
    primary = "video_material" if "video_material" in resources else "camera_dump"
    completeness_percent = 72 if primary == "video_material" else 56
    quality_score = 74 if primary == "video_material" else 60
    missing_fields = [] if primary == "video_material" else ["resolution", "continuity"]
    extension = "vid" if primary == "video_material" else "cam"
    filename = f"camera_{operation_filename_slug(target_label)}_{operation_id}_{fragment_index:03d}.{extension}"
    duration = max(0, int(fragment_end_ts - fragment_start_ts))
    return {
        "name": filename,
        "file_category": "camera",
        "directory": "/data/camera",
        "preview_mode": "media_placeholder",
        "resource_types": resources,
        "operation_id": operation_id,
        "fragment_index": fragment_index,
        "source_operation_type": operation.get("operation_type"),
        "status": "stored",
        "sellable": False,
        "market_status": "not_listed",
        "metadata": {
            "operation_id": operation_id,
            "target": target,
            "target_id": operation.get("target_id"),
            "fragment_index": fragment_index,
            "started_at": operation_iso_from_ts(fragment_start_ts),
            "ended_at": operation_iso_from_ts(fragment_end_ts),
            "duration_seconds": duration,
            "quality": "high" if primary == "video_material" else "medium",
            "quality_score": quality_score,
            "frame_quality": "high" if primary == "video_material" else "medium",
            "resource_primary": primary,
            "completeness_percent": completeness_percent,
            "completeness_tier": completeness_tier_for_percent(completeness_percent),
            "missing_fields": missing_fields,
            "completeness": {
                "percent": completeness_percent,
                "tier": completeness_tier_for_percent(completeness_percent),
                "missing": missing_fields,
                "quality_score": quality_score,
            },
        },
        "summary": {
            "label": "Camera Stream Fragment",
            "duration_seconds": duration,
            "resource_primary": primary,
            "has_video_material": "video_material" in resources,
            "completeness_percent": completeness_percent,
            "quality_score": quality_score,
            "missing_fields": missing_fields,
        },
    }


def ensure_camera_stream_fragments(profile, operation, now_ts):
    if operation.get("operation_type") != "camera_stream":
        return False
    if operation.get("status") not in (OPERATION_ACTIVE_STATUSES | OPERATION_FINALIZABLE_STATUSES):
        return False

    started_ts = parse_operation_timestamp(operation.get("started_at"))
    expires_ts = parse_operation_timestamp(operation.get("expires_at"))
    if started_ts is None or expires_ts is None or expires_ts <= started_ts:
        return False

    observed_ts = min(now_ts, expires_ts)
    if observed_ts <= started_ts:
        return False

    interval = CAMERA_STREAM_FRAGMENT_INTERVAL_SECONDS
    target_count = int((observed_ts - started_ts) // interval)
    if observed_ts >= expires_ts:
        duration = max(0, expires_ts - started_ts)
        target_count = int(duration // interval)
        if duration % interval:
            target_count += 1

    files = ensure_files_inventory(profile)
    fragments = operation.setdefault("fragments", [])
    existing_indexes = {
        int(item.get("fragment_index"))
        for item in fragments
        if isinstance(item, dict) and str(item.get("fragment_index", "")).isdigit()
    }
    changed = False
    for index in range(1, target_count + 1):
        fragment_start = started_ts + (index - 1) * interval
        fragment_end = min(started_ts + index * interval, expires_ts)
        if index in existing_indexes:
            fragment_name = next(
                (
                    str(item.get("file_name") or "")
                    for item in fragments
                    if isinstance(item, dict) and int(item.get("fragment_index") or -1) == index
                ),
                "",
            )
            if (
                not camera_file_exists(files, operation.get("operation_id"), index)
                and not operation_artifact_exists(
                    profile,
                    files,
                    ["camera"],
                    operation.get("operation_id"),
                    file_name=fragment_name or None,
                    fragment_index=index,
                )
            ):
                fragment_file = build_camera_fragment_file(operation, index, fragment_start, fragment_end)
                storage_result = append_runtime_file_if_space(profile, operation, "camera", fragment_file)
                if storage_result["stored"]:
                    changed = True
                elif storage_result["changed"]:
                    changed = True
            continue
        fragment_file = build_camera_fragment_file(operation, index, fragment_start, fragment_end)
        if not camera_file_exists(files, operation.get("operation_id"), index):
            storage_result = append_runtime_file_if_space(profile, operation, "camera", fragment_file)
            if not storage_result["stored"]:
                if storage_result["changed"]:
                    changed = True
                continue
            fragment_file = storage_result["file"]
        fragments.append({
            "fragment_index": index,
            "file_name": fragment_file["name"],
            "created_at": fragment_file["metadata"]["ended_at"],
            "started_at": fragment_file["metadata"]["started_at"],
            "ended_at": fragment_file["metadata"]["ended_at"],
            "resource_types": fragment_file["resource_types"],
        })
        changed = True

    if changed:
        resource_buffer = operation.setdefault("resource_buffer", {})
        resource_buffer["camera_fragments_created"] = len(operation.get("fragments", []))
        resource_buffer.setdefault("files", [])
        for fragment in operation.get("fragments", []):
            if not any(item.get("name") == fragment.get("file_name") for item in resource_buffer["files"]):
                resource_buffer["files"].append({
                    "name": fragment.get("file_name"),
                    "directory": "/data/camera",
                    "file_category": "camera",
                })
    return changed


def camera_shutdown_state_for_operation(operation, now_ts):
    remaining = operation_remaining_seconds(operation, now_ts)
    status = operation.get("status")
    if status in {"start", "running"} and remaining == 0:
        state = "recovering"
        active = False
    elif status in {"start", "running"} and (remaining is None or remaining > 0):
        state = "offline" if (remaining or 0) > 60 else "recovering"
        active = True
    elif status in {"timeout", "completed"}:
        state = "recovering"
        active = False
    else:
        state = "disturbed"
        active = status not in {"failed", "cancelled"}
    return {
        "type": "camera_shutdown",
        "camera_state": state,
        "active": active,
        "remaining_seconds": remaining,
        "valid_until": operation.get("expires_at"),
        "risk_modifier": "camera_shutdown",
        "mitigates": ["camera_detected", "camera_stream_detected"],
        "prepared_for": "risk_model_sprint_15",
    }


def ensure_camera_shutdown_state(operation, now_ts):
    if operation.get("operation_type") != "camera_shutdown":
        return False
    state = camera_shutdown_state_for_operation(operation, now_ts)
    if operation.get("support_state") == state:
        return False
    operation["support_state"] = state
    return True


ATM_LOG_RESOURCE_TYPES = ["atm_dump", "financial_records"]


def atm_log_resource_types(operation):
    resource_buffer = operation.get("resource_buffer") or {}
    declared = [
        str(item).strip()
        for item in resource_buffer.get("resource_types", [])
        if str(item).strip() in ATM_LOG_RESOURCE_TYPES
    ]
    if not declared:
        declared = ["atm_dump"]
    if "financial_records" in declared and "atm_dump" not in declared:
        declared.insert(0, "atm_dump")
    return list(dict.fromkeys(declared))


def atm_record_rows(operation, row_type="atm"):
    operation_id = operation.get("operation_id") or "operation"
    seed = stable_procedural_seed(operation_id, row_type, operation.get("target_id"))
    rng = random_module.Random(seed)
    started_ts = parse_operation_timestamp(operation.get("started_at"))
    if started_ts is None:
        started_ts = datetime.now(timezone.utc).timestamp()
    count = 5 if row_type == "atm" else 8
    rows = []
    for index in range(1, count + 1):
        created_at = operation_iso_from_ts(started_ts + index * 73)
        amount = rng.randint(20, 950)
        suffix = str(rng.randint(1000, 9999))
        rows.append({
            "index": index,
            "timestamp": created_at,
            "account": f"acct_****{suffix}",
            "event": "withdrawal" if index % 2 else "balance_check",
            "amount_hint": f"{amount} HC",
            "confidence": "medium" if row_type == "atm" else "high",
        })
    return rows


def build_atm_dump_file(operation):
    target = operation.get("target") or {}
    target_label = display_target_label(target, "ATM")
    operation_id = operation.get("operation_id") or "operation"
    records = atm_record_rows(operation, "atm")
    completeness_percent = clamp_int(45 + min(35, len(records) * 4), default=65)
    quality_score = 62
    filename = f"atm_{operation_filename_slug(target_label)}_{operation_id}.dump"
    return {
        "name": filename,
        "file_category": "atm",
        "directory": "/data/atm",
        "preview_mode": "table",
        "resource_types": ["atm_dump"],
        "operation_id": operation_id,
        "source_operation_type": operation.get("operation_type"),
        "status": "stored",
        "sellable": False,
        "market_status": "not_listed",
        "metadata": {
            "operation_id": operation_id,
            "target": target,
            "target_id": operation.get("target_id"),
            "record_count": len(records),
            "started_at": operation.get("started_at"),
            "ended_at": operation.get("ended_at") or operation.get("expires_at"),
            "quality": "medium",
            "quality_score": quality_score,
            "completeness_percent": completeness_percent,
            "completeness_tier": completeness_tier_for_percent(completeness_percent),
            "missing_fields": ["time_span", "terminal_identity"],
            "completeness": {
                "percent": completeness_percent,
                "tier": completeness_tier_for_percent(completeness_percent),
                "missing": ["time_span", "terminal_identity"],
                "quality_score": quality_score,
            },
            "risk_hint": "high-value/high-risk",
        },
        "records": records,
    }


def build_financial_records_file(operation):
    target = operation.get("target") or {}
    target_label = display_target_label(target, "ATM")
    operation_id = operation.get("operation_id") or "operation"
    records = atm_record_rows(operation, "financial")
    completeness_percent = clamp_int(58 + min(34, len(records) * 4), default=80)
    quality_score = 78
    filename = f"finance_{operation_filename_slug(target_label)}_{operation_id}.dat"
    return {
        "name": filename,
        "file_category": "financial",
        "directory": "/data/financial",
        "preview_mode": "table",
        "resource_types": ["financial_records"],
        "operation_id": operation_id,
        "source_operation_type": operation.get("operation_type"),
        "status": "stored",
        "sellable": False,
        "market_status": "not_listed",
        "metadata": {
            "operation_id": operation_id,
            "target": target,
            "target_id": operation.get("target_id"),
            "record_count": len(records),
            "started_at": operation.get("started_at"),
            "ended_at": operation.get("ended_at") or operation.get("expires_at"),
            "quality": "high",
            "quality_score": quality_score,
            "completeness_percent": completeness_percent,
            "completeness_tier": completeness_tier_for_percent(completeness_percent),
            "missing_fields": ["amount_visibility"],
            "completeness": {
                "percent": completeness_percent,
                "tier": completeness_tier_for_percent(completeness_percent),
                "missing": ["amount_visibility"],
                "quality_score": quality_score,
            },
            "account_confidence": "medium",
            "risk_hint": "high-value/high-risk",
        },
        "records": records,
    }


def finalize_atm_log_extraction_files(profile, operation):
    if operation.get("operation_type") != "atm_log_extraction":
        return False
    if operation.get("status") not in {"completed", "timeout"}:
        return False

    resource_buffer = operation.setdefault("resource_buffer", {})
    files = ensure_files_inventory(profile)
    operation_id = operation.get("operation_id")
    resources = atm_log_resource_types(operation)
    expected_folders = []
    if "atm_dump" in resources:
        expected_folders.append("atm")
    if "financial_records" in resources:
        expected_folders.append("financial")
    if resource_buffer.get("atm_files_created") and all(
        operation_artifact_exists(profile, files, [folder], operation_id)
        for folder in expected_folders
    ):
        return False
    if resource_buffer.get("atm_files_created"):
        resource_buffer["atm_files_created"] = False

    created_files = []
    changed = False

    if "atm_dump" in resources and not data_file_exists(files, "atm", operation_id):
        storage_result = append_runtime_file_if_space(profile, operation, "atm", build_atm_dump_file(operation))
        if storage_result["stored"]:
            created_files.append(storage_result["file"])
            changed = True
        elif storage_result["changed"]:
            changed = True

    if "financial_records" in resources and not data_file_exists(files, "financial", operation_id):
        storage_result = append_runtime_file_if_space(profile, operation, "financial", build_financial_records_file(operation))
        if storage_result["stored"]:
            created_files.append(storage_result["file"])
            changed = True
        elif storage_result["changed"]:
            changed = True

    if not created_files:
        return changed

    risk_state = operation.setdefault("risk_state", initial_risk_state_for_operation("atm_log_extraction"))
    risk_state.setdefault("events", [])
    if "atm_alarm" not in risk_state["events"]:
        risk_state["events"].append("atm_alarm")
    risk_state["level"] = "high"
    risk_state["hint"] = "high-value/high-risk financial terminal operation"
    risk_state["consequences_enabled"] = False

    resource_buffer["atm_files_created"] = True
    resource_buffer.setdefault("files", [])
    for file_entry in created_files:
        resource_buffer["files"].append({
            "name": file_entry["name"],
            "directory": file_entry["directory"],
            "file_category": file_entry["file_category"],
        })
    return True


PERSISTENT_SNIFFER_RESOURCE_TYPES = [
    "financial_records",
    "credentials",
    "internal_recon_state",
    "device_logs",
]


def persistent_sniffer_resource_types(operation):
    resource_buffer = operation.get("resource_buffer") or {}
    declared = [
        str(item).strip()
        for item in resource_buffer.get("resource_types", [])
        if str(item).strip() in PERSISTENT_SNIFFER_RESOURCE_TYPES
    ]
    if not declared:
        declared = ["credentials"]
    return list(dict.fromkeys(declared))


def operation_duration_from_timestamps(operation):
    started_ts = parse_operation_timestamp(operation.get("started_at"))
    ended_ts = parse_operation_timestamp(operation.get("ended_at") or operation.get("expires_at"))
    if started_ts is None or ended_ts is None:
        return int(operation.get("duration_seconds") or 0)
    return max(0, int(ended_ts - started_ts))


def build_sniffer_financial_file(operation):
    target = operation.get("target") or {}
    target_label = display_target_label(target, "IMPLANT")
    operation_id = operation.get("operation_id") or "operation"
    records = atm_record_rows(operation, "financial")
    completeness_percent = clamp_int(55 + min(35, len(records) * 4), default=78)
    quality_score = 75
    filename = f"sniff_finance_{operation_filename_slug(target_label)}_{operation_id}.dat"
    return {
        "name": filename,
        "file_category": "financial",
        "directory": "/data/financial",
        "preview_mode": "table",
        "resource_types": ["financial_records"],
        "operation_id": operation_id,
        "source_operation_type": operation.get("operation_type"),
        "status": "stored",
        "sellable": False,
        "market_status": "not_listed",
        "metadata": {
            "operation_id": operation_id,
            "target": target,
            "target_id": operation.get("target_id"),
            "installed_at": operation.get("started_at"),
            "ended_at": operation.get("ended_at") or operation.get("expires_at"),
            "duration_seconds": operation_duration_from_timestamps(operation),
            "collected_count": len(records),
            "risk_hint": "long_operation/sniffer_detected/high_value",
            "quality": "high",
            "quality_score": quality_score,
            "completeness_percent": completeness_percent,
            "completeness_tier": completeness_tier_for_percent(completeness_percent),
            "missing_fields": ["account_confidence"],
            "completeness": {
                "percent": completeness_percent,
                "tier": completeness_tier_for_percent(completeness_percent),
                "missing": ["account_confidence"],
                "quality_score": quality_score,
            },
        },
        "records": records,
    }


def build_sniffer_credentials_file(operation):
    target = operation.get("target") or {}
    target_label = display_target_label(target, "IMPLANT")
    operation_id = operation.get("operation_id") or "operation"
    seed = stable_procedural_seed(operation_id, "credentials", operation.get("target_id"))
    credential_count = 2 + (seed % 4)
    completeness_percent = clamp_int(48 + min(35, credential_count * 7), default=68)
    quality_score = clamp_int(62 + credential_count * 4, default=70)
    filename = f"credentials_{operation_filename_slug(target_label)}_{operation_id}.enc"
    return {
        "name": filename,
        "file_category": "credentials",
        "directory": "/data/credentials",
        "preview_mode": "encrypted_blob",
        "resource_types": ["credentials"],
        "operation_id": operation_id,
        "source_operation_type": operation.get("operation_type"),
        "status": "stored",
        "sellable": False,
        "market_status": "not_listed",
        "metadata": {
            "operation_id": operation_id,
            "target": target,
            "target_id": operation.get("target_id"),
            "installed_at": operation.get("started_at"),
            "ended_at": operation.get("ended_at") or operation.get("expires_at"),
            "duration_seconds": operation_duration_from_timestamps(operation),
            "collected_count": credential_count,
            "risk_hint": "long_operation/sniffer_detected/high_value",
            "encryption": "sealed",
            "scope": "access tokens",
            "quality": "sealed",
            "quality_score": quality_score,
            "completeness_percent": completeness_percent,
            "completeness_tier": completeness_tier_for_percent(completeness_percent),
            "missing_fields": ["validity", "freshness"],
            "completeness": {
                "percent": completeness_percent,
                "tier": completeness_tier_for_percent(completeness_percent),
                "missing": ["validity", "freshness"],
                "quality_score": quality_score,
            },
        },
        "summary": {
            "label": "Encrypted Credentials",
            "credential_count": credential_count,
            "plain_text_visible": False,
            "completeness_percent": completeness_percent,
            "quality_score": quality_score,
            "missing_fields": ["validity", "freshness"],
        },
    }


def build_sniffer_device_file(operation):
    target = operation.get("target") or {}
    target_label = display_target_label(target, "IMPLANT")
    operation_id = operation.get("operation_id") or "operation"
    completeness_percent = 17
    quality_score = 48
    filename = f"device_logs_{operation_filename_slug(target_label)}_{operation_id}.log"
    return {
        "name": filename,
        "file_category": "device",
        "directory": "/data/device",
        "preview_mode": "card",
        "resource_types": ["device_logs"],
        "operation_id": operation_id,
        "source_operation_type": operation.get("operation_type"),
        "status": "stored",
        "sellable": False,
        "market_status": "not_listed",
        "metadata": {
            "operation_id": operation_id,
            "target": target,
            "target_id": operation.get("target_id"),
            "installed_at": operation.get("started_at"),
            "ended_at": operation.get("ended_at") or operation.get("expires_at"),
            "duration_seconds": operation_duration_from_timestamps(operation),
            "collected_count": 6,
            "quality": "low",
            "quality_score": quality_score,
            "risk_hint": "long_operation/sniffer_detected",
            "completeness_percent": completeness_percent,
            "completeness_tier": "fragment",
            "missing_fields": [item for item in DEVICE_INTELLIGENCE_RESOURCE_TYPES if item != "device_logs"],
            "completeness": {
                "resource_count": 1,
                "max_resource_count": len(DEVICE_INTELLIGENCE_RESOURCE_TYPES),
                "percent": completeness_percent,
                "tier": "fragment",
                "missing": [item for item in DEVICE_INTELLIGENCE_RESOURCE_TYPES if item != "device_logs"],
                "quality_score": quality_score,
            },
        },
        "summary": {
            "label": "Sniffer Device Logs",
            "tier": "fragment",
            "completeness_percent": completeness_percent,
            "quality_score": quality_score,
            "missing_fields": [item for item in DEVICE_INTELLIGENCE_RESOURCE_TYPES if item != "device_logs"],
            "included": ["device_logs"],
        },
    }


def build_sniffer_system_state_file(operation):
    target = operation.get("target") or {}
    target_label = display_target_label(target, "IMPLANT")
    operation_id = operation.get("operation_id") or "operation"
    filename = f"recon_state_{operation_filename_slug(target_label)}_{operation_id}.state"
    return {
        "name": filename,
        "file_category": "system",
        "directory": "/system",
        "preview_mode": "operation_state",
        "resource_types": ["internal_recon_state"],
        "operation_id": operation_id,
        "source_operation_type": operation.get("operation_type"),
        "status": "stored",
        "sellable": False,
        "market_status": "not_listed",
        "metadata": {
            "operation_id": operation_id,
            "target": target,
            "target_id": operation.get("target_id"),
            "installed_at": operation.get("started_at"),
            "ended_at": operation.get("ended_at") or operation.get("expires_at"),
            "duration_seconds": operation_duration_from_timestamps(operation),
            "collected_count": 1,
            "risk_hint": "long_operation/sniffer_detected",
            "state": "implant_recon_complete",
        },
    }


def finalize_persistent_sniffer_files(profile, operation):
    if operation.get("operation_type") != "persistent_sniffer":
        return False
    if operation.get("status") not in {"completed", "timeout"}:
        return False

    resource_buffer = operation.setdefault("resource_buffer", {})
    files = ensure_files_inventory(profile)
    operation_id = operation.get("operation_id")
    resources = persistent_sniffer_resource_types(operation)
    expected_folders = []
    if "financial_records" in resources:
        expected_folders.append("financial")
    if "credentials" in resources:
        expected_folders.append("credentials")
    if "device_logs" in resources:
        expected_folders.append("device")
    if "internal_recon_state" in resources:
        expected_folders.append("system")
    if resource_buffer.get("sniffer_files_created") and all(
        operation_artifact_exists(profile, files, [folder], operation_id)
        for folder in expected_folders
    ):
        return False
    if resource_buffer.get("sniffer_files_created"):
        resource_buffer["sniffer_files_created"] = False

    created_files = []
    changed = False

    if "financial_records" in resources and not data_file_exists(files, "financial", operation_id):
        storage_result = append_runtime_file_if_space(profile, operation, "financial", build_sniffer_financial_file(operation))
        if storage_result["stored"]:
            created_files.append(storage_result["file"])
            changed = True
        elif storage_result["changed"]:
            changed = True

    if "credentials" in resources and not data_file_exists(files, "credentials", operation_id):
        storage_result = append_runtime_file_if_space(profile, operation, "credentials", build_sniffer_credentials_file(operation))
        if storage_result["stored"]:
            created_files.append(storage_result["file"])
            changed = True
        elif storage_result["changed"]:
            changed = True

    if "device_logs" in resources and not data_file_exists(files, "device", operation_id):
        storage_result = append_runtime_file_if_space(profile, operation, "device", build_sniffer_device_file(operation))
        if storage_result["stored"]:
            created_files.append(storage_result["file"])
            changed = True
        elif storage_result["changed"]:
            changed = True

    if "internal_recon_state" in resources and not data_file_exists(files, "system", operation_id):
        storage_result = append_runtime_file_if_space(profile, operation, "system", build_sniffer_system_state_file(operation))
        if storage_result["stored"]:
            created_files.append(storage_result["file"])
            changed = True
        elif storage_result["changed"]:
            changed = True

    if not created_files:
        return changed

    risk_state = operation.setdefault("risk_state", initial_risk_state_for_operation("persistent_sniffer"))
    risk_state.setdefault("events", [])
    for event in ["long_operation_detected", "sniffer_detected"]:
        if event not in risk_state["events"]:
            risk_state["events"].append(event)
    if any(item in resources for item in ["financial_records", "credentials"]):
        risk_state["level"] = "high"
        if "high_value" not in risk_state["events"]:
            risk_state["events"].append("high_value")
    else:
        risk_state["level"] = "medium"
    risk_state["hint"] = "long_operation/sniffer_detected/high_value"
    risk_state["consequences_enabled"] = False

    resource_buffer["sniffer_files_created"] = True
    resource_buffer.setdefault("files", [])
    for file_entry in created_files:
        resource_buffer["files"].append({
            "name": file_entry["name"],
            "directory": file_entry["directory"],
            "file_category": file_entry["file_category"],
        })
    return True


WIFI_SCANNER_RESOURCE_TYPES = ["wifi_networks", "hotspot_database"]
AUDIO_INTERFERENCE_RESOURCE_TYPES = ["audio_transcript"]
VEHICLE_ECU_RESOURCE_TYPES = ["vehicle_diagnostics"]
GENERIC_TRACE_RESOURCE_TYPES = ["location_history", "internal_recon_state"]


def operation_declared_resources(operation, allowed, fallback):
    resource_buffer = operation.get("resource_buffer") or {}
    declared = [
        str(item).strip()
        for item in resource_buffer.get("resource_types", [])
        if str(item).strip() in allowed
    ]
    if not declared:
        declared = list(fallback)
    return list(dict.fromkeys(declared))


def wifi_scanner_resource_types(operation):
    return operation_declared_resources(operation, WIFI_SCANNER_RESOURCE_TYPES, ["wifi_networks"])


def audio_interference_resource_types(operation):
    return operation_declared_resources(operation, AUDIO_INTERFERENCE_RESOURCE_TYPES, ["audio_transcript"])


def vehicle_ecu_resource_types(operation):
    return operation_declared_resources(operation, VEHICLE_ECU_RESOURCE_TYPES, ["vehicle_diagnostics"])


def generic_trace_resource_types(operation):
    return operation_declared_resources(operation, GENERIC_TRACE_RESOURCE_TYPES, ["location_history"])


def build_wifi_scanner_file(operation):
    target = operation.get("target") or {}
    target_label = display_target_label(target, "NET")
    operation_id = operation.get("operation_id") or "operation"
    resources = wifi_scanner_resource_types(operation)
    seed = stable_procedural_seed(operation_id, "wifi_scanner", operation.get("target_id"))
    rng = random_module.Random(seed)
    network_count = 4 + rng.randint(0, 5)
    records = []
    for index in range(1, network_count + 1):
        records.append({
            "index": index,
            "ssid": f"AP_{rng.randint(1000, 9999)}",
            "security": choice(["WPA2", "WPA3", "WPA2-Enterprise"]),
            "signal": f"-{rng.randint(38, 84)} dBm",
            "channel": rng.choice([1, 6, 11, 36, 44, 149]),
        })
    if "hotspot_database" in resources:
        hotspot_count = network_count + rng.randint(3, 8)
    else:
        hotspot_count = network_count
    completeness_percent = clamp_int(46 + network_count * 5 + (16 if "hotspot_database" in resources else 0), default=62)
    quality_score = clamp_int(54 + network_count * 3 + (12 if "hotspot_database" in resources else 0), default=64)
    filename = f"wifi_{operation_filename_slug(target_label)}_{operation_id}.net"
    return {
        "name": filename,
        "file_category": "network",
        "directory": "/data/network",
        "preview_mode": "table",
        "resource_types": resources,
        "operation_id": operation_id,
        "source_operation_type": operation.get("operation_type"),
        "status": "stored",
        "sellable": False,
        "market_status": "not_listed",
        "metadata": {
            "operation_id": operation_id,
            "target": target,
            "target_id": operation.get("target_id"),
            "started_at": operation.get("started_at"),
            "ended_at": operation.get("ended_at") or operation.get("expires_at"),
            "record_count": len(records),
            "network_count": network_count,
            "hotspot_count": hotspot_count,
            "quality": "high" if "hotspot_database" in resources else "medium",
            "quality_score": quality_score,
            "completeness_percent": completeness_percent,
            "completeness_tier": completeness_tier_for_percent(completeness_percent),
            "missing_fields": [] if "hotspot_database" in resources else ["coverage_area", "freshness"],
        },
        "records": records,
        "summary": {
            "label": "Wi-Fi Recon",
            "record_count": len(records),
            "hotspot_count": hotspot_count,
            "completeness_percent": completeness_percent,
            "quality_score": quality_score,
        },
    }


def build_audio_interference_file(operation):
    target = operation.get("target") or {}
    target_label = display_target_label(target, "AUDIO")
    operation_id = operation.get("operation_id") or "operation"
    duration = operation_duration_from_timestamps(operation)
    line_count = max(3, min(12, duration // 180 or 3))
    lines = [
        {"timestamp": operation.get("started_at"), "speaker": "unknown", "text": "fragment zakloconego strumienia audio"}
        for _ in range(line_count)
    ]
    completeness_percent = clamp_int(42 + min(35, line_count * 5), default=60)
    quality_score = clamp_int(48 + min(30, line_count * 4), default=58)
    filename = f"audio_{operation_filename_slug(target_label)}_{operation_id}.txt"
    return {
        "name": filename,
        "file_category": "audio",
        "directory": "/data/audio",
        "preview_mode": "transcript",
        "resource_types": audio_interference_resource_types(operation),
        "operation_id": operation_id,
        "source_operation_type": operation.get("operation_type"),
        "status": "stored",
        "sellable": False,
        "market_status": "not_listed",
        "metadata": {
            "operation_id": operation_id,
            "target": target,
            "target_id": operation.get("target_id"),
            "started_at": operation.get("started_at"),
            "ended_at": operation.get("ended_at") or operation.get("expires_at"),
            "duration_seconds": duration,
            "speaker_count": 1,
            "transcript_quality": "partial",
            "quality_score": quality_score,
            "completeness_percent": completeness_percent,
            "completeness_tier": completeness_tier_for_percent(completeness_percent),
            "missing_fields": ["speaker_count", "keyword_hits"],
        },
        "transcript": lines,
        "summary": {
            "label": "Audio Transcript",
            "line_count": line_count,
            "completeness_percent": completeness_percent,
            "quality_score": quality_score,
        },
    }


def build_vehicle_ecu_file(operation):
    target = operation.get("target") or {}
    target_label = display_target_label(target, "ECU")
    operation_id = operation.get("operation_id") or "operation"
    seed = stable_procedural_seed(operation_id, "vehicle_ecu", operation.get("target_id"))
    rng = random_module.Random(seed)
    systems = ["ECU", "ABS", "BMS", "GPS", "infotainment"]
    records = [
        {
            "system": system,
            "status": rng.choice(["nominal", "warning", "locked", "diagnostic"]),
            "confidence": rng.choice(["medium", "high"]),
        }
        for system in systems[: 3 + rng.randint(0, 2)]
    ]
    completeness_percent = clamp_int(50 + len(records) * 7, default=72)
    quality_score = clamp_int(58 + len(records) * 5, default=74)
    filename = f"vehicle_{operation_filename_slug(target_label)}_{operation_id}.diag"
    return {
        "name": filename,
        "file_category": "vehicle",
        "directory": "/data/vehicle",
        "preview_mode": "table",
        "resource_types": vehicle_ecu_resource_types(operation),
        "operation_id": operation_id,
        "source_operation_type": operation.get("operation_type"),
        "status": "stored",
        "sellable": False,
        "market_status": "not_listed",
        "metadata": {
            "operation_id": operation_id,
            "target": target,
            "target_id": operation.get("target_id"),
            "started_at": operation.get("started_at"),
            "ended_at": operation.get("ended_at") or operation.get("expires_at"),
            "systems_count": len(records),
            "quality": "medium",
            "quality_score": quality_score,
            "completeness_percent": completeness_percent,
            "completeness_tier": completeness_tier_for_percent(completeness_percent),
            "missing_fields": ["fault_depth", "telemetry_quality"],
        },
        "records": records,
        "summary": {
            "label": "Vehicle Diagnostics",
            "systems_count": len(records),
            "completeness_percent": completeness_percent,
            "quality_score": quality_score,
        },
    }


def build_generic_trace_location_file(operation):
    target = operation.get("target") or {}
    target_label = display_target_label(target, "TARGET")
    operation_id = operation.get("operation_id") or "operation"
    started_ts = parse_operation_timestamp(operation.get("started_at")) or datetime.now(timezone.utc).timestamp()
    expires_ts = parse_operation_timestamp(operation.get("ended_at") or operation.get("expires_at")) or started_ts
    duration = max(0, int(expires_ts - started_ts))
    checkpoint_count = max(2, min(8, duration // 600 or 2))
    checkpoints = []
    for index in range(1, checkpoint_count + 1):
        checkpoint_ts = started_ts + (duration * index / checkpoint_count if checkpoint_count else 0)
        position = compute_operation_position(operation, checkpoint_ts) or operation_base_position(operation)
        if isinstance(position, tuple):
            position = {"lat": round(position[0], 7), "lng": round(position[1], 7)}
        checkpoints.append({
            "index": index,
            "created_at": operation_iso_from_ts(checkpoint_ts),
            "lat": (position or {}).get("lat"),
            "lng": (position or {}).get("lng"),
            "event_type": "generic_trace_checkpoint",
        })
    completeness_percent = clamp_int(38 + checkpoint_count * 7, default=58)
    quality_score = clamp_int(50 + checkpoint_count * 4, default=62)
    filename = f"trace_{operation_filename_slug(target_label)}_{operation_id}.log"
    return {
        "name": filename,
        "file_category": "gps",
        "directory": "/data/gps",
        "preview_mode": "table",
        "resource_types": ["location_history"],
        "operation_id": operation_id,
        "source_operation_type": operation.get("operation_type"),
        "status": "stored",
        "sellable": False,
        "market_status": "not_listed",
        "metadata": {
            "operation_id": operation_id,
            "target": target,
            "target_id": operation.get("target_id"),
            "started_at": operation.get("started_at"),
            "ended_at": operation.get("ended_at") or operation.get("expires_at"),
            "checkpoint_count": len(checkpoints),
            "quality": "medium",
            "quality_score": quality_score,
            "completeness_percent": completeness_percent,
            "completeness_tier": completeness_tier_for_percent(completeness_percent),
            "missing_fields": ["target_identity_confidence"],
        },
        "checkpoints": checkpoints,
        "summary": {
            "label": "Generic Trace",
            "checkpoint_count": len(checkpoints),
            "completeness_percent": completeness_percent,
            "quality_score": quality_score,
        },
    }


def append_operation_file_reference(operation, file_entry):
    resource_buffer = operation.setdefault("resource_buffer", {})
    resource_buffer.setdefault("files", [])
    if any(item.get("name") == file_entry.get("name") for item in resource_buffer["files"]):
        return
    resource_buffer["files"].append({
        "name": file_entry["name"],
        "directory": file_entry["directory"],
        "file_category": file_entry["file_category"],
    })


def finalize_camera_stream_file(profile, operation):
    if operation.get("operation_type") != "camera_stream":
        return False
    if operation.get("status") not in {"completed", "timeout"}:
        return False

    files = ensure_files_inventory(profile)
    operation_id = operation.get("operation_id")
    fragments = operation.setdefault("fragments", [])
    if data_file_exists(files, "camera", operation_id) or operation_artifact_exists(profile, files, ["camera"], operation_id):
        return False
    if fragments:
        operation["fragments"] = []
        resource_buffer = operation.setdefault("resource_buffer", {})
        resource_buffer["camera_fragments_created"] = 0
        resource_buffer["files"] = [
            item for item in resource_buffer.get("files", [])
            if not (isinstance(item, dict) and item.get("file_category") == "camera")
        ]
    if data_file_exists(files, "camera", operation_id):
        return False

    started_ts = parse_operation_timestamp(operation.get("started_at"))
    ended_ts = parse_operation_timestamp(operation.get("ended_at") or operation.get("expires_at"))
    if started_ts is None:
        started_ts = datetime.now(timezone.utc).timestamp()
    if ended_ts is None or ended_ts <= started_ts:
        ended_ts = started_ts + min(60, int(operation.get("duration_seconds") or 60))
    storage_result = append_runtime_file_if_space(
        profile,
        operation,
        "camera",
        build_camera_fragment_file(operation, 1, started_ts, ended_ts),
    )
    if not storage_result["stored"]:
        return storage_result["changed"]
    fragment_file = storage_result["file"]
    fragments.append({
        "fragment_index": 1,
        "file_name": fragment_file["name"],
        "created_at": fragment_file["metadata"]["ended_at"],
        "started_at": fragment_file["metadata"]["started_at"],
        "ended_at": fragment_file["metadata"]["ended_at"],
        "resource_types": fragment_file["resource_types"],
    })
    resource_buffer = operation.setdefault("resource_buffer", {})
    resource_buffer["camera_fragments_created"] = 1
    append_operation_file_reference(operation, fragment_file)
    return True


def finalize_wifi_scanner_files(profile, operation):
    if operation.get("operation_type") != "wifi_scanner":
        return False
    if operation.get("status") not in {"completed", "timeout"}:
        return False
    resource_buffer = operation.setdefault("resource_buffer", {})
    files = ensure_files_inventory(profile)
    operation_id = operation.get("operation_id")
    if resource_buffer.get("network_files_created") and operation_artifact_exists(profile, files, ["network"], operation_id):
        return False
    if resource_buffer.get("network_files_created"):
        resource_buffer["network_files_created"] = False

    if data_file_exists(files, "network", operation_id):
        resource_buffer["network_files_created"] = True
        return False
    storage_result = append_runtime_file_if_space(profile, operation, "network", build_wifi_scanner_file(operation))
    if not storage_result["stored"]:
        return storage_result["changed"]
    network_file = storage_result["file"]
    resource_buffer["network_files_created"] = True
    append_operation_file_reference(operation, network_file)
    return True


def finalize_audio_interference_files(profile, operation):
    if operation.get("operation_type") != "audio_interference":
        return False
    if operation.get("status") not in {"completed", "timeout"}:
        return False
    resource_buffer = operation.setdefault("resource_buffer", {})
    files = ensure_files_inventory(profile)
    operation_id = operation.get("operation_id")
    if resource_buffer.get("audio_files_created") and operation_artifact_exists(profile, files, ["audio"], operation_id):
        return False
    if resource_buffer.get("audio_files_created"):
        resource_buffer["audio_files_created"] = False

    if data_file_exists(files, "audio", operation_id):
        resource_buffer["audio_files_created"] = True
        return False
    storage_result = append_runtime_file_if_space(profile, operation, "audio", build_audio_interference_file(operation))
    if not storage_result["stored"]:
        return storage_result["changed"]
    audio_file = storage_result["file"]
    resource_buffer["audio_files_created"] = True
    append_operation_file_reference(operation, audio_file)
    return True


def finalize_vehicle_ecu_files(profile, operation):
    if operation.get("operation_type") != "vehicle_ecu":
        return False
    if operation.get("status") not in {"completed", "timeout"}:
        return False
    resource_buffer = operation.setdefault("resource_buffer", {})
    files = ensure_files_inventory(profile)
    operation_id = operation.get("operation_id")
    if resource_buffer.get("vehicle_files_created") and operation_artifact_exists(profile, files, ["vehicle"], operation_id):
        return False
    if resource_buffer.get("vehicle_files_created"):
        resource_buffer["vehicle_files_created"] = False

    if data_file_exists(files, "vehicle", operation_id):
        resource_buffer["vehicle_files_created"] = True
        return False
    storage_result = append_runtime_file_if_space(profile, operation, "vehicle", build_vehicle_ecu_file(operation))
    if not storage_result["stored"]:
        return storage_result["changed"]
    vehicle_file = storage_result["file"]
    resource_buffer["vehicle_files_created"] = True
    append_operation_file_reference(operation, vehicle_file)
    return True


def finalize_generic_trace_file(profile, operation):
    if operation.get("operation_type") != "generic_trace":
        return False
    if operation.get("status") not in {"completed", "timeout"}:
        return False
    resource_buffer = operation.setdefault("resource_buffer", {})
    files = ensure_files_inventory(profile)
    operation_id = operation.get("operation_id")
    changed = False
    resources = generic_trace_resource_types(operation)
    expected_folders = []
    if "location_history" in resources:
        expected_folders.append("gps")
    if "internal_recon_state" in resources:
        expected_folders.append("system")
    if resource_buffer.get("trace_files_created") and all(
        operation_artifact_exists(profile, files, [folder], operation_id)
        for folder in expected_folders
    ):
        return False
    if resource_buffer.get("trace_files_created"):
        resource_buffer["trace_files_created"] = False

    if "location_history" in resources and not data_file_exists(files, "gps", operation_id):
        storage_result = append_runtime_file_if_space(profile, operation, "gps", build_generic_trace_location_file(operation))
        if storage_result["stored"]:
            append_operation_file_reference(operation, storage_result["file"])
            changed = True
        elif storage_result["changed"]:
            changed = True
    if "internal_recon_state" in resources and not data_file_exists(files, "system", operation_id):
        storage_result = append_runtime_file_if_space(profile, operation, "system", build_sniffer_system_state_file(operation))
        if storage_result["stored"]:
            append_operation_file_reference(operation, storage_result["file"])
            changed = True
        elif storage_result["changed"]:
            changed = True
    if any(data_file_exists(files, folder, operation_id) for folder in expected_folders):
        resource_buffer["trace_files_created"] = True
    return changed


def mark_operation_cleanup_state(operation, now_iso=None):
    if not isinstance(operation, dict):
        return False
    if operation.get("status") not in OPERATION_TERMINAL_STATUSES:
        return False

    cleanup = operation.setdefault("cleanup_state", {})
    changed = False
    now_iso = now_iso or runtime_file_now()

    updates = {
        "active_object_active": False,
        "marker_visible": False,
        "support_active": False,
        "cleaned_at": cleanup.get("cleaned_at") or now_iso,
    }
    if operation.get("operation_type") == "persistent_sniffer":
        updates["implant_state"] = "ended"
    if operation.get("operation_type") == "camera_shutdown":
        support_state = operation.setdefault("support_state", {})
        if support_state.get("active") is not False:
            support_state["active"] = False
            changed = True
        if support_state.get("risk_modifier_active") is not False:
            support_state["risk_modifier_active"] = False
            changed = True

    for key, value in updates.items():
        if cleanup.get(key) != value:
            cleanup[key] = value
            changed = True
    return changed


def refresh_operation_runtime(operation, now_ts=None):
    now_ts = now_ts if now_ts is not None else datetime.now(timezone.utc).timestamp()
    refreshed = dict(operation or {})
    movement_model = refreshed.get("movement_model") or movement_model_for_operation(
        refreshed.get("operation_type"),
        refreshed.get("target_type"),
    )
    refreshed["movement_model"] = movement_model
    refreshed["duration_seconds"] = int(
        refreshed.get("duration_seconds") or operation_duration_seconds(refreshed.get("operation_type"))
    )
    if not refreshed.get("procedural_seed"):
        refreshed["procedural_seed"] = stable_procedural_seed(
            refreshed.get("operation_id"),
            refreshed.get("owner_username"),
            refreshed.get("target_id"),
            refreshed.get("operation_type"),
        )

    remaining = operation_remaining_seconds(refreshed, now_ts)
    refreshed["remaining_seconds"] = remaining
    refreshed["expired"] = remaining == 0 if remaining is not None else False

    if refreshed.get("status") in OPERATION_ACTIVE_STATUSES and refreshed["expired"]:
        refreshed["status"] = "timeout"

    current_position = compute_operation_position(refreshed, now_ts)
    if current_position:
        refreshed["current_position"] = current_position
    update_operation_risk_meter(refreshed, now_ts=now_ts)
    return refreshed


def refresh_operations_runtime(profile, persist_timeouts=False, now_ts=None, username=None):
    now_ts = now_ts if now_ts is not None else datetime.now(timezone.utc).timestamp()
    operations = profile.get("operations") or []
    refreshed_operations = []
    changed = False

    for index, operation in enumerate(operations):
        if ensure_vehicle_tracking_checkpoints(operation, now_ts):
            changed = True
        if ensure_camera_stream_fragments(profile, operation, now_ts):
            changed = True
        if ensure_camera_shutdown_state(operation, now_ts):
            changed = True
        refreshed = refresh_operation_runtime(operation, now_ts=now_ts)
        if operation.get("operation_risk_meter") != refreshed.get("operation_risk_meter"):
            operation["operation_risk_meter"] = refreshed.get("operation_risk_meter")
            changed = True
        refreshed_operations.append(refreshed)
        if persist_timeouts and operation.get("status") != refreshed.get("status"):
            operation["status"] = refreshed.get("status")
            if refreshed.get("status") in OPERATION_TERMINAL_STATUSES:
                operation["ended_at"] = operation.get("ended_at") or operation_iso_from_ts(now_ts)
            changed = True
        if operation.get("status") in OPERATION_TERMINAL_STATUSES:
            if mark_operation_cleanup_state(operation, now_iso=operation_iso_from_ts(now_ts)):
                changed = True
        if operation.get("status") in OPERATION_FINALIZABLE_STATUSES:
            if finalize_vehicle_tracking_file(profile, operation):
                changed = True
            if finalize_device_tracking_file(profile, operation):
                changed = True
            if finalize_atm_log_extraction_files(profile, operation):
                changed = True
            if finalize_persistent_sniffer_files(profile, operation):
                changed = True
            if finalize_camera_stream_file(profile, operation):
                changed = True
            if finalize_wifi_scanner_files(profile, operation):
                changed = True
            if finalize_audio_interference_files(profile, operation):
                changed = True
            if finalize_vehicle_ecu_files(profile, operation):
                changed = True
            if finalize_generic_trace_file(profile, operation):
                changed = True
            if apply_operation_quality_to_files(profile, operation):
                changed = True
        if operation.get("status") in OPERATION_RISK_ASSESSABLE_STATUSES:
            if assess_operation_risk(profile, operation):
                changed = True

    try:
        incident_result = incident_initializer.sync_operations(operations, now=operation_iso_from_ts(now_ts))
        incident_actions = incident_result.get("actions") or []
        if incident_actions:
            publish_incident_actions(username or profile.get("username"), incident_actions)
        warning_actions = sync_response_warnings(
            username or profile.get("username"),
            profile,
            operations,
            now_iso=operation_iso_from_ts(now_ts),
        )
        if incident_actions or warning_actions:
            meters_by_operation_id = {
                str(operation.get("operation_id") or ""): operation.get("operation_risk_meter")
                for operation in operations
                if isinstance(operation, dict)
            }
            for refreshed in refreshed_operations:
                operation_id = str(refreshed.get("operation_id") or "")
                if operation_id in meters_by_operation_id:
                    refreshed["operation_risk_meter"] = meters_by_operation_id[operation_id]
            changed = True
    except Exception as exc:
        print(f"[INCIDENT] initializer skipped: {exc}")

    if changed:
        normalize_files_inventory(profile)
        normalize_profile_storage(profile)

    return refreshed_operations, changed


def refresh_and_persist_operations(username, profile):
    if not username or not isinstance(profile, dict):
        return profile

    previous_storage = storage_delta_snapshot(profile)
    operations, changed = refresh_operations_runtime(profile, persist_timeouts=True, username=username)
    try:
        player_operation_store.upsert_operations(
            username,
            profile.get("operations", []),
            event_type="operation.runtime_sync",
            source="refresh_and_persist_operations",
        )
    except Exception as exc:
        print(f"[OPERATIONS] store sync skipped: {exc}")
    if not changed:
        return profile

    UserProfileManager(username).update_profile({
        "operations": profile.get("operations", []),
        "files": profile.get("files", {}),
        "risk_events": profile.get("risk_events", []),
        "system_messages": profile.get("system_messages", []),
        "market_history": profile.get("market_history", []),
        "storage_capacity": profile.get("storage_capacity"),
        "storage_used": profile.get("storage_used"),
        "storage_unit": profile.get("storage_unit", "MB"),
        "storage_soft_limit": True,
        "storage_over_limit": profile.get("storage_over_limit", False),
    })
    record_storage_delta(
        username,
        profile,
        reason="operation_runtime",
        previous=previous_storage,
        dedupe_key_prefix=f"storage:{username}:operation_runtime:{runtime_file_now()}",
    )
    fresh_profile = user_store.get_profile(username) or profile
    fresh_profile = dict(fresh_profile)
    fresh_profile.pop("password", None)
    fresh_profile.pop("salt", None)
    fresh_profile["apps"] = normalize_app_contracts(fresh_profile.get("apps", []))
    normalize_files_inventory(fresh_profile)
    session["profile"] = fresh_profile
    return fresh_profile


def load_profile_readonly(username, strip_sensitive=True, normalize_apps=True, normalize_files=False):
    if not username:
        return None

    profile = user_store.get_profile(username)
    if not profile:
        return None

    profile = dict(profile)
    if strip_sensitive:
        profile.pop("password", None)
        profile.pop("salt", None)
    if normalize_apps:
        profile["apps"] = normalize_app_contracts(profile.get("apps", []))
    if normalize_files:
        normalize_files_inventory(profile)
    normalize_runtime_profile_defaults(profile)
    apply_runtime_stores_to_profile(username, profile)
    return profile


def active_operations_from_operations(operations):
    return [
        operation for operation in (operations or [])
        if operation_is_active(operation)
    ]


def operation_history_from_operations(operations):
    return [
        operation for operation in (operations or [])
        if operation.get("status") in OPERATION_TERMINAL_STATUSES
    ]


def operation_output_size_mb(operation):
    resource_buffer = operation.get("resource_buffer") if isinstance(operation.get("resource_buffer"), dict) else {}
    total = 0
    for item in resource_buffer.get("files", []) or []:
        if not isinstance(item, dict):
            continue
        total += clamp_storage_number(
            item.get("file_size") or (item.get("metadata") or {}).get("file_size"),
            default=0,
            minimum=0,
        )
    return total


def summarize_operation_for_client(operation):
    target = operation.get("target") if isinstance(operation.get("target"), dict) else {}
    current_position = operation.get("current_position")
    if not isinstance(current_position, dict):
        current_position = {}
    risk_state = operation.get("risk_state") if isinstance(operation.get("risk_state"), dict) else {}
    risk_meter = operation.get("operation_risk_meter") if isinstance(operation.get("operation_risk_meter"), dict) else {}

    return {
        "operation_id": operation.get("operation_id"),
        "operation_type": operation.get("operation_type"),
        "owner_username": operation.get("owner_username"),
        "source_app_id": operation.get("source_app_id"),
        "map_action_id": operation.get("map_action_id"),
        "target_id": operation.get("target_id"),
        "target": {
            "label": target.get("label") or target.get("name") or target.get("target_id"),
            "name": target.get("name") or target.get("label"),
            "lat": target.get("lat"),
            "lng": target.get("lng", target.get("lon")),
            "target_type": target.get("target_type"),
            "target_mode": target.get("target_mode"),
        },
        "target_type": operation.get("target_type"),
        "target_mode": operation.get("target_mode"),
        "status": operation.get("status"),
        "started_at": operation.get("started_at"),
        "expires_at": operation.get("expires_at"),
        "ended_at": operation.get("ended_at"),
        "remaining_seconds": operation.get("remaining_seconds"),
        "expired": operation.get("expired"),
        "output_mb": operation_output_size_mb(operation),
        "current_position": {
            "lat": current_position.get("lat"),
            "lng": current_position.get("lng", current_position.get("lon")),
        } if current_position else {},
        "risk_state": {
            "level": risk_state.get("level") or risk_state.get("risk_level"),
            "risk_level": risk_state.get("risk_level") or risk_state.get("level"),
            "score": risk_state.get("score"),
            "hint": risk_state.get("hint"),
            "modifiers": risk_state.get("modifiers", []),
        },
        "operation_risk_meter": {
            "mode": risk_meter.get("mode"),
            "risk_version": risk_meter.get("risk_version"),
            "current_heat": risk_meter.get("current_heat"),
            "active_contribution": risk_meter.get("active_contribution"),
            "risk_level": risk_meter.get("risk_level"),
            "warning_threshold": risk_meter.get("warning_threshold"),
            "incident_threshold": risk_meter.get("incident_threshold"),
            "warning_crossed": risk_meter.get("warning_crossed"),
            "incident_crossed": risk_meter.get("incident_crossed"),
            "cancelled": risk_meter.get("cancelled"),
        } if risk_meter else {},
        "risk_level": operation.get("risk_level"),
    }


OPERATION_CONTROL_APP_ID = "operationControl"

OPERATION_CONTROL_TYPE_FAMILIES = {
    "vehicle_tracking": "gps",
    "generic_trace": "recon",
    "device_tracking": "device",
    "camera_stream": "camera",
    "camera_shutdown": "camera",
    "atm_log_extraction": "atm",
    "persistent_sniffer": "implant",
    "wifi_scanner": "network",
    "microphone_sniffer": "audio",
    "audio_interference": "audio",
    "vehicle_ecu": "vehicle",
    "implant_timer": "implant",
}

OPERATION_CONTROL_RESOURCE_FAMILIES = {
    "gps_logs": "gps",
    "location_history": "gps",
    "gps": "gps",
    "device_logs": "device",
    "device": "device",
    "camera_dump": "camera",
    "video_material": "camera",
    "camera": "camera",
    "audio_transcript": "audio",
    "audio": "audio",
    "wifi_networks": "network",
    "hotspot_database": "network",
    "network": "network",
    "atm_dump": "atm",
    "atm": "atm",
    "vehicle_diagnostics": "vehicle",
    "vehicle": "vehicle",
    "internal_recon_state": "recon",
    "system": "recon",
    "credentials": "network",
    "financial_records": "atm",
}

OPERATION_CONTROL_OUTPUT_DEFAULTS = {
    "vehicle_tracking": "gps",
    "generic_trace": "system",
    "device_tracking": "device",
    "camera_stream": "camera",
    "camera_shutdown": "camera",
    "atm_log_extraction": "atm",
    "persistent_sniffer": "credentials",
    "wifi_scanner": "network",
    "microphone_sniffer": "audio",
    "audio_interference": "audio",
    "vehicle_ecu": "vehicle",
    "implant_timer": "system",
}


def operation_control_app_installed(profile):
    return app_is_installed(profile or {}, OPERATION_CONTROL_APP_ID)


def operation_control_load_profile(username, strip_sensitive=True):
    return load_profile_readonly(
        username,
        strip_sensitive=strip_sensitive,
        normalize_apps=True,
        normalize_files=False,
    )


def operation_control_forbidden_response():
    return jsonify({
        "success": False,
        "error": "operation_control_not_installed",
        "message": "Operation Control nie jest zainstalowany.",
    }), 403


def operation_control_unique(values):
    seen = set()
    result = []
    for value in values or []:
        value = str(value or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def operation_control_resource_types(operation):
    resources = []
    direct = operation.get("resource_types")
    if isinstance(direct, list):
        resources.extend(direct)
    elif direct:
        resources.append(direct)

    resource_buffer = operation.get("resource_buffer") if isinstance(operation.get("resource_buffer"), dict) else {}
    buffered = resource_buffer.get("resource_types")
    if isinstance(buffered, list):
        resources.extend(buffered)
    elif buffered:
        resources.append(buffered)

    for item in resource_buffer.get("files", []) or []:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        for key in ("resource_type", "category", "file_category"):
            if item.get(key):
                resources.append(item.get(key))
            if metadata.get(key):
                resources.append(metadata.get(key))
        for key in ("resource_types", "resources"):
            value = item.get(key)
            if isinstance(value, list):
                resources.extend(value)
            value = metadata.get(key)
            if isinstance(value, list):
                resources.extend(value)

    return operation_control_unique(resources)


def operation_control_family(operation):
    operation_type = str(operation.get("operation_type") or "").strip()
    if operation_type in OPERATION_CONTROL_TYPE_FAMILIES:
        return OPERATION_CONTROL_TYPE_FAMILIES[operation_type]

    map_action_id = str(operation.get("map_action_id") or "").strip()
    if map_action_id in OPERATION_CONTROL_TYPE_FAMILIES:
        return OPERATION_CONTROL_TYPE_FAMILIES[map_action_id]

    for resource in operation_control_resource_types(operation):
        family = OPERATION_CONTROL_RESOURCE_FAMILIES.get(resource)
        if family:
            return family
    return "other"


def operation_control_position(operation):
    current_position = operation.get("current_position")
    if not isinstance(current_position, dict):
        current_position = {}
    try:
        return {
            "lat": round(float(current_position.get("lat")), 7),
            "lng": round(float(current_position.get("lng", current_position.get("lon"))), 7),
        }
    except (TypeError, ValueError):
        return None


def operation_control_distance_from_bike(position, origin):
    if not isinstance(position, dict) or not isinstance(origin, dict):
        return None, False
    try:
        distance = Haversine.haversine_distance(
            float(origin.get("lat")),
            float(origin.get("lng", origin.get("lon"))),
            float(position.get("lat")),
            float(position.get("lng", position.get("lon"))),
        )
    except (TypeError, ValueError):
        return None, False
    return int(round(distance)), True


def operation_control_output_summary(operation):
    operation_type = str(operation.get("operation_type") or "").strip()
    resource_buffer = operation.get("resource_buffer") if isinstance(operation.get("resource_buffer"), dict) else {}
    files = [item for item in (resource_buffer.get("files", []) or []) if isinstance(item, dict)]
    first_file = files[0] if files else {}
    first_metadata = first_file.get("metadata") if isinstance(first_file.get("metadata"), dict) else {}

    file_category = (
        first_file.get("file_category")
        or first_file.get("category")
        or first_file.get("folder")
        or first_metadata.get("file_category")
        or first_metadata.get("category")
        or OPERATION_CONTROL_OUTPUT_DEFAULTS.get(operation_type)
        or "system"
    )
    defaults = FILE_CATEGORY_DEFAULTS.get(str(file_category), FILE_CATEGORY_DEFAULTS["system"])
    directory = (
        first_file.get("directory")
        or first_file.get("path")
        or first_metadata.get("directory")
        or first_metadata.get("path")
        or defaults.get("directory")
    )
    preview_mode = (
        first_file.get("preview_mode")
        or first_metadata.get("preview_mode")
        or defaults.get("preview_mode")
    )
    resource_types = operation_control_resource_types(operation) or defaults.get("resource_types", [])
    expected_size_mb = operation_output_size_mb(operation)
    if not expected_size_mb:
        expected_size_mb = clamp_storage_number(
            operation.get("expected_size_mb")
            or resource_buffer.get("expected_size_mb")
            or first_file.get("file_size")
            or first_metadata.get("file_size"),
            default=0,
            minimum=0,
        )

    if resource_buffer.get("cancelled") or operation.get("status") == "cancelled":
        output_status = "cancelled"
    elif files:
        output_status = "created"
    elif operation.get("status") in OPERATION_ACTIVE_STATUSES:
        output_status = "pending"
    else:
        output_status = "empty"

    return {
        "file_category": str(file_category),
        "resource_types": operation_control_unique(resource_types),
        "directory": directory,
        "preview_mode": preview_mode,
        "expected_size_mb": expected_size_mb,
        "output_status": output_status,
        "file_count": len(files),
    }


def operation_control_incident_summary(operation):
    risk_meter = operation.get("operation_risk_meter") if isinstance(operation.get("operation_risk_meter"), dict) else {}
    incident_id = risk_meter.get("incident_id")
    incident = None
    if incident_id:
        try:
            incident = incident_store.get(incident_id)
        except Exception:
            incident = None
    incident = incident if isinstance(incident, dict) else {}
    status = incident.get("status") or risk_meter.get("incident_status")
    active = bool(incident_id and str(status or "active") not in {"resolved", "cancelled", "expired"})
    response_units = (
        incident.get("response_units")
        or incident.get("public_response_units")
        or risk_meter.get("response_units")
        or []
    )
    return {
        "active": active,
        "incident_id": incident_id,
        "level": incident.get("level") or incident.get("severity") or risk_meter.get("incident_level"),
        "status": status,
        "warning": bool(risk_meter.get("warning_crossed") or risk_meter.get("warning_id")),
        "arrival_at": risk_meter.get("warning_arrival_at") or incident.get("arrival_at"),
        "response_units": response_units,
    }


def operation_control_risk_summary(operation):
    summary = summarize_operation_for_client(operation)
    risk_meter = summary.get("operation_risk_meter") or {}
    risk_state = summary.get("risk_state") or {}
    return {
        "level": risk_state.get("level") or risk_meter.get("risk_level") or operation.get("risk_level"),
        "score": risk_state.get("score"),
        "current_heat": risk_meter.get("current_heat"),
        "active_contribution": risk_meter.get("active_contribution"),
        "warning_threshold": risk_meter.get("warning_threshold"),
        "incident_threshold": risk_meter.get("incident_threshold"),
        "warning_crossed": risk_meter.get("warning_crossed"),
        "incident_crossed": risk_meter.get("incident_crossed"),
    }


def summarize_operation_control_item(operation, profile=None):
    base = summarize_operation_for_client(operation)
    profile = profile if isinstance(profile, dict) else {}
    target = base.get("target") if isinstance(base.get("target"), dict) else {}
    position = operation_control_position(operation)
    origin = victim_picker_position(profile)
    distance, distance_available = operation_control_distance_from_bike(position, origin)
    can_cancel = operation.get("status") in OPERATION_ACTIVE_STATUSES
    disabled_reason = None
    if not can_cancel:
        disabled_reason = "already_terminal" if operation.get("status") in OPERATION_TERMINAL_STATUSES else "not_active"

    return {
        **base,
        "operation_family": operation_control_family(operation),
        "target_id": base.get("target_id") or target.get("target_id"),
        "target_label": target.get("label") or target.get("name") or base.get("target_id"),
        "position": position,
        "distance_from_bike": distance,
        "distance_available": distance_available,
        "risk": operation_control_risk_summary(operation),
        "incident": operation_control_incident_summary(operation),
        "output": operation_control_output_summary(operation),
        "can_cancel": can_cancel,
        "disabled_reason": disabled_reason,
    }


def build_operation_control_snapshot(username, profile, operations=None):
    profile = profile if isinstance(profile, dict) else {}
    if operations is None:
        operations, _ = refresh_operations_runtime(profile, persist_timeouts=False, username=username)
    active_operations = active_operations_from_operations(operations)
    operation_history = operation_history_from_operations(operations)
    active_items = [summarize_operation_control_item(operation, profile=profile) for operation in active_operations]
    history_items = [summarize_operation_control_item(operation, profile=profile) for operation in operation_history[-25:]]

    groups_by_family = {}
    for item in active_items:
        family = item.get("operation_family") or "other"
        group = groups_by_family.setdefault(family, {
            "operation_family": family,
            "count": 0,
            "operation_ids": [],
            "output_types": set(),
            "incident_count": 0,
        })
        group["count"] += 1
        group["operation_ids"].append(item.get("operation_id"))
        output = item.get("output") if isinstance(item.get("output"), dict) else {}
        if output.get("file_category"):
            group["output_types"].add(output.get("file_category"))
        incident = item.get("incident") if isinstance(item.get("incident"), dict) else {}
        if incident.get("active"):
            group["incident_count"] += 1

    groups = []
    for group in groups_by_family.values():
        groups.append({
            **group,
            "output_types": sorted(group["output_types"]),
        })
    groups.sort(key=lambda item: (-item.get("count", 0), item.get("operation_family", "")))

    return {
        "success": True,
        "ok": True,
        "scope": "operation_control",
        "position": victim_picker_position(profile),
        "active_count": len(active_items),
        "history_count": len(operation_history),
        "incident_count": sum(1 for item in active_items if (item.get("incident") or {}).get("active")),
        "groups": groups,
        "operations": active_items,
        "active_operations": active_items,
        "operation_history": history_items,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def persist_operation_control_profile(username, profile):
    UserProfileManager(username).update_profile({
        "operations": profile.get("operations", []),
        "files": profile.get("files", {}),
        "risk_events": profile.get("risk_events", []),
        "system_messages": profile.get("system_messages", []),
    })


def cancel_profile_operation(profile, operation_id, cancelled_by="player", now_ts=None):
    if not operation_id:
        return None, "missing_operation_id"
    now_ts = now_ts if now_ts is not None else datetime.now(timezone.utc).timestamp()
    operations = profile.setdefault("operations", [])
    for operation in operations:
        if not isinstance(operation, dict):
            continue
        if str(operation.get("operation_id") or "") != str(operation_id):
            continue
        if operation.get("status") in OPERATION_TERMINAL_STATUSES:
            return operation, "already_terminal"
        if operation.get("status") not in OPERATION_ACTIVE_STATUSES:
            return operation, "not_active"

        now_iso = operation_iso_from_ts(now_ts)
        operation["status"] = "cancelled"
        operation["ended_at"] = now_iso
        operation["cancelled_at"] = now_iso
        operation["cancelled_by"] = cancelled_by
        operation["remaining_seconds"] = 0
        operation["expired"] = True
        resource_buffer = operation.setdefault("resource_buffer", {})
        resource_buffer["cancelled"] = True
        resource_buffer.setdefault("files", [])
        mark_operation_cleanup_state(operation, now_iso=now_iso)
        update_operation_risk_meter(operation, now_ts=now_ts)
        assess_operation_risk(profile, operation)
        normalize_files_inventory(profile)
        return operation, "cancelled"
    return None, "not_found"


def active_operations_from_profile(profile):
    username = (profile or {}).get("username")
    operations, _ = refresh_operations_runtime(profile, username=username)
    return active_operations_from_operations(operations)


def save_owned_hacked_security(username, lat, lng, security):
    profile = user_store.get_profile(username) or {}
    target, hacked_list, added_from_store = find_owned_hacked_target(profile, username, lat, lng)
    if not target:
        return None, False

    target["security"] = dict(security or {})
    mgr = UserProfileManager(username)
    if added_from_store:
        mgr.update_profile({
            "hacked": hacked_list,
            "captured_targets_source": "sqlite",
        })

    updated = mgr.update_hacked_target_by_coords(lat, lng, {"security": dict(security or {})})
    if not updated:
        return None, False

    refreshed_target = find_captured_target_for_owner(username, lat, lng) or target
    refreshed_target["security"] = dict(security or {})
    territory_store.save_captured_target(username, refreshed_target)
    mgr.update_profile({"captured_targets_source": "sqlite"})
    return refreshed_target, True


def find_foreign_area_for_point(username, lat, lng):
    for area in territory_store.list_player_areas():
        if area.get("owner_username") == username:
            continue
        if area.get("status") != "active":
            continue
        if point_in_polygon(float(lat), float(lng), area.get("vertices", [])):
            owner_profile = user_store.get_profile(area.get("owner_username"))
            return {
                **area,
                "owner_nick": (owner_profile or {}).get("nick") or area.get("owner_username")
            }
    return None


def find_area_for_point(lat, lng):
    for area in territory_store.list_player_areas():
        if area.get("status") != "active":
            continue
        if point_in_polygon(float(lat), float(lng), area.get("vertices", [])):
            owner_profile = user_store.get_profile(area.get("owner_username"))
            return {
                **area,
                "owner_nick": (owner_profile or {}).get("nick") or area.get("owner_username"),
                "owner_clan": get_profile_clan(owner_profile or {})
            }
    return None


def find_contested_targets_for_player(username, areas=None):
    areas = areas or territory_store.list_player_areas()
    my_areas = [
        area for area in areas
        if area.get("owner_username") == username and area.get("status") == "active"
    ]
    foreign_areas = [
        area for area in areas
        if area.get("owner_username") != username and area.get("status") == "active"
    ]
    if not my_areas or not foreign_areas:
        return []

    owned_positions = {
        target_position_key(target)
        for target in territory_store.list_captured_targets(username, stationary=True)
        if target_position_key(target)
    }
    recently_lost_positions = {
        target_position_key(item.get("target") or {})
        for conflict in territory_conflict_store.list_active_for_player(username)
        for item in (conflict.get("targets") or [])
        if (item.get("captured") or item.get("status") == "captured")
        and item.get("previous_owner") == username
        and target_position_key(item.get("target") or {})
    }
    contested = {}
    for my_area in my_areas:
        for foreign_area in foreign_areas:
            if not polygons_intersect(my_area.get("vertices", []), foreign_area.get("vertices", [])):
                continue

            owner_username = foreign_area.get("owner_username")
            owner_profile = user_store.get_profile(owner_username) or {}
            for target in territory_store.list_captured_targets(owner_username, stationary=True):
                key = target_coord_key(target)
                if not key or key in contested:
                    continue
                if target_position_key(target) in owned_positions:
                    continue
                if target_position_key(target) in recently_lost_positions:
                    continue
                if target.get("previous_owner_username") == username:
                    continue
                try:
                    lat = float(target.get("lat"))
                    lng = float(target.get("lng", target.get("lon")))
                except (TypeError, ValueError):
                    continue

                if not point_in_polygon(lat, lng, my_area.get("vertices", [])):
                    continue

                contested_target = dict(target)
                contested_target.update({
                    "lat": lat,
                    "lng": lng,
                    "lon": lng,
                    "owner_username": owner_username,
                    "owner_nick": owner_profile.get("nick") or owner_username,
                    "owner_clan": get_profile_clan(owner_profile),
                    "foreign_area_id": foreign_area.get("id"),
                    "my_area_id": my_area.get("id"),
                    "target_mode": "territory_contest",
                    "contest_owner_username": owner_username,
                })
                contested[key] = contested_target

    return list(contested.values())


def contested_targets_from_active_conflicts(username, conflicts=None, areas=None):
    username = str(username or "").strip()
    if not username:
        return []
    conflicts = conflicts if conflicts is not None else territory_conflict_store.list_active_for_player(username)
    if areas is None:
        areas = safe_player_areas(territory_store.list_player_areas())
    contested = {}
    owner_profiles = {}

    def conflict_front_geometries(conflict):
        raw_geometries = conflict.get("intersections") or []
        if not raw_geometries and conflict.get("intersection"):
            raw_geometries = [conflict.get("intersection")]
        normalized = []
        for geometry in raw_geometries:
            vertices = []
            for vertex in geometry or []:
                if isinstance(vertex, dict):
                    lat = vertex.get("lat")
                    lng = vertex.get("lng", vertex.get("lon"))
                elif isinstance(vertex, (list, tuple)) and len(vertex) >= 2:
                    lat, lng = vertex[0], vertex[1]
                else:
                    continue
                try:
                    vertices.append({"lat": float(lat), "lng": float(lng)})
                except (TypeError, ValueError):
                    continue
            if len(vertices) >= 3:
                normalized.append(vertices)
        return normalized

    def add_contested_target(conflict, owner_username, target, item=None, extra=None):
        owner_username = str(owner_username or "").strip()
        if not owner_username or owner_username == username:
            return
        if item and item.get("previous_owner") == username:
            return
        if target.get("previous_owner_username") == username:
            return
        try:
            lat = float(target.get("lat", (item or {}).get("lat")))
            lng = float(target.get("lng", target.get("lon", (item or {}).get("lng", (item or {}).get("lon")))))
        except (TypeError, ValueError):
            return

        front_geometries = conflict_front_geometries(conflict)
        if front_geometries and not any(
            territory_point_in_polygon_or_boundary(
                {"lat": lat, "lng": lng}, geometry
            )
            for geometry in front_geometries
        ):
            return

        target = dict(target)
        target["lat"] = lat
        target["lng"] = lng
        target["lon"] = lng
        key = target_coord_key(target)
        if not key or key in contested:
            return

        if owner_username not in owner_profiles:
            owner_profiles[owner_username] = user_store.get_profile(owner_username) or {}
        owner_profile = owner_profiles.get(owner_username) or {}
        label = str(target.get("label") or target.get("name") or (item or {}).get("label") or "Kolizja")
        target.update({
            "label": label,
            "name": str(target.get("name") or label),
            "owner_username": owner_username,
            "owner_nick": owner_profile.get("nick") or owner_username,
            "owner_clan": get_profile_clan(owner_profile),
            "target_mode": "territory_contest",
            "contest_owner_username": owner_username,
            "conflict_id": conflict.get("conflict_id") or conflict.get("id"),
            "legacy_conflict_id": conflict.get("id"),
            "stable_conflict_id": conflict.get("conflict_id") or conflict.get("id"),
            "source_type": target.get("source_type") or "territory_contest",
        })
        if extra:
            target.update(extra)
        contested[key] = target

    for conflict in conflicts or []:
        participants = set(conflict.get("participants") or conflict.get("participant_usernames") or [])
        if username not in participants:
            continue
        for item in conflict.get("targets") or []:
            if not isinstance(item, dict):
                continue
            if item.get("captured") or item.get("status") == "captured":
                continue
            owner_username = str(item.get("owner_username") or item.get("owner") or "").strip()
            if not owner_username or owner_username == username:
                continue
            if item.get("previous_owner") == username:
                continue
            target = dict(item.get("target") or {})
            add_contested_target(conflict, owner_username, target, item=item)

        if not areas:
            continue

        conflict_area_ids = {str(item) for item in (conflict.get("area_ids") or []) if item is not None}
        if not conflict_area_ids:
            continue
        conflict_areas = [
            area for area in areas or []
            if str(area.get("id")) in conflict_area_ids and area.get("status", "active") == "active"
        ]
        my_areas = [area for area in conflict_areas if area.get("owner_username") == username]
        foreign_areas = [area for area in conflict_areas if area.get("owner_username") != username]
        if not my_areas or not foreign_areas:
            # Legacy conflicts may retain area ids from before a territory
            # rebuild. Recover the current participant areas read-only; the
            # conflict/front identity still decides whether these owners are
            # in the same active cycle.
            front_geometries = conflict_front_geometries(conflict)

            def area_touches_front(area):
                vertices = area.get("vertices") or []
                return any(
                    any(
                        territory_point_in_polygon_or_boundary(vertex, vertices)
                        for vertex in geometry
                    )
                    or any(
                        territory_point_in_polygon_or_boundary(vertex, geometry)
                        for vertex in vertices
                    )
                    for geometry in front_geometries
                )

            participant_areas = [
                area for area in areas or []
                if area.get("status", "active") == "active"
                and area.get("owner_username") in participants
                and (not front_geometries or area_touches_front(area))
            ]
            my_areas = [area for area in participant_areas if area.get("owner_username") == username]
            foreign_areas = [area for area in participant_areas if area.get("owner_username") != username]
        if not my_areas or not foreign_areas:
            continue

        for foreign_area in foreign_areas:
            owner_username = str(foreign_area.get("owner_username") or "").strip()
            if not owner_username or owner_username == username:
                continue
            members = territory_area_cluster_members(territory_store, foreign_area)
            role_by_position = {
                target_position_key(target): role
                for role, targets in (
                    ("pillar", members.get("pillars") or []),
                    ("inner", members.get("inners") or []),
                )
                for target in targets
                if target_position_key(target)
            }
            for target in members.get("objects") or []:
                key = target_coord_key(target)
                if not key or key in contested:
                    continue
                if target.get("previous_owner_username") == username:
                    continue
                try:
                    lat = float(target.get("lat"))
                    lng = float(target.get("lng", target.get("lon")))
                except (TypeError, ValueError):
                    continue
                add_contested_target(
                    conflict,
                    owner_username,
                    target,
                    extra={
                        "foreign_area_id": foreign_area.get("id"),
                        "my_area_id": my_areas[0].get("id"),
                        "node_role": role_by_position.get(target_position_key(target), "inner"),
                    },
                )
    return list(contested.values())


def find_contested_target(username, lat, lng, label=None):
    areas = safe_player_areas(territory_store.list_player_areas())
    for target in contested_targets_from_active_conflicts(username, areas=areas):
        if round(float(target.get("lat")), 5) != round(float(lat), 5):
            continue
        if round(float(target.get("lng", target.get("lon"))), 5) != round(float(lng), 5):
            continue
        if label and str(target.get("label") or target.get("name") or "") != str(label):
            continue
        return target
    return None


def find_captured_target_for_owner(username, lat, lng, label=None):
    for target in territory_store.list_captured_targets(username):
        try:
            same_coords = (
                round(float(target.get("lat")), 5) == round(float(lat), 5)
                and round(float(target.get("lng", target.get("lon"))), 5) == round(float(lng), 5)
            )
        except (TypeError, ValueError):
            continue
        if not same_coords:
            continue
        if label and str(target.get("label") or target.get("name") or "") != str(label):
            continue
        return target
    return None


def find_owned_captured_target_for_runtime_target(username, target):
    if not username or not isinstance(target, dict) or not target:
        return None
    try:
        lat = target.get("lat")
        lng = target.get("lng", target.get("lon"))
        float(lat)
        float(lng)
    except (TypeError, ValueError):
        return None

    label = target_label_value(target)
    captured = find_captured_target_for_owner(username, lat, lng, label=label) if label else None
    return captured or find_captured_target_for_owner(username, lat, lng)


def add_system_message_to_user(username, msg_type, title, text):
    if not username:
        return False
    message = {
        "type": msg_type,
        "title": title,
        "text": text,
        "body": text,
        "source": "domain_event",
        "status": "new"
    }
    _, created = system_message_store.add_message(username, message, source="domain_event")
    return bool(created)


def cyberner_notification_source(scope, peer_name, sender):
    if scope == "group":
        return "world"
    if scope == "channel":
        peer = str(peer_name or "")
        if peer == "friends":
            return "friends"
        if peer.startswith("clan:"):
            return "clan"
        return "unknown"

    normalized = str(sender or peer_name or "").strip().lower()
    if normalized in {"ai central", "ai"} or "ai central" in normalized:
        return "ai"
    if normalized == "ghost exchange" or "ghost exchange" in normalized:
        return "ghost_exchange"
    if normalized in {"system", "ghost system"} or "system" in normalized:
        return "system"
    if "misje" in normalized or "mission" in normalized:
        return "mission"
    if "marketplace" in normalized:
        return "marketplace"
    if "blacknet" in normalized:
        return "blacknet"
    return "player"


def cyberner_notification_title(source, scope, peer_name, sender):
    if source == "world":
        return "WORLD"
    if source == "friends":
        return "ZNAJOMI"
    if source == "clan":
        return "KLAN"
    if source == "ai":
        return "AI Central"
    if source == "ghost_exchange":
        return "Ghost Exchange"
    if source == "system":
        return "System"
    if source == "mission":
        return "Misje"
    if source == "marketplace":
        return "Marketplace"
    if source == "blacknet":
        return "BlackNet"
    return str(sender or peer_name or "Cyberner")


def cyberner_notification_text(source):
    if source == "world":
        return "Nowa aktywnosc."
    return "Nowa wiadomosc."


def add_cyberner_notification_to_user(username, scope, peer_name, sender):
    if not username:
        return False
    profile = user_store.get_profile(username)
    if not profile:
        return False

    source = cyberner_notification_source(scope, peer_name, sender)
    title = cyberner_notification_title(source, scope, peer_name, sender)
    messages = profile.get("system_messages", [])
    if not isinstance(messages, list):
        messages = []
    new_id = max([m.get("id", 0) for m in messages if isinstance(m, dict)], default=0) + 1
    messages.append({
        "id": new_id,
        "type": "info",
        "notification_type": "cyberner",
        "source": source,
        "scope": scope,
        "peer": "global" if scope == "group" else peer_name,
        "sender": sender,
        "title": title,
        "text": cyberner_notification_text(source),
        "status": "new",
    })
    profile["system_messages"] = messages
    user_store.save_profile(profile)
    return True


def add_cyberner_direct_notification(username, peer_name, sender, subject, body):
    mail_store.add_direct_notification(username, peer_name, sender, subject, body)
    add_cyberner_notification_to_user(username, "direct", peer_name or sender, sender)
    record_mail_thread_update(
        username,
        "direct",
        peer_name or sender,
        message=latest_mail_message(username, "direct", peer_name or sender),
        reason="cyberner_direct_notification",
    )


def notify_area_intrusion(actor_username, lat, lng):
    area = find_foreign_area_for_point(actor_username, lat, lng)
    if not area:
        return None

    owner_username = area.get("owner_username")
    if not owner_username or owner_username == actor_username:
        return None

    if territory_store.recent_area_event_exists(
        owner_username,
        actor_username,
        "intruder_enter",
        area_id=area.get("id"),
        seconds=60
    ):
        return area

    actor_profile = user_store.get_profile(actor_username) or {}
    actor_name = actor_profile.get("nick") or actor_username
    territory_store.add_area_event(
        owner_username=owner_username,
        actor_username=actor_username,
        event_type="intruder_enter",
        area_id=area.get("id"),
        lat=lat,
        lng=lng,
        payload={
            "actor_nick": actor_name,
            "area_status": area.get("status", "active")
        }
    )
    add_system_message_to_user(
        owner_username,
        "warning",
        "Obcy gracz na twoim terenie",
        f"{actor_name} wszedł na kontrolowany przez Ciebie obszar."
    )
    return area


def notify_encircled_area_owners(cooldown_seconds=300):
    for area in safe_player_areas(territory_store.list_player_areas()):
        if area.get("status") != "encircled":
            continue

        owner_username = area.get("owner_username")
        area_id = area.get("id")
        area_key = conflict_area_key(area)
        has_stable_event = territory_store.area_event_exists_with_payload_key(
            owner_username,
            owner_username,
            "area_encircled",
            "area_key",
            area_key,
        )
        has_recent_legacy_event = territory_store.recent_area_event_exists(
            owner_username,
            owner_username,
            "area_encircled",
            area_id=area_id,
            seconds=cooldown_seconds,
        )
        if has_stable_event or has_recent_legacy_event:
            continue

        territory_store.add_area_event(
            owner_username=owner_username,
            actor_username=owner_username,
            event_type="area_encircled",
            area_id=area_id,
            lat=area.get("centroid_lat"),
            lng=area.get("centroid_lng"),
            payload={"area_status": "encircled", "area_key": area_key}
        )
        add_system_message_to_user(
            owner_username,
            "danger",
            "Pole zostało otoczone",
            "Jedno z Twoich pól zostało pochłonięte przez większy obszar innego gracza. Jesteś bardziej widoczny i podatny na atak."
        )


def ensure_profile_template_projects_folder():
    template = resources_store.get("user_template", default={})
    files = template.setdefault("files", {})
    changed = False
    if template.get("hackcoins") != 1000:
        template["hackcoins"] = 1000
        changed = True
    if "operations" not in template:
        template["operations"] = []
        changed = True
    if "market_history" not in template:
        template["market_history"] = []
        changed = True
    if "risk_events" not in template:
        template["risk_events"] = []
        changed = True
    if "projects" not in files:
        files["projects"] = []
        changed = True
    if "pro_system_projects" not in files:
        files["pro_system_projects"] = []
        changed = True
    if "gps" not in files:
        files["gps"] = []
        changed = True
    if "territory_stats" not in template:
        template["territory_stats"] = {
            "total_area": 0,
            "effective_area": 0,
            "area_baseline": 0,
            "next_level_area": 0,
            "area_to_next_level": 0,
            "clusters_count": 0,
            "captured_targets_count": 0,
            "last_area_gain": 0,
            "last_effective_gain": 0,
            "total_perimeter": 0,
            "edges_count": 0,
            "span_density": 0,
            "density_multiplier": 0
        }
        changed = True
    if "desktop_settings" not in template:
        template["desktop_settings"] = {
            "wallpaper": "",
            "icon_positions": {},
            "auto_fullscreen": False,
            "map_tile_scheme": "osm"
        }
        changed = True
    else:
        desktop_settings = template["desktop_settings"] if isinstance(template["desktop_settings"], dict) else {}
        if desktop_settings is not template["desktop_settings"]:
            template["desktop_settings"] = desktop_settings
            changed = True
        if "wallpaper" not in desktop_settings:
            desktop_settings["wallpaper"] = ""
            changed = True
        if "icon_positions" not in desktop_settings or not isinstance(desktop_settings.get("icon_positions"), dict):
            desktop_settings["icon_positions"] = {}
            changed = True
        if "auto_fullscreen" not in desktop_settings:
            desktop_settings["auto_fullscreen"] = False
            changed = True
        if "map_tile_scheme" not in desktop_settings:
            desktop_settings["map_tile_scheme"] = "osm"
            changed = True
    if changed:
        resources_store.set("user_template", template)


def get_player_level(profile):
    try:
        return max(1, int(profile.get("level", 1)))
    except (TypeError, ValueError):
        return 1


def get_player_action_range(profile):
    level = get_player_level(profile)
    bonus = clamp_storage_number((profile or {}).get("scan_range_bonus"), default=0, minimum=0)
    return min(4000, round(300 * math.sqrt(level)) + bonus)


def get_player_map_zoom(profile):
    bonus = clamp_storage_number((profile or {}).get("map_zoom_bonus"), default=0, minimum=0)
    return max(1, min(20, 18 + bonus))


def get_player_min_map_zoom(profile):
    level = get_player_level(profile)
    if level >= 24:
        return 14
    if level >= 12:
        return 15
    if level >= 6:
        return 16
    if level >= 3:
        return 17
    return 18


def get_profile_clan(profile):
    if not profile:
        return ""
    raw = (
        str(profile.get("clan") or "").strip()
        or str((profile.get("fraction") or {}).get("name") or "").strip()
    )
    return FACTION_NAMES.get(raw, raw)


def get_pro_system_tool(tool_id):
    tool_id = str(tool_id or "").strip()
    return next((tool for tool in PRO_SYSTEM_TOOLS if tool["id"] == tool_id), None)


def is_pro_system_tool(app):
    return (
        isinstance(app, dict)
        and app.get("type") == "pro-system-tool"
        and app.get("category") == "pro-system-tools"
    )


def is_system_creator_app(app):
    return (
        isinstance(app, dict)
        and (
            (
                app.get("type") == "creator"
                and app.get("category") == "creators"
            )
            or (
                app.get("type") == "system_lab"
                and app.get("category") == "pro-system-lab"
            )
        )
    )


def is_system_catalog_app(app):
    return is_googleplex_product(app) or is_pro_system_tool(app) or is_system_creator_app(app)


def profile_fraction_values(profile):
    values = {
        str(profile.get("clan") or "").strip(),
        str((profile.get("fraction") or {}).get("name") or "").strip(),
        get_profile_clan(profile),
    }
    return {value for value in values if value}


def pro_system_tools_catalog():
    return [
        {
            **dict(tool),
            "published": True,
            "downloads": int(tool.get("downloads") or 0),
        }
        for tool in PRO_SYSTEM_TOOLS
    ]


def creator_system_apps_catalog():
    return [
        {
            **dict(app),
            "published": True,
            "downloads": int(app.get("downloads") or 0),
        }
        for app in CREATOR_SYSTEM_APPS
    ]


def get_app_catalog():
    apps = resources_store.get("app_config", default=[]) or []
    return normalize_app_contracts(
        list(apps) + pro_system_tools_catalog() + creator_system_apps_catalog() + googleplex_product_catalog()
    )


def googleplex_product_catalog():
    return [dict(product) for product in GOOGLEPLEX_EFFECT_PRODUCTS]


def storage_upgrade_products_catalog():
    return [dict(product) for product in GOOGLEPLEX_EFFECT_PRODUCTS if product.get("product_type") == "storage_upgrade"]


def app_is_installed(profile, app_id):
    app_id = str(app_id or "").strip()
    if not app_id:
        return False
    return any(str(app.get("id") or "").strip() == app_id for app in profile.get("apps", []) or [])


def storage_product_is_purchased(profile, product_id):
    product_id = str(product_id or "").strip()
    if not product_id:
        return False
    upgrades = profile.get("storage_upgrades", []) if isinstance(profile, dict) else []
    if not isinstance(upgrades, list):
        return False
    return any(str(item.get("id") or "").strip() == product_id for item in upgrades if isinstance(item, dict))


def googleplex_product_is_purchased(profile, product_id):
    product_id = str(product_id or "").strip()
    if not product_id:
        return False
    for field_name in ("googleplex_products", "product_purchases"):
        purchases = profile.get(field_name, []) if isinstance(profile, dict) else []
        if isinstance(purchases, list) and any(
            str(item.get("id") or "").strip() == product_id
            for item in purchases
            if isinstance(item, dict)
        ):
            return True
    return storage_product_is_purchased(profile, product_id)


def googleplex_product_storage_bonus(product):
    if not isinstance(product, dict):
        return 0
    for effect in product.get("effects") or []:
        if isinstance(effect, dict) and str(effect.get("type") or "") == "storage_capacity_bonus":
            return clamp_storage_number(effect.get("value") or product.get("storage_capacity_bonus"), default=0, minimum=0)
    return clamp_storage_number(product.get("storage_capacity_bonus"), default=0, minimum=0)


def reconcile_googleplex_storage_products(profile):
    if not isinstance(profile, dict):
        return False

    storage_products = {
        str(product.get("id") or ""): product
        for product in storage_upgrade_products_catalog()
        if isinstance(product, dict) and product.get("id")
    }
    purchased_ids = []
    for field_name in ("googleplex_products", "product_purchases", "storage_upgrades"):
        values = profile.get(field_name)
        if not isinstance(values, list):
            continue
        for item in values:
            if isinstance(item, dict):
                product_id = str(item.get("id") or "").strip()
                if product_id in storage_products and product_id not in purchased_ids:
                    purchased_ids.append(product_id)

    if not purchased_ids:
        return False

    changed = False
    required_capacity = DEFAULT_STORAGE_CAPACITY_MB + sum(
        googleplex_product_storage_bonus(storage_products[product_id])
        for product_id in purchased_ids
    )
    current_capacity = clamp_storage_number(
        profile.get("storage_capacity"),
        default=DEFAULT_STORAGE_CAPACITY_MB,
        minimum=64,
    )
    if current_capacity < required_capacity:
        profile["storage_capacity"] = required_capacity
        changed = True

    product_purchases = profile.get("product_purchases")
    if not isinstance(product_purchases, list):
        product_purchases = []
        profile["product_purchases"] = product_purchases
        changed = True
    googleplex_products = profile.get("googleplex_products")
    if not isinstance(googleplex_products, list):
        googleplex_products = []
        profile["googleplex_products"] = googleplex_products
        changed = True
    storage_upgrades = profile.get("storage_upgrades")
    if not isinstance(storage_upgrades, list):
        storage_upgrades = []
        profile["storage_upgrades"] = storage_upgrades
        changed = True

    existing_product_ids = {
        str(item.get("id") or "").strip()
        for item in product_purchases
        if isinstance(item, dict)
    }
    existing_googleplex_ids = {
        str(item.get("id") or "").strip()
        for item in googleplex_products
        if isinstance(item, dict)
    }
    existing_upgrade_ids = {
        str(item.get("id") or "").strip()
        for item in storage_upgrades
        if isinstance(item, dict)
    }

    for product_id in purchased_ids:
        product = storage_products[product_id]
        bonus = googleplex_product_storage_bonus(product)
        if product_id not in existing_product_ids:
            product_purchases.append({
                "id": product_id,
                "name": product.get("name"),
                "product_type": "storage_upgrade",
                "category": product.get("category", "storage"),
                "effects": [{"type": "storage_capacity_bonus", "value": bonus}],
                "price": product.get("price", 0),
                "consumable": False,
            })
            changed = True
        if product_id not in existing_googleplex_ids:
            googleplex_products.append({
                "id": product_id,
                "name": product.get("name"),
                "product_type": "storage_upgrade",
                "category": product.get("category", "storage"),
                "effects": [{"type": "storage_capacity_bonus", "value": bonus}],
                "price": product.get("price", 0),
                "consumable": False,
            })
            changed = True
        if product_id not in existing_upgrade_ids:
            storage_upgrades.append({
                "id": product_id,
                "name": product.get("name"),
                "storage_capacity_bonus": bonus,
                "price": product.get("price", 0),
            })
            changed = True

    return changed


def is_googleplex_product(item):
    return isinstance(item, dict) and bool(item.get("product_type") or item.get("effects"))


def apply_googleplex_product_effect(profile, product, username=None):
    if not isinstance(profile, dict) or not isinstance(product, dict):
        return {"applied": [], "messages": []}
    effects = product.get("effects")
    if not isinstance(effects, list):
        effects = []
    if not effects and product.get("product_type") == "storage_upgrade" and product.get("storage_capacity_bonus"):
        effects = [{"type": "storage_capacity_bonus", "value": product.get("storage_capacity_bonus")}]
    applied = []
    messages = []

    for effect in effects:
        if not isinstance(effect, dict):
            continue
        effect_type = str(effect.get("type") or "").strip()
        if effect_type == "storage_capacity_bonus":
            bonus = clamp_storage_number(effect.get("value") or product.get("storage_capacity_bonus"), default=0, minimum=1)
            normalize_profile_storage(profile)
            profile["storage_capacity"] = clamp_storage_number(
                profile.get("storage_capacity"),
                default=DEFAULT_STORAGE_CAPACITY_MB,
                minimum=DEFAULT_STORAGE_CAPACITY_MB,
            ) + bonus
            applied.append({"type": effect_type, "value": bonus})
            messages.append(f"Pojemnosc dysku +{bonus} MB.")
        elif effect_type == "travel_city":
            city_key = str(effect.get("city") or product.get("travel_city") or "").strip()
            city = TRAVEL_CITIES.get(city_key)
            if not city:
                raise ValueError(f"Nieznane miasto biletu: {city_key}")
            position_updates = normalize_profile_position_update(
                {"lat": city["lat"], "lng": city["lng"]},
                username=username,
                source="googleplex_travel",
            )
            profile.update(position_updates)
            profile["current_city"] = city["name"]
            applied.append({"type": effect_type, "city": city["name"], "lat": city["lat"], "lng": city["lng"]})
            messages.append(f"Przejazd do miasta: {city['name']}.")
        elif effect_type in {"map_zoom_bonus", "scan_range_bonus", "bike_range_bonus"}:
            value = clamp_storage_number(effect.get("value"), default=0, minimum=1)
            current = clamp_storage_number(profile.get(effect_type), default=0, minimum=0)
            profile[effect_type] = current + value
            applied.append({"type": effect_type, "value": value, "total": profile[effect_type]})
            messages.append(f"{effect_type} +{value}.")

    normalize_profile_storage(profile)
    return {"applied": applied, "messages": messages}


def public_pro_system_tools(profile=None):
    tools = []
    for tool in PRO_SYSTEM_TOOLS:
        item = dict(tool)
        installed = app_is_installed(profile or {}, item.get("id")) if profile else False
        item["installed"] = installed
        item["enabled"] = installed
        if not installed:
            item["disabled_reason"] = "Narzedzie nie jest zainstalowane."
        tools.append(item)
    return tools


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def infer_legacy_map_actions(app):
    """TODO_MIGRATION: infer app.map_actions for pre-contract app records."""
    actions = set()
    app_type = str(app.get("type") or "").strip()
    detects = {str(item).strip() for item in as_list(app.get("detects"))}
    interferes = {str(item).strip() for item in as_list(app.get("interferes_with"))}
    effects = {str(item).strip() for item in as_list(app.get("effects"))}

    def has_any(values, keywords):
        return bool(values.intersection(keywords))

    if app_type == "scanner" and has_any(detects, {"open_ports"}):
        actions.add("scan_ports")
    if app_type in {"exploit", "exploit_suite"}:
        actions.add("exploit")
    if app_type in {"scanner", "os_component"} and has_any(detects, {"processes", "active_tasks", "security_logs"}):
        actions.add("sniff")
    if has_any(detects, {"user_location", "device_presence", "ip_leaks"}):
        actions.add("trace")
    if has_any(detects, {"camera_feed", "video_stream"}):
        actions.add("camera_stream")
    if has_any(interferes, {"camera", "video_stream"}):
        actions.add("camera_shutdown")
    if has_any(detects, {"microphone_activity", "audio_stream"}):
        actions.add("mic_sniff")
    if has_any(detects, {"bluetooth_device", "bluetooth_devices", "device_location", "device_presence"}):
        actions.add("trace_device")
    if has_any(interferes, {"vehicle_ecu", "car_system", "gps_tracker"}):
        actions.add("car_hack")
    if has_any(detects, {"gps_location", "car_signal", "movement_data"}):
        actions.add("trace_gps")
    if has_any(detects, {"atm_logs", "financial_data"}):
        actions.add("atm_logs")
    if app_type == "sniffer" or has_any(effects, {"network_capture"}):
        actions.add("install_sniffer")
    if has_any(detects, {"wifi", "ssid", "access_points"}):
        actions.add("scan_hotspots")
    if has_any(interferes, {"speaker", "audio_output"}):
        actions.add("audio_hack")

    return sorted(actions)


LEGACY_MAP_ACTION_SOURCES = {"legacy_inferred", "migration_inferred"}


def cleanup_migrated_map_actions(app, actions):
    """Remove known false-positive map actions from migrated app contracts."""
    app_type = str((app or {}).get("type") or "").strip()
    action_set = {
        str(action).strip()
        for action in (actions or [])
        if str(action).strip()
    }

    # Sprint 24: exploit_suite used to inherit scan_ports from weak_configs /
    # open_ports. That made PenCombo appear as a scanner. Keep exploit, remove
    # scan_ports unless the app has a truly explicit, non-migrated contract.
    if app_type == "exploit_suite":
        action_set.discard("scan_ports")

    return sorted(action_set)


def infer_operation_types_from_map_actions(map_actions):
    operations = []
    for action in map_actions or []:
        for operation_type in MAP_ACTION_OPERATION_TYPES.get(str(action).strip(), []):
            if operation_type not in operations:
                operations.append(operation_type)
    return operations


def normalize_app_contract(app, infer_legacy=True):
    normalized = dict(app or {})
    explicit_actions = [
        str(action).strip()
        for action in as_list(normalized.get("map_actions"))
        if str(action).strip()
    ]
    if explicit_actions:
        source = str(normalized.get("map_actions_source") or "").strip()
        if source in LEGACY_MAP_ACTION_SOURCES:
            explicit_actions = cleanup_migrated_map_actions(normalized, explicit_actions)
        normalized["map_actions"] = list(dict.fromkeys(explicit_actions))
    elif infer_legacy:
        inferred = infer_legacy_map_actions(normalized)
        if inferred:
            normalized["map_actions"] = cleanup_migrated_map_actions(normalized, inferred)
            normalized["map_actions_source"] = "legacy_inferred"
        else:
            normalized["map_actions"] = []
    else:
        normalized["map_actions"] = []

    explicit_operations = [
        str(operation_type).strip()
        for operation_type in as_list(normalized.get("operation_types"))
        if str(operation_type).strip()
    ]
    if explicit_operations:
        normalized["operation_types"] = list(dict.fromkeys(explicit_operations))
    else:
        inferred_operations = infer_operation_types_from_map_actions(normalized.get("map_actions", []))
        normalized["operation_types"] = inferred_operations
        if inferred_operations:
            normalized["operation_types_source"] = "legacy_inferred"

    normalized["resource_types"] = list(dict.fromkeys(
        str(resource_type).strip()
        for resource_type in as_list(normalized.get("resource_types"))
        if str(resource_type).strip()
    ))
    normalized["target_types"] = list(dict.fromkeys(
        str(target_type).strip()
        for target_type in as_list(normalized.get("target_types"))
        if str(target_type).strip()
    ))
    normalize_app_storage_fields(normalized)
    normalize_app_quality_fields(normalized)
    normalize_app_balance_fields(normalized)
    return normalized


def normalize_app_contracts(apps, infer_legacy=True):
    return [normalize_app_contract(app, infer_legacy=infer_legacy) for app in (apps or [])]


def is_legacy_map_action_fallback_enabled():
    value = os.environ.get("CHAOS_LEGACY_MAP_ACTION_FALLBACK")
    if value is None:
        return True
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def get_apps_for_map_action(apps, map_action_id, allow_legacy_fallback=True):
    map_action_id = str(map_action_id or "").strip()
    if not map_action_id:
        return [], "none"

    legacy_enabled = allow_legacy_fallback and is_legacy_map_action_fallback_enabled()
    normalized_apps = normalize_app_contracts(apps, infer_legacy=legacy_enabled)
    matched = [
        app for app in normalized_apps
        if map_action_id in {
            str(action).strip()
            for action in as_list(app.get("map_actions"))
            if str(action).strip()
        }
        and (
            legacy_enabled
            or str(app.get("map_actions_source") or "").strip() not in LEGACY_MAP_ACTION_SOURCES
        )
    ]
    if matched:
        return matched, "map_actions"

    if not legacy_enabled:
        return [], "none"

    # TODO_MIGRATION: keep the old router only for installed apps that have not
    # been migrated to app.map_actions yet.
    legacy_matched = get_apps_for_action(apps, map_action_id)
    if legacy_matched:
        return legacy_matched, "legacy"
    return [], "none"


def serialize_tool_selection_app(app):
    name = str(app.get("name") or app.get("id") or "").strip()
    return {
        "id": app.get("id"),
        "name": name,
        "icon": app.get("icon", "🛠️"),
        "interface": app.get("interface", ""),
        "type": app.get("type", ""),
        "map_actions": as_list(app.get("map_actions")),
        "operation_types": as_list(app.get("operation_types")),
        "resource_types": as_list(app.get("resource_types")),
        "target_types": as_list(app.get("target_types")),
        "tool_file": app.get("file_name") or app.get("project_file") or (f"{name}.sh" if name else ""),
        "description": app.get("description", ""),
        "file_size": app.get("file_size"),
        "disk_usage": app.get("disk_usage") or app.get("install_size"),
        "install_size": app.get("install_size") or app.get("disk_usage"),
        "quality_score": app.get("quality_score"),
        "reliability": app.get("reliability"),
        "creator_power": app.get("creator_power"),
        "power_score": app.get("power_score"),
        "price_hint": app.get("price_hint"),
        "balance_tier": app.get("balance_tier"),
        "recommended_level": app.get("recommended_level"),
        "recommended_respect": app.get("recommended_respect"),
        "map_actions_source": app.get("map_actions_source", ""),
    }


def apply_app_map_actions_to_aimed_target(profile, app, username=None):
    """Mark the active target as touched by a launched app's map-action contract."""
    aimed_target = profile.get("aimed_target")
    if not isinstance(aimed_target, dict) or not aimed_target:
        return False, []
    if not target_has_stable_runtime_identity(aimed_target):
        return False, []

    normalized_app = normalize_app_contract(app or {})
    actions = [
        str(action).strip()
        for action in as_list(normalized_app.get("map_actions"))
        if str(action).strip()
    ]
    if not actions:
        return False, []

    allowed = aimed_target.setdefault("actions_allowed", {})
    if username:
        try:
            latest_profile = user_store.get_profile(username) or {}
            latest_target = latest_profile.get("aimed_target") or {}
            if (
                isinstance(latest_target, dict)
                and targets_share_runtime_identity(latest_target, aimed_target)
            ):
                latest_allowed = latest_target.get("actions_allowed") or {}
                if isinstance(latest_allowed, dict):
                    for key, value in latest_allowed.items():
                        if value is True and allowed.get(key) is not True:
                            allowed[key] = True
        except Exception:
            pass

    changed = False
    marked = []
    for action in actions:
        for key in (action, HACK_ACTION_STEP_ALIASES.get(action, action)):
            if not key:
                continue
            if allowed.get(key) is not True:
                allowed[key] = True
                changed = True
            if key not in marked:
                marked.append(key)

    if changed:
        profile["aimed_target"] = aimed_target
        if username:
            try:
                player_target_runtime_store.upsert_aimed(username, aimed_target, status="in_progress", source="app_map_actions")
            except Exception as exc:
                print(f"[target runtime] app action merge failed user={username} error={exc}", flush=True)
    return changed, marked


def merge_latest_aimed_target_runtime_state(profile, username):
    """Keep target app progress monotonic when app/map requests finish out of order."""
    profile = profile if isinstance(profile, dict) else {}
    aimed_target = profile.get("aimed_target")
    current_target_is_valid = (
        isinstance(aimed_target, dict)
        and bool(aimed_target)
        and target_has_stable_runtime_identity(aimed_target)
    )
    if not username:
        return aimed_target

    try:
        stored_target = player_target_runtime_store.get_active_target(username)
    except Exception as exc:
        print(f"[target runtime] read failed user={username} error={exc}", flush=True)
        stored_target = {}
    try:
        runtime_state = player_target_runtime_store.get(username)
    except Exception:
        runtime_state = {}

    if isinstance(stored_target, dict) and stored_target:
        if find_owned_captured_target_for_runtime_target(username, stored_target):
            if current_target_is_valid and not targets_share_selection_identity(stored_target, aimed_target):
                try:
                    player_target_runtime_store.upsert_aimed(
                        username,
                        aimed_target,
                        source="runtime_merge_new_target_over_captured_stored",
                    )
                except Exception as exc:
                    print(
                        f"[target runtime] new target over captured stored failed user={username} error={exc}",
                        flush=True,
                    )
                profile["aimed_target"] = aimed_target
                return aimed_target
            try:
                player_target_runtime_store.mark_captured(username, stored_target, source="runtime_merge_stored_captured")
            except Exception as exc:
                print(f"[target runtime] stored captured merge failed user={username} error={exc}", flush=True)
            profile["aimed_target"] = {}
            return {}
        if not isinstance(aimed_target, dict) or not aimed_target:
            profile["aimed_target"] = stored_target
            return stored_target
        if targets_share_selection_identity(stored_target, aimed_target):
            allowed = aimed_target.setdefault("actions_allowed", {})
            for key, value in (stored_target.get("actions_allowed") or {}).items():
                if value is True:
                    allowed[key] = True
            security = aimed_target.setdefault("security", {})
            for key, value in (stored_target.get("security") or {}).items():
                if value is False:
                    security[key] = False
            if not aimed_target.get("target_id"):
                aimed_target["target_id"] = stored_target.get("target_id") or build_operation_target_id(aimed_target)
            try:
                player_target_runtime_store.upsert_aimed(username, aimed_target, source="runtime_merge")
            except Exception:
                pass
            profile["aimed_target"] = aimed_target
            return aimed_target
        if current_target_is_valid:
            try:
                player_target_runtime_store.upsert_aimed(username, aimed_target, source="runtime_merge_new_target")
            except Exception as exc:
                print(f"[target runtime] new target merge failed user={username} error={exc}", flush=True)
            profile["aimed_target"] = aimed_target
            return aimed_target
        profile["aimed_target"] = stored_target
        return stored_target

    if not isinstance(aimed_target, dict) or not aimed_target:
        return aimed_target

    if isinstance(runtime_state, dict) and runtime_state.get("status") in {"cleared", "captured"}:
        runtime_target = runtime_state.get("target") or {}
        if (not runtime_target and not current_target_is_valid) or (
            runtime_target and targets_share_selection_identity(runtime_target, aimed_target)
        ):
            profile["aimed_target"] = {}
            return {}

    if find_owned_captured_target_for_runtime_target(username, aimed_target):
        try:
            player_target_runtime_store.mark_captured(username, aimed_target, source="runtime_merge_captured")
        except Exception as exc:
            print(f"[target runtime] captured merge failed user={username} error={exc}", flush=True)
        profile["aimed_target"] = {}
        return {}

    try:
        player_target_runtime_store.seed_from_profile(username, profile)
    except Exception:
        pass

    try:
        latest_profile = user_store.get_profile(username) or {}
    except Exception:
        return aimed_target

    latest_target = latest_profile.get("aimed_target") or {}
    if not isinstance(latest_target, dict) or not latest_target:
        return aimed_target

    if not targets_share_selection_identity(latest_target, aimed_target):
        return aimed_target

    allowed = aimed_target.setdefault("actions_allowed", {})
    latest_allowed = latest_target.get("actions_allowed") or {}
    if isinstance(latest_allowed, dict):
        for key, value in latest_allowed.items():
            if value is True:
                allowed[key] = True

    security = aimed_target.setdefault("security", {})
    latest_security = latest_target.get("security") or {}
    if isinstance(security, dict) and isinstance(latest_security, dict):
        for key, value in latest_security.items():
            if value is False and security.get(key) is not False:
                security[key] = False

    profile["aimed_target"] = aimed_target
    return aimed_target


def infer_googleplex_app_level(app):
    level = str(app.get("app_level") or app.get("level_label") or "").strip()
    if level:
        return level

    try:
        required_level = int(app.get("required_level") or 1)
    except (TypeError, ValueError):
        required_level = 1
    try:
        price = int(app.get("price") or 0)
    except (TypeError, ValueError):
        price = 0

    resource_count = len(as_list(app.get("resource_types")))
    operation_count = len(as_list(app.get("operation_types")))

    if required_level >= 10 or price >= 3000 or resource_count >= 3:
        return "Pro"
    if required_level >= 4 or price >= 1000 or operation_count >= 2 or resource_count >= 2:
        return "Advanced"
    return "Basic"


def googleplex_catalog_payload(app, profile):
    item = dict(app or {})
    normalize_app_storage_fields(item)
    normalize_app_quality_fields(item)
    normalize_app_balance_fields(item)
    item["map_actions"] = [
        str(action).strip()
        for action in as_list(item.get("map_actions"))
        if str(action).strip()
    ]
    item["operation_types"] = [
        str(operation_type).strip()
        for operation_type in as_list(item.get("operation_types"))
        if str(operation_type).strip()
    ]
    item["resource_types"] = [
        str(resource_type).strip()
        for resource_type in as_list(item.get("resource_types"))
        if str(resource_type).strip()
    ]
    item["target_types"] = [
        str(target_type).strip()
        for target_type in as_list(item.get("target_types"))
        if str(target_type).strip()
    ]
    item["app_level"] = infer_googleplex_app_level(item)
    if is_googleplex_product(item):
        item["installed"] = (not item.get("consumable")) and googleplex_product_is_purchased(profile or {}, item.get("id"))
    else:
        item["installed"] = app_is_installed(profile, item.get("id"))

    try:
        price = max(0, int(item.get("price") or 0))
    except (TypeError, ValueError):
        price = 0
    balance = int((profile or {}).get("hackcoins", 0) or 0)
    item["can_afford"] = balance >= price
    item["install_blocked_reason"] = ""
    if item["installed"]:
        item["install_blocked_reason"] = "Aplikacja juz kupiona."
    elif not item["can_afford"]:
        item["install_blocked_reason"] = f"Brak HC. Cena: {price}, masz: {balance}."

    requirement_error = validate_app_install_requirements(item, profile or {})
    if not item["install_blocked_reason"] and requirement_error:
        item["install_blocked_reason"] = requirement_error

    return item


def validate_app_install_requirements(app_data, profile):
    if not is_system_catalog_app(app_data):
        return None

    level = get_player_level(profile)
    try:
        respect = int(profile.get("respect", 0) or 0)
    except (TypeError, ValueError):
        respect = 0

    required_level = int(app_data.get("required_level") or 1)
    required_respect = int(app_data.get("required_respect") or 0)
    if level < required_level:
        return f"Wymagany poziom {required_level}."
    if respect < required_respect:
        return f"Wymagany Respect {required_respect}."

    allowed = [str(item).strip() for item in (app_data.get("allowed_fractions") or []) if str(item).strip()]
    if allowed and profile_fraction_values(profile).isdisjoint(set(allowed)):
        return "Ta aplikacja jest niedostepna dla Twojej frakcji."
    return None


def ensure_purchase_account_profile(username):
    username = str(username or "").strip()
    if not username:
        return None
    profile = user_store.get_profile(username)
    if profile:
        return profile

    profile = {
        "username": username,
        "nick": username,
        "hackcoins": 0,
        "level": 1,
        "respect": 0,
        "apps": [],
        "files": {"tools": [], "projects": []},
        "system_messages": [],
        "desktop_settings": {"wallpaper": "", "icon_positions": {}, "auto_fullscreen": False, "map_tile_scheme": "osm"},
    }
    user_store.save_profile(profile)
    return profile


MAP_TILE_SCHEMES = {
    "osm": {
        "label": "OpenStreetMap",
        "tiles": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attr": "OpenStreetMap contributors",
        "zoom_offset": 0,
    },
    "carto_light": {
        "label": "Carto Light",
        "tiles": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        "attr": "OpenStreetMap contributors, CARTO",
        "zoom_offset": 0,
    },
    "carto_dark": {
        "label": "Carto Dark",
        "tiles": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        "attr": "OpenStreetMap contributors, CARTO",
        "zoom_offset": 0,
    },
    "opentopo": {
        "label": "OpenTopo",
        "tiles": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        "attr": "Map data: OpenStreetMap contributors, SRTM | Map style: OpenTopoMap",
        "zoom_offset": -1,
        "max_zoom_cap": 17,
    },
}


def normalize_desktop_settings(settings):
    source = settings if isinstance(settings, dict) else {}
    normalized = {
        "wallpaper": str(source.get("wallpaper") or "").strip(),
        "icon_positions": source.get("icon_positions") if isinstance(source.get("icon_positions"), dict) else {},
        "auto_fullscreen": source.get("auto_fullscreen") is True,
        "map_tile_scheme": str(source.get("map_tile_scheme") or "osm").strip(),
    }
    if normalized["wallpaper"] not in [
        "",
        "wall-1", "wall-2", "wall-3",
        "wall-chaos-green", "wall-chaos-blue", "wall-chaos-red",
        "wall-chaos-amber", "wall-chaos-violet",
    ]:
        normalized["wallpaper"] = ""
    if normalized["map_tile_scheme"] not in MAP_TILE_SCHEMES:
        normalized["map_tile_scheme"] = "osm"
    return normalized


def ghostlab_project_slug(name):
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(name or "").strip().lower()).strip("_")
    return slug[:48] or "project"


def unique_ghostlab_project_slug(base_slug, projects):
    taken = {str(project.get("slug") or "") for project in projects}
    slug = base_slug
    index = 2
    while slug in taken:
        suffix = f"_{index}"
        slug = f"{base_slug[:max(1, 48 - len(suffix))]}{suffix}"
        index += 1
    return slug


def get_profile_pro_system_projects(profile):
    files = profile.setdefault("files", {})
    projects = files.get("pro_system_projects")
    if not isinstance(projects, list):
        projects = []
    files["pro_system_projects"] = projects
    return files, projects


def default_ghostlab_blueprint(template_id):
    defaults = {
        "financial_sniffer": {
            "steal_percent": 8,
            "detection_percent": 18,
            "cooldown_minutes": 180,
            "success_message": "Financial Sniffer przechwycil drobny przeplyw HC.",
            "failure_message": "Operacja finansowa zostala wygaszona przez zabezpieczenia.",
            "reward_note": "HC transfer draft",
        },
        "friend_kicker": {
            "success_percent": 45,
            "detection_percent": 20,
            "target_policy": "random_contact",
            "victim_message": "Wykryto probe manipulacji kontaktami.",
            "contact_message": "Polaczenie z jednym z graczy zostalo zerwane.",
        },
        "security_panel_proxy": {
            "allowed_switches": "boolean_security_only",
            "presets": "open, low, regular, secure, all",
            "rules": "apply SECURITY_CONFLICTS",
            "conflict_matrix": "locked_until_compiler",
        },
        "system_log_reader": {
            "log_limit": 5,
            "include_type": True,
            "include_status": True,
            "include_created_at": True,
            "redaction_policy": "system_messages_only",
        },
        "arsenal_cleaner": {
            "success_percent": 40,
            "detection_percent": 22,
            "target_policy": "random_non_core_app",
            "protected_apps": "Terminal, Mapa, Browser, Email, Wallet HC, Profil, Pliki",
            "remove_tools_file": True,
        },
    }
    return dict(defaults.get(str(template_id or ""), {"notes": ""}))


def validate_ghostlab_blueprint(template_id, blueprint):
    errors = []
    warnings = []

    def number_between(key, label, min_value, max_value):
        value = blueprint.get(key)
        if not isinstance(value, (int, float)):
            errors.append(f"{label} musi byc liczba.")
            return None
        if value < min_value or value > max_value:
            errors.append(f"{label} musi byc w zakresie {min_value}-{max_value}.")
        return value

    def required_text(key, label, max_len=240):
        value = str(blueprint.get(key) or "").strip()
        if not value:
            errors.append(f"{label} nie moze byc puste.")
        if len(value) > max_len:
            errors.append(f"{label} jest za dlugie.")
        return value

    template_id = str(template_id or "")
    if template_id == "financial_sniffer":
        steal = number_between("steal_percent", "Steal %", 1, 8)
        detection = number_between("detection_percent", "Detection %", 0, 95)
        cooldown = number_between("cooldown_minutes", "Cooldown", 5, 1440)
        required_text("success_message", "Success message")
        required_text("failure_message", "Failure message")
        required_text("reward_note", "Rewards", 160)
        if steal and steal > 6:
            warnings.append("Steal % powyzej 6 zwiekszy balansowe ryzyko w compilerze.")
        if detection is not None and detection < 10:
            warnings.append("Detection % ponizej 10 moze zostac podbite w compilerze.")
        preview = [
            f"kradziez do {steal or '?'}% salda ofiary",
            f"wykrycie {detection if detection is not None else '?'}%",
            f"cooldown {cooldown or '?'} min",
        ]
    elif template_id == "friend_kicker":
        success = number_between("success_percent", "Success %", 1, 85)
        detection = number_between("detection_percent", "Detection %", 0, 95)
        required_text("target_policy", "Targets", 80)
        required_text("victim_message", "Victim system message")
        required_text("contact_message", "Contact system message")
        preview = [
            f"szansa wypchniecia {success or '?'}%",
            f"wykrycie {detection if detection is not None else '?'}%",
            "atakujacy nie widzi listy kontaktow",
        ]
    elif template_id == "security_panel_proxy":
        required_text("allowed_switches", "Allowed switches", 120)
        required_text("presets", "Presets", 160)
        required_text("rules", "Rules")
        required_text("conflict_matrix", "Conflict matrix")
        preview = [
            "panel zmiany boolean security",
            "presety beda mapowane w compilerze",
            "SECURITY_CONFLICTS pozostaje zrodlem zasad",
        ]
    elif template_id == "system_log_reader":
        limit = number_between("log_limit", "Log limit", 1, 5)
        for key in ("include_type", "include_status", "include_created_at"):
            if not isinstance(blueprint.get(key), bool):
                errors.append(f"{key} musi byc boolean.")
        required_text("redaction_policy", "Redaction policy", 120)
        preview = [
            f"odczyt maksymalnie {limit or '?'} system messages",
            "bez prywatnych maili i chatu",
            "wynik tylko podczas aktywnego dostepu",
        ]
    elif template_id == "arsenal_cleaner":
        success = number_between("success_percent", "Success %", 1, 80)
        detection = number_between("detection_percent", "Detection %", 0, 95)
        required_text("target_policy", "Targets", 100)
        required_text("protected_apps", "Protected apps")
        if not isinstance(blueprint.get("remove_tools_file"), bool):
            errors.append("Remove files/tools entry musi byc boolean.")
        preview = [
            f"szansa usuniecia {success or '?'}%",
            f"wykrycie {detection if detection is not None else '?'}%",
            "chronione aplikacje nie beda kandydatami",
        ]
    else:
        required_text("notes", "Notes")
        preview = ["custom draft bez kompilatora"]

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "preview": preview,
    }


def build_ghostlab_artifact(project, blueprint, version):
    compiled_at = datetime.utcnow().isoformat(timespec="seconds")
    template_id = str(project.get("template_id") or "custom")
    contracts = {
        "financial_sniffer": "financial_sniffer",
        "friend_kicker": "friend_kicker",
        "security_panel_proxy": "security_panel",
        "system_log_reader": "system_logs",
        "arsenal_cleaner": "arsenal_cleaner",
    }
    return {
        "artifact_id": f"{project.get('id')}_build_{version}",
        "project_id": str(project.get("id") or ""),
        "project_name": str(project.get("name") or "Untitled"),
        "version": version,
        "status": "compiled",
        "compiled_at": compiled_at,
        "template_id": template_id,
        "template_name": str(project.get("template_name") or ""),
        "tool_category": str(project.get("tool_category") or ""),
        "runtime_contract": contracts.get(template_id, "custom_blueprint"),
        "blueprint_snapshot": dict(blueprint),
    }


def ghostlab_template_app_contract(template_id):
    template_id = str(template_id or "")
    contracts = {
        "financial_sniffer": {
            "tool_family": "sniffer",
            "tool_mode": "desktop",
            "map_actions": [],
            "target_types": ["player"],
            "operation_types": [],
            "resource_types": ["financial_records", "internal_recon_state"],
        },
        "friend_kicker": {
            "tool_family": "exploit",
            "tool_mode": "desktop",
            "map_actions": [],
            "target_types": ["player"],
            "operation_types": [],
            "resource_types": ["internal_recon_state"],
        },
        "security_panel_proxy": {
            "tool_family": "exploit",
            "tool_mode": "desktop",
            "map_actions": [],
            "target_types": ["player"],
            "operation_types": [],
            "resource_types": ["internal_recon_state"],
        },
        "system_log_reader": {
            "tool_family": "scanner_recon",
            "tool_mode": "desktop",
            "map_actions": [],
            "target_types": ["player"],
            "operation_types": [],
            "resource_types": ["device_logs", "internal_recon_state"],
        },
        "arsenal_cleaner": {
            "tool_family": "exploit",
            "tool_mode": "desktop",
            "map_actions": [],
            "target_types": ["player"],
            "operation_types": [],
            "resource_types": ["internal_recon_state"],
        },
    }
    return dict(contracts.get(template_id, {
        "tool_family": "pro_system_tool",
        "tool_mode": "desktop",
        "map_actions": [],
        "target_types": ["player"],
        "operation_types": [],
        "resource_types": ["internal_recon_state"],
    }))


def build_ghostlab_googleplex_app(project, owner_username, owner_profile):
    artifact = project.get("artifact") if isinstance(project.get("artifact"), dict) else {}
    if not artifact:
        return None

    blueprint = artifact.get("blueprint_snapshot")
    if not isinstance(blueprint, dict):
        blueprint = project.get("blueprint") if isinstance(project.get("blueprint"), dict) else {}

    template_id = str(project.get("template_id") or artifact.get("template_id") or "custom")
    risk_defaults = {
        "financial_sniffer": 5,
        "friend_kicker": 4,
        "security_panel_proxy": 3,
        "system_log_reader": 2,
        "arsenal_cleaner": 5,
    }
    price_defaults = {
        "financial_sniffer": 4200,
        "friend_kicker": 3600,
        "security_panel_proxy": 5200,
        "system_log_reader": 2800,
        "arsenal_cleaner": 4700,
    }
    required_defaults = {
        "financial_sniffer": (12, 180),
        "friend_kicker": (10, 150),
        "security_panel_proxy": (15, 240),
        "system_log_reader": (8, 90),
        "arsenal_cleaner": (14, 220),
    }
    required_level, required_respect = required_defaults.get(template_id, (10, 120))
    app_id = str(project.get("googleplex_app_id") or f"ghostlab_{project.get('slug')}_{artifact.get('version', 1)}")
    contract = ghostlab_template_app_contract(template_id)
    app = {
        "id": app_id,
        "name": str(project.get("name") or "GhostLab Tool"),
        "icon": str(project.get("icon") or "🧪"),
        "type": "pro-system-tool",
        "category": "pro-system-tools",
        "description": (
            f"GhostLab Publisher artifact from {project.get('template_name') or template_id}. "
            "Custom runtime zostanie aktywowany w pozniejszym sprincie."
        ),
        "price": price_defaults.get(template_id, 3000),
        "required_level": required_level,
        "required_respect": required_respect,
        "allowed_fractions": [],
        "risk_level": risk_defaults.get(template_id, 3),
        "purchase_account": owner_username,
        "creator_username": owner_username,
        "creator_nick": (owner_profile or {}).get("nick") or owner_username,
        "interface": "terminal",
        "published": True,
        "downloads": 0,
        "generated": True,
        "ghostlab_generated": True,
        "runtime_status": "pending_custom_runtime",
        "source": "ghostlab",
        "source_project_id": str(project.get("id") or ""),
        "source_build_version": artifact.get("version"),
        "artifact_id": artifact.get("artifact_id"),
        "tool_category": str(project.get("tool_category") or artifact.get("tool_category") or ""),
        "template_id": template_id,
        "template_name": str(project.get("template_name") or artifact.get("template_name") or ""),
        "levels": [
            {
                "command": f"ghostlab-tool --artifact {artifact.get('artifact_id')}",
                "logs": [
                    "GhostLab artifact installed.",
                    "Custom pro-system runtime pending.",
                    "Tool metadata available in Googleplex."
                ]
            }
        ],
        "metadata": {
            "blueprint": blueprint,
            "artifact": artifact,
        },
    }
    app.update(contract)
    app["map_actions_source"] = "ghostlab_contract"
    app.update(build_generated_app_quality_fields(owner_profile or {}, app))
    app = normalize_app_contract(app, infer_legacy=False)
    normalize_app_storage_fields(app)
    normalize_app_quality_fields(app)
    enforce_generated_app_price_floor(app)
    return app


def serialize_ghostlab_project(project):
    blueprint = project.get("blueprint") if isinstance(project.get("blueprint"), dict) else {}
    validation = validate_ghostlab_blueprint(project.get("template_id"), blueprint)
    builds = project.get("builds") if isinstance(project.get("builds"), list) else []
    artifact = project.get("artifact") if isinstance(project.get("artifact"), dict) else {}
    publisher_contract = ghostlab_template_app_contract(project.get("template_id") or artifact.get("template_id"))
    publisher_contract.update({
        "type": "pro-system-tool",
        "category": "pro-system-tools",
        "map_actions_source": "ghostlab_contract",
        "runtime_status": "pending_custom_runtime",
    })
    return {
        "id": str(project.get("id") or ""),
        "name": str(project.get("name") or "Untitled"),
        "slug": str(project.get("slug") or ghostlab_project_slug(project.get("name"))),
        "icon": str(project.get("icon") or "🧪"),
        "tool_category": str(project.get("tool_category") or ""),
        "template_id": str(project.get("template_id") or ""),
        "template_name": str(project.get("template_name") or ""),
        "blueprint": blueprint,
        "validation": validation,
        "builds": builds,
        "artifact": artifact,
        "latest_build": builds[-1] if builds else None,
        "publisher_contract": publisher_contract,
        "googleplex_app_id": str(project.get("googleplex_app_id") or ""),
        "published_at": str(project.get("published_at") or ""),
        "status": str(project.get("status") or "draft"),
        "created_at": str(project.get("created_at") or ""),
        "updated_at": str(project.get("updated_at") or ""),
    }


def serialize_player_hack_access(access):
    if not access:
        return {
            "active": False,
            "tools": public_pro_system_tools(),
        }

    victim_profile = user_store.get_profile(access.get("victim_username")) or {}
    attacker_profile = user_store.get_profile(access.get("attacker_username")) or {}
    seconds_left = max(0, int(access.get("seconds_left") or 0))
    return {
        "active": seconds_left > 0,
        "victim_username": access.get("victim_username"),
        "victim_nick": victim_profile.get("nick") or access.get("victim_username"),
        "hacked_until": access.get("hacked_until"),
        "seconds_left": seconds_left,
        "cooldown_until": access.get("cooldown_until"),
        "cooldown_seconds_left": max(0, int(access.get("cooldown_seconds_left") or 0)),
        "tools": public_pro_system_tools(attacker_profile),
    }


def mask_contact_name(name):
    name = str(name or "").strip()
    if not name:
        return ""
    return f"{name[0]}***"


PROTECTED_APP_NAMES = {
    "terminal",
    "mapa",
    "browser",
    "email",
    "wallet hc",
    "profil",
    "pliki",
    "ustawienia",
    "appforge",
    "termcreator",
    "windowmaker",
    "buttonmaker",
}


def app_display_name(app):
    if not isinstance(app, dict):
        return ""
    return str(app.get("name") or app.get("label") or app.get("id") or "").strip()


def is_cleanable_app(app):
    if not isinstance(app, dict):
        return False
    name = app_display_name(app)
    if not name:
        return False
    if name.strip().lower() in PROTECTED_APP_NAMES:
        return False
    if app.get("category") == "core":
        return False
    if app.get("system_app") is True or app.get("protected") is True:
        return False
    return True


def remove_app_tool_files(files, app):
    files = dict(files or {})
    tools = list(files.get("tools", []) or [])
    name = app_display_name(app)
    candidates = set()
    if name:
        candidates.add(f"{name}.sh")
    for key in ["project_file", "file_name"]:
        value = str(app.get(key) or "").strip() if isinstance(app, dict) else ""
        if value:
            candidates.add(value)
    files["tools"] = [
        item for item in tools
        if tool_file_entry_name(item) not in candidates
    ]
    return files


def tool_file_entry_name(item):
    if isinstance(item, dict):
        return str(
            item.get("name")
            or item.get("filename")
            or item.get("file_name")
            or item.get("project_file")
            or ""
        ).strip()
    return str(item or "").strip()


def app_tool_file_candidates(app):
    app = app if isinstance(app, dict) else {}
    name = app_display_name(app)
    candidates = set()
    if name:
        candidates.add(f"{name}.sh")
    for key in ["project_file", "file_name"]:
        value = str(app.get(key) or "").strip()
        if value:
            candidates.add(value)
    return candidates


def player_actor_action(enabled, reason=""):
    return {
        "enabled": bool(enabled),
        "reason": "" if enabled else reason,
    }


def resolve_player_actor_relation(viewer_profile, actor_profile, context=None):
    context = context or {}
    viewer_username = viewer_profile.get("username")
    actor_username = actor_profile.get("username") or context.get("username")

    if actor_username and actor_username == viewer_username:
        return "self"

    if context.get("is_friend"):
        return "friend"

    viewer_clan = get_profile_clan(viewer_profile)
    actor_clan = get_profile_clan(actor_profile)
    if viewer_clan and actor_clan and viewer_clan == actor_clan:
        return "same_clan"

    if context.get("is_intruder"):
        return "intruder"

    return "neutral"


def resolve_player_actor_actions(viewer_username, actor_data, relation):
    is_self = relation == "self" or actor_data.get("username") == viewer_username
    is_friend = relation == "friend"
    is_same_clan = relation == "same_clan"
    is_pending = bool(actor_data.get("is_pending_contact"))
    is_marked_target = bool(actor_data.get("is_marked_target"))

    return {
        "add_friend": player_actor_action(
            not is_self and not is_friend and not is_same_clan and not is_pending,
            "Zaproszenie juz oczekuje." if is_pending else "Niedostepne dla siebie, znajomych i swojego klanu.",
        ),
        "chat": player_actor_action(
            is_friend,
            "Rozmowa dostepna tylko dla znajomych.",
        ),
        "transfer_hc": player_actor_action(
            not is_self,
            "Nie mozna przelac HC samemu sobie.",
        ),
        "mark_target": player_actor_action(
            not is_self and not is_friend and not is_same_clan and not is_marked_target,
            "Ten gracz jest juz celem." if is_marked_target else "Nie mozna oznaczac siebie, znajomych ani swojego klanu.",
        ),
        "profile": player_actor_action(
            not is_self,
            "To twoj profil.",
        ),
    }


def build_player_actor(viewer_username, actor_data, relation=None, context=None):
    context = dict(context or {})
    username = actor_data.get("username") or context.get("username")
    nick = actor_data.get("nick") or username
    lat = actor_data.get("lat")
    lng = actor_data.get("lng", actor_data.get("lon"))
    relation = relation or "neutral"

    return {
        "username": username,
        "nick": nick,
        "avatar": actor_data.get("avatar", ""),
        "lat": lat,
        "lng": lng,
        "status": actor_data.get("status") or context.get("contact_status") or context.get("status") or "",
        "clan": actor_data.get("clan") or context.get("clan") or "",
        "level": actor_data.get("level", context.get("level")),
        "profession": actor_data.get("profession") or context.get("profession") or "",
        "territory_count": actor_data.get("territory_count", context.get("territory_count")),
        "target_status": actor_data.get("target_status") or context.get("target_status") or "",
        "relation": relation,
        "context": context,
        "actions": resolve_player_actor_actions(
            viewer_username,
            {
                "username": username,
                "is_pending_contact": actor_data.get("is_pending_contact") or context.get("is_pending_contact"),
                "is_marked_target": actor_data.get("is_marked_target") or context.get("is_marked_target"),
            },
            relation
        ),
    }


VICTIM_PICKER_APP_ID = "victimPicker"
VICTIM_PICKER_ACTIONS_ALLOWED_TEMPLATE = {
    "scan_ports": False,
    "exploit": False,
    "sniff": False,
    "trace": False,
}


def victim_picker_position(profile):
    position = (profile or {}).get("curently_possition") or (profile or {}).get("current_position") or {}
    try:
        lat = float(position.get("lat"))
        lng = float(position.get("lng", position.get("lon")))
    except (TypeError, ValueError, AttributeError):
        return None
    if lat in (0, 0.0) or lng in (0, 0.0):
        return None
    return {"lat": lat, "lng": lng}


def victim_picker_app_installed(profile):
    return app_is_installed(profile or {}, VICTIM_PICKER_APP_ID)


def victim_picker_distance(candidate, origin):
    if not origin:
        return None
    try:
        return round(Haversine.haversine_distance(
            float(candidate.get("lat")),
            float(candidate.get("lng", candidate.get("lon"))),
            float(origin.get("lat")),
            float(origin.get("lng")),
        ))
    except (TypeError, ValueError):
        return None


def victim_picker_focus_payload(candidate):
    try:
        return {
            "lat": float(candidate.get("lat")),
            "lng": float(candidate.get("lng", candidate.get("lon"))),
            "zoom": 18,
            "mode": candidate.get("target_mode") or "standard",
            "target_id": candidate.get("target_id"),
        }
    except (TypeError, ValueError):
        return None


def build_victim_picker_candidate(viewer_profile, raw_target, candidate_source, origin=None, action_range=None, can_aim=True, disabled_reason=""):
    target = dict(raw_target or {})
    try:
        lat = float(target.get("lat"))
        lng = float(target.get("lng", target.get("lon")))
    except (TypeError, ValueError):
        lat = None
        lng = None

    target["lat"] = lat
    target["lng"] = lng
    target["lon"] = lng
    apply_target_display_label(target)
    target_mode = str(target.get("target_mode") or "standard").strip() or "standard"
    target_type = infer_target_type_from_target(target)
    target_id = (
        target.get("target_id")
        or target.get("candidate_id")
        or build_operation_target_id(target)
    )
    distance_m = victim_picker_distance(target, origin)
    in_range = bool(
        distance_m is not None
        and action_range is not None
        and distance_m <= action_range
    )
    reason = str(disabled_reason or "").strip()
    if lat is None or lng is None:
        can_aim = False
        reason = reason or "missing_position"
    elif origin is None:
        can_aim = False
        reason = reason or "missing_player_position"
    elif not in_range:
        reason = reason or "out_of_range"

    aimed = (viewer_profile or {}).get("aimed_target") or {}
    is_aimed = targets_share_runtime_identity(aimed, target)
    focus = victim_picker_focus_payload({
        **target,
        "target_id": target_id,
        "target_mode": target_mode,
    })
    teleport = dict(focus or {})
    if teleport:
        teleport["requires_confirmation"] = True

    return {
        "target_id": str(target_id),
        "target_mode": target_mode,
        "target_type": target_type,
        "source_type": target.get("source_type") or candidate_source,
        "candidate_source": candidate_source,
        "label": display_target_label(target),
        "name": target.get("name") or display_target_label(target),
        "icon": target.get("icon") or "\U0001F3AF",
        "lat": lat,
        "lng": lng,
        "distance_m": distance_m,
        "action_range_m": action_range,
        "in_range": in_range,
        "can_aim": bool(can_aim),
        "disabled_reason": "" if can_aim else reason,
        "is_aimed": bool(is_aimed),
        "focus": focus,
        "teleport": teleport,
        "raw_ref": {
            "target_username": target.get("target_username") or target.get("username"),
            "vulnerability_id": target.get("vulnerability_id"),
            "foreign_area_id": target.get("foreign_area_id"),
            "contest_owner_username": target.get("contest_owner_username"),
        },
        "target": target,
    }


def build_victim_picker_standard_candidates(viewer_profile, origin, action_range):
    candidates = []
    for target in (viewer_profile or {}).get("targets", []) or []:
        if not isinstance(target, dict):
            continue
        payload = {
            **target,
            "target_mode": target.get("target_mode") or "standard",
            "source_type": target.get("source_type") or "manual",
            "target_id": build_operation_target_id({
                **target,
                "target_mode": target.get("target_mode") or "standard",
            }),
        }
        candidates.append(build_victim_picker_candidate(
            viewer_profile,
            payload,
            "profile.targets",
            origin=origin,
            action_range=action_range,
        ))
    return candidates


def build_victim_picker_active_target_candidate(viewer_profile, origin, action_range):
    aimed = (viewer_profile or {}).get("aimed_target") or {}
    if not isinstance(aimed, dict) or not aimed:
        return None

    try:
        lat = float(aimed.get("lat"))
        lng = float(aimed.get("lng", aimed.get("lon")))
    except (TypeError, ValueError):
        return None

    payload = {
        **aimed,
        "lat": lat,
        "lng": lng,
        "lon": lng,
        "target_mode": aimed.get("target_mode") or "standard",
        "source_type": aimed.get("source_type") or "active_target",
        "target_id": aimed.get("target_id") or build_operation_target_id(aimed),
    }
    candidate = build_victim_picker_candidate(
        viewer_profile,
        payload,
        "profile.targets",
        origin=origin,
        action_range=action_range,
    )
    candidate["is_aimed"] = True
    candidate["is_active_target"] = True
    return candidate


def build_victim_picker_player_candidates(viewer_username, viewer_profile, origin, action_range):
    candidates = {}
    aimed = (viewer_profile or {}).get("aimed_target") or {}
    aimed_player_username = aimed.get("target_username") if aimed.get("target_mode") == "player" else None

    def add_player_candidate(target_username, source, extra_context=None):
        target_username = str(target_username or "").strip()
        if not target_username or target_username == viewer_username or target_username in candidates:
            return
        target_profile = user_store.get_profile(target_username)
        if not target_profile:
            return
        position = target_profile.get("curently_possition") or {}
        context = dict(extra_context or {})
        context["is_friend"] = bool(context.get("is_friend"))
        context["is_intruder"] = bool(context.get("is_intruder"))
        context["is_marked_target"] = bool(aimed_player_username and aimed_player_username == target_username)
        relation = resolve_player_actor_relation(viewer_profile, target_profile, context)
        actor = build_player_actor(
            viewer_username,
            {
                "username": target_username,
                "nick": target_profile.get("nick") or target_username,
                "avatar": target_profile.get("avatar", ""),
                "lat": position.get("lat"),
                "lng": position.get("lng", position.get("lon")),
                "is_marked_target": context["is_marked_target"],
            },
            relation=relation,
            context=context,
        )
        action = (actor.get("actions") or {}).get("mark_target") or {}
        disabled_reason = action.get("reason") or ""
        target = {
            "target_id": f"player:{target_username}",
            "target_mode": "player",
            "target_username": target_username,
            "username": target_username,
            "nick": target_profile.get("nick") or target_username,
            "avatar": target_profile.get("avatar", ""),
            "relation": relation,
            "lat": position.get("lat"),
            "lng": position.get("lng", position.get("lon")),
            "label": target_profile.get("nick") or target_username,
            "name": target_profile.get("nick") or target_username,
            "icon": "\U0001F3AF",
            "source_type": "player",
            "generated": True,
            "security": dict(target_profile.get("security") or {}),
        }
        candidates[target_username] = build_victim_picker_candidate(
            viewer_profile,
            target,
            source,
            origin=origin,
            action_range=action_range,
            can_aim=bool(action.get("enabled")),
            disabled_reason=disabled_reason,
        )

    for contact in mail_store.list_accepted_contacts(viewer_username):
        add_player_candidate(contact.get("name"), "player.friend", {"is_friend": True})
    for intruder in territory_store.list_recent_area_intruders(viewer_username):
        add_player_candidate(intruder.get("username"), "player.intruder", {"is_intruder": True})
    if aimed_player_username:
        add_player_candidate(aimed_player_username, "player.aimed", {"is_marked_target": True})
    return list(candidates.values())


def build_victim_picker_vulnerability_candidates(viewer_username, viewer_profile, origin, action_range):
    candidates = []
    for report in vulnerability_store.list_active():
        item = dict(report or {})
        target = dict(item.get("target") or {})
        target.update({
            "target_id": f"vulnerability:{item.get('id')}",
            "target_mode": "vulnerability",
            "vulnerability_id": item.get("id"),
            "lat": item.get("lat"),
            "lng": item.get("lng"),
            "lon": item.get("lng"),
            "label": item.get("label") or target.get("label"),
            "name": item.get("name") or target.get("name") or item.get("label"),
            "icon": item.get("icon") or target.get("icon") or "\U0001F6E1",
            "source_type": item.get("source_type") or target.get("source_type") or "vulnerability",
            "generated": item.get("generated", target.get("generated", True)),
            "security": dict(item.get("security") or target.get("security") or {}),
        })
        is_reporter = item.get("reported_by_username") == viewer_username
        candidates.append(build_victim_picker_candidate(
            viewer_profile,
            target,
            "clan_vulnerability",
            origin=origin,
            action_range=action_range,
            can_aim=not is_reporter,
            disabled_reason="own_vulnerability" if is_reporter else "",
        ))
    return candidates


def build_victim_picker_conflict_candidates(viewer_username, viewer_profile, origin, action_range):
    candidates = []
    try:
        contested_targets = contested_targets_from_active_conflicts(viewer_username)
    except Exception as exc:
        print(f"[victim-picker] conflict source failed: {exc}", flush=True)
        contested_targets = []
    for target in contested_targets:
        if not isinstance(target, dict):
            continue
        payload = {
            **target,
            "target_mode": "territory_contest",
            "source_type": target.get("source_type") or "territory_contest",
            "icon": target.get("icon") or "\U0001F6E1",
            "target_id": build_operation_target_id({
                **target,
                "target_mode": "territory_contest",
            }),
        }
        candidates.append(build_victim_picker_candidate(
            viewer_profile,
            payload,
            "territory_conflict",
            origin=origin,
            action_range=action_range,
        ))
    return candidates


def build_victim_picker_candidates(viewer_username, viewer_profile):
    origin = victim_picker_position(viewer_profile)
    action_range = get_player_action_range(viewer_profile or {})
    candidates = []
    active_candidate = build_victim_picker_active_target_candidate(viewer_profile, origin, action_range)
    if active_candidate:
        candidates.append(active_candidate)
    candidates.extend(build_victim_picker_standard_candidates(viewer_profile, origin, action_range))
    candidates.extend(build_victim_picker_player_candidates(viewer_username, viewer_profile, origin, action_range))
    candidates.extend(build_victim_picker_vulnerability_candidates(viewer_username, viewer_profile, origin, action_range))
    candidates.extend(build_victim_picker_conflict_candidates(viewer_username, viewer_profile, origin, action_range))

    deduped = {}
    for candidate in candidates:
        key = str(candidate.get("target_id") or "")
        if not key or key in deduped:
            continue
        deduped[key] = candidate
    return sorted(
        deduped.values(),
        key=lambda item: (
            item.get("distance_m") is None,
            item.get("distance_m") if item.get("distance_m") is not None else 10**12,
            item.get("label") or "",
        ),
    )


def clean_victim_picker_aimed_target(candidate):
    target = dict(candidate.get("target") or {})
    clean = {
        "lat": candidate.get("lat"),
        "lng": candidate.get("lng"),
        "lon": candidate.get("lng"),
        "label": candidate.get("label"),
        "name": candidate.get("name") or candidate.get("label"),
        "icon": candidate.get("icon") or "\U0001F3AF",
        "source_type": candidate.get("source_type") or candidate.get("candidate_source") or "victim_picker",
        "generated": bool(target.get("generated", True)),
        "target_mode": candidate.get("target_mode") or "standard",
        "target_username": target.get("target_username") or target.get("username"),
        "username": target.get("target_username") or target.get("username"),
        "nick": target.get("nick"),
        "avatar": target.get("avatar", ""),
        "relation": target.get("relation"),
        "vulnerability_id": target.get("vulnerability_id"),
        "contest_owner_username": target.get("contest_owner_username"),
        "foreign_area_id": target.get("foreign_area_id"),
        "security": dict(target.get("security") or {}),
        "actions_allowed": dict(VICTIM_PICKER_ACTIONS_ALLOWED_TEMPLATE),
    }
    apply_target_display_label(clean)
    return clean


def find_victim_picker_candidate_by_id(viewer_username, viewer_profile, target_id):
    target_id = str(target_id or "").strip()
    if not target_id:
        return None, build_victim_picker_candidates(viewer_username, viewer_profile)
    candidates = build_victim_picker_candidates(viewer_username, viewer_profile)
    for candidate in candidates:
        if str(candidate.get("target_id") or "") == target_id:
            return candidate, candidates
    return None, candidates


def serialize_victim_picker_candidate(candidate):
    item = dict(candidate or {})
    item.pop("target", None)
    return item


TERRITORY_CONTROL_APP_ID = "territoryControl"
TERRITORY_CONTROL_PRESETS = {"open", "low", "regular", "secure", "all"}


def territory_control_app_installed(profile):
    return app_is_installed(profile or {}, TERRITORY_CONTROL_APP_ID)


def territory_control_position(profile):
    return victim_picker_position(profile)


def territory_control_distance(target, origin):
    return victim_picker_distance(target, origin)


def territory_control_security_summary(security):
    values = [
        value for value in (security or {}).values()
        if isinstance(value, bool)
    ]
    total = len(values)
    enabled = sum(1 for value in values if value)
    percent = round((enabled / total) * 100) if total else 0
    return {
        "security_enabled": enabled,
        "security_total": total,
        "security_percent": percent,
    }


def territory_control_target_id(target):
    return build_operation_target_id({
        **(target or {}),
        "target_mode": (target or {}).get("target_mode") or "territory_control",
    })


def territory_control_focus_payload(target, mode="object", cluster_id=None, zoom=18):
    try:
        focus = {
            "lat": float(target.get("lat")),
            "lng": float(target.get("lng", target.get("lon"))),
            "zoom": zoom,
            "mode": mode,
        }
    except (AttributeError, TypeError, ValueError):
        return None
    if cluster_id is not None:
        focus["cluster_id"] = str(cluster_id)
    focus["target_id"] = target.get("target_id") or territory_control_target_id(target)
    return focus


def territory_control_object_payload(username, target, node_role, origin=None, profile=None, cluster_id=None):
    target = dict(target or {})
    try:
        lat = float(target.get("lat"))
        lng = float(target.get("lng", target.get("lon")))
    except (TypeError, ValueError):
        return None
    target["lat"] = lat
    target["lng"] = lng
    target["lon"] = lng
    apply_target_display_label(target)
    security = dict(target.get("security") or {})
    summary = territory_control_security_summary(security)
    target_id = territory_control_target_id(target)
    aimed = (profile or {}).get("aimed_target") or {}
    disabled_reason = ""
    can_abandon = target.get("owner_username") in (None, "", username)
    if not can_abandon:
        disabled_reason = "foreign_object"
    focus = territory_control_focus_payload({**target, "target_id": target_id}, mode="object")
    teleport = dict(focus or {})
    if teleport:
        teleport["requires_confirmation"] = True
    payload = {
        "target_id": target_id,
        "label": display_target_label(target),
        "name": target.get("name") or display_target_label(target),
        "icon": target.get("icon") or "\U0001F4CD",
        "source_type": target.get("source_type") or "",
        "node_role": node_role,
        "state": "alone" if node_role == "alone" else "clustered",
        "lat": lat,
        "lng": lng,
        "distance_from_bike": territory_control_distance(target, origin),
        "security": security,
        **summary,
        "is_aimed": bool(aimed and targets_share_runtime_identity(aimed, target)),
        "can_abandon": bool(can_abandon),
        "disabled_reason": disabled_reason,
        "can_show_on_map": True,
        "can_teleport": True,
        "map_focus": focus,
        "teleport": teleport,
    }
    if cluster_id is not None:
        payload["cluster_id"] = str(cluster_id)
    return payload


def territory_control_target_in_area(target, area):
    try:
        return point_in_polygon(
            float(target.get("lat")),
            float(target.get("lng", target.get("lon"))),
            area.get("vertices", []),
        )
    except (TypeError, ValueError):
        return False


def territory_control_area_threat(username, area, conflicts):
    area_id = area.get("id")
    related = []
    attacked_positions = set()
    area_id_text = str(area_id) if area_id is not None else ""
    for conflict in conflicts or []:
        if str(conflict.get("status") or "active") != "active":
            continue
        area_ids = {str(item) for item in (conflict.get("area_ids") or [])}
        participants = {str(item) for item in (conflict.get("participants") or [])}
        if username not in participants:
            continue

        conflict_targets = [
            item for item in (conflict.get("targets") or [])
            if isinstance(item, dict) and isinstance(item.get("target"), dict)
        ]
        targets_in_area = [
            item for item in conflict_targets
            if territory_control_target_in_area(item.get("target") or {}, area)
        ]
        area_id_matches = bool(area_id_text and area_id_text in area_ids)
        if not area_id_matches and not targets_in_area:
            continue

        related.append(conflict)
        scoped_targets = targets_in_area or conflict_targets
        for item in scoped_targets:
            target = item.get("target") or {}
            owner = item.get("owner_username") or item.get("owner")
            previous_owner = item.get("previous_owner")
            if owner == username or previous_owner == username:
                key = target_position_key(target)
                if key:
                    attacked_positions.add(key)
    threat_state = "clear"
    if related:
        threat_state = "collision"
    return {
        "conflicts": [enrich_conflict_payload(conflict) for conflict in related],
        "conflict_count": len(related),
        "attacked_positions": attacked_positions,
        "threat_state": threat_state,
        "threat_flags": {
            "collision": bool(related),
            "attacked": False,
        },
    }


def territory_control_nearest_object(objects, origin):
    candidates = [
        item for item in objects or []
        if item.get("distance_from_bike") is not None
    ]
    if not candidates:
        return (objects or [None])[0]
    return min(candidates, key=lambda item: item.get("distance_from_bike"))


def build_territory_control_snapshot(username, profile=None):
    profile = profile if isinstance(profile, dict) else load_profile_readonly(
        username,
        strip_sensitive=True,
        normalize_apps=True,
        normalize_files=False,
    )
    if not isinstance(profile, dict):
        return None

    origin = territory_control_position(profile)
    captured_targets = territory_store.list_captured_targets(username)
    own_areas = safe_player_areas(territory_store.list_player_areas(username))
    conflicts = get_active_conflicts_for_player(username)

    assigned_keys = set()
    clusters = []
    for area in own_areas:
        area_id = area.get("id")
        vertices = area.get("vertices") or []
        vertex_keys = {target_position_key(vertex) for vertex in vertices}
        vertex_keys.discard(None)
        pillars = []
        inners = []
        for target in captured_targets:
            key = target_position_key(target)
            if not key:
                continue
            if key in vertex_keys:
                item = territory_control_object_payload(
                    username, target, "pillar", origin=origin, profile=profile, cluster_id=area_id
                )
                if item:
                    pillars.append(item)
                    assigned_keys.add(key)
                continue
            if territory_control_target_in_area(target, area):
                item = territory_control_object_payload(
                    username, target, "inner", origin=origin, profile=profile, cluster_id=area_id
                )
                if item:
                    inners.append(item)
                    assigned_keys.add(key)

        if len(pillars) < 3:
            continue

        objects = pillars + inners
        nearest = territory_control_nearest_object(objects, origin)
        centroid = {
            "lat": float(area.get("centroid_lat")),
            "lng": float(area.get("centroid_lng")),
        }
        threat = territory_control_area_threat(username, area, conflicts)
        attacked_pillars_count = sum(
            1 for pillar in pillars
            if target_position_key(pillar) in threat["attacked_positions"]
        )
        attacked_targets_count = len(threat["attacked_positions"])
        if attacked_targets_count:
            threat["threat_state"] = "attacked"
        threat["threat_flags"]["attacked"] = bool(attacked_targets_count)
        cluster_id = str(area_id)
        map_focus = {
            "type": "cluster",
            "cluster_id": cluster_id,
            "lat": centroid["lat"],
            "lng": centroid["lng"],
            "zoom": 17,
        }
        clusters.append({
            "cluster_id": cluster_id,
            "label": f"Klaster {cluster_id}",
            "status": area.get("status") or "active",
            "threat_state": threat["threat_state"],
            "node_count": len(objects),
            "pillar_count": len(pillars),
            "inner_count": len(inners),
            "area_size": float(area.get("area_size") or 0),
            "perimeter": calculate_area_perimeter(vertices),
            "conflict_count": threat["conflict_count"],
            "attacked_pillars_count": attacked_pillars_count,
            "attacked_targets_count": attacked_targets_count,
            "threat_flags": threat["threat_flags"],
            "centroid": centroid,
            "navigation_target": nearest,
            "distance_from_bike": nearest.get("distance_from_bike") if nearest else None,
            "map_focus": map_focus,
            "conflicts": threat["conflicts"],
            "pillars": pillars,
            "inners": inners,
        })

    alone_pillars = []
    for target in captured_targets:
        key = target_position_key(target)
        if not key or key in assigned_keys:
            continue
        item = territory_control_object_payload(
            username, target, "alone", origin=origin, profile=profile, cluster_id=None
        )
        if item:
            item.pop("cluster_id", None)
            alone_pillars.append(item)

    clusters.sort(key=lambda item: (item.get("distance_from_bike") is None, item.get("distance_from_bike") or 10**12, item.get("cluster_id")))
    alone_pillars.sort(key=lambda item: (item.get("distance_from_bike") is None, item.get("distance_from_bike") or 10**12, item.get("label") or ""))
    return {
        "scope": "territory_control",
        "position": origin,
        "cluster_count": len(clusters),
        "alone_count": len(alone_pillars),
        "clusters": clusters,
        "alone_pillars": alone_pillars,
    }


def territory_control_find_cluster(snapshot, cluster_id):
    cluster_id = str(cluster_id or "").strip()
    for cluster in (snapshot or {}).get("clusters") or []:
        if str(cluster.get("cluster_id") or "") == cluster_id:
            return cluster
    return None


def territory_control_find_owned_target(username, lat, lng, label=None):
    for target in territory_store.list_captured_targets(username):
        if not targets_share_position(target, {"lat": lat, "lng": lng}):
            continue
        if label and str(target.get("label") or target.get("name") or "") != str(label):
            continue
        return target
    return None


def territory_control_object_snapshot(username, target, profile=None):
    snapshot = build_territory_control_snapshot(username, profile=profile)
    target_id = territory_control_target_id(target)
    for cluster in (snapshot or {}).get("clusters") or []:
        for item in (cluster.get("pillars") or []) + (cluster.get("inners") or []):
            if item.get("target_id") == target_id or targets_share_position(item, target):
                return item, snapshot
    for item in (snapshot or {}).get("alone_pillars") or []:
        if item.get("target_id") == target_id or targets_share_position(item, target):
            return item, snapshot
    return None, snapshot


def ensure_dev_admin_account():
    profile = user_store.get_profile("admin")
    if not profile:
        profile = resources_store.get("user_template", default={}) or {}
        profile["username"] = "admin"
        profile["avatar"] = profile.get("avatar") or "/static/images/default_avatar.png"
        profile["nick"] = profile.get("nick") or "DevAdmin"
        profile["level"] = max(int(profile.get("level", 1) or 1), 50)
        profile["hackcoins"] = max(int(profile.get("hackcoins", 0) or 0), 100000)
        profile["respect"] = max(int(profile.get("respect", 0) or 0), 1000)
        profile["clan"] = profile.get("clan") or "DEV"
        profile["curently_possition"] = profile.get("curently_possition") or {"lat": 52.2297, "lng": 21.0122}
        profile["inventory"] = profile.get("inventory") or []
        profile["files"] = profile.get("files") or {"download": [], "pictures": [], "social-media": [], "projects": [], "tools": []}

    profile["username"] = "admin"
    profile["password"] = "1234"
    profile["salt"] = profile.get("salt") or "dev_salt"
    profile["dev_account"] = True
    profile["level"] = max(int(profile.get("level", 1) or 1), 50)
    profile["hackcoins"] = max(int(profile.get("hackcoins", 0) or 0), 100000)
    profile["respect"] = max(int(profile.get("respect", 0) or 0), 1000)
    ensure_files_inventory(profile)
    user_store.save_profile(profile)
    return profile


def build_minimal_target_security(security_template, max_enabled=VULNERABILITY_MAX_ENABLED_SECURITY):
    bool_keys = [
        key for key, value in (security_template or {}).items()
        if isinstance(value, bool)
    ]
    enabled_keys = set(sample(bool_keys, min(max_enabled, len(bool_keys)))) if bool_keys else set()
    security = {}

    for key, value in (security_template or {}).items():
        if isinstance(value, bool):
            security[key] = key in enabled_keys
        elif isinstance(value, int):
            security[key] = 0
        else:
            security[key] = value

    return security


def normalize_key_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def extract_app_unlock_keys(app):
    unlock_keys = set()
    for field in ("interferes_with", "disables", "affects"):
        unlock_keys.update(normalize_key_list((app or {}).get(field)))

    effect = (app or {}).get("effect")
    if isinstance(effect, dict):
        unlock_keys.update(
            key for key, value in effect.items()
            if value is False
        )

    for level in (app or {}).get("levels", []) or []:
        if not isinstance(level, dict):
            continue
        for option in level.get("options", []) or []:
            if not isinstance(option, dict):
                continue
            option_effect = option.get("effect", {})
            if isinstance(option_effect, dict):
                unlock_keys.update(
                    key for key, value in option_effect.items()
                    if value is False
                )

    return unlock_keys


def calculate_player_unlock_potential(profile, target_security):
    active_security_keys = {
        key for key, value in (target_security or {}).items()
        if value is True
    }
    unlock_keys = set()
    app_breakdown = []

    for app in (profile or {}).get("apps", []) or []:
        app_keys = extract_app_unlock_keys(app)
        relevant_keys = sorted(app_keys & active_security_keys)
        unlock_keys.update(app_keys)
        if app_keys:
            app_breakdown.append({
                "id": app.get("id"),
                "name": app.get("name"),
                "unlock_keys": sorted(app_keys),
                "relevant_keys": relevant_keys,
            })

    covered_keys = active_security_keys & unlock_keys
    total = len(active_security_keys)
    coverage = (len(covered_keys) / total) if total else 1.0

    return {
        "can_report": coverage >= VULNERABILITY_REPORT_THRESHOLD,
        "coverage": round(coverage, 4),
        "coverage_percent": round(coverage * 100, 2),
        "threshold": VULNERABILITY_REPORT_THRESHOLD,
        "threshold_percent": round(VULNERABILITY_REPORT_THRESHOLD * 100, 2),
        "active_security_keys": sorted(active_security_keys),
        "covered_keys": sorted(covered_keys),
        "missing_keys": sorted(active_security_keys - covered_keys),
        "unlock_keys": sorted(unlock_keys),
        "apps": app_breakdown,
    }


def resolve_target_security_for_vulnerability_check(profile, payload):
    payload = payload or {}
    target_security = payload.get("security")
    if isinstance(target_security, dict):
        return target_security

    target = payload.get("target") or payload
    if isinstance(target, dict) and isinstance(target.get("security"), dict):
        return target["security"]

    aimed = (profile or {}).get("aimed_target") or {}
    try:
        same_target = (
            round(float(aimed.get("lat")), 5) == round(float(target.get("lat")), 5)
            and round(float(aimed.get("lng", aimed.get("lon"))), 5) == round(float(target.get("lng", target.get("lon"))), 5)
            and (not target.get("label") or aimed.get("label") == target.get("label"))
        )
    except (TypeError, ValueError):
        same_target = False

    if same_target and isinstance(aimed.get("security"), dict):
        return aimed["security"]

    security_template = resources_store.get("user_security", default={})
    return build_minimal_target_security(security_template)


def summarize_areas(areas):
    return sum(float(area.get("area_size") or 0) for area in areas)


def calculate_area_perimeter(vertices):
    if len(vertices or []) < 2:
        return 0

    perimeter = 0
    for index, vertex in enumerate(vertices):
        next_vertex = vertices[(index + 1) % len(vertices)]
        perimeter += Haversine.haversine_distance(
            float(vertex.get("lat")),
            float(vertex.get("lng")),
            float(next_vertex.get("lat")),
            float(next_vertex.get("lng"))
        )
    return perimeter


def summarize_territory_metrics(areas, level):
    total_area = summarize_areas(areas)
    total_perimeter = 0
    edges_count = 0

    for area in areas:
        vertices = area.get("vertices", [])
        edges_count += len(vertices)
        total_perimeter += calculate_area_perimeter(vertices)

    spans_per_100m = edges_count / max(total_perimeter / 100, 1)
    density_multiplier = spans_per_100m * max(1, level) * 0.1
    density_multiplier = max(0.05, min(1.0, density_multiplier))
    effective_area = total_area * density_multiplier

    return {
        "total_area": total_area,
        "total_perimeter": total_perimeter,
        "edges_count": edges_count,
        "span_density": spans_per_100m,
        "density_multiplier": density_multiplier,
        "effective_area": effective_area
    }


def calculate_respect_gain(effective_gain):
    if effective_gain <= 0:
        return 0
    return max(1, min(25, round(effective_gain / 2000)))


def apply_territory_progression(profile, areas):
    stats = dict(profile.get("territory_stats") or {})
    legacy_stats = "effective_area" not in stats
    previous_area = float(stats.get("total_area") or 0)
    level = get_player_level(profile)
    metrics = summarize_territory_metrics(areas, level)
    total_area = metrics["total_area"]
    effective_area = metrics["effective_area"]
    previous_effective_area = effective_area if legacy_stats else float(stats.get("effective_area") or 0)
    area_gain = max(0, total_area - previous_area)
    effective_gain = max(0, effective_area - previous_effective_area)
    respect_gain = calculate_respect_gain(effective_gain)
    levels_gained = 0

    baseline = float(stats.get("area_baseline") or 0)
    if legacy_stats or baseline <= 0 or baseline > max(effective_area * 3, 1):
        baseline = effective_area
    elif effective_area > previous_effective_area:
        while baseline > 0 and effective_area >= baseline * 1.10 and levels_gained < 1:
            level += 1
            levels_gained += 1
            baseline = baseline * 1.10

    next_level_area = baseline * 1.10 if baseline > 0 else 0
    area_to_next = max(0, next_level_area - effective_area)

    stats.update({
        "total_area": round(total_area, 2),
        "effective_area": round(effective_area, 2),
        "area_baseline": round(baseline, 2),
        "next_level_area": round(next_level_area, 2),
        "area_to_next_level": round(area_to_next, 2),
        "clusters_count": len(areas),
        "captured_targets_count": len(profile.get("hacked", [])),
        "last_area_gain": round(area_gain, 2),
        "last_effective_gain": round(effective_gain, 2),
        "total_perimeter": round(metrics["total_perimeter"], 2),
        "edges_count": metrics["edges_count"],
        "span_density": round(metrics["span_density"], 4),
        "density_multiplier": round(metrics["density_multiplier"], 4),
    })

    profile["territory_stats"] = stats
    profile["level"] = level
    profile["respect"] = int(profile.get("respect", 0) or 0) + respect_gain
    profile["exp"] = f"{round(total_area, 2)} m²"

    messages = profile.get("system_messages", [])
    if respect_gain:
        messages.append({
            "type": "success",
            "title": "Respect za terytorium",
            "text": f"Twoja sieć powiększyła się o {round(area_gain)} m². +{respect_gain} respect.",
            "status": "new"
        })
        messages[-1]["text"] = f"Twoja sieć powiększyła się o {round(effective_gain)} m² efektywnej kontroli. +{respect_gain} respect."
    if levels_gained:
        messages.append({
            "type": "success",
            "title": "Awans poziomu",
            "text": f"Rozszerzyłeś terytorium o kolejne 10%. Nowy level: {level}.",
            "status": "new"
        })
    profile["system_messages"] = messages
    profile["exp"] = f"{round(effective_area, 2)} m² efektywne"

    return {
        "area_gain": round(area_gain, 2),
        "effective_gain": round(effective_gain, 2),
        "respect_gain": respect_gain,
        "levels_gained": levels_gained,
        "level": level,
        "total_area": round(total_area, 2),
        "effective_area": round(effective_area, 2),
        "next_level_area": round(next_level_area, 2),
    }


def refresh_territory_stats_snapshot(profile, areas):
    stats = dict(profile.get("territory_stats") or {})
    legacy_stats = "effective_area" not in stats
    level = get_player_level(profile)
    metrics = summarize_territory_metrics(areas, level)
    total_area = metrics["total_area"]
    effective_area = metrics["effective_area"]
    baseline = float(stats.get("area_baseline") or 0)
    if (legacy_stats or baseline <= 0 or baseline > max(effective_area * 3, 1)) and effective_area > 0:
        baseline = effective_area
    next_level_area = baseline * 1.10 if baseline > 0 else 0
    area_to_next = max(0, next_level_area - effective_area)

    stats.update({
        "total_area": round(total_area, 2),
        "effective_area": round(effective_area, 2),
        "area_baseline": round(baseline, 2),
        "next_level_area": round(next_level_area, 2),
        "area_to_next_level": round(area_to_next, 2),
        "clusters_count": len(areas),
        "captured_targets_count": len(profile.get("hacked", [])),
        "last_area_gain": float(stats.get("last_area_gain") or 0),
        "last_effective_gain": float(stats.get("last_effective_gain") or 0),
        "total_perimeter": round(metrics["total_perimeter"], 2),
        "edges_count": metrics["edges_count"],
        "span_density": round(metrics["span_density"], 4),
        "density_multiplier": round(metrics["density_multiplier"], 4),
    })
    profile["territory_stats"] = stats
    profile["exp"] = f"{round(total_area, 2)} m²"
    profile["exp"] = f"{round(effective_area, 2)} m² efektywne"
    return profile


def refresh_stale_territory_polygons(areas):
    now = datetime.utcnow().timestamp()
    owners = {
        area.get("owner_username")
        for area in areas
        if area.get("owner_username")
    }

    refreshed = False
    for owner in owners:
        owner_areas = [area for area in areas if area.get("owner_username") == owner]
        captured_count = len(territory_store.list_captured_targets(owner, stationary=True))
        if captured_count < 3:
            continue

        cached_at = TERRITORY_REBUILD_CACHE.get(owner, 0)
        if now - cached_at < TERRITORY_REBUILD_CACHE_SECONDS:
            continue

        triangle_areas = sum(1 for area in owner_areas if len(area.get("vertices", [])) == 3)
        looks_fragmented = len(owner_areas) > 1 and triangle_areas == len(owner_areas)
        stored_vertices_count = sum(len(area.get("vertices", [])) for area in owner_areas)
        looks_convex_trimmed = stored_vertices_count < captured_count
        first_rebuild_for_process = owner not in TERRITORY_REBUILD_CACHE
        if not first_rebuild_for_process and not looks_fragmented and not looks_convex_trimmed:
            continue

        owner_profile = user_store.get_profile(owner) or {}
        rebuild_player_areas_with_territory_delta(
            owner,
            owner_profile.get("level", 1),
            reason="stale_territory_polygon_refresh",
        )
        TERRITORY_REBUILD_CACHE[owner] = now
        refreshed = True

    return refreshed


def slugify_app_name(name):
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower()).strip("_")
    return slug or "app"


def parse_csv_field(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def parse_lines_field(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [line.strip() for line in str(value or "").splitlines() if line.strip()]


def parse_scalar(value):
    text = str(value).strip()
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def parse_effect_field(value):
    effect = {}
    for chunk in str(value or "").replace("\n", ",").split(","):
        if "=" not in chunk:
            continue
        key, raw_value = chunk.split("=", 1)
        key = key.strip()
        if key:
            effect[key] = parse_scalar(raw_value)
    return effect


def parse_button_lines(value):
    buttons = []
    for line in parse_lines_field(value):
        if "|" in line:
            label, action = line.split("|", 1)
        else:
            label = line
            action = slugify_app_name(line)
        label = label.strip()
        if label:
            buttons.append({"label": label, "action": action.strip() or slugify_app_name(label)})
    return buttons


def parse_option_lines(value):
    options = []
    for index, line in enumerate(parse_lines_field(value)):
        parts = [part.strip() for part in line.split("|")]
        label = parts[0] if parts else ""
        if not label:
            continue
        effect = parse_effect_field(parts[1] if len(parts) > 1 else "")
        option = {
            "id": index,
            "label": label,
            "effect": effect
        }
        if len(parts) > 2 and parts[2]:
            option["price"] = int(parse_scalar(parts[2]))
        options.append(option)
    return options


CREATOR_EXPLICIT_TOOL_FAMILIES = {"scanner_recon", "exploit", "sniffer"}


def build_generated_app(data, creator_username, creator_nick):
    name = str(data.get("name", "")).strip()
    if not name:
        raise ValueError("Brak nazwy aplikacji.")
    if ";" in name:
        raise ValueError("Nazwa aplikacji nie moze zawierac srednika (;).")

    interface = data.get("interface", "progressbar_random")
    if interface not in {"progressbar_random", "window", "terminal", "button_choices"}:
        raise ValueError("Nieprawidlowy interface aplikacji.")

    slug = slugify_app_name(name)
    app_id = f"user_{creator_username}_{slug}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    description = str(data.get("description", "")).strip() or "Aplikacja wygenerowana przez gracza."
    price = max(0, int(data.get("price") or 0))
    app_type = str(data.get("type", "custom")).strip() or "custom"
    detects = parse_csv_field(data.get("detects"))
    requires_off = parse_csv_field(data.get("requires_off"))
    interferes_with = parse_csv_field(data.get("interferes_with"))
    disables = parse_csv_field(data.get("disables"))
    map_actions = parse_csv_field(data.get("map_actions"))
    operation_types = parse_csv_field(data.get("operation_types"))
    resource_types = parse_csv_field(data.get("resource_types"))
    target_types = parse_csv_field(data.get("target_types"))
    tool_family = str(data.get("tool_family") or "").strip()
    tool_mode = str(data.get("tool_mode") or data.get("scanner_mode") or "").strip()
    if tool_family not in CREATOR_EXPLICIT_TOOL_FAMILIES:
        tool_mode = ""
    scanner_mode = tool_mode if tool_family == "scanner_recon" else ""

    app = {
        "id": app_id,
        "name": name,
        "icon": data.get("icon") or "\U0001F6E0\uFE0F",
        "type": app_type,
        "detects": detects,
        "interferes_with": interferes_with,
        "requires_off": requires_off,
        "price": price,
        "allowed_fractions": [],
        "disables": disables,
        "affects": parse_csv_field(data.get("affects")),
        "description": description,
        "interface": interface,
        "levels": [],
        "creator_username": creator_username,
        "creator_nick": creator_nick,
        "generated": True,
        "published": True,
        "downloads": 0,
        "project_file": f"{name}.sh",
        "created_at": datetime.utcnow().isoformat(timespec="seconds"),
    }
    if tool_family:
        app["tool_family"] = tool_family
    if tool_mode:
        app["tool_mode"] = tool_mode
    if scanner_mode:
        app["scanner_mode"] = scanner_mode
    if map_actions:
        app["map_actions"] = map_actions
        app["map_actions_source"] = "creator_explicit"
    elif tool_family in CREATOR_EXPLICIT_TOOL_FAMILIES:
        app["map_actions"] = []
        app["map_actions_source"] = "creator_explicit"
    if operation_types:
        app["operation_types"] = operation_types
    if resource_types:
        app["resource_types"] = resource_types
    if target_types:
        app["target_types"] = target_types

    creator_profile = user_store.get_profile(creator_username) or {}
    app.update(build_generated_app_quality_fields(creator_profile, app))
    app = normalize_app_contract(app, infer_legacy=tool_family not in CREATOR_EXPLICIT_TOOL_FAMILIES)
    normalize_app_storage_fields(app)
    normalize_app_quality_fields(app)
    enforce_generated_app_price_floor(app)

    level_title = str(data.get("level_title") or f"{name} - panel").strip()

    if interface == "window":
        buttons = parse_button_lines(data.get("window_buttons")) or [
            {"label": "Uruchom modul", "action": "run_generated"}
        ]
        app["levels"] = [{
            "title": level_title,
            "list": parse_lines_field(data.get("window_list")) or [
                "Modul zaladowany.",
                f"Celuje w: {', '.join(interferes_with) or 'brak parametrow'}",
                f"Wymaga OFF: {', '.join(requires_off) or 'brak'}",
            ],
            "buttons": buttons,
        }]
    elif interface == "terminal":
        terminal_levels = data.get("terminal_levels")
        if isinstance(terminal_levels, list) and terminal_levels:
            app["levels"] = [
                {
                    "command": str(level.get("command") or f"./{slug}.sh --target current").strip(),
                    "logs": parse_lines_field(level.get("logs")) or ["Raport zapisany."],
                }
                for level in terminal_levels
                if isinstance(level, dict)
            ]
        if not app["levels"]:
            app["levels"] = [{
                "command": str(data.get("terminal_command") or f"./{slug}.sh --target current").strip(),
                "logs": parse_lines_field(data.get("terminal_logs")) or [
                    "Laczenie z celem...",
                    "Analiza zabezpieczen...",
                    "Wysylanie ladunku...",
                    "Raport zapisany.",
                ],
            }]
    elif interface == "button_choices":
        options = parse_option_lines(data.get("button_options")) or [{
            "id": 0,
            "label": "Wykonaj",
            "effect": {key: False for key in interferes_with},
        }]
        app["levels"] = [{
            "title": level_title,
            "text": str(data.get("button_text") or description).strip(),
            "options": options,
        }]
    else:
        app["levels"] = [{
            "title": level_title,
            "steps": parse_lines_field(data.get("progress_steps")) or [
                "Inicjalizacja modulu...",
                "Sprawdzanie wymagan celu...",
                "Omijanie zabezpieczen...",
                "Finalizacja operacji...",
            ],
            "result_success": str(data.get("result_success") or "Operacja zakonczona powodzeniem.").strip(),
            "result_failure": str(data.get("result_failure") or "Operacja zablokowana przez zabezpieczenia celu.").strip(),
        }]

    return app


ensure_profile_template_projects_folder()



app.config.update(FLASK_SESSION_CONFIG)

Session(app)


def normalize_runtime_profile_defaults(profile):
    if not isinstance(profile, dict):
        return profile

    for key in ("own_places", "captured_targets", "territory", "areas"):
        if not isinstance(profile.get(key), list):
            profile[key] = []
    reconcile_googleplex_storage_products(profile)
    normalize_profile_storage(profile)
    return profile


def profile_template_payload(profile):
    if not isinstance(profile, dict):
        return {}

    template = resources_store.get("user_template", default={}) or {}
    if not isinstance(template, dict) or not template:
        payload = dict(profile)
    else:
        payload = {
            key: copy.deepcopy(profile[key]) if key in profile else copy.deepcopy(default_value)
            for key, default_value in template.items()
        }

    payload.pop("password", None)
    payload.pop("salt", None)
    normalize_profile_storage(payload)
    return payload


def log_missing_profile_warning(source):
    print(
        "[WARN] missing profile "
        f"source={source} user={session.get('user') or '-'} "
        f"path={request.path if request else '-'} "
        f"referer={request.headers.get('Referer', '-') if request else '-'}",
        flush=True,
    )


def redirect_missing_profile_to_login():
    message = "Brak danych profilu. Zaloguj sie ponownie albo skontaktuj sie z administratorem."
    log_missing_profile_warning("map_view")
    session.pop("user", None)
    session.pop("profile", None)
    session["login_error"] = message
    return redirect(url_for("index"))


def sync_session_profile(rebuild_territory=True):
    username = session.get("user")
    if not username:
        return None

    if not rebuild_territory:
        profile = user_store.get_profile(username)
        if not profile:
            return None
        profile = dict(profile)
        profile.pop("password", None)
        profile.pop("salt", None)
        profile["apps"] = normalize_app_contracts(profile.get("apps", []))
        normalize_files_inventory(profile)
        normalize_runtime_profile_defaults(profile)
        apply_runtime_stores_to_profile(username, profile)
        UserProfileManager(username).update_profile({
            "storage_capacity": profile.get("storage_capacity"),
            "storage_used": profile.get("storage_used"),
            "storage_unit": profile.get("storage_unit", "MB"),
            "storage_soft_limit": True,
            "storage_over_limit": profile.get("storage_over_limit", False),
            "storage_upgrades": profile.get("storage_upgrades", []),
            "googleplex_products": profile.get("googleplex_products", []),
            "product_purchases": profile.get("product_purchases", []),
        })
        session["profile"] = profile
        return profile

    try:
        mgr = UserProfileManager(username)
    except ValueError:
        log_missing_profile_warning("sync_session_profile")
        return None
    profile = mgr.get_profile(strip_sensitive=True)
    if not isinstance(profile, dict):
        log_missing_profile_warning("sync_session_profile")
        return None
    profile["apps"] = normalize_app_contracts(profile.get("apps", []))
    normalize_files_inventory(profile)
    normalize_runtime_profile_defaults(profile)
    apply_runtime_stores_to_profile(username, profile)
    normalized_clan = get_profile_clan(profile)
    if normalized_clan and normalized_clan != profile.get("clan"):
        profile["clan"] = normalized_clan
    if isinstance(profile.get("fraction"), dict):
        fraction_name = str(profile["fraction"].get("name") or "").strip()
        mapped_fraction_name = FACTION_NAMES.get(fraction_name, fraction_name)
        if mapped_fraction_name and mapped_fraction_name != fraction_name:
            profile["fraction"]["id"] = fraction_name
            profile["fraction"]["name"] = mapped_fraction_name
    merge_captured_targets_into_profile(username, profile)
    areas = rebuild_player_areas_with_territory_delta(
        username,
        profile.get("level", 1),
        reason="sync_session_profile",
    )
    refresh_territory_stats_snapshot(profile, areas)
    mgr.update_profile({
        "clan": profile.get("clan", ""),
        "fraction": profile.get("fraction", {}),
        "hacked": profile.get("hacked", []),
        "captured_targets_source": profile.get("captured_targets_source", "sqlite"),
        "territory_stats": profile["territory_stats"],
        "exp": profile["exp"],
        "apps": profile.get("apps", []),
        "storage_capacity": profile.get("storage_capacity"),
        "storage_used": profile.get("storage_used"),
        "storage_unit": profile.get("storage_unit", "MB"),
        "storage_soft_limit": True,
        "storage_over_limit": profile.get("storage_over_limit", False),
        "storage_upgrades": profile.get("storage_upgrades", []),
        "googleplex_products": profile.get("googleplex_products", []),
        "product_purchases": profile.get("product_purchases", []),
    })
    notify_encircled_area_owners()
    session["profile"] = profile
    return profile


def merge_captured_targets_into_profile(username, profile):
    store_targets = territory_store.list_captured_targets(username)
    source = profile.get("captured_targets_source")

    if source == "sqlite" or store_targets:
        changed = profile.get("hacked", []) != store_targets or source != "sqlite"
        profile["hacked"] = store_targets
        profile["captured_targets_source"] = "sqlite"
        return changed

    legacy_targets = [
        target for target in (profile.get("hacked") or [])
        if isinstance(target, dict)
        and target.get("lat") is not None
        and (target.get("lng") is not None or target.get("lon") is not None)
    ]
    if legacy_targets:
        profile["hacked"] = legacy_targets
        territory_store.sync_profile_hacked_targets(username, profile)
        profile["hacked"] = territory_store.list_captured_targets(username)
    else:
        profile["hacked"] = []

    profile["captured_targets_source"] = "sqlite"
    return True

def set_profile_session():
    username = session.get("user")
    if not username:
        return None

    mgr = UserProfileManager(username)
    profile = mgr.get_profile(strip_sensitive=True)
    session["profile"] = profile



def get_apps_for_action(apps, action):
    def has_any(value_list, keywords):
        return any(v in value_list for v in keywords)

    if action == "scan_ports":
        return [app for app in apps if app.get("type") == "scanner" and has_any(app.get("detects", []), ["open_ports"])]

    elif action == "exploit":
        return [app for app in apps if app.get("type") == "exploit"]

    elif action == "sniff":
        return [app for app in apps if app.get("type") in ["scanner", "os_component"] and has_any(app.get("detects", []), ["processes", "active_tasks", "security_logs"])]

    elif action == "trace":
        return [app for app in apps if has_any(app.get("detects", []), ["user_location", "device_presence", "ip_leaks"])]

    # 🆕 Specjalne akcje
    elif action == "camera_stream":
        return [app for app in apps if has_any(app.get("detects", []), ["camera_feed", "video_stream"])]

    elif action == "camera_shutdown":
        return [app for app in apps if has_any(app.get("interferes_with", []), ["camera"])]

    elif action == "mic_sniff":
        return [app for app in apps if has_any(app.get("detects", []), ["microphone_activity", "audio_stream"])]

    elif action == "trace_device":
        return [app for app in apps if has_any(app.get("detects", []), ["bluetooth_device", "device_location"])]

    elif action == "car_hack":
        return [app for app in apps if has_any(app.get("interferes_with", []), ["vehicle_ecu", "car_system", "gps_tracker"])]

    elif action == "trace_gps":
        return [app for app in apps if has_any(app.get("detects", []), ["gps_location", "car_signal"])]

    elif action == "atm_logs":
        return [app for app in apps if has_any(app.get("detects", []), ["atm_logs", "financial_data"])]

    elif action == "install_sniffer":
        return [app for app in apps if app.get("type") == "sniffer" or has_any(app.get("effects", []), ["network_capture"])]

    elif action == "scan_hotspots":
        return [app for app in apps if has_any(app.get("detects", []), ["wifi", "ssid", "access_points"])]

    elif action == "audio_hack":
        return [app for app in apps if has_any(app.get("interferes_with", []), ["speaker", "audio_output"])]

    # fallback
    else:
        return []

def is_username_taken(username):
    mgr = UserProfileManager("admin")
    return any(u["username"] == username for u in mgr.all_users)

def is_public_ip(ip):
    try:
        parsed = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return not (
        parsed.is_private
        or parsed.is_loopback
        or parsed.is_reserved
        or parsed.is_link_local
        or parsed.is_multicast
        or parsed.is_unspecified
    )


def get_request_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    for value in forwarded.split(","):
        ip = value.strip()
        if ip and is_public_ip(ip):
            return ip

    for header in ["CF-Connecting-IP", "X-Real-IP"]:
        ip = (request.headers.get(header) or "").strip()
        if ip and is_public_ip(ip):
            return ip

    ip = (request.remote_addr or "").strip()
    return ip if is_public_ip(ip) else ""


def fallback_start_city():
    city = choice(START_CITY_FALLBACKS)
    return {
        "city": city["city"],
        "lat": city["lat"],
        "lng": city["lng"],
        "source": "fallback_city"
    }


def get_start_location_by_ip(ip):
    if not ip:
        return fallback_start_city()

    try:
        response = requests.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,message,country,regionName,city,lat,lon,query"},
            timeout=2.5
        )
        data = response.json()
        if response.ok and data.get("status") == "success" and data.get("lat") is not None and data.get("lon") is not None:
            return {
                "city": data.get("city") or data.get("regionName") or data.get("country") or "Unknown",
                "lat": float(data["lat"]),
                "lng": float(data["lon"]),
                "source": "ip",
                "ip": data.get("query") or ip
            }
    except requests.RequestException:
        pass
    except (TypeError, ValueError):
        pass

    return fallback_start_city()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin":
            ensure_dev_admin_account()

        if authenticate_user(username, password):
            session["user"] = username
            set_profile_session()
            return redirect(url_for("desktop"))

        return render_template("login.html", error="❌ Nieprawidłowe dane logowania")

    return render_template("login.html", error=session.pop("login_error", None))

@app.route("/register")
def register_page():
    return render_template("register.html")


USERNAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{2,23}$")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,}$")


def validate_registration_username(username):
    username = str(username or "").strip()
    if not USERNAME_RE.match(username):
        return None, "Login musi miec 3-24 znaki i moze zawierac litery, cyfry, _, . albo -."
    return username, ""


def validate_registration_email(email):
    email = str(email or "").strip().lower()
    if len(email) > 254 or not EMAIL_RE.match(email):
        return None, "Podaj poprawny adres e-mail."
    return email, ""


def validate_registration_password(password):
    password = str(password or "")
    if len(password) < 8:
        return "Haslo musi miec co najmniej 8 znakow."
    if len(password) > 128:
        return "Haslo jest zbyt dlugie."
    if not re.search(r"[A-Za-z]", password):
        return "Haslo musi zawierac przynajmniej jedna litere."
    if not re.search(r"\d", password):
        return "Haslo musi zawierac przynajmniej jedna cyfre."
    return ""


def validate_registration_nick(nick):
    nick = str(nick or "").strip()
    if len(nick) < 2 or len(nick) > 32:
        return None, "Nick musi miec 2-32 znaki."
    return nick, ""


@app.route("/api/register-check", methods=["POST"])
def register_check_username():
    data = request.get_json(silent=True) or {}
    username = data.get("checking_username")
    type_data = data.get("type_data")

    if type_data == "user":
        username, error = validate_registration_username(username)
        if error:
            return jsonify(success=False, error=error)
        exists = user_store.username_exists(username)
        return jsonify(success=not exists, error="Login jest juz zajety." if exists else "")

    elif type_data == "email":
        email, error = validate_registration_email(username)
        if error:
            return jsonify(success=False, error=error)
        useremails = {str(u.get("email", "")).strip().lower() for u in user_store.list_profiles()}
        exists = email in useremails
        return jsonify(success=not exists, error="Ten adres e-mail jest juz zarejestrowany." if exists else "")

    return jsonify(success=False)


@app.route("/api/register-finalize", methods=["POST"])
def api_register_finalize():

    data = request.get_json(silent=True) or {}

    username, username_error = validate_registration_username(data.get("username"))
    password = str(data.get("password") or "")
    password_error = validate_registration_password(password)
    faction = data.get("faction")
    role = data.get("role")
    nick, nick_error = validate_registration_nick(data.get("nick"))
    email, email_error = validate_registration_email(data.get("email"))

    if not all([username, password, faction, role, nick, email]):
        return jsonify(success=False, error="Brakuje danych."), 400
    if username_error:
        return jsonify(success=False, error=username_error), 400
    if password_error:
        return jsonify(success=False, error=password_error), 400
    if nick_error:
        return jsonify(success=False, error=nick_error), 400
    if email_error:
        return jsonify(success=False, error=email_error), 400
    if user_store.username_exists(username):
        return jsonify(success=False, error="Login jest juz zajety."), 409
    useremails = {str(u.get("email", "")).strip().lower() for u in user_store.list_profiles()}
    if email in useremails:
        return jsonify(success=False, error="Ten adres e-mail jest juz zarejestrowany."), 409

    ip = get_request_ip()
    start_location = get_start_location_by_ip(ip)
    city = start_location["city"]
    lat = start_location["lat"]
    lng = start_location["lng"]
    avatar_path = f"/static/images/avatar-frakcja-{faction}-player-{role}.png"
    faction_name = FACTION_NAMES.get(str(faction), str(faction))

    try:
        mgr = UserProfileManager("admin")
        if not mgr.add_new_user(username, password):
            return jsonify(success=False, error="Użytkownik już istnieje.")

        mgr = UserProfileManager(username)
        mgr.update_profile({
            "avatar": avatar_path,
            "nick": str(nick),
            "email": str(email),
            "hackcoins": 1000,
            "curently_possition": {"lat": lat, "lng": lng},
            "clan": faction_name,
            "fraction": {"id": str(faction), "name": faction_name, "role": role}
        })

        session["user"] = username
        set_profile_session()
        return jsonify(success=True, redirect="/desktop")

    except Exception as e:
        return jsonify(success=False, error=str(e)), 400






@app.route("/desktop")
def desktop():
    user = session.get("user")
    if not user:
        return redirect(url_for("index"))

    profile = sync_session_profile()
    return render_template("linux.html", user=user, inventory=profile["inventory"], profile=profile)


def require_dev_admin():
    return session.get("user") == "admin"


def build_dev_state():
    profile = sync_session_profile()
    profiles = []
    for item in user_store.list_profiles():
        profiles.append({
            "username": item.get("username"),
            "nick": item.get("nick"),
            "clan": get_profile_clan(item),
            "level": item.get("level"),
            "hackcoins": item.get("hackcoins"),
            "respect": item.get("respect"),
            "position": item.get("curently_possition", {}),
            "targets": len(item.get("targets", []) or []),
            "hacked": len(item.get("hacked", []) or []),
        })

    return {
        "logged_as": session.get("user"),
        "profile": {
            "username": profile.get("username"),
            "nick": profile.get("nick"),
            "clan": get_profile_clan(profile),
            "level": profile.get("level"),
            "hackcoins": profile.get("hackcoins"),
            "respect": profile.get("respect"),
            "position": profile.get("curently_possition", {}),
            "territory_stats": profile.get("territory_stats", {}),
        },
        "users": profiles,
        "areas": territory_store.list_player_areas(),
        "vulnerabilities": vulnerability_store.list_active(),
    }


def redacted_profile(profile):
    data = copy_profile = dict(profile or {})
    copy_profile.pop("password", None)
    copy_profile.pop("salt", None)
    return data


def build_admin_user_snapshot(profile):
    profile = dict(profile or {})
    hacked = profile.get("hacked", []) or []
    apps = profile.get("apps", []) or []
    files = profile.get("files", {}) or {}
    tools = list(files.get("tools", []) or [])
    project_files = list(files.get("projects", []) or [])
    aimed_target = profile.get("aimed_target", {}) or {}

    return {
        "username": profile.get("username"),
        "nick": profile.get("nick"),
        "email": profile.get("email", ""),
        "clan": get_profile_clan(profile),
        "fraction": profile.get("fraction", {}),
        "level": profile.get("level"),
        "hackcoins": profile.get("hackcoins"),
        "respect": profile.get("respect"),
        "exp": profile.get("exp"),
        "position": profile.get("curently_possition", {}),
        "territory_stats": profile.get("territory_stats", {}),
        "aimed_target": aimed_target,
        "aimed_target_security": aimed_target.get("security", {}),
        "own_security": profile.get("security", {}),
        "apps": apps,
        "tools": tools,
        "projects": project_files,
        "targets": profile.get("targets", []) or [],
        "hacked_targets": hacked,
        "hacked_targets_security": [
            {
                "label": target.get("label"),
                "name": target.get("name"),
                "lat": target.get("lat"),
                "lng": target.get("lng"),
                "source_type": target.get("source_type"),
                "security": target.get("security", {}),
                "actions_allowed": target.get("actions_allowed", {}),
                "captured_at": target.get("captured_at"),
            }
            for target in hacked
        ],
        "system_messages": profile.get("system_messages", []) or [],
        "raw_profile": redacted_profile(profile),
    }


def build_admin_dashboard_state():
    users = [build_admin_user_snapshot(profile) for profile in user_store.list_profiles()]
    users.sort(key=lambda item: item.get("username") or "")
    return {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds"),
        "logged_as": session.get("user"),
        "users": users,
        "areas": territory_store.list_player_areas(),
        "vulnerabilities": vulnerability_store.list_active(),
    }


def render_json_block(data):
    return html.escape(json.dumps(data, ensure_ascii=False, indent=2), quote=False)


def render_admin_user_card(user):
    username = html.escape(str(user.get("username") or ""))
    nick = html.escape(str(user.get("nick") or ""))
    clan = html.escape(str(user.get("clan") or "brak"))
    aimed = user.get("aimed_target") or {}
    aimed_label = html.escape(str(aimed.get("label") or aimed.get("name") or "brak"))
    aimed_mode = html.escape(str(aimed.get("target_mode") or "standard"))
    apps_count = len(user.get("apps") or [])
    tools_count = len(user.get("tools") or [])
    hacked_count = len(user.get("hacked_targets") or [])
    own_security_on = sum(1 for value in (user.get("own_security") or {}).values() if value is True)
    target_security_on = sum(1 for value in (user.get("aimed_target_security") or {}).values() if value is True)

    return f"""
    <details class="user-card">
      <summary>
        <span class="user-main">{username}</span>
        <span>{nick}</span>
        <span>{clan}</span>
        <span>LVL {user.get("level")}</span>
        <span>HC {user.get("hackcoins")}</span>
      </summary>
      <div class="grid">
        <section>
          <h3>Celownik</h3>
          <p><b>Cel:</b> {aimed_label}</p>
          <p><b>Tryb:</b> {aimed_mode}</p>
          <p><b>Aktywne zabezpieczenia celu:</b> {target_security_on}</p>
          <pre>{render_json_block(aimed)}</pre>
        </section>
        <section>
          <h3>Narzędzia</h3>
          <p><b>Aplikacje:</b> {apps_count}</p>
          <p><b>Pliki tools:</b> {tools_count}</p>
          <pre>{render_json_block({"apps": user.get("apps", []), "tools": user.get("tools", []), "projects": user.get("projects", [])})}</pre>
        </section>
        <section>
          <h3>Security gracza</h3>
          <p><b>ON:</b> {own_security_on}</p>
          <pre>{render_json_block(user.get("own_security", {}))}</pre>
        </section>
        <section>
          <h3>Przejęte obiekty</h3>
          <p><b>Liczba:</b> {hacked_count}</p>
          <pre>{render_json_block(user.get("hacked_targets_security", []))}</pre>
        </section>
      </div>
      <details>
        <summary>Pełny profil operacyjny</summary>
        <pre>{render_json_block(user.get("raw_profile", {}))}</pre>
      </details>
    </details>
    """


@app.route("/api/dev/state")
def api_dev_state():
    if not require_dev_admin():
        return jsonify({"success": False, "message": "Dev state wymaga logowania jako admin."}), 403
    return jsonify({"success": True, "state": build_dev_state()})


@app.route("/api/state/changes")
def api_state_changes():
    recovery_scopes = ["wallet", "storage", "apps", "mail", "ghost_exchange", "map", "territory", "ghostnetwork"]
    username = session.get("user")
    if not username:
        return jsonify({
            "current_version": 0,
            "changes": [],
            "recovery_required": True,
            "reason": "not_logged_in",
            "recovery_scopes": recovery_scopes,
        }), 401

    result = delta_bus.get_changes_since(
        username,
        request.args.get("since", 0),
        request.args.get("limit", GameStateDeltaBus.DEFAULT_QUERY_LIMIT),
    )
    if result.get("recovery_required"):
        result["recovery_scopes"] = recovery_scopes
    return jsonify(result)


@app.route("/api/ghostnetwork/snapshot")
def api_ghostnetwork_snapshot():
    username = session.get("user")
    view = str(request.args.get("view") or "map").strip().lower()
    if not username:
        return jsonify({
            "ok": False,
            "error": "not_logged_in",
            "scope": "ghostnetwork",
            "view": view,
            "current_version": 0,
            "parts": [],
        }), 401

    profile = load_profile_readonly(
        username,
        strip_sensitive=True,
        normalize_apps=False,
        normalize_files=False,
    )
    if not profile:
        session.pop("user", None)
        session.pop("profile", None)
        return jsonify({
            "ok": False,
            "error": "profile_not_found",
            "scope": "ghostnetwork",
            "view": view,
            "current_version": 0,
            "parts": [],
        }), 401

    viewer = ghostnetwork_player_payload(username, profile)
    viewer.update({
        "viewer_id": username,
        "viewer_clan": viewer.get("clan_code") or "",
        "viewer_profession": viewer.get("ghost_profession") or profile.get("profession") or "",
        "audience_scope": "player",
        "is_authenticated": True,
    })

    try:
        projection = GhostNetworkService().get_snapshot_for_viewer(viewer)
    except Exception as exc:
        print(f"[ghostnetwork] snapshot failed user={username} error={exc}", flush=True)
        return jsonify({
            "ok": False,
            "error": "ghostnetwork_unavailable",
            "scope": "ghostnetwork",
            "view": view,
            "current_version": 0,
            "parts": [],
        }), 503

    projection = projection if isinstance(projection, dict) else {}
    if "parts" not in projection and isinstance(projection.get("snapshot"), dict):
        raw_snapshot = projection.get("snapshot") or {}
        projection = {
            **projection,
            "cycle": raw_snapshot.get("cycle"),
            "parts": raw_snapshot.get("parts") or [],
            "connections": raw_snapshot.get("connections") or [],
            "machines": raw_snapshot.get("machines") or [],
            "progress": raw_snapshot.get("progress") or {},
            "state_version": raw_snapshot.get("state_version") or 0,
        }
    projection = normalize_snapshot_view(projection, view=view)

    cycle = projection.get("cycle") if isinstance(projection.get("cycle"), dict) else {}
    try:
        current_version = int(projection.get("state_version") or cycle.get("state_version") or 0)
    except (TypeError, ValueError):
        current_version = 0

    return jsonify({
        "ok": True,
        "scope": "ghostnetwork",
        "view": projection.get("view") or view or "map",
        "current_version": current_version,
        **projection,
    })


def _ghostnetwork_archive_viewer():
    username = session.get("user")
    if not username:
        return None, None, (jsonify({"ok": False, "error": "not_logged_in", "scope": "ghostnetwork_archive"}), 401)
    profile = load_profile_readonly(
        username,
        strip_sensitive=True,
        normalize_apps=False,
        normalize_files=False,
    )
    if not profile:
        session.pop("user", None)
        session.pop("profile", None)
        return None, None, (jsonify({"ok": False, "error": "profile_not_found", "scope": "ghostnetwork_archive"}), 401)
    viewer = ghostnetwork_player_payload(username, profile)
    viewer["viewer_id"] = username
    return username, viewer, None


@app.route("/api/ghostnetwork/archive/signals")
def api_ghostnetwork_archive_signals():
    _username, _viewer, error_response = _ghostnetwork_archive_viewer()
    if error_response:
        return error_response
    try:
        limit = max(1, min(int(request.args.get("limit") or 50), 200))
    except (TypeError, ValueError):
        limit = 50
    return jsonify({
        "ok": True,
        "scope": "ghostnetwork_archive",
        "signals": GhostNetworkService().list_signal_archive(limit=limit),
    })


@app.route("/api/ghostnetwork/archive/signals/<signal_id>")
def api_ghostnetwork_archive_signal_detail(signal_id):
    _username, viewer, error_response = _ghostnetwork_archive_viewer()
    if error_response:
        return error_response
    include_private = str(request.args.get("private") or "").strip() in {"1", "true", "yes"}
    detail = GhostNetworkService().get_signal_archive_detail(signal_id, include_private=include_private)
    if not detail.get("ok"):
        return jsonify(detail), 404
    detail["viewer"] = {
        "viewer_id": (viewer or {}).get("viewer_id") or "",
        "clan_code": (viewer or {}).get("clan_code") or "",
    }
    return jsonify(detail)


@app.route("/api/ghostnetwork/archive/player")
def api_ghostnetwork_archive_player():
    username, _viewer, error_response = _ghostnetwork_archive_viewer()
    if error_response:
        return error_response
    try:
        limit = max(1, min(int(request.args.get("limit") or 50), 200))
    except (TypeError, ValueError):
        limit = 50
    return jsonify(GhostNetworkService().get_player_archive_history(username, limit=limit))


@app.route("/api/ghostnetwork/archive/clans")
def api_ghostnetwork_archive_clans():
    _username, _viewer, error_response = _ghostnetwork_archive_viewer()
    if error_response:
        return error_response
    try:
        limit = max(1, min(int(request.args.get("limit") or 100), 250))
    except (TypeError, ValueError):
        limit = 100
    return jsonify(GhostNetworkService().get_clan_archive_history(limit=limit))


@app.route("/api/ghostnetwork/archive/map")
def api_ghostnetwork_archive_map():
    _username, _viewer, error_response = _ghostnetwork_archive_viewer()
    if error_response:
        return error_response
    try:
        limit = max(1, min(int(request.args.get("limit") or 200), 1000))
    except (TypeError, ValueError):
        limit = 200
    signal_id = str(request.args.get("signal_id") or "").strip()
    return jsonify(GhostNetworkService().get_historical_map_layer(signal_id=signal_id, limit=limit))


@app.route("/api/ghostnetwork/archive/readiness")
def api_ghostnetwork_archive_readiness():
    _username, _viewer, error_response = _ghostnetwork_archive_viewer()
    if error_response:
        return error_response
    return jsonify(GhostNetworkService().get_archive_readiness_report())


@app.route("/api/dev/delta-diagnostics")
def api_dev_delta_diagnostics():
    if not require_dev_admin():
        return jsonify({"success": False, "message": "Delta diagnostics wymaga konta admin."}), 403

    username = session.get("user") or ""
    return jsonify({
        "success": True,
        "diagnostics": delta_bus.diagnostics(
            username,
            limit=request.args.get("limit", 25),
            pollers_active_count=request.args.get("pollers_active_count", 0),
            snapshot_recovery_count=request.args.get("snapshot_recovery_count", 0),
        )
    })


@app.route("/api/dev/response-network-safety")
def api_dev_response_network_safety():
    if not require_dev_admin():
        return jsonify({"success": False, "message": "Response Network safety wymaga konta admin."}), 403

    return jsonify(build_response_network_safety_snapshot(
        limit=request.args.get("limit", 25),
    ))


@app.route("/api/dev/territory-context/recovery")
def api_dev_territory_context_recovery():
    if not require_dev_admin():
        return jsonify({"success": False, "message": "Territory recovery wymaga konta admin."}), 403

    actor_username = request.args.get("actor_username") or session.get("user")
    try:
        if request.args.get("lat") is not None and request.args.get("lng") is not None:
            snapshot = territory_delta_publisher.recovery_snapshot_for_point(
                request.args.get("lat"),
                request.args.get("lng"),
                actor_username=actor_username,
            )
        elif all(request.args.get(name) is not None for name in ("min_lat", "min_lng", "max_lat", "max_lng")):
            snapshot = territory_delta_publisher.recovery_snapshot_for_bbox(
                request.args.get("min_lat"),
                request.args.get("min_lng"),
                request.args.get("max_lat"),
                request.args.get("max_lng"),
                actor_username=actor_username,
                limit=request.args.get("limit", 50),
            )
        else:
            return jsonify({
                "success": False,
                "message": "Podaj lat/lng albo min_lat/min_lng/max_lat/max_lng.",
            }), 400
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400

    delta_result = None
    if request.args.get("since") is not None:
        delta_result = delta_bus.get_changes_since(
            actor_username,
            request.args.get("since", 0),
            request.args.get("delta_limit", GameStateDeltaBus.DEFAULT_QUERY_LIMIT),
        )

    return jsonify({
        "success": True,
        "territory_recovery": snapshot,
        "delta_diagnostics": territory_delta_publisher.recovery_diagnostics(delta_result or {}),
    })


@app.route("/api/blacknet/world-facts")
def api_blacknet_world_facts():
    if not session.get("user"):
        return jsonify({
            "success": False,
            "message": "BlackNet world facts wymagaja aktywnej sesji.",
            "snapshot": None,
        }), 401
    snapshot = build_blacknet_world_facts_snapshot()
    return jsonify({
        "success": True,
        "snapshot": snapshot,
    })


@app.route("/api/blacknet/world-signals")
def api_blacknet_world_signals():
    if not session.get("user"):
        return jsonify({
            "success": False,
            "message": "BlackNet world signals wymagaja aktywnej sesji.",
            "snapshot": None,
        }), 401
    try:
        limit = int(request.args.get("limit") or BLACKNET_WORLD_SIGNALS_LIMIT)
    except (TypeError, ValueError):
        limit = BLACKNET_WORLD_SIGNALS_LIMIT
    limit = max(1, min(32, limit))
    exclude_ids = [
        item.strip()
        for item in str(request.args.get("exclude") or "").split(",")
        if item.strip()
    ]
    signal_snapshot = build_blacknet_world_signals(limit=limit, exclude_ids=exclude_ids)
    return jsonify({
        "success": True,
        "snapshot": signal_snapshot,
    })


@app.route("/api/blacknet/ollama/outbox/generate", methods=["POST"])
def api_blacknet_ollama_outbox_generate():
    if not require_dev_admin():
        return jsonify({
            "success": False,
            "message": "BlackNet Ollama outbox wymaga konta admin.",
        }), 403
    facts_snapshot = build_blacknet_world_facts_snapshot()
    signal_snapshot = build_blacknet_world_signals(facts_snapshot)
    package = build_blacknet_ollama_outbox(facts_snapshot, signal_snapshot)
    path = write_blacknet_ollama_outbox(package)
    return jsonify({
        "success": True,
        "digest_id": package.get("digest_id"),
        "status": package.get("status"),
        "validation": package.get("validation"),
        "path": path,
        "outbox": package,
    })


@app.route("/api/blacknet/ollama/outbox/latest")
def api_blacknet_ollama_outbox_latest():
    if not require_dev_admin():
        return jsonify({
            "success": False,
            "message": "BlackNet Ollama outbox wymaga konta admin.",
            "outbox": None,
        }), 403
    status = request.args.get("status", "ready")
    package = latest_blacknet_ollama_outbox(status=status)
    if not isinstance(package, dict):
        return jsonify({
            "success": False,
            "message": "Brak paczki BlackNet Ollama outbox.",
            "error": "outbox_not_found",
            "outbox": None,
        }), 404
    return jsonify({
        "success": True,
        "outbox": package,
    })


@app.route("/api/blacknet/ollama/outbox/<digest_id>")
def api_blacknet_ollama_outbox_get(digest_id):
    if not require_dev_admin():
        return jsonify({
            "success": False,
            "message": "BlackNet Ollama outbox wymaga konta admin.",
            "outbox": None,
        }), 403
    package = read_blacknet_ollama_outbox(digest_id)
    if not isinstance(package, dict):
        return jsonify({
            "success": False,
            "message": "Paczka BlackNet Ollama outbox nie istnieje.",
            "error": "outbox_not_found",
            "outbox": None,
        }), 404
    return jsonify({
        "success": True,
        "outbox": package,
    })


@app.route("/api/blacknet/ollama/outbox/<digest_id>/status", methods=["POST"])
def api_blacknet_ollama_outbox_status(digest_id):
    if not require_dev_admin():
        return jsonify({
            "success": False,
            "message": "Zmiana statusu BlackNet Ollama outbox wymaga konta admin.",
        }), 403
    payload = request.get_json(silent=True) or {}
    package, error = update_blacknet_ollama_outbox_status(
        digest_id,
        payload.get("status"),
        message=payload.get("message") or "",
    )
    if error == "not_found":
        return jsonify({
            "success": False,
            "message": "Paczka BlackNet Ollama outbox nie istnieje.",
            "error": error,
        }), 404
    if error:
        return jsonify({
            "success": False,
            "message": "Nie mozna zmienic statusu paczki BlackNet Ollama.",
            "error": error,
        }), 400
    return jsonify({
        "success": True,
        "digest_id": package.get("digest_id"),
        "status": package.get("status"),
        "outbox": package,
    })


@app.route("/api/blacknet/cta/teleport", methods=["POST"])
def api_blacknet_cta_teleport():
    username = session.get("user")
    if not username:
        return jsonify({
            "success": False,
            "message": "Teleport BlackNet wymaga aktywnej sesji.",
            "error": "not_logged_in",
        }), 401

    payload = request.get_json(silent=True) or {}
    hotspot_id = str(
        payload.get("hotspot_id")
        or payload.get("cta_target_id")
        or payload.get("target_id")
        or ""
    ).strip()
    label = str(payload.get("label") or payload.get("target_label") or "").strip()
    source = str(payload.get("source") or "blacknet").strip().lower()
    try:
        payload_lat = float(payload.get("lat"))
        payload_lng = float(payload.get("lng"))
    except (TypeError, ValueError):
        payload_lat = None
        payload_lng = None
    hotspot = BLACKNET_HOTSPOTS.get(hotspot_id)
    has_payload_position = (
        payload_lat is not None
        and payload_lng is not None
        and -90 <= payload_lat <= 90
        and -180 <= payload_lng <= 180
    )
    if hotspot:
        position = {
            "lat": float(hotspot["lat"]),
            "lng": float(hotspot["lng"]),
        }
        target_label = hotspot.get("label") or hotspot_id or label or "target"
        hotspot_payload = {
            "id": hotspot["id"],
            "label": hotspot["label"],
            "risk": hotspot.get("risk", ""),
        }
    elif has_payload_position:
        position = {
            "lat": payload_lat,
            "lng": payload_lng,
        }
        target_label = label or "target"
        hotspot_payload = None
    else:
        error_code = "unknown_hotspot" if hotspot_id else "unknown_target"
        return jsonify({
            "success": False,
            "message": "Cel teleportu BlackNet wygasl albo nie posiada wspolrzednych.",
            "error": error_code,
        }), 404

    profile = load_profile_readonly(username, strip_sensitive=False)
    if not isinstance(profile, dict):
        session.pop("user", None)
        session.pop("profile", None)
        return jsonify({
            "success": False,
            "message": "Profil nie istnieje.",
            "error": "profile_not_found",
        }), 401

    position_updates = normalize_profile_position_update(position, username=username, source=source or "blacknet")
    profile.update(position_updates)

    mgr = UserProfileManager(username)
    mgr.update_profile(position_updates)
    session["profile"] = profile

    intrusion_area = notify_area_intrusion(username, position["lat"], position["lng"])
    teleport_reason = "terminal_teleport" if source == "terminal" else "blacknet_teleport"
    record_map_player_actor_delta(
        username,
        profile,
        change_type="map.player_moved",
        reason=teleport_reason,
        intrusion_area=intrusion_area,
    )
    message_prefix = "Teleport wykonany" if source == "terminal" else "Teleport BlackNet wykonany"

    return jsonify({
        "success": True,
        "message": f"{message_prefix}: {target_label}.",
        "hotspot": hotspot_payload,
        "curently_possition": position_updates.get("curently_possition"),
        "current_position": position_updates.get("current_position"),
        "position_version": position_updates.get("position_version"),
        "position_updated_at": position_updates.get("position_updated_at"),
        "intrusion": bool(intrusion_area),
        "intrusion_area": {
            "id": intrusion_area.get("id"),
            "owner_username": intrusion_area.get("owner_username"),
            "owner_nick": intrusion_area.get("owner_nick"),
        } if intrusion_area else None,
    })


@app.route("/api/admin/dashboard")
def api_admin_dashboard():
    if not require_dev_admin():
        return jsonify({"success": False, "message": "Admin dashboard wymaga logowania jako admin."}), 403
    return jsonify({"success": True, "state": build_admin_dashboard_state()})


@app.route("/admin")
@app.route("/dev")
def dev_dashboard():
    if not session.get("user"):
        return redirect(url_for("index"))
    if not require_dev_admin():
        return jsonify({"success": False, "message": "Dev dashboard wymaga konta admin."}), 403

    state = build_admin_dashboard_state()
    user_cards = "\n".join(render_admin_user_card(user) for user in state["users"])
    areas_count = len(state.get("areas") or [])
    vulnerabilities_count = len(state.get("vulnerabilities") or [])
    return f"""
<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <title>GH0ST ADMIN</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; padding: 18px; background: #050805; color: #cfff92; font-family: Consolas, monospace; }}
    a {{ color: #7dff48; text-decoration: none; }}
    h1, h2, h3 {{ margin: 0 0 10px; color: #f0ffe4; }}
    p {{ margin: 5px 0; }}
    pre {{ white-space: pre-wrap; max-height: 360px; overflow: auto; background: #020402; border: 1px solid rgba(125,255,72,.45); padding: 12px; color: #dfffcf; }}
    .bar {{ display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }}
    .brand {{ font-size: 22px; font-weight: 800; letter-spacing: .08em; color: #b8ff28; }}
    .pill {{ border: 1px solid #1db954; padding: 6px 10px; background: rgba(29,185,84,.12); }}
    .stats {{ display: grid; grid-template-columns: repeat(4, minmax(150px, 1fr)); gap: 10px; margin-bottom: 16px; }}
    .stat {{ border: 1px solid rgba(125,255,72,.5); background: rgba(29,185,84,.08); padding: 12px; }}
    .user-card {{ border: 1px solid rgba(125,255,72,.55); background: rgba(0,0,0,.35); margin: 12px 0; }}
    .user-card > summary {{ cursor: pointer; display: grid; grid-template-columns: 1.2fr 1fr 1fr .6fr .7fr; gap: 10px; padding: 12px; background: rgba(29,185,84,.12); color: #eaffde; }}
    .user-main {{ color: #b8ff28; font-weight: 800; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(280px, 1fr)); gap: 12px; padding: 12px; }}
    section {{ border: 1px solid rgba(125,255,72,.28); padding: 12px; background: rgba(0,0,0,.25); }}
    details details {{ margin: 0 12px 12px; border-top: 1px solid rgba(125,255,72,.25); padding-top: 10px; }}
    @media (max-width: 900px) {{
      .stats, .grid, .user-card > summary {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="bar">
    <span class="brand">GH0ST ADMIN</span>
    <span class="pill">admin / 1234</span>
    <a href="/desktop">desktop</a>
    <a href="/api/admin/dashboard">api/admin/dashboard</a>
    <a href="/api/dev/state">api/dev/state</a>
  </div>
  <div class="stats">
    <div class="stat"><h3>Użytkownicy</h3><p>{len(state["users"])}</p></div>
    <div class="stat"><h3>Pola</h3><p>{areas_count}</p></div>
    <div class="stat"><h3>Podatności</h3><p>{vulnerabilities_count}</p></div>
    <div class="stat"><h3>Wygenerowano</h3><p>{html.escape(state["generated_at"])}</p></div>
  </div>
  <h2>Użytkownicy</h2>
  {user_cards}
  <h2>Terytoria</h2>
  <pre>{render_json_block(state.get("areas", []))}</pre>
  <h2>Podatności</h2>
  <pre>{render_json_block(state.get("vulnerabilities", []))}</pre>
</body>
</html>
"""



@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))



@app.route("/command", methods=["POST"])
def command():
    data = request.json
    user_input = data.get("input", "")
    flow_id = request.headers.get("X-Hack-Flow-Id", "")
    skip_map_runtime = bool(
        data.get("skip_map_runtime")
        or data.get("launch_queue")
        or data.get("source") == "launch_queue"
    )

    profile = sync_session_profile()
    user_apps = profile.get('apps', [])

    result = interpret_command(user_input, profile)

    if result.get("logout"):
        return jsonify({"logout": True, "response": "Wylogowywanie..."})

    if result.get("close_terminal"):
        return jsonify({
            "closeTerminal": True,
            "response": result.get("response", "Zamykanie terminala...")
        })

    if result.get("openSystemApp"):
        return jsonify({
            "openSystemApp": result.get("openSystemApp"),
            "response": result.get("response", "Otwieram...")
        })

    if result.get("clear"):
        return jsonify({"clear": True})

    if result.get("terminalTeleport"):
        return jsonify({
            "response": result.get("response", "Przygotowano teleport."),
            "terminalTeleport": result.get("terminalTeleport"),
        })

    if result.get("confirm_userdel"):
        username_to_delete = result["confirm_userdel"]
        return jsonify({
            "confirm": {
                "action": "userdel",
                "username": username_to_delete,
                "prompt": f"Usunąć konto '{username_to_delete}'? [Y/N]"
            }
        })

    # Zwykła odpowiedź terminala
    if "response" in result:
        return jsonify({"response": result["response"]})

    # Uruchamianie aplikacji
    if "runApp" in result:
        app_id = result.get("runApp")
        found_app = next((a for a in user_apps if a["id"] == app_id), None)
        if not found_app:
            return jsonify({"response": f"Nie znaleziono aplikacji o ID: {app_id}"})

        created_operations = []
        target_changed = False
        marked_actions = []
        if not skip_map_runtime:
            target_changed, marked_actions = apply_app_map_actions_to_aimed_target(profile, found_app, session.get("user"))
            if profile.get("aimed_target"):
                merge_latest_aimed_target_runtime_state(profile, session.get("user"))
                created_operations = create_missing_operations_for_app_target(
                    profile,
                    session.get("user"),
                    found_app,
                    profile.get("aimed_target") or {},
                )
        else:
            app_flow_debug(
                flow_id,
                "command_skip_map_runtime_for_launch_queue",
                user=session.get("user"),
                app_id=app_id,
                app_name=found_app.get("name"),
            )

        if target_changed or created_operations:
            UserProfileManager(session["user"]).update_profile({
                "aimed_target": profile.get("aimed_target", {}),
                "operations": profile.get("operations", []),
            })
            session["profile"] = profile
            if target_changed:
                record_map_target_delta(
                    session["user"],
                    profile.get("aimed_target") or {},
                    change_type="map.target_updated",
                    reason="app_launch_actions_allowed",
                )

        return jsonify({
            "runApp": True,
            "consoleEffect": f"Uruchamianie aplikacji {found_app['name']}...",
            "applicationId": app_id,
            "applicationEffect": found_app,
            "target": profile.get("aimed_target") if target_changed else None,
            "actions_allowed_marked": marked_actions,
            "created_operations": created_operations,
        })
    return jsonify({"response": f"❓ Nieznana komenda: {user_input}"})


@app.route("/api/users/delete", methods=["POST"])
def delete_user_account():
    if "user" not in session:
        return jsonify({"success": False, "message": "Nie jesteś zalogowany"}), 401

    current_user = session.get("user")
    data = request.get_json(silent=True) or {}
    username_to_delete = (data.get("username") or "").strip()
    if not username_to_delete:
        return jsonify({"success": False, "message": "Brak nazwy użytkownika."}), 400

    if username_to_delete == "admin":
        return jsonify({"success": False, "message": "Nie można usunąć konta admin."}), 400

    territory_store.delete_user_data(username_to_delete)
    deleted = user_store.delete_user(username_to_delete)
    if not deleted:
        return jsonify({"success": False, "message": f"Użytkownik '{username_to_delete}' nie istnieje."}), 404

    logout = username_to_delete == current_user
    if logout:
        session.clear()

    return jsonify({
        "success": True,
        "logout": logout,
        "redirect": url_for("index") if logout else None,
        "message": f"Usunięto konto '{username_to_delete}'."
    })

@app.route("/target-security-status", methods=["POST"])
def target_security_status():
    data = request.get_json(silent=True) or {}
    try:
        lat = float(data.get("lat"))
        lng = float(data.get("lng"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Brak poprawnych wspolrzednych celu."}), 400

    profile = sync_session_profile()
    found, hacked_list, added_from_store = find_owned_hacked_target(profile, session["user"], lat, lng)

    if not found:
        if profile.get("captured_targets_source") == "sqlite":
            UserProfileManager(session["user"]).update_profile({
                "hacked": hacked_list,
                "captured_targets_source": "sqlite",
            })
            session["profile"] = profile
        return jsonify({"success": False, "message": "Cel nie został jeszcze zhakowany"}), 404

    if added_from_store or profile.get("captured_targets_source") == "sqlite":
        UserProfileManager(session["user"]).update_profile({
            "hacked": hacked_list,
            "captured_targets_source": "sqlite",
        })
        session["profile"] = profile

    security = found.get("security", {})
    return jsonify({"success": True, "security": security})


def find_owned_hacked_target(profile, username, lat, lng):
    hacked_list = profile.get("hacked", []) or []

    store_target = next(
        (
            t for t in territory_store.list_captured_targets(username)
            if round(float(t.get("lat", 0)), 5) == round(float(lat), 5)
            and round(float(t.get("lng", t.get("lon", 0))), 5) == round(float(lng), 5)
        ),
        None
    )
    if store_target:
        replaced = False
        for index, item in enumerate(hacked_list):
            if targets_share_position(item, store_target):
                hacked_list[index] = store_target
                replaced = True
                break
        if not replaced:
            hacked_list.append(store_target)
        profile["hacked"] = hacked_list
        profile["captured_targets_source"] = "sqlite"
        return store_target, hacked_list, not replaced

    if profile.get("captured_targets_source") == "sqlite":
        filtered, removed = filter_targets_by_position(
            hacked_list,
            {"lat": lat, "lng": lng},
            match_label=False
        )
        if removed:
            profile["hacked"] = filtered
        return None, profile.get("hacked", []), False

    target = next(
        (
            t for t in hacked_list
            if round(float(t.get("lat", 0)), 5) == round(float(lat), 5)
            and round(float(t.get("lng", t.get("lon", 0))), 5) == round(float(lng), 5)
        ),
        None
    )
    if target:
        saved_target = territory_store.save_captured_target(username, target)
        for index, item in enumerate(hacked_list):
            if targets_share_position(item, saved_target):
                hacked_list[index] = saved_target
                break
        profile["hacked"] = hacked_list
        profile["captured_targets_source"] = "sqlite"
        return saved_target, hacked_list, False

    return None, hacked_list, False


def build_security_preset(current_security, preset):
    preset = (preset or "").strip().lower()
    bool_keys = [key for key, value in (current_security or {}).items() if isinstance(value, bool)]
    int_keys = [key for key, value in (current_security or {}).items() if isinstance(value, int) and not isinstance(value, bool)]
    security = dict(current_security or {})

    ratios = {
        "open": 0.0,
        "low": 0.18,
        "regular": 0.55,
        "secure": 0.82,
        "all": 1.0,
    }
    if preset not in ratios:
        raise ValueError("Nieznany preset zabezpieczen.")

    enabled_count = round(len(bool_keys) * ratios[preset])
    enabled_keys = set(bool_keys[:enabled_count])

    for key in bool_keys:
        security[key] = key in enabled_keys

    int_value = 0
    if preset == "low":
        int_value = 1
    elif preset == "regular":
        int_value = 45
    elif preset == "secure":
        int_value = 80
    elif preset == "all":
        int_value = 100

    for key in int_keys:
        security[key] = int_value

    return security


@app.route("/secure-action", methods=["POST"])
def secure_action():
    data = request.get_json(silent=True) or {}
    action = data.get("action")  # np. 'vpn_enabled'
    lat = data.get("lat")
    lng = data.get("lng")

    if not all([action, lat, lng]):
        return jsonify({"success": False, "message": "Brak wymaganych danych."}), 400

    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Brak poprawnych wspolrzednych celu."}), 400

    profile = sync_session_profile()
    if not profile:
        return jsonify({"success": False, "message": "Brak profilu użytkownika."}), 403

    # szukamy celu po współrzędnych w sekcji hacked
    target, hacked_list, added_from_store = find_owned_hacked_target(profile, session["user"], lat, lng)
    if not target:
        return jsonify({"success": False, "message": "Nie znaleziono celu."}), 404

    # odczyt i przełączenie stanu
    security = target.get("security", {})
    current_value = security.get(action, False)
    new_value = not current_value
    security[action] = new_value

    _, updated = save_owned_hacked_security(session["user"], lat, lng, security)

    if not updated:
        return jsonify({"success": False, "message": "Nie udało się zapisać zmian."}), 500

    profile["hacked"] = territory_store.list_captured_targets(session["user"])
    profile["captured_targets_source"] = "sqlite"
    session["profile"] = profile

    return jsonify({
        "success": True,
        "message": f"{action} ustawiono na {new_value}",
        "new_value": new_value,
        "security": security
    })


@app.route("/secure-preset", methods=["POST"])
def secure_preset():
    data = request.get_json(silent=True) or {}
    preset = data.get("preset")
    lat = data.get("lat")
    lng = data.get("lng")

    if not all([preset, lat, lng]):
        return jsonify({"success": False, "message": "Brak wymaganych danych."}), 400

    profile = sync_session_profile()
    if not profile:
        return jsonify({"success": False, "message": "Brak profilu uzytkownika."}), 403

    target, hacked_list, added_from_store = find_owned_hacked_target(profile, session["user"], lat, lng)
    if not target:
        return jsonify({"success": False, "message": "Nie znaleziono celu."}), 404

    try:
        security = build_security_preset(target.get("security", {}), preset)
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400

    target["security"] = security
    _, updated = save_owned_hacked_security(session["user"], lat, lng, security)
    if not updated:
        return jsonify({"success": False, "message": "Nie udalo sie zapisac presetu."}), 500

    profile["hacked"] = territory_store.list_captured_targets(session["user"])
    profile["captured_targets_source"] = "sqlite"
    session["profile"] = profile

    return jsonify({
        "success": True,
        "message": f"Preset {preset} zapisany.",
        "preset": preset,
        "security": security
    })




@app.route("/map")
def map_view():
    profile = sync_session_profile()
    if not profile:
        return redirect_missing_profile_to_login()
    ava_lat = profile.get("curently_possition", {}).get("lat", 52.2297)
    ava_lng = profile.get("curently_possition", {}).get("lng", 21.0122)
    zoom = get_player_map_zoom(profile)
    min_zoom = get_player_min_map_zoom(profile)
    desktop_settings = normalize_desktop_settings(profile.get("desktop_settings"))
    requested_scheme = str(request.args.get("scheme") or "").strip()
    scheme_id = requested_scheme if requested_scheme in MAP_TILE_SCHEMES else desktop_settings.get("map_tile_scheme")
    tile_scheme = MAP_TILE_SCHEMES.get(scheme_id) or MAP_TILE_SCHEMES["osm"]
    scheme_zoom = max(1, min(20, zoom + int(tile_scheme.get("zoom_offset") or 0)))
    if tile_scheme.get("max_zoom_cap") is not None:
        scheme_zoom = min(scheme_zoom, int(tile_scheme["max_zoom_cap"]))
    scheme_min_zoom = min(min_zoom, scheme_zoom)
    m = folium.Map(
        location=[ava_lat, ava_lng],
        zoom_start=scheme_zoom,
        min_zoom=scheme_min_zoom,
        max_zoom=scheme_zoom,
        tiles=tile_scheme["tiles"],
        attr=tile_scheme["attr"],
    )

    # # Dodaj różne style
    # # OpenStreetMap
    # folium.TileLayer('OpenStreetMap', name='Standard').add_to(m)

    # # Stamen Toner
    # folium.TileLayer(
    #     tiles='https://stamen-tiles.a.ssl.fastly.net/toner/{z}/{x}/{y}.png',
    #     attr='Map tiles by Stamen Design, CC BY 3.0 — Map data © OpenStreetMap contributors',
    #     name='Czarno-biała'
    # ).add_to(m)

    # # Stamen Watercolor
    # folium.TileLayer(
    #     tiles='https://stamen-tiles.a.ssl.fastly.net/watercolor/{z}/{x}/{y}.jpg',
    #     attr='Map tiles by Stamen Design, CC BY 3.0 — Map data © OpenStreetMap contributors',
    #     name='Watercolor'
    # ).add_to(m)

    # # CartoDB Positron (jasna)
    # folium.TileLayer(
    #     tiles='https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    #     attr='©OpenStreetMap, ©CartoDB',
    #     name='Jasna'
    # ).add_to(m)

    # # CartoDB Dark Matter (ciemna)
    # folium.TileLayer(
    #     tiles='https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    #     attr='©OpenStreetMap, ©CartoDB',
    #     name='Ciemna'
    # ).add_to(m)

    # # Dodaj kontrolkę do zmiany warstwy
    # folium.LayerControl().add_to(m)

    hacked_position_keys = {
        target_position_key(target)
        for target in profile.get("hacked", []) or []
        if target_position_key(target)
    }
    targets = [
        target for target in profile.get("targets", []) or []
        if target_position_key(target) not in hacked_position_keys
    ]
    for t in targets:
        text_icon = t.get("icon", "🎯")
        label = display_target_label(t)
        name = display_target_label(t)
        source_type = t.get("source_type", "manual")
        generated = str(t.get("generated", False)).lower()
        target_id = html.escape(build_operation_target_id(t))

        folium.Marker(
            location=[t["lat"], t["lng"]],
            tooltip=label,
            icon=DivIcon(
                icon_size=(32, 42),
                icon_anchor=(16, 42),
                class_name="target-marker",
                html=f'''
                    <div class="marker-label" 
                        data-label="{label}" 
                        data-name="{name}" 
                        data-source-type="{source_type}" 
                        data-generated="{generated}"
                        data-target-id="{target_id}"
                        data-icon="{text_icon}" 
                        data-lat="{t["lat"]}" 
                        data-lng="{t["lng"]}"
                        style="font-size:2rem;line-height:2rem;">
                        {text_icon}
                    </div>
                '''
            )
        ).add_to(m)


    hacked = profile.get("hacked", [])
    for h in hacked:
        text_icon = h.get("icon", "🛜")
        label = display_target_label(h)
        name = display_target_label(h)
        source_type = h.get("source_type", "hacked")
        generated = str(h.get("generated", False)).lower()
        h_lng = h.get("lng", h.get("lon"))
        target_id = html.escape(build_operation_target_id(h))

        folium.Marker(
            location=[h["lat"], h_lng],
            tooltip=label,
            icon=DivIcon(
                icon_size=(32, 42),
                icon_anchor=(16, 42),
                class_name="target-hacked",
                html=f'''
                    <div class="marker-hacked" 
                        data-label="{label}" 
                        data-name="{name}" 
                        data-source-type="{source_type}" 
                        data-generated="{generated}"
                        data-target-id="{target_id}"
                        data-icon="{text_icon}" 
                        data-lat="{h["lat"]}" 
                        data-lng="{h_lng}"
                        style="font-size:3rem;line-height:2rem;">
                        {text_icon}
                    </div>
                '''
            )
        ).add_to(m)


    profile_aimed_target = profile.get("aimed_target", {})

    if profile_aimed_target.get("lat") is not None and profile_aimed_target.get("lng") is not None:

        text_icon = profile_aimed_target.get("icon", "📶")
        label = display_target_label(profile_aimed_target)
        name = display_target_label(profile_aimed_target)
        source_type = profile_aimed_target.get("source_type", "aimed")
        generated = str(profile_aimed_target.get("generated", False)).lower()
        target_mode = html.escape(str(profile_aimed_target.get("target_mode") or "standard"))
        target_username = html.escape(str(profile_aimed_target.get("target_username") or ""))
        target_relation = html.escape(str(profile_aimed_target.get("relation") or ""))
        target_id = html.escape(build_operation_target_id(profile_aimed_target))

        folium.Marker(
            location=[profile_aimed_target["lat"], profile_aimed_target["lng"]],
            tooltip=label,
            icon=DivIcon(
                icon_size=(32, 42),
                icon_anchor=(16, 42),
                class_name="target-marker",
                html=f'''
                    <div class="marker-label" 
                        data-label="{label}" 
                        data-name="{name}" 
                        data-source-type="{source_type}" 
                        data-generated="{generated}"
                        data-target-id="{target_id}"
                        data-target-mode="{target_mode}"
                        data-target-username="{target_username}"
                        data-relation="{target_relation}"
                        data-icon="{text_icon}" 
                        data-lat="{profile_aimed_target["lat"]}" 
                        data-lng="{profile_aimed_target["lng"]}"
                        style="font-size:3rem;line-height:2rem;">
                        {text_icon}
                    </div>
                '''
            )
        ).add_to(m)

    # Ręcznie wyciągamy HTML i JS, by kontrolować resztę layoutu
    map_html = m.get_root().render()

    return render_template(
        "map_template.html",
        map_html=Markup(map_html),
        folium_css=Markup('<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.3/dist/leaflet.css" />'),
        folium_js=Markup('<script src="https://unpkg.com/leaflet@1.9.3/dist/leaflet.js"></script>'),
        profile=profile_template_payload(profile)
    )



@app.route('/map-action', methods=['POST'])
def map_action():
    data = request.get_json()
    action = data.get("action")
    lat = float(data.get("lat"))
    lng = float(data.get("lng"))
    
    profile = sync_session_profile()
    ava_lat = profile.get("curently_possition", {}).get("lat", 52.2297)
    ava_lng = profile.get("curently_possition", {}).get("lng", 21.0122)
    action_range = get_player_action_range(profile)

    def assign_icon_and_type(tags: dict) -> tuple[str, str]:
        """
        {
            'name': 'Alior Bank', 
            'lat': 52.2926013, 
            'lon': 21.0481023, 
            'tags': {
                'addr:city': 'Warszawa', 
                'addr:housenumber': '1', 
                'addr:postcode': '03-286', 
                'addr:street': 'Ludwika Kondratowicza', 
                'amenity': 'bank', 
                'atm': 'yes', 
                'brand': 'Alior Bank', 
                'brand:wikidata': 'Q9148395', 
                'brand:wikipedia': 'pl:Alior Bank', 
                'check_date': '2025-06-02', 
                'name': 'Alior Bank', 
                'opening_hours': 'Mo-We,Fr 09:00-17:00; Th 11:00-17:00', 
                'wheelchair': 'yes'
                }
            }
        """
        # Lista par (tag_key, tag_value, emoji, source_type), w kolejności ważności
        priority_map = [
            ("atm", "yes", "🏧", "atm"),
            ("amenity", "bank", "🏦", "bank"),
            ("amenity", "restaurant", "🍽️", "restaurant"),
            ("amenity", "cafe", "☕", "cafe"),
            ("amenity", "bar", "🍺", "bar"),
            ("amenity", "fast_food", "🍔", "fast_food"),
            ("amenity", "car_wash", "🧽", "car_wash"),
            ("amenity", "bicycle_parking", "🚲", "bicycle_parking"),
            ("amenity", "bench", "🪑", "bench"),
            ("amenity", "dentist", "🦷", "dentist"),
            ("amenity", "vending_machine", "🤖", "vending_machine"),
            ("amenity", "parcel_locker", "📦", "parcel_locker"),
            ("amenity", "pharmacy", "💊", "pharmacy"),
            ("amenity", "school", "🏫", "school"),
            ("amenity", "hospital", "🏥", "hospital"),
            ("shop", "beauty", "💄", "shop_beauty"),
            ("shop", "hairdresser", "💇", "shop_hairdresser"),
            ("shop", "books", "📚", "shop_books"),
            ("shop", "clothes", "👕", "shop_clothes"),
            ("shop", "electronics", "💻", "shop_electronics"),
            ("internet_access", None, "📡", "internet_access"),
            ("office", None, "🏢", "office"),
            ("healthcare", "dentist", "🦷", "dentist"),
        ]

        for key, expected_value, icon, source in priority_map:
            actual_value = tags.get(key)
            if actual_value is not None and (expected_value is None or actual_value == expected_value):
                return icon, source

        return "📍", "unknown"


    if action == "mark_target":
        label = data.get("label")
        icon = data.get("icon")
        source_type = data.get("source_type", "manual")
        name = data.get("name", label or "Cel oznaczony")
        generated = bool(data.get("generated", False))

        if not (label and icon):
            return jsonify({'error': 'Brak danych'}), 400

        target = {
            "lat": lat,
            "lng": lng,
            "label": label,          # widoczne na tooltipie
            "name": name,            # opcjonalnie: szczegóły w inspektorze
            "icon": icon,            # emoji
            "source_type": source_type,  # np. "shop", "atm", "manual"
            "generated": generated
        }

        # Dodaj do profilu
        targets = profile.get("targets", [])
        targets.append(target)
        profile["targets"] = targets
        session["profile"] = profile

        mgr = UserProfileManager(session["user"])
        mgr.update_profile({"targets": targets})

        return jsonify(status=f"🎯 Cel oznaczony: ({lat}, {lng})")
    
    if action == "scan":
        distance = Haversine.haversine_distance(lat, lng, ava_lat, ava_lng)

        if distance > action_range:
            return jsonify({
                "status": "🔍 Skanowanie nie udane! Nie jesteś w zasięgu.",
                "markers": []
            })

        # Pobierz już oznaczone cele (jako lat/lng pary)
        existing_targets = {(t["lat"], t["lng"]) for t in profile.get("targets", [])}

        # Zbierz unikalne wyniki ze wszystkich kategorii
        all_results = []

        try:
            fetched_results = fetcher.get_all(lat=lat, lon=lng, result_limit=60)
        except Exception as e:
            return jsonify({
                "status": f"Nie udało się pobrać danych mapy: {e}",
                "markers": []
            })

        for fetched in [fetched_results]:
            for obj in fetched:
                key = (obj["lat"], obj["lon"])
                if key in existing_targets:
                    continue

                tags = obj.get("tags", {})
                icon = "📍"
                source_type = "unknown"

                aiat = assign_icon_and_type(tags)

                obj["icon"], obj["source_type"] = aiat
                icon, source_type = aiat

                obj["generated"] = False  # oryginał
                all_results.append(obj)

                # 🧠 GENEROWANE OBIEKTY
                extra = []
                base_lat, base_lng = obj["lat"], obj["lon"]

                def jitter(offset=0.00015):
                    return random() * offset - offset / 2

                def radial_jitter(min_offset=0.00009, max_offset=0.00018, angle=None):
                    if angle is None:
                        angle = random() * math.tau
                    distance = min_offset + random() * (max_offset - min_offset)
                    return math.sin(angle) * distance, math.cos(angle) * distance

                
                hour = datetime.now().hour

                if source_type.startswith("shop"):
                    # Kamery
                    camera_count = randint(2, 4)
                    start_angle = random() * math.tau
                    for camera_index in range(camera_count):
                        angle = start_angle + (math.tau * camera_index / camera_count)
                        dlat, dlng = radial_jitter(0.00022, 0.00034, angle)
                        extra.append({
                            "lat": base_lat + dlat,
                            "lon": base_lng + dlng,
                            "name": "Kamera sklepu",
                            "icon": "📷",
                            "source_type": source_type,
                            "generated": True
                        })
                    if 8 <= hour <= 20:
                        client_count = randint(3, 8)
                        start_angle = random() * math.tau
                        for client_index in range(client_count):
                            angle = start_angle + (math.tau * client_index / client_count)
                            dlat, dlng = radial_jitter(0.00036, 0.00058, angle)
                            extra.append({
                                "lat": base_lat + dlat,
                                "lon": base_lng + dlng,
                                "name": "Klient",
                                "icon": "🧍",
                                "source_type": source_type,
                                "generated": True
                            })

                elif source_type == "atm":
                    extra.append({
                        "lat": base_lat + 0.000015,
                        "lon": base_lng - 0.000015,
                        "name": "Kamera bankomatu",
                        "icon": "📹",
                        "source_type": source_type,
                        "generated": True
                    })
                    for _ in range(randint(1, 3)):
                        extra.append({
                            "lat": base_lat + jitter(),
                            "lon": base_lng + jitter(),
                            "name": "Osoba przy bankomacie",
                            "icon": "🧍",
                            "source_type": source_type,
                            "generated": True
                        })

                elif source_type == "bicycle_parking":
                    extra.append({
                        "lat": base_lat + jitter(),
                        "lon": base_lng + jitter(),
                        "name": "Stacja rowerowa",
                        "icon": "🚲",
                        "source_type": source_type,
                        "generated": True
                    })

                elif source_type == "restaurant":
                    for _ in range(randint(2, 5)):
                        extra.append({
                            "lat": base_lat + jitter(),
                            "lon": base_lng + jitter(),
                            "name": "Gość restauracji",
                            "icon": "🧑‍🍳",
                            "source_type": source_type,
                            "generated": True
                        })

                elif source_type == "parcel_locker":
                    extra.append({
                        "lat": base_lat + jitter(),
                        "lon": base_lng + jitter(),
                        "name": "Kuriero-bot",
                        "icon": "📦",
                        "source_type": source_type,
                        "generated": True
                    })

                elif source_type == "parking":
                    brands = ["🚗 Audi", "🚙 VW", "🚘 Tesla", "🚕 Mercedes"]
                    for b in brands:
                        extra.append({
                            "lat": base_lat + jitter(0.0002),
                            "lon": base_lng + jitter(0.0002),
                            "name": f"Auto: {b}",
                            "icon": b.split()[0],
                            "source_type": source_type,
                            "generated": True
                        })

                all_results.extend(extra)



        # for category in tag_filters:
        #     fetched = fetcher.get_category(category, lat=lat, lon=lng, result_limit=20)
        #     for obj in fetched:
        #         key = (obj["lat"], obj["lon"])
        #         if key not in existing_targets:
        #             all_results.append(obj)

        return jsonify({
            "status": f"🔍 Zeskanowano {len(all_results)} nowych obiektów.",
            "markers": all_results
        })
    
    if action == "travel":
        route_waypoints = data.get("route_waypoints") if data.get("route_commit") else []
        route_points = []
        if isinstance(route_waypoints, list):
            for waypoint in route_waypoints:
                if not isinstance(waypoint, dict):
                    continue
                try:
                    point_lat = float(waypoint.get("lat"))
                    point_lng = float(waypoint.get("lng", waypoint.get("lon")))
                except (TypeError, ValueError):
                    continue
                route_points.append({"lat": point_lat, "lng": point_lng})
        if route_points:
            final_point = route_points[-1]
            if round(final_point["lat"], 6) != round(lat, 6) or round(final_point["lng"], 6) != round(lng, 6):
                route_points.append({"lat": lat, "lng": lng})
        else:
            route_points = [{"lat": lat, "lng": lng}]

        distance = 0
        planned_lat, planned_lng = ava_lat, ava_lng
        for route_point in route_points:
            distance = Haversine.haversine_distance(route_point["lat"], route_point["lng"], planned_lat, planned_lng)
            if distance > action_range:
                break
            planned_lat, planned_lng = route_point["lat"], route_point["lng"]

        if distance > action_range:
            return jsonify({
                "status": "too_far",
                "message": f"Za daleko, zasięg motocykla: {action_range} m."
            })

        position_updates = normalize_profile_position_update({"lat": lat, "lng": lng}, username=session.get("user"), source="travel")
        profile.update(position_updates)
        session["profile"] = profile

        mgr = UserProfileManager(session["user"])
        mgr.update_profile(position_updates)
        intrusion_area = notify_area_intrusion(session["user"], lat, lng)
        record_map_player_actor_delta(
            session["user"],
            profile,
            change_type="map.player_moved",
            reason="travel",
            intrusion_area=intrusion_area,
        )

        return jsonify({
            "status": f"🎯 Cel osiągnięty: ({lat}, {lng})",
            "message": f"🎯 Cel osiągnięty: ({lat}, {lng})",
            "curently_possition": position_updates.get("curently_possition"),
            "current_position": position_updates.get("current_position"),
            "position_version": position_updates.get("position_version"),
            "position_updated_at": position_updates.get("position_updated_at"),
            "intrusion": bool(intrusion_area),
            "intrusion_area": {
                "id": intrusion_area.get("id"),
                "owner_username": intrusion_area.get("owner_username"),
                "owner_nick": intrusion_area.get("owner_nick")
            } if intrusion_area else None
        })

    return jsonify(status=f"Zarejestrowano: {action} dla ({lat}, {lng})")


@app.route('/hack-action', methods=['POST'])
def hack_action():
    app_flow_started_at = time.perf_counter()
    data = request.get_json() or {}
    action = data['action']
    canonical_action = HACK_ACTION_STEP_ALIASES.get(action, action)
    lat = data['lat']
    lng = data['lng']
    label = display_target_label({
        "display_label": data.get("display_label"),
        "label": data.get("label"),
        "name": data.get("name"),
        "title": data.get("title"),
        "lat": lat,
        "lng": lng,
        "source_type": data.get("source_type", "manual"),
        "target_type": data.get("target_type"),
        "target_id": data.get("target_id"),
        "vulnerability_id": data.get("vulnerability_id"),
        "foreign_area_id": data.get("foreign_area_id"),
        "target_mode": data.get("target_mode"),
    })
    data["label"] = label
    if is_missing_target_name(data.get("name")):
        data["name"] = label
    vulnerability_id = data.get("vulnerability_id")
    requested_target_mode = data.get("target_mode")
    player_target_profile = None
    player_target_username = str(data.get("target_username") or "").strip()
    selected_app_id = str(data.get("selected_app_id") or "").strip()
    flow_id = str(data.get("_flow_id") or "")[:96]
    client_action_key = str(data.get("_client_action_key") or "")[:220]
    hack_action_idempotency_key = None
    hack_action_idempotency_started = False
    vulnerability_report = None
    contested_target = None
    hack_flow_debug(
        flow_id,
        "request_start",
        user=session.get("user"),
        action=action,
        selected=bool(selected_app_id),
        selected_app_id=selected_app_id,
        client_key=client_action_key,
        lat=lat,
        lng=lng,
        label=label,
        target_mode=requested_target_mode,
    )
    app_flow_debug(
        flow_id,
        "hack_action_start",
        started_at=app_flow_started_at,
        user=session.get("user"),
        action=action,
        selected=bool(selected_app_id),
        selected_app_id=selected_app_id,
        client_key=client_action_key,
        label=label,
    )

    if not selected_app_id:
        readonly_profile = load_profile_readonly(
            session.get("user"),
            strip_sensitive=True,
            normalize_apps=True,
            normalize_files=False,
        )
        if not readonly_profile:
            return jsonify({
                "success": False,
                "blocked": True,
                "reason": "profile_not_found",
                "status": "Brak danych profilu."
            }), 401

        preflight_player_target_username = player_target_username
        preflight_vulnerability_report = None
        if vulnerability_id:
            try:
                preflight_vulnerability_report = vulnerability_store.get(int(vulnerability_id))
            except (TypeError, ValueError):
                preflight_vulnerability_report = None
            if not preflight_vulnerability_report or preflight_vulnerability_report.get("status") != "active":
                return jsonify({
                    "success": False,
                    "blocked": True,
                    "status": "Ta podatnosc nie jest juz aktywna."
                }), 404
            if preflight_vulnerability_report.get("reported_by_username") == session["user"]:
                return jsonify({
                    "success": False,
                    "blocked": True,
                    "status": "Nie mozesz hackowac wlasnego zgloszenia podatnosci."
                }), 403

        preflight_contested_target = find_contested_target(session["user"], lat, lng, label)
        preflight_target_snapshot = {
            "lat": lat,
            "lng": lng,
            "label": label,
            "name": data.get("name", label),
            "source_type": data.get("source_type", "manual"),
            "target_mode": requested_target_mode or (
                "vulnerability" if preflight_vulnerability_report
                else ("territory_contest" if preflight_contested_target else "standard")
            ),
            "vulnerability_id": (
                preflight_vulnerability_report.get("id")
                if preflight_vulnerability_report else vulnerability_id
            ),
            "foreign_area_id": (
                preflight_contested_target.get("foreign_area_id")
                if preflight_contested_target else data.get("foreign_area_id")
            ),
            "target_username": preflight_player_target_username if requested_target_mode == "player" else None,
        }
        if requested_target_mode != "player":
            preflight_already_captured = find_owned_captured_target_for_runtime_target(
                session.get("user"),
                preflight_target_snapshot,
            )
            if preflight_already_captured:
                clear_aimed_target_if_matches(session["user"], preflight_target_snapshot)
                hack_flow_debug(
                    flow_id,
                    "return_stale_captured_target_guard_preflight",
                    user=session.get("user"),
                    action=action,
                    target_id=build_operation_target_id(preflight_already_captured),
                    client_key=client_action_key,
                )
                return jsonify({
                    "success": True,
                    "duplicate": True,
                    "status": f"Cel jest juz przejety: {display_target_label(preflight_already_captured)}",
                    "target": {},
                    "captured_target": preflight_already_captured,
                    "added_apps": [],
                    "created_operations": [],
                    "map_action_id": action,
                    "canonical_action": canonical_action,
                })

        if requested_target_mode == "player":
            if not preflight_player_target_username:
                aimed_player = (readonly_profile.get("aimed_target") or {}).get("target_username")
                preflight_player_target_username = str(aimed_player or "").strip()
            preflight_player_profile = user_store.get_profile(preflight_player_target_username)
            if not preflight_player_profile:
                return jsonify({
                    "success": False,
                    "blocked": True,
                    "status": "Ten gracz nie istnieje."
                }), 404
            active_access = player_hack_access_store.get_active_access(session["user"], preflight_player_target_username)
            cooldown = player_hack_access_store.get_cooldown(session["user"], preflight_player_target_username)
            if cooldown and not active_access:
                minutes_left = max(1, math.ceil((cooldown.get("cooldown_seconds_left") or 0) / 60))
                return jsonify({
                    "success": False,
                    "blocked": True,
                    "status": f"Cooldown aktywny. Ponowny hack gracza mozliwy za ok. {minutes_left} min.",
                    "cooldown_seconds_left": cooldown.get("cooldown_seconds_left", 0),
                    "cooldown_until": cooldown.get("cooldown_until")
                }), 429

        preflight_foreign_area = find_foreign_area_for_point(session["user"], float(lat), float(lng))
        if (
            preflight_foreign_area
            and not preflight_vulnerability_report
            and not preflight_contested_target
            and requested_target_mode != "player"
        ):
            return jsonify({
                "success": False,
                "blocked": True,
                "status": f"⛔ Target znajduje się na kontrolowanym terenie gracza {preflight_foreign_area['owner_nick']}.",
                "area": {
                    "id": preflight_foreign_area.get("id"),
                    "owner_username": preflight_foreign_area.get("owner_username"),
                    "owner_nick": preflight_foreign_area.get("owner_nick"),
                    "status": preflight_foreign_area.get("status")
                }
            }), 403

        preflight_apps = normalize_app_contracts(readonly_profile.get("apps", []))
        preflight_matched_apps, preflight_match_source = get_apps_for_map_action(preflight_apps, action)
        if not preflight_matched_apps and canonical_action != action:
            preflight_matched_apps, preflight_match_source = get_apps_for_map_action(preflight_apps, canonical_action)

        if not preflight_matched_apps:
            return jsonify({
                "success": False,
                "blocked": True,
                "reason": "no_app",
                "status": "Brak aplikacji obsługującej tę akcję.",
                "map_action_id": action,
                "canonical_action": canonical_action
            }), 409

        if len(preflight_matched_apps) > 1:
            app_flow_debug(
                flow_id,
                "hack_action_return_tool_selection_preflight",
                started_at=app_flow_started_at,
                action=action,
                matched=len(preflight_matched_apps),
                apps=[app.get("id") or app.get("name") for app in preflight_matched_apps],
            )
            hack_flow_debug(
                flow_id,
                "return_tool_selection_preflight",
                user=session.get("user"),
                action=action,
                matched=len(preflight_matched_apps),
                apps=[app.get("id") or app.get("name") for app in preflight_matched_apps],
                client_key=client_action_key,
            )
            return jsonify({
                "success": True,
                "tool_selection_required": True,
                "status": "Wybierz narzędzie z katalogu /tools.",
                "map_action_id": action,
                "canonical_action": canonical_action,
                "app_match_source": preflight_match_source,
                "matching_apps": [serialize_tool_selection_app(app) for app in preflight_matched_apps],
                "pending_action": {
                    "action": action,
                    "lat": lat,
                    "lng": lng,
                    "label": label,
                    "icon": data.get("icon", "📶"),
                    "source_type": data.get("source_type", "manual"),
                    "name": data.get("name", label),
                    "generated": data.get("generated", False),
                    "vulnerability_id": vulnerability_id,
                    "target_mode": requested_target_mode,
                    "contest_owner_username": data.get("contest_owner_username"),
                    "foreign_area_id": data.get("foreign_area_id"),
                    "target_username": preflight_player_target_username or data.get("target_username"),
                    "_flow_id": flow_id,
                    "_client_action_key": data.get("_client_action_key"),
            }
        })

    if selected_app_id:
        step_started_at = time.perf_counter()
        readonly_profile = load_profile_readonly(
            session.get("user"),
            strip_sensitive=True,
            normalize_apps=True,
            normalize_files=False,
        )
        app_flow_debug_timed(
            flow_id,
            "hack_action_selected_readonly_profile_done",
            app_flow_started_at,
            step_started_at,
            has_profile=bool(readonly_profile),
            apps=len((readonly_profile or {}).get("apps", [])),
        )
        step_started_at = time.perf_counter()
        readonly_apps = normalize_app_contracts((readonly_profile or {}).get("apps", []))
        early_matched_apps, _ = get_apps_for_map_action(readonly_apps, action)
        if not early_matched_apps and canonical_action != action:
            early_matched_apps, _ = get_apps_for_map_action(readonly_apps, canonical_action)
        early_selected_app = next(
            (
                app for app in early_matched_apps
                if str(app.get("id") or "") == selected_app_id
                or str(app.get("name") or "") == selected_app_id
            ),
            None,
        )
        app_flow_debug_timed(
            flow_id,
            "hack_action_selected_early_match_done",
            app_flow_started_at,
            step_started_at,
            matched=len(early_matched_apps or []),
            selected_found=bool(early_selected_app),
        )
        if early_selected_app:
            step_started_at = time.perf_counter()
            hack_action_idempotency_key = build_hack_action_idempotency_key(
                session.get("user"),
                flow_id,
                action,
                early_selected_app,
                data.get("_client_action_key"),
            )
            idempotency_metadata = build_hack_action_receipt_metadata(
                session.get("user"),
                action,
                early_selected_app,
                data,
            )
            idempotency_metadata["flow_id"] = flow_id
            app_flow_debug_timed(
                flow_id,
                "hack_action_selected_idempotency_key_done",
                app_flow_started_at,
                step_started_at,
                key=hack_action_idempotency_key,
            )
            step_started_at = time.perf_counter()
            idempotency_state, idempotency_receipt = begin_hack_action_idempotency(
                hack_action_idempotency_key,
                idempotency_metadata,
            )
            app_flow_debug_timed(
                flow_id,
                "hack_action_selected_idempotency_begin_done",
                app_flow_started_at,
                step_started_at,
                key=hack_action_idempotency_key,
                state=idempotency_state,
                store=(idempotency_receipt or {}).get("store", "sqlite"),
            )
            hack_flow_debug(
                flow_id,
                "idempotency_early",
                user=session.get("user"),
                action=action,
                app=early_selected_app.get("id") or early_selected_app.get("name"),
                key=hack_action_idempotency_key,
                state=idempotency_state,
                store=(idempotency_receipt or {}).get("store", "sqlite"),
                client_key=client_action_key,
            )
            if idempotency_state == "completed" and idempotency_receipt:
                cached_payload = copy.deepcopy(idempotency_receipt.get("payload") or {})
                cached_payload["duplicate"] = True
                cached_payload["idempotent_replay"] = True
                hack_flow_debug(flow_id, "return_idempotent_replay_early", key=hack_action_idempotency_key)
                return jsonify(cached_payload), int(idempotency_receipt.get("status_code") or 200)
            if idempotency_state == "in_flight":
                hack_flow_debug(flow_id, "return_idempotent_in_flight_early", key=hack_action_idempotency_key)
                return jsonify({
                    "success": True,
                    "duplicate": True,
                    "status": "Akcja jest juz uruchamiana.",
                    "map_action_id": action,
                    "canonical_action": canonical_action,
                }), 202
            hack_action_idempotency_started = True

    step_started_at = time.perf_counter()
    profile = sync_session_profile()
    app_flow_debug_timed(
        flow_id,
        "hack_action_sync_session_profile_done",
        app_flow_started_at,
        step_started_at,
        selected=bool(selected_app_id),
        has_profile=bool(profile),
        apps=len(profile.get("apps", []) if isinstance(profile, dict) else []),
        operations=len(profile.get("operations", []) if isinstance(profile, dict) else []),
        queue_len=len(profile.get("launch_queue", []) if isinstance(profile, dict) else []),
    )
    hack_flow_debug(
        flow_id,
        "after_sync_session_profile",
        user=session.get("user"),
        action=action,
        selected=bool(selected_app_id),
        apps=len(profile.get("apps", []) if isinstance(profile, dict) else []),
        operations=len(profile.get("operations", []) if isinstance(profile, dict) else []),
        launch_queue=list(profile.get("launch_queue", []) if isinstance(profile, dict) else []),
    )
    step_started_at = time.perf_counter()
    if vulnerability_id:
        try:
            vulnerability_report = vulnerability_store.get(int(vulnerability_id))
        except (TypeError, ValueError):
            vulnerability_report = None

        if not vulnerability_report or vulnerability_report.get("status") != "active":
            return jsonify({
                "success": False,
                "blocked": True,
                "status": "Ta podatnosc nie jest juz aktywna."
            }), 404

        if vulnerability_report.get("reported_by_username") == session["user"]:
            return jsonify({
                "success": False,
                "blocked": True,
                "status": "Nie mozesz hackowac wlasnego zgloszenia podatnosci."
            }), 403

        reporter = vulnerability_report.get("reported_by_username")
        if reporter and reporter != session["user"]:
            add_system_message_to_user(
                reporter,
                "info",
                "Proba hackowania podatnosci",
                (
                    f"{profile.get('nick') or session['user']} uruchomil akcje {action} "
                    f"na zgloszeniu {vulnerability_report.get('label')}."
                )
            )
    app_flow_debug_timed(
        flow_id,
        "hack_action_vulnerability_check_done",
        app_flow_started_at,
        step_started_at,
        vulnerability_id=vulnerability_id,
        found=bool(vulnerability_report),
    )

    step_started_at = time.perf_counter()
    contested_target = find_contested_target(session["user"], lat, lng, label)
    if contested_target:
        owner_username = contested_target.get("owner_username")
        attacker_name = profile.get("nick") or session["user"]
        if owner_username and owner_username != session["user"]:
            add_system_message_to_user(
                owner_username,
                "warning",
                "Atak na punkt kolizyjny",
                f"{attacker_name} uruchomil akcje {action} na twoim obiekcie {contested_target.get('label') or contested_target.get('name')}."
            )
            add_cyberner_direct_notification(
                owner_username,
                "System",
                "System",
                "Atak na punkt kolizyjny",
                (
                    f"{attacker_name} ({session['user']}) atakuje twoj obiekt "
                    f"{contested_target.get('label') or contested_target.get('name')}.\n"
                    f"Akcja: {action}\n"
                    f"Pozycja: {lat}, {lng}"
                )
            )
    app_flow_debug_timed(
        flow_id,
        "hack_action_contest_check_done",
        app_flow_started_at,
        step_started_at,
        contested=bool(contested_target),
        owner=(contested_target or {}).get("owner_username"),
        foreign_area_id=(contested_target or {}).get("foreign_area_id"),
    )

    step_started_at = time.perf_counter()
    if requested_target_mode == "player":
        if not player_target_username:
            aimed_player = (profile.get("aimed_target") or {}).get("target_username")
            player_target_username = str(aimed_player or "").strip()
        player_target_profile = user_store.get_profile(player_target_username)
        if not player_target_profile:
            return jsonify({
                "success": False,
                "blocked": True,
                "status": "Ten gracz nie istnieje."
            }), 404
        active_access = player_hack_access_store.get_active_access(session["user"], player_target_username)
        cooldown = player_hack_access_store.get_cooldown(session["user"], player_target_username)
        if cooldown and not active_access:
            minutes_left = max(1, math.ceil((cooldown.get("cooldown_seconds_left") or 0) / 60))
            return jsonify({
                "success": False,
                "blocked": True,
                "status": f"Cooldown aktywny. Ponowny hack gracza mozliwy za ok. {minutes_left} min.",
                "cooldown_seconds_left": cooldown.get("cooldown_seconds_left", 0),
                "cooldown_until": cooldown.get("cooldown_until")
            }), 429
    app_flow_debug_timed(
        flow_id,
        "hack_action_player_target_check_done",
        app_flow_started_at,
        step_started_at,
        requested_player=requested_target_mode == "player",
        target_username=player_target_username,
        found=bool(player_target_profile),
    )

    step_started_at = time.perf_counter()
    foreign_area = find_foreign_area_for_point(session["user"], float(lat), float(lng))
    app_flow_debug_timed(
        flow_id,
        "hack_action_foreign_area_check_done",
        app_flow_started_at,
        step_started_at,
        foreign_area=bool(foreign_area),
        owner=(foreign_area or {}).get("owner_username"),
    )
    if foreign_area and not vulnerability_report and not contested_target and requested_target_mode != "player":
        return jsonify({
            "success": False,
            "blocked": True,
            "status": f"⛔ Target znajduje się na kontrolowanym terenie gracza {foreign_area['owner_nick']}.",
            "area": {
                "id": foreign_area.get("id"),
                "owner_username": foreign_area.get("owner_username"),
                "owner_nick": foreign_area.get("owner_nick"),
                "status": foreign_area.get("status")
            }
        }), 403

    step_started_at = time.perf_counter()
    installed_apps = normalize_app_contracts(profile.get("apps", []))
    profile["apps"] = installed_apps
    matched_apps, match_source = get_apps_for_map_action(installed_apps, action)
    if not matched_apps and canonical_action != action:
        matched_apps, match_source = get_apps_for_map_action(installed_apps, canonical_action)
    app_flow_debug_timed(
        flow_id,
        "hack_action_full_app_match_done",
        app_flow_started_at,
        step_started_at,
        installed=len(installed_apps or []),
        matched=len(matched_apps or []),
        match_source=match_source,
    )

    if not matched_apps:
        return jsonify({
            "success": False,
            "blocked": True,
            "reason": "no_app",
            "status": "Brak aplikacji obsługującej tę akcję.",
            "map_action_id": action,
            "canonical_action": canonical_action
        }), 409

    if selected_app_id:
        step_started_at = time.perf_counter()
        selected_app = next(
            (
                app for app in matched_apps
                if str(app.get("id") or "") == selected_app_id
                or str(app.get("name") or "") == selected_app_id
            ),
            None
        )
        if not selected_app:
            return jsonify({
                "success": False,
                "blocked": True,
                "reason": "invalid_tool",
                "status": "Wybrane narzędzie nie obsługuje tej akcji.",
                "map_action_id": action,
                "canonical_action": canonical_action
            }), 400
        matched_apps = [selected_app]
        app_flow_debug_timed(
            flow_id,
            "hack_action_selected_app_validated",
            app_flow_started_at,
            step_started_at,
            selected_app_id=selected_app_id,
            selected_name=selected_app.get("name"),
        )
    elif len(matched_apps) > 1:
        app_flow_debug(
            flow_id,
            "hack_action_return_tool_selection_full",
            started_at=app_flow_started_at,
            action=action,
            matched=len(matched_apps),
            apps=[app.get("id") or app.get("name") for app in matched_apps],
        )
        hack_flow_debug(
            flow_id,
            "return_tool_selection_full",
            user=session.get("user"),
            action=action,
            matched=len(matched_apps),
            apps=[app.get("id") or app.get("name") for app in matched_apps],
            client_key=client_action_key,
        )
        return jsonify({
            "success": True,
            "tool_selection_required": True,
            "status": "Wybierz narzędzie z katalogu /tools.",
            "map_action_id": action,
            "canonical_action": canonical_action,
            "app_match_source": match_source,
            "matching_apps": [serialize_tool_selection_app(app) for app in matched_apps],
            "pending_action": {
                "action": action,
                "lat": lat,
                "lng": lng,
                "label": label,
                "icon": data.get("icon", "📶"),
                "source_type": data.get("source_type", "manual"),
                "name": data.get("name", label),
                "generated": data.get("generated", False),
                "vulnerability_id": vulnerability_id,
                "target_mode": requested_target_mode,
                "contest_owner_username": data.get("contest_owner_username"),
                "foreign_area_id": data.get("foreign_area_id"),
                "target_username": player_target_username or data.get("target_username"),
                "_flow_id": flow_id,
                "_client_action_key": data.get("_client_action_key"),
            }
        })

    if not hack_action_idempotency_key:
        step_started_at = time.perf_counter()
        hack_action_idempotency_key = build_hack_action_idempotency_key(
            session.get("user"),
            flow_id,
            action,
            matched_apps[0] if matched_apps else {},
            data.get("_client_action_key"),
        )
        app_flow_debug_timed(
            flow_id,
            "hack_action_full_idempotency_key_done",
            app_flow_started_at,
            step_started_at,
            key=hack_action_idempotency_key,
        )
    if not hack_action_idempotency_started:
        step_started_at = time.perf_counter()
        idempotency_metadata = build_hack_action_receipt_metadata(
            session.get("user"),
            action,
            matched_apps[0] if matched_apps else {},
            data,
        )
        idempotency_metadata["flow_id"] = flow_id
        app_flow_debug_timed(
            flow_id,
            "hack_action_full_idempotency_metadata_done",
            app_flow_started_at,
            step_started_at,
            key=hack_action_idempotency_key,
        )
        step_started_at = time.perf_counter()
        idempotency_state, idempotency_receipt = begin_hack_action_idempotency(
            hack_action_idempotency_key,
            idempotency_metadata,
        )
        app_flow_debug_timed(
            flow_id,
            "hack_action_full_idempotency_begin_done",
            app_flow_started_at,
            step_started_at,
            key=hack_action_idempotency_key,
            state=idempotency_state,
            store=(idempotency_receipt or {}).get("store", "sqlite"),
        )
        hack_flow_debug(
            flow_id,
            "idempotency_full",
            user=session.get("user"),
            action=action,
            app=((matched_apps[0] or {}).get("id") or (matched_apps[0] or {}).get("name")) if matched_apps else "",
            key=hack_action_idempotency_key,
            state=idempotency_state,
            store=(idempotency_receipt or {}).get("store", "sqlite"),
            client_key=client_action_key,
        )
        if idempotency_state == "completed" and idempotency_receipt:
            cached_payload = copy.deepcopy(idempotency_receipt.get("payload") or {})
            cached_payload["duplicate"] = True
            cached_payload["idempotent_replay"] = True
            hack_flow_debug(flow_id, "return_idempotent_replay_full", key=hack_action_idempotency_key)
            return jsonify(cached_payload), int(idempotency_receipt.get("status_code") or 200)
        if idempotency_state == "in_flight":
            hack_flow_debug(flow_id, "return_idempotent_in_flight_full", key=hack_action_idempotency_key)
            return jsonify({
                "success": True,
                "duplicate": True,
                "status": "Akcja jest juz uruchamiana.",
                "map_action_id": action,
                "canonical_action": canonical_action,
            }), 202

    requested_target_snapshot = {
        "lat": lat,
        "lng": lng,
        "label": label,
        "name": data.get("name", label),
        "source_type": data.get("source_type", "manual"),
        "target_mode": requested_target_mode or ("vulnerability" if vulnerability_report else ("territory_contest" if contested_target else "standard")),
        "vulnerability_id": vulnerability_report.get("id") if vulnerability_report else vulnerability_id,
        "foreign_area_id": contested_target.get("foreign_area_id") if contested_target else data.get("foreign_area_id"),
        "target_username": player_target_username if requested_target_mode == "player" else None,
    }
    already_captured_target = None
    if requested_target_mode != "player":
        step_started_at = time.perf_counter()
        already_captured_target = find_owned_captured_target_for_runtime_target(
            session.get("user"),
            requested_target_snapshot,
        )
        app_flow_debug_timed(
            flow_id,
            "hack_action_already_captured_check_done",
            app_flow_started_at,
            step_started_at,
            found=bool(already_captured_target),
            target_id=build_operation_target_id(already_captured_target or requested_target_snapshot),
        )
    if already_captured_target:
        clear_aimed_target_if_matches(session["user"], requested_target_snapshot)
        profile["aimed_target"] = {}
        session["profile"] = profile
        response_payload = {
            "success": True,
            "duplicate": True,
            "status": f"Cel jest juz przejety: {display_target_label(already_captured_target)}",
            "target": {},
            "captured_target": already_captured_target,
            "added_apps": [],
            "created_operations": [],
            "map_action_id": action,
            "canonical_action": canonical_action,
            "debug_flow": {
                "flow_id": flow_id,
                "client_action_key": client_action_key,
                "idempotency_key": hack_action_idempotency_key,
                "stale_captured_target_guard": True,
            },
        }
        hack_flow_debug(
            flow_id,
            "return_stale_captured_target_guard",
            user=session.get("user"),
            action=action,
            key=hack_action_idempotency_key,
            target_id=build_operation_target_id(already_captured_target),
        )
        finish_hack_action_idempotency(hack_action_idempotency_key, response_payload, 200)
        return jsonify(response_payload)

    if "launch_queue" not in profile:
        profile["launch_queue"] = []
    existing_launch_receipts = set()
    existing_launch_names = set()
    for queue_item in profile.get("launch_queue") or []:
        if isinstance(queue_item, dict):
            receipt = str(queue_item.get("receipt") or queue_item.get("launch_receipt") or "").strip()
            name = str(queue_item.get("name") or queue_item.get("app_name") or "").strip()
        else:
            receipt = ""
            name = str(queue_item or "").strip()
        if receipt:
            existing_launch_receipts.add(receipt)
        if name:
            existing_launch_names.add(name)
    new_apps = []
    for app in matched_apps:
        app_name = str(app.get("name") or "").strip()
        app_id = str(app.get("id") or "").strip()
        receipt_seed = "|".join([
            str(flow_id or ""),
            str(client_action_key or ""),
            str(selected_app_id or app_id or app_name),
        ])
        launch_receipt = hashlib.sha1(receipt_seed.encode("utf-8")).hexdigest()[:20]
        if launch_receipt in existing_launch_receipts:
            continue
        if not launch_receipt and app_name in existing_launch_names:
            continue
        new_apps.append({
            "name": app_name,
            "app_id": app_id,
            "flow_id": flow_id,
            "receipt": launch_receipt,
            "action": action,
            "client_action_key": client_action_key,
        })
        existing_launch_receipts.add(launch_receipt)
        existing_launch_names.add(app_name)
    profile["launch_queue"].extend(new_apps)
    app_flow_debug(
        flow_id,
        "hack_action_launch_queue_append",
        started_at=app_flow_started_at,
        action=action,
        selected_app_id=selected_app_id,
        new_apps=new_apps,
        launch_queue=list(profile.get("launch_queue", [])),
    )
    hack_flow_debug(
        flow_id,
        "launch_queue_append",
        user=session.get("user"),
        action=action,
        selected_app_id=selected_app_id,
        new_apps=new_apps,
        launch_queue=list(profile.get("launch_queue", [])),
    )
    step_started_at = time.perf_counter()
    security_template = resources_store.get(
        "user_security",
        default={}
    )
    app_flow_debug_timed(
        flow_id,
        "hack_action_security_template_loaded",
        app_flow_started_at,
        step_started_at,
        keys=len(security_template or {}),
    )

    previous_target = profile.get("aimed_target", {})
    step_started_at = time.perf_counter()
    try:
        same_coords = (
            round(float(previous_target.get("lat")), 6) == round(float(lat), 6)
            and round(float(previous_target.get("lng", previous_target.get("lon"))), 6) == round(float(lng), 6)
        )
    except (TypeError, ValueError):
        same_coords = False
    same_label = str(previous_target.get("label") or "") == str(label or "")
    same_target = same_coords and same_label
    if vulnerability_report:
        same_vulnerability = int(previous_target.get("vulnerability_id") or 0) == int(vulnerability_report.get("id") or 0)
        same_target = same_vulnerability or (same_coords and same_label)
    if requested_target_mode == "player" and player_target_username:
        same_target = (
            previous_target.get("target_mode") == "player"
            and previous_target.get("target_username") == player_target_username
        ) or same_target

    app_flow_debug_timed(
        flow_id,
        "hack_action_target_identity_check_done",
        app_flow_started_at,
        step_started_at,
        same_target=same_target,
        previous_target_id=build_operation_target_id(previous_target or {}),
    )
    step_started_at = time.perf_counter()
    mgr = UserProfileManager(session["user"])
    app_flow_debug_timed(
        flow_id,
        "hack_action_profile_manager_ready",
        app_flow_started_at,
        step_started_at,
        user=session["user"],
    )
    target_branch_started_at = time.perf_counter()
    if same_target:
        if "actions_allowed" not in previous_target:
            previous_target["actions_allowed"] = {}

        previous_target["actions_allowed"][action] = True
        previous_target["actions_allowed"][canonical_action] = True
        if vulnerability_report:
            previous_target["target_mode"] = "vulnerability"
            previous_target["vulnerability_id"] = vulnerability_report.get("id")
            previous_target["security"] = dict(vulnerability_report.get("security") or previous_target.get("security") or {})
        elif contested_target:
            previous_target["target_mode"] = "territory_contest"
            previous_target["contest_owner_username"] = contested_target.get("owner_username")
            previous_target["foreign_area_id"] = contested_target.get("foreign_area_id")
            previous_target["security"] = dict(contested_target.get("security") or previous_target.get("security") or {})
        elif requested_target_mode == "player":
            previous_target["target_mode"] = "player"
            previous_target["target_username"] = player_target_username
            previous_target["username"] = player_target_username
            previous_target["security"] = dict((player_target_profile or {}).get("security") or previous_target.get("security") or {})
        profile["aimed_target"] = previous_target
        app_flow_debug_timed(
            flow_id,
            "hack_action_target_same_branch_done",
            app_flow_started_at,
            target_branch_started_at,
            allowed=previous_target.get("actions_allowed"),
            target_mode=previous_target.get("target_mode"),
        )

    else:
        remove_started_at = time.perf_counter()
        mgr.remove_from_list_by_coords("targets", lat, lng, label=label)
        app_flow_debug_timed(
            flow_id,
            "hack_action_target_remove_old_coords_done",
            app_flow_started_at,
            remove_started_at,
            label=label,
        )

        aimed_target = {
            "lat": lat,
            "lng": lng,
            "label": label,
            "name": data.get("name", label),
            "icon": data.get("icon", "📶"),
            "source_type": data.get("source_type", "manual"),
            "generated": data.get("generated", False),
            "target_mode": "player" if requested_target_mode == "player" else ("vulnerability" if vulnerability_report else ("territory_contest" if contested_target else "standard")),
            "target_username": player_target_username if requested_target_mode == "player" else None,
            "username": player_target_username if requested_target_mode == "player" else None,
            "nick": (player_target_profile or {}).get("nick") if requested_target_mode == "player" else None,
            "avatar": (player_target_profile or {}).get("avatar", "") if requested_target_mode == "player" else "",
            "relation": data.get("relation") if requested_target_mode == "player" else None,
            "vulnerability_id": vulnerability_report.get("id") if vulnerability_report else None,
            "contest_owner_username": contested_target.get("owner_username") if contested_target else None,
            "foreign_area_id": contested_target.get("foreign_area_id") if contested_target else None,
            "security": {},
            "actions_allowed": {
                "scan_ports": False,
                "exploit": False,
                "sniff": False,
                "trace": False
            }
        }
        build_started_at = time.perf_counter()
        apply_target_display_label(aimed_target)

        aimed_target["actions_allowed"][action] = True
        aimed_target["actions_allowed"][canonical_action] = True

        if vulnerability_report:
            aimed_target["security"] = dict(vulnerability_report.get("security") or {})
        elif contested_target:
            aimed_target["security"] = dict(contested_target.get("security") or {})
        elif requested_target_mode == "player":
            aimed_target["security"] = dict((player_target_profile or {}).get("security") or {})
            if not aimed_target["security"]:
                aimed_target["security"] = {
                    key: val
                    for key, val in security_template.items()
                    if isinstance(val, (bool, int))
                }
        else:
            for key, val in security_template.items():
                if isinstance(val, bool):
                    aimed_target["security"][key] = choice([True, False])
                elif isinstance(val, int):
                    aimed_target["security"][key] = randint(0, 100)

        profile["aimed_target"] = aimed_target
        app_flow_debug_timed(
            flow_id,
            "hack_action_target_new_branch_done",
            app_flow_started_at,
            build_started_at,
            target_mode=aimed_target.get("target_mode"),
            security_keys=len(aimed_target.get("security") or {}),
            allowed=aimed_target.get("actions_allowed"),
        )

    app_flow_debug_timed(
        flow_id,
        "hack_action_target_state_prepared",
        app_flow_started_at,
        step_started_at,
        same_target=same_target,
        target_mode=(profile.get("aimed_target") or {}).get("target_mode"),
        target_id=build_operation_target_id(profile.get("aimed_target") or {}),
        allowed=(profile.get("aimed_target") or {}).get("actions_allowed"),
    )

    step_started_at = time.perf_counter()
    created_operations = create_operations_for_app_action(
        profile,
        session["user"],
        matched_apps[0] if matched_apps else {},
        action,
        profile["aimed_target"]
    )
    app_flow_debug_timed(
        flow_id,
        "hack_action_create_operations_done",
        app_flow_started_at,
        step_started_at,
        action=action,
        count=len(created_operations or []),
        ids=[op.get("operation_id") for op in created_operations or [] if isinstance(op, dict)],
        operations_total=len(profile.get("operations", [])),
    )
    hack_flow_debug(
        flow_id,
        "created_operations",
        user=session.get("user"),
        action=action,
        count=len(created_operations or []),
        ids=[op.get("operation_id") for op in created_operations or [] if isinstance(op, dict)],
        operations_total=len(profile.get("operations", [])),
    )

    if action == "scan_ports":
        step_started_at = time.perf_counter()
        append_risk_event(
            profile,
            "suspicious_network_activity",
            "map_action",
            RISK_EVENT_BASE_SCORES["suspicious_network_activity"],
            operation={
                "operation_id": None,
                "operation_type": None,
                "map_action_id": action,
                "target_id": build_operation_target_id(profile.get("aimed_target") or {}),
                "target": profile.get("aimed_target") or {},
            },
            action=action,
            dedupe_key=risk_scan_action_dedupe_key(session["user"], action, lat, lng),
        )
        app_flow_debug_timed(
            flow_id,
            "hack_action_risk_event_appended",
            app_flow_started_at,
            step_started_at,
            action=action,
            risk_events=len(profile.get("risk_events", [])),
        )

    # Zapisz
    step_started_at = time.perf_counter()
    merge_latest_aimed_target_runtime_state(profile, session.get("user"))
    app_flow_debug_timed(
        flow_id,
        "hack_action_merge_latest_runtime_done",
        app_flow_started_at,
        step_started_at,
        target_id=build_operation_target_id(profile.get("aimed_target") or {}),
        allowed=(profile.get("aimed_target") or {}).get("actions_allowed"),
    )
    session["profile"] = profile
    step_started_at = time.perf_counter()
    set_player_aimed_target(
        session["user"],
        profile,
        profile["aimed_target"],
        update_fields={
            "launch_queue": profile["launch_queue"],
            "operations": profile.get("operations", []),
            "risk_events": profile.get("risk_events", []),
            "system_messages": profile.get("system_messages", []),
        },
        reason="hack_action_target_set",
    )
    app_flow_debug_timed(
        flow_id,
        "hack_action_set_player_aimed_target_done",
        app_flow_started_at,
        step_started_at,
        target_id=build_operation_target_id(profile.get("aimed_target") or {}),
        operations_total=len(profile.get("operations", [])),
        queue_len=len(profile.get("launch_queue", [])),
    )
    step_started_at = time.perf_counter()
    accepted_created_operations = filter_accepted_created_operations(profile, created_operations)
    app_flow_debug_timed(
        flow_id,
        "hack_action_filter_created_operations_done",
        app_flow_started_at,
        step_started_at,
        created=len(created_operations or []),
        accepted=len(accepted_created_operations or []),
    )
    hack_flow_debug(
        flow_id,
        "after_persist",
        user=session.get("user"),
        action=action,
        target_id=build_operation_target_id(profile.get("aimed_target") or {}),
        allowed=(profile.get("aimed_target") or {}).get("actions_allowed"),
        operations_total=len(profile.get("operations", [])),
        accepted_created=[op.get("operation_id") for op in accepted_created_operations or [] if isinstance(op, dict)],
    )
    step_started_at = time.perf_counter()
    record_map_target_delta(
        session["user"],
        profile.get("aimed_target") or {},
        change_type="map.target_updated",
        reason="hack_action_target_set",
    )
    app_flow_debug_timed(
        flow_id,
        "hack_action_record_map_target_delta_done",
        app_flow_started_at,
        step_started_at,
        target_id=build_operation_target_id(profile.get("aimed_target") or {}),
    )

    response_payload = {
        "status": f"🎯 Cel ustawiony: {display_target_label(profile.get('aimed_target') or {})}",
        "target": profile["aimed_target"],
        "added_apps": new_apps,
        "created_operations": accepted_created_operations,
        "map_action_id": action,
        "app_match_source": match_source,
        "debug_flow": {
            "flow_id": flow_id,
            "client_action_key": client_action_key,
            "pid": os.getpid(),
            "thread": threading.get_ident(),
            "idempotency_key": hack_action_idempotency_key,
            "new_apps": new_apps,
            "created_operation_ids": [op.get("operation_id") for op in created_operations or [] if isinstance(op, dict)],
            "accepted_operation_ids": [op.get("operation_id") for op in accepted_created_operations or [] if isinstance(op, dict)],
        }
    }
    app_flow_debug(
        flow_id,
        "hack_action_return_success",
        started_at=app_flow_started_at,
        action=action,
        selected_app_id=selected_app_id,
        new_apps=new_apps,
        accepted_count=len(accepted_created_operations or []),
        target_id=build_operation_target_id(profile.get("aimed_target") or {}),
    )
    hack_flow_debug(
        flow_id,
        "return_success",
        user=session.get("user"),
        action=action,
        status_code=200,
        new_apps=new_apps,
        accepted_count=len(accepted_created_operations or []),
        key=hack_action_idempotency_key,
    )
    step_started_at = time.perf_counter()
    finish_hack_action_idempotency(hack_action_idempotency_key, response_payload, 200)
    app_flow_debug_timed(
        flow_id,
        "hack_action_finish_idempotency_done",
        app_flow_started_at,
        step_started_at,
        key=hack_action_idempotency_key,
    )
    return jsonify(response_payload)





@app.route("/api/profile")
def api_profile():
    if "user" not in session:
        return jsonify({"error": "Brak danych użytkownika"}), 401

    snapshot_started_at = blacknet_utc_now()
    profile = sync_session_profile()
    profile = refresh_and_persist_operations(session["user"], profile)
    profile["desktop_settings"] = normalize_desktop_settings(profile.get("desktop_settings"))
    profile["dev_mode"] = is_dev_mode_enabled()
    profile["app_version"] = APP_VERSION
    attach_profile_snapshot_meta(profile, snapshot_started_at, blacknet_utc_now())
    return jsonify(profile)


@app.route("/api/dev/bug-reports")
def api_dev_bug_reports():
    denied = require_dev_mode()
    if denied:
        return denied

    reports = dev_bug_report_store.list_reports(
        search=request.args.get("search", ""),
        category=request.args.get("category", ""),
        status=request.args.get("status", ""),
    )
    return jsonify({
        "success": True,
        "reports": reports,
        "categories": sorted(DevBugReportStore.VALID_CATEGORIES),
        "severities": sorted(DevBugReportStore.VALID_SEVERITIES),
        "statuses": sorted(DevBugReportStore.VALID_STATUSES),
        "app_version": APP_VERSION,
    })


@app.route("/api/dev/bug-reports/similar")
def api_dev_bug_report_similar():
    denied = require_dev_mode()
    if denied:
        return denied

    return jsonify({
        "success": True,
        "reports": dev_bug_report_store.find_similar(request.args.get("title", "")),
    })


@app.route("/api/dev/bug-reports", methods=["POST"])
def api_dev_bug_report_create():
    denied = require_dev_mode()
    if denied:
        return denied

    data = request.get_json() or {}
    data["context"] = build_dev_bug_server_context(
        session.get("user"),
        client_context=data.get("context"),
    )
    data["app_version"] = APP_VERSION
    try:
        report = dev_bug_report_store.create_report(
            data,
            created_by=session.get("user"),
            app_version=APP_VERSION,
        )
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400

    return jsonify({
        "success": True,
        "report": report,
        "similar": dev_bug_report_store.find_similar(report.get("title", "")),
        "message": "Zgloszenie zostalo zapisane.",
    })


@app.route("/api/dev/bug-reports/<int:report_id>", methods=["PATCH"])
def api_dev_bug_report_update(report_id):
    denied = require_dev_mode()
    if denied:
        return denied

    report = dev_bug_report_store.update_report(report_id, request.get_json() or {})
    if not report:
        return jsonify({"success": False, "message": "Nie znaleziono zgloszenia."}), 404
    return jsonify({
        "success": True,
        "report": report,
        "message": "Zgloszenie zostalo zaktualizowane.",
    })


@app.route("/api/operations")
def api_operations():
    if "user" not in session:
        return jsonify({"success": False, "message": "Brak danych uzytkownika"}), 401

    summary_mode = str(request.args.get("summary") or request.args.get("active_only") or "").strip().lower() in {"1", "true", "yes", "active"}
    if summary_mode:
        profile = load_profile_readonly(session["user"], normalize_apps=False, normalize_files=False)
        if not profile:
            session.clear()
            return jsonify({"success": False, "message": "Brak danych uzytkownika"}), 401
        operations = operations_from_store_or_profile(session["user"], profile, refresh=False)
        active_operations = active_operations_from_operations(operations)
        operation_history = operation_history_from_operations(operations)
        return jsonify({
            "success": True,
            "active_operations": [
                summarize_operation_for_client(operation)
                for operation in active_operations
            ],
            "operation_history": [
                summarize_operation_for_client(operation)
                for operation in operation_history[-25:]
            ],
            "active_count": len(active_operations),
            "history_count": len(operation_history),
            "source": "player_operations",
        })
    else:
        profile = sync_session_profile()
    profile = refresh_and_persist_operations(session["user"], profile)
    operations, _ = refresh_operations_runtime(profile, persist_timeouts=False, username=session["user"])
    active_operations = active_operations_from_operations(operations)
    operation_history = operation_history_from_operations(operations)

    return jsonify({
        "success": True,
        "operations": operations,
        "active_operations": active_operations,
        "operation_history": operation_history,
    })


@app.route("/api/operations/cancel", methods=["POST"])
def api_cancel_operation():
    if "user" not in session:
        return jsonify({"success": False, "message": "Brak danych uzytkownika"}), 401

    data = request.get_json() or {}
    operation_id = str(data.get("operation_id") or "").strip()
    if not operation_id:
        return jsonify({"success": False, "message": "Brak identyfikatora operacji."}), 400

    profile = sync_session_profile()
    operation, result = cancel_profile_operation(profile, operation_id, cancelled_by=session["user"])
    if result == "not_found":
        store_operation, store_result = player_operation_store.cancel_operation(
            session["user"],
            operation_id,
            cancelled_by=session["user"],
        )
        if store_result == "cancelled":
            operation = store_operation
            result = "cancelled"
    if result == "not_found":
        return jsonify({"success": False, "message": "Nie znaleziono operacji."}), 404
    if result in {"already_terminal", "not_active"}:
        return jsonify({
            "success": False,
            "message": "Operacja nie jest juz aktywna.",
            "operation": operation,
        }), 409

    UserProfileManager(session["user"]).update_profile({
        "operations": profile.get("operations", []),
        "files": profile.get("files", {}),
        "risk_events": profile.get("risk_events", []),
        "system_messages": profile.get("system_messages", []),
    })
    player_operation_store.upsert_operations(
        session["user"],
        profile.get("operations", []),
        event_type="operation.cancelled",
        source="api_operations_cancel",
    )
    stored_profile = user_store.get_profile(session["user"]) or {}
    profile["operations"] = stored_profile.get("operations", [])
    profile["files"] = stored_profile.get("files", {})
    profile["risk_events"] = stored_profile.get("risk_events", [])
    profile["system_messages"] = stored_profile.get("system_messages", [])
    session["profile"] = profile
    operations, _ = refresh_operations_runtime(profile, persist_timeouts=False, username=session["user"])

    return jsonify({
        "success": True,
        "message": "Operacja zostala anulowana.",
        "operation": operation,
        "operations": operations,
        "active_operations": active_operations_from_operations(operations),
        "operation_history": operation_history_from_operations(operations),
    })


@app.route("/api/ghost-control/operations")
@app.route("/api/pro-system/operation-control")
def operation_control_snapshot():
    if "user" not in session:
        return jsonify({"success": False, "error": "not_logged_in"}), 401

    username = session["user"]
    profile = operation_control_load_profile(username, strip_sensitive=True)
    if not profile:
        session.clear()
        return jsonify({"success": False, "error": "profile_not_found"}), 401
    if not operation_control_app_installed(profile):
        return operation_control_forbidden_response()

    operations = operations_from_store_or_profile(username, profile, refresh=False)
    return jsonify(build_operation_control_snapshot(username, profile, operations=operations))


@app.route("/api/ghost-control/operations/cancel", methods=["POST"])
@app.route("/api/pro-system/operation-control/cancel", methods=["POST"])
def operation_control_cancel():
    if "user" not in session:
        return jsonify({"success": False, "error": "not_logged_in"}), 401

    username = session["user"]
    data = request.get_json(silent=True) or {}
    operation_id = str(data.get("operation_id") or "").strip()
    if not operation_id:
        return jsonify({"success": False, "error": "missing_operation_id"}), 400

    profile = sync_session_profile(rebuild_territory=False)
    if not profile:
        return jsonify({"success": False, "error": "profile_not_found"}), 404
    if not operation_control_app_installed(profile):
        return operation_control_forbidden_response()

    refresh_operations_runtime(profile, persist_timeouts=True, username=username)
    operation, result = cancel_profile_operation(profile, operation_id, cancelled_by=username)
    if result == "not_found":
        store_operation, store_result = player_operation_store.cancel_operation(
            username,
            operation_id,
            cancelled_by=username,
        )
        if store_result == "cancelled":
            operation = store_operation
            result = "cancelled"
    if result == "not_found":
        return jsonify({"success": False, "error": "not_found", "message": "Nie znaleziono operacji."}), 404
    if result in {"already_terminal", "not_active"}:
        return jsonify({
            "success": False,
            "error": result,
            "message": "Operacja nie jest juz aktywna.",
            "operation": summarize_operation_control_item(operation, profile=profile) if operation else None,
        }), 409
    if result != "cancelled":
        return jsonify({"success": False, "error": result or "cancel_failed"}), 409

    persist_operation_control_profile(username, profile)
    player_operation_store.upsert_operations(
        username,
        profile.get("operations", []),
        event_type="operation.cancelled",
        source="operation_control_cancel",
    )
    operations = operations_from_store_or_profile(username, profile, refresh=False)
    snapshot = build_operation_control_snapshot(username, profile, operations=operations)
    return jsonify({
        "success": True,
        "ok": True,
        "message": "Operacja zostala anulowana.",
        "result": result,
        "operation": summarize_operation_control_item(operation, profile=profile),
        "snapshot": snapshot,
        "remaining_active": snapshot.get("active_count", 0),
    })


@app.route("/api/ghost-control/operations/cancel-group", methods=["POST"])
@app.route("/api/pro-system/operation-control/cancel-group", methods=["POST"])
def operation_control_cancel_group():
    if "user" not in session:
        return jsonify({"success": False, "error": "not_logged_in"}), 401

    username = session["user"]
    data = request.get_json(silent=True) or {}
    requested_family = str(data.get("operation_family") or "").strip().lower()
    operation_ids = data.get("operation_ids")
    if not isinstance(operation_ids, list):
        return jsonify({"success": False, "error": "invalid_operation_ids"}), 400
    operation_ids = [str(item or "").strip() for item in operation_ids if str(item or "").strip()]
    if not operation_ids:
        return jsonify({"success": False, "error": "empty_operation_ids"}), 400

    profile = sync_session_profile(rebuild_territory=False)
    if not profile:
        return jsonify({"success": False, "error": "profile_not_found"}), 404
    if not operation_control_app_installed(profile):
        return operation_control_forbidden_response()

    operations, _ = refresh_operations_runtime(profile, persist_timeouts=True, username=username)
    operation_map = {
        str(operation.get("operation_id") or ""): operation
        for operation in operations or []
        if isinstance(operation, dict) and operation.get("operation_id")
    }
    now_ts = datetime.now(timezone.utc).timestamp()
    results = []
    cancelled = []
    already_terminal = []
    not_found = []
    failed = []

    for operation_id in operation_ids:
        operation = operation_map.get(operation_id)
        if not operation:
            item = {"operation_id": operation_id, "status": "not_found"}
            results.append(item)
            not_found.append(operation_id)
            continue

        family = operation_control_family(operation)
        if requested_family and family != requested_family:
            item = {
                "operation_id": operation_id,
                "status": "failed",
                "reason": "family_mismatch",
                "operation_family": family,
            }
            results.append(item)
            failed.append(item)
            continue

        if operation.get("status") in OPERATION_TERMINAL_STATUSES:
            item = {
                "operation_id": operation_id,
                "status": "already_terminal",
                "operation_family": family,
            }
            results.append(item)
            already_terminal.append(operation_id)
            continue

        _, result = cancel_profile_operation(profile, operation_id, cancelled_by=username, now_ts=now_ts)
        if result == "cancelled":
            item = {
                "operation_id": operation_id,
                "status": "cancelled",
                "operation_family": family,
            }
            results.append(item)
            cancelled.append(operation_id)
        elif result == "already_terminal":
            item = {
                "operation_id": operation_id,
                "status": "already_terminal",
                "operation_family": family,
            }
            results.append(item)
            already_terminal.append(operation_id)
        elif result == "not_found":
            item = {"operation_id": operation_id, "status": "not_found"}
            results.append(item)
            not_found.append(operation_id)
        else:
            item = {
                "operation_id": operation_id,
                "status": "failed",
                "reason": result or "cancel_failed",
                "operation_family": family,
            }
            results.append(item)
            failed.append(item)

    persist_operation_control_profile(username, profile)
    player_operation_store.upsert_operations(
        username,
        profile.get("operations", []),
        event_type="operation.cancelled_group",
        source="operation_control_cancel_group",
    )
    operations = operations_from_store_or_profile(username, profile, refresh=False)
    snapshot = build_operation_control_snapshot(username, profile, operations=operations)
    return jsonify({
        "success": True,
        "ok": True,
        "operation_family": requested_family or None,
        "results": results,
        "cancelled": cancelled,
        "already_terminal": already_terminal,
        "not_found": not_found,
        "failed": failed,
        "remaining_active": snapshot.get("active_count", 0),
        "snapshot": snapshot,
    })


@app.route("/api/ghost-exchange")
def api_ghost_exchange():
    if "user" not in session:
        return jsonify({"success": False, "message": "Brak danych uzytkownika"}), 401

    username = session["user"]
    profile = user_store.get_profile(username) or sync_session_profile()
    profile = refresh_and_persist_operations(username, profile)
    previous_storage = storage_delta_snapshot(profile)
    market_runtime = refresh_market_runtime(username, profile)
    if market_runtime.get("changed"):
        UserProfileManager(username).update_profile({
            "files": profile.get("files", {}),
            "market_history": profile.get("market_history", []),
            "hackcoins": profile.get("hackcoins", 0),
            "system_messages": profile.get("system_messages", []),
            "storage_capacity": profile.get("storage_capacity"),
            "storage_used": profile.get("storage_used"),
            "storage_unit": profile.get("storage_unit", "MB"),
            "storage_soft_limit": True,
            "storage_over_limit": profile.get("storage_over_limit", False),
        })
        record_storage_delta(
            username,
            profile,
            reason="ghost_exchange_auto_sale",
            previous=previous_storage,
            dedupe_key_prefix=f"storage:{username}:ghost_exchange:{market_runtime.get('sales', [{}])[0].get('batch_id') if market_runtime.get('sales') else runtime_file_now()}",
        )
        for sale in market_runtime.get("sales", []):
            record_wallet_balance_delta(
                username,
                profile.get("hackcoins", 0),
                reason="ghost_exchange_auto_sale",
                dedupe_key=f"wallet:balance:{username}:ghost_exchange:{sale.get('batch_id') or sale.get('id')}",
            )
        record_ghost_exchange_delta(
            username,
            profile,
            sales=market_runtime.get("sales", []),
            reason="ghost_exchange_auto_sale",
        )
        session["profile"] = profile
    sectors = build_ghost_exchange_sector_payload(profile)
    dashboard = build_ghost_exchange_dashboard_payload(profile, sectors=sectors)
    return jsonify({
        "success": True,
        "currency": "HC",
        "balance": profile.get("hackcoins", 0),
        "hackcoins": profile.get("hackcoins", 0),
        "files": collect_ghost_exchange_files(profile),
        "summary": dashboard["summary"],
        "sectors": dashboard["sectors"],
        "recent_transactions": dashboard["recent_transactions"],
        "history_7d": dashboard["history_7d"],
        "market_runtime": market_runtime,
        "market_queue_changed": market_runtime.get("queued", 0),
        "statuses": ["not_listed", "ready_to_list", "listed_preview"],
    })


@app.route("/api/ghost-exchange/preview", methods=["POST"])
def api_ghost_exchange_preview():
    if "user" not in session:
        return jsonify({"success": False, "message": "Brak danych uzytkownika"}), 401

    data = request.get_json() or {}
    file_id = str(data.get("file_id") or "").strip()
    if not file_id:
        return jsonify({"success": False, "message": "Brak identyfikatora pliku."}), 400

    profile = user_store.get_profile(session["user"]) or sync_session_profile()
    profile = refresh_and_persist_operations(session["user"], profile)
    file_entry = mark_ghost_exchange_preview(profile, file_id)
    if not file_entry:
        return jsonify({"success": False, "message": "Plik nie jest dostepny do przygotowania oferty."}), 404

    normalize_profile_storage(profile)
    UserProfileManager(session["user"]).update_profile({
        "files": profile.get("files", {}),
        "storage_capacity": profile.get("storage_capacity"),
        "storage_used": profile.get("storage_used"),
        "storage_unit": profile.get("storage_unit", "MB"),
        "storage_soft_limit": True,
        "storage_over_limit": profile.get("storage_over_limit", False),
    })
    session["profile"] = profile
    return jsonify({
        "success": True,
        "message": "Oferta przygotowana w trybie preview.",
        "file": ghost_exchange_listing_payload(file_entry),
        "files": collect_ghost_exchange_files(profile),
    })


@app.route("/api/ghost-exchange/sell", methods=["POST"])
def api_ghost_exchange_sell():
    if "user" not in session:
        return jsonify({"success": False, "message": "Brak danych uzytkownika"}), 401

    data = request.get_json() or {}
    file_id = str(data.get("file_id") or "").strip()
    if not file_id:
        return jsonify({"success": False, "message": "Brak identyfikatora pliku."}), 400

    username = session["user"]
    profile = user_store.get_profile(username) or sync_session_profile()
    profile = refresh_and_persist_operations(username, profile)
    previous_storage = storage_delta_snapshot(profile)
    sale = sell_ghost_exchange_file(profile, username, file_id)
    if not sale:
        return jsonify({"success": False, "message": "Plik nie jest dostepny do sprzedazy albo zostal juz sprzedany."}), 404

    current_hc = profile.get("hackcoins", 0)
    try:
        current_hc = int(current_hc)
    except (TypeError, ValueError):
        current_hc = 0
    new_balance = current_hc + int(sale["price"])
    profile["hackcoins"] = new_balance
    record_wallet_balance_delta(
        username,
        profile.get("hackcoins", 0),
        reason="ghost_exchange_manual_sale",
        dedupe_key=f"wallet:balance:{username}:ghost_exchange_manual:{file_id}",
    )

    sold_file_name = sale["file"].get("name") or sale["file"].get("filename") or "data_package"
    mail_body = (
        f"Pakiet danych: {sold_file_name}\n"
        f"Kategoria rynku: {sale['market_category']}\n"
        f"Cena: {sale['price']} HC\n"
        f"Kupujacy: {sale['buyer_type']}\n"
        f"Czas: {sale['sold_at']}\n"
        "Status pliku: sold / removed from data inventory"
    )
    add_cyberner_direct_notification(
        username,
        "Ghost Exchange",
        "Ghost Exchange",
        "Sprzedano pakiet danych",
        mail_body,
    )
    normalize_profile_storage(profile)

    UserProfileManager(username).update_profile({
        "hackcoins": profile.get("hackcoins", 0),
        "files": profile.get("files", {}),
        "market_history": profile.get("market_history", []),
        "storage_capacity": profile.get("storage_capacity"),
        "storage_used": profile.get("storage_used"),
        "storage_unit": profile.get("storage_unit", "MB"),
        "storage_soft_limit": True,
        "storage_over_limit": profile.get("storage_over_limit", False),
    })
    record_storage_delta(
        username,
        profile,
        reason="ghost_exchange_manual_sale",
        previous=previous_storage,
        dedupe_key_prefix=f"storage:{username}:ghost_exchange_manual:{file_id}",
    )
    record_ghost_exchange_delta(
        username,
        profile,
        sales=[profile.get("market_history", [])[-1]] if profile.get("market_history") else [],
        reason="ghost_exchange_manual_sale",
    )
    session["profile"] = profile

    return jsonify({
        "success": True,
        "message": f"Sprzedano pakiet danych za {sale['price']} HC.",
        "sale": {
            "file_name": sold_file_name,
            "price": sale["price"],
            "currency": "HC",
            "market_category": sale["market_category"],
            "buyer_type": sale["buyer_type"],
            "sold_at": sale["sold_at"],
            "market_status": "sold",
        },
        "balance": new_balance,
        "files": collect_ghost_exchange_files(profile),
    })


@app.route("/api/profile/security", methods=["POST"])
def update_profile_security():
    if "user" not in session:
        return jsonify({"error": "Brak danych uzytkownika"}), 401

    data = request.get_json() or {}
    key = (data.get("key") or "").strip()
    value = data.get("value")

    profile = sync_session_profile()
    security = profile.get("security", {})

    if key not in security or not isinstance(security.get(key), bool):
        return jsonify({"error": "Nieprawidlowa opcja zabezpieczen."}), 400

    if not isinstance(value, bool):
        return jsonify({"error": "Wartosc musi byc true albo false."}), 400

    security[key] = value
    changed_by_rules = []

    if value:
        for conflicted_key in SECURITY_CONFLICTS.get(key, []):
            if isinstance(security.get(conflicted_key), bool) and security.get(conflicted_key):
                security[conflicted_key] = False
                changed_by_rules.append(conflicted_key)

    mgr = UserProfileManager(session["user"])
    mgr.update_profile({"security": security})
    profile = sync_session_profile()

    return jsonify({
        "success": True,
        "security": profile.get("security", {}),
        "changed_by_rules": changed_by_rules,
        "rules": SECURITY_CONFLICTS
    })


@app.route("/api/profile/desktop", methods=["POST"])
def update_profile_desktop():
    if "user" not in session:
        return jsonify({"error": "Brak danych uzytkownika"}), 401

    data = request.get_json(silent=True) or {}
    username = session["user"]
    profile = user_store.get_profile(username)
    if not profile:
        session.pop("user", None)
        session.pop("profile", None)
        return jsonify({"error": "Brak danych uzytkownika"}), 401
    settings = normalize_desktop_settings(profile.get("desktop_settings"))

    if "wallpaper" in data:
        wallpaper = str(data.get("wallpaper") or "").strip()
        if wallpaper not in [
            "",
            "wall-1", "wall-2", "wall-3",
            "wall-chaos-green", "wall-chaos-blue", "wall-chaos-red",
            "wall-chaos-amber", "wall-chaos-violet",
        ]:
            return jsonify({"error": "Nieprawidlowa tapeta."}), 400
        settings["wallpaper"] = wallpaper

    if isinstance(data.get("icon_positions"), dict):
        cleaned = {}
        for key, pos in data["icon_positions"].items():
            if not isinstance(pos, dict):
                continue
            try:
                left = int(float(pos.get("left", 0)))
                top = int(float(pos.get("top", 0)))
            except (TypeError, ValueError):
                continue
            cleaned[str(key)] = {
                "left": max(0, left),
                "top": max(0, top)
            }
        settings["icon_positions"] = cleaned

    if "auto_fullscreen" in data:
        settings["auto_fullscreen"] = data.get("auto_fullscreen") is True

    if "map_tile_scheme" in data:
        map_tile_scheme = str(data.get("map_tile_scheme") or "osm").strip()
        if map_tile_scheme not in MAP_TILE_SCHEMES:
            return jsonify({"error": "Nieprawidlowy schemat mapy."}), 400
        settings["map_tile_scheme"] = map_tile_scheme

    mgr = UserProfileManager(username)
    mgr.update_profile({"desktop_settings": settings})
    profile["desktop_settings"] = settings
    session["profile"] = profile
    return jsonify({"success": True, "desktop_settings": settings})


@app.route("/api/profile/account", methods=["POST"])
def update_profile_account():
    if "user" not in session:
        return jsonify({"error": "Brak danych uzytkownika"}), 401

    data = request.get_json(silent=True) or {}
    username = session["user"]
    profile = user_store.get_profile(username)
    if not profile:
        session.clear()
        return jsonify({"error": "Brak danych uzytkownika"}), 401

    updates = {}

    if "email" in data:
        email, email_error = validate_registration_email(data.get("email"))
        if email_error:
            return jsonify({"success": False, "error": email_error}), 400
        useremails = {
            str(item.get("email", "")).strip().lower()
            for item in user_store.list_profiles()
            if str(item.get("username") or "") != username
        }
        if email in useremails:
            return jsonify({"success": False, "error": "Ten adres e-mail jest juz zarejestrowany."}), 409
        profile["email"] = email
        updates["email"] = email

    if "new_password" in data:
        current_password = str(data.get("current_password") or "")
        new_password = str(data.get("new_password") or "")
        password_error = validate_registration_password(new_password)
        if password_error:
            return jsonify({"success": False, "error": password_error}), 400
        if not authenticate_user(username, current_password):
            return jsonify({"success": False, "error": "Aktualne haslo jest nieprawidlowe."}), 403
        profile["password"] = new_password
        profile.pop("salt", None)
        updates["password_changed"] = True

    if not updates:
        return jsonify({"success": False, "error": "Brak zmian do zapisania."}), 400

    user_store.save_profile(profile)
    profile = user_store.get_profile(username) or profile
    profile.pop("password", None)
    profile.pop("salt", None)
    session["profile"] = profile

    return jsonify({
        "success": True,
        "profile": {
            "email": profile.get("email", ""),
        },
        **updates,
    })


@app.route("/api/wallet")
def api_wallet():
    if "user" not in session:
        return jsonify({"error": "Nie jestes zalogowany"}), 401

    try:
        return jsonify(wallet_store.get_wallet(session["user"]))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/wallet/transfer", methods=["POST"])
def api_wallet_transfer():
    if "user" not in session:
        return jsonify({"error": "Nie jestes zalogowany"}), 401

    data = request.get_json() or {}
    try:
        result = wallet_store.transfer(
            session["user"],
            data.get("to"),
            data.get("amount"),
            data.get("note", "")
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    transaction_id = (result.get("transaction") or {}).get("id")
    record_wallet_balance_delta(
        session["user"],
        result.get("balance", 0),
        reason="wallet_transfer_outgoing",
        dedupe_key=f"wallet:balance:{session['user']}:transfer:{transaction_id}:outgoing",
    )
    recipient = str(data.get("to") or "").strip()
    if recipient:
        try:
            record_wallet_balance_delta(
                recipient,
                result.get("recipient_balance", 0),
                reason="wallet_transfer_incoming",
                dedupe_key=f"wallet:balance:{recipient}:transfer:{transaction_id}:incoming",
            )
        except Exception as exc:
            print(f"[DELTA] recipient wallet delta failed for {recipient}: {exc}")

    session["profile"] = sync_session_profile(rebuild_territory=False)
    wallet = wallet_store.get_wallet(session["user"])
    return jsonify({
        "success": True,
        "balance": result["balance"],
        "currency": result["currency"],
        "transaction": result["transaction"],
        "transactions": wallet["transactions"],
        "ledger": wallet.get("ledger", []),
        "ledger_audit": wallet.get("ledger_audit", {}),
    })


@app.route("/api/player-hack/access")
def api_player_hack_access():
    if "user" not in session:
        return jsonify({"active": False, "error": "Nie jestes zalogowany"}), 401

    access = player_hack_access_store.get_active_access(session["user"])
    return jsonify(serialize_player_hack_access(access))


@app.route("/api/player-hack/tool/use", methods=["POST"])
def api_player_hack_tool_use():
    if "user" not in session:
        return jsonify({"success": False, "error": "Nie jestes zalogowany"}), 401

    data = request.get_json() or {}
    tool_id = str(data.get("tool_id") or "").strip()
    victim_username = str(data.get("victim_username") or "").strip()
    tool = get_pro_system_tool(tool_id)
    if not tool:
        return jsonify({"success": False, "error": "Nie ma takiego narzedzia."}), 404
    if not victim_username:
        return jsonify({"success": False, "error": "Brak celu narzedzia."}), 400

    access = player_hack_access_store.get_active_access(session["user"], victim_username)
    if not access:
        return jsonify({
            "success": False,
            "error": "Dostep do tego gracza wygasl albo nie istnieje."
        }), 403

    attacker_profile = user_store.get_profile(session["user"]) or {}
    if not app_is_installed(attacker_profile, tool_id):
        return jsonify({
            "success": False,
            "error": "Narzedzie nie jest zainstalowane."
        }), 403

    if tool_id == "systemLogReader":
        victim_profile = user_store.get_profile(victim_username)
        if not victim_profile:
            return jsonify({"success": False, "error": "Gracz celu nie istnieje."}), 404

        raw_messages = victim_profile.get("system_messages", []) or []
        safe_logs = []
        for msg in raw_messages[-5:]:
            if not isinstance(msg, dict):
                continue
            safe_logs.append({
                "type": str(msg.get("type") or ""),
                "title": str(msg.get("title") or ""),
                "text": str(msg.get("text") or ""),
                "status": str(msg.get("status") or ""),
                "created_at": str(msg.get("created_at") or ""),
            })
        message = (
            "System Log Reader odczytal ostatnie komunikaty ofiary."
            if safe_logs
            else "Brak komunikatow systemowych do odczytu."
        )
        return jsonify({
            "success": True,
            "tool_id": "systemLogReader",
            "tool": dict(tool),
            "result_type": "system_logs",
            "message": message,
            "logs": safe_logs,
            "access": serialize_player_hack_access(access),
        })

    if tool_id == "securityPanelProxy":
        victim_profile = user_store.get_profile(victim_username)
        if not victim_profile:
            return jsonify({"success": False, "error": "Gracz celu nie istnieje."}), 404

        return jsonify({
            "success": True,
            "tool_id": "securityPanelProxy",
            "tool": dict(tool),
            "result_type": "security_panel",
            "message": "Security Panel Proxy polaczony z profilem ofiary.",
            "victim_username": victim_username,
            "victim_nick": victim_profile.get("nick") or victim_username,
            "security": dict(victim_profile.get("security") or {}),
            "rules": SECURITY_CONFLICTS,
            "access": serialize_player_hack_access(access),
        })

    if tool_id == "financialSniffer":
        if player_hack_access_store.has_tool_usage(access, session["user"], victim_username, tool_id):
            return jsonify({
                "success": False,
                "error": "Financial Sniffer byl juz uzyty podczas tego dostepu."
            }), 409

        victim_profile = user_store.get_profile(victim_username)
        attacker_profile = user_store.get_profile(session["user"])
        if not victim_profile:
            return jsonify({"success": False, "error": "Gracz celu nie istnieje."}), 404
        if not attacker_profile:
            return jsonify({"success": False, "error": "Atakujacy nie istnieje."}), 404

        try:
            attacker_level = int(attacker_profile.get("level", 1) or 1)
        except (TypeError, ValueError):
            attacker_level = 1
        try:
            attacker_respect = int(attacker_profile.get("respect", 0) or 0)
        except (TypeError, ValueError):
            attacker_respect = 0
        try:
            victim_balance = int(victim_profile.get("hackcoins", 0) or 0)
        except (TypeError, ValueError):
            victim_balance = 0

        base_min = 5
        base_max = 25
        level_bonus = min(75, attacker_level * 3)
        respect_bonus = min(100, attacker_respect // 5)
        max_steal = max(base_min, base_max + level_bonus + respect_bonus)
        cap_by_balance = max(0, math.floor(victim_balance * 0.08))

        if victim_balance <= 0:
            final_amount = 0
            message = "Konto ofiary jest puste."
        else:
            stolen_amount = randint(base_min, max_steal)
            final_amount = min(stolen_amount, cap_by_balance, victim_balance)
            message = (
                f"Financial Sniffer przechwycil {final_amount} HC."
                if final_amount > 0
                else "Financial Sniffer nie znalazl bezpiecznej kwoty do przechwycenia."
            )

        risk_level = int(tool.get("risk_level", 2) or 2)
        detection_chance = min(45, 8 + risk_level * 5 + max(0, 10 - attacker_level))
        detected = (random() * 100) < detection_chance

        transfer_result = wallet_store.technical_transfer(
            victim_username,
            session["user"],
            final_amount,
            note="financialSniffer",
        )
        if final_amount > 0:
            record_wallet_balance_delta(
                victim_username,
                transfer_result.get("source_balance", 0),
                reason="financial_sniffer_outgoing",
                dedupe_key=f"wallet:balance:{victim_username}:financial_sniffer:{transfer_result.get('transaction_id')}:outgoing",
            )
            record_wallet_balance_delta(
                session["user"],
                transfer_result.get("target_balance", 0),
                reason="financial_sniffer_incoming",
                dedupe_key=f"wallet:balance:{session['user']}:financial_sniffer:{transfer_result.get('transaction_id')}:incoming",
            )
        player_hack_access_store.record_tool_usage(
            access,
            session["user"],
            victim_username,
            tool_id,
            result="detected" if detected else "silent",
            amount=final_amount,
        )

        if detected:
            add_system_message_to_user(
                victim_username,
                "warning",
                "Podejrzany ruch finansowy",
                "Wykryto probe sniffingu finansowego na twoim koncie."
            )

        refreshed_access = player_hack_access_store.get_active_access(session["user"], victim_username)
        return jsonify({
            "success": True,
            "tool_id": "financialSniffer",
            "tool": dict(tool),
            "result_type": "financial_sniffer",
            "message": message,
            "stolen_amount": final_amount,
            "currency": "HC",
            "detected": detected,
            "victim_balance_after_known": False,
            "attacker_balance": transfer_result.get("target_balance"),
            "access": serialize_player_hack_access(refreshed_access),
        })

    if tool_id == "friendKicker":
        if player_hack_access_store.has_tool_usage(access, session["user"], victim_username, tool_id):
            return jsonify({
                "success": False,
                "error": "Friend Kicker byl juz uzyty podczas tego dostepu."
            }), 409

        victim_profile = user_store.get_profile(victim_username)
        attacker_profile = user_store.get_profile(session["user"])
        if not victim_profile:
            return jsonify({"success": False, "error": "Gracz celu nie istnieje."}), 404
        if not attacker_profile:
            return jsonify({"success": False, "error": "Atakujacy nie istnieje."}), 404

        blocked_contacts = {
            "",
            victim_username.lower(),
            "admin",
            "system",
            "googolplex",
        }
        contacts = []
        for contact in mail_store.list_contacts(victim_username):
            name = str((contact or {}).get("name") or "").strip()
            if not name or name.lower() in blocked_contacts:
                continue
            contacts.append(name)

        if not contacts:
            player_hack_access_store.record_tool_usage(
                access,
                session["user"],
                victim_username,
                tool_id,
                result="no_contacts",
                amount=0,
            )
            refreshed_access = player_hack_access_store.get_active_access(session["user"], victim_username)
            return jsonify({
                "success": True,
                "tool_id": "friendKicker",
                "tool": dict(tool),
                "result_type": "friend_kicker",
                "message": "Brak kontaktow do wypchniecia.",
                "removed": False,
                "reason": "Brak kontaktow do wypchniecia.",
                "target_contact_known": False,
                "kicked_contact_masked": "",
                "chance": 0,
                "roll": 0,
                "detected": False,
                "access": serialize_player_hack_access(refreshed_access),
            })

        kicked_contact = choice(contacts)
        try:
            attacker_level = int(attacker_profile.get("level", 1) or 1)
        except (TypeError, ValueError):
            attacker_level = 1
        try:
            attacker_respect = int(attacker_profile.get("respect", 0) or 0)
        except (TypeError, ValueError):
            attacker_respect = 0

        chance = min(85, 35 + attacker_level * 4 + attacker_respect // 10)
        roll = randint(1, 100)
        removed = roll <= chance
        risk_level = int(tool.get("risk_level", 3) or 3)
        detected = removed or ((random() * 100) < min(45, 8 + risk_level * 5))

        if removed:
            mail_store.remove_contact(victim_username, kicked_contact)
            if mail_store.is_contact(kicked_contact, victim_username):
                mail_store.remove_contact(kicked_contact, victim_username)
            add_system_message_to_user(
                victim_username,
                "warning",
                "Zaklocenie kontaktow",
                "Jeden z kontaktow zostal zerwany przez nieznana ingerencje."
            )
            add_system_message_to_user(
                kicked_contact,
                "info",
                "Kontakt utracony",
                "Polaczenie z jednym z graczy zostalo zerwane."
            )
            message = "Friend Kicker zerwal jeden kontakt ofiary."
            result = "removed"
        else:
            if detected:
                add_system_message_to_user(
                    victim_username,
                    "warning",
                    "Wykryto probe manipulacji kontaktami",
                    "Wykryto probe manipulacji kontaktami."
                )
            message = "Friend Kicker nie zdolal zerwac kontaktu."
            result = "failed_detected" if detected else "failed_silent"

        player_hack_access_store.record_tool_usage(
            access,
            session["user"],
            victim_username,
            tool_id,
            result=result,
            amount=1 if removed else 0,
        )
        refreshed_access = player_hack_access_store.get_active_access(session["user"], victim_username)
        return jsonify({
            "success": True,
            "tool_id": "friendKicker",
            "tool": dict(tool),
            "result_type": "friend_kicker",
            "message": message,
            "removed": removed,
            "target_contact_known": False,
            "kicked_contact_masked": mask_contact_name(kicked_contact) if removed else "",
            "chance": chance,
            "roll": roll,
            "detected": detected,
            "access": serialize_player_hack_access(refreshed_access),
        })

    if tool_id == "arsenalCleaner":
        if player_hack_access_store.has_tool_usage(access, session["user"], victim_username, tool_id):
            return jsonify({
                "success": False,
                "error": "Arsenal Cleaner byl juz uzyty podczas tego dostepu."
            }), 409

        victim_profile = user_store.get_profile(victim_username)
        attacker_profile = user_store.get_profile(session["user"])
        if not victim_profile:
            return jsonify({"success": False, "error": "Gracz celu nie istnieje."}), 404
        if not attacker_profile:
            return jsonify({"success": False, "error": "Atakujacy nie istnieje."}), 404

        apps = list(victim_profile.get("apps", []) or [])
        candidates = [app for app in apps if is_cleanable_app(app)]

        if not candidates:
            player_hack_access_store.record_tool_usage(
                access,
                session["user"],
                victim_username,
                tool_id,
                result="no_apps",
                amount=0,
            )
            refreshed_access = player_hack_access_store.get_active_access(session["user"], victim_username)
            return jsonify({
                "success": True,
                "tool_id": "arsenalCleaner",
                "tool": dict(tool),
                "result_type": "arsenal_cleaner",
                "message": "Brak aplikacji do wyczyszczenia.",
                "removed": False,
                "reason": "Brak aplikacji do wyczyszczenia.",
                "removed_app_masked": "",
                "removed_app_type": "",
                "chance": 0,
                "roll": 0,
                "detected": False,
                "access": serialize_player_hack_access(refreshed_access),
            })

        target_app = choice(candidates)
        target_app_id = str(target_app.get("id") or "").strip()
        target_app_name = app_display_name(target_app)
        try:
            attacker_level = int(attacker_profile.get("level", 1) or 1)
        except (TypeError, ValueError):
            attacker_level = 1
        try:
            attacker_respect = int(attacker_profile.get("respect", 0) or 0)
        except (TypeError, ValueError):
            attacker_respect = 0
        try:
            victim_level = int(victim_profile.get("level", 1) or 1)
        except (TypeError, ValueError):
            victim_level = 1

        chance = min(80, max(20, 35 + attacker_level * 4 + attacker_respect // 12 - victim_level * 2))
        roll = randint(1, 100)
        removed = roll <= chance
        risk_level = int(tool.get("risk_level", 4) or 4)
        detected = removed or ((random() * 100) < min(50, 10 + risk_level * 5))

        if removed:
            def app_matches(item):
                if not isinstance(item, dict):
                    return False
                if target_app_id and str(item.get("id") or "").strip() == target_app_id:
                    return True
                return app_display_name(item) == target_app_name

            victim_profile["apps"] = [app for app in apps if not app_matches(app)]
            victim_profile["files"] = remove_app_tool_files(victim_profile.get("files", {}), target_app)
            user_store.save_profile(victim_profile)
            add_system_message_to_user(
                victim_username,
                "warning",
                "Arsenal naruszony",
                "Jedno z narzedzi zostalo usuniete przez nieznana ingerencje."
            )
            message = "Arsenal Cleaner usunal jedno narzedzie ofiary."
            result = "removed"
        else:
            if detected:
                add_system_message_to_user(
                    victim_username,
                    "warning",
                    "Wykryto probe czyszczenia arsenalu",
                    "Wykryto probe czyszczenia arsenalu."
                )
            message = "Arsenal Cleaner nie zdolal usunac aplikacji."
            result = "failed_detected" if detected else "failed_silent"

        player_hack_access_store.record_tool_usage(
            access,
            session["user"],
            victim_username,
            tool_id,
            result=result,
            amount=1 if removed else 0,
        )
        refreshed_access = player_hack_access_store.get_active_access(session["user"], victim_username)
        return jsonify({
            "success": True,
            "tool_id": "arsenalCleaner",
            "tool": dict(tool),
            "result_type": "arsenal_cleaner",
            "message": message,
            "removed": removed,
            "removed_app_masked": mask_contact_name(target_app_name) if removed else "",
            "removed_app_type": str(target_app.get("type") or target_app.get("interface") or ""),
            "chance": chance,
            "roll": roll,
            "detected": detected,
            "access": serialize_player_hack_access(refreshed_access),
        })

    return jsonify({
        "success": True,
        "message": f"{tool['name']} przyjete do kolejki. To jest placeholder narzedzia.",
        "tool": dict(tool),
        "access": serialize_player_hack_access(access),
    })


@app.route("/api/player-hack/security/update", methods=["POST"])
def api_player_hack_security_update():
    if "user" not in session:
        return jsonify({"success": False, "error": "Nie jestes zalogowany"}), 401

    data = request.get_json() or {}
    victim_username = str(data.get("victim_username") or "").strip()
    key = str(data.get("key") or "").strip()
    value = data.get("value")
    if not victim_username:
        return jsonify({"success": False, "error": "Brak ofiary."}), 400
    if not key:
        return jsonify({"success": False, "error": "Brak klucza zabezpieczenia."}), 400

    access = player_hack_access_store.get_active_access(session["user"], victim_username)
    if not access:
        return jsonify({
            "success": False,
            "error": "Dostep do tego gracza wygasl albo nie istnieje."
        }), 403

    victim_profile = user_store.get_profile(victim_username)
    if not victim_profile:
        return jsonify({"success": False, "error": "Gracz celu nie istnieje."}), 404

    security = dict(victim_profile.get("security") or {})
    if key not in security or not isinstance(security.get(key), bool):
        return jsonify({"success": False, "error": "Nieprawidlowa opcja zabezpieczen."}), 400
    if not isinstance(value, bool):
        return jsonify({"success": False, "error": "Wartosc musi byc true albo false."}), 400

    security[key] = value
    changed_by_rules = []
    if value:
        for conflicted_key in SECURITY_CONFLICTS.get(key, []):
            if isinstance(security.get(conflicted_key), bool) and security.get(conflicted_key):
                security[conflicted_key] = False
                changed_by_rules.append(conflicted_key)

    victim_profile["security"] = security
    user_store.save_profile(victim_profile)
    refreshed_access = player_hack_access_store.get_active_access(session["user"], victim_username)
    return jsonify({
        "success": True,
        "security": security,
        "changed_by_rules": changed_by_rules,
        "rules": SECURITY_CONFLICTS,
        "access": serialize_player_hack_access(refreshed_access),
    })


@app.route("/api/player-hack/security/preset", methods=["POST"])
def api_player_hack_security_preset():
    if "user" not in session:
        return jsonify({"success": False, "error": "Nie jestes zalogowany"}), 401

    data = request.get_json() or {}
    victim_username = str(data.get("victim_username") or "").strip()
    preset = str(data.get("preset") or "").strip().lower()
    if not victim_username:
        return jsonify({"success": False, "error": "Brak ofiary."}), 400

    access = player_hack_access_store.get_active_access(session["user"], victim_username)
    if not access:
        return jsonify({
            "success": False,
            "error": "Dostep do tego gracza wygasl albo nie istnieje."
        }), 403

    victim_profile = user_store.get_profile(victim_username)
    if not victim_profile:
        return jsonify({"success": False, "error": "Gracz celu nie istnieje."}), 404

    try:
        security = build_security_preset(victim_profile.get("security", {}), preset)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    victim_profile["security"] = security
    user_store.save_profile(victim_profile)
    refreshed_access = player_hack_access_store.get_active_access(session["user"], victim_username)
    return jsonify({
        "success": True,
        "security": security,
        "preset": preset,
        "rules": SECURITY_CONFLICTS,
        "access": serialize_player_hack_access(refreshed_access),
    })


@app.route("/api/map/player-targets/mark", methods=["POST"])
def mark_player_target():
    if "user" not in session:
        return jsonify({"success": False, "error": "Nie jestes zalogowany"}), 401

    viewer_username = session["user"]
    data = request.get_json() or {}
    target_username = str(data.get("target_username") or data.get("username") or "").strip()

    if not target_username:
        return jsonify({"success": False, "error": "Brak nazwy gracza."}), 400
    if target_username == viewer_username:
        return jsonify({"success": False, "error": "Nie mozna oznaczyc siebie jako celu."}), 400

    viewer_profile = sync_session_profile(rebuild_territory=False)
    target_profile = user_store.get_profile(target_username)
    if not target_profile:
        return jsonify({"success": False, "error": "Nie ma takiego gracza."}), 404

    is_intruder = any(
        intruder.get("username") == target_username
        for intruder in territory_store.list_recent_area_intruders(viewer_username)
    )
    context = {
        "is_friend": mail_store.is_accepted_contact(viewer_username, target_username),
        "is_intruder": is_intruder,
    }
    relation = resolve_player_actor_relation(viewer_profile, target_profile, context)
    if relation in {"self", "friend", "same_clan"}:
        return jsonify({
            "success": False,
            "error": "Nie mozna oznaczac siebie, znajomych ani swojego klanu.",
            "relation": relation,
        }), 403

    position = target_profile.get("curently_possition", {}) or {}
    lat = position.get("lat")
    lng = position.get("lng")
    if lat in (None, 0, 0.0) or lng in (None, 0, 0.0):
        return jsonify({"success": False, "error": "Brak aktualnej pozycji gracza."}), 400

    aimed_target = viewer_profile.get("aimed_target") or {}
    already_target = (
        aimed_target.get("target_mode") == "player"
        and aimed_target.get("target_username") == target_username
    )

    security_template = resources_store.get("user_security", default={})
    target_security = dict(target_profile.get("security") or {})
    if not target_security:
        target_security = {
            key: value
            for key, value in security_template.items()
            if isinstance(value, (bool, int))
        }

    label = target_profile.get("nick") or target_username
    player_target = {
        "target_mode": "player",
        "target_username": target_username,
        "username": target_username,
        "nick": target_profile.get("nick") or target_username,
        "avatar": target_profile.get("avatar", ""),
        "relation": relation,
        "lat": float(lat),
        "lng": float(lng),
        "lon": float(lng),
        "label": label,
        "name": label,
        "icon": "🎯",
        "source_type": "player",
        "generated": True,
        "stationary": False,
        "security": target_security,
        "actions_allowed": {
            "scan_ports": False,
            "exploit": False,
            "sniff": False,
            "trace": False,
        },
        # TODO(player-hack): po udanym hacku target_mode=player ma otwierac
        # galaz narzedzi systemowych z Googleplexa: profil, pliki, maile,
        # aplikacje i zabezpieczenia, z wymaganiami HC/level/klan/frakcja.
    }

    set_player_aimed_target(
        viewer_username,
        viewer_profile,
        player_target,
        reason="player_target_mark",
    )
    session["profile"] = viewer_profile

    return jsonify({
        "success": True,
        "status": "already_target" if already_target else "marked",
        "message": f"Gracz {label} jest na celowniku.",
        "target": player_target,
    })


@app.route("/api/victim-picker/candidates")
def victim_picker_candidates():
    if "user" not in session:
        return jsonify({"success": False, "error": "not_logged_in"}), 401

    username = session["user"]
    profile = user_store.get_profile(username)
    if not isinstance(profile, dict):
        return jsonify({"success": False, "error": "profile_not_found"}), 404

    profile = dict(profile)
    profile["apps"] = normalize_app_contracts(profile.get("apps", []))
    if not victim_picker_app_installed(profile):
        return jsonify({
            "success": False,
            "error": "victim_picker_not_installed",
            "message": "Victim Picker wymaga instalacji z Googleplex.",
        }), 403

    origin = victim_picker_position(profile)
    action_range = get_player_action_range(profile)
    candidates = build_victim_picker_candidates(username, profile)
    return jsonify({
        "success": True,
        "scope": "victim_picker",
        "position": origin,
        "action_range_m": action_range,
        "candidate_count": len(candidates),
        "candidates": [serialize_victim_picker_candidate(candidate) for candidate in candidates],
        "aimed_target": profile.get("aimed_target") or None,
        "active_target_id": build_operation_target_id(profile.get("aimed_target") or {}) if profile.get("aimed_target") else "",
    })


@app.route("/api/victim-picker/aim", methods=["POST"])
def victim_picker_aim():
    if "user" not in session:
        return jsonify({"success": False, "error": "not_logged_in"}), 401

    username = session["user"]
    payload = request.get_json(silent=True) or {}
    target_id = str(payload.get("target_id") or "").strip()
    if not target_id:
        return jsonify({"success": False, "error": "missing_target_id"}), 400

    profile = user_store.get_profile(username)
    if not isinstance(profile, dict):
        return jsonify({"success": False, "error": "profile_not_found"}), 404

    profile = dict(profile)
    profile["apps"] = normalize_app_contracts(profile.get("apps", []))
    if not victim_picker_app_installed(profile):
        return jsonify({
            "success": False,
            "error": "victim_picker_not_installed",
            "message": "Victim Picker wymaga instalacji z Googleplex.",
        }), 403

    candidate, candidates = find_victim_picker_candidate_by_id(username, profile, target_id)
    if not candidate:
        return jsonify({
            "success": False,
            "error": "target_not_found",
            "message": "Kandydat nie istnieje albo przestal byc dostepny.",
            "candidate_count": len(candidates),
        }), 404
    if not candidate.get("can_aim"):
        return jsonify({
            "success": False,
            "error": "target_unavailable",
            "message": candidate.get("disabled_reason") or "Kandydat jest niedostepny.",
            "candidate": serialize_victim_picker_candidate(candidate),
        }), 409

    aimed_target = clean_victim_picker_aimed_target(candidate)
    set_player_aimed_target(
        username,
        profile,
        aimed_target,
        reason="victim_picker_aim",
    )
    profile.pop("password", None)
    profile.pop("salt", None)
    session["profile"] = profile
    record_map_target_delta(
        username,
        aimed_target,
        change_type="map.target_updated",
        reason="victim_picker_aim",
    )
    return jsonify({
        "success": True,
        "status": "aimed_target_set",
        "message": f"Cel ustawiony: {display_target_label(aimed_target)}",
        "target": aimed_target,
        "candidate": serialize_victim_picker_candidate(candidate),
    })


def territory_control_load_profile(username, strip_sensitive=True):
    profile = load_profile_readonly(
        username,
        strip_sensitive=strip_sensitive,
        normalize_apps=True,
        normalize_files=False,
    )
    if not isinstance(profile, dict):
        return None
    return profile


def territory_control_forbidden_response():
    return jsonify({
        "success": False,
        "error": "territory_control_not_installed",
        "message": "Territory Control wymaga instalacji z Googleplex.",
    }), 403


@app.route("/api/ghost-control/territory")
@app.route("/api/pro-system/territory-control")
def territory_control_clusters():
    if "user" not in session:
        return jsonify({"success": False, "error": "not_logged_in"}), 401

    username = session["user"]
    profile = territory_control_load_profile(username)
    if not profile:
        return jsonify({"success": False, "error": "profile_not_found"}), 404
    if not territory_control_app_installed(profile):
        return territory_control_forbidden_response()

    snapshot = build_territory_control_snapshot(username, profile=profile)
    return jsonify({
        "success": True,
        "ok": True,
        **snapshot,
    })


@app.route("/api/ghost-control/territory/<cluster_id>")
@app.route("/api/pro-system/territory-control/<cluster_id>")
def territory_control_cluster_detail(cluster_id):
    if "user" not in session:
        return jsonify({"success": False, "error": "not_logged_in"}), 401

    username = session["user"]
    profile = territory_control_load_profile(username)
    if not profile:
        return jsonify({"success": False, "error": "profile_not_found"}), 404
    if not territory_control_app_installed(profile):
        return territory_control_forbidden_response()

    snapshot = build_territory_control_snapshot(username, profile=profile)
    cluster = territory_control_find_cluster(snapshot, cluster_id)
    if not cluster:
        return jsonify({
            "success": False,
            "error": "cluster_not_found",
            "cluster_id": str(cluster_id or ""),
            "clusters": snapshot.get("clusters", []),
            "alone_pillars": snapshot.get("alone_pillars", []),
        }), 404
    return jsonify({
        "success": True,
        "ok": True,
        "scope": "territory_control.cluster",
        "cluster": cluster,
    })


@app.route("/api/ghost-control/territory/security", methods=["POST"])
def territory_control_security_toggle():
    if "user" not in session:
        return jsonify({"success": False, "error": "not_logged_in"}), 401

    username = session["user"]
    data = request.get_json(silent=True) or {}
    action = str(data.get("action") or "").strip()
    label = data.get("label")
    try:
        lat = float(data.get("lat"))
        lng = float(data.get("lng", data.get("lon")))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "invalid_position"}), 400
    if not action:
        return jsonify({"success": False, "error": "missing_action"}), 400

    profile = territory_control_load_profile(username, strip_sensitive=False)
    if not profile:
        return jsonify({"success": False, "error": "profile_not_found"}), 404
    if not territory_control_app_installed(profile):
        return territory_control_forbidden_response()

    target = territory_control_find_owned_target(username, lat, lng, label=label)
    if not target:
        return jsonify({"success": False, "error": "target_not_found"}), 404

    security = dict(target.get("security") or {})
    security[action] = not bool(security.get(action, False))
    updated_target, updated = save_owned_hacked_security(username, lat, lng, security)
    if not updated:
        return jsonify({"success": False, "error": "security_save_failed"}), 500

    record_map_target_delta(
        username,
        updated_target or target,
        change_type="map.target_updated",
        reason="territory_control_security",
    )
    object_snapshot, snapshot = territory_control_object_snapshot(username, updated_target or target, profile=profile)
    summary = territory_control_security_summary(security)
    return jsonify({
        "success": True,
        "ok": True,
        "action": action,
        "new_value": security.get(action),
        "security": security,
        **summary,
        "disabled_rules": [],
        "object": object_snapshot,
        "snapshot": snapshot,
    })


@app.route("/api/ghost-control/territory/security-preset", methods=["POST"])
def territory_control_security_preset():
    if "user" not in session:
        return jsonify({"success": False, "error": "not_logged_in"}), 401

    username = session["user"]
    data = request.get_json(silent=True) or {}
    preset = str(data.get("preset") or "").strip().lower()
    label = data.get("label")
    try:
        lat = float(data.get("lat"))
        lng = float(data.get("lng", data.get("lon")))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "invalid_position"}), 400
    if preset not in TERRITORY_CONTROL_PRESETS:
        return jsonify({"success": False, "error": "invalid_preset", "preset": preset}), 400

    profile = territory_control_load_profile(username, strip_sensitive=False)
    if not profile:
        return jsonify({"success": False, "error": "profile_not_found"}), 404
    if not territory_control_app_installed(profile):
        return territory_control_forbidden_response()

    target = territory_control_find_owned_target(username, lat, lng, label=label)
    if not target:
        return jsonify({"success": False, "error": "target_not_found"}), 404

    try:
        security = build_security_preset(target.get("security", {}), preset)
    except ValueError as exc:
        return jsonify({"success": False, "error": "invalid_preset", "message": str(exc)}), 400

    updated_target, updated = save_owned_hacked_security(username, lat, lng, security)
    if not updated:
        return jsonify({"success": False, "error": "security_save_failed"}), 500

    record_map_target_delta(
        username,
        updated_target or target,
        change_type="map.target_updated",
        reason="territory_control_security_preset",
    )
    object_snapshot, snapshot = territory_control_object_snapshot(username, updated_target or target, profile=profile)
    summary = territory_control_security_summary(security)
    return jsonify({
        "success": True,
        "ok": True,
        "preset": preset,
        "security": security,
        **summary,
        "disabled_rules": [],
        "object": object_snapshot,
        "snapshot": snapshot,
    })


@app.route("/api/ghost-control/territory/abandon", methods=["POST"])
def territory_control_abandon():
    if "user" not in session:
        return jsonify({"success": False, "error": "not_logged_in"}), 401

    username = session["user"]
    data = request.get_json(silent=True) or {}
    if data.get("confirm") is not True:
        return jsonify({"success": False, "error": "confirmation_required"}), 409
    label = data.get("label")
    try:
        lat = float(data.get("lat"))
        lng = float(data.get("lng", data.get("lon")))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "invalid_position"}), 400

    profile = territory_control_load_profile(username, strip_sensitive=False)
    if not profile:
        return jsonify({"success": False, "error": "profile_not_found"}), 404
    if not territory_control_app_installed(profile):
        return territory_control_forbidden_response()

    target = territory_control_find_owned_target(username, lat, lng, label=label)
    if not target:
        return jsonify({"success": False, "error": "target_not_found"}), 404

    removed_from_store = territory_store.remove_captured_target(username, lat, lng, label=target.get("label"))
    if not removed_from_store:
        removed_from_store = territory_store.remove_captured_target(username, lat, lng)

    mgr = UserProfileManager(username)
    removed_from_profile = mgr.remove_from_list_by_coords("hacked", lat, lng, label=target.get("label"))
    if not removed_from_profile:
        removed_from_profile = mgr.remove_from_list_by_coords("hacked", lat, lng)

    clear_aimed_target_if_matches(username, target)
    rebuilt_areas = rebuild_player_areas_with_territory_delta(
        username,
        profile.get("level", 1),
        reason="territory_control_abandon",
    )
    all_areas = territory_store.list_player_areas()
    detect_territory_conflicts(
        actor_username=username,
        source_event="territory_control_abandon",
        areas=all_areas,
    )
    fresh_targets = territory_store.list_captured_targets(username)
    mgr.update_profile({
        "hacked": fresh_targets,
        "captured_targets_source": "sqlite",
    })
    record_map_target_delta(
        username,
        target,
        change_type="map.target_removed",
        reason="territory_control_abandon",
    )
    fresh_profile = territory_control_load_profile(username)
    snapshot = build_territory_control_snapshot(username, profile=fresh_profile)
    return jsonify({
        "success": True,
        "ok": True,
        "removed": bool(removed_from_store or removed_from_profile),
        "target": target,
        "rebuilt_area_count": len(rebuilt_areas or []),
        "snapshot": snapshot,
        "clusters": snapshot.get("clusters", []),
        "alone_pillars": snapshot.get("alone_pillars", []),
    })


@app.route("/api/map/friends")
def map_friends():
    if "user" not in session:
        return jsonify({"error": "Nie jesteś zalogowany"}), 401

    username = session["user"]
    friends = []
    for contact in mail_store.list_accepted_contacts(username):
        friend_profile = user_store.get_profile(contact.get("name", ""))
        if not friend_profile:
            continue

        position = friend_profile.get("curently_possition", {}) or {}
        lat = position.get("lat")
        lng = position.get("lng")
        if lat in (None, 0, 0.0) or lng in (None, 0, 0.0):
            continue

        friends.append({
            "username": friend_profile.get("username"),
            "nick": friend_profile.get("nick") or friend_profile.get("username"),
            "avatar": friend_profile.get("avatar", ""),
            "lat": lat,
            "lng": lng,
            "status": contact.get("status", "offline")
        })

    return jsonify({"friends": friends})


@app.route("/api/map/player-actors")
def map_player_actors():
    if "user" not in session:
        return jsonify({"error": "Nie jestes zalogowany"}), 401

    viewer_username = session["user"]
    viewer_profile = sync_session_profile(rebuild_territory=False)
    actors_by_username = {}
    aimed_target = viewer_profile.get("aimed_target") or {}
    aimed_player_username = (
        aimed_target.get("target_username")
        if aimed_target.get("target_mode") == "player"
        else None
    )
    territory_counts = {}
    viewer_area_ids = set()
    try:
        for area in territory_store.list_player_areas():
            clean_area = normalize_player_area(area)
            if not clean_area:
                continue
            owner_username = clean_area.get("owner_username") or clean_area.get("login")
            if owner_username:
                territory_counts[owner_username] = territory_counts.get(owner_username, 0) + 1
            if owner_username == viewer_username and clean_area.get("status", "active") == "active":
                area_id = clean_area.get("id")
                if area_id is not None:
                    viewer_area_ids.add(str(area_id))
    except Exception as exc:
        print(f"Nie udalo sie policzyc terytoriow player_actor: {exc}")

    def merge_actor(actor_profile, lat, lng, source, extra_context=None):
        if not actor_profile:
            return

        actor_username = actor_profile.get("username")
        if not actor_username or actor_username == viewer_username:
            return
        if lat in (None, 0, 0.0) or lng in (None, 0, 0.0):
            return

        existing = actors_by_username.get(actor_username)
        existing_context = (existing or {}).get("context", {})
        context = {
            **existing_context,
            **dict(extra_context or {}),
        }
        context["source"] = source
        context["sources"] = sorted(set(existing_context.get("sources", []) + [source]))
        context["is_friend"] = bool(context.get("is_friend") or existing_context.get("is_friend"))
        context["is_intruder"] = bool(context.get("is_intruder") or existing_context.get("is_intruder"))
        context["is_pending_contact"] = bool(
            context.get("is_pending_contact")
            or existing_context.get("is_pending_contact")
            or mail_store.has_pending_contact_request(viewer_username, actor_username)
        )
        context["is_marked_target"] = bool(
            context.get("is_marked_target")
            or existing_context.get("is_marked_target")
            or (aimed_player_username and aimed_player_username == actor_username)
        )
        if context["is_marked_target"]:
            context["target_status"] = "aimed"
        actor_clan = get_profile_clan(actor_profile)
        if actor_clan:
            context["clan"] = actor_clan
        context["level"] = actor_profile.get("level", context.get("level"))
        context["territory_count"] = territory_counts.get(actor_username, context.get("territory_count", 0))
        profession = (
            actor_profile.get("profession")
            or actor_profile.get("role")
            or (actor_profile.get("fraction") or {}).get("role")
            or (actor_profile.get("operator") or {}).get("profession")
            or ""
        )
        if profession:
            context["profession"] = profession

        actor_data = {
            "username": actor_username,
            "nick": actor_profile.get("nick") or actor_username,
            "avatar": actor_profile.get("avatar", ""),
            "lat": lat,
            "lng": lng,
            "status": context.get("contact_status", ""),
            "clan": context.get("clan", ""),
            "level": context.get("level"),
            "profession": context.get("profession", ""),
            "territory_count": context.get("territory_count", 0),
            "is_pending_contact": context.get("is_pending_contact", False),
            "is_marked_target": context.get("is_marked_target", False),
            "target_status": context.get("target_status", ""),
        }
        relation = resolve_player_actor_relation(viewer_profile, actor_profile, context)
        actors_by_username[actor_username] = build_player_actor(
            viewer_username,
            actor_data,
            relation=relation,
            context=context,
        )

    for contact in mail_store.list_accepted_contacts(viewer_username):
        actor_profile = user_store.get_profile(contact.get("name", ""))
        if not actor_profile:
            continue
        position = actor_profile.get("curently_possition", {}) or {}
        merge_actor(
            actor_profile,
            position.get("lat"),
            position.get("lng"),
            "friend",
            {
                "is_friend": True,
                "contact_status": contact.get("status", "offline"),
            },
        )

    for intruder in territory_store.list_recent_area_intruders(viewer_username):
        intruder_area_id = intruder.get("area_id")
        if intruder_area_id is not None and str(intruder_area_id) not in viewer_area_ids:
            continue
        actor_profile = user_store.get_profile(intruder.get("username"))
        if not actor_profile:
            continue
        merge_actor(
            actor_profile,
            intruder.get("lat"),
            intruder.get("lng"),
            "intruder",
            {
                "is_intruder": True,
                "area_id": intruder.get("area_id"),
                "created_at": intruder.get("created_at"),
            },
        )

    return jsonify({
        "player_actors": sorted(
            actors_by_username.values(),
            key=lambda actor: (actor.get("relation", ""), actor.get("nick") or actor.get("username") or ""),
        )
    })


@app.route("/api/map/player-areas")
def map_player_areas():
    if "user" not in session:
        return jsonify({"error": "Nie jesteś zalogowany"}), 401

    username = session["user"]
    profile = user_store.get_profile(username) or {}
    player_areas_warnings = []
    try:
        all_areas = safe_player_areas(territory_store.list_player_areas())
    except Exception as exc:
        print(f"[WARN] map player areas list failed: {exc}", flush=True)
        player_areas_warnings.append("areas_unavailable")
        all_areas = []
    # Keep this endpoint strictly read-only. Rebuilding stale polygons here can
    # run the full encirclement resolver during map boot and timeout a worker.
    if any(area.get("needs_rebuild") or area.get("stale") for area in all_areas):
        player_areas_warnings.append("stale_refresh_deferred")

    conflict_snapshot_mode = is_territory_conflict_snapshot_read_enabled()
    territory_conflict_snapshots = []
    active_conflicts_payload = []
    if conflict_snapshot_mode:
        try:
            territory_conflict_snapshots = [
                projected
                for projected in (
                    project_territory_conflict_snapshot(snapshot)
                    for snapshot in territory_conflict_store.list_latest_snapshots_for_player(username)
                )
                if projected
            ]
            (
                active_conflicts_payload,
                conflict_areas,
                revealed_conflict_targets,
                captured_conflict_pillars,
            ) = legacy_conflict_fields_from_snapshots(territory_conflict_snapshots)
        except Exception as exc:
            print(f"[WARN] map conflict snapshots skipped: {exc}", flush=True)
            player_areas_warnings.append("conflict_snapshots_unavailable")
            active_conflicts_payload = []
            conflict_areas = []
            revealed_conflict_targets = []
            captured_conflict_pillars = []
    else:
        try:
            active_conflicts = get_active_conflicts_for_player(username)
        except Exception as exc:
            print(f"[WARN] map player areas conflicts skipped: {exc}", flush=True)
            player_areas_warnings.append("conflicts_unavailable")
            active_conflicts = []
        for conflict in active_conflicts:
            try:
                active_conflicts_payload.append(enrich_conflict_payload(conflict))
            except Exception as exc:
                print(f"[WARN] map player areas conflict enrich skipped: {exc}", flush=True)
                player_areas_warnings.append("conflict_enrich_skipped")
        conflict_areas = []
        revealed_conflict_targets = []
        captured_conflict_pillars = []
        for conflict in active_conflicts_payload:
            if not isinstance(conflict, dict):
                continue
            conflict_areas.append(conflict)
            for item in (conflict.get("targets") or []):
                if not isinstance(item, dict):
                    continue
                target_payload = {
                    **item,
                    "conflict_id": conflict.get("conflict_id") or conflict.get("id"),
                    "conflict_key": conflict.get("conflict_key"),
                }
                revealed_conflict_targets.append(target_payload)
                if item.get("captured") or item.get("status") == "captured":
                    captured_conflict_pillars.append(target_payload)
    try:
        contested_targets = contested_targets_from_active_conflicts(
            username,
            active_conflicts_payload,
            all_areas,
        )
    except Exception as exc:
        print(f"[WARN] map player areas contested targets skipped: {exc}", flush=True)
        player_areas_warnings.append("contested_targets_unavailable")
        contested_targets = []
    areas = []
    owner_profile_cache = {username: profile}
    for area in all_areas:
        clean_area = normalize_player_area(area)
        if not clean_area:
            continue
        owner_username = clean_area.get("owner_username")
        owner_profile = owner_profile_cache.get(owner_username)
        if owner_profile is None:
            try:
                owner_profile = user_store.get_profile(owner_username)
            except Exception as exc:
                print(f"[WARN] map player area owner profile skipped: {owner_username} {exc}", flush=True)
                owner_profile = None
            owner_profile_cache[owner_username] = owner_profile
        if not owner_profile and owner_username != username:
            continue
        if not owner_profile:
            owner_profile = profile if owner_username == username else {}
        status = clean_area.get("status", "active")
        if status == "encircled":
            try:
                if territory_area_encircled_by_protected_owner(
                    clean_area,
                    all_areas,
                    profile_cache=owner_profile_cache,
                ):
                    status = "active"
            except Exception:
                # This is a tooltip/read-model correction only. Bad legacy
                # territory data must not break the critical map boot path.
                pass
        areas.append({
            "id": clean_area.get("id"),
            "owner_username": owner_username,
            "owner_nick": (owner_profile or {}).get("nick") or owner_username,
            "owner_clan": get_profile_clan(owner_profile or {}),
            "is_mine": owner_username == username,
            "vertices": clean_area.get("vertices", []),
            "centroid_lat": clean_area.get("centroid_lat"),
            "centroid_lng": clean_area.get("centroid_lng"),
            "area_size": clean_area.get("area_size"),
            "max_edge_distance": clean_area.get("max_edge_distance"),
            "status": status,
            "exposed": status == "encircled",
        })

    intruders = []
    try:
        recent_intruders = territory_store.list_recent_area_intruders(username)
    except Exception as exc:
        print(f"[WARN] map player areas intruders skipped: {exc}", flush=True)
        player_areas_warnings.append("intruders_unavailable")
        recent_intruders = []
    for intruder in recent_intruders:
        try:
            intruder_profile = user_store.get_profile(intruder.get("username"))
        except Exception:
            intruder_profile = None
        intruders.append({
            "area_id": intruder.get("area_id"),
            "username": intruder.get("username"),
            "nick": (intruder_profile or {}).get("nick") or intruder.get("payload", {}).get("actor_nick") or intruder.get("username"),
            "avatar": (intruder_profile or {}).get("avatar", ""),
            "lat": intruder.get("lat"),
            "lng": intruder.get("lng"),
            "created_at": intruder.get("created_at"),
        })

    return jsonify({
        "areas": areas,
        "player_areas": areas,
        "intruders": intruders,
        "territory_conflicts": active_conflicts_payload,
        "territory_conflict_snapshots": territory_conflict_snapshots,
        "territory_conflict_snapshot_mode": conflict_snapshot_mode,
        "conflict_areas": conflict_areas,
        "revealed_conflict_targets": revealed_conflict_targets,
        "captured_conflict_pillars": captured_conflict_pillars,
        "contested_targets": contested_targets,
        "warnings": player_areas_warnings,
        "player": {
            "level": get_player_level(profile),
            "action_range": get_player_action_range(profile),
            "map_zoom": get_player_map_zoom(profile),
            "min_map_zoom": get_player_min_map_zoom(profile)
        }
    })


@app.route("/api/map/incidents")
def map_incidents():
    if "user" not in session:
        return jsonify({"error": "Nie jestes zalogowany"}), 401

    return jsonify({
        "success": True,
        "scope": "incident",
        "incidents": incident_store.list_public(),
    })


@app.route("/api/map/incident-npc-capsules")
def map_incident_npc_capsules():
    if "user" not in session:
        return jsonify({"error": "Nie jestes zalogowany"}), 401

    try:
        active_incident_count = len(incident_store.list_active())
    except Exception:
        active_incident_count = None
    now_dt = datetime.now(timezone.utc)
    backfilled_actions = ensure_response_npc_capsules_for_active_incidents(session["user"])
    raw_capsules = npc_capsule_store.list_public()
    capsules = [
        capsule
        for capsule in raw_capsules
        if response_npc_capsule_runtime_active(capsule, now_dt)
    ]
    return jsonify({
        "success": True,
        "scope": "npc",
        "server_time": response_npc_runtime_iso(now_dt),
        "capsules": capsules,
        "debug": {
            "active_incident_count": active_incident_count,
            "backfilled_action_count": len(backfilled_actions or []),
            "raw_public_capsule_count": len(raw_capsules),
            "public_capsule_count": len(capsules),
            "expired_public_capsule_count": max(0, len(raw_capsules) - len(capsules)),
            "capsule_ids": [str(capsule.get("capsule_id") or "") for capsule in capsules[:8]],
            "capsule_runtime": [
                response_npc_public_capsule_debug(capsule, now_dt)
                for capsule in raw_capsules[:8]
            ],
        },
    })


def execute_response_network_consequence(decision):
    intent = consequence_policy.prepare_intent(decision)
    if intent.get("status") != "prepared":
        return intent

    actor_id = str(intent.get("actor_id") or "").strip()
    if not actor_id:
        return {
            "status": "rejected",
            "reason": "missing_actor",
            "consequence_executed": False,
            "penalty_executed": False,
        }

    profile = user_store.get_profile(actor_id)
    if not isinstance(profile, dict):
        return {
            "status": "rejected",
            "reason": "profile_not_found",
            "actor_id": actor_id,
            "consequence_executed": False,
            "penalty_executed": False,
        }

    def _cancel_operation(profile_arg, operation_id):
        return cancel_profile_operation(
            profile_arg,
            operation_id,
            cancelled_by="response_network",
        )

    def _refresh_operations(profile_arg):
        operations, changed = refresh_operations_runtime(
            profile_arg,
            persist_timeouts=False,
            username=actor_id,
        )
        if changed:
            profile_arg["operations"] = operations
        return operations

    previous_storage = storage_delta_snapshot(profile)
    previous_hc = profile.get("hackcoins")
    result = consequence_executor.execute(
        intent,
        profile,
        cancel_operation=_cancel_operation,
        refresh_operations=_refresh_operations,
        kill_switch_active=consequence_policy.kill_switch_active,
    )

    if result.get("status") in {"executed", "superseded", "rejected", "disabled"}:
        if result.get("status") == "executed":
            if result.get("confiscated_tools"):
                tool = result.get("confiscated_tool") if isinstance(result.get("confiscated_tool"), dict) else {}
                app_id = tool.get("app_id") or tool.get("app_name") or intent.get("operation_id")
                record_apps_delta(
                    actor_id,
                    profile,
                    "apps.app_uninstalled",
                    app_id=app_id,
                    reason="response_network_tool_confiscation",
                    dedupe_key=f"apps:uninstalled:{actor_id}:response_network:{result.get('consequence_id') or intent.get('consequence_id')}",
                    extra={"confiscated_tool": tool},
                )
            if result.get("confiscated_hc") and profile.get("hackcoins") != previous_hc:
                record_wallet_balance_delta(
                    actor_id,
                    profile.get("hackcoins", 0),
                    reason="response_network_hc_confiscation",
                    dedupe_key=f"wallet:balance:{actor_id}:response_network:{result.get('consequence_id') or intent.get('consequence_id')}",
                )
            record_storage_delta(
                actor_id,
                profile,
                reason="response_network_consequence",
                previous=previous_storage,
                dedupe_key_prefix=f"storage:{actor_id}:response_network:{result.get('consequence_id') or intent.get('consequence_id')}",
            )
        profile_update = {
            "operations": profile.get("operations", []),
            "apps": profile.get("apps", []),
            "files": profile.get("files", {}),
            "hackcoins": profile.get("hackcoins", 0),
            "risk_events": profile.get("risk_events", []),
            "system_messages": profile.get("system_messages", []),
            "market_history": profile.get("market_history", []),
            "confiscation_history": profile.get("confiscation_history", []),
            "judgment": profile.get("judgment", {}),
            "judgment_history": profile.get("judgment_history", []),
            "incident_history": profile.get("incident_history", []),
            "radio_events": profile.get("radio_events", []),
            "storage_capacity": profile.get("storage_capacity"),
            "storage_used": profile.get("storage_used"),
            "storage_unit": profile.get("storage_unit", "MB"),
            "storage_soft_limit": True,
            "storage_over_limit": profile.get("storage_over_limit", False),
        }
        if "wallet" in profile:
            profile_update["wallet"] = profile.get("wallet", profile.get("hackcoins", 0))
        UserProfileManager(actor_id).update_profile(profile_update)
        if session.get("user") == actor_id:
            session["profile"] = profile

    return result


@app.route("/api/map/incidents/detection-candidates", methods=["POST"])
def map_incident_detection_candidates():
    if "user" not in session:
        return jsonify({"success": False, "error": "not_logged_in"}), 401

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"success": False, "error": "invalid_payload"}), 400

    candidate = dict(payload)
    candidate["observer_username"] = session.get("user")
    candidate["mode"] = "full"
    try:
        decision = detection_validator.validate(candidate, profile_loader=load_profile_readonly)
    except Exception as exc:
        print(f"[DETECTION] full validation failed: {exc}", flush=True)
        return jsonify({
            "success": False,
            "mode": "full",
            "status": "rejected",
            "reason": "validation_error",
        }), 200

    consequence = None
    if decision.get("status") == "accepted":
        consequence = execute_response_network_consequence(decision)
        if consequence and consequence.get("status") == "executed":
            decision["consequence_executed"] = True
            decision["penalty_executed"] = bool(consequence.get("penalty_executed"))

    return jsonify({
        "success": True,
        "mode": decision.get("mode") or "full",
        "status": decision.get("status") or decision.get("result"),
        "reason": decision.get("reason"),
        "candidate_id": decision.get("candidate_id"),
        "penalty_executed": bool(decision.get("penalty_executed")),
        "consequence_executed": bool(decision.get("consequence_executed")),
        "consequence": {
            "status": consequence.get("status"),
            "reason": consequence.get("reason"),
            "consequence_id": consequence.get("consequence_id"),
            "operation_id": consequence.get("operation_id"),
            "consequence_executed": bool(consequence.get("consequence_executed")),
            "penalty_executed": bool(consequence.get("penalty_executed")),
            "confiscated_tools": bool(consequence.get("confiscated_tools")),
            "confiscated_hc": bool(consequence.get("confiscated_hc")),
            "judgment": bool(consequence.get("judgment")),
        } if isinstance(consequence, dict) else None,
    })


@app.route("/api/map/clan-vulnerabilities")
def map_clan_vulnerabilities():
    if "user" not in session:
        return jsonify({"error": "Nie jestes zalogowany"}), 401

    profile = sync_session_profile(rebuild_territory=False)
    username = session["user"]
    clan = get_profile_clan(profile)
    reports = []

    for report in vulnerability_store.list_active():
        item = dict(report)
        target = dict(item.get("target") or {})
        target["lat"] = item.get("lat")
        target["lng"] = item.get("lng")
        target["lon"] = item.get("lng")
        target["label"] = item.get("label")
        target["name"] = item.get("name")
        target["icon"] = item.get("icon")
        target["source_type"] = item.get("source_type")
        target["generated"] = item.get("generated")
        target["security"] = item.get("security", {})

        item["target"] = target
        item["is_reporter"] = item.get("reported_by_username") == username
        item["same_clan"] = bool(clan and item.get("reported_by_clan") == clan)
        reports.append(item)

    return jsonify({"vulnerabilities": reports})


@app.route("/api/vulnerabilities/potential", methods=["POST"])
def vulnerability_potential():
    if "user" not in session:
        return jsonify({"success": False, "message": "Nie jestes zalogowany."}), 401

    profile = sync_session_profile()
    payload = request.get_json() or {}
    target_security = resolve_target_security_for_vulnerability_check(profile, payload)
    potential = calculate_player_unlock_potential(profile, target_security)

    message = "Arsenal wystarcza do zgloszenia podatnosci."
    if not potential["can_report"]:
        message = (
            "Nie udalo sie wystawic podatnosci. "
            f"Arsenal pokrywa {potential['coverage_percent']}% aktywnych zabezpieczen, "
            f"wymagane {potential['threshold_percent']}%."
        )

    return jsonify({
        "success": True,
        "can_report": potential["can_report"],
        "message": message,
        "potential": potential,
        "security": target_security,
    })


@app.route("/api/vulnerabilities/report", methods=["POST"])
def report_vulnerability():
    if "user" not in session:
        return jsonify({"success": False, "message": "Nie jestes zalogowany."}), 401

    profile = sync_session_profile()
    username = session["user"]
    payload = request.get_json() or {}
    target = payload.get("target") or payload

    if not isinstance(target, dict):
        return jsonify({"success": False, "message": "Brak danych celu."}), 400

    try:
        lat = float(target.get("lat"))
        lng = float(target.get("lng", target.get("lon")))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Brak poprawnej pozycji celu."}), 400

    target["lat"] = lat
    target["lng"] = lng
    target["lon"] = lng
    target["label"] = str(target.get("label") or target.get("name") or "Cel")
    target["name"] = str(target.get("name") or target["label"])

    target_security = resolve_target_security_for_vulnerability_check(profile, {"target": target})
    potential = calculate_player_unlock_potential(profile, target_security)
    if not potential["can_report"]:
        return jsonify({
            "success": False,
            "can_report": False,
            "message": (
                "Nie udalo sie wystawic podatnosci. "
                f"Arsenal pokrywa {potential['coverage_percent']}% aktywnych zabezpieczen, "
                f"wymagane {potential['threshold_percent']}%."
            ),
            "potential": potential,
        }), 403

    clan = get_profile_clan(profile)
    security_template = resources_store.get("user_security", default={})
    report_security = build_minimal_target_security(security_template)
    territory = find_area_for_point(lat, lng)
    owner_username = (territory or {}).get("owner_username") or ""
    owner_clan = (territory or {}).get("owner_clan") or ""

    report = vulnerability_store.report(
        target,
        username,
        clan,
        report_security,
        territory_owner_username=owner_username,
        territory_owner_clan=owner_clan,
    )
    report["is_reporter"] = report.get("reported_by_username") == username
    report["same_clan"] = bool(clan and report.get("reported_by_clan") == clan)

    if owner_username and owner_username != username:
        same_clan = owner_clan and owner_clan == clan
        add_system_message_to_user(
            owner_username,
            "info" if same_clan else "warning",
            "Info: podatnosc na terytorium" if same_clan else "Alarm: obca podatnosc",
            (
                f"{profile.get('nick') or username} wystawil podatnosc celu "
                f"{target['label']} na twoim terytorium."
            )
        )

    return jsonify({
        "success": True,
        "message": f"Podatnosc celu {target['label']} wystawiona dla klanu.",
        "report": report,
        "potential": potential,
    })


@app.route("/api/vulnerabilities/<int:report_id>/withdraw", methods=["POST"])
def withdraw_vulnerability(report_id):
    if "user" not in session:
        return jsonify({"success": False, "message": "Nie jestes zalogowany."}), 401

    report = vulnerability_store.withdraw(report_id, session["user"])
    if not report:
        return jsonify({"success": False, "message": "Nie mozna wycofac tego oznaczenia."}), 403

    return jsonify({
        "success": True,
        "message": "Oznaczenie podatnosci wycofane.",
        "report": report,
    })


@app.route("/resources.json")
def resources():
    appsdata = get_app_catalog()

    profile = sync_session_profile()

    catalog = []
    for app in appsdata:
        if not app.get("published", True):
            continue
        catalog.append(googleplex_catalog_payload(app, profile))

    return jsonify(catalog)


@app.route("/api/radio/channel/<channel_id>")
def radio_channel_manifest(channel_id):
    safe_channel_id = re.sub(r"[^a-zA-Z0-9_\-]", "", str(channel_id or ""))
    if not safe_channel_id or safe_channel_id != channel_id:
        return jsonify({"success": False, "message": "Nieprawidlowy kanal radia."}), 400

    radio_root = os.path.abspath(os.path.join(app.static_folder, "mp3", "radio", "channel"))
    channel_dir = os.path.abspath(os.path.join(radio_root, safe_channel_id))
    if not channel_dir.startswith(radio_root + os.sep):
        return jsonify({"success": False, "message": "Nieprawidlowy kanal radia."}), 400

    meta_path = os.path.join(channel_dir, "meta.channel")
    if not os.path.isfile(meta_path):
        return jsonify({"success": False, "message": "Nie znaleziono kontraktu kanalu."}), 404

    try:
        with open(meta_path, "r", encoding="utf-8") as handle:
            channel = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return jsonify({"success": False, "message": "Nie udalo sie odczytac kontraktu kanalu."}), 500

    excluded = {str(item).casefold() for item in channel.get("exclude", []) if item}
    tracks = []
    try:
        for filename in os.listdir(channel_dir):
            if not filename.lower().endswith(".mp3"):
                continue
            if filename.casefold() in excluded:
                continue
            title = os.path.splitext(filename)[0].replace("_", " ").strip() or filename
            tracks.append({"title": title, "file": filename})
    except OSError:
        return jsonify({"success": False, "message": "Nie udalo sie odczytac katalogu kanalu."}), 500

    sort_mode = str(channel.get("sort") or "name").lower()
    if sort_mode in ("name", "filename", "title"):
        tracks.sort(key=lambda item: str(item["file"]).casefold())

    return jsonify({
        "success": True,
        "channel": channel,
        "tracks": tracks,
        "track_count": len(tracks),
    })


@app.route("/api/radio/channels")
def radio_channels_manifest():
    radio_root = os.path.abspath(os.path.join(app.static_folder, "mp3", "radio", "channel"))
    channels = []

    try:
        channel_ids = sorted(
            name for name in os.listdir(radio_root)
            if re.match(r"^[a-zA-Z0-9_\-]+$", name)
            and os.path.isdir(os.path.join(radio_root, name))
        )
    except OSError:
        return jsonify({"success": False, "message": "Nie udalo sie odczytac katalogu radia."}), 500

    for channel_id in channel_ids:
        meta_path = os.path.join(radio_root, channel_id, "meta.channel")
        if not os.path.isfile(meta_path):
            continue
        try:
            with open(meta_path, "r", encoding="utf-8") as handle:
                channel = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        try:
            schema = int(channel.get("schema") or 0)
        except (TypeError, ValueError):
            schema = 0
        if schema != 1:
            continue
        channels.append({
            "id": channel_id,
            "meta_id": channel.get("id") or channel_id,
            "name": channel.get("name") or channel_id,
            "slug": channel.get("slug") or channel_id,
            "description": channel.get("description") or "",
            "source": channel.get("source") or "unknown",
            "autoplay": channel.get("autoplay", True),
            "loop": channel.get("loop", True),
            "mode": channel.get("mode") or "ordered",
            "sort": channel.get("sort") or "name",
        })

    return jsonify({
        "success": True,
        "channels": channels,
        "default_channel": "ghost_streem_1",
        "count": len(channels),
    })


@app.route("/api/ghostlab/projects")
def ghostlab_projects():
    if "user" not in session:
        return jsonify({"success": False, "message": "Nie jestes zalogowany."}), 401

    profile = sync_session_profile()
    _, projects = get_profile_pro_system_projects(profile)
    return jsonify({
        "success": True,
        "projects": [serialize_ghostlab_project(project) for project in projects],
    })


@app.route("/api/ghostlab/projects", methods=["POST"])
def ghostlab_create_project():
    if "user" not in session:
        return jsonify({"success": False, "message": "Nie jestes zalogowany."}), 401

    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or "").strip()
    template_id = str(data.get("template_id") or "").strip()
    template_name = str(data.get("template_name") or "").strip()
    tool_category = str(data.get("tool_category") or "").strip()
    icon = str(data.get("icon") or "🧪").strip()[:8] or "🧪"
    if not name:
        return jsonify({"success": False, "message": "Podaj nazwe projektu."}), 400
    if len(name) > 64:
        return jsonify({"success": False, "message": "Nazwa projektu jest za dluga."}), 400
    if len(template_id) > 64 or len(template_name) > 80 or len(tool_category) > 40:
        return jsonify({"success": False, "message": "Metadane szablonu sa za dlugie."}), 400

    profile = sync_session_profile()
    files, projects = get_profile_pro_system_projects(profile)
    base_slug = ghostlab_project_slug(name)
    is_template_project = bool(template_id)
    slug = unique_ghostlab_project_slug(base_slug, projects) if is_template_project else base_slug
    if not is_template_project and any(str(project.get("slug") or "") == slug for project in projects):
        return jsonify({"success": False, "message": "Projekt o takiej nazwie juz istnieje."}), 400

    now = datetime.utcnow().isoformat(timespec="seconds")
    project = {
        "id": f"glp_{slug}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "name": name,
        "slug": slug,
        "icon": icon,
        "tool_category": tool_category,
        "template_id": template_id,
        "template_name": template_name,
        "blueprint": default_ghostlab_blueprint(template_id),
        "builds": [],
        "status": "draft",
        "created_at": now,
        "updated_at": now,
    }
    projects.append(project)
    files["pro_system_projects"] = projects
    UserProfileManager(session["user"]).update_profile({"files": files})
    session["profile"] = sync_session_profile(rebuild_territory=False)

    return jsonify({
        "success": True,
        "message": f"Utworzono projekt {name}.",
        "project": serialize_ghostlab_project(project),
        "projects": [serialize_ghostlab_project(item) for item in projects],
    })


@app.route("/api/ghostlab/projects/<project_id>", methods=["PATCH"])
def ghostlab_rename_project(project_id):
    if "user" not in session:
        return jsonify({"success": False, "message": "Nie jestes zalogowany."}), 401

    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "message": "Podaj nowa nazwe projektu."}), 400
    if len(name) > 64:
        return jsonify({"success": False, "message": "Nazwa projektu jest za dluga."}), 400

    profile = sync_session_profile()
    files, projects = get_profile_pro_system_projects(profile)
    project = next((item for item in projects if str(item.get("id")) == str(project_id)), None)
    if not project:
        return jsonify({"success": False, "message": "Nie znaleziono projektu."}), 404

    slug = ghostlab_project_slug(name)
    if any(str(item.get("id")) != str(project_id) and str(item.get("slug") or "") == slug for item in projects):
        return jsonify({"success": False, "message": "Projekt o takiej nazwie juz istnieje."}), 400

    project["name"] = name
    project["slug"] = slug
    project["updated_at"] = datetime.utcnow().isoformat(timespec="seconds")
    files["pro_system_projects"] = projects
    UserProfileManager(session["user"]).update_profile({"files": files})
    session["profile"] = sync_session_profile(rebuild_territory=False)

    return jsonify({
        "success": True,
        "message": f"Zmieniono nazwe projektu na {name}.",
        "project": serialize_ghostlab_project(project),
        "projects": [serialize_ghostlab_project(item) for item in projects],
    })


@app.route("/api/ghostlab/projects/<project_id>/blueprint", methods=["PATCH"])
def ghostlab_update_project_blueprint(project_id):
    if "user" not in session:
        return jsonify({"success": False, "message": "Nie jestes zalogowany."}), 401

    data = request.get_json(silent=True) or {}
    blueprint = data.get("blueprint")
    if not isinstance(blueprint, dict):
        return jsonify({"success": False, "message": "Blueprint musi byc obiektem."}), 400

    profile = sync_session_profile()
    files, projects = get_profile_pro_system_projects(profile)
    project = next((item for item in projects if str(item.get("id")) == str(project_id)), None)
    if not project:
        return jsonify({"success": False, "message": "Nie znaleziono projektu."}), 404

    validation = validate_ghostlab_blueprint(project.get("template_id"), blueprint)
    if not validation["valid"]:
        return jsonify({
            "success": False,
            "message": "Blueprint wymaga poprawek.",
            "validation": validation,
        }), 400

    project["blueprint"] = blueprint
    project["status"] = "draft"
    project["updated_at"] = datetime.utcnow().isoformat(timespec="seconds")
    files["pro_system_projects"] = projects
    UserProfileManager(session["user"]).update_profile({"files": files})
    session["profile"] = sync_session_profile(rebuild_territory=False)

    return jsonify({
        "success": True,
        "message": "Blueprint zapisany jako draft.",
        "project": serialize_ghostlab_project(project),
        "validation": validation,
        "projects": [serialize_ghostlab_project(item) for item in projects],
    })


@app.route("/api/ghostlab/projects/<project_id>/compile", methods=["POST"])
def ghostlab_compile_project(project_id):
    if "user" not in session:
        return jsonify({"success": False, "message": "Nie jestes zalogowany."}), 401

    data = request.get_json(silent=True) or {}
    profile = sync_session_profile()
    files, projects = get_profile_pro_system_projects(profile)
    project = next((item for item in projects if str(item.get("id")) == str(project_id)), None)
    if not project:
        return jsonify({"success": False, "message": "Nie znaleziono projektu."}), 404

    blueprint = data.get("blueprint")
    if blueprint is None:
        blueprint = project.get("blueprint") if isinstance(project.get("blueprint"), dict) else {}
    if not isinstance(blueprint, dict):
        return jsonify({"success": False, "message": "Blueprint musi byc obiektem."}), 400

    validation = validate_ghostlab_blueprint(project.get("template_id"), blueprint)
    if not validation["valid"]:
        return jsonify({
            "success": False,
            "message": "Compile zatrzymany. Blueprint wymaga poprawek.",
            "validation": validation,
        }), 400

    builds = project.get("builds") if isinstance(project.get("builds"), list) else []
    version = len(builds) + 1
    artifact = build_ghostlab_artifact(project, blueprint, version)
    build = {
        "version": version,
        "created_at": artifact["compiled_at"],
        "status": "compiled",
        "artifact_id": artifact["artifact_id"],
        "template_id": artifact["template_id"],
    }
    builds.append(build)
    project["blueprint"] = blueprint
    project["builds"] = builds
    project["artifact"] = artifact
    project["status"] = "compiled"
    project["updated_at"] = datetime.utcnow().isoformat(timespec="seconds")
    files["pro_system_projects"] = projects
    UserProfileManager(session["user"]).update_profile({"files": files})
    session["profile"] = sync_session_profile(rebuild_territory=False)

    return jsonify({
        "success": True,
        "message": f"Build v{version} skompilowany. Artefakt zapisany w projekcie.",
        "project": serialize_ghostlab_project(project),
        "build": build,
        "artifact": artifact,
        "validation": validation,
        "projects": [serialize_ghostlab_project(item) for item in projects],
    })


@app.route("/api/ghostlab/projects/<project_id>/export")
def ghostlab_export_project(project_id):
    if "user" not in session:
        return jsonify({"success": False, "message": "Nie jestes zalogowany."}), 401

    profile = sync_session_profile()
    _, projects = get_profile_pro_system_projects(profile)
    project = next((item for item in projects if str(item.get("id")) == str(project_id)), None)
    if not project:
        return jsonify({"success": False, "message": "Nie znaleziono projektu."}), 404

    serialized = serialize_ghostlab_project(project)
    snapshot = {
        "format": "ghostlab-project",
        "format_version": 1,
        "exported_at": datetime.utcnow().isoformat(timespec="seconds"),
        "owner": session["user"],
        "project": serialized,
    }
    filename = f"{serialized.get('slug') or 'ghost_project'}.glab"
    body = json.dumps(snapshot, ensure_ascii=False, indent=2)
    return Response(
        body,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/api/ghostlab/projects/<project_id>/publisher", methods=["POST"])
def ghostlab_publish_project(project_id):
    if "user" not in session:
        return jsonify({"success": False, "message": "Nie jestes zalogowany."}), 401

    profile = sync_session_profile()
    files, projects = get_profile_pro_system_projects(profile)
    project = next((item for item in projects if str(item.get("id")) == str(project_id)), None)
    if not project:
        return jsonify({"success": False, "message": "Nie znaleziono projektu."}), 404

    blueprint = project.get("blueprint") if isinstance(project.get("blueprint"), dict) else {}
    validation = validate_ghostlab_blueprint(project.get("template_id"), blueprint)
    if not validation["valid"]:
        return jsonify({
            "success": False,
            "message": "Publisher zatrzymany. Blueprint wymaga poprawek.",
            "validation": validation,
        }), 400

    builds = project.get("builds") if isinstance(project.get("builds"), list) else []
    artifact = project.get("artifact") if isinstance(project.get("artifact"), dict) else {}
    if not builds or not artifact:
        return jsonify({
            "success": False,
            "message": "Publisher wymaga skompilowanego artefaktu. Uruchom Compile.",
        }), 400

    app_data = build_ghostlab_googleplex_app(project, session["user"], profile)
    if not app_data:
        return jsonify({"success": False, "message": "Nie udalo sie zbudowac rekordu Googleplex."}), 400

    store = resources_store.get("app_config", default=[]) or []
    existing_same_name = next((
        app for app in store
        if str(app.get("id")) != str(app_data["id"])
        and str(app.get("name") or "").strip().lower() == app_data["name"].strip().lower()
    ), None)
    if existing_same_name:
        return jsonify({
            "success": False,
            "message": "W Googleplex istnieje juz aplikacja o takiej nazwie.",
        }), 400

    replaced = False
    updated_store = []
    for app in store:
        if str(app.get("id")) == str(app_data["id"]):
            previous_downloads = int(app.get("downloads") or 0)
            app_data["downloads"] = previous_downloads
            updated_store.append(app_data)
            replaced = True
        else:
            updated_store.append(app)
    if not replaced:
        updated_store.append(app_data)
    resources_store.set("app_config", updated_store)

    now = datetime.utcnow().isoformat(timespec="seconds")
    project["googleplex_app_id"] = app_data["id"]
    project["published_at"] = now
    project["status"] = "published"
    project["updated_at"] = now
    files["pro_system_projects"] = projects
    UserProfileManager(session["user"]).update_profile({"files": files})
    session["profile"] = sync_session_profile(rebuild_territory=False)

    return jsonify({
        "success": True,
        "message": "Publisher zakonczony. Artefakt trafil do Googleplex jako pro-system-tool.",
        "project": serialize_ghostlab_project(project),
        "app": app_data,
        "projects": [serialize_ghostlab_project(item) for item in projects],
    })


@app.route("/api/ghostlab/projects/<project_id>", methods=["DELETE"])
def ghostlab_delete_project(project_id):
    if "user" not in session:
        return jsonify({"success": False, "message": "Nie jestes zalogowany."}), 401

    profile = sync_session_profile()
    files, projects = get_profile_pro_system_projects(profile)
    kept = [item for item in projects if str(item.get("id")) != str(project_id)]
    if len(kept) == len(projects):
        return jsonify({"success": False, "message": "Nie znaleziono projektu."}), 404

    files["pro_system_projects"] = kept
    UserProfileManager(session["user"]).update_profile({"files": files})
    session["profile"] = sync_session_profile(rebuild_territory=False)

    return jsonify({
        "success": True,
        "message": "Projekt usuniety.",
        "projects": [serialize_ghostlab_project(item) for item in kept],
    })


@app.route("/api/apps/generate", methods=["POST"])
def generate_app():
    if "user" not in session:
        return jsonify({"success": False, "message": "Nie jestes zalogowany."}), 401

    profile = sync_session_profile()
    creator_username = session["user"]
    creator_nick = profile.get("nick") or creator_username

    try:
        app_data = build_generated_app(request.get_json() or {}, creator_username, creator_nick)
    except (TypeError, ValueError) as e:
        return jsonify({"success": False, "message": str(e)}), 400

    store = resources_store.get("app_config", default=[])
    if any(app.get("name", "").lower() == app_data["name"].lower() for app in store):
        return jsonify({"success": False, "message": "Aplikacja o takiej nazwie juz istnieje."}), 400

    store.append(app_data)
    resources_store.set("app_config", store)

    files = profile.get("files", {})
    projects = files.get("projects", [])
    project_file = app_data["project_file"]
    if project_file not in projects:
        projects.append(project_file)
    files["projects"] = projects

    mgr = UserProfileManager(creator_username)
    mgr.update_profile({"files": files})
    sync_session_profile()

    return jsonify({
        "success": True,
        "message": f"Opublikowano {app_data['name']} w Googleplex.",
        "app": app_data
    })


@app.route("/api/apps/generated/<path:project_file>", methods=["DELETE"])
def remove_generated_app(project_file):
    if "user" not in session:
        return jsonify({"success": False, "message": "Nie jestes zalogowany."}), 401

    username = session["user"]
    store = resources_store.get("app_config", default=[])
    app_data = next((
        app for app in store
        if app.get("project_file") == project_file and app.get("creator_username") == username
    ), None)

    if not app_data:
        return jsonify({"success": False, "message": "Nie znaleziono projektu autora."}), 404

    store = [app for app in store if app.get("id") != app_data.get("id")]
    resources_store.set("app_config", store)

    profile = sync_session_profile()
    files = profile.get("files", {})
    projects = files.get("projects", [])
    files["projects"] = [item for item in projects if item != project_file]
    mgr = UserProfileManager(username)
    mgr.update_profile({"files": files})
    sync_session_profile()

    return jsonify({
        "success": True,
        "message": f"Wycofano {app_data['name']} z Googleplex. Zainstalowane kopie pozostaja aktywne."
    })

@app.route("/files/<folder>")
def get_folder_contents(folder):
    # plik JSON zawierający strukturę folderów
    data = resources_store.get(
        "files_data",
        default={}
    )

    return jsonify(data.get(folder, []))  # zwróć listę plików w folderze

@app.route("/messages.json")
def messages():
    return jsonify(resources_store.get(
        "messages",
        default=[]
    ))

@app.route("/friends.json")
def friends():
    return jsonify(resources_store.get(
        "friends",
        default=[]
    ))

def ensure_mail_seed(profile=None):
    username = session.get("user")
    if not username:
        return None

    if profile is None:
        profile = sync_session_profile()

    default_messages = resources_store.get(
        "messages",
        default=[]
    )
    mail_store.ensure_seeded(username, profile, [], default_messages)
    mail_store.remove_contacts_without_users(username)
    return username


def build_cyberner_channels(profile, contacts, group_active_count, accepted_contacts=None):
    """Build singleton channel read model without storing channels as contacts."""
    contact_count = len(contacts or [])
    accepted_count = len(accepted_contacts or [])
    channels = [
        {
            "source": "world",
            "channel": "world",
            "scope": "group",
            "peer": "global",
            "title": "WORLD",
            "subtitle": "Publiczny kanal swiata gry",
            "preview": "Publiczny kanal online graczy",
            "enabled": True,
            "active_count": int(group_active_count or 0),
            "meta": f"{int(group_active_count or 0)} online",
        },
        {
            "source": "friends",
            "channel": "friends",
            "scope": "channel",
            "peer": "friends",
            "title": "ZNAJOMI",
            "subtitle": "Kanal kontaktow gracza",
            "preview": "Wspolny kanal zaakceptowanych kontaktow",
            "enabled": True,
            "meta": f"{accepted_count} znajomych",
            "contacts_count": contact_count,
            "accepted_contacts_count": accepted_count,
        },
    ]

    clan = get_profile_clan(profile or {})
    if clan:
        channels.append({
            "source": "clan",
            "channel": "clan",
            "scope": "channel",
            "peer": f"clan:{clan}",
            "title": "KLAN",
            "subtitle": f"Kanal klanu {clan}",
            "preview": "Wspolny kanal czlonkow klanu",
            "enabled": True,
            "meta": clan,
            "clan": clan,
        })

    return channels


def cyberner_channel_recipients(username, profile, peer_name):
    """Resolve Cyberner channel recipients without storing channels as contacts."""
    peer_name = str(peer_name or "").strip()
    if peer_name == "friends":
        return [
            contact.get("name")
            for contact in mail_store.list_accepted_contacts(username)
            if contact.get("name")
        ]

    if peer_name.startswith("clan:"):
        clan = get_profile_clan(profile or {})
        requested_clan = peer_name.split(":", 1)[1].strip()
        if not clan or requested_clan != clan:
            raise ValueError("Kanal klanu jest niedostepny.")

        recipients = []
        for item in user_store.list_profiles():
            other_username = item.get("username")
            if not other_username or other_username == username:
                continue
            if get_profile_clan(item) == clan:
                recipients.append(other_username)
        return recipients

    raise ValueError("Nieznany kanal Cybernera.")


def cyberner_message_recipients(username, profile, scope, peer_name):
    if scope == "group":
        return [
            contact.get("name")
            for contact in mail_store.list_contacts(username)
            if contact.get("name") and contact.get("name") != username
        ]
    if scope == "channel":
        return cyberner_channel_recipients(username, profile, peer_name)
    if scope == "direct":
        peer_name = str(peer_name or "").strip()
        if peer_name and peer_name != username and user_store.get_profile(peer_name):
            return [peer_name]
    return []


@app.route("/api/mail/bootstrap")
def mail_bootstrap():
    if "user" not in session:
        return jsonify({"error": "Brak danych użytkownika"}), 401

    username = session.get("user")
    profile = load_profile_readonly(username, strip_sensitive=True)
    if not profile:
        session.pop("user", None)
        session.pop("profile", None)
        return jsonify({"ok": False, "error": "profile_not_found"}), 401
    username = ensure_mail_seed(profile)
    mail_store.touch_presence(username)
    contacts = mail_store.list_contacts(username)
    accepted_contacts = mail_store.list_accepted_contacts(username)
    pending_threads = mail_store.list_pending_threads(username)
    group_messages = mail_store.list_messages(username, "group", "global")
    group_active_count = mail_store.group_active_count(username)

    return jsonify({
        "username": username,
        "channels": build_cyberner_channels(profile, contacts, group_active_count, accepted_contacts),
        "contacts": contacts,
        "pending_threads": pending_threads,
        "group_messages": group_messages,
        "unread_counts": mail_store.unread_counts(username),
        "group_active_count": group_active_count
    })

@app.route("/api/contacts", methods=["POST"])
def add_contact():
    if "user" not in session:
        return jsonify({"error": "Nie jesteś zalogowany"}), 401

    username = ensure_mail_seed()
    data = request.get_json() or {}
    contact_name = data.get("name", "")
    status = data.get("status", "offline")

    try:
        mail_store.add_contact(username, contact_name, status)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"success": True, "contacts": mail_store.list_contacts(username)})

@app.route("/api/player-contact/request", methods=["POST"])
def request_player_contact():
    if "user" not in session:
        return jsonify({"success": False, "error": "Nie jestes zalogowany"}), 401

    username = ensure_mail_seed()
    data = request.get_json() or {}
    target_username = str(data.get("target_username") or "").strip()

    if not target_username:
        return jsonify({"success": False, "error": "Brak nazwy gracza."}), 400
    if target_username == username:
        return jsonify({"success": False, "error": "Nie mozesz dodac samego siebie."}), 400

    target_profile = user_store.get_profile(target_username)
    if not target_profile:
        return jsonify({"success": False, "error": "Nie ma takiego uzytkownika."}), 404

    if mail_store.is_accepted_contact(username, target_username):
        return jsonify({
            "success": True,
            "status": "already_friend",
            "message": "Ten gracz jest juz na liscie znajomych.",
            "contacts": mail_store.list_contacts(username),
        })
    if mail_store.is_contact(username, target_username):
        return jsonify({
            "success": True,
            "status": "already_pending",
            "message": "Zaproszenie juz oczekuje.",
            "contacts": mail_store.list_contacts(username),
        })
    if mail_store.is_contact(target_username, username):
        mail_store.add_contact(username, target_username)
        return jsonify({
            "success": True,
            "status": "already_friend",
            "message": "Ten gracz jest juz na liscie znajomych.",
            "contacts": mail_store.list_contacts(username),
        })

    if mail_store.has_pending_contact_request(username, target_username):
        return jsonify({
            "success": True,
            "status": "already_pending",
            "message": "Zaproszenie juz oczekuje.",
            "contacts": mail_store.list_contacts(username),
        })

    requester_profile = user_store.get_profile(username) or {}
    requester_nick = requester_profile.get("nick") or username
    add_cyberner_direct_notification(
        target_username,
        username,
        requester_nick,
        "Gest przywitania",
        f"👋 {requester_nick} wysyla Ci gest przywitania. Odpowiedz, zeby dodac go do znajomych."
    )

    return jsonify({
        "success": True,
        "status": "requested",
        "message": f"Wyslano gest przywitania do {target_profile.get('nick') or target_username}.",
        "contacts": mail_store.list_contacts(username),
    })

@app.route("/api/contacts/<contact_name>", methods=["DELETE"])
def remove_contact(contact_name):
    if "user" not in session:
        return jsonify({"error": "Nie jesteś zalogowany"}), 401

    username = ensure_mail_seed()
    mail_store.remove_contact(username, contact_name)
    return jsonify({"success": True, "contacts": mail_store.list_contacts(username)})

@app.route("/api/chats/messages")
def chat_messages():
    if "user" not in session:
        return jsonify({"error": "Nie jesteś zalogowany"}), 401

    username = session.get("user")
    profile = load_profile_readonly(username, strip_sensitive=True)
    if not profile:
        session.pop("user", None)
        session.pop("profile", None)
        return jsonify({"error": "profile_not_found"}), 401
    username = ensure_mail_seed(profile)
    scope = request.args.get("scope", "group")
    peer_name = request.args.get("peer", "global" if scope == "group" else "")

    try:
        if scope == "channel":
            cyberner_channel_recipients(username, profile, peer_name)
        messages = mail_store.list_messages(username, scope, peer_name)
        mail_store.mark_thread_read(username, scope, peer_name)
        record_mail_delta(
            username,
            "mail.unread_changed",
            scope=scope,
            peer_name=peer_name,
            reason="thread_read",
            dedupe_key=f"mail:unread_read:{username}:{mail_delta_thread_key(scope, peer_name)}:{runtime_file_now()}",
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "messages": messages,
        "unread_counts": mail_store.unread_counts(username),
        "group_active_count": mail_store.group_active_count(username)
    })

@app.route("/api/chats/messages", methods=["POST"])
def send_chat_message():
    if "user" not in session:
        return jsonify({"error": "Nie jesteś zalogowany"}), 401

    username = session.get("user")
    profile = load_profile_readonly(username, strip_sensitive=True)
    if not profile:
        session.pop("user", None)
        session.pop("profile", None)
        return jsonify({"error": "profile_not_found"}), 401
    username = ensure_mail_seed(profile)
    data = request.get_json() or {}
    scope = data.get("scope", "group")
    peer_name = data.get("peer", "global" if scope == "group" else "")
    body = data.get("body", "")

    try:
        channel_recipients = None
        notification_recipients = cyberner_message_recipients(username, profile, scope, peer_name)
        if scope == "channel":
            channel_recipients = notification_recipients
        auto_add_contact = scope == "direct" and not mail_store.is_contact(username, peer_name)
        mail_store.add_message(
            username,
            scope,
            peer_name,
            username,
            body,
            auto_add_contact=auto_add_contact,
            channel_recipients=channel_recipients,
        )
        sender_message = latest_mail_message(username, scope, "global" if scope == "group" else peer_name)
        record_mail_thread_update(
            username,
            scope,
            "global" if scope == "group" else peer_name,
            message=sender_message,
            reason="message_sent",
        )
        for recipient_name in notification_recipients:
            add_cyberner_notification_to_user(
                recipient_name,
                scope,
                "global" if scope == "group" else peer_name,
                username,
            )
            recipient_peer = "global" if scope == "group" else (username if scope == "direct" else peer_name)
            recipient_message = latest_mail_message(recipient_name, scope, recipient_peer)
            record_mail_thread_update(
                recipient_name,
                scope,
                recipient_peer,
                message=recipient_message,
                reason="message_received",
            )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    messages = mail_store.list_messages(username, scope, "global" if scope == "group" else peer_name)
    return jsonify({
        "success": True,
        "messages": messages,
        "contacts": mail_store.list_contacts(username),
        "pending_threads": mail_store.list_pending_threads(username),
        "unread_counts": mail_store.unread_counts(username),
        "group_active_count": mail_store.group_active_count(username)
    })

@app.route('/system-messages')
def get_system_messages():
    if "user" not in session:
        return jsonify([])

    profile = load_profile_readonly(session["user"], normalize_apps=False, normalize_files=False)
    if not profile:
        session.clear()
        return jsonify({"logout": True})

    legacy_new = [
        message for message in profile.get("system_messages", []) or []
        if isinstance(message, dict) and message.get("status") == "new"
    ]
    if legacy_new:
        system_message_store.add_messages(session["user"], legacy_new, source="legacy_profile")

    new_msgs = system_message_store.consume_pending(session["user"])
    return jsonify(new_msgs)

@app.route('/add-system-message', methods=['POST'])
def add_system_message():
    if "user" not in session:
        return jsonify({"error": "Nie jesteś zalogowany"}), 401

    data = request.get_json()
    msg_type = data.get("type")
    title = data.get("title")
    text = data.get("text")

    if not all([msg_type, title, text]):
        return jsonify({"error": "Brakuje danych: type, title, text"}), 400

    dedupe_key = data.get("dedupe_key") or f"manual:{session['user']}:{msg_type}:{title}:{hashlib.sha1(str(text or '').encode('utf-8', errors='ignore')).hexdigest()[:16]}"
    new_msg = {
        "type": msg_type,
        "title": title,
        "text": text,
        "body": text,
        "status": "new",
        "source": "api",
        "dedupe_key": dedupe_key,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _, created = system_message_store.add_message(session["user"], new_msg, source="api")
    duplicate_pending = not created
    hack_flow_debug(
        request.headers.get("X-Hack-Flow-Id") or request.headers.get("X-Client-Action-Key") or "",
        "system_message_request",
        user=session.get("user"),
        msg_type=msg_type,
        title=title,
        text_hash=hashlib.sha1(str(text or "").encode("utf-8", errors="ignore")).hexdigest()[:12],
        duplicate=duplicate_pending,
        pending_count=0,
    )
    if duplicate_pending:
        return jsonify({"status": "success", "duplicate": True, "message": "Wiadomosc juz czeka"})

    return jsonify({"status": "success", "message": "Wiadomość dodana"})


@app.route('/install-app', methods=['POST'])
def install_app():
    try:
        if "user" not in session:
            return jsonify({"status": "error", "message": "Nie jestes zalogowany."}), 401

        data = request.get_json() or {}
        app_id = data.get("app_id")
        store = resources_store.get(
            "app_config",
            default=[]
        )
        catalog = get_app_catalog()

        app_data = next((app for app in catalog if app.get("id") == app_id), None)
        if not app_data:
            print(f"[ERROR] Nie znaleziono aplikacji o ID: {app_id}")
            return jsonify({"status": "error", "message": "App not found"})

        # --- Pobierz i zsynchronizuj aktualny profil ---
        profile = sync_session_profile()
        previous_storage = storage_delta_snapshot(profile)
        mgr = UserProfileManager(session["user"])
        apps = profile.get("apps", [])
        is_product = is_googleplex_product(app_data)
        if is_product and not app_data.get("consumable") and googleplex_product_is_purchased(profile, app_id):
            return jsonify({
                "status": "error",
                "reason": "already_purchased",
                "message": "Produkt jest juz kupiony."
            }), 409
        if not is_product and any(a.get("id") == app_id for a in apps):
            return jsonify({
                "status": "error",
                "reason": "already_installed",
                "message": "Aplikacja jest juz kupiona."
            }), 409

        requirement_error = validate_app_install_requirements(app_data, profile)
        if requirement_error:
            return jsonify({"status": "error", "message": requirement_error})

        buyer_username = session["user"]
        buyer_name = profile.get("nick") or buyer_username
        price = max(0, int(app_data.get("price") or 0))
        creator_username = (app_data.get("creator_username") or "").strip()
        purchase_account = str(app_data.get("purchase_account") or "").strip()
        payee_username = purchase_account or creator_username or "admin"
        payee_profile = (
            ensure_purchase_account_profile(payee_username)
            if purchase_account
            else user_store.get_profile(payee_username)
        )

        if not payee_profile and payee_username != "admin":
            payee_username = "admin"
            payee_profile = user_store.get_profile(payee_username)

        if price > 0:
            if not payee_profile and payee_username != buyer_username:
                return jsonify({
                    "status": "error",
                    "message": "Brak odbiorcy platnosci. Skontaktuj sie z adminem."
                })

            if int(profile.get("hackcoins", 0) or 0) < price:
                return jsonify({
                    "status": "error",
                    "reason": "insufficient_hc",
                    "message": f"Brak HC. Cena: {price}, masz: {profile.get('hackcoins', 0)}."
                })

            profile["hackcoins"] = int(profile.get("hackcoins", 0) or 0) - price

            if payee_profile and payee_username != buyer_username:
                payee_profile["hackcoins"] = int(payee_profile.get("hackcoins", 0) or 0) + price
                user_store.save_profile(payee_profile)
                add_cyberner_direct_notification(
                    payee_username,
                    "Googolplex",
                    "Googolplex",
                    "Wpłata za aplikację",
                    f"{buyer_name} kupił aplikację {app_data['name']} za {price} HackCoinów."
                )
            elif payee_username == buyer_username:
                profile["hackcoins"] = int(profile.get("hackcoins", 0) or 0) + price

        if is_product:
            effect_result = apply_googleplex_product_effect(profile, app_data, username=buyer_username)
            purchases = profile.setdefault("googleplex_products", [])
            if not isinstance(purchases, list):
                purchases = []
                profile["googleplex_products"] = purchases
            product_purchases = profile.setdefault("product_purchases", [])
            if not isinstance(product_purchases, list):
                product_purchases = []
                profile["product_purchases"] = product_purchases
            purchase_record = {
                "id": app_id,
                "name": app_data.get("name"),
                "product_type": app_data.get("product_type"),
                "category": app_data.get("category"),
                "effects": effect_result.get("applied", []),
                "price": price,
                "consumable": bool(app_data.get("consumable")),
                "purchased_at": runtime_file_now(),
            }
            purchases.append(purchase_record)
            product_purchases.append(dict(purchase_record))
            if app_data.get("product_type") == "storage_upgrade":
                upgrades = profile.setdefault("storage_upgrades", [])
                if not isinstance(upgrades, list):
                    upgrades = []
                    profile["storage_upgrades"] = upgrades
                if not any(isinstance(item, dict) and item.get("id") == app_id for item in upgrades):
                    storage_effect = next(
                        (item for item in effect_result.get("applied", []) if item.get("type") == "storage_capacity_bonus"),
                        {},
                    )
                    upgrades.append({
                        "id": app_id,
                        "name": app_data.get("name"),
                        "storage_capacity_bonus": storage_effect.get("value") or app_data.get("storage_capacity_bonus"),
                        "price": price,
                        "purchased_at": purchase_record["purchased_at"],
                    })
            system_message_store.add_message(buyer_username, {
                "title": "Zakup Googleplex",
                "text": f"Produkt <b>{app_data['name']}</b> zostal aktywowany.",
                "type": "success",
                "status": "new",
                "product_id": app_id,
                "effects": effect_result.get("applied", []),
                "dedupe_key": f"googleplex_product:{buyer_username}:{app_id}:{purchase_record['purchased_at']}",
            }, source="googleplex_product")
            update_payload = {
                "hackcoins": profile.get("hackcoins", 0),
                "storage_capacity": profile.get("storage_capacity"),
                "storage_used": profile.get("storage_used"),
                "storage_unit": profile.get("storage_unit", "MB"),
                "storage_soft_limit": True,
                "storage_over_limit": profile.get("storage_over_limit", False),
                "storage_upgrades": profile.get("storage_upgrades", []),
                "googleplex_products": purchases,
                "product_purchases": product_purchases,
                "curently_possition": profile.get("curently_possition"),
                "current_city": profile.get("current_city"),
                "map_zoom_bonus": profile.get("map_zoom_bonus", 0),
                "scan_range_bonus": profile.get("scan_range_bonus", 0),
                "bike_range_bonus": profile.get("bike_range_bonus", 0),
            }
            mgr.update_profile(update_payload)
            record_storage_delta(
                buyer_username,
                profile,
                reason="googleplex_product_purchase",
                previous=previous_storage,
                dedupe_key_prefix=f"storage:{buyer_username}:googleplex_product:{app_id}:{purchase_record.get('purchased_at')}",
            )
            record_wallet_balance_delta(
                buyer_username,
                profile.get("hackcoins", 0),
                reason="googleplex_product_purchase",
                dedupe_key=f"wallet:balance:{buyer_username}:googleplex_product:{app_id}:{purchase_record.get('purchased_at')}",
            )
            if any(item.get("type") == "travel_city" for item in effect_result.get("applied", [])):
                record_map_player_actor_delta(
                    buyer_username,
                    profile,
                    change_type="map.player_moved",
                    reason="googleplex_travel_product",
                    dedupe_key_prefix=f"map:player_actor:{buyer_username}:googleplex_travel:{app_id}:{purchase_record.get('purchased_at')}",
                )
            if payee_profile and payee_username != buyer_username:
                record_wallet_balance_delta(
                    payee_username,
                    payee_profile.get("hackcoins", 0),
                    reason="googleplex_product_sale",
                    dedupe_key=f"wallet:balance:{payee_username}:googleplex_product_sale:{buyer_username}:{app_id}:{purchase_record.get('purchased_at')}",
                )
            session["profile"] = sync_session_profile(rebuild_territory=False)
            return jsonify({
                "status": "success",
                "message": "Produkt zostal kupiony.",
                "hackcoins": profile.get("hackcoins", 0),
                "price": price,
                "paid_to": payee_username if price > 0 else None,
                "storage": {
                    "capacity": profile.get("storage_capacity"),
                    "used": profile.get("storage_used"),
                    "unit": profile.get("storage_unit", "MB"),
                    "added": next(
                        (item.get("value") for item in effect_result.get("applied", []) if item.get("type") == "storage_capacity_bonus"),
                        0,
                    ),
                    "soft_limit": True,
                    "over_limit": profile.get("storage_over_limit", False),
                },
                "product": purchase_record,
                "effects": effect_result.get("applied", []),
                "storage_upgrade": {
                    "id": app_id,
                    "name": app_data.get("name"),
                    "storage_capacity_bonus": next(
                        (item.get("value") for item in effect_result.get("applied", []) if item.get("type") == "storage_capacity_bonus"),
                        app_data.get("storage_capacity_bonus", 0),
                    ),
                },
                "apps": profile.get("apps", apps),
                "files": profile.get("files", {}),
            })

        # --- Dodaj do apps ---
        if not any(a.get("id") == app_id for a in apps):
            apps.append(app_data)

        # --- Dodaj do files/tools ---
        files = profile.get("files", {})
        tools = files.get("tools", [])
        file_name = f'{app_data["name"]}.sh'
        if file_name not in tools:
            tools.append(file_name)
        files["tools"] = tools
        profile["apps"] = normalize_app_contracts(apps)
        profile["files"] = files
        normalize_profile_storage(profile)

        if (not is_system_catalog_app(app_data)) or app_data.get("ghostlab_generated"):
            for app in store:
                if app.get("id") == app_id:
                    app["downloads"] = int(app.get("downloads", 0)) + 1
                    break
            resources_store.set("app_config", store)

        # --- Aktualizuj profil (aplikacje i pliki) ---
        mgr.update_profile({
            "apps": profile.get("apps", apps),
            "files": files,
            "hackcoins": profile.get("hackcoins", 0),
            "storage_capacity": profile.get("storage_capacity"),
            "storage_used": profile.get("storage_used"),
            "storage_unit": profile.get("storage_unit", "MB"),
            "storage_soft_limit": True,
            "storage_over_limit": profile.get("storage_over_limit", False),
        })
        record_storage_delta(
            buyer_username,
            profile,
            reason="googleplex_app_install",
            previous=previous_storage,
            dedupe_key_prefix=f"storage:{buyer_username}:googleplex_app:{app_id}",
        )
        record_apps_delta(
            buyer_username,
            profile,
            "apps.app_installed",
            app=app_data,
            app_id=app_id,
            reason="googleplex_app_install",
            dedupe_key=f"apps:installed:{buyer_username}:{app_id}",
        )
        record_wallet_balance_delta(
            buyer_username,
            profile.get("hackcoins", 0),
            reason="googleplex_app_install",
            dedupe_key=f"wallet:balance:{buyer_username}:googleplex_app:{app_id}",
        )
        if payee_profile and payee_username != buyer_username:
            record_wallet_balance_delta(
                payee_username,
                payee_profile.get("hackcoins", 0),
                reason="googleplex_app_sale",
                dedupe_key=f"wallet:balance:{payee_username}:googleplex_app_sale:{buyer_username}:{app_id}",
            )

        # --- SYSTEM MESSAGE przez runtime store ---
        new_message = {
            "title": "Instalacja zakończona",
            "text": f"Aplikacja <b>{app_data['name']}</b> została poprawnie zainstalowana!",
            "type": "success",
            "status": "new"
        }

        new_message["dedupe_key"] = f"googleplex_app_install:{buyer_username}:{app_id}"
        system_message_store.add_message(buyer_username, new_message, source="googleplex_install")

        return jsonify({
            "status": "success",
            "message": "Aplikacja została zainstalowana.",
            "hackcoins": profile.get("hackcoins", 0),
            "price": price,
            "paid_to": payee_username if price > 0 else None,
            "storage": {
                "capacity": profile.get("storage_capacity"),
                "used": profile.get("storage_used"),
                "unit": profile.get("storage_unit", "MB"),
                "added": app_data.get("disk_usage") or app_data.get("install_size") or app_data.get("file_size") or 0,
                "soft_limit": True,
                "over_limit": profile.get("storage_over_limit", False),
            },
            "app": normalize_app_contract(app_data),
            "apps": profile.get("apps", apps),
            "files": profile.get("files", {}),
        })

    except Exception as e:
        print(f"[EXCEPTION] Wystąpił błąd podczas instalacji: {e}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/apps/uninstall', methods=['POST'])
def uninstall_app():
    if "user" not in session:
        return jsonify({"status": "error", "message": "Nie jestes zalogowany."}), 401

    data = request.get_json() or {}
    app_id = str(data.get("app_id") or "").strip()
    tool_file = str(data.get("tool_file") or data.get("filename") or "").strip()
    app_name = str(data.get("name") or "").strip()

    profile = sync_session_profile()
    if not profile:
        return jsonify({"status": "error", "message": "Brak danych profilu."}), 404

    previous_storage = storage_delta_snapshot(profile)
    apps = normalize_app_contracts(profile.get("apps", []))
    normalize_files_inventory(profile)
    files = profile.get("files", {})

    matched_app = None
    for app in apps:
        candidates = app_tool_file_candidates(app)
        if app_id and str(app.get("id") or "") == app_id:
            matched_app = app
            break
        if tool_file and tool_file in candidates:
            matched_app = app
            break
        if app_name and app_display_name(app) == app_name:
            matched_app = app
            break

    removed_app = False
    removed_tool = False
    if matched_app:
        matched_id = str(matched_app.get("id") or "")
        apps = [
            app for app in apps
            if str(app.get("id") or "") != matched_id
        ]
        before_tools = len(files.get("tools", []) or [])
        files = remove_app_tool_files(files, matched_app)
        removed_tool = len(files.get("tools", []) or []) != before_tools
        removed_app = True
    elif tool_file:
        tools = list(files.get("tools", []) or [])
        kept_tools = [
            item for item in tools
            if tool_file_entry_name(item) != tool_file
        ]
        removed_tool = len(kept_tools) != len(tools)
        files["tools"] = kept_tools

    profile["apps"] = normalize_app_contracts(apps)
    profile["files"] = files
    normalize_profile_storage(profile)

    mgr = UserProfileManager(session["user"])
    mgr.update_profile({
        "apps": profile.get("apps", []),
        "files": profile.get("files", {}),
        "storage_capacity": profile.get("storage_capacity"),
        "storage_used": profile.get("storage_used"),
        "storage_unit": profile.get("storage_unit", "MB"),
        "storage_soft_limit": True,
        "storage_over_limit": profile.get("storage_over_limit", False),
    })
    record_storage_delta(
        session["user"],
        profile,
        reason="app_uninstall",
        previous=previous_storage,
        dedupe_key_prefix=f"storage:{session['user']}:app_uninstall:{app_id or tool_file or app_name or runtime_file_now()}",
    )
    if removed_app or removed_tool:
        record_apps_delta(
            session["user"],
            profile,
            "apps.app_uninstalled",
            app=matched_app,
            app_id=(matched_app or {}).get("id") or app_id or tool_file or app_name,
            reason="app_uninstall",
            dedupe_key=f"apps:uninstalled:{session['user']}:{(matched_app or {}).get('id') or app_id or tool_file or app_name}",
        )
    session["profile"] = profile

    status = "success" if removed_app or removed_tool else "noop"
    message = (
        "Aplikacja zostala odinstalowana."
        if removed_app
        else "Aplikacja nie byla zainstalowana."
    )
    return jsonify({
        "status": status,
        "success": True,
        "removed_app": removed_app,
        "removed_tool": removed_tool,
        "message": message,
        "apps": profile.get("apps", []),
        "files": profile.get("files", {}),
        "storage": {
            "capacity": profile.get("storage_capacity"),
            "used": profile.get("storage_used"),
            "unit": profile.get("storage_unit", "MB"),
            "soft_limit": True,
            "over_limit": profile.get("storage_over_limit", False),
        }
    })


@app.route("/launch-queue")
def launch_queue():
    app_flow_started_at = time.perf_counter()
    flow_id = request.headers.get("X-Hack-Flow-Id") or ""
    if "user" not in session:
        return jsonify([])

    try:
        step_started_at = time.perf_counter()
        launch_list = user_store.consume_launch_queue(session["user"])
        app_flow_debug_timed(
            flow_id,
            "launch_queue_consume_done",
            app_flow_started_at,
            step_started_at,
            user=session.get("user"),
            count=len(launch_list or []),
            apps=launch_list or [],
        )
    except Exception:
        session.clear()
        return jsonify({"logout": True})

    if launch_list is None:
        session.clear()
        return jsonify({"logout": True})

    hack_flow_debug(
        flow_id,
        "launch_queue_read",
        user=session.get("user"),
        count=len(launch_list),
        apps=launch_list,
    )
    if not launch_list:
        return jsonify([])

    # Opróżnij kolejkę po pobraniu
    session_profile = session.get("profile")
    if isinstance(session_profile, dict):
        session_profile["launch_queue"] = []
        session["profile"] = session_profile
    hack_flow_debug(
        flow_id,
        "launch_queue_cleared",
        user=session.get("user"),
        count=len(launch_list),
        apps=launch_list,
    )
    return jsonify(launch_list)


@app.route('/gonna-win', methods=['POST'])
def gonna_win():
    app_flow_started_at = time.perf_counter()
    data = request.get_json(silent=True) or {}
    app_id = data.get("app_id")
    choice_id = data.get("choice_id", None)
    operation_only = bool(data.get("operation_only"))
    flow_id = str(data.get("_flow_id") or request.headers.get("X-Hack-Flow-Id") or "")[:96]
    launch_receipt = str(
        data.get("launch_receipt")
        or data.get("receipt")
        or data.get("launch_key")
        or ""
    ).strip()[:160]
    launch_source = str(data.get("launch_source") or data.get("source") or "").strip()[:64]
    gonna_win_receipt_key = ""
    if launch_receipt and app_id and session.get("user"):
        receipt_scope = "operation_only" if operation_only else f"choice:{choice_id if choice_id is not None else 'auto'}"
        receipt_seed = "|".join([
            "gonna_win",
            str(session.get("user") or ""),
            str(app_id or ""),
            receipt_scope,
            launch_receipt,
        ])
        gonna_win_receipt_key = "gonna_win:" + hashlib.sha1(receipt_seed.encode("utf-8")).hexdigest()[:32]
        state, receipt = app_action_receipt_store.begin(
            gonna_win_receipt_key,
            username=session.get("user"),
            app_id=str(app_id or ""),
            action=receipt_scope,
            target_key=launch_receipt,
            source=launch_source or "gonna_win",
            ttl_seconds=900,
        )
        if state != "new":
            payload = copy.deepcopy((receipt or {}).get("payload") or {})
            status_code = int((receipt or {}).get("status_code") or 202)
            if not payload:
                payload = {
                    "success": True,
                    "duplicate": True,
                    "idempotent_replay": True,
                    "operation_only": operation_only,
                    "target": None,
                    "actions_allowed_marked": [],
                    "created_operations": [],
                }
            payload["duplicate"] = True
            payload["idempotent_replay"] = True
            app_flow_debug(
                flow_id,
                "gonna_win_receipt_replay",
                started_at=app_flow_started_at,
                app_id=app_id,
                choice_id=choice_id,
                operation_only=operation_only,
                receipt_key=gonna_win_receipt_key,
                state=state,
                status_code=status_code,
            )
            return jsonify(payload), status_code
    app_flow_debug(
        flow_id,
        "gonna_win_start",
        started_at=app_flow_started_at,
        user=session.get("user"),
        app_id=app_id,
        choice_id=choice_id,
        operation_only=operation_only,
        launch_receipt=launch_receipt,
        receipt_key=gonna_win_receipt_key,
    )

    def finish_gonna_win_receipt(payload, status_code=200, status=None):
        if not gonna_win_receipt_key:
            return
        app_action_receipt_store.finish(
            gonna_win_receipt_key,
            payload,
            status_code=status_code,
            ttl_seconds=900,
            status=status,
        )

    CRITICAL_SECURITY_KEYS = [
        "stealth_mode", "scan_detection", "exploit_protection", "vpn_enabled",
        "browser_protection", "os_hardening", "log_guardian", "process_monitor",
        "firewall", "log_integrity", "network_anomaly_detection", "spoofing_protection",
        "activity_monitor", "player_tracking", "system_visibility", "firewall_core",
        "kernel_guard", "system_integrity_check", "heap_protection", "memory_lock",
        "background_injection", "memory_guard", "vpn_blocker"
    ]
    # CRITICAL_SECURITY_KEYS = [
    #     "stealth_mode"
    # ] # DEV LISTA

    step_started_at = time.perf_counter()
    profile = sync_session_profile()
    app_flow_debug_timed(
        flow_id,
        "gonna_win_sync_session_profile",
        app_flow_started_at,
        step_started_at,
        has_profile=bool(profile),
        has_target=bool(profile and profile.get("aimed_target")),
        apps=len(profile.get("apps", []) if isinstance(profile, dict) else []),
        operations=len(profile.get("operations", []) if isinstance(profile, dict) else []),
    )
    if not profile or "aimed_target" not in profile:
        payload = {"success": False, "message": "Brak celu"}
        finish_gonna_win_receipt(payload, status_code=400, status=AppActionReceiptStore.STATUS_FAILED)
        return jsonify(payload), 400

    aimed = profile["aimed_target"]
    target_sec = aimed.get("security", {})
    contest_owner_username = aimed.get("contest_owner_username") if aimed.get("target_mode") == "territory_contest" else None
    contest_owner_target = None
    if contest_owner_username:
        contest_owner_target = find_captured_target_for_owner(
            contest_owner_username,
            aimed.get("lat"),
            aimed.get("lng"),
            aimed.get("label")
        )
        if contest_owner_target and isinstance(contest_owner_target.get("security"), dict):
            target_sec = dict(contest_owner_target.get("security") or {})
            profile["aimed_target"]["security"] = target_sec

    apps = profile.get("apps", [])
    app = next((a for a in apps if a["id"] == app_id), None)

    if not app:
        payload = {"success": False, "message": "Nie znaleziono aplikacji"}
        finish_gonna_win_receipt(payload, status_code=404, status=AppActionReceiptStore.STATUS_FAILED)
        return jsonify(payload), 404
    normalized_app_for_guard = normalize_app_contract(app or {})
    app_requires_map_target = bool(
        as_list(normalized_app_for_guard.get("map_actions"))
        or as_list(normalized_app_for_guard.get("operation_types"))
    )
    if app_requires_map_target and not target_has_stable_runtime_identity(profile.get("aimed_target")):
        app_flow_debug(
            flow_id,
            "gonna_win_reject_invalid_target",
            started_at=app_flow_started_at,
            app_id=app_id,
            target=profile.get("aimed_target"),
        )
        payload = {
            "success": False,
            "blocked": True,
            "reason": "invalid_target",
            "message": "Brak stabilnego celu dla aplikacji mapowej.",
            "target": profile.get("aimed_target") or {},
            "created_operations": [],
        }
        finish_gonna_win_receipt(payload, status_code=409, status=AppActionReceiptStore.STATUS_FAILED)
        return jsonify(payload), 409

    step_started_at = time.perf_counter()
    target_changed, marked_actions = apply_app_map_actions_to_aimed_target(profile, app, session.get("user"))
    app_flow_debug_timed(
        flow_id,
        "gonna_win_apply_app_map_actions_done",
        app_flow_started_at,
        step_started_at,
        app_id=app_id,
        target_changed=target_changed,
        marked_actions=marked_actions,
    )
    created_operations = []
    if profile.get("aimed_target"):
        step_started_at = time.perf_counter()
        merge_latest_aimed_target_runtime_state(profile, session.get("user"))
        app_flow_debug_timed(
            flow_id,
            "gonna_win_merge_latest_runtime_done",
            app_flow_started_at,
            step_started_at,
            target_id=build_operation_target_id(profile.get("aimed_target") or {}),
            allowed=(profile.get("aimed_target") or {}).get("actions_allowed"),
        )
        step_started_at = time.perf_counter()
        created_operations = create_missing_operations_for_app_target(
            profile,
            session.get("user"),
            app,
            profile.get("aimed_target") or {},
        )
        app_flow_debug_timed(
            flow_id,
            "gonna_win_create_missing_operations_done",
            app_flow_started_at,
            step_started_at,
            app_id=app_id,
            created=[op.get("operation_id") for op in created_operations or [] if isinstance(op, dict)],
            operations_total=len(profile.get("operations", [])),
        )
    app_flow_debug(
        flow_id,
        "gonna_win_map_runtime_applied",
        started_at=app_flow_started_at,
        app_id=app_id,
        target_changed=target_changed,
        marked_actions=marked_actions,
        created_operations=[op.get("operation_id") for op in created_operations or [] if isinstance(op, dict)],
    )

    if operation_only:
        mgr = UserProfileManager(session["user"])
        session["profile"] = profile
        step_started_at = time.perf_counter()
        mgr.update_profile({
            "aimed_target": profile.get("aimed_target", {}),
            "operations": profile.get("operations", []),
        })
        app_flow_debug_timed(
            flow_id,
            "gonna_win_operation_only_profile_update_done",
            app_flow_started_at,
            step_started_at,
            app_id=app_id,
            operations_total=len(profile.get("operations", [])),
        )
        if target_changed:
            step_started_at = time.perf_counter()
            record_map_target_delta(
                session["user"],
                profile.get("aimed_target") or {},
                change_type="map.target_updated",
                reason="app_launch_operation_start",
            )
            app_flow_debug_timed(
                flow_id,
                "gonna_win_operation_only_delta_done",
                app_flow_started_at,
                step_started_at,
                app_id=app_id,
            )
        app_flow_debug(
            flow_id,
            "gonna_win_return_operation_only",
            started_at=app_flow_started_at,
            app_id=app_id,
            target_changed=target_changed,
            created_count=len(created_operations or []),
        )
        payload = {
            "success": True,
            "operation_only": True,
            "target": profile.get("aimed_target"),
            "actions_allowed_marked": marked_actions,
            "created_operations": created_operations,
        }
        finish_gonna_win_receipt(payload)
        return jsonify(payload)

    success = False

    step_started_at = time.perf_counter()
    if choice_id is None:
        required_off = app.get("requires_off", [])
        all_off = all(target_sec.get(k) is False for k in required_off)

        if all_off:
            interferes = app.get("interferes_with", [])
            for key in interferes:
                if key in target_sec:
                    target_sec[key] = False
            success = True
    else:
        options = app.get("levels", [])[0].get("options", [])
        try:
            choi = options[int(choice_id)]
            effect = choi.get("effect", {})
            for k, v in effect.items():
                target_sec[k] = v
            success = True
        except (IndexError, ValueError):
            payload = {"success": False, "message": "Nieprawidlowy choice_id"}
            finish_gonna_win_receipt(payload, status_code=400, status=AppActionReceiptStore.STATUS_FAILED)
            return jsonify(payload), 400

    app_flow_debug_timed(
        flow_id,
        "gonna_win_choice_effect_applied",
        app_flow_started_at,
        step_started_at,
        app_id=app_id,
        choice_id=choice_id,
        success=success,
        security_keys=len(target_sec or {}),
    )

    # aktualizacja profilu
    profile["aimed_target"]["security"] = target_sec
    step_started_at = time.perf_counter()
    merge_latest_aimed_target_runtime_state(profile, session.get("user"))
    app_flow_debug_timed(
        flow_id,
        "gonna_win_security_merge_latest_runtime_done",
        app_flow_started_at,
        step_started_at,
        target_id=build_operation_target_id(profile.get("aimed_target") or {}),
        allowed=(profile.get("aimed_target") or {}).get("actions_allowed"),
    )
    if profile.get("aimed_target"):
        try:
            step_started_at = time.perf_counter()
            player_target_runtime_store.upsert_aimed(
                session.get("user"),
                profile.get("aimed_target") or {},
                status="in_progress",
                source="gonna_win_security_update",
            )
            app_flow_debug_timed(
                flow_id,
                "gonna_win_target_runtime_upsert_done",
                app_flow_started_at,
                step_started_at,
                target_id=build_operation_target_id(profile.get("aimed_target") or {}),
            )
        except Exception as exc:
            print(f"[target runtime] security update failed user={session.get('user')} error={exc}", flush=True)
    if contest_owner_username and contest_owner_target:
        contest_owner_target["security"] = dict(target_sec)
        owner_mgr = UserProfileManager(contest_owner_username)
        step_started_at = time.perf_counter()
        owner_mgr.update_hacked_target_by_coords(
            contest_owner_target.get("lat"),
            contest_owner_target.get("lng"),
            {"security": dict(target_sec)}
        )
        territory_store.save_captured_target(contest_owner_username, contest_owner_target)
        app_flow_debug_timed(
            flow_id,
            "gonna_win_contest_owner_security_update_done",
            app_flow_started_at,
            step_started_at,
            owner=contest_owner_username,
        )

    # 📌 Weryfikacja: czy cel został skutecznie rozbrojony (>=70% wyłączonych + wszystkie actions_allowed)
    total = len(CRITICAL_SECURITY_KEYS)
    off = sum(1 for k in CRITICAL_SECURITY_KEYS if target_sec.get(k) is False)

    percent_off = (off / total) * 100
    target_mode = profile["aimed_target"].get("target_mode", "standard")
    allowed_actions = profile["aimed_target"].get("actions_allowed", {})
    all_actions_allowed = all(
        allowed_actions.get(k) is True
        for k in ["scan_ports", "exploit", "sniff", "trace"]
    )

    mgr = UserProfileManager(session["user"])
    session["profile"] = profile
    rebuilt_areas = None
    progression = None
    captured_target_response = None
    captured_conflicts = []
    conflict_consolidation_summary = []
    conflict_capture_summary = None

    if percent_off >= 70 and all_actions_allowed:
        app_flow_debug(
            flow_id,
            "gonna_win_capture_branch_enter",
            started_at=app_flow_started_at,
            app_id=app_id,
            target_mode=target_mode,
            percent_off=round(percent_off, 2),
            allowed_actions=allowed_actions,
        )
        if profile["aimed_target"].get("target_mode") == "player":
            victim_username = str(profile["aimed_target"].get("target_username") or profile["aimed_target"].get("username") or "").strip()
            if not victim_username or not user_store.get_profile(victim_username):
                payload = {
                    "success": False,
                    "message": "Nie mozna utworzyc dostepu: gracz celu nie istnieje."
                }
                finish_gonna_win_receipt(payload, status_code=404, status=AppActionReceiptStore.STATUS_FAILED)
                return jsonify(payload), 404

            access = player_hack_access_store.grant_access(
                session["user"],
                victim_username,
                access_minutes=PLAYER_HACK_ACCESS_MINUTES,
                cooldown_hours=PLAYER_HACK_COOLDOWN_HOURS,
            )
            player_hack_access = serialize_player_hack_access(access)
            try:
                player_target_runtime_store.mark_captured(
                    session["user"],
                    profile.get("aimed_target") or {},
                    source="player_hack_access_granted",
                )
            except Exception as exc:
                print(f"[target runtime] player capture mark failed user={session.get('user')} error={exc}", flush=True)
            profile["aimed_target"] = {}
            success = True
            session["profile"] = profile
            step_started_at = time.perf_counter()
            mgr.update_profile({
                "aimed_target": {},
                "system_messages": profile.get("system_messages", []),
                "operations": profile.get("operations", []),
            })
            app_flow_debug_timed(
                flow_id,
                "gonna_win_player_access_profile_update_done",
                app_flow_started_at,
                step_started_at,
                app_id=app_id,
            )
            app_flow_debug(
                flow_id,
                "gonna_win_return_player_access",
                started_at=app_flow_started_at,
                app_id=app_id,
                choice_id=choice_id,
                percent_off=round(percent_off, 2),
            )
            payload = {
                "success": True,
                "percent_off": round(percent_off, 2),
                "captured_target": None,
                "hacked": profile.get("hacked", []),
                "player_areas_count": None,
                "progression": None,
                "player_hack_access": player_hack_access,
                "target": None,
                "actions_allowed_marked": marked_actions,
                "created_operations": created_operations,
                "message": f"Dostep do {player_hack_access.get('victim_nick') or victim_username} aktywny przez {PLAYER_HACK_ACCESS_MINUTES} min."
            }
            finish_gonna_win_receipt(payload)
            return jsonify(payload)

        captured_target = dict(profile["aimed_target"])
        captured_target_mode = captured_target.get("target_mode")
        vulnerability_report = None
        contest_owner_username = captured_target.get("contest_owner_username") if captured_target.get("target_mode") == "territory_contest" else None
        if captured_target.get("vulnerability_id"):
            try:
                vulnerability_report = vulnerability_store.get(int(captured_target.get("vulnerability_id")))
            except (TypeError, ValueError):
                vulnerability_report = None
        if contest_owner_username:
            captured_target["target_mode"] = "standard"
            captured_target["previous_owner_username"] = contest_owner_username
            captured_target.pop("contest_owner_username", None)
            captured_target.pop("foreign_area_id", None)
            captured_target.pop("my_area_id", None)
        captured_lng = captured_target.get("lng", captured_target.get("lon"))
        captured_target["lat"] = float(captured_target.get("lat"))
        captured_target["lng"] = float(captured_lng)
        captured_target["lon"] = float(captured_lng)
        captured_target["owner_username"] = session["user"]
        captured_target["captured_at"] = datetime.utcnow().isoformat(timespec="seconds")
        captured_target["stationary"] = not bool(captured_target.get("generated", False))
        if not captured_target.get("target_id"):
            captured_target["target_id"] = build_operation_target_id(captured_target)
        step_started_at = time.perf_counter()
        captured_target = territory_store.save_captured_target(session["user"], captured_target)
        app_flow_debug_timed(
            flow_id,
            "gonna_win_save_captured_target_done",
            app_flow_started_at,
            step_started_at,
            target_id=build_operation_target_id(captured_target),
        )
        pillar_capture_action_id = gonna_win_receipt_key or launch_receipt
        if not pillar_capture_action_id and flow_id:
            pillar_capture_seed = "|".join([
                "gonna_win_pillar_capture",
                str(session.get("user") or ""),
                str(flow_id),
                str(app_id or ""),
                str(choice_id if choice_id is not None else "auto"),
                str(captured_target.get("conflict_id") or ""),
                str(captured_target.get("target_id") or ""),
            ])
            pillar_capture_action_id = (
                "gonna_win_pillar_capture:"
                + hashlib.sha1(pillar_capture_seed.encode("utf-8")).hexdigest()[:32]
            )
        if captured_target_mode == "territory_contest" or captured_target.get("conflict_id"):
            step_started_at = time.perf_counter()
            captured_conflicts = capture_conflict_pillar(
                captured_target,
                captured_by_username=session["user"],
                previous_owner_username=contest_owner_username,
                action_id=pillar_capture_action_id or None,
            )
            conflict_capture_summary = {
                "attempted": True,
                "target_id": captured_target.get("target_id"),
                "node_role": captured_target.get("node_role"),
                "conflict_id": (
                    captured_target.get("stable_conflict_id")
                    or captured_target.get("conflict_id")
                    or captured_target.get("legacy_conflict_id")
                ),
                "changed": bool(captured_conflicts),
                "affected_conflicts": [
                    conflict.get("conflict_id") or conflict.get("id")
                    for conflict in captured_conflicts
                ],
            }
            print(
                "[TERRITORY_CAPTURE] "
                f"user={session.get('user')} result="
                f"{json.dumps(conflict_capture_summary, ensure_ascii=False)}",
                flush=True,
            )
            app_flow_debug_timed(
                flow_id,
                "gonna_win_capture_conflict_pillar_done",
                app_flow_started_at,
                step_started_at,
                target_id=captured_target.get("target_id"),
                conflict_id=captured_target.get("conflict_id"),
                changed=bool(captured_conflicts),
                action_id=pillar_capture_action_id,
            )
        captured_target_response = dict(captured_target)
        step_started_at = time.perf_counter()
        safe_ghostnetwork_on_target_hacked(
            session["user"],
            profile,
            captured_target_response,
            result={
                "success": True,
                "target_captured": True,
                "percent_off": round(percent_off, 2),
                "source": "gonna_win_capture",
            },
            reason="gonna_win_capture",
        )
        app_flow_debug_timed(
            flow_id,
            "gonna_win_ghostnetwork_hook_done",
            app_flow_started_at,
            step_started_at,
            target_id=build_operation_target_id(captured_target_response),
        )

        hacked_targets = profile.setdefault("hacked", [])
        already_hacked_index = next(
            (
                index for index, target in enumerate(hacked_targets)
                if round(target.get("lat", 0), 5) == round(captured_target.get("lat", 0), 5)
                and round(target.get("lng", target.get("lon", 0)), 5) == round(captured_target.get("lng", captured_target.get("lon", 0)), 5)
                and target.get("label") == captured_target.get("label")
            ),
            None
        )
        if already_hacked_index is None:
            hacked_targets.append(captured_target)
        else:
            hacked_targets[already_hacked_index] = captured_target

        profile["targets"], _ = filter_targets_by_position(
            profile.get("targets", []),
            captured_target,
            match_label=False
        )

        if contest_owner_username and contest_owner_username != session["user"]:
            owner_mgr = UserProfileManager(contest_owner_username)
            step_started_at = time.perf_counter()
            removed_from_profile = owner_mgr.remove_from_list_by_coords(
                "hacked",
                captured_target.get("lat"),
                captured_target.get("lng"),
                label=captured_target.get("label")
            )
            if not removed_from_profile:
                owner_mgr.remove_from_list_by_coords(
                    "hacked",
                    captured_target.get("lat"),
                    captured_target.get("lng")
                )
            removed_from_store = territory_store.remove_captured_target(
                contest_owner_username,
                captured_target.get("lat"),
                captured_target.get("lng"),
                captured_target.get("label")
            )
            if not removed_from_store:
                territory_store.remove_captured_target(
                    contest_owner_username,
                    captured_target.get("lat"),
                    captured_target.get("lng")
                )
            owner_mgr.update_profile({
                "hacked": territory_store.list_captured_targets(contest_owner_username),
                "captured_targets_source": "sqlite",
            })
            clear_aimed_target_if_matches(contest_owner_username, captured_target)
            app_flow_debug_timed(
                flow_id,
                "gonna_win_contest_owner_remove_target_done",
                app_flow_started_at,
                step_started_at,
                owner=contest_owner_username,
                removed_from_profile=removed_from_profile,
                removed_from_store=removed_from_store,
            )

        if vulnerability_report:
            vulnerability_store.set_status(vulnerability_report.get("id"), "hacked")
        elif not contest_owner_username and captured_target_mode != "player":
            vulnerability_store.mark_hacked_by_target(
                captured_target.get("lat"),
                captured_target.get("lng"),
                captured_target.get("label")
            )
        if captured_target_mode == "player":
            # TODO(player-hack): tutaj wejdzie docelowy panel/narzedzia
            # administracji profilu gracza: pliki, maile, aplikacje,
            # zabezpieczenia oraz systemowe aplikacje z Googleplexa
            # z wymaganiami HC/level/klan/frakcja.
            pass
        if vulnerability_report and vulnerability_report.get("reported_by_username") != session["user"]:
            hacked_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            attacker_name = profile.get("nick") or session["user"]
            attacker_clan = get_profile_clan(profile) or "brak"
            target_label = display_target_label(captured_target)
            add_system_message_to_user(
                vulnerability_report.get("reported_by_username"),
                "success",
                "Podatnosc przejeta",
                (
                    f"{attacker_name} przejal cel "
                    f"{target_label} z twojego zgloszenia."
                )
            )
            add_cyberner_direct_notification(
                vulnerability_report.get("reported_by_username"),
                "System",
                "System",
                "Podatnosc zostala zhakowana",
                (
                    f"Twoja zgloszona podatnosc zostala zhakowana.\n\n"
                    f"Cel: {target_label}\n"
                    f"Typ: {captured_target.get('source_type', 'unknown')}\n"
                    f"Pozycja: {captured_target.get('lat')}, {captured_target.get('lng')}\n"
                    f"Atakujacy: {attacker_name} ({session['user']})\n"
                    f"Klan atakujacego: {attacker_clan}\n"
                    f"Czas: {hacked_at}\n"
                    f"ID zgloszenia: {vulnerability_report.get('id')}"
                )
            )
        step_started_at = time.perf_counter()
        rebuilt_areas = rebuild_player_areas_with_territory_delta(
            session["user"],
            profile.get("level", 1),
            reason="pillar_captured",
        )
        app_flow_debug_timed(
            flow_id,
            "gonna_win_rebuild_player_areas_done",
            app_flow_started_at,
            step_started_at,
            user=session["user"],
            areas=len(rebuilt_areas or []),
        )
        if contest_owner_username and contest_owner_username != session["user"]:
            owner_profile = user_store.get_profile(contest_owner_username) or {}
            step_started_at = time.perf_counter()
            owner_areas = rebuild_player_areas_with_territory_delta(
                contest_owner_username,
                owner_profile.get("level", 1),
                reason="pillar_lost",
            )
            refresh_territory_stats_snapshot(owner_profile, owner_areas)
            user_store.save_profile(owner_profile)
            app_flow_debug_timed(
                flow_id,
                "gonna_win_owner_rebuild_done",
                app_flow_started_at,
                step_started_at,
                owner=contest_owner_username,
                owner_areas=len(owner_areas or []),
            )
            attacker_name = profile.get("nick") or session["user"]
            target_label = display_target_label(captured_target)
            add_system_message_to_user(
                contest_owner_username,
                "danger",
                "Utrata punktu terytorium",
                f"{attacker_name} przejal twoj obiekt {target_label}. Terytorium zostalo przebudowane."
            )
            add_cyberner_direct_notification(
                contest_owner_username,
                "System",
                "System",
                "Utrata punktu terytorium",
                (
                    f"Obiekt {target_label} zostal przejety przez {attacker_name} ({session['user']}).\n"
                    f"Pozycja: {captured_target.get('lat')}, {captured_target.get('lng')}"
                )
            )
            step_started_at = time.perf_counter()
            rebuilt_areas = rebuild_player_areas_with_territory_delta(
                session["user"],
                profile.get("level", 1),
                reason="pillar_captured_owner_rebuild",
            )
            app_flow_debug_timed(
                flow_id,
                "gonna_win_attacker_rebuild_after_owner_done",
                app_flow_started_at,
                step_started_at,
                user=session["user"],
                areas=len(rebuilt_areas or []),
            )
            profile["hacked"] = territory_store.list_captured_targets(session["user"])
            hacked_targets = profile["hacked"]
        step_started_at = time.perf_counter()
        progression = apply_territory_progression(profile, rebuilt_areas)
        app_flow_debug_timed(
            flow_id,
            "gonna_win_apply_territory_progression_done",
            app_flow_started_at,
            step_started_at,
            levels_gained=(progression or {}).get("levels_gained"),
        )
        if progression["levels_gained"]:
            step_started_at = time.perf_counter()
            rebuilt_areas = rebuild_player_areas_with_territory_delta(
                session["user"],
                profile.get("level", 1),
                reason="territory_progression",
            )
            app_flow_debug_timed(
                flow_id,
                "gonna_win_rebuild_after_progression_done",
                app_flow_started_at,
                step_started_at,
                user=session["user"],
                areas=len(rebuilt_areas or []),
            )
        if captured_conflicts:
            step_started_at = time.perf_counter()
            conflict_consolidation_summary = [
                {
                    "conflict_id": conflict.get("conflict_id") or conflict.get("id"),
                    "queued": True,
                    "conflict_version": conflict.get("conflict_version"),
                    "geometry_status": conflict.get("geometry_status"),
                }
                for conflict in captured_conflicts
            ]
            print(
                "[TERRITORY_CONSOLIDATION_QUEUED] "
                f"user={session.get('user')} results="
                f"{json.dumps(conflict_consolidation_summary, ensure_ascii=False)}",
                flush=True,
            )
            app_flow_debug_timed(
                flow_id,
                "gonna_win_conflict_consolidation_queued",
                app_flow_started_at,
                step_started_at,
                conflicts=len(captured_conflicts),
                results=conflict_consolidation_summary,
            )
        step_started_at = time.perf_counter()
        notify_encircled_area_owners()
        app_flow_debug_timed(
            flow_id,
            "gonna_win_notify_encircled_done",
            app_flow_started_at,
            step_started_at,
        )

        try:
            step_started_at = time.perf_counter()
            player_target_runtime_store.mark_captured(
                session["user"],
                captured_target_response or captured_target,
                source="gonna_win_capture",
            )
            app_flow_debug_timed(
                flow_id,
                "gonna_win_target_runtime_mark_captured_done",
                app_flow_started_at,
                step_started_at,
                target_id=build_operation_target_id(captured_target_response or captured_target),
            )
        except Exception as exc:
            print(f"[target runtime] capture mark failed user={session.get('user')} error={exc}", flush=True)
        profile["aimed_target"] = {}
        success = True
        session["profile"] = profile

        step_started_at = time.perf_counter()
        mgr.update_profile({
            "hacked": hacked_targets,
            "targets": profile.get("targets", []),
            "aimed_target": {},
            "level": profile["level"],
            "respect": profile["respect"],
            "exp": profile["exp"],
            "captured_targets_source": "sqlite",
            "territory_stats": profile["territory_stats"],
            "system_messages": profile["system_messages"],
            "operations": profile.get("operations", []),
        })
        app_flow_debug_timed(
            flow_id,
            "gonna_win_capture_profile_update_done",
            app_flow_started_at,
            step_started_at,
            hacked=len(hacked_targets or []),
            operations_total=len(profile.get("operations", [])),
        )
        step_started_at = time.perf_counter()
        record_map_target_delta(
            session["user"],
            captured_target_response or captured_target,
            change_type="map.target_captured",
            reason="gonna_win_capture",
        )
        app_flow_debug_timed(
            flow_id,
            "gonna_win_capture_delta_done",
            app_flow_started_at,
            step_started_at,
            target_id=build_operation_target_id(captured_target_response or captured_target),
        )
    else:
        step_started_at = time.perf_counter()
        mgr.update_profile({
            "aimed_target": profile["aimed_target"],
            "operations": profile.get("operations", []),
        })
        app_flow_debug_timed(
            flow_id,
            "gonna_win_partial_profile_update_done",
            app_flow_started_at,
            step_started_at,
            target_id=build_operation_target_id(profile.get("aimed_target") or {}),
            operations_total=len(profile.get("operations", [])),
        )

    app_flow_debug(
        flow_id,
        "gonna_win_return",
        started_at=app_flow_started_at,
        app_id=app_id,
        choice_id=choice_id,
        success=success,
        percent_off=round(percent_off, 2),
        captured=bool(captured_target_response),
        target_present=bool(profile.get("aimed_target")),
        created_count=len(created_operations or []),
    )
    payload = {
        "success": success,
        "percent_off": round(percent_off, 2),
        "captured_target": captured_target_response,
        "target": profile.get("aimed_target"),
        "actions_allowed_marked": marked_actions,
        "hacked": profile.get("hacked", []),
        "player_areas_count": len(rebuilt_areas) if rebuilt_areas is not None else None,
        "progression": progression,
        "created_operations": created_operations,
        "territory_conflict_consolidation": conflict_consolidation_summary,
        "territory_conflict_capture": conflict_capture_summary,
    }
    finish_gonna_win_receipt(payload)
    return jsonify(payload)




if __name__ == "__main__":
    app.run(debug=True)
