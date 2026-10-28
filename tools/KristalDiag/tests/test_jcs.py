import json, hashlib
from pathlib import Path
from kristaldiag.jcs import digest

ROOT=Path(__file__).resolve().parents[1]

def test_normative_jcs_vectors():
    doc=json.loads((ROOT/'tck/jcs/vectors.json').read_text(encoding='utf-8'))
    for v in doc['vectors']:
        canonical,hx,_=digest(v['input'],v.get('content_boundary',{}).get('exclude_json_pointers',[]))
        assert canonical==v['expected_canonical'],v['id']
        assert hx==v['expected_sha256_hex'],v['id']
