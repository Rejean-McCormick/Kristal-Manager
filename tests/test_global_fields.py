import json
from pathlib import Path
from kristal_manager.unified.field_audit import inspect_workspace,write_coverage
from kristal_manager.unified import service

def make(tmp_path):
    r=tmp_path/'locals';r.mkdir(exist_ok=True)
    w=r/'Kristal-01';w.mkdir()
    (w/'kristal.workspace.json').write_text(json.dumps({'format':'kristal.local-workspace/3.2.0',
      'title':'Kristal-01','slug':'kristal-01','state_ref':'urn:one','status':'building',
      'native_model':{'kind':'structured','canonical_paths':['canon/s1.json']},
      'classification':{'primary_archetype':'ARK-01','primary_usage':'PRF-20'},
      'semantic_mapping':{'file':'semantic-mapping/semantic-map.json'}}))
    return r,w

def test_missing_and_declared_distinct(tmp_path):
    root,w=make(tmp_path)
    fields=inspect_workspace(w)
    assert fields['fields']['title']['status']=='PRESENT'
    assert fields['fields']['classification.primary_archetype']['status']=='DECLARED_UNVERIFIED'
    assert fields['fields']['classification.unesco_thesaurus']['status']=='NOT_DECLARED_REVIEW'
    assert any(item['kind']=='BROKEN_REFERENCE' for item in fields['issues'])
    assert fields['fields']['state_scope']['status']=='OPTIONAL_ABSENT'

def test_field_export_and_full_scan(tmp_path,monkeypatch):
    root,w=make(tmp_path)
    (w/'canon').mkdir();(w/'canon/s1.json').write_text('{}')
    out=tmp_path/'audits'/'global'
    rows=[{'path':str(w)}]
    result=write_coverage(root,rows,out,db=tmp_path/'test.db')
    assert result['count']==1
    assert (out/'CHAMPS-127-MANQUANTS.csv').is_file()
    monkeypatch.setattr(service,'inventory',lambda *a,**k:{'workspaces':1})
    monkeypatch.setattr(service,'analyze',lambda *a,**k:{'counts':{'kristals':1}})
    monkeypatch.setattr(service,'overview',lambda *a,**k:{'workspaces':[],'count':0})
    result=service.scan_global(root,out=tmp_path/'audits'/'second',db=tmp_path/'test.db')
    assert result['coverage']['count']==1 and Path(result['zip']).exists()
    assert result['failed_phases']=={}


def test_redacted_diag_context_forwarding(tmp_path):
    from kristal_manager.diag_bridge import _extract_official_findings
    current=tmp_path/'current';level=current/'levels'/'N06';level.mkdir(parents=True)
    suspicious='TOP_SECRET_EXAMPLE_NOT_TO_FORWARD'
    (level/'result.json').write_text(json.dumps({'findings':[{
      'id':'N06-SECRETS-002','verdict':'WARN','message':'Potential token',
      'evidence':[{'path':'archive/file.html','line':3,'pattern':'generic-secret-assignment',
                  'third_party_archive_candidate':True,'secret_value':suspicious}]}]}),encoding='utf-8')
    findings=_extract_official_findings(current,{'levels':[{'id':'N06'}]})
    assert findings[0]['context'][0]['third_party_archive_candidate'] is True
    assert suspicious not in json.dumps(findings)
