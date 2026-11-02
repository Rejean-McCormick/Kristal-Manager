"""Manager-integrated publication window. No independent launcher or implicit upload."""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
from queue import Empty, Queue
import shutil
import threading
import uuid
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .core import ManagerError
from .publication_stage import prepare_private_collection
from .manual_sync import plan_copies, apply_copies
from .private_collection_sync import plan_private_sync, apply_private_sync
from .publication_flow import (prepare_local_commit, publish_approved_commit,
    build_wiki_with_semantik_spek,create_wiki_plans,
    prepare_wiki_review,publish_wiki_reviewed)


def selectable_kristals(root: Path) -> list[tuple[str, str]]:
    """Return (actual folder name, routing slug) without renaming either.

    The folder is the human-facing name; the slug is the immutable selection
    key used by the private collection engine. Duplicate slugs are refused
    rather than silently routing two visible workspaces to the same target.
    """
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    if root.is_dir():
        from .publication_stage import SLUG
        for folder in sorted(root.iterdir(), key=lambda p: p.name.casefold()):
            if not folder.is_dir() or folder.is_symlink():
                continue
            metadata = folder / 'kristal.workspace.json'
            if not metadata.is_file() or metadata.is_symlink():
                continue
            try:
                workspace = json.loads(metadata.read_text(encoding='utf8'))
            except (ValueError, OSError):
                continue
            slug = workspace.get('slug') if isinstance(workspace, dict) else None
            if not isinstance(slug, str) or not SLUG.fullmatch(slug):
                continue
            key = slug.casefold()
            if key in seen:
                raise ManagerError(f'Duplicate routing slug in locals: {slug}')
            seen.add(key)
            entries.append((folder.name, slug))
    return sorted(entries, key=lambda item: (item[0].casefold(), item[1]))


def selected_slugs(root: Path) -> list[str]:
    """Compatibility API: callers still receive routing slugs, not labels."""
    return sorted(slug for _name, slug in selectable_kristals(root))


