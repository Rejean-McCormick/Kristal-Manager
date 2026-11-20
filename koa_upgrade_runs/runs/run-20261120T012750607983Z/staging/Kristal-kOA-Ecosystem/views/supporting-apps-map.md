# Supporting applications / tooling — v0.7.1

Ces pièces sont reconnues comme composants fonctionnels, mais leur autorité reste bornée.

## Ekole
Cœur pédagogique neutre: moteur local, portail, espace apprenant et éditeur, consommant des paquets ekole.content-pack/0.1; ne possède pas les corpus Québec ou Pastorale.
- scope: `digital_product`
- placement: `domain_application` / `observed_local_engine_no_cross_system_qualification`

## Ekole Pastorale
Corpus indépendant de 32 cours et 7 parcours pour le moteur Ekole; révision doctrinale, pédagogique, de protection et de licences requise avant publication.
- scope: `domain_content`
- placement: `knowledge_corpus` / `content_pack_schema_compatible_not_published`

## Ekole Québec
Corpus scolaire de 202 cours et 6 parcours distinct du moteur neutre; validation officielle non établie.
- scope: `domain_content`
- placement: `knowledge_corpus` / `content_pack_schema_compatible_not_certified`

## Akor
Missions d’apprentissage concerté et rôles complémentaires; connexions à Kontexte, Kompose, Orgo, Orgo Worlds et Ekole visées, sans interopération opérationnelle démontrée.
- scope: `digital_product`
- placement: `peripheral_app` / `integration_intended_unverified`

## Kompose
Outil de composition pédagogique mentionné comme dépendance visée par Akor; dépôt distant enregistré mais dossier local déclaré absent au scan 2026-10-27.
- scope: `digital_product`
- placement: `peripheral_app` / `local_checkout_missing_in_last_scan`

## Kontexte
Service de contexte pédagogique cité par Akor; dépôt distant enregistré mais dossier local déclaré absent au scan 2026-10-27.
- scope: `digital_product`
- placement: `peripheral_app` / `local_checkout_missing_in_last_scan`

## Inkuisite / Inkui
Atelier local de composition d’examens, barèmes, correction et rétroaction; la revue humaine reste distincte du calcul automatique. Aucun déploiement Moodle qualifié par le snapshot.
- scope: `domain_application`
- placement: `domain_application` / `local_executable_unqualified_interop`

## BoKristal
Prototype de distribution de connaissances multi-supports; ni canonicalisation v6 ni engagements v9 garantis par la démonstration. Pas de déploiement production.
- scope: `peripheral_app`
- placement: `peripheral_app` / `prototype_not_production`

## Spek
Moteur autonome de publication sémantique locale et multilingue; ne valide ni engagements Kristal, ni RuntimeSets GF/PGF, ni autorisation de publication.
- scope: `digital_product`
- placement: `peripheral_app` / `independent_application`

## diK
Outil alpha.7 de dictionnaires KQ/KP, couverture linguistique et crosswalks Wikidata revus; cible Framework 11 draft.3, ne remplace pas les identités canoniques.
- scope: `tooling`
- placement: `tooling` / `experimental_alpha_not_certified`

## Kristalizer
Analyse KQ/KP et propositions Wikidata avec contrôle humain; staging hors source et builds locaux, aucune correspondance canonique exacte imposée automatiquement.
- scope: `tooling`
- placement: `tooling` / `analysis_and_review_no_auto_migration`

## Kristal Authoring Kit
Kit d’édition local v4.0.0-draft.4 avec profil v11 opt-in et construction v9/v10; enregistrements d’artefacts requis, aucune activation ou publication implicite.
- scope: `tooling`
- placement: `tooling` / `v11_opt_in_unqualified_for_this_legacy_corpus`

## Arketype
Système d’archétypes cité par Ekole Pastorale; extensions ARK-20/ARK-21 candidates et non normatives, non installées implicitement.
- scope: `tooling`
- placement: `tooling` / `candidate_extensions_only`

