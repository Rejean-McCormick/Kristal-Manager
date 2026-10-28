# Kristal Icon Generator — UNESCO Thesaurus (politique active)

- **Une seule taxonomie de domaine : UNESCO Thesaurus**, référence épinglée dans `Kristal-Framework/spec/v7/reference-kos/unesco-thesaurus-profile.json`, miroir local `runtime/unesco-thesaurus-profile.json` (**7 domaines, 88 microthésaurus**).
- Les notations UNESCO canoniques sont `1` à `7` et les URI sont celles du profil. `UT1` à `UT7` sont **uniquement des tokens de noms d’icônes** pour éviter la collision avec les anciens noms ISCED (`01` à `10`). Les couleurs sont la palette Kristal, **pas des couleurs officielles UNESCO**.
- Le profil de domaine provient exclusivement des métadonnées explicites `kristal.workspace.json > classification.unesco_thesaurus` (ou `classification.unesco`). Les microthésaurus, s’ils existent, doivent appartenir aux domaines déclarés. Les statuts `candidate`, incohérents et absents restent **non classés** et sont inscrits dans `unresolved_unesco`. Aucun fallback sur l’ancien code ISCED, le nom du dossier, le README ou l’icône n’est autorisé.
- Le domaine 7 (`Countries and country groupings`) est une facette géographique dans le TOC par défaut : il ne constitue pas une catégorie résiduelle.
- Natures `REF|COL|MOD|PRT|TWN|INV|SRC` et maturités `M0…M5` restent indépendantes.
- Format icône `KR-{NATURE}-UT{CODE}[-UT{CODE}][-UT{CODE}]-M{0…5}.ico`. Les fichiers existants `KR-*-00…10-*.ico` restent historiques ; ils ne sont pas renommés ni réutilisés automatiquement. Un nouveau rendu et l’écriture de `desktop.ini` exigent toujours l’action de l’utilisateur.
- Dans `desktop.ini`, `DomainScheme=UNESCO Thesaurus`, `DomainLevel=domain`, `Domain1=1` (etc.) ; dans `.kristal/icon-profile.json`, chaque domaine porte `code`, `uri` et `icon_token`. `state_ref` et les identités KQ ne changent pas.
- Arketype (`ARK-*` et `PRF-*`) décrit la structure et le profil d’usage et ne dépend pas du Thésaurus.
