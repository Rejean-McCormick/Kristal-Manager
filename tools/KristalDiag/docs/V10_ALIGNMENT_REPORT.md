# KristalDiag 1.0.0-alpha.4 — v10 alignment and verification

**Source:** user-supplied `znapshot_KristalDiag_10121936.zip` (12 October 2026).  
**Source ZIP SHA-256:** `58005c08d2a983b9808778725470f6e107c3c6c7606f35f1536fdf1755db4a86`.  
**Status:** source-code update prepared locally. **No remote GitHub commit, C1 signature, C2 authorization, publication, activation or canonical Kristal was changed.**

## D-01 — Pin and contracts: retained, independently checked

The input already targeted `10.0.0-draft.3.1` and pinned Framework commit
`fe54a88271e2ad7522abacdfbde90f9397954053` in its CI and
`kristaldiag/resources/locks/framework-v10.json`. The update **does not repin**
the Framework or reinterpret frozen v9 commitments. The 17 recorded pinned
Framework source-file SHA-256 digests match the contents of the separately
provided `Code_snapshot_Kristal-Framework(7).zip`.

`V10-Standard` was executed locally against that extracted Framework snapshot
using the independent KristalDiag Python implementation. All required levels
passed, including `K32` contract-set alignment. The persisted evidence was
independently re-read by `verify-run --require-pass`, which returned `VALID`.
This is snapshot-level evidence; the live GitHub commit and deployed systems
were **not** fetched or verified in this delivery.

## D-02 — Levels K25–K32: defect fixed

The uploaded `schemas/level-result.schema.json` incorrectly recognized only
K00–K24. The examiner executed v10 levels already, but the offline verifier
could reject their persisted results. The schema now supports K25–K32, while
K33 remains invalid. Regression tests cover both the positive and negative
cases, plus verification of an actual saved K25 run.

## D-03 — C1/C2/C3 evidence: fail-closed, not a signature

`kristaldiag verify-run SUMMARY --require-pass` checks evidence tree integrity
and **rejects valid but non-PASS runs** with a nonzero exit code. Both CI
workflows now apply this stronger gate to expected successful reports. The
manual release-audit workflow accepts **only a 40-character Framework commit
SHA** and checks that the resolved checkout matches it, rather than accepting
floating branch names or tags.

Persisted evidence verification now rejects unsafe relative paths, traversal,
absolute names, symlink evidence and malformed manifest SHA-256 values. The
new tests cover these rejection cases.

**Explicit limit:** evidence manifests contain hashes but no cryptographic
signature or trust anchor. A standalone `verify-run` PASS is **not** an
independently signed C1 prepublication receipt and **not** a C2 owner grant.
See `docs/C1_C2_C3_HANDOFF.md`. The candidate prepublic receipt contracts have
not been unilaterally implemented or declared ratified.

## D-04 — v10 reader/materialization boundary

Existing K29 GitHub read-surface/index verification, v9 polymorphic and
materialization checks were retained. Existing tests for hosted file tampering
and an in-process v10 full self-test passed. **Real network availability,
external blob materialization, permission scopes and production publication
remain unqualified** without a separate staging run and explicit approval.

## Tests actually executed on the extracted source

| Check | Result |
|---|---|
| `python -m pytest -q` (including seven new regression tests) | **46 passed** |
| `KRISTALDIAG_TEST_IN_PROCESS=1 python -m kristaldiag self-test` | **PASS**, V10-Full |
| `python scripts/release_check.py` | **PASS**, mirrors/contract manifests/links/tests/self-test |
| `conform <extracted Framework> --profile V10-Standard` | **PASS**, including K32 |
| `verify-run <that run>/summary.json --require-pass` | **VALID** |
| Live GitHub CI, C1/C2/C3 signed handoff, actual Windows device | **NOT TESTED** |

## Scope and rollout

This update is entirely English and maintains the non-mutating examiner
architecture. To integrate it with real C2/C3, first ratify the signed receipt
format, keys, scope, revocation/expiry and validation responsibilities, then
validate a non-sensitive exact-revision staging pilot. Do not let a report file
or a GitHub index grant publication by its mere presence.
