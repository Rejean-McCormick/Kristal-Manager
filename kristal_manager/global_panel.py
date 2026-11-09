"""Fenêtre intégrée du pipeline global, explicable, en lecture seule des Kristals."""
from __future__ import annotations

from pathlib import Path
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import webbrowser
from . import kristalizer_bridge
from .qualification_history import display_declared, display_unesco_declaration, display_ark_structure
from .classification_labels import display_category
from .semantic_enrichment import display_semantic_role, display_prf_refinement, annotate_ai_dossiers
from .editorial_review import annotate_editorial_review, annotate_historical_unesco_attention, display_unesco_review, display_current_unesco_review
from .column_views import ColumnViewControl
from .native_evidence import annotate_native_sources, display_native_source_review
from .authoring_observations import annotate_authoring, display_authoring_status, display_source_catalog
from .review_progress import REVIEW_FOCI, assess_review, matches_focus, export_review_queue
from .editorial_decisions import current_editorial_state


# Labels d'interface uniquement. Les codes bruts restent intacts dans les rapports JSON.
_READ_LABELS = {
    'observed': 'graph read',
    'native_observed': 'native contract read',
    'partial': 'partial reading',
    'unsupported': 'unsupported',
    'error': 'reader error',
}
_REVIEW_LABELS = {
    'proposed': 'proposed',
    'needs_discussion': 'needs discussion',
    'approved_locally': 'locally approved',
    'rejected_locally': 'locally rejected',
}


def display_content_status(code):
    return _READ_LABELS.get(code, code or '—')


def display_registered_ark(row):
    r = row.get('registered_review')
    if not r:
        return 'Not in review register'
    status = r.get('archetype_review_status')
    choices = r.get('archetype_recommendations') or []
    chosen = r.get('locally_selected_archetype')
    label = _REVIEW_LABELS.get(status, status or 'not verified')
    # Une décision locale n'est pas un tag écrit dans le Kristal.
    names = [display_category(code, 'ark') for code in ([chosen] if chosen else choices)]
    return '{} ({})'.format(' / '.join(names) if names else 'Not assigned', label)


