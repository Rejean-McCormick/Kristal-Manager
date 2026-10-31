# Autorité des données : un seul centre, plusieurs sources spécialisées

Le terme « source centrale » signifie **projection unifiée de l'état des outils**, pas transfert de l'autorité canonique au Manager.

| Donnée | Source faisant autorité | Copie/Projection dans Manager | Mutation autorisée |
|---|---|---|---|
| État, identités, assertions KQ/KP | Kristal / Kit / canon | métadonnées observées | Kit avec procédure explicite |
| Workspace, ARK/PRF déclarés | `kristal.workspace.json`, métadonnées du projet | colonnes et fiches | workflow d'auteur, pas scan |
| Métadonnées Discovery | sorties du Kit et input fingerprint | cache/fraîcheur | Kit après changement explicite |
| Contenu KQ/KP indexé | artefacts source référencés | `kristal-contenu-global.sqlite3` | reconstruction contrôlée |
| Verdict KristalDiag | rapport propre à KristalDiag + preuves | `observations` dans index opérationnel | nouvelle exécution uniquement |
| Proposition structurelle Arketype | rapport Arketype | observation + décision utilisateur | approbation séparée |
| Revue historique | registre local de revue | historique contextualisé | flux de revue |
| Résultats de vérification | moteur de vérification + empreintes | observation dans index | nouveau run |
| Publication GitHub | GitHub et manifeste de publication | lecture de statut externe | jamais depuis scan |

## Distinguer trois niveaux

1. **Réalité source** : fichiers et engagements, peut changer via outils auteurs.
2. **Mesure** : observation datée, explicite sur sa portée et ses limites.
3. **Décision** : validation ou rejet humain/automatisé autorisé, traçable et réversible.

## Ce qui se reconstruit

L'inventaire et le catalogue peuvent être recréés depuis les sources. Les preuves de diagnostics et les décisions humaines doivent être sauvegardées, exportables et auditables : les « reconstruire » en relançant un diagnostic ne reproduirait pas nécessairement l'ancien état.
