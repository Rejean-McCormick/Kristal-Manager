# Formulator

**Formulator is the active research, calculation, validation and proof-generation engine around MathKristal.** It consumes a Challenge, its local Kristal v6 research memory, and a pinned read-only MathKristal snapshot.

```text
Challenge docs + Challenge Kristal v6 + MathKristal global (read-only)
                              |
                         Formulator
                              |
       plan / falsify / research / calculate / verify
                              |
                         ProofBundle
```

## Operator console

The recommended entry point is now the local console:

```bash
PYTHONPATH=src python -m formulator console \
  --challenges-root /path/to/Kristal-Grand-Challenges/challenges \
  --kristal /path/to/Kristal-Math \
  --workspace ./workspace
```

Then use the first tab and press **DO ALL**.

The console exposes Overview, Research, Knowledge, **ChatGPT Relay**, Verification, Logs and Settings. `DO ALL` runs every deterministic stage automatically, prepares the seven antagonistic research prompts, and places them in a clipboard-mediated queue: **Copy prompt → ChatGPT → Paste & Process**. No AI API or provider command is required.

For adjacent extracted repositories, the convenience launchers are:

```bash
./launch-console.sh /path/to/challenges /path/to/Kristal-Math ./workspace
```

or `launch-console.bat` on Windows.

See [`docs/09_OPERATOR_CONSOLE.md`](docs/09_OPERATOR_CONSOLE.md).

### One-click diagnostics

Use **Copy diagnostic** in the top bar whenever you want to send the current state to ChatGPT. Formulator creates a timestamped bundle under `workspace/diagnostics/`, groups runs under `batches/`, runs its self-test suite under `tests/`, and places the compact `CHATGPT.txt` report directly in the clipboard. See [`docs/10_DIAGNOSTIC_BUNDLES.md`](docs/10_DIAGNOSTIC_BUNDLES.md).

## One-click CLI

The exact same orchestration is available without the UI:

```bash
PYTHONPATH=src python -m formulator do-all \
  --challenge /path/to/challenges/riemann-hypothesis \
  --challenges-root /path/to/challenges \
  --kristal /path/to/Kristal-Math \
  --workspace ./workspace
```

The CLI stops at `awaiting_ai` when a ChatGPT relay batch is ready. The operator console is the intended interface for processing those prompts. Formulator never treats an unprocessed prompt or a ChatGPT answer as proof.

## MathKristal integration

Formulator uses the native MathKristal surfaces: referents/assertions, `reverse-index`, `proof-closure`, research/formal profiles, Formula IR, MMT/OpenMath and provenance. It does not silently convert the global corpus or write to it.

When MathKristal ActionPaths surfaces are present, Formulator also consumes them read-only:

- `runtime/actions/application-signatures.json` — planning-eligible local proof/refutation actions;
- `runtime/paths/paths.json` and `shortcuts.json` — certified compact routes;
- `runtime/paths/theorem-cards.json` — source-located theorem summaries and key proof points;
- `runtime/paths/branch-atlas.json` — long certified branches;
- `runtime/paths/flags.json` — non-canonical exploration landmarks only.

The active frontier matches actions through their premise/conclusion interface rather than broad domain labels, so a generic node such as `number_theory` does not pull every theorem in that domain into a BSD prompt. Relay prompts are role-budgeted and self-contained: a fresh ChatGPT conversation receives the useful local actions/routes without a blind dump of the whole graph.

The preflight remains available independently:

```bash
PYTHONPATH=src python -m formulator preflight \
  --challenge /path/to/challenge \
  --kristal /path/to/Kristal-Math
```

## Research dynamics

The executable engine keeps three distinct memories:

- **KnowledgeGraph** — bounded, read-only view of MathKristal around the current obligation;
- **ResearchGraph** — persistent per-Challenge objectives, hypotheses, obligations, attempts and results;
- **StrategyGraph** — cross-Challenge procedural memory of which research methods tend to work.

It implements information-per-cost planning, semantic-loss penalties, counterexample-first execution, bridge discovery, frame scoring, hypothesis compression, seven antagonistic agent roles, append-only attempt/failure memory, cross-Challenge transfer candidates and explicit freezing of externally validated results.

Finite tests, agent output, bridge candidates and strategy statistics are never treated as mathematical proof.

## Documentation

- [`docs/01_INPUT_CONTRACT.md`](docs/01_INPUT_CONTRACT.md)
- [`docs/02_PIPELINE.md`](docs/02_PIPELINE.md)
- [`docs/03_PROOF_MODEL.md`](docs/03_PROOF_MODEL.md)
- [`docs/04_VERIFIER_ADAPTERS.md`](docs/04_VERIFIER_ADAPTERS.md)
- [`docs/05_OUTPUTS_AND_LOGS.md`](docs/05_OUTPUTS_AND_LOGS.md)
- [`docs/06_IMPLEMENTATION_MVP.md`](docs/06_IMPLEMENTATION_MVP.md)
- [`docs/07_MATHKRISTAL_INTEGRATION.md`](docs/07_MATHKRISTAL_INTEGRATION.md)
- [`docs/08_RESEARCH_DYNAMICS.md`](docs/08_RESEARCH_DYNAMICS.md)
- [`docs/09_OPERATOR_CONSOLE.md`](docs/09_OPERATOR_CONSOLE.md)
