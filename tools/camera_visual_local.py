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
    # Flask resolves templates/static from run.py; mutable relative paths stay
    # inside the isolated working directory, including other subsystem databases.
    stop = threading.Event()

    def tick():
        while not stop.wait(2):
            try:
                run.process_operation_runtime_tick()
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
