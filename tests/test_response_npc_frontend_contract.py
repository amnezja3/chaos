import unittest
from pathlib import Path

from response_network.npc_capsule_factory import SNIKER_DIRECTIONS_8, VISUAL_FAMILIES


class ResponseNPCFrontendContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map_template = Path("templates/map_template.html").read_text(encoding="utf-8")
        cls.terminal_js = Path("static/js/terminal.js").read_text(encoding="utf-8")

    def test_map_uses_existing_sniker_png_contract(self):
        self.assertIn("actor_type", Path("response_network/npc_capsule_factory.py").read_text(encoding="utf-8"))
        self.assertIn("response_npc", Path("response_network/npc_capsule_factory.py").read_text(encoding="utf-8"))
        self.assertIn("npc_${family}_${direction}.png", self.map_template)
        for direction in SNIKER_DIRECTIONS_8:
            self.assertIn(direction, self.map_template)
        for family in VISUAL_FAMILIES:
            self.assertIn(family, self.map_template)

    def test_map_positions_npcs_locally_without_npc_moved(self):
        self.assertIn("positionResponseNpcAt", self.map_template)
        self.assertIn("requestAnimationFrame(window.tickResponseNpcActors)", self.map_template)
        self.assertIn("/api/map/incident-npc-capsules", self.map_template)
        self.assertNotIn("npc.moved", self.map_template)

    def test_full_response_feedback_has_countdown_and_marker_status(self):
        self.assertIn("response-npc-marker-countdown", self.map_template)
        self.assertIn("response-npc-marker-feedback", self.map_template)
        self.assertIn("applyDetectionFeedbackToNpc", self.map_template)
        self.assertIn("mode: 'full'", self.map_template)
        self.assertIn("is-detected", self.map_template)
        self.assertIn("is-rejected", self.map_template)

    def test_delta_feed_routes_npc_scope_and_recovery(self):
        self.assertIn("updateResponseNpcDeltaView", self.terminal_js)
        self.assertIn("recoverResponseNpcDeltaScope", self.terminal_js)
        self.assertIn('event.scope === "npc"', self.terminal_js)
        self.assertIn('String(event.type || "").startsWith("npc.")', self.terminal_js)


if __name__ == "__main__":
    unittest.main()
