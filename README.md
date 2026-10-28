> **Mise à jour Manager (28 octobre 2026) — Icônes des dossiers `locals` :** dans le menu **Icons**, activer si souhaité « Activer icônes personnalisées sur dossiers Windows (session) » (désactivé au démarrage), puis « Gérer les icônes de locals… ». Sans activation, le générateur est strictement en lecture seule et refuse l'écriture par API. Après activation, il faut cocher une deuxième autorisation et confirmer la génération dans le navigateur. Le dossier sélectionné (`C:\mycode\Kristal\locals` par défaut sous Windows) est lu directement ; les Kristals non alignés explicitement sur le Thésaurus UNESCO sont ignorés. Le générateur Node est **intégré au dépôt Manager mais conserve son interface navigateur**. Voir [docs/LOCAL_FOLDER_ICONS_OPT_IN.md](docs/LOCAL_FOLDER_ICONS_OPT_IN.md).

> **Mise à jour du 28 octobre 2026 :** la classification active des sujets et des icônes est unifiée sur le **Thésaurus UNESCO** (7 domaines / 88 microthésaurus). ISCED-F n’est plus une catégorie utilisée par le Manager, son audit ou le générateur d’icônes. Consulter [UNESCO_CONSOLIDATION_2026-10-28.md](UNESCO_CONSOLIDATION_2026-10-28.md).

> **UNESCO taxonomy integration (2026-10-27):** Kristal Manager now reads the pinned Framework v7 UNESCO Thesaurus reference (7 domains, 88 microthesauri) alongside ISCED-F 2013 icon broad fields. These are separate axes, not guessed classifications. The **Actions → UNESCO classification audit…** overlay exports offline JSON and HTML; no Kristal source is modified. See [UNESCO_CLASSIFICATION_2026-10-27.md](UNESCO_CLASSIFICATION_2026-10-27.md).

**Édition consolidée — icônes Windows + diagnostic guidé :** consulter [CONSOLIDATION_2026-10-27.md](CONSOLIDATION_2026-10-27.md).

# Kristal Manager

**Mise à jour icônes sur le Manager 19 h 24 :** lire [MISE_A_JOUR_ICONES_1924.md](MISE_A_JOUR_ICONES_1924.md). Les icônes Windows existantes sont affichées dans la table ; le générateur Windows original reste séparé.

**Local content update:** `0.1.0-alpha.15` · **Framework target:** `10.0.0-draft.3.2` · **Operational status:** **read-only inventory and content catalogue available; GitHub synchronization disabled**.

Kristal Manager owns the operational inventory of **existing** Kristal workspaces and, when independently restored and qualified, should orchestrate controlled GitHub v10 read-surface synchronization. It does **not** own the semantic interpretation of knowledge, the archetype library, domain qualifications, or publication/activation.

> This update repairs an important source-distribution defect: the supplied alpha.11 snapshot and the publicly accessible GitHub `main` branch both lacked the `kristal_manager/` Python package referenced by the launcher and tests. We have **not reconstructed the missing alpha.11 Git sync engine** from guesswork. Instead, the recovery package provides a working and tested read-only inventory, a desktop GUI, a Konstellation-facing local export, and an intact C2 cryptographic verifier. Any remote mutation remains blocked until the full backend can be recovered and audited.

## Content scanner and SQLite overview (alpha.15)

Manager now provides an optional, local descriptive content catalogue in addition to its operational inventory. It reads the selected registered v11 graph and dictionaries, or a recognized native v6 assertion payload, without executing Kristal code or modifying sources. It separates structured value components from main assertions, reports source/lexical coverage and Wikidata alignment states, and ranks subjects by observed assertion count rather than inferring semantic importance.

```text
python -m kristal_manager catalog C:\Kristals --db C:\Catalogues\content.sqlite3 --overview C:\Catalogues\content.html
python -m kristal_manager catalog-query Terre --db C:\Catalogues\content.sqlite3
```

