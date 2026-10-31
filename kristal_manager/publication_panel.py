"""Manager-integrated publication window. No independent launcher or implicit upload."""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
from queue import Empty, Queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .core import ManagerError
from .publication_stage import prepare_private_collection
from .publication_flow import prepare_local_commit, publish_approved_commit, export_wiki_candidate


def selected_slugs(root: Path) -> list[str]:
    slugs=[]
    if root.is_dir():
        for p in sorted(root.iterdir(),key=lambda p:p.name.lower()):
            if not p.is_dir() or p.is_symlink():continue
            w=p/'kristal.workspace.json'
            if not w.is_file():continue
            try:
                slug=json.loads(w.read_text(encoding='utf8')).get('slug')
            except (ValueError,OSError):continue
            from .publication_stage import SLUG
            if isinstance(slug,str) and SLUG.fullmatch(slug):slugs.append(slug)
    return sorted(set(slugs))


class PublicationPanel(tk.Toplevel):
    def __init__(self,owner):
        super().__init__(owner)
        self.owner=owner
        self.title('Kristal Manager — Publier sur GitHub')
        self.geometry('890x810');self.minsize(730,590)
        self.transient(owner)
        self._jobs=Queue();self._busy=False
        locals_root=Path(owner.path_var.get()).expanduser()
        if not locals_root.is_dir():locals_root=Path(r'C:\mycode\Kristal\locals')
        collection_root=locals_root.parent
        # New, private, out-of-repo candidate. Parent folder is created by the user operation.
        private_dir=Path(os.environ.get('LOCALAPPDATA') or str(Path.home()))/'Kristal'/'private-candidates'
        suggested=private_dir/('candidate-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
        self.locals=tk.StringVar(value=str(locals_root))
        self.kit=tk.StringVar(value=str(collection_root/'Kristal-Authoring-Kit'/'tools'/'kristal.py'))
        self.checkout=tk.StringVar(value=str(collection_root/'kristal-public'))
        self.candidate=tk.StringVar(value=str(suggested))
        self.trust=tk.StringVar()
        self.c1=tk.StringVar()
        self.c2=tk.StringVar()
        self.policy=tk.StringVar()
        self.dry=tk.BooleanVar(value=True)
        self.retire=tk.BooleanVar(value=False)
        self.external=tk.BooleanVar(value=False)
        self._render()
        self.after(130,self._poll)
        self.grab_set()

    def _line(self,parent,label,variable,*,kind='dir'):
        row=ttk.Frame(parent);row.pack(fill='x',pady=2)
        ttk.Label(row,text=label,width=19).pack(side='left')
        ttk.Entry(row,textvariable=variable).pack(side='left',fill='x',expand=True)
        def browse():
            if kind=='file':p=filedialog.askopenfilename(parent=self)
            else:p=filedialog.askdirectory(parent=self)
            if p:variable.set(p)
        ttk.Button(row,text='…',width=3,command=browse).pack(side='left',padx=(3,0))

    def _render(self):
        page=ttk.Frame(self,padding=12);page.pack(fill='both',expand=True)
        ttk.Label(page,text='Publication GitHub depuis les sources locales',font=('Segoe UI',14,'bold')).pack(anchor='w')
        ttk.Label(page,text='1. Préparer privé  →  2. Créer le commit local  →  3. Signatures C1/C2  →  4. Push',
                  wraplength=840).pack(anchor='w',pady=(1,8))
        self._line(page,'Source locals',self.locals)
        self._line(page,'Kit existant',self.kit,kind='file')
        self._line(page,'Candidat privé',self.candidate)
        self._line(page,'Dépôt public local',self.checkout)
        selector=ttk.LabelFrame(page,text='Kristals à publier (sélection multiple explicite)')
        selector.pack(fill='x',pady=6)
        self.listbox=tk.Listbox(selector,selectmode='extended',height=5,exportselection=False)
        self.listbox.pack(side='left',fill='x',expand=True,padx=5,pady=5)
        ttk.Button(selector,text='Rafraîchir',command=self.refresh).pack(side='right',padx=5)
        self.refresh()
        ttk.Checkbutton(page,text='Dry Run — aucune écriture ni push (activé par défaut)',variable=self.dry).pack(anchor='w')
        ttk.Checkbutton(page,text='Retirer le stub historique Zoology incomplet du checkout (si strictement reconnu)',
                        variable=self.retire).pack(anchor='w')
        buttons=ttk.Frame(page);buttons.pack(fill='x',pady=(7,9))
        self.stage=ttk.Button(buttons,text='1 · Préparer la collection privée',command=self.prepare)
        self.stage.pack(side='left',padx=(0,6))
        self.commit=ttk.Button(buttons,text='2 · Préparer le commit local',command=self.make_commit)
        self.commit.pack(side='left',padx=(0,6))
        evidence=ttk.LabelFrame(page,text='Preuves indépendantes exigées pour le push')
        evidence.pack(fill='x',pady=5)
        self._line(evidence,'Trust C123 (.json)',self.trust,kind='file')
        self._line(evidence,'Reçus C1 (dossier)',self.c1)
        self._line(evidence,'Reçus C2 (dossier)',self.c2)
        self._line(evidence,'Policy C2 (dossier)',self.policy)
        ttk.Checkbutton(page,text='Je confirme avoir vérifié indépendamment les émetteurs et révocations C1/C2',
                        variable=self.external).pack(anchor='w',pady=(4,2))
        self.push=ttk.Button(page,text='3 · Vérifier les preuves et pousser le commit EXACT',command=self.publish)
        self.push.pack(anchor='w',pady=3)
        self.wiki=ttk.Button(page,text='4 · Générer le brouillon Wiki après push',command=self.export_wiki)
        self.wiki.pack(anchor='w',pady=3)
        ttk.Label(page,text='Le contrôle hors réseau ne constitue pas une autorisation. Sans preuves signées, le push est bloqué.',
                  wraplength=830).pack(anchor='w')
        self.journal=tk.Text(page,wrap='word',height=11,font=('Consolas',9))
        self.journal.pack(fill='both',expand=True,pady=(7,0))
        self._log('Interface du Manager prête. Aucun dépôt n’a été modifié.')

    def _log(self,line):
        self.journal.insert('end',str(line)+'\n');self.journal.see('end')

    def refresh(self):
        self.listbox.delete(0,'end')
        for slug in selected_slugs(Path(self.locals.get()).expanduser()):self.listbox.insert('end',slug)

    def _selected(self):
        return [self.listbox.get(i) for i in self.listbox.curselection()]

    def _job(self,label,fn):
        if self._busy:return
        self._busy=True
        for b in (self.stage,self.commit,self.push,self.wiki):b.configure(state='disabled')
        self._log('DÉBUT — '+label)
        def run():
            try:self._jobs.put((label,fn(),None))
            except Exception as exc:self._jobs.put((label,None,str(exc)))
        threading.Thread(target=run,daemon=True).start()

    def _poll(self):
        try:
            while True:
                label,result,error=self._jobs.get_nowait()
                self._busy=False
                for b in (self.stage,self.commit,self.push,self.wiki):b.configure(state='normal')
                if error:
                    self._log('BLOQUÉ — '+error)
                    self.owner.log('WARN','Publication : '+error)
                else:
                    self._log(json.dumps(result,ensure_ascii=False,indent=2))
                    self.owner.log('INFO','Publication : '+label+' : '+result.get('status',''))
                    if result.get('push_performed'):
                        messagebox.showinfo('GitHub confirmé','Commit en ligne : '+result['revision']+'\n'+result['catalog_url'],parent=self)
        except Empty:pass
        if self.winfo_exists():self.after(130,self._poll)

    def prepare(self):
        slugs=self._selected()
        if not slugs:
            messagebox.showwarning('Sélection','Sélectionne explicitement un ou plusieurs Kristals.',parent=self);return
        out=Path(self.candidate.get()).expanduser()
        write=not self.dry.get()
        def job():
            if write:out.parent.mkdir(parents=True,exist_ok=True)
            return prepare_private_collection(locals_root=Path(self.locals.get()),kit_script=Path(self.kit.get()),
                  output=out,slugs=slugs,write_private=write,build_on_copy=True)
        self._job('Préparation privée',job)

    def make_commit(self):
        if not self.dry.get() and not messagebox.askyesno('Confirmation',
                'Créer un commit LOCAL dans kristal-public ? AUCUN push ne sera effectué.',parent=self):return
        c=Path(self.candidate.get());r=Path(self.checkout.get());retire=self.retire.get();write=not self.dry.get()
        self._job('Commit Git local',lambda:prepare_local_commit(candidate=c,
                  checkout=r,retire_zoology_stub=retire,write=write))

    def publish(self):
        if not self.external.get():
            messagebox.showwarning('Preuves indépendantes','Confirmation des autorisations C1/C2 requise.',parent=self);return
        if not all(x.get().strip() for x in (self.trust,self.c1,self.c2,self.policy)):
            messagebox.showwarning('Preuves manquantes','Renseigne les quatre chemins de preuves.',parent=self);return
        if not self.dry.get() and not messagebox.askyesno('Publier sur Internet',
                    'Diffusion PUBLIQUE irréversible des fichiers autorisés. Pousser maintenant vers GitHub ?',parent=self):return
        values=(Path(self.checkout.get()),Path(self.trust.get()),Path(self.c1.get()),Path(self.c2.get()),Path(self.policy.get()))
        write=not self.dry.get()
        self._job('Vérification C1/C2 et push',lambda:publish_approved_commit(checkout=values[0],
                  trust=values[1],c1_dir=values[2],c2_dir=values[3],
                  policy_dir=values[4],external_approval_confirmed=True,push=write))

    def export_wiki(self):
        checkout=Path(self.checkout.get())
        parent=Path(self.candidate.get()).expanduser().parent
        dest=parent / ('wiki-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
        write=not self.dry.get()
        self._job('Brouillon Wiki',lambda:export_wiki_candidate(
                  checkout=checkout,output=dest,write=write))
