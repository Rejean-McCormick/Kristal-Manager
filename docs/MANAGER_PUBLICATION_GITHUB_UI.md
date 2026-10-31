# Publier sur GitHub depuis Kristal-Manager

## Parcours intégré

Dans `Kristal-Manager.pyw`, ouvrir **Publier sur GitHub…** dans la barre d'actions
ou dans le menu Actions. La fenêtre permet la **sélection explicite** des
Kristals dans `locals`, sans créer de liens Windows ni modifier les sources.

1. **Préparer la collection privée** : utilise le Kit existant
   (`tools/kristal.py`) et le service `publication_stage.py` du Manager. Les
   constructions se font **sur copies temporaires**. Le répertoire candidat
   est créé sous `%LOCALAPPDATA%\Kristal\private-candidates` par défaut, en
   dehors de tous les dépôts Git.
2. **Préparer le commit local** : requiert un checkout propre de `kristal-public`
   sur `main`, dont `origin` correspond à `Rejean-McCormick/kristal-public`.
   Vérifie le candidat par le contrôleur **C3 déjà fourni par le dépôt public**,
   copie exclusivement les fichiers cités dans les manifestes et crée un commit
   local, sans aucun push. Un éventuel ancien stub Zoology peut être retiré
   **uniquement** en cochant l'option et si son contenu exact est reconnu.
3. **Qualification et autorisations** : faire qualifier le commit (son SHA exact)
   par les autorités indépendantes C1/C2. Fournir le fichier de confiance
   C123, un reçu `slug.json` dans chaque dossier C1/C2 et le répertoire de
   politique C2. Le contrôleur `tools/c123_offline.py` du dépôt public et
   `kristal_manager.publication_gate` du Manager sont vérifiés successivement.
   Une vérification hors réseau ne **confère pas** à elle seule une autorisation;
   les émetteurs et l'état des révocations doivent être confirmés indépendamment.
4. **Vérifier et pousser** : une confirmation explicite, les deux familles de
   preuves correctes, un commit immuable et un remote inchangé sont requis.
   Le code exécute **uniquement** `git push origin HEAD:refs/heads/main`.
   Le SHA distant est ensuite vérifié. Le Manager n'appelle jamais GitSink.

**Dry Run** est activé par défaut. Aucune étape de préparation ne contacte
GitHub. Les champs de sécurité ne sont pas enregistrés dans les préférences.
Ne pas utiliser le `GitSink.bat` générique pour diffuser des données de Kristals;
il fait `git add --all` et son comportement n'est pas lié aux contrôles C1/C2.

## CLI équivalente, sans lanceur supplémentaire

```powershell
cd C:\mycode\Kristal\Kristal-Manager
python -m kristal_manager stage-public-candidate --locals C:\mycode\Kristal\locals --kit C:\mycode\Kristal\Kristal-Authoring-Kit\tools\kristal.py --output "$env:LOCALAPPDATA\Kristal\private-candidates\lot5" --slug kristal-ai --slug kristal-accounting --slug kristal-aerospace --slug kristal-aging --slug kristal-agriculture --write-private --build-on-copy
python -m kristal_manager prepare-public-commit --candidate "$env:LOCALAPPDATA\Kristal\private-candidates\lot5" --checkout C:\mycode\Kristal\kristal-public --retire-zoology-stub --write
```

Après signature C1/C2 indépendante et contrôle des autorisations :

```powershell
python -m kristal_manager push-approved-public-commit --checkout C:\mycode\Kristal\kristal-public --trust C:\chemin-prive\c123-trust.json --c1-dir C:\chemin-prive\c1 --c2-dir C:\chemin-prive\c2 --policy-dir C:\chemin-prive\c2-policy --confirm-independent-approval --push
```

Sans `--push`, la dernière commande ne modifie aucun serveur. Il faut également
que `KRISTAL_C2_TRUST_PIN` soit configuré vers l'empreinte attendue du trust C2.
Les deux familles de preuves ont des formats différents, conservés tels quels.
Il n'est pas possible de les remplacer par une case cochée ou par un simple test
local du Kit.

## Ce que le bouton ne fait pas encore

- Il ne crée pas de clés/signatures C1/C2, ne supprime pas une autorisation,
  ne contourne pas le blocage de publication du dépôt public.
- Il n'active pas le **Wiki GitHub natif**, actuellement désactivé côté dépôt.
  Le générateur existant `kristal-public/tools/wiki_export.py` peut produire un
  brouillon privé lié au SHA *après* que la publication soit confirmée; le
  déploiement du dépôt wiki reste une action distincte.
- Il n'écrase pas silencieusement des Kristals déjà hébergés et ne met pas
  automatiquement à jour un index public existant. Une évolution incrémentale
  exige un protocole signé pour la nouvelle révision.

## Journal et état

Le panneau écrit dans son journal et dans celui de la fenêtre principale du
Manager. Le lien retourné après un vrai push est :
`https://github.com/Rejean-McCormick/kristal-public/tree/<SHA>/kristals`.
Les essais en copies locales ne sont pas des attestations C1/C2.

## Brouillon Wiki depuis le même panneau

Après confirmation du SHA en ligne, **4 · Générer le brouillon Wiki après push**
lance le générateur `tools/wiki_export.py` déjà présent dans `kristal-public`.
Le brouillon `Home.md`, `_Sidebar.md` et les fiches par Kristal sont écrits
dans un **nouveau dossier privé hors Git**, avec liens vers le SHA public exact.
Il reste à activer l'option Wiki dans les réglages GitHub, puis à pousser ces
pages dans le dépôt Git du wiki avec une approbation de cette diffusion.
