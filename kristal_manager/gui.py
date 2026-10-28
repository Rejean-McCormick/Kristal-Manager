"""Kristal Manager: English-first local inventory, checks and descriptive catalog.

Inventory, verification and catalog operations remain read-only. The separately
confirmed folder-rename action changes one workspace path but never its files.
Publishing and access authorization are not inferred from local checks.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
import subprocess
from pathlib import Path
from queue import Empty, Queue
import traceback
from threading import Thread
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

from .core import detect_kristal, scan_roots
from .diag_bridge import DiagConfigurationError, validate_config, run_diagnostic, run_official_diagnostic
from .diag_panel import DiagnosticPanel
from .batch_panel import BatchRenamePanel
from .classification_panel import ClassificationPanel
from .classification_bridge import (observe, reference, display_domain, display_micro, display_isced)
from .inventory import inventory, konstellation_preview, save_private_inventory
from .icon_bridge import discover_icon, read_registry_icon_index, tk_photo_from_icon, IconInfo
from .operational import assess_local
from .ui_prefs import default_root, load_settings, save_settings
from .workspace_tools import (category_of, classification_of, arketype_of, usage_profile_of,
                              is_historical, plan_rename, apply_rename, export_workspace)

BG = '#f5f8f8'
TEXT = '#243e3c'
BRAND = '#1E6864'  # Official Kristal brand color
BRAND_DARK = '#155451'
BRAND_TINT = '#eaf3f0'
TEAL = BRAND
SUB = '#506865'


def display_state_id(state_ref: str | None) -> str:
    """Compact presentation only; original identifier is retained in JSON detail."""
    if not state_ref:
        return '—'
    components = state_ref.split(':')
    if len(components) >= 4 and components[0] == 'urn' and components[1] == 'kristal':
        if components[2] == 'state':
            return ':'.join(components[3:])
        if components[-1] == 'state':
            return ':'.join(components[2:-1])
    return state_ref


def display_category(row: dict) -> str:
    value = category_of(row)
    return {'Historical archive':'Historical archive',
            'Non catégorisé':'Uncategorized',
            'Kristal imbriqué':'Nested Kristal'}.get(value, value)


class ManagerWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Kristal Manager — Inventory & diagnostics')
        self.geometry('1260x830')
        self.minsize(900, 620)
        self.configure(bg=BG)
        self._logo_image = None
        self._app_icon_image = None
        self._apply_window_icon()

        self.settings = load_settings()
        self.events = Queue()
        self.rows: list[dict] = []
        self.icons: dict[str, IconInfo] = {}
        self.icon_images: dict[str, tk.PhotoImage] = {}
        self.roots: list[Path] = []
        self.busy = False
        self.catalog_overview: Path | None = None
        self._current_job = None
        self._diag_dialog = None
        self._unfiltered_count = 0
        self.path_var = tk.StringVar(value=default_root(self.settings))
        self.filter_var = tk.StringVar()
        self.category_var = tk.StringVar(value='All UNESCO domains')
        self.micro_var = tk.StringVar(value='All microthesauri')
        self.isced_var = tk.StringVar(value='All ISCED fields')
        self.taxonomy_cache: dict[str, dict] = {}
        self.arketype_var = tk.StringVar(value='All Arketypes')
        self.usage_var = tk.StringVar(value='All usage profiles')
        self.show_history_var = tk.BooleanVar(value=False)
        self.sort_field = 'title'
        self.sort_desc = False
        self.status_var = tk.StringVar(value='Choose a folder, then click Scan folder.')
        self.scope_var = tk.StringVar(value='Folder not scanned')
        self.count_var = tk.StringVar(value='— Kristals')
        self.ready_var = tk.StringVar(value='— ready')
        self.issue_var = tk.StringVar(value='— to review')
        self.selection_var = tk.StringVar(value='No Kristal selected')

        self._configure_style()
        self._create_menu()
        self._create_header()
        self._create_browser()
        self._create_footer()
        self._refresh_actions()
        self.log('INFO', 'Manager opened. No automatic scan or writes to Kristals.')
        self.log('INFO', f'Suggested folder: {self.path_var.get()}')
        self.after(120, self.poll)

    @staticmethod
    def _asset_path(name: str) -> Path:
        # Works from another working directory and from the .pyw launcher.
        return Path(__file__).resolve().parent / 'assets' / name

    def _apply_window_icon(self):
        # Tk's iconphoto handles cross-platform PNG; on Windows the native ICO
        # also enables the branded titlebar/taskbar representation.
        try:
            self._app_icon_image = tk.PhotoImage(file=str(self._asset_path('app_icon.png')))
            self.iconphoto(True, self._app_icon_image)
        except (tk.TclError, OSError):
            self._app_icon_image = None
        if os.name == 'nt':
            for candidate in ('window.ico', 'app_icon.ico'):
                try:
                    self.iconbitmap(str(self._asset_path(candidate)))
                    break
                except (tk.TclError, OSError):
                    pass  # Missing/bad icon must not prevent launching Manager.

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
        filemenu.add_command(label='Choose folder…', command=self.select_root)
        filemenu.add_command(label='Scan folder      Ctrl+R', command=self.start_scan)
        filemenu.add_separator()
        filemenu.add_command(label='Export inventory JSON…', command=self.export)
        filemenu.add_command(label='Export private Konstellation preview…', command=self.export_konstellation)
        filemenu.add_separator()
        filemenu.add_command(label='Exit', command=self.destroy)
        bar.add_cascade(label='File', menu=filemenu)
        actions = tk.Menu(bar, tearoff=False)
        actions.add_command(label='Verify selected Kristal (local)', command=self.start_verify)
        actions.add_command(label='Open diagnostic center…', command=self.start_diag_selected)
        actions.add_command(label='Configure external KristalDiag (advanced)…', command=self.configure_diag)
        actions.add_command(label='Export diagnostic observations (JSON)…', command=self.export_diag_report)
        actions.add_command(label='Catalog selected Kristal', command=self.start_catalog_selected)
        actions.add_command(label='Catalog all Kristals in folder', command=self.start_catalog_all)
        actions.add_command(label='Open content HTML overview…', command=self.open_content_overview)
        actions.add_separator()
        actions.add_command(label='UNESCO classification audit…', command=self.open_classification_audit)
        actions.add_command(label='Normalize folders in batch…', command=self.open_batch_rename)
        actions.add_command(label='Preview / rename selected folder…', command=self.rename_selected)
        actions.add_command(label='Export selected Kristal as ZIP…', command=lambda: self.export_selected('zip'))
        actions.add_command(label='Export selected Kristal as .kristal (experimental)…', command=lambda: self.export_selected('kristal'))
        bar.add_cascade(label='Actions', menu=actions)
        icons_menu = tk.Menu(bar, tearoff=False)
        icons_menu.add_command(label='Refresh icons (read-only)', command=self.refresh_icons)
        icons_menu.add_command(label='Selected icon information', command=self.icon_info)
        icons_menu.add_separator()
        icons_menu.add_command(label='Open Kristal Icon Generator (Windows)…', command=self.launch_icon_generator)
        bar.add_cascade(label='Icons', menu=icons_menu)
        logs = tk.Menu(bar, tearoff=False)
        logs.add_command(label='Copy log', command=self.copy_log)
        logs.add_command(label='Clear log', command=self.clear_log)
        logs.add_command(label='Save log…', command=self.save_log)
        bar.add_cascade(label='Log', menu=logs)
        helpmenu = tk.Menu(bar, tearoff=False)
        helpmenu.add_command(label='Understanding statuses and actions', command=self.open_help)
        helpmenu.add_command(label='About / limitations', command=self.show_limits)
        bar.add_cascade(label='Help', menu=helpmenu)
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
        ttk.Label(names, text='Kristal Manager', style='Title.TLabel').pack(anchor='w')
        ttk.Label(names,
                  text='Browse · Verify · Catalog · Integrated KristalDiag | No publishing',
                  style='BrandHeader.TLabel').pack(anchor='w')

        source = ttk.LabelFrame(self, text='1 · Folder to scan', style='Section.TLabelframe')
        source.pack(fill='x', padx=18, pady=(5, 5))
        pathline = ttk.Frame(source)
        pathline.pack(fill='x')
        self.root_entry = ttk.Entry(pathline, textvariable=self.path_var, font=('Consolas', 10))
        self.root_entry.pack(side='left', fill='x', expand=True)
        self.root_entry.bind('<Return>', lambda _: self.start_scan())
        ttk.Button(pathline, text='Browse…', command=self.select_root).pack(side='left', padx=(7, 0))
        self.scan_button = ttk.Button(pathline, text='Scan folder', style='Primary.TButton', command=self.start_scan)
        self.scan_button.pack(side='left', padx=(7, 0))
        self.path_var.trace_add('write', self._path_changed)
        ttk.Label(source, text='The path above controls global scans. Cataloging the selected Kristal is a separate action.',
                  style='Sub.TLabel').pack(anchor='w', pady=(6, 0))

        summary = ttk.Frame(self, padding=(20, 4))
        summary.pack(fill='x')
        for var in (self.count_var, self.ready_var, self.issue_var):
            ttk.Label(summary, textvariable=var, style='H2.TLabel').pack(side='left', padx=(0, 24))
        ttk.Label(summary, textvariable=self.scope_var, style='Sub.TLabel').pack(side='right')

    def _create_browser(self):
        wrapper = ttk.LabelFrame(self, text='2 · Browse Kristals', style='Section.TLabelframe')
        wrapper.pack(fill='both', expand=True, padx=18, pady=(6, 6))
        controls = ttk.Frame(wrapper)
        controls.pack(fill='x', pady=(0, 7))
        ttk.Label(controls, text='Search').pack(side='left')
        filter_entry = ttk.Entry(controls, textvariable=self.filter_var)
        filter_entry.pack(side='left', fill='x', expand=True, padx=(8, 5))
        self.filter_entry = filter_entry
        ttk.Button(controls, text='Clear filter', command=lambda: self.filter_var.set('')).pack(side='left')
        self.actions_menu = tk.Menu(self, tearoff=0)
        self.actions_menu.add_command(label='Scan folder', command=self.start_scan)
        self.actions_menu.add_command(label='Refresh icons', command=self.refresh_icons)
        self.actions_menu.add_command(label='Icon information', command=self.icon_info)
        self.actions_menu.add_command(label='Open Windows icon generator…', command=self.launch_icon_generator)
        self.actions_menu.add_separator()
        self.actions_menu.add_command(label='Verify selected Kristal', command=self.start_verify)
        self.actions_menu.add_command(label='Open diagnostic center…', command=self.start_diag_selected)
        self.actions_menu.add_command(label='Configure external KristalDiag (advanced)…', command=self.configure_diag)
        self.actions_menu.add_command(label='Export diagnostic observations (JSON)…', command=self.export_diag_report)
        self.actions_menu.add_command(label='Catalog selected Kristal', command=self.start_catalog_selected)
        self.actions_menu.add_command(label='Catalog all Kristals in folder', command=self.start_catalog_all)
        self.actions_menu.add_command(label='Open HTML overview', command=self.open_content_overview)
        self.actions_menu.add_command(label='UNESCO classification audit…', command=self.open_classification_audit)
        self.actions_menu.add_command(label='Normalize folders in batch…', command=self.open_batch_rename)
        self.actions_menu.add_command(label='Preview / rename selected folder…', command=self.rename_selected)
        self.actions_menu.add_command(label='Export Kristal as ZIP…', command=lambda: self.export_selected('zip'))
        self.actions_menu.add_command(label='Export Kristal as .kristal (experimental)…', command=lambda: self.export_selected('kristal'))
        self.actions_menu.add_separator()
        self.actions_menu.add_command(label='Export inventory JSON', command=self.export)
        self.actions_menu.add_command(label='Export private Konstellation preview', command=self.export_konstellation)
        self.actions_menu.add_separator()
        self.actions_menu.add_command(label='Copy log', command=self.copy_log)
        self.actions_menu.add_command(label='Clear log', command=self.clear_log)
        self.actions_button = ttk.Menubutton(controls, text='All actions ▾', menu=self.actions_menu)
        self.actions_button.pack(side='left', padx=(9, 0))
        self.filter_var.trace_add('write', lambda *_: self.refresh())
        selectors = ttk.Frame(wrapper)
        selectors.pack(fill='x', pady=(0, 6))
        ttk.Label(selectors, text='UNESCO domain').pack(side='left')
        self.category_choice = ttk.Combobox(selectors, textvariable=self.category_var, state='readonly',
                                             values=['All UNESCO domains'], width=30)
        self.category_choice.pack(side='left', padx=(7, 12))
        self.category_choice.bind('<<ComboboxSelected>>', lambda _: self.refresh())
        ttk.Label(selectors, text='Microthesaurus').pack(side='left')
        self.micro_choice = ttk.Combobox(selectors, textvariable=self.micro_var, state='readonly',
                                         values=['All microthesauri'], width=33)
        self.micro_choice.pack(side='left', padx=(7, 12))
        self.micro_choice.bind('<<ComboboxSelected>>', lambda _: self.refresh())
        ttk.Label(selectors, text='ISCED-F (icon)').pack(side='left')
        self.isced_choice = ttk.Combobox(selectors, textvariable=self.isced_var, state='readonly',
                                         values=['All ISCED fields'], width=13)
        self.isced_choice.pack(side='left', padx=(7, 12))
        self.isced_choice.bind('<<ComboboxSelected>>', lambda _: self.refresh())
        ttk.Label(selectors, text='Filter by UNESCO codes; not inferred from names', style='Sub.TLabel').pack(side='right')
        other_selectors = ttk.Frame(wrapper)
        other_selectors.pack(fill='x', pady=(0,6))
        selectors = other_selectors
        ttk.Label(selectors, text='Arketype').pack(side='left')
        self.arketype_choice = ttk.Combobox(selectors, textvariable=self.arketype_var,
                                            state='readonly', values=['All Arketypes'], width=18)
        self.arketype_choice.pack(side='left', padx=(8, 12))
        self.arketype_choice.bind('<<ComboboxSelected>>', lambda _: self.refresh())
        ttk.Label(selectors, text='Usage').pack(side='left')
        self.usage_choice = ttk.Combobox(selectors, textvariable=self.usage_var,
                                         state='readonly', values=['All usage profiles'], width=18)
        self.usage_choice.pack(side='left', padx=(8, 12))
        self.usage_choice.bind('<<ComboboxSelected>>', lambda _: self.refresh())
        ttk.Checkbutton(selectors, text='Show internal archives / snapshots',
                        variable=self.show_history_var, command=self.refresh).pack(side='left')
        ttk.Label(selectors, text='Click column headers to sort', style='Sub.TLabel').pack(side='right')

        paned = ttk.Panedwindow(wrapper, orient='vertical')
        paned.pack(fill='both', expand=True)
        upper = ttk.Frame(paned)
        paned.add(upper, weight=3)
        lower = ttk.Frame(paned)
        paned.add(lower, weight=2)

        cols = ('title', 'category', 'micro', 'isced', 'arketype', 'usage', 'readiness', 'diag', 'profile', 'state_ref', 'artifacts', 'content')
        # Keep icons with the selected Kristal's detail card, not in the table.
        self.tree = ttk.Treeview(upper, columns=cols, show='headings', selectmode='browse', height=10)
        for key, heading, width in [
            ('title', 'Kristal', 210), ('category', 'UNESCO domain', 180),
            ('micro', 'Microthesaurus', 210), ('isced', 'ISCED-F', 85),
            ('arketype', 'Arketype', 95), ('usage', 'Usage (PRF)', 100),
            ('readiness', 'Local status', 108), ('diag', 'KristalDiag', 116),
            ('profile', 'Technical profile', 125), ('state_ref', 'State ID', 130),
            ('artifacts', 'Artifacts', 88), ('content', 'Content', 155),
        ]:
            self.tree.heading(key, text=heading, command=lambda field=key: self.change_sort(field))
            self.tree.column(key, width=width, minwidth=75, stretch=key in ('title', 'category'))
        yscroll = ttk.Scrollbar(upper, orient='vertical', command=self.tree.yview)
        xscroll = ttk.Scrollbar(upper, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        upper.rowconfigure(0, weight=1)
        upper.columnconfigure(0, weight=1)
        self.tree.grid(row=0, column=0, sticky='nsew')
        yscroll.grid(row=0, column=1, sticky='ns')
        xscroll.grid(row=1, column=0, sticky='ew')
        self.tree.tag_configure('alert', foreground='#a04d25')
        self.tree.tag_configure('historic', foreground='#717d7b')
        self.tree.bind('<<TreeviewSelect>>', self.show_details)
        self.tree.bind('<Double-1>', lambda _: self.start_diag_selected())

        quick = ttk.Frame(lower)
        quick.pack(fill='x', pady=(6, 2))
        ttk.Label(quick, textvariable=self.selection_var, style='H2.TLabel').pack(side='left', fill='x', expand=True)
        self.diag_button = ttk.Button(quick, text='Diagnostic…', command=self.start_diag_selected)
        self.diag_button.pack(side='right', padx=(5, 0))
        self.verify_button = ttk.Button(quick, text='Verify this Kristal', command=self.start_verify)
        self.verify_button.pack(side='right', padx=(5, 0))
        self.selected_catalog_button = ttk.Button(quick, text='Catalog this Kristal', command=self.start_catalog_selected)
        self.selected_catalog_button.pack(side='right', padx=(5, 0))
        self.copy_path_button = ttk.Button(quick, text='Copy path', command=self.copy_selected_path)
        self.copy_path_button.pack(side='right', padx=(5, 0))
        self.icon_info_button = ttk.Button(quick, text='Icon info', command=self.icon_info)
        self.icon_info_button.pack(side='right', padx=(5, 0))
        self.organize_menu = tk.Menu(self, tearoff=False)
        self.organize_menu.add_command(label='Preview / rename folder…', command=self.rename_selected)
        self.organize_menu.add_command(label='Normalize folders in batch…', command=self.open_batch_rename)
        self.organize_menu.add_command(label='UNESCO classification audit…', command=self.open_classification_audit)
        self.organize_menu.add_separator()
        self.organize_menu.add_command(label='Export as ZIP…', command=lambda: self.export_selected('zip'))
        self.organize_menu.add_command(label='Export as .kristal (Manager format)…', command=lambda: self.export_selected('kristal'))
        self.organize_button = ttk.Menubutton(quick, text='Organize / export ▾', menu=self.organize_menu)
        self.organize_button.pack(side='right', padx=(5, 0))

        self.tabs = ttk.Notebook(lower)
        self.tabs.pack(fill='both', expand=True, pady=(4, 0))
        summary_tab = ttk.Frame(self.tabs, padding=8)
        raw_tab = ttk.Frame(self.tabs, padding=8)
        log_tab = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(summary_tab, text='Overview / next steps')
        self.tabs.add(raw_tab, text='JSON details')
        self.tabs.add(log_tab, text='Operation log')
        # Selection icon: deliberately outside the scrollable text panel.
        self.selected_icon_frame = ttk.Frame(summary_tab, width=112)
        self.selected_icon_frame.pack(side='left', fill='y', padx=(0, 12))
        self.selected_icon_frame.pack_propagate(False)
        self.selected_icon_label = ttk.Label(self.selected_icon_frame, text='No icon',
                                             anchor='center', style='Sub.TLabel')
        self.selected_icon_label.pack(fill='x', pady=(14, 4))
        self.selected_icon_caption = ttk.Label(self.selected_icon_frame, text='',
                                               anchor='center', style='Sub.TLabel', wraplength=100)
        self.selected_icon_caption.pack(fill='x')
        self.selected_icon_image = None
        self.summary_text = self._readonly_text(summary_tab, font=('Segoe UI', 10), height=8)
        self.details = self._readonly_text(raw_tab, font=('Consolas', 9), height=8)
        raw_buttons = ttk.Frame(raw_tab)
        raw_buttons.pack(fill='x', pady=(5, 0))
        ttk.Button(raw_buttons, text='Copy JSON details', command=self.copy_details).pack(side='left')
        self.journal = self._readonly_text(log_tab, font=('Consolas', 9), height=8, wrap='word')
        logbuttons = ttk.Frame(log_tab)
        logbuttons.pack(fill='x', pady=(5, 0))
        ttk.Button(logbuttons, text='Copy log', command=self.copy_log).pack(side='left')
        ttk.Button(logbuttons, text='Clear log', command=self.clear_log).pack(side='left', padx=(7, 0))
        ttk.Button(logbuttons, text='Save log…', command=self.save_log).pack(side='left', padx=(7, 0))
        self._set_text(self.summary_text, 'Select a Kristal to view its status and available actions.')
        self._set_text(self.details, 'Select a Kristal to view its JSON details.')

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
            self.status_var.set(f'Nothing to copy: {subject}.')
            return
        self.clipboard_clear()
        self.clipboard_append(value)
        self.update_idletasks()
        self.status_var.set(f'{subject} copied to clipboard.')

    def copy_log(self):
        self._clipboard(self._text(self.journal), 'Log')

    def clear_log(self):
        self._set_text(self.journal, '')
        self.status_var.set('Log cleared (files and scan results are unchanged).')

    def _safe_output(self, destination: Path, *, source: Path | None = None) -> bool:
        # Prevent user-chosen derived outputs under managed source roots.
        dest = destination.expanduser().resolve()
        protected = list(self.roots)
        if source is not None:
            protected.append(source)
        for root in protected:
            if dest.is_relative_to(root.resolve()):
                messagebox.showerror('Protected destination',
                    'Choose a location OUTSIDE the Kristal folders.\n'
                    f'Rejected destination: {destination}\nProtected folder: {root}', parent=self)
                self.log('BLOCKED', f'Derived file inside source folder: {destination}')
                return False
        return True

    def save_log(self):
        name = filedialog.asksaveasfilename(parent=self, title='Save local log',
                                            defaultextension='.txt', initialfile='kristal-manager-journal.txt',
                                            filetypes=[('Text', '*.txt')])
        if not name:
            return
        p = Path(name)
        if not self._safe_output(p):
            return
        if p.exists() and not messagebox.askyesno('Replace?', f'Replace this file?\n{p}', parent=self):
            return
        try:
            p.write_text(self._text(self.journal), encoding='utf-8')
            self.status_var.set(f'Log saved: {p}')
            self.log('INFO', f'Log saved: {p}')
        except OSError as exc:
            self._fail('Save log', exc)

    def copy_details(self):
        self._clipboard(self._text(self.details), 'JSON details')

    def copy_selected_path(self):
        row = self._selected_row()
        if row:
            self._clipboard(row['path'], 'Kristal path')

    def rename_selected(self):
        if self.busy:
            return
        row = self._selected_row()
        if not row or not self.roots:
            messagebox.showinfo('Kristal required', 'Select a scanned Kristal.', parent=self)
            return
        try:
            plan = plan_rename(row['path'], self.roots[0])
        except (OSError, ValueError, RuntimeError) as exc:
            messagebox.showinfo('Rename unavailable', str(exc), parent=self)
            return
        self.log('PREVIEW', f'Renommage : {plan.source} → {plan.destination} (aucune écriture)')
        warning = ('\nThis Kristal contains internal historical archives.' if plan.has_history else '')
        if not messagebox.askyesno('Confirm folder rename',
             f'Declared name: {plan.declared_title}\n\n'
             f'FROM: {plan.source}\nTO: {plan.destination}\n\n'
             'Only the folder will be renamed; no internal files are edited.\n'
             'WARNING: shortcuts, scripts, and absolute references may stop working.'
             + warning + '\n\nRename this folder on disk?', parent=self):
            self.log('INFO', 'Rename canceled after preview.')
            return
        try:
            new_path = apply_rename(plan, scan_root=self.roots[0])
            self.log('SUCCESS', f'Folder renamed: {new_path}')
            self.status_var.set(f'Folder renamed: {new_path.name} · relance de l’inventaire')
            self.start_scan()
        except (OSError, ValueError, RuntimeError) as exc:
            self._fail('Rename rejected or unavailable', exc, diagnostic=traceback.format_exc())

    def export_selected(self, format: str):
        if self.busy:
            return
        row = self._selected_row()
        if not row:
            messagebox.showinfo('Kristal required', 'Select a Kristal to export.', parent=self)
            return
        source = Path(row['path'])
        if not (source / 'kristal.workspace.json').is_file() or is_historical(row):
            messagebox.showinfo('Export unavailable', 'Select a Kristal, not an internal archive.', parent=self)
            return
        title = 'Kristal ZIP archive' if format == 'zip' else 'Experimental Manager .kristal archive'
        name = filedialog.asksaveasfilename(parent=self, title=title, defaultextension='.' + format,
             initialfile=source.name + '.' + format, filetypes=[(title, '*.' + format)],
             confirmoverwrite=False)
        if not name:
            return
        target = Path(name)
        if not self._safe_output(target, source=source):
            return
        if target.exists():
            messagebox.showerror('File existant', 'The Manager does not replace existing archives. Choose another name.', parent=self)
            return
        if format == 'kristal' and not messagebox.askyesno('Experimental format',
             'The .kristal file is a local ZIP archive with a Manager manifest.\n'
             'This is NOT an official Kristal Framework package.\n\nContinue?', parent=self):
            return
        self._start(f'Export {format.upper()} de « {row["title"]} »…',
                    lambda: export_workspace(source, target, format=format), folder=source, job='archive_export')

    def focus_filter(self):
        self.filter_entry.focus_set()
        self.filter_entry.select_range(0, 'end')

    def _path_changed(self, *_):
        if hasattr(self, 'scope_var') and self.roots:
            if Path(self.path_var.get()).expanduser() != self.roots[0]:
                self.scope_var.set('Path changed · rescan required')

    def select_root(self):
        current = Path(self.path_var.get()).expanduser()
        initial = current if current.is_dir() else (current.parent if current.parent.is_dir() else Path.home())
        root = filedialog.askdirectory(parent=self, title='Choose root folder or Kristal to scan',
                                       initialdir=str(initial), mustexist=True)
        if root:
            self.path_var.set(root)
            self.log('INFO', f'Dossier saisi : {root} (cliquer sur Scan folder).')

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
        self.diag_button.configure(state='normal' if idle and selected and supports_catalog and not is_historical(row) else 'disabled')
        self.selected_catalog_button.configure(state='normal' if idle and supports_catalog else 'disabled')
        self.copy_path_button.configure(state='normal' if selected else 'disabled')
        self.icon_info_button.configure(state='normal' if selected else 'disabled')
        self.organize_button.configure(state='normal' if idle and supports_catalog and not is_historical(row) else 'disabled')
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
        self.log('START', label)
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
            messagebox.showerror('Folder not found', f'Le dossier indiqué n’existe pas :\n{folder}', parent=self)
            return
        self._start('Scanning local inventory…', lambda: scan_roots([folder]),
                    folder=folder.resolve(), job='scan')

    def start_verify(self):
        row = self._selected_row()
        if not row:
            messagebox.showinfo('Selection required', 'Select a Kristal in the list first.', parent=self)
            return
        path = Path(row['path'])
        self._start(f'Vérification locale de « {row["title"]} »…',
                    lambda: (str(path), assess_local(path)), folder=path, job='verify')

    def configure_diag(self):
        """Operator explicitly chooses the trusted KristalDiag entrypoint and CLI syntax."""
        if self.busy:
            return
        dialog = tk.Toplevel(self)
        dialog.title('Configure external KristalDiag — independent C1 tool')
        dialog.geometry('790x405')
        dialog.minsize(680, 360)
        dialog.transient(self)
        dialog.grab_set()
        outer = ttk.Frame(dialog, padding=16)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='KristalDiag executable or script', style='H2.TLabel').pack(anchor='w')
        program_var = tk.StringVar(value=self.settings.get('diag_program', ''))
        argv_var = tk.StringVar(value=self.settings.get('diag_arguments', '{workspace}'))
        location = ttk.Frame(outer)
        location.pack(fill='x', pady=(7, 12))
        ttk.Entry(location, textvariable=program_var).pack(side='left', expand=True, fill='x')
        def browse():
            choice = filedialog.askopenfilename(parent=dialog, title='Trusted KristalDiag executable',
                filetypes=[('Programmes', '*.exe *.py *.js *.mjs'), ('All files', '*.*')])
            if choice:
                program_var.set(choice)
        ttk.Button(location, text='Browse…', command=browse).pack(side='left', padx=(7, 0))
        ttk.Label(outer, text='Arguments (confirm against KristalDiag documentation)').pack(anchor='w')
        ttk.Entry(outer, textvariable=argv_var).pack(fill='x', pady=(6, 8))
        ttk.Label(outer, text='Variables: {workspace} = Kristal folder; {report} = temporary JSON report.').pack(anchor='w')
        explanation = (
            'Exemple de syntaxe fictive, à ne PAS utiliser sans confirmation de KristalDiag :\n'
            '  validate --workspace {workspace} --output {report}\n\n'
            'Le Manager n’invente pas les arguments officiels. L’exécutable ou le script doit être fourni\n'
            'par vous et installé hors de C:\\mycode\\Kristal\\locals.\n'
            'Une exécution externe peut modifier des fichiers ou accéder au réseau selon l’outil.\n'
            'Un code de sortie 0 ne vaut pas attestation C1.'
        )
        ttk.Label(outer, text=explanation, justify='left', style='Sub.TLabel').pack(anchor='w', pady=(12, 8))
        bar = ttk.Frame(outer)
        bar.pack(side='bottom', fill='x')
        def save():
            try:
                validate_config(program_var.get().strip(), argv_var.get().strip(),
                    root=self.roots[0] if self.roots else self.path_var.get())
            except (OSError, DiagConfigurationError) as exc:
                messagebox.showerror('Incomplete configuration', str(exc), parent=dialog)
                return
            self.settings['diag_program'] = program_var.get().strip()
            self.settings['diag_arguments'] = argv_var.get().strip()
            try:
                save_settings(self.settings)
            except OSError as exc:
                messagebox.showerror('Preferences not saved', str(exc), parent=dialog)
                return
            self.log('CONFIG', f'KristalDiag externe configuré : {self.settings["diag_program"]}')
            self.status_var.set('KristalDiag configuré ; exécution uniquement après confirmation.')
            dialog.destroy()
        ttk.Button(bar, text='Cancel', command=dialog.destroy).pack(side='right')
        ttk.Button(bar, text='Save', style='Primary.TButton', command=save).pack(side='right', padx=(0, 8))
        dialog.wait_window()

    def start_diag_selected(self):
        """Open a guided panel: no manual executable path or CLI arguments."""
        row = self._selected_row()
        if not row or is_historical(row) or not (Path(row['path']) / 'kristal.workspace.json').is_file():
            messagebox.showinfo('Primary Kristal required',
                'Select a primary Kristal, not an internal archive.', parent=self)
            return
        if self.busy:
            messagebox.showinfo('Operation in progress', 'Finish the current operation first.', parent=self)
            return
        if self._diag_dialog and self._diag_dialog.winfo_exists():
            self._diag_dialog.lift()
            self._diag_dialog.focus_set()
            return
        self._diag_dialog = DiagnosticPanel(self, row)

    def run_diag_from_panel(self, row: dict, profile: str):
        """Run the bundled KristalDiag in a worker thread, never in the Tk thread."""
        path = Path(row['path'])
        self._start(f'KristalDiag {profile} : {row["title"]}…',
                    lambda: (str(path), run_official_diagnostic(path, profile=profile)),
                    folder=path, job='diag')

    def export_diag_report(self):
        if self.busy:
            return
        results = [r for r in self.rows if not is_historical(r) and r.get('diag_report') is not None]
        if not results:
            messagebox.showinfo('No diagnostic',
                'No KristalDiag report was observed in this session.', parent=self)
            return
        chosen = filedialog.asksaveasfilename(parent=self, title='Export observed KristalDiag results',
            initialfile='kristal-diag-observations.json', defaultextension='.json', filetypes=[('JSON', '*.json')])
        if not chosen:
            return
        destination = Path(chosen)
        if not self._safe_output(destination):
            return
        if destination.exists() and not messagebox.askyesno('Replace?', f'Remplacer {destination} ?', parent=self):
            return
        data = {
            'format': 'kristal.manager-diag-observations/0.1-experimental',
            'generated_at': datetime.now().astimezone().isoformat(),
            'scope': 'observations in the current Manager session only',
            'qualification': 'NOT_ESTABLISHED',
            'records': [{'title': r['title'], 'path': r['path'], 'state_ref': r.get('state_ref'),
                         'diag_report': r['diag_report']} for r in results],
        }
        try:
            destination.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        except OSError as exc:
            self._fail('Export KristalDiag observations', exc)
            return
        self.log('SUCCESS', f'{len(results)} KristalDiag observations exported: {destination}')
        self.status_var.set(f'{len(results)} external diagnostic reports exported · qualification not established')

    def _catalog_destination(self, suggested):
        folder = Path.home() / 'Desktop'
        if not folder.is_dir():
            folder = Path.home()
        name = filedialog.asksaveasfilename(parent=self,
                title='Derived SQLite catalog (OUTSIDE Kristal folders)',
                initialdir=str(folder), initialfile=suggested, defaultextension='.sqlite3',
                filetypes=[('SQLite catalog', '*.sqlite3')], confirmoverwrite=False)
        if not name:
            return None
        target = Path(name).expanduser().absolute()
        if not self._safe_output(target):
            return None
        if target.exists() and not messagebox.askyesno('Replace catalog?',
                f'Un catalogue existe déjà à cet emplacement. Le remplacer après validation ?\n\n{target}', parent=self):
            return None
        return target

    def start_catalog_selected(self):
        if self.busy:
            return
        row = self._selected_row()
        if not row:
            messagebox.showinfo('Selection required', 'Select the Kristal to catalog.', parent=self)
            return
        folder = Path(row['path'])
        if not (folder / 'kristal.workspace.json').is_file():
            messagebox.showinfo('Catalog unavailable',
                'This entry is auxiliary state without kristal.workspace.json.\n'
                'Cataloging requires a recognized Kristal.', parent=self)
            return
        database = self._catalog_destination(f'{row["slug"]}-contenu.sqlite3')
        if database:
            self._run_catalog(folder, database, mode='selected')

    def start_catalog_all(self):
        if self.busy:
            return
        folder = Path(self.path_var.get().strip()).expanduser()
        if not folder.is_dir():
            messagebox.showerror('Folder not found', 'Choose an existing folder.', parent=self)
            return
        if not messagebox.askyesno('Catalog all Kristals',
             'This scans all Kristals under:\n'
             f'{folder}\n\nElle crée uniquement des fichiers dérivés hors des Kristals. Continuer ?', parent=self):
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
        self._start(f'Catalogue {"du Kristal" if mode == "selected" else "du dossier"} en cours…',
                    work, folder=folder, job='catalog')

    def poll(self):
        try:
            while True:
                kind, payload, folder, diagnostic = self.events.get_nowait()
                if kind != 'diag_dependency':
                    self.busy = False
                    self._current_job = None
                if kind == 'error':
                    if self._diag_dialog and self._diag_dialog.winfo_exists():
                        self._diag_dialog.render_error(payload)
                    self._fail('Operation interrupted', RuntimeError(payload), diagnostic=diagnostic)
                elif kind == 'diag_dependency':
                    dialog, result = payload
                    if dialog.winfo_exists():
                        dialog._dependency_done(result)
                elif kind == 'scan':
                    before = self._selected_path()
                    # A new structural scan invalidates previous checks/catalogue readings; never show stale results.
                    self.rows = [r for r in payload if not r.get('hidden_auxiliary')]
                    self._load_icons()
                    self.roots = [folder]
                    self.path_var.set(str(folder))
                    self._unfiltered_count = len(self.rows)
                    self._refresh_category_choices()
                    self._remember_root(folder)
                    self.refresh(prefer=before)
                    self.scope_var.set(f'Inventory: {folder}')
                    self.status_var.set(f'{sum(not is_historical(r) for r in self.rows)} Kristals · '
                                        f'{sum(is_historical(r) for r in self.rows)} internal archives masquées · conformité non établie')
                    self.log('SUCCESS', f'Inventaire : {sum(not is_historical(r) for r in self.rows)} Kristals et '
                           f'{sum(is_historical(r) for r in self.rows)} internal archives sous {folder}')
                elif kind == 'verify':
                    path, report = payload
                    row = next((r for r in self.rows if r['path'] == path), None)
                    if row:
                        row['operational_assessment'] = report
                        if self._selected_path() == path:
                            self.show_details()
                    self.status_var.set('Local check: ' + str(report.get('operational_result')) +
                                        ' · PAS une conformité Framework')
                    self.log('RESULT', f'{Path(path).name} : {report.get("operational_result")}; '
                           f'Framework : {report.get("framework_state_verification", {}).get("status")}')
                elif kind == 'diag':
                    path, report = payload
                    row = next((r for r in self.rows if r['path'] == path), None)
                    if row:
                        row['diag_report'] = report
                    self.refresh(prefer=path)
                    self.tabs.select(0)
                    if (self._diag_dialog and self._diag_dialog.winfo_exists()
                            and self._diag_dialog.row['path'] == path):
                        self._diag_dialog.render_result(report)
                    self.status_var.set('KristalDiag : ' + str(report.get('verdict') or report['process_status']) +
                        ' · report observed; C1 qualification not established')
                    self.log('DIAG', f'{Path(path).name} : {report["process_status"]} · '
                             f'fichier JSON : {"oui" if report.get("external_report") is not None else "non"} · '
                             f'sources modifiées : {"OUI" if report["input_changed_during_run"] else "not detected"}')
                elif kind == 'archive_export':
                    self.status_var.set(f'Local archive created: {payload["path"]}')
                    self.log('SUCCESS', f'Export {payload["format"]} : {payload["files"]} fichiers · {payload["path"]}')
                    if payload['format'] == 'kristal':
                        self.log('LIMITE', 'Experimental Manager .kristal format; not certified by Framework.')
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
                        self._load_icons()
                        self._refresh_category_choices()
                        self.path_var.set(str(folder))
                        self._remember_root(folder)
                        self.scope_var.set(f'Inventory: {folder}')
                    elif not self.rows:
                        self.rows = list(observed.values())
                        self._load_icons()
                        self.roots = [folder]
                        self._refresh_category_choices()
                    current = self._selected_path()
                    self.catalog_overview = payload['overview']
                    self.refresh(prefer=current)
                    result = payload['result']
                    self.status_var.set(f'Catalog completed: {result["workspaces"]} Kristal(aux) · '
                                        f'{result["updated"]} actualisé(s), {result["cached"]} inchangé(s)')
                    self.log('SUCCESS', f'Catalogue : {result["workspaces"]} Kristals. '
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
            self.log('WARNING', f'Could not save preferences: {exc}')

    def _fail(self, label, exc, *, diagnostic=None):
        self.log('ERROR', f'{label} : {exc}')
        if diagnostic:
            self.log('TRACE', diagnostic.rstrip())
        self.tabs.select(2)
        self.status_var.set(f'{label} · see the log (no source files were modified).')
        messagebox.showerror(label, str(exc) + '\n\nLe détail est dans l’onglet Operation log.', parent=self)

    def _load_icons(self):
        """Only read already applied icons and optional exact-name Registry cache.

        This is invoked after structural changes; does not modify sources.
        PhotoImage creation happens in the Tk main thread, never in workers.
        """
        from tkinter import TclError
        self.icons = {}
        self.icon_images = {}
        self.taxonomy_cache = {}
        try:
            registry = read_registry_icon_index()
        except (OSError, ValueError) as exc:
            registry = {}
            self.log('WARNING', f'Icon Registry cache unavailable: {exc}')
        for row in self.rows:
            path = row['path']
            try:
                icon = discover_icon(path, registry_icons=registry)
                self.icons[path] = icon
                if icon.ico is not None:
                    picture = tk_photo_from_icon(tk, icon.ico, preferred=32)
                    if picture is not None:
                        self.icon_images[path] = picture
            except (OSError, ValueError, TclError) as exc:
                self.icons[path] = IconInfo('error', None, note=str(exc))
        self.log('ICONS', f'{len(self.icon_images)} icons found in {len(self.rows)} entries; no source changes.')

    def refresh_icons(self):
        if self.busy:
            return
        before = self._selected_path()
        self._load_icons()
        self.refresh(prefer=before)
        self.status_var.set(f'{len(self.icon_images)} icons found; read-only')

    def icon_info(self):
        row = self._selected_row()
        if not row:
            messagebox.showinfo('Icon information', 'Select a Kristal first.', parent=self)
            return
        icon = self.icons.get(row['path']) or discover_icon(row['path'])
        info = (f'Kristal : {row["title"]}\n'
                f'Source: {icon.source}\n'
                f'ICO file: {icon.ico or "no file found"}\n'
                f'Nature: {icon.nature or "undefined"}\n'
                f'Maturity: {icon.maturity if icon.maturity is not None else "undefined"}\n'
                f'Domains: {", ".join(icon.domains) or "—"}\n\n'
                f'{icon.note or "Read-only"}\n\n'
                'Le Registry fournit une icône de présentation, pas la preuve '
                'd’une icône Windows appliquée dans locals.')
        messagebox.showinfo('Icon provenance', info, parent=self)

    def launch_icon_generator(self):
        """Separate original Windows generator; no implicit metadata or Explorer writes."""
        if self.busy:
            return
        program = Path(__file__).resolve().parent.parent / 'tools' / 'icon-generator' / 'Ouvrir_Generateur.cmd'
        if os.name != 'nt':
            messagebox.showinfo('Windows icon generator',
                'This feature requires Windows and the Node.js runtime required by the icon generator.', parent=self)
            return
        if not program.is_file():
            messagebox.showerror('Icon generator not found', f'Lanceur introuvable : {program}', parent=self)
            return
        if not messagebox.askyesno('Open Windows icon generator?',
                'Kristal Icon Generator est un outil indépendant.\n'
                'Il utilise normalement C:\\mycode\\Kristal\\Kristal-Kollection, '
                'et NON le dossier locals de Manager.\n\n'
                'Son scan de démarrage peut écrire des métadonnées de présentation. '
                'La personnalisation des dossiers Windows n’est appliquée '
                'qu’après confirmation dans le générateur.\n\n'
                'Ouvrir cet outil ?', parent=self):
            return
        try:
            os.startfile(str(program))
            self.log('INFO', 'Icon generator opened; icon refresh remains manual.')
        except OSError as exc:
            self._fail('Launch icon generator', exc, diagnostic=traceback.format_exc())

    def _change_category(self, _event=None):
        if self.category_var.get() == 'Historical archive':
            self.show_history_var.set(True)
        self.refresh()

    def _classify(self, row: dict) -> dict:
        key = row['path']
        if key not in self.taxonomy_cache:
            self.taxonomy_cache[key] = observe(row, self.icons.get(key))
        return self.taxonomy_cache[key]

    def _refresh_category_choices(self):
        pinned = reference()
        domains = [f'{key} {val["label_en"]}' for key,val in pinned['domains'].items()]
        micro = [f'{key} {val["label_en"]}' for key,val in pinned['microthesauri'].items()]
        fields = [f'{key} {val}' for key,val in pinned['isced'].items()]
        for variable,combo,values,default in (
            (self.category_var,self.category_choice,['All UNESCO domains',*domains,'Unmapped'],'All UNESCO domains'),
            (self.micro_var,self.micro_choice,['All microthesauri',*micro,'Unmapped'],'All microthesauri'),
            (self.isced_var,self.isced_choice,['All ISCED fields',*fields,'Unmapped'],'All ISCED fields')):
            combo.configure(values=values)
            if variable.get() not in values:variable.set(default)
        primary = sorted({x for r in self.rows if not is_historical(r)
                          if (x := arketype_of(r))}, key=str.casefold)
        usages = sorted({x for r in self.rows if not is_historical(r)
                         if (x := usage_profile_of(r))}, key=str.casefold)
        arketype_values = ['All Arketypes', *primary, 'Unclassified']
        usage_values = ['All usage profiles', *usages, 'Unclassified']
        self.arketype_choice.configure(values=arketype_values)
        self.usage_choice.configure(values=usage_values)
        if self.arketype_var.get() not in arketype_values:
            self.arketype_var.set('All Arketypes')
        if self.usage_var.get() not in usage_values:
            self.usage_var.set('All usage profiles')

    def change_sort(self, field: str):
        if self.sort_field == field:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_field, self.sort_desc = field, False
        self.refresh()

    def refresh(self, *, prefer: str | None = None):
        if not hasattr(self, 'tree'):
            return
        selected = self._selected_path() if prefer is None else prefer
        for item in self.tree.get_children():
            self.tree.delete(item)
        q = self.filter_var.get().strip().casefold()
        category = self.category_var.get()
        micro_filter = self.micro_var.get()
        isced_filter = self.isced_var.get()
        selected_arketype = self.arketype_var.get()
        selected_usage = self.usage_var.get()
        visible = []
        for i, row in enumerate(self.rows):
            historic = is_historical(row)
            if historic and not self.show_history_var.get():
                continue
            classified = self._classify(row)
            cat = display_domain(classified)
            micro = display_micro(classified)
            isced = display_isced(classified)
            if category not in ('All UNESCO domains', 'All categories', 'Toutes catégories') and category != 'Unmapped' and not any(
                    category.startswith(code + ' ') for code in classified['unesco']['domain_codes']):
                continue
            if category == 'Unmapped' and classified['unesco']['domain_codes']:
                continue
            if micro_filter != 'All microthesauri' and micro_filter != 'Unmapped' and not any(
                    micro_filter.startswith(code + ' ') for code in classified['unesco']['microthesaurus_codes']):
                continue
            if micro_filter == 'Unmapped' and classified['unesco']['microthesaurus_codes']:
                continue
            if isced_filter != 'All ISCED fields' and isced_filter != 'Unmapped' and not any(
                    isced_filter.startswith(code + ' ') for code in classified['isced_f2013']['codes']):
                continue
            if isced_filter == 'Unmapped' and classified['isced_f2013']['codes']:
                continue
            ark = arketype_of(row) or 'Unclassified'
            usage = usage_profile_of(row) or 'Unclassified'
            if selected_arketype != 'All Arketypes' and ark != selected_arketype:
                continue
            if selected_usage != 'All usage profiles' and usage != selected_usage:
                continue
            corpus = ' '.join(str(row.get(k, '')) for k in
                              ('title', 'slug', 'state_ref', 'profile', 'readiness', 'native_kind', 'content_summary')) + ' ' + cat + ' ' + micro + ' ' + isced + ' ' + display_category(row) + ' ' + ark + ' ' + usage + ' ' + (self.icons.get(row['path']).nature if self.icons.get(row['path']) else '')
            if q and q not in corpus.casefold():
                continue
            metrics = (row.get('content_summary') or {}).get('metrics') or {}
            n = metrics.get('assertions')
            content = f'{n:,} assertions' if isinstance(n, int) else ('measured, not quantified' if row.get('content_summary') else 'not scanned')
            diag = row.get('diag_report') or {}
            diag_label = ('Not run' if not diag else
                          str(diag.get('verdict')) if diag.get('verdict') else
                          'Executed' if diag.get('process_status') == 'EXECUTED_EXIT_0' else
                          'Failed / timed out' if diag.get('process_status') in ('TIMEOUT', 'EXECUTED_NONZERO') else 'Review')
            ico = self.icons.get(row['path'])
            values = (row['title'], cat, micro, isced, ark if ark != 'Unclassified' else '—',
                      usage if usage != 'Unclassified' else '—',
                      row['readiness'], diag_label, row.get('profile') or '—',
                      display_state_id(row.get('state_ref')), row.get('registered_artifacts', 0), content)
            visible.append((i, row, values, historic))
        mapping = {'title': 0, 'category': 1, 'micro': 2, 'isced': 3,
                   'arketype': 4, 'usage': 5, 'readiness': 6, 'diag': 7,
                   'profile': 8, 'state_ref': 9, 'artifacts': 10, 'content': 11}
        pos = mapping.get(self.sort_field, 0)
        visible.sort(key=lambda v: (v[2][pos] if pos == 10 else str(v[2][pos]).casefold(),
                                    v[1]['path'].casefold()), reverse=self.sort_desc)
        for i, row, values, historic in visible:
            tags = ('alert',) if row.get('state_conflict') or row.get('needs_migration') else ('historic',) if historic else ()
            self.tree.insert('', 'end', iid=str(i), values=values, tags=tags)
        match = next((iid for iid in self.tree.get_children() if self.rows[int(iid)]['path'] == selected), None)
        if match is None:
            match = self.tree.get_children()[0] if self.tree.get_children() else None
        if match:
            self.tree.selection_set(match)
            self.tree.see(match)
        else:
            self.selection_var.set('No Kristal selected')
            self._set_text(self.summary_text, 'No Kristals match this folder / filter.')
            self._set_text(self.details, '')
            self._show_selection_icon(None)
        normal = [r for r in self.rows if not is_historical(r)]
        hidden = len(self.rows) - len(normal)
        self.count_var.set(f'{len(normal)} Kristal' + ('s' if len(normal) != 1 else ''))
        ready = sum(row.get('readiness') == 'READY' for row in normal)
        self.ready_var.set(f'{ready} ready')
        self.issue_var.set(f'{len(normal) - ready} to review · {hidden} internal archives')
        self._refresh_actions()
        if match:
            self.show_details()

    def show_details(self, _event=None):
        row = self._selected_row()
        if not row:
            self._refresh_actions()
            return
        self.selection_var.set(row.get('title', 'Kristal'))
        keys = ('title', 'slug', 'path', 'state_ref', 'workspace_format', 'native_kind',
                'readiness', 'profile', 'state_commitment', 'state_blob_digest', 'state_conflict_reasons',
                'portable_ai_enabled', 'ai_entrypoint_present', 'hosted_network_baseline',
                'discovery', 'operational_assessment', 'content_summary', 'diag_report')
        icon = self.icons.get(row['path'])
        taxonomy = self._classify(row)
        icon_json = {'source': icon.source, 'ico_path': str(icon.ico) if icon.ico else None,
                     'nature': icon.nature, 'maturity': icon.maturity,
                     'domains': list(icon.domains), 'note': icon.note} if icon else None
        self._set_text(self.details, json.dumps({**{k: row.get(k) for k in keys},
                                                     'manager_icon': icon_json,
                                                     'manager_category': category_of(row),
                                                     'manager_unesco_taxonomy': taxonomy,
                                                     'manager_arketype_classification': classification_of(row),
                                                     'manager_historical_archive': is_historical(row)},
                                                    ensure_ascii=False, indent=2))
        operational = row.get('operational_assessment') or {}
        discovery = operational.get('discovery') or row.get('discovery') or {}
        framework = operational.get('framework_state_verification') or {}
        content = row.get('content_summary') or {}
        outcome = operational.get('operational_result') or 'not run'
        diag = row.get('diag_report') or {}
        metrics = content.get('metrics') or {}
        info = [
            f'KRISTAL : {row["title"]}',
            f'Folder: {row["path"]}',
            f'UNESCO domain: {display_domain(taxonomy)}',
            f'UNESCO microthesaurus: {display_micro(taxonomy)}',
            f'UNESCO mapping: {taxonomy["unesco"]["status"]} (not independently verified)',
            f'ISCED-F visual field: {display_isced(taxonomy)} ({taxonomy["isced_f2013"]["source"]})',
            f'Legacy domain (free text): {display_category(row)}',
            f'Classification review: {"; ".join(taxonomy["issues"]) or "none flagged"}',
            f'Arketype: {arketype_of(row) or "Unclassified"}',
            f'Usage profile (PRF): {usage_profile_of(row) or "Unclassified"}',
            f'Supporting Arketypes: {", ".join(classification_of(row).get("supporting_archetypes") or []) or "—"}',
            f'Classification: declared metadata; not independently verified',
            f'Nested historical archive: {"yes" if is_historical(row) else "no"}',
            f'Local status: {row["readiness"]}  |  Technical profile: {row.get("profile") or "—"}',
            f'State identity: {row.get("state_ref") or "—"}',
            f'Registered artifacts: {row.get("registered_artifacts", 0)}',
            f'Icon: {icon.source if icon else "not scanned"}'
            + (f' · {icon.nature}' if icon and icon.nature else ''),
            '',
            f'Local check: {outcome}',
            f'Discovery integrity: {discovery.get("integrity") or "not measured"}',
            f'Framework verification: {framework.get("status") or "not run"}',
            f'KristalDiag : {diag.get("verdict") or diag.get("process_status") or "not run"}',
            f'Verified signed C1 attestation: not established',
            f'Content: {content.get("content_status") or "not cataloged"}',
            f'Observed assertions: {metrics.get("assertions", "not measured")}',
            '',
            'NEXT: Verify this Kristal to check registered files,',
            'use Diagnostic… to run the bundled KristalDiag,',
            'and Catalog this Kristal to inspect descriptive content.',
            'These checks do not establish a verified C1 attestation.',
        ]
        if diag:
            info.extend(['', f'External JSON report: {"received" if diag.get("external_report") is not None else "absent"}',
                         f'Known state files changed during diagnosis: {"OUI" if diag.get("input_changed_during_run") else "not detected"}',
                         f'Exit code: {diag.get("returncode")}',
                         'See JSON details for the external report.'])
        if row.get('needs_migration') or row.get('state_conflict'):
            info.extend(['', 'WARNING: structure migration or state conflict reported.'])
        if operational.get('issues'):
            info.extend(['', 'Reported issues:', *('• ' + str(x) for x in operational['issues'])])
        self._show_selection_icon(row)
        self._set_text(self.summary_text, '\n'.join(info))
        self._refresh_actions()

    def _show_selection_icon(self, row):
        """Render selected Kristal's ICO beside the detail text, not in the list."""
        self.selected_icon_image = None
        if not row:
            self.selected_icon_label.configure(image='', text='No icon')
            self.selected_icon_caption.configure(text='')
            return
        icon = self.icons.get(row['path'])
        if icon and icon.ico:
            try:
                image = tk_photo_from_icon(tk, icon.ico, preferred=64)
                if image is not None:
                    self.selected_icon_image = image
                    self.selected_icon_label.configure(image=image, text='')
                else:
                    self.selected_icon_label.configure(image='', text='No preview')
            except (tk.TclError, OSError):
                self.selected_icon_label.configure(image='', text='No preview')
        else:
            self.selected_icon_label.configure(image='', text='No icon')
        self.selected_icon_caption.configure(text=(icon.nature or icon.source) if icon else 'No icon')

    def open_classification_audit(self):
        if not self.rows:
            messagebox.showinfo('Scan required','Scan the Kristal folder first.',parent=self)
            return
        ClassificationPanel(self)

    def open_batch_rename(self):
        if self.busy:
            return
        if not self.roots:
            messagebox.showinfo('Scan required', 'Scan the local folder first.', parent=self)
            return
        try:
            BatchRenamePanel(self, self.roots[0])
        except Exception as exc:
            messagebox.showerror('Batch normalization', str(exc), parent=self)

    def open_content_overview(self):
        overview = self.catalog_overview
        if not overview or not overview.is_file():
            chosen = filedialog.askopenfilename(parent=self, title='Open existing HTML overview',
                filetypes=[('HTML', '*.html'), ('All files', '*.*')])
            if not chosen:
                return
            overview = Path(chosen)
        webbrowser.open(overview.resolve().as_uri())
        self.log('INFO', f'HTML overview opened: {overview}')

    def export(self):
        if self.busy or not self.roots:
            messagebox.showinfo('Inventory required', 'Scan a folder first.', parent=self)
            return
        name = filedialog.asksaveasfilename(parent=self, title='Private inventory JSON',
                defaultextension='.json', initialfile='kristal-inventaire-local.json', filetypes=[('JSON', '*.json')])
        if not name:
            return
        target = Path(name)
        if not self._safe_output(target):
            return
        overwrite = target.exists()
        if overwrite and not messagebox.askyesno('Replace?', f'Remplacer le fichier ?\n{target}', parent=self):
            return
        try:
            result = inventory(self.roots)
            save_private_inventory(result, target, overwrite=overwrite)
            self.log('SUCCESS', f'Inventory JSON exported: {result["record_count"]} entries · {target}')
            self.status_var.set(f'{result["record_count"]} entries exported · local only')
        except Exception as exc:
            self._fail('Inventory export', exc, diagnostic=traceback.format_exc())

    def export_konstellation(self):
        if self.busy or not self.roots:
            messagebox.showinfo('Inventory required', 'Scan a folder first.', parent=self)
            return
        from tkinter import simpledialog
        principal = simpledialog.askstring('Explicit authorization (local preview)',
                'Local principal identifier authorized to view ALL inventoried titles.\n'
                'Permissions are not checked automatically.\nCancel to decline.', parent=self)
        if not principal:
            return
        if not messagebox.askyesno('Private preview only',
             'You explicitly authorize this principal to view ALL titles in a local preview.\n'
             'No publication or activation will occur. Continue?', parent=self):
            return
        name = filedialog.asksaveasfilename(parent=self, title='Private Konstellation preview',
             defaultextension='.json', initialfile='kristal-konstellation-prive.json', filetypes=[('JSON', '*.json')])
        if not name:
            return
        dest = Path(name)
        if not self._safe_output(dest):
            return
        overwrite = dest.exists()
        if overwrite and not messagebox.askyesno('Replace?', f'Remplacer le fichier ?\n{dest}', parent=self):
            return
        try:
            result = konstellation_preview(self.roots, allowed_principals=[principal])
            save_private_inventory(result, dest, overwrite=overwrite)
            self.status_var.set(f'Private local preview: {len(result["entries"])} entries · unpublished')
            self.log('SUCCESS', f'Private Konstellation preview created: {dest}')
        except Exception as exc:
            self._fail('Konstellation export', exc, diagnostic=traceback.format_exc())

    def open_help(self):
        helptext = (
            'GETTING STARTED\n\n'
            '1. Set the root folder (Windows default: C:\\mycode\\Kristal\\locals).\n'
            '2. Click Scan folder to build the inventory without changing source files.\n'
            '3. Select a Kristal to view its profile and icon in the lower panel.\n'
            '4. Verify this Kristal to check registered source files.\n'
            '5. Diagnostic… runs bundled KristalDiag in a guided window.\n'
            '6. Catalog this Kristal produces descriptive SQLite/HTML outside source folders.\n\n'
            'ORGANIZE AND EXPORT\n'
            '• Organize / export → Preview / rename folder changes one top-level Kristal path.\n'
            '• Organize / export → Normalize folders in batch previews every proposed name.\n'
            '  Nothing is selected by default. You must explicitly select folders and approve.\n'
            '  Each selected folder is backed up to ZIP before any rename.\n'
            '  Undo from journal can restore folder names when paths and metadata still match.\n'
            '• The batch operation does not rewrite absolute paths in scripts or outside references.\n'
            '• ZIP exports copy the selected Kristal; .kristal is experimental (not an official package).\n\n'
            'PRESENTATION\n'
            '• The selected Kristal icon appears next to its overview at the bottom.\n'
            '• State ID in the list is abbreviated; the authoritative URN stays in JSON details.\n'
            '• Historical snapshots are hidden by default, without deleting anything.\n'
            '• Sort using a column header; filter by category or search text.\n\n'
            'LIMITS\n'
            'READY is a local structural status, not Framework conformance.\n'
            'Local verification and KristalDiag do not establish publication, access grants, or V11 certification.\n'
            'No GitHub publishing is performed by the Manager.'
        )
        window = tk.Toplevel(self)
        window.title('Help — workflows and limitations')
        window.geometry('770x560')
        box = ttk.Frame(window, padding=12)
        box.pack(fill='both', expand=True)
        widget = tk.Text(box, wrap='word', padx=12, pady=12, font=('Segoe UI', 10))
        widget.insert('1.0', helptext)
        widget.configure(state='disabled')
        widget.pack(fill='both', expand=True)
        ttk.Button(box, text='Close', command=window.destroy).pack(anchor='e', pady=(8, 0))
        window.transient(self)

    def show_limits(self):
        messagebox.showinfo('Kristal Manager — limitations',
            'Local inventory and diagnostics application.\n\n'
            'No GitHub publication or activation.\n'
            'Local verification only covers registered sources.\n'
            'State commitments require a compatible Framework reference to be verified.\n'
            'Framework V11 conformance still requires independent qualification.', parent=self)


def main():
    app = ManagerWindow()
    app.mainloop()


if __name__ == '__main__':
    main()
