from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any
from . import REPORT_SCHEMA, VERSION

@dataclass(slots=True)
class Finding:
    id: str
    verdict: str
    category: str
    message: str
    path: str | None = None
    evidence: Any = None
    expected: Any = None
    observed: Any = None
    standard_ref: str | None = None
    impact: str | None = None
    remediation: str | None = None
    def to_dict(self):
        return {k:v for k,v in asdict(self).items() if v is not None}

@dataclass(slots=True)
class Artifact:
    kind: str
    path: str
    description: str | None = None
    data: dict[str, Any] | None = None
    def to_dict(self): return {k:v for k,v in asdict(self).items() if v is not None}

@dataclass(slots=True)
class LevelResult:
    level: str
    name: str
    verdict: str
    findings: list[Finding] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    started_at: str = ''
    ended_at: str = ''
    duration_seconds: float = 0.0
    metadata: dict[str,Any] = field(default_factory=dict)
    def to_dict(self, *, run_id:str, target_root:str, profile:str|None=None):
        return {
            'schema': REPORT_SCHEMA,
            'standard': 'KristalDiag',
            'standard_version': VERSION,
            'run_id': run_id,
            'profile': profile,
            'level_id': self.level,
            'level_name': self.name,
            'target_root': target_root,
            'started_at': self.started_at,
            'ended_at': self.ended_at,
            'duration_seconds': round(self.duration_seconds,6),
            'verdict': self.verdict,
            'findings': [f.to_dict() for f in self.findings],
            'artifacts': [a.to_dict() for a in self.artifacts],
            'metadata': self.metadata,
        }
