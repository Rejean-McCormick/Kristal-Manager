# Kristal Manager — ajout des icônes sur la version 19 h 24

**Base préservée :** `znapshot_Kristal-Manager_10271924.zip`, soit Manager `0.1.0-alpha.15+ui-organize-diagbridge-2026-10-27`.

## Installation

1. Conserver une copie de l'ancien Manager et **ne pas décompresser dans** `C:\mycode\Kristal\locals`.
2. Décompresser l'archive complète dans un dossier neuf, par exemple `C:\mycode\Kristal\Kristal-Manager-Icones`.
3. Lancer `Launch-Kristal-Manager.cmd` (Python 3.11+ avec Tkinter).
4. Conserver ou saisir `C:\mycode\Kristal\locals`, puis cliquer **Analyser le dossier**.
5. Les icônes lisibles apparaissent devant le nom du Kristal dans la première colonne. Leur nature figure dans la colonne **Icône / nature**. Une absence de miniature ne signifie pas que le dossier Windows a perdu son icône.
6. Pour les icônes installées après le scan : **Icônes > Actualiser les icônes (lecture seule)**.
7. **Info icône** ou le menu **Icônes > Information** précise le fichier `.ico`, la provenance, la nature et la maturité, sans vérification sémantique.

## Provenance des icônes (lecture seule)

1. `desktop.ini` du Kristal (`[.ShellClassInfo] IconResource`) et fichier `.ico` local. Lecture UTF-8 ou UTF-16 LE.
2. `.kristal/icon-profile.json` et cache `.ico` dans le Kristal.
3. En dernier recours, Registry de présentation dans `C:\mycode\Kristal\Kristal-Kollection\_registry\...`, **sur nom de dossier identique uniquement**. Variable optionnelle `KRISTAL_COLLECTION_ROOT` pour changer ce chemin.

Le Registry ne démontre pas que l'icône est appliquée à Windows, et ne synchronise pas les données de Kristal-Kollection avec `locals`. Le décodeur Tkinter ne sait afficher que les trames ICO avec image PNG (telles que celles produites par ce générateur). Les anciens ICO uniquement BMP restent intacts, mais sans miniature dans Manager.

## Générateur Windows d'origine

Le projet **Kristal Icon Generator 2.5.0** est fourni dans `tools/icon-generator/`, inchangé par la fusion.

- **Icônes > Ouvrir Kristal Icon Generator (Windows)…** : lance `tools/icon-generator/Ouvrir_Generateur.cmd` avec confirmation explicite.
- **Node.js** est nécessaire ; ce lanceur vise par défaut `C:\mycode\Kristal\Kristal-Kollection` et non `locals`.
- Le scan de démarrage du générateur **peut écrire** des profils de présentation et le Registry dans sa collection. La modification des icônes Windows via `.ico` et `desktop.ini` reste contrôlée **dans l'outil d'origine**, sur action explicite.
- Après une application depuis le générateur, revenir dans Manager et utiliser **Actualiser les icônes**. Rien ne se déclenche automatiquement et Manager n'écrit pas sur `desktop.ini`.

## Évolutions 19 h 24 conservées

Le Manager conserve le module **KristalDiag externe**, les catégories, le tri, le masquage d'archives, le renommage explicite de dossier avec prévisualisation, la sauvegarde ZIP, l'export `.kristal` expérimental, le catalogue SQLite, les exports JSON, et le journal Copier/Effacer/Enregistrer.

Les fichiers `core.py`, `diag_bridge.py`, `workspace_tools.py`, `content_catalog.py`, `ui_prefs.py` et leurs tests existants n'ont pas été modifiés par cette intégration. Les assets du logo officiel `#1E6864` ont aussi été restaurés : la version 19 h 24 contenait des références à ces assets mais ne les embarquait pas.

## Limites et tests

- **82 tests ciblés réussis**, dont le pont d'icônes, le rendu de GUI Tk en affichage virtuel, les catégories, la sélection, le tri et les tests préexistants de KristalDiag et d'organisation.
- **Suite intégrale : 112 réussis, 14 échecs hérités**, dans `tests/test_core.py`. Ces échecs proviennent d'anciennes opérations de synchronisation/publication/migration GitHub désactivées et d'un résultat historique `VALID` attendu à la place de `LOCAL_STRUCTURE_ONLY`.
- L'application réelle des icônes de dossier par Windows Explorer reste à tester **sur Windows**. Un test Linux/Tk ne reproduit pas le shell Windows.
- Aucune synchronisation GitHub, qualification Framework, publication ou activation automatique n'est réintroduite.
- Arkétype n'a **pas** été intégré à cette mise à jour ciblée : la demande portait sur les icônes et la conservation des nouveautés du Manager 19 h 24.
