"""One operational control center. Advanced historic tools remain accessible in Manager.

All long-running operations are sent to a worker thread; no Tk access occurs in
workers, and automatic refresh never executes diagnostics or mutates workspaces.
"""
from __future__ import annotations
from pathlib import Path
from queue import Queue, Empty
from threading import Thread, Event
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from . import service, repository

_COLUMNS=(('title','Kristal',230),('readiness','Structure',110),
          ('diagnostic_verdict','KristalDiag',115),('diagnostic_freshness','Fraîcheur Diag',135),
          ('analysis_priority','Analyse',100),('analysis_freshness','Fraîcheur analyse',125),
          ('arketype_level','Structure ARK',165),('decisions_count','Décisions locales',125))

class UnifiedControlCenter(tk.Toplevel):
    """Operator-initiated scan/analyze/diagnose -> same persistent data source."""
    def __init__(self,master,root: str | Path, *, db=None):
        super().__init__(master)
        self.title('Kristal Manager — Centre unifié vNext')
        self.geometry('1230x740');self.minsize(800,560)
        self.root=Path(root).expanduser().resolve()
        self.db=db
        self.queue=Queue();self.busy=False;self.rows={};self.last_view=None
        self.cancel_request=Event();self.active_action=None
        self.text_status=tk.StringVar(value='Prêt. Les actions sont locales et sans publication Git.')
        self.show_issues=tk.BooleanVar(value=False)
        self.filter_text=tk.StringVar()
        self._layout()
        self.after(100,self._poll)
        self._begin('Lecture du registre',lambda:service.overview(self.root,db=self.db))

    def _layout(self):
        shell=ttk.Frame(self,padding=14);shell.pack(fill='both',expand=True)
        ttk.Label(shell,text='Centre de contrôle des Kristals',font=('Segoe UI',17,'bold')).pack(anchor='w')
        ttk.Label(shell,text='Une source opérationnelle : inventaire · contenu · diagnostics · Arketype · décisions locales',
                  wraplength=1160).pack(anchor='w',pady=(3,7))
        ttk.Label(shell,text='Sources : '+str(self.root),wraplength=1150).pack(anchor='w')
        bar=ttk.Frame(shell);bar.pack(fill='x',pady=(12,7))
        self.actions=[]
        for text,callback in (
            ('1 · Inventorier',self.inventory),('2 · Analyser',self.analyze),
            ('3 · Diagnostiquer (V9)',self.diagnose),('Importer ARK',self.import_ark),
            ('Importer Diag',self.import_diag),('Exporter l’état',self.export),('Actualiser',self.refresh)):
            button=ttk.Button(bar,text=text,command=callback);button.pack(side='left',padx=(0,6));self.actions.append(button)
        self.stop_button=ttk.Button(bar,text='Arrêter après le Kristal courant',command=self.stop_batch,state='disabled')
        self.stop_button.pack(side='right')
        self.count_label=ttk.Label(shell,text='Aucun état chargé')
        self.count_label.pack(anchor='w',pady=(3,4))
        ttk.Label(shell,textvariable=self.text_status,wraplength=1150).pack(anchor='w',pady=(3,8))
        line=ttk.Frame(shell);line.pack(fill='x',pady=(4,6))
        ttk.Label(line,text='Filtrer :').pack(side='left')
        search=ttk.Entry(line,textvariable=self.filter_text,width=36);search.pack(side='left',padx=(5,12))
        self.filter_text.trace_add('write',lambda *_:self._render())
        ttk.Checkbutton(line,text='Seulement les diagnostics non PASS ou périmés',
                        variable=self.show_issues,command=self._render).pack(side='left')
        area=ttk.Frame(shell);area.pack(fill='both',expand=True)
        self.table=ttk.Treeview(area,show='headings',columns=[item[0] for item in _COLUMNS],selectmode='browse')
        for key,label,width in _COLUMNS:
            self.table.heading(key,text=label)
            self.table.column(key,width=width,stretch=key=='title',minwidth=72)
        y=ttk.Scrollbar(area,orient='vertical',command=self.table.yview)
        x=ttk.Scrollbar(area,orient='horizontal',command=self.table.xview)
        self.table.configure(yscrollcommand=y.set,xscrollcommand=x.set)
        self.table.grid(row=0,column=0,sticky='nsew');y.grid(row=0,column=1,sticky='ns');x.grid(row=1,column=0,sticky='ew')
        area.rowconfigure(0,weight=1);area.columnconfigure(0,weight=1)
        self.table.tag_configure('warning',foreground='#A86815')
        self.table.tag_configure('failure',foreground='#B3231D')
        self.table.bind('<Double-1>',lambda _:self.details())
        buttons=ttk.Frame(shell);buttons.pack(fill='x',pady=(10,0))
        ttk.Button(buttons,text='Détails et historique du Kristal',command=self.details).pack(side='left')
        ttk.Button(buttons,text='Dernières exécutions',command=self.runs).pack(side='left',padx=(8,0))
        ttk.Button(buttons,text='Contrôler la base',command=self.check_index).pack(side='right')
        ttk.Label(shell,text='Les résultats V9 ne certifient pas v11. Arketype et UNESCO restent des observations/propositions.',
                  wraplength=1160).pack(anchor='w',pady=(10,0))

    def _begin(self,label,fn):
        if self.busy:return
        self.busy=True;self.active_action=label;self.cancel_request.clear();self.text_status.set(label+'…')
        self.stop_button.configure(state='normal' if label.startswith('Diagnostics') else 'disabled')
        for b in self.actions:b.configure(state='disabled')
        def worker():
            try:self.queue.put(('ok',fn()))
            except Exception as exc:self.queue.put(('error',str(exc)))
        Thread(target=worker,daemon=True).start()

    def _poll(self):
        try:
            while True:
                kind,payload=self.queue.get_nowait()
                if kind=='progress':
                    self.text_status.set(str(payload));continue
                self.busy=False;self.stop_button.configure(state='disabled')
                for b in self.actions:b.configure(state='normal')
                if kind=='error':
                    self.text_status.set('Échec : '+payload[:500]);messagebox.showerror('Opération non terminée',payload,parent=self)
                else:
                    if isinstance(payload,dict) and 'workspaces' in payload and isinstance(payload['workspaces'],list):
                        self._use_state(payload)
                    else:
                        self.text_status.set('Terminé. '+str(payload)[:450])
                        self.refresh()
        except Empty:pass
        if self.winfo_exists():self.after(120,self._poll)

    def _use_state(self,view):
        self.last_view=view
        self.rows={row['path']:row for row in view.get('workspaces',[])}
        items=self.rows.values()
        bad=sum(1 for r in items if r['diagnostic_verdict'] not in ('PASS','NOT_RUN','NOT_APPLICABLE')
                or r['diagnostic_freshness'] in ('STALE','UNVERIFIED'))
        self.count_label.configure(text=f'{len(self.rows)} Kristals  ·  {bad} diagnostics à vérifier  ·  '
                             f'{len(view.get("runs",[]))} exécutions récentes')
        self.text_status.set('État chargé depuis le registre local. Aucun diagnostic exécuté par le rafraîchissement.')
        self._render()

    def _render(self):
        existing=self.table.get_children()
        if existing:self.table.delete(*existing)
        query=self.filter_text.get().strip().casefold()
        for path,row in self.rows.items():
            if query and query not in (row['title']+' '+path).casefold():continue
            verdict=row['diagnostic_verdict'];fresh=row['diagnostic_freshness']
            bad=verdict not in ('PASS','NOT_RUN','NOT_APPLICABLE') or fresh in ('STALE','UNVERIFIED')
            if self.show_issues.get() and not bad:continue
            tag='failure' if verdict in ('FAIL','BLOCKED','EXECUTION_ERROR') else ('warning' if bad else '')
            self.table.insert('','end',iid=path,values=[str(row.get(key) if row.get(key) is not None else '—') for key,_,_ in _COLUMNS],tags=(tag,))

    def inventory(self):
        self._begin('Inventaire en cours',lambda:service.inventory(self.root,db=self.db))
    def analyze(self):
        if messagebox.askyesno('Analyser le dossier','Indexer le contenu et les classifications des Kristals ?\nAucun canon ne sera modifié.',parent=self):
            self._begin('Analyse complète en cours',lambda:service.analyze(self.root,db=self.db))
    def diagnose(self):
        if messagebox.askyesno('KristalDiag intégré','Diagnostiquer les Kristals V9 du dossier ?\nLes contrats non V9 seront NOT_APPLICABLE et non PASS.',parent=self):
            self._begin('Diagnostics V9 en cours',lambda:service.diagnose(self.root,db=self.db,
                cancel_event=self.cancel_request,on_progress=lambda n,total,name,status:
                self.queue.put(('progress',f'{n}/{total} · {name} · {status}'))))
    def stop_batch(self):
        if self.busy:
            self.cancel_request.set()
            self.text_status.set('Arrêt demandé : fin du Kristal courant, preuves déjà enregistrées conservées.')
            self.stop_button.configure(state='disabled')

    def import_ark(self):
        file=filedialog.askopenfilename(parent=self,title='Importer le rapport structurel Arketype',
                                         filetypes=[('Rapports JSON','*.json')])
        if file:self._begin('Import Arketype en cours',lambda:service.import_arketype(file,db=self.db))
    def import_diag(self):
        file=filedialog.askopenfilename(parent=self,title='Importer un diagnostic JSON historique',
                                        filetypes=[('Rapports JSON','*.json')])
        if file:self._begin('Import historique de diagnostics',
                            lambda:service.import_diagnostic_report(file,self.root,db=self.db))
    def export(self):
        file=filedialog.asksaveasfilename(parent=self,title='Exporter la vue consolidée',
                                          defaultextension='.json',filetypes=[('JSON','*.json')])
        if file:
            try:
                saved=service.export(self.root,file,db=self.db)
                self.text_status.set('Rapport : '+saved)
            except Exception as exc:messagebox.showerror('Export impossible',str(exc),parent=self)
    def refresh(self):
        self._begin('Actualisation de la vue',lambda:service.overview(self.root,db=self.db))
    def _selected(self):
        ids=self.table.selection()
        return ids[0] if ids else None
    def _text_dialog(self,title,content):
        popup=tk.Toplevel(self);popup.title(title);popup.geometry('970x620')
        frame=ttk.Frame(popup,padding=8);frame.pack(fill='both',expand=True)
        t=tk.Text(frame,wrap='none',font=('Consolas',10));t.pack(fill='both',expand=True)
        t.insert('1.0',content);t.configure(state='disabled')
        ttk.Button(frame,text='Fermer',command=popup.destroy).pack(anchor='e',pady=4)
    def details(self):
        path=self._selected()
        if not path:return
        histories={kind:repository.history(path,kind,limit=8,db=self.db)
                   for kind in ('diagnostic','analysis','arketype','inventory','verification')}
        detail={'workspace':self.rows.get(path),'history':histories,
                'decisions':repository.list_decisions(path,db=self.db)}
        self._text_dialog(Path(path).name,json.dumps(detail,indent=2,ensure_ascii=False,default=str))
    def runs(self):
        self._text_dialog('Dernières exécutions',json.dumps(repository.list_runs(db=self.db),indent=2,ensure_ascii=False))
    def check_index(self):
        try:self._text_dialog('Intégrité du registre',json.dumps(repository.integrity_check(db=self.db),indent=2))
        except Exception as exc:messagebox.showerror('Erreur SQLite',str(exc),parent=self)
