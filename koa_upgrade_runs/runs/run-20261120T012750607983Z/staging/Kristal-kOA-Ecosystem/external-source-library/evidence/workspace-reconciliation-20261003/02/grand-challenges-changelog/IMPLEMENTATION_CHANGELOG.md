# Implementation changelog — Challenge dynamics

Each of the 12 Challenges now has initialized research-dynamics state:

- `kristal/research/research-graph.json`;
- `kristal/research/active-frontier.json`;
- `kristal/research/frames.json`;
- `kristal/research/attempts.jsonl`;
- `kristal/research/agent-contributions.jsonl`;
- `kristal/research/strategy-observations.jsonl`.

The Challenge manifest points to these surfaces. The repository includes JSON Schemas for the ResearchGraph, active frontier and strategy observations, and the validator checks the two structured graph artifacts in addition to the v6 Challenge Kristal state and pinned MathKristal snapshot.

## v6 — Formulator Console compatibility

No research-data contract was broken. Added operator-console guidance and explicit compatibility with Formulator v5 `DO ALL` / portfolio orchestration. Challenge Kristal v6 files remain the persistent source of research state.

## 2026-10-02 — 3-problem data pump

- Enriched BSD to 27 curated known records, 6 frames, 6 new proof/research obligations, 3 candidate hypotheses.
- Enriched Tate to 25 curated known records, 6 frames, 6 new obligations, 3 candidate hypotheses.
- Enriched Langlands functoriality to 24 curated known records, 6 frames, 6 new obligations, 3 candidate hypotheses.
- Added current 2026 results (Burungale–Tian rank-zero p-converse; Newton–Thorne Hilbert symmetric powers).
- Added BSD LMFDB rank 0/1/2 regression calculations.
- Rebuilt all three local Kristal v6 states from the pinned MathKristal snapshot.

## Coverage-first / BSD Ring — 2026-10-03

- ajout de la méthode générique `Coverage Circuit` ;
- séparation stricte carte stratégique / vérité Kristal ;
- BSD reçoit une boucle de 9 carrefours, des gaps et des satellites ;
- phase actuelle : couverture avant optimisation ;
- validation automatique du circuit lorsqu'un Challenge active `coverage_first`.
