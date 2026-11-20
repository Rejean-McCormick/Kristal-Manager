# Kor — 0.7.0

Kor est l’interface personnelle mobile de l’écosystème kOA : une **projection filtrée, simplifiée et orientée action de Konnaxion et Orgo**, adaptée à l’utilisateur, au World, aux permissions et au contexte.

> **Konnaxion et Orgo portent les environnements et états métier. Kor montre sur téléphone ce qui compte maintenant, sans créer une deuxième architecture métier.**

La navigation principale reste dérivée de la structure propriétaire du World. Les pages d’entrée restent minimales — contexte, annonce courte, une action dominante, quelques statistiques, quelques éléments utiles — tandis que les pages de détail peuvent utiliser le contrat adaptatif `kor.surface/1.2`.

## État exécutable 0.7

Le service accepte `kor.surface/1.0`, `1.1` et `1.2`. Le client Android implémente maintenant :

- navigation stable dérivée de Konnaxion/Orgo, Back hiérarchique, deep links et recherche dans « Plus »;
- classes d’attention A0–A7, slots d’accueil bornés, état vu/masqué/reporté lié à la révision et rail critique cross-World contrôlé par la politique propriétaire;
- fraîcheur/staleness explicite et blocage des actions sensibles lorsque la projection est périmée;
- renderer adaptatif pour `announcement`, `action`, `stats`, `list`, `checklist`, `form`, `capture`, `evidence`, `timeline`, `map`, `compare`, `discussion`, `media`, `relationship` et `status`;
- brouillons chiffrés et capture locale photo/audio/fichier/QR/localisation, digest SHA-256, téléversement, reprise, suppression et références d’artifacts dans les actions propriétaires;
- identité d’appareil Android Keystore, OIDC Authorization Code + PKCE, stockage chiffré et garde biométrique réelle;
- notifications FCM lorsqu’elles sont configurées, avec synchronisation périodique WorkManager comme voie de récupération;
- chrome Android français/anglais; le contenu projeté conserve sa locale, sa révision et sa provenance propriétaires.

Une action Kor ne devient jamais « réussie » parce que l’utilisateur a appuyé sur un bouton. Kor conserve les axes **capture locale → transport → admission → résultat propriétaire**. Le binding de déploiement approuvé reste responsable de construire et valider l’interaction canonique; les publishers Konnaxion/Orgo restent responsables de publier les surfaces autorisées.

## Structure produit

Kor ne possède pas les objets qu’il projette :

- **Konnaxion** reste propriétaire de ses Worlds, contenus et objets;
- **Orgo** reste propriétaire du travail opérationnel canonique;
- **IK** reste canonique pour les interactions transversales lorsqu’il s’applique;
- **Kor** possède la présentation mobile, l’orchestration d’attention, le cache/draft local, l’offline UX, la capture appareil, les notifications et les transports humains.

Korio, QR/caméra, email, relay, disponibilité, credentials et constellation sémantique sont des capacités contextuelles, pas une taxonomie de navigation imposée.

## Démarrage

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.lock
pip install --no-build-isolation --no-deps -e .
kor init-local
. var/local/env.sh
kor serve
```

Documentation : [`docs/00_INDEX.md`](docs/00_INDEX.md). État technique : [`IMPLEMENTATION.fr.md`](IMPLEMENTATION.fr.md). Validation : [`VALIDATION.md`](VALIDATION.md).
