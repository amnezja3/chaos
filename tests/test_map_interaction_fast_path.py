import unittest
from pathlib import Path


class MapInteractionFastPathContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map_source = Path("templates/map_template.html").read_text(encoding="utf-8")
        cls.ghost_css = Path("static/css/ghostnetwork_map.css").read_text(encoding="utf-8")

    def test_leaflet_gestures_toggle_one_debounced_interaction_contract(self):
        for token in (
            "const MAP_INTERACTION_SETTLE_MS = 160",
            "map.on('dragstart movestart zoomstart'",
            "map.on('dragend moveend zoomend', settleMapInteraction)",
            "mapInteractionContainer.classList.add('is-map-interacting')",
            "mapInteractionContainer.classList.remove('is-map-interacting')",
            "document.body.classList.add('is-map-interacting')",
            "document.body.classList.remove('is-map-interacting')",
        ):
            self.assertIn(token, self.map_source)

        fast_path = self.map_source[
            self.map_source.index("function beginMapInteraction"):
            self.map_source.index("map.createPane('territoryPane')")
        ]
        for forbidden in ("fetch(", "invalidateSize(", "setView(", "location.reload"):
            self.assertNotIn(forbidden, fast_path)

    def test_coarse_pointer_reduced_motion_and_manual_low_power_share_classes(self):
        for token in (
            "'(hover: none) and (pointer: coarse)'",
            "'(prefers-reduced-motion: reduce)'",
            "chaos_map_low_power",
            "window.setChaosMapLowPowerMode",
            "classList.toggle('is-map-low-power', state.lowPower)",
        ):
            self.assertIn(token, self.map_source)
        for token in (
            "body.is-map-low-power .active-operations-panel",
            "backdrop-filter: none !important",
            "@media (prefers-reduced-motion: reduce), (hover: none) and (pointer: coarse)",
        ):
            self.assertIn(token, self.map_source)

    def test_semantic_state_remains_while_expensive_decoration_is_flattened(self):
        for token in (
            ".leaflet-container.is-map-interacting .ghostnetwork-part-art",
            ".leaflet-container.is-map-interacting .ghostnetwork-connection",
            ".leaflet-container.is-map-interacting .ghostnetwork-territory-active",
            ".leaflet-container.is-map-low-power .ghostnetwork-territory-hostile",
            "animation: none !important",
            "filter: none !important",
        ):
            self.assertIn(token, self.ghost_css)
        self.assertIn(".leaflet-interactive.ghostnetwork-territory-active", self.ghost_css)
        self.assertIn(".leaflet-interactive.ghostnetwork-territory-hostile", self.ghost_css)
        self.assertIn("stroke-dasharray: 3 5", self.ghost_css)

    def test_npc_animation_pauses_without_network_io_and_reconciles_after_settle(self):
        tick = self.map_source[
            self.map_source.index("window.tickResponseNpcActors = function"):
            self.map_source.index("window.ensureResponseNpcAnimation = function")
        ]
        pause = tick.index("window.chaosMapInteractionState.active")
        movement = tick.index("window.updateResponseNpcMarker")
        detection = tick.index("window.runLocalDetectionProbe")
        self.assertLess(pause, movement)
        self.assertLess(pause, detection)
        self.assertNotIn("fetch(", tick)

        settle = self.map_source[
            self.map_source.index("function settleMapInteraction"):
            self.map_source.index("[mapCoarsePointerQuery, mapReducedMotionQuery]")
        ]
        self.assertIn("window.responseNpcLastTick = 0", settle)
        self.assertIn("window.ensureResponseNpcAnimation()", settle)


if __name__ == "__main__":
    unittest.main()
