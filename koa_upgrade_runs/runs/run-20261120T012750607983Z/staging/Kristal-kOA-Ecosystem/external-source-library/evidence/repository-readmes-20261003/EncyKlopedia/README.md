# EncyKlopedia (EncyK) — 0.12.0

EncyK is the ecosystem's **source discovery, acquisition, extraction and handoff pipeline**.

> **EncyK finds and prepares source evidence. It does not store the canonical library and it does not decide the final semantic meaning.**

## Responsibility

```text
external sources
      ↓
EncyK
  discover
  acquire
  scope
  extract losslessly
  prepare external identity candidates
      ↓
Médiathèque kOA
  persistent source authority
      ↓
IK → DaaT (optional integration path)
      ↓
Kristal / Kristall
  semantic authority
      ↓
Kompiler
  read-only context compilation
```

## Repository zones

```text
00_system      code, contracts, configuration, architecture docs
10_sources     seeds + acquisition inputs/caches
20_evidence    outgoing lossless evidence + Médiathèque handoffs
30_working     rebuildable indexes, discovery state and caches
90_runtime     temporary/runtime status, reports and recovery
```

There is deliberately no `40_kristal` and no `50_mediatheque` in the active architecture.

## Scope pipeline

```text
configured roots
   ↓
resolve source identities
   ↓
discover project scope
   ↓
freeze exact external entity IDs + project roles
   ↓
extract COMPLETE selected source records
   ↓
prepare source-qualified external identity candidates
   ↓
content-addressed Médiathèque handoff
```

The engine is scope-rooted and domain-neutral. Existing intellectual scopes happen to use people as roots; other scopes may use works, installations, processes or other local role/kind hints.

## Lossless evidence invariant

Selection rules decide **which source records enter the scope**. They do not decide which fields are discarded.

For Wikidata, an admitted entity is retained as complete source JSON including claims, literal values, statement IDs/ranks, qualifiers, references, labels, aliases, descriptions, external identifiers and sitelinks.

The global SQLite, optional project SQLite, entity vault and random-access locator are derived accelerators only.

## External identity candidates

`06_prepare_identity_candidates.py` emits source-qualified identity hints such as:

```text
wikidata:Q8018
```

These are **not** Kristal/Kristall semantic identities. They do not mint KQ/KP/KA/KS identifiers and they are not assertions. Their purpose is to preserve source identity and useful external IDs through the handoff.

## Source authority

EncyK no longer maintains a mini-Médiathèque.

The canonical handoff target is:

```text
Médiathèque kOA >= 0.2.0
koa.source-catalog/2.0.0
```

Médiathèque owns durable Source → Snapshot → Representation identity, hashes, rights/access facts and stable source locators. `20_evidence/` can be retained for retry/audit, but it is not a second canonical library.

## DaaT / Kristal / Kristall

**DaaT** is the human name; `daat` is the machine identifier. DaaT is an optional external IK↔Kristal admission/contract-mapping boundary. It is not an EncyK stage.

Current compatibility baseline:

- Interaction Kernel `2.0.0-dev.2`;
- portable Kristal contract `kristal_state/6.0` / Standard `6.0.0`;
- Kristal/Kristall `7.0.0-draft.3.2`.

EncyK does not vendor those contracts and does not write Kristal/Kristall artifacts.

## Kompiler

Kompiler `0.5.0` is downstream and read-only. It compiles context from knowledge read surfaces. It is not a source normalization/acquisition stage and EncyK does not call it as part of harvest.

## Active handoff contract

```text
encyk.source-evidence-handoff/2.0.0
```

See:

- `00_system/contracts/knowledge-baseline.json`
- `00_system/contracts/source-evidence-handoff/2.0.0/`
- `00_system/docs/architecture.md`
- `00_system/docs/ecosystem-boundaries.md`

## Main commands

Default pipeline:

```powershell
.\harvest.ps1 -Scope catholic-pilot
```

Force raw discovery/extraction when explicitly desired:

```powershell
.\harvest_raw.ps1 -Scope catholic-pilot
```

Use the global discovery index as an accelerator:

```powershell
.\harvest.ps1 -Scope catholic-pilot -DiscoveryBackend index
```

Optionally build a per-project query SQLite:

```powershell
.\harvest.ps1 -Scope catholic-pilot -BuildQueryIndex
```

GUI:

```text
run_scope_manager.pyw
```

## Authority summary

- source discovery/acquisition/extraction: **EncyK**;
- persistent source bytes/snapshots/representations: **Médiathèque kOA**;
- IK↔Kristal admission/mapping when used: **DaaT**;
- semantic identity and epistemic/crystallization artifacts: **Kristal/Kristall**;
- context compilation over knowledge read surfaces: **Kompiler**.
