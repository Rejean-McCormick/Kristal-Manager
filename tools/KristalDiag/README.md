# KristalDiag v10

[![KristalDiag CI](https://github.com/Rejean-McCormick/KristalDiag/actions/workflows/ci.yml/badge.svg)](https://github.com/Rejean-McCormick/KristalDiag/actions/workflows/ci.yml)

**KristalDiag is the independent diagnostic, conformance and release-qualification examiner for Kristal.**

Current target: **Kristal `10.0.0-draft.3.1`**, pinned to the immutable published Framework commit `Rejean-McCormick/Kristal-Framework@fe54a88271e2ad7522abacdfbde90f9397954053`. The Windows source-package SHA-256 is retained only as supplemental capture evidence.

```text
Kristal-Framework              = normative specification + reference implementation
KristalDiag              = independent examiner
Kristal Manager          = local inventory + validation orchestration + GitHub sync
Kristal GitHub Setup     = bootstrap + qualify/publish/activate
Kompiler                 = optional read-only context compiler
```

KristalDiag does **not** manage Local Kristals, perform backups, publish releases or activate channels. It examines artifacts and evidence produced by those systems.

## What changed in v10

KristalDiag keeps its independent v9 commitment implementation and adds independent v10 checks for:

- node manifests and capability descriptors;
- generic host bindings and `kristal.host/github/1.0`;
- node/binding relational coherence;
- Publication Records and exact state references;
- byte-verifiable `kristal.publication-bundle/1.0` bundles;
- publication identity binding to the exact bundle manifest;
- directory/discovery semantics;
- the invariant `SEMANTIC STATE != HOSTING != PUBLICATION LOCATION != DISCOVERY DIRECTORY`;
- malformed v10 contracts and tampered publication bytes;
- Standard `release.json` / `contract-set.json` alignment;
- draft.3.1 GitHub AI/read surfaces, sync manifests and high-scale collection indexes;
- exact hosted file byte/digest verification plus AI/state binding.

The examiner uses its own frozen contracts. It does not validate a target using schemas supplied by that target.

## Quick start

```bash
python -m pip install -e .

kristaldiag doctor --target .
kristaldiag self-test

# Generic hosted-network conformance
kristaldiag conform /path/to/target --profile V10-Node-Reader
kristaldiag conform /path/to/target --profile V10-Full

# GitHub host profile
kristaldiag conform /path/to/hosted-node --profile V10-GitHub-Host

# Campaigns
kristaldiag run v10 /path/to/target
kristaldiag run release /path/to/Kristal-Framework
```


## Evidence and inter-repository alignment (alpha.4)

The v10 evidence schema now supports K25–K32; `verify-run` rejects unsafe
paths and checks persisted result/digest coherence. CI can require both evidence
integrity and an actual PASS with `--require-pass`. This is **not** a signed C1
receipt or a C2 authorization. See [C1/C2/C3 handoff](docs/C1_C2_C3_HANDOFF.md).

## Draft.3 GitHub AI/read-surface verification

KristalDiag independently verifies the operational contracts used by Local Kit 3.2.4, Manager alpha.11 and the GitHub collection workflow:

- `kristal.github-read-surface/1.0`;
- `kristal.github-sync-manifest/1.0`;
- `kristal.github-collection-index/1.0`.

For a hosted collection, K29 can verify `kristals/index.json` and every indexed `kristals/<slug>/` subtree, including exact file SHA-256/size, the v9 State Commitment, `AI_MANIFEST.json`, `ai/INDEX.json`, the derived surface digest and unmanaged-file exclusion. Subtrees are checked with bounded parallel workers so thousands of Kristals can be examined without changing the semantic model.

The read surface and collection index remain derived navigation/integrity surfaces. They are **not** v9 semantic authority, publication, or activation.

## V10 profiles

| Profile | Qualification surface |
|---|---|
| `V10-Node-Reader` | v10 contracts, node/binding relations, separation, negative corpus |
| `V10-Publisher` | inherited v9 reader/publisher + verified v10 publication bundles |
| `V10-Directory` | Node Reader + directory/discovery semantics |
| `V10-GitHub-Host` | Node Reader + GitHub reference host profile + draft.3.1 hosted read-surface checks when present |
| `V10-Full` | inherited V9-Full semantics + generic v10 node/publisher/directory checks |
| `V10-Standard` | normative Framework repository: inherited compatibility + v10 contracts/regressions + release/contract-set alignment |

`V10-Full` intentionally does **not** require GitHub. GitHub is a reference host profile, not semantic identity.

## Diagnostic levels

V10 adds K25–K32:

```text
K25  machine contracts & capabilities
K26  node / binding relations
K27  Publication Record + bundle integrity
K28  directory & discovery semantics
K29  GitHub host profile
K30  semantic / hosting separation
K31  negative & adversarial corpus
K32  Standard / contract-set alignment
```

K14 remains the final fail-closed gate.

## Independent publication verification

For a local or downloaded publication bundle containing:

```text
publication.json
bundle-manifest.json
state-snapshot.json
```

KristalDiag independently recomputes:

1. the v9 State Snapshot commitment;
2. payload sizes and SHA-256 byte digests;
3. the manifest byte digest;
4. the v10 `publication_id` identity projection;
5. the binding between Publication Record, manifest and exact state.

It does not call the Framework JavaScript verifier for this check.

## Frozen examiner provenance

`kristaldiag/resources/locks/framework-v10.json` records the exact published Framework commit and captured draft.3.1 contract hashes. Vendored examiner copies are integrity-hashed by `contract-manifest.json`.

## Read-only boundary

KristalDiag fingerprints the target before and after qualification. Target code is not imported. Target commands execute only through an explicit trusted driver with `--allow-exec`; ordinary qualification is static/read-only.

Every conformance verdict remains qualification evidence only:

```json
{
  "qualification_only": true,
  "authority_granted": false
}
```

## Evidence

Each run produces a verifiable evidence bundle under `.kristaldiag/` or the selected `--control-dir`. Verify it with:

```bash
kristaldiag verify-run /path/to/current/summary.json
```

See `docs/LEVELS.md`, `docs/CONFORMANCE.md`, `docs/ARCHITECTURE.md` and `docs/CI_INTEGRATION.md`.
