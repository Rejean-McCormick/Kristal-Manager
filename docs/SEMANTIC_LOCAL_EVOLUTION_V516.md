# Local semantic evolution V5.16: one local-first operation

V5.16 materializes a useful **active semantic reading projection** *inside each
local Kristal*, under `derived/semantic/`, instead of asking its operator to
resolve every historical revision before any usable dictionary is available.

The v11 `authoring.json` profile is the existing local owner's selection of
registry, graph, crosswalk and catalog. This operation **reads that selection**;
it does not choose a revision by date or filename and does not change the
profile. The V5.14 historical observatory remains a separate, complete view.

## One-shot operation (PowerShell 7)

The accompanying multi-repository overlay installer installs code, runs its
focused regression tests, and executes the local evolution in one `-Apply` call.
Direct invocation after installation is also supported:

```powershell
$env:PYTHONPATH = 'C:\mycode\Kristal\Kristal-Manager'
$private = Join-Path $env:LOCALAPPDATA 'Kristal'
New-Item -ItemType Directory -Force -Path $private | Out-Null
python -m kristal_manager.local_semantic_evolution_v516 `
  --locals 'C:\mycode\Kristal\locals' --private-dir $private --apply
```

Read one meaning without rebuilding the index:

```powershell
python -m kristal_manager.local_semantic_evolution_v516 `
  --locals 'C:\mycode\Kristal\locals' --lookup 'KQ1001'
python -m kristal_manager.local_semantic_evolution_v516 `
  --locals 'C:\mycode\Kristal\locals' --lookup 'Q42'
python -m kristal_manager.local_semantic_evolution_v516 `
  --locals 'C:\mycode\Kristal\locals' --lookup 'étoile'
```

All lookup results include `(namespace_id, semantic_id)` and the owning local
workspace. Equal words in a language are not merged into a single meaning.

## Actual local write set

- Immutable content-addressed projection:
  `derived/semantic/v516/active-<sha256-prefix>.json`.
- Local active projection pointer:
  `derived/semantic/active-resolution.json`.
- Complete private V5.14 integrity evidence, V5.16 run report, and copies of
  any old managed pointers under `%LOCALAPPDATA%\Kristal`.

Every local write is preflighted against the selected profile, canonical state
index, four registered artifacts, and all catalog-layer SHA-256 commitments.
Pointers are atomically replaced and previous pointers are backed up before
any local update. On an ordinary exception, committed pointers are restored.
Fresh immutable projection files remain as harmless, unreferenced history.
Re-running with unchanged sources is idempotent.

The active view exposes each identity's type/status, highest-priority human
labels per language, lower-priority alternative terms, source-recorded accepted
Wikidata exactMatch and other *candidate* QIDs separately. When the source has
no label or multiple unapproved candidate QIDs, it does not invent a meaning.

## Exact authority boundary

This is a **real local Kristal update of the derived semantic reading surface**.
It is **not a canonical graph, registry or crosswalk mutation**. It does not
approve a candidate `exactMatch`, claim independent C1/C2 qualification,
publish, modify `kristal-public`, commit Git or activate a RuntimeSet.

Source-recorded accepted Wikidata mappings are labeled as such, not elevated to
independently verified truth. A canonical semantic correction that changes
meaning must use the Authoring Kit's new-artifact, recoverable registration path;
never edit `canon/state.index.json` or overwrite a past canonical revision.
