# Publication Wiki avec SemantiK Architect

Dans la fenêtre du Manager **Publier sur GitHub**, le quatrième bouton appelle désormais
`kristal-public/tools/wiki_export.py` avec les trois dépendances explicites :

- `SemantiK Architect` (racine du dépôt Python/SDK) ;
- `RuntimeSet SemantiK` (racine des runtimes qualifiés) ;
- `Projections privées SA` (un `<slug>.json` vérifiable par Kristal du commit publié).

Chemins proposés :

```text
C:\mycode\Kristal\SemantiK-Architect
C:\mycode\Kristal\SemantiK-Architect\runtime
%LOCALAPPDATA%\Kristal\private-candidates\wiki-semantic-projections
```

La génération refuse les profils manquants / non qualifiés, les assertions sans
provenance, les obligations non couvertes, les digests C3 divergents et les commits
non confirmés. Elle ne crée jamais de preuves de publication, ne déploie pas le Wiki
GitHub et ne copie pas `locals` dans le dépôt public.

**Statut important :** le raccordement logiciel est préparé, mais les cinq Kristals
ne possèdent pas encore dans les artefacts fournis de projections de communication
au contrat SemantiK ni de RuntimeSets qualifiés pour leurs domaines. Le brouillon
Wiki en prose ne peut donc pas être annoncé prêt à publier. Le Manager doit recevoir
ces projections depuis la couche sémantique propriétaire, pas les deviner.

Voir également `kristal-public/docs/SEMANTIK_WIKI.md`.
