# Reporting and evidence

Each run writes an immutable-style evidence tree under `.kristaldiag/current/` and copies it to `.kristaldiag/runs/<run_id>/`.

```text
current/
├── effective_config.json
├── levels/<level-id>/result.json
├── summary.json
├── summary.txt
├── report.md
├── conformance-verdict.json
└── evidence-manifest.json
```

`summary.json` aggregates level status. `conformance-verdict.json` is the bounded qualification statement. `evidence-manifest.json` hashes every other persisted evidence file.

`verify-run` performs offline verification of schemas, run identifiers, level/verdict consistency and SHA-256 evidence hashes.

Verdicts: `PASS`, `WARN`, `FAIL`, `SKIP`, `BLOCKED`, `PARTIAL`, `ERROR`, `INFRA_ERROR`, `CONFIG_ERROR`.

An optional level that executes and observes a real `FAIL` still fails the diagnostic campaign. “Optional” changes completeness requirements, not observed truth.

`verify-run SUMMARY` verifies only the internal evidence tree: schema consistency,
reported level verdicts and file SHA-256. `verify-run SUMMARY --require-pass` additionally
returns a failure exit code if the observed summary verdict is not `PASS`.
Neither mode establishes signer authenticity, independent C1 approval or a C2 grant.
The evidence manifest is **not signed**, and an attacker controlling the entire evidence
tree could replace both evidence files and their hashes. Treat its provenance separately.

All evidence paths are interpreted as canonical relative POSIX paths, restricted to the
evidence tree; symlinks, traversal and absolute names are rejected.
