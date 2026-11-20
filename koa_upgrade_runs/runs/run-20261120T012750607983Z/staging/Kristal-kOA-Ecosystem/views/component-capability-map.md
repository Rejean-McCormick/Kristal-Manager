# Component × capability map

Sourced/curated capability placement. Repository identity alone never creates capability authority.

## Ariane
Moteur de navigation d’applications basé sur un Atlas versionné de states/transitions, avec vérification, safety gates et approbations.

- **Atlas sémantique d’interface** — `system`
- **Navigation vérifiée d’application** — `owner`
- **Gating de sécurité des actions** — `guardrail`
- **Approbation humaine explicite** — `guardrail`
- **Diagnostics / qualification** — `drift/validation`

## Ariane Assist Client
Surface optionnelle de guidance/overlay et validation par capture pour les workflows humains/desktop.

- **Navigation vérifiée d’application** — `human_guidance`
- **Composition de surfaces** — `optional_surface`

## Ariane Atlas
Carte machine-readable d’états, éléments, transitions, fingerprints et résultats attendus d’une application.

- **Atlas sémantique d’interface** — `owner`
- **Stockage versionné sécurisé** — `navigation_assets`

## Ariane Diagnostics
Standalone local diagnostic consoles for the Ariane target repository.

- **Diagnostics / qualification** — `primary`
- **Qualification / evidence gates** — `secondary`
- **Navigation vérifiée d’application** — `secondary`

## Ariane Runtime / Theseus
Boucle observe→match→plan→act→verify qui suit l’Atlas et s’arrête en cas d’incertitude non résolue.

- **Navigation vérifiée d’application** — `owner`
- **Intégration fiable / reconciliation** — `verified_transition`

## Ariane Safety / approvals
Classification de risque, politiques fail-closed et approbation humaine pour les actions sensibles.

- **Gating de sécurité des actions** — `owner`
- **Approbation humaine explicite** — `owner`
- **Custodie d’audit / disclosure** — `session_evidence`

## Ars Magna Lulli
Plan de contrôle GitOps multi-langues: coordonne projets, contributeurs, dépôts, pipelines, états de promotion et indexation de preuves sans devenir l’autorité linguistique ou de validation.

- **Orchestration GitOps multi-langues** — `owner`
- **Workflow / routing / escalation** — `gitops_pipeline`
- **Continuité de contexte** — `source_evidence_lineage`

## Audit Broker
Custodie bornée des enregistrements d’audit, divulgation sélective, retention et chaîne de garde.

- **Custodie d’audit / disclosure** — `owner`
- **Impact / accountability** — `evidence_custody`

## CertifiKation
Parcours de certification, évaluations, validation par pairs, portfolio de compétences et interop LMS.

- **Certification et portfolio** — `owner`

## Da’at
Frontière de mapping/ACL/anti-corruption vers les contrats Kristal natifs.

- **Résolution de référents** — `adapter`
- **Mapping / ACL boundary** — `owner`
- **Échange d’artefacts** — `boundary`

## Diagnostics & Conformance Tooling
Famille de diagnostics indépendants qui observent, qualifient et produisent des preuves/gates sans devenir propriétaires du runtime évalué.

- **Diagnostics / qualification** — `primary`
- **Qualification / evidence gates** — `primary`

## Editorial Figure Engine
Deterministic code-first SVG figure engine for books, reports, academic and institutional diagrams using semantic YAML/JSON inputs and explicit editorial templates.

- **Assemblage rôle × contexte × inventaire** — `primary`
- **Documentation / transmission** — `secondary`

## EkoH
Signaux d’expertise contextuelle, qualité de contribution, crédibilité éthique, historique et confidentialité.

- **Signal d’expertise contextuel** — `owner`
- **Lectures pondérées explicables** — `context_provider`

## EL / Âme Artificielle
Moteur expérimental de graphe psycho-causal sémantique avec snapshots immuables et activation transitoire; application de recherche, sans autorité générale kOA.

