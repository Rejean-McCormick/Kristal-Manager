"""Regression coverage for alpha.12 read-only recovery and Konstellation export."""
from pathlib import Path
import hashlib
import json
import os
import sys
import zipfile
import pytest
from kristal_manager.core import detect_kristal, scan_roots, ManagerError, sync_local_to_github, backup_local, import_local
from kristal_manager.inventory import inventory, save_private_inventory, FORMAT
from kristal_manager.cli import main


def workspace(root: Path, name: str, state_ref=None, commitment='a') -> Path:
    p=root/name;p.mkdir(parents=True)
    (p/'kristal.workspace.json').write_text(json.dumps({
       'format':'kristal.local-workspace/3.2.0','title':name,'slug':name.lower(),
       'state_ref':state_ref or f'urn:kristal:state:{name.lower()}',
       'native_model':{'kind':'experimental_graph'},
       'target':{'hosted_network_baseline':'kristal.hosting/10.0'},
       'portable_ai':{'enabled':False}}))
    state={'schema_version':'9.0','artifact_type':'kristal_state_snapshot',
           'state_ref':state_ref or f'urn:kristal:state:{name.lower()}',
           'logical_commitment':{'profile':'kristal.state-commitment/jcs-sha256-v1','digest':'sha256:'+commitment*64},
           'members':[],'references':[],'parents':[]}
    target=p/'state/state-snapshot.json';target.parent.mkdir()
    target.write_text(json.dumps(state))
    return p


def test_fleet_inventory_structure(tmp_path):
    workspace(tmp_path,'Alpha');workspace(tmp_path,'Beta')
    out=inventory([tmp_path]);assert out['format']==FORMAT
    assert out['record_count']==2
    for row in out['records']:
        assert row['readiness']=='READY'
        assert row['availability']=='local'
        assert row['qualification']=='NOT_ESTABLISHED'
        assert row['publication']=='NOT_ESTABLISHED'
        assert row['archetype']=='UNDECLARED'
        assert row['state_ref'].startswith('urn:kristal:')
        assert 'local_path' not in row


def test_export_can_include_path_only_by_explicit_opt_in(tmp_path):
    k=workspace(tmp_path,'Alpha')
    assert inventory([tmp_path],include_paths=True)['records'][0]['local_path']==str(k.resolve())


def test_duplicate_identity_reported_not_merged(tmp_path):
    workspace(tmp_path,'Alpha',state_ref='urn:shared')
    workspace(tmp_path,'Beta',state_ref='urn:shared')
    out=inventory([tmp_path]);assert out['record_count']==2
    assert all(x['identity_collision'] and x['readiness']=='IDENTITY COLLISION' for x in out['records'])


def test_same_slug_different_state_refs_remain_distinct(tmp_path):
    workspace(tmp_path,'Alpha',state_ref='urn:a')
    p=workspace(tmp_path,'Beta',state_ref='urn:b')
    obj=json.loads((p/'kristal.workspace.json').read_text());obj['slug']='alpha'
    (p/'kristal.workspace.json').write_text(json.dumps(obj))
    out=inventory([tmp_path]);assert len(out['records'])==2
    assert {x['state_ref'] for x in out['records']}=={'urn:a','urn:b'}


def test_conflicting_local_states_fail_closed(tmp_path):
    p=workspace(tmp_path,'Alpha')
    current=p/'state/state-snapshot.json'
    obj=json.loads(current.read_text());obj['logical_commitment']['digest']='sha256:'+'b'*64
    other=p/'build/v9/state-snapshot.json';other.parent.mkdir(parents=True);other.write_text(json.dumps(obj))
    rec=detect_kristal(p)
    assert rec['readiness']=='STATE CONFLICT'
    assert rec['state_conflict']


def test_private_file_export_no_overwrite(tmp_path):
    workspace(tmp_path,'Alpha')
    payload=inventory([tmp_path]);file=tmp_path/'inventory.json'
    save_private_inventory(payload,file)
    assert json.loads(file.read_text())['format']==FORMAT
    if os.name!='nt':assert (file.stat().st_mode & 0o077)==0
    with pytest.raises(ManagerError,match='overwrite'):
        save_private_inventory(payload,file)


def test_file_export_symlink_denied(tmp_path):
    target=tmp_path/'real';target.write_text('safe')
    link=tmp_path/'link'
    try:link.symlink_to(target)
    except OSError:pytest.skip('symlinks unavailable')
    with pytest.raises(ManagerError):save_private_inventory({'records':[]},link,overwrite=True)
    assert target.read_text()=='safe'


def test_cli_scan_and_export(tmp_path,capsys):
    workspace(tmp_path,'Alpha')
    assert main(['scan',str(tmp_path)])==0
    assert 'Alpha' in capsys.readouterr().out
    output=tmp_path/'out.json'
    assert main(['export',str(tmp_path),'--output',str(output)])==0
    d=json.loads(output.read_text())
    assert len(d['records'])==1


def test_remote_mutations_unavailable_even_if_requested(tmp_path):
    workspace(tmp_path,'Alpha')
    with pytest.raises(ManagerError,match='blocked'):
        sync_local_to_github({'path':str(tmp_path/'Alpha')},workspace_root=tmp_path,
                             network_config=tmp_path/'network.toml')
    with pytest.raises(ManagerError,match='blocked'):
        backup_local(tmp_path/'Alpha',owner='anyone',repo='test',visibility='public')


def test_archive_traversal_forbidden(tmp_path):
    f=tmp_path/'danger.zip'
    with zipfile.ZipFile(f,'w') as z:z.writestr('../outside.txt','x')
    with pytest.raises(ManagerError,match='traversal'):
        import_local(f,tmp_path/'dest')
    assert not (tmp_path/'outside.txt').exists()


def test_no_canonical_files_read_or_modified(tmp_path):
    p=workspace(tmp_path,'Alpha')
    secret=p/'canon/domain/private.json';secret.parent.mkdir(parents=True)
    secret.write_text('{"secret":"do-not-export"}')
    before=hashlib.sha256(secret.read_bytes()).hexdigest()
    serialized=json.dumps(inventory([tmp_path]))
    assert 'do-not-export' not in serialized
    assert hashlib.sha256(secret.read_bytes()).hexdigest()==before
