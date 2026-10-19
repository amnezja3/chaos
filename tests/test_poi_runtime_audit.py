from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from poi_infrastructure.providers import Registry
from poi_infrastructure.repository import Repository
from tools.poi_runtime_audit import main


class RuntimeAuditTests(unittest.TestCase):
    def test_only_allowlisted_environment_and_no_config_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'data/poi_cache.sqlite3'
            registry = Registry(Repository(path))
            registry.initialize()
            registry.save('fixture',0,dict(name='Fixture',url='https://example.org/api/interpreter',
                operator_group='example.org',priority=0),'test')
            before = registry.list()
            processes = [dict(name='chaos',pm2_env=dict(pm_cwd=directory,status='online',
                SECRET_KEY='DO_NOT_PRINT',CHAOS_POI_PROVIDER_REGISTRY_ENABLED='1'))]
            out = io.StringIO()
            with patch('tools.poi_runtime_audit.subprocess.run',return_value=Mock(stdout=json.dumps(processes))), redirect_stdout(out):
                main()
            self.assertNotIn('DO_NOT_PRINT',out.getvalue())
            result = json.loads(out.getvalue())
            self.assertEqual(result['eligible_normal_scan'],[])
            self.assertEqual(result['settings']['CHAOS_POI_PROVIDER_REGISTRY_ENABLED'],'1')
            self.assertEqual(result['settings']['CHAOS_OVERPASS_TIMEOUT_SECONDS'],'8')
            self.assertEqual(registry.list(),before)


if __name__ == '__main__':
    unittest.main()
