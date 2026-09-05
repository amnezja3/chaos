import copy
import pathlib
import struct
import unittest

from ghostnetwork.catalog import get_catalog
from ghostnetwork.part_assets import (
    SUPERPOWER_ASSET_ROOT,
    part_superpower_asset_contract,
    part_visual_asset_contract,
)
from tools.export_ghostnetwork_part_assets import ASSET_ROOT, build_asset_report


class GhostNetworkPartAssetExportTests(unittest.TestCase):
    def test_catalog_exports_twenty_unique_individual_png_contracts(self):
        catalog = get_catalog()
        before = copy.deepcopy(catalog)

        report = build_asset_report(catalog)

        self.assertTrue(report["ok"])
        self.assertTrue(report["read_only"])
        self.assertEqual(report["parts_count"], 20)
        self.assertEqual(len({item["logical_asset_key"] for item in report["parts"]}), 20)
        self.assertEqual(len({item["target_path"] for item in report["parts"]}), 20)
        self.assertTrue(all(item["target_path"].startswith(f"{ASSET_ROOT}/") for item in report["parts"]))
        self.assertTrue(all(item["target_path"].endswith(".png") for item in report["parts"]))
        self.assertTrue(all(item["transparency_required"] for item in report["parts"]))
        self.assertEqual(catalog, before, "asset export must not mutate the canonical catalog")
        readme = (pathlib.Path(__file__).resolve().parents[1] / ASSET_ROOT / "README.md").read_text(encoding="utf-8")
        for item in report["parts"]:
            self.assertIn(item["filename"], readme)

    def test_all_delivered_png_files_match_dimensions_and_alpha_contract(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        report = build_asset_report(get_catalog())
        for item in report["parts"]:
            path = root / item["target_path"]
            self.assertTrue(path.is_file(), item["target_path"])
            data = path.read_bytes()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            width, height = struct.unpack(">II", data[16:24])
            self.assertEqual((width, height), (128, 128))
            self.assertIn(data[25], (4, 6), "PNG must carry an alpha channel")

    def test_runtime_cycle_part_ids_are_joined_by_canonical_part_code(self):
        catalog = get_catalog()
        runtime_parts = [{
            "cycle_id": "ghostnetwork_0001",
            "part_id": f"ghostnetwork_0001_{item['part_code'].lower()}",
            "part_code": item["part_code"],
        } for item in reversed(catalog["parts"])]

        report = build_asset_report(
            catalog,
            cycle={"cycle_id": "ghostnetwork_0001"},
            runtime_parts=runtime_parts,
        )

        self.assertTrue(report["ok"])
        self.assertEqual(report["runtime_parts_count"], 20)
        by_code = {item["part_code"]: item for item in report["parts"]}
        self.assertEqual(by_code["V1"]["part_id"], "ghostnetwork_0001_v1")
        self.assertEqual(by_code["S5"]["part_id"], "ghostnetwork_0001_s5")

    def test_superpower_artwork_is_complete_and_separate_from_part_artwork(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        contracts = [
            part_superpower_asset_contract(definition)
            for definition in get_catalog()["parts"]
        ]

        self.assertEqual(20, len(contracts))
        self.assertEqual(20, len({item["visual_asset_path"] for item in contracts}))
        for definition, contract in zip(get_catalog()["parts"], contracts):
            part_contract = part_visual_asset_contract(definition)
            self.assertEqual(
                part_contract["visual_asset_filename"],
                contract["visual_asset_filename"],
            )
            self.assertTrue(
                contract["visual_asset_path"].startswith(f"{SUPERPOWER_ASSET_ROOT}/")
            )
            path = root / contract["visual_asset_path"]
            self.assertTrue(path.is_file(), contract["visual_asset_path"])
            self.assertEqual(b"\x89PNG\r\n\x1a\n", path.read_bytes()[:8])


if __name__ == "__main__":
    unittest.main()
