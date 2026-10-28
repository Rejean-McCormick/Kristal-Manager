#!/usr/bin/env python3
from pathlib import Path
import os,subprocess,sys,tempfile
root=Path(__file__).resolve().parents[1]
def run(*args,env=None):
    print('+',' '.join(args));subprocess.run(args,cwd=root,check=True,env=env)
run(sys.executable,'-m','compileall','-q','kristaldiag','levels')
run(sys.executable,'scripts/verify_contract_mirrors.py')
run(sys.executable,'scripts/generate_contract_manifest.py')
run(sys.executable,'scripts/generate_suite_manifest.py')
run(sys.executable,'scripts/check_docs_links.py')
# Unit tests use in-process level execution for speed.
env=dict(os.environ);env['KRISTALDIAG_TEST_IN_PROCESS']='1'
run(sys.executable,'-m','pytest','-q',env=env)
# Release check keeps self-test in-process for speed; CI also runs the default isolated-worker path.
env2=dict(os.environ);env2['KRISTALDIAG_TEST_IN_PROCESS']='1'
run(sys.executable,'kristaldiag.py','self-test',env=env2)
run(sys.executable,'scripts/generate_repo_manifest.py')
print('KristalDiag v10 consolidated release check: PASS')
