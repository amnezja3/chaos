import math
import unittest

from response_network.prison_catalog import get_prison, list_prisons, PRISON_CATALOG_VERSION


class PrisonCatalogTest(unittest.TestCase):
    def test_destinations_have_unique_ids_and_valid_coordinates(self):
        prisons = list_prisons()
        self.assertEqual(PRISON_CATALOG_VERSION, 1)
        self.assertEqual(len(prisons), 10)
        self.assertEqual(len({p['id'] for p in prisons}), 10)
        for prison in prisons:
            self.assertTrue(prison['name'] and prison['city'] and prison['country'])
            self.assertTrue(math.isfinite(prison['lat']) and -90 <= prison['lat'] <= 90)
            self.assertTrue(math.isfinite(prison['lng']) and -180 <= prison['lng'] <= 180)
            self.assertIn(prison['type'], {'supermax', 'maximum_security', 'high_security'})

    def test_approved_precision_and_optional_labels_survive(self):
        self.assertEqual(get_prison('portlaoise')['lat'], 53.0369975)
        self.assertEqual(get_prison('portlaoise')['lng'], -7.2874778)
        self.assertEqual(get_prison('cecot')['full_name'], 'Terrorism Confinement Center')
        self.assertEqual(get_prison('altiplano')['alias'], 'Altiplano')
        self.assertEqual(get_prison('fuchu')['name'], 'Fuchū Prison')

    def test_callers_cannot_change_catalog_and_unknown_id_has_no_fallback(self):
        destination = get_prison('adx_florence')
        destination['lat'] = 0
        items = list_prisons()
        items[0]['lat'] = 0
        items.clear()
        self.assertEqual(get_prison('adx_florence')['lat'], 38.35639)
        self.assertEqual(len(list_prisons()), 10)
        with self.assertRaises(KeyError):
            get_prison('unknown')
