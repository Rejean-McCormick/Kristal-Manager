"""Local-only desktop recovery interface for Kristal Manager.

The original GUI package is absent from the supplied snapshot and GitHub main.
This operator surface supports scanning/inspection/export, not remote writes.
"""
from __future__ import annotations
from pathlib import Path
from queue import Queue,Empty
from threading import Thread
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from .core import scan_roots
from .inventory import inventory,save_private_inventory,konstellation_preview

BG='#f7faf9'; TEAL='#1e6864'; TEXT='#173230'

class ManagerWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Kristal Manager — Local Inventory')
        self.geometry('1100x720')
        self.minsize(780,550)
        self.configure(background=BG)
        self.events=Queue();self.rows=[];self.roots=[];self.busy=False
        s=ttk.Style(self)
        if 'clam' in s.theme_names():s.theme_use('clam')
        s.configure('TFrame',background=BG)
        s.configure('TLabel',background=BG,foreground=TEXT)
        s.configure('Title.TLabel',font=('Segoe UI',19,'bold'),foreground=TEAL)
        s.configure('Sub.TLabel',foreground='#55716c')
        s.configure('Treeview',rowheight=28)
        s.configure('Treeview.Heading',font=('Segoe UI',10,'bold'))
        head=ttk.Frame(self,padding=(22,16));head.pack(fill='x')
        ttk.Label(head,text='KRISTAL MANAGER',style='Title.TLabel').pack(anchor='w')
        ttk.Label(head,text='Local inventory · State diagnostics · Konstellation export',style='Sub.TLabel').pack(anchor='w')
        controls=ttk.Frame(self,padding=(22,4));controls.pack(fill='x')
        self.path_var=tk.StringVar(value=str((Path.home()/'mycode/Kristal/locals').resolve()))
        ttk.Entry(controls,textvariable=self.path_var,width=82).pack(side='left',fill='x',expand=True)
        ttk.Button(controls,text='Browse…',command=self.select_root).pack(side='left',padx=5)
        self.scan_button=ttk.Button(controls,text='Scan local Kristals',command=self.start_scan)
        self.scan_button.pack(side='left')
        self.filter_var=tk.StringVar()
        filterbar=ttk.Frame(self,padding=(22,12));filterbar.pack(fill='x')
        ttk.Label(filterbar,text='Filter').pack(side='left',padx=(0,8))
        ttk.Entry(filterbar,textvariable=self.filter_var).pack(side='left',fill='x',expand=True)
        ttk.Button(filterbar,text='Export local inventory JSON',command=self.export).pack(side='left',padx=(12,0))
        ttk.Button(filterbar,text='Export My Kristals (opt-in)',command=self.export_konstellation).pack(side='left',padx=(8,0))
        self.filter_var.trace_add('write',lambda *_:self.refresh())
        grid=ttk.Frame(self,padding=(22,0,22,10));grid.pack(fill='both',expand=True)
        cols=('title','readiness','profile','source','state_ref','artifacts')
        self.tree=ttk.Treeview(grid,columns=cols,show='headings',selectmode='browse',height=11)
        for col,label,width in [('title','Kristal',200),('readiness','Local state',130),('profile','Profile',100),
                                ('source','State source',100),('state_ref','State identity',250),('artifacts','Artifacts',70)]:
            self.tree.heading(col,text=label);self.tree.column(col,width=width,stretch=col in ('title','state_ref'))
        scroll=ttk.Scrollbar(grid,orient='vertical',command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
        self.tree.bind('<<TreeviewSelect>>',self.show_details)
        ttk.Label(self,text='Selected workspace · inspection metadata only',padding=(22,1),style='Sub.TLabel').pack(anchor='w')
        details=ttk.Frame(self,padding=(22,2,22,3));details.pack(fill='both')
        self.details=tk.Text(details,height=10,wrap='word',font=('Consolas',10),bg='white',fg=TEXT)
        self.details.pack(fill='both');self.details.configure(state='disabled')
        self.status_var=tk.StringVar(value='Read-only · no GitHub writes, publication or activation')
        ttk.Label(self,textvariable=self.status_var,padding=(22,7),style='Sub.TLabel').pack(fill='x')
        self.after(100,self.poll)

    def select_root(self):
        root=filedialog.askdirectory(title='Choose a directory containing local Kristals')
        if root:self.path_var.set(root)
    def start_scan(self):
        if self.busy:return
        folder=Path(self.path_var.get()).expanduser()
        if not folder.is_dir():
            messagebox.showerror('Invalid root','Select an existing local directory.');return
        self.busy=True;self.scan_button.configure(state='disabled')
        self.status_var.set('Scanning local workspaces…')
        def work():
            try:self.events.put(('result',scan_roots([folder]),folder))
            except Exception as exc:self.events.put(('error',str(exc),folder))
        Thread(target=work,daemon=True).start()
    def poll(self):
        try:
            while True:
                kind,payload,folder=self.events.get_nowait()
                self.busy=False;self.scan_button.configure(state='normal')
                if kind=='error':
                    messagebox.showerror('Scan failed',payload)
                    self.status_var.set('Local scan failed; no files changed')
                else:
                    self.rows=[x for x in payload if not x.get('hidden_auxiliary')]
                    self.roots=[folder];self.refresh()
                    self.status_var.set(f'{len(self.rows)} local workspaces found · structural inventory only · no GitHub writes')
        except Empty:pass
        self.after(100,self.poll)
    def refresh(self):
        old=self.tree.selection();selected=old[0] if old else None
        for child in self.tree.get_children():self.tree.delete(child)
        query=self.filter_var.get().strip().casefold()
        for i,row in enumerate(self.rows):
            if query and query not in ' '.join(str(row.get(k,'')) for k in ('title','slug','state_ref','profile','readiness','native_kind')).casefold():
                continue
            self.tree.insert('', 'end',iid=str(i),values=(row['title'],row['readiness'],row.get('profile') or '—',
                   row.get('state_source') or '—',row.get('state_ref') or '—',row['registered_artifacts']))
        if selected in self.tree.get_children():self.tree.selection_set(selected)
    def show_details(self,event=None):
        selected=self.tree.selection()
        if not selected:return
        row=self.rows[int(selected[0])]
        show={k:row.get(k) for k in ('title','slug','path','state_ref','workspace_format','native_kind',
                                    'readiness','state_commitment','state_blob_digest','state_conflict_reasons',
                                    'portable_ai_enabled','ai_entrypoint_present','hosted_network_baseline','discovery')}
        self.details.configure(state='normal');self.details.delete('1.0','end')
        self.details.insert('end',json.dumps(show,ensure_ascii=False,indent=2))
        self.details.configure(state='disabled')
    def export_konstellation(self):
        if self.busy or not self.roots:
            messagebox.showinfo('Scan first','Scan local Kristals before exporting.');return
        principal=simpledialog.askstring('Explicit local access grant',
            'Enter the local Konstellation principal ID you are authorized to expose ALL listed Kristals to.\nNo automatic permission check is performed.\nCancel to deny all.',parent=self)
        if not principal:return
        if not messagebox.askyesno('Private preview only',
            'This explicitly authorizes the named local preview principal to see ALL inventoried Kristal titles.\nContinue?'):
            return
        file=filedialog.asksaveasfilename(title='Private KNAV preview file',defaultextension='.json',
                     initialfile='private-konstellation-preview.json',filetypes=[('JSON','*.json')])
        if not file:return
        dest=Path(file)
        allow=dest.exists() and messagebox.askyesno('Confirm replacement',f'Replace existing local file?\n{dest}')
        if dest.exists() and not allow:return
        try:
            result=konstellation_preview(self.roots,allowed_principals=[principal])
            save_private_inventory(result,dest,overwrite=allow)
            self.status_var.set(f'Private KNAV preview: {len(result["entries"])} entries, not published')
        except Exception as exc:messagebox.showerror('Preview failed',str(exc))

    def export(self):
        if self.busy or not self.roots:
            messagebox.showinfo('Scan first','Scan a local root before exporting.');return
        file=filedialog.asksaveasfilename(title='Private inventory export',defaultextension='.json',
                     filetypes=[('JSON','*.json')],initialfile='kristal-local-inventory.json')
        if not file:return
        destination=Path(file)
        allow=destination.exists() and messagebox.askyesno('Confirm replacement',f'Replace existing local file?\n{destination}')
        if destination.exists() and not allow:return
        try:
            # Fresh scan, without private local paths by default.
            result=inventory(self.roots)
            save_private_inventory(result,destination,overwrite=allow)
            self.status_var.set(f'Exported {result["record_count"]} local-only records to {destination.name}')
        except Exception as exc:messagebox.showerror('Export failed',str(exc))

def main():
    app=ManagerWindow();app.mainloop()

if __name__=='__main__':main()