## Skope
Exploration/lecture sémantique mentionnée par Spek comme ressource optionnelle; intégration au moteur de publication non démontrée ici.
- scope: `tooling`
- placement: `tooling` / `interface_to_be_qualified`

## Kor
Client mobile Kor 0.7, projection filtrée de Konnaxion et Orgo sans appropriation des états métier; intégration d’exécution intersystème non démontrée par le snapshot.
- scope: `digital_product`
- placement: `peripheral_app` / `independent_mobile_projection`

## Koali Control Panel
Console de développement et d’orchestration de kOA-Linux pour workspaces, diagnostics, validation, assemblage, tests et workflows de release; elle ne possède pas l’autorité métier runtime.
- scope: `tooling`
- placement: `tooling` / `supporting_not_runtime_authority`

## Konnaxion Capsule Manager
Packaging, installation et lifecycle reproductibles de Konnaxion via capsules signées, profils réseau, gates, sauvegarde, restauration et rollback.
- scope: `digital_product`
- placement: `product_subsystem` / `owned_extension`

## Konnaxion Worlds
Orchestration de contextes civiques isolés avec identités/scopes, releases, snapshots, switching et garanties anti-contamination.
- scope: `digital_product`
- placement: `product_subsystem` / `owned_extension`

## Orgo Worlds
Contextes opérationnels isolés, releases, memberships, scenario packs et injection contrôlée vers Orgo sans écriture DB inter-système.
- scope: `digital_product`
- placement: `product_subsystem` / `owned_extension`

## Kintsugi / Kompendio
Cadre d’intégration par contrats et frontières explicites, incluant des modes Mimic/Annex pour composer des capacités sans double vérité ni absorption d’autorité.
- scope: `digital_conceptual`
- placement: `tooling` / `documentation_and_pattern_framework`

## Diagnostics & Conformance Tooling
Famille de diagnostics indépendants qui observent, qualifient et produisent des preuves/gates sans devenir propriétaires du runtime évalué.
- scope: `tooling`
- placement: `tooling` / `independent_qualification`

## Konnaxion SecurityDiag
Legacy Konnaxion security-diagnostic lineage consolidated into KonnaxionDiag v4.2.3.
- scope: `tooling`
- placement: `tooling` / `capability_grouped_under_konnaxiondiag_not_separate_repository`

## LevelUpDiag Koali
Diagnostic suite for the live Koali product system while retaining historical kOA-Linux stabilization/release campaigns.
- scope: `tooling`
- placement: `tooling` / `independent_qualification`

## Konnaxion LevelUpDiag
Legacy Konnaxion functional-diagnostic lineage consolidated into KonnaxionDiag v4.2.3.
- scope: `tooling`
- placement: `tooling` / `capability_grouped_under_konnaxiondiag_not_separate_repository`

## LevelUpDiag Kristal
Kristal-specific LevelUpDiag lineage superseded by KristalDiag v7.
- scope: `tooling`
- placement: `tooling` / `superseded_lineage`

## LevelUpDiag Orgo
Outil indépendant de diagnostic/qualification pour la cible correspondante; produit des preuves et verdicts sans posséder l’état métier de la cible.
- scope: `tooling`
- placement: `tooling` / `independent_qualification`

## LevelUpDiag SemantiK Architect
Outil indépendant de diagnostic/qualification pour la cible correspondante; produit des preuves et verdicts sans posséder l’état métier de la cible.
- scope: `tooling`
- placement: `tooling` / `independent_qualification`

## LevelUpDiag MediKristal
Outil indépendant de diagnostic/qualification pour la cible correspondante; produit des preuves et verdicts sans posséder l’état métier de la cible.
- scope: `tooling`
- placement: `tooling` / `independent_qualification`

## Ariane Diagnostics
Standalone local diagnostic consoles for the Ariane target repository.
- scope: `tooling`
- placement: `tooling` / `independent_qualification`

