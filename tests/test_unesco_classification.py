"""Pinned UNESCO/ISCED reference: read-only, no invented classifications."""
from __future__ import annotations
import json
from pathlib import Path
from kristal_manager.classification_bridge import (reference,observe,build_audit,audit_html,
                                                     display_domain,display_micro,display_isced)
from kristal_manager.core import detect_kristal
from kristal_manager.inventory import inventory


def create(root:Path, data:dict, icon_fields=None):
    root.mkdir(parents=True)
    content={'format':'kristal.local-workspace/3.2.0','title':'Kristal-Architecture','slug':'kristal-architecture',
             'state_ref':'urn:kristal:architecture:state',**data}
    (root/'kristal.workspace.json').write_text(json.dumps(content),encoding='utf8')
    if icon_fields is not None:
        (root/'.kristal').mkdir()
        (root/'.kristal'/'icon-profile.json').write_text(json.dumps({
            'profile':'kristal-icon/1.0','domains':[{'code':x} for x in icon_fields]}),encoding='utf8')
    return detect_kristal(root)


def test_reference_is_fixed_and_uri_based():
    r=reference()
    assert len(r['domains'])==7 and len(r['microthesauri'])==88
    assert r['microthesauri']['4.45']['label_en']=='Human settlements and land use'
    assert r['microthesauri']['4.45']['domain']=='4'
    assert r['domains']['7']['kristall_default_role'] in ('facet_root','category_root','facet_category')
    assert len(r['isced'])==11
    assert r['isced']['07']=='Engineering, manufacturing and construction'


def test_no_inference_from_name_or_legacy_domain(tmp_path):
    row=create(tmp_path/'Kristal-Architecture',{'subject':{'domain':'architecture'}},['07'])
    got=observe(row)
    assert got['unesco']['domain_codes']==[]
    assert got['unesco']['microthesaurus_codes']==[]
    assert got['unesco']['source']=='none'
    assert got['isced_f2013']['codes']==['07']
    assert got['legacy_domain']=='architecture'
    assert display_domain(got)=='Unmapped'
    assert got['conformity']=='NOT_EVALUATED'


def test_declared_unesco_uris_are_validated_without_guessing(tmp_path):
    r=reference()
    row=create(tmp_path/'Kristal-Architecture',{'classification':{'unesco_thesaurus':{
        'domains':[r['domains']['4']['uri']],
        'microthesauri':[r['microthesauri']['4.45']['uri']],
        'concept_uris':['https://vocabularies.unesco.org/example/explicit']},
        'isced_f2013':{'broad_fields':['07']}}},['07'])
    got=observe(row)
    assert got['unesco']['domain_codes']==['4']
    assert got['unesco']['microthesaurus_codes']==['4.45']
    assert got['unesco']['status']=='Declared'
    assert got['isced_f2013']['codes']==['07']
    assert not got['issues']
    assert '4.45' in display_micro(got)


def test_detects_mismatch_and_unknown_notations(tmp_path):
    row=create(tmp_path/'Kristal-Architecture',{'classification':{
        'unesco':{'domain':'2','microthesaurus':'4.45'},'isced_f2013':['06']}},['07'])
    obs=observe(row)
    assert obs['unesco']['status']=='Review'
    assert len(obs['issues'])==2
    assert any('domain does not contain' in m for m in obs['issues'])
    assert any('icon profile disagree' in m for m in obs['issues'])
    row2=create(tmp_path/'Different',{'classification':{
        'unesco':{'microthesauri':['2.999','not-a-UNESCO-code']}}},[])
    assert any('Unknown UNESCO microthesaurus' in m for m in observe(row2)['issues'])


def test_kq_seed_is_hint_not_declaration(tmp_path):
    row=create(tmp_path/'Kristal-Architecture',{'subject':{'id':'KQ5058'}},['07'])
    obs=observe(row)
    assert obs['unesco']['status']=='Seed hint only'
    assert obs['unesco']['domain_codes']==[]
    hint=obs['unesco']['seed_hint']
    assert hint['subject_kq']=='KQ5058'
    assert [x['notation'] for x in hint['placements']]==['4.45','6.45']
    assert 'not a declaration' in hint['note']


def test_audit_excludes_nested_snapshots_and_escapes_html(tmp_path):
    parent=tmp_path/'Kristal-A'; a=create(parent,{'title':'<script>alert(1)</script>'},['07'])
    nested=create(parent/'original-snapshot-before-activation',{'title':'snapshot'},[])
    nested['nested_under']=str(parent)
    audit=build_audit([a,nested])
    assert audit['counts']['kristals']==1
    assert audit['counts']['unesco_unmapped']==1
    assert audit['counts']['isced_observed']==1
    html=audit_html(audit)
    assert '&lt;script&gt;' in html and '<script>' not in html


def test_inventory_exports_separate_taxonomies(tmp_path):
    create(tmp_path/'Kristal-Architecture',{'classification':{
        'unesco':{'microthesaurus':'4.45'},'isced_f2013':{'broad_fields':['07']}}},['07'])
    inv=inventory([tmp_path]);record=inv['records'][0]
    assert record['unesco_thesaurus']['domain_codes']==['4']
    assert record['isced_f2013']['codes']==['07']
    assert record['classification_verified'] is False


def test_gui_unesco_filter_and_audit_panel(tmp_path, monkeypatch):
    import os, time
    import pytest
    if os.name!='nt' and not os.environ.get('DISPLAY'):
        pytest.skip('requires graphical display')
    from kristal_manager import gui
    from kristal_manager.classification_panel import ClassificationPanel
    root=tmp_path/'locals'
    create(root/'Kristal-A',{'title':'Kristal-A','classification':{
        'unesco_thesaurus':{'microthesauri':['4.45']}}},['07'])
    create(root/'Kristal-B',{'title':'Kristal-B'},['05'])
    monkeypatch.setattr(gui,'save_settings',lambda *_:None)
    app=gui.ManagerWindow()
    try:
        app.path_var.set(str(root));app.start_scan()
        stop=time.monotonic()+10
        while app.busy and time.monotonic()<stop:
            app.update();time.sleep(.01)
        app.update()
        assert not app.busy
        assert len(app.tree.get_children())==2
        assert app.tree.heading('category')['text']=='UNESCO domain'
        assert 'micro' in app.tree['columns'] and 'isced' in app.tree['columns']
        assert '4 Social and human sciences' in app.category_choice['values']
        app.category_var.set('4 Social and human sciences');app.refresh()
        assert len(app.tree.get_children())==1
        assert app._selected_row()['title']=='Kristal-A'
        app.micro_var.set('4.45 Human settlements and land use');app.refresh()
        assert len(app.tree.get_children())==1
        app.isced_var.set('05 Natural sciences, mathematics and statistics');app.refresh()
        assert len(app.tree.get_children())==0
        app.category_var.set('All UNESCO domains');app.micro_var.set('All microthesauri')
        app.isced_var.set('All ISCED fields');app.refresh()
        panel=ClassificationPanel(app)
        try:
            panel.update()
            assert panel.report['counts']['kristals']==2
            assert panel.report['counts']['unesco_declared']==1
            assert panel.report['counts']['isced_observed']==2
        finally:
            panel.destroy()
    finally:
        app.destroy()
