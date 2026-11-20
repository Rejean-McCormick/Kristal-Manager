# UCKK Publisher v0.2.3 — alignement remount v0.1.9

- Réintègre le correctif critique de v0.1.9 dans le deploy-agent durci : après chaque bascule de `/opt/uckk/current`, `php`, `web` et `cron` sont recréés avec `--force-recreate`.
- Vérifie ensuite via `docker inspect` que chaque bind mount pointe exactement sur la release immuable publiée; la publication échoue sinon.
- Le rollback force la même recréation afin de remonter réellement la release précédente.
- Passe le deploy-agent de `0.2.0` à `0.2.1`, ce qui force Publisher à détecter un agent VPS non réinstallé.
- Aligne l'identité HTTP de vérification sur `UCKK-Publisher/0.2.3`.

> Important : après ce drop-in, réinstaller le deploy-agent root-owned sur le VPS avec `server/install_deploy_agent.sh`; sinon le prévol refusera la publication avec une version d'agent inattendue.

# UCKK Publisher v0.1.8 — source de vérité + navigation publique

- `C:\mycode\UCKK\uckk-moodle` devient explicitement la **source de vérité** du code UCKK.
- `C:\mycode\UCKK\moodle\moodle\public` est le **runtime local**, jamais la source éditoriale.
- `Préparer le paquet` synchronise automatiquement la source vers le runtime, supprime uniquement les fichiers devenus obsolètes qui étaient précédemment suivis par le Publisher, puis vérifie chaque empreinte. Une divergence résiduelle bloque le paquet.
- Si la source change après `Préparer`, `Mettre UCKK en ligne` reconstruit automatiquement le paquet avant l’upload.
- `Vérifier UCKK en ligne` contrôle maintenant la navigation UCC `Voies / Cours / Penseurs`, le routage public des cartes de Voies et les repères `Languirand / Proulx / Einstein / Spinoza / Bergson / Teilhard de Chardin`.
- Docker local n’est pas requis pour synchroniser ou préparer. Il est seulement nécessaire si le runtime local lui-même est servi par Docker et qu’on veut tester le site local dans le navigateur.

## Rôles consolidés

- **uckk-moodle** : source de vérité du code.
- **UCKK Ops Console** : développement et maintenance locale (démarrage du Moodle local, diagnostics, upgrade, purge caches, opérations techniques).
- **UCKK Publisher** : propriétaire exclusif du pipeline de publication (prévol, sync source → runtime, contrôle d’intégrité, paquet, déploiement, rollback de release et vérification HTTPS).
- **VPS `/opt/uckk`** : cible de déploiement; pas une source à modifier manuellement.

# UCKK Publisher v0.1.7 — landings multi-façades

- `https://uckk.org/` redirige vers la page login UCKK avec `theme=uckk` et le bouton « Explorer sans connexion ».
- `https://ucc.uckk.org/` est une porte d’entrée publique qui redirige vers la page d’accueil UCC (`/local/uckk/index.php?theme=ucc`).
- `https://math.uckk.org/` est une porte d’entrée publique qui redirige vers la page d’accueil Math (`/local/uckk/index.php?theme=ucmath`).
- UCC et Math restent des alias d’entrée vers l’unique Moodle canonique `uckk.org`; `$CFG->wwwroot` reste unique et stable.
- Le `verify` contrôle désormais les trois contrats de landing et des marqueurs de contenu, en plus du MIME CSS.
- Nécessite des enregistrements DNS A/AAAA valides pour `ucc.uckk.org` et `math.uckk.org` vers le VPS.
- Conserve les correctifs v0.1.6 : rollback, seed contrôlé, Médiathèque, Moodle 5.2, Traefik, egress, PATH_INFO/CSS, BOM et cron.

# UCKK Publisher v0.1.6


## Correctifs v0.1.6

