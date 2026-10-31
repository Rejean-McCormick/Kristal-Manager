# Tests et réserves réelles

## Tests effectués dans la sandbox Linux

- Migration v1→v2 et sauvegarde préalable.
- Idempotence v1/v2, écriture dans une seule transaction.
- Profil de diagnostic et provenance `run_id` distincts.
- Marquage `STALE` lorsqu'un fichier V9 suivi change.
- Observation Arketype marquée `PARTIAL_SCOPE`, jamais certifiée.
- Décision locale sans changement du canon.
- Inventaire complet et dashboard sur 127 Kristals simulés.
- V9 `NOT_APPLICABLE` et `EXECUTION_ERROR` sans fausse réussite.
- Diagnostic interrompu et reprise des éléments de preuve déjà enregistrés.
- Import de rapport ancien conservé comme `UNVERIFIED`.
- Ouvrir / fermer / rouvrir GUI sous affichage Xvfb.

Les tests ne remplacent pas un essai sous Windows 11 + PowerShell 7.

## Suite complète (à qualifier avant publication stable)

La suite historique a encore 16 échecs sur un snapshot de base. La plupart
concernent l'ancien backend de publication, volontairement désactivé (aucun
push/commit Git autorisé par Manager). Deux concernent des assertions de
l'ancienne GUI devenues obsolètes sur l'ordre des colonnes et la catégorie
UNESCO. **Aucun test n'a été modifié pour masquer ces échecs.**

Les tests ciblés vNext, l'indexation, l'intégration graphique, l'UI locale,
les ressources graphiques et le nouveau registre réussissent. Voir le
rapport `LIVRAISON-VNEXT-TESTS.txt` à la racine du dépôt complet.

## Définition de terminé pour une future vNext stable

Une suite historique révisée et cohérente avec la politique de sécurité,
une stratégie de profils v10/v11/natifs et un test complet sous Windows réel
restent nécessaires avant de qualifier cette version comme stable.
