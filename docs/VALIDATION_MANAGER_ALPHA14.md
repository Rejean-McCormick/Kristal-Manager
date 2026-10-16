# Validation — Kristal Manager 0.1.0-alpha.14 (2026-10-16)

**Purpose:** operational validation/orchestration on a v10 Framework draft.3.2
baseline. Does not alter canonical Kristals or grant publication/read access.

## Operational evidence vs authority

| Check | Implemented | Authority |
|---|---|---|
| Local workspace structure/state identity conflict | Yes | Observation only |
| Discovery 3.3 advisory triple, registered-byte SHA-256 and source fingerprint | Yes | Operational observation, not canonical |
| Semantic v9 State Commitment | Optional, exact trusted Framework reference only | Reference verifier; no C1 certificate |
| Independent C1 qualification | No | External C1 |
| C2 owner grant and publication scope | No | External Bootstrap/C2 |
| C3 hosted collection/read-surface verification | No | External C3 |
| Authorized reader and Konstellation exploration | No | Downstream Reader Policy and Konstellation |

## Verified example: Catho

- Local structure: `READY`, with v9 state source.
- Discovery: `stale`, `tracked file size changed`.
- Frozen canonical v9 state verification through supplied Framework
  10.0.0-draft.3.2 reference: `VERIFIED`.
- Aggregate operational assessment: `ATTENTION_REQUIRED` (derived data only).
- Remedy: the *Authoring Kit* owner reruns `build-discovery` on a controlled
  copy, then Manager re-verifies. Do not alter canonical commitments to resolve
  stale reader metadata.

## Security constraints

- Read-only filesystem access; no GitHub operation is enabled.
- `--framework-root` is an explicit trust boundary and will execute that trusted
  reference locally; do not pass downloaded/untrusted code.
- No automatic use of `reader-profile` parser hints as executable commands.
- The registered-source check cannot attest unlisted files.
- Local CLI `verify` can include filesystem paths; do not publish its JSON.
- Local inventory export remains private and strips absolute paths by default.

## Unresolved

The historical alpha.11 core tests intentionally remain unmet, primarily
related to removed GitHub synchronization, exact read-surface preparation,
migration and hosting workflows. They are not hidden or asserted passing.
Full Framework v10 conformance, C1/C2/C3 integration, Windows GUI and hosted
Konstellation exchange remain unverified.
