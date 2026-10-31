# Performance, cache et opérations sur 127 Kristals

## Objectif

Réduire le coût du travail répétitif et rendre les gros lots récupérables, sans sacrifier la fraîcheur ni les preuves. Les seuils chiffrés seront établis après benchmark Windows, pas prescrits arbitrairement.

## Principaux coûts constatés

- Énumération récursive et hachage de gros corpus.
- Variantes multiples de graphes v11 (anciens `wikidata-...`, `v11-1`, `v11-2`).
- Catalogue global potentiellement très volumineux (~189 Mo sur un poste ancien).
- Exécution d'un subprocess KristalDiag par workspace.
- Rendu de colonnes Treeview et tri/filtre des 127 sans modèle de données partagé.

## Optimisations sûres

1. Mise en cache **par entrée et portée**; contenu réutilisé uniquement si hash/digest fiable et version de lecteur identique.
2. Scan « léger » pour métadonnées courantes, analyse « lourde » explicite.
3. Pools bornés, par défaut 1 subprocess Diag; mesurer avant d'autoriser davantage de concurrence.
4. Écrire un résumé incrémental après chaque Kristal; reprise en cas d'interruption sans refaire ceux dont le résultat reste courant.
5. Mémoriser dimensions et totaux de graphe sans charger leurs objets en entier dans l'UI.
6. Pagination de l'historique et des findings; rechercher par SQLite/index dédié.
7. Isoler mises à jour GUI via file de messages; ne jamais appeler `subprocess.run()` sur le thread Tk.
8. Sauvegarder les empreintes d'entrée par lot pour distinguer vrais changements du simple changement de date.

## Mesures à produire

Temps p50/p95 par moteur, taux de cache, bytes hachés, peak RSS, temps de réponse GUI pendant batch, nombre de fichiers/répertoires observés, taux d'erreur, taille des preuves, temps reprise après arrêt.

## Limites

Il est interdit de sauter un contrôle requis parce qu'il est lent tout en conservant un verdict `PASS`; les sorties partielles doivent indiquer `PARTIAL`/`UNVERIFIED` selon le contrat approprié.
