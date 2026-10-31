"""Read-only GUI inventory of full Kristal folder weights for manual bundle sharing."""
from __future__ import annotations

import json
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .bundle_inventory import scan_inventory, format_brief


def mib(num: int) -> str:
    return f'{num / (1024 * 1024):,.2f}'


class BundleInventoryPanel(tk.Toplevel):
    def __init__(self, parent, source):
        super().__init__(parent)
        self.title('Manager — poids réels des Kristals pour bundles complets')
        self.geometry('1080x700')
        self.minsize(780,520)
        self.source=Path(source)
        self.report=None
        self.working=False
        self.status=tk.StringVar(value='Pas encore mesuré. Lecture seule; aucun ZIP ni fichier source modifié.')
        frame=ttk.Frame(self,padding=13);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Inventaire de tailles — dossiers Kristals complets',
                  font=('Segoe UI',14,'bold')).pack(anchor='w')
        ttk.Label(frame,text='Mesure tous les fichiers (y compris .git, médias, versions et dérivés), et lit le tag ARK déclaré s’il existe. Ne compresse rien.',
                  wraplength=1020).pack(anchor='w',pady=(2,9))
        actions=ttk.Frame(frame);actions.pack(fill='x')
        self.scan_btn=ttk.Button(actions,text='Mesurer tous les Kristals',command=self.scan)
        self.scan_btn.pack(side='left')
        self.export_btn=ttk.Button(actions,text='Exporter inventaire JSON…',command=self.export)
        self.export_btn.pack(side='left',padx=(8,0))
        self.copy_btn=ttk.Button(actions,text='Copier la liste pour ChatGPT',command=self.copy)
        self.copy_btn.pack(side='left',padx=(8,0))
        ttk.Button(actions,text='Fermer',command=self.destroy).pack(side='right')
        self.export_btn.configure(state='disabled');self.copy_btn.configure(state='disabled')
        self.progress=ttk.Progressbar(frame,mode='indeterminate')
        self.progress.pack(fill='x',pady=(10,4))
        ttk.Label(frame,textvariable=self.status,wraplength=1030).pack(anchor='w',pady=(0,7))
        area=ttk.Frame(frame);area.pack(fill='both',expand=True)
        columns=('project','mb','canon','files','ark','status')
        self.table=ttk.Treeview(area,columns=columns,show='headings',height=16)
        for key,title,width in [('project','Kristal',350),('mb','Total Mo (brut)',125),
           ('canon','Canon Mo',105),('files','Fichiers',105),('ark','Tag ARK déclaré',135),
           ('status','Mesure',130)]:
            self.table.heading(key,text=title)
            self.table.column(key,width=width,stretch=key=='project',anchor='e' if key in ('mb','canon','files') else 'w')
        sy=ttk.Scrollbar(area,orient='vertical',command=self.table.yview)
        self.table.configure(yscrollcommand=sy.set)
        self.table.pack(side='left',fill='both',expand=True)
        sy.pack(side='right',fill='y')
        self.table.bind('<<TreeviewSelect>>',self.show_detail)
        self.details=tk.Text(frame,height=10,wrap='word',font=('Consolas',9))
        self.details.pack(fill='both',expand=True,pady=(7,0))
        self.details.configure(state='disabled')

    def scan(self):
        if self.working:return
        self.working=True;self.scan_btn.configure(state='disabled')
        self.export_btn.configure(state='disabled');self.copy_btn.configure(state='disabled')
        self.progress.start(12)
        self.status.set('Mesure des tailles sur disque en cours (fichiers non ouverts)…')
        def work():
            try:
                output=scan_inventory(self.source)
                self._notify(lambda:self._finish(output,None))
            except Exception as exc:
                self._notify(lambda e=str(exc):self._finish(None,e))
        threading.Thread(target=work,daemon=True).start()

    def _notify(self,callback):
        try:self.after(0,callback)
        except (tk.TclError,RuntimeError):pass

    def _finish(self,report,error):
        self.working=False;self.progress.stop();self.scan_btn.configure(state='normal')
        if error:
            self.status.set('Scan interrompu : '+error)
            messagebox.showerror('Inventaire tailles',error,parent=self)
            return
        self.report=report
        self.table.delete(*self.table.get_children())
        for i,r in enumerate(report['projects']):
            self.table.insert('','end',iid=str(i),values=(r['project'],mib(r['bytes_total']),
              mib(r['bytes_canon']),r['file_count'],
              (r.get('declaration') or {}).get('primary_archetype') or '—',
              'Complet' if r['measurement_complete'] else 'À vérifier'))
        c=report['counts']
        self.status.set(f"{c['projects']} Kristals · {mib(c['total_bytes'])} Mio bruts · "
            f"{c['total_files']} fichiers · {c['incomplete_projects']} mesure(s) incomplète(s). "
            'Les tailles ZIP dépendent de la compression.')
        self.export_btn.configure(state='normal');self.copy_btn.configure(state='normal')
        if report['projects']:
            self.table.selection_set('0');self.show_detail()

    def show_detail(self,event=None):
        if not self.report:return
        ids=self.table.selection()
        if not ids:return
        row=self.report['projects'][int(ids[0])]
        payload=json.dumps({'project':row['project'],'path':row['path'],
          'bytes_total':row['bytes_total'], 'file_count':row['file_count'],
          'bytes_canon':row['bytes_canon'],'top_level_bytes':row['top_level_bytes'],
          'declaration':row['declaration'],'largest_files':row['largest_files'],
          'measurement_complete':row['measurement_complete'],'issues':row['issues']},
           ensure_ascii=False,indent=2)
        self.details.configure(state='normal');self.details.delete('1.0','end')
        self.details.insert('1.0',payload);self.details.configure(state='disabled')

    def copy(self):
        if not self.report:return
        try:
            output=format_brief(self.report)
            self.clipboard_clear();self.clipboard_append(output);self.update_idletasks()
            self.status.set(f'Inventaire copié ({len(self.report["projects"])} Kristals). Colle dans ChatGPT.')
        except tk.TclError as exc:
            messagebox.showerror('Copie impossible',str(exc),parent=self)

    def export(self):
        if not self.report:return
        path=filedialog.asksaveasfilename(parent=self,title='Exporter tailles des Kristals',
            initialfile='RAPPORT_TAILLES_KRISTALS.json',defaultextension='.json',
            filetypes=[('Fichier JSON','*.json')])
        if not path:return
        target=Path(path).expanduser().resolve()
        source=self.source.expanduser().resolve()
        # No reports inside the source tree or its Kristals; avoid contamination.
        if target == source or target.is_relative_to(source):
            messagebox.showerror('Sortie refusée',
                'Enregistre le rapport hors du dossier locals/Kristals.',parent=self)
            return
        try:
            target.write_text(json.dumps(self.report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        except OSError as exc:
            messagebox.showerror('Export impossible',str(exc),parent=self);return
        self.status.set('Inventaire exporté : '+str(target))
