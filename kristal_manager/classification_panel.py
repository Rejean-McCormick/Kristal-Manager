"""Offline UNESCO classification audit overlay; no classification writes."""
from __future__ import annotations
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .classification_bridge import build_audit, audit_html, display_domain, display_micro, display_isced, save_private_html
from .inventory import save_private_inventory


class ClassificationPanel(tk.Toplevel):
    def __init__(self, manager):
        super().__init__(manager)
        self.manager = manager
        self.title('UNESCO classification audit — Kristal Manager')
        self.geometry('1110x675')
        self.minsize(800, 470)
        self.transient(manager)
        self.report = build_audit(manager.rows, manager.icons)
        self.configure(bg='#f5f8f8')
        head = ttk.Frame(self, padding=16)
        head.pack(fill='x')
        ttk.Label(head, text='UNESCO Classification Audit', style='H2.TLabel').pack(anchor='w')
        c = self.report['counts']
        ttk.Label(head, text=f'{c["kristals"]} Kristals  ·  {c["unesco_declared"]} UNESCO declared  ·  '
                    f'{c["isced_observed"]} ISCED observed  ·  {c["needs_review"]} flagged for review').pack(anchor='w', pady=(5,0))
        ttk.Label(head, text='Framework v7: 7 domains / 88 microthesauri  •  Icon Generator: ISCED-F 2013. '
                    'No automatic assignment or source modifications.', style='Sub.TLabel').pack(anchor='w',pady=(6,0))
        actions = ttk.Frame(self, padding=(16,2))
        actions.pack(fill='x')
        ttk.Button(actions, text='Export JSON…', command=self.export_json).pack(side='left')
        ttk.Button(actions, text='Export HTML…', command=self.export_html).pack(side='left', padx=8)
        ttk.Button(actions, text='Close', command=self.destroy).pack(side='right')
        main = ttk.Frame(self,padding=(16,7,16,16));main.pack(fill='both',expand=True)
        cols = ('title','domain','micro','isced','status','flags')
        self.tree = ttk.Treeview(main,columns=cols,show='headings',height=12)
        for key, title, width in [('title','Kristal',180),('domain','UNESCO domain',220),
                                  ('micro','UNESCO microthesaurus',230),('isced','ISCED',65),
                                  ('status','Mapping',100),('flags','Issues',190)]:
            self.tree.heading(key,text=title)
            self.tree.column(key,width=width,minwidth=65,stretch=key in ('title','micro'))
        scroll=ttk.Scrollbar(main,orient='vertical',command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side='left',fill='both',expand=True)
        scroll.pack(side='right',fill='y')
        for i,rec in enumerate(self.report['entries']):
            self.tree.insert('','end',iid=str(i),values=(rec['title'],display_domain(rec),
                display_micro(rec),display_isced(rec),rec['unesco']['status'],
                '; '.join(rec['issues']) or '—'))
        self.tree.bind('<<TreeviewSelect>>',self._show)
        self.detail=tk.Text(self,height=8,wrap='word',font=('Consolas',9),background='#ffffff')
        self.detail.pack(fill='both',padx=16,pady=(0,16))
        self.detail.configure(state='disabled')
        if self.report['entries']:
            self.tree.selection_set('0');self._show()

    def _show(self, event=None):
        selected = self.tree.selection()
        if not selected:return
        record=self.report['entries'][int(selected[0])]
        text=json.dumps(record,indent=2,ensure_ascii=False)
        self.detail.configure(state='normal');self.detail.delete('1.0','end')
        self.detail.insert('1.0',text);self.detail.configure(state='disabled')

    def _target(self, suffix):
        name = filedialog.asksaveasfilename(parent=self,title='Save private UNESCO audit',
                  defaultextension=suffix,initialfile='kristal-unesco-audit'+suffix,
                  filetypes=[('JSON' if suffix=='.json' else 'HTML', '*'+suffix)])
        if not name:return None
        target=Path(name)
        if not self.manager._safe_output(target): return None
        return target

    def export_json(self):
        target=self._target('.json')
        if target is None:return
        if target.exists() and not messagebox.askyesno('Overwrite?',f'Overwrite {target}?',parent=self):return
        try:
            save_private_inventory(self.report,target,overwrite=target.exists())
            self.manager.log('SUCCESS',f'UNESCO audit JSON: {target}')
        except (OSError, ValueError) as exc:
            messagebox.showerror('Export failed',str(exc),parent=self)

    def export_html(self):
        target=self._target('.html')
        if target is None:return
        if target.exists() and not messagebox.askyesno('Overwrite?',f'Overwrite {target}?',parent=self):return
        try:
            # JSON is the detailed diagnostic; HTML is a compact offline view.
            save_private_html(target, audit_html(self.report), overwrite=target.exists())
            self.manager.log('SUCCESS',f'UNESCO audit HTML: {target}')
        except (OSError, ValueError) as exc:
            messagebox.showerror('Export failed',str(exc),parent=self)
