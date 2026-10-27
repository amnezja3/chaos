"""Prepare a small versioned Natural Earth mask offline; no DB or network."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.natural_earth_region import extract,VERSION,SOURCE,SOURCE_SHA256,LICENSE
from tools.world_land_water_inspect import inspect


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True)
    p.add_argument('--bbox',type=float,nargs=4,required=True)
    p.add_argument('--output',required=True)
    args=p.parse_args()
    with open(args.source,'rb') as f:raw=f.read(15*1024*1024+1)
    body=extract(raw,args.bbox)
    encoded=json.dumps(body,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    digest=hashlib.sha256(encoded).hexdigest()
    manifest=dict(bounds=args.bbox,provider='natural-earth',snapshot=digest,fetched_at=time.time(),
        dataset_version=VERSION,license_ref=LICENSE,dependencies=[SOURCE_SHA256],body_sha256=digest)
    output=Path(args.output);output.mkdir(parents=True,exist_ok=False)
    (output/'body.json').write_bytes(encoded)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    result=inspect(output/'body.json',output/'manifest.json')
    result.update(source=SOURCE,source_sha256=SOURCE_SHA256,scale='1:10000000',
        usage='generalized_archive_only_not_osm_or_gameplay',source_license='public_domain')
    (output/'report.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result))


if __name__=='__main__':main()
