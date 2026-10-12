# C2 — Signed Public Exposure Control (Candidate)

**This is a candidate, non-normative security contract. It is not an authorization to publish any particular Kristal.**

The included `kristal_manager/publication_gate.py` is the C2 Ed25519 verification module taken from the supplied `Kristal-GitHub-Bootstrap` snapshot (no private keys). It is covered by the original `tests/test_c2_public_gate.py`.

The verifier accepts public `sync` or `publish` operations only when all of the following independently hold:

1. A trusted, externally pinned `trust.json` provides separate public keys for the owner approver and independent qualifier.
2. A signed, unexpired authorization grant matches `slug`, `state_ref`, repository, and the allowed list of paths.
3. A separately signed, unexpired qualification receipt matches `grant_id`, operation, exact identity, logical State Commitment, and digest of all candidate bytes.
4. Revocation registry does not revoke the grant.
5. Every current file is still present, non-symlinked, within the candidate directory and has the expected digest.

The evidence formats are `kristal.c2-public-authorization/0.1-candidate`, `kristal.c2-prepublic-qualification/0.1-candidate`, `kristal.c2-trust/0.1-candidate`, and `kristal.c2-revocations/0.1-candidate`.

Environment variables for a future guarded public operation: `KRISTAL_C2_POLICY_DIR` and `KRISTAL_C2_TRUST_PIN`. Install `cryptography>=42` when using the independent signature verifier.

**The alpha.12 recovery does not expose any remote synchronization operation.** Even a passing C2 verification test cannot authorize an operation if the original sync backend is missing, nor can it replace GitHub rulesets or independent C1/C3 checks. Private signing keys are never included in this repo.
