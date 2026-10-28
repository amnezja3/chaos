from contextlib import closing
from pathlib import Path
import hashlib
import json
import unittest
from unittest.mock import patch
import test_world_shadow as fixtures
from tools.world_poi_evidence import inspect


class EvidenceTests(unittest.TestCase):
    setUp=fixtures.WorldShadowTests.setUp
    grant=fixtures.WorldShadowTests.grant
    fetch=fixtures.WorldShadowTests.fetch

    def seed(self):
        self.grant()
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark',return_value=(self.batch,{})):
            self.fetch()

    def test_exact_profile_export_is_read_only_and_not_certified(self):
        self.seed()
        repo=self.service.repo
        with closing(repo.connect()) as c:before='\n'.join(c.iterdump())
        target=Path(self.tmp.name)/'evidence'
        with patch('socket.create_connection',side_effect=AssertionError('network')):
            result=inspect(repo.path,target)
        self.assertEqual(result['samples'][0]['objects'],1)
        self.assertFalse(result['samples'][0]['regional_scan_approved'])
        item=result['samples'][0]
        raw=(target/item['export_file']).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),item['export_sha256'])
        self.assertNotIn('provenance',json.loads(raw)['objects'][0])
        with closing(repo.connect()) as c:self.assertEqual(before,'\n'.join(c.iterdump()))
        with self.assertRaises(FileExistsError):inspect(repo.path,target)

    def test_corrupt_digest_is_reported_not_exported(self):
        self.seed()
        with self.service.repo.transaction() as c:c.execute("UPDATE world_snapshot SET digest='wrong'")
        result=inspect(self.service.repo.path)
        self.assertEqual(result['samples'],[])
        self.assertEqual(result['issues'][0]['reason'],'digest_mismatch')

    def test_bounded_scan_does_not_claim_missing_data(self):
        self.seed()
        with patch('tools.world_poi_evidence.MAX_BYTES',1):result=inspect(self.service.repo.path)
        self.assertTrue(result['truncated'])
        self.assertEqual(result['examined'],0)
        self.assertEqual(result['samples'],[])

    def test_missing_database_not_created(self):
        path=Path(self.tmp.name)/'missing.sqlite3'
        with self.assertRaises(ValueError):inspect(path)
        self.assertFalse(path.exists())

    def test_bbox_profile_and_scope_usage_are_visible_without_secrets(self):
        self.seed()
        from poi_infrastructure.world_storage import pack
        from poi_infrastructure.credit_budget import CreditBudget
        import time
        repo=self.service.repo
        ledger=CreditBudget(repo)
        ledger.configure_scope('maplark','evidence-test',time.time()-1,time.time()+100,20)
        with repo.transaction() as c:
            row=c.execute('SELECT id,payload FROM world_snapshot').fetchone()
            payload=json.loads(row['payload'])
            payload['profile']='poi'
            payload['selection']='maplark-bbox-unverified'
            payload['observation_context']={'acquisition':'sector-bbox-v1','request_params':{'bbox':'20,51,20.01,51.01','apiKey':'SECRET'}}
            payload['objects'][0]['tags']['phone']='PRIVATE'
            raw=pack(payload)
            c.execute('UPDATE world_snapshot SET payload=?,digest=? WHERE id=?',(raw,hashlib.sha256(raw).hexdigest(),row['id']))
        target=Path(self.tmp.name)/'bbox'
        result=inspect(repo.path,target)
        self.assertEqual(result['samples'][0]['acquisition'],'sector-bbox-v1')
        self.assertTrue(any(s['scope']=='evidence-test' and s['remaining']==20 for s in result['active_budget_scopes']))
        for path in target.iterdir():
            self.assertNotIn('SECRET',path.read_text())
            self.assertNotIn('PRIVATE',path.read_text())
