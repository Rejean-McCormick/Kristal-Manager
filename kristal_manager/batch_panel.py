"""Preview and opt-in batch folder normalization overlay.

All filesystem mutations are delegated to batch_rename. The UI previews and
requires confirmation, runs backups before renames, and supports guarded undo.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from queue import Queue, Empty
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .batch_rename import preview_batch, run_batch, undo_batch


class BatchRenamePanel(tk.Toplevel):
    def __init__(self, manager, root: Path):
        super().__init__(manager)
        self.manager = manager
        self.root = Path(root).resolve(strict=True)
        self.title('Batch folder normalization — Kristal Manager')
        self.geometry('1050x680')
        self.minsize(830, 535)
        self.transient(manager)
        self.protocol('WM_DELETE_WINDOW', self._close)
        self.items = preview_batch(self.root)
        self.selected = set()
        self.events = Queue()
        self.active = False
        self.last_journal = None
        self.output = tk.StringVar(value=str(Path.home() / 'Desktop' / 'Kristal-Manager-Reports'
                                              if (Path.home() / 'Desktop').is_dir()
                                              else Path.home() / 'Kristal-Manager-Reports'))
        self.status = tk.StringVar()
        self._layout()
        self._populate()
        self.grab_set()
        self.focus_set()

    def _layout(self):
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='Normalize folder names in batch', style='H2.TLabel').pack(anchor='w')
        ttk.Label(outer, text='Preview only until you approve. Only direct Kristals with kristal.workspace.json are eligible.',
                  style='Sub.TLabel').pack(anchor='w', pady=(3, 9))
        controls = ttk.Frame(outer)
        controls.pack(fill='x', pady=(0, 7))
        ttk.Button(controls, text='Select eligible', command=self._all).pack(side='left')
        ttk.Button(controls, text='Clear selection', command=self._none).pack(side='left', padx=(6, 0))
        ttk.Button(controls, text='Refresh preview', command=self._reload).pack(side='left', padx=(6, 0))
        ttk.Label(controls, textvariable=self.status, style='Sub.TLabel').pack(side='right')
        frame = ttk.Frame(outer)
        frame.pack(fill='both', expand=True)
        cols = ('pick', 'current', 'suggested', 'status', 'reason')
        self.tree = ttk.Treeview(frame, columns=cols, show='headings', selectmode='browse')
        headings = [('pick','Use',55),('current','Current folder',270),('suggested','Standard folder',290),
                    ('status','Status',115),('reason','Reason',230)]
        for key, title, width in headings:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=50, stretch=key in ('current','suggested','reason'),
                             anchor='center' if key in ('pick','status') else 'w')
        self.tree.pack(side='left', fill='both', expand=True)
        sy = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        sy.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=sy.set)
        self.tree.tag_configure('blocked', foreground='#a04d25')
        self.tree.tag_configure('unchanged', foreground='#677775')
        self.tree.bind('<ButtonRelease-1>', self._toggle_click)
        self.tree.bind('<space>', self._toggle_keyboard)
        ttk.Label(outer, text='Backup and report location (outside the Kristal folders):').pack(anchor='w', pady=(10, 3))
        line = ttk.Frame(outer)
        line.pack(fill='x')
        ttk.Entry(line, textvariable=self.output).pack(side='left', fill='x', expand=True)
        ttk.Button(line, text='Browse…', command=self._browse).pack(side='left', padx=(7, 0))
        ttk.Label(outer, text='ZIP backups are mandatory. Absolute paths inside scripts and external references are NOT updated.',
                  foreground='#a04d25', wraplength=920).pack(anchor='w', pady=(10, 5))
        self.progress = ttk.Progressbar(outer, mode='indeterminate')
        self.progress.pack(fill='x', pady=(2, 6))
        bottom = ttk.Frame(outer)
        bottom.pack(fill='x')
        self.run_button = ttk.Button(bottom, text='Back up and rename selected…', style='Primary.TButton', command=self._run)
        self.run_button.pack(side='left')
        self.undo_button = ttk.Button(bottom, text='Undo from journal…', command=self._undo)
        self.undo_button.pack(side='left', padx=(8, 0))
        ttk.Button(bottom, text='Close', command=self._close).pack(side='right')

    def _populate(self):
        self.tree.delete(*self.tree.get_children())
        for index, item in enumerate(self.items):
            symbol = '☑' if str(item.source) in self.selected else ('☐' if item.status == 'rename' else '—')
            self.tree.insert('', 'end', iid=str(index), tags=(item.status,), values=(
                symbol, item.source.name, item.destination.name if item.destination else '—',
                {'rename':'Ready','unchanged':'Already standard','blocked':'Blocked'}[item.status], item.reason))
        eligible = sum(i.status == 'rename' for i in self.items)
        self.status.set(f'{len(self.selected)} selected / {eligible} eligible · {len(self.items)} scanned')
        self.run_button.configure(state='normal' if self.selected and not self.active else 'disabled')

    def _toggle(self, iid):
        if self.active or not iid:
            return
        item = self.items[int(iid)]
        if item.status != 'rename':
            return
        key = str(item.source)
        if key in self.selected:
            self.selected.remove(key)
        else:
            self.selected.add(key)
        self._populate()
        self.tree.selection_set(iid)

    def _toggle_click(self, event):
        if self.tree.identify_column(event.x) == '#1':
            self._toggle(self.tree.identify_row(event.y))

    def _toggle_keyboard(self, _event):
        focus = self.tree.focus()
        self._toggle(focus)
        return 'break'

    def _all(self):
        self.selected = {str(i.source) for i in self.items if i.status == 'rename'}
        self._populate()

    def _none(self):
        self.selected.clear()
        self._populate()

    def _reload(self):
        if self.active:
            return
        self.items = preview_batch(self.root)
        self.selected &= {str(i.source) for i in self.items if i.status == 'rename'}
        self._populate()

    def _browse(self):
        if self.active:
            return
        result = filedialog.askdirectory(parent=self, title='Choose a backup/report directory', initialdir=str(Path.home()))
        if result:
            self.output.set(str(Path(result) / 'Kristal-Manager-Reports'))

    def _begin(self, task):
        self.active = True
        self.run_button.configure(state='disabled')
        self.undo_button.configure(state='disabled')
        self.progress.start(12)
        threading.Thread(target=lambda: self._worker(task), daemon=True).start()
        self.after(120, self._poll)

    def _worker(self, task):
        try:
            self.events.put(('ok', task()))
        except Exception as exc:
            self.events.put(('error', str(exc)))

    def _poll(self):
        try:
            state, result = self.events.get_nowait()
        except Empty:
            if self.winfo_exists():
                self.after(120, self._poll)
            return
        self.active = False
        self.progress.stop()
        self.undo_button.configure(state='normal')
        if state == 'error':
            messagebox.showerror('Batch operation failed', result, parent=self)
        else:
            self.last_journal = result.get('journal_file')
            renamed = sum(r.get('status') == 'renamed' for r in result.get('entries', []))
            rolled = sum(r.get('status') in ('rolled_back','undone') for r in result.get('entries', []))
            messagebox.showinfo('Batch operation result',
                f"Status: {result.get('status')}\nRenamed: {renamed}\nRolled back / undone: {rolled}"
                f"\n\nJournal: {self.last_journal}\n\nReview the journal before proceeding.", parent=self)
            self.manager.log('BATCH', f"{result.get('status')} · {renamed} renamed · {self.last_journal}")
            if result.get('status') in ('completed','undone','failed','undo_partial'):
                # Refresh disk paths, not just the old in-memory rows.
                self.manager.start_scan()
        try:
            self._reload()
        except Exception as exc:
            self.status.set(f'Preview unavailable: {exc}')

    def _run(self):
        if not self.selected or self.active:
            return
        dest = Path(self.output.get()).expanduser()
        selected = sorted(self.selected)
        if not messagebox.askyesno('Confirm batch rename',
            f'Rename {len(selected)} folders under:\n{self.root}\n\n'
            f'Back up each complete Kristal as ZIP before any rename.\nReports: {dest}\n\n'
            'This changes folder paths. External links and scripts are not automatically updated. Continue?', parent=self):
            return
        self._begin(lambda: run_batch(self.root, selected, dest, backup=True))

    def _undo(self):
        if self.active:
            return
        filename = filedialog.askopenfilename(parent=self, title='Choose the batch journal to undo',
             initialdir=str(Path(self.last_journal).parent if self.last_journal else Path(self.output.get())),
             filetypes=[('JSON journal','*.json')])
        if not filename:
            return
        if not messagebox.askyesno('Undo batch renames',
            'Restore folder names from the selected journal?\nThis is blocked if source/destination conflicts exist.', parent=self):
            return
        self._begin(lambda: undo_batch(filename, scan_root=self.root))

    def _close(self):
        if self.active:
            messagebox.showinfo('Batch operation in progress', 'The operation must finish before this window can close.', parent=self)
            return
        self.destroy()
