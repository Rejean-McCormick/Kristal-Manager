# Local content scanner — alpha.15

Manager previously inventoried workspace identity, state readiness and advisory Discovery metadata. `catalog` adds a private **descriptive projection of selected content**, not semantic qualification or a replacement for the canonical authoring graph.

## Run

```text
python -m kristal_manager catalog C:\Kristals --db C:\Catalogues\kristal-content.sqlite3 --overview C:\Catalogues\kristal-content.html
python -m kristal_manager catalog-query Terre --db C:\Catalogues\kristal-content.sqlite3
python -m kristal_manager catalog-query Q2 --db C:\Catalogues\kristal-content.sqlite3
python -m kristal_manager catalog-overview --db C:\Catalogues\kristal-content.sqlite3 --output C:\Catalogues\kristal-content.html --overwrite
```

In the GUI choose a source root, then **Scan content → SQLite + overview**. Save the database outside source Kristal workspaces; a companion HTML overview is generated. **Open content overview** opens that local file. A later content scan updates the same recognized database. The old operational inventory and minimal Konstellation export are unchanged.

The supplied roots define the complete catalogue snapshot: workspaces no longer present are removed from the derived database, never from disk. A different complete root set deliberately changes the catalogue scope. Missing input roots fail before database writes. Existing unrelated databases are refused. One failed workspace can be reported as unknown without fabricating zero counts.

## What it observes

- Declared subject/domain, native model, ownership, invariants, target profiles and registered contracts, with their source descriptor retained in the summary.
- The **active registered v11 graph**, registry, crosswalk and dictionary catalogue. Historical registered graphs are not added to active counts.
- Native registered v6 `kristal_state` assertion payloads when no active v11 profile exists. Unsupported formats remain `unsupported`, with null measurements; no schema is inferred from arbitrary JSON.
- Entity/property/assertion/source counts, main assertions versus typed value components, dictionary languages and descriptive label coverage. A Q/P code alone is not counted as a descriptive label.
- If an existing, namespace-matching identity migration map supplies a readable native key, it may be displayed as a **reported legacy key**, with its source marked. It never becomes a curated label, accepted identity or descriptive-label coverage credit. Missing Wikidata property labels remain visible as codes rather than invented translations.
- Most-described subjects and most-frequent relations from non-component assertions. Counts are a useful preview, **not an editorial importance score**.
- Reported accepted/candidate Wikidata alignments. When a registered source ledger exists, source claims are identified by both explicit subject and property alignment; preferred/normal/deprecated ranks remain separate. No record is promoted to truth or accepted identity by Manager.

The source ledger is used for provenance classification; the database stores assertion source references and the selected ledger path, not another full copy of all original snapshots. All domain payloads remain owned by the Kristal. Concept IDs are scoped by workspace and reported semantic namespace. Identical labels never merge identities; copies sharing a state identity remain separate and are flagged.

## Incremental and bounded

Workspace discovery prunes generated/materialized trees, snapshots and dependency directories, while still finding nested workspaces in ordinary directories. Explicitly selecting a root inside such a tree remains possible.

Only declared selected inputs are read; source snapshots, dumps and arbitrary folders are not exhaustively opened. By default a selected file is limited to **64 MiB**, a workspace to four times that budget, and dependency count to 256. Over-limit, missing, blocked or invalid inputs produce partial/unknown observations. `--max-file-mib` adjusts the file budget; `--force` reparses unchanged inputs.

Incremental scans hash only previously selected inputs, then skip parsing and database replacement for unchanged workspaces. They detect changed bytes even when file size and timestamps are preserved. Cache reuse is tied to the scanner version and size option. Changes to the active selector, state, registered index, graph, registry, source ledger or dictionaries invalidate the affected row. This is not a whole-dump checksum gate.

Database updates are staged through SQLite backup and published by atomic file replacement after a quick integrity check. An interrupted or failed scan retains the previous catalogue.

`catalog-show Q2 --db PATH` opens indexed assertions for a concept, including one level of typed value fields. `--catalog-id` scopes the result to one local copy and `--limit` bounds returned assertions.

## SQLite structure

- `workspaces`: independent local copy ID, private local path, descriptive summary JSON, observed dependency fingerprints.
- `nodes`: scoped semantic IDs, entity/property kind, preferred available label, reported exact external ID.
- `terms`: multilingual search terms and case-folded search values.
- `assertions`: scoped subject, predicate, typed object, qualifiers, source references, reported rank and descriptive regime.
- `meta`: provisional catalogue format, complete scanned roots and last scan time.

`assertion_subject` and `assertion_predicate` support content queries. `catalog-query` searches labels in all indexed dictionary languages; Q/P and KQ/KP identifiers use exact matching. Results report the Kristal and namespace rather than merging equal IDs across copies.

The HTML file is a self-contained, offline overview of **summaries and top concepts**, not a full browser search across every assertion. Its filter applies to those previews. For all indexed concepts use the CLI/database. Source text is inserted as inert JSON and DOM `textContent`, never executed as HTML.

## Boundaries and evidence

The scanner does not execute Kristal code, modify workspaces, regenerate Discovery, download missing data, infer factual completeness, qualify a state, publish or synchronize anything. A catalogue is a dated local observation; rescan to refresh it. It may contain domain content and private paths and is not automatically included in Konstellation's narrow preview or exposed over a network. New catalogue/HTML files are owner-only on POSIX; choose an appropriate private directory on Windows.

`tests/test_content_catalog.py` exercises content selection, provenance counts, exact-ID search, namespaces, incremental byte changes, malformed/missing data, dictionary fingerprints, symlinks, source preservation, native v6 fallback, stale-row removal, safe HTML, CLI and unrelated database refusal. Recovery/discovery/operational/C2 tests remain separate from the unresolved historical `test_core.py` synchronization suite.
