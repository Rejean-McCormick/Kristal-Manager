# Contribution à la documentation et au code

## Discipline de changement

1. Lire [STATUS](STATUS.md) et l'[ADR sur le monolithe](11-decisions/0001-monolithe-modulaire.md).
2. Pour un changement de protocole, commencer par le contrat public et un test indépendant; pour une interface, commencer par le parcours utilisateur.
3. Ajouter un ADR si le changement altère l'autorité d'un stockage, l'indépendance du diagnostic, les permissions ou les frontières des modules.
4. Décrire les effets de bord (`locals`, base de contenu, index opérationnel, rapports, Git).
5. Ajouter tests heureux, erreur, interruption, péremption et réexécution; mettre à jour la matrice d'acceptation.
6. Vérifier les liens et la grammaire de statut; versionner la documentation dans le même changement que le code.

## Nommage et conventions

- Python 3.11+, type hints pour les ports publics; entrées structurées plutôt que dictionnaires arbitraires à la frontière.
- Identifiants techniques immuables distincts du titre affiché; chemins Windows comparés avec stratégie explicite.
- Journal et rapport : UTC ISO 8601; valeurs d'état stables en anglais, libellés UI français localisables.
- Respecter le principe *proposition != approbation != canon*.
- Un nouveau scanner écrit dans un adaptateur d'ingestion, **pas directement dans les tables ou le Treeview**.
- Ne pas placer de données privées de diagnostic dans les fixtures publiques.

## Revue obligatoire

La PR doit inclure : périmètre, composantes modifiées, migration oui/non, provenance de l'évidence, tests exécutés, tests non exécutés, risque de régression et plan de retour arrière. Les métriques et limites du corpus de 127 sont datées, jamais présentées comme des garanties intemporelles.

## Maintenance de `/docs`

- Ce dossier est la **documentation du futur produit** : ne pas y copier sans sélection toute l'histoire des overlays.
- Les anciens fichiers de référence du Manager et du Diag restent disponibles en zone `legacy` ou archive tant que les décisions ne sont pas migrées.
- Les guides joints influencent les choix; ils ne remplacent pas les contrats spécifiques du code Kristal.
