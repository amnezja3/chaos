from contextlib import closing
from pathlib import Path
import unittest
from unittest.mock import patch
import test_world_discovery_worker as fixtures
from tools.world_land_water_import import run
from poi_infrastructure.providers import Registry
from poi_infrastructure.routing import reason


class ImportTests(unittest.TestCase):
    setUp=fixtures.DiscoveryWorkerTests.setUp
    save_provider=fixtures.DiscoveryWorkerTests.save_provider

    def test_import_roundtrip_is_offline_idempotent_and_not_routable(self):
        self.assertEqual(run('missing')['status'],'plan')
        backup=Path(self.tmp.name)/'before.sqlite3'
        with patch('socket.create_connection',side_effect=AssertionError('network')):
            result=run(self.repo.path,apply=True,backup=backup)
        self.assertEqual(result['status'],'imported_verified')
        self.assertEqual(result['local_state'],'COMPLETE_FRESH')
        self.assertEqual(result['objects'],2)
        provider=next(p for p in Registry(self.repo).list() if p['id']=='natural-earth')
        self.assertEqual(reason(provider,'poi','live'),'offline_archive_only')
        self.assertEqual(reason(provider,'land_water','background'),'offline_archive_only')
        self.assertFalse(provider['probe_allowed'])
        with closing(self.repo.connect()) as c:before='\n'.join(c.iterdump())
        self.assertEqual(run(self.repo.path,apply=True,backup=Path(self.tmp.name)/'unused')['status'],'already_imported')
        with closing(self.repo.connect()) as c:self.assertEqual(before,'\n'.join(c.iterdump()))
        self.assertTrue(backup.exists())
        self.assertEqual(self.ledger.status('maplark')[0]['committed'],0)

    def test_existing_revoked_source_is_not_reapproved(self):
        registry=Registry(self.repo)
        run(self.repo.path,apply=True,backup=Path(self.tmp.name)/'before.sqlite3')
        p=next(p for p in registry.list() if p['id']=='natural-earth')
        registry.enable(p['id'],p['revision'],False,'test')
        with self.assertRaisesRegex(ValueError,'not_approved'):
            run(self.repo.path,apply=True,backup=Path(self.tmp.name)/'unused.sqlite3')
