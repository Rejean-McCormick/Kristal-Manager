# GF RGL AI Compendium

A source-grounded instruction system for AI-assisted development, extension, repair, testing, review, and upstream delivery of **Grammatical Framework Resource Grammar Library languages**.

This Compendium is a **documentation, retrieval, and governance reference package**. It is not an autonomous program: it contains no executable generator suite, compiler integration, network service, or automatic patch producer.

This compendium is exclusively for **RGL language engineering**. It does not cover application grammars, domain grammars, translation applications, or general beginner instruction.

## Purpose

The compendium enables an AI to work on an RGL language without relying on memory, surface analogy, or uncontrolled copying from another language.

It combines:

- exact GF and RGL contracts;
- target-language linguistic evidence;
- architecture-aware model-language comparison;
- reusable engineering patterns;
- deterministic development and repair workflows;
- compiler and test evidence when available;
- explicit maturity, provenance, and release gates.

The intended result is not merely code that compiles. The result must preserve the target language’s grammatical distinctions, fit the RGL abstraction, remain maintainable, and be suitable for expert review and eventual upstream contribution.

## Current package status

```yaml
status: source_grounded_provisional
release_ready: false

patterns:
  expected: 56
  present: 56

language_profiles:
  expected: 15
  present: 15

evidence:
  total_records: 181
  accepted_records: 179
  quarantined_records: 2

catalog_reconciliation:
  catalog_evidence_count_sum: 179
  catalog_anchor_mismatches: 0
  catalog_json_csv_mismatches: 0

internal_validation:
  structured_syntax: pass
  language_template_schema_checks: pass
  broken_markdown_links: 0

external_validation:
  gf_compiler_available: false
  compiler_validation: not_run
  executable_regression_validation: not_run
  complete_linguistic_expert_validation: not_run
```

Two evidence records remain in the ledger but are excluded from accepted-evidence
counts:

- `EA-EP021-003`: the cited Romanian field does not establish the grammatical
  polarity behavior required by EP021;
- `EA-EP045-003`: the cited Maltese range does not directly establish the
  decomposition required by EP045.

Internal consistency has been reconciled. Exact source-locator revalidation,
independent Git-object reconstruction of the recorded RGL commit, GF compilation,
executable regressions, and complete linguistic expert validation remain external
checks and must not be inferred from internal document consistency.

## Start here

Every task starts with:

```text
00_MASTER_ROUTER.md
```

The router determines the smallest relevant context for the task and prevents the AI from loading unrelated documentation.

Do not begin implementation by browsing model-language code directly.

Before writing code, the AI must resolve:

1. the exact RGL source and compiler version;
2. the exact abstract signature;
3. the target module and category contracts;
4. the target language’s accepted architecture;
5. inherited or shared implementations;
6. relevant linguistic evidence;
7. the required tests and completion gate.

## Scope

### Included

- creating a new RGL language;
- extending or completing an existing RGL language;
- designing `Cat`, resource, morphology, and paradigm modules;
- implementing concrete syntax modules;
- implementing `Extend`, `Extra`, and explicit `Missing` coverage;
- designing and reviewing family functors;
- selecting architecture-compatible model languages;
- repairing compiler failures;
- repairing incorrect linguistic output;
- designing morphology and syntax regression tests;
- evaluating implementation maturity;
- documenting decisions and unresolved questions;
- preparing an upstream-quality contribution.

### Excluded

- application grammars;
- domain-specific abstract syntaxes;
- ordinary use of `SyntaxX` to build applications;
- PGF application integration;
- translation-system design;
- beginner GF tutorials;
- generic linguistic descriptions that do not affect RGL implementation;
- copied source listings without an active engineering purpose.

See `01_SCOPE_RGL_ONLY.md` for the normative boundary.

## Core operating principle

```text
evidence
→ architecture
→ category contracts
→ implementation plan
→ minimal code
→ compiler evidence
→ linguistic tests
→ reconciled documentation
```

Code is never the first durable artifact.

The AI must document the decision boundary before implementing the corresponding representation or constructor.

## Authority order

When sources disagree, use this order:

1. exact abstract signatures from the locked RGL version;
2. compiler results and reproducible tests;
3. current target-language source;
4. inherited functor and shared-resource source;
5. accepted target-language decisions;
6. language-specific linguistic evidence;
7. architecture-compatible model-language evidence;
8. generated engineering-pattern guidance;
9. comments, historical notes, and unfinished implementations.

No generated compendium file outranks exact source or compiler evidence.

See `02_AUTHORITY_AND_PROVENANCE.md`.

## Repository map

