from __future__ import annotations
import base64, json, os
from datetime import datetime,timezone,timedelta
from pathlib import Path
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from kristal_manager.publication_gate import (
    AUTH_FORMAT, QUAL_FORMAT, TRUST_FORMAT, REVOCATION_FORMAT, PublicGateError,
    candidate_rows, candidate_digest, canonical, sha256, verify_public_write,
)

STATE='sha256:'+'a'*64

def iso(days=30):
    return (datetime.now(timezone.utc)+timedelta(days=days)).replace(microsecond=0).isoformat().replace('+00:00','Z')

def setup(tmp):
    src=tmp/'author';src.mkdir(); (src/'AI_START_HERE.md').write_text('Hello',encoding='utf8')
    (src/'state').mkdir();(src/'state/state-snapshot.json').write_text('{"demo":1}',encoding='utf8')
    root=tmp/'trust';root.mkdir()
    a,q=Ed25519PrivateKey.generate(),Ed25519PrivateKey.generate()
    def keystr(k):return base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode('ascii')
    def write(rel, obj):
        path=root/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj),encoding='utf8')
    def signed(k,p):return {'payload':p,'signature':base64.b64encode(k.sign(canonical(p))).decode('ascii')}
    trust={'format':TRUST_FORMAT,'approver_public_key':keystr(a),'qualifier_public_key':keystr(q)}
    write('trust.json',trust)
    os.environ['KRISTAL_C2_TRUST_PIN']=sha256(canonical(trust))
    write('revocations.json',{'format':REVOCATION_FORMAT,'revoked_grant_ids':[]})
    paths=['AI_START_HERE.md','state/state-snapshot.json']
    grant={'format':AUTH_FORMAT,'grant_id':'grant-z-1','slug':'zoology','state_ref':'urn:kristal:state:zoology','repository':'Rejean-McCormick/kristal-public','allowed_paths':paths,'expires_at':iso()}
    qualification={'format':QUAL_FORMAT,'grant_id':'grant-z-1','operation':'sync','slug':'zoology','state_ref':'urn:kristal:state:zoology','repository':'Rejean-McCormick/kristal-public','state_commitment':STATE,'candidate_digest':candidate_digest(candidate_rows(src,paths)),'expires_at':iso(1),'result':'PASS'}
    write('grants/zoology.json',signed(a,grant))
    write('qualifications/zoology-sync.json',signed(q,qualification))
    def check(**kw):
        args=dict(operation='sync',slug='zoology',state_ref='urn:kristal:state:zoology',repository='Rejean-McCormick/kristal-public',local_root=src,paths=paths,state_commitment=STATE,policy_dir=root)
        args.update(kw)
        return verify_public_write(**args)
    return src,root,grant,qualification,check,write,signed,a,q

def test_signed_approval_and_exact_independent_attestation_accept(tmp_path):
    *_,check,write,signed,a,q=setup(tmp_path)
    assert check()['result']=='AUTHORIZED_AND_QUALIFIED'

def test_missing_trust_fails_closed(tmp_path,monkeypatch):
    src,root,grant,qual,check,*_=setup(tmp_path)
    with pytest.raises(PublicGateError,match='Missing or invalid'):verify_public_write(operation='sync',slug='zoology',state_ref='urn:kristal:state:zoology',repository='Rejean-McCormick/kristal-public',local_root=src,paths=['AI_START_HERE.md'],state_commitment=STATE,policy_dir=root/'missing')

def test_changed_bytes_invalidate_qualification(tmp_path):
    src,root,grant,qual,check,*_=setup(tmp_path)
    (src/'AI_START_HERE.md').write_text('Changed')
    with pytest.raises(PublicGateError,match='Candidate bytes'):check()

def test_revoked_grant_denied(tmp_path):
    src,root,grant,qual,check,write,*_=setup(tmp_path)
    write('revocations.json',{'format':REVOCATION_FORMAT,'revoked_grant_ids':['grant-z-1']})
    with pytest.raises(PublicGateError,match='revoked'):check()

def test_unapproved_path_denied(tmp_path):
    src,root,grant,qual,check,*_=setup(tmp_path)
    (src/'new.json').write_text('{}')
    with pytest.raises(PublicGateError,match='unapproved'):check(paths=['new.json'])

