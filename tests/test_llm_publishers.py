import copy
import unittest
from unittest.mock import Mock, patch

from flask import g, session

from database import get_hot_path_metrics, reset_hot_path_metrics, restore_hot_path_metrics
from googleplex_news import build_googleplex_news_snapshot, merge_googleplex_news_publications
import run


def publication(record_id="medium-one", medium="googleplex_news", **overrides):
    record = {
        "medium_record_id": record_id,
        "publication_ordinal": 7,
        "publication_receipt_id": f"receipt-{record_id}",
        "target_medium": medium,
        "audience_scope": "public",
        "audience_clan": "",
        "audience_owner": "",
        "source_scope": "blacknet_world",
        "source_event_id": "event-one",
        "source_receipt_id": "source-receipt-one",
        "truth_class": "canonical",
        "title": "Bezpieczny tytul",
        "body": "Narracja oparta na faktach.",
        "tone": "info",
        "fact_refs": ["fact:one"],
        "cta_ref": "cta:one",
        "cta_action": "open_map",
        "cta_payload": {"target_id": "world"},
        "presentation_slot": "gp-home-world-grid",
        "published_at": "2026-08-29T12:00:00+00:00",
    }
    record.update(overrides)
    return record


class LlmPublisherAdapterTest(unittest.TestCase):
    def test_googleplex_news_replaces_stable_slots_without_growing_feed(self):
        snapshot = build_googleplex_news_snapshot(
            catalog=[{"id": "tool", "name": "Tool", "published": True}],
            viewer_key="alice", session_generation="one", limit=20,
        )
        foundation_ids = {
            item["content"]["news_id"] for item in snapshot["entries"]
        }
        records = [
            publication(
                f"medium-{index}", fact_refs=[f"fact:{index}"],
                title=f"Bezpieczny tytul {index}",
                body=f"Narracja oparta na fakcie {index}.",
            )
            for index in range(10)
        ]
        merged = merge_googleplex_news_publications(copy.deepcopy(snapshot), records, limit=20)
        published = [
            item for item in merged["entries"]
            if item["content"]["source"] == "ollama_enriched"
        ]
        self.assertEqual(len(published), 1)
        self.assertEqual(len(merged["entries"]), len(snapshot["entries"]))
        self.assertEqual(
            {item["content"]["news_id"] for item in merged["entries"]},
            foundation_ids,
        )
        self.assertNotIn("medium-0", {
            item["content"]["news_id"] for item in merged["entries"]
        })
        self.assertEqual(merged["entries"][0]["presentation"]["weight"], "hero")
        self.assertEqual(merged["entries"][0]["content"]["news_id"], "gp-home-world-grid")
        self.assertTrue(merged["protocol_status"]["publication_enabled"])
        self.assertTrue(merged["protocol_status"]["ollama_used"])

        for slot_id in foundation_ids - {"gp-home-world-grid"}:
            before = next(
                item for item in snapshot["entries"]
                if item["content"]["news_id"] == slot_id
            )
            after = next(
                item for item in merged["entries"]
                if item["content"]["news_id"] == slot_id
            )
            self.assertEqual(after, before)

    def test_googleplex_news_ignores_publication_without_explicit_slot(self):
        snapshot = build_googleplex_news_snapshot(
            catalog=[], viewer_key="alice", session_generation="one", limit=20,
        )
        merged = merge_googleplex_news_publications(
            snapshot, [publication(presentation_slot="")], limit=20
        )
        self.assertFalse(any(
            item["content"]["source"] == "ollama_enriched"
            for item in merged["entries"]
        ))

    def test_stage_two_navigation_and_small_copy_update_only_assigned_slots(self):
        snapshot = build_googleplex_news_snapshot(
            catalog=[], viewer_key="alice", session_generation="one", limit=20,
        )
        before = {
            item["content"]["news_id"]: copy.deepcopy(item)
            for item in snapshot["entries"]
        }
        records = [
            publication(
                "blacknet-promo", presentation_slot="gp-home-blacknet",
                content_kind="navigation_promo", title="Przechwyc szum swiata",
                body="Wejdz w strumien sygnalow, zanim zaklocenia zmienia ich rytm.",
                asset_ref="gp_fallback_network", cta_action="open_blacknet",
                cta_payload={"target_id": "world"},
            ),
            publication(
                "operations-copy", presentation_slot="gp-home-operations",
                content_kind="capability_card", title="Rytm operacji",
                body="Sprawdz aktywne i zakonczone dzialania.",
                asset_ref="gp_fallback_system", cta_action="open_operation",
                cta_payload={"target_id": "operation-center"},
            ),
            publication(
                "disabled-slot", presentation_slot="gp-home-integrity",
                content_kind="capability_card", title="Nielegalna podmiana",
                body="Ten systemowy slot pozostaje statyczny.",
                asset_ref="gp_fallback_system",
            ),
        ]

        merged = merge_googleplex_news_publications(snapshot, records, limit=20)
        after = {
            item["content"]["news_id"]: item for item in merged["entries"]
        }

        self.assertEqual(after["gp-home-blacknet"]["content"]["title"], "Przechwyc szum swiata")
        self.assertEqual(after["gp-home-blacknet"]["action"]["action_type"], "open_blacknet")
        self.assertEqual(after["gp-home-operations"]["content"]["title"], "Rytm operacji")
        self.assertEqual(after["gp-home-operations"]["action"]["action_type"], "open_operation")
        self.assertEqual(after["gp-home-integrity"], before["gp-home-integrity"])
        for slot_id in set(before) - {"gp-home-blacknet", "gp-home-operations"}:
            self.assertEqual(after[slot_id], before[slot_id])
        self.assertEqual(set(merged["diagnostics"]["publication_slot_ids"]), {
            "gp-home-blacknet", "gp-home-operations",
        })

    def test_googleplex_news_drops_unapproved_cta_without_dropping_content(self):
        snapshot = build_googleplex_news_snapshot(
            catalog=[], viewer_key="alice", session_generation="one", limit=20,
        )
        merged = merge_googleplex_news_publications(
            snapshot, [publication(cta_action="arbitrary_tool_call")], limit=20
        )
        entry = merged["entries"][0]
        self.assertEqual(entry["content"]["source"], "ollama_enriched")
        self.assertEqual(entry["action"]["kind"], "STAMP_ONLY")

    def test_googleplex_news_deduplicates_identical_content_across_fact_refs(self):
        snapshot = build_googleplex_news_snapshot(
            catalog=[], viewer_key="alice", session_generation="one", limit=20,
        )
        records = [
            publication(
                "duplicate-content-one", fact_refs=["fact:one"],
                title="Napięcie rośnie nad Tokio",
                body="W pobliżu miasta wykryto aktywny konflikt.",
            ),
            publication(
                "duplicate-content-two", fact_refs=["fact:two"],
                title="  Napięcie   rośnie nad Tokio ",
                body="W pobliżu miasta wykryto aktywny konflikt.",
            ),
        ]

        merged = merge_googleplex_news_publications(snapshot, records, limit=20)
        enriched = [
            item for item in merged["entries"]
            if item["content"]["source"] == "ollama_enriched"
        ]

        self.assertEqual(len(enriched), 1)

    def test_googleplex_news_hides_historical_unsafe_publication(self):
        snapshot = build_googleplex_news_snapshot(
            catalog=[], viewer_key="alice", session_generation="one", limit=20,
        )
        merged = merge_googleplex_news_publications(snapshot, [publication(
            body="Produkt 02b4180b63e5 jest aktywny."
        )], limit=20)
        self.assertFalse(any(
            item["content"]["source"] == "ollama_enriched"
            for item in merged["entries"]
        ))

    def test_googleplex_product_card_remains_canonical_catalog_projection(self):
        snapshot = build_googleplex_news_snapshot(
            catalog=[{
                "id": "v-map", "name": "V-MAP", "published": True,
                "description": "Skanuje i szuka otwartych portow i luk w zabezpieczeniach.",
                "downloads": 15,
            }],
            viewer_key="alice", session_generation="one", limit=20,
        )
        product_record = publication(
            "historical-product-publication",
            fact_refs=["blacknet_fact:bnf:googleplex:googleplex_product_signal:v-map"],
            title="Modelowy tytul produktu",
            body="Modelowy opis produktu.",
        )

        merged = merge_googleplex_news_publications(snapshot, [product_record], limit=20)
        featured = next(
            item for item in merged["entries"]
            if item["content"]["news_id"] == "gp-home-featured"
        )

        self.assertEqual(featured["content"]["source"], "googleplex")
        self.assertEqual(featured["content"]["title"], "V-MAP")
        self.assertEqual(
            featured["content"]["summary"],
            "Skanuje i szuka otwartych portow i luk w zabezpieczeniach.",
        )
        self.assertEqual(featured["presentation"]["primary_stat"], "15 DL")
        self.assertEqual(featured["action"]["action_type"], "open_googleplex_search")
        self.assertEqual(featured["action"]["action_target"], "V-MAP")
        self.assertEqual(featured["action"]["action_payload_ref"], "v-map")
        self.assertFalse(any(
            item["content"]["source"] == "ollama_enriched"
            for item in merged["entries"]
        ))

    def test_blacknet_projection_preserves_labels_and_fails_closed_on_cta(self):
        signal = run.blacknet_signal_from_publication(publication(
            medium="blacknet", cta_action="arbitrary_tool_call"
        ))
        self.assertEqual(signal["source"], "ollama_enriched")
        self.assertEqual(signal["cta_action"], "none")
        self.assertEqual(signal["metadata"]["truth_class"], "canonical")
        self.assertEqual(signal["metadata"]["fact_refs"], ["fact:one"])

        unsafe_teleport = run.blacknet_signal_from_publication(publication(
            medium="blacknet", cta_action="teleport_to_hotspot",
            cta_payload={"target_id": "incident_badd648821f3"},
        ))
        self.assertEqual(unsafe_teleport["cta_action"], "focus_map_target")

        coordinate_teleport = run.blacknet_signal_from_publication(publication(
            medium="blacknet", cta_action="teleport_to_hotspot",
            cta_payload={
                "target_id": "incident_canonical", "lat": 52.2297,
                "lng": 21.0122, "label": "okolice Warszawy",
            },
        ))
        self.assertEqual(coordinate_teleport["cta_action"], "teleport_to_hotspot")
        self.assertEqual(coordinate_teleport["metadata"]["lat"], 52.2297)
        self.assertEqual(coordinate_teleport["metadata"]["lng"], 21.0122)
        self.assertEqual(coordinate_teleport["metadata"]["hotspot_id"], "")
        self.assertNotIn("52.2297", coordinate_teleport["metadata"]["target_label"])

        incident_preview = run.blacknet_signal_from_publication(publication(
            medium="blacknet", cta_action="teleport_to_hotspot",
            fact_refs=["blacknet_fact:bnf:incidents:incident_hotspot_reaction:one"],
            cta_payload={
                "target_id": "incident_one", "lat": 52.23,
                "lng": 21.01, "label": "Strefa incydentu L4",
            },
        ))
        self.assertEqual(incident_preview["cta_action"], "focus_map_target")
        self.assertEqual(incident_preview["cta"], "POKAZ NA MAPIE")
        self.assertEqual(incident_preview["metadata"]["lat"], 52.23)
        self.assertEqual(incident_preview["metadata"]["lng"], 21.01)

    def test_blacknet_endpoint_caps_narratives_and_keeps_deterministic_signal(self):
        heavy_profile_fixture = {"payload": "x" * (35 * 1024 * 1024)}
        self.assertGreaterEqual(len(heavy_profile_fixture["payload"]), 35 * 1024 * 1024)
        records = [
            publication(
                f"blacknet-{index}", medium="blacknet",
                fact_refs=["blacknet_fact:deterministic-one"],
                source_receipt_id=f"source-{index}",
            )
            for index in range(5)
        ]
        foundation = {
            "version": "foundation-v1",
            "signals": [{
                "id": "deterministic-one", "fact_id": "deterministic-one",
                "source": "world_generated",
            }],
            "diagnostics": {},
        }
        repository = Mock()
        repository.list_narrative_medium_records_for_viewer.return_value = records
        service = Mock(repository=repository)
        token = reset_hot_path_metrics()
        try:
            with run.app.test_request_context("/api/blacknet/world-signals?limit=8"):
                session["user"] = "alice"
                g.session_generation = "generation-a"
                with patch.object(run, "build_blacknet_world_signals", return_value=foundation), patch.object(
                    run.identity_projection_store, "get_identity", return_value={"username": "alice"}
                ), patch.object(run, "get_ghostnetwork_service", return_value=service), patch.object(
                    run.user_store, "get_profile", side_effect=AssertionError("35 MB full profile read")
                ) as profile_read, patch.object(
                    run.user_store, "list_profiles", side_effect=AssertionError("profile scan")
                ) as profile_scan:
                    response = run.api_blacknet_world_signals()
                self.assertFalse(profile_read.called)
                self.assertFalse(profile_scan.called)
            metrics = get_hot_path_metrics()
        finally:
            restore_hot_path_metrics(token)
        payload = response.get_json()["snapshot"]
        self.assertEqual(payload["diagnostics"]["published_narratives"], 1)
        self.assertEqual(payload["diagnostics"]["suppressed_narrated_fallbacks"], 1)
        self.assertNotIn("deterministic-one", [item["id"] for item in payload["signals"]])
        self.assertNotEqual(payload["version"], "foundation-v1")
        for key in (
            "profile_full_read", "profile_full_write", "profile_bytes",
            "all_user_profile_scan", "per_recipient_profile_read",
        ):
            self.assertEqual(metrics[key], 0)

    def test_agi_channel_is_owner_scoped_read_only_publication_projection(self):
        owner_record = publication(
            "agi-owner", medium="cyberner", source_scope="googleplex_app",
            audience_scope="owner", audience_owner="alice",
        )
        repository = Mock()
        repository.list_narrative_medium_records.return_value = [owner_record]
        route = {
            "channel": "agi2108", "channel_key": "agi-2108:alice",
            "store_key": "alice",
        }
        with patch.object(run, "get_ghostnetwork_service", return_value=Mock(repository=repository)):
            messages = run.cyberner_list_route_messages("alice", route, limit=10)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["sender"], "AI Central / AGI 2108")
        repository.list_narrative_medium_records.assert_called_once_with(
            "cyberner", audience_scope="owner", audience_owner="alice", limit=10
        )
        with self.assertRaisesRegex(ValueError, "tylko do odczytu"):
            run.cyberner_store_message("alice", {"username": "alice"}, route, "hello")

    def test_agi_rejected_candidate_is_unavailable_and_never_echoed(self):
        repository = Mock()
        repository.list_narrative_outbox.return_value = [{
            "outbox_id": "task-one", "status": "completed",
            "audience_scope": "owner", "audience_owner": "alice",
            "created_at": "2026-08-29T12:00:00+00:00",
            "updated_at": "2026-08-29T12:01:00+00:00",
            "facts": [{"public_text": "Jak znalezc czesc?"}],
        }]
        repository.get_narrative_candidate_for_task.return_value = {
            "validation_status": "rejected",
            "validation_errors": ["owner_analysis_echo"],
        }
        repository.get_narrative_publication_for_source_receipt.return_value = publication(
            "agi-echo", medium="cyberner", source_scope="googleplex_app",
            audience_scope="owner", audience_owner="alice",
            title="Analiza AGI", body="Jak znalezc czesc?",
        )
        with run.app.test_request_context("/api/googleplex/llm/tasks/receipt-one"):
            session["user"] = "alice"
            with patch.object(
                run, "get_ghostnetwork_service",
                return_value=Mock(repository=repository),
            ):
                response = run.api_googleplex_llm_task_status("receipt-one")
        payload = response.get_json()
        self.assertEqual(payload["receipt"]["status"], "failed")
        self.assertNotIn("publication", payload)
        self.assertNotIn("owner_analysis_echo", str(payload))


if __name__ == "__main__":
    unittest.main()
