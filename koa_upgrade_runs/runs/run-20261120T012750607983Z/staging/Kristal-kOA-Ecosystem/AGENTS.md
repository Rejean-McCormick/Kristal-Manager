# AGENTS.md — Kristal kOA Ecosystem

This workspace follows **Kristal Local Kit 3.2.2**. The normalization is additive: do not rewrite the existing semantic graph merely to fit the workspace layout.

Before changing canonical knowledge:

1. treat `knowledge-base/corpus/koa-ecosystem.kristal-state.json` as the registered canonical artifact;
2. preserve existing Semantic IDs, assertion IDs, evidence references, epistemic categories and authority boundaries;
3. use the editorial catalogs under `knowledge-base/sources/` and their documented build rules rather than hand-editing generated views;
4. keep `repository != authority`, `hosting != ownership`, `scenario != deployment`, `projection != canon`;
5. do not infer missing Git remotes, activation, membership or runtime deployment from names or local presence;
6. treat AI/model output as proposal-only unless explicitly reviewed and accepted into the canon;
7. keep build, materialization, backup, hosting, publication and activation separate from semantic identity.

## Validation order

```text
python knowledge-base/tools/validate.py
python tools/kristal.py check .
python tools/kristal.py build-v9 .
```

The legacy `.kristal/v9/` envelope is retained for compatibility/evidence. New Local Kit builds are written to `build/v9/`. Do not edit either generated build surface to change domain truth.

Publication or activation must never be implicit.
