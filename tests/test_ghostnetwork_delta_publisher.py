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


if __name__ == "__main__":
    unittest.main()
