# SemantiK Runtime Orchestrator 1.2.0

Independent fail-closed release orchestrator for SemantiK Architect RuntimeSets. Version 1.2.0 is aligned with **SemantiK Architect 1.3.0-alpha.2** and remains deliberately outside all source/knowledge/context semantic authority boundaries.

The orchestrator owns release coordination only:

```text
GF / Wordbench artifacts
  -> SA conformance + validation
  -> diagnostics/evidence
  -> transactional promotion / rollback
  -> RuntimeSet activation
```

The current ecosystem baseline is Kristal/Kristall `7.0.0-draft.3.2` with portable `kristal_state/6.0`, but those are **communication-input** semantics handled upstream by SemantiK Architect ACLs. This repository does not import Kristal/Kristall, DaaT/Interaction Kernel, Kompiler, EncyK, Médiathèque, Orgo, LevelUpDiag, GF Wordbench, or SemantiK Architect internals.

**DaaT** (`daat`) may exist in an upstream interaction path toward Kristal, but it has no role in RuntimeSet promotion. **Kompiler** context assembly likewise has no role in release validity. Runtime release decisions are based only on immutable grammar/runtime artifacts, conformance evidence, diagnostics and configured deployment gates.

Existing `sa_version_range = ">=1.0,<2.0"` remains compatible with SemantiK Architect 1.3 alpha.

After a real `Konstellation.pgf` has been compiled in the SemantiK Architect profile-3 directory, `examples/konstellation-fr-3.json` can be used with the direct prebuilt-PGF path. Production release gates remain fail-closed.

Run:

```bash
python -m pytest -q
```
