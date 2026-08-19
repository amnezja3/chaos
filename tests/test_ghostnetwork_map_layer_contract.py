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

    def test_territory_only_part_uses_visible_polygon_center_without_exact_location(self):
        self.assertIn("window.territoryAreaLayers", self.map_js)
        self.assertIn("layer.getBounds()", self.map_js)
        self.assertIn("bounds.getCenter()", self.map_js)

    def test_connection_styles_are_isolated_and_lightweight(self):
        css = (ROOT / "static" / "css" / "ghostnetwork_map.css").read_text(encoding="utf-8")
        self.assertIn(".ghostnetwork-connection", css)
        self.assertIn("ghostnetwork-connection-pulse", css)
        self.assertIn("prefers-reduced-motion", css)


if __name__ == "__main__":
    unittest.main()
