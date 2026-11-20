# Interaction Kernel

Interaction Kernel (IK) is a distributed interoperability protocol and reference implementation for autonomous systems. It is not an operational database, artifact store or distributed transaction coordinator.

**Status:** `v2.0-draft` reference implementation (`2.0.0-dev.2`).

The repository contains:

- normative JSON Schemas for IK records and artifact interchange;
- versioned Profile descriptors and payload schemas;
- Python and TypeScript runtimes;
- RFC 8785 JCS + SHA-256 semantic request fingerprinting;
- a reusable admission pipeline;
- TCK/golden vectors shared across runtimes;
- Konnaxion, Orgo, DaaT/Kristal, kOA-Linux and UCKK reference adapters;
- a pinned Kristal portable `6.0.0` dependency lock plus a pinned Kristal `7.0.0-draft.3.1` design baseline;
- GitHub-native technical documentation.

## Architecture

```text
Konnaxion  <----------- IK ----------->  Orgo
    \                                   /
     \                                 /
      +---------- IK ---------->  DaaT ---------- IK ----------> UCKK
                                      |
                         portable v6 contract / v7 baseline
                                      |
                              Kristal / Kristall
```

Konnaxion↔Orgo remains direct. Kristal is not a mandatory relay. DaaT is the narrow IK anti-corruption/admission boundary in front of Kristal/Kristall; the stable machine identifier is `daat`. DaaT performs explicit contract mapping, not source acquisition, general corpus normalization, artifact storage, or Kristall semantic-identity authoring. UCKK publication is an optional participant integration: DaaT sends immutable Kristal publication references through IK, while the artifact bytes may remain owned by the kOA Mediatheque.

## Quick checks

### Python

```bash
cd runtime/python
PYTHONPATH=src python -m unittest discover -s tests -v
```

On PowerShell, use `$env:PYTHONPATH = "src"` before the test command, or run the repository-level `scripts/test_all.ps1`.

### TypeScript

```bash
cd runtime/typescript
npm run build
npm test
```

The TypeScript runtime intentionally has no runtime dependencies.

## Repository map

```text
contracts/      IK schemas, Profiles and payload schemas
locks/          immutable downstream dependency locks
runtime/        Python + TypeScript reference runtimes
adapters/       Konnaxion / Orgo / DaaT / kOA-Linux / UCKK reference adapters
tck/            cross-language golden vectors
scripts/        validation utilities
docs/           technical documentation + ADRs
```

## Accepted architecture decisions

- Runtime Pack: Konnaxion selects/requests; local platform activation is executed by the configured `RuntimePackActivationPort` owner (kOA-Linux when present).
- Kristal compatibility: portable artifacts remain pinned to Standard `6.0.0` and canonicalization `kristal.v6:jcs-rfc8785`; the current additive Kristal/Kristall design baseline is pinned separately at `7.0.0-draft.3.1`.
- Konnaxion handoff: `DecisionRecord` is the canonical immutable handoff contract.
- Request fingerprint: semantic projection → RFC 8785 JCS → SHA-256.
- State/artifact boundary: each participant owns its mutable operational state; IK transports interactions and references; DaaT performs explicit versioned contract mapping into Kristal-native interfaces; no distributed cross-owner database transaction is required. DaaT does not own acquisition, corpus normalization, or Kristall semantic identity.
- Kristal → UCKK publication: UCKK-specific mapping is an IK adapter; canonical Kristal ownership remains upstream, and the kOA Mediatheque may continue to own immutable publication bundle bytes.

See [`docs/`](docs/README.md).