- **État de connaissance structuré** — `semantic_graph`
- **Résolution de référents** — `graph_relations`
- **Snapshot immuable + provenance** — `soul_snapshot`

## EncyKlopedia
Source discovery, acquisition, extraction and handoff pipeline. It prepares source evidence and immutable harvest handoffs but does not own the canonical knowledge library or final semantic meaning.

- **Sensing / intake** — `support`
- **Découverte de sources** — `owner`
- **Snapshot immuable + provenance** — `owner`
- **Résolution de référents** — `candidate_source`

## ethiKos
Pipeline civique: discovery, deliberation, drafting, decision, accountability.

- **Consultations publiques** — `primary`
- **Délibération structurée** — `primary`
- **Drafting collaboratif** — `primary`
- **DecisionRecord / résultat publiable** — `process`

## GF Observatory
Produit compagnon indépendant et en lecture seule qui agrège des artefacts versionnés de Wordbench pour rendre visibles maturité, readiness, tendances, bloqueurs et liens de preuve; il ne compile ni ne modifie les workspaces.

- **Observation agrégée de maturité linguistique** — `owner`
- **Diagnostics / qualification** — `read_only_projection`

## GF RGL AI Compendium
Référence documentaire et de gouvernance source-grounded pour développer, réparer, tester, revoir et préparer l’upstream des langues GF/RGL; fournit contrats, provenance, workflows, evidence policy et gates sans compiler ni déclarer le succès d’exécution.

- **Gouvernance d’ingénierie GF/RGL** — `owner`
- **Qualification / evidence gates** — `policy_provider`

## GF Wordbench
Workbench indépendant de validation, diagnostics, régression et release-readiness pour un projet de langue GF. GF natif reste l’autorité d’exécution; Wordbench préserve les preuves, scénarios, goldens, manifests et verdicts de gate.

- **Validation GF avec preuves reproductibles** — `owner`
- **Diagnostics / qualification** — `language_validation`
- **Qualification / evidence gates** — `evidence_provider`
- **Artefacts linguistiques validés pour runtime multilingue** — `artifact_provider`

## Governance Policy Runtime
Évalue les politiques locales versionnées et produit décisions/obligations/receipts sans exécuter l’opération gouvernée.

- **Évaluation de policy / obligations** — `owner`
- **Gating de sécurité des actions** — `policy_gate`

## Identity & Trust
Établit l’identité et les preuves de confiance bornées; authentifie/vérifie sans décider les autorisations métier.

- **Identity & trust evidence** — `owner`
- **Opération hors-ligne / local-first** — `local_authentication`

## Interaction Kernel
Distributed interoperability protocol and reference implementation for autonomous systems; owns versioned envelope/profile semantics, not participant databases, artifact stores or transaction coordination.

- **Interopérabilité contractuelle** — `owner`
- **Échange d’artefacts** — `protocol`
- **Intégration fiable / reconciliation** — `semantics`

## Kamel
Système modulaire qui assemble rôles, contextes, inventaires, cartes et modules en decks structurés, validés et rendus pour compréhension, décision et apprentissage.

- **Assemblage rôle × contexte × inventaire** — `owner`
- **Compilation / rendu de decks** — `owner`
- **Reader policies / projections** — `decision_support`
- **Diagnostics / qualification** — `contract_validation`

## keenKonnect
Espaces de projets/construction, collaboration, artefacts et travail partagé.

- **Espaces de projets** — `owner`
- **Stockage versionné sécurisé** — `orchestrates`
- **Réseautage / mise en relation** — `support`

## KeyFlow
Outil/formulaire observé dans l’inventaire local historique; rôle d’intake/formulaires plausible, architecture détaillée non fournie dans cette passe.

- **Sensing / intake** — `candidate_forms`
- **Consultations publiques** — `candidate_form_flow`

