"""Kristal Manager: French-first local inventory, checks and descriptive catalog.

All source operations are read-only. Publishing and access authorization are not
inferred from structural/registered-source checks. UI Tk work stays on main thread.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
from queue import Empty, Queue
import traceback
from threading import Thread
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

from .core import detect_kristal, scan_roots
from .inventory import inventory, konstellation_preview, save_private_inventory
from .operational import assess_local
from .ui_prefs import default_root, load_settings, save_settings

BG = '#f5f8f8'
TEXT = '#243e3c'
BRAND = '#1E6864'  # Couleur officielle de Kristal
BRAND_DARK = '#155451'
BRAND_TINT = '#eaf3f0'
TEAL = BRAND
SUB = '#506865'


class ManagerWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Kristal Manager — Inventaire & diagnostics')
        self.geometry('1260x830')
        self.minsize(900, 620)
        self.configure(bg=BG)
        self._logo_image = None
        self._app_icon_image = None
        self._apply_window_icon()

        self.settings = load_settings()
        self.events = Queue()
        self.rows: list[dict] = []
        self.roots: list[Path] = []
        self.busy = False
        self.catalog_overview: Path | None = None
        self._current_job = None
        self._unfiltered_count = 0
        self.path_var = tk.StringVar(value=default_root(self.settings))
        self.filter_var = tk.StringVar()
        self.status_var = tk.StringVar(value='Choisissez un dossier, puis cliquez sur « Analyser le dossier ».')
        self.scope_var = tk.StringVar(value='Dossier non analysé')
        self.count_var = tk.StringVar(value='— cristaux')
        self.ready_var = tk.StringVar(value='— prêts')
        self.issue_var = tk.StringVar(value='— à examiner')
        self.selection_var = tk.StringVar(value='Aucun cristal sélectionné')

        self._configure_style()
        self._create_menu()
        self._create_header()
        self._create_browser()
        self._create_footer()
        self._refresh_actions()
        self.log('INFO', 'Application ouverte. Aucun scan automatique ni écriture dans les cristaux.')
        self.log('INFO', f'Dossier proposé : {self.path_var.get()}')
        self.after(120, self.poll)

    @staticmethod
    def _asset_path(name: str) -> Path:
        # Works from another working directory and from the .pyw launcher.
        return Path(__file__).resolve().parent / 'assets' / name

    def _apply_window_icon(self):
        try:
            self._app_icon_image = tk.PhotoImage(file=str(self._asset_path('app_icon.png')))
            self.iconphoto(True, self._app_icon_image)
        except (tk.TclError, OSError):
            # Branding must not block local inventory when an asset is missing.
            self._app_icon_image = None

    def _configure_style(self):
        s = ttk.Style(self)
        if 'clam' in s.theme_names():
            s.theme_use('clam')
        s.configure('TFrame', background=BG)
        s.configure('BrandHeader.TFrame', background=BRAND_TINT)
        s.configure('BrandHeader.TLabel', background=BRAND_TINT, foreground=TEXT)
        s.configure('TLabel', background=BG, foreground=TEXT, font=('Segoe UI', 10))
        s.configure('Sub.TLabel', foreground=SUB, font=('Segoe UI', 9))
        s.configure('Title.TLabel', foreground=BRAND, background=BRAND_TINT, font=('Segoe UI', 22, 'bold'))
        s.configure('H2.TLabel', font=('Segoe UI', 12, 'bold'), foreground=TEAL)
        s.configure('Section.TLabelframe', background=BG, padding=8)
        s.configure('Section.TLabelframe.Label', background=BG, foreground=TEAL, font=('Segoe UI', 10, 'bold'))
        s.configure('Treeview', font=('Segoe UI', 9), rowheight=27)
        s.configure('Treeview.Heading', font=('Segoe UI', 9, 'bold'))
        s.configure('Primary.TButton', padding=(14, 8), font=('Segoe UI', 9, 'bold'),
                    background=BRAND, foreground='white', bordercolor=BRAND,
                    focuscolor=BRAND_DARK)
        s.map('Primary.TButton',
              background=[('disabled', '#c9d5d1'), ('pressed', BRAND_DARK), ('active', BRAND_DARK)],
              foreground=[('disabled', '#536966'), ('active', 'white')])
        s.map('Treeview', background=[('selected', BRAND)], foreground=[('selected', 'white')])
        s.configure('TNotebook.Tab', padding=(15, 7))
        s.map('TNotebook.Tab', foreground=[('selected', BRAND)])
        s.configure('TButton', padding=(9, 6))

    def _create_menu(self):
        bar = tk.Menu(self)
        filemenu = tk.Menu(bar, tearoff=False)
        filemenu.add_command(label='Choisir le dossier…', command=self.select_root)
        filemenu.add_command(label='Analyser le dossier      Ctrl+R', command=self.start_scan)
        filemenu.add_separator()
        filemenu.add_command(label='Exporter inventaire JSON…', command=self.export)
        filemenu.add_command(label='Exporter aperçu privé Konstellation…', command=self.export_konstellation)
        filemenu.add_separator()
        filemenu.add_command(label='Quitter', command=self.destroy)
        bar.add_cascade(label='Fichier', menu=filemenu)
        actions = tk.Menu(bar, tearoff=False)
        actions.add_command(label='Vérifier le cristal sélectionné', command=self.start_verify)
        actions.add_command(label='Cataloguer le cristal sélectionné', command=self.start_catalog_selected)
        actions.add_command(label='Cataloguer tous les cristaux du dossier', command=self.start_catalog_all)
        actions.add_command(label='Ouvrir un aperçu de contenu HTML…', command=self.open_content_overview)
        bar.add_cascade(label='Actions', menu=actions)
        logs = tk.Menu(bar, tearoff=False)
        logs.add_command(label='Copier le journal', command=self.copy_log)
        logs.add_command(label='Effacer le journal', command=self.clear_log)
        logs.add_command(label='Enregistrer le journal…', command=self.save_log)
        bar.add_cascade(label='Journal', menu=logs)
        helpmenu = tk.Menu(bar, tearoff=False)
        helpmenu.add_command(label='Comprendre les statuts et fonctions', command=self.open_help)
        helpmenu.add_command(label='À propos / limites', command=self.show_limits)
        bar.add_cascade(label='Aide', menu=helpmenu)
        self.configure(menu=bar)
        self.bind_all('<Control-r>', lambda _: self.start_scan())
        self.bind_all('<Control-f>', lambda _: self.focus_filter())

    def _create_header(self):
        outer = ttk.Frame(self, padding=(18, 12, 18, 12), style='BrandHeader.TFrame')
        outer.pack(fill='x')
        heading = ttk.Frame(outer, style='BrandHeader.TFrame')
        heading.pack(fill='x')
        try:
            self._logo_image = tk.PhotoImage(file=str(self._asset_path('logo_header.png')))
            ttk.Label(heading, image=self._logo_image, style='BrandHeader.TLabel').pack(side='left', padx=(0, 15))
        except (tk.TclError, OSError):
            self._logo_image = None
        names = ttk.Frame(heading, style='BrandHeader.TFrame')
        names.pack(side='left', fill='x', expand=True)
        ttk.Label(names, text='KRISTAL MANAGER', style='Title.TLabel').pack(anchor='w')
        ttk.Label(names,
                  text='Explorer  ·  Vérifier localement  ·  Cataloguer  |  Aucun accès réseau ou publication',
                  style='BrandHeader.TLabel').pack(anchor='w')

        source = ttk.LabelFrame(self, text='1 · Dossier à examiner', style='Section.TLabelframe')
        source.pack(fill='x', padx=18, pady=(5, 5))
        pathline = ttk.Frame(source)
        pathline.pack(fill='x')
        self.root_entry = ttk.Entry(pathline, textvariable=self.path_var, font=('Consolas', 10))
        self.root_entry.pack(side='left', fill='x', expand=True)
        self.root_entry.bind('<Return>', lambda _: self.start_scan())
        ttk.Button(pathline, text='Parcourir…', command=self.select_root).pack(side='left', padx=(7, 0))
        self.scan_button = ttk.Button(pathline, text='Analyser le dossier', style='Primary.TButton', command=self.start_scan)
        self.scan_button.pack(side='left', padx=(7, 0))
        self.path_var.trace_add('write', self._path_changed)
        ttk.Label(source, text='Le chemin ci-dessus est le périmètre des scans globaux. Le catalogue du cristal sélectionné est une action distincte.',
                  style='Sub.TLabel').pack(anchor='w', pady=(6, 0))

        summary = ttk.Frame(self, padding=(20, 4))
        summary.pack(fill='x')
        for var in (self.count_var, self.ready_var, self.issue_var):
            ttk.Label(summary, textvariable=var, style='H2.TLabel').pack(side='left', padx=(0, 24))
        ttk.Label(summary, textvariable=self.scope_var, style='Sub.TLabel').pack(side='right')

    def _create_browser(self):
        wrapper = ttk.LabelFrame(self, text='2 · Explorer les cristaux', style='Section.TLabelframe')
        wrapper.pack(fill='both', expand=True, padx=18, pady=(6, 6))
        controls = ttk.Frame(wrapper)
        controls.pack(fill='x', pady=(0, 7))
        ttk.Label(controls, text='Rechercher').pack(side='left')
        filter_entry = ttk.Entry(controls, textvariable=self.filter_var)
        filter_entry.pack(side='left', fill='x', expand=True, padx=(8, 5))
        self.filter_entry = filter_entry
        ttk.Button(controls, text='Effacer filtre', command=lambda: self.filter_var.set('')).pack(side='left')
        self.actions_menu = tk.Menu(self, tearoff=0)
        self.actions_menu.add_command(label='Analyser le dossier', command=self.start_scan)
        self.actions_menu.add_separator()
        self.actions_menu.add_command(label='Vérifier le cristal sélectionné', command=self.start_verify)
        self.actions_menu.add_command(label='Cataloguer le cristal sélectionné', command=self.start_catalog_selected)
        self.actions_menu.add_command(label='Cataloguer tous les cristaux du dossier', command=self.start_catalog_all)
        self.actions_menu.add_command(label='Ouvrir un aperçu HTML', command=self.open_content_overview)
        self.actions_menu.add_separator()
        self.actions_menu.add_command(label='Exporter l’inventaire JSON', command=self.export)
        self.actions_menu.add_command(label='Exporter un aperçu privé Konstellation', command=self.export_konstellation)
        self.actions_menu.add_separator()
        self.actions_menu.add_command(label='Copier le journal', command=self.copy_log)
        self.actions_menu.add_command(label='Effacer le journal', command=self.clear_log)
        self.actions_button = ttk.Menubutton(controls, text='Toutes les fonctions ▾', menu=self.actions_menu)
        self.actions_button.pack(side='left', padx=(9, 0))
        self.filter_var.trace_add('write', lambda *_: self.refresh())

        paned = ttk.Panedwindow(wrapper, orient='vertical')
        paned.pack(fill='both', expand=True)
        upper = ttk.Frame(paned)
        paned.add(upper, weight=3)
        lower = ttk.Frame(paned)
        paned.add(lower, weight=2)

        cols = ('title', 'readiness', 'profile', 'state_ref', 'artifacts', 'content')
        self.tree = ttk.Treeview(upper, columns=cols, show='headings', selectmode='browse', height=10)
        for key, heading, width in [
            ('title', 'Cristal', 290), ('readiness', 'État local', 110),
            ('profile', 'Profil', 140), ('state_ref', 'Identité d’état', 320),
            ('artifacts', 'Artefacts', 90), ('content', 'Contenu observé', 190),
        ]:
            self.tree.heading(key, text=heading)
            self.tree.column(key, width=width, minwidth=75, stretch=key in ('title', 'state_ref'))
        yscroll = ttk.Scrollbar(upper, orient='vertical', command=self.tree.yview)
        xscroll = ttk.Scrollbar(upper, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        upper.rowconfigure(0, weight=1)
        upper.columnconfigure(0, weight=1)
        self.tree.grid(row=0, column=0, sticky='nsew')
        yscroll.grid(row=0, column=1, sticky='ns')
        xscroll.grid(row=1, column=0, sticky='ew')
        self.tree.tag_configure('alert', foreground='#a04d25')
        self.tree.bind('<<TreeviewSelect>>', self.show_details)

        quick = ttk.Frame(lower)
        quick.pack(fill='x', pady=(6, 2))
        ttk.Label(quick, textvariable=self.selection_var, style='H2.TLabel').pack(side='left', fill='x', expand=True)
        self.verify_button = ttk.Button(quick, text='Vérifier ce cristal', command=self.start_verify)
        self.verify_button.pack(side='right', padx=(5, 0))
        self.selected_catalog_button = ttk.Button(quick, text='Cataloguer ce cristal', command=self.start_catalog_selected)
        self.selected_catalog_button.pack(side='right', padx=(5, 0))
        self.copy_path_button = ttk.Button(quick, text='Copier son chemin', command=self.copy_selected_path)
        self.copy_path_button.pack(side='right', padx=(5, 0))

        self.tabs = ttk.Notebook(lower)
        self.tabs.pack(fill='both', expand=True, pady=(4, 0))
        summary_tab = ttk.Frame(self.tabs, padding=8)
        raw_tab = ttk.Frame(self.tabs, padding=8)
        log_tab = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(summary_tab, text='Fiche / prochaine étape')
        self.tabs.add(raw_tab, text='Détails JSON')
        self.tabs.add(log_tab, text='Journal des opérations')
        self.summary_text = self._readonly_text(summary_tab, font=('Segoe UI', 10), height=8)
        self.details = self._readonly_text(raw_tab, font=('Consolas', 9), height=8)
        raw_buttons = ttk.Frame(raw_tab)
        raw_buttons.pack(fill='x', pady=(5, 0))
        ttk.Button(raw_buttons, text='Copier les détails JSON', command=self.copy_details).pack(side='left')
        self.journal = self._readonly_text(log_tab, font=('Consolas', 9), height=8, wrap='word')
        logbuttons = ttk.Frame(log_tab)
        logbuttons.pack(fill='x', pady=(5, 0))
        ttk.Button(logbuttons, text='Copier le journal', command=self.copy_log).pack(side='left')
        ttk.Button(logbuttons, text='Effacer le journal', command=self.clear_log).pack(side='left', padx=(7, 0))
        ttk.Button(logbuttons, text='Enregistrer le journal…', command=self.save_log).pack(side='left', padx=(7, 0))
        self._set_text(self.summary_text, 'Sélectionnez un cristal pour afficher son état et les actions possibles.')
        self._set_text(self.details, 'Sélectionnez un cristal pour afficher ses informations JSON.')

    def _readonly_text(self, parent, *, font, height, wrap='word'):
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True)
        widget = tk.Text(frame, wrap=wrap, height=height, font=font, bg='white', fg=TEXT,
                         borderwidth=0, padx=10, pady=8, state='disabled', undo=False)
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=widget.yview)
        widget.configure(yscrollcommand=scrollbar.set)
        widget.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        return widget

    def _create_footer(self):
        foot = ttk.Frame(self, padding=(18, 3, 18, 10))
        foot.pack(fill='x')
        self.progress = ttk.Progressbar(foot, mode='indeterminate', length=110)
        self.progress.pack(side='right', padx=(8, 0))
        ttk.Label(foot, textvariable=self.status_var, style='Sub.TLabel').pack(side='left', fill='x', expand=True)

    def _set_text(self, widget, content):
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', content)
        widget.configure(state='disabled')

    def _text(self, widget):
        return widget.get('1.0', 'end-1c')

    def log(self, level: str, message: str):
        stamp = datetime.now().strftime('%H:%M:%S')
        self.journal.configure(state='normal')
        self.journal.insert('end', f'[{stamp}] {level:<7} {message}\n')
        self.journal.see('end')
        self.journal.configure(state='disabled')

    def _clipboard(self, value: str, subject: str):
        if not value:
            self.status_var.set(f'Rien à copier : {subject}.')
            return
        self.clipboard_clear()
        self.clipboard_append(value)
        self.update_idletasks()
        self.status_var.set(f'{subject} copié dans le presse-papiers.')

    def copy_log(self):
        self._clipboard(self._text(self.journal), 'Journal')

    def clear_log(self):
        self._set_text(self.journal, '')
        self.status_var.set('Journal effacé (les analyses et fichiers restent inchangés).')

    def _safe_output(self, destination: Path, *, source: Path | None = None) -> bool:
        # Prevent user-chosen derived outputs under managed source roots.
        dest = destination.expanduser().resolve()
        protected = list(self.roots)
        if source is not None:
            protected.append(source)
        for root in protected:
            if dest.is_relative_to(root.resolve()):
                messagebox.showerror('Destination protégée',
                    'Choisissez un emplacement EN DEHORS des dossiers de cristaux.\n'
                    f'Destination refusée : {destination}\nDossier protégé : {root}', parent=self)
                self.log('REFUS', f'Fichier dérivé dans un dossier source : {destination}')
                return False
        return True

    def save_log(self):
        name = filedialog.asksaveasfilename(parent=self, title='Enregistrer le journal local',
                                            defaultextension='.txt', initialfile='kristal-manager-journal.txt',
                                            filetypes=[('Texte', '*.txt')])
        if not name:
            return
        p = Path(name)
        if not self._safe_output(p):
            return
        if p.exists() and not messagebox.askyesno('Remplacer ?', f'Remplacer ce fichier ?\n{p}', parent=self):
            return
        try:
            p.write_text(self._text(self.journal), encoding='utf-8')
            self.status_var.set(f'Journal enregistré : {p}')
            self.log('INFO', f'Journal enregistré hors de l’application : {p}')
        except OSError as exc:
            self._fail('Enregistrement du journal', exc)

    def copy_details(self):
        self._clipboard(self._text(self.details), 'Détails JSON')

    def copy_selected_path(self):
        row = self._selected_row()
        if row:
            self._clipboard(row['path'], 'Chemin du cristal')

    def focus_filter(self):
        self.filter_entry.focus_set()
        self.filter_entry.select_range(0, 'end')

    def _path_changed(self, *_):
        if hasattr(self, 'scope_var') and self.roots:
            if Path(self.path_var.get()).expanduser() != self.roots[0]:
                self.scope_var.set('Chemin modifié · analyse à relancer')

    def select_root(self):
        current = Path(self.path_var.get()).expanduser()
        initial = current if current.is_dir() else (current.parent if current.parent.is_dir() else Path.home())
        root = filedialog.askdirectory(parent=self, title='Choisir le dossier racine ou le cristal à analyser',
                                       initialdir=str(initial), mustexist=True)
        if root:
            self.path_var.set(root)
            self.log('INFO', f'Dossier saisi : {root} (cliquer sur Analyser le dossier).')

    def _selected_row(self):
        chosen = self.tree.selection()
        return self.rows[int(chosen[0])] if chosen and int(chosen[0]) < len(self.rows) else None

    def _selected_path(self):
        r = self._selected_row()
        return r['path'] if r else None

    def _refresh_actions(self):
        row = self._selected_row()
        selected = row is not None
        supports_catalog = selected and (Path(row['path']) / 'kristal.workspace.json').is_file()
        idle = not self.busy
        self.scan_button.configure(state='normal' if idle else 'disabled')
        self.verify_button.configure(state='normal' if idle and selected else 'disabled')
        self.selected_catalog_button.configure(state='normal' if idle and supports_catalog else 'disabled')
        self.copy_path_button.configure(state='normal' if selected else 'disabled')
        self.actions_button.configure(state='normal' if idle else 'disabled')
        if self.busy:
            self.progress.start(15)
        else:
            self.progress.stop()

    def _start(self, label, fn, *, folder: Path, job: str):
        if self.busy:
            return
        self.busy = True
        self._current_job = job
        self.status_var.set(label)
        self.log('DÉBUT', label)
        self._refresh_actions()

        def worker():
            try:
                payload = fn()
                self.events.put((job, payload, folder, None))
            except Exception as exc:
                self.events.put(('error', str(exc), folder, traceback.format_exc()))
        Thread(target=worker, daemon=True).start()

    def start_scan(self):
        folder = Path(self.path_var.get().strip()).expanduser()
        if not folder.is_dir():
            messagebox.showerror('Dossier introuvable', f'Le dossier indiqué n’existe pas :\n{folder}', parent=self)
            return
        self._start('Inventaire structurel en cours…', lambda: scan_roots([folder]),
                    folder=folder.resolve(), job='scan')

    def start_verify(self):
        row = self._selected_row()
        if not row:
            messagebox.showinfo('Sélection nécessaire', 'Sélectionnez d’abord un cristal dans la liste.', parent=self)
            return
        path = Path(row['path'])
        self._start(f'Vérification locale de « {row["title"]} »…',
                    lambda: (str(path), assess_local(path)), folder=path, job='verify')

    def _catalog_destination(self, suggested):
        folder = Path.home() / 'Desktop'
        if not folder.is_dir():
            folder = Path.home()
        name = filedialog.asksaveasfilename(parent=self,
                title='Catalogue SQLite dérivé (EN DEHORS des dossiers de cristaux)',
                initialdir=str(folder), initialfile=suggested, defaultextension='.sqlite3',
                filetypes=[('Catalogue SQLite', '*.sqlite3')], confirmoverwrite=False)
        if not name:
            return None
        target = Path(name).expanduser().absolute()
        if not self._safe_output(target):
            return None
        if target.exists() and not messagebox.askyesno('Mettre à jour le catalogue ?',
                f'Un catalogue existe déjà à cet emplacement. Le remplacer après validation ?\n\n{target}', parent=self):
            return None
        return target

    def start_catalog_selected(self):
        if self.busy:
            return
        row = self._selected_row()
        if not row:
            messagebox.showinfo('Sélection nécessaire', 'Sélectionnez le cristal à cataloguer.', parent=self)
            return
        folder = Path(row['path'])
        if not (folder / 'kristal.workspace.json').is_file():
            messagebox.showinfo('Catalogue non disponible',
                'Cette entrée est un état/artefact auxiliaire, sans kristal.workspace.json.\n'
                'Le catalogue descriptif exige un cristal reconnu.', parent=self)
            return
        database = self._catalog_destination(f'{row["slug"]}-contenu.sqlite3')
        if database:
            self._run_catalog(folder, database, mode='selected')

    def start_catalog_all(self):
        if self.busy:
            return
        folder = Path(self.path_var.get().strip()).expanduser()
        if not folder.is_dir():
            messagebox.showerror('Dossier introuvable', 'Choisissez un dossier existant.', parent=self)
            return
        if not messagebox.askyesno('Catalogue global',
             'Cette opération parcourra tous les cristaux reconnus sous :\n'
             f'{folder}\n\nElle crée uniquement des fichiers dérivés hors des cristaux. Continuer ?', parent=self):
            return
        database = self._catalog_destination('kristal-contenu-global.sqlite3')
        if database:
            self._run_catalog(folder.resolve(), database, mode='all')

    def _run_catalog(self, folder: Path, database: Path, *, mode: str):
        if not self._safe_output(database, source=folder) or not self._safe_output(database.with_suffix('.html'), source=folder):
            return
        # The backend atomically replaces the database and blocks outputs inside any source workspace.
        overview = database.with_suffix('.html')
        def work():
            from .content_catalog import build_catalog, summaries, write_overview, candidates
            result = build_catalog([folder], database, direct_only=(mode == "selected"))
            summaries_by_id = {r['catalog_id']: r for r in summaries(database)['records']}
            observed = {}
            for source in candidates([folder], direct_only=(mode == "selected")):
                row = detect_kristal(source)
                if row:
                    row['content_summary'] = summaries_by_id.get(hashlib.sha256(str(source).encode()).hexdigest())
                    observed[row['path']] = row
            # Overview written only after a complete SQLite snapshot; failures keep catalog.
            write_overview(database, overview, overwrite=True)
            return {'result': result, 'rows': observed, 'overview': overview, 'mode': mode,
                    'inventory': scan_roots([folder]) if mode == 'all' else None}
        self._start(f'Catalogue {"du cristal" if mode == "selected" else "du dossier"} en cours…',
                    work, folder=folder, job='catalog')

    def poll(self):
        try:
            while True:
                kind, payload, folder, diagnostic = self.events.get_nowait()
                self.busy = False
                self._current_job = None
                if kind == 'error':
                    self._fail('Opération interrompue', RuntimeError(payload), diagnostic=diagnostic)
                elif kind == 'scan':
                    before = self._selected_path()
                    # A new structural scan invalidates previous checks/catalogue readings; never show stale results.
                    self.rows = [r for r in payload if not r.get('hidden_auxiliary')]
                    self.roots = [folder]
                    self.path_var.set(str(folder))
                    self._unfiltered_count = len(self.rows)
                    self._remember_root(folder)
                    self.refresh(prefer=before)
                    self.scope_var.set(f'Inventaire de : {folder}')
                    self.status_var.set(f'{len(self.rows)} cristaux détectés · lecture seule · conformité non établie')
                    self.log('SUCCÈS', f'Inventaire : {len(self.rows)} cristaux sous {folder}')
                elif kind == 'verify':
                    path, report = payload
                    row = next((r for r in self.rows if r['path'] == path), None)
                    if row:
                        row['operational_assessment'] = report
                        if self._selected_path() == path:
                            self.show_details()
                    self.status_var.set('Contrôle local : ' + str(report.get('operational_result')) +
                                        ' · PAS une conformité Framework')
                    self.log('RÉSULTAT', f'{Path(path).name} : {report.get("operational_result")}; '
                           f'Framework : {report.get("framework_state_verification", {}).get("status")}')
                elif kind == 'catalog':
                    observed = payload['rows']
                    for existing in self.rows:
                        new = observed.get(existing['path'])
                        if new:
                            existing['content_summary'] = new.get('content_summary')
                    if payload['mode'] == 'all':
                        # The scan root may have changed since the prior inventory.
                        # Mirror it rather than displaying unrelated workspaces.
                        prior = {r['path']: r for r in self.rows}
                        self.rows = [r for r in payload['inventory'] if not r.get('hidden_auxiliary')]
                        for row in self.rows:
                            old = prior.get(row['path'])
                            if old and old.get('operational_assessment'):
                                # Do not copy an old result: source bytes may have changed.
                                pass
                            if row['path'] in observed:
                                row['content_summary'] = observed[row['path']].get('content_summary')
                        self.roots = [folder]
                        self.path_var.set(str(folder))
                        self._remember_root(folder)
                        self.scope_var.set(f'Inventaire de : {folder}')
                    elif not self.rows:
                        self.rows = list(observed.values())
                        self.roots = [folder]
                    current = self._selected_path()
                    self.catalog_overview = payload['overview']
                    self.refresh(prefer=current)
                    result = payload['result']
                    self.status_var.set(f'Catalogue terminé : {result["workspaces"]} cristal(aux) · '
                                        f'{result["updated"]} actualisé(s), {result["cached"]} inchangé(s)')
                    self.log('SUCCÈS', f'Catalogue : {result["workspaces"]} cristaux. '
                           f'SQLite : {result["database"]} · HTML : {self.catalog_overview}')
                    self.tabs.select(0)
                self._refresh_actions()
        except Empty:
            pass
        self.after(120, self.poll)

    def _remember_root(self, folder):
        self.settings['last_root'] = str(folder)
        try:
            save_settings(self.settings)
        except OSError as exc:
            self.log('ATTENTION', f'Préférences non enregistrées : {exc}')

    def _fail(self, label, exc, *, diagnostic=None):
        self.log('ERREUR', f'{label} : {exc}')
        if diagnostic:
            self.log('TRACE', diagnostic.rstrip())
        self.tabs.select(2)
        self.status_var.set(f'{label} · consulter le journal (les sources n’ont pas été modifiées).')
        messagebox.showerror(label, str(exc) + '\n\nLe détail est dans l’onglet Journal des opérations.', parent=self)

    def refresh(self, *, prefer: str | None = None):
        if not hasattr(self, 'tree'):
            return
        selected = self._selected_path() if prefer is None else prefer
        for item in self.tree.get_children():
            self.tree.delete(item)
        q = self.filter_var.get().strip().casefold()
        for i, row in enumerate(self.rows):
            corpus = ' '.join(str(row.get(k, '')) for k in
                              ('title', 'slug', 'state_ref', 'profile', 'readiness', 'native_kind', 'content_summary'))
            if q and q not in corpus.casefold():
                continue
            metrics = (row.get('content_summary') or {}).get('metrics') or {}
            n = metrics.get('assertions')
            content = f'{n:,} assertions' if isinstance(n, int) else ('mesuré, non quantifié' if row.get('content_summary') else 'non analysé')
            self.tree.insert('', 'end', iid=str(i), values=(row['title'], row['readiness'], row.get('profile') or '—',
                            row.get('state_ref') or '—', row.get('registered_artifacts', 0), content),
                            tags=('alert',) if row.get('state_conflict') or row.get('needs_migration') else ())
        match = next((iid for iid in self.tree.get_children() if self.rows[int(iid)]['path'] == selected), None)
        if match is None:
            match = self.tree.get_children()[0] if self.tree.get_children() else None
        if match:
            self.tree.selection_set(match)
            self.tree.see(match)
        else:
            self.selection_var.set('Aucun cristal sélectionné')
            self._set_text(self.summary_text, 'Aucun cristal dans ce périmètre / filtre.')
            self._set_text(self.details, '')
        self.count_var.set(f'{len(self.rows)} cristaux')
        ready = sum(row.get('readiness') == 'READY' for row in self.rows)
        self.ready_var.set(f'{ready} prêts')
        self.issue_var.set(f'{len(self.rows) - ready} à examiner')
        self._refresh_actions()
        if match:
            self.show_details()

    def show_details(self, _event=None):
        row = self._selected_row()
        if not row:
            self._refresh_actions()
            return
        self.selection_var.set(row.get('title', 'Cristal'))
        keys = ('title', 'slug', 'path', 'state_ref', 'workspace_format', 'native_kind',
                'readiness', 'state_commitment', 'state_blob_digest', 'state_conflict_reasons',
                'portable_ai_enabled', 'ai_entrypoint_present', 'hosted_network_baseline',
                'discovery', 'operational_assessment', 'content_summary')
        self._set_text(self.details, json.dumps({k: row.get(k) for k in keys}, ensure_ascii=False, indent=2))
        operational = row.get('operational_assessment') or {}
        discovery = operational.get('discovery') or row.get('discovery') or {}
        framework = operational.get('framework_state_verification') or {}
        content = row.get('content_summary') or {}
        outcome = operational.get('operational_result') or 'non effectué'
        metrics = content.get('metrics') or {}
        info = [
            f'CRISTAL : {row["title"]}',
            f'Dossier : {row["path"]}',
            f'État local : {row["readiness"]}  |  Profil : {row.get("profile") or "—"}',
            f'Identité : {row.get("state_ref") or "—"}',
            f'Artefacts enregistrés : {row.get("registered_artifacts", 0)}',
            '',
            f'Contrôle local : {outcome}',
            f'Intégrité Discovery : {discovery.get("integrity") or "non mesurée"}',
            f'Verification Framework : {framework.get("status") or "non effectuée"}',
            f'Contenu : {content.get("content_status") or "non catalogué"}',
            f'Assertions observées : {metrics.get("assertions", "non mesurées")}',
            '',
            'À FAIRE : « Vérifier ce cristal » pour contrôler les fichiers enregistrés,',
            'puis « Cataloguer ce cristal » pour mesurer le contenu descriptif.',
            'Ces contrôles ne prouvent ni conformité Framework, ni qualification, ni publication.',
        ]
        if row.get('needs_migration') or row.get('state_conflict'):
            info.extend(['', 'ATTENTION : structure à migrer ou conflit d’état signalé.'])
        if operational.get('issues'):
            info.extend(['', 'Points signalés :', *('• ' + str(x) for x in operational['issues'])])
        self._set_text(self.summary_text, '\n'.join(info))
        self._refresh_actions()

    def open_content_overview(self):
        overview = self.catalog_overview
        if not overview or not overview.is_file():
            chosen = filedialog.askopenfilename(parent=self, title='Ouvrir un aperçu HTML existant',
                filetypes=[('HTML', '*.html'), ('Tous les fichiers', '*.*')])
            if not chosen:
                return
            overview = Path(chosen)
        webbrowser.open(overview.resolve().as_uri())
        self.log('INFO', f'Aperçu HTML ouvert : {overview}')

    def export(self):
        if self.busy or not self.roots:
            messagebox.showinfo('Inventaire nécessaire', 'Analysez d’abord un dossier.', parent=self)
            return
        name = filedialog.asksaveasfilename(parent=self, title='Inventaire privé, JSON',
                defaultextension='.json', initialfile='kristal-inventaire-local.json', filetypes=[('JSON', '*.json')])
        if not name:
            return
        target = Path(name)
        if not self._safe_output(target):
            return
        overwrite = target.exists()
        if overwrite and not messagebox.askyesno('Remplacer ?', f'Remplacer le fichier ?\n{target}', parent=self):
            return
        try:
            result = inventory(self.roots)
            save_private_inventory(result, target, overwrite=overwrite)
            self.log('SUCCÈS', f'Inventaire JSON exporté : {result["record_count"]} entrées · {target}')
            self.status_var.set(f'{result["record_count"]} enregistrements exportés · local uniquement')
        except Exception as exc:
            self._fail('Export de l’inventaire', exc, diagnostic=traceback.format_exc())

    def export_konstellation(self):
        if self.busy or not self.roots:
            messagebox.showinfo('Inventaire nécessaire', 'Analysez d’abord un dossier.', parent=self)
            return
        from tkinter import simpledialog
        principal = simpledialog.askstring('Autorisation explicite (aperçu local)',
                'Identifiant du principal local autorisé à voir TOUS les titres inventoriés.\n'
                'Aucune permission n’est vérifiée automatiquement.\nAnnuler = refuser.', parent=self)
        if not principal:
            return
        if not messagebox.askyesno('Aperçu privé seulement',
             'Vous autorisez explicitement ce principal à voir TOUS les titres de ce dossier dans un aperçu local.\n'
             'Aucune publication ou activation ne sera faite. Continuer ?', parent=self):
            return
        name = filedialog.asksaveasfilename(parent=self, title='Aperçu privé Konstellation',
             defaultextension='.json', initialfile='kristal-konstellation-prive.json', filetypes=[('JSON', '*.json')])
        if not name:
            return
        dest = Path(name)
        if not self._safe_output(dest):
            return
        overwrite = dest.exists()
        if overwrite and not messagebox.askyesno('Remplacer ?', f'Remplacer le fichier ?\n{dest}', parent=self):
            return
        try:
            result = konstellation_preview(self.roots, allowed_principals=[principal])
            save_private_inventory(result, dest, overwrite=overwrite)
            self.status_var.set(f'Aperçu local privé : {len(result["entries"])} entrées · non publié')
            self.log('SUCCÈS', f'Aperçu Konstellation privé généré : {dest}')
        except Exception as exc:
            self._fail('Export Konstellation', exc, diagnostic=traceback.format_exc())

    def open_help(self):
        helptext = ('PARCOURS RECOMMANDÉ\n\n'
           '1. Choisir un dossier racine (par défaut : C:\\mycode\\Kristal\\locals sous Windows).\n'
           '2. Analyser le dossier : identifier les cristaux, sans écriture sur les sources.\n'
           '3. Choisir un cristal dans le tableau et lire sa fiche.\n'
           '4. Vérifier ce cristal : contrôler les sources enregistrées.\n'
           '5. Cataloguer ce cristal : créer une base SQLite et un HTML descriptifs, hors des sources.\n'
           '6. Ouvrir le HTML avec « Actions » ou « Toutes les fonctions ».\n\n'
           'FONCTIONS GLOBALES\n'
           '« Cataloguer tous les cristaux du dossier » agit sur la racine saisie, PAS uniquement sur la ligne sélectionnée.\n'
           '« Exporter inventaire » écrit un JSON local privé.\n'
           '« Exporter aperçu privé Konstellation » nécessite un accord et un principal explicites.\n\n'
           'JOURNAL\n'
           'L’onglet Journal des opérations propose Copier, Effacer et Enregistrer.\n'
           'Effacer retire seulement le texte de l’interface, sans toucher aux cristaux.\n\n'
           'LIMITES\n'
           'READY = état structurel local. LOCAL_CHECKS_PASSED = sources enregistrées contrôlées.\n'
           'Le catalogue mesure le contenu ; aucun de ces résultats ne qualifie automatiquement '
           'la conformité Framework, C1/C2/C3, l’autorisation, la publication ou l’activation.')
        window = tk.Toplevel(self)
        window.title('Aide — parcours et limites')
        window.geometry('770x560')
        box = ttk.Frame(window, padding=12)
        box.pack(fill='both', expand=True)
        text = tk.Text(box, wrap='word', padx=12, pady=12, font=('Segoe UI', 10))
        text.insert('1.0', helptext)
        text.configure(state='disabled')
        text.pack(fill='both', expand=True)
        ttk.Button(box, text='Fermer', command=window.destroy).pack(anchor='e', pady=(8, 0))
        window.transient(self)

    def show_limits(self):
        messagebox.showinfo('Kristal Manager · limites de l’outil',
            'Interface locale de récupération et de diagnostic.\n\n'
            'Aucune écriture GitHub, publication ou activation.\n'
            'La vérification est limitée aux sources enregistrées.\n'
            'Les engagements d’état restent non vérifiés sans référence Framework compatible.\n'
            'La conformité v11 doit faire l’objet d’une qualification indépendante.', parent=self)


def main():
    app = ManagerWindow()
    app.mainloop()


if __name__ == '__main__':
    main()
