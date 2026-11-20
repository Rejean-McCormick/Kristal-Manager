````markdown
# VM-ENGINE v0 — Voting Machine (README)  
_Component 09/89 • Entry point for developers and reviewers_

> **Purpose**: This engine implements deterministic tabulation/allocation with explicit gates and frontier handling. It runs fully offline, produces canonical artifacts, and is verified by a normative test pack (Annex B). Code behavior is subordinate to the Specs (**Docs 1–7**) and Annexes (**A–C**).

---

## What this is (in 4 bullets)

- **Deterministic** pipeline: same inputs → byte-identical outputs across OS/arch.  
- **Offline by default**: builds and tests run with `--locked` and no network I/O.  
- **Canonical JSON** everywhere: UTF-8, **LF** line endings, **sorted keys**.  
- **Ties**: resolved deterministically (policy-driven); when policy is random, a **seeded RNG (ChaCha20)** is used and recorded in `RunRecord` only if a random tie actually occurred.

---

## Quickstart (copy-paste)

> Requires Rust (toolchain pinned via `rust-toolchain.toml`) and `cargo`. See **Troubleshooting** for Windows line-ending notes.

### 1) Build the CLI

**Bash (Linux/macOS/Git Bash on Windows)**

```bash
rustup show
cargo build --locked -p vm_cli
````

**PowerShell**

```powershell
rustup show
cargo build --locked -p vm_cli
```

### 2) Run a tiny Annex-B fixture

> Uses the minimal fixture in `fixtures/annex_b/part_0` (or `VM-TST-001` if you prefer—both are included in Annex B).

**Bash**

```bash
./target/release/vm_cli run \
  --manifest fixtures/annex_b/part_0/manifest.json \
  --output   artifacts/run
```

**PowerShell**

```powershell
.\target\release\vm_cli run `
  --manifest fixtures\annex_b\part_0\manifest.json `
  --output   artifacts\run
```

Artifacts produced:

```
artifacts/run/
  result.json        # canonical result (RES:<hash>)
  run_record.json    # provenance (RUN:<ts>-<hash>)
  frontier_map.json  # optional, when enabled by manifest/policy
```

### 3) Determinism smoke (same seed twice → identical bytes)

**Bash**

```bash
SEED=1
./target/release/vm_cli run --manifest fixtures/annex_b/part_0/manifest.json --rng-seed $SEED --output artifacts/run1
./target/release/vm_cli run --manifest fixtures/annex_b/part_0/manifest.json --rng-seed $SEED --output artifacts/run2
cmp -s artifacts/run1/result.json artifacts/run2/result.json
cmp -s artifacts/run1/run_record.json artifacts/run2/run_record.json
echo "OK: byte-identical"
```

**PowerShell**

```powershell
$SEED=1
.\target\release\vm_cli run --manifest fixtures\annex_b\part_0\manifest.json --rng-seed $SEED --output artifacts\run1
.\target\release\vm_cli run --manifest fixtures\annex_b\part_0\manifest.json --rng-seed $SEED --output artifacts\run2
if ((Get-FileHash artifacts\run1\result.json).Hash -eq (Get-FileHash artifacts\run2\result.json).Hash -and
    (Get-FileHash artifacts\run1\run_record.json).Hash -eq (Get-FileHash artifacts\run2\run_record.json).Hash) {
  "OK: byte-identical"
} else { throw "Mismatch" }
```

---

## Determinism & offline guarantees (stated)

* **Canonical serialization**: UTF-8, **LF**, **sorted JSON keys** at all object levels; arrays ordered per Doc 1.
* **No network I/O** at runtime; builds/tests use `--locked`; Cargo is configured **offline by default** (`.cargo/config.toml`).
* **Tie policy** (`VM-VAR-050`) may be deterministic (order-index) or random. Random tie-breaks use a **seed** (`VM-VAR-052`, non-FID) and are echoed in `RunRecord` **only if** a random tie occurred.
* **IDs**: `RES:<hash>`, `RUN:<ts>-<hash>`, and optional `FR:<hash>` are computed from canonical bytes.
* **Reporting** (Doc 7): one-decimal percentages; renderer **never recomputes** outcomes—reads canonical artifacts only.

---

## Repository map (short)

```
crates/
  vm_core/       # core types & invariants
  vm_io/         # canonical I/O, schemas bindings
  vm_algo/       # allocation, gates, edge cases (Doc 4)
  vm_pipeline/   # state machine orchestration (Doc 5)
  vm_report/     # renderers (JSON/HTML); no recomputation
  vm_cli/        # command-line interface
  vm_app/        # optional Tauri UI (not built by default)

