"""Small Tkinter front-end for explicit, staged kOA Kristal updates."""
import json, subprocess, sys, threading, tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path

class UI(tk.Tk):
 def __init__(self):
  super().__init__();self.title('kOA — Mise à jour contrôlée du Kristal');self.geometry('850x650')
  self.candidate=tk.StringVar();self.campaign=tk.StringVar();self.config=tk.StringVar()
  self.accept_legacy=tk.BooleanVar(value=False)
  head=ttk.Frame(self,padding=12);head.pack(fill='x')
  ttk.Label(head,text='Kristal-kOA-Ecosystem · Overlay de mise à jour',font=('Segoe UI',14,'bold')).pack(anchor='w')
  ttk.Label(head,text='Staging → validation native → Manager → diagnostic facultatif → installation sur confirmation.').pack(anchor='w')
  panel=ttk.Frame(self,padding=12);panel.pack(fill='x')
  def path_row(label,var,file=False):
   row=ttk.Frame(panel);row.pack(fill='x',pady=5)
   ttk.Label(row,text=label,width=16).pack(side='left')
   ttk.Entry(row,textvariable=var).pack(side='left',expand=True,fill='x',padx=5)
   if file:ttk.Button(row,text='Parcourir...',command=lambda:var.set(filedialog.askopenfilename(filetypes=[('ZIP / JSON','*.zip *.json'),('Tous les fichiers','*.*')]))).pack(side='right')
  path_row('ZIP candidat',self.candidate,True);path_row('Campagne',self.campaign);path_row('Config JSON',self.config,True)
  btn=ttk.Frame(self,padding=12);btn.pack(fill='x')
  for label,func in [('Inventorier',lambda:self.run('inventaire')),('Kit disponible?',lambda:self.run('kit-status')),
                     ('1. Préparer',lambda:self.run('preparer','--candidate',self.candidate.get())),
                     ('2. Valider',lambda:self.with_campaign('valider')),
                     ('3. Diagnostiquer',lambda:self.confirm_action('diagnostiquer')),
                     ('4. Installer',lambda:self.confirm_action('installer')),
                     ('5. Restaurer',lambda:self.confirm_action('restaurer'))]:
   ttk.Button(btn,text=label,command=func).pack(side='left',padx=2,pady=2)
  ttk.Checkbutton(self,text='J’autorise la seule exception connue LEGACY STATE v6/v9 (ne certifie pas le Kristal)',variable=self.accept_legacy).pack(anchor='w',padx=12)
  ttk.Label(self,text='Les preuves historiques ne sont jamais promues automatiquement.',padding=(12,5)).pack(anchor='w')
  self.log=scrolledtext.ScrolledText(self,wrap='word',state='disabled');self.log.pack(fill='both',expand=True,padx=12,pady=8)
  self.busy=False
 def with_campaign(self,action):
  rid=self.campaign.get().strip()
  if not rid:messagebox.showwarning('Campagne','Prépare une campagne ou saisis son identifiant.');return
  self.run(action,'--campagne',rid)
 def confirm_action(self,action):
  rid=self.campaign.get().strip()
  if not rid:messagebox.showwarning('Campagne','Identifiant manquant.');return
  msg=('Lancer un nouveau diagnostic (sans promotion des preuves)?' if action=='diagnostiquer' else
       'Installer le staging après sauvegarde de l’ancien Kristal?' if action=='installer' else
       'Restaurer la sauvegarde précédente? Les modifications ultérieures bloqueront la restauration.')
  if not messagebox.askyesno('Confirmation explicite',msg):return
  params=['--campagne',rid]
  if action in ('installer','restaurer'):params.append('--confirmer')
  if action=='installer' and self.accept_legacy.get():params.append('--accepter-heritage-v6')
  self.run(action,*params)
 def append(self,s):
  self.log.configure(state='normal');self.log.insert('end',s+'\n');self.log.see('end');self.log.configure(state='disabled')
 def run(self,action,*args):
  if self.busy:return
  if action=='preparer' and not self.candidate.get():messagebox.showwarning('Candidat','Sélectionne une archive ZIP.');return
  self.busy=True;self.append('\n>>> '+action+' '+' '.join(str(x) for x in args))
  cli=[sys.executable,'-m','koa_upgrade.cli']
  if self.config.get().strip():cli+=['--config',self.config.get().strip()]
  cli+=[action,*map(str,args)]
  def worker():
   try:
    proc=subprocess.run(cli,cwd=str(Path(__file__).resolve().parents[1]),capture_output=True,text=True,encoding='utf-8',errors='replace',shell=False)
    output=proc.stdout+'\n'+proc.stderr
    self.after(0,lambda:self.append(output+'\nCode: '+str(proc.returncode)))
    if action=='preparer' and proc.returncode==0:
     try:
      id=json.loads(proc.stdout)['campaign'];self.after(0,lambda:self.campaign.set(id))
     except (KeyError,ValueError):pass
   except Exception as e:self.after(0,lambda:self.append('ERREUR: '+repr(e)))
   finally:self.after(0,lambda:setattr(self,'busy',False))
  threading.Thread(target=worker,daemon=True).start()

if __name__=='__main__':UI().mainloop()
