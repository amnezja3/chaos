import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch

import run
from database import (
    UserIdentityProjectionStore,
    UserStore,
    get_hot_path_metrics,
    reset_hot_path_metrics,
    restore_hot_path_metrics,
)
from ghostnetwork.deltas import normalize_snapshot_view
from tests.session_generation_fixture import SessionGenerationFixture


def projected_part(
    public_id,
    relation,
    module_state,
    *,
    territory_id=None,
    owner_id=None,
    territory_clan=None,
    location_visibility="exact",
    latitude=52.2,
    longitude=21.0,
    contested=False,
):
    exact = location_visibility == "exact"
    return {
        "public_entity_id": public_id,
        "part_id": public_id.replace("ghost-node:", "part-")
        if relation != "foreign_blocked" else None,
        "viewer_relation": relation,
        "visibility_level": "contained_hidden"
        if relation == "foreign_blocked" else "full_public",
        "identity_visible": relation != "foreign_blocked",
        "module_state": module_state,
        "conflict_state": "contested" if contested else "none",
        "contested": contested,
        "territory_id": territory_id,
        "territory_owner_id": owner_id,
        "territory_clan": territory_clan,
        "clan_code": None if relation == "foreign_blocked" else "virex",
        "location_visibility": location_visibility,
        "can_show_on_map": bool(exact or territory_id),
        "can_teleport": exact,
        "latitude": latitude if exact else None,
        "longitude": longitude if exact else None,
        "part_code": "SAFE" if relation != "foreign_blocked" else None,
        "name": "Safe part" if relation != "foreign_blocked" else None,
        "machine_code": "safe-machine" if relation != "foreign_blocked" else None,
        "profession_code": "safe-profession" if relation != "foreign_blocked" else None,
        "ability_code": "safe-ability" if relation != "foreign_blocked" else None,
        "state_version": 11,
    }


def projection(parts, *, cache_key="viewer-cache", cycle_status="active"):
    return {
        "projection": "viewer_visibility",
        "visibility_version": "ghost-visibility-v2",
        "cache_key": cache_key,
        "state_version": 11,
        "viewer": {"viewer_id": "alice", "viewer_clan": "virex"},
        "cycle": {
            "cycle_id": "cycle-132",
            "status": cycle_status,
            "state_version": 11,
        },
        "parts": parts,
        "connections": [{
            "public_connection_id": "ghost-link:public",
            "state": "active",
            "state_version": 11,
            "can_show_on_map": True,
            "endpoint_a": {"latitude": 52.2, "longitude": 21.0},
            "endpoint_b": {"latitude": 52.3, "longitude": 21.1},
        }],
        "suite": {"legacy_full_copies": list(parts)},
    }


def valid_profile(username="alice", padding=""):
    return {
        "username": username,
        "nick": "Alice",
        "email": "alice@example.test",
        "level": 1,
        "hackcoins": 1000,
        "respect": 0,
        "exp": "0 / 1000",
        "clan": "virex",
        "ghost_clan_code": "virex",
        "fraction": {},
        "inventory": [],
        "files": {"tools": [], "download": []},
        "apps": [],
        "hacked": [],
        "desktop_settings": {},
        "security": {},
        "territory_stats": {},
        "operations": [],
        "targets": [],
        "system_messages": [],
        "launch_queue": [],
        "hot_path_padding": padding,
    }


