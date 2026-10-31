# Kristal Manager — mode local uniquement

## Frontière explicite

- Le Manager n'effectue **aucune** commande `git add`, `git commit`, `git push`, `git pull` ni publication GitHub.
- Le fichier historique `GitSink.bat` reste présent uniquement pour neutraliser les anciens raccourcis : il affiche un avertissement et retourne un code d'erreur sans appeler Git.
- Les données dérivées se trouvent dans `catalogue/` (SQLite/HTML) et `rapports/` (rapports/archives ZIP). Ces répertoires sont exclus de Git pour les **nouveaux fichiers non suivis**.
- Attention : `.gitignore` ne retire **pas** rétroactivement les fichiers déjà suivis ou présents dans des commits. Leur éventuel nettoyage de l'historique Git relève exclusivement du processus Git manuel, en dehors du Manager.
- Les opérations restent locales. Aucune modification de `locals/` par l'analyse globale ; les autres fonctions d'écriture éventuelles nécessitent une confirmation explicite.

## Flux de travail

1. Ouvrir le Manager et vérifier la racine `C:\mycode\Kristal\locals`.
2. Ouvrir **Analyse globale…**.
3. Lancer **Scanner et analyser les Kristals**.
4. Examiner le rapport et le plan de corrections ; exporter/transmettre le ZIP `rapports/problemes-analyse-*.zip` si nécessaire.
5. Corriger uniquement les cas examinés et relancer l'analyse pour comparaison.

**Aucun push GitHub n'est nécessaire ni proposé dans ce flux.**
