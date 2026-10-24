import os
import time
import unittest
from unittest.mock import patch
from poi_infrastructure.world_pilot import allowed


class PilotScopeTests(unittest.TestCase):
    def setUp(self):
        self.spatial=dict(lat=52,lon=21,radius=300)
        self.env=patch.dict(os.environ,CHAOS_POI_WORLD_PILOT_USER='robot',
            CHAOS_POI_WORLD_PILOT_CENTER='52,21',CHAOS_POI_WORLD_PILOT_UNTIL=str(time.time()+3600))
        self.env.start();self.addCleanup(self.env.stop)

    def test_account_center_radius_and_expiry(self):
        self.assertTrue(allowed('robot',self.spatial))
        self.assertFalse(allowed('other',self.spatial))
        self.assertFalse(allowed(None,self.spatial))
        self.assertFalse(allowed('robot',dict(self.spatial,lat=52.00001)))
        self.assertFalse(allowed('robot',dict(self.spatial,radius=301)))
        with patch.dict(os.environ,CHAOS_POI_WORLD_PILOT_UNTIL=str(time.time()-1)):
            self.assertFalse(allowed('robot',self.spatial))

    def test_invalid_configuration_fails_closed(self):
        for name,value in [('CHAOS_POI_WORLD_PILOT_CENTER',''),('CHAOS_POI_WORLD_PILOT_CENTER','nan,21'),
                           ('CHAOS_POI_WORLD_PILOT_UNTIL','inf'),('CHAOS_POI_WORLD_PILOT_UNTIL',str(time.time()+90000)),
                           ('CHAOS_POI_WORLD_PILOT_USER','')]:
            with self.subTest(name=name,value=value),patch.dict(os.environ,{name:value}):
                self.assertFalse(allowed('robot',self.spatial))
        self.assertFalse(allowed('robot',None))
        self.assertFalse(allowed('robot',dict(self.spatial,radius=float('nan'))))
