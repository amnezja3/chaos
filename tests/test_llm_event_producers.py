import copy
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import run
from scripts import territory_conflict_worker
from database import (
    PlayerInventoryStore,
    ProfilePrecommitRejected,
    reset_request_transaction_precommit_guard,
    set_request_transaction_precommit_guard,
)
from ghostnetwork import (
    BlackNetNarrativeProducer,
    GhostNetworkRepository,
    GhostNetworkService,
    GoogleplexLlmTaskIngress,
)
from ghostnetwork.ollama_policy import build_ollama_task_package
from ghostnetwork.ollama_policy import parse_and_validate_ollama_content
from ghostnetwork.editorial import GoogleplexEditorialProducer
from ghostnetwork.producers import narrative_intent_for_signal


class LlmEventProducerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "llm-producers.sqlite3")
        self.repo = GhostNetworkRepository(self.db_path)
        self.inventory = PlayerInventoryStore(self.db_path)
        self.service = GhostNetworkService(repository=self.repo)
        self.app_contract = {
            "id": "future-agi-tool",
            "llm_ingress": {
                "enabled": True,
                "canon_version": "googleplex-llm-ingress-v1",
                "templates": [{
                    "id": "owner-analysis",
                    "target_medium": "cyberner",
                    "input_fields": {
                        "topic": {"required": True, "max_length": 120},
                    },
                    "allowed_actions": [{
                        "cta_action": "open_cyberner_channel",
                        "payload": {"channel": "agi-2108"},
                    }],
                }],
            },
        }

    def tearDown(self):
        self.tmp.cleanup()

    def install_app(self, username="alice"):
        self.inventory.seed_from_profile(username, {
            "apps": [{"id": self.app_contract["id"], "status": "installed"}],
            "files": {"tools": []},
            "storage_capacity": 100,
            "storage_used": 1,
        })

    def app_payload(self, **updates):
        payload = {
            "app_id": self.app_contract["id"],
            "client_receipt_id": "client-receipt-0001",
            "approved_template_id": "owner-analysis",
            "input": {"topic": "Sytuacja GhostNetwork"},
        }
        payload.update(updates)
        return payload

    def test_ghostnetwork_transition_creates_safe_idempotent_task(self):
        event = {
            "event_id": "event-public-activation",
            "event_type": "ghost.part_activated",
            "cycle_id": "cycle-one",
            "part_id": "internal-secret-part-id",
            "entity_id": "internal-secret-part-id",
            "state_version": 17,
            "audience_scope": "public",
            "payload": {
                "previous_status": "contained",
                "status": "active",
            },
        }
        first = self.service.publish_narrative_event(event)
        second = self.service.publish_narrative_event(event)
        self.assertTrue(first["ok"])
        self.assertEqual(len(first["outbox"]), 1)
        self.assertTrue(second["outbox"][0]["idempotent"])
        task = first["outbox"][0]
        encoded = json.dumps(task["facts"])
        self.assertNotIn("internal-secret-part-id", encoded)
        self.assertIn("ghost-node:", encoded)
        self.assertEqual(task["audience_scope"], "public")

        internal = self.service.publish_narrative_event({
            **event,
            "event_id": "event-internal",
            "audience_scope": "internal",
        })
        self.assertEqual(internal["outbox"], [])

    def test_blacknet_digest_is_bounded_deduplicated_and_profile_free(self):
        snapshot = {
            "version": "signals-v1",
            "world_facts_version": "facts-v1",
            "generated_at": "2026-08-28T08:07:00+00:00",
            "signals": [{
                "id": "world-signal-1",
                "fact_id": "fact-1",
                "signal_type": "product_signal",
                "category": "googleplex",
                "region_id": "global",
                "title": "NOWY PRODUKT",
                "label": "GOOGLEPLEX",
                "value": "1",
                "stat": "STABILNY",
                "importance": 2,
                "cta_action": "open_googleplex",
                "cta_target_id": "product-one",
            }],
        }
        producer = BlackNetNarrativeProducer(self.repo)
        first = producer.enqueue_digest(snapshot)
        second = producer.enqueue_digest(snapshot)
        news = producer.enqueue_digest(snapshot, target_medium="googleplex_news")
        self.assertEqual(first["status"], "created")
        self.assertEqual(second["status"], "deduplicated")
        self.assertEqual(first["task"]["outbox_id"], second["task"]["outbox_id"])
        self.assertEqual(first["task"]["source_scope"], "blacknet_world")
        self.assertEqual(news["status"], "created")
        self.assertEqual(news["task"]["target_medium"], "googleplex_news")
        self.assertEqual(
            news["task"]["allowed_actions"][0]["fact_ref"],
            "blacknet_fact:fact-1",
        )
        self.assertNotEqual(first["task"]["outbox_id"], news["task"]["outbox_id"])

        teleport_snapshot = copy.deepcopy(snapshot)
        teleport_snapshot["version"] = "signals-teleport"
        teleport_snapshot["signals"][0]["cta_action"] = "teleport_to_hotspot"
        teleport = producer.enqueue_digest(teleport_snapshot, window_id="teleport-window")
        self.assertEqual(
            teleport["task"]["allowed_actions"][0]["cta_action"],
            "focus_map_target",
        )

        coordinate_snapshot = copy.deepcopy(teleport_snapshot)
        coordinate_snapshot["version"] = "signals-coordinate-teleport"
        coordinate_snapshot["signals"][0]["metadata"] = {
            "lat": 52.2297, "lng": 21.0122, "location_label": "Warszawa",
        }
        coordinate_teleport = producer.enqueue_digest(
            coordinate_snapshot, window_id="coordinate-teleport-window",
            target_medium="googleplex_news",
        )
        coordinate_action = coordinate_teleport["task"]["allowed_actions"][0]
        self.assertEqual(coordinate_action["cta_action"], "teleport_to_hotspot")
        self.assertEqual(coordinate_action["payload"]["lat"], 52.2297)
        self.assertEqual(coordinate_action["payload"]["lng"], 21.0122)
        self.assertEqual(coordinate_action["payload"]["label"], "Warszawa")
        coordinate_package = build_ollama_task_package(coordinate_teleport["task"])
        coordinate_input = json.loads(coordinate_package["messages"][1]["content"])
        self.assertIn("lat", coordinate_input["fact_columns"])
        self.assertIn("lng", coordinate_input["fact_columns"])
        self.assertIn(52.2297, coordinate_input["facts"][0])
        self.assertIn(21.0122, coordinate_input["facts"][0])

        with patch.object(run.user_store, "list_profiles", side_effect=AssertionError("full profile scan")), \
                patch.object(run.user_store, "get_profile", side_effect=AssertionError("full profile read")), \
                patch.object(run, "build_blacknet_googleplex_facts", return_value=[]), \
                patch.object(run, "build_blacknet_radio_facts", return_value=[]), \
                patch.object(run, "build_blacknet_conflict_activity_facts", return_value=[]), \
                patch.object(run, "build_blacknet_incident_facts", return_value=[]):
            safe = run.build_blacknet_narrative_source_snapshot(
                now=datetime(2026, 8, 28, 8, 0, tzinfo=timezone.utc)
            )
        self.assertEqual(safe["diagnostics"]["profile_reads"], 0)

    def test_stage_one_editorial_task_has_one_backend_selected_source(self):
        snapshot = {
            "version": "world-v1",
            "world_facts_version": "facts-v1",
        }
        signal = {
            "id": "conflict-one",
            "fact_id": "bnf:conflicts:conflict_target_alert:one",
            "signal_type": "conflict_target_alert",
            "category": "conflict",
            "title": "CONFLICT / POI-788AEF",
            "label": "TARGET SPORNY",
            "stat": "contested",
            "importance": 75,
            "cta_action": "focus_map_target",
            "cta_target_id": "legacy:canonical-target",
            "metadata": {"lat": 35.6766, "lng": 139.653286},
            "region_id": "world-INCYDENT / L4 ESCALATED",
        }
        producer = BlackNetNarrativeProducer(self.repo)

        blacknet = producer.enqueue_signal(snapshot, signal, target_medium="blacknet")
        replay = producer.enqueue_signal(snapshot, signal, target_medium="blacknet")
        news = producer.enqueue_signal(
            snapshot, signal, target_medium="googleplex_news"
        )

        self.assertEqual(blacknet["status"], "created")
        self.assertEqual(replay["status"], "deduplicated")
        self.assertEqual(len(blacknet["task"]["facts"]), 1)
        self.assertEqual(blacknet["task"]["facts"][0]["region_id"], "")
        self.assertEqual(blacknet["task"]["allowed_actions"], [])
        self.assertEqual(
            blacknet["task"]["task_variant"], "blacknet_signal_narration"
        )
        self.assertEqual(
            blacknet["task"]["narrative_intent"],
            "intercepted_conflict_warning",
        )
        self.assertEqual(
            news["task"]["task_variant"], "googleplex_world_dispatch"
        )
        self.assertEqual(
            news["task"]["validation"]["presentation_slot"],
            "gp-home-world-grid",
        )
        self.assertEqual(news["task"]["presentation_slot"], "gp-home-world-grid")
        self.assertEqual(
            news["task"]["selected_source_ref"],
            news["task"]["facts"][0]["fact_id"],
        )
        self.assertEqual(news["task"]["expected_slot_version"], 0)
        package = build_ollama_task_package(news["task"])
        model_input = json.loads(package["messages"][1]["content"])
        self.assertEqual(
            model_input["narrative_intent"], "intercepted_conflict_warning"
        )
        self.assertEqual(package["fact_count"], 1)
        self.assertNotIn("ctas", model_input)
        self.assertIn("title", model_input["fact_columns"])
        self.assertIn("stat", model_input["fact_columns"])
        self.assertEqual(
            package["selected_source_ref"], news["task"]["facts"][0]["fact_id"]
        )
        self.assertEqual(
            package["fixed_action"]["payload"]["target_id"],
            "legacy:canonical-target",
        )

    def test_signal_narrative_intent_mapping_is_code_owned(self):
        cases = (
            ({"signal_type": "conflict_target_alert"}, "intercepted_conflict_warning"),
            ({"signal_type": "incident_hotspot"}, "intercepted_incident_alert"),
            ({"signal_type": "radio_promotion"}, "intercepted_broadcast_fragment"),
            ({
                "signal_type": "product_opportunity",
                "fact_id": "bnf:googleplex:googleplex_product_signal:one",
            }, "intercepted_product_transmission"),
        )
        for signal, expected in cases:
            with self.subTest(signal=signal):
                self.assertEqual(narrative_intent_for_signal(signal), expected)

    def test_blacknet_product_intent_omits_heat_and_download_metrics(self):
        signal = {
            "id": "product-one",
            "fact_id": "bnf:googleplex:googleplex_product_signal:one",
            "signal_type": "product_opportunity",
            "category": "googleplex",
            "title": "GOOGLEPLEX / Bilet: Tokio",
            "label": "CENA",
            "value": "520 HC",
            "stat": "45 TEMP / 0 POBRAN",
            "importance": 50,
        }
        result = BlackNetNarrativeProducer(self.repo).enqueue_signal(
            {"world_facts_version": "facts-v2"}, signal, target_medium="blacknet"
        )
        task = result["task"]
        self.assertEqual(task["prompt_version"], "blacknet-signal-prompt-v9")
        self.assertEqual(task["canon_version"], "product-signal-v4")
        self.assertEqual(task["narrative_intent"], "intercepted_product_transmission")
        self.assertEqual(task["facts"][0]["value"], "520 HC")
        self.assertEqual(task["facts"][0]["stat"], "")

        package = build_ollama_task_package(task)
        model_input = json.loads(package["messages"][1]["content"])
        self.assertNotIn("stat", model_input["fact_columns"])
        self.assertIn("value", model_input["fact_columns"])

        metrics = parse_and_validate_ollama_content(json.dumps({
            "title": "GOOGLEPLEX / Bilet: Tokio",
            "body": "CENA to 520 HC, a czas oczekiwania wynosi 45 TEMP / 0 POBRAN.",
            "tone": "mystery",
            "fact_refs": [task["facts"][0]["fact_id"]],
            "cta_ref": None,
        }), package)
        self.assertEqual(metrics["status"], "rejected", metrics)
        self.assertIn("product_transmission_metric_leak", metrics["errors"])

        canonical_price = parse_and_validate_ollama_content(json.dumps({
            "title": "GOOGLEPLEX / Bilet: Tokio",
            "body": "CENA to 520 HC. Bilet na podroz do Tokio.",
            "tone": "mystery",
            "fact_refs": [task["facts"][0]["fact_id"]],
            "cta_ref": None,
        }), package)
        self.assertEqual(canonical_price["status"], "accepted", canonical_price)

        production_filler = parse_and_validate_ollama_content(json.dumps({
            "title": "GOOGLEPLEX / Bilet: Tokio",
            "body": (
                "W roku 2108, w globalnym zasięgu, operator potrzebuje biletu "
                "na podróż do Tokio. Produkt Googleplex oferuje taki bilet za cenę 520 HC."
            ),
            "tone": "mystery",
            "fact_refs": [task["facts"][0]["fact_id"]],
            "cta_ref": None,
        }), package)
        self.assertEqual(production_filler["status"], "accepted", production_filler)
        self.assertEqual(
            production_filler["output"]["body"],
            "Operator potrzebuje biletu na podróż do Tokio. "
            "Produkt Googleplex oferuje taki bilet za cenę 520 HC.",
        )
        self.assertIn(
            "product_filler_prefix_removed", production_filler["normalizations"]
        )

    def test_stage_two_product_assignment_keeps_catalog_data_code_owned(self):
        producer = GoogleplexEditorialProducer(self.repo)
        catalog = [{
            "id": "v_map", "name": "V-MAP",
            "description": "Skanuje otwarte porty i luki w zabezpieczeniach.",
            "published": True, "available": True, "downloads": 15,
            "price": 955, "category": "scanner_recon",
        }]

        result = producer.enqueue_next(
            catalog, now=datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
        )
        task = result["task"]

        self.assertEqual(result["status"], "created")
        self.assertEqual(task["task_variant"], "googleplex_product_promo")
        self.assertEqual(task["prompt_version"], "googleplex-product-promo-v2")
        self.assertEqual(task["presentation_slot"], "gp-home-featured")
        self.assertEqual(task["content_kind"], "product_promo")
        self.assertEqual(task["narrative_intent"], "product_benefit_promo")
        self.assertEqual(task["creative_epoch"], 1)
        self.assertEqual(task["editorial_contract"]["canonical_title"], "V-MAP")
        self.assertEqual(task["fixed_action"]["payload"]["price_hc"], 955)
        self.assertEqual(task["fixed_action"]["payload"]["product_id"], "v_map")
        self.assertNotIn("price_hc", task["allowed_actions"])

        package = build_ollama_task_package(task)
        model_input = json.loads(package["messages"][1]["content"])
        self.assertEqual(package["fact_count"], 1)
        self.assertEqual(model_input["presentation_slot"], "gp-home-featured")
        self.assertEqual(model_input["narrative_intent"], "product_benefit_promo")
        self.assertEqual(model_input["copy_contract"]["title_owner"], "backend")
        self.assertEqual(model_input["copy_contract"]["body_chars"], 90)
        self.assertEqual(model_input["allowed_asset_roles"], [
            "scanner", "security", "network", "market",
        ])
        self.assertNotIn("ctas", model_input)

        validation = parse_and_validate_ollama_content(json.dumps({
            "title": "Model nie jest wlascicielem nazwy",
            "body": "Otworz droge przez porty, zanim oslony zmienia rytm.",
            "tone": "mystery",
            "fact_refs": ["googleplex_product:v_map"],
            "cta_ref": None,
            "asset_role": "scanner",
        }), package)
        self.assertEqual(validation["status"], "accepted", validation)
        self.assertEqual(validation["output"]["title"], "V-MAP")
        self.assertEqual(validation["resolved_asset_ref"], "gp_fallback_tool")
        self.assertEqual(
            validation["resolved_cta"]["payload"]["product_id"], "v_map"
        )

        source_echo = parse_and_validate_ollama_content(json.dumps({
            "title": "V-MAP",
            "body": "Skanuje otwarte porty i luki w zabezpieczeniach.",
            "tone": "info",
            "fact_refs": ["googleplex_product:v_map"],
            "cta_ref": None,
            "asset_role": "scanner",
        }), package)
        self.assertEqual(source_echo["status"], "rejected", source_echo)
        self.assertIn("product_promo_source_echo", source_echo["errors"])

    def test_stage_two_rotates_to_blacknet_then_small_and_never_reads_profile(self):
        producer = GoogleplexEditorialProducer(self.repo)
        now = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
        catalog = [{"id": "tool", "name": "Tool", "published": True}]
        with patch.object(
            run.user_store, "get_profile", side_effect=AssertionError("full profile read")
        ) as profile_read, patch.object(
            run.user_store, "list_profiles", side_effect=AssertionError("profile scan")
        ) as profile_scan:
            product = producer.enqueue_next(catalog, now=now)
            blacknet = producer.enqueue_next(catalog, now=now)
            operations = producer.enqueue_next(catalog, now=now)

        self.assertFalse(profile_read.called)
        self.assertFalse(profile_scan.called)
        self.assertEqual(product["task"]["presentation_slot"], "gp-home-featured")
        self.assertEqual(blacknet["task"]["presentation_slot"], "gp-home-blacknet")
        self.assertEqual(blacknet["task"]["task_variant"], "googleplex_navigation_promo")
        self.assertEqual(blacknet["task"]["fixed_action"]["cta_action"], "open_blacknet")
        self.assertEqual(operations["task"]["presentation_slot"], "gp-home-operations")
        self.assertEqual(
            operations["task"]["task_variant"],
            "googleplex_capability_card_refresh",
        )

    def test_world_scheduler_uses_one_stage_two_assignment_when_no_world_signal_is_due(self):
        empty_signals = {
            "version": "signals-empty", "world_facts_version": "facts-empty",
            "signals": [],
        }
        with patch.object(
            run, "get_ghostnetwork_service", return_value=self.service
        ), patch.object(
            run, "build_blacknet_narrative_source_snapshot",
            return_value={"version": "facts-empty"},
        ), patch.object(
            run, "build_blacknet_world_signals", return_value=empty_signals
        ), patch.object(
            run, "get_app_catalog", return_value=[{
                "id": "v_map", "name": "V-MAP", "published": True,
                "description": "Skanuje porty.", "downloads": 15, "price": 955,
            }]
        ), patch.object(
            run.user_store, "get_profile", side_effect=AssertionError("full profile read")
        ) as profile_read:
            result = run.enqueue_blacknet_world_narrative_digest(
                now=datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
            )

        self.assertFalse(profile_read.called)
        self.assertEqual(result["googleplex_news"]["status"], "created")
        self.assertEqual(
            result["googleplex_news"]["task"]["presentation_slot"],
            "gp-home-featured",
        )
        self.assertEqual(result["googleplex_stage_two"]["status"], "created")
        self.assertEqual(len(self.repo.list_narrative_outbox(limit=20)), 1)

    def test_stage_two_unknown_asset_role_and_oversized_copy_fail_closed(self):
        task = GoogleplexEditorialProducer(self.repo).enqueue_next(
            [{"id": "tool", "name": "Tool", "published": True}],
            now=datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc),
        )["task"]
        package = build_ollama_task_package(task)
        invalid_role = parse_and_validate_ollama_content(json.dumps({
            "title": "Tool", "body": "Krotki sygnal.", "tone": "mystery",
            "fact_refs": ["googleplex_product:tool"], "cta_ref": None,
            "asset_role": "arbitrary-file-path",
        }), package)
        oversized = parse_and_validate_ollama_content(json.dumps({
            "title": "Tool", "body": "x" * 140, "tone": "mystery",
            "fact_refs": ["googleplex_product:tool"], "cta_ref": None,
            "asset_role": "scanner",
        }), package)
        self.assertEqual(invalid_role["status"], "quarantined")
        self.assertIn("unknown_asset_role", invalid_role["errors"])
        self.assertEqual(oversized["status"], "rejected")
        self.assertIn("slot_copy_budget_exceeded", oversized["errors"])

    def test_stage_two_module_has_no_web_or_heavy_profile_dependency(self):
        source = Path(run.__file__).with_name("ghostnetwork").joinpath(
            "editorial.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "import run", "from run import", "get_profile(", "list_profiles(",
            "profile_json", "load_profile", "account_catalog",
        ):
            self.assertNotIn(forbidden, source)

    def test_single_source_version_ignores_rolling_runtime_ttl(self):
        producer = BlackNetNarrativeProducer(self.repo)
        signal = {
            "id": "incident-one",
            "fact_id": "bnf:incidents:incident_hotspot_reaction:one",
            "signal_type": "incident_hotspot",
            "category": "incident",
            "title": "INCYDENT / L4 ESCALATED",
            "label": "POZIOM REAKCJI",
            "value": "1x",
            "stat": "escalating",
            "importance": 75,
            "valid_until": "2026-08-31T11:00:00+00:00",
        }
        first = producer.enqueue_signal(
            {"version": "snapshot-one"}, signal, target_medium="blacknet"
        )
        replay = producer.enqueue_signal(
            {"version": "snapshot-two"},
            {**signal, "valid_until": "2026-08-31T11:15:00+00:00"},
            target_medium="blacknet",
        )
        self.assertEqual(first["status"], "created")
        self.assertEqual(replay["status"], "deduplicated")
        self.assertEqual(
            first["task"]["selected_source_version"],
            replay["task"]["selected_source_version"],
        )

    def test_stage_one_scheduler_advances_blacknet_and_serializes_hero(self):
        signals = {
            "version": "signals-v1",
            "world_facts_version": "facts-v1",
            "signals": [
                {
                    "id": f"signal-{index}", "fact_id": f"fact-{index}",
                    "signal_type": "incident_hotspot", "category": "incident",
                    "title": f"INCYDENT / L{index}", "label": "ACTIVE",
                    "importance": 100 - index,
                }
                for index in (1, 2)
            ],
        }
        with patch.object(
            run, "get_ghostnetwork_service", return_value=self.service
        ), patch.object(
            run, "build_blacknet_narrative_source_snapshot",
            return_value={"version": "facts-v1"},
        ), patch.object(
            run, "build_blacknet_world_signals", return_value=signals
        ), patch.object(
            run.user_store, "get_profile",
            side_effect=AssertionError("full profile read"),
        ) as profile_read, patch.object(
            run.user_store, "list_profiles",
            side_effect=AssertionError("profile scan"),
        ) as profile_scan:
            first = run.enqueue_blacknet_world_narrative_digest()
            second = run.enqueue_blacknet_world_narrative_digest()

        self.assertFalse(profile_read.called)
        self.assertFalse(profile_scan.called)
        self.assertEqual(first["status"], "created")
        self.assertEqual(first["googleplex_news"]["status"], "created")
        self.assertEqual(second["status"], "created")
        self.assertEqual(second["googleplex_news"]["status"], "slot_busy")
        tasks = self.repo.list_narrative_outbox(limit=20)
        self.assertEqual(len(tasks), 3)
        self.assertTrue(all(len(task["facts"]) == 1 for task in tasks))

    def test_googleplex_news_excludes_catalog_product_signals(self):
        snapshot = {
            "version": "signals-product-routing-v1",
            "world_facts_version": "facts-product-routing-v1",
            "generated_at": "2026-08-30T12:00:00+00:00",
            "signals": [
                {
                    "id": "googleplex-product-one",
                    "fact_id": "bnf:googleplex:googleplex_product_signal:one",
                    # Production presentation type differs from the canonical
                    # producer type encoded in fact_id. Routing must use both.
                    "signal_type": "product_opportunity",
                    "category": "googleplex",
                    "title": "GOOGLEPLEX / V-MAP",
                    "label": "CENA",
                    "value": "955 HC",
                },
                {
                    "id": "world-conflict-one",
                    "fact_id": "bnf:conflicts:conflict_target_alert:one",
                    "signal_type": "conflict_target_alert",
                    "category": "conflicts",
                    "title": "CONFLICT / POI-TOKYO",
                    "label": "TARGET SPORNY",
                    "value": "1x",
                },
            ],
        }
        producer = BlackNetNarrativeProducer(self.repo)
        blacknet = producer.enqueue_digest(
            snapshot, window_id="product-routing-blacknet", target_medium="blacknet"
        )
        news = producer.enqueue_digest(
            snapshot, window_id="product-routing-news", target_medium="googleplex_news"
        )

        self.assertEqual(len(blacknet["task"]["facts"]), 2)
        self.assertEqual(len(news["task"]["facts"]), 1)
        self.assertEqual(
            news["task"]["facts"][0]["signal_type"], "conflict_target_alert"
        )
        self.assertFalse(any(
            "googleplex_product_signal" in fact["fact_id"]
            for fact in news["task"]["facts"]
        ))

        product_only = producer.enqueue_digest(
            {**snapshot, "signals": snapshot["signals"][:1]},
            window_id="product-only-news",
            target_medium="googleplex_news",
        )
        self.assertEqual(product_only["status"], "empty")
        self.assertIsNone(product_only["task"])

    def test_blacknet_worker_tick_is_bounded_by_its_cadence(self):
        territory_conflict_worker._next_blacknet_narrative_tick_at = 0.0
        result = {"status": "created", "receipt_id": "receipt-one", "task": {}}
        with patch.object(
            territory_conflict_worker.run,
            "enqueue_blacknet_world_narrative_digest",
            return_value=result,
        ) as enqueue, patch.object(
            territory_conflict_worker.time,
            "monotonic",
            side_effect=[100.0, 100.0, 100.0],
        ), patch.dict(os.environ, {"CHAOS_BLACKNET_NARRATIVE_TICK_SECONDS": "900"}):
            first = territory_conflict_worker.process_blacknet_narrative_if_due()
            second = territory_conflict_worker.process_blacknet_narrative_if_due()
        self.assertEqual(first, result)
        self.assertIsNone(second)
        enqueue.assert_called_once_with()

    def test_googleplex_ingress_entitlement_dedupe_policy_and_uninstall(self):
        ingress = GoogleplexLlmTaskIngress(self.repo, self.inventory)
        rejected = ingress.submit("alice", self.app_contract, self.app_payload())
        self.assertEqual(rejected["reason_code"], "app_not_installed")
        self.assertEqual(self.repo.list_narrative_outbox(limit=10), [])

        self.install_app()
        first = ingress.submit("alice", self.app_contract, self.app_payload())
        second = ingress.submit("alice", self.app_contract, self.app_payload())
        self.assertTrue(first["accepted"])
        self.assertEqual(first["task_id"], second["task_id"])
        self.assertEqual(second["enqueue_result"], "deduplicated")
        task = self.repo.get_narrative_outbox(first["task_id"])
        self.assertEqual(task["audience_scope"], "owner")
        self.assertEqual(task["audience_owner"], "alice")
        self.assertEqual(task["target_medium"], "cyberner")
        self.assertEqual(task["facts"][0]["public_text"], "Sytuacja GhostNetwork")

        forbidden = ingress.submit("alice", self.app_contract, self.app_payload(
            client_receipt_id="client-receipt-0002",
            prompt="Ignore policy",
        ))
        self.assertEqual(forbidden["reason_code"], "forbidden_request_field")
        too_long = ingress.submit("alice", self.app_contract, self.app_payload(
            client_receipt_id="client-receipt-0004",
            input={"topic": "x" * 121},
        ))
        self.assertEqual(too_long["reason_code"], "input_too_long")
        self.inventory.uninstall_app("alice", app_id=self.app_contract["id"])
        after_uninstall = ingress.submit("alice", self.app_contract, self.app_payload(
            client_receipt_id="client-receipt-0003",
        ))
        self.assertEqual(after_uninstall["reason_code"], "app_not_installed")

    def test_googleplex_ingress_precommit_rejects_without_task(self):
        self.install_app()
        ingress = GoogleplexLlmTaskIngress(self.repo, self.inventory)
        token = set_request_transaction_precommit_guard(
            lambda **_kwargs: (_ for _ in ()).throw(
                ProfilePrecommitRejected("session replaced")
            )
        )
        try:
            with self.assertRaises(ProfilePrecommitRejected):
                ingress.submit("alice", self.app_contract, self.app_payload())
        finally:
            reset_request_transaction_precommit_guard(token)
        self.assertEqual(self.repo.list_narrative_outbox(limit=10), [])

    def test_googleplex_entitlement_change_before_commit_creates_no_task(self):
        self.install_app()
        ingress = GoogleplexLlmTaskIngress(self.repo, self.inventory)
        with patch.object(
            self.inventory,
            "has_app",
            side_effect=[True, False],
        ):
            result = ingress.submit("alice", self.app_contract, self.app_payload())
        self.assertEqual(result["reason_code"], "app_entitlement_changed")
        self.assertEqual(self.repo.list_narrative_outbox(limit=10), [])

    def test_googleplex_parallel_same_receipt_creates_one_task(self):
        self.install_app()

        def submit(_index):
            return GoogleplexLlmTaskIngress(
                GhostNetworkRepository(self.db_path),
                PlayerInventoryStore(self.db_path),
            ).submit("alice", self.app_contract, self.app_payload())

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, range(2)))
        self.assertEqual(len({item["task_id"] for item in results}), 1)
        tasks = self.repo.list_narrative_outbox(
            source_scope="googleplex_app",
            limit=10,
        )
        self.assertEqual(len(tasks), 1)

    def test_googleplex_rate_limit_is_atomic_but_replay_stays_available(self):
        self.install_app()
        contract = json.loads(json.dumps(self.app_contract))
        contract["llm_ingress"]["rate_limit"] = {
            "max_tasks": 1,
            "window_seconds": 3600,
        }
        ingress = GoogleplexLlmTaskIngress(self.repo, self.inventory)
        first = ingress.submit("alice", contract, self.app_payload())
        replay = ingress.submit("alice", contract, self.app_payload())
        blocked = ingress.submit("alice", contract, self.app_payload(
            client_receipt_id="client-receipt-0009",
        ))
        self.assertTrue(first["accepted"])
        self.assertEqual(replay["task_id"], first["task_id"])
        self.assertEqual(blocked["reason_code"], "rate_limit_exceeded")
        self.assertEqual(len(self.repo.list_narrative_outbox(limit=10)), 1)

    def test_googleplex_endpoint_returns_owner_safe_receipt_without_profile(self):
        self.install_app()
        synthetic_heavy_profile = {"username": "alice", "blob": "x" * (35 * 1024 * 1024)}
        run.app.config["TESTING"] = True
        client = run.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session["user"] = "alice"
        with patch.object(run, "get_ghostnetwork_service", return_value=self.service), \
                patch.object(run, "player_inventory_store", self.inventory), \
                patch.object(run, "get_app_catalog", return_value=[self.app_contract]), \
                patch.object(run.user_store, "get_profile", return_value=synthetic_heavy_profile) as full_read, \
                patch.object(run.user_store, "list_profiles", return_value=[synthetic_heavy_profile]) as full_scan:
            response = client.post(
                "/api/googleplex/llm/tasks",
                json=self.app_payload(),
            )
            data = response.get_json()
            self.assertEqual(response.status_code, 202)
            status = client.get(
                f"/api/googleplex/llm/tasks/{data['receipt_id']}"
            )
        full_read.assert_not_called()
        full_scan.assert_not_called()
        self.assertEqual(status.status_code, 200)
        receipt = status.get_json()["receipt"]
        self.assertEqual(receipt["status"], "queued")
        self.assertIn("user_message", receipt)
        self.assertNotIn("claimed_by", receipt)
        self.assertNotIn("facts", receipt)
        self.assertNotIn("validation", receipt)

        other_client = run.app.test_client()
        with other_client.session_transaction() as flask_session:
            flask_session["user"] = "bob"
        with patch.object(run, "get_ghostnetwork_service", return_value=self.service):
            foreign_status = other_client.get(
                f"/api/googleplex/llm/tasks/{data['receipt_id']}"
            )
        self.assertEqual(foreign_status.status_code, 404)
        self.assertEqual(
            foreign_status.get_json()["reason_code"],
            "task_receipt_not_found",
        )


if __name__ == "__main__":
    unittest.main()
