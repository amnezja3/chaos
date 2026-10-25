from contextlib import closing
import json
import unittest
from unittest.mock import patch

import test_world_read as fixtures
from poi_infrastructure.service import POIError


class ArchiveRetentionTests(unittest.TestCase):
    setUp = fixtures.LocalWorldReadTests.setUp
    object = fixtures.LocalWorldReadTests.object
    exact = fixtures.LocalWorldReadTests.exact

    def publish(self, retain=None):
        batch, _ = self.exact()
        return self.world.publish_batch('query',self.owner,batch,provider='fixture',revision=1,
            storage_reference='explicit-archive-decision',fresh_until=self.fresh,
            usable_until=self.usable,retain_until=retain)

    def allow(self):
        self.policy['scopes'].append('world_storage')
        self.policy['review_due_at']=self.now+86400
        with self.repo.transaction() as c:
            c.execute('UPDATE poi_provider_config SET config=? WHERE id=?',
                      (json.dumps(self.policy),'fixture'))

    def test_archive_survives_cleanup_but_never_extends_scan_freshness(self):
        self.allow()
        snapshot=self.publish(self.now+7200)
        with patch('time.time',return_value=self.now+3600):
            self.assertIsNone(self.world.read_batch(snapshot,allow_stale=True))
            self.assertEqual(self.world.prune_expired(),0)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_snapshot').fetchone()[0],1)
        with patch('time.time',return_value=self.now+7201):
            self.assertEqual(self.world.prune_expired(),1)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_retention').fetchone()[0],0)
            self.assertEqual(c.execute('SELECT count(*) FROM world_member').fetchone()[0],0)

    def test_no_explicit_retention_preserves_legacy_expiry(self):
        self.publish()
        with patch('time.time',return_value=self.usable+1):
            self.assertEqual(self.world.prune_expired(),1)

    def test_cache_scope_cannot_grant_archive(self):
        with self.assertRaisesRegex(POIError,'world_retention_policy_required'):
            self.publish(self.now+2000)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_snapshot').fetchone()[0],0)

    def test_retention_cannot_outlive_provider_review(self):
        self.allow()
        with self.assertRaisesRegex(POIError,'world_retention_policy_required'):
            self.publish(self.now+86401)

    def test_retention_before_usable_expiry_is_invalid(self):
        self.allow()
        with self.assertRaisesRegex(POIError,'world_retention_invalid'):
            self.publish(self.now+1000)
