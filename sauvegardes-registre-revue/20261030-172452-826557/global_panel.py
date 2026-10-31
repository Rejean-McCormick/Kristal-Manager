"""Fenêtre intégrée du pipeline global, explicable, en lecture seule des Kristals."""
from __future__ import annotations

from pathlib import Path
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser
from . import kristalizer_bridge


def format_chatgpt_summary(report: dict, kristalizer: dict | None = None, kristalizer_build: dict | None = None) -> str:
    """Résumé collable : inventaire complet, anomalies et hypothèses non validées.

    Cette fonction ne lit pas les Kristals et ne tente aucune synchronisation.
    Les preuves détaillées restent dans le ZIP créé par le pipeline global.
    """
    counts = report.get('counts') or {}
    entries = report.get('entries') or []
    out = [
        'KRISTAL MANAGER — RAPPORT À ANALYSER AVEC CHATGPT',
        'Source : analyse globale locale, en lecture seule (propositions non validées).',
        f"Date UTC : {report.get('generated_at') or 'non renseignée'}",
        f"Dossier scanné : {report.get('source') or 'non renseigné'}",
        f"Mode : {report.get('verification_mode') or 'non renseigné'}",
        ('Totaux : {kristals} Kristals; {blocker} bloqueurs; {warning} avertissements; '
         '{review} à examiner; {info} informations; {arketype_candidates} candidats Arketype; '
         '{unesco_micro_candidates} microthésaurus UNESCO suggérés.').format(
            **{key: counts.get(key, 0) for key in ('kristals', 'blocker', 'warning',
                    'review', 'info', 'arketype_candidates', 'unesco_micro_candidates')}),
        'IMPORTANT : READY, Arketype et UNESCO sont des observations locales, pas une qualification C1/C2/C3.',
        'Demande : trier les anomalies, proposer les corrections sûres et l’ordre de traitement.',
        '',
        f'ENTRÉES ({len(entries)}) :',
    ]
    for index, row in enumerate(entries, start=1):
        values = [
            f"{index:03d} [{row.get('priority') or '?'}] {row.get('title') or 'Sans titre'}",
            f"ID={row.get('state_ref') or '—'}",
            f"chemin={row.get('path') or '—'}",
            f"structure={row.get('readiness') or '—'}",
            f"contenu={row.get('content_status') or '—'}",
            f"vérification={row.get('operational_result') or '—'}",
            f"ARK?={row.get('proposed_arketype') or '—'}",
            f"UNESCO?={row.get('proposed_unesco_domain') or '—'}/{row.get('proposed_unesco') or '—'}",
            'mots-clés=' + ', '.join(str(x) for x in (row.get('keywords') or [])[:8]),
        ]
        issues = row.get('problems') or []
        if issues:
            values.append('anomalies=' + '; '.join(
                f"{x.get('code', 'ISSUE')}: {x.get('detail', '')}" if isinstance(x, dict) else str(x)
                for x in issues))
        if row.get('human_review'):
            values.append('à examiner=' + '; '.join(str(x) for x in row['human_review']))
        out.append(' | '.join(values))
    if kristalizer:
        totals = kristalizer.get('totals', {})
        out.extend(['', 'KRISTALIZER — RAPPORT IMPORTÉ (aucune identité validée)'])
        out.append('Scan : ' + str(kristalizer.get('source_generated_at') or 'inconnu'))
        out.append('Projets : {projects}; v11 préparés non actifs : {v11_non_active}; migrations requises : {migration_required}; rapprochements Wikidata EN ATTENTE : {wikidata_candidates}; identifiants locaux concernés : {distinct_local_identifiers}; notions documentaires : {documentary_topics}; liens natifs : {native_claim_links}.'.format(**totals))
        for name, row in sorted(kristalizer.get('projects', {}).items()):
            out.append(f"{name} : {row['v11']}; candidats={row['candidates']}; identités={row['local_identities_with_candidates']}; notions={row['documentary_topics']}")
        out.append('Les candidats Wikidata ne constituent pas des exactMatch certifiés, ni une qualification C1/C2/C3.')
    if kristalizer_build:
        bt = kristalizer_build['totals']
        out.extend(['', 'KRISTALIZER — BUILD SUR COPIES (aucune publication ou activation automatique)'])
        out.append(f"Projets={bt['projects']}; BUILT(copie)={bt['built']}; MIGRATION_MANUELLE_V11={bt['migration_required']}; erreurs={bt['failed']}; publiés={bt['published']}; activés={bt['activated']}.")
        out.append(f"Kit={bt.get('kit_version')}; Framework pin={bt.get('kit_framework_pin')}; source modifiée={bt.get('source_modified')}.")
        for name, item in sorted(kristalizer_build['projects'].items()):
            out.append(name + ' : ' + item['status'] + (' (copie uniquement)' if item['staged_copy_only'] else ''))
        out.append('BUILT ne valide pas la sémantique, les identités Wikidata ou les niveaux Framework C1/C2/C3.')
    out += ['', 'LIMITES :']
    out += ['- ' + str(x) for x in (report.get('limits') or [])]
    out += ['- Les indices détaillés et les preuves sont dans le ZIP des problèmes.']
    return '\n'.join(out) + '\n'


