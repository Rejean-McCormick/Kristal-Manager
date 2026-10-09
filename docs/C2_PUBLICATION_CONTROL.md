# C2 — Garde d'exposition publique de Kristal Manager

Ce patch expérimental bloque les écritures vers `kristal-public` et toute autre collection de cible `public` sauf si :

1. Le Local Kit a produit une surface `kristal.github-read-surface/1.0` valide et les fichiers n'ont pas changé ;
2. Un grant initial **signé Ed25519** autorise précisément ce Kristal, son `state_ref`, le dépôt cible et **tous** les chemins de la surface de lecture ;
3. Une qualification **distinctement signée** par C1 lie le même `grant_id`, l'opération `sync`, le `state_logical_commitment` et un digest de **tous les octets du candidat** ;
4. Le grant n'est pas révoqué ni expiré et la qualification n'est pas expirée ;
5. Le magasin de politiques est en dehors du Kristal et son `trust.json` correspond au pin `KRISTAL_C2_TRUST_PIN` provenant de la configuration opérateur.

Le contrôle a lieu avant les requêtes au dépôt dans `sync_local_to_github()`, avant le checkout dans `_sync_prepared_collection()` et avant le commit/push final. Les tests avec un dépôt Git local prouvent que les autres comportements Sync restent identiques. Les flux privés ne sont pas modifiés.

**Variables requises pour une synchronisation publique :** `KRISTAL_C2_POLICY_DIR` et `KRISTAL_C2_TRUST_PIN`. Installer `cryptography>=42` pour vérifier les signatures (`py -m pip install cryptography`). Aucun déblocage implicite et aucun contournement `--force` ne sont offerts.

**Format expérimental :** `kristal.c2-public-authorization/0.1-candidate`, `kristal.c2-prepublic-qualification/0.1-candidate`. Pour une opération Manager, le reçu doit avoir `"operation": "sync"`. Les chemins autorisés sont ceux retournés par le Local Kit **relatifs à la racine du Kristal**, et peuvent donc inclure `AI_MANIFEST.json`, `ai/...`, `canon/...` et `state/state-snapshot.json`. Manager produit aussi les métadonnées d'hôte dérivées `.kristal/sync-manifest.json` et `kristals/index.json` ; elles sont implicites au fonctionnement de Sync et doivent être prises en compte lors de la revue de visibilité.

Le programme d'administration des grants se trouve dans l'autre dépôt, `Kristal-GitHub-Bootstrap/tools/c2_policy_admin.py`. **Ne pas laisser les clés de signature dans une collection, le dossier local d'un Kristal ou un dépôt public**. La clé qualifier doit rester sous le contrôle C1, distinct de l'approbateur initial.

**Aucune autorisation spécifique Zoology n'est accordée par ce patch.** Toute commande publique est bloquée par défaut jusqu'à mise en place du grant réel et de la qualification indépendante correspondante. Le contrôle local ne remplace pas les règles de branche GitHub à implémenter avec C3.

**Backups :** le backup de l’intégralité d’un Kristal vers un dépôt **public** est désactivé par précaution. Les chemins non inclus dans la surface qualifiée ne peuvent pas être couverts par un simple balayage heuristique des secrets. Les backups privés restent disponibles.
