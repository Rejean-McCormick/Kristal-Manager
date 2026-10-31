# Kristal Manager — Centre d'analyse globale intégré (0.2)

## Installation (Windows)

1. Fermer Kristal Manager.
2. Sauvegarder le dossier existant `C:\mycode\Kristal\Kristal-Manager` (par copie ou ZIP).
3. Décompresser **le paquet complet** dans `C:\mycode\Kristal\`, en fusionnant `Kristal-Manager` (ne pas supprimer les anciens fichiers). Les icônes/logo locaux non présents dans l'instantané source sont ainsi préservés.
4. Démarrer `C:\mycode\Kristal\Kristal-Manager\Launch-Kristal-Manager.cmd`.
5. Dans la fenêtre, vérifier `C:\mycode\Kristal\locals`, puis cliquer **Analyse globale…**.
6. Laisser **Actualiser le catalogue (cache incrémental)** coché. Optionnel : **Vérifier aussi les fichiers enregistrés**.
7. Cliquer **Scanner et analyser les Kristals**. La première passe peut prendre davantage de temps ; la base SQLite évite de reparcourir le contenu inchangé lors des passes suivantes.

## Où sont les résultats ?

- `Kristal-Manager\catalogue\kristal-contenu-global.sqlite3` : catalogue privé incrémental.
- `Kristal-Manager\catalogue\kristal-contenu-global.html` : aperçu du contenu.
- `Kristal-Manager\rapports\analyse-AAAAMMJJ-HHMMSS-xxxxxx\` : rapport daté ; un nouveau dossier à chaque exécution.
- `Kristal-Manager\rapports\problemes-analyse-AAAAMMJJ-HHMMSS-xxxxxx.zip` : preuves individuelles des observations avec avertissement/bloqueur, audit UNESCO et plan de correction, **sans les Kristals sources**.

La fenêtre permet **Copier résultats pour ChatGPT** (résumé de tous les Kristals, états, mots-clés, propositions et anomalies), **Copier Kristal sélectionné** (JSON avec preuves détaillées) et, dans une fiche ouverte par double-clic, **Copier ces détails**. Puis faire `Ctrl+V` dans ChatGPT. Aucun compte ni transfert automatique n’est effectué. Le ZIP reste disponible pour les preuves intégrales. Les rapports contiennent des chemins locaux, éventuellement des sujets et mots-clés : **les relire avant tout partage**.

## Ce que cette version sait faire

- Scanner une racine `locals` et inventorier les Kristals actifs (les archives internes restent séparées).
- Maintenir un catalogue **incrémental** du contenu enregistré ; format inconnu = non observé (pas zéro).
- Extraire les mots-clés observés et une courte description exploratoire.
- Proposer un Arketype `ARK-01…ARK-19` sur des indices **structurels**, même sans classification déclarée.
- Proposer des domaines et microthésaurus UNESCO parmi les 7 domaines et 88 microthésaurus du référentiel épinglé ; jamais au moyen de l'icône ISCED seule.
- Afficher les indicateurs de couverture lexicale utiles à un examen diK (sans générer d'identité KQ/KP).
- En option, vérifier localement l'intégrité des sources Discovery enregistrées, avec 4 travailleurs maximum.
- Préparer un **plan de corrections** non exécutable et exporter les observations problématiques en ZIP.
- Accéder à l'outil de **normalisation des noms en lot**, déjà présent dans le Manager, avec aperçu et sauvegarde obligatoire.

## Fonctionnement local uniquement

Aucune opération Git/GitHub n'est lancée par ce Manager. Le script historique `GitSink.bat` est désactivé et ne peut plus pousser. Les dossiers dérivés `catalogue/` et `rapports/` sont ignorés pour les **nouveaux fichiers Git non suivis**. Un fichier déjà ajouté à Git n'est pas désindexé automatiquement par la mise à jour. La gestion Git se fait séparément, manuellement.

## Limites et précautions

- L'algorithme lexical est heuristique. Ses scores **ne sont pas des probabilités ni des certifications**. Les indices structurels insuffisants sont indiqués comme indéterminés. Arketype et domaine UNESCO sont **indépendants**.
- Ni le Framework, ni KristalDiag externe, ni les convertisseurs canoniques diK/Kit ne sont exécutés automatiquement en masse.
- Aucune classification n'est inscrite dans `kristal.workspace.json` ; aucune identité ou correspondance sémantique n'est modifiée ou créée.
- Le statut `READY` local n'est pas une conformité Framework v11, une qualification C1, une attestation C2/C3 ou une autorisation d'accès.
- Les problèmes de collision d'identité, les états historiques et les conversions diK restent **à examiner avant toute écriture**.
- Les écritures autorisées par ce flux sont **uniquement dérivées** (`catalogue` et `rapports`, hors des Kristals).

## Mode automatisé facultatif (sans nouvelle application)

Le même moteur est appelable via le CLI intégré :

```bat
cd /d C:\mycode\Kristal\Kristal-Manager
py -3 -m kristal_manager analyse-globale C:\mycode\Kristal\locals
```

Option : `--verifier-localement`. Option de cache : `--sans-recataloguer` (attention : les résultats peuvent être périmés). Les chemins `--catalogue` et `--rapports` permettent de changer les destinations en dehors de la racine source.

## Références et provenance

Les 19 définitions Arketype sont reprises du snapshot arketype transmis le 28 octobre 2026, dans `kristal_manager/reference/semantic/arketype/archetypes/`. Le référentiel UNESCO est celui déjà épinglé par Kristal Manager dans `kristal_manager/reference/unesco-thesaurus-profile.json`. Les règles diK sont traduites en **observations lexicales**, pas en vérification du moteur diK. Les contrats diK v11 et Integration Pack n'ont pas été exécutés ni requalifiés dans cette version.
