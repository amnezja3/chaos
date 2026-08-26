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
        cls.terminal = Path("static/js/terminal.js").read_text(encoding="utf-8")
        cls.manifest = json.loads(
            Path("static/audio/sfx/manifest.v1.json").read_text(encoding="utf-8")
        )

    def test_sfx_loads_once_before_radio_and_terminal(self):
        self.assertEqual(self.template.count("js/game_sfx.js"), 1)
        self.assertIn("game_sfx.js') }}?v=sfx-ghostnetwork-6", self.template)
        self.assertIn("manifest.v1.json?v=sfx-ghostnetwork-6", self.sfx)
        self.assertLess(self.template.index("js/game_sfx.js"), self.template.index("js/ghost_radio.js"))
        self.assertLess(self.template.index("js/game_sfx.js"), self.template.index("js/terminal.js"))

    def test_manifest_has_secret_path_allowlist_with_expected_buses(self):
        self.assertEqual(self.manifest["schema"], 1)
        self.assertEqual(self.manifest["base_path"], "/static/audio/sfx")
        expected_secret_path = {f"secret_path.scene_{index:02d}" for index in range(1, 7)}
        expected_capture = {
            "capture.target",
            "capture.conflict_pillar",
            "capture.conflict_resolved",
        }
        expected_messages = {
            "cyberner.message_incoming",
            "cyberner.message_sent",
            "system.warning",
            "system.critical",
        }
        expected_ofs = {
            "ofs.intro", "ofs.choice_available", "ofs.choice_confirmed",
            "ofs.progress_checkpoint", "ofs.success", "ofs.failure",
            "ofs.runtime_warning",
        }
        expected_ghostnetwork = {
            "ghostnetwork.part_discovered",
            "ghostnetwork.part_contained",
            "ghostnetwork.part_activated",
            "ghostnetwork.part_hostile",
            "ghostnetwork.part_lost",
            "ghostnetwork.module_progress",
            "ghostnetwork.module_complete",
            "ghostnetwork.signal",
        }
        self.assertEqual(
            set(self.manifest["events"]),
            expected_secret_path | expected_capture | expected_messages | expected_ofs | expected_ghostnetwork,
        )
        self.assertTrue(all(
            self.manifest["events"][event]["bus"] == "lore"
            for event in expected_secret_path
        ))
        self.assertTrue(all(
            self.manifest["events"][event]["bus"] == "gameplay"
            for event in expected_capture
        ))
        self.assertEqual(
            set(self.manifest["buses"]),
            {"lore", "gameplay", "message", "system", "ui"},
        )
        self.assertTrue(self.manifest["events"]["system.critical"]["interrupt_lower_priority"])
        self.assertTrue(self.manifest["events"]["ghostnetwork.signal"]["interrupt_lower_priority"])

    def test_ghostnetwork_sfx_uses_live_delta_gate_and_canonical_events(self):
        expected_mapping = {
            '"ghost.part_discovered": "ghostnetwork.part_discovered"',
            '"ghost.part_contained": "ghostnetwork.part_contained"',
            '"ghost.part_activated": "ghostnetwork.part_activated"',
            '"ghost.part_contested": "ghostnetwork.part_hostile"',
            '"ghost.part_revealed": "ghostnetwork.part_lost"',
            '"ghost.part_deactivated": "ghostnetwork.part_lost"',
            '"ghost.machine_progress_changed": "ghostnetwork.module_progress"',
            '"ghost.machine_online": "ghostnetwork.module_complete"',
            '"ghost.signal_sent": "ghostnetwork.signal"',
        }
        for mapping in expected_mapping:
            self.assertIn(mapping, self.terminal)
        self.assertIn("function playGhostNetworkDeltaSfx", self.terminal)
        self.assertIn("function isGhostNetworkLifecycleSfxTransition", self.terminal)
        self.assertIn("!isGhostNetworkLifecycleSfxTransition(type, payload)", self.terminal)
        self.assertIn("!stateDeltaSfxPlaybackAllowed", self.terminal)
        self.assertIn("Number(payload.active_parts || 0) === Number(payload.previous_active_parts || 0)", self.terminal)
        self.assertIn("playGhostNetworkDeltaSfx(event);", self.terminal)
        self.assertIn("event_id: `ghostnetwork:${eventId}`", self.terminal)
        recovery_source = self.terminal[
            self.terminal.index("async function recoverGhostNetworkDeltaScope"):
            self.terminal.index("async function recoverDeltaScopes")
        ]
        self.assertNotIn("playGhostNetworkDeltaSfx", recovery_source)
        self.assertNotIn("GameSfx.play", recovery_source)

        result = subprocess.run(
            ["node", "tests/js/test_ghostnetwork_sfx_transitions.js"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("ghostnetwork transition sfx tests: OK", result.stdout)

    def test_live_message_audio_is_decoupled_from_hydration_and_cursors(self):
        self.assertIn('event.type === "cyberner.message_created" && stateDeltaSfxPlaybackAllowed', self.terminal)
        self.assertIn('event_id: `cyberner:${messageId}`', self.terminal)
        self.assertIn("stateDeltaSfxLive && !stateDeltaSfxCatchup", self.terminal)
        self.assertIn("systemMessageSfxLive && !systemMessageSfxCatchup", self.terminal)
        self.assertNotIn("cyberner_channel_cursor_store", self.terminal)

    def test_engine_stays_decoupled_from_gameplay_hooks(self):
        self.assertNotIn("aim-target", self.sfx)
        self.assertNotIn("target_captured", self.sfx)
        self.assertNotIn("cyberner.message_created", self.sfx)
        self.assertNotIn("OperationFeedbackSystem", self.sfx)

    def test_watchdog_respects_asset_duration_before_forced_cleanup(self):
        self.assertIn('voice.audio.addEventListener("loadedmetadata"', self.sfx)
        self.assertIn("Math.max(configured, assetDuration)", self.sfx)
        self.assertIn("WATCHDOG_HARD_LIMIT_MS", self.sfx)

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
