"""Shared camera materials, separate from player grants. Explicit CLI worker only."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import time

from database import db_connect, atomic_runtime_transaction
from camera_visual_source import SourceError, MapillarySource, optimize, distance

SCHEMAS = (
    '''CREATE TABLE IF NOT EXISTS camera_visual_archives (
    archive_id TEXT PRIMARY KEY,target_json TEXT NOT NULL,source TEXT NOT NULL,
    status TEXT NOT NULL,created_at REAL NOT NULL,updated_at REAL NOT NULL,
    lease TEXT NOT NULL DEFAULT '',lease_until REAL NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0,retry_at REAL NOT NULL DEFAULT 0,
    expires_at REAL NOT NULL DEFAULT 0,reason TEXT NOT NULL DEFAULT '',images_json TEXT NOT NULL DEFAULT '[]')''',
    'CREATE INDEX IF NOT EXISTS camera_archive_pending ON camera_visual_archives(status,retry_at,created_at)',
    '''CREATE TABLE IF NOT EXISTS camera_visual_withdrawals (
    source TEXT NOT NULL,image_id TEXT NOT NULL,reason TEXT NOT NULL,created_at REAL NOT NULL,
    PRIMARY KEY(source,image_id))''',
    '''CREATE TABLE IF NOT EXISTS camera_visual_budget (
    day TEXT PRIMARY KEY,requests INTEGER NOT NULL DEFAULT 0,bytes_reserved INTEGER NOT NULL DEFAULT 0)''',
)


def root():
    return Path(os.environ.get('CHAOS_CAMERA_ARCHIVE_DIR','data/camera_visual')).resolve()


def archive_key(target, source):
    # Shared by applications/players for the same stable camera and selection profile.
    identity = target.get('camera_id') or f"{float(target['lat']):.7f}:{float(target.get('lng',target.get('lon'))):.7f}"
    return hashlib.sha256(f'{source}:v1:{identity}:{target.get("heading", "unknown")}'.encode()).hexdigest()


class FixtureSource:
    name='fixture'

    def fetch(self,target,reserve):
        from camera_visual import IMAGES
        base=Path(__file__).parent/'assets/camera_visual/pilot_164_0/paris'
        result=[]
        for name in IMAGES:
            data,meta=optimize((base/name).read_bytes())
            result.append((data,{**meta,'image_id':name,'source':'AI_GENERATED_TEST',
                'author':'CHAOS / AI-generated','license':'Test material — no license assigned',
                'license_url':'','source_url':'','captured_at':None,
                'rights_reference':'local-fixture-only','photo_lat':None,'photo_lon':None,
                'distance_m':None,'heading':None,'sequence_id':None}))
        return result


class ArchiveStore:
    def __init__(self,path):
        self.path=path

    def enqueue(self,conn,target):
        source=os.environ.get('CHAOS_CAMERA_SOURCE','off')
        if source not in ('fixture','mapillary'):
            return None
        key=archive_key(target,source); now=time.time()
        target={k:target[k] for k in ('camera_id','lat','lng','lon','heading') if k in target}
        existing=conn.execute('SELECT * FROM camera_visual_archives WHERE archive_id=?',(key,)).fetchone()
        if existing:
            if existing['status'] in ('FAILED','NO_COVERAGE','EXPIRED','READY') and existing['expires_at']<=now and existing['retry_at']<=now:
                conn.execute("UPDATE camera_visual_archives SET status='QUEUED',created_at=?,updated_at=?,attempts=0,images_json='[]' WHERE archive_id=?",(now,now,key))
            return key
        if source=='mapillary':
            # Reuse only a bounded ready set whose actual photographs fit this
            # camera too. A geographic cell alone is not proof of coverage.
            for candidate in conn.execute("SELECT archive_id FROM camera_visual_archives WHERE source=? AND status='READY' AND expires_at>? ORDER BY updated_at DESC LIMIT 32",(source,now)):
                images=self.manifest(conn,candidate['archive_id'])['images']
                if images and all(i.get('photo_lat') is not None and i.get('photo_lon') is not None
                        and distance(float(target['lat']),float(target.get('lng',target.get('lon'))),i['photo_lat'],i['photo_lon'])<=100
                        and (target.get('heading') is None or (i.get('heading') is not None and abs((i['heading']-float(target['heading'])+180)%360-180)<=45)) for i in images):
                    return candidate['archive_id']
        if len(conn.execute("SELECT 1 FROM camera_visual_archives WHERE status IN ('QUEUED','FETCHING','DEFERRED') LIMIT 128").fetchall())>=128:
            return None
        conn.execute('''INSERT OR IGNORE INTO camera_visual_archives
            (archive_id,target_json,source,status,created_at,updated_at) VALUES (?,?,?,'QUEUED',?,?)''',
            (key,json.dumps(target,ensure_ascii=False),source,now,now))
        return key

    def manifest(self,conn,key):
        row=conn.execute('SELECT * FROM camera_visual_archives WHERE archive_id=?',(key,)).fetchone()
        if not row:
            return {'status':'NO_COVERAGE','images':[]}
        status=row['status']
        if status in ('QUEUED','FETCHING','DEFERRED') and row['created_at']+900<time.time():
            status='EXPIRED'
        if status=='READY' and row['expires_at']<=time.time():
            status='EXPIRED'
        if row['source']=='mapillary' and (os.environ.get('CHAOS_CAMERA_SERVE')!='1' or not os.environ.get('CHAOS_CAMERA_RIGHTS_REFERENCE')):
            status='DEFERRED'
        images=[]
        if status=='READY':
            for item in json.loads(row['images_json']):
                if not conn.execute('SELECT 1 FROM camera_visual_withdrawals WHERE source=? AND image_id=?',
                                    (item['source'],item['image_id'])).fetchone():
                    images.append(item)
            if not images:
                status='REVOKED'
        return {'archive_id':key,'status':status,'images':images,'reason':row['reason']}

    def reserve(self,size):
        day=time.strftime('%Y-%m-%d',time.gmtime())
        with atomic_runtime_transaction(self.path) as conn:
            conn.execute('INSERT OR IGNORE INTO camera_visual_budget(day) VALUES (?)',(day,))
            row=conn.execute('SELECT * FROM camera_visual_budget WHERE day=?',(day,)).fetchone()
            if row['requests']>=int(os.environ.get('CHAOS_CAMERA_MAX_REQUESTS','100')) or row['bytes_reserved']+size>int(os.environ.get('CHAOS_CAMERA_MAX_BYTES',str(100*1024*1024))):
                raise SourceError('budget_deferred',86400)
            conn.execute('UPDATE camera_visual_budget SET requests=requests+1,bytes_reserved=bytes_reserved+? WHERE day=?',(size,day))

    def process_one(self,source=None):
        if os.environ.get('CHAOS_CAMERA_WORKER')!='1':
            return {'status':'OFF'}
        now=time.time(); fence=secrets.token_hex(16)
        with atomic_runtime_transaction(self.path) as conn:
            conn.execute("UPDATE camera_visual_archives SET status='EXPIRED' WHERE archive_id IN (SELECT archive_id FROM camera_visual_archives WHERE status='READY' AND expires_at<=? LIMIT 64)",(now,))
            if conn.execute("SELECT 1 FROM camera_visual_archives WHERE status='FETCHING' AND lease_until>? LIMIT 1",(now,)).fetchone():
                return {'status':'BUSY'}
            row=conn.execute('''SELECT * FROM camera_visual_archives
                WHERE (status IN ('QUEUED','DEFERRED') AND retry_at<=?)
                    OR (status='FETCHING' AND lease_until<?)
                    OR (status IN ('QUEUED','DEFERRED') AND created_at<?)
                ORDER BY created_at LIMIT 1''',(now,now,now-900)).fetchone()
            if not row:
                return {'status':'IDLE'}
            key=row['archive_id']
            if now-row['created_at']>900 or row['attempts']>=2:
                conn.execute("UPDATE camera_visual_archives SET status='EXPIRED',reason='job_deadline' WHERE archive_id=?",(key,))
                return {'status':'EXPIRED'}
            if conn.execute("SELECT count(*) FROM camera_visual_archives WHERE status='READY'").fetchone()[0]>=int(os.environ.get('CHAOS_CAMERA_MAX_ARCHIVES','10')):
                conn.execute("UPDATE camera_visual_archives SET status='DEFERRED',retry_at=?,reason='archive_quota' WHERE archive_id=?",(now+3600,key))
                return {'status':'DEFERRED'}
            conn.execute("UPDATE camera_visual_archives SET status='FETCHING',lease=?,lease_until=?,attempts=attempts+1,updated_at=? WHERE archive_id=?",(fence,now+120,now,key))
        images=[]; status='FAILED'; reason=''; retry=0
        try:
            provider=source or (FixtureSource() if row['source']=='fixture' else MapillarySource())
            if provider.name!=row['source']:
                raise SourceError('source_mismatch')
            retention=int(os.environ.get('CHAOS_CAMERA_RETENTION_SECONDS','0')) if row['source']=='mapillary' else 86400
            if retention<=0:
                raise SourceError('retention_unapproved')
            directory=root(); directory.mkdir(parents=True,exist_ok=True)
            if shutil.disk_usage(directory).free<100*1024*1024:
                raise SourceError('disk_low')
            payloads=provider.fetch(json.loads(row['target_json']),self.reserve)
            if len(payloads)>3:
                raise SourceError('image_count_limit')
            for data,meta in payloads:
                if not meta.get('author') or not meta.get('license') or not meta.get('rights_reference'):
                    raise SourceError('attribution_incomplete')
                if row['source']=='mapillary' and (not meta.get('license_url') or not meta.get('source_url')):
                    raise SourceError('attribution_incomplete')
                digest=hashlib.sha256(data).hexdigest()
                if digest!=meta['sha256']:
                    raise SourceError('checksum_invalid')
                name=digest+'.webp'; temporary=directory/(name+'.'+fence+'.tmp')
                with temporary.open('xb') as handle:
                    handle.write(data); handle.flush(); os.fsync(handle.fileno())
                os.replace(temporary,directory/name)
                images.append({**meta,'file':name,'acquired_at':time.time()})
            status='READY' if images else 'NO_COVERAGE'
            if not images:
                retry=3600
        except SourceError as exc:
            reason=str(exc); retry=exc.retry_after
            status='DEFERRED' if row['attempts']<1 else 'FAILED'
        except Exception:
            # Neither URLs, tokens nor upstream bodies belong in public diagnostics.
            reason='source_processing_failed'; retry=300
            status='DEFERRED' if row['attempts']<1 else 'FAILED'
        with atomic_runtime_transaction(self.path) as conn:
            if status=='READY':
                if row['source']=='mapillary' and (os.environ.get('CHAOS_CAMERA_ACQUISITION')!='1' or not os.environ.get('CHAOS_CAMERA_RIGHTS_REFERENCE')):
                    status='DEFERRED'; reason='policy_changed'; images=[]; retry=300
                else:
                    images=[i for i in images if not conn.execute('SELECT 1 FROM camera_visual_withdrawals WHERE source=? AND image_id=?',(i['source'],i['image_id'])).fetchone()]
                    if not images:
                        status='REVOKED'
            changed=conn.execute('''UPDATE camera_visual_archives SET status=?,reason=?,images_json=?,
                expires_at=?,updated_at=?,retry_at=?,lease='',lease_until=0 WHERE archive_id=? AND lease=? AND lease_until>?''',
                (status,reason,json.dumps(images),time.time()+retention if status=='READY' else 0,
                 time.time(),time.time()+retry,key,fence,time.time())).rowcount
        return {'status':status if changed else 'LEASE_LOST','archive_id':key,'images':len(images)}

    def withdraw(self,source,image_id,reason):
        with atomic_runtime_transaction(self.path) as conn:
            conn.execute('INSERT OR REPLACE INTO camera_visual_withdrawals VALUES (?,?,?,?)',
                         (source,image_id,reason[:200],time.time()))

    def media_path(self,item):
        name=item.get('file','')
        if name!=item.get('sha256','')+'.webp' or len(item.get('sha256',''))!=64 or any(c not in '0123456789abcdef' for c in item.get('sha256','')):
            raise SourceError('media_path_invalid')
        path=root()/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise SourceError('media_checksum_invalid')
        return path

    def gc(self):
        """Bounded unreferenced files only, with a grace period for in-flight publish."""
        with db_connect(self.path) as conn:
            referenced={i['file'] for row in conn.execute("SELECT images_json FROM camera_visual_archives WHERE status='READY' AND expires_at>?",(time.time(),)) for i in json.loads(row['images_json'])
                        if not conn.execute('SELECT 1 FROM camera_visual_withdrawals WHERE source=? AND image_id=?',(i['source'],i['image_id'])).fetchone()}
        removed=0
        for path in list(root().glob('*'))[:256]:
            if path.is_file() and path.name not in referenced and path.stat().st_mtime<time.time()-3600:
                path.unlink(); removed+=1
        return removed

    def backup(self,destination):
        """Private archive-only backup; no player grants or profile data."""
        destination=Path(destination)
        destination.mkdir(parents=True,exist_ok=False)
        with db_connect(self.path) as conn:
            rows=[dict(r) for r in conn.execute('SELECT * FROM camera_visual_archives LIMIT 1001')]
            if len(rows)>1000: raise SourceError('backup_requires_larger_operator_batch')
            withdrawals=[dict(r) for r in conn.execute('SELECT * FROM camera_visual_withdrawals')]
            budgets=[dict(r) for r in conn.execute('SELECT * FROM camera_visual_budget')]
        for row in rows:
            for item in json.loads(row['images_json']):
                source=root()/item['file']
                if source.exists():
                    shutil.copyfile(self.media_path(item),destination/item['file'])
        (destination/'manifest.json').write_text(json.dumps({'version':1,'archives':rows,
            'withdrawals':withdrawals,'budgets':budgets}),encoding='utf-8')
        return len(rows)

    def restore(self,directory):
        """Additive restore: current withdrawals, grants and budgets never roll back."""
        directory=Path(directory)
        raw=(directory/'manifest.json').read_bytes()
        if len(raw)>10*1024*1024: raise SourceError('backup_manifest_limit')
        snapshot=json.loads(raw)
        if snapshot.get('version')!=1: raise SourceError('backup_version')
        media=root();media.mkdir(parents=True,exist_ok=True)
        for row in snapshot['archives']:
            for item in json.loads(row['images_json']):
                name=item['sha256']+'.webp'
                if item['file']!=name or len(item['sha256'])!=64 or any(c not in '0123456789abcdef' for c in item['sha256']):
                    raise SourceError('backup_path')
                source=directory/name
                if not source.exists(): continue # Expired/withdrawn data may have been purged.
                if hashlib.sha256(source.read_bytes()).hexdigest()!=item['sha256']: raise SourceError('backup_checksum')
                temporary=media/(name+'.restore.tmp');shutil.copyfile(source,temporary);os.replace(temporary,media/name)
        with atomic_runtime_transaction(self.path) as conn:
            for item in snapshot['withdrawals']:
                conn.execute('INSERT OR IGNORE INTO camera_visual_withdrawals VALUES (?,?,?,?)',
                             (item['source'],item['image_id'],item['reason'],item['created_at']))
            for item in snapshot['budgets']:
                conn.execute('''INSERT INTO camera_visual_budget VALUES (?,?,?) ON CONFLICT(day) DO UPDATE SET
                    requests=max(requests,excluded.requests),bytes_reserved=max(bytes_reserved,excluded.bytes_reserved)''',
                    (item['day'],item['requests'],item['bytes_reserved']))
            columns=['archive_id','target_json','source','status','created_at','updated_at','lease','lease_until','attempts','retry_at','expires_at','reason','images_json']
            for row in snapshot['archives']:
                conn.execute('INSERT OR IGNORE INTO camera_visual_archives ('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')',tuple(row[k] for k in columns))
        return len(snapshot['archives'])
