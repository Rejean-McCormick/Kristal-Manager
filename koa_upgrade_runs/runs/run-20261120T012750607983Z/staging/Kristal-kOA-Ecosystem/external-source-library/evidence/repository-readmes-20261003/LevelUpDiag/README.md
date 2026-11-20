# LevelUpDiag Neutral Frame

**Version:** 1.0.0  
**Mode:** copy-in diagnostics frame  
**Runtime dependencies:** Python 3.10+ standard library only

LevelUpDiag is a neutral diagnostics frame designed to be copied as the `levelupdiag/` directory inside a repository that must be diagnosed.

It deliberately makes **no assumption** that the target has a web UI, API, backend, frontend, database, service, package manager, test framework, build system, or release process.

The frame provides a small universal baseline, capability discovery, structured evidence, declared-validator execution, campaign aggregation, process isolation, timeouts, redaction, and extension points. After copying it into a repository, you can keep it generic or adapt it in place to the target.

## Quick start

Recommended layout:

```text
my-target-repository/
├── ... target files ...
└── levelupdiag/            <- copy this whole directory here
```

Run from any directory:

```bash
python levelupdiag/levelupdiag.py doctor
python levelupdiag/levelupdiag.py run baseline
python levelupdiag/levelupdiag.py run standard
```

On Windows you can also use:

```bat
levelupdiag\RUN_LEVELUPDIAG.bat standard
```

On POSIX systems:

```bash
./levelupdiag/RUN_LEVELUPDIAG.sh standard
```

By default the target repository is the **parent directory of `levelupdiag/`**. Override it with `--target` when needed.

Generated evidence is written under:

```text
<target>/.levelupdiag/
```

The source frame itself remains under `levelupdiag/` and should normally be committed. Runtime evidence under `.levelupdiag/` should normally be ignored.

## Universal levels

| ID | Level | Purpose |
|---|---|---|
| N00 | Diagnostic Integrity | Validate the diagnostics frame itself before trusting its output. |
| N01 | Target Context | Resolve target, runtime context, VCS state, paths and basic executability. |
| N02 | Repository Inventory | Build bounded, technology-neutral evidence about repository shape and capabilities. |
| N03 | Repository Hygiene | Detect broken links, conflict markers, path hazards and oversized source artifacts. |
| N04 | Tooling Discovery | Detect manifests, lock files, automation surfaces and candidate local tools without assuming they are required. |
| N05 | Declared Validations | Run only validators explicitly declared in configuration. Empty by default. |
| N06 | Security Hygiene | Perform conservative, bounded hygiene checks without claiming a security audit. |

There is intentionally **no universal “API”, “UI”, “service”, “accessibility”, “visual”, or “release” level**. Add such levels only when the target actually has those contracts.

## Campaigns

`baseline` runs only universal read-oriented diagnostics. `standard` also evaluates the declared-validator level; when none are declared it performs no guessed command and remains valid. `deep` is provided as an extension campaign and currently has the same neutral set as `standard`; adapt it only when deeper target-specific checks are justified.

Campaign verdicts preserve distinctions between:

```text
PASS / WARN / FAIL / SKIP / BLOCKED / PARTIAL / ERROR / INFRA_ERROR / CONFIG_ERROR
```

A required `SKIP`, `BLOCKED`, `PARTIAL`, or missing result is never silently treated as a pass.

## Configuration

The committed file `levelupdiag.config.json` contains neutral defaults. Optional machine-local overrides can be put in `levelupdiag.config.local.json` (ignored by default).

Most repositories need **no configuration** for the baseline campaign.

Declared validators are intentionally explicit:

```json
{
  "validators": [
    {
      "id": "project-tests",
      "name": "Project test suite",
      "command": ["your-test-command", "--flag"],
      "cwd": ".",
      "required": true,
      "timeout_seconds": 900,
      "mutates_target": false,
      "network": false
    }
  ]
}
```

LevelUpDiag never invents a test/build command and executes it merely because a manifest exists. Discovery and execution are separate phases.

## Safety model

Default behavior:

- target is treated as read-only except for `.levelupdiag/` evidence;
- commands use argument arrays and `shell=False`;
- validator commands must be declared explicitly;
- validator declarations marked `mutates_target: true` are blocked unless mutation is explicitly enabled;
- validator declarations marked `network: true` are blocked unless network is explicitly enabled;
- every external command has a timeout;
- stdout/stderr stored in reports is bounded and redacted;
- target paths are normalized and checked;
- tracked VCS state is sampled before/after a campaign to detect unexpected changes;
- the diagnostics source directory and generated evidence directory are excluded from repository scans by default.

This frame cannot sandbox arbitrary commands. A declared validator has the same OS permissions as the user running it.

## Exit codes

| Code | Meaning |
|---:|---|
| 0 | Campaign accepted (`PASS` or `WARN`) |
| 10 | Target validation failure (`FAIL`) |
| 20 | Required evidence incomplete or blocked |
| 30 | Configuration, infrastructure, or diagnostics-tool error |
| 64 | CLI usage error |

## Adapting after copy

Read `docs/ADAPTATION_GUIDE.md` before adding target-specific diagnostics. The key rule is: **model real target contracts; do not preserve generic levels merely for symmetry.**

Useful commands:

```bash
python levelupdiag/levelupdiag.py list
python levelupdiag/levelupdiag.py show-config
python levelupdiag/levelupdiag.py run N03
python levelupdiag/levelupdiag.py run standard --jobs 4
python levelupdiag/levelupdiag.py verify-run .levelupdiag/runs/<run-id>/summary.json
```

## Repository identity

This is a neutral source frame, not a central runtime dependency. Once copied into a target repository, the copy may evolve independently.
