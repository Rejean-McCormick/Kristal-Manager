"""Shared, presentation-only column profiles for both Manager table surfaces.

Treeview `displaycolumns` only changes visibility and order. All underlying row
values and classifications remain unchanged; selection and sorting still work.
"""
from __future__ import annotations

from tkinter import ttk
import tkinter as tk

PRESET_NAMES = ('Essential', 'Review queue', 'Classification', 'Semantic review', 'Diagnostics', 'All columns')

PRESETS = {
    'manager': {
        'Essential': ('title', 'editorial_state', 'semantic_role', 'arketype', 'usage', 'micro', 'authoring_status', 'readiness'),
        'Review queue': ('title', 'editorial_state', 'review_stage', 'next_action', 'authoring_status', 'source_catalog', 'native_evidence', 'prf_review', 'unesco_review', 'readiness'),
        'Classification': ('title', 'arketype', 'usage', 'category', 'micro', 'unesco_review', 'prf_review'),
        'Semantic review': ('title', 'semantic_role', 'native_evidence', 'prf_review', 'unesco_review', 'arketype', 'usage', 'micro'),
        'Diagnostics': ('title', 'readiness', 'authoring_status', 'source_catalog', 'diag', 'profile', 'state_ref', 'artifacts', 'content'),
    },
    'analysis': {
        'Essential': ('title', 'editorial_state', 'semantic_role_ai', 'declared_ark', 'declared_prf', 'declared_unesco', 'authoring_status', 'priority'),
        'Review queue': ('title', 'editorial_state', 'review_stage', 'next_action', 'authoring_status', 'source_catalog', 'native_evidence', 'prf_review_ai', 'unesco_review', 'priority'),
        'Classification': ('title', 'declared_ark', 'declared_prf', 'subject_domain', 'declared_unesco', 'unesco_review', 'registered_ark', 'new_suggestions'),
        'Semantic review': ('title', 'semantic_role_ai', 'native_evidence', 'prf_review_ai', 'unesco_review', 'content_status', 'ark_structure_history', 'registered_ark'),
        'Diagnostics': ('title', 'priority', 'readiness', 'authoring_status', 'source_catalog', 'content_status', 'ark_structure_history', 'v11_kristalizer', 'keywords'),
    },
}


def columns_for(surface: str, preset: str, all_columns: tuple[str, ...]) -> tuple[str, ...]:
    """Validate the advertised view; never produce an empty or invalid Treeview layout."""
    known = tuple(all_columns)
    if preset == 'All columns':
        return known
    if surface not in PRESETS or preset not in PRESETS[surface]:
        raise ValueError(f'Unknown column view: {surface}/{preset}')
    result = tuple(key for key in PRESETS[surface][preset] if key in known)
    if 'title' not in result or not result:
        raise ValueError('A column view must include the Kristal name')
    return result


def configure_tree_columns(tree, surface: str, preset: str) -> tuple[str, ...]:
    all_columns = tuple(tree['columns'])
    selected = columns_for(surface, preset, all_columns)
    tree.configure(displaycolumns=selected)
    return selected


class ColumnViewControl:
    """One shared profile chooser plus optional custom column selection.

    Custom columns affect only this user's UI preferences; the view never writes
    to the scanned source trees and cannot approve any semantic classification.
    """
    def __init__(self, parent, tree, surface: str, *, initial: str = 'Essential',
                 custom_columns=None, on_change=None):
        if surface not in PRESETS:
            raise ValueError('Invalid table surface')
        self.tree = tree
        self.surface = surface
        self.on_change = on_change
        valid = set(tree['columns'])
        chosen = tuple(x for x in (custom_columns or ()) if x in valid)
        self._custom = tuple(x for x in tree['columns'] if x in chosen or x == 'title') if chosen else None
        if self._custom and len(self._custom) < 2:
            self._custom = None
        self.frame = ttk.Frame(parent)
        ttk.Label(self.frame, text='Column view').pack(side='left', padx=(0, 5))
        names = (*PRESET_NAMES, 'Custom') if self._custom else PRESET_NAMES
        self.choice = tk.StringVar(value=initial if initial in names else 'Essential')
        self.selector = ttk.Combobox(self.frame, state='readonly', width=18,
                                      textvariable=self.choice, values=names)
        self.selector.pack(side='left')
        self.selector.bind('<<ComboboxSelected>>', lambda _event: self.apply())
        ttk.Button(self.frame, text='Choose columns…', command=self.customize).pack(side='left', padx=(5, 0))
        self.apply(notify=False)

    def apply(self, *, notify=True):
        current = self.choice.get()
        if current == 'Custom' and self._custom:
            columns = self._custom
            self.tree.configure(displaycolumns=columns)
        else:
            if current not in PRESET_NAMES:
                current = 'Essential'
                self.choice.set(current)
            columns = configure_tree_columns(self.tree, self.surface, current)
        if notify and self.on_change:
            self.on_change(current, columns)
        return columns

    def customize(self):
        window = tk.Toplevel(self.frame)
        window.title('Choose visible columns')
        window.geometry('410x540')
        window.transient(self.frame.winfo_toplevel())
        window.grab_set()
        ttk.Label(window, text='Select columns to show (Kristal is always visible)',
                  padding=(12, 12)).pack(anchor='w')
        outer = ttk.Frame(window, padding=(12, 0, 12, 6));outer.pack(fill='both', expand=True)
        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        frame = ttk.Frame(canvas)
        frame.bind('<Configure>', lambda _e: canvas.configure(scrollregion=canvas.bbox('all')))
        item = canvas.create_window((0, 0), window=frame, anchor='nw')
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(item, width=event.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        current = set(tuple(self.tree['displaycolumns']))
        switches = {}
        for key in self.tree['columns']:
            label = str(self.tree.heading(key, 'text'))
            var = tk.BooleanVar(value=key in current)
            switches[key] = var
            ttk.Checkbutton(frame, text=label, variable=var,
                            state='disabled' if key == 'title' else 'normal').pack(anchor='w', pady=2)
        buttons = ttk.Frame(window, padding=10);buttons.pack(fill='x')
        def save():
            selected = tuple(key for key in self.tree['columns'] if switches[key].get() or key == 'title')
            self._custom = selected
            self.choice.set('Custom')
            self.selector.configure(values=(*PRESET_NAMES, 'Custom'))
            self.apply()
            window.destroy()
        ttk.Button(buttons, text='Apply', command=save).pack(side='right', padx=5)
        ttk.Button(buttons, text='Cancel', command=window.destroy).pack(side='right')
