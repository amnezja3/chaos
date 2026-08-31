import unittest
from pathlib import Path


class Sprint130123FrontendContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.terminal = Path("static/js/terminal.js").read_text(encoding="utf-8")
        cls.map_template = Path("templates/map_template.html").read_text(encoding="utf-8")

    def test_browser_tabs_keep_separate_queries(self):
        self.assertIn("const browserQueries = {", self.terminal)
        self.assertIn("googleplex: \"\"", self.terminal)
        self.assertIn("exchange: \"\"", self.terminal)
        self.assertIn("browserQueries[activeBrowserTab] = search.value", self.terminal)
        self.assertIn("search.value = browserQueries[tabName] || \"\"", self.terminal)

    def test_blacknet_cta_uses_target_tab_query_only(self):
        self.assertIn("browserQueries.googleplex = query", self.terminal)
        self.assertIn("browserQueries.exchange = sector", self.terminal)
        self.assertIn('switchBrowserTab("googleplex")', self.terminal)
        self.assertIn('switchBrowserTab("exchange")', self.terminal)

    def test_catalog_payload_is_array_checked_before_assignment(self):
        validation = "if (!resourcesRes.ok || !Array.isArray(catalogPayload))"
        assignment = "catalog = catalogPayload"
        self.assertIn(validation, self.terminal)
        self.assertLess(self.terminal.index(validation), self.terminal.index(assignment))

    def test_focus_and_teleport_reject_zero_zero(self):
        self.assertIn("function hasUsableGameplayCoordinates", self.terminal)
        self.assertIn("!(Math.abs(lat) < 0.000001 && Math.abs(lng) < 0.000001)", self.terminal)
        self.assertIn("if (!hasUsableGameplayCoordinates(focus))", self.terminal)

    def test_blacknet_coordinate_teleport_does_not_resolve_display_label_as_hotspot(self):
        self.assertIn('const hotspotId = hasCoordinates ? "" : String(', self.terminal)
        self.assertIn("window.blacknetCoordinateFocusLayer = L.circleMarker([lat, lng]", self.map_template)

    def test_non_osm_tile_scheme_has_runtime_404_fallback(self):
        self.assertIn('layer.on("tileerror"', self.map_template)
        self.assertIn("consecutiveErrors < 3", self.map_template)
        self.assertIn("layer.setUrl(mapTileScheme.fallback_tiles, false)", self.map_template)
        self.assertNotIn("mapTileScheme.selected = mapTileScheme.fallback", self.map_template)

    def test_map_tiles_send_origin_without_generation_query(self):
        self.assertIn('<meta name="referrer" content="origin">', self.map_template)
        self.assertNotIn('<meta name="referrer" content="no-referrer">', self.map_template)


if __name__ == "__main__":
    unittest.main()