```text
GF_RGL_AI_CODEX/
├── 00_MASTER_ROUTER.md
├── 01_SCOPE_RGL_ONLY.md
├── 02_AUTHORITY_AND_PROVENANCE.md
├── 03_CONTEXT_AND_NOISE_POLICY.md
├── 04_DEVELOPMENT_STATE_MACHINE.md
├── contracts/
├── engineering_patterns/
├── workflows/
├── diagnostics/
├── testing/
├── protocols/
├── language_template/
├── schemas/
└── tools/
```

### `contracts/`

Version-locked or version-associated descriptions of the RGL API and source structure. Some indexes are generated from documentation and remain provisional until checked against exact source:

- abstract signatures;
- category obligations;
- module ownership;
- producer and consumer relations;
- inheritance and functor structure;
- paradigm APIs;
- language capability coverage;
- lock-field and record-retyping constraints.

See `contracts/CONTRACT_PROVENANCE.md` for the authority and verification status of each contract family.

These files answer: **What does the RGL require, and where does each responsibility belong?**

### `engineering_patterns/`

Professional engineering patterns extracted from mature and informative RGL implementations.

These files answer: **How have experienced GF developers preserved information, controlled realization, organized morphology, reused families, and avoided architectural dead ends?**

A model language is selected by representation compatibility and subsystem maturity, not by genealogical proximity alone.

### `workflows/`

Deterministic procedures for:

- new-language development;
- extending an existing language;
- morphology development;
- category and resource design;
- syntax implementation;
- family reuse;
- `Extend`, `Extra`, and `Missing`;
- compilation;
- compiler repair;
- linguistic-output repair;
- upstream delivery.

Workflow files coordinate other parts of the compendium. They must not duplicate contracts or pattern explanations.

### `diagnostics/`

Machine-readable and procedural guidance for classifying:

- GF compiler errors;
- module and path errors;
- type and record mismatches;
- overload and inheritance failures;
- linguistic realization failures;
- complexity and compilation-growth problems.

Diagnostics identify the likely subsystem and route the AI to the appropriate workflow.

### `testing/`

Normative requirements for:

- morphology tables;
- lexical constructors;
- category construction;
- syntax constructors;
- feature interactions;
- clitics, agreement, government, order, polarity, and register;
- parse and linearization checks;
- regression suites;
- release readiness.

Compilation alone is never sufficient evidence of correctness.

### `protocols/`

Mandatory governance for AI-generated changes:

- proof-carrying patch records;
- independent AI or human review;
- synchronization of code, evidence, decisions, contracts, and tests.

Code returned without its evidence, assumptions, and tests is incomplete.

### `language_template/`

The standard document-first pack for every target language.

A language pack contains only target-language material:

- source lock;
- linguistic and architectural profile;
- morphology and syntax plans;
- atomic evidence;
- accepted decisions;
- open questions;
- implementation status;
- golden morphology and syntax data;
- executable regressions;
- generated coverage and compiler reports.

Universal GF and RGL explanations must not be repeated inside language packs.

### `schemas/`

Schemas for stable machine-readable records, including:

- language manifests;
- category contracts;
- evidence;
- decisions;
- tests;
- patches;
- maturity classifications;
- implementation-status records.

### `tools/`

Specifications for generating contracts, validating the compendium, checking evidence freshness, and recording generation provenance.

The directory is documentary: no executable generator suite is included. Existing generated files are reference snapshots whose internal consistency can be checked, but complete reproducible regeneration is not claimed by this package.

## AI retrieval policy

The AI should load the smallest sufficient context.

For an implementation or repair task, the default retrieval set is:

1. one workflow;
2. the exact abstract signature;
3. the relevant target-language category contracts;
4. the relevant language decisions and evidence;
5. the inherited implementation, when present;
6. no more than three engineering-pattern records;
7. the required tests.

The AI must not load complete model-language directories unless architecture selection or unresolved source analysis requires them.

See `03_CONTEXT_AND_NOISE_POLICY.md`.

## Development states

A target language progresses through controlled states:

```text
unexamined
→ evidence_collected
→ architecture_selected
→ contracts_defined
→ morphology_implemented
→ core_syntax_implemented
→ extensions_implemented
→ regression_validated
→ release_candidate
→ upstream_ready
```

An AI may work incrementally, but it must not claim a later state without satisfying the corresponding gate.

See `04_DEVELOPMENT_STATE_MACHINE.md`.

## Required language-pack entry point

Every language pack begins with:

```text
language_template/MANIFEST.yaml
```

The manifest identifies:

- authoritative files;
- target source and compiler versions;
- current development state;
- generated artifacts;
- unresolved blockers;
- the correct workflow for the next task.

The AI must read the manifest before any language-specific document.

## Required patch envelope

Every code change must be accompanied by a structured record containing at least:

