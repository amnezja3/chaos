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
        "published_at": "2026-08-29T12:00:00+00:00",
    }
    record.update(overrides)
    return record


class LlmPublisherAdapterTest(unittest.TestCase):
    def test_googleplex_news_merges_bounded_publication_and_keeps_fallback(self):
        snapshot = build_googleplex_news_snapshot(
            catalog=[{"id": "tool", "name": "Tool", "published": True}],
            viewer_key="alice", session_generation="one", limit=20,
        )
        foundation_ids = {
            item["content"]["news_id"] for item in snapshot["entries"]
        }
        records = [publication(f"medium-{index}") for index in range(10)]
        merged = merge_googleplex_news_publications(copy.deepcopy(snapshot), records, limit=20)
        published = [
            item for item in merged["entries"]
            if item["content"]["source"] == "ollama_enriched"
        ]
        self.assertEqual(len(published), 6)
        self.assertTrue(foundation_ids.intersection(
            item["content"]["news_id"] for item in merged["entries"]
        ))
        self.assertTrue(merged["protocol_status"]["publication_enabled"])
        self.assertTrue(merged["protocol_status"]["ollama_used"])

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

    def test_blacknet_projection_preserves_labels_and_fails_closed_on_cta(self):
        signal = run.blacknet_signal_from_publication(publication(
            medium="blacknet", cta_action="arbitrary_tool_call"
        ))
        self.assertEqual(signal["source"], "ollama_enriched")
        self.assertEqual(signal["cta_action"], "none")
        self.assertEqual(signal["metadata"]["truth_class"], "canonical")
        self.assertEqual(signal["metadata"]["fact_refs"], ["fact:one"])

    def test_blacknet_endpoint_caps_narratives_and_keeps_deterministic_signal(self):
        heavy_profile_fixture = {"payload": "x" * (35 * 1024 * 1024)}
        self.assertGreaterEqual(len(heavy_profile_fixture["payload"]), 35 * 1024 * 1024)
        records = [publication(f"blacknet-{index}", medium="blacknet") for index in range(5)]
        foundation = {
            "version": "foundation-v1",
            "signals": [{"id": "deterministic-one", "source": "world_generated"}],
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
        self.assertEqual(payload["diagnostics"]["published_narratives"], 2)
        self.assertIn("deterministic-one", [item["id"] for item in payload["signals"]])
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


if __name__ == "__main__":
    unittest.main()
