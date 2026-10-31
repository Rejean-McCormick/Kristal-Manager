# Imports, exports et traçabilité

## Exports standards cibles

| Export | Contenu | Emplacement | Garanties |
|---|---|---|---|
| Résumé utilisateur | inventaire, statuts, priorités, profils | hors `locals` | colonnes documentées, dates/versions |
| Analyse technique | observations, findings, limitations | hors `locals` | identifiants de runs, portée |
| Preuves KristalDiag | rapports intégraux, fichiers de niveau, sha256 | dossier de preuve versionné | préserver le format original |
| Révision taxonomique | propositions ARK/PRF/UNESCO | CSV/JSON séparés | jamais approuvées à l'import |
| Maintenance DB | inventaire des index, `integrity_check` | dossier maintenance | pas de secrets ni assertions brutes non demandées |

## Imports autorisés

Rapport Arketype : valider format `arketype.structural-batch/0.1`, `path` et `state_ref`, borne de taille, résultats 127 prévisibles mais non exigés en général. Anciens diagnostics : respecter CSV historique (`Kristal;Profil;Verdict;Rapport...`) et marquer `UNVERIFIED` faute de fingerprint. Rapports Kristalizer : une surface à part, versionnée et non confondue avec le diagnostic indépendant.

## Vérification de provenance

Pour chaque import : conserver `source_filename`, `content_sha256`, `imported_at`, `source_created_at` si déclaré, `report_version`, `adapter_version`, `original_uri`, `verified_digest`, `limitations`. L'import d'un ZIP doit vérifier que les chemins internes n'échappent jamais au dossier destination et doit rejeter les liens symboliques non autorisés.

## Exemple d'export PowerShell (opérationnel, existant)

```powershell
cd C:\mycode\Kristal\Kristal-Manager
python -m kristal_manager.operations_cli etat --root C:\mycode\Kristal\locals
python -m kristal_manager.operations_cli importer-arketype C:\chemin\RAPPORT_ARKETYPE_STRUCTURE.json
```

**Ces commandes appartiennent à l'overlay du 31-10.** Elles ne préjugent pas de la présence du module sur une installation plus ancienne.
