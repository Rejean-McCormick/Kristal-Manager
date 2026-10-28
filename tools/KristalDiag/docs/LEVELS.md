# Diagnostic levels

## Neutral harness — N00–N06

| Level | Purpose |
|---|---|
| N00 | diagnostic integrity and runtime |
| N01 | target context, VCS and evidence placement |
| N02 | bounded repository inventory |
| N03 | repository hygiene |
| N04 | tooling/manifests discovery without execution |
| N05 | explicitly declared validators; requires `--allow-exec` |
| N06 | conservative secret/security hygiene scan |

## Historical substrate — K00–K13

K00–K13 retain the pre-v9 v6/v7 qualification surface. K14 is the parent-runner conformance gate.

## Kristal v9 — K15–K24

| Level | Purpose |
|---|---|
| K15 | v9 machine contracts |
| K16 | independent logical/state commitments |
| K17 | State Snapshot semantics and pinning |
| K18 | derivations & reproducibility |
| K19 | materialization binding |
| K20 | Exchange binding |
| K21 | build / publish / activate lifecycle semantics |
| K22 | polymorphic workloads |
| K23 | negative & invariance corpus |
| K24 | inherited v6/v7/v8 compatibility substrate |

## Kristal v10 — K25–K32

| Level | Purpose |
|---|---|
| K25 | v10 machine contracts and capability baseline |
| K26 | node/binding identity, descriptors and relation coherence |
| K27 | Publication Record, exact-state binding and independent publication-bundle byte verification |
| K28 | directory/discovery semantics and exact advertised states/channels |
| K29 | `kristal.host/github/1.0` profile plus draft.3.1 AI/read-surface, sync-manifest and collection-index integrity |
| K30 | independently demonstrate semantic-state / hosting separation |
| K31 | malformed-contract and tampered-bundle adversarial corpus |
| K32 | Standard `release.json` / `contract-set.json` v10 draft.3.1 alignment |

K32 is a Standard-repository audit level; it is not required by generic node profiles.

## Final gate — K14

K14 is produced after selected levels. It fail-closes required SKIP evidence and enforces read-only target fingerprinting.

## Release engineering — R00–R04

| Level | Purpose |
|---|---|
| R00 | documentation/link integrity |
| R01 | diagnostic snapshot/repository manifest reproducibility |
| R02 | Git cleanliness/tag/version identity |
| R03 | signature/trust surface inspection |
| R04 | vendored contract/TCK integrity and profile consistency |
