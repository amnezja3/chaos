from dataclasses import replace
import hashlib
import json
from pathlib import Path
import unittest

import test_world_land_water as fixtures
from poi_infrastructure.land_water import prepare_product
from poi_infrastructure.natural_earth_region import extract,SOURCE_SHA256,VERSION
from poi_infrastructure.world_contract import ContractError
from poi_infrastructure.world_read import SelectionProof,AREA_SELECTION
from poi_infrastructure.land_water import ADAPTER


ROOT=Path(__file__).parent/'fixtures/world/natural_earth_5_1_1'


class NaturalEarthTests(unittest.TestCase):
    def test_real_multipart_partition_roundtrip_with_dependencies(self):
        raw=(ROOT/'body.json').read_bytes()
        manifest=json.loads((ROOT/'manifest.json').read_bytes())
        self.assertEqual(hashlib.sha256(raw).hexdigest(),manifest['body_sha256'])
        self.assertEqual(manifest['dependencies'],[SOURCE_SHA256])
        f=fixtures.LandWaterTests();f.setUp();self.addCleanup(f.doCleanups)
        fixture=f.fixture
        provenance=replace(f.provenance,source_dataset_at=VERSION,license_ref=manifest['license_ref'])
        bounds=manifest['bounds']
        batch=prepare_product(json.loads(raw),bounds=bounds,dependencies=manifest['dependencies'],provenance=provenance)
        land=next(o for o in batch.objects if o.land_water_origin.role=='land')
        self.assertEqual(land.geometry.kind,'MultiPolygon')
        self.assertEqual(len(land.geometry.coordinates),2)
        proof=SelectionProof('area','land_water','land_water',AREA_SELECTION,ADAPTER,'query',
            tuple(bounds),'isolated-natural-earth-fixture',dataset_version=VERSION)
        fixture.world.publish_batch('query',fixture.owner,batch,provider='fixture',revision=1,
            storage_reference='fixture-storage-v1',fresh_until=fixture.fresh,usable_until=fixture.usable,
            coverage=proof,certified_selections=(('fixture',ADAPTER,'land_water',AREA_SELECTION,'isolated-natural-earth-fixture'),))
        read=f.read(bounds,dataset_version=VERSION,dependency_digests=(SOURCE_SHA256,))
        self.assertEqual(read.state,'COMPLETE_FRESH')
        self.assertEqual(read.batch,batch)
        self.assertEqual(f.read(bounds,dataset_version=VERSION,dependency_digests=('b'*64,)).state,'MISS')

    def test_extractor_refuses_unpinned_or_oversized_source_region(self):
        with self.assertRaisesRegex(ContractError,'source_mismatch'):
            extract(b'{}',(22,60,22.01,60.01))
        with self.assertRaisesRegex(ContractError,'bounds'):
            extract(b'{}',(22,60,23,61))
