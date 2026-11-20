# Diagnostics, qualification and release tooling

Current and retained lineages. Superseded lineages remain represented for traceability.

## Diagnostics & Conformance Tooling
Famille de diagnostics indépendants qui observent, qualifient et produisent des preuves/gates sans devenir propriétaires du runtime évalué.
- placement: `tooling` / `independent_qualification`

## Ariane Diagnostics
Standalone local diagnostic consoles for the Ariane target repository.
- placement: `tooling` / `independent_qualification`

## LevelUpDiag Ariane
Portable LevelUpDiag frame/profile derived from Ariane diagnostics for repeatable external-target qualification.
- placement: `tooling` / `independent_qualification`

## LevelUpDiag Koali
Diagnostic suite for the live Koali product system while retaining historical kOA-Linux stabilization/release campaigns.
- placement: `tooling` / `independent_qualification`

## KonnaxionDiag
Consolidated Konnaxion functional and security qualification suite with bounded evidence, ReleaseSet qualification and signed release authorization; qualification remains separate from enforcement.
- placement: `tooling` / `active_consolidated_qualification`

## Konnaxion SecurityDiag
Legacy Konnaxion security-diagnostic lineage consolidated into KonnaxionDiag v4.2.3.
- placement: `tooling` / `superseded_lineage`

## Konnaxion LevelUpDiag
Legacy Konnaxion functional-diagnostic lineage consolidated into KonnaxionDiag v4.2.3.
- placement: `tooling` / `superseded_lineage`

## KristalDiag
Independent KristalDiag v10 (target Framework `10.0.0-draft.3.1`), separate from the Standard, authoring, publication and activation. Its V9-State-Reader conformance profile can examine the present v9 workspace but does not certify v11.
- placement: `tooling` / `independent_v10_conformance_suite`

## Kristal Authoring Kit
Local authoring kit v4 draft.4; v11 is strictly opt-in and requires independently registered canonical artifacts before a selected graph is built. Publishing and activation are separate.
- placement: `tooling` / `v11_opt_in_unqualified_for_this_legacy_corpus`

## Kristalizer
Local scan and staging tool, with approval-required KQ/KP crosswalk candidates; v11 migration is needed for the existing legacy graph. Vendored Kit remains pinned to draft.3.
- placement: `tooling` / `analysis_and_review_no_auto_migration`

## diK
Offline lexical catalog and semantic identity tooling alpha.7; independent crosswalk review, not an automatic canonical identifier migration.
- placement: `tooling` / `experimental_alpha_not_certified`

## LevelUpDiag Kristal
Kristal-specific LevelUpDiag lineage superseded by KristalDiag v7.
- placement: `tooling` / `superseded_lineage`

## LevelUpDiag Orgo
Outil indépendant de diagnostic/qualification pour la cible correspondante; produit des preuves et verdicts sans posséder l’état métier de la cible.
- placement: `tooling` / `independent_qualification`

## LevelUpDiag SemantiK Architect
Outil indépendant de diagnostic/qualification pour la cible correspondante; produit des preuves et verdicts sans posséder l’état métier de la cible.
- placement: `tooling` / `independent_qualification`

## RepoDiag
Generic external repository diagnostics runner that executes only declared validations and produces bounded machine-readable evidence.
- placement: `tooling` / `active_generic_tool`

## UCKK SecurityDiag
Independent security qualification suite targeting UCKK Moodle source, UCKK Publisher and the production Linux VPS.
- placement: `tooling` / `independent_qualification`

## Koali Control Panel
Console de développement et d’orchestration de kOA-Linux pour workspaces, diagnostics, validation, assemblage, tests et workflows de release; elle ne possède pas l’autorité métier runtime.
- placement: `tooling` / `supporting_not_runtime_authority`

## Konnaxion Capsule Manager
Packaging, installation et lifecycle reproductibles de Konnaxion via capsules signées, profils réseau, gates, sauvegarde, restauration et rollback.
- placement: `product_subsystem` / `owned_extension`

## Konstellation Publisher
Local Windows publisher that packages, deploys and health-checks Konstellation releases on a remote VPS behind the existing Traefik boundary.
- placement: `tooling` / `active_deployment_tool`

## UCKK Publisher
Release publisher/deploy agent workflow for immutable UCKK releases, remount verification, rollback and production publication.
- placement: `consumer_subsystem` / `owned_by_uckk`

