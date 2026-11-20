# SemantiK Architect 1.3.0-alpha.2 — ecosystem-aligned articulation

SemantiK Architect is a deterministic semantic-to-human multilingual communication engine. The 1.3 alpha keeps the stable portable `kristal_state/6.0` articulation boundary, aligns it with Kristal/Kristall `7.0.0-draft.3.2`, and retains the first **mathematical communication profile**: MathKristal Formula IR is projected explicitly into the canonical semantic graph, planned as a mathematical articulation operation, and delegated to **Informath / MathCore / GF** for verbal realization.

## What 1.3 adds

- `MathKristalFormulaAcl` for `mathkristal.formula-ir` 1.0.0;
- full structural traceability from Formula IR nodes into the canonical semantic graph;
- `math-pure-1` and `math-natural-1` planning paths;
- `math.informalize_formula` as an additive realization operation;
- `InformathMathRealizer`, invoked through the existing `RealizerPort`;
- Formula IR → Dedukti projection and versioned Informath symbol registries;
- a candidate Euler profile and schemas/examples;
- Python SDK and CLI surfaces: `project-math` and `render-math`;
- no embedded French/English mathematical grammar and no hidden template fallback.

The profile remains **candidate-only** until a concrete Informath runtime is pinned, hashed, and passes language/profile conformance.

## Canonical pipeline

```text
external domain model / portable Kristal v6 projection / MathKristal Formula IR
        ↓ explicit ACL / communication projection
CommunicationRequest
        ↓
CommunicationPlanner
        ↓
CommunicationPlan
        ↓ lexical preflight
LanguagePlanner
        ↓
LanguagePlan / RealizationUnit
        ↓ exact lexical binding when required
RealizerPort
        ├─ generic language → versioned SA↔GF bridge → PGF/GF
        └─ mathematical language → Informath → MathCore/Informath → GF/RGL
        ↓
CommunicationResult + coverage + RuntimeSet identity
```

There is still one application pipeline. Only the realization adapter is specialized by an explicit operation/profile; no semantic or grammatical fallback is inferred at runtime.

## MathKristal integration

SemantiK Architect does not parse LaTeX to guess mathematics. It consumes a structure-first Formula IR through:

```text
semantik.mathkristal-formula-ir.communication-projection/1.0
```

The caller explicitly supplies the Formula IR and selects the expression/proposition to articulate. The ACL maps every relevant formula node to canonical graph nodes/statements, adds one explicit `present-formula` articulation anchor, and stores the original Formula IR as supporting context for the specialized realizer.

Example:

```bash
PYTHONPATH=src:. python -m semantik_architect.adapters.inbound.cli.main \
  --runtime-root runtime \
  project-math examples/mathkristal_euler_formula.json \
  --language fr --mode PURE
```

`PURE` targets the unique/verbose MathCore-style realization. `NATURAL` allows an admitted Informath runtime to request controlled variations. SemantiK never upgrades either rendering to mathematical truth.

See:

- [`docs/reference/MATHKRISTAL_FORMULA_IR_PROJECTION.md`](docs/reference/MATHKRISTAL_FORMULA_IR_PROJECTION.md)
- [`docs/reference/INFORMATH_MATH_REALIZATION.md`](docs/reference/INFORMATH_MATH_REALIZATION.md)
- [`profiles/math-pure-1/`](profiles/math-pure-1/)

## Kristal / Kristall integration

`KristalV6Acl` remains the stable portable articulation boundary: raw `kristal_state` is never interpreted as a communication request. The portable contract stays `kristal_state/6.0` / Standard `6.0.0`, while the current ecosystem design baseline is Kristal/Kristall `7.0.0-draft.3.2`.

Kristal/Kristall owns semantic identity, assertions, Mesh/axes/registries and crystallization. An upstream semantic owner or projection producer explicitly selects what is to be communicated; every selected assertion remains traceable through `source_refs`. **DaaT** (`daat`) may admit/map an external contract toward Kristal but does not decide communication obligations. **Kompiler** may assemble read-only context but cannot create truth, assertion identity or obligations.

MathKristal Formula IR can also be wrapped in the existing portable Kristal v6 communication projection when the corresponding proposition/assertion is present in an authoritative state or v7-derived v6 projection. See [`docs/reference/KRISTAL_KRISTALL_V7_ALIGNMENT.md`](docs/reference/KRISTAL_KRISTALL_V7_ALIGNMENT.md).

## Lexical and grammar authorities

The established authority split remains:

```text
Wikidata / Wikidata Lexeme → generic lexical knowledge
Domain/project terminology → explicit overrides
Informath symbol registry → formal-math ↔ GF concept bindings
GF/RGL → morphology, syntax, word order, agreement, final realization
SemantiK Architect → communication planning and articulation only
```

## Validation

```bash
PYTHONPATH=src:. python tools/validate_repository.py
```

Current snapshot validation is recorded in `VALIDATION_REPORT.md`.

## No hidden fallback

SemantiK Architect has **no hidden fallback** renderer, grammar, source parser, or semantic inference path. Missing capabilities remain explicit failures.

## Fail-closed invariant

Missing Formula IR structure, unmapped math symbols, unavailable Informath, unsupported language, invalid RuntimeSet identity, lexical gaps, or GF/Informath failures are explicit errors. SemantiK Architect does not silently substitute prose templates or change mathematical meaning.
