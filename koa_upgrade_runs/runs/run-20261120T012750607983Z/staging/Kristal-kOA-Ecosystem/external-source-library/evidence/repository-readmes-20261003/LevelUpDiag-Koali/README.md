# LevelUpDiag-Koali v2.5

LevelUpDiag-Koali 2.5 is the diagnostic suite for the **live Koali product system**, while preserving the historical kOA-Linux stabilization and release campaigns.

Its primary default is now `koali-system`: it observes the Koali shell that is actually running on the Windows host, reads the canonical `.koali-dev/state` projection, validates linked owner contracts without copying application repositories, independently probes required runtimes, and verifies that optional modules do not incorrectly degrade the global Shell.

Current KS4.4 product policy:

```text
Konnaxion          shell-critical / must be ready
Orgo               shell-critical / must be ready
Médiathèque kOA    shell-critical / must be ready
SemantiK Architect linked + projected / runtime outage currently accepted
Kristal / kOA Linux / Control Panel / Digital Ecosystem   source-only
```

Run it after starting Koali with `RUN_KOALI.cmd`:

```powershell
python levelupdiag.py run koali-system
# or
RUN_KOALI_SYSTEM_DIAG.cmd
```

The desktop console automatically uses **native Windows Python** for `koali-system`, because it must inspect the Windows-hosted Koali process/state and loopback endpoints. Legacy kOA-Linux campaigns keep the existing WSL-aware backend policy.


## Legacy kOA core stabilization scope

The legacy core campaign remains `stabilization`:

```text
N00 Diagnostic Integrity
N01 Environment
N04 Contracts
N05 Components
```

This scope deliberately defers independent subsystems while the Koali host/build/runtime environment is being stabilized:

```text
Konnaxion          placeholder_until_integration
Ariane             deferred_until_koali_integration_test
Orgo               draft_not_admitted
Semantik Architect deferred_not_admitted
```

This does **not** weaken or rewrite the canonical `sovereign-linux-node` profile. Full-target VALIDATION and RELEASE remain strict and can still report those subsystem authorities as unresolved. The `stabilization-runtime` campaign adds N08/N09/N10 when a bootable image/runtime context becomes available, while retaining DEBUG non-blocking campaign semantics.

## Repository layout

The specialization remains a sibling of the kOA-Linux repository:

```text
C:\mycode\kOA-Linux\
├── koa-linux\
└── LevelUpDiag-Koali\
```

The default target is `../koa-linux`.

Local developer utilities such as `GitSink.bat` are not a DEBUG gate. If an underlying kOA conformance validator reports a local utility or generated build residue, that individual level may report `FAIL/WARN`, but DEBUG continues collecting independent functional/runtime evidence.

## Modes

### DEBUG — default

Use while developing, loading, testing, or diagnosing kOA-Linux.

- no tracked-Git-state protection;
- no dependency verdict blocks another level;
- repository/documentation/release formalities are excluded from the default campaign;
- `FAIL`, `BLOCKED`, `CONFIG_ERROR`, `SKIP`, and `PARTIAL` remain visible at their local level but make the campaign `WARN`, not globally `BLOCKED`;
- `ERROR`/`INFRA_ERROR` still mean the diagnostic execution itself had a problem.

### VALIDATION

Use to check repository/documentation/conformance in addition to functional gates.
Dependencies can be blocked by `BLOCKED`, `ERROR`, `INFRA_ERROR`, or `CONFIG_ERROR`, but a clean Git worktree is not imposed globally.

### RELEASE

Use for strict finalization. Tracked Git state is snapshotted before and after the campaign; mutation by diagnostics is an error.

## Normal execution

```bash
python levelupdiag.py doctor
python levelupdiag.py list
python levelupdiag.py run stabilization
```

Explicit modes are supported:

```bash
python levelupdiag.py run N08,N09,N10 --mode debug
python levelupdiag.py run validation --mode validation
python levelupdiag.py run release --mode release
```

Windows launcher default:

```bat
RUN_LEVELUPDIAG.bat
```

Linux/macOS launcher default:

```bash
./RUN_LEVELUPDIAG.sh
```

Both now default to the `koali-system` campaign.

## Console

`LEVELUPDIAG_CONSOLE.pyw` exposes three policies and an execution backend. With `desktop_console.execution_backend = "auto"`, Windows uses WSL automatically; Linux/macOS use the native interpreter. The Windows UI does not silently fall back to native Python if WSL is unavailable.

- **DEBUG — non bloquant**
- **VALIDATION — conformité**
- **RELEASE — strict**

Presets:

- **KOALI SYSTEM**: N00 + N12, strict live product-system validation.
- **KOALI DEBUG**: N00 + N12, same evidence with non-blocking DEBUG aggregation.
- **STABILISATION kOA**: N00, N01, N04, N05.
- **AUDIT TOTAL**: legacy N00-N10 in DEBUG non-blocking mode.
- **VALIDATION kOA**: legacy N00-N10.
- **RELEASE**: legacy N00-N11.

