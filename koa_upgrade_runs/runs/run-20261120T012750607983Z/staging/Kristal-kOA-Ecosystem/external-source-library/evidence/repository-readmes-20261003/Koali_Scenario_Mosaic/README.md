# Koali Scenario Mosaic V2

**Koali, the Sociotechnical Operating System**

Scenario Mosaic V2 is a bilingual, static-first atlas of **36 canonical sociotechnical problems**. The public experience now starts from problems people recognize, then exposes failure mechanisms, scale, urgency, stakes, real-world parallels, and the Koali response path.

## What changed from V1

V1 organized 120 examples into eight equal capability territories. V2 intentionally removes that symmetry.

- **36 canonical scenarios**, not 120 filler-balanced examples;
- **8 problem families** with variable scenario counts;
- **problem-first navigation**, not capability-first navigation;
- facets for **problem family, scale, urgency, and stakes**;
- explicit **failure mechanisms** and **coordination gap**;
- documented **real-world parallels** in every scenario;
- selected scenario pages now expose problem anatomy and the full sourced editorial scenario;
- the 24 Koali response patterns remain embedded in scenario metadata;
- Astro remains **static-first, bilingual, responsive, keyboard/touch accessible, and deployable on Netlify**.

## Content source of truth

The localized Markdown files are the source of truth:

```text
src/content/scenarios/en/SCN-001.md ... SCN-036.md
src/content/scenarios/fr/SCN-001.md ... SCN-036.md
```

Each file contains both the localized narrative and the V2 metadata used by the interface:

- `problem_family`
- `failure_mechanisms`
- `scale`
- `urgency`
- `stakes`
- `coordination_gap`
- `domains`
- `koali_patterns`
- `koali_components`
- `real_case_ids`
- evidence/runtime status

No separate 120-entry scenario metadata file remains.

## Public routes

```text
/                  → browser-language choice
/en/uses/          → English Mosaic
/fr/uses/          → French Mosaic
/en/uses/SCN-001/  → English scenario
/fr/uses/SCN-001/  → French scenario
```

Legacy `/uses/` routes still redirect to English.

## Mosaic interface

The interaction shell retained from V1 includes:

- hexagonal Mosaic identity;
- hover/focus selection;
- touch preview rather than accidental navigation;
- swipe next/previous on coarse-pointer devices;
- magnetic family labels in the production Astro build;
- responsive selected-scenario preview;
- `Surprise me` and reset;
- EN/FR route continuity.

V2 adds multi-axis filtering:

- problem family;
- scale;
- urgency;
- stakes;
- free-text search across titles, mechanisms, domains, Koali patterns/components, real cases and response copy.

## Selected scenario page

A selected scenario shows:

1. a scenario image, followed by a compact scale / urgency / coordination-gap / stakes row;
2. problem family, hook and failure mechanisms;
3. Koali system path;
4. five problem-anatomy hexagons:
   - what breaks;
   - who holds part of the picture;
   - Koali response;
   - real-world parallels;
   - what success looks like;
5. the complete sourced scenario document.

Real cases are analogues of the documented failure mechanism. They are **not claims that Koali would have prevented a specific event or guaranteed a different outcome**.


## Scenario images

V2.2 restores the V1 responsive image-preparation pipeline. Final source artwork is optional and can arrive progressively.

Place a square master at exactly **1254×1254 PNG** here:

```text
src/assets/scenario-images/SCN-001.png
...
src/assets/scenario-images/SCN-036.png
```

`npm run images:build` uses Sharp + Lanczos3 to generate:

```text
public/scenarios/images/SCN-001-418.png
public/scenarios/images/SCN-001.png      # 627×627 default
```

The browser receives a `srcset` containing 418w and 627w plus the existing `sizes` contract. If a master is absent but a usable public PNG already exists, the production build can regenerate the responsive set from that public file. If no final PNG exists at all, the existing family-level SVG fallback remains active.

The normal commands run the preparation automatically:

```bash
npm run dev
npm run build
npm run preview:offline
```

To inspect the image pipeline directly:

```bash
npm run images:build
npm run images:validate
```

## French public taxonomy

Internal metadata remains language-neutral (`critical`, `context_loss`, `high`, etc.). Public French UI uses context-aware localization so grammatical values remain correct: for example `Urgence: Critique`, `Déficit de coordination: Élevé`, and `Perte de contexte · Dilution du signal · Absence d’escalade · Fausse certitude`. Real-world case names also use localized display titles while retaining original source links.

## Develop

Node `>=22.12.0` is required.

```bash
npm install
npm run validate
npm run dev
npm run build
```

The V2 validator checks the bilingual 36-scenario contract, source/evidence minimums, localized real-case registry, French public labels, and family image fallbacks.

## Zero-install preview

```bash
npm run preview:offline
```

Then open `START.html` or `preview/index.html` directly. The offline preview contains both Mosaic languages and all 72 localized scenario pages.

## Deployment

`netlify.toml` retains the static Astro deployment model. Production output is `dist/`.

## Historical documentation

The `docs/` folder contains substantial V1 design history. It remains useful as rationale for the interaction shell, responsive preview, bilingual architecture and magnetic labels, but the V2 source of truth is this README plus `docs/60_V2_PROBLEM_FIRST_ARCHITECTURE.md` and the scenario Markdown corpus.

## Preview stability and smartphone behavior

V2.2 explicitly preserves the V1 interaction contract:

- desktop/laptop hover updates content **without changing the preview height or moving the Mosaic**;
- fine-pointer hover uses a 140 ms intent delay;
- smartphone taps preview a scenario instead of navigating accidentally;
- horizontal swipe moves to the previous/next visible scenario;
- smartphone reading order is **scenario copy → Koali path/context → image**;
- mobile editorial copy uses content-driven height rather than fixed rows that clip text.

These rules are validated by `scripts/validate-v2.py` and documented historically in `docs/PREVIEW_LAYOUT_INTERACTION_CONTRACT.md`.
