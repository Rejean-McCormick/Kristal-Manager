# Agent navigation — Kristal Manager

Ce fichier ajoute des consignes de navigation. Il ne remplace aucun contrat ni preuve propriétaire.

## Avant de modifier quoi que ce soit

1. Lire [`docs/ai/INDEX.md`](docs/ai/INDEX.md) et [`docs/ai/AI_CONTEXT.md`](docs/ai/AI_CONTEXT.md).
2. Identifier le fichier propriétaire de l’autorité, le profil adopté et le périmètre exact.
3. Ne jamais traiter une capture SmartDump comme un état de déploiement ou un commit vérifié.
4. Séparer observation, validation native, qualification indépendante, publication et activation.
5. Préserver sources, preuves, versions et sauvegardes; ne pas promouvoir les nouveaux résultats sans revue explicite.

**Périmètre spécifique :** Manager gère les inventaires et vérifications locales. Le Framework, les propriétaires des Kristals et les qualificateurs indépendants conservent leurs autorités.

**Vérifications pertinentes :**
- `python -m kristal_manager verify "<chemin-local-kristal>"`
- `python -m kristal_manager scan "<racine-des-kristals>"`

Les règles historiques et consignes de portée plus étroite du dépôt priment sur cet index généré.
