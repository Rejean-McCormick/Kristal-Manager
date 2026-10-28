import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
# Unit tests exercise level logic in-process for speed. The packaged self-test
# and dedicated scheduler test exercise the default isolated-process path.
os.environ.setdefault('KRISTALDIAG_TEST_IN_PROCESS','1')
