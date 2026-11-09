"""Read-only UI consolidation: main Manager and Global Analysis use shared views."""
from __future__ import annotations

import json
import os
import time

import pytest

from kristal_manager.column_views import PRESET_NAMES, columns_for
from kristal_manager.editorial_review import annotate_editorial_review, display_unesco_review
from kristal_manager.gui import display_kristal_folder


def test_presets_are_coherent_and_expose_all_fields():
    main = ('title', 'semantic_role', 'arketype', 'usage', 'micro', 'category',
            'prf_review', 'unesco_review', 'readiness', 'diag', 'profile', 'state_ref',
            'artifacts', 'content')
    analysis = ('title', 'priority', 'readiness', 'content_status', 'declared_ark',
                'declared_prf', 'semantic_role_ai', 'prf_review_ai', 'subject_domain',
                'declared_unesco', 'unesco_review', 'ark_structure_history',
                'registered_ark', 'v11_kristalizer', 'new_suggestions', 'keywords')
    for surface, columns in [('manager', main), ('analysis', analysis)]:
        for preset in PRESET_NAMES:
            chosen = columns_for(surface, preset, columns)
            assert chosen and chosen[0] == 'title'
            assert set(chosen).issubset(columns)
        assert columns_for(surface, 'All columns', columns) == columns
        assert len(columns_for(surface, 'Essential', columns)) < len(columns)
        assert 'unesco_review' in columns_for(surface, 'Classification', columns)
        assert 'prf_review' in columns_for(surface, 'Semantic review', columns) or 'prf_review_ai' in columns_for(surface, 'Semantic review', columns)
    with pytest.raises(ValueError):
        columns_for('manager', 'Unsupported', main)


def test_display_uses_live_workspace_title_not_folder_name():
    assert display_kristal_folder({'title':'Accounting', 'path':r'C:\mycode\Kristal\locals\Kristal-Accounting'}) == 'Accounting'
    assert display_kristal_folder({'title':'VaticanOps', 'path':'/a/Kristal-VaticanOps'}) == 'VaticanOps'
    assert display_kristal_folder({'title':'', 'path':'/a/Kristal-Weather'}) == 'Weather'


def test_historic_editorial_remarks_are_strictly_matched_to_current_proposal():
    # The AI triage is documentary evidence only. No stored UNESCO code changes.
    source = json.load(open(__file__.replace('tests/test_column_views_consolidated.py', 'data/ai_review_priorities_2026-11-04.json'),encoding='utf-8'))
    sample = next(x for x in source['unesco_disagreements'] if x['title'] == 'SolarSystem')
    row = {'state_ref':sample['state_ref'], 'proposed_unesco':sample['suggested_code'],
           'qualification_evidence':{'metadata_source':'LIVE_WORKSPACE',
                  'metadata':{'unesco':{'microthesauri':[{'code':x} for x in sample['declared_codes']]}}},
           'semantic_enrichment':{'status':'MATCHED_CURRENT_DESCRIPTORS',
                  'unesco_proposal_disagrees_with_declared':True}}
    original = json.dumps(row['qualification_evidence'],sort_keys=True)
    assert annotate_editorial_review([row]) == 1
    assert display_unesco_review(row) == 'Likely off-topic — AI review'
    assert json.dumps(row['qualification_evidence'],sort_keys=True) == original
    row['proposed_unesco'] = '2.30'
    assert annotate_editorial_review([row]) == 0
    assert 'review' in display_unesco_review(row)


@pytest.mark.skipif(os.name != 'nt' and not os.environ.get('DISPLAY'), reason='GUI display required')
def test_manager_column_views_and_live_descriptors(tmp_path, monkeypatch):
    from kristal_manager import gui, central_store
    from kristal_manager.classification_labels import display_category
    folder = tmp_path/'locals'/'Kristal-Accounting'
    folder.mkdir(parents=True)
    workspace = {'format':'kristal.local-workspace/3.2.0', 'title':'Accounting',
                 'slug':'accounting','state_ref':'urn:kristal:accounting:state',
                 'subject':{'domain':'accounting'},
                 'classification':{'primary_archetype':'ARK-01','primary_usage':'PRF-20'}}
    descriptor = folder/'kristal.workspace.json'
    descriptor.write_text(json.dumps(workspace),encoding='utf-8')
    before = descriptor.read_bytes()
    monkeypatch.setattr(central_store,'database_path',lambda:tmp_path/'derived.sqlite3')
    monkeypatch.setattr(gui,'save_settings',lambda *_:None)
    app=gui.ManagerWindow()
    try:
        app.path_var.set(str(folder.parent))
        app.start_scan()
        deadline=time.monotonic()+15
        while app.busy and time.monotonic()<deadline:
            app.update();time.sleep(.01)
        app.update()
        assert not app.busy and len(app.rows)==1
        key = app.tree.get_children()[0]
        fields = dict(zip(app.tree['columns'], app.tree.item(key,'values')))
        assert fields['title']=='Accounting'
        assert fields['arketype']==display_category('ARK-01','ark')
        assert fields['usage']==display_category('PRF-20','prf')
        assert tuple(app.tree['displaycolumns']) == columns_for('manager', 'Essential', tuple(app.tree['columns']))
        for preset in PRESET_NAMES:
            app.column_views.choice.set(preset)
            app.column_views.apply()
            assert tuple(app.tree['displaycolumns']) == columns_for('manager',preset,tuple(app.tree['columns']))
            assert app.tree.selection() == (key,)
        app.open_semantic_dossier()
        assert app.winfo_exists()
        assert descriptor.read_bytes()==before
    finally:
        app.destroy()


@pytest.mark.skipif(os.name != 'nt' and not os.environ.get('DISPLAY'), reason='GUI display required')
def test_analysis_center_column_views_have_same_names(tmp_path, monkeypatch):
    from kristal_manager import gui
    monkeypatch.setattr(gui,'save_settings',lambda *_:None)
    app = gui.ManagerWindow()
    try:
        app.open_global_center()
        panel = app._global_dialog
        assert panel is not None
        for preset in PRESET_NAMES:
            panel.column_views.choice.set(preset)
            panel.column_views.apply()
            assert tuple(panel.table['displaycolumns']) == columns_for('analysis',preset,tuple(panel.table['columns']))
        assert 'unesco_review' in panel.table['columns']
        assert 'semantic_role_ai' in panel.table['columns']
        panel.destroy()
    finally:
        app.destroy()
