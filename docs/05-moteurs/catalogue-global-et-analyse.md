# Catalogue de contenu, analyse globale et triage

## Existant

`content_catalog.py` construit l'index SQLite de contenu et l'aperçu HTML; `global_analysis.analyze_all()` peut reconstruire ou réutiliser le catalogue, produire un audit UNESCO, un triage sémantique et des vérifications locales. Les sorties sont dirigées hors des Kristals et une analyse crée un dossier de rapport unique.

## Portée

Le catalogue mesure et indexe les contenus observables; il n'est pas un moteur de preuve de vérité des KQ/KP. L'analyse globale affiche les statuts `blocker`, `warning`, `review`, `info` selon leurs règles, mais une action `review` signifie souvent **validation sémantique nécessaire** et non panne technique.

## 16 contrats natifs

La dernière analyse affiche 16 `native_observed`, tous avec `CONTENT_OR_ALIGNMENT_REVIEW: content inference limited`. Ce résultat signifie que le lecteur de contenu a des **limites de couverture**, pas que les sources sont corrompues. L'optimisation cible ajoute des adaptateurs natifs typés, une mesure « couvert/ignoré/échec » et le lien vers les fichiers réellement inspectés.

## Recommandations

1. Découpler construction de catalogue et calcul des propositions sémantiques : chacun peut être rejoué de façon traçable.
2. Garder un cache indexé par périmètre et hash; éviter les relectures des versions v11 historiques identiques.
3. Ne pas relire intégralement des couches de dictionnaires similaires si les hashes l'autorisent.
4. Distinguer « métadonnées UNESCO proposées existantes » d'une incohérence de code.
5. Centraliser les observations finales dans le registre, conserver les fichiers analytiques détaillés hors SQLite léger.

## Tests de comparaison

Même source + même catalogue = résultat équivalent; modification d'une seule source = invalidation ciblée; une entrée d'archive historique ne compte pas comme nouveau Kristal; absence de lecture native = couverture limitée, non verdict négatif sur la vérité métier.
