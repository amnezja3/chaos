"""Capture independent Overpass answers on a synthetic, isolated Linux database.

No download, server, network, or gameplay changes. Requires installed upstream
update_database and osm3s_query executables. Never overwrites a database/output.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from poiFetchClass import POIFetcher


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bin-dir',type=Path,required=True)
    parser.add_argument('--work-dir',type=Path,required=True)
    args=parser.parse_args()
    work=args.work_dir.resolve()
    if work.exists():
        parser.error('Work directory must not exist; never use the game data directory')
    updater=(args.bin_dir/'update_database').resolve()
    query_bin=(args.bin_dir/'osm3s_query').resolve()
    if not updater.is_file() or not query_bin.is_file():
        parser.error('Both upstream Overpass executables are required')
    source=ROOT/'tests/fixtures/poi/geometry_source.osm'
    work.mkdir(parents=True)
    database=work/'synthetic-db'
    database.mkdir()
    subprocess.run([str(updater),'--db-dir='+str(database),'--version=chaos-synthetic-v1'],
                   input=source.read_bytes(),check=True,timeout=120,capture_output=True)
    profile=POIFetcher(tag_filters=['shop','amenity','office','healthcare','atm=yes','man_made=surveillance'])
    cases={}
    for name,lat,lon,radius in [('origin',0,0,300),('nearby',0,.001,300),('edge',0,.002,300),
                                ('small',0,0,100),('empty',1,1,300),('larger',0,0,600)]:
        profile.radius=radius
        query=profile._build_query(lat,lon)
        result=subprocess.run([str(query_bin),'--db-dir='+str(database),'--concise'],input=query.encode(),
                              check=True,timeout=30,capture_output=True)
        payload=json.loads(result.stdout)
        if payload.get('remark') or not isinstance(payload.get('elements'),list):
            raise RuntimeError('incomplete reference: '+name)
        cases[name]=dict(lat=lat,lon=lon,radius=radius,query=query,response=payload)
    manifest=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  query_binary_sha256=hashlib.sha256(query_bin.read_bytes()).hexdigest(),
                  updater_binary_sha256=hashlib.sha256(updater.read_bytes()).hexdigest(),cases=cases)
    output=work/'reference.json'
    output.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(dict(ok=True,reference=str(output),cases=len(cases),network_calls=0)))


if __name__=='__main__':main()
