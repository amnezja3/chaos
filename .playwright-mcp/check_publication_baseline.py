import os,sys,tempfile,subprocess,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root),str(root/'tests')]
source=subprocess.check_output(['git','show','HEAD:ghostnetwork/repository.py'],cwd=root).decode('utf-8')
with tempfile.TemporaryDirectory() as tmp:
 os.chdir(tmp)
 os.environ['CHAOS_SECRET_KEY']='isolated-baseline'
 os.environ['CHAOS_SESSION_FILE_DIR']=tmp+'/sessions'
 import ghostnetwork.repository as repo
 exec(compile(source,str(root/'ghostnetwork/repository.py'),'exec'),repo.__dict__)
 suite=unittest.defaultTestLoader.loadTestsFromNames(['test_narrative_publications.NarrativePublicationTest.test_late_older_state_cannot_replace_active_head','test_narrative_publications.NarrativePublicationTest.test_newer_thread_state_invalidates_previous_head'])
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 os.chdir(root)
 sys.exit(not result.wasSuccessful())
