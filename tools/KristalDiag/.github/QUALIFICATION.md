# GitHub qualification model

KristalDiag is an **independent examiner**, not the normative Kristal Standard and not the GitHub lifecycle controller.

## Automatic gates

1. KristalDiag self-tests on Python 3.11, 3.12 and 3.13 and requires its built-in `V10-Full` corpus to pass.
2. CI checks out `Rejean-McCormick/Kristal-Framework` at immutable commit `fe54a88271e2ad7522abacdfbde90f9397954053` and applies `V10-Standard`.
3. Release audit accepts an explicit Framework ref, runs `V10-Standard`, then the broad `release` campaign and verifies evidence-manifest integrity.

Draft.3.1 is pinned to immutable Framework commit `fe54a88271e2ad7522abacdfbde90f9397954053`. CI deliberately does not substitute floating `main`.

## Independence boundary

The v9 commitment implementation is Python under `kristaldiag/v9.py`; v10 publication/bundle identity checks and GitHub read-surface/collection checks are Python under `kristaldiag/v10.py`. The examiner does not execute the Framework JavaScript verifier to manufacture agreement.

SchemaStore uses frozen examiner copies rather than target-provided schemas. `kristaldiag/resources/locks/framework-v10.json` records the exact draft.3.1 candidate snapshot SHA-256 and captured contract hashes. After draft.3.1 is pushed, record its immutable Git commit there as well.

## Inherited substrate

Historical `V7-*` and v9 profiles remain available. K24 continues to use the frozen inherited baseline under `kristaldiag/resources/baseline/9.0.0-draft.1/`; v10 does not silently rewrite historical commitment meaning.

## Lifecycle boundary

Kristal Local Kit owns authoring/read-surface construction. Kristal Manager owns local inventory, validation orchestration and GitHub synchronization. Kristal GitHub Setup/Bootstrap owns provisioning, qualification dispatch, publication and activation. KristalDiag may independently examine resulting repository descriptors, hosted read surfaces, collection indexes, downloaded publication bundles and evidence, but does not mutate those surfaces.

## Alpha.4 verifier hardening

Level results K25–K32 are now recognized by the persisted evidence schema.
The verification gate rejects unsafe evidence paths and, with `--require-pass`,
valid-but-non-PASS evidence. This **does not create a signed C1 receipt** or
C2 permission: external signature and owner-grant verification must be agreed
with their respective owners before a public sync/publish pipeline is enabled.
