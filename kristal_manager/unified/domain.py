"""No Tk / SQL dependencies. Contracts for normalized operational observations."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json

class Freshness(str, Enum):
    CURRENT = 'CURRENT'
    PARTIAL = 'PARTIAL_SCOPE'
    STALE = 'STALE'
    UNVERIFIED = 'UNVERIFIED'

class RunStatus(str, Enum):
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    INTERRUPTED = 'INTERRUPTED'

class EvidenceStatus(str, Enum):
    PASS = 'PASS'
    FAIL = 'FAIL'
    WARN = 'WARN'
    BLOCKED = 'BLOCKED'
    NOT_APPLICABLE = 'NOT_APPLICABLE'
    EXECUTION_ERROR = 'EXECUTION_ERROR'
    UNKNOWN = 'UNKNOWN'

@dataclass(frozen=True)
class EvidenceReference:
    uri: str | None = None
    sha256: str | None = None
    source_scope: str = 'bounded-v9'
    qualification: str = 'NOT_ESTABLISHED'


def safe_object(value: object, *, maximum: int = 2*1024*1024) -> str:
    serialized = json.dumps(value,ensure_ascii=False,sort_keys=True,default=str,
                            separators=(',',':'))
    if len(serialized.encode('utf-8')) > maximum:
        raise ValueError('Le rapport est trop volumineux pour le registre; conserver la preuve séparément.')
    return serialized


def safe_workspace(path: str | Path) -> Path:
    target = Path(path).expanduser().resolve(strict=True)
    if not target.is_dir() or not (target/'kristal.workspace.json').is_file():
        raise ValueError('La cible doit être un Kristal local avec kristal.workspace.json')
    return target


def normalize_verdict(value: str | None) -> str:
    text = str(value or 'UNKNOWN').upper()
    return text if text in {status.value for status in EvidenceStatus} else 'UNKNOWN'
