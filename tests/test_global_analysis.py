"""Tests end-to-end des propositions intégrées, sans modifications des Kristals."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import zipfile
import pytest
from kristal_manager.global_analysis import analyze_all, export_problem_bundle
from kristal_manager.core import ManagerError
from kristal_manager.semantic_triage import get_references, arketype_candidates, unesco_candidates


def write(root: Path, rel: str, obj: dict):
    p=root/rel;p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False),encoding='utf-8')


def make_kristal(root: Path):
    p=root/'Kristal-Astronomy';p.mkdir(parents=True)
    write(p,'kristal.workspace.json',{'format':'kristal.local-workspace/3.2.0',
           'title':'Kristal-Astronomy','state_ref':'urn:kristal:astronomy:state',
           'native_model':{'kind':'measurement_contextualized_object_graph',
                           'description':'Observations astronomiques de galaxies et étoiles'},
           'subject':{'domain':'astronomy'}})
    write(p,'canon/state.index.json',{'canonical_artifacts':[{'path':'canon/'+k+'.json','logical_contract':{'id':k}} for k in ('registry','graph','crosswalk','dictionaries/catalog')]})
    write(p,'.kristal/v11/authoring.json',{'format':'kristal.authoring-v11-profile/1.0',
           'registry':'canon/registry.json','graph':'canon/graph.json',
           'crosswalk':'canon/crosswalk.json','catalog':'canon/dictionaries/catalog.json'})
    write(p,'canon/registry.json',{'namespace_id':'urn:kristal:astronomy:state'})
    write(p,'canon/graph.json',{'artifact_type':'kristal_semantic_graph',
            'namespace_id':'urn:kristal:astronomy:state', 'entities':['KQ1'],
            'properties':['KP1'], 'assertions':[]})
    write(p,'canon/crosswalk.json',{'mappings':[]})
    write(p,'canon/dictionaries/fr.json',{'entries':[{'semantic_id':'KQ1','preferred_term':'Galaxie spirale'},
                                                        {'semantic_id':'KP1','preferred_term':'étoile'}]})
    content=(p/'canon/dictionaries/fr.json').read_bytes()
    write(p,'canon/dictionaries/catalog.json',{'languages':[{'tag':'fr', 'layers':[
        {'kind':'curated','path':'fr.json','priority':1,
         'sha256': hashlib.sha256(content).hexdigest()}]}]})
    return p


def snapshot(root: Path):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def test_inference_reference_and_abstention():
    ark, profile, mt=get_references()
    assert len(ark)==19 and len(mt)==88
    assert arketype_candidates(ark,'','', '', '', [])['primary_candidate'] is None
    result=unesco_candidates(mt,[{'term':'galaxie'}], 'Kristal-Astronomy','astronomie','galaxie')
    assert result['candidates'][0]['microthesaurus_code']=='2.30'
    assert result['mapped'] is False


def test_all_pipeline_and_cache_and_export(tmp_path):
    source=tmp_path/'locals';make_kristal(source)
    initial=snapshot(source)
    db=tmp_path/'manager'/'catalogue'/'global.sqlite3'
    reports=tmp_path/'manager'/'rapports'
    a=analyze_all(source,catalogue=db,reports_base=reports)
    assert initial==snapshot(source)
    assert a['catalog_stats']['updated']==1
    assert a['global_report']['counts']['kristals']==1
    assert a['global_report']['entries'][0]['proposed_unesco']=='2.30'
    assert a['global_report']['entries'][0]['priority'] in ('review','warning')
    assert Path(a['html_report']).is_file()
    with zipfile.ZipFile(a['problem_archive']) as z:
        assert 'rapport_global.json' in z.namelist()
        assert not any(name.endswith('canon/graph.json') for name in z.namelist())
    with pytest.raises(FileExistsError):export_problem_bundle(a['report_directory'])
    b=analyze_all(source,catalogue=db,reports_base=reports)
    assert b['catalog_stats']['cached']==1
    assert b['catalog_stats']['updated']==0
    assert initial==snapshot(source)
    assert a['report_directory']!=b['report_directory']


def test_outside_source_required(tmp_path):
    source=tmp_path/'locals';make_kristal(source)
    with pytest.raises(ManagerError):
        analyze_all(source,catalogue=source/'global.sqlite3',reports_base=tmp_path/'reports')
    with pytest.raises(ManagerError):
        analyze_all(source,catalogue=tmp_path/'global.sqlite3',reports_base=source/'reports')


def test_cli_analyse_globale(tmp_path,capsys):
    from kristal_manager.cli import main
    root=tmp_path/'locals';make_kristal(root)
    rc=main(['analyse-globale',str(root),'--catalogue',str(tmp_path/'catalog.db'),
             '--rapports',str(tmp_path/'rapports')])
    assert rc==0
    obj=json.loads(capsys.readouterr().out)
    assert Path(obj['problem_archive']).is_file()


def test_gui_global_center_runs(monkeypatch,tmp_path):
    import os, time
    if os.name != 'nt' and not os.environ.get('DISPLAY'):
        pytest.skip('Tk requires a display')
    from kristal_manager import gui, global_analysis
    import tkinter.messagebox as boxes
    root=tmp_path/'locals';make_kristal(root)
    before=snapshot(root)
    monkeypatch.setattr(global_analysis,'CATALOGUE_PATH',tmp_path/'manager'/'catalogue'/'global.sqlite3')
    monkeypatch.setattr(global_analysis,'RAPPORTS_PATH',tmp_path/'manager'/'rapports')
    monkeypatch.setattr(gui, 'save_settings', lambda *_: None)
    monkeypatch.setattr(boxes,'askyesno',lambda *_,**__: True)
    app=gui.ManagerWindow()
    try:
        app.path_var.set(str(root))
        app.open_global_center()
        panel=app._global_dialog
        assert panel and panel.winfo_exists()
        panel._run()
        deadline=time.monotonic()+12
        while app.busy and time.monotonic()<deadline:
            app.update();time.sleep(.03)
        app.update()
        assert not app.busy
        assert panel.result and len(panel.entries)==1
        assert 'Kristals' in panel.status.get()
        assert len(panel.table.get_children())==1
        assert str(panel.copy_all_button.cget('state'))=='normal'
        assert str(panel.copy_selected_button.cget('state'))=='disabled'
        panel._copy_all()
        assert 'Kristal-Astronomy' in app.clipboard_get()
        panel.table.selection_set(panel.table.get_children()[0])
        panel._update_selection_buttons()
        assert str(panel.copy_selected_button.cget('state'))=='normal'
        panel._copy_selected()
        selection=json.loads(app.clipboard_get())
        assert selection['synthese_globale']['title']=='Kristal-Astronomy'
        assert 'indices_detailles' in selection
        assert before==snapshot(root)
        assert Path(panel.result['problem_archive']).is_file()
    finally:
        app.destroy()


def test_chatgpt_clipboard_summary_contains_all_entries_and_issues():
    from kristal_manager.global_panel import format_chatgpt_summary
    data = {
        'source': r'C:\mycode\Kristal\locals', 'generated_at': '2026-10-28T17:00:00Z',
        'verification_mode': 'inventory_only',
        'counts': {'kristals': 2, 'blocker': 1, 'warning': 0, 'review': 1,
                   'arketype_candidates': 1, 'unesco_micro_candidates': 1},
        'entries': [
            {'title': 'Kristal-Astronomy', 'state_ref': 'urn:kristal:astronomy:state',
             'readiness': 'READY', 'content_status': 'observed', 'priority': 'review',
             'proposed_arketype': 'ARK-02', 'proposed_unesco_domain': '2',
             'proposed_unesco': '2.30', 'keywords': ['galaxie', 'étoile'], 'problems': []},
            {'title': 'Kristal-Biology', 'state_ref': 'urn:kristal:biology:state',
             'readiness': 'IDENTITY COLLISION', 'content_status': 'observed', 'priority': 'blocker',
             'keywords': ['ADN'], 'problems': [
                 {'code': 'IDENTITY_COLLISION', 'severity': 'blocker', 'detail': 'copie historique'}]},
        ],
        'limits': ['Aucune certification C1/C2/C3.'],
    }
    summary = format_chatgpt_summary(data)
    assert '2 Kristals' in summary
    assert 'Kristal-Astronomy' in summary and '2.30' in summary
    assert 'Kristal-Biology' in summary and 'IDENTITY_COLLISION' in summary
    assert 'galaxie' in summary and 'étoile' in summary
    assert 'non validées' in summary and 'C1/C2/C3' in summary


def test_unesco_parent_domain_always_matches_proposed_microthesaurus():
    _,_,mt=get_references()
    mixed=unesco_candidates(mt,[{'term':'population'},{'term':'biology'}],
                            'Kristal-Biology','biologie des populations','population')
    if mixed['status']=='candidates_to_review':
        assert mixed['domain_candidates'][0]['domain_code']==mixed['candidates'][0]['domain_code']
        assert mixed['independent_domain_candidates']
