# RepoDiag

RepoDiag is a generic external repository diagnostics runner. It inspects a target
repository, executes only declared validations, records bounded evidence, and
produces machine-readable per-level and campaign reports.

It is intentionally maintained as its **own repository**. Target projects do not
need to vendor RepoDiag.

## Basic use

From the target repository:

```text
python C:\path\to\RepoDiag\repodiag.py doctor
python C:\path\to\RepoDiag\repodiag.py run standard
```

Or select the target explicitly from anywhere:

```text
python C:\path\to\RepoDiag\repodiag.py --target C:\path\to\target run standard
```

`REPODIAG_TARGET` can also provide the default target path.

Runtime evidence is written below `<target>/.repodiag/` and should normally be
ignored by the target repository.

## Core model

The neutral diagnostic levels are:

- N00 — Diagnostic Integrity
- N01 — Target Context
- N02 — Repository Inventory
- N03 — Repository Hygiene
- N04 — Tooling Discovery
- N05 — Declared Validations
- N06 — Security Hygiene

The framework separates discovery from execution: it does not invent build/test
commands merely because a manifest file exists. Commands run by N05 must be
declared in configuration.

## simdjson RVV-VLA profile

This repository also carries the current RVV-VLA project profile used with the
companion simdjson repository:

- R10 — RVV Source Contract
- R20 — GCC Global VLEN Matrix
- R30 — GCC Runtime Dispatch Matrix
- R40 — Clang Global VLEN Matrix
- R50 — Upstream Acceptance

Useful campaigns:

- `rvv-static`
- `rvv`
- `rvv-full`
- `deep`

Example:

```text
python repodiag.py --target C:\mycode\Simdjson\simdjson-rvv-vla run rvv
```

The RVV levels delegate cross-build/QEMU work to the target repository's own
`scripts/rvv/run_tests.py`. The authoritative RVV tests stay with simdjson.

## Configuration

Committed defaults live in `repodiag.config.json`.
Machine-local overrides may be placed in `repodiag.config.local.json`.
An example is provided as `repodiag.config.local.example.json`.

Important safety defaults:

- target mutation disabled
- network access disabled
- bounded command output capture
- generated evidence isolated under `.repodiag/`
- tracked-file protection enabled

## Commands

```text
python repodiag.py doctor
python repodiag.py list
python repodiag.py show-config
python repodiag.py run baseline
python repodiag.py run standard
python repodiag.py run N03
python repodiag.py run rvv
python repodiag.py verify-run <target>/.repodiag/runs/<run-id>/summary.json
```

Windows and POSIX launchers are provided as `RUN_REPODIAG.bat` and
`RUN_REPODIAG.sh`.

## Documentation

See `docs/` for architecture, configuration, level contracts, result format,
security model, adaptation guidance, and the simdjson RVV-VLA profile.