## King Klown
Couche narrative et de mobilisation; interface culturelle/pédagogique sans autorité technique.

- **Narration / mobilisation** — `owner`
- **Documentation / transmission** — `pedagogy`

## Kintsugi / Kompendio
Cadre d’intégration par contrats et frontières explicites, incluant des modes Mimic/Annex pour composer des capacités sans double vérité ni absorption d’autorité.

- **Patterns d’intégration remplaçable** — `primary`
- **Interopérabilité contractuelle** — `primary`
- **Intégration fiable / reconciliation** — `secondary`

## Knowledge
Bibliothèque collaborative d’apprentissage/connaissances sous KonnectED.

- **Parcours d’apprentissage** — `knowledge_library`

## kOA Assembly
Résout profils, dépendances, ressources, stockage, services et Release Sets vers des plans de déploiement déterministes.

- **Résolution déterministe de profils** — `owner`
- **Admission / trust / policy** — `composition`
- **Release channels / Release Sets** — `release_plan`

## kOA Node Agent
Opérations locales privilégiées, étroites et autorisées de lifecycle/activation/récupération.

- **Opérations locales privilégiées** — `owner`
- **Activation / rollback Runtime Pack** — `privileged_executor`

## Koali / kOA-Linux
Sovereign local-first, offline-capable governed operating system for kOA workloads. It owns platform profiles, admission, release/lifecycle and host composition without absorbing independent subsystem authority.

- **Admission / trust / policy** — `owner`
- **Release channels / Release Sets** — `owner`
- **Opération hors-ligne / local-first** — `owner`
- **Backup / restore / recovery** — `platform`

## Koali Control Panel
Console de développement et d’orchestration de kOA-Linux pour workspaces, diagnostics, validation, assemblage, tests et workflows de release; elle ne possède pas l’autorité métier runtime.

- **Diagnostics / qualification** — `primary`
- **Qualification / evidence gates** — `primary`
- **Résolution déterministe de profils** — `secondary`
- **Release channels / Release Sets** — `secondary`

## Koali Scenario Mosaic
Bilingual static-first scenario atlas. Current V2 repository presents 36 canonical sociotechnical problems; the package still retains the earlier 120-scenario corpus as historical/use-pattern evidence.

- **Cartographie de scénarios** — `owner`
- **Documentation / transmission** — `mapping`

## Koali Spaces
Optional independently versioned experience/composition layer that composes validated product surfaces and routing while preserving product-owned UI/business authority.

- **Composition de surfaces** — `owner`
- **Opération hors-ligne / local-first** — `presentation`

## Kompiler
Local-first context compiler that performs read-only queries against trusted knowledge surfaces, preserves provenance/conflicts, applies budgets/ranking and emits bounded context packs without becoming a source or semantic authority.

- **Reader policies / projections** — `primary`
- **État de connaissance structuré** — `secondary`
- **Continuité de contexte** — `secondary`
- **Assistance IA bornée** — `secondary`
- **Échange d’artefacts** — `secondary`

## Konductor
Runtime durable pour travail IA autonome borné: workflows typés, routage validé, outils permissionnés, checkpoints, événements, human-in-the-loop et reprise.

- **Orchestration IA durable et bornée** — `owner`
- **Gating de sécurité des actions** — `runtime`
- **Approbation humaine explicite** — `runtime`
- **Custodie d’audit / disclosure** — `event_stream`

## Konfid
Cross-system security control plane for identity bindings, scoped authorization, risk detection, governed containment, approvals and auditable response; integrates without becoming domain-state authority.

- **Identity & trust evidence** — `binding_context`
- **Évaluation de policy / obligations** — `cross_system_authz`
- **Détection de risque / containment** — `owner`
- **Approbation humaine explicite** — `critical_actions`
- **Custodie d’audit / disclosure** — `evidence_plane`

## Konnaxion
État civique/public, coordination, consultations, délibération, DecisionRecords, accountability et expériences publiques.

