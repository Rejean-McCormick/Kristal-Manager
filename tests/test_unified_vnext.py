"""Manager vNext acceptance contract: persistence, migration and truthful statuses."""
from __future__ import annotations
from pathlib import Path
import json
import sqlite3
import pytest
from kristal_manager import central_store
from kristal_manager.unified import repository as repo, service
from kristal_manager.unified.cli import main as cli_main


def make(root:Path, name:str='Kristal-Test', v9:bool=True) -> Path:
    w=root/name
    w.mkdir(parents=True,exist_ok=True)
    (w/'kristal.workspace.json').write_text(json.dumps({'format':'kristal.local-workspace/3.2.0',
         'title':name,'slug':name,'state_ref':'urn:kristal:test:state'}),encoding='utf8')
    if v9:
        p=w/'.kristal/v9/capabilities.json';p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text('{"test":true}',encoding='utf8')
    return w


def report(w:Path,verdict='PASS') -> dict:
    return {'format':'kristal.manager-kristaldiag/1.0','workspace':str(w),
            'profile':'V9-State-Reader','verdict':verdict,
            'executed_at':'2026-10-31T12:00:00+00:00','process_status':'EXECUTED_EXIT_0',
            'input_fingerprint':central_store._fingerprint(w),
            'input_changed_during_run':False,'qualification':'NOT_ESTABLISHED'}


def test_atomic_v1_v2_and_profile(tmp_path):
    w=make(tmp_path);db=tmp_path/'ops.sqlite3'
    run=repo.start_run('KristalDiag',root=tmp_path,db=db)
    assert central_store.record_diagnostic(w,report(w),db=db,run_id=run)
    assert central_store.record_diagnostic(w,report(w),db=db,run_id=run) is False
    repo.finish_run(run,'COMPLETED',processed=1,db=db)
    new=repo.latest_observation(w,'diagnostic',profile='V9-State-Reader',db=db)
    assert new['verdict']=='PASS' and new['freshness']=='CURRENT' and new['run_id']==run
    assert repo.latest_observation(w,'diagnostic',profile='V10-Full',db=db) is None
    with sqlite3.connect(db) as c:
        assert c.execute('select count(*) from observations').fetchone()[0]==1
        assert c.execute('select count(*) from observations_v2').fetchone()[0]==1
        assert c.execute('pragma user_version').fetchone()[0]==2


def test_source_modification_marks_stale_not_pass(tmp_path):
    w=make(tmp_path);db=tmp_path/'ops.sqlite3'
    central_store.record_diagnostic(w,report(w),db=db)
    assert repo.latest_observation(w,'diagnostic',db=db)['freshness']=='CURRENT'
    (w/'.kristal/v9/capabilities.json').write_text('{"changed":true}',encoding='utf8')
    assert repo.latest_observation(w,'diagnostic',db=db)['freshness']=='STALE'
    assert repo.dashboard(db=db)[0]['diagnostic_verdict']=='PASS'
    assert repo.dashboard(db=db)[0]['diagnostic_freshness']=='STALE'


def test_analysis_arketype_never_become_certifications(tmp_path):
    w=make(tmp_path);db=tmp_path/'ops.sqlite3'
    central_store.record_analysis({'entries':[{'path':str(w),'priority':'review'}]},db=db)
    central_store.record_arketype_batch({'results':[{'path':str(w),'comparison':'STRUCTURE_ADAPTEE_2_SUR_3'}]},db=db)
    entries=repo.dashboard(db=db)
    assert entries[0]['analysis_priority']=='review'
    assert entries[0]['analysis_freshness']=='PARTIAL_SCOPE'
    assert entries[0]['arketype_freshness']=='PARTIAL_SCOPE'
    assert repo.latest_observation(w,'arketype',db=db)['qualification']=='NOT_ESTABLISHED'


