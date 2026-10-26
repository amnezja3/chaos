import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

from tools.overpass_probe import inspect


class ProbeCliTests(unittest.TestCase):
    def test_status_and_rate_limit_do_not_mutate_or_probe(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'poi.sqlite3'
            with sqlite3.connect(path) as c:
                c.executescript('CREATE TABLE poi_provider_config(id TEXT,config TEXT);'
                    'CREATE TABLE leases(key TEXT,until_at REAL);'
                    'CREATE TABLE providers(name TEXT,until_at REAL);')
                c.execute('INSERT INTO poi_provider_config VALUES (?,?)',('coffee',json.dumps(dict(
                    revision=3,operator_group='overpass.private.coffee',technical_status='tested_failed',
                    enabled=False,probe_allowed=True,review_due_at=time.time()+3600))))
                c.execute('INSERT INTO leases VALUES (?,?)',('@health-rate:overpass.private.coffee',time.time()+900))
            c.close()
            before=path.read_bytes()
            result=inspect(path,'coffee')
            self.assertGreater(result['retry_after_seconds'],890)
            self.assertEqual(result['network_calls'],0)
            run=subprocess.run([sys.executable,'tools/overpass_probe.py','--db',str(path),
                '--provider','coffee','--execute'],capture_output=True,text=True,timeout=15)
            self.assertEqual(run.returncode,1,run.stderr)
            self.assertEqual(json.loads(run.stdout)['status'],'not_ready')
            self.assertEqual(path.read_bytes(),before)

    def test_missing_database_is_not_created(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'missing.sqlite3'
            with self.assertRaises(sqlite3.OperationalError):inspect(path,'coffee')
            self.assertFalse(path.exists())

    def test_help_runs_from_file_without_initializing_database(self):
        run=subprocess.run([sys.executable,'tools/overpass_probe.py','--help'],
            capture_output=True,text=True,timeout=15)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertIn('--execute',run.stdout)
