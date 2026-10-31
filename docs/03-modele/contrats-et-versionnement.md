# Contrats d'échange et versionnement

## Principe

Une observation est enregistrée en un format Manager versionné, mais **conserve le rapport natif du moteur** via une référence, un digest et une provenance. L'adaptateur est une *anti-corruption layer*, non une conversion qui détruit les champs spécifiques.

## Enveloppe cible `kristal.manager.observation/2.0` (proposition)

```json
{
  "format": "kristal.manager.observation/2.0",
  "observation_id": "sha256:...",
  "run_id": "run-...",
  "workspace": {"state_ref": "urn:kristal:state:physics", "path": "C:\\mycode\\Kristal\\locals\\Kristal-Physics"},
  "kind": "diagnostic",
  "source": {"engine": "KristalDiag", "version": "recorded", "profile": "V9-State-Reader", "contract_pin": "recorded"},
  "input": {"fingerprint_scope": "v9-known-files/1", "fingerprint": "sha256:..."},
  "execution": {"started_at": "2026-10-31T12:00:00Z", "ended_at": "2026-10-31T12:00:08Z", "status": "DONE"},
  "result": {"verdict": "PASS", "qualification": "NOT_ESTABLISHED"},
  "evidence": {"uri": "file:///.../summary.json", "sha256": "..."},
  "freshness": "CURRENT"
}
```

**Remarque** : les `...` sont des espaces réservés dans ce contrat cible; aucun objet contenant ces valeurs ne doit être accepté en production.

## Identité/idempotence

`observation_id = sha256(canonical_json(workspace_instance, kind, engine, profile, input_fingerprint, evidence_digest, schema_version))`. Une exécution distincte a son propre `run_id`; deux événements identiques rejoués ne doublonnent pas. Une nouvelle exécution sur les mêmes entrées peut produire un `run_id` distinct, sans écraser l'ancienne.

## Compatibilité

- **Lecture ascendante** : importeurs `0.1`/`1.0` séparés et testés; pas de renommage silencieux des verdicts.
- **Écriture** : seule la version active du contrat est émise; un ancien client reçoit une erreur claire de version.
- **Payload** : borner volume; preuves détaillées stockées hors SQLite, référencées par digest.
- **Horodatage** : UTC et chaîne ISO explicite; ne pas utiliser l'heure de l'import pour prétendre dater l'analyse historique.

Pour l'existant, voir [stockage](../04-donnees/stockage-sqlite.md) et [exemple ancien](../12-references/exemples-de-resultats.md).
