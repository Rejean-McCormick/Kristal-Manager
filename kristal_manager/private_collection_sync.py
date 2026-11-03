"""Offline, selected-only transfer of Kit reader surfaces into a PRIVATE collection checkout.

Does not stage/commit/push, read remote visibility, provision nodes, certify C1/C2/C3,
or write the PUBLIC checkout. Existing unselected members remain byte-for-byte intact.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import uuid

from .core import ManagerError
from .publication_stage import _canonical, _hash, SLUG, POLICY

SHA = re.compile(r'^sha256:[0-9a-f]{64}$')
GITHUB = re.compile(r'^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([\w.-]+/[\w.-]+?)(?:\.git)?/?$', re.I)
DENIED = {'.env', '.npmrc', '.pypirc', 'id_rsa', 'id_ed25519', 'credentials.json', 'secrets.json', 'network.toml', 'trust.json', 'revocations.json'}
DENIED_EXT = ('.pem','.key','.pfx','.p12','.token','.sqlite','.sqlite3','.db')


def _err(message):
    raise ManagerError(message)


def _rel(path):
    if not isinstance(path, str) or not path or '\\' in path or ':' in path or '\x00' in path:
        _err('Chemin de surface non sûr')
    parts = path.split('/')
    if any(x in ('', '.', '..') for x in parts) or path.startswith('/'):
        _err('Traversée de répertoire interdite')
    for x in parts:
        l = x.lower()
        if l in ('.git','.ssh','.venv','__pycache__','node_modules','secrets','grants','qualifications'):
            _err('Composant sensible non publiable dans une surface : ' + x)
    name=parts[-1].lower()
    if name in DENIED or name.startswith('.env.') or name.endswith(DENIED_EXT):
        _err('Fichier sensible dans une surface de lecture : ' + name)
    return PurePosixPath(path)


def _json(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
        _err('Métadonnée absente ou invalide : ' + path.name)
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeError) as exc:
        raise ManagerError('Métadonnée JSON invalide : ' + path.name) from exc
    if not isinstance(value, dict):
        _err('Métadonnée attendue comme objet : ' + path.name)
    return value


def _sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for buf in iter(lambda:stream.read(1024*1024),b''):
            h.update(buf)
    return 'sha256:'+h.hexdigest()


def _files(root):
    if root.is_symlink() or not root.is_dir():
        _err('Dossier inexistant ou symbolique : ' + root.name)
    found=set()
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in dirs+files:
            f=Path(base)/name
            if f.is_symlink():
                _err('Lien symbolique interdit : ' + name)
        for name in files:
            relative=(Path(base)/name).relative_to(root).as_posix()
            _rel(relative)
            found.add(relative)
    if len({s.casefold() for s in found})!=len(found):
        _err('Collision de noms sous Windows')
    return found


def _validate_collection(root):
    """Verify all member files, manifest/index consistency and immutable digests."""
    folder=root/'kristals'
    if folder.is_symlink() or not folder.is_dir():
        _err('Dossier kristals/ absent')
    index=_json(folder/'index.json')
    if index.get('format')!='kristal.github-collection-index/1.0':
        _err('Format index de collection inattendu')
    rows=index.get('kristals')
    if not isinstance(rows,list) or type(index.get('count')) is not int or index['count']!=len(rows):
        _err('Nombre de Kristals incohérent dans index')
    projected={'format':'kristal.github-collection-index/1.0','kristals':rows}
    if index.get('index_digest')!=_hash(_canonical(projected)):
        _err('Empreinte de l’index incorrecte')
    if rows!=sorted(rows,key=lambda x:(x['slug'].encode('utf-8'),x['path'].encode('utf-8'))):
        _err('Ordre des membres de collection incohérent')
    slugs=[]
    for row in rows:
        if not isinstance(row,dict):_err('Entrée d’index invalide')
        slug=row.get('slug')
        if not isinstance(slug,str) or not SLUG.fullmatch(slug) or row.get('path')!='kristals/'+slug:
            _err('Identité de membre invalide')
        limited = row.get('entrypoint') == 'kristals/'+slug+'/README.md'
        if row.get('entrypoint') not in ('kristals/'+slug+'/README.md','kristals/'+slug+'/AI_START_HERE.md'):
            _err('Entrée de lecture invalide')
        slugs.append(slug)
        member=folder/slug
        listed=_files(member)
        manifest=_json(member/'.kristal/sync-manifest.json')
        expected={'slug':slug,'target_root':'kristals/'+slug,'entrypoint':('README.md' if limited else 'AI_START_HERE.md'),
                  'state_ref':row.get('state_ref'),'state_logical_commitment':row.get('state_logical_commitment'),
                  'surface_digest':row.get('surface_digest'),'file_count':row.get('file_count'),
                  'total_bytes':row.get('total_bytes'),
                  'materialization_object_count':row.get('materialization_object_count')}
        if any(manifest.get(k)!=v for k,v in expected.items()):
            _err('Index/manifest divergents : '+slug)
        expected_format='kristal.github-private-read-surface/1.0' if limited else 'kristal.github-read-surface/1.0'
        if manifest.get('format')!='kristal.github-sync-manifest/1.0' or manifest.get('read_surface_format')!=expected_format:
            _err('Format manifeste incorrect : '+slug)
        if not isinstance(manifest.get('policy'),dict) or any(manifest['policy'].get(k) is not True for k in POLICY):
            _err('Politique read-surface invalide : '+slug)
        commitment=row.get('state_logical_commitment')
        if not isinstance(commitment,dict) or not SHA.fullmatch(str(commitment.get('digest',''))):
            _err('Commitment invalide : '+slug)
        if not SHA.fullmatch(str(row.get('surface_digest',''))):
            _err('Digest de surface invalide : '+slug)
        entries=manifest.get('files')
        if not isinstance(entries,list) or len(entries)!=row.get('file_count'):
            _err('Fichiers manifestés incohérents : '+slug)
        wanted={'.kristal/sync-manifest.json'}
        digest_files=[]
        total=0
        for e in entries:
            if not isinstance(e,dict): _err('Entrée de fichier invalide')
            rel=_rel(e.get('path'))
            if rel.as_posix() in wanted:_err('Fichier dupliqué')
            wanted.add(rel.as_posix())
            f=member.joinpath(*rel.parts)
            if not f.is_file() or f.is_symlink():_err('Fichier manquant : '+rel.as_posix())
            size=f.stat().st_size
            if type(e.get('size')) is not int or size!=e['size'] or _sha(f)!=e.get('sha256'):
                _err('Taille ou SHA-256 invalide : '+rel.as_posix())
            total+=size
            digest_files.append(e)
        if wanted!=listed:
            _err('Fichier orphelin ou manquant dans '+slug+' : '+', '.join(sorted(wanted ^ listed)[:4]))
        if limited:
            if 'README.md' not in listed or len([e for e in entries if e.get('role')=='state_snapshot'])!=1:
                _err('Surface privée limitée sans README ni état V9 unique : '+slug)
            if any(p.startswith('ai/') or p.startswith('AI_') for p in listed):
                _err('Une surface privée limitée ne peut se présenter comme capsule AI : '+slug)
        elif not {'AI_START_HERE.md','AI_MANIFEST.json','ai/INDEX.json','state/state-snapshot.json'}<=listed:
            _err('Surface de lecture AI obligatoire absente : '+slug)
        if total!=row.get('total_bytes'):
            _err('Total des octets invalide : '+slug)
        ordered=sorted(digest_files,key=lambda x:x['path'].encode('utf-8'))
        if ordered!=digest_files:_err('Manifest désordonné')
        objects=[] if limited else _json(member/'ai/INDEX.json').get('materialization_blobs',[])
        if not isinstance(objects,list) or len(objects)!=row.get('materialization_object_count'):
            _err('Inventaire matérialisations invalide : '+slug)
        proj={'format':expected_format,'slug':slug,'state_ref':row['state_ref'],
              'state_logical_commitment':row['state_logical_commitment'],
              'entrypoint':('README.md' if limited else 'AI_START_HERE.md'),'files':ordered,'materialization_objects':objects}
        if _hash(_canonical(proj))!=row['surface_digest']:
            _err('Digest de surface incorrect : '+slug)
        if limited:
            state_rel=next(e['path'] for e in entries if e.get('role')=='state_snapshot')
            state=_json(member/state_rel)
            if state.get('artifact_type')!='kristal_state_snapshot' or state.get('schema_version')!='9.0' or \
               state.get('state_ref')!=row['state_ref'] or state.get('logical_commitment')!=commitment:
                _err('État V9 privé limité non lié au manifeste : '+slug)
    if len(set(slugs))!=len(slugs) or len({s.casefold() for s in slugs})!=len(slugs):
        _err('Membres dupliqués')
    actual={p.name for p in folder.iterdir() if p.is_dir()}
    if actual!=set(slugs):
        _err('Dossiers Kristal non indexés : '+', '.join(sorted(actual ^ set(slugs))))
    if any(p.is_symlink() for p in folder.iterdir()):_err('Lien symbolique dans collection')
    if {p.name for p in folder.iterdir() if p.is_file()}!={'index.json'}:
        _err('Fichier non indexé à la racine de collection')
    return index


def _git(checkout,*args):
    try:
        r=subprocess.run(['git','-C',str(checkout),*args],stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,timeout=20,check=False)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise ManagerError('Git local indisponible') from exc
    if r.returncode:
        _err('Commande Git locale non validée : '+ ' '.join(args[:2]))
    return r.stdout.decode('utf-8','strict').strip()


def _private_checkout(root):
    if root.name.casefold()!='kristal-private' or not root.is_dir() or root.is_symlink():
        _err('Destination attendue : checkout local kristal-private')
    if Path(_git(root,'rev-parse','--show-toplevel')).resolve()!=root:
        _err('La destination doit être racine exacte de son dépôt Git')
    if _git(root,'status','--porcelain=v1','--untracked-files=all'):
        _err('Dépôt privé non propre : inspecter les changements avant la copie')
    origin=_git(root,'remote','get-url','origin')
    push=_git(root,'remote','get-url','--push','origin')
    if origin!=push:_err('Remote push et origin différents')
    m=GITHUB.fullmatch(origin)
    if not m or m.group(1).split('/')[-1].casefold()!='kristal-private':
        _err('Remote GitHub privé non reconnu ; aucun accès réseau vérifié')
    node=_json(root/'.kristal/node.json')
    binding=_json(root/'.kristal/bindings/github.json')
    caps=_json(root/'.kristal/capabilities.json')
    if node.get('schema_version')!='10.0' or node.get('artifact_type')!='kristal_node_manifest' or 'collection' not in node.get('roles',[]):
        _err('Identité V10 collection absente')
    if caps.get('schema_version')!='10.0' or caps.get('artifact_type')!='kristal_v10_capabilities':
        _err('Capabilities Bootstrap absentes')
    if binding.get('schema_version')!='10.0' or binding.get('artifact_type')!='kristal_host_binding' or binding.get('node_id')!=node.get('node_id'):
        _err('Binding de nœud incohérent')
    if binding.get('resource',{}).get('visibility')!='private' or binding.get('resource',{}).get('kind')!='repository':
        _err('Ce dépôt ne déclare pas une visibilité privée')
    if binding.get('profile',{}).get('id')!='kristal.host/github':
        _err('Profil GitHub inattendu')
    repo=m.group(1)
    if str(binding['resource'].get('locator','')).casefold()!='github://'+repo.casefold():
        _err('Binding et origin GitHub ne correspondent pas')
    refs=node.get('bindings')
    if not isinstance(refs,list) or not any(isinstance(x,dict) and x.get('binding_id')==binding.get('binding_id') and x.get('descriptor')=='.kristal/bindings/github.json' for x in refs):
        _err('Le nœud ne référence pas le binding GitHub')
    return _git(root,'rev-parse','HEAD'),origin


def plan_private_sync(*, candidate: Path, checkout: Path, slugs: list[str]):
    candidate=Path(candidate).expanduser().resolve(strict=True)
    checkout=Path(checkout).expanduser().resolve(strict=True)
    if candidate==checkout or candidate.is_relative_to(checkout) or checkout.is_relative_to(candidate):
        _err('Candidat et clone doivent être séparés')
    if not slugs or len(slugs)!=len(set(slugs)) or any(not isinstance(s,str) or not SLUG.fullmatch(s) for s in slugs):
        _err('Sélection explicite de slugs uniques exigée')
    head, origin=_private_checkout(checkout)
    idx=_validate_collection(candidate)
    selected={s for s in slugs}
    if set(row['slug'] for row in idx['kristals'])!=selected:
        _err('La sélection ne correspond pas exactement au candidat préparé')
    folder=checkout/'kristals'
    if folder.is_symlink():_err('Collection de destination symbolique')
    if (folder/'index.json').is_file():
        previous=_validate_collection(checkout)
    else:
        if folder.exists() and list(folder.iterdir()):
            _err('Collection déjà peuplée mais sans index valide : aucune suppression automatique')
        previous={'format':'kristal.github-collection-index/1.0','kristals':[]}
    existing={r['slug']:r for r in previous['kristals']}
    incoming={r['slug']:r for r in idx['kristals']}
    merged={**existing,**incoming}
    rows=sorted(merged.values(),key=lambda x:(x['slug'].encode('utf8'),x['path'].encode('utf8')))
    projection={'format':'kristal.github-collection-index/1.0','kristals':rows}
    next_index={**projection,'count':len(rows),'index_digest':_hash(_canonical(projection)),
        'note':'Derived navigation index for GitHub/AI discovery; not semantic authority.'}
    projects=[]
    for slug in sorted(selected):
        old=existing.get(slug)
        oldfiles=set()
        newfiles=_files(candidate/'kristals'/slug)
        if old:
            oldfiles=_files(folder/slug)
        changes=sorted(x for x in newfiles if x not in oldfiles or
                       _sha(candidate/'kristals'/slug/x)!=_sha(folder/slug/x))
        remove=sorted(oldfiles-newfiles)
        projects.append({'slug':slug,'mode':'UPDATE' if old else 'ADD',
                         'copy_or_update':changes,'retire_selected_only':remove})
    fingerprint={'candidate_index_sha':_sha(candidate/'kristals/index.json'),
                 'previous_index_sha':_sha(folder/'index.json') if (folder/'index.json').is_file() else None,
                 'git_HEAD':head,'origin':origin,
                 'slugs':sorted(selected),'projects':projects,'new_index_digest':next_index['index_digest']}
    token=_hash(_canonical(fingerprint))
    return {'status':'DRY_RUN','candidate':str(candidate),'checkout':str(checkout),
            'slugs':sorted(selected),'selected_count':len(selected),
            'preserved_count':len(existing.keys()-selected),'merged_count':len(rows),
            'projects':projects,'retire_count':sum(len(p['retire_selected_only']) for p in projects),
            'index_digest':next_index['index_digest'],
            'plan_token':token,'_next_index':next_index,
            'git_add':False,'git_commit':False,'git_push':False,'public_write':False,
            'remote_visibility_verified':False,
            'warning':'Visibilité privée déclarée localement seulement : confirmer ACL sur GitHub avant synchronisation manuelle.'}


def apply_private_sync(*,candidate:Path,checkout:Path,slugs:list[str],expected_token:str,allow_retire:bool=False):
    plan=plan_private_sync(candidate=candidate,checkout=checkout,slugs=slugs)
    if not expected_token or expected_token!=plan['plan_token']:
        _err('Prévisualisation périmée ; relancer la simulation avant toute écriture')
    if plan['retire_count'] and not allow_retire:
        _err('Des fichiers obsolètes seraient retirés des membres sélectionnés : consentement explicite requis')
    checkout=Path(plan['checkout']);candidate=Path(plan['candidate'])
    backuproot=checkout.parent/'KRISTAL-PRIVATE-SYNC-BACKUPS'
    if backuproot.exists() and (backuproot.is_symlink() or not backuproot.is_dir()):
        _err('Dossier de sauvegarde inaccessible')
    backuproot.mkdir(exist_ok=True)
    batch=backuproot/('private-sync-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:10])
    batch.mkdir()
    # Prepare all copies and the prospective index BEFORE touching any checkout member.
    moved=[]
    had_index=(checkout/'kristals/index.json').is_file()
    indexdest=checkout/'kristals/index.json'
    before_index=None
    try:
        (batch/'incoming').mkdir();(batch/'before').mkdir()
        for slug in plan['slugs']:
            shutil.copytree(candidate/'kristals'/slug,batch/'incoming'/slug,symlinks=False)
        # Full validation still covers the candidate and copy (all paths already verified at plan time).
        idx=plan['_next_index']
        (batch/'next-index.json').write_text(json.dumps(idx,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        if had_index:
            before_index=(batch/'before/index.json')
            shutil.copy2(indexdest,before_index)
        (checkout/'kristals').mkdir(exist_ok=True)
        for slug in plan['slugs']:
            old=checkout/'kristals'/slug
            prior=batch/'before'/slug
            if old.exists():
                os.replace(old,prior)
            moved.append((slug,old,prior))
            os.replace(batch/'incoming'/slug,old)
        os.replace(batch/'next-index.json',indexdest)
        # A full postflight catches schema or operation mistakes while backup still exists.
        _validate_collection(checkout)
        receipt={'format':'kristal.private-local-sync-receipt/1.0',
                 'status':'COPIED_LOCAL_ONLY','checkout':str(checkout),'slugs':plan['slugs'],
                 'plan_token':plan['plan_token'],'index_digest':idx['index_digest'],
                 'git_head_before':_git(checkout,'rev-parse','HEAD'),
                 'old_index_present':had_index,'old_index_sha256':_sha(before_index) if before_index else None,
                 'new_index_sha256':_sha(indexdest),
                 'members_sha256':{s:{x:_sha(checkout/'kristals'/s/x) for x in _files(checkout/'kristals'/s)} for s in plan['slugs']},
                 'previous_members':[slug for slug,_,prior in moved if prior.is_dir()],
                 'git_add':False,'git_commit':False,'git_push':False,'public_write':False,
                 'remote_visibility_verified':False}
        (batch/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        return {'status':'COPIED_LOCAL_ONLY','selected_count':len(plan['slugs']),
                'preserved_count':plan['preserved_count'],'checkout':str(checkout),
                'backup_receipt':str(batch/'receipt.json'),'projects':plan['projects'],
                'git_add':False,'git_commit':False,'git_push':False,'public_write':False,
                'next':'Inspecter GitHub Desktop ; vérifier ACL privées ; commit et synchronisation manuels.'}
    except Exception:
        # Roll back our own moves; NEVER run git reset/clean or touch unselected members.
        try:
            for slug,old,prior in reversed(moved):
                if old.is_dir():shutil.rmtree(old)
                if prior.is_dir():os.replace(prior,old)
            if had_index and before_index is not None and before_index.is_file():
                shutil.copy2(before_index,indexdest)
            elif not had_index:indexdest.unlink(missing_ok=True)
        except Exception as recovery_exc:
            raise ManagerError('Restauration incomplète : sauvegardes conservées à '+str(batch)) from recovery_exc
        raise


def rollback_private_sync(*,receipt:Path):
    receipt=Path(receipt).expanduser().resolve(strict=True)
    data=_json(receipt)
    if data.get('format')!='kristal.private-local-sync-receipt/1.0':
        _err('Reçu de restauration invalide')
    checkout=Path(data['checkout']).resolve(strict=True)
    if receipt.parent.parent.resolve()!= (checkout.parent/'KRISTAL-PRIVATE-SYNC-BACKUPS').resolve():
        _err('Sauvegarde située hors de l’emplacement attendu')
    # Do not roll back if Git checkout has new commits or operator modifications.
    if (receipt.parent/'RESTORED').exists():_err('Restauration déjà effectuée')
    if _git(checkout,'rev-parse','HEAD') != data.get('git_head_before'):
        _err('Des commits ont été créés depuis la copie : restauration refusée')
    if not (checkout/'kristals/index.json').is_file() or _sha(checkout/'kristals/index.json')!=data.get('new_index_sha256'):
        _err('Index modifié depuis la pose : restauration refusée')
    for slug, hashes in data['members_sha256'].items():
        folder=checkout/'kristals'/slug
        if _files(folder)!=set(hashes) or any(_sha(folder/name)!=h for name,h in hashes.items()):
            _err('Un membre a été modifié : restauration refusée')
    batch=receipt.parent
    # Refuse if old selected trees are missing from backup.
    for slug in data['previous_members']:
        if not (batch/'before'/slug).is_dir(): _err('Sauvegarde membre manquante')
    if data['old_index_present'] and _sha(batch/'before/index.json')!=data['old_index_sha256']:
        _err('Sauvegarde index altérée')
    # Validate no git commit was made since the transfer; working tree is intentionally dirty.
    # Receipt is one-shot: create a state flag to reject replay.
    if (batch/'RESTORED').exists():_err('Restauration déjà effectuée')
    for slug in data['slugs']:
        shutil.rmtree(checkout/'kristals'/slug)
        prior=batch/'before'/slug
        if prior.is_dir():os.replace(prior,checkout/'kristals'/slug)
    if data['old_index_present']:
        shutil.copy2(batch/'before/index.json',checkout/'kristals/index.json')
    else:(checkout/'kristals/index.json').unlink()
    (batch/'RESTORED').write_text('Restauration locale effectuée ; vérifier GitHub Desktop.\n',encoding='utf8')
    return {'status':'RESTORED_LOCAL_ONLY','selected_count':len(data['slugs']),'checkout':str(checkout)}
