"""Two sequential, pinned-IP diagnostics; no gameplay/provider activation."""
import argparse
import hashlib
import ipaddress
import json
import multiprocessing
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from poiFetchClass import POIFetcher
from poi_infrastructure.providers import Registry
from poi_infrastructure.repository import Repository
from poi_infrastructure.secure_transport import public_addresses, request
from poi_infrastructure.service import Config, POIError, validate, retry_delay

DEADLINE = 35
UA = 'CHAOS/POI-v160 (+https://chaos.re; year2108@chaos.re)'


def summarize(status, data):
    if status != 200:
        return dict(validated=False)
    validate(data, Config())
    return dict(validated=True, elements=len(data['elements']))


def python_child(pipe, url, query, ip, deadline):
    trace = {}
    result = dict(transport='python')
    try:
        status, retry, data = request(Config(diagnostic_errors=True), url, query,
            DEADLINE, deadline, pinned_ip=ip, trace=trace)
        result.update(http_status=status, retry_after=retry, **summarize(status,data))
        if status != 200:
            result['diagnostic'] = data
    except Exception as exc:
        result['error'] = str(exc) if isinstance(exc, POIError) else type(exc).__name__
    finally:
        result['trace'] = trace
        pipe.send(result)
        pipe.close()


def python_request(url, query, ip):
    ctx = multiprocessing.get_context('spawn')
    parent, child = ctx.Pipe(duplex=False)
    started = time.monotonic()
    process = ctx.Process(target=python_child,args=(child,url,query,ip,started+DEADLINE))
    try:
        process.start()
        child.close()
        if parent.poll(max(0,started+DEADLINE-time.monotonic())):
            try:
                result = parent.recv()
            except EOFError:
                result = dict(transport='python',error='child_failed')
        else:
            result = dict(transport='python',error='hard_deadline',trace_unavailable=True)
        return dict(result,total_seconds=round(time.monotonic()-started,4))
    finally:
        parent.close()
        child.close()
        if process.pid is not None:
            process.join(.1)
            if process.is_alive():
                process.terminate()
                process.join(1)
            if process.is_alive():
                process.kill()
                process.join(1)
            process.close()


def curl_request(url, query, ip):
    host = urlsplit(url).hostname
    with tempfile.TemporaryDirectory(prefix='chaos-poi-compare-') as directory:
        path = Path(directory)
        (path/'request').write_bytes(urlencode({'data':query}).encode())
        command = ['curl','--noproxy','*','--http1.1','--resolve',f'{host}:443:{ip}',
            '--connect-timeout','3','--max-time',str(DEADLINE),'--max-filesize','4194304',
            '--silent','--show-error','-A',UA,'-H','Accept: application/json',
            '-H','Accept-Encoding: identity','-H','Content-Type: application/x-www-form-urlencoded',
            '--data-binary','@'+str(path/'request'),'-o',str(path/'body'),
            '-D',str(path/'headers'),'-w','%{json}',url]
        try:
            completed = subprocess.run(command,capture_output=True,text=True,timeout=DEADLINE+2)
        except subprocess.TimeoutExpired:
            return dict(transport='curl',error='hard_deadline')
        try:
            meta = json.loads(completed.stdout)
        except ValueError:
            meta = {}
        result = dict(transport='curl',exit_code=completed.returncode,
            http_status=meta.get('http_code'), remote_ip=meta.get('remote_ip'),
            first_byte_seconds=meta.get('time_starttransfer'),total_seconds=meta.get('time_total'),
            tcp_seconds=meta.get('time_connect'),tls_seconds=meta.get('time_appconnect'))
        if completed.returncode:
            result['error'] = completed.stderr[:500]
        if (path/'headers').exists():
            for line in (path/'headers').read_text(errors='replace').splitlines():
                if line.lower().startswith('retry-after:'):
                    result['retry_after'] = line.split(':',1)[1].strip()
        if (path/'body').exists():
            raw = (path/'body').read_bytes()
            if result['http_status'] == 200 and completed.returncode == 0:
                try:
                    result.update(summarize(200,json.loads(raw)))
                except (ValueError,POIError) as exc:
                    result['error'] = str(exc)[:200]
            else:
                result['body_excerpt'] = raw[:2048].decode(errors='replace')
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default=str(ROOT/'data/poi_cache.sqlite3'))
    parser.add_argument('--ip',default='95.163.216.90')
    parser.add_argument('--execute',action='store_true')
    args = parser.parse_args()
    try:
        if ipaddress.ip_address(args.ip).version != 4:
            raise ValueError()
    except ValueError:
        raise POIError('diagnostic_requires_ipv4')
    if not Path(args.db).is_file() or not shutil.which('curl'):
        raise POIError('existing_poi_db_and_curl_required')
    repo = Repository(args.db)
    registry = Registry(repo)
    candidate = next((p for p in registry.list() if p['id']=='overpass-vk'),None)
    if not candidate or not Registry.approved(candidate,'small_probe'):
        raise POIError('successful_approved_probe_required')
    url = candidate['url']
    host = urlsplit(url).hostname
    if args.ip not in [r[3][0] for r in public_addresses(host)]:
        raise POIError('pinned_ip_not_in_public_dns')
    query = POIFetcher(radius=300,tag_filters=['shop','amenity','office','healthcare',
        'atm=yes','man_made=surveillance'])._build_query(52.2319,21.0067).replace('[timeout:15]','[timeout:25]')
    print(json.dumps(dict(status='plan',ip=args.ip,order=['python','curl'],http_version='1.1',
        query_sha256=hashlib.sha256(query.encode()).hexdigest(),deadline_per_request=DEADLINE,
        query_timeout=25, max_network_calls=2, gameplay_configuration_unchanged=True)),flush=True)
    if not args.execute:
        return
    group = candidate['operator_group']
    if not repo.allowed(group):
        raise POIError('circuit_open')
    # Same diagnostic rate lease as single-scan CLI. No bypass on variant changes.
    if not repo.acquire('@controlled-scan-rate:'+group,900):
        raise POIError('controlled_scan_rate_limited')
    for transport in (python_request,curl_request):
        current = next((p for p in registry.list() if p['id']==candidate['id']),None)
        if current != candidate or not repo.allowed(group):
            raise POIError('provider_changed_or_circuit_open')
        slot = repo.acquire('@upstream',42,probe_group=group)
        if not slot:
            raise POIError('upstream_busy')
        started = time.monotonic()
        try:
            result = transport(url,query,args.ip)
            print(json.dumps(result),flush=True)
            registry.record_health(candidate['id'],candidate['revision'],
                'compare_'+result['transport'],result.get('error') or str(result.get('http_status')),
                time.monotonic()-started)
        finally:
            try:
                repo.release('@probe:'+group,slot)
            finally:
                repo.release('@upstream',slot)
        if result.get('retry_after') or result.get('http_status') == 429:
            repo.outcome(group,False,retry_delay(result.get('retry_after')) or 30)
            print(json.dumps(dict(status='stopped',reason='provider_retry_after_or_429')),flush=True)
            break


if __name__ == '__main__':
    try:
        main()
    except POIError as exc:
        print(json.dumps(dict(ok=False,error=str(exc))))
        raise SystemExit(1)
