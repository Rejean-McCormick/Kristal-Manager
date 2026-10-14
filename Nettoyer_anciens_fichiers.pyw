"""Optional, narrowly scoped migration cleaner for Kristal Manager alpha.13.

Run only after installing the updated package in the SAME directory. Never
performs generic recursive cleanup, follows links, or deletes unknown data.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

ROOT = Path(__file__).resolve().parent
# Historic root snapshot index was moved to docs/snapshots/ in alpha.13.
# Delete only if its original bytes are unchanged. There are no other targets.
OBSOLETE = {
    'SNAPSHOT_INDEX.txt': '121722c3b4c6c0129aa9ea19bf9ab7e298f29ca68475351778417a55926404d1'
}

def eligible_files():
    rows = []
    for relative, expected in OBSOLETE.items():
        path = ROOT / relative
        if path.is_symlink():
            rows.append((relative, 'REFUSÉ : lien symbolique', False))
        elif not path.exists():
            rows.append((relative, 'Absent : aucune action', False))
        elif not path.is_file():
            rows.append((relative, 'REFUSÉ : pas un fichier', False))
        else:
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            rows.append((relative, 'Supprimable (empreinte connue)' if digest==expected else
                         'REFUSÉ : contenu local modifié', digest==expected))
    return rows

class Cleaner(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Kristal Manager — Nettoyage local contrôlé')
        self.geometry('690x320');self.minsize(560,290)
        self.configure(bg='#f7faf9')
        box=ttk.Frame(self,padding=20);box.pack(fill='both',expand=True)
        ttk.Label(box,text='NETTOYAGE LOCAL — alpha.13',font=('Segoe UI',15,'bold')).pack(anchor='w')
        ttk.Label(box,text='Racine fixe : '+str(ROOT),wraplength=630).pack(anchor='w',pady=(8,0))
        ttk.Label(box,text='Seul l’ancien index de snapshot, désormais archivé dans docs/snapshots, est concerné.',
                  wraplength=630).pack(anchor='w',pady=(4,10))
        self.output=tk.Text(box,height=5,wrap='word',state='disabled');self.output.pack(fill='x')
        self.confirm=tk.BooleanVar(value=False)
        ttk.Checkbutton(box,text='Je confirme la suppression des SEULS fichiers éligibles ci-dessus',
                        variable=self.confirm).pack(anchor='w',pady=10)
        line=ttk.Frame(box);line.pack(fill='x')
        ttk.Button(line,text='Réexaminer',command=self.refresh).pack(side='left')
        ttk.Button(line,text='Supprimer les fichiers confirmés',command=self.cleanup).pack(side='left',padx=10)
        ttk.Button(line,text='Fermer',command=self.destroy).pack(side='right')
        self.refresh()

    def refresh(self):
        self.confirm.set(False)
        rows=eligible_files()
        self.output.configure(state='normal');self.output.delete('1.0','end')
        for name,status,_ in rows:self.output.insert('end',f'{name}  —  {status}\n')
        self.output.configure(state='disabled')

    def cleanup(self):
        if not self.confirm.get():
            messagebox.showwarning('Confirmation requise','Cochez la confirmation après avoir lu le tableau.');return
        targets=[relative for relative,_,ok in eligible_files() if ok]
        if not targets:
            messagebox.showinfo('Aucune action','Aucun fichier obsolète non modifié à supprimer.');return
        if not messagebox.askyesno('Confirmation finale',
            'Supprimer définitivement uniquement :\n'+ '\n'.join(targets)+'\n\nAucun sous-dossier ne sera parcouru.'):
            return
        deleted=[]
        for relative in targets:
            path=ROOT / relative
            expected=OBSOLETE[relative]
            # A second check, immediately before deletion, prevents accidental
            # removal of a modified file between preview and confirmation.
            if not path.is_symlink() and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==expected:
                path.unlink();deleted.append(relative)
        self.refresh()
        messagebox.showinfo('Terminé',f'{len(deleted)} fichier(s) supprimé(s).')

if __name__=='__main__':
    Cleaner().mainloop()
