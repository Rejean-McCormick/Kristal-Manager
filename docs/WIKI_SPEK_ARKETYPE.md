# Wiki Kristal — pipeline Manager → SemantiK → Spek

## Séparation des responsabilités

- `locals` demeure l'unique espace source canonique.
- Le Manager sélectionne les Kristals et les assertions **à exposer** (la mise en page ne choisit pas les faits).
- SemantiK Architect réalise les formulations à partir d'entrées sémantiques structurées, non de prose brute.
- Spek reçoit les **unités déjà sélectionnées**, leurs rôles éditoriaux et les réalisations SemantiK par clé/langue.
- Le dépôt `kristal-public` contient les surfaces publiées après C1/C2/C3 et l'export Wiki produit des **brouillons privés**.

## Répertoire de transfert privé

Par défaut, le panneau « Publier sur GitHub » utilise :

```text
%LOCALAPPDATA%\Kristal\private-candidates\wiki-spek-inputs\
  kristal-ai\
    article.json
    realizations.json
    archetype.json
  kristal-accounting\
    article.json
    realizations.json
    archetype.json
```

Format de `archetype.json` :

```json
{"format":"spek.wiki-archetype-binding/1.0","archetype":"referentiel-semantique"}
```

Le `slug` du dossier doit correspondre exactement à `kristals/index.json` (C3). L'archétype doit appartenir aux 19 profils de `Spek/wiki-templates/archetype-profiles.json`.

Le `article.json` est une projection **Spek** `kristal.layout-article-source/0.1`, et `realizations.json` est une table `kristal.layout-realizations/0.1`. Les clés de titre, sous-titre, résumé, headings et unités doivent toutes être renseignées. Pour l'export réel, les réalisations doivent annoncer un canal `semantik_architect`, le request ID et le RuntimeSet, sans prétendre que Spek valide leur signature.

## Opération

1. Préparer la collection C3 sur un commit local du dépôt public et obtenir les autorisations indépendantes C1/C2.
2. Confirmer que ce **même** commit est en ligne ; ceci est contrôlé par `publication_flow.py`.
3. Fournir les bundles Spek remplis par les résultats SemantiK; l'automatisation de ce mapping est un chantier restant.
4. Cliquer sur **« Composer le Wiki avec Spek + SemantiK après push »**.
5. Le dossier créé est privé et contient `Home.md`, `_Sidebar.md`, une page par Kristal et `manifest.json` ; **ce bouton ne pousse pas le Wiki natif**.

Le GitHub Wiki natif de `kristal-public` est un dépôt Git distinct et doit être activé dans les paramètres. Publication ultérieure seulement après revue éditoriale, confidentialité, qualification SA, approbations et signature des surfaces.

## Limites intentionnelles

- Pas de réalisation de texte automatique depuis un état brut : SemantiK requiert une projection de communication explicite.
- Pas de conversion heuristique d'un archétype vers un layout incompatible.
- Pas de publication ni de réseau dans Spek.
- Pas de faux succès si une fiche manque, si l'état v9 ne correspond pas ou si la source n'est pas validée.
