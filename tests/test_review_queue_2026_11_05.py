"""Read-only native evidence, shared stage labels, and safe exports."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from kristal_manager.native_evidence import annotate_native_sources, load_native_catalog
from kristal_manager.review_progress import assess_review, matches_focus, export_review_queue, REVIEW_FOCI
from kristal_manager.column_views import PRESET_NAMES, columns_for


def _make_row(tmp_path, state='urn:kristal:ai:state'):
    index = load_native_catalog()
    record = index[state]
    root = tmp_path / 'locals' / 'Kristal-AI'
    root.mkdir(parents=True)
    # A synthetic copy with exact source bytes cannot be forged to match the
    # archived hashes. An intentionally changed workspace must fail closed.
    (root / 'kristal.workspace.json').write_text(json.dumps({'state_ref':state}), encoding='utf-8')
    return {'path':str(root), 'title':'AI', 'state_ref':state, 'readiness':'READY',
            'qualification_evidence':{'metadata_source':'LIVE_WORKSPACE'},
            'semantic_enrichment':{'status':'MATCHED_CURRENT_DESCRIPTORS'}}


def test_catalog_is_explicitly_noncanonical():
    index=load_native_catalog()
    assert len(index)==127
    assert all(entry['human_approved'] is False for entry in index.values())


def test_changed_source_is_reported_and_never_approved(tmp_path):
    row=_make_row(tmp_path)
    totals=annotate_native_sources([row])
    assert totals['matched']==0
    assert row['native_source_review']['human_approved'] is False
    assert row['native_source_review']['c1_c2_c3']=='NOT_ESTABLISHED'
    assert row['native_source_review']['status'] in ('SOURCES_CHANGED_REVIEW_AGAIN','SOURCES_UNAVAILABLE')
    stage=assess_review(row)
    assert stage['qualification']=='NOT_ESTABLISHED'
    assert stage['stage'] in ('Source review outdated','Source evidence pending')


def test_priority_flags_do_not_grant_approval():
    row={'readiness':'READY', 'native_source_review':{'status':'SOURCE_BYTES_MATCHED'},
         'semantic_enrichment':{'status':'MATCHED_CURRENT_DESCRIPTORS',
                                'prf_candidate':{'id':'PRF-01'},
                                'unesco_proposal_disagrees_with_declared':True},
         'content_status':'native_observed'}
    a=assess_review(row)
    assert a['stage']=='UNESCO review'
    assert matches_focus(a,'PRF alternative')
    assert matches_focus(a,'UNESCO disagreement')
    assert matches_focus(a,'Native contract')
    assert not matches_focus(a,'Source evidence changed')
    assert a['human_approved'] is False
    assert a['qualification']=='NOT_ESTABLISHED'
    with pytest.raises(ValueError):matches_focus(a,'Approve')


def test_column_queue_is_coherent_in_both_windows():
    assert 'Review queue' in PRESET_NAMES
    for area, names in [('manager',('title','review_stage','next_action','native_evidence','prf_review','unesco_review','readiness')),
                        ('analysis',('title','review_stage','next_action','native_evidence','prf_review_ai','unesco_review','priority'))]:
        assert columns_for(area,'Review queue',names)==names
        assert columns_for(area,'Essential',names)[0]=='title'


def test_review_csv_is_private_draft_and_no_overwrite(tmp_path):
    row=_make_row(tmp_path)
    annotate_native_sources([row])
    out=export_review_queue(tmp_path/'review.csv',[row], source_root=tmp_path/'locals')
    with out.open(encoding='utf-8-sig',newline='') as file:
        data=list(csv.DictReader(file))
    assert len(data)==1 and data[0]['qualification']=='NOT_ESTABLISHED'
    assert data[0]['review_stage'] in ('Source review outdated', 'Source evidence pending')
    with pytest.raises(FileExistsError):export_review_queue(out,[row])
    with pytest.raises(ValueError):export_review_queue(tmp_path/'locals'/'bad.csv',[row],source_root=tmp_path/'locals')
    assert not (tmp_path/'locals'/'bad.csv').exists()


@pytest.mark.skipif(__import__('os').name!='nt' and not __import__('os').environ.get('DISPLAY'), reason='Tk required')
def test_both_gui_tables_offer_review_queue(monkeypatch):
    from kristal_manager import gui
    monkeypatch.setattr(gui,'save_settings',lambda *_: None)
    app=gui.ManagerWindow()
    try:
        assert 'review_stage' in app.tree['columns']
        assert 'native_evidence' in app.tree['columns']
        app.column_views.choice.set('Review queue')
        app.column_views.apply()
        assert 'next_action' in app.tree['displaycolumns']
        app.open_global_center()
        panel=app._global_dialog
        assert 'review_stage' in panel.table['columns']
        panel.column_views.choice.set('Review queue')
        panel.column_views.apply()
        assert 'native_evidence' in panel.table['displaycolumns']
        panel.review_focus_var.set('UNESCO disagreement')
        panel._fill()
        panel.destroy()
    finally:
        app.destroy()


def test_historical_unesco_disagreements_reach_main_manager(tmp_path):
    from kristal_manager.editorial_review import annotate_historical_unesco_attention, display_unesco_review
    info=json.loads((Path(__file__).resolve().parents[1]/'data'/'ai_review_priorities_2026-11-04.json').read_text('utf-8'))
    item=next(x for x in info['unesco_disagreements'] if x['title']=='SolarSystem')
    row={'state_ref':item['state_ref'], 'readiness':'READY',
         'qualification_evidence':{'metadata_source':'LIVE_WORKSPACE',
                      'metadata':{'unesco':{'microthesauri':[{'code':c} for c in item['declared_codes']]}}},
         'semantic_enrichment':{'status':'MATCHED_CURRENT_DESCRIPTORS'}}
    assert annotate_historical_unesco_attention([row])==1
    assert 'Historical' in display_unesco_review(row)
    assert matches_focus(assess_review(row),'UNESCO disagreement')
    assert not row['historical_unesco_attention']['human_approved']
    row['qualification_evidence']['metadata']['unesco']['microthesauri'] = []
    assert annotate_historical_unesco_attention([row])==0
    assert not matches_focus(assess_review(row),'UNESCO disagreement')


def test_export_escapes_spreadsheet_formulas(tmp_path):
    row=_make_row(tmp_path)
    row['title']='=SUM(1,1)'
    path=export_review_queue(tmp_path/'safecsv.csv',[row])
    with path.open('r',encoding='utf-8-sig',newline='') as f:
        result=list(csv.DictReader(f))
    assert result[0]['title'].startswith("'=")