The desktop GUI adds **Scan content → SQLite + overview** and **Open content overview**. The HTML page is an offline, searchable overview of summaries; the database/CLI searches all indexed concepts. Incremental scans hash only selected inputs and reparse changed projects. Unsupported or bounded content is explicitly partial/unknown. No dump validation, network endpoint, public export or semantic qualification is implied.

See [the scanner contract and limits](docs/CONTENT_CATALOG.md) or [French quick start](LIRE_CONTENU.md). The example in `exemple-16-cristaux` was computed from the 16 structured Wikidata projects supplied in this session.

## Quick start (Windows)

1. Extract the entire repository to a local directory.
2. Install Python **3.11+** (Tkinter is normally available with standard Windows Python).
3. Double-click **`Kristal-Manager.pyw`** or `Launch-Kristal-Manager.cmd`.
4. Select the parent folder of your local Kristals and choose **Scan local Kristals**.
5. Inspect workspace identity, profile, state snapshot source, structural readiness and recorded commitments.
6. To export locally, choose **Export local inventory JSON**. The file remains on your machine.

The accompanying `kristal-manager.html` can open an exported JSON inventory with your browser's local file picker. It is a convenience table, **not** a duplicate Konstellation semantic explorer.

## Operational verification (alpha.14, Kristal v10 baseline)

Manager coordinates **read-only, local operational checks**. It does not claim to
be the independent Framework/C1 validator or publication authority. Use:

```bash
python -m kristal_manager verify "C:\mycode\Kristal\locals\MyKristal"
python -m kristal_manager scan "C:\mycode\Kristal\locals" --verify-sources
python -m kristal_manager export "C:\mycode\Kristal\locals" --verify-sources --output inventory-private.json
```

`verify` computes the current Kit 3.3 registered-source fingerprints using local
bytes. It distinguishes `LOCAL_CHECKS_PASSED`, `LOCAL_STRUCTURE_ONLY`,
`ATTENTION_REQUIRED`, and `BLOCKED`. A stale Discovery triple does **not** by
itself invalidate a canonical v9 state. CLI `verify` exits with code `3` for
attention/blockers, `0` otherwise, and `2` on invocation errors.

For optional **independent semantic State Commitment checking** using your own
trusted, exact *Kristal Framework* v10 checkout:

```bash
python -m kristal_manager verify "C:\mycode\Kristal\locals\MyKristal" --framework-root "C:\mycode\Kristal\Kristal-Framework"
```

Requires Node.js and Framework reference scripts. Manager checks the exact
Framework `contracts/contract-set.json` SHA-256 from the supplied 10.0.0-draft.3.2
snapshot before invoking its `verify-state-v9`. This is the v9 **semantic state
baseline within v10**, not an obsolete Framework version. Executing the local
Framework scripts requires **trusting that checkout**; Manager does not install
code or fetch remote files. If the Framework is absent or unpinned, semantic
verification remains `NOT_EVALUATED`.

The GUI adds **Verify selected (local)**, which checks registered bytes without
calling external code. Neither the GUI nor CLI regenerates Discovery, modifies
canon, sends data, syncs to GitHub, or declares C1 qualification, C2 grants,
C3 hosting, publication, activation or read authorization. Repair stale derived
metadata using the Authoring Kit's `build-discovery`, then run Manager again.

## CLI (English)

From the repository root:

```bash
python -m kristal_manager scan "C:\mycode\Kristal\locals"
python -m kristal_manager inspect "C:\mycode\Kristal\locals\MyKristal"
python -m kristal_manager export "C:\mycode\Kristal\locals" --output private-local-inventory.json
```

`export` refuses overwriting an existing file unless `--overwrite` is supplied. Absolute local paths are omitted by default; `--include-paths` is a deliberate and potentially sensitive operator opt-in. On POSIX systems the generated file is owner-readable only (`0600`). **Do not place this export in a public GitHub repository or an unauthenticated web server.**

