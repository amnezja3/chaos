import tempfile
import unittest
from pathlib import Path

from database import TerritoryConflictStore, TerritoryStore
from response_network.territory_context_reader import TerritoryContextReader


def square(lat, lng, size=0.01):
    return [
        {"lat": lat, "lng": lng},
        {"lat": lat, "lng": lng + size},
        {"lat": lat + size, "lng": lng + size},
        {"lat": lat + size, "lng": lng},
    ]


class TerritoryContextReaderTest(unittest.TestCase):
    def _temp_db(self):
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        handle.close()
        return Path(handle.name)

    def _cleanup(self, path):
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(f"{path}{suffix}")
            if candidate.exists():
                try:
                    candidate.unlink()
                except PermissionError:
                    pass

    def test_point_context_returns_owner_status_and_no_profile_fields(self):
        path = self._temp_db()
        try:
            territory_store = TerritoryStore(db_path=str(path))
            conflict_store = TerritoryConflictStore(db_path=str(path))
            territory_store.replace_player_areas("alice", [{
                "vertices": square(52.0, 21.0),
                "centroid_lat": 52.005,
                "centroid_lng": 21.005,
                "area_size": 100,
                "max_edge_distance": 1000,
                "status": "active",
            }])
            reader = TerritoryContextReader(territory_store, conflict_store)

            context = reader.for_point(52.004, 21.004, actor_username="alice")

            self.assertTrue(context["inside_any_territory"])
            self.assertTrue(context["inside_own_territory"])
            self.assertFalse(context["inside_foreign_territory"])
            territory = context["territories"][0]
            self.assertEqual(territory["owner_id"], "alice")
            self.assertEqual(territory["status"], "active")
            self.assertIsNone(territory["clan_id"])
            self.assertEqual(territory["clan_source"], "not_available_without_profile")
            self.assertNotIn("owner_nick", territory)
            self.assertNotIn("avatar", territory)
        finally:
            self._cleanup(path)

    def test_point_context_marks_foreign_territory(self):
        path = self._temp_db()
        try:
            territory_store = TerritoryStore(db_path=str(path))
            conflict_store = TerritoryConflictStore(db_path=str(path))
            territory_store.replace_player_areas("bob", [{
                "vertices": square(52.1, 21.1),
                "centroid_lat": 52.105,
                "centroid_lng": 21.105,
                "area_size": 100,
                "max_edge_distance": 1000,
                "status": "active",
            }])
            reader = TerritoryContextReader(territory_store, conflict_store)

            context = reader.for_point(52.104, 21.104, actor_username="alice")

            self.assertTrue(context["inside_foreign_territory"])
            self.assertEqual(context["owner_ids"], ["bob"])
        finally:
            self._cleanup(path)

    def test_active_conflict_is_attached_by_area_id(self):
        path = self._temp_db()
        try:
            territory_store = TerritoryStore(db_path=str(path))
            conflict_store = TerritoryConflictStore(db_path=str(path))
            territory_store.replace_player_areas("alice", [{
                "vertices": square(52.0, 21.0),
                "centroid_lat": 52.005,
                "centroid_lng": 21.005,
                "area_size": 100,
                "max_edge_distance": 1000,
                "status": "active",
            }])
            territory_store.replace_player_areas("bob", [{
                "vertices": square(52.02, 21.02),
                "centroid_lat": 52.025,
                "centroid_lng": 21.025,
                "area_size": 100,
                "max_edge_distance": 1000,
                "status": "active",
            }])
            areas = territory_store.list_player_areas()
            area_ids = [area["id"] for area in areas]
            conflict_store.upsert_conflict({
                "conflict_key": "alice:bob:test",
                "participants": ["alice", "bob"],
                "area_ids": area_ids,
                "intersections": [],
                "targets": [],
                "status": "active",
            })
            reader = TerritoryContextReader(territory_store, conflict_store)

            context = reader.for_point(52.004, 21.004, actor_username="alice")

            territory = context["territories"][0]
            self.assertEqual(len(territory["conflict_ids"]), 1)
            self.assertEqual(territory["conflicts"][0]["conflict_key"], "alice:bob:test")
        finally:
            self._cleanup(path)

    def test_bbox_context_is_limited_and_does_not_return_geometry_vertices(self):
        path = self._temp_db()
        try:
            territory_store = TerritoryStore(db_path=str(path))
            conflict_store = TerritoryConflictStore(db_path=str(path))
            territory_store.replace_player_areas("alice", [{
                "vertices": square(52.0, 21.0),
                "centroid_lat": 52.005,
                "centroid_lng": 21.005,
                "area_size": 100,
                "max_edge_distance": 1000,
                "status": "active",
            }])
            territory_store.replace_player_areas("bob", [{
                "vertices": square(53.0, 22.0),
                "centroid_lat": 53.005,
                "centroid_lng": 22.005,
                "area_size": 100,
                "max_edge_distance": 1000,
                "status": "active",
            }])
            reader = TerritoryContextReader(territory_store, conflict_store)

            context = reader.for_bbox(51.99, 20.99, 52.02, 21.02, limit=10)

            self.assertEqual(context["owner_ids"], ["alice"])
            self.assertEqual(len(context["territories"]), 1)
            self.assertIn("bbox", context["territories"][0])
            self.assertNotIn("vertices", context["territories"][0])
        finally:
            self._cleanup(path)

    def test_compare_point_with_legacy_area_confirms_matching_area(self):
        path = self._temp_db()
        try:
            territory_store = TerritoryStore(db_path=str(path))
            conflict_store = TerritoryConflictStore(db_path=str(path))
            territory_store.replace_player_areas("alice", [{
                "vertices": square(52.0, 21.0),
                "centroid_lat": 52.005,
                "centroid_lng": 21.005,
                "area_size": 100,
                "max_edge_distance": 1000,
                "status": "active",
            }])
            legacy_area = territory_store.list_player_areas("alice")[0]
            reader = TerritoryContextReader(territory_store, conflict_store)

            comparison = reader.compare_point_with_legacy_area(52.004, 21.004, legacy_area, actor_username="alice")

            self.assertTrue(comparison["match"])
            self.assertIn(comparison["legacy_territory_id"], comparison["context_territory_ids"])
        finally:
            self._cleanup(path)


if __name__ == "__main__":
    unittest.main()
