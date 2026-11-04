"""Window for ARK structural observations. Never modifies a Kristal."""
from __future__ import annotations
import csv
import io
import json
import sqlite3
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog
from . import archetype_structure_bridge


class ArchetypePanel(tk.Toplevel):
    def __init__(self, parent, source_root, selected_root=None):
        super().__init__(parent)
        self.title('Arketype — correspondance structurelle indicative')
        self.geometry('1080x670')
        self.minsize(760,470)
        self.source_root=Path(source_root)
        self.selected_root=Path(selected_root) if selected_root else None
        self.results=[]
        self.status=tk.StringVar(value='Read-only · scores do not constitute Framework validation.')
        main=ttk.Frame(self,padding=12);main.pack(fill='both',expand=True)
        ttk.Label(main,text='Declared Arketype ↔ observed canonical structure',font=('Segoe UI',14,'bold')).pack(anchor='w')
        ttk.Label(main,text='3/3, 2/3, 1/3: descriptive indicators only, never certification. “Free” is valid. No canonical files modified.',wraplength=1030).pack(anchor='w',pady=(3,8))
        actions=ttk.Frame(main);actions.pack(fill='x')
        self.selected_btn=ttk.Button(actions,text='Inspect selected Kristal',command=self.selected)
        self.selected_btn.pack(side='left')
        if not self.selected_root:self.selected_btn.configure(state='disabled')
        self.all_btn=ttk.Button(actions,text='Inspect all Kristals',command=self.all)
        self.all_btn.pack(side='left',padx=7)
        self.export_btn=ttk.Button(actions,text='Export JSON report…',command=self.export)
        self.export_btn.pack(side='left',padx=7)
        self.copy_btn=ttk.Button(actions,text='Copy selection',command=self.copy)
        self.copy_btn.pack(side='left',padx=7)
        ttk.Button(actions,text='Fermer',command=self.destroy).pack(side='right')
        self.progress=ttk.Progressbar(main,mode='indeterminate');self.progress.pack(fill='x',pady=(9,4))
        ttk.Label(main,textvariable=self.status,wraplength=1040).pack(anchor='w')
        columns=('project','declared','mode','score','comparison','suggested','files','fields')
        area=ttk.Frame(main);area.pack(fill='both',expand=True,pady=(9,2))
        self.table=ttk.Treeview(area,columns=columns,show='headings',height=10)
        for key,label,width in [('project','Kristal',290),('declared','Declared ARK',105),('mode','Mode',90),('score','Indice',85),('comparison','Observation',230),('suggested','Suggestions',150),('files','JSON canon',95),('fields','Champs',85)]:
            self.table.heading(key,text=label);self.table.column(key,width=width,stretch=key=='project')
        sy=ttk.Scrollbar(area,orient='vertical',command=self.table.yview)
        self.table.configure(yscrollcommand=sy.set)
        self.table.pack(side='left',fill='both',expand=True);sy.pack(side='right',fill='y')
        self.table.bind('<<TreeviewSelect>>',self.show_selection)
        self.detail=tk.Text(main,height=12,wrap='word',font=('Consolas',9))
        self.detail.pack(fill='both',expand=True,pady=(5,0))
        self.detail.configure(state='disabled')
        self.export_btn.configure(state='disabled');self.copy_btn.configure(state='disabled')

    def _start(self,full):
        if getattr(self,'working',False):return
        target=self.source_root if full else self.selected_root
        if not target:return
        self.working=True;self.selected_btn.configure(state='disabled');self.all_btn.configure(state='disabled')
        self.progress.start(10);self.status.set('Observing canonical JSON keys and structures…')
        def worker():
            try:
                output=archetype_structure_bridge.inspect_all(target) if full else {'results':[archetype_structure_bridge.inspect(target)]}
                self.after(0,lambda:self._done(output.get('results',[]),None,output.get('errors',[])))
            except Exception as exc:
                self.after(0,lambda err=str(exc):self._done([],err,[]))
        threading.Thread(target=worker,daemon=True).start()

    def selected(self):self._start(False)
    def all(self):self._start(True)

    def _done(self,results,error,errors):
        self.working=False;self.progress.stop()
        self.selected_btn.configure(state='normal' if self.selected_root else 'disabled');self.all_btn.configure(state='normal')
        if error:
            self.status.set('Error: '+error);messagebox.showerror('Arketype',error,parent=self);return
        self.results=results
        # ARK observations feed the same read model as inventory and KristalDiag.
        try:
            from .central_store import record_arketype_batch
            record_arketype_batch({'results': results})
        except (OSError, ValueError, sqlite3.Error, RuntimeError) as exc:
            self.status.set('Index central ARK non disponible : ' + str(exc))
        self.table.delete(*self.table.get_children())
        for i,r in enumerate(results):
            d=r['declaration'];cand=r['suggestions'];obs=r['structure']
            self.table.insert('','end',iid=str(i),values=(r['project'],d['primary_archetype'] or '—',
               d['structure_mode'] or 'not declared',r['declared_level'],r['comparison'],
               ', '.join(x['id'] for x in cand[:3]) or '—',obs['counts']['files'],obs['counts'].get('distinct_fields',0)))
        self.status.set(f'{len(results)} Kristal(s) observed, {len(errors)} unreadable · no classification approved · no source files changed.')
        self.errors=errors
        self.export_btn.configure(state='normal' if results else 'disabled')
        self.copy_btn.configure(state='normal' if results else 'disabled')
        if results:self.table.selection_set('0');self.show_selection()

    def show_selection(self,event=None):
        items=self.table.selection()
        if not items:return
        item=self.results[int(items[0])]
        self.detail.configure(state='normal');self.detail.delete('1.0','end')
        self.detail.insert('1.0',json.dumps(item,ensure_ascii=False,indent=2))
        self.detail.configure(state='disabled')

    def copy(self):
        selected=self.table.selection()
        if not selected:return
        data=json.dumps(self.results[int(selected[0])],ensure_ascii=False,indent=2)
        self.clipboard_clear();self.clipboard_append(data);self.update_idletasks()
        self.status.set('Structure report copied; paste into ChatGPT.')

    def export(self):
        if not self.results:return
        name=filedialog.asksaveasfilename(parent=self,title='Save ARK observations',defaultextension='.json',filetypes=[('JSON','*.json')],initialfile='RAPPORT_ARKETYPE_STRUCTURE.json')
        if name:
            p=Path(name).resolve()
            for row in self.results:
                canon=Path(row['path']).resolve()/'canon'
                if p.is_relative_to(canon):
                    messagebox.showerror('Path rejected','Do not write a report into canon/.',parent=self);return
            p.write_text(json.dumps({'format':'arketype.structural-batch/0.1','results':self.results,'errors':getattr(self,'errors',[])},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            self.status.set('Report saved: '+str(p))
