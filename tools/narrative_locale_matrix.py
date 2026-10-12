"""Run every canary once, record failures, never publish or retry until success."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def run_matrix(db, snapshot, report_path, generate=False):
    rows = json.loads(Path(snapshot).read_text())
    worker = next(r['pm2_env'] for r in rows if r['name']=='chaos-ollama-worker')
    saved = {**worker.get('env', {}), **worker}
    env = os.environ.copy()
    env.update({k:str(v) for k,v in saved.items()
                if k.startswith('CHAOS_') and isinstance(v,(str,int,float))})
    if generate and not env.get('CHAOS_MISTRAL_API_KEY','').strip():
        raise ValueError('worker_secret_missing')
    results = []
    # Reserve the report before spending any tokens. Never overwrite a prior run.
    fd = os.open(report_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as report:
        for provider in ('mistral','ollama'):
            for locale in ('pl','en'):
                for medium in ('blacknet','cyberner','googleplex_news'):
                    command = [sys.executable, str(Path(__file__).with_name('narrative_locale_canary.py')),
                               '--db',str(db),'--provider',provider,'--locale',locale,'--medium',medium]
                    if generate:
                        command += ['--generate','--show-text']
                    print(f'TEST: {provider} / {locale} / {medium}', flush=True)
                    completed = subprocess.run(command, env=env, capture_output=True, text=True, encoding='utf-8')
                    try:
                        result = json.loads(completed.stdout)
                    except ValueError:
                        result = {'ok':False,'error':'canary_process_failed','exit_code':completed.returncode}
                    result['requested_provider'] = provider
                    result['locale'] = locale
                    result['medium'] = medium
                    if completed.returncode:
                        result['ok'] = False
                    results.append(result)
                    report.seek(0)
                    json.dump(results, report, ensure_ascii=False, indent=2)
                    report.truncate()
                    report.flush()
                    print(json.dumps(result, ensure_ascii=False), flush=True)
    passed = sum(r.get('ok') is True for r in results)
    print(json.dumps({'passed':passed,'failed':len(results)-passed,'report':str(report_path)}))
    return 0 if passed == len(results) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True, type=Path)
    parser.add_argument('--pm2-snapshot', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--generate', action='store_true')
    args = parser.parse_args()
    if not args.db.is_file():
        parser.error('Database must already exist.')
    return run_matrix(args.db,args.pm2_snapshot,args.report,args.generate)


if __name__ == '__main__':
    sys.exit(main())
