import hashlib
import unittest
from unittest.mock import patch

from ghostnetwork.deltas import GhostNetworkDeltaPublisher, rebuild_ghostnetwork_delta_projection


class FakeDeltaBus:
    def __init__(self):
        self.records = []

    def record_change(self, username, scope, change_type, **kwargs):
        event = {
            "username": username,
            "scope": scope,
            "type": change_type,
            **kwargs,
        }
        self.records.append(event)
        return event


class FakeRepository:
    def __init__(self):
        self.snapshot_reads = 0
        self.events = [
            {
                "event_id": "event-old",
                "event_type": "ghost.part_discovered",
                "cycle_id": "ghostnetwork_0001",
                "state_version": 6,
                "part_id": "part-1",
            },
            {
                "event_id": "event-new",
                "event_type": "ghost.connection_changed",
                "cycle_id": "ghostnetwork_0001",
                "state_version": 8,
                "connection_id": "conn-1",
            },
        ]

    def build_internal_snapshot(self, cycle_id):
        self.snapshot_reads += 1
        return {
            "cycle": {"cycle_id": cycle_id, "state_version": 8},
            "parts": [],
            "connections": [],
            "progress": {},
            "state_version": 8,
        }

    def list_events(self, cycle_id, limit=1000):
        return list(self.events[:limit])

    def get_state_version(self, cycle_id):
        return 8


class GhostNetworkDeltaPublisherTest(unittest.TestCase):
    def test_publishes_safe_part_delta_through_existing_delta_bus(self):
        delta_bus = FakeDeltaBus()
        repository = FakeRepository()
        projection = {
            "projection": "viewer_visibility",
            "visibility_version": "ghost-visibility-v1",
            "state_version": 8,
            "cycle": {"cycle_id": "ghostnetwork_0001", "state_version": 8},
            "parts": [
                {
                    "part_id": "part-1",
                    "public_entity_id": "ghost-public-1",
                    "module_state": "active",
                    "visibility_level": "full_owner",
                    "location_visibility": "exact",
                    "latitude": 52.2,
                    "longitude": 21.0,
                    "can_show_on_map": True,
                    "state_version": 8,
                }
            ],
            "connections": [],
            "progress": {},
        }
        event = {
            "event_id": "event-1",
            "event_type": "ghost.part_discovered",
            "cycle_id": "ghostnetwork_0001",
            "part_id": "part-1",
            "state_version": 8,
            "created_at": "2026-07-19T10:00:00Z",
        }
        viewer = {"username": "alice", "viewer_clan": "VIREX"}

        with patch("ghostnetwork.deltas.build_viewer_projection", return_value=projection):
            published = GhostNetworkDeltaPublisher(
                repository=repository,
                delta_bus=delta_bus,
            ).publish_event(event, [viewer])

        self.assertEqual(len(published), 1)
        record = published[0]
        self.assertEqual(record["username"], "alice")
        self.assertEqual(record["scope"], "ghostnetwork")
        self.assertEqual(record["type"], "ghost.part_discovered")
        self.assertEqual(record["entity_id"], "ghost-public-1")
        self.assertTrue(record["dedupe_key"].startswith("ghostnetwork:alice:ghostnetwork:"))
        payload = record["payload"]
        self.assertEqual(payload["event_id"], "event-1")
        self.assertEqual(payload["cycle_id"], "ghostnetwork_0001")
        self.assertEqual(payload["state_version"], 8)
        self.assertTrue(payload["snapshot_checksum"])
        self.assertEqual(payload["part_projection"]["public_entity_id"], "ghost-public-1")

        with patch("ghostnetwork.deltas.build_viewer_projection", return_value=projection):
            replay = GhostNetworkDeltaPublisher(
                repository=repository,
                delta_bus=delta_bus,
            ).publish_event(event, [viewer])
        self.assertEqual(replay[0]["dedupe_key"], record["dedupe_key"])

    def test_rebuild_projection_filters_events_after_version(self):
        projection = rebuild_ghostnetwork_delta_projection(
            "ghostnetwork_0001",
            from_version=6,
            repository=FakeRepository(),
        )

        self.assertEqual(projection["cycle_id"], "ghostnetwork_0001")
        self.assertEqual(projection["from_version"], 6)
        self.assertEqual(projection["current_version"], 8)
        self.assertEqual(projection["event_count"], 1)
        self.assertEqual(projection["events"][0]["event_id"], "event-new")

    def test_hidden_part_event_is_not_published_without_safe_projection(self):
        delta_bus = FakeDeltaBus()
        repository = FakeRepository()
        hidden_projection = {
            "projection": "viewer_visibility",
            "visibility_version": "ghost-visibility-v1",
            "state_version": 9,
            "cycle": {"cycle_id": "ghostnetwork_0001", "state_version": 9},
            "parts": [],
            "connections": [],
            "progress": {},
        }
        event = {
            "event_id": "event-hidden",
            "event_type": "ghost.part_contested",
            "cycle_id": "ghostnetwork_0001",
            "part_id": "internal-secret-part-id",
            "state_version": 9,
        }

        with patch("ghostnetwork.deltas.build_viewer_projection", return_value=hidden_projection):
            published = GhostNetworkDeltaPublisher(
                repository=repository,
                delta_bus=delta_bus,
            ).publish_event(event, [{"username": "outsider", "viewer_clan": "OTHER"}])

        self.assertEqual(published, [])
        self.assertEqual(delta_bus.records, [])

    def test_hidden_safe_projection_is_matched_by_public_entity_id(self):
        delta_bus = FakeDeltaBus()
        repository = FakeRepository()
        raw = "ghostnetwork_0001:internal-secret-part-id"
        public_id = f"ghost-node:{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"
        projection = {
            "projection": "viewer_visibility",
            "visibility_version": "ghost-visibility-v1",
            "state_version": 9,
            "cycle": {"cycle_id": "ghostnetwork_0001", "state_version": 9},
            "parts": [{
                "part_id": None,
                "public_entity_id": public_id,
                "visibility_level": "contained_hidden",
                "location_visibility": "territory_only",
                "territory_id": "territory-1",
                "can_show_on_map": True,
            }],
            "connections": [],
            "progress": {},
        }
        event = {
            "event_id": "event-hidden-safe",
            "event_type": "ghost.part_contested",
            "cycle_id": "ghostnetwork_0001",
            "part_id": "internal-secret-part-id",
            "state_version": 9,
        }

        with patch("ghostnetwork.deltas.build_viewer_projection", return_value=projection):
            published = GhostNetworkDeltaPublisher(
                repository=repository,
                delta_bus=delta_bus,
            ).publish_event(event, [{"username": "outsider", "viewer_clan": "OTHER"}])

        self.assertEqual(len(published), 1)
        self.assertEqual(published[0]["entity_id"], public_id)
        self.assertIsNone(published[0]["payload"]["part_projection"]["part_id"])

    def test_multi_recipient_publication_reads_internal_snapshot_once(self):
        repository = FakeRepository()
        event = {
            "event_id": "event-signal",
            "event_type": "ghost.signal_sent",
            "cycle_id": "ghostnetwork_0001",
            "state_version": 8,
        }
        recipients = [{"username": f"user-{index}"} for index in range(25)]

        GhostNetworkDeltaPublisher(
            repository=repository,
            delta_bus=FakeDeltaBus(),
        ).publish_event(event, recipients)

        self.assertEqual(repository.snapshot_reads, 1)


if __name__ == "__main__":
    unittest.main()
