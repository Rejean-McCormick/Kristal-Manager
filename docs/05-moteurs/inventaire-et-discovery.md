# Inventaire, Discovery et lecture de l'état

## Implémentation observée

`core.scan_roots()` cherche les dossiers Kristal, détecte `kristal.workspace.json`, normalise le `state_ref`, repère les états candidats et les liens parent/enfant; `discovery.py` et `workspace_tools.py` gèrent les métadonnées générées et leur fraîcheur. Le code traite explicitement les workspaces historiques/auxiliaires.

## Contrat du scanner cible

Entrées : racines locales autorisées, options d'inclusion des archives et chemins exclus. Sorties : `WorkspaceRef`, `state_ref`, `format`, `native_kind`, readiness, engagement observé, candidats de conflit, fingerprint de Discovery, type de contrat, signal d'incomplétude. Une erreur de lecture d'un workspace est **isolée**, les 126 autres restent visibles.

## Stratégie de performance

- Phase A : énumérer les répertoires candidats et leurs descripteurs sans recalculer tous les hashes canon.
- Phase B : invalider uniquement les workspaces dont les fichiers d'entrée connus changent; enregistrer la portée de chaque empreinte.
- Phase C : effectuer les lectures et SHA supplémentaires uniquement sur demande ou lorsqu'un cache n'est pas fiable.
- Toujours permettre « rescan complet » avec équivalence de résultats, et profiler les postes Windows (disque local/antivirus).

## Fraîcheur

La suppression ou modification d'un fichier source invalidant Discovery doit déclencher un avertissement précis, non être masquée par une date de scan récente. Une modification du `kristal.workspace.json` peut légitimement nécessiter une régénération Discovery par le Kit. Cette action **n'appartient pas** au scanner de Manager.

## Tests

127 principaux reconnus; 16 natifs; dossiers imbriqués; conflit de `state_ref`; répertoire temporairement verrouillé; casse Windows; chemin long; lien symbolique; workspace renommé; Discovery périmé; absence de source sans crash global.
