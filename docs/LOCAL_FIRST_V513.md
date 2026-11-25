# V5.13 — source canonique locale et surface publique dérivée

Statut : **procédure candidate de diagnostic**, sans qualification C1/C2, sans sélection de révision et sans autorité de publication.

## Règle d'autorité

- `C:\mycode\Kristal\locals\Kristal-*\canon\` est la source des corrections canoniques pour chaque Kristal local.
- `C:\mycode\Kristal\kristal-public\kristals\<slug>\` est une **projection de lecture dérivée**, pas un lieu de correction.
- Les registres `KQ/KP/KA/KS` sont propres à leur namespace. Un `KQ1001` isolé n'est pas un identifiant fédéré; un QID Wikidata demeure une référence externe, même avec un `exactMatch` proposé.
- L'alignement diK, la provenance, les labels et la preuve de revue restent distincts. Ne jamais deviner un sens à partir d'un identifiant numérique.

## Audit V5.13 (sans mutation)

Depuis la racine Git du Manager :

```powershell
python -m kristal_manager audit-local-public `
  --locals 'C:\mycode\Kristal\locals' `
  --public 'C:\mycode\Kristal\kristal-public' `
  --output "$env:LOCALAPPDATA\Kristal\private-local-first-v513.json"
```

Le dossier parent du rapport doit exister. Le rapport est nouveau, privé et **hors des deux arbres source**; un rapport préexistant n'est pas écrasé. Sans `--output`, seul un résumé JSON est affiché sur stdout; utiliser `--full` pour le rapport intégral par Kristal. Des ZIP de snapshot peuvent remplacer `--locals` et `--public` pour un audit figé sans extraction.

Interpréter `OBSERVATION_ONLY` comme **intégrité des éléments canoniques comparés**, jamais comme approbation sémantique, qualification, sélection de révision ou permission de publier. Code de sortie `3` = blocage d'intégrité; `2` = entrée invalide. Une absence locale du dépôt public est une observation, et un artefact canonique absent de la projection mais **absent du sync-manifest** est hors périmètre de synchronisation, pas une erreur à combler.

**Collision de slugs locaux — V5.13.2 :** si plusieurs dossiers immédiats de `locals` déclarent le même `slug`, le rapport indique leurs chemins, `state_ref`, SHA-256 de chaque `canon/state.index.json` et comparaison à l'index public. Les dossiers ambigus sont exclus des comparaisons autoritatives; les autres Kristals continuent à être audités. Le statut devient `BLOCKED_INTEGRITY` et le rapport est néanmoins enregistré si `--output` est fourni. Même deux index identiques **ne permettent pas** de choisir le canon automatiquement. Le propriétaire doit résoudre l'inventaire et la responsabilité des dossiers avant publication; ne pas déplacer/supprimer de copie en réponse automatique au diagnostic.

Le rapport relève les groupes de révisions v11 **déclarés dans `canon/state.index.json`**. Les groupes partiels et plusieurs révisions ne sont jamais départagés automatiquement. Une seule révision déclarée ne prouve pas une sélection qualifiée. Pour les crosswalks déclarés, il compte les `exactMatch` candidats, acceptés et les méthodes de revue. Une décision `accepted` avec méthode `audited_rule` demeure un **état inscrit dans l'artefact**, pas une qualification indépendante que Manager serait autorisé à déduire.

## Trajectoire autorisée, après revue humaine

1. Examiner les anomalies, la provenance, les libellés et les conflits Wikidata dans diK. Préparer une **nouvelle révision candidate** dans le Kristal local concerné; ne pas remplacer l'histoire.
2. Valider les contrats du Framework et les contrôles de l'Authoring Kit; sélectionner une révision selon le graphe épinglé et ses preuves. Ne pas convertir une similarité lexicale en `exactMatch`.
3. Manager : `stage-public-candidate --slug <slug> --build-on-copy --write-private` construit une copie **privée**, seulement pour les slugs explicitement choisis. Ne jamais exécuter cette étape pour tout `locals` sans revue.
4. Contrôler le candidat, sa chaîne de preuves et la conformité C3. `prepare-public-commit` prépare éventuellement un commit local exact (aucun push).
5. Seul `push-approved-public-commit` avec reçus indépendants C1/C2, politique et accord explicite peut pousser un commit exactement approuvé. C1/C2 non vérifiés = **pas de push**. Publication et activation RuntimeSet sont séparées.

Le Bootstrap peut observer un drift de fichiers gérés. Ses anciens hash dans `bootstrap-state.json` ne doivent être ni réécrits ni « réparés » par cet audit. Rapprochement uniquement sur plan propriétaire revu.

### Périmètre des mesures sur les snapshots du 24 novembre 2026

127 Kristals locaux, 126 membres publics, 126/126 index `state.index.json` identiques, 985/985 artefacts communs identiques, 7 artefacts locaux non déclarés dans les manifestes publics, un Kristal local non publié (`pitheory-prime-bridge`). Dans les crosswalks v11 **déclarés**, 154 occurrences `exactMatch` portent `status=accepted` et `review.method=audited_rule` : les 154 restent à examiner au titre de la preuve indépendante. Ce résultat est un constat des **snapshots fournis**, pas une preuve de l'état Windows après installation ni de qualification Wikidata.
