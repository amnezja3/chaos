import os
import tempfile
import unittest

from database import dumps_json
from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService
from ghostnetwork.closure import GhostNetworkClosureService


class GhostNetworkNarrativeOutboxTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        self.cycles = GhostCycleService(repository=self.repo)
        self.closure = GhostNetworkClosureService(repository=self.repo)
        self.service = GhostNetworkService(repository=self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def create_locked_cycle(self):
        cycle = self.cycles.create_cycle()["cycle"]
        now = self.repo.now()
        for index, part in enumerate(self.repo.list_parts(cycle["cycle_id"])):
            lat = 52.20 + index * 0.001
            lng = 21.00 + index * 0.001
            self.repo.update_part(
                part["part_id"],
                status="active",
                target_id=f"POI-{part['part_code']}",
                latitude=lat,
                longitude=lng,
                discovered_by=f"operator-{index}",
                discovered_clan=part["clan_code"],
                discovered_at=now,
                anchor_snapshot_json=dumps_json(
                    {
                        "target_id": f"POI-{part['part_code']}",
                        "lat": lat,
                        "lng": lng,
                        "label": part["part_code"],
                    }
                ),
                territory_id=f"territory-{part['part_code']}",
                territory_owner_id=f"operator-{index}",
                territory_clan=part["clan_code"],
                territory_state_version=3000 + index,
                activated_at=now,
                last_activated_at=now,
                conflict_state="none",
                conflict_id="",
            )
        closing_part = self.repo.list_parts(cycle["cycle_id"])[-1]
        closing_event = self.repo.append_event(
            "ghost.part_activated",
            cycle_id=cycle["cycle_id"],
            part_id=closing_part["part_id"],
            entity_id=closing_part["part_id"],
            player_id="closing-operator",
            clan_code=closing_part["clan_code"],
            territory_id=closing_part["territory_id"],
            dedupe_key=f"test:narrative:closing:{cycle['cycle_id']}",
            event_id=f"event-narrative-closing-{cycle['cycle_id']}",
            payload={"player_id": "closing-operator"},
        )
        lock = self.closure.attempt_cycle_lock(cycle["cycle_id"], closing_event["event_id"])
        self.assertTrue(lock["locked"], lock)
        return self.repo.get_cycle(cycle["cycle_id"])

    def test_transmission_creates_safe_media_outbox(self):
        cycle = self.create_locked_cycle()
        result = self.service.start_transmission(cycle["cycle_id"])
        self.assertTrue(result["ok"], result)
        self.assertIn("narrative", result)
        self.assertTrue(result["narrative"]["ok"], result["narrative"])

        signal_id = result["signal"]["signal_id"]
        outbox = self.repo.list_narrative_outbox(signal_id=signal_id, limit=20)
        self.assertEqual({item["target_medium"] for item in outbox}, {"blacknet", "cyberner", "radio"})
        self.assertTrue(all(item["status"] == "ready" for item in outbox))
        self.assertTrue(all(item["truth_class"] == "canonical" for item in outbox))
        self.assertTrue(all(item["processor"] == "ollama" for item in outbox))
        self.assertTrue(all(item["schema_version"] == "ghost-narrative-task-v1" for item in outbox))
        self.assertEqual(len({item["dedupe_key"] for item in outbox}), 3)

        for item in outbox:
            self.assertEqual(item["cycle_id"], cycle["cycle_id"])
            self.assertEqual(item["signal_id"], signal_id)
            self.assertEqual(item["audience_scope"], "public")
            self.assertEqual(item["canon_version"], "ghostnetwork-narrative-v1")
            fact_types = {fact["fact_type"] for fact in item["facts"]}
            self.assertIn("signal_sent", fact_types)
            self.assertIn("network_closed", fact_types)
            self.assertNotIn("parts", dumps_json(item["facts"]))
            self.assertNotIn("password", dumps_json(item["facts"]))
            self.assertNotIn("session", dumps_json(item["facts"]))
            action_names = {action["cta_action"] for action in item["allowed_actions"]}
            self.assertTrue(action_names.issubset({
                "open_ghostnetwork_suite",
                "open_ghostsignal_archive",
                "open_cyberner_channel",
                "play_ghostnetwork_podcast",
            }))
            self.assertNotIn("teleport_without_confirmation", action_names)

    def test_narrative_publish_is_idempotent(self):
        cycle = self.create_locked_cycle()
        result = self.service.start_transmission(cycle["cycle_id"])
        event = self.repo.get_event_by_dedupe_key(f"ghost:signal_sent:{cycle['cycle_id']}")
        first_count = len(self.repo.list_narrative_outbox(signal_id=result["signal"]["signal_id"], limit=20))
        second = self.service.publish_narrative_event(event)
        second_count = len(self.repo.list_narrative_outbox(signal_id=result["signal"]["signal_id"], limit=20))
        self.assertEqual(first_count, second_count)
        self.assertTrue(all(item.get("idempotent") for item in second["outbox"]))

    def test_retry_failed_publications_does_not_duplicate(self):
        cycle = self.create_locked_cycle()
        result = self.service.start_transmission(cycle["cycle_id"])
        item = self.repo.list_narrative_outbox(signal_id=result["signal"]["signal_id"], medium="blacknet")[0]
        self.repo.update_narrative_outbox_status(item["outbox_id"], "failed", validation={"ok": False})

        before = len(self.repo.list_narrative_outbox(signal_id=result["signal"]["signal_id"], limit=20))
        retried = self.service.retry_failed_narrative_publications()
        after = len(self.repo.list_narrative_outbox(signal_id=result["signal"]["signal_id"], limit=20))
        updated = self.repo.get_narrative_outbox(item["outbox_id"])
        self.assertEqual(before, after)
        self.assertEqual(retried["count"], 1)
        self.assertEqual(updated["status"], "ready")

    def test_ollama_output_cannot_add_facts_or_unsafe_cta(self):
        cycle = self.create_locked_cycle()
        result = self.service.start_transmission(cycle["cycle_id"])
        item = self.repo.list_narrative_outbox(signal_id=result["signal"]["signal_id"], medium="blacknet")[0]
        invalid = self.service.narrative.validate_model_output(
            item,
            {
                "medium": "blacknet",
                "truth_class": "canonical",
                "title": "GhostSignal",
                "body": "New hidden part captured",
                "fact_refs": ["not-in-package"],
                "cta_action": "teleport_without_confirmation",
            },
        )
        self.assertFalse(invalid["ok"])
        self.assertIn("unknown_fact_ref", invalid["errors"])
        self.assertIn("cta_not_allowed", invalid["errors"])


if __name__ == "__main__":
    unittest.main()