## LevelUpDiag Ariane
Portable LevelUpDiag frame/profile derived from Ariane diagnostics for repeatable external-target qualification.
- scope: `tooling`
- placement: `tooling` / `independent_qualification`

## Konnaxion Universe & Worlds Manager
Standalone manager for canonical Konnaxion Universe/World seed packs, using Konnaxion-owned Worlds services and contracts.
- scope: `digital_product`
- placement: `product_subsystem` / `owned_extension`

## KonnaxionDiag
Consolidated Konnaxion functional and security qualification suite with bounded evidence, ReleaseSet qualification and signed release authorization; qualification remains separate from enforcement.
- scope: `tooling`
- placement: `tooling` / `active_consolidated_qualification`

## Konstellation Publisher
Local Windows publisher that packages, deploys and health-checks Konstellation releases on a remote VPS behind the existing Traefik boundary.
- scope: `tooling`
- placement: `tooling` / `active_deployment_tool`

## SemantiK Phrase Ops Console
Operational multilingual lab/console for SemantiK capability verification and bounded GF Wordbench handoffs; it does not become a second language architecture.
- scope: `tooling`
- placement: `tooling` / `active_lab`

## KristalDiag
Suite de conformance et qualification indépendante Kristal v10, cible 10.0.0-draft.3.1; contrôle des contrats, manifests de publication et surfaces GitHub en lecture seule; ne publie ni n’active.
- scope: `tooling`
- placement: `tooling` / `independent_v10_conformance_suite`

## RepoDiag
Generic external repository diagnostics runner that executes only declared validations and produces bounded machine-readable evidence.
- scope: `tooling`
- placement: `tooling` / `active_generic_tool`

## UCKK SecurityDiag
Independent security qualification suite targeting UCKK Moodle source, UCKK Publisher and the production Linux VPS.
- scope: `tooling`
- placement: `tooling` / `independent_qualification`

## UCKK Publisher
Release publisher/deploy agent workflow for immutable UCKK releases, remount verification, rollback and production publication.
- scope: `broader_initiative`
- placement: `consumer_subsystem` / `owned_by_uckk`

## Editorial Figure Engine
Deterministic code-first SVG figure engine for books, reports, academic and institutional diagrams using semantic YAML/JSON inputs and explicit editorial templates.
- scope: `tooling`
- placement: `tooling` / `active_independent_tool`

## Formulator
Active MathKristal research/calculation/validation/proof-generation engine. It works from Challenge docs, challenge-local Kristal v6 and a pinned read-only MathKristal snapshot; maintains bounded KnowledgeGraph, persistent ResearchGraph and cross-Challenge StrategyGraph memories; uses counterexample-first/falsification stages and bounded human-mediated AI relay; finite tests or agent output never count as proof.
- scope: `tooling`
- placement: `tooling` / `active_research_engine`

## Kristal Grand Challenges
Persistent research workbench for 12 selected mathematical grand challenges. Each Challenge owns a local Kristal v6 with imported, established_external, research, validated_local and promotion_candidates layers; global Kristal Math stays read-only and promotion is explicit, never automatic.
- scope: `research_adjacent`
- placement: `research_adjacent` / `persistent_challenge_workspace`

## Astro Signals
Quantitative natal-chart research application using deterministic astronomical calculations, continuous geometric fields and explicit uncertainty propagation. V2.3 has a true unknown-time mode: it does not invent a birth time, sweeps the local civil day, exposes median/range plus P10/P90 sensitivity, and suppresses time-dependent claims that cannot be supported.
- scope: `research_adjacent`
- placement: `research_adjacent` / `independent_application`

## Voxtral Audiobook Studio
Local Streamlit audiobook-production workflow around Voxtral TTS: import manuscript, segment by chapter/passage, generate audio, review, selectively regenerate failed/edited passages, retain multiple segment versions, estimate cost and export chapters or complete books. Segment state makes revision granular instead of rebuilding the whole book.
- scope: `peripheral_app`
- placement: `peripheral_app` / `adjacent_media_tool_not_core`

