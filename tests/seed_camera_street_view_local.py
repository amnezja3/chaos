"""Create a NEW completed grant on the dedicated local copy using a controlled clock.

Never resets/reopens an old grant. Not a production command or HTTP endpoint.
"""
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch
import uuid

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'instance/cvn-gameplay-164'
os.environ['CHAOS_DB_PATH']=str(WORK/'data/game.sqlite3')
os.environ['CHAOS_SESSION_FILE_DIR']=str(WORK/'sessions')
os.environ['CHAOS_CAMERA_VISUAL_PILOT']='1'
os.environ['CHAOS_CAMERA_SOURCE']='fixture'
os.environ['CHAOS_CAMERA_WORKER']='1'
os.chdir(WORK);sys.path.insert(0,str(ROOT))
import run
from database import db_connect
from camera_visual import CameraVisual
from camera_visual_archive import ArchiveStore

service=CameraVisual(run)
with db_connect(service.path) as conn:
    target=service.target(conn,'main')
    app=service.app(conn,'main','admin_seed_camera_stream_v1')
original=dict(target)
target={**target,'security':dict(target.get('security') or {})}
for key in app.get('requires_off',[]):
    target['security'][key]=False
run.player_target_runtime_store.upsert_aimed('main',target)
receipt='local-browser-'+uuid.uuid4().hex
now=time.time()
try:
    with patch('camera_visual.time.time',return_value=now-1810):
        response=service.result('main',dict(app_id=app['id'],expected_target=target,
            launch_receipt=receipt,launch_source='desktop_menu'))
        if not response['success'] or response.get('duplicate'):
            raise RuntimeError('New isolated test grant required')
        archive=ArchiveStore(service.path).process_one()
        if archive['status'] not in ('READY','IDLE'):raise RuntimeError(archive)
    operation=run.refresh_operation_runtime(response['created_operations'][0],now_ts=now)
    run.player_operation_store.upsert_operations('main',[operation])
    run.finalize_operation_files_bounded('main',operation)
    service.finalize('main',operation)
    print(json.dumps({'receipt':receipt,'state':service.snapshot('main')[0]['state'],
                      'controlled_clock':True,'duration_seconds':operation['duration_seconds']}))
finally:
    run.player_target_runtime_store.upsert_aimed('main',original)
