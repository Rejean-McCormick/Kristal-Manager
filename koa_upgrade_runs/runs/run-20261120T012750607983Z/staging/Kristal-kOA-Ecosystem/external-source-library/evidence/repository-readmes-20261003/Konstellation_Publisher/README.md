# Konstellation Publisher v0.1.3

## Correctif v0.1.2

Le healthcheck Docker utilise `127.0.0.1` depuis le conteneur. Konstellation valide strictement l’en-tête `Host`; le Publisher ajoute donc maintenant `localhost`, `127.0.0.1` et `[::1]` aux hôtes autorisés, en plus de `konstellation.uckk.org` et des alias configurés. Les échecs de santé affichent également les derniers logs du conteneur pour faciliter le diagnostic.

Application Windows légère pour publier **Konstellation 0.5** sur le même VPS Netcup que Konnaxion/UCKK, sans exposer le port 4321 sur l'hôte.

## Ce que fait le Publisher

1. Vérifie le dépôt local Konstellation, le pack JSON optionnel et les Lens.
2. Vérifie SSH, `sudo -n`, Docker, le réseau public Konnaxion et le fichier dynamique Traefik.
3. Fabrique un paquet de release reproductible côté Publisher.
4. Envoie le paquet sur le VPS et installe la release sous `/opt/konstellation`.
5. Construit une image Docker Node 24.15, puis démarre Konstellation sur un réseau Docker interne + le réseau Traefik existant.
6. N'expose aucun port hôte. Traefik rejoint le conteneur par l'alias `konstellation-app:4321`.
7. Ajoute la route HTTPS pour `konstellation.uckk.org` au Traefik Konnaxion (ou le domaine modifié dans l’interface) en conservant l'inode du fichier dynamique.
8. Vérifie `/api/health`, `/api/bootstrap` et `/api/capabilities`.
9. Conserve les trois dernières releases et les trois dernières sauvegardes d'état.

## Configuration déjà reprise du Publisher UCKK

- VPS : `2.56.97.41`
- utilisateur SSH : `kx-admin`
- clé : `C:\Users\rejea\.ssh\id_ed25519`
- instance Konnaxion : `konnaxion-prod`
- réseau Traefik : `kx-konnaxion-prod-public`
- racine distante : `/opt/konstellation`

Le domaine est maintenant **préconfiguré sur `konstellation.uckk.org`**. Il reste modifiable dans l’interface avant publication si nécessaire.

## Sources locales préremplies

- Konstellation : `C:\mycode\Konstellation\Konstellation`
- pack Théophile : `C:\mycode\Konstellation\Theophile_Konstellation_SemantiK_TestKit\theophile-konstellation.pack.json`
- Lens : `C:\mycode\Konstellation\Theophile_Konstellation_SemantiK_TestKit\lenses`

## Utilisation

Lancer `Start_Konstellation_Publisher.bat`. Le domaine `konstellation.uckk.org` est déjà rempli; vérifier la configuration puis utiliser les boutons dans l'ordre :

1. **Vérifier Konstellation**
2. **Vérifier le VPS**
3. **Préparer le paquet**
4. **Publier Konstellation**
5. **Vérifier en ligne**

## Docker / Node

Le snapshot fourni exige Node `>=24.15.0`, mais ne contient pas de `package-lock.json`. L'image utilise donc `node:24.15.0-bookworm-slim` et `npm install --omit=dev`, puis `npm run build`. Aucun Node n'est requis directement sur le VPS.

## SemantiK

L'intégration SemantiK est **désactivée par défaut**. Elle peut être activée dans l'interface avec :

- URL : `http://semantik:8766/`
- RuntimeSet : `konstellation-fr-2`
- profil : `konstellation-explorer-2`
- langue : `fr`

Important : les fichiers fournis contiennent le **TestKit Théophile/Konstellation/SemantiK**, mais pas le dépôt exécutable complet de **SemantiK Architect**. Ce Publisher configure Konstellation pour joindre un service SemantiK déjà disponible; il ne tente pas d'inventer ou de reconstruire ce serveur à partir du TestKit.

## Disposition distante

```text
/opt/konstellation/
├── releases/<release-id>/
├── content/<release-id>/
├── current -> releases/<release-id>
├── current-content -> content/<release-id>
├── runtime/
│   ├── .env
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── semantik.json
├── backups/
└── publisher-state.json
```

## Réseau

```text
Internet :443
    |
    v
Traefik Konnaxion
    |
    +-- réseau kx-konnaxion-prod-public
            |
            v
      konstellation-app:4321
            |
            +-- réseau konstellation-internal
```

Le port `4321` est seulement `expose` dans Docker; il n'est jamais publié sur l'interface du VPS.

## Sécurité

- SSH par clé publique.
- Actions privilégiées via `sudo -n`.
- Aucun port Konstellation publié sur l'hôte.
- secret de curseur généré au premier déploiement et conservé dans `/opt/konstellation/runtime/.env` en mode `0600`.
- `semantik.json` distant en mode `0600`.
- sauvegarde de la configuration Traefik avant modification.
- conservation de l'inode du fichier dynamique Traefik, comme dans UCKK Publisher.

## Limite Traefik

Le fichier dynamique appartient au runtime Konnaxion. Si Konnaxion le régénère entièrement, sa route peut disparaître. Relancer **Publier Konstellation** réapplique la route.

## TLS automatique

Après l'installation de la route Traefik, le Publisher vérifie le certificat servi pour le domaine. Si le DNS A pointe déjà vers le VPS mais que Traefik sert encore son certificat auto-signé par défaut, le Publisher redémarre une seule fois le conteneur Traefik Konnaxion et attend jusqu'à 90 secondes le certificat public. Si le DNS n'est pas encore propagé, la publication reste valide et **Vérifier en ligne** pourra être relancé plus tard.
