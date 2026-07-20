import os
import tempfile
import unittest

from ghostnetwork import GhostAbilityRegistry, GhostCycleService, GhostNetworkRepository, GhostNetworkService
from ghostnetwork.abilities import ABILITY_MECHANICS_STATUSES, DEFAULT_PART_LOSS_POLICY
from ghostnetwork.catalog import get_catalog


class GhostAbilityRegistryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        self.cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        self.registry = GhostAbilityRegistry(repository=self.repo)
        self.service = GhostNetworkService(repository=self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def part_by_code(self, part_code):
        return next(
            part for part in self.repo.list_parts(self.cycle["cycle_id"])
            if part["part_code"] == part_code
        )

    def activate_part(self, part, owner="territory-owner"):
        return self.repo.update_part(
            part["part_id"],
            status="active",
            target_id=f"target-{part['part_id']}",
            latitude=52.25,
            longitude=21.0,
            discovered_by="main",
            discovered_clan=part["clan_code"],
            conflict_state="none",
            frozen_status="",
            conflict_id="",
            territory_id="territory-active",
            territory_owner_id=owner,
            territory_clan=part["clan_code"],
        )

    def public_part(self, part):
        return self.repo.update_part(
            part["part_id"],
            status="public",
            target_id=f"target-{part['part_id']}",
            latitude=52.25,
            longitude=21.0,
            discovered_by="main",
            discovered_clan=part["clan_code"],
            conflict_state="none",
            frozen_status="",
            conflict_id="",
            territory_id="",
            territory_owner_id="",
            territory_clan="",
        )

    def player(self, clan="virex", profession="broker", username="operator"):
        return {
            "username": username,
            "clan": clan,
            "profession": profession,
            "level": 17,
        }

    def test_catalog_contracts_have_adapters_and_policies(self):
        catalog = get_catalog()
        self.assertEqual(len(catalog["abilities"]), 20)
        seen_adapters = set()
        for effect in self.registry.list_for_clan("virex"):
            seen_adapters.add(effect["adapter_code"])
            self.assertIn(effect["mechanics_status"], ABILITY_MECHANICS_STATUSES)
            self.assertEqual(effect["part_loss_policy"], DEFAULT_PART_LOSS_POLICY)
            self.assertTrue(effect["contract_checksum"])
        self.assertEqual(len(self.registry.list_for_clan("virex")), 5)
        self.assertTrue(seen_adapters)

        for ability in catalog["abilities"]:
            effect = self.registry.get(ability["ability_code"])
            self.assertIsNotNone(effect, ability["ability_code"])
            self.assertIn(effect["adapter_code"], self.registry.adapters)
            self.assertNotEqual(effect["mechanics_status"], "implemented")

    def test_profession_without_active_part_has_no_active_power(self):
        resolved = self.registry.resolve_player_abilities(self.player())
        self.assertEqual(resolved["active_abilities"], [])
        self.assertEqual(resolved["ability"]["activation_reason"], "module_not_active")
        self.assertFalse(self.registry.is_ability_active(self.player(), "insider_feed"))

    def test_matching_active_part_enables_power_for_clan_profession_members(self):
        self.activate_part(self.part_by_code("V1"), owner="someone_else")
        resolved = self.registry.resolve_player_abilities(self.player(username="ally"))
        self.assertEqual(len(resolved["active_abilities"]), 1)
        ability = resolved["active_abilities"][0]
        self.assertEqual(ability["ability_code"], "insider_feed")
        self.assertEqual(ability["profession_code"], "broker")
        self.assertEqual(ability["source_part_code"], "V1")
        self.assertTrue(self.service.is_ability_active(self.player(username="ally"), "insider_feed"))

    def test_wrong_profession_or_clan_cannot_use_active_part(self):
        self.activate_part(self.part_by_code("V1"), owner="main")
        wrong_profession = self.registry.resolve_player_abilities(self.player(profession="architect"))
        self.assertEqual(wrong_profession["active_abilities"], [])
        self.assertEqual(wrong_profession["ability"]["ability_code"], "service_entrance")

        wrong_clan = self.registry.resolve_player_abilities(
            self.player(clan="echo_freedom", profession="hacktivist")
        )
        self.assertEqual(wrong_clan["active_abilities"], [])

    def test_owner_without_matching_profession_has_no_personal_power(self):
        self.activate_part(self.part_by_code("V1"), owner="owner")
        resolved = self.registry.resolve_player_abilities(
            self.player(clan="virex", profession="architect", username="owner")
        )
        self.assertEqual(resolved["active_abilities"], [])
        self.assertFalse(self.registry.is_ability_active(self.player(profession="architect"), "insider_feed"))

    def test_conflict_preserves_power_when_frozen_state_is_active(self):
        active = self.activate_part(self.part_by_code("V1"), owner="main")
        self.repo.update_part(
            active["part_id"],
            conflict_state="contested",
            frozen_status="active",
            conflict_id="conflict-v1",
        )
        resolved = self.registry.resolve_player_abilities(self.player())
        self.assertEqual(len(resolved["active_abilities"]), 1)
        self.assertEqual(resolved["active_abilities"][0]["conflict_state"], "contested")

    def test_stable_part_loss_disables_power_and_changes_cache_key(self):
        active = self.activate_part(self.part_by_code("V1"), owner="main")
        first = self.registry.resolve_player_abilities(self.player())
        self.assertEqual(len(first["active_abilities"]), 1)

        self.public_part(active)
        second = self.registry.resolve_player_abilities(self.player())
        self.assertEqual(second["active_abilities"], [])
        self.assertEqual(second["ability"]["activation_reason"], "module_not_active")
        self.assertNotEqual(first["cache_key"], second["cache_key"])

    def test_closed_or_transmitted_cycle_disables_power(self):
        self.activate_part(self.part_by_code("V1"), owner="main")
        active = self.registry.resolve_player_abilities(self.player())
        self.assertEqual(len(active["active_abilities"]), 1)

        self.repo.update_cycle(self.cycle["cycle_id"], transmitted_at=self.repo.now())
        transmitted = self.registry.resolve_player_abilities(self.player())
        self.assertEqual(transmitted["active_abilities"], [])
        self.assertEqual(transmitted["ability"]["activation_reason"], "cycle_closed_or_transmitted")

    def test_collect_effects_and_modifier_are_central_noop_until_adapter_implements_mechanics(self):
        self.activate_part(self.part_by_code("V1"), owner="main")
        effects = self.registry.collect_effects("market_demand_preview", {"player_context": self.player()})
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["ability_code"], "insider_feed")
        self.assertEqual(
            self.registry.apply_modifier("market_demand_preview", {"player_context": self.player()}, 100),
            100,
        )


if __name__ == "__main__":
    unittest.main()
