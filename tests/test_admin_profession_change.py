import unittest
from unittest.mock import patch

import run


class AdminProfessionChangeTest(unittest.TestCase):
    def setUp(self):
        run.app.config.update(TESTING=True, SECRET_KEY="admin-profession-test")
        self.client = run.app.test_client()
        with self.client.session_transaction() as session:
            session["user"] = "admin"

    @staticmethod
    def virex_profile(role="4"):
        return {
            "username": "player",
            "clan": "VIREX",
            "fraction": {"id": "3", "name": "VIREX", "role": role},
            "avatar": f"/static/images/avatar-frakcja-3-player-{role}.png",
        }

    def test_contract_offers_only_five_professions_from_players_clan(self):
        contract = run.build_admin_profession_contract(self.virex_profile())

        self.assertEqual("profit_enforcer", contract["current_code"])
        self.assertEqual(5, len(contract["choices"]))
        self.assertEqual(
            {"broker", "architect", "manipulator", "profit_enforcer", "algorithm_curator"},
            {item["code"] for item in contract["choices"]},
        )

    def test_contract_builds_canonical_broker_update_and_legacy_slot(self):
        contract = run.build_admin_profession_contract(self.virex_profile(), "broker")

        self.assertEqual("broker", contract["updates"]["ghost_profession"])
        self.assertEqual("broker", contract["updates"]["profession"])
        self.assertEqual("1", contract["updates"]["fraction"]["role"])
        self.assertEqual(
            "/static/images/avatar-frakcja-3-player-1.png",
            contract["updates"]["avatar"],
        )

    def test_contract_rejects_profession_from_another_clan(self):
        with self.assertRaisesRegex(ValueError, "profession_not_available_for_player_clan"):
            run.build_admin_profession_contract(self.virex_profile(), "analyzer")

    def test_admin_card_renders_clan_scoped_selector_and_generation_guard(self):
        card = run.render_admin_user_card(
            run.build_admin_user_snapshot(self.virex_profile())
        )

        self.assertIn('action="/api/admin/users/profession"', card)
        self.assertIn('value="broker"', card)
        self.assertIn('value="profit_enforcer" selected', card)
        self.assertNotIn('value="analyzer"', card)
        self.assertIn('name="_session_generation"', card)

    def test_admin_endpoint_updates_profile_through_guarded_store(self):
        record = {
            "state": "valid",
            "profile": self.virex_profile(),
            "profile_revision": 7,
        }
        with patch.object(run.user_store, "get_profile_with_revision", return_value=record), \
                patch.object(run.user_store, "save_profile_guarded") as save:
            response = self.client.post(
                "/api/admin/users/profession",
                json={"username": "player", "profession_code": "broker"},
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("Broker", response.get_json()["profession_name"])
        save.assert_called_once()
        candidate = save.call_args.args[0]
        self.assertEqual("broker", candidate["ghost_profession"])
        self.assertEqual("broker", candidate["profession"])
        self.assertEqual(7, save.call_args.kwargs["expected_revision"])
        self.assertEqual("admin.profession_change", save.call_args.kwargs["source"])

    def test_non_admin_is_rejected(self):
        with self.client.session_transaction() as session:
            session["user"] = "player"

        response = self.client.post(
            "/api/admin/users/profession",
            json={"username": "player", "profession_code": "broker"},
        )

        self.assertEqual(403, response.status_code)

    def test_registration_slots_map_to_all_canonical_professions(self):
        expected = {
            "1": ("sentinel_order", [
                "analyzer", "defender", "reconstructor", "mediator", "executor",
            ]),
            "2": ("echo_freedom", [
                "hacktivist", "social_engineer", "revealer", "visionary", "igniter",
            ]),
            "3": ("virex", [
                "broker", "architect", "manipulator", "profit_enforcer", "algorithm_curator",
            ]),
            "4": ("phantom_mesh", [
                "illusionist", "virologist", "paranoid", "network_splitter", "mirror_judge",
            ]),
        }
        for faction_id, (clan_code, professions) in expected.items():
            for slot, profession_code in enumerate(professions, start=1):
                with self.subTest(faction=faction_id, role=slot):
                    identity = run.build_registration_identity_contract(faction_id, slot)
                    self.assertEqual(clan_code, identity["clan_code"])
                    self.assertEqual(profession_code, identity["profession_code"])
                    self.assertEqual(str(slot), identity["role_slot"])
                    self.assertEqual(
                        f"/static/images/avatar-frakcja-{faction_id}-player-{slot}.png",
                        identity["avatar"],
                    )

    def test_registration_rejects_unknown_faction_or_role_slot(self):
        for faction, role in (("5", "1"), ("3", "0"), ("3", "6"), ("3", "broker")):
            with self.subTest(faction=faction, role=role):
                with self.assertRaises(ValueError):
                    run.build_registration_identity_contract(faction, role)


if __name__ == "__main__":
    unittest.main()