def format_chatgpt_summary(report: dict, kristalizer: dict | None = None, kristalizer_build: dict | None = None) -> str:
    """Résumé collable : inventaire complet, anomalies et hypothèses non validées.

    Cette fonction ne lit pas les Kristals et ne tente aucune synchronisation.
    Les preuves détaillées restent dans le ZIP créé par le pipeline global.
    """
    counts = report.get('counts') or {}
    entries = report.get('entries') or []
    out = [
        'KRISTAL MANAGER — REPORT FOR CHATGPT REVIEW',
        'Source: local read-only global analysis (unvalidated proposals).',
        f"UTC date: {report.get('generated_at') or 'not provided'}",
        f"Scanned folder: {report.get('source') or 'not provided'}",
        f"Mode: {report.get('verification_mode') or 'not provided'}",
        ('Totals: {kristals} Kristals; {blocker} blockers; {warning} warnings; '
         '{review} to review; {info} informational; {arketype_candidates} Arketype candidates; '
         '{unesco_micro_candidates} suggested UNESCO microthesauri.').format(
            **{key: counts.get(key, 0) for key in ('kristals', 'blocker', 'warning',
                    'review', 'info', 'arketype_candidates', 'unesco_micro_candidates')}),
        ('Canonical reading: {graph_content_observed} graphs/states recognized; '
         '{native_contract_observed} native contracts read without inferring KQ/KP graphs; '
         '{content_partial} partial readings; {content_unsupported} unsupported; '
         '{content_error} reader errors.').format(
             **{key:counts.get(key,0) for key in ('graph_content_observed','native_contract_observed',
                    'content_partial','content_unsupported','content_error')}),
        f"Local review register: {counts.get('registered_review_matched',0)} reviews linked to scanned identities; decisions are separate from canonical tags.",
        (f"Recovered records: {counts.get('historical_qualifications_matched', 0)} historical profiles; "
         f"{counts.get('live_classifications_read', 0)} current workspace metadata reads. "
         'Historical PRF/ARK observations are not human approvals.'),
        (f"AI semantic dossiers: {sum((r.get('semantic_enrichment') or {}).get('status') == 'MATCHED_CURRENT_DESCRIPTORS' for r in entries)} current metadata matches; "
         f"{sum(bool((r.get('semantic_enrichment') or {}).get('prf_candidate')) for r in entries)} exploratory PRF alternatives; "
         f"{sum(bool((r.get('semantic_enrichment') or {}).get('unesco_proposal_disagrees_with_declared')) for r in entries)} UNESCO proposal disagreements. "
         'AI editorial drafts are NOT approved PRF/ARK/UNESCO classifications.'),
        (f"Authoring: {counts.get('authoring_building',0)} declared building; "
         f"{counts.get('source_catalog_entries',0)} catalogued source records; "
         f"{counts.get('source_catalog_empty',0)} empty source catalogues; "
         f"{counts.get('source_catalog_issues',0)} catalogue shape/locator issues; "
         f"{counts.get('native_metadata_only_changed',0)} metadata-only evidence changes. "
         'Local metadata and source records do not independently establish approval.'),
        'IMPORTANT: READY, Arketype and UNESCO are local observations, not C1/C2/C3 qualification.',
        'Request: prioritize issues, suggest safe fixes and an order of action.',
        '',
        f'ENTRIES ({len(entries)}):',
    ]
    for index, row in enumerate(entries, start=1):
        values = [
            f"{index:03d} [{row.get('priority') or '?'}] {row.get('title') or 'Untitled'}",
            f"ID={row.get('state_ref') or '—'}",
            f"path={row.get('path') or '—'}",
            f"structure={row.get('readiness') or '—'}",
            f"content={row.get('content_status') or '—'}",
            f"verification={row.get('operational_result') or '—'}",
            f"declared_ARK={display_declared(row, 'primary_archetype')}",
            f"declared_PRF={display_declared(row, 'primary_usage')}",
            f"AI_semantic_role={display_semantic_role(row)}",
            f"AI_PRF_review={display_prf_refinement(row)}",
            f"AI_review_status={(row.get('semantic_enrichment') or {}).get('status', 'NOT_REVIEWED')}",
            f"native_source_review={display_native_source_review(row)}",
            f"authoring_status={display_authoring_status(row)}",
            f"source_catalog={display_source_catalog(row)}",
            f"review_stage={assess_review(row)['stage']}",
            f"next_action={assess_review(row)['next_action']}",
            f"AI_UNESCO_review={display_unesco_review(row)}",
            f"subject_domain={display_declared(row, 'subject_domain')}",
            f"ARK_structural_observation={display_ark_structure(row)}",
            f"declared_UNESCO={display_unesco_declaration(row)}",
            f"ARK_new_proposal={display_category(row['proposed_arketype'], 'ark') if row.get('proposed_arketype') else 'none'}",
            f"UNESCO_suggestion={display_category(row['proposed_unesco'], 'unesco') if row.get('proposed_unesco') else (display_category(row['proposed_unesco_domain'], 'unesco_domain') if row.get('proposed_unesco_domain') else 'none')}",
            'keywords=' + ', '.join(str(x) for x in (row.get('keywords') or [])[:8]),
        ]
        issues = row.get('problems') or []
        if issues:
            values.append('issues=' + '; '.join(
                f"{x.get('code', 'ISSUE')}: {x.get('detail', '')}" if isinstance(x, dict) else str(x)
                for x in issues))
        registered = row.get('registered_review')
        if registered:
            values.append('review_register=' + ', '.join(display_category(code, 'ark') for code in registered['archetype_recommendations'])
                          + '/' + registered['archetype_review_status']
                          + '/anchors-' + registered['provenance_status']['status'])
        if row.get('human_review'):
            values.append('to_review=' + '; '.join(str(x) for x in row['human_review']))
        out.append(' | '.join(values))
    if kristalizer:
        totals = kristalizer.get('totals', {})
        out.extend(['', 'KRISTALIZER — IMPORTED REPORT (no validated identities)'])
        out.append('Scan: ' + str(kristalizer.get('source_generated_at') or 'unknown'))
        out.append('Projects: {projects}; v11 prepared but inactive: {v11_non_active}; migrations required: {migration_required}; PENDING Wikidata matches: {wikidata_candidates}; local identifiers affected: {distinct_local_identifiers}; documentary topics: {documentary_topics}; native claim links: {native_claim_links}.'.format(**totals))
        for name, row in sorted(kristalizer.get('projects', {}).items()):
            out.append(f"{name} : {row['v11']}; candidates={row['candidates']}; identities={row['local_identities_with_candidates']}; topics={row['documentary_topics']}")
        out.append('Wikidata candidates are not certified exactMatch relationships or C1/C2/C3 qualification.')
    if kristalizer_build:
        bt = kristalizer_build['totals']
        out.extend(['', 'KRISTALIZER — BUILD ON COPIES (no automatic publication or activation)'])
        out.append(f"Projects={bt['projects']}; BUILT(copy)={bt['built']}; MIGRATION_MANUELLE_V11={bt['migration_required']}; errors={bt['failed']}; published={bt['published']}; activated={bt['activated']}.")
        out.append(f"Kit={bt.get('kit_version')}; Framework pin={bt.get('kit_framework_pin')}; source modified={bt.get('source_modified')}.")
        for name, item in sorted(kristalizer_build['projects'].items()):
            out.append(name + ' : ' + item['status'] + (' (copy only)' if item['staged_copy_only'] else ''))
        out.append('BUILT does not validate semantics, Wikidata identity matching, or Framework C1/C2/C3 levels.')
    out += ['', 'LIMITATIONS:']
    out += ['- ' + str(x) for x in (report.get('limits') or [])]
    out += ['- Detailed findings and evidence are in the issues ZIP.']
    return '\n'.join(out) + '\n'


