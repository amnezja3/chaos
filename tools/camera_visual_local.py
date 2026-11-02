"""Run the real Flask desktop and operation tick on the isolated pilot copy.

No substitute UI, result selector, authentication bypass or time-warp endpoint.
"""
import argparse
import os
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8998)
    parser.add_argument('--system-test', action='store_true',
                        help='Isolated main: marked world camera, fixture material, Insider Feed, 180s base download')
    args = parser.parse_args()
    work = ROOT / 'instance/cvn-gameplay-164'
    database = work / 'data/game.sqlite3'
    if not database.is_file():
        parser.error('Missing isolated database copy: ' + str(database))
    os.environ['CHAOS_DB_PATH'] = str(database)
    os.environ['CHAOS_SESSION_FILE_DIR'] = str(work / 'sessions')
    os.environ['CHAOS_CAMERA_VISUAL_PILOT'] = '1'
    os.environ['CHAOS_CAMERA_VISUAL_PILOT_USER'] = 'main'
    os.chdir(work)
    sys.path.insert(0, str(ROOT))
    import run
    if args.system_test:
        # Test data only in the fixed isolated copy above. No grant, receipt,
        # completed operation or ability window is fabricated.
        from database import PlayerMarkedTargetStore
        from response_network.camera_contract import camera_marker
        from ghostnetwork import GhostCycleService
        os.environ.update(CHAOS_CAMERA_STREET_VIEW='1', CHAOS_CAMERA_VISUAL_PILOT='0',
                          CHAOS_CAMERA_SOURCE='fixture', CHAOS_CAMERA_WORKER='1',
                          CHAOS_CAMERA_ARCHIVE_DIR=str(work / 'data/system-camera-material'))
        run.GHOSTNETWORK_ABILITIES_ENABLED = True
        run.DEFAULT_OPERATION_DURATIONS_SECONDS['camera_stream'] = 180
        run.user_store.patch_profile_guarded('main',
            dict(ghost_clan_code='virex', clan='virex', ghost_profession='broker', level=60),
            source='test.camera.system.local')
        repository = run.get_ghostnetwork_service().repository
        cycle = GhostCycleService(repository=repository).ensure_active_cycle()['cycle']
        part = next(p for p in repository.list_parts(cycle['cycle_id']) if p['part_code'] == 'V1')
        repository.update_part(part['part_id'], status='active', target_id='local-system-power',
            latitude=50, longitude=20, discovered_by='main', discovered_clan='virex',
            conflict_state='none', frozen_status='', conflict_id='', territory_id='local-power-area',
            territory_owner_id='main', territory_clan='virex')
        marker = camera_marker(dict(lat=50, lng=20, osm_id='local-system-shop', name='System test shop'))
        marker.update(security={'firewall':False}, actions_allowed={'camera_stream':True})
        PlayerMarkedTargetStore(str(database)).upsert('main', marker)
        run.player_position_store.upsert('main', dict(lat=50, lng=20))
        run.player_target_runtime_store.upsert_aimed('main', marker)
    # Flask resolves templates/static from run.py; mutable relative paths stay
    # inside the isolated working directory, including other subsystem databases.
    stop = threading.Event()

    def tick():
        while not stop.wait(2):
            try:
                run.process_operation_runtime_tick()
                if args.system_test:
                    from camera_visual_archive import ArchiveStore
                    ArchiveStore(str(database)).process_one()
            except Exception as error:
                print('PILOT tick failed: ' + type(error).__name__ + ': ' + str(error), flush=True)

    worker = threading.Thread(target=tick, name='local-operation-tick', daemon=True)
    worker.start()
    try:
        run.app.run(host='127.0.0.1', port=args.port, debug=False, use_reloader=False)
    finally:
        stop.set()
        worker.join(timeout=5)


if __name__ == '__main__':
    main()
