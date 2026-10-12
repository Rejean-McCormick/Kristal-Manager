# Kristal Manager — Architecture and Ownership

**Release:** 0.1.0-alpha.12 recovery · **Status:** local inventory recovery; hosted mutation blocked.

## Roles

| Project | Authoritative responsibility |
| --- | --- |
| Kristal Framework v10 draft.3.1 | Knowledge-state/commitment contracts, v10 hosting profiles |
| Authoring Kit 3.2.4+ | Workspace creation, check, v9 build and exact GitHub read-surface |
| KristalDiag / C1 | Independent qualification of the exact candidate revision |
| Bootstrap / C2 | Trust policy, independent approval, authorization and publication safeguards |
| Kristal Manager | **Operational inventory** and future guarded read-surface transport |
| Public and private GitHub collections / C3 | Hosted read surfaces, sync manifests, derived collection indexes |
| Konstellation | **Navigation** between existing Kristals and within supported concepts/reader projections |
| Arketype | Neutral archetypes, patterns and template descriptions |

## Current implemented local flow

```text
Operator selects local roots
      |
      v
Read-only workspace discovery
      |
      +--> workspace descriptor + v9 state candidates
      +--> current/release/legacy separation
      +--> conflict and readiness diagnostics
      |
      v
Local Tkinter inventory or private JSON export
      |
      v
Trusted Konstellation-side integration (PROPOSED, not live)
```

`kristal.manager-local-inventory/0.1-candidate` is an explicitly provisional noncanonical metadata projection. It is not yet a Framework schema or authenticated hosted endpoint.

## Intended future pipeline (NOT implemented by recovery package)

```text
Kit check -> build-v9 -> build-ai -> read-surface --require-ready
   -> validate exact local octets + C1 independently attest
   -> C2 sign grant for scope / paths / revision / destination
   -> remote write only after required gates
   -> single collection transaction + derived index
   -> C3 structural collection validation
   -> optional separately authorized immutable publication and activation
```

## Data and trust boundaries

- `state_ref` is the knowledge-state identity; the folder path and slug are not.
- A v9 logical State Commitment is distinct from a file checksum or Git SHA.
- The local index and Konstellation view are derived projections, not semantic authority.
- The local inspector shows recorded commitments without independently recalculating logical JCS commitments.
- A local `READY` result is **not** independent qualification.
- Public sync is public exposure; approval is required **before** checkout/push or any other remote write.
- No public path may include private/hidden source content unless independently authorized.
- `KRISTAL_C2_TRUST_PIN` and signed evidence are operator-scoped; never bundled in code, JSON export, or public workspace.
- Missing files/read surfaces yield a blocked/not-ready status, not an assertion that source knowledge is absent.

## Source availability limitation

The supplied original snapshot and current GitHub default branch contain only documentation, launchers, and tests; **`kristal_manager/core.py`, `gui.py`, and `publication_gate.py` were absent**. The alpha.12 recovery supplies a new, explicitly restricted implementation. Restoring the original synchronization backend remains a separate engineering task and must not be inferred from this interface.
