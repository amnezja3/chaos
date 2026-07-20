import copy
import unittest

from ghostnetwork import GhostNetworkService
from ghostnetwork.catalog import (
    CATALOG_VERSION,
    get_catalog,
    get_catalog_checksum,
    get_catalog_diagnostics,
    get_onboarding_catalog,
    normalize_ghostnetwork_profile_identity,
    validate_catalog,
)


class GhostNetworkCatalogTest(unittest.TestCase):
    def setUp(self):
        self.catalog = get_catalog()

    def test_catalog_loads_and_validates(self):
        self.assertEqual(self.catalog["catalog_version"], CATALOG_VERSION)
        report = validate_catalog(self.catalog)
        self.assertTrue(report["ok"], report)

    def test_canonical_counts(self):
        self.assertEqual(len(self.catalog["clans"]), 4)
        self.assertEqual(len(self.catalog["machines"]), 4)
        self.assertEqual(len(self.catalog["parts"]), 20)
        self.assertEqual(len(self.catalog["professions"]), 20)
        self.assertEqual(len(self.catalog["abilities"]), 20)

    def test_five_parts_per_clan_and_machine(self):
        for clan in self.catalog["clans"]:
            parts = [item for item in self.catalog["parts"] if item["clan_code"] == clan["code"]]
            self.assertEqual(len(parts), 5, clan["code"])
        for machine in self.catalog["machines"]:
            parts = [item for item in self.catalog["parts"] if item["machine_code"] == machine["code"]]
            self.assertEqual(len(parts), 5, machine["code"])

    def test_unique_codes(self):
        for collection, field in (
            ("clans", "code"),
            ("machines", "code"),
            ("parts", "part_code"),
            ("professions", "code"),
            ("abilities", "ability_code"),
        ):
            values = [item[field] for item in self.catalog[collection]]
            self.assertEqual(len(values), len(set(values)), collection)

    def test_profession_part_one_to_one_and_abilities_exist(self):
        professions_by_part = {item["part_code"]: item for item in self.catalog["professions"]}
        parts_by_profession = {item["profession_code"]: item for item in self.catalog["parts"]}
        abilities = {item["ability_code"] for item in self.catalog["abilities"]}
        self.assertEqual(len(professions_by_part), 20)
        self.assertEqual(len(parts_by_profession), 20)
        for part in self.catalog["parts"]:
            self.assertIn(part["part_code"], professions_by_part)
            self.assertIn(part["ability_code"], abilities)

    def test_machines_belong_to_expected_clans(self):
        expected = {
            "virex_oracle": "virex",
            "echo_libertas": "echo_freedom",
            "phantom_veil": "phantom_mesh",
            "sentinel_aegis": "sentinel_order",
        }
        machines = {item["code"]: item for item in self.catalog["machines"]}
        for machine_code, clan_code in expected.items():
            self.assertEqual(machines[machine_code]["clan_code"], clan_code)

    def test_v1_and_s5_are_canonical(self):
        parts = {item["part_code"]: item for item in self.catalog["parts"]}
        professions = {item["code"]: item for item in self.catalog["professions"]}
        self.assertEqual(parts["V1"]["name"], "Ledger Nexus")
        self.assertEqual(parts["V1"]["profession_code"], "broker")
        self.assertEqual(professions["broker"]["name"], "Broker")
        self.assertEqual(parts["S5"]["name"], "Judgment Core")
        self.assertEqual(parts["S5"]["profession_code"], "executor")
        self.assertEqual(professions["executor"]["name"], "Egzekutor")

    def test_normalizes_current_clan_variants(self):
        variants = {
            "VIREX": "virex",
            "Echo Wolnosci": "echo_freedom",
            "Echo Wolności": "echo_freedom",
            "Siatka Widmo": "phantom_mesh",
            "Strażnicy Ładu": "sentinel_order",
            4: "sentinel_order",
        }
        for value, expected in variants.items():
            result = normalize_ghostnetwork_profile_identity({
                "clan": value,
                "profession": "executor" if expected == "sentinel_order" else "broker",
            })
            if expected != "virex":
                # Make the profession match the clan for this branch.
                profession_by_clan = {
                    "echo_freedom": "visionary",
                    "phantom_mesh": "paranoid",
                    "sentinel_order": "executor",
                }
                result = normalize_ghostnetwork_profile_identity({
                    "clan": value,
                    "profession": profession_by_clan[expected],
                })
            self.assertEqual(result["clan_code"], expected)
            self.assertTrue(result["catalog_valid"], result)

    def test_reject_unknown_clan(self):
        result = normalize_ghostnetwork_profile_identity({
            "clan": "unknown clan",
            "profession": "broker",
        })
        self.assertFalse(result["catalog_valid"])
        self.assertIn("missing_or_unknown_clan", result["validation_errors"])

    def test_reject_profession_from_different_clan(self):
        result = normalize_ghostnetwork_profile_identity({
            "clan": "virex",
            "profession": "executor",
        })
        self.assertFalse(result["catalog_valid"])
        self.assertIn("profession_clan_mismatch", result["validation_errors"])

    def test_onboarding_projection_does_not_reveal_topology(self):
        onboarding = get_onboarding_catalog()
        payload = repr(onboarding)
        self.assertNotIn("topology_anchor", onboarding)
        self.assertNotIn("connections", payload)
        self.assertNotIn("latitude", payload)
        self.assertNotIn("longitude", payload)
        self.assertEqual(len(onboarding["clans"]), 4)
        for clan in onboarding["clans"]:
            self.assertEqual(clan["machine"]["status"], "inactive")
            self.assertEqual(len(clan["professions"]), 5)

    def test_diagnostics_checksum_is_stable_and_sensitive_to_changes(self):
        first = get_catalog_diagnostics()
        second = get_catalog_diagnostics()
        self.assertEqual(first["checksum"], second["checksum"])
        mutated = copy.deepcopy(self.catalog)
        mutated["clans"][0]["name"] = "VIREX MUTATED"
        self.assertNotEqual(first["checksum"], get_catalog_checksum(mutated))

    def test_service_exposes_catalog_without_active_cycle(self):
        service = GhostNetworkService()
        diagnostics = service.get_catalog_diagnostics()
        self.assertTrue(diagnostics["validation"]["ok"])
        self.assertEqual(diagnostics["catalog_version"], CATALOG_VERSION)


if __name__ == "__main__":
    unittest.main()