## What the inventory means

| Property | Source / meaning |
| --- | --- |
| `state_ref` | Workspace declaration and current v9 state snapshot; explicitly checked for mismatch |
| `state_commitment` | Digest **reported by** the state snapshot, not independently recomputed or factually qualified |
| `state_blob_digest` | Byte SHA-256 of the current snapshot file, **not** the logical State Commitment |
| `readiness` | Locally observed structural readiness (`READY`, `NO STATE`, `STATE CONFLICT`, etc.) |
| `hosted_network_baseline` | Declared v10 target capability, **not** proof of being hosted |
| `archetype` | `UNDECLARED` by default; Arketype association requires an explicit mapping |
| `qualification` / `publication` | `NOT_ESTABLISHED` unless independently validated elsewhere |
| `availability` | `local`; a local record is not automatically publicly accessible |

The inventory export format remains provisional as **`kristal.manager-local-inventory/0.1-candidate`**, a local integration proposal, **not a normative Framework format**. It is intended for a future **authenticated, policy-first Konstellation fleet adapter**. Konstellation owns navigation among Kristals and into concepts; Manager only owns operational inventory and access-restricted metadata export. The final producer/consumer contract must be agreed by both repositories before any network endpoint is enabled.

## v10 architecture boundaries

```text
Authoring Kit 3.3+    --> Local workspace + exact read-surface (when ready)
                         |
Kristal Manager    -->   Local inventory + operational verification
                         | (future, gated and audited)
                         +--> C1 independent qualification + C2 authorization
                         +--> GitHub collection sync manifest + derived index
                         +--> C3 hosted collection verification
Konstellation      <--   Read-only, policy-scoped inventory + verified hosted sources
Arketype           -->   Archetype descriptions and noncanonical design patterns
```

A successful check does **not** qualify claims or authorize network exposure. Sync is separate from immutable publication and activation. A push to a public GitHub repository is already **public exposure**, so C1/C2 must be checked **before any public network write**.

## Recovery capabilities and explicit blockers

| Capability | State in alpha.13 recovery |
| --- | --- |
| Local scan, nested workspaces, basic conflict detection | **Implemented** |
| On-demand registered-byte verification and operational report | **Implemented (alpha.14)** |
| Pinned, trusted Framework state verification | **Optional integration (alpha.14)** |
| GUI inventory, search, selected-state inspection | **Implemented** |
| Local-only policy-minimized JSON export | **Implemented** |
| Standalone offline HTML inventory viewer | **Implemented** |
| C2 signed grant / per-revision qualification verifier | **Included** from Bootstrap's candidate verifier; independent security tests run |
| Kit readiness and read-surface invocation | **NOT RESTORED**; see docs |
| C1, C2 and C3 interoperability end-to-end | **NOT VERIFIED** |
| Local migration, preparation of publish requests | **BLOCKED**, original implementation unavailable |
| GitHub sync / batch sync / full backup | **BLOCKED**, no remote mutation performed |
| Live GitHub state, remote branch protections, Windows interactive GUI | **NOT VERIFIED** |

## Tests

```bash
python -m pip install -e ".[test]"
python -m pytest -q tests/test_recovery.py tests/test_c2_public_gate.py tests/test_discovery_adapter.py tests/test_operational_v10.py tests/test_content_catalog.py
```

The original `tests/test_core.py` remains available as an **unresolved compatibility suite** documenting legacy alpha.11 behavior. Many of those tests expect a synchronization engine not supplied in the source repository. **Do not claim that the historical suite passes** or remove its failed cases to disguise missing behavior. A future source recovery must restore those operations with C1/C2/C3 guards and validate every historical test.

## Relevant documentation

