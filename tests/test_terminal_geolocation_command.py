import unittest
from pathlib import Path

from terminals.commands import interpret_command


class TerminalGeolocationCommandTests(unittest.TestCase):
    def test_cur_loc_requests_browser_geolocation(self):
        result = interpret_command("teleport cur:loc", {"username": "robot"})

        self.assertEqual(result["terminalGeolocationRequest"]["purpose"], "teleport")
        self.assertIn("lokalizacji", result["response"])
        self.assertNotIn("terminalTeleport", result)

    def test_cur_loc_is_case_insensitive(self):
        result = interpret_command("teleport CUR:LOC", {"username": "robot"})

        self.assertEqual(result["terminalGeolocationRequest"]["purpose"], "teleport")

    def test_coordinate_teleport_contract_is_unchanged(self):
        result = interpret_command("teleport 52.2297:21.0122", {"username": "robot"})

        self.assertAlmostEqual(result["terminalTeleport"]["lat"], 52.2297)
        self.assertAlmostEqual(result["terminalTeleport"]["lng"], 21.0122)
        self.assertNotIn("terminalGeolocationRequest", result)

    def test_coordinate_focus_uses_map_only_contract(self):
        result = interpret_command("focus 50.0614:19.9383", {"username": "robot"})

        self.assertAlmostEqual(result["terminalMapFocus"]["lat"], 50.0614)
        self.assertAlmostEqual(result["terminalMapFocus"]["lng"], 19.9383)
        self.assertEqual(result["terminalMapFocus"]["mode"], "focus")
        self.assertNotIn("terminalTeleport", result)

    def test_focus_cur_loc_requests_geolocation_without_teleport(self):
        result = interpret_command("focus CUR:LOC", {"username": "robot"})

        self.assertEqual(result["terminalGeolocationRequest"]["purpose"], "focus")
        self.assertNotIn("terminalTeleport", result)

    def test_focus_validates_coordinate_bounds(self):
        result = interpret_command("focus 91:181", {"username": "robot"})

        self.assertIn("poza zakresem", result["response"])
        self.assertNotIn("terminalMapFocus", result)

    def test_help_documents_both_focus_forms(self):
        help_text = interpret_command("help", {"username": "robot"})["response"]

        self.assertIn("focus <lat:lon>", help_text)
        self.assertIn("focus cur:loc", help_text)

    def test_focus_frontend_opens_map_without_confirmation_or_position_write(self):
        source = Path("static/js/terminal.js").read_text(encoding="utf-8")
        handler = source[
            source.index("function handleTerminalMapFocus"):
            source.index("function terminalGeolocationErrorMessage")
        ]
        self.assertIn('openSystemAppFromTerminal("map")', handler)
        self.assertIn("notifyOpenMapsBlacknetFocus", handler)
        self.assertNotIn("showGhostDecisionDialog", handler)
        self.assertNotIn("/api/blacknet/cta/teleport", handler)


if __name__ == "__main__":
    unittest.main()
