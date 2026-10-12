import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from tools.narrative_locale_matrix import run_matrix


class LocaleMatrixTest(unittest.TestCase):
    def test_rejection_does_not_skip_other_cases_or_retry_or_leak_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root/'pm2.json'
            report = root/'report.json'
            snapshot.write_text(json.dumps([{'name':'chaos-ollama-worker',
                'pm2_env':{'env':{'CHAOS_MISTRAL_API_KEY':'test-secret-not-to-print'}}}]))
            responses = [SimpleNamespace(returncode=1,stdout=json.dumps({'ok':False,'published':False,'errors':['voice_unsupported_number']}))]
            responses += [SimpleNamespace(returncode=0,stdout=json.dumps({'ok':True,'published':False})) for _ in range(11)]
            output = io.StringIO()
            with patch('tools.narrative_locale_matrix.subprocess.run', side_effect=responses) as run, contextlib.redirect_stdout(output):
                self.assertEqual(run_matrix(root/'db',snapshot,report,True),1)
                self.assertEqual(run.call_count,12)
                self.assertEqual(len({tuple(c.args[0]) for c in run.call_args_list}),12)
                self.assertTrue(all('--generate' in c.args[0] for c in run.call_args_list))
                self.assertEqual(len(json.loads(report.read_text())),12)
                self.assertNotIn('test-secret-not-to-print',output.getvalue()+report.read_text())
                with self.assertRaises(FileExistsError):
                    run_matrix(root/'db',snapshot,report,True)
                self.assertEqual(run.call_count,12)
