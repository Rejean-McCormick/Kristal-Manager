# Conformance model

KristalDiag separates diagnostic campaigns from conformance profiles. A required `SKIP` is converted to `BLOCKED` by K14; missing evidence never becomes PASS.

## Kristal v10 profiles

### V10-Node-Reader

Validates v10 machine contracts, exact node/binding relations, the v9/v10 separation invariant and the v10 negative corpus.

### V10-Publisher

Includes inherited v9 state/publisher checks and K27. A strong pass requires Publication Records plus local/retrieved bundle bytes that can be independently verified. A Publication Record without bundle bytes cannot prove retry/idempotence byte equality.

### V10-Directory

Includes Node Reader + K28. Directory entries are discovery/routing surfaces and do not redefine semantic federation.

### V10-GitHub-Host

Includes Node Reader + K29 and validates `kristal.host/github/1.0`. Optional plan-dependent host capabilities may be absent without changing semantic conformance.

### V10-Full

Requires inherited V9-Full semantics plus v10 node, publisher, directory, separation and negative checks. Generic V10-Full does not require the GitHub host profile.

### V10-Standard

Examiner profile for the normative Kristal-Framework repository itself. It checks inherited v9 compatibility, v10 machine contracts, separation/negative regressions and K32 release/contract-set alignment without pretending the Standard repository is itself a hosted publisher node.

## V9 / historical profiles

`V9-State-Reader`, `V9-Builder`, `V9-Materializer`, `V9-Publisher`, `V9-Full` and historical `V7-*` profiles remain available. Their semantic commitment checks are not silently redefined by the v10 upgrade.

## Campaigns

- `baseline`: neutral read-only diagnostics;
- `standard`: historical substrate checks;
- `v9`: all K15–K24 v9 checks;
- `v10`: K25–K31 hosted-network checks plus dependencies;
- `deep`: broad neutral + historical + v9 + v10 checks;
- `release`: deep + K32 + R00–R04 release evidence.

## Qualification boundary

A PASS means observed evidence satisfies the selected checks. It does not grant epistemic authority, publication authority, activation authority, deployment authorization or factual truth.
