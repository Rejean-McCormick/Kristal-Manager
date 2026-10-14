# v10 Alignment — Requirements and Gates

**Baseline observed:** Kristal Framework `10.0.0-draft.3.1` and Authoring Kit 3.2.4. The locally declared `kristal.hosting/10.0` target does not prove remote hosting, v10 qualification or publication.

| Work item | Responsible component | Status in recovery |
| --- | --- | --- |
| M-01: restore operational Python runtime | Manager | **Partial:** local inventory, GUI and C2 verifier supplied; original sync backend still missing |
| M-02: authorize public sync before any exposure | Manager / C1 / Bootstrap C2 | **Fail closed:** no GitHub write operation available |
| M-03: consume exact Authoring Kit 3.2.4 `read-surface` | Manager | **Pending authentic backend and conformance fixtures** |
| KNAV-01: safe read-only local registry feed | Manager | **Local prototype implemented**; contract not ratified |
| KNAV-02: fleet navigator integration | Konstellation | **Not implemented here** |
| C3: verify GitHub collection index/sync manifest | Public/private collection | **Not executed by recovery package** |

## Acceptance gates before enabling writes

- Freeze Framework contract-set SHA and Authoring Kit CLI at an exact compatible revision.
- Verify candidate file list and bytes against Kit's source `read-surface --require-ready` output.
- Require C1 independently signed receipt and C2 owner grant before any public network write.
- Qualify C2 grants for exact operation, destination, `state_ref`, logical commitment, digest and path scope; fail on expiry or revocation.
- Test against private staging with real Git semantics: one transaction per collection, stale managed-file cleanup only, integrity and identity collisions.
- Keep immutable publication and activation **separate**; do not treat sync as public release.
- Verify hosted index against C3 and exercise a Konstellation read-only round-trip.

**Nothing in this release updates a canonical workspace or remote collection.**


## Alpha.13 read-only Discovery 3.3 supplement

Kit 3.3-derived `kristal.discovery/1.0`, `kristal.reader-inventory/1.0`
and `kristal.reader-profile/1.0` are now inspected locally (optional
on-demand registered-byte verification). **The historic exact v10 GitHub
read-surface sync engine is still not restored or tested.** C1, C2, C3 and
publication/activation gates stay closed.
