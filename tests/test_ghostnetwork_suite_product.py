import unittest

import run


class GhostNetworkSuiteProductTests(unittest.TestCase):
    def test_product_belongs_to_control_suite_and_uses_admin_fallback(self):
        product = run.get_pro_system_tool("ghostnetworkSuite")
        self.assertIsNotNone(product)
        self.assertEqual(product["family_id"], "ghost_control_suite")
        self.assertEqual(product["price"], 10000)
        self.assertEqual(product["purchase_account"], "admin")
        self.assertEqual(product["interface"], "system_launcher")
        self.assertEqual(product["system_launcher"], "createGhostNetworkSuiteApp")

    def test_product_is_published_in_googleplex_catalog(self):
        products = {item["id"]: item for item in run.pro_system_tools_catalog()}
        product = products["ghostnetworkSuite"]
        self.assertTrue(product["published"])
        self.assertEqual(product["price"], 10000)
        self.assertEqual(product["purchase_account"], "admin")


if __name__ == "__main__":
    unittest.main()
