import json
import unittest
from pathlib import Path


class SecretPathSfxContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map_template = Path("templates/map_template.html").read_text(encoding="utf-8")
        cls.terminal = Path("static/js/terminal.js").read_text(encoding="utf-8")
        cls.manifest = json.loads(
            Path("static/audio/sfx/manifest.v1.json").read_text(encoding="utf-8")
        )

    def test_six_visual_scenes_map_one_to_one_to_six_events(self):
        scene_ids = (
            "target_repaired",
            "route_open",
            "skill_verified",
            "acceleration",
            "lore_discovered",
            "chaos_protocol_2108",
        )
        for index, scene_id in enumerate(scene_ids, start=1):
            event_key = f"secret_path.scene_{index:02d}"
            self.assertIn(f"scene_id: '{scene_id}'", self.map_template)
            self.assertIn(f"sound_event: '{event_key}'", self.map_template)
            self.assertIn(event_key, self.manifest["events"])
        self.assertEqual(self.map_template.count("sound_event: 'secret_path.scene_"), 6)

    def test_one_selected_scene_drives_visual_and_audio(self):
        self.assertIn("const scene = secretPathLoreScenes[", self.map_template)
        self.assertIn("scene.eyebrow", self.map_template)
        self.assertIn("scene.title", self.map_template)
        self.assertIn("scene.copy", self.map_template)
        self.assertIn("sfx.play(scene.sound_event", self.map_template)
        self.assertIn("scene_id: scene.scene_id", self.map_template)

    def test_audio_is_armed_from_gesture_and_plays_after_success(self):
        endpoint = self.map_template.index("async function aimMapTargetOnly")
        arm = self.map_template.index("armSecretPathAudio();", endpoint)
        fetch = self.map_template.index("fetch('/api/map/aim-target'", endpoint)
        show = self.map_template.index("showSecretPathLore(data.target);", endpoint)
        self.assertLess(arm, fetch)
        self.assertGreater(show, fetch)
        self.assertIn("event_id: `secret-path:${targetId}:${sequence}`", self.map_template)
        self.assertIn("}, 4000);", self.map_template)

    def test_settings_expose_enabled_volume_and_neutral_test(self):
        self.assertIn("data-settings-sfx-enabled", self.terminal)
        self.assertIn("data-settings-sfx-volume", self.terminal)
        self.assertIn("data-settings-sfx-test", self.terminal)
        self.assertIn("window.GameSfx.setEnabled", self.terminal)
        self.assertIn("window.GameSfx.setVolume", self.terminal)
        self.assertIn("window.GameSfx.play('secret_path.scene_06'", self.terminal)


if __name__ == "__main__":
    unittest.main()
