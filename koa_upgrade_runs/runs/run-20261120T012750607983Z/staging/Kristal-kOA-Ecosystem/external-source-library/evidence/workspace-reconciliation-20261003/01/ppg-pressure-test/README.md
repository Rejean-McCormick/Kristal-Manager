# Partners for Public Good: Pressure-Test Koali

**Status:** Open public call  
**Version:** 1.0  
**Published:** 2026-08-17  
**PPG public sources last checked:** 2026-08-17

> **Independent public call. This repository does not imply affiliation, endorsement, partnership, or participation by Partners for Public Good.**

Partners for Public Good is building a public-sector technology practice around hands-on implementation and governance support, supported technology pilots, product feedback, vendor accountability, and learning from what works in real government environments.

Koali makes concrete architectural claims in exactly that terrain.

I am putting those claims in public and asking PPG to challenge them under real institutional constraints.

> **Partners for Public Good: pressure-test Koali against government reality.**

This is not a request for endorsement, adoption of the broader kOA initiative, or validation of a worldview. It is an invitation to take a bounded technical object, apply institutional constraints that matter in practice, and identify where its architecture fails, overreaches, duplicates existing solutions, or adds more burden than value.

---

## The object under test

**Koali** — currently documented in the [`kOA-Linux`](https://github.com/Rejean-McCormick/kOA-Linux) repository — is a local-first, offline-capable, modular operating environment for governed digital systems.

Its current constitutional and system documentation makes strong claims about:

- explicit authority;
- component and data separation;
- profile-scoped requirements rather than universal configuration;
- optional and removable external integrations;
- bounded external AI;
- fail-closed authority;
- safe degradation;
- offline continuity;
- selective audit and recourse;
- critical-transition receipts;
- portability, restoration, and credible exit.

Those claims should not be accepted because their architect believes in them.

They should survive contact with institutions that know what technology implementation actually costs.

---

## The central Koali proposition

Government technology is heterogeneous by nature. Institutions already depend on different vendors, applications, records, workflows, departments, policies, networks, and legal authorities.

Koali does **not** start from the proposition that these should converge onto one platform.

It asks a different question:

> **Can independently governed systems cooperate under explicit, inspectable boundaries without being absorbed into one platform or silently transferring authority?**

This is the distinction behind the Koali approach:

> **Broad operating environment. Distributed authority. Profile-scoped deployment.**

and:

> **Cooperation without absorption.**

A valid Koali profile can require one capability, make another optional, prohibit another, and leave an external service external. Optional components and integrations are not supposed to become global requirements simply because they are useful or common.

That discipline is central to the pressure test.

---

## How this repository connects to the existing ecosystem

This repo is intentionally **not** another kOA or Koali documentation center.

```text
Partners for Public Good public problem space
                    ↓
          this public call / test frame
                    ↓
      Koali / kOA-Linux — object under test
                    ↓
     ┌──────────────┼──────────────┐
     ↓              ↓              ↓
  Kristal       Konnaxion        Orgo
 knowledge      coordination     execution
     └──────────────┼──────────────┘
                    ↓
      independently governed systems
```

**Canonical routes:**

- [Koali / kOA-Linux](https://github.com/Rejean-McCormick/kOA-Linux) — the operating environment being pressure-tested.
- [kOA Digital Ecosystem](https://github.com/Rejean-McCormick/kOA_Digital_Ecosystem) — technical system-of-systems context; not the full kOA cultural/philosophical universe.
- [Kristal Framework](https://github.com/Rejean-McCormick/kristal-framework) — governed knowledge artifacts.
- [Konnaxion](https://github.com/Rejean-McCormick/Konnaxion) — public coordination and civic capabilities.
- [Orgo](https://github.com/Rejean-McCormick/Orgo) — organizational execution and operational continuity.

Other subsystems remain governed by their own repositories and should only enter a test when the selected government workflow actually requires them.

> **Reference the source that owns the claim. Do not make this repo the new owner.**

---

## Why PPG

PPG Tech's current public work is unusually relevant because it is explicitly concerned with the human and operational problems around government technology: cross-department collaboration, strategic procurement, AI governance, government/vendor relationships, supported pilots, implementation capacity, and measuring what works.

PPG has also publicly emphasized a point that matters here: governments are not asking for one tool that solves everything. They need better ways to test technology, govern it, work with vendors, and build internal capacity.

Koali should therefore be tested **as an environment for plural systems**, not pitched as another totalizing product.

→ [Why this call is directed to PPG](WHY_PPG.md)

---

## What I am asking PPG to test

Not whether every kOA application works.

Not whether every Koali feature is desirable.

The first test is more architectural:

> **Can Koali describe and govern a real public-sector technology environment without becoming the new source of hidden centralization it was designed to prevent?**

A useful pressure test could start with a government technology procurement and implementation lifecycle, then force Koali to represent:

- existing institutional systems rather than replacing them;
- real decision and legal authorities;
- data ownership and disclosure boundaries;
- external vendors and AI services;
- degraded and offline states;
- integration failure;
- component removal;
- audit obligations;
- operational exceptions;
- migration and exit.

If Koali cannot model those constraints without excessive complexity, the architecture needs to change.

→ [Claims under test](CLAIMS_UNDER_TEST.md)

→ [Proposed pressure-test method](PRESSURE_TEST.md)

→ [Hard questions](QUESTIONS.md)

### Repository map

| Document | Purpose |
|---|---|
| [SCOPE.md](SCOPE.md) | Establishes the boundary: kOA is the broader work; Koali is the institutional test object |
| [WHY_PPG.md](WHY_PPG.md) | Shows why PPG's current public work creates a serious test environment |
| [CLAIMS_UNDER_TEST.md](CLAIMS_UNDER_TEST.md) | Converts Koali architecture into claims that can fail |
| [PRESSURE_TEST.md](PRESSURE_TEST.md) | Defines a workflow-first stress-test method |
| [QUESTIONS.md](QUESTIONS.md) | Lists the questions most likely to expose weak assumptions |
| [SOURCES.md](SOURCES.md) | Routes every technical or PPG claim back to its canonical source |

---

## Why this call is public

Koali is public. Its architectural claims are inspectable. A critique of public-interest infrastructure should be able to exist independently of whether a private message receives a response.

Publishing the call creates a durable object that anyone can inspect:

**claim → source → challenge → evidence → revision**

That is also consistent with the architecture being proposed.

PPG is free to ignore, reject, privately critique, or publicly engage with the call. The point of publishing it is not to manufacture endorsement. It is to make the proposition difficult to confuse with a private sales pitch.

---

## kOA and Koali are not synonyms

Koali is part of the broader **kOA** body of work. kOA is intentionally larger than a technical operating environment and includes technical systems, civic and political theory, cultural and narrative work, King Klown, and separate speculative and metaphysical exploration.

This call does not sanitize or redefine that larger body of work.

It sets a test boundary:

> **Koali can be evaluated as an institutional operating environment without requiring PPG to validate or endorse the rest of kOA.**

The fuller scope boundary is documented in [SCOPE.md](SCOPE.md).

---

## Source policy

This repository is an interface, not a new documentation authority.

> **Reference, do not replicate.**

Canonical Koali claims belong to the live Koali / `kOA-Linux` documentation. Claims about Kristal, Konnaxion, Orgo, SmartVote, or other systems belong to their own repositories.

Implementation state must be checked against current code, contracts, tests, releases, and evidence.

> **Documented ≠ Implemented ≠ Tested ≠ Validated.**

→ [Canonical sources](SOURCES.md)

---

## The call

**Partners for Public Good: bring a government workflow, constraint set, or failure mode that your team understands deeply. Try to make Koali fail against it.**

A useful outcome is not agreement. It is knowing which claims survive and which ones must be revised.

**Don't endorse Koali. Try to break it.**
