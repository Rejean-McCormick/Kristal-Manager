import copy
import hashlib
import json
from pathlib import Path
import pytest

from kristal_manager.review_registry import (FORMAT, load_registry, annotate_entries, update_decision)


def _workspace(root, name, state_ref):
    folder=root/name
    (folder/'canon').mkdir(parents=True)
    anchors={}
    for rel, raw in [('kristal.workspace.json',json.dumps({'state_ref':state_ref})),('canon/state.index.json','{"index":true}')]:
        f=folder/rel
        f.write_text(raw,encoding='utf8')
        anchors[rel]=hashlib.sha256(f.read_bytes()).hexdigest()
    return folder,anchors


def _reg(state_ref,anchors):
    return {'format':FORMAT,'entries':[{'state_ref':state_ref,'name':'Kristal-A',
        'batch':'B01','snapshot_date':'2026-10-30',
        'technical_snapshot':{'result':'LOCAL_CHECKS_PASSED_ON_SNAPSHOT'},
        'archetype_review':{'recommended_primary_candidates':['ARK-14'],'status':'proposed',
            'local_human_approval':False,'rationale':'Simulation'},
        'provenance':{'anchors_sha256':anchors}}]}


def test_scan_enrichment_no_current_status_forged(tmp_path):
    root=tmp_path/'locals';root.mkdir()
    folder,anchors=_workspace(root,'Kristal-A','urn:test:one')
    r=tmp_path/'review.json';r.write_text(json.dumps(_reg('urn:test:one',anchors)),encoding='utf8')
    rows=[{'title':'Kristal-A','state_ref':'urn:test:one','path':str(folder),
           'priority':'review','operational_result':'NOT_EVALUATED','content_status':'observed'},
          {'title':'Kristal-B','state_ref':'urn:test:two','path':str(folder),
           'priority':'review','operational_result':'NOT_EVALUATED'}]
    result=annotate_entries(rows,source=root,registry_path=r)
    assert result['matched']==1 and result['not_found']==1
    assert rows[0]['review_registry_status']=='MATCH'
    assert rows[0]['registered_review']['current_scan_technical_health']=='NOT_VERIFIED_IN_THIS_SCAN'
    assert rows[0]['registered_review']['archetype_review_status']=='proposed'
    assert rows[0]['priority']=='review'
    assert rows[1]['registered_review'] is None
    (folder/'kristal.workspace.json').write_text('{"state_ref": "urn:test:one", "updated":true}')
    assert annotate_entries(rows,source=root,registry_path=r)['anchor_changed']==1
    assert rows[0]['review_registry_status']=='CHANGED'


def test_manual_decision_logged_and_not_tagged(tmp_path):
    root=tmp_path/'locals';root.mkdir()
    folder,anchors=_workspace(root,'Kristal-A','urn:test:one')
    path=tmp_path/'reviews.json';path.write_text(json.dumps(_reg('urn:test:one',anchors)))
    old={p:p.read_bytes() for p in folder.rglob('*') if p.is_file()}
    with pytest.raises(ValueError):update_decision('urn:test:one','approved_locally','',path=path)
    decision=update_decision('urn:test:one','approved_locally','Validation locale après examen',path=path)
    assert decision['new_status']=='approved_locally'
    stored=load_registry(path)
    assert stored['entries'][0]['archetype_review']['status']=='approved_locally'
    assert len(stored['entries'][0]['decision_log'])==1
    assert old=={p:p.read_bytes() for p in folder.rglob('*') if p.is_file()}
    assert stored['entries'][0]['archetype_review']['recommended_primary_candidates']==['ARK-14']


def test_ambiguous_cannot_approve_and_corrupt_not_overwritten(tmp_path):
    root=tmp_path/'locals';root.mkdir()
    _folder,anchors=_workspace(root,'Kristal-A','urn:test:one')
    data=_reg('urn:test:one',anchors)
    data['entries'][0]['archetype_review']['recommended_primary_candidates']=['ARK-15','ARK-19']
    path=tmp_path/'review.json';path.write_text(json.dumps(data))
    with pytest.raises(ValueError):update_decision('urn:test:one','approved_locally','some note',path=path)
    update_decision('urn:test:one','approved_locally','J’ai vérifié la structure',path=path,selected_primary='ARK-19')
    assert load_registry(path)['entries'][0]['archetype_review']['review_selected_primary']=='ARK-19'
    path.write_text('invalid json')
    old=path.read_bytes()
    assert not annotate_entries([{'state_ref':'urn:test:one','path':str(_folder)}],source=root,registry_path=path)['available']
    assert path.read_bytes()==old


def test_ref_only_no_fallback_to_name(tmp_path):
    root=tmp_path/'locals';root.mkdir()
    folder,anchors=_workspace(root,'Kristal-A','urn:test:one')
    path=tmp_path/'review.json';path.write_text(json.dumps(_reg('urn:test:one',anchors)))
    rows=[{'title':'Kristal-A','state_ref':'urn:OTHER','path':str(folder),'priority':'review'}]
    summary=annotate_entries(rows,source=root,registry_path=path)
    assert summary['matched']==0 and rows[0]['review_registry_status']=='NOT_REGISTERED'


def test_seed_has_14_unique_unapproved_records():
    from kristal_manager.review_registry import _seed_document
    seed=_seed_document()
    assert len(seed['entries'])==14
    assert len({x['state_ref'] for x in seed['entries']})==14
    assert all(x['archetype_review']['status']!='approved_locally' for x in seed['entries'])
    assert all(not x['archetype_review']['tag_written'] for x in seed['entries'])
