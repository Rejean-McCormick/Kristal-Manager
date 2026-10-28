# CI integration

The supplied CI has two layers:

1. Python 3.11/3.12/3.13 unit tests plus the built-in independent `V10-Full` fixture.
2. An external qualification of `Rejean-McCormick/Kristal-Framework` pinned directly to immutable commit `fe54a88271e2ad7522abacdfbde90f9397954053`.

Draft.3.1 is pinned in `kristaldiag/resources/locks/framework-v10.json` to immutable commit `fe54a88271e2ad7522abacdfbde90f9397954053`. CI MUST NOT replace that exact pin with floating `main`.

The external `V10-Standard` gate is pinned directly to commit `fe54a88271e2ad7522abacdfbde90f9397954053`.

For release audit, `framework-release-audit.yml` accepts an explicit commit/tag/ref, runs `V10-Standard`, then the broader release campaign, and verifies the produced evidence manifest.

## Alpha.4 evidence gates

Both CI paths call `kristaldiag verify-run ... --require-pass` so a consistent but
non-PASS diagnostic result cannot be counted as a successful gate. Verification
still establishes evidence **integrity**, not independently signed C1 identity,
owner C2 authorization, deployment approval, publication or activation.

The manual Framework release audit now requires a full 40-character commit SHA,
not a floating branch or tag; the workflow checks the resolved checkout SHA.
See [C1/C2/C3 handoff](C1_C2_C3_HANDOFF.md).
