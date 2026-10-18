"""Export the current scanner's queries into a standalone Linux reference test."""
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from poiFetchClass import POIFetcher

RUNNER = '''import hashlib, json, pathlib, subprocess
root = pathlib.Path('/test')
work = root / 'result'
work.mkdir()  # Refuse to overwrite earlier evidence.
db = work / 'db'
db.mkdir()
source = root / 'geometry_source.osm'
updater = pathlib.Path('/app/bin/update_database')
query_bin = pathlib.Path('/app/bin/osm3s_query')
def run(command, data, seconds, name):
    result = subprocess.run(command, input=data, capture_output=True, timeout=seconds)
    (work / (name + '.stderr')).write_bytes(result.stderr)
    result.check_returncode()
    return result.stdout
run([str(updater), '--db-dir='+str(db), '--version=chaos-synthetic-v1'], source.read_bytes(), 120, 'import')
cases = json.loads((root / 'queries.json').read_text())
for name, case in cases.items():
    payload = json.loads(run([str(query_bin), '--db-dir='+str(db), '--concise'], case['query'].encode(), 30, name))
    if payload.get('remark') or not isinstance(payload.get('elements'), list):
        raise RuntimeError('Incomplete answer: '+name)
    case['response'] = payload
    print(name, 'elements:', len(payload['elements']), flush=True)
manifest = dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    query_binary_sha256=hashlib.sha256(query_bin.read_bytes()).hexdigest(),
    updater_binary_sha256=hashlib.sha256(updater.read_bytes()).hexdigest(), cases=cases)
(work / 'reference.json').write_text(json.dumps(manifest, indent=2))
print('PASS: six reference answers captured; geometry parity still requires comparison.')
'''


def main():
    output = ROOT / 'artifacts' / 'poi-geometry-160.zip'
    profile = POIFetcher(tag_filters=['shop', 'amenity', 'office', 'healthcare', 'atm=yes', 'man_made=surveillance'])
    cases = {}
    for name, lat, lon, radius in [('origin', 0, 0, 300), ('nearby', 0, .001, 300),
                                   ('edge', 0, .002, 300), ('small', 0, 0, 100),
                                   ('empty', 1, 1, 300), ('larger', 0, 0, 600)]:
        profile.radius = radius
        cases[name] = dict(lat=lat, lon=lon, radius=radius, query=profile._build_query(lat, lon))
    compile(RUNNER, 'reference.py', 'exec')
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(ROOT / 'tests/fixtures/poi/geometry_source.osm', 'geometry_source.osm')
        bundle.writestr('queries.json', json.dumps(cases, indent=2))
        bundle.writestr('reference.py', RUNNER)
    print(output)


if __name__ == '__main__':
    main()
