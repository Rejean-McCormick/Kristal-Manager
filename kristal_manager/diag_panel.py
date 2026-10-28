"""Modal, one-click KristalDiag UI; no command line or profile typing required."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Thread
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .diag_bridge import OFFICIAL_PROFILES, bundled_kristaldiag, evidence_directory

PALETTE = '#1E6864'
PROFILE_CHOICES = {
    'État du Kristal — recommandé': 'V9-State-Reader',
    'Réseau et nœud V10 — avancé': 'V10-Node-Reader',
    'Contrôle étendu V10 — avancé': 'V10-Full',
}


class DiagnosticPanel(tk.Toplevel):
    """One overlay per selected Kristal, remains responsive while worker runs."""

    def __init__(self, manager, row: dict):
        super().__init__(manager)
        self.manager = manager
        self.row = dict(row)
        self.result: dict | None = row.get('diag_report')
        self.title('Diagnostic du Kristal — Kristal Manager')
        self.geometry('880x665')
        self.minsize(690, 510)
        self.transient(manager)
        self.protocol('WM_DELETE_WINDOW', self._close)
        self.configure(background='#f5f8f8')
        self.status = tk.StringVar(value='Prêt pour le diagnostic.')
        self.profile = tk.StringVar(value=next(iter(PROFILE_CHOICES)))
        self.report_location = tk.StringVar(value='Les résultats seront enregistrés dans les données locales du Manager.')
        self._layout()
        self._check_ready()
        if self.result:
            self.render_result(self.result)
        self.grab_set()
        self.focus_set()

    def _layout(self):
        header = tk.Frame(self, bg='#eaf3f0', padx=20, pady=15)
        header.pack(fill='x')
        try:
            self._brand_icon = tk.PhotoImage(file=str(Path(__file__).resolve().parent / 'assets' / 'logo_header.png'))
            tk.Label(header, image=self._brand_icon, bg='#eaf3f0').pack(side='left', padx=(0, 12))
        except (tk.TclError, OSError):
            self._brand_icon = None
        tk.Label(header, text='DIAGNOSTIC KRISTAL', bg='#eaf3f0', fg=PALETTE,
                 font=('Segoe UI', 19, 'bold')).pack(anchor='w')
        tk.Label(header, text=self.row.get('title', 'Kristal'), bg='#eaf3f0',
                 fg='#243e3c', font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(2, 1))
        tk.Label(header, text=self.row.get('path', ''), bg='#eaf3f0',
                 fg='#506865', font=('Segoe UI', 9)).pack(anchor='w')

        body = ttk.Frame(self, padding=16)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='Quel diagnostic lancer ?', style='H2.TLabel').pack(anchor='w')
        tools = ttk.Frame(body)
        tools.pack(fill='x', pady=(7, 5))
        self.combo = ttk.Combobox(tools, state='readonly', textvariable=self.profile,
                                  values=list(PROFILE_CHOICES), width=39)
        self.combo.pack(side='left', fill='x', expand=True)
        self.start_button = ttk.Button(tools, text='Lancer le diagnostic',
                                       style='Primary.TButton', command=self._run)
        self.start_button.pack(side='left', padx=(12, 0))

        self.help = ttk.Label(body,
            text='V9-State-Reader : état et engagements locaux. Les modes V10 exigent d’autres surfaces et peuvent échouer sur un Kristal local.',
            style='Sub.TLabel', wraplength=790)
        self.help.pack(anchor='w', pady=(2, 6))
        ttk.Label(body, textvariable=self.status, style='H2.TLabel', wraplength=810).pack(anchor='w', pady=(4, 5))
        self.progress = ttk.Progressbar(body, mode='indeterminate')
        self.progress.pack(fill='x')
        ttk.Label(body, text='Diagnostic indépendant : le verdict ne vaut ni publication, ni certification V11, ni autorisation.',
                  style='Sub.TLabel', wraplength=790).pack(anchor='w', pady=(8, 4))

        bottom = ttk.Frame(body)
        bottom.pack(side='bottom', fill='x', pady=(10, 0))
        self.copy_button = ttk.Button(bottom, text='Copier le résultat', command=self._copy)
        self.copy_button.pack(side='left')
        self.save_button = ttk.Button(bottom, text='Exporter le rapport…', command=self._save)
        self.save_button.pack(side='left', padx=(7, 0))
        self.open_button = ttk.Button(bottom, text='Ouvrir les preuves', command=self._open_evidence)
        self.open_button.pack(side='left', padx=(7, 0))
        ttk.Button(bottom, text='Fermer', command=self._close).pack(side='right')
        notebook = ttk.Notebook(body)
        notebook.pack(fill='both', expand=True, pady=(6, 0))
        main = ttk.Frame(notebook, padding=6)
        detail = ttk.Frame(notebook, padding=6)
        notebook.add(main, text='Résumé et anomalies')
        notebook.add(detail, text='Rapport JSON')
        main.rowconfigure(0, weight=1)
        main.columnconfigure(0, weight=1)
        self.summary = tk.Text(main, wrap='word', font=('Segoe UI', 10), relief='flat',
                               borderwidth=1, padx=12, pady=10, height=10)
        self.summary.grid(row=0, column=0, sticky='nsew')
        s = ttk.Scrollbar(main, orient='vertical', command=self.summary.yview)
        s.grid(row=0, column=1, sticky='ns')
        self.summary.configure(yscrollcommand=s.set, state='disabled')
        detail.rowconfigure(0, weight=1)
        detail.columnconfigure(0, weight=1)
        self.json_text = tk.Text(detail, wrap='none', font=('Consolas', 9), relief='flat', padx=10, pady=9, height=10)
        self.json_text.grid(row=0, column=0, sticky='nsew')
        y = ttk.Scrollbar(detail, orient='vertical', command=self.json_text.yview)
        y.grid(row=0, column=1, sticky='ns')
        self.json_text.configure(yscrollcommand=y.set, state='disabled')

        self._buttons()
        self._set_text(self.summary,
            '1. Choisissez le contrôle « État du Kristal — recommandé » (déjà sélectionné).\n'
            '2. Cliquez sur « Lancer le diagnostic ».\n'
            '3. Le verdict et les anomalies s’afficheront ici.\n\n'
            'Les résultats sont sauvegardés automatiquement hors du dossier des Kristals.')

    @staticmethod
    def _set_text(widget, value):
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', value)
        widget.configure(state='disabled')

    def _buttons(self):
        state = 'normal' if self.result else 'disabled'
        for widget in (self.copy_button, self.save_button):
            widget.configure(state=state)
        self.open_button.configure(state='normal' if self.result and
                                   Path(self.result.get('evidence_directory', '/not-present')).is_dir() else 'disabled')

    def _check_ready(self):
        if not bundled_kristaldiag().is_file():
            self.status.set('Moteur KristalDiag introuvable dans cette archive.')
            self.start_button.configure(state='disabled')
            return
        import importlib.util
        if importlib.util.find_spec('jsonschema') is None:
            self.status.set('Un prérequis Python manque : jsonschema.')
            self.start_button.configure(state='disabled')
            self.install_button = ttk.Button(self.start_button.master, text='Installer le prérequis…',
                                             command=self._install_dependency)
            self.install_button.pack(side='left', padx=(7, 0))
        else:
            self.start_button.configure(state='normal' if not self.manager.busy else 'disabled')

    def _install_dependency(self):
        if not messagebox.askyesno('Installer jsonschema ?',
            'KristalDiag a besoin du paquet Python « jsonschema ».\n\n'
            'L’installer avec pip pour cet utilisateur peut nécessiter Internet et modifier son environnement Python.\n'
            'Aucun Kristal ne sera modifié. Continuer ?', parent=self):
            return
        self.install_button.configure(state='disabled')
        self.status.set('Installation du prérequis en cours…')
        self.progress.start(12)
        def task():
            try:
                p = subprocess.run([sys.executable, '-m', 'pip', 'install', '--user', 'jsonschema>=4.20'],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, timeout=240, check=False)
                return (p.returncode, p.stdout.decode('utf-8', errors='replace')[-3000:])
            except (OSError, subprocess.TimeoutExpired) as exc:
                return (-1, str(exc))
        def done(result):
            if not self.winfo_exists():
                return
            self.progress.stop()
            code, message = result
            if code == 0:
                self.status.set('Prérequis installé. Vous pouvez lancer le diagnostic.')
                self.install_button.pack_forget()
                self.start_button.configure(state='normal')
            else:
                self.status.set('Installation impossible — consultez le message.')
                self.install_button.configure(state='normal')
                messagebox.showerror('Installation du prérequis', message, parent=self)
        def worker():
            outcome = task()
            try:
                # The main window's queue is already polled on Tk's main thread.
                self.manager.events.put(('diag_dependency', (self, outcome), None, None))
            except Exception:
                pass
        Thread(target=worker, daemon=True).start()
        self._dependency_done = done

    def _run(self):
        if self.manager.busy:
            messagebox.showinfo('Opération en cours', 'Terminez d’abord l’opération actuelle.', parent=self)
            return
        selected = PROFILE_CHOICES[self.profile.get()]
        self.result = None
        self._buttons()
        self.start_button.configure(state='disabled')
        self.combo.configure(state='disabled')
        self.status.set('Diagnostic en cours…')
        self.progress.start(13)
        self._set_text(self.summary, 'KristalDiag examine les fichiers. Le résultat apparaîtra ici.')
        self.manager.run_diag_from_panel(self.row, selected)

    def render_result(self, result: dict):
        if not self.winfo_exists():
            return
        self.result = result
        self.progress.stop()
        self.combo.configure(state='readonly')
        self.start_button.configure(state='normal')
        summary = result.get('external_report') or {}
        verdict = result.get('verdict') or 'Indéterminé'
        process = result.get('process_status') or '—'
        self.status.set(f'Verdict KristalDiag : {verdict}  ·  Exécution : {process}')
        rows = [
            f'KRISTAL : {self.row.get("title")}',
            f'Profil testé : {result.get("profile") or "outil externe"}',
            f'Verdict observé : {verdict}',
            f'Contrôles : {result.get("counts") or "aucun résumé"}',
            f'Fichiers d’état connus modifiés : {"ATTENTION : OUI" if result.get("input_changed_during_run") else "aucun changement détecté"}',
            '',
            'ANOMALIES',
        ]
        issues = result.get('findings') or []
        if issues:
            rows.extend(f'• {i.get("level")} {i.get("verdict")} — {i.get("message")}' for i in issues[:100])
        else:
            rows.append('Aucune anomalie détaillée trouvée dans le rapport.' if summary else
                        'Aucun rapport KristalDiag exploitable — consulter le journal ci-dessous.')
        rows.extend(['', 'PREUVES', result.get('evidence_directory') or '—', '',
                     'LIMITES : V9/V10 selon le profil; aucune attestation C1 signée ou validation v11 établie.'])
        stderr = result.get('stderr_excerpt') or ''
        if stderr:
            rows.extend(['', 'JOURNAL D’ERREUR', stderr[-3000:]])
        self._set_text(self.summary, '\n'.join(rows))
        self._set_text(self.json_text, json.dumps(result, indent=2, ensure_ascii=False))
        self._buttons()

    def render_error(self, message: str):
        if not self.winfo_exists():
            return
        self.progress.stop()
        self.combo.configure(state='readonly')
        self.start_button.configure(state='normal')
        self.status.set('Le diagnostic n’a pas pu être terminé.')
        self._set_text(self.summary, 'ERREUR\n\n' + str(message) + '\n\nAucun verdict de conformité ne peut être déduit.')

    def _copy(self):
        if self.result:
            self.clipboard_clear()
            self.clipboard_append(json.dumps(self.result, indent=2, ensure_ascii=False))
            self.status.set('Résultat JSON copié dans le presse-papiers.')

    def _save(self):
        if not self.result:
            return
        dest = filedialog.asksaveasfilename(parent=self, title='Exporter le rapport KristalDiag',
            initialfile='kristaldiag-rapport.json', defaultextension='.json', filetypes=[('JSON', '*.json')])
        if dest:
            target = Path(dest)
            if not self.manager._safe_output(target):
                return
            if target.exists() and not messagebox.askyesno('Remplacer ?', f'Remplacer {target} ?', parent=self):
                return
            try:
                target.write_text(json.dumps(self.result, indent=2, ensure_ascii=False), encoding='utf-8')
                self.status.set('Rapport exporté : ' + str(target))
            except OSError as exc:
                messagebox.showerror('Export impossible', str(exc), parent=self)

    def _open_evidence(self):
        folder = Path(self.result.get('evidence_directory', '')) if self.result else None
        if folder and folder.is_dir():
            if os.name == 'nt':
                os.startfile(str(folder))
            else:
                import webbrowser
                webbrowser.open(folder.as_uri())

    def _close(self):
        if getattr(self.manager, '_diag_dialog', None) is self:
            self.manager._diag_dialog = None
        self.destroy()
