# Mesures initiales et protocole de comparaison

## État rapporté au 31 octobre 2026

- 127 Kristals, 0 bloqueur Manager, 16 avertissements de contenu natif limité, 111 « à examiner ».
- 111 graphes/états compris et 16 contrats natifs reconnus, 0 erreur de lecteur.
- Arketype structurel : 28×`3/3`, 49×`2/3`, 14×`1/3`, 33×`0/3`, 3 indéterminés.
- Ensemble de 14 revues historiques locales et 127 déclarations Arketype détectées par le scanner structurel.
- Suite ciblée du dernier overlay : 54 réussites dans un environnement graphique virtuel; suite historique complète non verte.
- Un ancien batch `V9-State-Reader` a produit 88 PASS/31 FAIL/7 WARN/1 BLOCKED **avant certaines corrections**; il ne doit pas servir de baseline courante sans nouveau run.

## Collecte reproductible à prévoir (CIBLE)

Pour chaque build, capturer : commit du Manager, commit/snapshot KristalDiag, version des contrats, OS, Python/Tk/PS7, manifeste des 127 workspaces (chemin normalisé + `state_ref` + hash de l'état d'entrée), nombre de diagnostics par profil, erreurs, temps total, p50/p95, mémoire de pointe, taille du catalogue, nombre de `CURRENT`/`STALE`, nombre de données proposées/approuvées.

**Ne pas comparer** 127 verdicts V9 et 127 verdicts de profil auto-adaptatif comme s'ils couvraient la même règle. Comparer par (`engine_version`, `profile`, `scope`, `source_fingerprint`).

## Critère d'amélioration

Passer de « plusieurs écrans et CSV divergents » à un parcours où chaque résultat possède un identifiant de run et une fiche commune; les 127 scans doivent demeurer `LOCAL_CHECKS_PASSED` si les sources n'ont pas changé; aucune réussite artificielle. Les seuils de performance exacts seront fixés après mesure Windows, pas inventés ici.