N02 Repository and N03 Documentation are intentionally absent from DEBUG PRINCIPAL.

## Level sequence

```text
N00 Diagnostic Integrity
N01 Environment
N02 Repository / Structure
N03 Documentation
N04 Contracts
N05 Components
N06 Integrations
N07 Profiles
N08 Security Runtime
N09 Offline Runtime
N10 System Runtime
N11 Delivery
N12 Koali Product System
```

All levels remain serial for stable evidence ordering.

Functional levels no longer depend transitively on N02. Selecting `N08,N09,N10` adds functional prerequisites N00, N01, N04 and N05, but not repository/documentation formalities.

## Campaigns

- `koali-system` — default live Koali qualification, N00 + N12 in VALIDATION mode.
- `koali-system-debug` — non-blocking live Koali diagnosis, N00 + N12 in DEBUG mode.
- `stabilization` — primary pre-subsystem Koali core stabilization, mode DEBUG.
- `stabilization-runtime` — core runtime qualification when image/QEMU context exists, mode DEBUG.
- `debug` — broader development diagnosis including integration/profile/runtime levels, mode DEBUG.
- `audit-total` — N00-N10 in one non-blocking DEBUG pass, scope `full_target_diagnostic`.
- `structure` — repository/documentation checks, mode VALIDATION.
- `validation` — N00-N10, mode VALIDATION.
- `release` — N00-N11, mode RELEASE.

Compatibility aliases remain: `preflight`, `core`, `standard`, `delivery`, `full`.

## Modular product UI diagnostics

LevelUpDiag does **not** define the Koali UX, shell implementation, product manifest filename, or product framework. Those remain owned by Koali documentation and the individual products.

N06 can optionally diagnose consequences of the Koali modular-UI contract when `ui_modularity.enabled` is set in local configuration. The diagnostic is read-only and configuration-driven:

- an optional product repository may be absent and that absence is accepted as an independent-removal state;
- a required product repository that is unavailable reports `BLOCKED`;
- configured standalone markers can verify that a product retains its own runnable UI entry point or equivalent product-owned surface;
- configured integration markers can verify that the product exposes its declared integrated contribution;
- configured dependency scan files can reject explicit private cross-product UI dependency tokens;
- LevelUpDiag does not invent or hard-code Orgo, Konnaxion, Kristal, Spaces, or other product UI file names.

Example local policy:

```json
{
  "ui_modularity": {
    "enabled": true,
    "base_root": "..",
    "products": [
      {
        "id": "example-product",
        "root": "example-product",
        "required": false,
        "standalone_markers": ["<product-owned standalone marker>"],
        "integration_markers": ["<public Koali integration marker>"],
        "scan_files": ["<dependency manifest or source file>"],
        "forbidden_private_ui_tokens": ["<private cross-product UI import token>"]
      }
    ]
  }
}
```

The example deliberately uses placeholders: concrete marker paths belong to each product's admitted contract, not to LevelUpDiag. This check is outside the `stabilization` campaign and therefore cannot turn a missing optional UI product into a Koali core-stabilization prerequisite.

## Result model

A campaign summary now separates:

```text
verdict
execution_verdict
system testability
conformance_verdict
```

In DEBUG, conformance is reported as `NOT_EVALUATED` by the campaign summary. Local level findings are still preserved exactly.

Example:

```text
LevelUpDiag debug [DEBUG] - WARN
Diagnostic execution: PASS
System testability: PARTIAL
Conformance: NOT_EVALUATED
```

That means the diagnostic completed and found unavailable/failed local checks; it does **not** mean the whole debug session is blocked.

## Git policy

DEBUG does not inspect Git globally before/after a run. N02 performs Git observations only when N02 is explicitly selected.
A dirty worktree in N02 is advisory in DEBUG.

RELEASE retains tracked-state mutation protection because release/finalization provenance is a separate concern.

## kOA-specific validation commands

Default commands are still the canonical public kOA-Linux vectors:

```text
Documentation  uv run --frozen python docs/tools/validate_docs.py
Contracts      uv run --frozen python ci/scripts/run-contracts.py
Components     uv run --frozen python ci/scripts/run-components.py
Profiles       uv run --frozen pytest -q tests/profiles
Security       uv run --frozen python ci/scripts/run-security.py
Offline        uv run --frozen python ci/scripts/run-offline.py
System         uv run --frozen python ci/scripts/run-system-tests.py
```

Koali gate markers such as `security: blocked`, `offline: blocked`, and `system: blocked` remain local level verdicts. In DEBUG they do not prevent independent levels from running.

## Evidence

Evidence remains under the target repository:

```text
.levelupdiag/
├── runs/<run-id>/
│   ├── effective_config.json
│   ├── summary.json
│   ├── summary.txt
│   └── levels/Nxx/result.json
└── latest/
```

