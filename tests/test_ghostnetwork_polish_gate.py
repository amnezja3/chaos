import pathlib
import struct
import unittest

from ghostnetwork.ability_presentation import ABILITY_PRESENTATIONS
from ghostnetwork.ability_realizers import (
    ALLOWED_REALIZER_FAMILIES,
    DEFERRED_REALIZER_FAMILIES,
    GhostAbilityProductionRealizer,
)
from ghostnetwork.catalog import get_catalog
from ghostnetwork.part_assets import (
    part_superpower_asset_contract,
    part_visual_asset_contract,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]


class GhostNetworkPolishGateTest(unittest.TestCase):
    def test_twenty_catalog_abilities_have_one_production_family_and_presentation(self):
        parts = get_catalog()["parts"]
        catalog_codes = {item["ability_code"] for item in parts}
        family_codes = set(GhostAbilityProductionRealizer.ABILITY_FAMILIES)

        self.assertEqual(20, len(parts))
        self.assertEqual(20, len(catalog_codes))
        self.assertEqual(catalog_codes, family_codes)
        self.assertEqual(catalog_codes, set(ABILITY_PRESENTATIONS))
        self.assertTrue(
            set(GhostAbilityProductionRealizer.ABILITY_FAMILIES.values())
            <= set(ALLOWED_REALIZER_FAMILIES)
        )
        self.assertFalse(
            set(GhostAbilityProductionRealizer.ABILITY_FAMILIES.values())
            & set(DEFERRED_REALIZER_FAMILIES)
        )

    def test_each_clan_has_five_complete_and_unique_profiles(self):
        parts = get_catalog()["parts"]
        by_clan = {}
        for part in parts:
            by_clan.setdefault(part["clan_code"], []).append(part)
            display_name, tagline, impact_ui = ABILITY_PRESENTATIONS[part["ability_code"]]
            self.assertTrue(display_name.strip())
            self.assertTrue(tagline.strip())
            self.assertTrue(impact_ui.strip())

        self.assertEqual(
            {"virex": 5, "echo_freedom": 5, "phantom_mesh": 5, "sentinel_order": 5},
            {clan: len(items) for clan, items in by_clan.items()},
        )
        self.assertEqual(20, len({values[0] for values in ABILITY_PRESENTATIONS.values()}))

    def test_presentation_impact_matches_the_certified_family(self):
        expected_impact = {
            "operation_speed": "operation_cards",
            "file_yield": "file_yield",
            "data_quality": "data_quality",
            "hack_actions": "target_action_dots",
            "target_security": "target_security_bar",
            "operation_risk": "operation_risk",
            "scan_range": "scan_range",
            "map_zoom": "map_zoom",
            "territory_defense": "territory_defense",
        }
        for ability_code, family in GhostAbilityProductionRealizer.ABILITY_FAMILIES.items():
            with self.subTest(ability_code=ability_code):
                self.assertEqual(expected_impact[family], ABILITY_PRESENTATIONS[ability_code][2])

    def test_all_timer_and_activation_assets_are_valid_unique_png_files(self):
        timer_paths = set()
        activation_paths = set()
        for part in get_catalog()["parts"]:
            for paths, contract in (
                (timer_paths, part_visual_asset_contract(part)),
                (activation_paths, part_superpower_asset_contract(part)),
            ):
                path = ROOT / contract["visual_asset_path"]
                self.assertTrue(path.is_file(), str(path))
                data = path.read_bytes()
                self.assertGreater(len(data), 24)
                self.assertEqual(b"\x89PNG\r\n\x1a\n", data[:8])
                width, height = struct.unpack(">II", data[16:24])
                self.assertGreater(width, 0)
                self.assertGreater(height, 0)
                paths.add(contract["visual_asset_path"])
        self.assertEqual(20, len(timer_paths))
        self.assertEqual(20, len(activation_paths))

    def test_shared_window_and_frontend_fallback_contract_remain_locked(self):
        config_source = (ROOT / "config.py").read_text(encoding="utf-8")
        map_source = (ROOT / "templates" / "map_template.html").read_text(encoding="utf-8")
        self.assertIn("15 * 60", config_source)
        self.assertIn("60 * 60", config_source)
        self.assertIn("Math.max(4000, Math.min(6000", map_source)
        self.assertGreaterEqual(map_source.count("asset.onerror = () => { asset.hidden = true; };"), 2)
        self.assertIn("addSystemMessage('warning', 'GhostNetwork'", map_source)
        self.assertIn("cache: 'no-store'", map_source)


if __name__ == "__main__":
    unittest.main()
