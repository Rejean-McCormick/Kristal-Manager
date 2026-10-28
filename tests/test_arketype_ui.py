"""Separate Framework Arketype classification from technical profile and domain."""
import json
import os
import time
from pathlib import Path

import pytest
from kristal_manager.core import detect_kristal
from kristal_manager.workspace_tools import classification_of, arketype_of, usage_profile_of, category_of


def create_workspace(folder, classification=None):
    folder.mkdir(parents=True)
    ws = {'format':'kristal.local-workspace/3.2.0', 'title':'Kristal-Diagnostic',
          'slug':'kristal-diagnostic', 'profile':'layered',
          'subject':{'domain':'automotive'}}
    if classification is not None:
        ws['classification'] = classification
    (folder/'kristal.workspace.json').write_text(json.dumps(ws),encoding='utf8')


def test_arketype_prf_are_not_technical_profile_or_domain(tmp_path):
    folder = tmp_path/'Kristal-Diagnostic'
    declaration = {'arketype_version':'1.4.0','primary_archetype':'ARK-08',
                   'supporting_archetypes':['ARK-09'], 'primary_usage':'PRF-15',
                   'domain':'automotive', 'usage_family':'diagnosis'}
    create_workspace(folder, declaration)
    row = detect_kristal(folder)
    assert row['profile'] == 'layered'
    assert arketype_of(row) == 'ARK-08'
    assert usage_profile_of(row) == 'PRF-15'
    assert category_of(row) == 'automotive'
    assert classification_of(row)['supporting_archetypes'] == ['ARK-09']


def test_no_inference_of_missing_classification(tmp_path):
    folder=tmp_path/'Kristal-Diagnostic'
    create_workspace(folder)
    row=detect_kristal(folder)
    assert arketype_of(row) is None
    assert usage_profile_of(row) is None
    assert category_of(row) == 'automotive'


def test_derived_discovery_classification_fallback_without_inventing_ids():
    row={'path':'/nonexistent-kristal', 'kind':'local', 'readiness':'READY',
         'discovery':{'classification':{'primary_archetype':'ARK-08', 'primary_usage':'PRF-15',
                                        'domain':'automotive'}}}
    assert arketype_of(row) == 'ARK-08'
    assert usage_profile_of(row) == 'PRF-15'
    assert category_of(row) == 'automotive'
    row['discovery']['classification']['primary_archetype']='causal-diagnostic'
    assert arketype_of(row) is None


@pytest.mark.skipif(os.name != 'nt' and not os.environ.get('DISPLAY'), reason='requires graphical display')
def test_gui_displays_and_filters_arketype_usage(tmp_path, monkeypatch):
    from kristal_manager import gui
    root=tmp_path/'locals'
    create_workspace(root/'Kristal-Diagnostic',{
        'primary_archetype':'ARK-08', 'primary_usage':'PRF-15', 'domain':'automotive'})
    create_workspace(root/'Other')
    monkeypatch.setattr(gui,'save_settings',lambda *_:None)
    app=gui.ManagerWindow()
    try:
        app.path_var.set(str(root))
        app.start_scan()
        deadline=time.monotonic()+10
        while app.busy and time.monotonic()<deadline:
            app.update()
            time.sleep(.01)
        app.update()
        assert not app.busy
        assert 'arketype' in app.tree['columns']
        assert 'usage' in app.tree['columns']
        assert 'ARK-08' in app.arketype_choice['values']
        assert 'PRF-15' in app.usage_choice['values']
        app.arketype_var.set('ARK-08')
        app.refresh()
        assert len(app.tree.get_children()) == 1
        selected=app.tree.get_children()[0]
        values=app.tree.item(selected)['values']
        assert values[2] == 'ARK-08' and values[3] == 'PRF-15'
        app.arketype_var.set('Unclassified')
        app.refresh()
        assert len(app.tree.get_children()) == 1
        assert app.tree.item(app.tree.get_children()[0])['values'][2] == '—'
    finally:
        app.destroy()


def test_inventory_exports_distinct_arketype_usage_and_domain(tmp_path):
    from kristal_manager.inventory import inventory
    root=tmp_path/'locals'
    create_workspace(root/'Kristal-Diagnostic',{
        'primary_archetype':'ARK-08', 'primary_usage':'PRF-15', 'domain':'automotive'})
    record=inventory([root])['records'][0]
    assert record['archetype']=='ARK-08'
    assert record['usage_profile']=='PRF-15'
    assert record['domain_category']=='automotive'
    assert record['profile']=='layered'
    assert record['classification_verified'] is False
