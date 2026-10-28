# Arketype / PRF / Domain classification in Kristal Manager

This version separates four independent notions that were previously mixed in the **Category** column.

| Display | Metadata | Meaning |
| --- | --- | --- |
| **Arketype** | `classification.primary_archetype` (`ARK-xx`) | Structural/design-time Arketype family |
| **Usage (PRF)** | `classification.primary_usage` (`PRF-xx`) | Declared Arketype use case |
| **Domain** | `classification.domain`; fallback `subject.domain`, `state_scope.domain` | Topic/domain, e.g. automotive |
| **Technical profile** | `kristal.workspace.json` `profile` | Local workspace profile (`layered`, `executable`, etc.) |

Fields `arketype_version`, `supporting_archetypes`, `usage_family`, and similar declared classification data remain visible in **JSON details**. The Manager never invents an ARK or PRF label from a title or inferred domain.

## Where it reads the data

1. Preferred: `kristal.workspace.json` -> `classification` (when present and nonempty).
2. Fallback: `kristal.discovery.json` -> `classification`, as read by the Manager discovery adapter.
3. If no valid declared `ARK-xx` / `PRF-xx` exists, show an em dash and offer an `Unclassified` filter.

Both sources are **declarations / noncanonical metadata**, not independent C1 certification. This interface does not write classification metadata, mutate Kristals, or run Kristalizer classification automatically. The correct authoring path for a future classification change is the **Arketype v1.4 catalog + Local Authoring Kit `classify`**, followed by its discovery regeneration/check procedure.

## UI behavior

- Separate filters for Domain, Arketype, Usage.
- Sortable columns for Domain, Arketype, Usage (PRF), Technical profile.
- The selected-Kristal summary names each field explicitly.
- Inventory JSON adds `usage_profile`, `domain_category`, `arketype_classification`, and `classification_verified: false`, retaining the existing `archetype` field for compatibility.

## Safety / limitations

- The Manager does not guess official Arketype IDs.
- A missing classification does not make a Kristal invalid.
- The local technical profile is not an Arketype use-case `PRF-xx`.
- Classification display is not semantic validation, access authorization or publication.

## Testing

The graphic tests for the classification filters and existing UI passed under a virtual display. Overall: **174 passed**, **14 historical failures** in the intentionally disabled publication/sync/migration backend. Tests on the user's Windows installation remain to be completed.
