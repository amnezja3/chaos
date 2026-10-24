from dataclasses import replace
import json
from pathlib import Path
import unittest
from poi_infrastructure.world_adapters import plan_maplark_region,plan_maplark,normalize_maplark,MAPLARK_VERSION
from poi_infrastructure.world_contract import Provenance,ContractError
from poi_infrastructure.world_region_candidate import prepare,SELECTION
from poi_infrastructure.world_read import SelectionProof


class RegionCandidateTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).parent/'fixtures/poi/maplark_roads_bbox_20261024'
        body=json.loads(path.with_suffix('.json').read_text())
        meta=json.loads(path.with_suffix('.metadata.json').read_text())
        self.batch=normalize_maplark(body,meta['headers'],Provenance('maplark',MAPLARK_VERSION,'single-response',1),profile='roads',maximum=1000)
        self.plan=plan_maplark_region(tuple(meta['bbox']))

    def test_candidate_preserves_full_objects_and_unknown_dataset(self):
        candidate=prepare(self.batch,self.plan)
        self.assertEqual((candidate.raw_objects,len(candidate.batch.objects)),(76,75))
        self.assertEqual(candidate.excluded_ids,('osm:way:201343570',))
        self.assertEqual(len(self.batch.objects),76)
        originals={o.identity:o for o in self.batch.objects}
        for obj in candidate.batch.objects:
            self.assertEqual(obj,originals[obj.identity])
            self.assertIsNone(obj.provenance.source_dataset_at)
        self.assertFalse(candidate.region_certified)
        with self.assertRaisesRegex(ContractError,'area_unsupported'):
            SelectionProof('area','roads','roads',SELECTION,MAPLARK_VERSION,'q',candidate.bounds,'not-a-certificate')

    def test_mixed_snapshot_or_dataset_rejected(self):
        first=self.batch.objects[0]
        for provenance in (replace(first.provenance,snapshot='other'),replace(first.provenance,source_dataset_at='other')):
            mixed=replace(self.batch,objects=(replace(first,provenance=provenance),*self.batch.objects[1:]))
            with self.assertRaisesRegex(ContractError,'mixed_source'):prepare(mixed,self.plan)

    def test_partial_and_radius_plan_rejected(self):
        with self.assertRaisesRegex(ContractError,'incomplete'):prepare(replace(self.batch,completeness='partial'),self.plan)
        with self.assertRaisesRegex(ContractError,'plan_invalid'):prepare(self.batch,plan_maplark(51.53,20.36,300,profile='roads'))

    def test_missing_geometry_and_other_layer_rejected(self):
        first=self.batch.objects[0]
        for changed in (replace(first,geometry=None),replace(first,layers=frozenset({'waterways'}))):
            with self.assertRaisesRegex(ContractError,'geometry_or_layer'):
                prepare(replace(self.batch,objects=(changed,*self.batch.objects[1:])),self.plan)

    def test_other_profile_cannot_inherit_roads_qualification(self):
        with self.assertRaisesRegex(ContractError,'profile_unqualified'):
            prepare(replace(self.batch,profile='coastline'),self.plan)
