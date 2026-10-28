# Operating model

KristalDiag is normally used in three modes.

## 1. Read-only diagnostics

```bash
kristaldiag run baseline TARGET
kristaldiag run v9 TARGET
```

No target command is executed.

## 2. Semantic conformance

Kristal v9:

```bash
kristaldiag conform TARGET --profile V9-State-Reader
kristaldiag conform TARGET --profile V9-Builder
kristaldiag conform TARGET --profile V9-Materializer
kristaldiag conform TARGET --profile V9-Publisher
kristaldiag conform TARGET --profile V9-Full
```

Historical v7 profiles remain available:

```bash
kristaldiag conform TARGET --profile V7-Reader
kristaldiag conform TARGET --profile V7-Mesh
kristaldiag conform TARGET --profile V7-Projection
kristaldiag conform TARGET --profile V7-Kristall
```

## 3. Release audit

```bash
kristaldiag run release TARGET
kristaldiag verify-run TARGET/.kristaldiag/current/summary.json
```

The release campaign is deliberately broader than a semantic profile: it adds documentation, reproducible snapshot, Git/release identity and vendored-contract checks.

## Exit posture

`PASS` is success. `WARN`/`PARTIAL` signal usable but incomplete evidence. `BLOCKED`/`FAIL` are release-significant. `ERROR`/`INFRA_ERROR`/`CONFIG_ERROR` mean the diagnostic evidence itself cannot be trusted as a successful qualification.