- **Consultations publiques** — `owner`
- **Délibération structurée** — `owner`
- **DecisionRecord / résultat publiable** — `owner`
- **Impact / accountability** — `owner`
- **Mémoire institutionnelle** — `civic/accountability_memory`
- **Parcours d’apprentissage** — `product`
- **Espaces de projets** — `product`
- **Réseautage / mise en relation** — `product`

## Konnaxion Capsule Manager
Packaging, installation et lifecycle reproductibles de Konnaxion via capsules signées, profils réseau, gates, sauvegarde, restauration et rollback.

- **Déploiement / lifecycle reproductible** — `primary`
- **Backup / restore / recovery** — `primary`
- **Release channels / Release Sets** — `secondary`
- **Opérations locales privilégiées** — `secondary`

## Konnaxion LevelUpDiag
Legacy Konnaxion functional-diagnostic lineage consolidated into KonnaxionDiag v4.2.3.

- **Diagnostics / qualification** — `primary`
- **Qualification / evidence gates** — `primary`

## Konnaxion SecurityDiag
Legacy Konnaxion security-diagnostic lineage consolidated into KonnaxionDiag v4.2.3.

- **Diagnostics / qualification** — `primary`
- **Qualification / evidence gates** — `primary`

## Konnaxion Universe & Worlds Manager
Standalone manager for canonical Konnaxion Universe/World seed packs, using Konnaxion-owned Worlds services and contracts.

- **Contextes / Worlds isolés** — `primary`
- **Déploiement / lifecycle reproductible** — `secondary`
- **Stockage versionné sécurisé** — `secondary`

## Konnaxion Worlds
Orchestration de contextes civiques isolés avec identités/scopes, releases, snapshots, switching et garanties anti-contamination.

- **Contextes / Worlds isolés** — `primary`
- **Espaces de projets** — `primary`
- **Backup / restore / recovery** — `secondary`

## KonnaxionDiag
Consolidated Konnaxion functional and security qualification suite with bounded evidence, ReleaseSet qualification and signed release authorization; qualification remains separate from enforcement.

- **Diagnostics / qualification** — `primary`
- **Qualification / evidence gates** — `secondary`
- **Release channels / Release Sets** — `secondary`
- **Gating de sécurité des actions** — `secondary`
- **Custodie d’audit / disclosure** — `secondary`
- **Détection de risque / containment** — `secondary`

## KonnectED
Apprentissage, connaissances, parcours et certification.

- **Parcours d’apprentissage** — `owner`
- **Certification et portfolio** — `owner`

## Konservation
Contenu créatif et préservation culturelle sous Kreative.

- **Préservation culturelle** — `owner`

## Konstellation
Universal adaptive navigation engine for Kristals. Reader policy + structural introspection + Lens produce explicit NavigationPlans and controlled renderers; views do not create truth.

- **Reader policies / projections** — `primary`
- **État de connaissance structuré** — `navigation_projection`
- **Navigation vérifiée d’application** — `primary`
- **Opération hors-ligne / local-first** — `local_first`
- **Continuité de contexte** — `navigation_context`

## Konstellation Publisher
Local Windows publisher that packages, deploys and health-checks Konstellation releases on a remote VPS behind the existing Traefik boundary.

- **Déploiement / lifecycle reproductible** — `primary`
- **Release channels / Release Sets** — `secondary`
- **Backup / restore / recovery** — `secondary`

## Konstruct
Espaces de collaboration de projets sous keenKonnect.

- **Espaces de projets** — `owner`

## Konsultations
Consultations publiques, intake, feedback, ballots/snapshots selon les frontières ethiKos.

- **Consultations publiques** — `owner`

## Kontact
Collaboration et réseautage sous Kreative.

- **Réseautage / mise en relation** — `owner`

## Kor
Personal mobile interface for kOA: filtered action-oriented projections of Konnaxion and Orgo with mobile presentation, offline UX, capture, notifications and human transport boundaries; it does not own projected business state.

