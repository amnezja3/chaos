import unittest
from pathlib import Path


class GhostAbilityPresentationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path("templates/map_template.html").read_text(encoding="utf-8")

    def test_map_uses_server_snapshot_and_not_client_realizer_parameters(self):
        self.assertIn("fetch('/api/ghostnetwork/ability'", self.source)
        self.assertIn("'Idempotency-Key': requestId", self.source)
        activation = self.source[
            self.source.index("async function activateGhostAbility"):
            self.source.index("window.refreshGhostAbilitySnapshot =", self.source.index("async function activateGhostAbility"))
        ]
        for forbidden in ("ability_code:", "realizer:", "multiplier:", "parameters:"):
            self.assertNotIn(forbidden, activation)

    def test_activation_show_and_timer_follow_shared_contract(self):
        for token in (
            "chaos-ghost-ability-overlay",
            "presentation.visual_asset_url",
            "presentation.sound_event",
            "presentation.show_duration_ms",
            "ghostAbilityRemaining(windowState.expires_at)",
            "ghostAbilityRemaining(windowState.cooldown_until)",
            "has-ghost-ability-effect",
            "sessionStorage.setItem(key, '1')",
        ):
            self.assertIn(token, self.source)

    def test_existing_territory_palette_is_reused_for_all_clans(self):
        palette = self.source[
            self.source.index("const territoryClanPalette"):
            self.source.index("function normalizeTerritoryClanName")
        ]
        for color in ("#E53935", "#FFD43B", "#00CFA6", "#238BFF"):
            self.assertIn(color, palette)
        self.assertIn("return territoryClanPalette", self.source)

    def test_clock_is_local_and_no_server_poll_loop_is_added(self):
        scheduler = self.source[
            self.source.index("function scheduleGhostAbilityClock"):
            self.source.index("async function refreshGhostAbilitySnapshot")
        ]
        self.assertIn("window.setInterval", scheduler)
        self.assertNotIn("fetch(", scheduler)


if __name__ == "__main__":
    unittest.main()
