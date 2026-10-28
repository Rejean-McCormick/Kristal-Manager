# Kristal Manager — UNESCO Thesaurus + ISCED-F integration

**Status:** read-only, metadata observation and audit, not classification authoring or conformance.

## Existing reference decisions (not newly invented)

- Framework v7 `spec/v7/UNESCO-Thesaurus-Alignment.md` designates the **UNESCO Thesaurus** as the default external `reference_spine` for encyclopedic Category/Subject navigation. It pins **7 domains / 88 microthesauri**. Domain 7 (countries) is generally a facet, not an independent knowledge discipline.
- Framework v7 `spec/v7/TOC-and-Subject-Model.md` distinguishes Subject KQ identity, Category and Axis. A Subject may be polyhierarchical. **UNESCO external concept URIs are not KQ identifiers**.
- Framework v7 `examples/v7/toc-registry-100-seed.example.json` is an **example seed** of 100 subjects; it cannot be treated as proof of a classification without reviewing the Subject's explicit KQ identity.
- Icon Generator `tools/icon-generator/ISCED_F2013_POLICY.md` standardizes its visual broad-field scheme on **ISCED-F 2013, codes 00–10**, allowing up to 3 in a Kristal-specific presentation extension. ISCED-F is different from the UNESCO Thesaurus.
- Arketype (`ARK-xx`), usage profile (`PRF-xx`), and technical profile (`layered`, `executable`…) are separate axes.

## What is implemented

- Bundled, offline copies of the Framework v7 UNESCO KOS **profile**, **baseline**, and **100-subject example seed**, retaining UNESCO notations and URIs. The code validates the pinned counts instead of generating a new taxonomy.
- Bundled **11 ISCED-F broad-field codes** based on the Icon Generator policy. English display translations are provided; color codes remain a Kristal presentation convention, not an UNESCO color standard.
- Main table now has **UNESCO domain**, **Microthesaurus**, and **ISCED-F** columns; independent filter menus for each. **Arketype** and **Usage (PRF)** remain separate. The old arbitrary domain is shown as `Legacy domain (free text)` in the detail card and inventory JSON for continuity.
- When a workspace declares an explicit UNESCO notation/URI in metadata, Manager validates it against the included reference; a known microthesaurus implies its defined parent domain. It flags unknown notations, domain↔microthesaurus conflicts, invalid ISCED codes, and disagreements between an explicit ISCED declaration and the icon profile.
- The icon's codes are read from `.kristal/icon-profile.json` (or an already-known icon presentation bridge), **not** guessed from the name. ISCED `00` is never used as a fallback.
- Existing Framework v7 seed placements are shown **as reference-only hints when the workspace explicitly uses a known `KQxxxx` subject identity**, not as automatic authoritative mappings. Example: `KQ5058` references UNESCO `4.45` and `6.45` in the v7 seed.
- **Actions → UNESCO classification audit…** opens an overlay with per-Kristal observations and local **Export JSON / Export HTML** buttons, excluding internal historical snapshots.
- Ordinary inventory JSON also includes `unesco_thesaurus`, `isced_f2013`, and `classification_review_issues` without changing the original exported fields.

## Supported explicit metadata for future authoring

The following is **a Manager reader convention**, not a new Framework normative schema and not written by Manager:

```json
{
  "classification": {
    "unesco_thesaurus": {
      "domains": ["http://vocabularies.unesco.org/thesaurus/domain4"],
      "microthesauri": ["http://vocabularies.unesco.org/thesaurus/mt4.45"]
    },
    "isced_f2013": {"broad_fields": ["07"]}
  }
}
```

Alternately, `classification.unesco`, `subject.unesco`, `subject.unesco_thesaurus` and explicit UNESCO-tagged `category_placements` are recognized. Only explicitly recorded notations and canonical URIs are accepted; **labels are not reverse-matched to UNESCO identifiers**. A declared URI does **not** establish an exact SKOS mapping or semantic conformance by itself.

## Verified on the supplied Kristal-Architecture archive

- Its desktop icon profile declares **ISCED-F `07`** (Engineering, manufacturing and construction).
- `subject.domain` is the free text `architecture`. This is **not** a UNESCO placement, so its UNESCO domain and microthesaurus display as **Unmapped**.
- The Framework v7 seed contains an Architecture subject KQ5058 aligned with 4.45 and 6.45, but the supplied local workspace **does not declare KQ5058**. This seed relationship is **not applied automatically**.
- Local inventory status READY is not a Framework conformity verdict.

## Limitations and safety

- No online UNESCO API or full 4,500-concept import. The included KOS profile covers the 7/88 navigational structure and v7 seed examples, not every individual thesaurus concept.
- Manager does not invent URIs, update metadata, migrate categories, rename folders, or certify a Kristal because of a classification match.
- A mismatch between UNESCO Thesaurus domain and ISCED-F icon domain is **not automatically an error**; the schemes have different purposes. Only conflicts within one declared classification are flagged.
- Exported audit JSON contains local paths; treat it as private. Save reports **outside** `locals`.
- This UI was tested with a virtual Linux desktop; Windows rendering still needs confirmation.
- Previous publication/synchronization/migration backend remains intentionally disabled.

## How to try it

1. Extract this whole ZIP to a **new directory**, preserving your previous Manager.
2. Run `Launch-Kristal-Manager.cmd` and scan `C:\mycode\Kristal\locals`.
3. Use the **UNESCO domain / Microthesaurus / ISCED-F (icon)** filters. An `Unmapped` UNESCO value is a missing explicit mapping, not a failed C1 check.
4. Open **Actions → UNESCO classification audit…**; review each Kristal and export JSON or HTML if needed.
5. Use the original Kristalizer / Authoring Kit workflow (not this Manager audit) for any future approved metadata classification change.
