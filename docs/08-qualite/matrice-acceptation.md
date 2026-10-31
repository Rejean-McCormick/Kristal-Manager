# Matrice d'acceptation du futur Manager

| ID | Scénario obligatoire | Attendu | Preuve de validation |
|---|---|---|---|
| AC-01 | Scan 127 sources | mêmes 127 identités, aucun effacement | manifeste comparé |
| AC-02 | Scan sans Diag | aucune exécution enfant | journal processus vide |
| AC-03 | Diag V9 applicable | verdict réel, provenance, preuves | `summary.json` validé |
| AC-04 | Natif sans V9 | `NOT_APPLICABLE` argumenté | fixture native |
| AC-05 | Run PASS, puis rescanner | verdict réapparaît sans relancer | SQLite + UI |
| AC-06 | Modifier entrée source | ancien PASS marqué périmé | fingerprint delta |
| AC-07 | Import ancien CSV PASS | `UNVERIFIED`, jamais CURRENT | rapport CSV historique |
| AC-08 | Rejouer un import | aucun événement dupliqué | compteur événements |
| AC-09 | Rapport Arketype 3/3 | affiché observation, non certification | fiche classification |
| AC-10 | UNESCO proposé valide | affiché proposé, pas « erreur de schéma » | mapping fixture |
| AC-11 | Test interrompu | sortie correcte, historique conservé | kill/process failure |
| AC-12 | DB manquante/corrompue | dégradation gracieuse, pas faux PASS | injection SQLite |
| AC-13 | Import ZIP chemins dangereux | refus, aucune sortie hors répertoire | path traversal fixture |
| AC-14 | `locals` avant/après | mêmes hashes pour opérations read-only | diff SHA-256 |
| AC-15 | Export de résultats | manifeste, dates, profils, limites | inspection fichier |
| AC-16 | Publication/GitHub | aucune opération implicite | faux remote et test réseau |
| AC-17 | 127 fiches UI | filtre/tri/sélection conservés | test GUI Windows |
| AC-18 | Retour arrière schéma | base précédente restaurée sans perte | scénario DB rollback |
| AC-19 | Diagnostic V10 choisi | profil réellement supporté et vérifié | rapport moteur |
| AC-20 | Lecture v11/native cible | couverture et limites honnêtes | corpus de validation |

## Gates de sortie

**P0 bloquants** : AC-01 à AC-08, AC-11 à AC-14 et AC-16. **P1 produit** : AC-09/10/15/17/18. **P2 extension** : AC-19/20, à planifier avec profils versionnés. Les critères non applicables doivent être marqués `NOT_TESTED` ou `NOT_APPLICABLE`, jamais cochés tacitement.

## Rapport de release

Inscrire versions Manager, Diag, Kit/Framework, OS Python et chemins sources anonymisés, cas testés, statut, logs, hashes, limitations connues, décision de validation et rollback. Aucun bilan « 127/127 OK » sans préciser la surface et le profil.
