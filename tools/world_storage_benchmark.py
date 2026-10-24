"""Offline synthetic baseline, temporary POI DB only; no API or production writes."""
import argparse
from contextlib import closing, contextmanager
import json
from pathlib import Path
import sys
import tempfile
import time
import tracemalloc

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from poi_infrastructure.repository import Repository
from poi_infrastructure.providers import Registry
from poi_infrastructure.world_storage import CanonicalWorldRepository
from poi_infrastructure.world_contract import Geometry, Provenance, ProviderBatch, WorldObject


class MeasuredRepository(Repository):
    measuring=False

    @contextmanager
    def transaction(self):
        entered=time.perf_counter()
        with super().transaction() as c:
            acquired=time.perf_counter()
            yield c
        finished=time.perf_counter()
        if self.measuring:
            self.transaction_samples.append((acquired-entered,finished-acquired))


def rss_high_water():
    # ru_maxrss is process-lifetime peak, not the delta attributable to this batch.
    if not sys.platform.startswith('linux'):
        return None
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024


def run(count):
    with tempfile.TemporaryDirectory(prefix='chaos-world-benchmark-') as directory:
        path=Path(directory)/'poi.sqlite3'
        repo=MeasuredRepository(path)
        Registry(repo).initialize()
        world=CanonicalWorldRepository(repo)
        world.initialize_canonical()
        with repo.transaction() as c:
            config=dict(enabled=True,policy_status='approved_for_defined_use',scopes=['storage'],review_due_at=time.time()+3600)
            c.execute('INSERT INTO poi_provider_config VALUES (?,?,?)',('fixture',1,json.dumps(config)))
        owner=repo.acquire('benchmark',300)
        tracemalloc.start()
        started=time.perf_counter()
        provenance=Provenance('fixture','benchmark-v1','synthetic',time.time(),license_ref='synthetic-only')
        objects=[]
        for i in range(count):
            x=21+(i%100)*0.001
            y=52+(i//100)*0.001
            geometry=Geometry.parse(dict(type='Polygon',coordinates=[[[x,y],[x+0.0005,y],
                [x+0.0005,y+0.0005],[x,y+0.0005],[x,y]]]))
            objects.append(WorldObject.create(external_id=str(i+1),tags={'shop':'books'},geometry=geometry,
                marker=None,marker_method=None,provenance=provenance,ordinal=i,osm_type='way',osm_id=i+1))
        batch=ProviderBatch(tuple(objects),'poi','complete',(),'synthetic-intersects-v1','source')
        normalized=time.perf_counter()
        now=time.time()
        repo.transaction_samples=[];repo.measuring=True
        # Keep an idle connection open so last-close cleanup does not erase WAL
        # before observing it. No reader transaction pins historical pages.
        with closing(repo.connect()) as observer:
            observer.execute('SELECT count(*) FROM world_snapshot').fetchone()
            snapshot=world.publish_batch('benchmark',owner,batch,provider='fixture',revision=1,
                storage_reference='synthetic-only',fresh_until=now+300,usable_until=now+1800)
            wal=Path(str(path)+'-wal')
            post_commit_wal=wal.stat().st_size if wal.exists() else 0
        repo.measuring=False
        published=time.perf_counter()
        result=world.inspect_region(snapshot,'poi',(21,52,21.01,52.01))
        read=time.perf_counter()
        _,peak=tracemalloc.get_traced_memory()
        tracemalloc.stop()
        with closing(repo.connect()) as c:
            logical=c.execute('SELECT sum(bytes) FROM world_snapshot').fetchone()[0]
            pages=c.execute('PRAGMA page_count').fetchone()[0]*c.execute('PRAGMA page_size').fetchone()[0]
        wal=Path(str(path)+'-wal')
        stats=dict(objects=count,vertices=count*5,normalization_seconds=round(normalized-started,4),
            publication_seconds=round(published-normalized,4),read_seconds=round(read-published,4),
            python_traced_peak_bytes=peak,logical_payload_and_members_bytes=logical,database_page_bytes=pages,
            observed_wal_bytes=wal.stat().st_size if wal.exists() else 0,
            post_commit_wal_bytes=post_commit_wal,
            process_lifetime_peak_rss_bytes=rss_high_water(),
            publication_transactions=len(repo.transaction_samples),
            max_transaction_entry_seconds=round(max((s[0] for s in repo.transaction_samples),default=0),6),
            max_transaction_hold_and_close_seconds=round(max((s[1] for s in repo.transaction_samples),default=0),6),
            selected=len(result['objects']),truncated=result['truncated'],coverage=result['coverage'])
        return stats


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--counts',nargs='+',type=int,default=[50,680,3000])
    args=parser.parse_args()
    if len(args.counts)>5 or any(not 1<=n<=5000 for n in args.counts):
        parser.error('Use up to five bounded counts between 1 and 5000')
    print(json.dumps(dict(network_calls=0,production_changed=False,synthetic=True,
        note='Synthetic, tracemalloc enabled. RSS is Linux process-lifetime high water (null elsewhere), not per-batch delta. WAL observations are not peaks. Transaction entry includes connection/BEGIN; hold includes commit/close. No concurrency load.',
        samples=[run(n) for n in args.counts]),indent=2))


if __name__=='__main__':
    main()