Commands use `shell=false`; output is bounded and redacted; target mutation remains disabled by configuration.

## Version 2.5.0

2.5.0 adds N12 **Koali Product System**. It validates the KS4.x multi-repository composition layer from its canonical runtime evidence instead of treating integrated applications as copied dependencies. N12 checks live state freshness, owner-contract discovery, runtime readiness, surface registrations, active Space projection, Shell-critical versus optional health semantics, public `/api/shell-state` privacy, and independent loopback probes. SemantiK Architect may remain unavailable without failing Koali while its catalog entry has `affectsShellState=false`.

The `koali-system` desktop campaign is forced to the native Windows backend; legacy kOA-Linux campaigns retain WSL-aware execution.

## Version 2.4.1

2.4.1 fixes the WSL environment inherited by the Windows desktop console. A direct `wsl.exe --exec` launch can expose a narrower `PATH` than an interactive WSL session, which made user-installed `uv`, Cargo, Rust and rustup disappear even though the run was correctly executing under WSL.

The WSL backend now probes `HOME` and `PATH` with the selected WSL Python interpreter, prepends the configurable `desktop_console.wsl_path_prepend` entries (default: `~/.local/bin` and `~/.cargo/bin`), and launches LevelUpDiag through `/usr/bin/env`. The Windows subprocess still uses `shell=false`; no login shell or profile-script dependency is introduced.

## Version 2.4.0

2.4.0 made desktop execution environment-aware. On Windows, the console `auto` backend launches LevelUpDiag through `wsl.exe --exec` and resolves the script path with `wslpath`, preventing Windows Python from producing misleading Linux-toolchain failures. It also added **AUDIT TOTAL**, a named N00-N10 DEBUG campaign for complete one-pass evidence collection, and aligned `levelupdiag_manifest.json` suite version with the package/UI version.

## Version 2.3.0

2.3.0 keeps the 2.2 core-stabilization policy and adds opt-in N06 diagnostics for modular product user interfaces. The new check validates only explicitly configured product roots, standalone/integration markers, and private-dependency tokens; it does not define the Koali UI architecture itself. Optional product absence is accepted as a valid independent-removal state.

It also fixes the desktop console's **DEBUG COMPLET** preset so it selects the `debug` campaign rather than `stabilization`.

## Version 2.2.0

2.2.0 changed the default workflow from broad debug to explicit **Koali core stabilization before subsystem integration**. It also requires the core Rust/native toolchain in N01 (`git`, `cargo`, `rustc`, `cc`), adds qualification-scope metadata to campaign summaries, and provides compatibility aliases plus `scripts/run_level.py` for older Koali Control Panel integrations.

## 2.6 — Store coverage and honest partial results

In version 2.6, `koali-system` ran N00 + N12 + N13. Version 2.7 separates the Store again. The **STORE** button
and `python levelupdiag.py run store` run N00 + N13 independently. N13 targets
`../koa-linux`, not the Spaces repository. Linux session probes are opt-in with
`store.runtime_checks=true`; Windows source checks do not certify the Linux store.
No packages are installed by this diagnostic. See [N13 setup and VM acceptance](docs/STORE_TESTS.md).

N12 reports accepted optional outages as WARN, disabled/missing live checks as
PARTIAL, and refuses redirects away from loopback. HTTP proxy environment variables
are ignored for local probes. Version 2.7 restores the Windows-only N00 + N12 campaign.


## Version 2.7 — Independent diagnostic scopes

The console now provides **AUDIT SANS VM** (`audit-local`) and **AUDIT QEMU**
(`audit-qemu`). Select the preset, then **LANCER SÉLECTION**. **AUDIT TOTAL**
keeps both scopes and documentation: missing VM prerequisites remain visible,
while available local tests still execute. **KOALI SYSTEM** remains native Windows,
N00 + N12. **STORE** remains an independent N00 + N13 campaign; its PARTIAL result
honestly means no end-to-end installation has been validated.

WSL probes and launches explicitly select `desktop_console.wsl_distro`
(default `Ubuntu-24.04`) and pass `--target` from `wsl_target_root`
(default `~/work/koa-linux`). On Rejean's configured distro this expands to
`/home/rejean/work/koa-linux`. The execution banner shows the distro and target.
The log button follows the report emitted by the completed run, including WSL paths.

Install this update together with the kOA-Linux gate-scope update. Use the Control
Panel's development preparation to refresh the imported Linux workspace after
copying the updated sources. Preserve existing `levelupdiag.config.local.json`;
check that it does not override `commands.offline` or `commands.system` with empty
arrays, or override the WSL distro/workspace with stale values.

`audit-local` covers configured source tests, including Store source tests in N10.
It does not validate a running Linux desktop. `audit-qemu` retains its prerequisite
levels and selects VM tests in N08–N10. RELEASE always selects the full runtime
scope. Scope and omitted commands are recorded in kOA gate reports.

See `UPDATE_20260919.md` for verification results and remaining image prerequisites.
