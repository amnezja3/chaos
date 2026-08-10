import unittest

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


if __name__ == "__main__":
    unittest.main()
