import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class GhostNetworkMapLayerContractTest(unittest.TestCase):
    def setUp(self):
        self.map_js = (ROOT / "static" / "js" / "map" / "ghostnetwork.js").read_text(encoding="utf-8")
        self.map_template = (ROOT / "templates" / "map_template.html").read_text(encoding="utf-8")
        self.terminal_js = (ROOT / "static" / "js" / "terminal.js").read_text(encoding="utf-8")

    def test_map_module_exposes_required_runtime_contract(self):
        for name in [
            "loadGhostNetworkSnapshot",
            "renderGhostParts",
            "renderGhostConnections",
            "createGhostConnectionLayer",
            "updateGhostConnectionLayer",
            "removeGhostConnectionLayer",
            "applyGhostConnectionDelta",
            "applyGhostNetworkDelta",
            "animateGhostConnectionPulse",
            "applyGhostPartDelta",
            "removeGhostPartMarker",
            "renderGhostTerritoryBadge",
            "openGhostPartPanel",
            "clearGhostNetworkLayer",
            "recoverGhostNetworkLayer",
            "GhostNetworkDeltaClient",
            "applyGhostNetworkDeltaPayload",
            "registerGhostNetworkDeltaView",
            "unregisterGhostNetworkDeltaView",
        ]:
            self.assertIn(f"window.{name}", self.map_js)

        self.assertIn("/api/ghostnetwork/snapshot", self.map_js)
        self.assertIn("ghostNetworkPartPane", self.map_js)
        self.assertIn("ghostNetworkConnectionPane", self.map_js)
        self.assertIn("ghostNetworkPulsePane", self.map_js)
        self.assertIn("ghostNetworkTerritoryPane", self.map_js)
        self.assertIn("window.ghostNetworkPartLayers", self.map_js)
        self.assertIn("window.ghostNetworkConnectionLayers", self.map_js)
        self.assertIn("public_connection_id", self.map_js)
        self.assertIn("public_entity_id", self.map_js)

    def test_map_layer_does_not_create_heavy_polling_or_profile_reads(self):
        self.assertNotIn("/api/profile", self.map_js)
        self.assertNotIn("sync_session_profile", self.map_js)
        self.assertNotIn("setInterval(", self.map_js)

    def test_map_template_loads_layer_as_optional_scope(self):
        self.assertIn("/static/css/ghostnetwork_map.css", self.map_template)
        self.assertIn("/static/js/map/ghostnetwork.js", self.map_template)
        self.assertIn("window.chaosMap = map", self.map_template)
        self.assertIn("loadGhostNetworkSnapshot", self.map_template)
        self.assertIn("'ghostnetwork'", self.map_template)

    def test_desktop_delta_feed_dispatches_ghostnetwork_scope(self):
        self.assertIn("updateGhostNetworkDeltaView", self.terminal_js)
        self.assertIn("GhostNetworkDeltaClient", self.terminal_js)
        self.assertIn("GhostNetworkDeltaClient.handle", self.terminal_js)
        self.assertIn("applyGhostNetworkDelta", self.terminal_js)
        self.assertIn("applyGhostPartDelta", self.terminal_js)
        self.assertIn("recoverGhostNetworkDeltaScope", self.terminal_js)
        self.assertIn('"ghostnetwork"', self.terminal_js)

    def test_filtered_domain_version_gaps_do_not_force_snapshot_recovery(self):
        self.assertNotIn('requestGhostNetworkRecovery("version_gap"', self.map_js)
        self.assertIn("per-user delta bus owns", self.map_js)

    def test_snapshot_preserves_last_good_layer_on_incomplete_or_stale_payload(self):
        self.assertIn("isCompleteGhostNetworkSnapshot", self.map_js)
        self.assertIn('console.warn("[ghostnetwork] incomplete snapshot rejected")', self.map_js)
        self.assertIn('console.warn("[ghostnetwork] stale snapshot rejected"', self.map_js)
        validation = self.map_js.index("if (!isCompleteGhostNetworkSnapshot(data))")
        render = self.map_js.index("renderGhostParts(data.parts || [])")
        self.assertLess(validation, render)

    def test_recovery_is_coalesced_and_missing_projection_requests_it_once(self):
        self.assertIn("if (ghostNetworkRecoveryPromise) return ghostNetworkRecoveryPromise", self.map_js)
        self.assertEqual(self.map_js.count('requestGhostNetworkRecovery("unapplied_delta", event)'), 1)
        self.assertNotIn('recoverGhostNetworkLayer({ reason: "missing_projection"', self.map_js)
        self.assertNotIn('recoverGhostNetworkLayer({ reason: "missing_connection_projection"', self.map_js)

    def test_pending_territory_registry_is_bounded_and_cleaned_with_marker(self):
        self.assertIn("while (pendingKeys.length > MAX_VISIBLE_PARTS)", self.map_js)
        remove_start = self.map_js.index("function removeGhostPartMarker")
        remove_end = self.map_js.index("function removeGhostConnectionLayer")
        remove_source = self.map_js[remove_start:remove_end]
        self.assertIn("delete window.ghostNetworkPendingTerritoryParts[normalizedKey]", remove_source)

    def test_territory_only_part_uses_visible_polygon_center_without_exact_location(self):
        self.assertIn("window.territoryAreaLayers", self.map_js)
        self.assertIn("layer.getBounds()", self.map_js)
        self.assertIn("bounds.getCenter()", self.map_js)
        self.assertIn("window.ghostNetworkPendingTerritoryParts", self.map_js)
        self.assertIn("window.refreshGhostTerritoryBadges", self.map_js)
        self.assertIn("window.refreshGhostTerritoryBadges()", self.map_template)

    def test_connection_styles_are_isolated_and_lightweight(self):
        css = (ROOT / "static" / "css" / "ghostnetwork_map.css").read_text(encoding="utf-8")
        self.assertIn(".ghostnetwork-connection", css)
        self.assertIn("ghostnetwork-connection-pulse", css)

    def test_territory_only_badge_has_renderable_dimensions(self):
        css = (ROOT / "static" / "css" / "ghostnetwork_map.css").read_text(encoding="utf-8")
        badge = css.split(".ghostnetwork-territory-badge {", 1)[1].split("}", 1)[0]
        self.assertIn("display: block", badge)
        self.assertIn("width: 16px", badge)
        self.assertIn("height: 16px", badge)
        self.assertIn("prefers-reduced-motion", css)

    def test_strategic_states_decorate_canonical_owner_polygon(self):
        self.assertIn('moduleState === "blocked"', self.map_js)
        self.assertIn('moduleState === "active"', self.map_js)
        self.assertIn("setGhostTerritoryLayerState", self.map_js)
        self.assertIn("window.refreshGhostTerritoryStates", self.map_js)
        self.assertNotIn("ghostNetworkStrategicOverlayLayers", self.map_js)

        css = (ROOT / "static" / "css" / "ghostnetwork_map.css").read_text(encoding="utf-8")
        self.assertIn(".leaflet-interactive.ghostnetwork-territory-active", css)
        self.assertIn(".leaflet-interactive.ghostnetwork-territory-hostile", css)

    def test_part_png_renderer_has_fallback_lifecycle_and_live_only_transitions(self):
        self.assertIn("part.visual_asset_url", self.map_js)
        self.assertIn("ghostnetwork-part-art", self.map_js)
        self.assertIn("ghostnetwork-part-fallback", self.map_js)
        self.assertIn('type === "ghost.part_contained"', self.map_js)
        self.assertIn('type === "ghost.part_activated"', self.map_js)
        snapshot_render = self.map_js.index("renderGhostParts(data.parts || [])")
        transition_logic = self.map_js.index('type === "ghost.part_contained"')
        self.assertLess(snapshot_render, transition_logic)

        css = (ROOT / "static" / "css" / "ghostnetwork_map.css").read_text(encoding="utf-8")
        self.assertIn("width: 54px", css)
        self.assertIn("ghostnetwork-part-jitter", css)
        self.assertIn("ghostnetwork-part-containment-transition", css)
        self.assertIn("ghostnetwork-part-activation-transition", css)

    def test_territory_snapshot_refresh_reapplies_strategic_state(self):
        self.assertIn("window.refreshGhostTerritoryStates();", self.map_template)


if __name__ == "__main__":
    unittest.main()
