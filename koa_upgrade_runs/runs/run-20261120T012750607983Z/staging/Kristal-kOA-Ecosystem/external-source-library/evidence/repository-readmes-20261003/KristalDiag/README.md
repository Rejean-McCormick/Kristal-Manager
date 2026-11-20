# KristalDiag v7

**KristalDiag is the consolidated diagnostic, release-qualification and conformance suite for Kristal Standard v7.**

It supersedes the Kristal-specific `levelupdiag_kristal` harness while preserving its strongest operational mechanisms. It remains independent from the Standard and from implementations such as Kompiler.

```text
Kristal Standard v7 = normative contract
KristalDiag          = independent examiner / diagnostic harness
Kompiler             = one implementation / consumer
Kristal / Kristall   = artifacts or implementations under test
```

Target standard: **Kristal `7.0.0-draft.2`**. Portable compatibility boundary: **`kristal_state/6.0`**.

## Three diagnostic planes

| Range | Role |
|---|---|
| N00–N06 | neutral harness, repository, tooling and security diagnostics |
| K00–K14 | Kristal v7 semantic conformance and profile gating |
| R00–R04 | release engineering and ratification evidence |

This separation is intentional. A missing Git tag must not redefine Kristal semantics; an invalid Mesh must not be downgraded to repository hygiene.

## Quick start

```bash
python kristaldiag.py doctor
python kristaldiag.py list

# Neutral/repository campaigns inherited from LevelUpDiag
python kristaldiag.py run baseline /path/to/target
python kristaldiag.py run standard /path/to/target
python kristaldiag.py run deep /path/to/target
python kristaldiag.py run release /path/to/target

# Normative Kristal v7 qualification
python kristaldiag.py conform /path/to/target --profile V7-Reader
python kristaldiag.py conform /path/to/target --profile V7-Projection

# Evidence inspection
python kristaldiag.py triage-current /path/to/target
python kristaldiag.py verify-run /path/to/target/.kristaldiag/current/summary.json
```

Installed form:

```bash
pip install .
kristaldiag conform /path/to/kristall --profile V7-Projection
```

## Conformance profiles

- `V7-Reader`
- `V7-Mesh`
- `V7-Projection`
- `V7-Kristall`

Every profile includes the neutral read-oriented harness levels `N00`, `N01`, `N02`, `N03`, `N04`, and `N06`, then the profile-specific Kristal semantic levels. `N05` (declared command execution) and `R00–R04` are deliberately outside semantic profile definitions.

Required `SKIP` evidence is fail-closed as `BLOCKED` at K14. `V7-Kristall` may remain `PARTIAL` until independent interoperability evidence exists.

## Campaigns

`baseline` performs generic read-oriented repository diagnostics and executes no target command.

`standard` adds the core reader/identity checks for Kristal v7.

`deep` runs the neutral layer plus all K00–K13 semantic diagnostics. Declared validators in N05 still require `--allow-exec`.

`release` extends `deep` with R00–R04 release-engineering evidence: documentation/link integrity, reproducible diagnostic snapshot, Git/release identity, signature/trust surface and contract/TCK/profile consistency.

## Process isolation

Selected N/K/R levels execute in fresh Python processes by default. Dependencies are explicit and independent `parallel_safe` levels are scheduled concurrently with a bounded worker count. A crashed level cannot poison the interpreter state of another level.

```bash
kristaldiag run deep TARGET --jobs 4
kristaldiag run deep TARGET --jobs 4 --fail-fast
```

## Execution and authority boundary

KristalDiag does not repair targets and grants no mutation or automation authority.

Target commands are never guessed. N05 only executes validators explicitly declared in `kristaldiag.config.json`, and only with `--allow-exec`. Kristal implementation hooks use explicit argv arrays from `kristaldiag-driver.json`, `shell=False`, bounded timeouts, and also require `--allow-exec`.

Every conformance verdict states:

```json
{
  "qualification_only": true,
  "authority_granted": false
}
```

The complete target tree is fingerprinted before and after a run. Unauthorized mutation makes K14 return `ERROR`.

## Evidence

```text
.kristaldiag/
├── current/
│   ├── effective_config.json
│   ├── levels/<ID>/result.json
│   ├── summary.json
│   ├── summary.txt
│   ├── report.md
│   ├── conformance-verdict.json
│   └── evidence-manifest.json
├── current-run.json
└── runs/<run_id>/...
```

`verify-run` validates report schemas, cross-file identity, verdict coherence and every SHA-256 in the evidence manifest.

## LevelUpDiag compatibility

The former Kristal-specific LevelUpDiag harness is consolidated here. A `levelupdiag.py` compatibility shim preserves the common `doctor`, `list`, `show-config`, `run baseline|standard|deep|release`, and `verify-run` workflows.

See [`docs/CONSOLIDATION.md`](docs/CONSOLIDATION.md).

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/LEVELS.md`](docs/LEVELS.md)
- [`docs/CONFORMANCE.md`](docs/CONFORMANCE.md)
- [`docs/CONFIG_REFERENCE.md`](docs/CONFIG_REFERENCE.md)
- [`docs/OPERATING_MODEL.md`](docs/OPERATING_MODEL.md)
- [`docs/CI_INTEGRATION.md`](docs/CI_INTEGRATION.md)
- [`docs/DRIVER.md`](docs/DRIVER.md)
- [`docs/REPORTING.md`](docs/REPORTING.md)
- [`docs/SECURITY.md`](docs/SECURITY.md)
- [`docs/CONSOLIDATION.md`](docs/CONSOLIDATION.md)