- **Reader policies / projections** — `primary`
- **Contextes / Worlds isolés** — `secondary`
- **Continuité de contexte** — `secondary`
- **Échange d’artefacts** — `secondary`
- **Opération hors-ligne / local-first** — `secondary`
- **Identity & trust evidence** — `secondary`

## Korum
Débats structurés à l’intérieur d’ethiKos.

- **Délibération structurée** — `owner`

## Kreative
Création, collaboration culturelle, réseau et préservation.

- **Réseautage / mise en relation** — `product`
- **Préservation culturelle** — `owner`

## Kristal
Portable knowledge-state standard and v7 meta-orchestration design. Current observed design baseline is 7.0.0-draft.3.2 while portable kristal_state/6.0 remains an active compatibility boundary.

- **État de connaissance structuré** — `owner`
- **Validation / reconnaissance** — `owner`
- **Reader policies / projections** — `owner`
- **Échange d’artefacts** — `producer`
- **Mémoire institutionnelle** — `structured_memory`
- **Assistance IA bornée** — `policy_boundary`

## Kristal Farms
Recherche/modèle d’infrastructure physique reliant énergie renouvelable, calcul, fibre, chaleur utile et résilience locale.

- **Compute/énergie/fibre/chaleur utile** — `owner`
- **Opération hors-ligne / local-first** — `infrastructure`

## kristal_runtime
Vérification/compatibilité Runtime Pack, état actif, receipts activation/rollback et santé du runtime.

- **Activation / rollback Runtime Pack** — `owner`
- **Opération hors-ligne / local-first** — `runtime`

## KristalDiag
Consolidated diagnostic, release-qualification and conformance suite for Kristal Standard v7, independent from the Standard and implementations such as Kompiler.

- **Diagnostics / qualification** — `primary`
- **Qualification / evidence gates** — `secondary`
- **Validation / reconnaissance** — `secondary`
- **Release channels / Release Sets** — `secondary`

## LevelUpDiag Ariane
Portable LevelUpDiag frame/profile derived from Ariane diagnostics for repeatable external-target qualification.

- **Diagnostics / qualification** — `primary`
- **Qualification / evidence gates** — `secondary`

## LevelUpDiag Koali
Diagnostic suite for the live Koali product system while retaining historical kOA-Linux stabilization/release campaigns.

- **Diagnostics / qualification** — `primary`
- **Qualification / evidence gates** — `primary`

## LevelUpDiag Kristal
Kristal-specific LevelUpDiag lineage superseded by KristalDiag v7.

- **Diagnostics / qualification** — `primary`
- **Qualification / evidence gates** — `primary`

## LevelUpDiag MediKristal
Outil indépendant de diagnostic/qualification pour la cible correspondante; produit des preuves et verdicts sans posséder l’état métier de la cible.

- **Diagnostics / qualification** — `primary`
- **Qualification / evidence gates** — `primary`

## LevelUpDiag Orgo
Outil indépendant de diagnostic/qualification pour la cible correspondante; produit des preuves et verdicts sans posséder l’état métier de la cible.

- **Diagnostics / qualification** — `primary`
- **Qualification / evidence gates** — `primary`

## LevelUpDiag SemantiK Architect
Outil indépendant de diagnostic/qualification pour la cible correspondante; produit des preuves et verdicts sans posséder l’état métier de la cible.

- **Diagnostics / qualification** — `primary`
- **Qualification / evidence gates** — `primary`

## MA-Gustave GF Language Engineering Ecosystem
Sous-écosystème indépendant de support à l’ingénierie linguistique GF/RGL. Il entoure GF sans le remplacer et peut soutenir les capacités multilingues de kOA/SemantiK sans appartenir au kOA Digital Ecosystem.

- **Réalisation sémantique multilingue** — `upstream_support`
- **Artefacts linguistiques validés pour runtime multilingue** — `support_family`

