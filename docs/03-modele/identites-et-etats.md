# Identités, chemins et registres

## Hiérarchie

Le `state_ref` déclaré identifie l'état métier. Le chemin local identifie une **instance de workspace sur un poste**. Le titre est une étiquette mutable. Les identités KQ/KP/KA/KS concernent des entités/relations/preuves, et ne doivent pas être confondues avec la clé de la table de workspaces.

## Forme cible

```json
{
  "workspace_instance_id": "local:... (identifiant stable généré hors canon)",
  "path": "C:\\mycode\\Kristal\\locals\\Kristal-Physics",
  "state_ref": "urn:kristal:state:physics",
  "title": "Kristal-Physics",
  "discovery": {"readiness": "READY", "fingerprint": "sha256:..."},
  "alias_paths": [],
  "observed_at": "2026-10-31T12:00:00Z"
}
```

**Exemple de schéma cible, pas un artefact à copier dans les sources.**

## Règles de rapprochement

- Un `state_ref` peut apparaître via plusieurs chemins : ne pas écraser silencieusement une instance par l'autre.
- Un déplacement de dossier avec même état ne rend pas automatiquement valides des preuves liées à des chemins de sortie; conserver lineage et repérer les déplacements.
- Un titre renommé ne constitue pas une identité nouvelle.
- Sous Windows, traiter la casse avec normalisation stable et interdire les symlinks non autorisés; conserver le chemin d'origine pour l'affichage.
- Les dossiers historiques/auxiliaires ne sont pas comptés parmi les workspaces principaux sans indication explicite.

## Implémentation livrée

`central_store.py` v1 utilise `_key(Path.resolve().casefold())` comme clé du workspace et stocke `state_ref` comme attribut. C'est un choix opérationnel transitoire : la version cible doit supporter les renommages/déplacements sans fusion abusive.

## Tests de collision

Même title / états différents; même `state_ref` / chemins différents; path déplacé; répertoire supprimé puis restauré; `state_ref` absent; historique non applicable; chemins très longs Windows et caractères Unicode.
