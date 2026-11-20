# LevelUpDiag for SemantiK Architect v1

**Profile version:** 2.3.0  
**Target:** `C:\mycode\SemantiK_Architect\SemantiK_Architect`  
**Mode:** read-oriented external-target diagnostics  
**Dependency policy:** standard-library diagnostic core; target tooling is invoked only when explicitly required by the profile

This LevelUpDiag profile is aligned with the clean SemantiK Architect v1 architecture through `1.3.0-alpha.2`, including the portable Kristal v6 communication boundary under the Kristal/Kristall `7.0.0-draft.3.2` ecosystem baseline and the MathKristal/Informath contract surface.
It diagnoses **SA itself** as a deterministic semantic-to-human communication engine whose
canonical pipeline is:

```text
CommunicationRequest
  -> CommunicationPlanner
  -> CommunicationPlan
  -> lexical preflight
  -> LanguagePlanner
  -> LanguagePlan / RealizationUnit
  -> exact lexical binding
  -> versioned SA↔GF bridge
  -> PGF/GF
  -> CommunicationResult + coverage + RuntimeSet identity
```

The profile does not expect an `app/` tree, FastAPI, a frontend, a single hard-coded PGF,
`requirements.txt`, family grammar engines, or grammar-development code inside SA.

## Run

From this LevelUpDiag directory:

```bat
RUN_SEMANTIK_ARCHITECT_DIAG.bat semantik
RUN_SEMANTIK_ARCHITECT_DIAG.bat standard
```

Or directly:

```bat
python levelupdiag.py doctor
python levelupdiag.py run semantik
python levelupdiag.py run standard
python levelupdiag.py run deep --jobs 1
```

Evidence is written under the target repository:

```text
.levelupdiag/runs/<run-id>/
```

## Campaigns

- `baseline`: generic repository evidence only.
- `semantik`: SA v1 architecture/contracts/runtime-model diagnostics without executing the full target validator.
- `standard`: recommended campaign; adds the target's canonical `tools/validate_repository.py` validation.
- `deep`: adversarial campaign; adds declared validators plus S90–S120 mutation, fail-closed, determinism/concurrency and isolated packaging probes.

## SemantiK-specific levels

| ID | Diagnostic domain |
|---|---|
| S10 | Architecture Lock — required locks/schemas/source tree and one canonical architecture |
| S20 | Python Architecture Integrity — syntax/imports, hexagonal dependency direction, PGF confinement, no language-code branches |
| S30 | Contract & Schema Integrity — all active schemas/examples plus executable Kristal portable-v6 traceability/non-inference and v7-baseline verification |
| S40 | RuntimeSet & Capability Model — composed immutable runtime manifests, hashes and release validation when deployed |
| S50 | SA↔GF Contract — operation registry, strict bridge consumption and optional PGF-binding readiness |
| S60 | Faithfulness & Planning Invariants — semantic→communication→language probe and exact obligation/reference coverage |
| S70 | Public SDK / CLI / HTTP Surface — importable package, warning-free CLI module execution, and stable public entry points without starting a server |
| S80 | Canonical Validation & Conformance — executes the target repository's own validator in `standard`/`deep` |
| S90 | Adversarial Semantic Invariants — malformed obligations, missing semantics, impossible constraints, deadlines, polarity and operation matrix |
| S100 | RuntimeSet Mutation — hash tampering, failed evidence, missing profiles, ambiguous activation and SA-version mismatch |
| S110 | Bridge & Lexical Adversarial — unconsumed slots/features, contract mismatch, missing concrete grammar and exact-lexeme failures |
| S120 | Determinism & Packaging — repeated/parallel render equality plus wheel build/install/import from a temporary clean copy |

## Runtime semantics

A missing deployed RuntimeSet is a `WARN`, not a source-code failure. SA may be fully valid as
an engine while no real language/profile artifact is present in the checkout.

If a RuntimeSet **is** deployed, LevelUpDiag validates its pinned artifacts and invokes SA's
public runtime release validator. A missing `pgf` Python binding is then `BLOCKED` for
real-language acceptance. If no RuntimeSet is deployed, missing `pgf` is only a `WARN`.

## Python environments / WSL

Target probes run with the target `src` directory on `PYTHONPATH`, so editable installation is
not required for diagnostics. To use WSL from a Windows LevelUpDiag UI, override locally:

```json
{
  "semantik": {
    "python_execution": "wsl",
    "wsl_distro": "Debian",
    "python_executable": "/path/to/python"
  }
}
```

No dependency installation, GF compilation, server startup, or target mutation is performed by
these SemantiK-specific levels.

## Windows UI

`RUN_LEVELUPDIAG_UI.vbs` remains the no-console launcher. The UI reads campaigns from
`levelupdiag_manifest.json`, so it automatically exposes the updated v1 profile.

See `docs/SEMANTIK_ARCHITECT_PROFILE.md` for the exact diagnostic contract.

## Deep adversarial campaign

`deep` is intentionally more expensive than `standard`. It creates all mutation fixtures only in temporary directories and never patches the target checkout. It is intended for pre-release bug hunting and should be run sequentially (`--jobs 1`) when investigating order/state issues.