## MediKristal
Architecture de connaissance médicale sémantique et traçable.

- **État de connaissance structuré** — `domain_application`
- **Validation / reconnaissance** — `domain_protocol`

## Médiathèque kOA
Single local Médiathèque kOA application. Application code and local content are separated physically; SQLite is the application state authority and content may live in a sibling content root.

- **Custodie média locale** — `owner`
- **Médiathèque / diffusion** — `private_local_authority`
- **Backup / restore / recovery** — `media_state`

## Orgo
Multi-tenant workflow and coordination application that owns Signal/Case/Task/workflow operational state, business authorization and operational UI, and can run standalone.

- **Décision → travail gouverné** — `owner`
- **Workflow / routing / escalation** — `owner`
- **Intégration fiable / reconciliation** — `owner`
- **Impact / accountability** — `producer`
- **Mémoire institutionnelle** — `operational_memory`

## Orgo Worlds
Contextes opérationnels isolés, releases, memberships, scenario packs et injection contrôlée vers Orgo sans écriture DB inter-système.

- **Contextes / Worlds isolés** — `primary`
- **Workflow / routing / escalation** — `primary`
- **Décision → travail gouverné** — `secondary`

## OurAI
Élément d’infrastructure de capacité identifié dans l’arborescence kOA.

- **Assistance IA bornée** — `candidate`

## Publication Gateway
Médie les publications entre domaines d’autorité/disclosure, préserve l’autorité source et produit une preuve terminale véridique.

- **Publication gouvernée inter-domaines** — `owner`
- **Intégration fiable / reconciliation** — `publication_reconciliation`

## RepoDiag
Generic external repository diagnostics runner that executes only declared validations and produces bounded machine-readable evidence.

- **Diagnostics / qualification** — `primary`
- **Qualification / evidence gates** — `secondary`

## Resource Governor
Résout enveloppes, admission, allocation, scheduling, throttling et suspension sans devenir autorité métier.

- **Admission / allocation de ressources** — `owner`
- **Admission / trust / policy** — `resource_gate`

## SemantiK Architect
Deterministic semantic-to-human multilingual communication engine aligned with portable kristal_state/6.0 and Kristal/Kristall 7 draft; owns communication planning/realization boundaries, not upstream semantic truth.

- **Réalisation sémantique multilingue** — `owner`
- **Échange d’artefacts** — `consumer/producer`

## SemantiK Phrase Ops Console
Operational multilingual lab/console for SemantiK capability verification and bounded GF Wordbench handoffs; it does not become a second language architecture.

- **Réalisation sémantique multilingue** — `primary`
- **Validation GF avec preuves reproductibles** — `secondary`
- **Diagnostics / qualification** — `secondary`
- **Artefacts linguistiques validés pour runtime multilingue** — `secondary`

## SemantiK Runtime Orchestrator
Fail-closed release orchestrator for SemantiK Architect RuntimeSets; owns release sequencing, promotion/rollback and activation ordering only.

- **Orchestration RuntimeSet** — `owner`
- **Release channels / Release Sets** — `domain_orchestrator`

## SenTient
Extraction, résolution et réconciliation candidates; ne crée ni reconnaissance ni autorité de référence.

- **Extraction de candidats** — `primary`
- **Résolution de référents** — `primary`

## Smart Vote
Lecture/décision: vote brut + lectures pondérées explicables, sans remplacer le baseline public ni fabriquer une souveraineté experte.

- **Vote / lecture de base** — `owner`
- **Lectures pondérées explicables** — `owner`
- **DecisionRecord / résultat publiable** — `reading/publish`

## Stockage
Dépôt sécurisé et versionné sous keenKonnect.

- **Stockage versionné sécurisé** — `owner`

## SwarmCraft
Pattern/capacité conceptuelle d’exécution bornée de tâches gouvernées; distinct d’une implémentation universelle.

