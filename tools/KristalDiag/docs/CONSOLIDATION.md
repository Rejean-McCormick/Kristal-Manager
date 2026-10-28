# LevelUpDiag → KristalDiag v7 consolidation

`levelupdiag_kristal` 0.6.0 and KristalDiag 0.2.0 overlapped. The v7 line consolidates them into one product: **KristalDiag**.

## What was retained

From LevelUpDiag:

- external/read-oriented harness model;
- neutral repository diagnostics;
- bounded inventory and security hygiene;
- declared validators instead of guessed commands;
- campaign selection (`baseline`, `standard`, `deep`);
- per-level timeouts;
- dependency-aware bounded parallel scheduling;
- process isolation per level;
- fail-fast option;
- output redaction;
- release-engineering diagnostics.

From KristalDiag:

- Kristal v7 conformance profiles;
- v6 portable-state compatibility checks;
- RFC8785/JCS vectors;
- KQ/KP/KA/KS, assertion families, Mesh, axes, Surfaces, projection and resonance checks;
- explicit interoperability evidence;
- offline-verifiable evidence trees;
- fail-closed profile gating;
- full-target read-only fingerprinting;
- `qualification_only=true` / `authority_granted=false` boundary.

## Unified level space

| Range | Meaning |
|---|---|
| `N00–N06` | neutral harness/repository diagnostics |
| `K00–K14` | Kristal v7 semantic conformance and profile gate |
| `R00–R04` | release engineering / ratification evidence |

`V7-*` profiles use neutral + semantic levels. Release levels do **not** redefine semantic conformance.

## Campaign mapping

| Previous LevelUpDiag | KristalDiag v7 |
|---|---|
| `run baseline` | `kristaldiag run baseline TARGET` |
| `run standard` | `kristaldiag run standard TARGET` |
| `run deep` | `kristaldiag run deep TARGET` |
| deep release qualification | `kristaldiag run release TARGET` |
| v6 K30–K35 | primarily K02/K04/K09 plus driver hooks |
| v5 K10–K24 | historical; reusable release concerns moved to R00–R04 or v7 K-levels |

A compatibility `levelupdiag.py` shim is shipped for common legacy commands.

## Execution policy

Target code is never guessed or imported. N05 only runs commands explicitly declared in `kristaldiag.config.json`, and only with `--allow-exec`. Kristal implementation hooks remain declared through `kristaldiag-driver.json`.

Each selected N/K/R level runs in a fresh process by default. Unit tests may opt into in-process execution, but packaged self-tests exercise process isolation.