```yaml
function: ...
abstract_type: ...
target_module: ...
source_version: ...
selected_patterns: [...]
evidence: [...]
fields_preserved: [...]
fields_changed: [...]
assumptions: [...]
rejected_alternatives: [...]
tests: [...]
compiler_result: ...
```

See `protocols/AI_PATCH_PROTOCOL.md`.

## Evidence and maturity

Model-language source is not automatically a validated model.

Evidence is classified at subsystem level:

- `validated_model`
- `pattern_evidence`
- `negative_evidence`
- `unavailable_context`

A mature morphology subsystem does not automatically validate the language’s clause architecture. A TODO-marked implementation may still provide useful pattern evidence, but it must not be copied as an authoritative design.

All evidence records should identify:

- source path;
- exact line or symbol;
- source revision or archive hash;
- relevant subsystem;
- maturity classification;
- interpretation;
- limitations.

## Generated versus authored files

The distinction below defines intended ownership and maintenance. It does not mean that this package currently contains executable generators.

### Intended generated artifacts

- abstract-signature indexes;
- module ownership;
- producer and consumer indexes;
- inheritance graphs;
- paradigm overload inventories;
- function and module coverage;
- compiler results;
- test results;
- stale-evidence reports;
- symbol indexes.

### Author deliberately

- scope and authority policy;
- workflows;
- architecture decisions;
- evidence interpretation;
- morphology and syntax plans;
- open questions;
- test intent;
- release decisions.

Do not maintain generated inventories manually when an authoritative generation process is available. Until reproducible generators and locked source artifacts are available together, generated files must retain explicit provenance and provisional status.

## Quality standard

A language or patch is not complete because one module compiles.

Completion requires evidence appropriate to the change, which may include:

- exact signature and category-contract verification;
- target-language evidence;
- architecture compatibility;
- minimal and localized implementation;
- successful minimal-module compilation;
- successful complete-language compilation;
- morphology and constructor tests;
- interaction tests;
- regression tests;
- explicit unsupported-function coverage;
- synchronized documentation;
- no undisclosed assumptions.

The normative completion criteria are defined in `testing/RELEASE_GATE.yaml`.

## Source corpus

The compendium is built from:

- the GF language and shell references;
- generated RGL API signatures, modules, types, and paradigm documentation;
- direct source analysis of multiple RGL languages and shared family implementations;
- language-specific evidence packs;
- compiler and test evidence when available.

The distributed package records the identities and hashes of canonical external artifacts such as `src.zip` and `doc.zip`, but does not embed those archives. `GFCompendium(31).txt` is supplementary documentation and never outranks exact locked source.

The current model-language corpus includes structurally diverse implementations such as Italian, German, Bulgarian, Romanian, Greek, Croatian, Macedonian, Finnish, Estonian, Japanese, Chinese, Hindi, Urdu, the shared Scandinavian implementation, Arabic, and Maltese.

These languages are evidence sources, not templates to be copied wholesale.

## Status convention

Each file should declare one of these statuses where relevant:

- `normative`
- `generated`
- `evidence_anchored`
- `provisional`
- `deprecated`

Generated files must include source and generator provenance. Provisional files must identify the condition required for promotion.

The reconciled package as a whole currently has status `source_grounded_provisional`. No compiler-, regression-, linguistic-, release-, or upstream-ready status may be inferred from internal document consistency alone.

## Validation boundaries

The following statements are established for the reconciled documentation
snapshot:

- all intended 56 pattern files and 15 language profiles are present;
- the accepted evidence ledger and both pattern catalogs reconcile;
- the JSON and CSV catalogs agree;
- the language-template artifacts pass their current authoritative schemas;
- internal Markdown links resolve;
- the `AdV` category contract records 3 producers and 7 consumers, derived from
  `contracts/PRODUCER_CONSUMER_INDEX.jsonl`.

The following statements are **not** established by this package:

- that every evidence locator still matches the separately stored canonical source;
- that the recorded RGL commit was independently reconstructed from Git objects;
- that any target language or patch compiles;
- that executable regressions pass;
- that linguistic behavior has received complete expert validation;
- that the documented generators can reproduce every artifact.

These are accepted limitations, not silent successes or parse failures.

## Design objective

The compendium is successful when an AI can:

1. discover the exact RGL obligation;
2. select an architecture from target-language evidence;
3. preserve all information required by downstream syntax;
4. implement the smallest justified change;
5. diagnose failures deterministically;
6. prove behavior through compilation and linguistic tests;
7. keep documentation synchronized with code;
8. produce a contribution that a GF maintainer can review efficiently.

The compendium should remain compact, versioned, generated where possible, and explicit where expert judgment is required.
