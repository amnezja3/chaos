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
            "presentation.timer_asset_url",
            "presentation.activation_tagline",
            "presentation.sound_event",
            "presentation.show_duration_ms",
            "ghostAbilityRemaining(windowState.expires_at)",
            "ghostAbilityRemaining(windowState.cooldown_until)",
            "has-ghost-ability-effect",
            "sessionStorage.setItem(key, '1')",
        ):
            self.assertIn(token, self.source)
        self.assertIn("options: { position: 'bottomleft' }", self.source)
        self.assertIn('class="chaos-ghost-ability-caption"', self.source)
        self.assertIn("'ghostnetwork.part_activated'", self.source)
        self.assertIn("presentation.visual_asset_max_px", self.source)
        self.assertIn("presentation.visual_asset_padding_px", self.source)
        self.assertIn("presentation.visual_asset_motion", self.source)
        self.assertIn("ghost-ability-asset-shake", self.source)
        self.assertIn("ghost-ability-text-quake", self.source)
        overlay = self.source[
            self.source.index("function showGhostAbilityActivation"):
            self.source.index("function ghostAbilityExpiryMessageOnce")
        ]
        clock = self.source[
            self.source.index("function renderGhostAbilityControl"):
            self.source.index("function scheduleGhostAbilityClock")
        ]
        self.assertNotIn("timer_asset_url", overlay)
        self.assertNotIn("semantic_description", overlay)
        self.assertIn("presentation.timer_asset_url || presentation.visual_asset_url", clock)

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

    def test_mobile_operation_panel_stays_below_ability_control(self):
        mobile = self.source[
            self.source.index("@media (max-width: 720px)"):
            self.source.index(".chaos-map-refresh-control", self.source.index("@media (max-width: 720px)"))
        ]
        operation_panel = mobile[
            mobile.index(".active-operations-panel {"):
            mobile.index("}", mobile.index(".active-operations-panel {"))
        ]
        self.assertIn("z-index: 850", operation_panel)
        self.assertIn("options: { position: 'bottomleft' }", self.source)
        self.assertIn(".leaflet-bottom.leaflet-right", self.source)
        self.assertIn("z-index: 800", self.source)


if __name__ == "__main__":
    unittest.main()
