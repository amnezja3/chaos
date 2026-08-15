import json
import subprocess
import unittest
from pathlib import Path


class GameSfxFrontendContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = Path("templates/linux.html").read_text(encoding="utf-8")
        cls.sfx = Path("static/js/game_sfx.js").read_text(encoding="utf-8")
        cls.radio = Path("static/js/ghost_radio.js").read_text(encoding="utf-8")
        cls.manifest = json.loads(
            Path("static/audio/sfx/manifest.v1.json").read_text(encoding="utf-8")
        )

    def test_sfx_loads_once_before_radio_and_terminal(self):
        self.assertEqual(self.template.count("js/game_sfx.js"), 1)
        self.assertIn("game_sfx.js') }}?v=sfx-secret-path-2", self.template)
        self.assertIn("manifest.v1.json?v=sfx-secret-path-2", self.sfx)
        self.assertLess(self.template.index("js/game_sfx.js"), self.template.index("js/ghost_radio.js"))
        self.assertLess(self.template.index("js/game_sfx.js"), self.template.index("js/terminal.js"))

    def test_manifest_has_secret_path_allowlist_with_expected_buses(self):
        self.assertEqual(self.manifest["schema"], 1)
        self.assertEqual(self.manifest["base_path"], "/static/audio/sfx")
        self.assertEqual(
            set(self.manifest["events"]),
            {f"secret_path.scene_{index:02d}" for index in range(1, 7)},
        )
        self.assertTrue(all(event["bus"] == "lore" for event in self.manifest["events"].values()))
        self.assertEqual(
            set(self.manifest["buses"]),
            {"lore", "gameplay", "message", "system", "ui"},
        )

    def test_foundation_has_no_gameplay_hooks(self):
        self.assertNotIn("aim-target", self.sfx)
        self.assertNotIn("target_captured", self.sfx)
        self.assertNotIn("cyberner.message_created", self.sfx)
        self.assertNotIn("OperationFeedbackSystem", self.sfx)

    def test_radio_exposes_transient_duck_without_overwriting_user_volume(self):
        self.assertIn("requestDuck(gain = 1", self.radio)
        self.assertIn("releaseDuck(handleOrToken)", self.radio)
        self.assertIn("userVolume * duckGain", self.radio)
        self.assertNotIn("state.volume = state.audio.volume", self.radio)

    def test_javascript_contract(self):
        result = subprocess.run(
            ["node", "tests/js/test_game_sfx.js"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("game_sfx contract ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
