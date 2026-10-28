# C1 / C2 / C3 independent qualification boundary

**Status: compatibility documentation, not a ratified signed-receipt producer.**

KristalDiag 1.0.0-alpha.4 independently examines a chosen target, including v9
semantic commitments and the v10 Framework, publication bundles, GitHub read
surfaces, sync manifests and collection indexes. It is an examiner, not a manager
or authorization server. The Framework baseline remains the exact, previously
pinned `10.0.0-draft.3.1` commit. No implicit repinning occurs here.

## Three independent boundaries

1. **C1 / KristalDiag:** Run a selected conformance profile and persist the
   bounded evidence tree. `verify-run --require-pass` checks that the local
   evidence hashes and the result are valid and PASS. This is **not a signed**
   C1 pre-publication qualification receipt.
2. **C2 / owner authorization:** Validate an independently ratified signed
   qualification receipt and an owner grant for the exact state revision, digest,
   visibility, repository, intended operation and paths **before exposing bytes**
   to a public GitHub repository. A successful diagnostic is not consent.
3. **C3 / hosted collection:** Verify the exact host collection index, sync
   manifests, paths, state/AI bindings and release material. Publication and
   activation require their own proofs and decisions, separate from sync.

## Local evidence steps (no network or target writes)

```bash
kristaldiag conform TARGET --profile V10-GitHub-Host --control-dir EVIDENCE_DIR
kristaldiag verify-run EVIDENCE_DIR/current/summary.json --require-pass
```

`V10-GitHub-Host` proves only the checks it executes. Other workload/
publication requirements may need `V10-Full` and explicit C1 rules. A PASS does
not imply factual correctness or global Framework conformance. Do not manufacture
a C1 signature or assume the owner authorized public publication.

## Pending cross-repository work

- Agree on a **versioned, signed** C1→C2 qualification receipt with C1, C2 and C3
  owners, including the exact source commit/revision, state identity/commitment,
  read-surface digest and allowed scope. Current `0.1-candidate` proposals are
  **not** promoted to a standard by this update.
- Add independent signer/verifier tests only after the canonical contract is
  ratified. Keep trust anchors outside candidate-controlled repositories.
- Test one small, nonsensitive staging Kristal across Kit 3.2.4, Manager,
  Bootstrap, C1/C2 and C3. A passing local unit suite is not end-to-end proof.

No code in this update synchronizes, publishes or activates any Kristal.