- [Architecture](ARCHITECTURE.md)
- [Current recovery status](docs/RECOVERY_STATUS.md)
- [Konstellation inventory handoff](docs/KONSTELLATION_INVENTORY.md)
- [v10 alignment and security gates](docs/V10_ALIGNMENT.md)
- [C2 signed evidence requirements](docs/C2_PUBLICATION_CONTROL.md)

No public/private Kristal collection was modified or published by this release artifact.

## Authentic original runtime found in Git history

After preparing this recovery build, an audit of repository history located the full authentic Python backend in commit **`237b1b539332da5d87bed4b185ea03794aad1057`**, from which the current public branch removed its Python package. See [Historical runtime recovery](docs/HISTORICAL_RUNTIME_RECOVERY.md) and `tools/restore_original_backend.py`. This is preferable to treating the recovery's intentionally disabled sync routines as their eventual implementation. The exporter works **offline** against a full local Git clone, stages verifiable source for review, and never changes the checkout or contacts GitHub.

**Operator caution:** `GitSink.bat` is an inherited generic Git helper that may stage/commit/push all changes; it is **not** used by the Manager launcher or recovery tests. Do not invoke it as an alignment or publication step.


## Authoring Kit 3.3 Discovery (alpha.13)

Manager now **reads, but never generates or modifies**, the following Kit 3.3
noncanonical files in each local workspace:

- `kristal.discovery.json` (`kristal.discovery/1.0`)
- `derived/reader-inventory.json` (`kristal.reader-inventory/1.0`)
- `derived/reader-profile.json` (`kristal.reader-profile/1.0`)

A missing set is allowed for historical Kristals. An incomplete, structurally
invalid, or internally inconsistent set is reported under `discovery.status`
without changing v9 state readiness. Matching fingerprints are shown as
`consistent_unverified` (NOT proof that local files are still unchanged).
For a costly explicit check of registered source bytes, use:

```bash
python -m kristal_manager inspect /path/to/Kristal --verify-discovery
```

This verification matches the Kit 3.3 fingerprint of its *recorded* source
files/segments; it does not discover unregistered content or confer authority.
Never treat reader hints as permission to open source files.

## Private Konstellation preview export (experimental)

The existing Konstellation My Kristals preview presently consumes a **different**
format. An opt-in adapter now emits precisely
`konstellation.manager-inventory-preview/0.1`:

```bash
python -m kristal_manager export-konstellation /path/to/locals \
  --principal-id local-user --output private-konstellation-preview.json
```

On Windows, use **Export My Kristals (opt-in)** in the Manager GUI, where the
principal and disclosure of *all inventoried titles* must be confirmed.
The operator must independently decide that the named local principal is
entitled to see every listed Kristal; Manager does NOT evaluate ACLs or issue
access grants. **Default deny** applies if no principal is supplied. Export is
private, local-only, file-based, capped by the existing consumer's limits, and
includes **no paths, secrets, canonical payloads or inferred publication status**.
All entries remain `visibility=private`, `availability=unknown`, and
`viewKind=inventory_only` when consumed by the current Konstellation preview.
The presence of READY in the Manager's local scan is **not** translated to
reader `ready`; no publication, remote write, or server endpoint is enabled.

The two JSON outputs serve different purposes: `export` produces a richer
restricted operational report, and `export-konstellation` produces the narrow
KNAV preview shape. Neither is a ratified Framework format.

## Local migration / cleanup

Only the stale root `SNAPSHOT_INDEX.txt` was relocated to
`docs/snapshots/SNAPSHOT_INDEX_20261013_1042.txt`. The updated ZIP contains
an optional **`Nettoyer_anciens_fichiers.pyw`** with a French desktop GUI.
It previews the exact obsolete root file, compares its original SHA-256 and
requires checkbox + confirmation before deleting an unchanged local copy.
It never deletes modified files or recursively scans workspaces.
Old package-manifest evidence is archived in `docs/snapshots/`; the new
root package manifest is regenerated for this distribution.
