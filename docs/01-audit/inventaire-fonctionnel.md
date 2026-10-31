# Inventaire des fonctions — à préserver pendant la refonte

| Capacité existante | UI future | Adaptateur ou service cible | Risque de perte |
|---|---|---|---|
| Scanner des dossiers | Inventaire | `inventory` | Dossiers imbriqués/historiques |
| Découvrir identité/état | Fiche Kristal | `discovery` | Conflits de `state_ref` |
| Contrôler intégrité locale | Fiche → Vérifier | `local_integrity` | Coût hachage |
| Produire catalogue KQ/KP | Analyser / Contenu | `catalog` | Temps/189 Mo |
| Analyse globale | Centre de contrôle | `analysis` | Provenance des suggestions |
| UNESCO | Fiche → Classification | `classification` | `proposed` ≠ `approved` |
| Arketype structurel | Fiche → Classification | `arketype` | 3 critères indicatifs |
| PRF | Fiche → Usage | `classification` | 96 profils généraux |
| Registre de 14 revues | Fiche → Historique | `review_registry` | Repères historiques devenus changés |
| Diag V9/V10 individuel | Fiche → Diagnostiquer | `diag_bridge` | Processus externe borné |
| Diag V9 en lot | Centre → Diagnostiquer lot | `diagnostics_batch` | Applicabilité et reprise |
| Import rapports historiques | Historique → Import | `operations_cli`/port | Ancien verdict non vérifié |
| Bundle/inventaire constellation | Avancé | `bundle_inventory` | Intégrité des archives |
| Kristalizer imports | Avancé / fiche | `kristalizer_bridge` | Problèmes d'identité temporelle |
| Icônes locales | Avancé / préférences | `icon_bridge` | Effets secondaires Windows |
| Publication/GitHub | Avancé, séparé et gardé | `publication_gate` | Ne jamais activer automatiquement |

## Méthode de déduplication

Pour chaque fonction, conserver **un déclencheur principal** et rediriger les anciens menus vers la même commande du service. Les anciens contrôles pourront subsister transitoirement comme raccourcis, mais ne doivent pas entretenir une deuxième implémentation du résultat. Une fonction ne doit pas être supprimée simplement parce qu'elle est peu visible.

## Preuves attendues avant suppression

Matrice ancien → nouveau; parité des rapports; migration de préférences; scénario d'un Kristal natif, d'un Kristal v11 et d'un Kristal v9; test de non-publication; retour arrière sur base historique.
