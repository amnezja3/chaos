"""Run selected unittest modules with all relative runtime data in a temp cwd."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / 'tests'))
with tempfile.TemporaryDirectory(prefix='chaos-isolated-tests-') as directory:
    os.chdir(directory)
    os.environ['CHAOS_SESSION_FILE_DIR'] = str(Path(directory) / 'sessions')
    os.environ['CHAOS_SECRET_KEY'] = 'isolated-tests-only'
    try:
        suite = unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    finally:
        os.chdir(root)
sys.exit(not result.wasSuccessful())
