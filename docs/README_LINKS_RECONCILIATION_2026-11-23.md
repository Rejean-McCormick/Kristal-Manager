# Kristal Manager — réconciliation des liens du README (23 novembre 2026)

**Type :** observation documentaire locale (`OBSERVED_SNAPSHOT`), **pas** publication, activation ni preuve de fonctionnement.

Source examinée : `SmartDump_20261123_144857.zip` > `Kristal-Manager_Code_snapshot.zip`, complétée par le contrôle d’existence de ces chemins sur GitHub `main` le 23 novembre 2026. Les neuf chemins ci-dessous ne figurent pas dans la capture ni dans le `main` consulté. La disponibilité dans d’autres branches, dans l’historique Git ou sur le disque original n’a pas été certifiée.

## Neuf références auparavant non résolues

| Référence du README précédent | État au 23-11 | Alternative réellement présente / action requise |
|---|---|---|
| `CONSOLIDATION_2026-10-27.md` | Absent | [Guide d’activation des icônes locales](LOCAL_FOLDER_ICONS_OPT_IN.md) ; conserver le document daté en historique s’il est retrouvé |
| `MISE_A_JOUR_ICONES_1924.md` | Absent | [Guide d’activation des icônes locales](LOCAL_FOLDER_ICONS_OPT_IN.md) ; pas de reconstitution du récit horaire |
| `ARCHITECTURE.md` | Absent | [Architecture cible](02-architecture/architecture-cible.md), explicitement **non implémentation garantie** |
| `docs/RECOVERY_STATUS.md` | Absent | [Audit daté de l’existant](01-audit/existant.md) et [implémentation vNext datée](13-implementation-vnext/README.md) ; le README racine reste la description des limites annoncées |
| `docs/KONSTELLATION_INVENTORY.md` | Absent | Section « Private Konstellation preview export (experimental) » du `README.md` racine (description de l’export, **pas** contrat ratifié) |
| `docs/V10_ALIGNMENT.md` | Absent | [Compatibilité V9/V10/V11](05-moteurs/compatibilite-v9-v10-v11.md) ; qualification du runtime indépendante |
| `docs/C2_PUBLICATION_CONTROL.md` | Absent | [Séparation des droits](09-securite/publication-et-separation-des-droits.md) et tests `tests/test_c2_public_gate.py` ; pas de permission de publier |
| `docs/HISTORICAL_RUNTIME_RECOVERY.md` | Absent | Référence de commit dans le README ; le script annoncé `tools/restore_original_backend.py` est également **absent**. La récupération n’est pas exécutable depuis la capture. |
| `docs/PRIVATE_STAGE_C3.md` | Absent | Politique de [séparation des droits](09-securite/publication-et-separation-des-droits.md) ; outil `stage-public-candidate` **non retrouvé** dans la capture. |

## Limites à préserver

- Les changements ci-dessus remplacent des **liens morts** par des sources existantes ou par une explication d’absence. Ils ne prétendent pas recréer les anciens documents.
- Le module de catalogue en lecture seule et les exports locaux ne doivent pas être assimilés à la synchronisation GitHub ou à la publication C3.
- L’interface « Publier sur GitHub… » fait l’objet d’une documentation conservée dans `docs/MANAGER_PUBLICATION_GITHUB_UI.md`; son opérationnalité ne peut pas être déduite du seul lien documentaire. Les barrières décrites par le README racine restent prioritaires dans cette compilation.
- Les travaux de récupération de code ou de publication nécessitent des artefacts authentiques, des tests d’acceptation et une décision propriétaire séparée. Aucune action Git n’est incluse dans cet overlay.
