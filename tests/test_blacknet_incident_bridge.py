import json
import math
import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import run
from response_network.incident_store import IncidentStore


def temp_db_path():
    fd, path = tempfile.mkstemp(prefix="chaos_blacknet_incident_", suffix=".sqlite")
    os.close(fd)
    os.remove(path)
    return path


def distance_m(a, b):
    lat1 = math.radians(float(a["lat"]))
    lat2 = math.radians(float(b["lat"]))
    dlat = lat2 - lat1
    dlng = math.radians(float(b["lng"]) - float(a["lng"]))
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 6_371_000 * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


class BlackNetIncidentBridgeTest(unittest.TestCase):
    def make_store(self):
        path = temp_db_path()
        return path, IncidentStore(db_path=path)

    def seed_incident(self, store, status="active"):
        return store.upsert({
            "incident_id": "incident_bridge",
            "status": status,
            "level": 3,
            "heat": 91,
            "center": {"lat": 52.23, "lng": 21.01},
            "search_radius_m": 260,
            "operation_ids": ["op-secret"],
            "suspect_refs": [{"actor_id": "main"}],
            "territory_refs": [{"territory_id": "territory-a"}],
            "npc_capsule_ids": [],
            "expires_at": "2026-07-14T11:00:00+00:00",
        }, event_type="incident.created", now="2026-07-14T10:00:00+00:00")

    def test_incident_facts_are_public_and_use_safe_entry_point(self):
        db_path, store = self.make_store()
        try:
            self.seed_incident(store)
            now = datetime(2026, 7, 14, 10, 30, tzinfo=timezone.utc)

            with patch.object(run, "incident_store", store):
                facts = run.build_blacknet_incident_facts(now)

            self.assertEqual(len(facts), 1)
            fact = facts[0]
            self.assertEqual(fact["fact_type"], "incident_hotspot_reaction")
            self.assertEqual(fact["source_system"], "incidents")
            metadata = fact["metadata"]
            self.assertEqual(metadata["incident_id"], "incident_bridge")
            self.assertEqual(metadata["public_state"], "active")
            self.assertEqual(metadata["trend"], "stabilny")
            self.assertEqual(metadata["incident_level"], 3)
            self.assertEqual(metadata["incident_lat"], 52.23)
            self.assertEqual(metadata["incident_lng"], 21.01)
            self.assertNotEqual((metadata["lat"], metadata["lng"]), (52.23, 21.01))
            self.assertGreater(
                distance_m({"lat": 52.23, "lng": 21.01}, {"lat": metadata["lat"], "lng": metadata["lng"]}),
                metadata["search_radius_m"],
            )
            serialized = json.dumps(fact, sort_keys=True)
            self.assertNotIn("op-secret", serialized)
            self.assertNotIn("suspect_refs", serialized)
            self.assertNotIn("territory_refs", serialized)
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_incident_fact_converts_to_stable_blacknet_teleport_signal(self):
        db_path, store = self.make_store()
        try:
            self.seed_incident(store)
            now = datetime(2026, 7, 14, 10, 30, tzinfo=timezone.utc)
            with patch.object(run, "incident_store", store):
                facts = run.build_blacknet_incident_facts(now)
            snapshot = {"version": "incident-facts", "facts": facts}

            signals = run.build_blacknet_world_signals(snapshot, now=now, limit=4)["signals"]

            self.assertEqual(len(signals), 1)
            signal = signals[0]
            self.assertEqual(signal["signal_type"], "incident_hotspot")
            self.assertEqual(signal["cta_action"], "teleport_to_hotspot")
            self.assertEqual(signal["cta_target"], "incident")
            self.assertEqual(signal["cta_target_id"], "incident_bridge")
            self.assertEqual(signal["entity_id"], "incident_bridge")
            self.assertEqual(signal["metadata"]["hotspot_id"], "incident_bridge")
            self.assertEqual(signal["metadata"]["incident_lat"], 52.23)
            self.assertEqual(signal["metadata"]["incident_lng"], 21.01)
            self.assertIn(signal["cta_action"], run.BLACKNET_ALLOWED_CTA_ACTIONS)
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_resolved_incident_is_not_published(self):
        db_path, store = self.make_store()
        try:
            self.seed_incident(store)
            store.cancel("incident_bridge", now="2026-07-14T10:10:00+00:00")
            now = datetime(2026, 7, 14, 10, 30, tzinfo=timezone.utc)

            with patch.object(run, "incident_store", store):
                facts = run.build_blacknet_incident_facts(now)

            self.assertEqual(facts, [])
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == "__main__":
    unittest.main()
