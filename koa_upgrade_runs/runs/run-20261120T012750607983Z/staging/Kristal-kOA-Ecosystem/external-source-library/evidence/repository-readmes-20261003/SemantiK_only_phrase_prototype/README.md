# SemantiK-only phrase prototype

Purpose: test `konstellation-explorer-3` / `konstellation-fr-3` without passing the current complete prose position as a realization slot.

The profile uses typed GF expressions (`NP`, `V2`, `ClassNP`) through SemantiK Architect's existing `gf_expr` lexical binding path. The current complete `position.text` strings are excluded from input artifacts and checked by `audit_no_phrase_leak.py`.

## Contents

- `semantic-seeds.json`: five structured prototype seeds with corpus provenance.
- `profile/`: candidate SA/GF profile 3 (GF sources, bridge, lexicon, profile, conformance suite).
- `requests/`: generated CommunicationRequests.
- `scripts/`: request builder, provenance/leak audits, schema validation, SA expression-level runner and conformance runner.
- `output/`: test results and conformance evidence from this environment.
- `runtime-orchestrator.konstellation-fr-3.template.json`: direct-PGF release template for Runtime Orchestrator 1.1.1.
- `PROTOTYPE_REPORT.md`: findings and next gate.

## Important limitation

No GF compiler or Python `pgf` binding is installed in the execution environment used to build this prototype, and no real `Konstellation.pgf` was present in the supplied snapshots. The final PGF linearization was therefore represented by a deterministic test fixture. All SemantiK Architect planning, lexical binding, bridge, output and coverage logic is real repository code.

For a real RuntimeSet, compile the profile with the normal GF toolchain (`gf -make KonstellationFre.gf`) and release the resulting PGF through SemantiK Runtime Orchestrator.
