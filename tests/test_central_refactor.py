"""Regression contract for the unified, non-canonical operational read model."""
import csv
import json
from pathlib import Path

import pytest

from kristal_manager import central_store as store
from kristal_manager import diagnostics_batch as batch


def workspace(tmp_path, name='Kristal-A', *, v9=True):
    root=tmp_path / 'locals' / name
    root.mkdir(parents=True)
    (root/'kristal.workspace.json').write_text('{"kristal": {}}', encoding='utf-8')
    if v9:
        (root/'.kristal/v9').mkdir(parents=True)
        (root/'.kristal/v9/capabilities.json').write_text('{"test":true}', encoding='utf-8')
    return root


def row(path):
    return {'path':str(path),'title':path.name,'state_ref':'urn:test:'+path.name,'readiness':'READY','profile':'v9'}


def diag(path, verdict='PASS'):
    return {'workspace':str(path),'profile':'V9-State-Reader','verdict':verdict,
            'process_status':'EXECUTED_EXIT_0','executed_at':'2026-10-31T13:19:59Z',
            'input_fingerprint':store._fingerprint(path),
            'input_changed_during_run':False,'qualification':'NOT_ESTABLISHED'}


def test_persist_restore_and_stale(tmp_path):
    a=workspace(tmp_path); db=tmp_path/'central.sqlite3'
    store.remember_workspaces([row(a)],db=db)
    assert store.record_diagnostic(a,diag(a),db=db)
    assert store.record_diagnostic(a,diag(a),db=db) is False  # idempotent
    fresh=store.restore_rows([row(a)],db=db)[0]
    assert fresh['diag_report']['verdict']=='PASS'
    assert fresh['diag_freshness']=='CURRENT'
    # Changing a source descriptor invalidates the claim, not the evidence.
    (a/'kristal.workspace.json').write_text('{"kristal":{"changed":true}}',encoding='utf-8')
    stale=store.restore_rows([row(a)],db=db)[0]
    assert 'diag_report' not in stale
    assert stale['diag_freshness']=='STALE_OR_UNVERIFIED'
    history=store.latest(a,'diagnostic',db=db)
    assert history['status']=='PASS' and history['freshness']=='STALE_OR_UNVERIFIED'


def test_arketype_and_global_preserved_separately(tmp_path):
    a=workspace(tmp_path);db=tmp_path/'central.sqlite3'
    store.remember_workspaces([row(a)],db=db)
    store.record_analysis({'entries':[{'path':str(a),'priority':'review','problems':[]}]},db=db)
    report={'results':[{'path':str(a),'project':a.name,'comparison':'STRUCTURE_ADAPTEE_2_SUR_3',
                        'structure':{'counts':{'files':5},'observation_complete':True}}]}
    assert store.record_arketype_batch(report,db=db)==1
    assert store.latest(a,'arketype',db=db)['payload']['qualification']=='NOT_ESTABLISHED'
    assert store.latest(a,'analysis',db=db)['status']=='review'
    assert store.latest(a,'diagnostic',db=db) is None


def test_batch_skips_absent_v9_without_executing(tmp_path, monkeypatch):
    a=workspace(tmp_path,'Kristal-A',v9=True)
    b=workspace(tmp_path,'Kristal-B',v9=False)
    monkeypatch.setattr(batch,'scan_roots',lambda _: [row(a),row(b)])
    called=[]; db=tmp_path/'central.sqlite3'
    def fake_runner(path,*,profile):
        called.append(path.name);return diag(path)
    output=batch.run_folder(a.parent,diag_runner=fake_runner,db=db,output_dir=tmp_path/'reports')
    assert output['total']==2 and output['counts']=={'PASS':1,'NOT_APPLICABLE':1}
    assert called==['Kristal-A']
    assert store.latest(b,'diagnostic',db=db)['status']=='NOT_APPLICABLE'
    assert (Path(output['report_directory'])/'BILAN-DIAGNOSTICS.csv').is_file()
    assert store.status_counts(a.parent,db=db)['current_diagnostics']==2


def test_batch_isolates_execution_error(tmp_path,monkeypatch):
    a=workspace(tmp_path,'Kristal-A');b=workspace(tmp_path,'Kristal-B')
    monkeypatch.setattr(batch,'scan_roots',lambda _:[row(a),row(b)])
    db=tmp_path/'central.sqlite3'
    def runner(path,*,profile):
        if path.name=='Kristal-A':raise RuntimeError('simulated failure')
        return diag(path,'WARN')
    output=batch.run_folder(a.parent,diag_runner=runner,db=db,output_dir=tmp_path/'reports')
    assert output['counts']=={'EXECUTION_ERROR':1,'WARN':1}
    assert store.latest(b,'diagnostic',db=db)['status']=='WARN'


def test_refuses_reports_inside_sources(tmp_path,monkeypatch):
    a=workspace(tmp_path);monkeypatch.setattr(batch,'scan_roots',lambda _:[row(a)])
    with pytest.raises(ValueError,match='outside'):
        batch.run_folder(a.parent,diag_runner=lambda *_ ,**__:diag(a),output_dir=a.parent/'generated')


def test_no_historical_overwrite_from_new_scan(tmp_path):
    a=workspace(tmp_path);db=tmp_path/'central.sqlite3'
    store.remember_workspaces([row(a)],db=db)
    store.record_diagnostic(a,diag(a),db=db)
    store.remember_workspaces([row(a)],db=db)
    assert store.latest(a,'diagnostic',db=db)['status']=='PASS'


def test_capability_change_marks_previous_pass_stale(tmp_path):
    root=workspace(tmp_path);db=tmp_path/'ops.sqlite3'
    store.remember_workspaces([row(root)],db=db)
    store.record_diagnostic(root,diag(root),db=db)
    assert store.latest(root,'diagnostic',db=db)['freshness']=='CURRENT'
    (root/'.kristal/v9/capabilities.json').write_text('{"test":false}',encoding='utf-8')
    assert store.latest(root,'diagnostic',db=db)['freshness']=='STALE_OR_UNVERIFIED'


def test_legacy_import_never_becomes_current_pass(tmp_path):
    root=workspace(tmp_path)
    db=tmp_path/'ops.sqlite3'
    import csv
    csv_path=tmp_path/'BILAN.csv'
    with csv_path.open('w',encoding='utf-8-sig',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=['Kristal','Profil','Verdict','Rapport'],delimiter=';')
        writer.writeheader();writer.writerow({'Kristal':root.name,'Profil':'V9-State-Reader',
                                               'Verdict':'PASS','Rapport':'historical-reference'})
    result=store.import_legacy_diagnostic_csv(csv_path,root.parent,db=db)
    assert result['imported']==1
    evidence=store.latest(root,'diagnostic',db=db)
    assert evidence['status']=='PASS'
    assert evidence['freshness']=='STALE_OR_UNVERIFIED'
    assert 'diag_report' not in store.restore_rows([row(root)],db=db)[0]
