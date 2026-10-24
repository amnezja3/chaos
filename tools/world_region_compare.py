"""Compare saved independent neighbor responses with local parent selections. No HTTP/DB."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shapely.geometry import box,shape
from poi_infrastructure.world_adapters import normalize_maplark,MAPLARK_VERSION
from poi_infrastructure.world_contract import Provenance,ContractError
from tools.world_discovery_inspect import read_json
from tools.world_region_plan import evaluate
from tools.world_region_probe import PARTS


def compare(samples):
    batches={};checks={}
    for part in PARTS:
        body,headers=samples[part]
        checks[part]=evaluate(PARTS[part],'roads',body,headers)
        batches[part]=normalize_maplark(body,headers,Provenance('maplark',MAPLARK_VERSION,'compare:'+part,0),profile='roads',maximum=1000)
    comparisons={}
    for part in ('left','right'):
        area=box(*PARTS[part])
        def select(batch):
            return {o.identity:o for o in batch.objects if 'roads' in o.layers and o.geometry
                    and not o.geometry.crosses_antimeridian and shape(o.geometry.geojson()).intersects(area)}
        expected=select(batches['parent']);actual=select(batches[part])
        missing=sorted(expected.keys()-actual.keys());extra=sorted(actual.keys()-expected.keys())
        changed=sorted(k for k in expected.keys()&actual.keys()
                       if not shape(expected[k].geometry.geojson()).equals(shape(actual[k].geometry.geojson())))
        tags_changed=sorted(k for k in expected.keys()&actual.keys() if dict(expected[k].tags).get('highway')!=dict(actual[k].tags).get('highway'))
        comparisons[part]=dict(local_objects=len(expected),independent_objects=len(actual),
            missing_from_independent=missing,additional_in_independent=extra,changed_full_geometry=changed,
            changed_highway=tags_changed,match=not(missing or extra or changed or tags_changed))
    observed=all(c['local_filter']['observed_geometry_pass'] for c in checks.values())
    return dict(status='compared_not_certified',network_calls=0,production_changed=False,
        region_certified=False,dataset_version_verified=False,
        sample_comparison_pass=observed and all(c['match'] for c in comparisons.values()),
        comparisons=comparisons,checks=checks,
        limitation='Matching samples do not prove absent features or an atomic provider dataset version')


def inspect_directories(paths):
    samples={};hashes={};reports={}
    for part in PARTS:
        directory=Path(paths[part])
        body,bhash=read_json(directory/'body.json');headers,hhash=read_json(directory/'headers.json')
        report,_=read_json(directory/'report.json')
        expected=evaluate(PARTS[part],'roads')['params']
        if report.get('params')!=expected or report.get('status')!='captured_not_certified':
            raise ContractError('capture_report_query_mismatch')
        if report.get('provider_revision') is None:raise ContractError('capture_revision_missing')
        samples[part]=(body,headers);hashes[part]=dict(body=bhash,headers=hhash);reports[part]=report
    result=compare(samples)
    revisions={r['provider_revision'] for r in reports.values()}
    result.update(artifact_sha256=hashes,provider_revisions_match=len(revisions)==1,
                  capture_reports='operator supplied; hashes identify inspected bytes, not signed provider attestations')
    if len(revisions)!=1:result['sample_comparison_pass']=False
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for part in PARTS:p.add_argument('--'+part,required=True,help='Existing capture directory')
    a=p.parse_args()
    try:result=inspect_directories(vars(a))
    except (OSError,ValueError,KeyError,ContractError) as exc:
        print(json.dumps(dict(ok=False,error=str(exc) if isinstance(exc,ContractError) else type(exc).__name__,network_calls=0)))
        return 1
    print(json.dumps(result));return 0 if result['sample_comparison_pass'] else 2


if __name__=='__main__':raise SystemExit(main())
