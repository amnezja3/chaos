from contextlib import closing
import json
import time
from unittest.mock import patch

import unittest
import test_world_dashboard as fixtures
from poi_infrastructure.world_dashboard import coverage
from poi_infrastructure.world_inventory_metrics import summary


class ViewportTests(unittest.TestCase):
    setUp=fixtures.DashboardTests.setUp
    def test_bbox_selects_before_limit_and_preserves_empty_proof(self):
        result=coverage(self.repo,'roads',True,bounds=(21.028,51.998,21.042,52.012))
        self.assertEqual(result['matching_snapshots'],1)
        self.assertTrue(result['items'][0]['empty'])
        self.assertEqual(result['items'][0]['id'],self.ids[1])
        self.assertEqual(coverage(self.repo,bounds=(0,0,1,1))['matching_snapshots'],0)
        with self.repo.transaction() as c:
            source=c.execute('SELECT * FROM world_snapshot WHERE id=?',(self.ids[3],)).fetchone()
            columns=source.keys()
            for i in range(105):
                values=dict(source);values['id']='other-'+str(i);values['fetched']+=i+1
                c.execute('INSERT INTO world_snapshot ('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')',tuple(values.values()))
        self.assertTrue(coverage(self.repo)['truncated'])
        old=coverage(self.repo,'roads',True,bounds=(20.998,51.998,21.012,52.012))
        self.assertEqual([i['id'] for i in old['items']],[self.ids[0]])
        self.assertFalse(old['truncated'])

    def test_invalid_bbox_rejected(self):
        for b in ((0,0,0,1),(0,0,float('nan'),1),(0,0,200,1),(0,0,1)):
            with self.assertRaises(ValueError):coverage(self.repo,bounds=b)

    def test_inventory_counts_identities_not_duplicate_members(self):
        before=summary(self.repo)
        self.assertTrue(before['complete'])
        self.assertEqual(before['unique_objects'],3)
        self.assertEqual(before['first_seen_retained_24h'],3)
        with self.repo.transaction() as c:
            c.execute('UPDATE world_snapshot SET fetched=?',(time.time()-2*86400,))
        after=summary(self.repo)
        self.assertEqual(after['unique_objects'],3)
        self.assertEqual(after['first_seen_retained_24h'],0)
        self.assertGreater(after['database_bytes'],0)

    def test_viewport_and_metrics_do_not_write_or_fetch(self):
        with closing(self.repo.connect()) as c:before='\n'.join(c.iterdump())
        with patch('socket.create_connection',side_effect=AssertionError('network forbidden')):
            coverage(self.repo,bounds=(20,51,22,53))
            summary(self.repo)
        with closing(self.repo.connect()) as c:self.assertEqual('\n'.join(c.iterdump()),before)
