# Dépendances, versions et frontière d'indépendance

## Observé dans les archives

- Manager : application Python/Tk, modules `kristal_manager/`, `tools/KristalDiag/` empaqueté, scripts de lancement Windows, outils de catalogue/rapport.
- KristalDiag : projet Python indépendant `kristaldiag/` et contrats embarqués sous `contracts/`/`resources/` ; `pyproject.toml` demande Python 3.11+ et `jsonschema>=4.20`.
- Manager alpha historique : `pyproject.toml` indique Python 3.11+, `cryptography` optionnel pour la voie publique; les fonctionnalités récentes possèdent aussi la dépendance `jsonschema` via Diag.
- Toolkits Arketype et Authoring Kit : sources et dictionnaires séparés, non équivalents à une librairie d'UI.

## Politique cible de vendoring

Choisir **une seule** politique de distribution pour chaque moteur : (A) dépendance versionnée avec hash; (B) snapshot embarqué sous `tools/` avec `VERSION`, licence, manifeste SHA-256 et tests du bridge. Le code embarqué ne devient pas, par simple copie, un module interne de Manager : le moteur conserve son protocole CLI, ses contrats, ses tests de conformance et son cycle de release.

## Versions croisées

Conserver une matrice `manager_version` × `diag_version` × `framework_contract_pin` × `kit_version`, avec statut `tested`, `unsupported`, `unknown`. Le snapshot KristalDiag examiné cible **Framework 10.0.0-draft.3.1**; aucune conformité v11 complète ne peut être déduite.

## Gestion de la compatibilité

Une évolution de CLI Diag provoque un test de contrat et un bump explicite de l'adaptateur; ne pas introspecter ou invoquer arbitrairement des profils par chaînes construites depuis un workspace. Le protocole autorisé est allowlisté côté Manager, versionné et capturé dans chaque run.

## Contrôle CI proposé

Tests d'import sans Tk; tests de subprocess non-shell; snapshot de rapport, compatibilité du schéma; analyse des chemins `tools/` et des contrats; comparaison de hashes du vendor; test de smoke Windows avec les prérequis réellement distribués.