fixtures/
  annex_b/       # canonical test pack (Annex B)

schemas/         # normative JSON Schemas (Doc 1)

artifacts/       # outputs created by runs/tests (ignored by git)
dist/            # reproducible release archives (Makefile)

Doc 1 — Database Specification (Entities, Fields, Relationships).md
Doc 2 — Common Variables Specification (Core, Operational Defaults, Advanced Controls).md
Doc 3 — Technical Platform & Release Policy.md
Doc 4 — Algorithm Specification (Steps, Allocation, Gates & Edge Cases).md
Doc 5 — Processing Pipeline Specification (State Machine & Functions).md
Doc 6 — Test Specifications (Allocation, Gates, Frontier & Determinism).md
Doc 7 — Reporting Specification (Structure, Templates & Visual Rules).md
Annex A — Variable Canonical Reference Table.md
Annex B — Canonical Test Pack.md
Annex C — Glossary & Definitions.md
```

---

## Specs are normative

If the code and the docs disagree, the **docs win**. See:

* **Doc 1** (entities/fields/relationships; canonical JSON rules)
* **Doc 2** (variable set & FID membership; Included vs Excluded)
* **Doc 4** (algorithmic steps; tie-resolution timing)
* **Doc 5** (state machine; step ordering and gates)
* **Doc 6** (test matrix, oracle expectations, determinism cases)
* **Doc 7** (reporting rules: sections, ordering, one-decimal presentation)
* **Annex A/B/C** (IDs & ranges, canonical tests, definitions)

---

## How to run tests

**Unit/integration tests**

```bash
cargo test --locked --workspace
```

**Canonical fixtures (Annex B)**

```bash
# Small sample:
./target/release/vm_cli run --manifest fixtures/annex_b/VM-TST-001/manifest.json --output artifacts/tst001

# Compare with expected (jq pretty-sort is optional):
jq -S . fixtures/annex_b/VM-TST-001/expected/result.json     > /tmp/exp.json
jq -S . artifacts/tst001/result.json                         > /tmp/got.json
diff -u /tmp/exp.json /tmp/got.json
```

**Makefile helpers**

```bash
make ci         # fmt → lint → build → test → fixtures → verify → hash
make fixtures   # run a minimal Annex B subset
make verify     # double-run determinism smoke
make dist       # reproducible archives in dist/
```

---

## Building reports (Doc 7)

* Renderers in `vm_report` emit JSON/HTML using **only** canonical inputs; **no recomputation**.
* Percentages are shown with **one decimal** (round-half-up once; no chained rounding).
* Fonts/assets are bundled or offline; **no remote requests** at render time.

---

## Troubleshooting

* **CRLF on Windows**: configure Git with LF policy (repo includes `.gitattributes`); avoid CRLF.

  ```
  git config core.autocrlf false
  ```
* **First build without `vendor/`**: Cargo is offline by default. Temporarily fetch, then restore offline:

  ```bash
  CARGO_NET_OFFLINE=0 cargo fetch
  # optionally: cargo vendor && commit vendor/
  ```
* **RNG seed**: Provide as an integer or hex string. If **no random tie occurs**, changing the seed **must not** change outputs.
* **Manifest inputs**: Each run must provide **exactly one** of: *ballots* **or** *precomputed tally*. Missing/extra → validation error.
* **jq not installed**: Use byte comparison (`cmp`/`fc`) or Python:

  ```bash
  python - <<'PY'
  ```

import sys, json
a=json.load(open('artifacts/run1/result.json')); b=json.load(open('artifacts/run2/result.json'))
print(a==b)
PY

```

---

## License & security

- License: see **`LICENSE`**.  
- Security: see **`SECURITY.md`**. No telemetry. No bug bounty.

---

## Contributing

Use `pre-commit` if installed (`.pre-commit-config.yaml` provides fast local gates). Submit PRs that reference the relevant sections of **Docs 1–7** and **Annex A/B**.

---
```
