# Architecture — Kristal Manager alpha.11

## Responsibility

```text
Local Kit          semantic/local build + exact GitHub/AI read-surface contract
Kristal Manager    inventory + validation + transport/orchestration
GitHub collections mutable reader/ingestion surface
GitHub Setup       qualification + immutable Publish + Activate
Kompiler           optional read-only context compiler
```

Manager does not define Kristal semantics. It consumes Local Kit and Framework contracts.

## Core invariants

```text
LOCAL PATH != KRISTAL IDENTITY
READ SURFACE != KRISTAL CANON
READ SURFACE DIGEST != LOGICAL COMMITMENT
SYNC != PUBLICATION
PUBLICATION != ACTIVATION
COLLECTION INDEX != SEMANTIC AUTHORITY
```

## Hosted collection layout

```text
kristal-public/ or kristal-private/
└── kristals/
    ├── index.json                         derived collection discovery index
    └── <slug>/
        ├── AI_START_HERE.md
        ├── AI_MANIFEST.json
        ├── ai/
        ├── canon/
        ├── docs/
        ├── sources/
        ├── state/
        ├── ... files selected by Local Kit read-surface
        └── .kristal/
            └── sync-manifest.json         operational Manager ownership/cache metadata
```

The exact subtree file list comes from `kristal.github-read-surface/1.0` emitted by Local Kit 3.2.4+.

## Single Sync transaction

```text
validate/cache
    ↓
verify v10 hosting capability
    ↓
Local Kit build-ai
    ↓
Local Kit read-surface --require-ready
    ↓
verify selected local files by SHA-256
    ↓
GitHub API fast path: sync-manifest + collection index
    ├── exact → ALREADY SYNCED
    └── changed
           ↓
      fetch/fast-forward collection
           ↓
      apply exact managed read surface
           ↓
      update kristals/index.json
           ↓
      stage only target subtree + index
           ↓
      one commit + one push
```

A previous Manager sync manifest defines which old paths Manager may delete. Unmanaged files are preserved.

## Batch execution model

For thousands of Kristals, per-Kristal Git transactions do not scale. alpha.11 separates independent CPU/read work from shared repository mutation:

```text
Phase 1  parallel Local validation (bounded)
Phase 2  parallel build-ai/read-surface preparation (bounded)
Phase 3  one repository transaction per collection
```

Public/private collection transactions may execute in parallel. Every individual collection receives at most one fetch/commit/push for the batch.

## Discovery model

`kristals/index.json` is a deterministic projection containing one entry per hosted Kristal:

```text
path
AI entrypoint
state_ref
logical commitment
read-surface digest
file count / byte count
materialization-object count
```

The index enables an AI or GitHub-connected reader to start from the collection root and find a relevant Kristal without recursively traversing thousands of directories. It is disposable/rebuildable metadata, not canon.

## Materialization boundary

Read-surface Sync may expose materialization manifests and materialization references selected by Local Kit. Manager does not automatically place large physical blobs in normal Git history. Blob transport remains a separate host policy (for example Releases, GHCR or LFS) and must not affect v9 logical commitments.

## Windows execution

All external CLI subprocesses use hidden-window flags on Windows. The GUI is launched through `Kristal-Manager.pyw`; no `.cmd` launcher is included. Long-running work uses background threads and a thread-safe progress queue feeding the GUI log.

## Local tool aliases

```text
C:\mycode\Kristal\Kristal-Authoring-Kit
C:\mycode\Kristal\Kristal-Framework
```

These are operator discovery aliases only. Network/framework identity remains defined by `network.toml`.