class GlobalAnalysisPanel(tk.Toplevel):
    def __init__(self, manager):
        super().__init__(manager)
        self.manager = manager
        self.title('Analysis Center — Kristal Manager')
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
        self.review_focus_var = tk.StringVar(value='All Kristals')
        self.status = tk.StringVar(value='Ready. No changes to Kristals.')
        self._layout()
        self._restore_kristalizer()
        self._restore_last_report()
        self.protocol('WM_DELETE_WINDOW', self._close)

    def _layout(self):
        top = ttk.Frame(self, padding=15)
        top.pack(fill='both', expand=True)
        heading = ttk.Frame(top)
        heading.pack(fill='x')
        # Reuse the original logo asset loaded by Manager; do not convert SVG at runtime.
        try:
            logo_path = self.manager._asset_path('logo_header.png')
            self._analysis_logo = tk.PhotoImage(file=str(logo_path))
            ttk.Label(heading, image=self._analysis_logo).pack(side='left', padx=(0, 12))
        except (tk.TclError, OSError):
            self._analysis_logo = None
        ttk.Label(heading, text='Analysis Center · Inventory, content, Arketype, UNESCO and diagnostics',
                  style='H2.TLabel').pack(side='left', anchor='w')
        ttk.Label(top, text='Source: folder shown in the main window. Local analysis only: no Git, GitHub or publication. Proposals do not grant qualification.',
                  wraplength=1100, style='Sub.TLabel').pack(anchor='w', pady=(3, 9))
        options = ttk.Frame(top)
        options.pack(fill='x', pady=(2, 5))
        ttk.Checkbutton(options, text='Refresh catalog (incremental cache)',
                        variable=self.update_catalogue).pack(side='left')
        ttk.Checkbutton(options, text='Also verify registered files (slower)',
                        variable=self.verify_locally).pack(side='left', padx=(16, 0))
        self.start = ttk.Button(options, text='Scan and analyze Kristals',
                                style='Primary.TButton', command=self._run)
        self.start.pack(side='right')
        self.batch_diag = ttk.Button(options, text='Run folder diagnostics (V9)', command=self._run_batch)
        self.batch_diag.pack(side='right', padx=(0, 8))
        self.progress = ttk.Progressbar(top, mode='indeterminate')
        self.progress.pack(fill='x', pady=(7, 5))
        ttk.Label(top, textvariable=self.status, style='Sub.TLabel', wraplength=1100).pack(anchor='w', pady=(1, 8))
        filterline = ttk.Frame(top)
        filterline.pack(fill='x', pady=(1, 5))
        ttk.Checkbutton(filterline, text='Show technical issues only',
                        variable=self.problems_only, command=self._fill).pack(side='left')
        ttk.Label(filterline, text='Review focus').pack(side='left', padx=(12, 4))
        focus = ttk.Combobox(filterline, state='readonly', width=23,
                             values=REVIEW_FOCI, textvariable=self.review_focus_var)
        focus.pack(side='left')
        focus.bind('<<ComboboxSelected>>', lambda _evt: self._fill())
        ttk.Label(filterline, text='Double-click a Kristal to view evidence and proposals.',
                  style='Sub.TLabel').pack(side='right')
        main = ttk.Frame(top)
        main.pack(fill='both', expand=True)
        columns = ('title','editorial_state','review_stage','next_action','authoring_status','source_catalog','native_evidence','priority','readiness','content_status','declared_ark','declared_prf','semantic_role_ai','prf_review_ai','subject_domain','declared_unesco','unesco_review','ark_structure_history','registered_ark','v11_kristalizer','new_suggestions','keywords')
        self.table = ttk.Treeview(main, columns=columns, show='headings', height=16)
        for key, label, width in [
            ('title','Kristal',210), ('editorial_state','Editorial state (local)',150),
            ('review_stage','Review stage (not approval)',205),
            ('next_action','Next review action',345),
            ('authoring_status','Authoring status (not qualification)',230),
            ('source_catalog','Source catalogue (unverified)',230), ('native_evidence','Native-source evidence',235),
            ('priority','Priority',85), ('readiness','Structure',135),
            ('content_status','Canonical reading',155),
            ('declared_ark','Arketype (declared)',230), ('declared_prf','Usage profile (declared)',235),
            ('semantic_role_ai','Semantic role (AI draft)',255), ('prf_review_ai','PRF refinement (AI draft)',260),
            ('subject_domain','Subject domain',170), ('declared_unesco','UNESCO subjects (declared)',250),
            ('unesco_review','UNESCO review (AI draft)',225),
            ('ark_structure_history','Structural evidence (historic)',195),
            ('v11_kristalizer','Kristalizer v11',150),
            ('registered_ark','Arketype review',230),
            ('new_suggestions','New scan proposals',180), ('keywords','Observed keywords',360)]:
            self.table.heading(key, text=label)
            self.table.column(key, width=width, minwidth=75, stretch=key in ('title','keywords'))
        sy = ttk.Scrollbar(main, orient='vertical', command=self.table.yview)
        sx = ttk.Scrollbar(main, orient='horizontal', command=self.table.xview)
        self.table.grid(row=0,column=0,sticky='nsew')
        sy.grid(row=0,column=1,sticky='ns')
        sx.grid(row=1,column=0,sticky='ew')
        main.rowconfigure(0,weight=1);main.columnconfigure(0,weight=1)
        self.table.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.column_views = ColumnViewControl(
            filterline, self.table, 'analysis',
            initial=(getattr(self.manager, 'settings', {}) or {}).get('analysis_column_view', 'Essential'),
            custom_columns=(getattr(self.manager, 'settings', {}) or {}).get('analysis_custom_columns'),
            on_change=lambda view, columns: getattr(self.manager, '_save_column_profile', lambda *_: None)('analysis_column_view', view, columns))
        self.column_views.frame.pack(side='left', padx=(15, 0))
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
        self.copy_all_button = ttk.Button(share, text='Copy results for ChatGPT',
                                          style='Primary.TButton', command=self._copy_all)
        self.copy_all_button.pack(side='left')
        self.editorial_menu = tk.Menu(self, tearoff=False)
        for state in ('Ready', 'Needs work', 'Not assessed'):
            self.editorial_menu.add_command(label=state + (' (editorial only)' if state == 'Ready' else ''),
                                             command=lambda selected=state: self._edit_editorial_state(selected))
        self.editorial_menu.add_separator()
        self.editorial_menu.add_command(label='Clear current decision',
                                         command=lambda: self._edit_editorial_state('Clear'))
        ttk.Menubutton(share, text='Editorial state ▾', menu=self.editorial_menu).pack(side='left', padx=(7, 0))
        self.export_queue_button = ttk.Button(share, text='Export review queue CSV…',
                                              command=self._export_queue)
        self.export_queue_button.pack(side='left', padx=(7, 0))
        self.copy_selected_button = ttk.Button(share, text='Copy selected Kristal',
                                               command=self._copy_selected)
        self.copy_selected_button.pack(side='left', padx=(7, 0))
        self.arketype_button = ttk.Button(share, text='Inspect Arketype structure…', command=self._arketype_inspect)
        self.arketype_button.pack(side='left', padx=(7, 0))
        self.bundle_button = ttk.Button(share, text='Sizes / bundles…', command=self._bundle_inventory)
        self.bundle_button.pack(side='left', padx=(7, 0))
        ttk.Label(share, text='Then paste here with Ctrl+V.', style='Sub.TLabel').pack(side='left', padx=(12, 0))
        ai = ttk.Frame(buttons)
        ai.pack(fill='x', pady=(0, 7))
        self.ai_review_button = ttk.Button(ai, text='Open AI semantic dossiers', command=self._open_ai_review)
        self.ai_review_button.pack(side='left')
        ttk.Label(ai, text='127 individualized descriptions · AI drafts only · no automatic PRF changes',
                  style='Sub.TLabel').pack(side='left', padx=(12, 0))
        tools = ttk.Frame(buttons)
        tools.pack(fill='x')
        self.open_html_button = ttk.Button(tools, text='Open HTML report', command=self._open_html)
        self.open_html_button.pack(side='left')
        self.open_zip_button = ttk.Button(tools, text='Find issues ZIP', command=self._open_zip_folder)
        self.open_zip_button.pack(side='left', padx=(7,0))
        self.plan_button = ttk.Button(tools, text='View correction plan', command=self._open_plan)
        self.plan_button.pack(side='left', padx=(7,0))
        self.import_kristalizer_button = ttk.Button(tools, text='Import Kristalizer report…', command=self._import_kristalizer)
        self.import_kristalizer_button.pack(side='left', padx=(7,0))
        ttk.Button(tools, text='Review register…', command=self._open_review_registry).pack(side='left',padx=(7,0))
        ttk.Button(tools, text='Normalize folder names in batch…',
                   command=self.manager.open_batch_rename).pack(side='left',padx=(7,0))
        ttk.Button(tools,text='Close',command=self._close).pack(side='right')
        self._set_running(False)

    # REGISTRE-REVUE-2026-10-30 : fenêtre dédiée, aucune écriture dans locals.
    def _open_review_registry(self):
        from .review_panel import ReviewRegistryPanel
        ReviewRegistryPanel(self, self.manager.path_var.get())

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
        path = filedialog.askopenfilename(parent=self, title='Select Kristalizer report ZIP',
                                        filetypes=[('ZIP archives', '*.zip')])
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
            messagebox.showerror('Kristalizer report rejected', str(exc), parent=self)
            return
        self._fill()
        if has_build:
            total = self.kristalizer_build['totals']
            self.status.set(f"BUILD imported (copies): {total['built']} successful; "
                            f"{total['migration_required']} v11 migrations needed; "
                            f"{total['failed']} failures; no Framework qualification.")
        else:
            total = self.kristalizer['totals']
            self.status.set(f"Kristalizer scan imported: {total['projects']} Kristals; "
                            f"{total['v11_non_active']} v11 prepared; {total['migration_required']} migrations required.")

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
        self.batch_diag.configure(state='disabled' if running else 'normal')
        if running:self.progress.start(15)
        else:self.progress.stop()
        available = bool(self.result)
        for button in (self.open_html_button,self.open_zip_button,self.plan_button,
                       self.copy_all_button,self.export_queue_button):
            button.configure(state='normal' if available else 'disabled')
        self._update_selection_buttons()

    def _run(self):
        if self.manager.busy:
            messagebox.showinfo('Operation in progress','Another operation is already running.',parent=self)
            return
        if self.manager.start_global_analysis(update_catalogue=self.update_catalogue.get(),
                                              verify_locally=self.verify_locally.get()):
            self.status.set('Analysis running… source files remain unchanged.')
            self._set_running(True)

    def _run_batch(self):
        if self.manager.start_batch_diagnostics():
            self.status.set('Bundled KristalDiag: V9 diagnostics running, evidence stored outside sources…')
            self._set_running(True)

    def on_batch_progress(self, done: int, total: int, name: str, verdict: str):
        self.status.set(f'KristalDiag {done}/{total} · {name} : {verdict}')

    def render_batch_result(self, summary: dict):
        counts = ', '.join(f'{k}={v}' for k, v in sorted(summary.get('counts', {}).items()))
        self.status.set(f'Diagnostics for {summary.get("total", 0)} Kristals complete · {counts} · '
                        f'report: {summary.get("report_directory", "?")}')
        self._set_running(False)

    def render_error(self, error: str):
        self._set_running(False)
        self.status.set('Analysis stopped: ' + error)

    def render_result(self, result: dict, *, restored: bool=False):
        self.result = result
        self.entries = result['global_report']['entries']
        # A restored report must NOT assert that old descriptors are still current.
        # Refresh all provenance annotations against live workspace metadata.
        if restored and self.entries:
            from .qualification_history import annotate_qualifications
            annotate_qualifications(self.entries, source=result['global_report'].get('source') or '.')
            annotate_ai_dossiers(self.entries)
            annotate_editorial_review(self.entries)
        annotate_historical_unesco_attention(self.entries)
        annotate_native_sources(self.entries)
        annotate_authoring(self.entries)
        self._fill()
        c = result['global_report']['counts']
        from collections import Counter
        current = Counter(current_editorial_state(r, getattr(self.manager, '_editorial_decisions', {}))['status']
                          for r in self.entries)
        self.status.set(
            f"{c['kristals']} Kristals · {c['blocker']} blockers · {c['warning']} technical warnings · "
            f"{current['Ready']} Ready · {current['Needs work']} Needs work · "
            f"{current['Building']} Building · {current['Not assessed']} Not assessed"
            + '  |  Local editorial states, not Framework qualification.'
            + (' Previous report restored.' if restored else ' New analysis complete.')
        )
        self._set_running(False)

    def _edit_editorial_state(self, status: str):
        selected = self.table.selection()
        if not selected:
            messagebox.showinfo('Select a Kristal', 'Select a Kristal first.', parent=self)
            return
        row = self.entries[int(selected[0])]
        from .editorial_decisions import set_decision, clear_decision, load_decisions
        option = status.casefold()
        note = ''
        if option == 'needs work':
            note = simpledialog.askstring('Reason', 'What specifically needs work?', parent=self)
            if note is None:
                return
            note = note.strip()
            if not note:
                messagebox.showerror('Reason required', 'Describe the issue briefly.', parent=self)
                return
        if option == 'ready' and not messagebox.askyesno('Editorial only',
                    'Mark this Kristal editorially Ready?\nThis is NOT C1/C2/C3 qualification.', parent=self):
            return
        try:
            if option == 'clear':
                clear_decision(row)
            else:
                set_decision(row, status, note)
            self.manager._editorial_decisions = load_decisions()
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            messagebox.showerror('Cannot save', str(exc), parent=self)
            return
        self._fill()
        self.manager.refresh(prefer=row['path'])

    def _fill(self):
        self.table.delete(*self.table.get_children())
        for i,r in enumerate(self.entries):
            review = assess_review(r)
            editorial = current_editorial_state(r, getattr(self.manager, '_editorial_decisions', {}))
            review['editorial_state'] = editorial['status']
            if not matches_focus(review, self.review_focus_var.get()):
                continue
            if self.problems_only.get() and r['priority'] not in ('blocker','warning'):
                continue
            kstate = kristalizer_bridge.lookup(self.kristalizer, r.get('path'))
            kbuild = kristalizer_bridge.lookup_build(self.kristalizer_build, r.get('path'))
            displayed = (('BUILT (copy)' if kbuild['status'] == 'BUILT' else kbuild['status']) if kbuild else
                         (kstate['v11'] if kstate else 'Not imported'))
            suggestions = []
            if r.get('proposed_arketype'):
                suggestions.append('Arketype: ' + display_category(r['proposed_arketype'], 'ark'))
            if r.get('proposed_unesco'):
                suggestions.append('UNESCO: ' + display_category(r['proposed_unesco'], 'unesco'))
            elif r.get('proposed_unesco_domain'):
                suggestions.append('UNESCO domain: ' + display_category(r['proposed_unesco_domain'], 'unesco_domain'))
            values=(r['title'],editorial['status'],review['stage'],review['next_action'],
                    display_authoring_status(r), display_source_catalog(r), display_native_source_review(r),
                    r['priority'],r['readiness'],display_content_status(r['content_status']),
                    display_declared(r,'primary_archetype'), display_declared(r,'primary_usage'),
                    display_semantic_role(r), display_prf_refinement(r),
                    display_declared(r,'subject_domain'), display_unesco_declaration(r),
                    display_current_unesco_review(r), display_ark_structure(r), display_registered_ark(r), displayed,
                    '; '.join(suggestions) if suggestions else 'No new proposals',
                    ', '.join(r['keywords'][:6]))
            self.table.insert('','end',iid=str(i),values=values,tags=(r['priority'],))
        self._update_selection_buttons()

    def _export_queue(self):
        if not self.entries:
            messagebox.showinfo('Nothing to export', 'Scan the Kristals first.', parent=self)
            return
        target = filedialog.asksaveasfilename(parent=self, title='Export local review queue',
                    initialfile='KRISTAL_REVIEW_QUEUE.csv', defaultextension='.csv',
                    filetypes=[('CSV spreadsheet', '*.csv')])
        if not target:
            return
        try:
            path = export_review_queue(target, self.entries,
                                       source_root=self.manager.path_var.get())
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror('Export rejected', str(exc), parent=self)
            return
        messagebox.showinfo('Review queue exported',
              f'{path}\n\nUnapproved observations; no canonical changes.', parent=self)

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
            messagebox.showerror('Copy failed', f'Clipboard unavailable: {exc}',
                                 parent=parent or self)
            return False
        self.status.set(f'{label} copied ({len(text):,} characters). Paste into ChatGPT with Ctrl+V.')
        return True

    def _copy_all(self):
        if self.result:
            self._copy_text(format_chatgpt_summary(self.result['global_report'], self.kristalizer, self.kristalizer_build),
                            label='Global results')

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
        data = {'synthese_globale': row,
                'review_progress': assess_review(row),
                'authoring_observation': row.get('authoring_observation'),
                'classification_names': {
                    'declared_arketype': display_declared(row, 'primary_archetype'),
                    'declared_usage_profile': display_declared(row, 'primary_usage'),
                    'declared_unesco_subjects': display_unesco_declaration(row),
                    'unesco_editorial_review': display_unesco_review(row),
                    'registered_arketype': display_registered_ark(row),
                    'proposed_arketype': (display_category(row['proposed_arketype'], 'ark')
                                          if row.get('proposed_arketype') else 'None proposed'),
                    'proposed_unesco_subject': (display_category(row['proposed_unesco'], 'unesco')
                                                if row.get('proposed_unesco') else 'None proposed'),
                }}
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
            messagebox.showinfo('Nothing selected',
                                'Select a Kristal in the list, then click Copy.', parent=self)
            return
        self._copy_text(json.dumps(data, ensure_ascii=False, indent=2),
                        label='Kristal details')

    def _details(self):
        selected=self.table.selection()
        if not selected:return
        row=self.entries[int(selected[0])]
        popup=tk.Toplevel(self)
        popup.title('Observations and proposals — ' + row['title'])
        popup.geometry('900x620')
        frame=ttk.Frame(popup,padding=12);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text=row['title']+' · unvalidated triage data',style='H2.TLabel').pack(anchor='w')
        text=tk.Text(frame,wrap='word',font=('Consolas',10))
        text.pack(fill='both',expand=True,pady=(8,0))
        data = self._selected_record() or {'synthese_globale': row}
        draft = row.get('semantic_enrichment') or {}
        if draft.get('status') == 'MATCHED_CURRENT_DESCRIPTORS':
            intro = ('AI SEMANTIC REVIEW — DRAFT, NOT APPROVED\n\n'
                     + 'Role: ' + str(draft.get('semantic_role_en')) + '\n'
                     + 'Purpose: ' + str(draft.get('semantic_scope_en')) + '\n'
                     + 'Key boundary: ' + str(draft.get('critical_distinction_en')) + '\n'
                     + 'PRF: ' + display_prf_refinement(row) + '\n'
                     + 'UNESCO review: ' + display_unesco_review(row) + '\n'
                     + 'Evidence: project metadata and historic summaries only; current descriptor matched.\n'
                     + 'No semantic / C1-C2-C3 qualification or publication authority.\n\n'
                     + '--- Full traceable evidence ---\n')
        else:
            intro = 'AI semantic review not current: ' + str(draft.get('status', 'NOT_REVIEWED')) + '\n\n'
        progress = assess_review(row)
        intro = ('REVIEW STAGE (not approval): ' + progress['stage'] + '\n'
                 + 'NEXT ACTION: ' + progress['next_action'] + '\n'
                 + 'NATIVE EVIDENCE: ' + display_native_source_review(row) + '\n\n' + intro)
        payload = intro + json.dumps(data, ensure_ascii=False, indent=2)
        text.insert('1.0', payload)
        text.configure(state='disabled')
        actions = ttk.Frame(frame)
        actions.pack(fill='x', pady=(7, 0))
        feedback = tk.StringVar(value='')
        ttk.Label(actions, textvariable=feedback, style='Sub.TLabel').pack(side='left')
        def copy_details():
            if self._copy_text(payload, label='Kristal details', parent=popup):
                feedback.set('Copied! Paste into ChatGPT with Ctrl+V.')
        ttk.Button(actions, text='Copy these details', command=copy_details).pack(side='right', padx=(7,0))
        ttk.Button(actions,text='Close',command=popup.destroy).pack(side='right')

    def _open_ai_review(self):
        if not self.result:
            return
        target = Path(self.result['report_directory']) / 'ai_semantic_review_127.html'
        if target.is_file() and not target.is_symlink():
            webbrowser.open(target.resolve().as_uri())
        else:
            messagebox.showinfo('AI dossiers not generated',
                                'Run Scan and analyze Kristals to generate the 127 AI review dossiers.', parent=self)

    def _open_html(self):
        if self.result:
            path=Path(self.result['html_report'])
            if path.is_file():webbrowser.open(path.resolve().as_uri())

    def _open_zip_folder(self):
        if self.result:
            path=Path(self.result['problem_archive'])
            if path.is_file():
                # Show exact ZIP location without uploading anything.
                messagebox.showinfo('Issues ZIP ready',str(path),parent=self)
            else:
                messagebox.showwarning('Archive not found','The ZIP must be regenerated.',parent=self)

    def _open_plan(self):
        if self.result:
            path=Path(self.result['report_directory']) / 'plan_corrections.json'
            if path.is_file():
                popup=tk.Toplevel(self);popup.title('Correction plan (preview only)')
                popup.geometry('850x610')
                txt=tk.Text(popup,wrap='word',font=('Consolas',10))
                txt.pack(fill='both',expand=True)
                txt.insert('1.0',path.read_text('utf-8'))
                txt.configure(state='disabled')

    def _close(self):
        if getattr(self.manager,'_global_dialog',None) is self:
            self.manager._global_dialog = None
        self.destroy()