def test_local_decisions_not_canonical(tmp_path):
    w=make(tmp_path);db=tmp_path/'ops.sqlite3'
    original=(w/'kristal.workspace.json').read_bytes()
    did=repo.record_decision(w,'ARK','ARK-01',status='proposed',db=db)
    repo.record_decision(w,'ARK','ARK-01',status='approved_locally',supersedes=did,db=db)
    assert len(repo.list_decisions(w,db=db))==2
    assert (w/'kristal.workspace.json').read_bytes()==original
    with pytest.raises(ValueError):repo.record_decision(w,'ARK','ARK-01',status='certified',db=db)


def test_migrate_v1_existing_and_backup(tmp_path):
    w=make(tmp_path);db=tmp_path/'ops.sqlite3'
    with sqlite3.connect(db) as conn:
        conn.execute('create table workspaces(path_key text primary key,path text,state_ref text,title text,readiness text,profile text,observed_at text not null)')
        conn.execute('create table observations(event_id text primary key,path_key text not null,kind text not null,profile text not null default \"\",status text,observed_at text not null,source_fingerprint text not null,payload text not null)')
        conn.execute('insert into workspaces values(?,?,?,?,?,?,?)',(str(w).casefold(),str(w),'id',w.name,'READY','v9','2026-10-31'))
        conn.execute('insert into observations values(?,?,?,?,?,?,?,?)',('legacy-1',str(w).casefold(),'diagnostic','V9-State-Reader','PASS','2026-10-31',json.dumps(central_store._fingerprint(w)),json.dumps(report(w))))
        conn.execute('pragma user_version=1')
    assert repo.backfill_v1(db=db)==1
    assert repo.backfill_v1(db=db)==0
    assert (tmp_path/'ops.sqlite3.before-v2.backup').is_file()
    assert repo.latest_observation(w,'diagnostic',db=db)['verdict']=='PASS'
    assert repo.integrity_check(db=db)['sqlite']=='ok'


def test_run_lifecycle_tracks_failure(tmp_path):
    db=tmp_path/'ops.sqlite3'
    run=repo.start_run('TestEngine',root=tmp_path,total=127,db=db)
    repo.set_progress(run,2,db=db)
    repo.finish_run(run,'FAILED',processed=2,error='Intentional failure',db=db)
    status=repo.list_runs(db=db)[0]
    assert status['status']=='FAILED' and status['processed']==2
    with pytest.raises(ValueError):repo.finish_run(run,'COMPLETED',db=db)


def test_inventory_and_export_no_source_change(tmp_path):
    root=tmp_path/'locals';root.mkdir();w=make(root)
    db=tmp_path/'ops.sqlite3';prior=(w/'kristal.workspace.json').read_bytes()
    result=service.inventory(root,db=db)
    assert result['workspaces']==1
    data=service.overview(root,db=db)
    assert data['count']==1 and data['workspaces'][0]['title']==w.name
    file=tmp_path/'export.json'
    assert Path(service.export(root,file,db=db)).is_file()
    assert (w/'kristal.workspace.json').read_bytes()==prior
    with pytest.raises(ValueError):service.export(root,w/'bad.json',db=db)


def test_batch_unifies_not_applicable_and_run(tmp_path,monkeypatch):
    from kristal_manager import diagnostics_batch
    source=tmp_path/'locals';source.mkdir()
    v9=make(source,'Kristal-V9');native=make(source,'Kristal-Native',v9=False)
    monkeypatch.setattr(diagnostics_batch,'scan_roots',lambda _:[{'path':str(v9),'title':v9.name},
                                                                   {'path':str(native),'title':native.name}])
    db=tmp_path/'ops.sqlite3'
    result=diagnostics_batch.run_folder(source,db=db,output_dir=tmp_path/'out',
        diag_runner=lambda workspace,profile:report(workspace))
    assert result['counts']=={'NOT_APPLICABLE':1,'PASS':1}
    assert result['run_id']==repo.list_runs(db=db)[0]['run_id']
    assert repo.list_runs(db=db)[0]['status']=='COMPLETED'
    assert repo.latest_observation(native,'diagnostic',db=db)['verdict']=='NOT_APPLICABLE'


