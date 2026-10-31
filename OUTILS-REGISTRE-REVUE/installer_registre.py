"""Conservative in-place integration with whatever Manager GUI is installed.

A full global_panel.py replacement would revert the user's Arketype and bundles
buttons. Therefore we insert only small, tested hooks, backing up originals.
"""
from __future__ import annotations

import datetime
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parent.parent
PKG=ROOT/'kristal_manager'
MARKER='REGISTRE-REVUE-2026-10-30'


def _insert_once(text:str, key:str, insert:str, *, filename:str)->str:
    if MARKER in text and insert in text:
        return text
    if text.count(key)!=1:
        raise ValueError(f'Point d’intégration incertain dans {filename}: {key!r} trouvé {text.count(key)} fois. Aucun remplacement.')
    return text.replace(key,insert+key,1)


def patch_analysis(s:str)->str:
    a='    priorities = Counter(item[\'priority\'] for item in items)\n'
    s=_insert_once(s,a,
        '    # REGISTRE-REVUE-2026-10-30 : avis historiques séparés des tests actuels.\n'
        '    from .review_registry import annotate_entries\n'
        '    review_summary = annotate_entries(items, source=root)\n',filename='global_analysis.py')
    k="              'entries': items,\n"
    if "'review_registry': review_summary," not in s:
        if s.count(k)!=1:raise ValueError('Bloc rapport global incompatible; aucun remplacement.')
        s=s.replace(k,"              'review_registry': review_summary,\n"+k,1)
    return s


def patch_panel(s:str)->str:
    # Hook method. Works with both the old and ARK/bundles enhanced panel.
    method='    def _restore_kristalizer(self):\n'
    s=_insert_once(s,method,
       '    # REGISTRE-REVUE-2026-10-30 : fenêtre dédiée, aucune écriture dans locals.\n'
       '    def _open_review_registry(self):\n'
       '        from .review_panel import ReviewRegistryPanel\n'
       '        ReviewRegistryPanel(self, self.manager.path_var.get())\n\n',filename='global_panel.py')
    # Button appended in the existing tools row, without replacing any prior buttons.
    anchor="        self.import_kristalizer_button.pack(side='left', padx=(7,0))\n"
    if 'text=\'Registre de revue…\'' not in s:
        if s.count(anchor)!=1:raise ValueError('Zone des outils Manager inconnue; aucun remplacement.')
        s=s.replace(anchor,anchor+
           "        ttk.Button(tools, text='Registre de revue…', command=self._open_review_registry).pack(side='left',padx=(7,0))\n",1)
    # Registered information is copyable in the ordinary report without replacing suggestions.
    copy_anchor="        if row.get('human_review'):\n"
    if "values.append('registre='" not in s:
        if s.count(copy_anchor)!=1:raise ValueError('Résumé ChatGPT Manager inconnu; aucun remplacement.')
        s=s.replace(copy_anchor,
            "        registered = row.get('registered_review')\n"
            "        if registered:\n"
            "            values.append('registre=' + ','.join(registered['archetype_recommendations'])\n"
            "                          + '/' + registered['archetype_review_status']\n"
            "                          + '/repères-' + registered['provenance_status']['status'])\n"+copy_anchor,1)
    return s


def _write_atomic(path:Path,content:str):
    fd,name=tempfile.mkstemp(prefix='.manager-revue-',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='') as out:
            out.write(content)
            out.flush();os.fsync(out.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


def install():
    current={}
    for name in ('global_analysis.py','global_panel.py'):
        file=PKG/name
        if not file.is_file() or file.is_symlink():
            raise ValueError(f'Manager absent ou fichier lié : {file}')
        current[file]=file.read_text(encoding='utf-8')
    changed={PKG/'global_analysis.py':patch_analysis(current[PKG/'global_analysis.py']),
             PKG/'global_panel.py':patch_panel(current[PKG/'global_panel.py'])}
    for path,data in changed.items():
        compile(data,str(path),'exec')
    sys.path.insert(0,str(ROOT))
    from kristal_manager.review_registry import load_registry
    reg=load_registry()  # no overwrite of existing decisions
    print(f"Registre disponible : {len(reg['entries'])} revues à {ROOT / 'catalogue' / 'registre_revue_kristals.json'}")
    if all(changed[p]==current[p] for p in current):
        print('Manager déjà intégré : aucune nouvelle écriture.');return
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backups=ROOT/'sauvegardes-registre-revue'/stamp
    backups.mkdir(parents=True,exist_ok=False)
    for p in current:
        shutil.copy2(p,backups/p.name)
    touched=[]
    try:
        for path,data in changed.items():
            if data!=current[path]:
                _write_atomic(path,data);touched.append(path)
    except Exception:
        for p in touched:
            _write_atomic(p,current[p])
        raise
    print('Manager intégré : oui. Bouton "Registre de revue…" ajouté sans supprimer les boutons existants.')
    print('Sauvegardes :',backups)
    print('Aucun Kristal, canon, diK, assertion ou tag modifié.')


if __name__=='__main__':
    try:install()
    except (OSError,ValueError,ImportError,SyntaxError) as exc:
        print('INSTALLATION NON TERMINEE :',str(exc))
        print('Aucun écrasement forcé; envoie ce message si besoin.')
        raise SystemExit(1)
