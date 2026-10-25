"""The offline workload must exercise shared accounting, including exhaustion."""
import unittest
from unittest.mock import patch
from tools.world_concurrency_benchmark import run


class ConcurrencyBenchmarkTests(unittest.TestCase):
    def test_four_processes_and_background_finish_without_exceeding_budget(self):
        result=run(scans=8,background=2,credit_limit=20)
        self.assertEqual(result['status'],'pass',result)
        self.assertTrue(all(result['checks'].values()))
        self.assertEqual(result['simulated_credits'],3)
        self.assertEqual(result['simulated_transport_calls'],1)
        self.assertEqual(result['lanes']['live']['attempts'],8)
        self.assertEqual(result['lanes']['background']['attempts'],2)
        self.assertGreater(sum(v['outcomes'].get('budget_exhausted',0) for v in result['lanes'].values()),0)
        self.assertEqual(result['network_calls'],0)
        self.assertEqual(result['production_writes'],0)

    def test_invalid_workloads_cannot_create_a_database(self):
        with patch('tools.world_concurrency_benchmark.tempfile.TemporaryDirectory') as directory:
            for kwargs in (dict(scans=101),dict(scans=True),dict(background=11),dict(credit_limit=19)):
                with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):run(**kwargs)
            directory.assert_not_called()


if __name__=='__main__':unittest.main()
