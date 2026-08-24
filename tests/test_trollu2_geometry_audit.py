import argparse
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tools.audit_trollu2_geometry import build_report


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _create_database(path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE captured_targets (
            id INTEGER PRIMARY KEY,
            owner_username TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            label TEXT,
            name TEXT,
            icon TEXT,
            source_type TEXT,
            generated INTEGER,
            stationary INTEGER,
            target_json TEXT,
            captured_at TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE territory_target_ownership (
            target_id TEXT PRIMARY KEY,
            owner_username TEXT NOT NULL,
            ownership_version INTEGER,
            lat REAL,
            lng REAL,
            label TEXT,
            target_json TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE player_areas (
            id INTEGER PRIMARY KEY,
            owner_username TEXT NOT NULL,
            vertices_json TEXT NOT NULL,
            area_size REAL,
            status TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        """
    )
    targets = [
        ("pillar:a", 52.0000, 21.0000),
        ("pillar:b", 52.0000, 21.0150),
        ("pillar:c", 52.0100, 21.0075),
    ]
    for index, (target_id, lat, lng) in enumerate(targets, 1):
        payload = {
            "target_id": target_id,
            "target_type": "pillar",
            "lat": lat,
            "lng": lng,
            "stationary": True,
            "ownership_source": "scan",
            "captured_at": "2026-08-20T12:00:00",
        }
        conn.execute(
            """
            INSERT INTO captured_targets VALUES
                (?, 'trolu2', ?, ?, ?, ?, '', 'pillar', 0, 1, ?, ?, ?, ?)
            """,
            (
                index, lat, lng, target_id, target_id, json.dumps(payload),
                "2026-08-20T12:00:00", "2026-08-20T12:00:00",
                "2026-08-20T12:00:00",
            ),
        )
        conn.execute(
            """
            INSERT INTO territory_target_ownership VALUES
                (?, 'trolu2', 1, ?, ?, ?, ?, ?, ?)
            """,
            (
                target_id, lat, lng, target_id, json.dumps(payload),
                "2026-08-20T12:00:00", "2026-08-20T12:00:00",
            ),
        )
    foreign = [
        {"lat": 51.9990, "lng": 21.0060},
        {"lat": 52.0030, "lng": 21.0120},
        {"lat": 52.0060, "lng": 21.0060},
    ]
    conn.execute(
        """
        INSERT INTO player_areas VALUES
            (9001, 'foreign', ?, 1000, 'active', ?, ?)
        """,
        (
            json.dumps(foreign), "2026-08-22T10:00:00",
            "2026-08-22T10:00:00",
        ),
    )
    conn.commit()
    conn.close()


class Trollu2GeometryAuditTests(unittest.TestCase):
    def test_geometry_audit_is_read_only_and_separates_level_and_world_causes(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "game.sqlite3"
            _create_database(database)
            before = _sha256(database)
            report = build_report(
                argparse.Namespace(
                    db=str(database), plan="", historical_db="",
                    incident_at="2026-08-21T15:08:32", output="",
                )
            )

            self.assertEqual(_sha256(database), before)
            self.assertIs(report["read_only"], True)
            self.assertIs(report["query_only"], True)
            self.assertEqual(report["database_writes"], 0)
            self.assertEqual(report["ghostnetwork_queries"], 0)
            self.assertEqual(report["subject_objects"]["counts"], {
                "captured_targets": 3,
                "stationary_targets": 3,
                "generated_targets": 0,
                "canonical_pillars": 3,
                "canonical_inners": 0,
                "ownership_entries": 3,
            })
            levels = {item["level"]: item for item in report["geometry_by_level"]}
            self.assertEqual(levels[2]["active_area_count"], 0)
            self.assertEqual(levels[25]["active_area_count"], 1)
            self.assertEqual(levels[26]["active_area_count"], 1)
            self.assertEqual(levels[50]["active_area_count"], 1)
            conflict = next(
                item for item in report["existing_geometry_collisions"]
                if item["level"] == 50
            )
            self.assertEqual(conflict["foreign_area_id"], 9001)
            self.assertEqual(
                conflict["historical_state"], "CREATED_AFTER_INCIDENT_CUTOFF"
            )
            self.assertEqual(conflict["classification"], "A+B — BOTH")
            self.assertEqual(report["verdict"], (
                "DIAGNOSIS CONFIRMED — BOTH LEVEL SCALING AND WORLD EVOLUTION "
                "CONTRIBUTE"
            ))

    def test_tokio_bonus_is_reported_separately_from_existing_geometry(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "game.sqlite3"
            plan_path = Path(directory) / "plan.json"
            _create_database(database)
            bonus_targets = [
                {"target_id": "bonus:1", "lat": 35.7000, "lng": 139.7000},
                {"target_id": "bonus:2", "lat": 35.7000, "lng": 139.7100},
                {"target_id": "bonus:3", "lat": 35.7100, "lng": 139.7050},
            ]
            plan_path.write_text(
                json.dumps({
                    "plan_id": "test-plan",
                    "territory_recovery": {
                        "cities": [{
                            "city": "Tokio",
                            "relocation": {
                                "applied": True, "distance_m": 3000,
                                "bearing_deg": 0,
                            },
                            "targets": bonus_targets,
                        }]
                    },
                }),
                encoding="utf-8",
            )
            report = build_report(
                argparse.Namespace(
                    db=str(database), plan=str(plan_path), historical_db="",
                    incident_at="2026-08-21T15:08:32", output="",
                )
            )

            bonus = report["tokio_bonus_diagnosis"]
            self.assertEqual(bonus["plan_id"], "test-plan")
            self.assertEqual(bonus["cities"], [{
                "city": "Tokio",
                "relocation": {
                    "applied": True, "distance_m": 3000, "bearing_deg": 0,
                },
                "pillar_count": 3,
            }])
            self.assertEqual(
                bonus["bonus_only_level_50"]["active_area_count"], 1
            )
            self.assertTrue(report["existing_geometry_collisions"])


if __name__ == "__main__":
    unittest.main()