- Corrige l’exécution SQL du rattachement Médiathèque : le Publisher passe désormais explicitement le script à MariaDB avec `-e` au lieu de le fournir comme argument positionnel.
- Vérifie que la bibliothèque primaire UCKK a bien été résolue et que MariaDB renvoie les compteurs attendus avant de poursuivre la publication.
- Journalise `bibliothèque`, `médias rattachés` et `publics actifs` pour rendre cette étape vérifiable dans le rapport de publication.
- Conserve le rollback de release introduit en v0.1.5 : si une étape échoue, `/opt/uckk/current` revient à la release précédente et les conteneurs sont relancés.
- Conserve tous les correctifs précédents : seed contrôlé, Moodle 5.2, routage `r.php`, PATH_INFO/CSS, egress Docker, BOM PHP, cron et Traefik.

## Correctifs v0.1.5

- Corrige l'orchestration du seed lors des republications : les presets sont appliqués en groupes dépendance-sûrs au lieu d'un `apply` global opaque.
- Évite le défaut d'idempotence actuellement observé dans le preset `competencies` : si le référentiel `UCKK-COMP-FRAMEWORK` existe déjà, le Publisher valide le registre mais n'applique pas une seconde fois ce preset.
- Sur une installation neuve, `competencies` est toujours appliqué une première fois avant les badges, templates, cours et rapports.
- En cas d'échec après la bascule de release, `/opt/uckk/current` est automatiquement restauré vers la release précédente et les conteneurs applicatifs sont relancés.
- `tool_uckkseed.defaultmode` est remis à `dry_run` même en cas d'échec.
- La sauvegarde DB + moodledata pré-publication est conservée. Le Publisher ne restaure pas automatiquement la base de manière destructive afin d'éviter d'effacer des écritures légitimes intervenues pendant la publication.
- Conserve tous les correctifs v0.1.4 : Moodle 5.2, routage `r.php`, PATH_INFO/CSS, egress Docker, BOM PHP, Médiathèque, cron et Traefik.

## Correctifs v0.1.4

- Active réellement le mode `apply` de `tool_uckkseed` pendant la publication puis remet `defaultmode=dry_run`; `--force` seul ne suffisait pas et les Voies/cours restaient absents.
- Configure définitivement le routeur Moodle 5.2 (`r.php`) pour les routes extensionless et les shims `.php`, avec conservation correcte de `PATH_INFO` pour `theme/styles.php/...`.
- Ajoute `$CFG->root`, `$CFG->dirroot`, `$CFG->libdir` et `$CFG->routerconfigured = true` au `config.php` généré; conserve `$CFG->sslproxy = true` sans activer `reverseproxy`.
- Ajoute un réseau Docker egress dédié à `php` et `cron`, tout en gardant MariaDB uniquement sur le réseau interne.
- Rattache après import les médias UCKK dont `libraryid` est NULL à la bibliothèque primaire du site `uckk`, afin que la Médiathèque publique puisse les exposer.
- Normalise les fichiers PHP de la release en supprimant les BOM UTF-8 susceptibles de casser les en-têtes HTTP/CSS.
- Aligne la boucle cron sur un démarrage approximativement toutes les 60 secondes au lieu d’attendre 60 secondes après la fin de chaque exécution.
- Conserve les correctifs Traefik v0.1.3 et les correctifs de layout/DB des versions précédentes.

## Correctifs v0.1.3

- Corrige l’erreur Moodle `reverseproxyabused` derrière Traefik : le Host public est conservé, donc `$CFG->reverseproxy` ne doit pas être activé dans cette architecture; `$CFG->sslproxy` reste activé pour la terminaison TLS en amont.
- Met à jour le fichier dynamique Traefik en conservant son inode, afin que le conteneur Traefik voie immédiatement les changements lorsqu’il est bind-mounté sur ce fichier.
- Conserve tous les correctifs v0.1.2 et v0.1.1.

## Correctifs v0.1.2

- Corrige la détection de base Moodle existante : la requête MariaDB n'injecte plus un antislash invalide dans le SQL.
- Rend `config.php` lisible par le conteneur PHP exécuté en `www-data`; les identifiants DB restent fournis par l'environnement Docker et ne sont pas stockés dans ce fichier.
- Conserve le correctif v0.1.1 pour le layout Moodle séparé (`public/admin/tool/uckkseed` et `public/tools/uckk-ops`).
- Masque désormais le mot de passe admin initial dans les logs de commandes Docker.


