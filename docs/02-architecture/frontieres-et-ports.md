# Frontières de modules et contrats de ports

Les signatures suivantes sont **CIBLE** (architecture proposée), non des fonctions déjà importables du snapshot.

```python
from dataclasses import dataclass
from typing import Protocol, Iterable

@dataclass(frozen=True)
class WorkspaceRef:
    state_ref: str
    path: str
    display_name: str

@dataclass(frozen=True)
class RunRequest:
    workspace: WorkspaceRef
    engine: str
    profile: str
    mode: str = "read_only"

class InventoryPort(Protocol):
    def scan(self, roots: list[str]) -> Iterable[WorkspaceRef]: ...

class ExaminerPort(Protocol):
    def applicability(self, request: RunRequest) -> tuple[bool, str]: ...
    def run(self, request: RunRequest) -> dict: ...

class ObservationStore(Protocol):
    def append(self, observation: dict) -> str: ...
    def latest(self, state_ref: str, kind: str, profile: str) -> dict | None: ...
```

## Séparation obligatoire

| Responsable | Possède | N'a pas le droit de |
|---|---|---|
| `domain` | règles, invariants, erreurs stables | importer Tk, lancer subprocess, écrire SQLite |
| `application` | ordre des tâches, politique d'exécution | interpréter le schéma V9 en dur |
| `inventory adapter` | observation des workspaces | éditer des canons ou des PRF |
| `diagnostics adapter` | invocation autorisée, paramètres, preuves | transformer un exit 0 en qualification |
| `classifier` | propositions et leurs justifications | enregistrer `approved` automatiquement |
| `persistence` | transactions, clés, migrations | décider que tel ARK est correct |
| `gui` | sélection, filtres, progression, feedback | recalculer son propre verdict divergent |

## Contrats d'erreur

Exceptions transformées à la frontière en `INPUT_INVALID`, `ENGINE_MISSING`, `PROFILE_NOT_APPLICABLE`, `TIMEOUT`, `ENGINE_ERROR`, `STORAGE_UNAVAILABLE`, `SOURCE_CHANGED`, `CANCELLED`, chacune avec origine et cause facultative. Le client n'interprète pas des chaînes arbitraires venant de stdout.

## Politique d'écriture

Les commandes `scan`, `analyze`, `diagnose`, `search`, `import-history` sont non-canoniques. Un éventuel `apply_patch` futur nécessite un autre port, un plan de modifications, des sauvegardes, une approbation et une vérification Kit; jamais un simple changement d'état de `ObservationStore`.
