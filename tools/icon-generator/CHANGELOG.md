## 2.7.0 — 2026-10-28

- Nouveau mode `--locals` : inventaire UNESCO direct des Kristals locaux, en mémoire, sans écriture au démarrage.
- Écriture des ICO et `desktop.ini` locale strictement bloquée à moins de `--enable-local-apply`, même si une requête HTTP tente d'écrire.
- Activation dans Kristal-Manager à chaque session, OFF par défaut, suivie d'une seconde coche et confirmation dans l'interface.
- Jamais de conversion ISCED → UNESCO ; exclusion des workspaces non classés ou incohérents.
- Actualisation de la présentation locale après application ; aucun effet sur le canon et les engagements d'identité.

## 2.6.0 — 2026-10-28

- Consolidation des domaines sur le Thésaurus UNESCO (7 domaines, 88 microthésaurus).
- Élimination d’ISCED-F du scanner et de la sélection active ; les anciens profils sont à réviser, jamais convertis automatiquement.
- Icônes à noms distincts `UT1` à `UT7`, conservation des vrais codes et URI UNESCO en métadonnées.
- Registry, validateur et génération de `desktop.ini` alignés ; l’écriture reste une action explicite.

## 2.5.0 — 2026-10-06

- observes Kristal v9 `state_ref` and logical commitment during collection scans as presentation evidence only;
- ships a v9-aware Registry builder while preserving the v8 normalization overlay as compatibility input;
- keeps icon/profile/desktop.ini output derived and non-authoritative.

# 2.4.0 — Domaines ISCED-F 2013 (UNESCO)

- remplace la charte de domaines maison par les 11 grands domaines **ISCED-F 2013** (`00`–`10`) ;
- verrouille les codes et noms UNESCO dans l’interface ; seules les couleurs de présentation Kristal restent éditables ;
- ajoute une migration des anciens codes (`BIO`, `AI`, `LAW`, `GAME`, etc.) vers ISCED-F ;
- migre la couche méta embarquée et le Registry bootstrap vers ISCED-F ;
- classe `Pokemon/Pokémon/game` dans `02 — Arts et lettres` ;
- ajoute `DomainScheme=ISCED-F 2013` et `DomainLevel=broad-field` dans `desktop.ini` ;
- n’invente plus de domaine arbitraire pour les cas sans correspondance ; ils sont reportés dans `unresolved_isced` ;
- conserve jusqu’à trois domaines comme extension visuelle Kristal, explicitement distincte du codage statistique officiel ;
- précise que les couleurs sont Kristal et **non officielles UNESCO**.

# Changelog

## 2.3.0 — scan automatique des nouveaux Kristals

- scanne automatiquement `Kristal-Kollection\domains\Kristal-*` au lancement ;
- détecte les nouveaux Kristals et les entrées Registry au profil d'icône incomplet ;
- ajoute `runtime/scan-kristals.mjs`, sans dépendance externe ;
- ajoute une palette runtime de domaines au générateur (remplacée en 2.4 par ISCED-F 2013) ;
- utilise la priorité : profil explicite → desktop.ini → métadonnées structurées → README/structure → fallback déterministe ;
- reconnaît notamment `Pokemon/Pokémon` comme domaine `GAME` ;
- calcule une maturité de représentation à partir de la structure, sans attribuer automatiquement M5 ;
- écrit `.kristal/icon-profile.json` et `.kristal/auto-scan.json` pour les profils manquants ;
- écrit `_registry/icon-scan-report.json` ;
- conserve l'origine et la confiance de la classification dans le profil Registry ;
- ajoute un fallback Node permettant d'injecter un nouveau profil dans un Registry existant même si Python n'est pas disponible ;
- conserve le clic explicite avant toute application ICO / `desktop.ini` ;
- conserve le correctif Windows EPERM de la 2.2.2.

## 2.2.2 — desktop.ini EPERM intégré

- retire `ReadOnly`, `Hidden` et `System` de `desktop.ini` avant lecture/réécriture ;
- remet `Hidden` et `System` après écriture, sans remettre `ReadOnly` ;
- conserve `attrib +R` sur le dossier pour l'application de la personnalisation Explorer.

## 2.2.1 — clic explicite dans l'interface

- le launcher prépare le Registry et ouvre l'interface sans appliquer d'icônes ;
- un seul bouton principal déclenche l'écriture.
