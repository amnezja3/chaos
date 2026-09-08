import unittest
from pathlib import Path


class MapLodRuntimeContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map_source = Path("templates/map_template.html").read_text(encoding="utf-8")
        cls.ghost_source = Path("static/js/map/ghostnetwork.js").read_text(encoding="utf-8")

    def test_zoom_lod_has_mobile_thresholds_and_reconcile_hooks(self):
        for token in (
            "if (zoom <= (mobile ? 12 : 10)) return 'strategic'",
            "if (zoom <= (mobile ? 15 : 13)) return 'tactical'",
            "map.on('zoom', scheduleMapLevelOfDetail)",
            "reconcileActiveOperationMarkerLod",
            "reconcileResponseNpcMarkerLod",
            "reconcileScanResultMarkerLod",
            "refreshGhostNetworkLod",
        ):
            self.assertIn(token, self.map_source)

    def test_mobile_territory_geometry_uses_shared_canvas_renderer(self):
        self.assertIn("L.canvas({ pane: 'territoryPane'", self.map_source)
        self.assertGreaterEqual(self.map_source.count("renderer: territoryPathRenderer()"), 4)
        self.assertIn("layer.setStyle(normalized === \"none\"", self.ghost_source)

    def test_mobile_tiles_stop_move_updates_and_restore_desktop_policy(self):
        self.assertIn("map.off('move', layer._onMove, layer)", self.map_source)
        self.assertIn("layer._chaosMoveListenerSuppressed = true", self.map_source)
        self.assertIn("if (!baseline.updateWhenIdle) map.on('move', layer._onMove, layer)", self.map_source)

    def test_dense_dom_layers_are_detached_not_deleted(self):
        for function_name in (
            "window.reconcileActiveOperationMarkerLod = function",
            "window.reconcileResponseNpcMarkerLod = function",
            "window.reconcileScanResultMarkerLod = function",
        ):
            start = self.map_source.index(function_name)
            section = self.map_source[start:start + 5000]
            self.assertIn("map.removeLayer", section)
            self.assertIn("addTo(map)", section)
        self.assertIn("is-map-lod-cluster", self.map_source)

    def test_ghostnetwork_far_lod_is_one_clipped_canvas_path(self):
        self.assertIn('return isMobileGhostNetworkMap() || lowPower || level !== "detail" ? "flat" : "full"', self.ghost_source)
        flat_start = self.ghost_source.index('if (ghostNetworkLodMode(map) === "flat")')
        flat_end = self.ghost_source.index("const layers = [", flat_start)
        flat = self.ghost_source[flat_start:flat_end]
        self.assertIn("renderer: renderer || undefined", flat)
        self.assertIn("noClip: false", flat)
        self.assertNotIn("L.layerGroup", flat)

    def test_development_probe_is_local_and_read_only(self):
        start = self.map_source.index("window.chaosMapPerformanceProbe = function")
        end = self.map_source.index("function targetLayerKey", start)
        probe = self.map_source[start:end]
        for token in ("leaflet_layers", "svg_paths", "dom_markers", "reconcile_ms", "long_tasks", "chaos_map_perf_probe"):
            self.assertIn(token, probe)
        for forbidden in ("fetch(", "localStorage.setItem", "sessionStorage.setItem"):
            self.assertNotIn(forbidden, probe)


if __name__ == "__main__":
    unittest.main()
