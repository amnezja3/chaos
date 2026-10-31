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
        calls=[]; reservations=[]
        def transport(url,**kwargs):
            calls.append((url,kwargs))
            if '/images?' in url:
                return json.dumps({'data':[dict(id='123',geometry={'coordinates':[2.33050,48.86417]},creator={'username':'fixture-author'},thumb_1024_url='https://cdn.invalid/photo')]}).encode(),'application/json'
            return buffer.getvalue(),'image/jpeg'
        with patch.dict(os.environ,MAPILLARY_ACCESS_TOKEN='fixture-token',CHAOS_CAMERA_ACQUISITION='1',
                        CHAOS_CAMERA_RIGHTS_REFERENCE='fixture-rights',CHAOS_CAMERA_LICENSE='fixture-license',CHAOS_CAMERA_LICENSE_URL='https://creativecommons.org/licenses/by-sa/4.0/'):
            images=MapillarySource(transport).fetch(self.target,reservations.append)
        self.assertEqual(len(images),1); self.assertEqual(len(calls),2)
        self.assertNotIn('fixture-token',calls[0][0]); self.assertNotIn('token',calls[1][1])
        self.assertNotIn('original',calls[0][0]); self.assertEqual(len(reservations),2)
        self.assertEqual(images[0][1]['author'],'fixture-author')

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
