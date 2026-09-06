import unittest
import inspect
from unittest.mock import Mock, patch

import run
from config import PERF_LOG_ENDPOINTS
from tests.session_generation_fixture import SessionGenerationFixture


class GhostNetworkReadPathSafetyTest(unittest.TestCase):
    def setUp(self):
        self.session_generation = SessionGenerationFixture(
            "chaos_ghostnetwork_read_session_"
        ).start()
        self.addCleanup(self.session_generation.stop)

    def _client(self):
        client = run.app.test_client()
        headers = self.session_generation.authenticate(client, "alice")
        return client, headers

    def test_default_profile_sync_does_not_rebuild_or_bridge(self):
        profile = {"username": "alice", "apps": [], "files": []}
        with run.app.test_request_context("/api/profile"):
            run.session["user"] = "alice"
            with patch.object(run.user_store, "get_profile", return_value=profile), \
                    patch.object(run, "rebuild_player_areas_with_territory_delta") as rebuild, \
                    patch.object(run, "bridge_ghostnetwork_territory_publication") as bridge:
                result = run.sync_session_profile(
                    persist_normalization=False,
                    cache_in_session=False,
                )
        self.assertEqual(result["username"], "alice")
        rebuild.assert_not_called()
        bridge.assert_not_called()

    def test_ghostnetwork_snapshot_is_read_only(self):
        service = Mock()
        service.get_snapshot_for_viewer.return_value = {
            "cycle": {"cycle_id": "ghostnetwork_0001", "state_version": 1},
            "parts": [],
            "connections": [],
            "state_version": 1,
        }
        with run.app.test_request_context("/api/ghostnetwork/snapshot?view=map"):
            run.session["user"] = "alice"
            with patch.object(run.identity_projection_store, "get_identity", return_value={"username": "alice"}) as identity, \
                    patch.object(run, "load_profile_readonly", side_effect=AssertionError("full profile read not expected")), \
                    patch.object(run, "GhostNetworkService", return_value=service), \
                    patch.object(run, "bridge_ghostnetwork_territory_publication") as bridge:
                response = run.api_ghostnetwork_snapshot()
        self.assertEqual(response.status_code, 200)
        identity.assert_called_once_with("alice")
        service.get_snapshot_for_viewer.assert_called_once()
        bridge.assert_not_called()

    def test_critical_map_endpoints_are_in_perf_logging_scope(self):
        self.assertTrue({
            "/map",
            "/api/map/player-areas",
            "/api/map/player-actors",
            "/api/operations",
            "/api/state/changes",
            "/api/ghostnetwork/snapshot",
            "/api/ghost-control/territory",
            "/api/ghost-control/territory/security",
            "/api/ghost-control/territory/security-preset",
            "/api/ghost-control/territory/abandon",
            "/api/blacknet/cta/teleport",
        }.issubset(PERF_LOG_ENDPOINTS))

    def test_player_areas_uses_only_lightweight_identity_and_capability_stores(self):
        source = inspect.getsource(run.map_player_areas)
        for token in ("user_store.get_profile(", "user_store.list_profiles(", "sync_session_profile("):
            self.assertNotIn(token, source)
        self.assertIn("identity_projection_store.get_identities", source)
        self.assertIn("capability_projection_store.get_capabilities", source)
        self.assertIn("list_player_areas(limit=500)", source)
        self.assertIn("list_recent_area_intruders(username, limit=100)", source)

    def test_scan_foreign_area_gate_is_bounded_and_uses_identity_projection(self):
        area_source = inspect.getsource(run.find_foreign_area_for_point)
        relation_source = inspect.getsource(run._territory_relation_profile)
        self.assertIn("list_player_areas(limit=1000)", area_source)
        self.assertIn("identity_projection_store.get_identity", relation_source)
        self.assertNotIn("user_store.get_profile", relation_source)

    def test_scan_branch_uses_position_and_capability_projections(self):
        source = inspect.getsource(run.map_action)
        start = source.index("# Scan is a hot path")
        scan_source = source[start:source.index("    else:", start)]
        self.assertIn("player_position_store.get_position", scan_source)
        self.assertIn("identity_projection_store.get_identity", scan_source)
        self.assertIn("capability_projection_store.get_capabilities", scan_source)
        self.assertIn("active_scan_range_effect", scan_source)
        self.assertNotIn("sync_session_profile", scan_source)

    def test_ability_endpoint_never_hydrates_full_profile(self):
        source = inspect.getsource(run.api_ghostnetwork_ability)
        for token in (
            "user_store.get_profile(", "user_store.list_profiles(",
            "sync_session_profile(", "profile_json",
        ):
            self.assertNotIn(token, source)
        self.assertIn("identity_projection_store.get_identity", source)
        self.assertIn("capability_projection_store.get_capabilities", source)

    def test_ability_endpoint_get_and_post_use_narrow_player_context(self):
        client, headers = self._client()
        service = Mock()
        service.get_player_ability_window_snapshot.return_value = {
            "ok": True, "available": True, "active": False, "cooldown": False,
            "ability": {"ability_name": "Przeplywy rynku"},
            "presentation": {"visual_asset_url": "/static/v1.png"},
            "window": None,
        }
        service.active_scan_range_effect.return_value = {
            "active": False, "base_range_m": 2528, "effective_range_m": 2528,
        }
        service.activate_player_ability.return_value = {
            "ok": True, "status": "activated", "window": {"window_id": "w1"},
        }
        identity = {"username": "alice", "clan": "virex", "profession": "broker"}
        capabilities = {"username": "alice", "level": 71, "action_range": 2528, "map_zoom": 18}
        with patch.object(run, "GHOSTNETWORK_ABILITIES_ENABLED", True), \
                patch.object(run.identity_projection_store, "get_identity", return_value=identity), \
                patch.object(run.capability_projection_store, "get_capabilities", return_value=capabilities), \
                patch.object(run, "get_ghostnetwork_service", return_value=service), \
                patch.object(run.user_store, "get_profile", side_effect=AssertionError("full profile read")), \
                patch.object(run.user_store, "list_profiles", side_effect=AssertionError("account scan")):
            get_response = client.get("/api/ghostnetwork/ability", headers=headers)
            post_response = client.post(
                "/api/ghostnetwork/ability",
                headers={**headers, "Idempotency-Key": "request-1"},
                json={"request_id": "request-1"},
            )
        self.assertEqual(200, get_response.status_code)
        get_payload = get_response.get_json()
        self.assertTrue(get_payload["available"])
        self.assertEqual(2528, get_payload["player"]["effective_scan_range_m"])
        self.assertFalse(get_payload["player"]["scan_range_active"])
        self.assertEqual(200, post_response.status_code)
        player_context = service.get_player_ability_window_snapshot.call_args.args[0]
        self.assertEqual("broker", player_context["profession"])
        self.assertEqual(71, player_context["level"])
        service.activate_player_ability.assert_called_once_with(player_context, "request-1")

    def test_target_ability_response_uses_sanitized_current_target(self):
        client, headers = self._client()
        service = Mock()
        service.activate_player_ability.return_value = {
            "ok": True,
            "status": "activated",
            "window": {
                "window_id": "w-v2",
                "ability_code": "service_entrance",
                "source_part_code": "V2",
                "target_id": "map:52.1:21.1:TARGET",
                "player_id": "alice",
                "dedupe_key": "private-dedupe",
            },
            "realizer": {
                "status": "applied",
                "applied_targets": 1,
                "applied_changes": 4,
            },
        }
        canonical_target = {
            "target_id": "map:52.1:21.1:TARGET",
            "lat": 52.1,
            "lng": 21.1,
            "label": "TARGET",
            "actions_allowed": {
                "scan_ports": True, "exploit": True,
                "sniff": True, "trace": True,
            },
            "security": {"firewall": True},
            "ability_application_keys": ["private-window:actions"],
        }
        identity = {
            "username": "alice", "clan": "virex", "profession": "architect",
        }
        capabilities = {
            "username": "alice", "level": 71,
            "action_range": 2528, "map_zoom": 18,
        }
        with patch.object(run, "GHOSTNETWORK_ABILITIES_ENABLED", True), \
                patch.object(run.identity_projection_store, "get_identity", return_value=identity), \
                patch.object(run.capability_projection_store, "get_capabilities", return_value=capabilities), \
                patch.object(run.player_target_runtime_store, "get_active_target", return_value=canonical_target), \
                patch.object(run, "get_ghostnetwork_service", return_value=service), \
                patch.object(run.user_store, "get_profile", side_effect=AssertionError("full profile read")):
            response = client.post(
                "/api/ghostnetwork/ability",
                headers={**headers, "Idempotency-Key": "request-v2"},
                json={"request_id": "request-v2"},
            )

        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        target = payload["target"]
        self.assertTrue(all(target["actions_allowed"].values()))
        self.assertEqual({"firewall": True}, target["security"])
        self.assertNotIn("ability_application_keys", target)
        self.assertEqual("w-v2", payload["window"]["window_id"])
        self.assertNotIn("target_id", payload["window"])
        self.assertNotIn("player_id", payload["window"])
        self.assertNotIn("dedupe_key", payload["window"])

    def test_sprint_130_12_endpoints_have_no_full_profile_helpers(self):
        forbidden = (
            "load_profile_readonly",
            "get_profile(",
            "get_profile_with_revision",
            "sync_session_profile",
            "UserProfileManager",
            "list_profile_identities",
            "list_profiles",
        )
        functions = (
            run.build_territory_control_snapshot,
            run.territory_control_clusters,
            run.territory_control_cluster_detail,
            run.territory_control_security_toggle,
            run.territory_control_security_preset,
            run.territory_control_abandon,
            run.api_blacknet_cta_teleport,
            run.api_ghostnetwork_snapshot,
        )
        for function in functions:
            source = inspect.getsource(function)
            for token in forbidden:
                self.assertNotIn(token, source, f"{function.__name__}: {token}")

    def test_target_snapshot_excludes_heavy_profile_fields(self):
        profile = {
            "username": "alice",
            "targets": [{
                "lat": 52.1, "lng": 21.1, "label": "Node", "icon": "N",
                "huge_private_runtime": "x" * 10000,
            }],
        }
        client, headers = self._client()
        with patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run.player_marked_target_store, "list_targets", return_value=profile["targets"]), \
                patch.object(run.territory_store, "list_captured_targets", return_value=[]):
            response = client.get("/api/map/target-snapshot", headers=headers)
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload["targets"]), 1)
        self.assertNotIn("huge_private_runtime", payload["targets"][0])

    def test_map_document_size_does_not_scale_with_target_collection(self):
        base = {
            "username": "alice", "nick": "Alice", "apps": [], "files": {},
            "curently_possition": {"lat": 52.2, "lng": 21.0},
            "aimed_target": {}, "targets": [], "hacked": [],
        }
        heavy = {
            **base,
            "targets": [
                {
                    "lat": 52.0 + index / 10000,
                    "lng": 21.0 + index / 10000,
                    "label": f"Target {index}",
                    "private_runtime": "x" * 5000,
                }
                for index in range(500)
            ],
        }
        client, headers = self._client()
        map_url = self.session_generation.document_url("/map", headers)
        with patch.object(run, "sync_session_profile", side_effect=[base, heavy]):
            small_response = client.get(map_url, headers=headers)
            heavy_response = client.get(map_url, headers=headers)
        self.assertEqual(small_response.status_code, 200)
        self.assertEqual(heavy_response.status_code, 200)
        self.assertLess(
            abs(len(heavy_response.get_data()) - len(small_response.get_data())),
            10000,
        )


if __name__ == "__main__":
    unittest.main()