def test_tampered_grant_signature_denied(tmp_path):
    src,root,grant,qual,check,write,signed,a,q=setup(tmp_path)
    changed=dict(grant,repository='someone/else')
    write('grants/zoology.json',{'payload':changed,'signature':signed(a,grant)['signature']})
    with pytest.raises(PublicGateError,match='signature'):check()

def test_wrong_attestation_operation_denied(tmp_path):
    src,root,grant,qual,check,write,signed,a,q=setup(tmp_path)
    write('qualifications/zoology-sync.json',signed(q,dict(qual,operation='publish')))
    with pytest.raises(PublicGateError,match='different grant'):check()

def test_qualification_must_be_current(tmp_path):
    src,root,grant,qual,check,write,signed,a,q=setup(tmp_path)
    write('qualifications/zoology-sync.json',signed(q,dict(qual,expires_at=iso(-1))))
    with pytest.raises(PublicGateError,match='expired'):check()

def test_wrong_destination_is_denied(tmp_path):
    src,root,grant,qual,check,write,signed,a,q=setup(tmp_path)
    with pytest.raises(PublicGateError,match='destination'):verify_public_write(operation='sync',slug='zoology',state_ref='urn:kristal:state:zoology',repository='unknown/public',local_root=src,paths=['AI_START_HERE.md'],state_commitment=STATE,policy_dir=root)


def test_public_manager_sync_denied_before_remote_queries(tmp_path,monkeypatch):
    import kristal_manager.core as core
    src=tmp_path/'local';src.mkdir()
    (src/'AI_START_HERE.md').write_text('hello')
    entry={'path':str(src),'slug':'zoology','publication_target':'public','title':'Zoology'}
    surface={'slug':'zoology','state_ref':'urn:kristal:state:zoology','target_root':'kristals/zoology',
             'state_logical_commitment':{'digest':STATE},'files':[{'path':'AI_START_HERE.md'}]}
    monkeypatch.setattr(core,'validate_local_cached',lambda *a,**k:{'result':'VALID'})
    monkeypatch.setattr(core,'find_framework_cli',lambda *a,**k:(None,None))
    monkeypatch.setattr(core,'prepare_github_read_surface',lambda *a,**k:{'local_path':str(src),'surface':surface,'entry':entry})
    monkeypatch.setattr(core,'resolve_publication_collection',lambda *a,**k:{'repository':'Rejean-McCormick/kristal-public'})
    monkeypatch.delenv('KRISTAL_C2_POLICY_DIR',raising=False)
    monkeypatch.setattr(core,'github_remote_json_file',lambda *a,**k:(_ for _ in ()).throw(AssertionError('remote must not be queried')))
    with pytest.raises(core.ManagerError,match='blocked'):
        core.sync_local_to_github(entry,workspace_root=tmp_path,network_config=tmp_path/'network.toml')


def test_public_manager_batch_denied_before_checkout(tmp_path,monkeypatch):
    import kristal_manager.core as core
    src=tmp_path/'local';src.mkdir();(src/'AI_START_HERE.md').write_text('hello')
    surface={'slug':'zoology','state_ref':'urn:kristal:state:zoology','target_root':'kristals/zoology',
             'state_logical_commitment':{'digest':STATE},'files':[{'path':'AI_START_HERE.md'}]}
    prepared={'local_path':str(src),'surface':surface,'entry':{'slug':'zoology'}}
    monkeypatch.setattr(core,'resolve_publication_collection',lambda *a,**k:{'repository':'Rejean-McCormick/kristal-public'})
    monkeypatch.setattr(core,'ensure_collection_checkout',lambda **kw:(_ for _ in ()).throw(AssertionError('checkout must not be touched')))
    monkeypatch.delenv('KRISTAL_C2_POLICY_DIR',raising=False)
    with pytest.raises(core.ManagerError,match='blocked before checkout'):
        core._sync_prepared_collection('public',[prepared],workspace_root=tmp_path,network_config=tmp_path/'network.toml',sync_cli=None,framework_sha=None)


def test_public_full_workspace_backup_forbidden_before_github_operations(tmp_path,monkeypatch):
    import kristal_manager.core as core
    folder=tmp_path/'local';folder.mkdir()
    monkeypatch.setattr(core,'ensure_backup_repo',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('must not touch GitHub')))
    with pytest.raises(core.ManagerError,match='full-workspace backup disabled'):
        core.backup_local(folder,owner='Rejean-McCormick',repo='public-backup',visibility='public')
