"""Non-qualifying Arketype structure inspection for Manager, read-only."""
from __future__ import annotations
import importlib.util
from pathlib import Path


def _observer():
    # Manager, Arketype and KristalDiag are siblings in C:\\mycode\\Kristal.
    root = Path(__file__).resolve().parents[2] / 'Arketype'
    source = root / 'arketype' / 'structural_observer.py'
    if not source.is_file():
        raise FileNotFoundError(f'Arketype non trouvé : {source}')
    spec = importlib.util.spec_from_file_location('_arketype_structure_manager', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module,root


def inspect(target):
    module,root = _observer()
    return module.inspect(target,root)


def inspect_all(target):
    module,root = _observer()
    return module.inspect_many(target,root)
