import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from database import db_connect
from camera_visual_archive import ArchiveStore,SCHEMAS,FixtureSource
from camera_visual_source import MapillarySource,SourceError,select_images,optimize,get_bytes


class CameraArchiveTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path=str(Path(self.tmp.name)/'test.sqlite3')
        self.env=patch.dict(os.environ,CHAOS_CAMERA_SOURCE='fixture',CHAOS_CAMERA_WORKER='1',
            CHAOS_CAMERA_ARCHIVE_DIR=str(Path(self.tmp.name)/'media'))
        self.env.start(); self.addCleanup(self.env.stop)
        with db_connect(self.path) as conn:
            for sql in SCHEMAS: conn.execute(sql)
        self.store=ArchiveStore(self.path)
        self.target=dict(camera_id='camera-1',lat=48.86417,lng=2.33050)

    def enqueue(self):
        with db_connect(self.path) as conn: return self.store.enqueue(conn,self.target)

    def manifest(self,key):
        with db_connect(self.path) as conn: return self.store.manifest(conn,key)

    def test_shared_archive_optimized_and_withdrawn(self):
        key=self.enqueue(); self.assertEqual(self.enqueue(),key)
        result=self.store.process_one(); self.assertEqual(result['status'],'READY',result)
        manifest=self.manifest(key); self.assertEqual(len(manifest['images']),3)
        for image in manifest['images']:
            self.assertLessEqual(image['width'],960); self.assertLessEqual(image['height'],540)
            self.assertTrue(self.store.media_path(image).is_file())
        self.assertEqual(self.store.process_one()['status'],'IDLE')
        item=manifest['images'][0]
        self.store.withdraw(item['source'],item['image_id'],'test withdrawal')
        self.assertEqual(len(self.manifest(key)['images']),2)
        # Tombstone also defeats a worker which encounters the same source later.
        self.target['camera_id']='camera-2'; other=self.enqueue(); self.store.process_one()
        self.assertNotIn(item['image_id'],[i['image_id'] for i in self.manifest(other)['images']])

    def test_empty_failure_restart_fencing_and_expiry(self):
        key=self.enqueue()
        class Empty:
            name='fixture'
            def fetch(self,target,reserve): return []
        self.assertEqual(self.store.process_one(Empty())['status'],'NO_COVERAGE')
        with db_connect(self.path) as conn:
            conn.execute("UPDATE camera_visual_archives SET status='FETCHING',lease='dead',lease_until=0,attempts=0")
        self.assertEqual(self.store.process_one(Empty())['status'],'NO_COVERAGE')
        with db_connect(self.path) as conn:
            conn.execute("UPDATE camera_visual_archives SET status='QUEUED',created_at=0")
        self.assertEqual(self.store.process_one()['status'],'EXPIRED')

    def test_budget_reserves_before_transport_and_is_not_refunded(self):
        with patch.dict(os.environ,CHAOS_CAMERA_MAX_REQUESTS='1'):
            self.store.reserve(100)
            with self.assertRaisesRegex(SourceError,'budget_deferred'): self.store.reserve(100)

    def test_measured_transfer_releases_capacity_once_on_original_day(self):
        with patch('camera_visual_archive.time.strftime',return_value='2026-11-02'):
            settle=self.store.reserve(100)
            self.store.reserve(50)  # failed/unsettled transfer remains charged
        with patch('camera_visual_archive.time.strftime',return_value='2026-11-03'):
            settle(20)
            settle(20)
        with self.assertRaises(ValueError): settle(101)
        with db_connect(self.path) as conn:
            row=conn.execute('SELECT * FROM camera_visual_budget').fetchone()
            self.assertEqual((row['day'],row['requests'],row['bytes_reserved']),('2026-11-02',2,70))

    def test_budget_fits_next_download_after_measured_settlement(self):
        with patch.dict(os.environ,CHAOS_CAMERA_MAX_BYTES='100'):
            settle=self.store.reserve(100)
            with self.assertRaises(SourceError): self.store.reserve(1)
            settle(10)
            self.store.reserve(90)
            with db_connect(self.path) as conn:
                row=conn.execute('SELECT * FROM camera_visual_budget').fetchone()
                self.assertEqual((row['requests'],row['bytes_reserved']),(2,100))

    def test_expiry_keeps_original_deferral_reason(self):
        self.enqueue()
        class BudgetBlocked:
            name='fixture'
            def fetch(self,target,reserve): raise SourceError('budget_deferred',86400)
        result=self.store.process_one(BudgetBlocked())
        self.assertEqual(result['reason'],'budget_deferred')
        with db_connect(self.path) as conn:
            conn.execute('UPDATE camera_visual_archives SET created_at=0')
        self.assertEqual(self.store.process_one()['status'],'EXPIRED')
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT reason FROM camera_visual_archives').fetchone()[0],
                             'job_deadline:budget_deferred')

    def test_selection_diagnostics_explain_rejected_photos(self):
        row=dict(id='123',geometry={'coordinates':[2.33050,48.86417]},
                 creator={'username':'fixture'},thumb_1024_url='https://cdn.invalid/photo')
        diagnostics={}
        self.assertEqual(select_images([{**row,'is_pano':True},
            {**row,'geometry':{'coordinates':[0,0]}},{**row,'creator':{}}],self.target,diagnostics),[])
        self.assertEqual(diagnostics,dict(returned=3,examined=3,panorama=1,distance=1,identity_or_author=1))

    def test_no_coverage_persists_safe_selection_counts_and_actual_metadata_bytes(self):
        raw=b'{"data": []}'
        with patch.dict(os.environ,CHAOS_CAMERA_SOURCE='mapillary',MAPILLARY_ACCESS_TOKEN='secret-fixture',
                        CHAOS_CAMERA_ACQUISITION='1',CHAOS_CAMERA_RETENTION_SECONDS='86400',
                        CHAOS_CAMERA_RIGHTS_REFERENCE='fixture',CHAOS_CAMERA_LICENSE='fixture',
                        CHAOS_CAMERA_LICENSE_URL='https://example.invalid/license'):
            self.enqueue()
            result=self.store.process_one(MapillarySource(lambda *a,**kw:(raw,'application/json')))
        self.assertEqual(result['status'],'NO_COVERAGE')
        self.assertEqual(json.loads(result['reason'].removeprefix('selection:')),
                         dict(returned=0,examined=0,selected=0))
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT reason FROM camera_visual_archives').fetchone()[0],result['reason'])
            self.assertEqual(conn.execute('SELECT bytes_reserved FROM camera_visual_budget').fetchone()[0],len(raw))

    def test_failed_metadata_transport_retains_full_reservation(self):
        def failure(*a,**kw): raise SourceError('source_deadline')
        with patch.dict(os.environ,MAPILLARY_ACCESS_TOKEN='fixture',CHAOS_CAMERA_ACQUISITION='1',
                        CHAOS_CAMERA_RIGHTS_REFERENCE='fixture',CHAOS_CAMERA_LICENSE='fixture',
                        CHAOS_CAMERA_LICENSE_URL='fixture'):
            with self.assertRaises(SourceError):
                MapillarySource(failure).fetch(self.target,self.store.reserve)
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT bytes_reserved FROM camera_visual_budget').fetchone()[0],1024*1024)

    def test_storage_quota_defers_before_fetch_and_does_not_block_other_jobs(self):
        first = self.enqueue()
        self.target['camera_id'] = 'camera-second'
        second = self.enqueue()
        with patch.dict(os.environ, CHAOS_CAMERA_MAX_STORAGE_BYTES='1'), patch.object(FixtureSource, 'fetch', side_effect=AssertionError('fetch before quota')):
            self.assertEqual(self.store.process_one()['status'], 'DEFERRED')
        result = self.store.process_one()
        self.assertEqual(result['archive_id'], second)
        self.assertEqual(result['status'], 'READY')
        self.assertEqual(self.manifest(first)['status'], 'DEFERRED')

    def test_low_disk_prevents_download(self):
        from collections import namedtuple
        self.enqueue()
        usage = namedtuple('Usage', 'total used free')(100, 99, 1)
        with patch('camera_visual_archive.shutil.disk_usage', return_value=usage), patch.object(FixtureSource, 'fetch', side_effect=AssertionError('fetch on full disk')):
            self.assertEqual(self.store.process_one()['status'], 'DEFERRED')

    def test_admin_retry_cannot_reset_backoff_and_actions_are_audited(self):
        key = self.enqueue()
        with self.assertRaisesRegex(ValueError, 'retry_not_due'):
            self.store.administer('admin', 'retry', key)
        with self.assertRaises(ValueError):
            self.store.administer('admin', 'withdraw', '123', '')
        self.store.administer('admin', 'withdraw', '123', 'withdrawal requested')
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM camera_visual_admin_audit').fetchone()[0], 1)

    def test_continuous_worker_collects_and_reports_without_manual_work_once(self):
        import subprocess
        import sys
        key=self.enqueue()
        cli=Path(__file__).resolve().parents[1]/'tools/camera_archive.py'
        result=subprocess.run([sys.executable,str(cli),'--db',self.path,'--action','work-loop',
                               '--apply','--cycles','1'],capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.manifest(key)['status'],'READY',result.stdout)
        with db_connect(self.path) as conn:
            health=json.loads(conn.execute("SELECT state_json FROM camera_visual_runtime WHERE role='archive'").fetchone()[0])
        self.assertEqual(health['status'],'READY')
        self.assertIn('gc_removed',health)

    def test_source_selection_direction_distance_and_missing_attribution(self):
        def row(i,heading=359,**kwargs):
            return dict(id=str(i),geometry={'coordinates':[2.33050,48.86417]},
                        creator={'username':'author'},compass_angle=heading,thumb_1024_url='https://cdn.invalid/test',**kwargs)
        chosen=select_images([row(1),row(2,1),row(3,180),row(4,is_pano=True)],self.target)
        self.assertEqual([r['id'] for r in chosen],['1','2'])
        self.assertEqual(select_images([{**row(1),'creator':{}},{**row(2),'geometry':{'coordinates':[0,0]}}],self.target),[])
        self.assertEqual(len(select_images([row(1,None),row(2,None)],self.target)),1)

    def test_mapillary_adapter_uses_fixtures_not_network(self):
        buffer=io.BytesIO(); Image.new('RGB',(1280,720),'gray').save(buffer,format='JPEG')
        calls=[]; reservations=[]; settlements=[]
        def reserve(size):
            reservations.append(size)
            return settlements.append
        def transport(url,**kwargs):
            calls.append((url,kwargs))
            if '/images?' in url:
                return json.dumps({'data':[dict(id='123',geometry={'coordinates':[2.33050,48.86417]},creator={'username':'fixture-author'},thumb_1024_url='https://cdn.invalid/photo')]}).encode(),'application/json'
            return buffer.getvalue(),'image/jpeg'
        with patch.dict(os.environ,MAPILLARY_ACCESS_TOKEN='fixture-token',CHAOS_CAMERA_ACQUISITION='1',
                        CHAOS_CAMERA_RIGHTS_REFERENCE='fixture-rights',CHAOS_CAMERA_LICENSE='fixture-license',CHAOS_CAMERA_LICENSE_URL='https://creativecommons.org/licenses/by-sa/4.0/'):
            images=MapillarySource(transport).fetch(self.target,reserve)
        self.assertEqual(len(images),1); self.assertEqual(len(calls),2)
        self.assertNotIn('fixture-token',calls[0][0]); self.assertNotIn('token',calls[1][1])
        self.assertNotIn('original',calls[0][0]); self.assertEqual(len(reservations),2)
        self.assertEqual(images[0][1]['author'],'fixture-author')
        self.assertEqual(len(settlements),2)
        self.assertEqual(settlements[1],len(buffer.getvalue()))
        self.assertLess(settlements[0],reservations[0])

    def test_ssrf_redirect_and_media_validation(self):
        for url in ('http://graph.mapillary.com/images','https://127.0.0.1/image','https://evil.invalid/image','https://user:pass@graph.mapillary.com/images'):
            with self.assertRaises(SourceError): get_bytes(url)
        with self.assertRaises(Exception): optimize(b'not an image')
        with self.assertRaises(SourceError): self.store.media_path({'file':'../../secret','sha256':'a'*64})

    def test_backup_restore_keeps_current_tombstone_and_budget(self):
        key=self.enqueue();self.store.process_one()
        image=self.manifest(key)['images'][0]
        backup=Path(self.tmp.name)/'backup'
        self.store.backup(backup)
        self.store.withdraw(image['source'],image['image_id'],'later decision')
        self.store.reserve(123)
        self.store.restore(backup)
        self.assertNotIn(image['image_id'],[i['image_id'] for i in self.manifest(key)['images']])
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT requests FROM camera_visual_budget').fetchone()[0],1)

    def test_parallel_workers_and_stale_fence(self):
        key=self.enqueue()
        store=self.store
        class Stale(FixtureSource):
            def fetch(self,target,reserve):
                self.busy=store.process_one()['status']
                with db_connect(store.path) as conn:
                    conn.execute("UPDATE camera_visual_archives SET lease='replacement' WHERE archive_id=?",(key,))
                return []
        source=Stale()
        self.assertEqual(store.process_one(source)['status'],'LEASE_LOST')
        self.assertEqual(source.busy,'BUSY')

    def test_rate_limit_is_deferred_without_browser_retry(self):
        self.enqueue()
        class RateLimited:
            name='fixture'
            def fetch(self,target,reserve): raise SourceError('source_http_429',600)
        self.assertEqual(self.store.process_one(RateLimited())['status'],'DEFERRED')
        self.assertEqual(self.store.process_one(RateLimited())['status'],'IDLE')

    def test_redirect_is_not_followed(self):
        from unittest.mock import MagicMock
        response=MagicMock(status=302);response.getheader.return_value='300'
        connection=MagicMock();connection.getresponse.return_value=response
        with patch('camera_visual_source.public_addresses',return_value=[(2,1,6,('8.8.8.8',443))]), patch('camera_visual_source.socket.socket'), patch('camera_visual_source.ssl.create_default_context'), patch('camera_visual_source.http.client.HTTPSConnection',return_value=connection):
            with self.assertRaisesRegex(SourceError,'source_http_302'):
                get_bytes('https://graph.mapillary.com/images')
        self.assertEqual(connection.request.call_count,1)


if __name__=='__main__': unittest.main()
