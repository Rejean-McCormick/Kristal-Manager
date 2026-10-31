# SQLite : état présent et schéma cible

## Deux bases, deux finalités

1. **Contenu descriptif** (`catalogue/kristal-contenu-global.sqlite3`) : index lourd, HTML et recherches; ne pas versionner dans Git et ne pas assimiler au canon.
2. **Opérations** (`catalogue/kristal-manager-operations.sqlite3`) : index léger de résultats, observations et contexte. Dans l'overlay récent, `central_store.py` l'ouvre avec SQLite transactionnel (`busy_timeout=20000`, `foreign_keys=ON`, `user_version=1`).

## Schéma livré — v1

```sql
CREATE TABLE workspaces (
  path_key TEXT PRIMARY KEY, path TEXT NOT NULL, state_ref TEXT,
  title TEXT, readiness TEXT, profile TEXT, observed_at TEXT NOT NULL
);
CREATE TABLE observations (
  event_id TEXT PRIMARY KEY,
  path_key TEXT NOT NULL REFERENCES workspaces(path_key),
  kind TEXT NOT NULL, profile TEXT NOT NULL DEFAULT '',
  status TEXT, observed_at TEXT NOT NULL,
  source_fingerprint TEXT NOT NULL, payload TEXT NOT NULL
);
CREATE INDEX idx_observations_lookup
  ON observations(path_key, kind, observed_at DESC);
```

`kind` actuellement accepté : `diagnostic`, `analysis`, `inventory`, `arketype`, `verification`; payload JSON borné à 2 Mio. La base v1 est utile mais ne stocke pas encore séparément la portée de fingerprint ni tous les champs d'exécution/provenance.

## Schéma cible v2 (proposition, **ne pas exécuter sur la base actuelle**)

```sql
CREATE TABLE runs (
  run_id TEXT PRIMARY KEY, engine TEXT NOT NULL, engine_version TEXT,
  profile TEXT, requested_at TEXT NOT NULL, started_at TEXT, ended_at TEXT,
  process_status TEXT NOT NULL, config_digest TEXT, report_root TEXT
);
CREATE TABLE workspace_instances (
  instance_id TEXT PRIMARY KEY, path TEXT NOT NULL UNIQUE,
  state_ref TEXT, title TEXT, last_seen_at TEXT
);
CREATE TABLE observations_v2 (
  observation_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL REFERENCES workspace_instances(instance_id),
  run_id TEXT REFERENCES runs(run_id),
  kind TEXT NOT NULL, verdict TEXT, source_scope TEXT,
  input_fingerprint TEXT, observed_at TEXT NOT NULL,
  payload_json TEXT NOT NULL, evidence_uri TEXT, evidence_sha256 TEXT
);
CREATE TABLE decisions (
  decision_id TEXT PRIMARY KEY, instance_id TEXT NOT NULL,
  taxonomy TEXT NOT NULL, code TEXT NOT NULL, status TEXT NOT NULL,
  evidence_ref TEXT, actor TEXT, decided_at TEXT, supersedes TEXT
);
```

## Pratiques d'exploitation

- Transactions courtes; migrations avec copie à froid ou `sqlite3.Connection.backup()`; `PRAGMA integrity_check` et version cohérente.
- En cas de panne SQLite, conserver preuves/CSV et marquer index partiel; ne jamais jeter le rapport moteur.
- WAL possible sur disque local compatible, à étudier avec antivirus Windows; éviter un dossier synchronisé cloud pour la DB active.
- Requêtes paginées, index sur `(instance_id, kind, profile, observed_at)`; ne pas charger 189 Mo dans le processus GUI.
- Préserver le réglage `.gitignore` : exclure les bases locales et rapports (un fichier déjà suivi doit être retiré via procédure Git, non supprimé du disque).
