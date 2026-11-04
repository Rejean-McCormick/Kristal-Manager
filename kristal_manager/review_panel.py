"""Tk window for persistent, clearly non-canonical Kristal review decisions."""
from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from .review_registry import load_registry, update_decision, _anchor_status

DISPLAY={'proposed':'Proposed (not validated)',
         'needs_discussion':'Needs discussion',
         'approved_locally':'Approved in local register',
         'rejected_locally':'Rejected in local register'}


class ReviewRegistryPanel(tk.Toplevel):
    def __init__(self,parent,source):
        super().__init__(parent)
        self.title('Manager — Kristal review register')
        self.geometry('1120x720')
        self.minsize(820,550)
        self.source=Path(source)
        self.reg=None
        frame=ttk.Frame(self,padding=13);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Review register — proposed, non-canonical classifications',
                  font=('Segoe UI',13,'bold')).pack(anchor='w')
        ttk.Label(frame,text='Historical results date from October 30 snapshots. A review is not a current disk check or Framework certification. No tag is written into locals/.',
                  wraplength=1060).pack(anchor='w',pady=(3,9))
        actions=ttk.Frame(frame);actions.pack(fill='x',pady=(0,8))
        ttk.Button(actions,text='Refresh',command=self.reload).pack(side='left')
        ttk.Button(actions,text='Record a local decision…',command=self.decide).pack(side='left',padx=(8,0))
        ttk.Button(actions,text='Export JSON copy…',command=self.export).pack(side='left',padx=(8,0))
        ttk.Button(actions,text='Copy summary',command=self.copy).pack(side='left',padx=(8,0))
        ttk.Button(actions,text='Close',command=self.destroy).pack(side='right')
        self.status=tk.StringVar(value='')
        ttk.Label(frame,textvariable=self.status).pack(anchor='w',pady=(0,7))
        columns=('name','batch','ark','review','anchors','technical')
        area=ttk.Frame(frame);area.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(area,columns=columns,show='headings',height=14)
        for key,label,width in [('name','Kristal',255),('batch','Pack',55),('ark','Suggested ARK',130),
                                 ('review','Review status',210),('anchors','Snapshot anchors',140),('technical','Historical check',220)]:
            self.tree.heading(key,text=label)
            self.tree.column(key,width=width,stretch=key=='name')
        ys=ttk.Scrollbar(area,orient='vertical',command=self.tree.yview)
        self.tree.configure(yscrollcommand=ys.set)
        self.tree.pack(side='left',fill='both',expand=True);ys.pack(side='right',fill='y')
        self.tree.bind('<<TreeviewSelect>>',self.detail)
        self.text=tk.Text(frame,height=13,wrap='word',font=('Consolas',9))
        self.text.pack(fill='both',expand=True,pady=(8,0))
        self.text.configure(state='disabled')
        self.reload()

    def reload(self):
        try:self.reg=load_registry()
        except (OSError,ValueError,TypeError) as exc:
            self.status.set('Register unavailable; no files overwritten: '+str(exc))
            messagebox.showerror('Cannot read register',str(exc),parent=self);return
        self.tree.delete(*self.tree.get_children())
        for i,entry in enumerate(self.reg['entries']):
            p=self.source/entry['name']
            anchors=_anchor_status(p,entry.get('provenance',{}).get('anchors_sha256',{})) if p.is_dir() else {'status':'UNVERIFIED'}
            entry['_local_anchor_status']=anchors
            ark=entry['archetype_review']
            self.tree.insert('','end',iid=str(i),values=(entry['name'],entry['batch'],
                ark.get('review_selected_primary') or ' / '.join(ark['recommended_primary_candidates']), DISPLAY.get(ark['status'],ark['status']),
                anchors['status'], 'PASS on copy (2026-10-30)'))
        self.status.set(f"{len(self.reg['entries'])} reviews; {sum(x['archetype_review']['status']=='approved_locally' for x in self.reg['entries'])} local approval(s). Canonical tags remain unchanged.")
        if self.reg['entries']:
            self.tree.selection_set('0');self.detail()

    def selected(self):
        selected=self.tree.selection()
        if not selected or self.reg is None:return None
        return self.reg['entries'][int(selected[0])]

    def detail(self,event=None):
        row=self.selected()
        if row is None:return
        obj={k:v for k,v in row.items() if k not in ('_local_anchor_status',)}
        obj['local_anchor_status']=row.get('_local_anchor_status')
        self.text.configure(state='normal');self.text.delete('1.0','end')
        self.text.insert('1.0',json.dumps(obj,ensure_ascii=False,indent=2))
        self.text.configure(state='disabled')

    def decide(self):
        row=self.selected()
        if row is None:
            messagebox.showinfo('Selection required','Select a Kristal first.',parent=self);return
        dialog=tk.Toplevel(self);dialog.title('Record a decision — '+row['name'])
        dialog.geometry('660x455');dialog.transient(self);dialog.grab_set()
        f=ttk.Frame(dialog,padding=15);f.pack(fill='both',expand=True)
        ttk.Label(f,text=row['name']+' · '+row['state_ref'],wraplength=620).pack(anchor='w')
        ttk.Label(f,text='Local review decision only (no ARK declaration in the Kristal).',wraplength=620).pack(anchor='w',pady=(7,10))
        values=['proposed','needs_discussion','approved_locally','rejected_locally']
        state=tk.StringVar(value=row['archetype_review']['status'])
        ttk.Label(f,text='Review status').pack(anchor='w')
        picker=ttk.Combobox(f,textvariable=state,values=values,state='readonly')
        picker.pack(fill='x',pady=(0,10))
        ttk.Label(f,text='Selected primary Arketype (explicit choice if multiple)').pack(anchor='w')
        proposed=row['archetype_review']['recommended_primary_candidates']
        primary=tk.StringVar(value=row['archetype_review'].get('review_selected_primary') or '')
        select_primary=ttk.Combobox(f,textvariable=primary,values=['']+proposed,state='readonly')
        select_primary.pack(fill='x',pady=(0,10))
        ttk.Label(f,text='Justification required (traceability)').pack(anchor='w')
        note=tk.Text(f,height=7,wrap='word');note.pack(fill='both',expand=True,pady=(0,10))
        ttk.Label(f,text='Local approval requires a justification and, if multiple candidates conflict, an explicit choice. No tag is written; a 3/3 score alone is insufficient.',wraplength=620).pack(anchor='w')
        def save():
            chosen=state.get()
            justification=note.get('1.0','end').strip()
            if chosen=='approved_locally' and row.get('_local_anchor_status',{}).get('status')!='MATCH':
                messagebox.showerror('Anchors changed',
                    'Both snapshot anchors must match before local approval. Review the active Kristal before deciding.',parent=dialog)
                return
            if chosen=='approved_locally' and not messagebox.askyesno('Confirm local review',
                'Approve this proposal ONLY in the review register? No canonical tag will be written.',parent=dialog):
                return
            try:update_decision(row['state_ref'],chosen,justification,selected_primary=primary.get() or None)
            except (OSError,ValueError,KeyError) as exc:
                messagebox.showerror('Decision rejected',str(exc),parent=dialog);return
            dialog.destroy();self.reload()
        ttk.Button(f,text='Save local decision',command=save).pack(anchor='e',pady=(7,0))

    def export(self):
        if self.reg is None:return
        path=filedialog.asksaveasfilename(parent=self,defaultextension='.json',
              initialfile='REGISTRE_REVUE_KRISTALS_EXPORT.json',filetypes=[('JSON','*.json')])
        if not path:return
        dest=Path(path).expanduser().resolve()
        src=self.source.expanduser().resolve()
        if dest.is_relative_to(src):
            messagebox.showerror('Output rejected','Export outside the locals folder.',parent=self);return
        try:dest.write_text(json.dumps({k:v for k,v in self.reg.items() if k!='entries'}|{
          'entries':[{k:v for k,v in row.items() if k!='_local_anchor_status'} for row in self.reg['entries']]},
               ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        except OSError as exc:
            messagebox.showerror('Export failed',str(exc),parent=self);return
        self.status.set('Copy exported (register unchanged): '+str(dest))

    def copy(self):
        if self.reg is None:return
        lines=['MANAGER — LOCAL NON-CANONICAL REVIEW (14 original records)']
        for row in self.reg['entries']:
            a=row['archetype_review'];lines.append(f"{row['name']} | {a.get('review_selected_primary') or ','.join(a['recommended_primary_candidates'])} | {a['status']} | anchors {row.get('_local_anchor_status',{}).get('status','UNVERIFIED')}")
        lines.append('Approval in the local register is not an ARK tag or Framework certification.')
        try:
            self.clipboard_clear();self.clipboard_append('\n'.join(lines)+'\n');self.update_idletasks()
            self.status.set('Summary copied for ChatGPT.')
        except tk.TclError as exc:messagebox.showerror('Copy failed',str(exc),parent=self)
