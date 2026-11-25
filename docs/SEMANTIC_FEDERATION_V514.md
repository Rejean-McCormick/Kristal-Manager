# Observatoire sémantique fédéré V5.14 — candidat privé

## Décision

La source canonique demeure **chaque Kristal local**, suivant son propre
`canon/state.index.json`. `kristal-public` est une surface de lecture dérivée,
jamais l'endroit où corriger le canon. Manager expose un **index SQLite privé,
reconstruisible**, sans créer d'identité, sélectionner de révision, fusionner de
concepts, approuver de mapping Wikidata ni publier.

## Identités et sens

- La clé d'une identité est **`(namespace_id, semantic_id)`**. Un `KQ1001`
  nu peut désigner plusieurs identités dans plusieurs namespaces.
- Chaque occurrence conserve le Kristal propriétaire, le répertoire de
  révision, le chemin canonique, les octets de référence SHA-256 et
  l'enregistrement JSON source; les occurrences de révisions distinctes
  restent distinctes, même pour la même clé.
- Un terme n'est pas effacé: les couches lexicales curatées `.json` et les
  couches Wikidata `.jsonl` gardent terme, langue, priorité, couche,
  namespace, provenance et données de revue disponibles.
- Un Q/P Wikidata est un **identifiant externe**, jamais un nouveau KQ/KP.
  `candidate` et `accepted` sont les **statuts enregistrés dans la source**,
  et ne signifient aucune qualification indépendante par cet observatoire.
- Un groupe de révision peut être complet (4 rôles), «dictionnaire seul» ou
  incomplet. Les variantes historiques `registry.json`, `graph.json` et
  `crosswalk.json` sont des alias de rôles si le `artifact_type` est correct.
  Les formats `canon/domain/v11/updates/<rev>/`,
  `canon/domain/v11/<rev>/` et `canon/domain/v11/` sont reconnus uniquement
  si les fichiers figurent dans le manifeste canonique local.

## Construction hors des dépôts

```powershell
$env:PYTHONPATH = 'C:\mycode\Kristal\Kristal-Manager'
$base = Join-Path $env:LOCALAPPDATA 'Kristal'
New-Item -ItemType Directory -Force -Path $base | Out-Null
$suffixe = (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + [guid]::NewGuid().ToString('N').Substring(0,8)
$db = Join-Path $base "SEMANTIC_V514_$suffixe.sqlite"
$rapport = Join-Path $base "SEMANTIC_V514_$suffixe.json"
python -m kristal_manager build-semantic-observatory `
  --locals 'C:\mycode\Kristal\locals' --db $db --report $rapport
if ($LASTEXITCODE -ne 0) { throw 'Intégrité V5.14 bloquée : lire le rapport' }
python -m kristal_manager semantic-observatory-query --db $db --q 'KQ1001'
python -m kristal_manager semantic-observatory-query --db $db --q 'Q42'
python -m kristal_manager semantic-observatory-query --db $db --q 'étoile' `
  --namespace-id 'kristal:bulk:kristal-astronomy'
```

La construction refuse l'écrasement d'un index/rapport existant, la sortie dans
la source canonique et dans un dépôt Git, les chemins dangereux, les doublons
de slug, les membres ZIP ambigus et les collisions d'identifiants complets
entre propriétaires. L'intégrité des couches lexicales est comparée à la SHA-256
inscrite dans chaque catalogue. Une anomalie bloquante produit
`BLOCKED_INTEGRITY` (exit 3); une exception empêche l'index partiel.

## Limites et prochaines portes

Ce contrôle n'est ni une validation Framework v11/TCK, ni une vérification de
provenance cryptographique Wikidata, ni un choix de révision canonique. Les
empreintes calculées attestent uniquement les octets lus. La sélection
contrôlée, la conciliation interrévisions, l'approbation de mapping et les
portes indépendantes C1/C2/C3 exigent des preuves distinctes et une décision
explicite avant tout effet sur les Kristals locaux ou la publication.