class GhostNetworkSuiteProjectionTest(unittest.TestCase):
    def test_empty_suite_snapshot_has_stable_empty_contract(self):
        result = normalize_snapshot_view(projection([]), view="suite")
        self.assertEqual(result["parts"], [])
        self.assertEqual(result["summary"]["parts_total"], 0)
        self.assertEqual(result["summary"]["parts_visible_to_viewer"], 0)
        self.assertEqual(result["groups"], {
            "public": [], "blocked": [], "clan_active": [],
            "self_foreign": [], "self_own": [],
        })
        self.assertTrue(result["suite_health"]["ok"])

    def test_twenty_parts_remain_single_records_and_duplicate_is_reported(self):
        parts = [
            projected_part(f"ghost-node:{index:02d}", "public_neutral", "neutral")
            for index in range(20)
        ]
        parts.append(dict(parts[0]))
        result = normalize_snapshot_view(projection(parts), view="suite")
        self.assertEqual(len(result["parts"]), 20)
        self.assertEqual(result["summary"]["parts_total"], 20)
        self.assertFalse(result["suite_health"]["ok"])
        self.assertEqual(
            result["suite_health"]["errors"],
            ["duplicate_public_entity_id:ghost-node:00"],
        )

    def test_suite_caps_corrupt_projection_at_twenty_parts(self):
        parts = [
            projected_part(f"ghost-node:{index:02d}", "public_neutral", "neutral")
            for index in range(21)
        ]
        result = normalize_snapshot_view(projection(parts), view="suite")
        self.assertEqual(len(result["parts"]), 20)
        self.assertEqual(result["summary"]["parts_total"], 20)
        self.assertFalse(result["suite_health"]["ok"])
        self.assertIn("parts_limit_exceeded:21", result["suite_health"]["errors"])

    def test_suite_is_one_part_list_with_reference_only_groups(self):
        parts = [
            projected_part("ghost-node:self-own", "self_own_active", "active", territory_id="area-own", owner_id="alice"),
            projected_part("ghost-node:public", "public_neutral", "neutral"),
            projected_part(
                "ghost-node:hidden", "foreign_blocked", "blocked",
                territory_id="area-hidden", owner_id="owner-1",
                territory_clan="sentinel_order", location_visibility="territory_only",
            ),
            projected_part("ghost-node:clan", "clan_own_active", "active", territory_id="area-clan", owner_id="owner-2"),
            projected_part("ghost-node:self-foreign", "self_foreign_blocked", "blocked", territory_id="area-self", owner_id="alice", contested=True),
            projected_part("ghost-node:foreign-active", "foreign_active", "active", territory_id="area-foreign", owner_id="owner-3"),
        ]
        result = normalize_snapshot_view(
            projection(parts),
            view="suite",
            owner_aliases={
                "alice": {"display_alias": "Alice", "source_profile_revision": 5, "source_profile_checksum": "a"},
                "owner-1": {"display_alias": "Owner One", "source_profile_revision": 7, "source_profile_checksum": "b"},
            },
        )

        self.assertNotIn("suite", result)
        self.assertEqual(len(result["parts"]), len(parts))
        self.assertEqual(
            [item["public_entity_id"] for item in result["parts"]],
            sorted(item["public_entity_id"] for item in parts),
        )
        grouped_ids = [item for values in result["groups"].values() for item in values]
        self.assertEqual(len(grouped_ids), len(set(grouped_ids)))
        self.assertTrue(all(isinstance(item, str) for item in grouped_ids))
        self.assertEqual(result["groups"]["public"], ["ghost-node:public"])
        self.assertEqual(result["groups"]["blocked"], ["ghost-node:hidden"])
        self.assertEqual(result["groups"]["clan_active"], ["ghost-node:clan"])
        self.assertEqual(result["groups"]["self_foreign"], ["ghost-node:self-foreign"])
        self.assertEqual(result["groups"]["self_own"], ["ghost-node:self-own"])
        self.assertNotIn("ghost-node:foreign-active", grouped_ids)

        self.assertEqual(result["summary"], {
            "parts_total": 6,
            "parts_discovered": 6,
            "parts_public": 1,
            "parts_blocked": 2,
            "parts_active": 3,
            "parts_contested": 1,
            "parts_visible_to_viewer": 6,
        })
        self.assertTrue(result["suite_health"]["ok"])

    def test_hidden_part_uses_only_territory_opaque_actions(self):
        hidden = projected_part(
            "ghost-node:hidden", "foreign_blocked", "blocked",
            territory_id="area-hidden", owner_id="owner-1",
            territory_clan="sentinel_order", location_visibility="territory_only",
        )
        result = normalize_snapshot_view(
            projection([hidden]),
            view="suite",
            owner_aliases={"owner-1": {"display_alias": "Owner One"}},
        )["parts"][0]

        self.assertIsNone(result["part_id"])
        self.assertIsNone(result["part_code"])
        self.assertIsNone(result["name"])
        self.assertIsNone(result["latitude"])
        self.assertIsNone(result["longitude"])
        self.assertEqual(result["owner"]["owner_alias"], "Owner One")
        self.assertEqual(result["location"], {
            "visibility": "territory_only",
            "latitude": None,
            "longitude": None,
            "map_focus_type": "ghostnetwork_territory",
            "map_focus_id": "area-hidden",
        })
        self.assertEqual(result["actions"], {
            "can_show_on_map": True,
            "can_teleport": True,
            "map_target_type": "ghostnetwork_territory",
            "map_target_id": "area-hidden",
            "teleport_target_type": "ghostnetwork_territory",
            "teleport_target_id": "area-hidden",
        })
        encoded = json.dumps(result, sort_keys=True)
        self.assertNotIn("safe-machine", encoded)
        self.assertNotIn("safe-profession", encoded)
        self.assertNotIn("safe-ability", encoded)

    def test_malformed_hidden_identity_is_cleared_fail_closed(self):
        hidden = projected_part(
            "ghost-node:hidden", "foreign_blocked", "blocked",
            territory_id="area-hidden", owner_id="owner-1",
            location_visibility="territory_only",
        )
        hidden.update({
            "part_id": "secret-part-id",
            "part_code": "SECRET-CODE",
            "name": "Secret name",
            "machine_code": "secret-machine",
            "ability_code": "secret-ability",
            "target_id": "secret-target",
            "vertices": [{"lat": 52.1, "lng": 21.1}],
            "geometry": {"type": "Polygon", "coordinates": [[21.1, 52.1]]},
            "reservation": {"target_id": "secret-reservation"},
        })
        result = normalize_snapshot_view(projection([hidden]), view="suite")
        item = result["parts"][0]
        encoded = json.dumps(item, sort_keys=True)
        self.assertNotIn("secret-part-id", encoded)
        self.assertNotIn("SECRET-CODE", encoded)
        self.assertNotIn("Secret name", encoded)
        self.assertNotIn("secret-machine", encoded)
        self.assertNotIn("secret-ability", encoded)
        self.assertNotIn("secret-target", encoded)
        self.assertNotIn("secret-reservation", encoded)
        self.assertNotIn("coordinates", encoded)
        self.assertTrue(result["suite_health"]["ok"])

    def test_exact_part_actions_use_public_entity_id(self):
        item = normalize_snapshot_view(
            projection([projected_part("ghost-node:public", "public_neutral", "neutral")]),
            view="suite",
        )["parts"][0]
        self.assertEqual(item["actions"]["map_target_type"], "ghostnetwork_part")
        self.assertEqual(item["actions"]["map_target_id"], "ghost-node:public")
        self.assertEqual(item["actions"]["teleport_target_id"], "ghost-node:public")

    def test_non_active_cycle_disables_actions(self):
        item = normalize_snapshot_view(
            projection(
                [projected_part("ghost-node:public", "public_neutral", "neutral")],
                cycle_status="transmitting",
            ),
            view="suite",
        )["parts"][0]
        self.assertFalse(item["actions"]["can_show_on_map"])
        self.assertFalse(item["actions"]["can_teleport"])
        self.assertIsNone(item["actions"]["map_target_id"])

    def test_suite_cache_key_includes_viewer_base_and_owner_revision(self):
        part = projected_part(
            "ghost-node:hidden", "foreign_blocked", "blocked",
            territory_id="area-hidden", owner_id="owner-1",
            location_visibility="territory_only",
        )
        one = normalize_snapshot_view(
            projection([part], cache_key="viewer-a"),
            view="suite",
            owner_aliases={"owner-1": {"display_alias": "One", "source_profile_revision": 1, "source_profile_checksum": "a"}},
        )
        two = normalize_snapshot_view(
            projection([part], cache_key="viewer-b"),
            view="suite",
            owner_aliases={"owner-1": {"display_alias": "One", "source_profile_revision": 1, "source_profile_checksum": "a"}},
        )
        renamed = normalize_snapshot_view(
            projection([part], cache_key="viewer-a"),
            view="suite",
            owner_aliases={"owner-1": {"display_alias": "Renamed", "source_profile_revision": 2, "source_profile_checksum": "b"}},
        )
        self.assertNotEqual(one["cache_key"], two["cache_key"])
        self.assertNotEqual(one["cache_key"], renamed["cache_key"])
        self.assertIn("view=suite", one["cache_key"])

    def test_suite_connections_have_no_endpoint_geometry(self):
        result = normalize_snapshot_view(projection([]), view="suite")
        connection = result["connections"][0]
        self.assertEqual(connection["public_connection_id"], "ghost-link:public")
        self.assertNotIn("endpoint_a", connection)
        self.assertNotIn("endpoint_b", connection)


