"""Manager-integrated publication window. No independent launcher or implicit upload."""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
from queue import Empty, Queue
import shutil
import threading
import time
import uuid
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .core import ManagerError
from .publication_stage import prepare_private_collection
from .public_local_sync import plan_local_public, apply_local_public, prepare_and_copy_public_local
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
        self.title('Kristal Manager — Préparation locale des Kristals')
        self.geometry('920x780');self.minsize(730,550)
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
        self._public_preview_token=None
        self._public_preview_key=None
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
        # Legacy destructive retirement is not offered in the everyday UI.
        # If a pre-C3 Zoology stub exists, the user selects Zoology to replace it.
        self.retire=tk.BooleanVar(value=False)
        self.public_status=tk.StringVar(value='Sélectionne un ou plusieurs Kristals.')
        self.public_details=tk.StringVar(value='Aucune modification du dossier public pour cette session.')
        self.progress_phase=tk.StringVar(value='Aucune préparation en cours.')
        self.progress_elapsed=tk.StringVar(value='')
        self._progress_started_at=None
        self._last_progress_second=-1
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
        """Daily task first; diagnostics and private transfer remain accessible."""
        container=ttk.Frame(self)
        container.pack(fill='both',expand=True)
        canvas=tk.Canvas(container,highlightthickness=0)
        bar=ttk.Scrollbar(container,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        bar.pack(side='right',fill='y')
        canvas.pack(side='left',fill='both',expand=True)
        page=ttk.Frame(canvas,padding=14)
        wid=canvas.create_window((0,0),window=page,anchor='nw')
        page.bind('<Configure>',lambda _ev:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda ev:canvas.itemconfigure(wid,width=ev.width))

        ttk.Label(page,text='Mettre des Kristals dans le dossier public',
                  font=('Segoe UI',15,'bold')).pack(anchor='w')
        ttk.Label(page,text='Choisis les Kristals, puis prépare le dossier local. '
                  'La synchronisation GitHub reste entièrement séparée.',
                  wraplength=800).pack(anchor='w',pady=(3,12))

        selector=ttk.LabelFrame(page,text='1. Kristals à préparer (Ctrl ou Maj pour plusieurs)')
        selector.pack(fill='x',pady=(0,10))
        self._selection_slugs: list[str] = []
        self.selection_count=tk.StringVar(value='0 sélectionné')
        listarea=ttk.Frame(selector)
        listarea.pack(fill='x',padx=8,pady=(8,4))
        self.listbox=tk.Listbox(listarea,selectmode='extended',height=12,
                                exportselection=False)
        self.listbox.pack(side='left',fill='both',expand=True)
        listscroll=ttk.Scrollbar(listarea,orient='vertical',command=self.listbox.yview)
        listscroll.pack(side='left',fill='y',padx=(4,0))
        self.listbox.configure(yscrollcommand=listscroll.set)
        self.listbox.bind('<<ListboxSelect>>',self._selection_changed)
        controls=ttk.Frame(selector)
        controls.pack(fill='x',padx=8,pady=(0,8))
        ttk.Label(controls,textvariable=self.selection_count).pack(side='left')
        self.refresh_button=ttk.Button(controls,text='Actualiser la liste',command=self.refresh)
        self.refresh_button.pack(side='right')
        self.refresh()

        public=ttk.LabelFrame(page,text='2. Dossier public local')
        public.pack(fill='x',pady=(0,8))
        destination=ttk.Frame(public)
        destination.pack(fill='x',padx=8,pady=(9,6))
        ttk.Label(destination,text='Destination : ').pack(side='left')
        ttk.Label(destination,textvariable=self.checkout,wraplength=650).pack(side='left',fill='x',expand=True)
        self.stage=ttk.Button(public,text='Mettre dans le dossier public',
                              command=self.prepare_public_direct)
        self.stage.pack(anchor='w',padx=8,pady=(5,8))
        ttk.Label(public,text='Préparation locale uniquement — aucun commit, push ou upload GitHub.',
                  wraplength=800).pack(anchor='w',padx=8,pady=(0,9))

        status=ttk.LabelFrame(page,text='Résultat')
        status.pack(fill='x',pady=(0,10))
        ttk.Label(status,textvariable=self.public_status,
                  font=('Segoe UI',10,'bold'),wraplength=790).pack(anchor='w',padx=8,pady=(8,3))
        ttk.Label(status,textvariable=self.public_details,
                  wraplength=790).pack(anchor='w',padx=8,pady=(0,5))
        ttk.Label(status,textvariable=self.progress_phase,
                  wraplength=790).pack(anchor='w',padx=8,pady=(0,5))
        self.progress_bar=ttk.Progressbar(status,orient='horizontal',mode='determinate',maximum=1)
        self.progress_bar.pack(fill='x',padx=8,pady=(0,4))
        ttk.Label(status,textvariable=self.progress_elapsed).pack(anchor='w',padx=8,pady=(0,10))

        # More specialized actions and configuration are kept in this window,
        # but no longer compete with the one-click local public task.
        self.advanced_button=ttk.Button(page,text='▸ Transfert privé et paramètres avancés',
                                        command=self._toggle_advanced)
        self.advanced_button.pack(anchor='w',pady=(2,4))
        self.advanced_frame=ttk.Frame(page)
        settings=ttk.LabelFrame(self.advanced_frame,text='Emplacements et outils')
        settings.pack(fill='x',pady=(2,8))
        self._line(settings,'Source locals',self.locals)
        self._line(settings,'Dossier public',self.checkout)
        self._line(settings,'Authoring Kit',self.kit,kind='file')
        self._line(settings,'Dossier privé',self.private_checkout)
        self._line(settings,'SemantiK Architect',self.semantik_root)
        self._line(settings,'RuntimeSet SemantiK',self.runtime_root)
        self._line(settings,'Plans éditoriaux',self.projections)
        self._line(settings,'Spek (Wiki)',self.spek_root)

        private=ttk.LabelFrame(self.advanced_frame,text='Transférer dans kristal-private (local)')
        private.pack(fill='x',pady=(0,8))
        ttk.Label(private,text='Parcours distinct : prévisualiser les mêmes Kristals sélectionnés, '
                  'puis copier dans le dépôt privé. Aucune synchronisation Git.',
                  wraplength=800).pack(anchor='w',padx=8,pady=(5,4))
        privbuttons=ttk.Frame(private)
        privbuttons.pack(anchor='w',padx=8,pady=(0,5))
        self.preview_private=ttk.Button(privbuttons,text='Prévisualiser la copie privée',
                                        command=self.preview_private_collection)
        self.preview_private.pack(side='left',padx=(0,7))
        self.apply_private=ttk.Button(privbuttons,text='Copier vers kristal-private',
                                      command=self.apply_private_collection)
        self.apply_private.pack(side='left')
        ttk.Checkbutton(private,text='Autoriser le retrait des fichiers privés obsolètes signalés dans l’aperçu',
                        variable=self.allow_retire_private).pack(anchor='w',padx=8,pady=(0,5))
        ttk.Label(private,text='Le dépôt privé doit être préparé par Bootstrap et disposer des droits adéquats.',
                  wraplength=800).pack(anchor='w',padx=8,pady=(0,7))

        self.log_button=ttk.Button(page,text='▸ Journal technique',command=self._toggle_log)
        self.log_button.pack(anchor='w',pady=(4,2))
        self.log_frame=ttk.Frame(page)
        self.journal=tk.Text(self.log_frame,wrap='word',height=10,font=('Consolas',9),
                             state='normal')
        self.journal.pack(fill='both',expand=True)
        self._advanced_open=False
        self._log_open=False
        self._log('Manager prêt. Aucun dépôt modifié.')
        self._update_selection_count()

    def _toggle_advanced(self):
        self._advanced_open=not self._advanced_open
        if self._advanced_open:
            self.advanced_frame.pack(fill='x',after=self.advanced_button,pady=(0,8))
            self.advanced_button.configure(text='▾ Masquer les paramètres avancés')
        else:
            self.advanced_frame.pack_forget()
            self.advanced_button.configure(text='▸ Transfert privé et paramètres avancés')

    def _toggle_log(self):
        self._log_open=not self._log_open
        if self._log_open:
            self.log_frame.pack(fill='both',expand=True,after=self.log_button,pady=(2,8))
            self.log_button.configure(text='▾ Masquer le journal technique')
        else:
            self.log_frame.pack_forget()
            self.log_button.configure(text='▸ Journal technique')

    def _log(self,line):
        self.journal.insert('end',str(line)+'\n');self.journal.see('end')

    def refresh(self):
        # Re-reading metadata never reselects a different workspace by index.
        previous=set(self._selected())
        try:
            entries=selectable_kristals(Path(self.locals.get()).expanduser())
        except (ManagerError, OSError) as exc:
            messagebox.showwarning('Kristal list',str(exc),parent=self)
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
        if hasattr(self,'stage') and not self._busy:
            self.stage.configure(state='normal' if count else 'disabled')

    def _invalidate_private_preview(self):
        self._private_preview_token=None
        self._private_preview_key=None
        self._private_preview_retire_count=0
        self.private_candidate.set('')
        self.allow_retire_private.set(False)

    def _selection_changed(self, _event=None):
        self._invalidate_private_preview()
        self._public_preview_token=None
        self._public_preview_key=None
        self._update_selection_count()
        if not self._busy:
            self.public_status.set('Sélectionne un ou plusieurs Kristals.' if not self._selected()
                                   else f'{len(self._selected())} Kristal(s) sélectionné(s), prêts à être préparés.')
            self.public_details.set('Aucune modification lancée pour cette sélection.')

    def _on_progress(self,event):
        names = {
            'preflight':'Vérification de la collection',
            'kit':'Vérification de l’Authoring Kit',
            'scan':'Analyse des Kristals',
            'precheck':'Vérification des sources',
            'build':'Construction des Kristals publics',
            'candidate_verify':'Vérification du candidat',
            'stage_copy':'Préparation des fichiers locaux',
            'verify':'Vérification C3',
            'cache':'Enregistrement du cache',
            'finished':'Terminé',
        }
        phase=names.get(event.get('phase'), 'Préparation')
        total=max(1,int(event.get('total') or 1))
        completed=max(0,min(total,int(event.get('completed') or 0)))
        self.progress_bar.configure(maximum=total,value=completed)
        slug=event.get('slug','')
        message=event.get('message') or ''
        self.progress_phase.set(f'{phase} — {completed}/{total}' +
                                (f' · {slug}' if slug else '') +
                                (f' · {message}' if message else ''))

    def _job(self,label,fn,*,with_progress=False):
        if self._busy:return
        self._busy=True
        for b in (self.preview_private,self.apply_private,self.stage,self.refresh_button):
            b.configure(state='disabled')
        self.listbox.configure(state='disabled')
        self._log('START — '+label)
        if label=='Préparation directe kristal-public (sans Git)':
            self.public_status.set('Préparation locale en cours…')
            self.public_details.set('Analyse et préparation des fichiers locaux. Aucun envoi GitHub.')
            self.progress_bar.configure(maximum=1,value=0)
            self.progress_phase.set('Démarrage des contrôles…')
            self._progress_started_at=time.monotonic()
            self._last_progress_second=-1
            self.progress_elapsed.set('Durée : 0 s')
        def run():
            def report_progress(event):
                # Background thread sends data only; tkinter updates in _poll.
                self._jobs.put(('__PROGRESS__',event,None))
            try:self._jobs.put((label,fn(report_progress) if with_progress else fn(),None))
            except Exception as exc:self._jobs.put((label,None,str(exc)))
        threading.Thread(target=run,daemon=True).start()

    def _poll(self):
        try:
            while True:
                label,result,error=self._jobs.get_nowait()
                if label == '__PROGRESS__':
                    if self._busy:
                        self._on_progress(result)
                    continue
                self._busy=False
                if label=='Préparation directe kristal-public (sans Git)' and self._progress_started_at is not None:
                    self.progress_elapsed.set(f'Durée totale : {int(time.monotonic()-self._progress_started_at)} s')
                    self._progress_started_at=None
                for b in (self.preview_private,self.apply_private,self.refresh_button):
                    b.configure(state='normal')
                self.listbox.configure(state='normal')
                self.stage.configure(state='normal' if self._selected() else 'disabled')
                if error:
                    if label=='Local public preview':
                        self._public_preview_token=None
                        self._public_preview_key=None
                    if label=='Private checkout preview':
                        self.private_candidate.set('')
                        self._private_preview_token=None
                        self._private_preview_key=None
                    self._log('BLOCKED — '+error)
                    if label=='Préparation directe kristal-public (sans Git)':
                        self.public_status.set('Préparation non effectuée')
                        self.public_details.set(error)
                        self.progress_phase.set('Préparation interrompue (voir le message ci-dessus).')
                    self.owner.log('WARN','Publication: '+error)
                else:
                    if label=='Local public preview':
                        self._public_preview_token=result['plan_token']
                        self._public_preview_key=(result['candidate'],result['checkout'])
                    if label=='Local public copy':
                        self._public_preview_token=None
                        self._public_preview_key=None
                    if label=='Private checkout preview':
                        self.private_candidate.set(result['candidate'])
                        self._private_preview_token=result['plan_token']
                        self._private_preview_retire_count=result['retire_count']
                        self._private_preview_key=(tuple(result['slugs']),result['candidate'],result['checkout'])
                    if label in ('Local private copy','Private preparation'):
                        self._private_preview_token=None
                        self._private_preview_key=None
                    self._log(json.dumps(result,ensure_ascii=False,indent=2))
                    if label=='Préparation directe kristal-public (sans Git)' and result.get('status') in ('LOCAL_PUBLIC_C3_VALID','LOCAL_PUBLIC_C3_PARTIAL'):
                        n=len(result.get('slugs',[]))
                        rejected = result.get('rejected', [])
                        if rejected:
                            self.public_status.set(f'{n} Kristal(s) préparé(s) · {len(rejected)} refusé(s) (voir détails).')
                        else:
                            self.public_status.set(f'{n} Kristal(s) mis dans le dossier public local avec succès.')
                        self.progress_bar.configure(maximum=1,value=1)
                        self.progress_phase.set('Collection préparée et vérifiée (C3).' if not rejected
                                                else 'Collection partielle vérifiée (C3). Kristals refusés non copiés.')
                        reused=len(result.get('reused_slugs',[]))
                        changed=len(result.get('new_slugs',[]))+len(result.get('updated_slugs',[]))
                        if result.get('incremental'):
                            details=f"{changed} nouveau(x)/modifié(s) · {reused} inchangé(s) réutilisé(s) · "
                        else:
                            details=f"{result.get('files_prepared',0)} fichiers préparés · "
                        if rejected:
                            details += 'Refusés : ' + ', '.join(x['slug'] for x in rejected[:12])
                            if len(rejected) > 12:
                                details += f' et {len(rejected)-12} autre(s)'
                            details += ' · '
                        self.public_details.set(details +
                            f"{result.get('collection_count',0)} Kristals dans la collection · "
                            'Aucun envoi GitHub. Vérifier le journal des refus et les droits avant toute synchronisation.')
                    if result.get('status')=='PRIVATE_WIKI_READY':self.wiki_candidate.set(result['output'])
                    if result.get('status')=='REQUIRES_INDEPENDENT_WIKI_REVIEW' and result.get('output'):
                        self.review_release.set(result['output'])
                    self.owner.log('INFO','Publication : '+label+' : '+result.get('status',''))
                    if result.get('push_performed'):
                        messagebox.showinfo('GitHub confirmed','Commit en ligne : '+result['revision']+'\n'+result['catalog_url'],parent=self)
        except Empty:pass
        if self._busy and self._progress_started_at is not None:
            second=int(time.monotonic()-self._progress_started_at)
            if second!=self._last_progress_second:
                self._last_progress_second=second
                self.progress_elapsed.set(f'Durée : {second} s · Manager travaille localement, sans GitHub')
        if self.winfo_exists():self.after(130,self._poll)

    def _manual_args(self):
        slugs=self._selected()
        if not slugs:
            raise ManagerError('Select at least one Kristal in the list.')
        return dict(locals_root=Path(self.locals.get()),destination_root=Path(self.manual_target.get()),
                    slugs=slugs,mode=self.manual_mode.get())

    def preview_manual_copies(self):
        try:args=self._manual_args()
        except ManagerError as exc:
            messagebox.showwarning('Selection',str(exc),parent=self);return
        self._copy_preview_key=None
        def job():
            plan=plan_copies(**args)
            return {k:v for k,v in plan.items() if k!='projects'} | {
                'projects':[{k:pr[k] for k in ('slug','source','target','files','to_copy','bytes')}
                            for pr in plan['projects']]}
        self._job('Local copy preview',job)

    def apply_manual_copies(self):
        try:args=self._manual_args()
        except ManagerError as exc:
            messagebox.showwarning('Selection',str(exc),parent=self);return
        resolved=str(args['destination_root'].expanduser().resolve())
        if self._copy_preview_key != (tuple(args['slugs']),resolved,args['mode']):
            messagebox.showwarning('Simulation requise','First preview this exact selection and folder.',parent=self)
            return
        if not messagebox.askyesno('LOCAL copies ONLY',
                f'Copier {len(args["slugs"])} Kristals vers :\n{resolved}\n\n'
                'NO git add, commit or push. Review all data before any public release. Confirm?',parent=self):
            return
        self._job('Copies locales',lambda:apply_copies(**args))

    def preview_private_collection(self):
        """Use ALREADY PREPARED read surfaces; never rebuild or modify source Kristals.

        A temporary candidate is an internal manifest/fingerprint package, not a
        user-facing publication step. Nothing is written to the Git checkout.
        """
        slugs=self._selected()
        if not slugs:
            messagebox.showwarning('Selection','Coche au moins un Kristal.',parent=self);return
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
        self._job('Private checkout preview',job)

    def apply_private_collection(self):
        slugs=self._selected()
        candidate=Path(self.private_candidate.get()).expanduser()
        checkout=Path(self.private_checkout.get()).expanduser()
        try:
            key=(tuple(sorted(slugs)),str(candidate.resolve(strict=True)),str(checkout.resolve(strict=True)))
        except OSError:
            messagebox.showwarning('Chemin','The candidate and private repository must exist.',parent=self);return
        if not slugs or self._private_preview_token is None or key!=self._private_preview_key:
            messagebox.showwarning('Preview required',
                 'Preview the same selection and private checkout before copying.',parent=self);return
        if self._private_preview_retire_count and not self.allow_retire_private.get():
            messagebox.showwarning('Controlled removal',
                f'{self._private_preview_retire_count} obsolete files are listed in the preview. '
                'Check explicit removal permission for this selection.',parent=self);return
        if not messagebox.askyesno('Copy to kristal-private',
             f'Copy only {len(slugs)} Kristals into PRIVATE checkout:\n{checkout}\n\n'
             'Only the listed files of selected Kristals will be updated. '
             'All other Kristals remain unchanged. No commit or push. Continue?',parent=self):return
        token=self._private_preview_token
        allow_retire=self.allow_retire_private.get()
        self._job('Local private copy',lambda:apply_private_sync(candidate=candidate,checkout=checkout,
                  slugs=slugs,expected_token=token,allow_retire=allow_retire))

    def prepare_public_direct(self):
        """One-click LOCAL preparation. No persistent candidate or Git writes."""
        slugs=self._selected()
        if not slugs:
            messagebox.showwarning('Sélection','Sélectionne au moins un Kristal.',parent=self)
            return
        locals_root=Path(self.locals.get()).expanduser()
        kit=Path(self.kit.get()).expanduser()
        checkout=Path(self.checkout.get()).expanduser()
        if not messagebox.askyesno('Mettre dans le dossier public local',
                f'Mettre {len(slugs)} Kristal(s) sélectionné(s) dans :\n{checkout}\n\n'
                'Le contenu local sera vérifié et sauvegardé avant mise à jour.\n'
                'Aucun envoi GitHub. Continuer ?',parent=self):
            return
        self._public_preview_token=None
        self._public_preview_key=None
        self._job('Préparation directe kristal-public (sans Git)',lambda progress:prepare_and_copy_public_local(
            locals_root=locals_root,kit_script=kit,checkout=checkout,
            slugs=slugs,retire_zoology_stub=False,progress=progress), with_progress=True)

    def prepare_public_candidate(self):
        """Create an isolated, C3-checkable candidate from selected workspaces.

        All Kit builds run on temporary copies; neither locals nor a Git checkout
        is changed. The candidate is never a C1/C2 approval or a public upload.
        """
        slugs=self._selected()
        if not slugs:
            messagebox.showwarning('Selection',
                'Select explicit Kristals for the PUBLIC candidate.',parent=self)
            return
        output=Path(self.candidate.get()).expanduser()
        if output.exists():
            messagebox.showwarning('Candidate exists',
                'Choose a new empty candidate path. Existing candidates are never overwritten.',
                parent=self)
            return
        if not messagebox.askyesno('Private C3 candidate',
                f'Build a PRIVATE publication candidate for {len(slugs)} selected Kristal(s)?\n'
                f'{output}\n\n'
                'Only temporary copies will be built. No Git commit, upload or public exposure.',
                parent=self):
            return
        locals_root=Path(self.locals.get()).expanduser()
        kit=Path(self.kit.get()).expanduser()
        def job():
            # This is a new private path, not a Git worktree. The staging engine
            # enforces that constraint and checks the Kit read-surface hashes.
            # Only create the default private candidate directory, and only
            # after verifying it does not live inside a Git checkout. Never
            # create arbitrary user-selected parents (which might be public).
            private_root=(Path(os.environ.get('LOCALAPPDATA') or str(Path.home()))
                          /'Kristal'/'private-candidates').resolve()
            if output.resolve().parent == private_root and not private_root.is_dir():
                from .publication_stage import _inside_git_tree
                if _inside_git_tree(private_root):
                    raise ManagerError('Private candidate directory is inside a Git checkout')
                private_root.mkdir(parents=True,exist_ok=True)
            return prepare_private_collection(locals_root=locals_root,kit_script=kit,
                output=output,slugs=slugs,write_private=True,build_on_copy=True)
        self._job('PUBLIC private C3 candidate',job)

    def preview_local_public(self):
        slugs=self._selected()
        if not slugs:
            messagebox.showwarning('Sélection','Sélectionne au moins un Kristal.',parent=self)
            return
        candidate=Path(self.candidate.get()).expanduser()
        checkout=Path(self.checkout.get()).expanduser()
        self._public_preview_token=None
        self._public_preview_key=None
        self._job('Local public preview',lambda:plan_local_public(
            candidate=candidate,checkout=checkout,retire_zoology_stub=self.retire.get()))

    def apply_local_public(self):
        candidate=Path(self.candidate.get()).expanduser()
        checkout=Path(self.checkout.get()).expanduser()
        token=self._public_preview_token
        try:
            candidate_path=str(candidate.resolve(strict=True))
            checkout_path=str(checkout.resolve(strict=True))
        except OSError:
            messagebox.showwarning('Chemins','Le candidat et le dossier public doivent exister.',parent=self)
            return
        if not token or self._public_preview_key != (candidate_path,checkout_path):
            messagebox.showwarning('Prévisualisation requise',
                'Clique d’abord sur B2 pour cette sélection exacte et ces dossiers.',parent=self)
            return
        if not messagebox.askyesno('Copie LOCALE uniquement',
            'Copier la sélection dans le dossier local kristal-public ?\n\n'
            'C3 sera vérifié et une sauvegarde sera conservée hors du dépôt.\n'
            'AUCUN git add, commit, push ou upload.\n\n'
            'Attention : ton script GitHub rendrait ces fichiers publics. '
            'Vérifie C1/C2 et les droits AVANT de lancer ce script.',parent=self):
            return
        self._job('Local public copy',lambda:apply_local_public(candidate=candidate,
            checkout=checkout,expected_token=token,
            retire_zoology_stub=self.retire.get()))

    def make_commit(self):
        if not self.dry.get() and not messagebox.askyesno('Confirmation',
                'Create a LOCAL commit in kristal-public? NO push will be performed.',parent=self):return
        c=Path(self.candidate.get());r=Path(self.checkout.get());retire=self.retire.get();write=not self.dry.get()
        self._job('Commit Git local',lambda:prepare_local_commit(candidate=c,
                  checkout=r,retire_zoology_stub=retire,write=write))

    def publish(self):
        if not self.external.get():
            messagebox.showwarning('Independent evidence','Confirmation of C1/C2 authorizations required.',parent=self);return
        if not all(x.get().strip() for x in (self.trust,self.c1,self.c2,self.policy)):
            messagebox.showwarning('Preuves manquantes','Provide all four evidence paths.',parent=self);return
        if not self.dry.get() and not messagebox.askyesno('Publier sur Internet',
                    'Irreversible PUBLIC release of authorized files. Push to GitHub now?',parent=self):return
        values=(Path(self.checkout.get()),Path(self.trust.get()),Path(self.c1.get()),Path(self.c2.get()),Path(self.policy.get()))
        write=not self.dry.get()
        self._job('C1/C2 verification and push',lambda:publish_approved_commit(checkout=values[0],
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
        self._job('Private Wiki editorial plans',job)

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
        self._job('Wiki generation with SemantiK + Spek',job)

    def prepare_review(self):
        private=Path(self.wiki_candidate.get())
        parent=Path(self.candidate.get()).expanduser().parent
        dest=parent/('wiki-review-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
        write=not self.dry.get()
        def job():
            if write:dest.parent.mkdir(parents=True,exist_ok=True)
            return prepare_wiki_review(checkout=Path(self.checkout.get()),private=private,
                      output=dest,write=write)
        self._job('Editorial review before Wiki publication',job)

    def publish_wiki(self):
        if not self.external.get():
            messagebox.showwarning('Revue obligatoire',
                'Validate C1/C2 signatures and independent review of Wiki pages.',parent=self);return
        if not all(x.get().strip() for x in (self.trust,self.c1,self.c2,self.policy,self.review_release,self.wiki_review)):
            messagebox.showwarning('Preuves requises',
                'C1/C2 signatures, prepared Wiki bundle and approved Wiki review required.',parent=self);return
        write=not self.dry.get()
        if write and not messagebox.askyesno('Publication du Wiki natif',
                'You are about to publish reviewed pages to the Internet in kristal-public.wiki.git. Confirm?',parent=self):return
        self._job('Publication du Wiki GitHub natif',lambda:publish_wiki_reviewed(
             checkout=Path(self.checkout.get()),release=Path(self.review_release.get()),
             review=Path(self.wiki_review.get()),trust=Path(self.trust.get()),
             c1_dir=Path(self.c1.get()),c2_dir=Path(self.c2.get()),
             policy_dir=Path(self.policy.get()),external_approval_confirmed=True,push=write))
