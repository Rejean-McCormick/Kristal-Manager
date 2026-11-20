# UCKK SecurityDiag

**Version:** 0.2.0  
**Target:** UCKK Moodle source + UCKK Publisher + fresh Linux production VPS  
**Runtime:** Python 3.10+, standard library only  
**Mode:** read-only qualification; no remediation

UCKK SecurityDiag is a smaller Moodle-focused derivative of the Konnaxion SecurityDiag operating model. It is designed for the UCKK architecture where custom Moodle code is published through **UCKK Publisher** into `/opt/uckk`, with MariaDB/PHP/Nginx/cron containers and a shared reverse-proxy network.

It intentionally does **not** edit SSH, UFW, Docker, Moodle settings, secrets, cron, databases, backups, or files. Remote commands are fixed read-only evidence probes. Network execution is opt-in.

## Install

Recommended layout:

```text
C:\mycode\UCKK\
├── uckk-moodle\
├── UCKK_Publisher\
└── UCKK_SecurityDiag\      <- keep it as a sibling for now
```

In `auto` mode the tool detects the sibling `uckk-moodle` target and `UCKK_Publisher`. The hardened Publisher uses a fail-closed top-level allowlist, so documentation, release tooling and SecurityDiag are not copied into Moodle `public/`. Keeping SecurityDiag as a sibling still provides the clearest separation of duties.

The hardened Publisher already excludes `securitydiag/` and `.securitydiag/`. An embedded layout is therefore supported, but the sibling layout remains recommended. Merge `INSTALL_GITIGNORE.txt` into the UCKK `.gitignore` when needed.

## First run

```powershell
cd C:\mycode\UCKK\UCKK_SecurityDiag
python .\securitydiag.py doctor
python .\securitydiag.py list
python .\securitydiag.py run repo
```

Or double-click:

```text
C:\mycode\UCKK\UCKK_SecurityDiag\SecurityDiagLauncher.pyw
```

Evidence is written below `.securitydiag/runs/<run-id>/` and `.securitydiag/latest/`.

## Configure the fresh VPS

Copy:

```text
securitydiag.config.local.example.json
→ securitydiag.config.local.json
```

Then set the new server hostname/IP, SSH key, known-hosts file and authorized-key fingerprint. Network checks remain disabled until you explicitly set:

```json
"execution": { "allow_network": true }
```

Production SSH defaults to `StrictHostKeyChecking=yes`. Do not change that to `accept-new` for the release gate.

## Campaigns

| Campaign | Purpose |
|---|---|
| `repo` | UCKK source, secrets, Publisher, Moodle code/config |
| `predeploy` | repo + clean VPS/SSH/firewall/permissions before exposure |
| `host` | VPS, SSH, firewall, Docker, backups/permissions, IOC |
| `incident` | focused post-compromise host/runtime/persistence evidence |
| `external` | public TLS, headers, ports and accidental file exposure |
| `release` | full S00-S11 qualification |

## Levels

| ID | Gate |
|---|---|
| S00 | Diagnostic Integrity |
| S01 | Target & Security Context |
| S02 | Repository Secrets & Artifact Hygiene |
| S03 | Supply Chain & Publisher Safety |
| S04 | Moodle Application Security |
| S05 | Host Baseline & SSH |
| S06 | Firewall & Listening Ports |
| S07 | UCKK Docker Runtime Isolation |
| S08 | Secrets, Permissions & Recovery |
| S09 | Persistence & Incident IOC Scan |
| S10 | External TLS & Moodle Attack Surface |
| S11 | UCKK Security Release Gate |

See `docs/S00_S11_MATRIX.md`.

## UCKK-specific release invariants

The release model treats the following as blocking or explicitly reviewable evidence:

- no deterministic default password such as a demonstration `visite/visite` account;
- no docs, runbooks, PowerShell/Python/shell tooling or snapshot metadata copied into Moodle `public/`;
- production Publisher SSH host keys verified strictly;
- DB and PHP-FPM ports not public;
- no privileged UCKK containers, host namespaces, Docker socket or dangerous host mounts;
- UCKK database attached only to its internal Docker network;
- `/opt/uckk/runtime/.env`, `moodledata` and backup material not group/world readable;
- recent backup metadata plus a real isolated DB + moodledata restore drill;
- no known compromise IOC, executable payload under writable Moodle data, or unexplained persistence;
- public site does not expose `README.md`, runbooks, `tools/`, `uckk-tools/`, `.git`, or raw `config.php` content.

## Post-compromise profile

The base configuration deliberately starts with:

```json
"release": { "profile": "incident_recovery" }
```

That profile requires explicit human attestations for a **fresh VPS**, no cloned old disk, rotated compromised secrets and Publisher SSH key, clean Git source, verified cloud firewall, and retirement/isolation of the old VPS.

The IOC scan can support that decision, but a clean scan does **not** make an old compromised host trustworthy.

## Restore drill

Copy:

```text
attestations/restore-drill.example.json
→ attestations/restore-drill.local.json
```

Only set the booleans to `true` after restoring the database **and moodledata** to an isolated target and verifying UCKK boots and critical data is intact.

## Exit policy

`PASS` and `WARN` return exit code 0. `FAIL` returns 10. Required incomplete evidence (`BLOCKED`, `PARTIAL`, etc.) returns 20. Tool/configuration errors return 30.

For release, warnings remain visible for operator disposition; required failed or incomplete evidence blocks the gate.


## 0.2.0 hardening coverage

S03/S04 now verify the remediations shipped with the UCKK hardening pack: strict pre-pinned SSH host keys, fail-closed public-webroot packaging, a fixed root-owned deploy agent instead of `sudo python3` on uploaded code, payload SHA-256 verification, safe archive extraction, no deterministic visit password, reviewed anonymous Moodle functions with AJAX rate limiting, non-root cron, restrictive Moodle data permissions, Nginx artifact denies/security headers and production PHP settings.

A green `repo` campaign proves the **source/deployment templates** satisfy these controls. It does not prove the live VPS is clean; S05-S11 still require host, runtime, external and recovery evidence before release.
