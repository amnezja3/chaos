import os
import tempfile
import unittest

from database import dumps_json
from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService


class GhostNetworkArchiveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        self.cycle_service = GhostCycleService(repository=self.repo)
        self.service = GhostNetworkService(repository=self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def create_locked_cycle(self):
        cycle = self.cycle_service.create_cycle()["cycle"]
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
                territory_state_version=2000 + index,
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
            dedupe_key=f"test:archive:closing:{cycle['cycle_id']}",
            event_id=f"event-archive-closing-{cycle['cycle_id']}",
            payload={"player_id": "closing-operator"},
        )
        lock = self.service.attempt_cycle_lock(cycle["cycle_id"], closing_event["event_id"])
        self.assertTrue(lock["locked"], lock)
        return self.repo.get_cycle(cycle["cycle_id"])

    def transmit_locked_cycle(self):
        cycle = self.create_locked_cycle()
        result = self.service.start_transmission(cycle["cycle_id"])
        self.assertTrue(result["ok"], result)
        self.assertTrue(result.get("archive", {}).get("ok"), result)
        return cycle, result

    def test_signal_archive_is_created_and_idempotent(self):
        _cycle, result = self.transmit_locked_cycle()
        signal_id = result["signal"]["signal_id"]

        first_detail = self.service.get_signal_archive_detail(signal_id, include_private=True)
        self.assertTrue(first_detail["ok"], first_detail)
        self.assertEqual(first_detail["archive_version"], "ghostnetwork.archive.v1")
        self.assertEqual(first_detail["signal"]["historical_nodes_count"], 20)
        self.assertEqual(len(first_detail["historical_nodes"]), 20)
        self.assertGreaterEqual(len(first_detail["achievements"]), 20)
        self.assertIn("discoverers", first_detail["private"])

        first_count = len(first_detail["achievements"])
        retry = self.service.finalize_signal_archive(signal_id)
        self.assertTrue(retry["ok"], retry)
        second_detail = self.service.get_signal_archive_detail(signal_id, include_private=True)
        self.assertEqual(len(second_detail["achievements"]), first_count)

    def test_archive_lists_player_history_and_map_nodes(self):
        _cycle, result = self.transmit_locked_cycle()
        signal_id = result["signal"]["signal_id"]

        signals = self.service.list_signal_archive(limit=5)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["signal_id"], signal_id)
        self.assertEqual(signals[0]["participants_count"], 21)

        player = self.service.get_player_archive_history("closing-operator")
        self.assertTrue(player["ok"], player)
        self.assertEqual(player["signals_count"], 1)
        self.assertGreater(player["ghostnetwork_rsp"], 0)
        self.assertTrue(any(item["achievement_code"] == "signal_operator" for item in player["achievements"]))

        layer = self.service.get_historical_map_layer(signal_id=signal_id)
        self.assertTrue(layer["ok"], layer)
        self.assertEqual(len(layer["nodes"]), 20)
        self.assertTrue(all("latitude" in node and "longitude" in node for node in layer["nodes"]))

    def test_archive_readiness_report_stays_read_only(self):
        self.transmit_locked_cycle()
        report = self.service.get_archive_readiness_report()
        self.assertEqual(report["archive_version"], "ghostnetwork.archive.v1")
        self.assertIn("health", report)
        self.assertTrue(report["latest_signal_detail_ok"], report)
        self.assertGreaterEqual(report["signals_archived"], 1)
        self.assertFalse(report["flags"]["suite_ui_enabled"])
        self.assertFalse(report["flags"]["ollama_control_enabled"])
        self.assertIn("first_contact", report["achievement_codes"])


if __name__ == "__main__":
    unittest.main()
