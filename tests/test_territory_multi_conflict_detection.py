import unittest

import run


def square(min_lat, min_lng, size=0.01):
    return [
        {"lat": min_lat, "lng": min_lng},
        {"lat": min_lat, "lng": min_lng + size},
        {"lat": min_lat + size, "lng": min_lng + size},
        {"lat": min_lat + size, "lng": min_lng},
    ]


def snapshot(conflict_id, participants, geometries, complete=True,
             geometry_status="clean"):
    return {
        "conflict_id": conflict_id,
        "status": "active",
        "complete": complete,
        "geometry_status": geometry_status,
        "snapshot_version": 4,
        "conflict_version": 3,
        "geometry_version": 4,
        "participants": participants,
        "conflict": {
            "conflict_id": conflict_id,
            "status": "active",
            "participants": participants,
            "participant_key": "::".join(sorted(participants)),
        },
        "fronts": [
            {
                "front_id": f"{conflict_id}:front:{index}",
                "status": "active",
                "participant_key": "::".join(sorted(participants)),
                "geometry": geometry,
            }
            for index, geometry in enumerate(geometries)
        ],
    }


class TerritoryMultiConflictDetectionTests(unittest.TestCase):
    @staticmethod
    def profiles(username):
        return {"clan": {"a": "red", "b": "blue", "d": "green"}.get(username, "")}

    def detect(self, snapshots):
        return run.detect_multi_conflict_candidates(
            snapshots, profile_lookup=self.profiles, minimum_overlap_area_sqm=1.0
        )

    def test_connected_area_graph_is_bilateralized_before_materialization(self):
        areas = [
            {
                "id": username, "owner_username": username, "status": "active",
                "vertices": square(52.0 + offset, 21.0 + offset, 0.02),
            }
            for username, offset in (("a", 0.0), ("b", 0.005), ("d", 0.01))
        ]
        plans = run.build_territory_conflict_detection_plan(areas)
        self.assertEqual(
            {plan["participant_key"] for plan in plans},
            {"a::b", "a::d", "b::d"},
        )
        self.assertTrue(all(len(plan["participants"]) == 2 for plan in plans))

    def test_independent_fronts_without_contact_do_not_create_candidate(self):
        report = self.detect([
            snapshot("a-d", ["a", "d"], [square(52.0, 21.0)]),
            snapshot("b-d", ["b", "d"], [square(52.1, 21.1)]),
        ])
        self.assertEqual(report["candidates"], [])
        self.assertEqual(report["mutations"], 0)

    def test_point_or_edge_contact_has_no_positive_area(self):
        for other in (square(52.01, 21.01), square(52.0, 21.01)):
            with self.subTest(other=other):
                report = self.detect([
                    snapshot("a-d", ["a", "d"], [square(52.0, 21.0)]),
                    snapshot("b-d", ["b", "d"], [other]),
                ])
                self.assertEqual(report["candidates"], [])

    def test_positive_area_overlap_creates_shadow_candidate(self):
        report = self.detect([
            snapshot("a-d", ["a", "d"], [square(52.0, 21.0)]),
            snapshot("b-d", ["b", "d"], [square(52.005, 21.005)]),
        ])
        candidate = report["candidates"][0]
        self.assertEqual(candidate["member_conflict_ids"], ["a-d", "b-d"])
        self.assertEqual(candidate["participant_usernames"], ["a", "b", "d"])
        self.assertGreater(candidate["overlap_area"], 1.0)
        self.assertEqual(candidate["candidate_status"], "shadow_detected")
        self.assertEqual(report["metrics"]["geometry_comparisons"], 1)

    def test_disconnected_overlaps_of_same_conflicts_are_separate_candidates(self):
        report = self.detect([
            snapshot("a-d", ["a", "d"], [
                square(52.0, 21.0), square(52.1, 21.1),
            ]),
            snapshot("b-d", ["b", "d"], [
                square(52.005, 21.005), square(52.105, 21.105),
            ]),
        ])
        self.assertEqual(len(report["candidates"]), 2)

    def test_connected_three_conflict_overlaps_form_one_candidate(self):
        report = self.detect([
            snapshot("a-d", ["a", "d"], [square(52.0, 21.0, 0.02)]),
            snapshot("b-d", ["b", "d"], [square(52.005, 21.005, 0.02)]),
            snapshot("c-d", ["c", "d"], [square(52.01, 21.01, 0.02)]),
        ])
        self.assertEqual(len(report["candidates"]), 1)
        self.assertEqual(
            report["candidates"][0]["member_conflict_ids"],
            ["a-d", "b-d", "c-d"],
        )

    def test_incomplete_snapshot_cannot_create_membership(self):
        report = self.detect([
            snapshot("a-d", ["a", "d"], [square(52.0, 21.0)]),
            snapshot("b-d", ["b", "d"], [square(52.005, 21.005)], complete=False),
        ])
        self.assertEqual(report["candidates"], [])
        self.assertEqual(report["skipped_snapshots"][0]["conflict_id"], "b-d")

    def test_legacy_multi_participant_record_exposes_pair_aliases(self):
        report = self.detect([
            snapshot("legacy", ["a", "b", "d"], [square(52.0, 21.0)]),
        ])
        legacy = report["legacy_multi_participant_conflicts"][0]
        self.assertEqual(legacy["pair_aliases"], ["a::b", "a::d", "b::d"])


if __name__ == "__main__":
    unittest.main()
