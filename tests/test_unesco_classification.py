"""The UNESCO Thesaurus is the only active subject-domain classification."""
import json
from pathlib import Path
from kristal_manager.classification_bridge import reference, observe, build_audit, audit_html, display_domain, display_micro
from kristal_manager.core import detect_kristal
from kristal_manager.inventory import inventory


def create(root: Path, data: dict, icon_codes=None, legacy=False):
    root.mkdir(parents=True)
    content={'format':'kristal.local-workspace/3.2.0','title':root.name,
             'slug':root.name.casefold(),'state_ref':f'urn:kristal:{root.name}:state',**data}
    (root/'kristal.workspace.json').write_text(json.dumps(content),encoding='utf8')
    if icon_codes is not None:
        (root/'.kristal').mkdir()
        (root/'.kristal'/'icon-profile.json').write_text(json.dumps({
            'profile':'kristal-icon/1.0',
            'classification':{'scheme':'ISCED-F 2013' if legacy else 'UNESCO Thesaurus'},
            'domains':[{'code':x} for x in icon_codes]}),encoding='utf8')
    return detect_kristal(root)


def test_reference_pinned_seven_domains_eighty_eight_microthesauri():
    r=reference()
    assert len(r['domains'])==7 and len(r['microthesauri'])==88
    assert r['domains']['3']['label_en']=='Culture'
    assert r['microthesauri']['3.20']['label_en']=='Religion'
    assert 'isced' not in r
    assert r['domains']['7']['kristall_default_role'] in ('facet_root','category_root','facet_category')


def test_no_isced_or_title_auto_conversion(tmp_path):
    row=create(tmp_path/'Kristal-Catho',{'subject':{'domain':'religion'},
        'classification':{'isced_f2013':{'broad_fields':['02']}}},['02'],legacy=True)
    obs=observe(row)
    assert obs['unesco']['domain_codes']==[]
    assert obs['legacy_icon_migration_needed']
    assert 'isced_f2013' not in obs
    assert display_domain(obs)=='Unmapped'
    assert obs['conformity']=='NOT_EVALUATED'


def test_explicit_unesco_mappings_use_canonical_codes_and_uris(tmp_path):
    r=reference()
    row=create(tmp_path/'Kristal-Catho',{'classification':{'unesco_thesaurus':{
        'kos_id':'kos:unesco-thesaurus',
        'domains':[r['domains']['3']['uri']],
        'microthesauri':[r['microthesauri']['3.20']['uri']]}}},['3'])
    obs=observe(row)
    assert obs['unesco']['domain_codes']==['3']
    assert obs['unesco']['microthesaurus_codes']==['3.20']
    assert obs['unesco']['status']=='Declared'
    assert not obs['legacy_icon_migration_needed']
    assert not obs['issues']
    assert 'Religion' in display_micro(obs)


def test_incompatible_and_unrecognized_mapping_is_flagged(tmp_path):
    row=create(tmp_path/'Kristal-A',{'classification':{'unesco_thesaurus':{
        'domain':'2','microthesaurus':'3.20'}}})
    obs=observe(row)
    assert obs['unesco']['status']=='Review'
    assert any('does not contain' in msg for msg in obs['issues'])
    row2=create(tmp_path/'Kristal-B',{'classification':{'unesco':{
        'microthesauri':['2.999','imaginary']}}})
    assert any('Unknown UNESCO microthesaurus' in x for x in observe(row2)['issues'])


def test_framework_seed_is_hint_not_declaration(tmp_path):
    row=create(tmp_path/'Kristal-A',{'subject':{'id':'KQ5058'}},['07'],legacy=True)
    obs=observe(row)
    assert obs['unesco']['status']=='Seed hint only'
    assert obs['unesco']['domain_codes']==[]
    assert obs['unesco']['seed_hint']['subject_kq']=='KQ5058'


def test_audit_inventory_no_active_isced_and_escapes_html(tmp_path):
    a=create(tmp_path/'Kristal-A',{'title':'<script>alert(1)</script>'},['02'],legacy=True)
    report=build_audit([a])
    assert report['counts']['legacy_icons_pending']==1
    assert report['counts']['unesco_unmapped']==1
    assert 'isced_observed' not in report['counts']
    html=audit_html(report)
    assert '&lt;script&gt;' in html and '<script>' not in html
    records=inventory([tmp_path])['records']
    assert len(records)==1
    assert records[0]['legacy_icon_migration_needed'] is True
    assert 'isced_f2013' not in records[0]


def test_gui_unesco_only_filter_and_audit_panel(tmp_path,monkeypatch):
    import os,time,pytest
    if os.name!='nt':
        import subprocess
        if not os.environ.get('DISPLAY') or subprocess.run(['sh','-c','xdpyinfo >/dev/null 2>&1'],timeout=5).returncode:
            pytest.skip('requires graphical display')
    from kristal_manager import gui
    from kristal_manager.classification_panel import ClassificationPanel
    root=tmp_path/'locals'
    create(root/'Kristal-A',{'classification':{'unesco_thesaurus':{'microthesauri':['3.20']}}},['3'])
    create(root/'Kristal-B',{},['02'],legacy=True)
    monkeypatch.setattr(gui,'save_settings',lambda *_:None)
    app=gui.ManagerWindow()
    try:
        app.path_var.set(str(root));app.start_scan()
        stop=time.monotonic()+10
        while app.busy and time.monotonic()<stop:
            app.update();time.sleep(.01)
        app.update()
        assert len(app.tree.get_children())==2
        assert 'isced' not in app.tree['columns']
        app.category_var.set('3 Culture');app.refresh()
        assert len(app.tree.get_children())==1
        panel=ClassificationPanel(app)
        try:
            assert panel.report['counts']['legacy_icons_pending']==1
        finally:panel.destroy()
    finally:app.destroy()