- **Décision → travail gouverné** — `executor`
- **Intégration fiable / reconciliation** — `outcome_reporter`

## UCKK / Univers-Cité King Klown
Branche d’apprentissage, média et diffusion publique; consommateur/projection autorisé de certains artefacts Kristal, sans devenir le canon Kristal.

- **Parcours d’apprentissage** — `owner`
- **Médiathèque / diffusion** — `owner`
- **Reader policies / projections** — `consumer_projection`
- **Mémoire institutionnelle** — `learning/archive_projection`
- **Documentation / transmission** — `diffusion`

## UCKK AI Provider
Extension IA optionnelle de la distribution; ne remplace pas les autorités institutionnelles, archive, intégrité ou décision.

- **Assistance IA bornée** — `optional_provider`

## UCKK Archive / Mediatheque
Archive didactique/média, evidence, provenance, revisions, exports et objets Kristal projetés.

- **Archive / provenance / révision** — `owner`
- **Médiathèque / diffusion** — `archive_media`
- **Mémoire institutionnelle** — `learning_memory`

## UCKK Assembly
Assemblées et décisions locales UCKK, séparées de l’archive et de l’intégrité.

- **Délibération structurée** — `local_assembly`
- **DecisionRecord / résultat publiable** — `local_decision`

## UCKK Challenge
Activités/défis et résultats appliqués, avec preuve et articulation vers l’archive.

- **Défis et apprentissage appliqué** — `owner`
- **Certification et portfolio** — `evidence_input`

## UCKK Dashboard
Surface de tableau de bord composant les données du noyau et des plugins sans devenir leur autorité.

- **Composition de surfaces** — `uckk_surface`
- **Reader policies / projections** — `dashboard`

## UCKK Institutional Core
Noyau partagé: programmes, pathways, rôles, profils Joueur, provenance, visibilité, navigation et services de bridge.

- **Registre institutionnel / académique** — `owner`
- **Parcours d’apprentissage** — `shared_registry`

## UCKK Integrity
Cas, review, appeal, corrections, invalidation et garde-fous d’intégrité institutionnelle.

- **Intégrité / appel / correction** — `owner`
- **Custodie d’audit / disclosure** — `institutional_integrity`

## UCKK Moodle
UCKK learning-platform materialization built on Moodle, consuming governed projections while UCKK retains its own institutional/learning boundaries.

- **Parcours d’apprentissage** — `primary`
- **Certification et portfolio** — `secondary`
- **Médiathèque / diffusion** — `secondary`
- **Registre institutionnel / académique** — `secondary`

## UCKK Ops Console
Local operations console for UCKK workflows and Moodle operations without requiring direct command memorization or manual low-level manipulation.

- **Workflow / routing / escalation** — `primary`
- **Déploiement / lifecycle reproductible** — `secondary`
- **Diagnostics / qualification** — `secondary`

## UCKK Publisher
Release publisher/deploy agent workflow for immutable UCKK releases, remount verification, rollback and production publication.

- **Publication gouvernée inter-domaines** — `primary`
- **Déploiement / lifecycle reproductible** — `secondary`
- **Release channels / Release Sets** — `secondary`
- **Backup / restore / recovery** — `secondary`

## UCKK Reports
Reporting institutionnel et exports sur les domaines UCKK autorisés.

- **Reporting pédagogique/institutionnel** — `owner`
- **Impact / accountability** — `reporting`

## UCKK SecurityDiag
Independent security qualification suite targeting UCKK Moodle source, UCKK Publisher and the production Linux VPS.

- **Diagnostics / qualification** — `primary`
- **Qualification / evidence gates** — `secondary`
- **Détection de risque / containment** — `secondary`

## UCKK Seed
Outil d’initialisation/versionnement des registres académiques et templates de la distribution.

- **Registre institutionnel / académique** — `seed_tool`
- **Résolution déterministe de profils** — `template_seed`

