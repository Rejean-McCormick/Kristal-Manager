# V5.15 — Conciliation fédérée sans sélection automatique

**État :** implémentation candidate, observation privée, non certifiante.

V5.14 construit le registre des occurrences. V5.15 examine ces occurrences
**sans réécrire** leurs sources et émet un second fichier SQLite privé contenant
des dossiers de revue. Les 190 révisions observées dans le snapshot restent
explicitement `unselected`. Aucune identité n'est fusionnée, aucun Wikidata
`exactMatch` n'est approuvé et aucune donnée locale/publique n'est modifiée.

## Contrat d'entrée et de traçabilité

`reconcile-semantic-observatory` exige le chemin **explicite** d'une base V5.14
existante : le programme ne cherche jamais «la plus récente» au hasard.

- Profil V5.14 et statut `CANDIDATE_INTEGRITY_ONLY` obligatoires.
- Comptages contrôlés contre les tables réelles; les révisions doivent toutes
  rester `unselected`. SQLite doit passer un `quick_check`.
- Empreinte SHA-256 de l'index V5.14 enregistrée, puis recalculée après analyse.
  Si l'entrée a changé, le résultat partiel est rejeté.
- Nouveaux fichiers `.sqlite` et `.json` seulement; sorties existantes ou
  situées dans une source canonique ou un dépôt Git refusées.
- L'index V5.14 original conserve les données source détaillées. Le fichier
  V5.15 conserve chaque dossier de revue et jusqu'à six occurrences exemplaires
  avec chemin, révision et contenu JSON d'origine. Aucun résultat n'est choisi
  à la place du propriétaire.

## Dossiers de revue

| Type | Interprétation | Suite |
| --- | --- | --- |
| `IDENTITY_KIND_VARIANTS` | Un ID de même namespace possède plusieurs rôles | Revue propriétaire |
| `IDENTITY_STATUS_VARIANTS` | Statuts de cycle de vie divergents | Revue de révisions |
| `COMPETING_PREFERRED_TERMS` | Termes préférés distincts pour un `(namespace, ID, langue)` | Concilier sans effacer l'historique |
| `SHARED_LEXICAL_TERM` | Un terme désigne plusieurs ID dans le même namespace/langue | Polynémie possible; ne pas fusionner |
| `EXACTMATCH_TARGET_VARIANTS` | Plusieurs Q/P actifs (`candidate` ou `accepted`) pour un même ID | Revue humaine des preuves KS |
| `EXACTMATCH_STATUS_VARIANTS` | Statuts différents pour une même cible | Revue de provenance |
| `RECORDED_ACCEPTANCE_WITHOUT_EVIDENCE` | Acceptation source sans liste de preuves | Bloquer toute promotion |
| `UNREGISTERED_LEXICAL_ID_IN_COMPLETE_REVISION` | Un terme n'a pas de registre dans une révision pourtant complète | Revue d'intégrité |
| `MULTIPLE_COMPLETE_REVISIONS` | Plusieurs révisions complètes non sélectionnées | Choix explicite du propriétaire |

Les cibles `rejected` sont **exclues** du diagnostic des cibles
`EXACTMATCH_TARGET_VARIANTS`; une proposition rejetée n'est pas une nouvelle
ambiguïté active. Les dictionnaires seuls ne sont pas déclarés «orphelins»
parce qu'ils n'ont pas de registre, puisque c'est un format légitime.

## Commandes PowerShell 7 / Python 3.12

```powershell
$env:PYTHONPATH = 'C:\mycode\Kristal\Kristal-Manager'
$repertoire = Join-Path $env:LOCALAPPDATA 'Kristal'
$source = 'CHEMIN_EXACT_VERS_UN_SEMANTIC_V514.sqlite'
$suffixe = (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + [guid]::NewGuid().ToString('N').Substring(0,8)
$review = Join-Path $repertoire "SEMANTIC_V515_$suffixe.sqlite"
$rapport = Join-Path $repertoire "SEMANTIC_V515_$suffixe.json"
python -m kristal_manager reconcile-semantic-observatory --source-db $source `
    --review-db $review --report $rapport
if ($LASTEXITCODE -ne 0) { throw 'Conciliation bloquée' }
python -m kristal_manager semantic-review-cases --review-db $review `
    --kind EXACTMATCH_TARGET_VARIANTS --limit 10
python -m kristal_manager semantic-review-cases --review-db $review `
    --namespace-id 'kristal:bulk:kristal-neuroscience' --limit 10
```

Le lanceur C0 `scripts/check_semantic_reconciliation_v515.ps1` construit une
nouvelle paire de rapports dans `%LOCALAPPDATA%\Kristal`. L'entrée doit être
passée avec `-SourceDb`; rien n'est choisi implicitement.

## Preuve de snapshot, pas autorité en service

Sur le ZIP local du 24 novembre 2026, la V5.15 a relevé **991 dossiers** :
367 ensembles de cibles `exactMatch` actives multiples (43 avec au moins une
acceptation enregistrée), 6 compétitions lexicales, 546 termes partagés et
72 propriétaires à plusieurs révisions complètes. Les statuts restent des
**observations source**, pas des décisions humaines ni une qualification.

Étape ultérieure séparée : revue du propriétaire, sélection avec empreinte de
la révision exacte, validation Framework v11/TCK, contrôles indépendants,
éventuelles nouvelles révisions **locales** via Kit, puis seulement préparation
de publication dérivée et portes C1/C2/C3.