class GlobalAnalysisPanel(tk.Toplevel):
    def __init__(self, manager):
        super().__init__(manager)
        self.manager = manager
        self.title('Centre d’analyse globale — Kristal Manager')
        self.geometry('1180x755')
        self.minsize(850, 560)
        self.transient(manager)
        self.result = None
        self.entries = []
        self.kristalizer = None
        self.kristalizer_build = None
        self.update_catalogue = tk.BooleanVar(value=True)
        self.verify_locally = tk.BooleanVar(value=False)
        self.problems_only = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value='Prêt. Aucune modification des Kristals.')
        self._layout()
        self._restore_kristalizer()
        self._restore_last_report()
        self.protocol('WM_DELETE_WINDOW', self._close)

    def _layout(self):
        top = ttk.Frame(self, padding=15)
        top.pack(fill='both', expand=True)
        ttk.Label(top, text='Analyse globale · Arketype + mots-clés + UNESCO + diK',
                  style='H2.TLabel').pack(anchor='w')
        ttk.Label(top, text='Source : dossier affiché dans la fenêtre principale. Analyse locale seulement : aucun Git, aucun GitHub, aucune publication. Propositions non qualifiantes.',
                  wraplength=1100, style='Sub.TLabel').pack(anchor='w', pady=(3, 9))
        options = ttk.Frame(top)
        options.pack(fill='x', pady=(2, 5))
        ttk.Checkbutton(options, text='Actualiser le catalogue (cache incrémental)',
                        variable=self.update_catalogue).pack(side='left')
        ttk.Checkbutton(options, text='Vérifier aussi les fichiers enregistrés (plus lent)',
                        variable=self.verify_locally).pack(side='left', padx=(16, 0))
        self.start = ttk.Button(options, text='Scanner et analyser les Kristals',
                                style='Primary.TButton', command=self._run)
        self.start.pack(side='right')
        self.progress = ttk.Progressbar(top, mode='indeterminate')
        self.progress.pack(fill='x', pady=(7, 5))
        ttk.Label(top, textvariable=self.status, style='Sub.TLabel', wraplength=1100).pack(anchor='w', pady=(1, 8))
        filterline = ttk.Frame(top)
        filterline.pack(fill='x', pady=(1, 5))
        ttk.Checkbutton(filterline, text='Afficher seulement les problèmes techniques',
                        variable=self.problems_only, command=self._fill).pack(side='left')
        ttk.Label(filterline, text='Double-cliquer sur un Kristal pour voir les preuves et les propositions.',
                  style='Sub.TLabel').pack(side='right')
        main = ttk.Frame(top)
        main.pack(fill='both', expand=True)
        columns = ('title','priority','readiness','content_status','v11_kristalizer','proposed_arketype','proposed_unesco_domain','proposed_unesco','keywords')
        self.table = ttk.Treeview(main, columns=columns, show='headings', height=16)
        for key, label, width in [
            ('title','Kristal',210), ('priority','Priorité',85), ('readiness','Structure',135),
            ('content_status','Contenu',140), ('v11_kristalizer','Kristalizer v11',150), ('proposed_arketype','ARK suggéré',100),
            ('proposed_unesco_domain','Domaine UNESCO',100),
            ('proposed_unesco','Micro UNESCO',110), ('keywords','Mots-clés observés',360)]:
            self.table.heading(key, text=label)
            self.table.column(key, width=width, minwidth=75, stretch=key in ('title','keywords'))
        sy = ttk.Scrollbar(main, orient='vertical', command=self.table.yview)
        sx = ttk.Scrollbar(main, orient='horizontal', command=self.table.xview)
        self.table.grid(row=0,column=0,sticky='nsew')
        sy.grid(row=0,column=1,sticky='ns')
        sx.grid(row=1,column=0,sticky='ew')
        main.rowconfigure(0,weight=1);main.columnconfigure(0,weight=1)
        self.table.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.table.tag_configure('blocker', foreground='#9c3428')
        self.table.tag_configure('warning', foreground='#9e631c')
        self.table.bind('<Double-1>', lambda _evt: self._details())
        self.table.bind('<<TreeviewSelect>>', lambda _evt: self._update_selection_buttons())
        self.table.bind('<Control-c>', lambda _evt: self._copy_selected())
        # Deux rangées pour que le bouton de copie ne disparaisse pas sur un petit écran.
        buttons = ttk.Frame(top)
        buttons.pack(fill='x', pady=(10, 0))
        share = ttk.Frame(buttons)
        share.pack(fill='x', pady=(0, 7))
        self.copy_all_button = ttk.Button(share, text='Copier résultats pour ChatGPT',
                                          style='Primary.TButton', command=self._copy_all)
        self.copy_all_button.pack(side='left')
        self.copy_selected_button = ttk.Button(share, text='Copier Kristal sélectionné',
                                               command=self._copy_selected)
        self.copy_selected_button.pack(side='left', padx=(7, 0))
        self.arketype_button = ttk.Button(share, text='Vérifier structure ARK…', command=self._arketype_inspect)
        self.arketype_button.pack(side='left', padx=(7, 0))
        self.bundle_button = ttk.Button(share, text='Tailles / bundles…', command=self._bundle_inventory)
        self.bundle_button.pack(side='left', padx=(7, 0))
        ttk.Label(share, text='Puis colle ici avec Ctrl+V.', style='Sub.TLabel').pack(side='left', padx=(12, 0))
        tools = ttk.Frame(buttons)
        tools.pack(fill='x')
        self.open_html_button = ttk.Button(tools, text='Ouvrir rapport HTML', command=self._open_html)
        self.open_html_button.pack(side='left')
        self.open_zip_button = ttk.Button(tools, text='Voir ZIP des problèmes', command=self._open_zip_folder)
        self.open_zip_button.pack(side='left', padx=(7,0))
        self.plan_button = ttk.Button(tools, text='Voir plan de corrections', command=self._open_plan)
        self.plan_button.pack(side='left', padx=(7,0))
        self.import_kristalizer_button = ttk.Button(tools, text='Importer rapport Kristalizer…', command=self._import_kristalizer)
        self.import_kristalizer_button.pack(side='left', padx=(7,0))
        ttk.Button(tools, text='Normaliser les noms en lot…',
                   command=self.manager.open_batch_rename).pack(side='left',padx=(7,0))
        ttk.Button(tools,text='Fermer',command=self._close).pack(side='right')
        self._set_running(False)

    def _restore_kristalizer(self):
        from .global_analysis import RAPPORTS_PATH
        try:
            self.kristalizer = kristalizer_bridge.load_last_import(RAPPORTS_PATH)
        except (OSError, ValueError, TypeError):
            self.kristalizer = None
        try:
            self.kristalizer_build = kristalizer_bridge.load_last_build(RAPPORTS_PATH)
        except (OSError, ValueError, TypeError):
            self.kristalizer_build = None

    def _import_kristalizer(self):
        path = filedialog.askopenfilename(parent=self, title='Choisir le ZIP de rapport Kristalizer',
                                        filetypes=[('Archives ZIP', '*.zip')])
        if not path:
            return
        from .global_analysis import RAPPORTS_PATH
        try:
            import zipfile
            with zipfile.ZipFile(path) as archive:
                has_build = 'STAGING/KRISTALIZER_BUILD_REPORT.json' in archive.namelist()
            if has_build:
                self.kristalizer_build = kristalizer_bridge.import_build_report(path, RAPPORTS_PATH)
            else:
                self.kristalizer = kristalizer_bridge.import_report(path, RAPPORTS_PATH)
        except (OSError, ValueError, TypeError, zipfile.BadZipFile) as exc:
            messagebox.showerror('Rapport Kristalizer refusé', str(exc), parent=self)
            return
        self._fill()
        if has_build:
            total = self.kristalizer_build['totals']
            self.status.set(f"BUILD importé (copies) : {total['built']} réussis; "
                            f"{total['migration_required']} migrations v11 nécessaires; "
                            f"{total['failed']} échecs; aucune qualification Framework.")
        else:
            total = self.kristalizer['totals']
            self.status.set(f"Scan Kristalizer importé : {total['projects']} Kristals; "
                            f"{total['v11_non_active']} v11 préparés; {total['migration_required']} migrations requises.")

    def _restore_last_report(self):
        # Read an existing report only if its source corresponds to the displayed root.
        try:
            from .global_analysis import RAPPORTS_PATH
            paths = sorted(RAPPORTS_PATH.glob('analyse-*/rapport_global.json'), reverse=True)
            source = str(Path(self.manager.path_var.get()).expanduser().resolve()).casefold()
            for path in paths[:20]:
                obj = json.loads(path.read_text('utf-8'))
                if obj.get('source','').casefold() == source:
                    self.result = {'report_directory': str(path.parent),
                                   'problem_archive': str(path.parent.parent / ('problemes-' + path.parent.name + '.zip')),
                                   'html_report': str(path.parent / 'semantique' / 'rapport.html'),
                                   'global_report': obj}
                    self.render_result(self.result, restored=True)
                    break
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    def _set_running(self, running: bool):
        self.start.configure(state='disabled' if running else 'normal')
        if running:self.progress.start(15)
        else:self.progress.stop()
        available = bool(self.result)
        for button in (self.open_html_button,self.open_zip_button,self.plan_button,
                       self.copy_all_button):
            button.configure(state='normal' if available else 'disabled')
        self._update_selection_buttons()

    def _run(self):
        if self.manager.busy:
            messagebox.showinfo('Opération en cours','Une autre opération est déjà en cours.',parent=self)
            return
        if self.manager.start_global_analysis(update_catalogue=self.update_catalogue.get(),
                                              verify_locally=self.verify_locally.get()):
            self.status.set('Analyse en cours… les fichiers sources restent inchangés.')
            self._set_running(True)

    def render_error(self, error: str):
        self._set_running(False)
        self.status.set('Analyse interrompue : ' + error)

    def render_result(self, result: dict, *, restored: bool=False):
        self.result = result
        self.entries = result['global_report']['entries']
        self._fill()
        c = result['global_report']['counts']
        self.status.set(f"{c['kristals']} Kristals · {c['blocker']} bloqueurs observés · "
                        f"{c['warning']} avertissements · {c['review']} à classifier/revoir"
                        + f" · {c.get('arketype_candidates',0)} ARK proposés · {c.get('unesco_micro_candidates',0)} UNESCO proposés"
                        + (' · dernier rapport conservé' if restored else ' · export ZIP créé')
                        + (' · diagnostic Kristalizer importé' if self.kristalizer else ''))
        self._set_running(False)

    def _fill(self):
        self.table.delete(*self.table.get_children())
        for i,r in enumerate(self.entries):
            if self.problems_only.get() and r['priority'] not in ('blocker','warning'):
                continue
            kstate = kristalizer_bridge.lookup(self.kristalizer, r.get('path'))
            kbuild = kristalizer_bridge.lookup_build(self.kristalizer_build, r.get('path'))
            displayed = (('BUILT (copie)' if kbuild['status'] == 'BUILT' else kbuild['status']) if kbuild else
                         (kstate['v11'] if kstate else '—'))
            values=(r['title'],r['priority'],r['readiness'],r['content_status'],
                    displayed, r['proposed_arketype'] or '—', r['proposed_unesco_domain'] or '—',
                    r['proposed_unesco'] or '—',
                    ', '.join(r['keywords'][:6]))
            self.table.insert('','end',iid=str(i),values=values,tags=(r['priority'],))
        self._update_selection_buttons()

    def _update_selection_buttons(self):
        selected = self.table.selection()
        valid = bool(self.result and selected and selected[0].isdigit()
                     and int(selected[0]) < len(self.entries))
        self.copy_selected_button.configure(state='normal' if valid else 'disabled')

    def _copy_text(self, text: str, *, label: str, parent=None):
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            # Conserver le contenu lors de la fermeture d'une fenêtre de détails.
            self.update_idletasks()
        except tk.TclError as exc:
            messagebox.showerror('Copie impossible', f'Presse-papiers indisponible : {exc}',
                                 parent=parent or self)
            return False
        self.status.set(f'{label} copiés ({len(text):,} caractères). Colle dans ChatGPT avec Ctrl+V.')
        return True

    def _copy_all(self):
        if self.result:
            self._copy_text(format_chatgpt_summary(self.result['global_report'], self.kristalizer, self.kristalizer_build),
                            label='Résultats globaux')

    def _arketype_inspect(self):
        from .archetype_panel import ArchetypePanel
        selected = self.table.selection()
        target = None
        if selected and selected[0].isdigit() and int(selected[0]) < len(self.entries):
            target = self.entries[int(selected[0])].get('path')
        ArchetypePanel(self, self.manager.path_var.get(), selected_root=target)

    def _bundle_inventory(self):
        from .bundle_panel import BundleInventoryPanel
        BundleInventoryPanel(self, self.manager.path_var.get())

    def _selected_record(self) -> dict | None:
        selected = self.table.selection()
        if not selected or not selected[0].isdigit():
            return None
        index = int(selected[0])
        if index >= len(self.entries):
            return None
        row = self.entries[index]
        data = {'synthese_globale': row}
        kstate = kristalizer_bridge.lookup(self.kristalizer, row.get('path'))
        if kstate:
            data['kristalizer_observation'] = kstate
            data['kristalizer_source_date'] = self.kristalizer.get('source_generated_at')
        kbuild = kristalizer_bridge.lookup_build(self.kristalizer_build, row.get('path'))
        if kbuild:
            data['kristalizer_build_sur_copie'] = kbuild
            data['qualification'] = 'NON_EVALUEE'
        try:
            report_dir = Path(self.result['report_directory']).resolve(strict=True)
            mapping = json.loads((report_dir / 'correspondance_rapports.json').read_text('utf-8'))
            detail_file = next((x.get('detail_file') for x in mapping
                                if x.get('path') == row.get('path')), None)
            if detail_file:
                full_path = (report_dir / detail_file).resolve(strict=True)
                if full_path.is_relative_to(report_dir):
                    data['indices_detailles'] = json.loads(full_path.read_text('utf-8'))
        except (OSError, ValueError, json.JSONDecodeError, TypeError):
            pass
        return data

    def _copy_selected(self):
        data = self._selected_record()
        if data is None:
            messagebox.showinfo('Aucune sélection',
                                'Sélectionne un Kristal dans la liste, puis clique sur Copier.', parent=self)
            return
        self._copy_text(json.dumps(data, ensure_ascii=False, indent=2),
                        label='Détails du Kristal')

    def _details(self):
        selected=self.table.selection()
        if not selected:return
        row=self.entries[int(selected[0])]
        popup=tk.Toplevel(self)
        popup.title('Observations et propositions — ' + row['title'])
        popup.geometry('900x620')
        frame=ttk.Frame(popup,padding=12);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text=row['title']+' · données de triage non validées',style='H2.TLabel').pack(anchor='w')
        text=tk.Text(frame,wrap='word',font=('Consolas',10))
        text.pack(fill='both',expand=True,pady=(8,0))
        data = self._selected_record() or {'synthese_globale': row}
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        text.insert('1.0', payload)
        text.configure(state='disabled')
        actions = ttk.Frame(frame)
        actions.pack(fill='x', pady=(7, 0))
        feedback = tk.StringVar(value='')
        ttk.Label(actions, textvariable=feedback, style='Sub.TLabel').pack(side='left')
        def copy_details():
            if self._copy_text(payload, label='Détails du Kristal', parent=popup):
                feedback.set('Copié ! Colle dans ChatGPT avec Ctrl+V.')
        ttk.Button(actions, text='Copier ces détails', command=copy_details).pack(side='right', padx=(7,0))
        ttk.Button(actions,text='Fermer',command=popup.destroy).pack(side='right')

    def _open_html(self):
        if self.result:
            path=Path(self.result['html_report'])
            if path.is_file():webbrowser.open(path.resolve().as_uri())

    def _open_zip_folder(self):
        if self.result:
            path=Path(self.result['problem_archive'])
            if path.is_file():
                # Show exact ZIP location without uploading anything.
                messagebox.showinfo('ZIP des problèmes prêt',str(path),parent=self)
            else:
                messagebox.showwarning('Archive introuvable','Le ZIP doit être régénéré.',parent=self)

    def _open_plan(self):
        if self.result:
            path=Path(self.result['report_directory']) / 'plan_corrections.json'
            if path.is_file():
                popup=tk.Toplevel(self);popup.title('Plan des corrections (prévisualisation seulement)')
                popup.geometry('850x610')
                txt=tk.Text(popup,wrap='word',font=('Consolas',10))
                txt.pack(fill='both',expand=True)
                txt.insert('1.0',path.read_text('utf-8'))
                txt.configure(state='disabled')

    def _close(self):
        if getattr(self.manager,'_global_dialog',None) is self:
            self.manager._global_dialog = None
        self.destroy()