def test_engine_exception_recorded_no_fake_pass(tmp_path,monkeypatch):
    from kristal_manager import diagnostics_batch
    root=tmp_path/'locals';root.mkdir();w=make(root)
    monkeypatch.setattr(diagnostics_batch,'scan_roots',lambda _:[{'path':str(w),'title':w.name}])
    def fails(*args,**kwargs):raise OSError('no tools')
    db=tmp_path/'ops.sqlite3'
    result=diagnostics_batch.run_folder(root,db=db,output_dir=tmp_path/'out',diag_runner=fails)
    assert result['counts']=={'EXECUTION_ERROR':1}
    assert repo.latest_observation(w,'diagnostic',db=db)['verdict']=='EXECUTION_ERROR'


def test_interrupted_batch_run_remains_visible(tmp_path,monkeypatch):
    from kristal_manager import diagnostics_batch
    root=tmp_path/'locals';root.mkdir();w=make(root)
    monkeypatch.setattr(diagnostics_batch,'scan_roots',lambda _:[{'path':str(w),'title':w.name}])
    def explode(*args):raise KeyboardInterrupt()
    db=tmp_path/'ops.sqlite3'
    with pytest.raises(KeyboardInterrupt):
        diagnostics_batch.run_folder(root,db=db,output_dir=tmp_path/'out',
            diag_runner=lambda ws,profile:report(ws),on_progress=explode)
    assert repo.list_runs(db=db)[0]['status']=='INTERRUPTED'


def test_cli_json_and_integrity(tmp_path,capsys):
    db=tmp_path/'ops.sqlite3'
    assert cli_main(['--db',str(db),'integrite'])==0
    assert json.loads(capsys.readouterr().out)['sqlite']=='ok'
    assert cli_main(['--db',str(db),'executions'])==0
    assert json.loads(capsys.readouterr().out)==[]


def test_import_json_historical_never_current(tmp_path):
    root=tmp_path/'locals';root.mkdir();w=make(root)
    db=tmp_path/'ops.sqlite3';source=tmp_path/'previous-run.json'
    old=report(w)
    source.write_text(json.dumps(old),encoding='utf8')
    result=service.import_diagnostic_report(source,root,db=db)
    assert result['imported']==1
    diag=repo.latest_observation(w,'diagnostic',db=db)
    assert diag['verdict']=='PASS' and diag['freshness']=='UNVERIFIED'
    assert diag['payload']['process_status']=='IMPORTED_UNVERIFIED'
    assert (w/'kristal.workspace.json').is_file()


def test_import_json_blocks_outside_workspace(tmp_path):
    root=tmp_path/'locals';root.mkdir();outside=make(tmp_path,'Kristal-Outside')
    file=tmp_path/'foreign.json'
    file.write_text(json.dumps(report(outside)),encoding='utf8')
    db=tmp_path/'ops.sqlite3'
    result=service.import_diagnostic_report(file,root,db=db)
    assert result['imported']==0 and result['skipped']==1


def test_cooperative_cancellation_persists_interrupted_run(tmp_path,monkeypatch):
    from kristal_manager import diagnostics_batch
    from threading import Event
    source=tmp_path/'locals';source.mkdir();one=make(source,'Kristal-One');two=make(source,'Kristal-Two')
    monkeypatch.setattr(diagnostics_batch,'scan_roots',lambda _:[{'path':str(one),'title':one.name},{'path':str(two),'title':two.name}])
    stop=Event();db=tmp_path/'ops.sqlite3'
    def progress(n,total,name,status):
        stop.set()
    with pytest.raises(diagnostics_batch.BatchCancelled):
        diagnostics_batch.run_folder(source,db=db,output_dir=tmp_path/'out',
                                    diag_runner=lambda ws,profile:report(ws),
                                    cancel_event=stop,on_progress=progress)
    assert repo.list_runs(db=db)[0]['status']=='INTERRUPTED'
    assert repo.list_runs(db=db)[0]['processed']==1
    assert repo.latest_observation(one,'diagnostic',db=db)['verdict']=='PASS'
    assert repo.latest_observation(two,'diagnostic',db=db) is None
