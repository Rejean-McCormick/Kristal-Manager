"""Regressions for the opt-in local Windows folder icon workflow.

Uses the Node local server on localhost; no Windows shell invocation is required for
checking read-only scan, disabled writes, or explicit .ico / desktop.ini output.
"""
import hashlib
import json
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[1] / 'tools' / 'icon-generator' / 'server.mjs'


def _snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def _json(url, suffix):
    with urllib.request.urlopen(url + suffix, timeout=3) as r:
        return json.loads(r.read())


def _post(url, suffix, data, content_type):
    req = urllib.request.Request(url + suffix, data, method='POST', headers={'Content-Type': content_type})
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _run_server(root, apply=False):
    cmd = ['node', str(SERVER), '--locals', str(root)] + (['--enable-local-apply'] if apply else [])
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        for _ in range(15):
            line = p.stdout.readline()
            if 'Ouverture:' in line:
                return p, line.split('Ouverture:', 1)[1].strip()
        raise AssertionError('local generator did not listen')
    except Exception:
        p.terminate()
        p.wait(timeout=5)
        raise


def _workspace(folder, classification):
    folder.mkdir()
    (folder/'kristal.workspace.json').write_text(json.dumps({
        'format':'kristal.local-workspace/3.2.0', 'title':folder.name,
        'state_ref':'urn:kristal:sample:state','classification':classification}),encoding='utf8')


@pytest.mark.skipif(not shutil.which('node'), reason='Node required')
def test_local_preview_readonly_and_optin_windows_files(tmp_path):
    good=tmp_path/'Kristal-Catho'
    unmapped=tmp_path/'Kristal-Unmapped'
    inconsistent=tmp_path/'Kristal-Inconsistent'
    _workspace(good, {'unesco_thesaurus':{'kos_id':'kos:unesco-thesaurus','microthesauri':['3.20']}})
    _workspace(unmapped, {'isced_f2013':{'broad_fields':['02']}})
    _workspace(inconsistent, {'unesco_thesaurus':{'domains':['6'],'microthesauri':['3.20']}})
    (unmapped/'.kristal').mkdir()
    (unmapped/'.kristal'/'icon-profile.json').write_text(json.dumps({
        'profile':'kristal-icon/1.0', 'classification':{'scheme':'ISCED-F 2013'},
        'domains':[{'code':'02'}]}),encoding='utf8')
    unchanged=_snapshot(tmp_path)
    proc,url=_run_server(tmp_path)
    try:
        status=_json(url,'api/status')
        assert status['mode']=='locals' and not status['local_apply_enabled']
        assert status['scan']['scanned']==3
        assert set(status['scan']['unresolved_unesco'])=={'Kristal-Unmapped','Kristal-Inconsistent'}
        catalog=_json(url,'api/registry')
        profiles={e['kristal_id']:e['presentation'].get('icon') for e in catalog['entries']}
        assert profiles['Kristal-Catho']['domains'][0]['code']=='3'
        assert profiles['Kristal-Unmapped'] is None
        assert profiles['Kristal-Inconsistent'] is None
        assert _post(url,'api/icon?filename=KR-REF-UT3-M1.ico',b'A'*50,'image/x-icon')[0]==403
        assert _post(url,'api/finalize',b'{}','application/json')[0]==403
        assert _snapshot(tmp_path)==unchanged
    finally:
        proc.terminate()
        proc.wait(timeout=5)

    proc,url=_run_server(tmp_path,apply=True)
    try:
        assert _snapshot(tmp_path)==unchanged  # even enabled: scan itself cannot write
        filename='KR-REF-UT3-M1.ico'
        ico=b'\0\0\1\0\1\0'+bytes([16,16,0,0,1,0,32,0,8,0,0,0,22,0,0,0])+b'\x89PNG\r\n\x1a\n'+b'\0'*16
        assert _post(url,'api/icon?filename='+filename,b'not an ICO'*10,'image/x-icon')[0]==400
        status,resp=_post(url,'api/icon?filename='+filename,ico,'image/x-icon')
        assert status==200 and resp['copied']==1
        status,resp=_post(url,'api/finalize',b'{}','application/json')
        assert status==200 and resp['counts']['applied']==1
        assert (good/'.kristal'/filename).exists()
        assert (good/'desktop.ini').read_bytes().startswith(b'\xff\xfe')
        assert json.loads((good/'.kristal'/'icon-profile.json').read_text())['classification']['scheme']=='UNESCO Thesaurus'
        assert not (unmapped/'desktop.ini').exists() and not (inconsistent/'desktop.ini').exists()
        assert not (tmp_path/'_registry').exists()
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_default_permission_is_off_and_not_persisted():
    from kristal_manager import gui
    # This property exists per instance, not in load_settings/save_settings.
    assert 'custom_folder_icons_enabled' in gui.ManagerWindow.__init__.__code__.co_names
    assert False in gui.ManagerWindow.__init__.__code__.co_consts
    from kristal_manager import ui_prefs
    assert 'custom_folder_icons_enabled' not in ui_prefs.load_settings.__code__.co_names
