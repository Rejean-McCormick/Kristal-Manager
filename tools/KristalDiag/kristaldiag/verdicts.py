from __future__ import annotations

VERDICTS=('PASS','WARN','FAIL','SKIP','BLOCKED','PARTIAL','ERROR','INFRA_ERROR','CONFIG_ERROR')
_RANK={'PASS':0,'SKIP':0,'WARN':1,'PARTIAL':1,'BLOCKED':2,'FAIL':3,'ERROR':4,'INFRA_ERROR':4,'CONFIG_ERROR':5}

def combine(values):
    vals=[v for v in values if v]
    return max(vals,key=lambda v:_RANK.get(v,99)) if vals else 'SKIP'

def exit_code(verdict:str)->int:
    if verdict in {'PASS','SKIP'}:return 0
    if verdict in {'WARN','PARTIAL'}:return 10
    if verdict in {'FAIL','BLOCKED'}:return 20
    return 30
