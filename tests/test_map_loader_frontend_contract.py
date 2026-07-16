import unittest
from pathlib import Path


class MapLoaderFrontendContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map_template = Path("templates/map_template.html").read_text(encoding="utf-8")

    def test_map_loading_uses_glitch_overlay_contract(self):
        self.assertIn("chaos-map-glitch-overlay", self.map_template)
        self.assertIn("ensureMapGlitchOverlay", self.map_template)
        self.assertIn("pickMapGhostSystemLog", self.map_template)
        self.assertIn("GhostSystem 2108", self.map_template)
        self.assertIn("setMapLoadingIntensity", self.map_template)
        self.assertIn("seedMapGlitchBlocks", self.map_template)
        self.assertIn("chaos-map-glitch-block", self.map_template)
        self.assertIn("--glitch-color", self.map_template)
        self.assertIn("radial-gradient(circle at 50% 50%", self.map_template)
        self.assertIn("chaos-map-glitch-overlay.has-map-log::after", self.map_template)
        self.assertNotIn("chaos-map-sync-status__spinner", self.map_template)

    def test_map_loading_cleans_ready_state(self):
        self.assertIn("state.overlay.classList.remove('is-visible', 'is-slow', 'is-heavy', 'is-overloaded', 'has-map-log')", self.map_template)
        self.assertIn("state.startedAt = 0", self.map_template)
        self.assertIn("clearTimeout(state.heavyTimer)", self.map_template)
        self.assertIn("Boolean(window.mapBootState?.ready)", self.map_template)
        self.assertIn("!bootOverlay?.classList.contains('is-visible')", self.map_template)
        self.assertIn("inset: auto;", self.map_template)

    def test_map_loading_handles_slow_error_and_reduced_motion(self):
        self.assertIn("Siec przeciazona", self.map_template)
        self.assertIn("Blad ladowania", self.map_template)
        self.assertIn("is-heavy", self.map_template)
        self.assertIn("is-overloaded", self.map_template)
        self.assertIn("prefers-reduced-motion: reduce", self.map_template)

    def test_critical_boot_steps_retry_transient_failures(self):
        self.assertIn("waitForMapBootRetry", self.map_template)
        self.assertIn("options.critical ? 2 : 0", self.map_template)
        self.assertIn("Ponawiam:", self.map_template)
        self.assertIn("boot_attempt", self.map_template)

    def test_travel_action_shows_destination_pulse_until_finished(self):
        self.assertIn("travel-destination-pulse", self.map_template)
        self.assertIn("showTravelDestinationPulse", self.map_template)
        self.assertIn("finishTravelPulse = showTravelDestinationPulse(lat, lng)", self.map_template)
        self.assertIn("typeof finishTravelPulse === 'function'", self.map_template)


if __name__ == "__main__":
    unittest.main()
