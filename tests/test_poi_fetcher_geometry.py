import unittest
from types import SimpleNamespace

from poiFetchClass import POIFetcher


class PoiFetcherGeometryTest(unittest.TestCase):
    def test_query_requests_nodes_ways_relations_with_centers(self):
        query = POIFetcher(tag_filters=["shop", "amenity=bank"])._build_query(
            52.2, 21.0, result_limit=60
        )
        self.assertIn('nwr(around:300,52.2,21.0)[~"^(shop)$"~"."]', query)
        self.assertIn('nwr(around:300,52.2,21.0)["amenity"="bank"]', query)
        self.assertIn("out center;", query)
        self.assertNotIn("node(around:", query)

    def test_categorize_accepts_node_way_and_relation_centers(self):
        result = SimpleNamespace(
            nodes=[SimpleNamespace(id=1, lat=52.1, lon=21.1, tags={"shop": "books", "name": "Node"})],
            ways=[SimpleNamespace(id=2, center_lat=52.2, center_lon=21.2,
                                  tags={"amenity": "bank", "name": "Way"})],
            relations=[SimpleNamespace(id=3, center_lat=52.3, center_lon=21.3,
                                       tags={"office": "company", "name": "Relation"})],
        )
        fetcher = POIFetcher(tag_filters=["shop", "amenity", "office"])
        fetcher._categorize_data(result)
        items = fetcher.get_all.__self__.data_by_category
        self.assertEqual(items["shop"][0]["osm_type"], "node")
        self.assertEqual(items["amenity"][0]["osm_type"], "way")
        self.assertEqual(items["office"][0]["osm_type"], "relation")
        self.assertIsNone(items["amenity"][0]["node_id"])


if __name__ == "__main__":
    unittest.main()