class GhostNetworkSuiteEndpointTest(unittest.TestCase):
    def setUp(self):
        self.session_generation = SessionGenerationFixture(
            "chaos_ghostnetwork_suite_session_"
        ).start()
        self.addCleanup(self.session_generation.stop)

    def client(self):
        client = run.app.test_client()
        headers = self.session_generation.authenticate(client, "alice")
        return client, headers

    def test_owner_aliases_use_one_bounded_batch_lookup(self):
        class FakeGhostNetworkService:
            def get_snapshot_for_viewer(self, viewer=None):
                return projection([
                    projected_part(
                        "ghost-node:hidden", "foreign_blocked", "blocked",
                        territory_id="area-hidden", owner_id="owner-1",
                        location_visibility="territory_only",
                    ),
                    projected_part(
                        "ghost-node:hidden-2", "foreign_blocked", "blocked",
                        territory_id="area-hidden-2", owner_id="owner-1",
                        location_visibility="territory_only",
                    ),
                ])

        client, headers = self.client()
        with patch.object(
            run.identity_projection_store,
            "get_identity",
            return_value={"username": "alice", "ghost_clan_code": "virex"},
        ), patch.object(
            run.identity_projection_store,
            "get_identities",
            return_value=[{
                "username": "owner-1",
                "display_alias": "Owner One",
                "source_profile_revision": 4,
                "source_profile_checksum": "checksum-owner-1",
            }],
        ) as owner_batch, patch.object(
            run.user_store,
            "get_profile",
            side_effect=AssertionError("full profile read"),
        ), patch.object(
            run,
            "sync_session_profile",
            side_effect=AssertionError("full profile sync"),
        ), patch.object(run, "GhostNetworkService", return_value=FakeGhostNetworkService()):
            response = client.get("/api/ghostnetwork/snapshot?view=suite", headers=headers)

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["parts"][0]["owner"]["owner_alias"], "Owner One")
        owner_batch.assert_called_once_with(["owner-1"], max_items=20)

    def test_owner_alias_failure_keeps_safe_snapshot_without_profile_fallback(self):
        class FakeGhostNetworkService:
            def get_snapshot_for_viewer(self, viewer=None):
                return projection([projected_part(
                    "ghost-node:hidden", "foreign_blocked", "blocked",
                    territory_id="area-hidden", owner_id="owner-stale",
                    location_visibility="territory_only",
                )])

        client, headers = self.client()
        with patch.object(
            run.identity_projection_store,
            "get_identity",
            return_value={"username": "alice", "ghost_clan_code": "virex"},
        ), patch.object(
            run.identity_projection_store,
            "get_identities",
            side_effect=RuntimeError("stale bounded projection"),
        ), patch.object(
            run.user_store,
            "get_profile",
            side_effect=AssertionError("full profile fallback"),
        ), patch.object(run, "GhostNetworkService", return_value=FakeGhostNetworkService()):
            response = client.get("/api/ghostnetwork/snapshot?view=suite", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.get_json()["parts"][0]["owner"]["owner_alias"])

    def test_heavy_profile_size_does_not_enter_suite_hot_path(self):
        metrics_by_size = []
        elapsed_by_size = []
        for padding_size in (0, 35_000_000):
            with self.subTest(padding_size=padding_size), tempfile.TemporaryDirectory() as tmpdir:
                db_path = os.path.join(tmpdir, "suite-heavy.sqlite3")
                users = UserStore(db_path=db_path, seed_path=os.path.join(tmpdir, "missing.json"))
                users.save_profile_guarded(
                    valid_profile(padding="x" * padding_size),
                    expected_revision=0,
                    source="test.ghostnetwork_suite.heavy_profile",
                    allow_create=True,
                )
                identities = UserIdentityProjectionStore(db_path=db_path)

                class FakeGhostNetworkService:
                    def get_snapshot_for_viewer(self, viewer=None):
                        return projection([])

                client, headers = self.client()
                identity_reads = 0
                original_get_identity = identities.get_identity

                def counted_identity(username):
                    nonlocal identity_reads
                    identity_reads += 1
                    return original_get_identity(username)

                token = reset_hot_path_metrics()
                started = time.perf_counter()
                try:
                    with patch.object(run, "identity_projection_store", identities), patch.object(
                        identities, "get_identity", side_effect=counted_identity
                    ), patch.object(
                        run.user_store, "get_profile", side_effect=AssertionError("full profile read")
                    ), patch.object(
                        run.user_store, "get_profile_with_revision", side_effect=AssertionError("heavy revision read")
                    ), patch.object(
                        run, "sync_session_profile", side_effect=AssertionError("full profile sync")
                    ), patch.object(run, "GhostNetworkService", return_value=FakeGhostNetworkService()):
                        response = client.get("/api/ghostnetwork/snapshot?view=suite", headers=headers)
                    elapsed_by_size.append((time.perf_counter() - started) * 1000)
                    metrics_by_size.append(get_hot_path_metrics())
                finally:
                    restore_hot_path_metrics(token)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(identity_reads, 1)

        for metrics in metrics_by_size:
            self.assertEqual(metrics["profile_full_read"], 0)
            self.assertEqual(metrics["profile_full_write"], 0)
            self.assertEqual(metrics["profile_bytes"], 0)
            self.assertEqual(metrics["all_user_profile_scan"], 0)
            self.assertEqual(metrics["per_recipient_profile_read"], 0)
            self.assertEqual(metrics["bounded_identity_count"], 1)
        self.assertEqual(len(elapsed_by_size), 2)


if __name__ == "__main__":
    unittest.main()