Application Windows légère pour publier l'installation Moodle UCKK actuelle sur le VPS Netcup déjà utilisé par Konnaxion.

## Ce que l'application fait

1. Vérifie le Moodle local, le seeder UCKK et le corpus Médiathèque.
2. Vérifie l'accès SSH au VPS, `sudo -n`, Docker, le réseau public Konnaxion et la configuration Traefik existante.
3. Construit un paquet local à partir du Moodle installé et du corpus Médiathèque.
4. Déploie UCKK dans `/opt/uckk` avec Docker Compose :
   - PHP 8.4-FPM
   - Nginx interne
   - MariaDB
   - cron Moodle
5. Attache le conteneur web au réseau public Traefik et donne à PHP/cron un réseau egress séparé; MariaDB reste isolée.
6. Ajoute une route `Host(...)` UCKK dans le fichier dynamique Traefik existant, après sauvegarde.
7. Installe/upgrade Moodle avec les CLI Moodle.
8. Exécute `tool_uckkseed` en dry-run puis apply.
9. Exécute l'import Médiathèque en dry-run puis apply.
10. Purge les caches et vérifie les pages HTTPS.

## Configuration préremplie

Les valeurs VPS ont été reprises du snapshot Konnaxion fourni :
- cible Netcup existante ;
- utilisateur SSH non-root `kx-admin` ;
- clé Ed25519 locale ;
- réseau Docker public de l'instance `konnaxion-prod` ;
- Traefik Konnaxion comme unique entrée HTTP/HTTPS ;
- UCKK isolé sous `/opt/uckk`.

Le mot de passe Moodle admin n'est jamais écrit dans `uckk_publisher.config.json`.

## Disposition Moodle locale supportée

Le Publisher reconnaît la disposition Moodle actuelle de UCKK :

- scripts CLI du cœur Moodle dans la racine, par exemple `admin/cli/upgrade.php` ;
- webroot et plugins UCKK sous `public/` ;
- `tool_uckkseed` sous `public/admin/tool/uckkseed/` ;
- importeur Médiathèque sous `public/tools/uckk-ops/`.

Il accepte aussi l'ancienne disposition où ces outils UCKK étaient directement à la racine. Il ne faut pas copier manuellement les plugins hors de `public/` pour satisfaire le prévol.

## Utilisation

Lancer :

`Start_UCKK_Publisher.bat`

Puis suivre les boutons dans l'ordre :

1. `Vérifier le local UCKK`
2. `Vérifier le VPS Netcup`
3. `Préparer le paquet`
4. `Mettre UCKK en ligne`
5. `Vérifier UCKK en ligne`

## DNS

Pour obtenir le HTTPS normal, le domaine configuré doit pointer vers le VPS Netcup avant ou peu après la publication. Traefik réutilise son resolver ACME existant.

## Sécurité

- SSH en clé publique seulement.
- Publication via `kx-admin` + `sudo -n`.
- Aucun port Moodle n'est publié directement sur l'hôte.
- UCKK rejoint le réseau Traefik existant uniquement par son conteneur Nginx.
- MariaDB reste sur un réseau Docker interne.
- Une sauvegarde DB + moodledata est créée avant une republication d'un site déjà installé.
- Le fichier dynamique Traefik est sauvegardé avant modification.
- Les secrets MariaDB sont conservés uniquement dans `/opt/uckk/runtime/.env` avec permissions 0600.
- Les rapports locaux n'enregistrent pas les mots de passe.

## Remarque

Le fichier dynamique Traefik appartient au runtime Konnaxion. Une action Konnaxion qui le régénère peut retirer la route UCKK. Relancer `Mettre UCKK en ligne` réapplique la route. Une intégration permanente pourra ensuite être ajoutée au générateur Traefik Konnaxion si nécessaire.
