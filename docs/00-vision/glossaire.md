# Glossaire opérationnel

| Terme | Sens retenu |
|---|---|
| Kristal local | Répertoire avec contrat de workspace/état, source analysée |
| `state_ref` | Identité d'état déclarée; ne pas la confondre avec le nom du dossier |
| Canon | Artefacts et engagements faisant autorité du côté Kristal/Kit, non du côté Manager |
| KQ/KP/KA/KS | Familles d'identités/relations/sources propres à Kristal; ne jamais générer par simple appariement lexical |
| Discovery | Métadonnées dérivées décrivant le workspace et sa fraîcheur |
| Catalogue de contenu | Index descriptif et recherche sur contenus KQ/KP et fichiers observés |
| Registre opérationnel | SQLite léger des workspaces, observations, dates, profils et liens vers preuves |
| Observation | Résultat attribué à un outil, avec limite de portée |
| Verdict | Résultat d'un profil de diagnostic déterminé (`PASS`, `FAIL`, etc.) |
| Statut de processus | Le moteur a-t-il été lancé, terminé, échoué ou interrompu ? |
| Fraîcheur | Concordance entre empreinte de l'entrée du run et état actuel observable |
| `NOT_APPLICABLE` | Profil non applicable, **pas** erreur ni succès |
| `NOT_RUN` | Aucun diagnostic correspondant encore enregistré ou lancé |
| `STALE_OR_UNVERIFIED` | Preuve historique, empreinte absente ou source modifiée |
| ARK | Classification structurelle Arketype, distincte du profil d'usage |
| PRF | Profil d'usage, peut être générique et à affiner |
| UNESCO | Domaine/microthésaurus proposé ou déclaré, non certification sémantique |
| Wikidata Q/P | Liens externes candidats ou acceptés **selon provenance**, pas validation externe automatique |
| C1/C2/C3 | Surfaces/étapes de qualification/autorisations distinctes à documenter par contrat Framework officiel |
| Moteur embarqué | Copie versionnée de KristalDiag fournie avec Manager, utilisée comme processus indépendant |
| Overlay direct | Archive à extraire à la racine prévue, sans exécution implicite |

## Étiquettes documentaires

`OBSERVÉ`, `LIVRÉ`, `CIBLE`, `HYPOTHÈSE`, `NON ÉTABLI`. Le libellé utilisateur peut être localisé; la valeur machine doit être stable et testée.
