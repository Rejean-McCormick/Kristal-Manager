# Kor — 0.7.0

Kor is the personal mobile access layer for the kOA ecosystem: a **filtered, simplified, action-oriented projection of authorized Konnaxion and Orgo surfaces**. Konnaxion/Orgo keep domain authority, IK keeps canonical cross-system interaction semantics where adopted, and Kor owns the phone experience, local/offline UX, attention orchestration, human projection/delivery and device capture.

Kor does **not** define a parallel product hierarchy. A World remains the root context and the primary phone navigation is derived from owner navigation. Landing pages stay intentionally sparse; deeper pages can use the adaptive `kor.surface/1.2` block grammar when the situation needs forms, checklists, capture, evidence, timelines, maps, comparisons, discussion, media, relationships or status.

## Executable 0.7 state

The service accepts `kor.surface/1.0`, `1.1` and `1.2`. The Android client implements:

- stable owner-derived World navigation, hierarchical Back, deep links and searchable `More`;
- lexicographic A0–A7 attention classes, bounded home slots, revision-bound seen/dismiss/snooze state and policy-gated cross-World critical attention;
- owner freshness/staleness policy and fail-closed sensitive actions;
- adaptive 1.2 blocks with encrypted drafts and accessibility/degraded fallbacks;
- local-first photo, audio, file, QR and foreground-location capture with encrypted artifact storage, SHA-256 digests, upload/retry/delete and owner-action attachment references;
- Android Keystore device identity, OIDC Authorization Code + PKCE, encrypted token/cache storage and biometric gating;
- FCM wake-up/attention delivery when configured plus periodic WorkManager pull synchronization as the recovery path;
- localized English/French app chrome, while owner-projected content keeps its own locale/revision/provenance.

Owner actions remain fail-closed: a button never becomes business success locally. Kor queues input/captures, the trusted deployment binding builds the canonical owner/IK interaction, and the UI keeps transport, admission and owner outcome distinct.

Konnaxion/Orgo publisher adapters and the canonical deployment binding are external integration dependencies; the default runtime does not impersonate them.

## Run

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.lock
pip install --no-build-isolation --no-deps -e .
kor init-local
. var/local/env.sh
kor serve
```

```bash
make check
```

- Service: `src/kor_service/`
- Native Android client: `android/`
- Surface schema: `schemas/owner-surface.schema.json`
- Executable API: `openapi/kor-service.openapi.json`
- Tests/fixtures: `tests/`
- Product and architecture: `docs/00_INDEX.md`
- Implementation details: `IMPLEMENTATION.fr.md`
- Validation snapshot: `VALIDATION.md`
- Decisions: `adr/0020-mobile-projection-of-konnaxion-orgo.md`, `adr/0021-attention-and-stable-navigation.md`, `adr/0022-adaptive-surface-runtime.md`

`make release-check` intentionally remains stricter than the implementation test suite: deployment-specific IK/Profile conformance, owner adapters, Play/privacy review and real-device field validation are release obligations, not behavior Kor should fake locally.
