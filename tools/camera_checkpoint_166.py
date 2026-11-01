"""Read-only bounded evidence for one camera; no provider calls or gameplay writes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from camera_visual_archive import archive_key
from camera_visual_source import distance


def report(db, archive_dir, username, camera_id):
    now = time.time()
    conn = sqlite3.connect(Path(db).resolve().as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA query_only=ON')
    try:
        row = conn.execute('''SELECT scan_id,marker_json,expires_at FROM response_camera_observations
            WHERE username=? AND camera_id=? ORDER BY expires_at DESC LIMIT 1''', (username,camera_id)).fetchone()
        if not row:
            return {'camera_id':camera_id,'status':'SCAN_REQUIRED','read_only':True}
        target = json.loads(row['marker_json'])
        lat, lon = target['lat'], target.get('lng',target.get('lon'))
        out = dict(camera_id=camera_id, coordinates=f'{lat}:{lon}',
            parent_target_id=target.get('parent_target_id'), label=target.get('label'),
            scan_id=row['scan_id'], scan_current=row['expires_at']>now,
            exact_archive_key=archive_key(target,'mapillary'), timestamp=now, read_only=True)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'camera_visual_archives' not in tables:
            return {**out,'archive_schema':False}
        grants = [dict(r) for r in conn.execute('''SELECT operation_id,receipt,viewer_closed,
            json_extract(payload_json,'$.success') AS server_success,
            json_extract(payload_json,'$.archive_id') AS archive_id
            FROM camera_visual_sessions WHERE username=? AND
            json_extract(payload_json,'$.target.camera_id')=? ORDER BY created_at DESC LIMIT 5''', (username,camera_id))]
        keys = list(dict.fromkeys([out['exact_archive_key']] + [g['archive_id'] for g in grants if g['archive_id']]))
        out['grants'] = grants
        root = Path(archive_dir).resolve()
        out['disk_free_bytes'] = shutil.disk_usage(root if root.exists() else root.parent).free
        out['archives'] = []
        for key in keys:
            archive = conn.execute('SELECT * FROM camera_visual_archives WHERE archive_id=?',(key,)).fetchone()
            if not archive:
                continue
            item = {k:archive[k] for k in ('archive_id','source','status','reason','attempts','created_at','updated_at','expires_at')}
            item['images'] = []
            for meta in json.loads(archive['images_json']):
                image = {k:meta.get(k) for k in ('image_id','source','author','license','format','width','height','bytes','changes')}
                # Same private path convention as ArchiveStore.media; never follow arbitrary metadata paths.
                digest = meta.get('sha256','')
                filename = digest + '.webp'
                path = (root / filename).resolve()
                image['checksum'] = 'MISSING'
                if len(digest)==64 and all(c in '0123456789abcdef' for c in digest) and meta.get('file')==filename and path.is_relative_to(root) and path.is_file():
                    image['checksum'] = 'OK' if hashlib.sha256(path.read_bytes()).hexdigest()==meta.get('sha256') else 'MISMATCH'
                item['images'].append(image)
            out['archives'].append(item)
        # Report nearby potential reuse before testing; never delete archives to force a miss.
        out['nearby_ready_archives'] = []
        for a in conn.execute("SELECT archive_id,images_json FROM camera_visual_archives WHERE source='mapillary' AND status='READY' AND expires_at>? ORDER BY updated_at DESC LIMIT 32",(now,)):
            images = json.loads(a['images_json'])
            if images and all(i.get('photo_lat') is not None and i.get('photo_lon') is not None and distance(lat,lon,i['photo_lat'],i['photo_lon'])<=100 for i in images):
                out['nearby_ready_archives'].append(a['archive_id'])
        out['budget'] = [dict(r) for r in conn.execute('SELECT * FROM camera_visual_budget ORDER BY day DESC LIMIT 2')]
        out['heartbeats'] = [{'role':r['role'],'age_seconds':round(now-r['updated_at'])} for r in conn.execute('SELECT role,updated_at FROM camera_visual_runtime')]
        for grant in grants:
            op = conn.execute('SELECT status FROM player_operations WHERE username=? AND operation_id=?',(username,grant['operation_id'])).fetchone()
            grant['operation_status'] = op['status'] if op else None
            grant['activator_exists'] = bool(grant['operation_id'] and conn.execute('SELECT 1 FROM player_data_files WHERE username=? AND operation_id=? AND file_id=?',(username,grant['operation_id'],'activation-'+grant['operation_id'])).fetchone())
        return out
    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--archive-dir', required=True)
    parser.add_argument('--username', default='main')
    parser.add_argument('--camera-id', required=True)
    args = parser.parse_args()
    print(json.dumps(report(args.db,args.archive_dir,args.username,args.camera_id),ensure_ascii=False,indent=2))