class PublicationPanel(tk.Toplevel):
    def __init__(self,owner):
        super().__init__(owner)
        self.owner=owner
        self.title('Kristal Manager — Transfert local des Kristals sélectionnés')
        self.geometry('1010x1000');self.minsize(770,680)
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
        self.private_checkout=tk.StringVar(value=str(collection_root/'kristal-private'))
        self._private_preview_token=None
        self._private_preview_key=None
        self._private_preview_retire_count=0
        self.allow_retire_private=tk.BooleanVar(value=False)
        self.semantik_root=tk.StringVar(value=str(collection_root/'SemantiK-Architect'))
        self.runtime_root=tk.StringVar(value=str(collection_root/'SemantiK-Architect'/'runtime'))
        self.projections=tk.StringVar(value=str(private_dir/'wiki-editorial-plans'))
        self.spek_root=tk.StringVar(value=str(collection_root/'Spek'))
        self.wiki_bundles=tk.StringVar(value=str(private_dir/'wiki-spek-inputs'))
        self.wiki_candidate=tk.StringVar()
        self.review_release=tk.StringVar()
        self.wiki_review=tk.StringVar()
        self.candidate=tk.StringVar(value=str(suggested))
        self.private_candidate=tk.StringVar(value='')
        self.manual_target=tk.StringVar(value=str(collection_root/"github-clones"))
        self.manual_mode=tk.StringVar(value="clones")
        self._copy_preview_key=None
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
        container=ttk.Frame(self);container.pack(fill='both',expand=True)
        canvas=tk.Canvas(container,highlightthickness=0)
        bar=ttk.Scrollbar(container,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        bar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        page=ttk.Frame(canvas,padding=12)
        wid=canvas.create_window((0,0),window=page,anchor='nw')
        page.bind('<Configure>',lambda _ev:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda ev:canvas.itemconfigure(wid,width=ev.width))
        ttk.Label(page,text='Transfert local — Kristals sélectionnés',font=('Segoe UI',14,'bold')).pack(anchor='w')
        ttk.Label(page,text='Sélectionner les dossiers Kristal → prévisualiser → transférer dans kristal-private. Aucun commit ni push.',
                  wraplength=840).pack(anchor='w',pady=(1,8))
        self._line(page,'Source locals',self.locals)
        self._line(page,'Kit (lecture)',self.kit,kind='file')
        self._line(page,'Clone privé local',self.private_checkout)
        self._line(page,'SemantiK Architect',self.semantik_root)
        self._line(page,'RuntimeSet SemantiK',self.runtime_root)
        self._line(page,'Plans éditoriaux privés',self.projections)
        self._line(page,'Spek (gabarits Wiki)',self.spek_root)
        selector=ttk.LabelFrame(page,text='Choisir les Kristals à transférer (Ctrl/Maj + clic; aucun choix automatique)')
        selector.pack(fill='x',pady=6)
        self._selection_slugs: list[str] = []
        self.selection_count=tk.StringVar(value='0 sélectionné')
        listarea=ttk.Frame(selector);listarea.pack(fill='x',expand=True,padx=5,pady=5)
        self.listbox=tk.Listbox(listarea,selectmode='extended',height=9,exportselection=False)
        self.listbox.pack(side='left',fill='both',expand=True)
        listscroll=ttk.Scrollbar(listarea,orient='vertical',command=self.listbox.yview)
        listscroll.pack(side='left',fill='y',padx=(2,0))
        self.listbox.configure(yscrollcommand=listscroll.set)
        self.listbox.bind('<<ListboxSelect>>',self._selection_changed)
        controls=ttk.Frame(selector);controls.pack(fill='x',padx=6,pady=(0,5))
        ttk.Label(controls,textvariable=self.selection_count).pack(side='left')
        ttk.Button(controls,text='Actualiser la liste',command=self.refresh).pack(side='right')
        self.refresh()
        private=ttk.LabelFrame(page,text='A · Copie locale sélective vers kristal-private')
        private.pack(fill='x',pady=(7,8))
        ttk.Label(private,text='Les fichiers existants sont contrôlés en interne, sans reconstruction V9. Prévisualisation puis copie locale uniquement.',
                  wraplength=850).pack(anchor='w',padx=6,pady=3)
        privbuttons=ttk.Frame(private);privbuttons.pack(anchor='w',padx=6,pady=4)
        self.preview_private=ttk.Button(privbuttons,text='1 · Prévisualiser les Kristals sélectionnés',command=self.preview_private_collection)
        self.preview_private.pack(side='left',padx=(0,5))
        self.apply_private=ttk.Button(privbuttons,text='2 · Transférer dans kristal-private (local)',command=self.apply_private_collection)
        self.apply_private.pack(side='left')
        ttk.Checkbutton(private,text='J’autorise le retrait des anciens fichiers affichés pour les Kristals sélectionnés uniquement',
                        variable=self.allow_retire_private).pack(anchor='w',padx=6,pady=2)
        ttk.Label(private,text='Le clone privé doit être propre et provisionné par Bootstrap : node, binding GitHub PRIVATE et capabilities. Vérifier séparément les ACL GitHub.',
                  wraplength=840).pack(anchor='w',padx=6,pady=(1,5))
        public=ttk.LabelFrame(page,text='B · Publication GitHub PUBLIQUE (parcours distinct, C1/C2/C3 requis)')
        public.pack(fill='x',pady=(5,8))
        self._line(public,'Dépôt public local',self.checkout)
        self._line(public,'Candidat public',self.candidate)
        # Legacy manual-copy-selected CLI remains available for independent Git repos;
        # do not expose it as the default workflow for collection repositories.
        ttk.Checkbutton(page,text='Dry Run pour la publication PUBLIQUE (parcours B seulement)',variable=self.dry).pack(anchor='w')
        ttk.Checkbutton(page,text='Retirer le stub historique Zoology incomplet du checkout (si strictement reconnu)',
                        variable=self.retire).pack(anchor='w')
        buttons=ttk.Frame(page);buttons.pack(fill='x',pady=(7,9))
        self.commit=ttk.Button(buttons,text='PUBLIC · Préparer un commit local (distinct du transfert privé)',command=self.make_commit)
        self.commit.pack(side='left',padx=(0,6))
        evidence=ttk.LabelFrame(page,text='Preuves indépendantes exigées pour le push')
        evidence.pack(fill='x',pady=5)
        self._line(evidence,'Trust C123 (.json)',self.trust,kind='file')
        self._line(evidence,'Reçus C1 (dossier)',self.c1)
        self._line(evidence,'Reçus C2 (dossier)',self.c2)
        self._line(evidence,'Policy C2 (dossier)',self.policy)
        ttk.Checkbutton(page,text='Je confirme avoir vérifié indépendamment les émetteurs et révocations C1/C2',
                        variable=self.external).pack(anchor='w',pady=(4,2))
        self.push=ttk.Button(page,text='PUBLIC · Vérifier C1/C2 et pousser le commit approuvé',command=self.publish)
        self.push.pack(anchor='w',pady=3)
        self.planwiki=ttk.Button(page,text='4 · Créer les plans privés des Kristals',command=self.create_plans)
        self.planwiki.pack(anchor='w',pady=3)
        self.wiki=ttk.Button(page,text='5 · Générer le Wiki complet (SemantiK + Spek)',command=self.export_wiki)
        self.wiki.pack(anchor='w',pady=3)
        self._line(page,'Brouillon Wiki privé',self.wiki_candidate)
        self._line(page,'Dossier Wiki revu',self.review_release)
        self._line(page,'Revue Wiki (.json)',self.wiki_review,kind='file')
        self.review_btn=ttk.Button(page,text='6 · Préparer les pages pour revue publique',command=self.prepare_review)
        self.review_btn.pack(anchor='w',pady=3)
        self.wiki_push=ttk.Button(page,text='7 · Publier le Wiki natif après revue et preuves',command=self.publish_wiki)
        self.wiki_push.pack(anchor='w',pady=3)
        ttk.Label(page,text='Le contrôle hors réseau ne constitue pas une autorisation. Sans preuves signées, le push est bloqué.',
                  wraplength=830).pack(anchor='w')
        self.journal=tk.Text(page,wrap='word',height=11,font=('Consolas',9))
        self.journal.pack(fill='both',expand=True,pady=(7,0))
        self._log('Interface du Manager prête. Aucun dépôt n’a été modifié.')

    def _log(self,line):
        self.journal.insert('end',str(line)+'\n');self.journal.see('end')

    def refresh(self):
        # Re-reading metadata never reselects a different workspace by index.
        previous=set(self._selected())
        try:
            entries=selectable_kristals(Path(self.locals.get()).expanduser())
        except (ManagerError, OSError) as exc:
            messagebox.showwarning('Liste des Kristals',str(exc),parent=self)
            return
        self.listbox.delete(0,'end')
        self._selection_slugs=[]
        for name, slug in entries:
            self._selection_slugs.append(slug)
            self.listbox.insert('end',name)
        for index, slug in enumerate(self._selection_slugs):
            if slug in previous:
                self.listbox.selection_set(index)
        self._invalidate_private_preview()
        self._update_selection_count()

    def _selected(self):
        return [self._selection_slugs[int(i)] for i in self.listbox.curselection()]

    def _update_selection_count(self):
        count=len(self.listbox.curselection())
        self.selection_count.set(f'{count} sélectionné(s) sur {len(self._selection_slugs)}')

    def _invalidate_private_preview(self):
        self._private_preview_token=None
        self._private_preview_key=None
        self._private_preview_retire_count=0
        self.private_candidate.set('')
        self.allow_retire_private.set(False)

    def _selection_changed(self, _event=None):
        self._invalidate_private_preview()
        self._update_selection_count()

    def _job(self,label,fn):
        if self._busy:return
        self._busy=True
        for b in (self.preview_private,self.apply_private,self.commit,self.push,self.planwiki,self.wiki,self.review_btn,self.wiki_push):b.configure(state='disabled')
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
                for b in (self.preview_private,self.apply_private,self.commit,self.push,self.planwiki,self.wiki,self.review_btn,self.wiki_push):b.configure(state='normal')
                if error:
                    if label=='Simulation du clone privé':
                        self.private_candidate.set('')
                        self._private_preview_token=None
                        self._private_preview_key=None
                    self._log('BLOQUÉ — '+error)
                    self.owner.log('WARN','Publication : '+error)
                else:
                    if label=='Simulation du clone privé':
                        self.private_candidate.set(result['candidate'])
                        self._private_preview_token=result['plan_token']
                        self._private_preview_retire_count=result['retire_count']
                        self._private_preview_key=(tuple(result['slugs']),result['candidate'],result['checkout'])
                    if label in ('Copie privée locale','Préparation privée'):
                        self._private_preview_token=None
                        self._private_preview_key=None
                    self._log(json.dumps(result,ensure_ascii=False,indent=2))
                    if result.get('status')=='PRIVATE_WIKI_READY':self.wiki_candidate.set(result['output'])
                    if result.get('status')=='REQUIRES_INDEPENDENT_WIKI_REVIEW' and result.get('output'):
                        self.review_release.set(result['output'])
                    self.owner.log('INFO','Publication : '+label+' : '+result.get('status',''))
                    if result.get('push_performed'):
                        messagebox.showinfo('GitHub confirmé','Commit en ligne : '+result['revision']+'\n'+result['catalog_url'],parent=self)
        except Empty:pass
        if self.winfo_exists():self.after(130,self._poll)

    def _manual_args(self):
        slugs=self._selected()
        if not slugs:
            raise ManagerError('Sélectionne au moins un Kristal dans la liste.')
        return dict(locals_root=Path(self.locals.get()),destination_root=Path(self.manual_target.get()),
                    slugs=slugs,mode=self.manual_mode.get())

    def preview_manual_copies(self):
        try:args=self._manual_args()
        except ManagerError as exc:
            messagebox.showwarning('Sélection',str(exc),parent=self);return
        self._copy_preview_key=None
        def job():
            plan=plan_copies(**args)
            return {k:v for k,v in plan.items() if k!='projects'} | {
                'projects':[{k:pr[k] for k in ('slug','source','target','files','to_copy','bytes')}
                            for pr in plan['projects']]}
        self._job('Simulation des copies locales',job)

    def apply_manual_copies(self):
        try:args=self._manual_args()
        except ManagerError as exc:
            messagebox.showwarning('Sélection',str(exc),parent=self);return
        resolved=str(args['destination_root'].expanduser().resolve())
        if self._copy_preview_key != (tuple(args['slugs']),resolved,args['mode']):
            messagebox.showwarning('Simulation requise','Prévisualise d’abord exactement cette sélection et ce dossier.',parent=self)
            return
        if not messagebox.askyesno('Copies locales UNIQUEMENT',
                f'Copier {len(args["slugs"])} Kristals vers :\n{resolved}\n\n'
                'AUCUN git add, commit ou push. Les données doivent être revues avant diffusion publique. Confirmer ?',parent=self):
            return
        self._job('Copies locales',lambda:apply_copies(**args))

    def preview_private_collection(self):
        """Use ALREADY PREPARED read surfaces; never rebuild or modify source Kristals.

        A temporary candidate is an internal manifest/fingerprint package, not a
        user-facing publication step. Nothing is written to the Git checkout.
        """
        slugs=self._selected()
        if not slugs:
            messagebox.showwarning('Sélection','Coche au moins un Kristal.',parent=self);return
        locals_root=Path(self.locals.get()).expanduser()
        kit=Path(self.kit.get()).expanduser()
        checkout=Path(self.private_checkout.get()).expanduser()
        self._private_preview_token=None
        self._private_preview_key=None
        self.private_candidate.set('')
        def job():
            temp_root=Path(os.environ.get('LOCALAPPDATA') or str(Path.home()))/'Kristal'/'private-candidates'
            temp_root.mkdir(parents=True,exist_ok=True)
            output=temp_root/('candidate-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:10])
            # Verification/packaging ONLY: build_on_copy=False, never build-v9.
            prepared=prepare_private_collection(locals_root=locals_root,kit_script=kit,
                       output=output,slugs=slugs,write_private=True,build_on_copy=False)
            try:
                plan=plan_private_sync(candidate=output,checkout=checkout,slugs=slugs)
            except Exception:
                # Candidate is a newly created internal scratch directory, not Git.
                if output.is_dir() and not output.is_symlink() and output.parent==temp_root:
                    shutil.rmtree(output)
                raise
            return {k:v for k,v in plan.items() if k!='_next_index'} | {
                'fichiers_controles':prepared.get('files_count',0),
                'reconstruction_V9':False,
                'transfert_effectue':False,
            }
        self._job('Simulation du clone privé',job)

    def apply_private_collection(self):
        slugs=self._selected()
        candidate=Path(self.private_candidate.get()).expanduser()
        checkout=Path(self.private_checkout.get()).expanduser()
        try:
            key=(tuple(sorted(slugs)),str(candidate.resolve(strict=True)),str(checkout.resolve(strict=True)))
        except OSError:
            messagebox.showwarning('Chemin','Le candidat et le dépôt privé doivent exister.',parent=self);return
        if not slugs or self._private_preview_token is None or key!=self._private_preview_key:
            messagebox.showwarning('Prévisualisation requise',
                 'Prévisualise exactement la sélection et le même clone privé avant de copier.',parent=self);return
        if self._private_preview_retire_count and not self.allow_retire_private.get():
            messagebox.showwarning('Retrait contrôlé',
                f'{self._private_preview_retire_count} fichiers obsolètes sont listés dans la simulation. '
                'Coche l’autorisation de retrait explicite pour cette sélection.',parent=self);return
        if not messagebox.askyesno('Copie vers kristal-private',
             f'Copier uniquement {len(slugs)} Kristals dans le clone PRIVÉ :\n{checkout}\n\n'
             'Seuls les fichiers affichés des Kristals cochés seront mis à jour. '
             'Les autres Kristals restent inchangés. Aucun commit ni push. Continuer ?',parent=self):return
        token=self._private_preview_token
        allow_retire=self.allow_retire_private.get()
        self._job('Copie privée locale',lambda:apply_private_sync(candidate=candidate,checkout=checkout,
                  slugs=slugs,expected_token=token,allow_retire=allow_retire))

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

    def create_plans(self):
        checkout=Path(self.checkout.get())
        base=Path(self.projections.get()).expanduser()
        write=not self.dry.get()
        def job():
            if write:base.parent.mkdir(parents=True,exist_ok=True)
            return create_wiki_plans(checkout=checkout,locals_root=Path(self.locals.get()),
                      output=base,language='fr',write=write)
        self._job('Plans éditoriaux Wiki privés',job)

    def export_wiki(self):
        checkout=Path(self.checkout.get())
        parent=Path(self.candidate.get()).expanduser().parent
        dest=parent / ('wiki-complet-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
        write=not self.dry.get()
        def job():
            if write:dest.parent.mkdir(parents=True,exist_ok=True)
            return build_wiki_with_semantik_spek(checkout=checkout,
                locals_root=Path(self.locals.get()),plans=Path(self.projections.get()),
                semantik_root=Path(self.semantik_root.get()),runtime_root=Path(self.runtime_root.get()),
                spek_root=Path(self.spek_root.get()),output=dest,language='fr',write=write)
        self._job('Génération Wiki SemantiK + Spek',job)

    def prepare_review(self):
        private=Path(self.wiki_candidate.get())
        parent=Path(self.candidate.get()).expanduser().parent
        dest=parent/('wiki-review-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
        write=not self.dry.get()
        def job():
            if write:dest.parent.mkdir(parents=True,exist_ok=True)
            return prepare_wiki_review(checkout=Path(self.checkout.get()),private=private,
                      output=dest,write=write)
        self._job('Revue éditoriale avant publication Wiki',job)

    def publish_wiki(self):
        if not self.external.get():
            messagebox.showwarning('Revue obligatoire',
                'Valider les signatures C1/C2 et la revue indépendante des pages Wiki.',parent=self);return
        if not all(x.get().strip() for x in (self.trust,self.c1,self.c2,self.policy,self.review_release,self.wiki_review)):
            messagebox.showwarning('Preuves requises',
                'Signatures C1/C2, dossier Wiki préparé et revue Wiki approuvée requis.',parent=self);return
        write=not self.dry.get()
        if write and not messagebox.askyesno('Publication du Wiki natif',
                'Tu vas publier les pages revues sur Internet dans kristal-public.wiki.git. Confirmer ?',parent=self):return
        self._job('Publication du Wiki GitHub natif',lambda:publish_wiki_reviewed(
             checkout=Path(self.checkout.get()),release=Path(self.review_release.get()),
             review=Path(self.wiki_review.get()),trust=Path(self.trust.get()),
             c1_dir=Path(self.c1.get()),c2_dir=Path(self.c2.get()),
             policy_dir=Path(self.policy.get()),external_approval_confirmed=True,push=write))
