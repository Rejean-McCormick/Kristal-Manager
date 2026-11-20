# Vue — kOA-Linux : composants internes

| Composant | Autorité / fonction | Capacités |
|---|---|---|
| **Audit Broker** | Custodie bornée des enregistrements d’audit, divulgation sélective, retention et chaîne de garde. | Custodie d’audit / disclosure<br>Impact / accountability |
| **Governance Policy Runtime** | Évalue les politiques locales versionnées et produit décisions/obligations/receipts sans exécuter l’opération gouvernée. | Évaluation de policy / obligations<br>Gating de sécurité des actions |
| **Identity & Trust** | Établit l’identité et les preuves de confiance bornées; authentifie/vérifie sans décider les autorisations métier. | Identity & trust evidence<br>Opération hors-ligne / local-first |
| **Publication Gateway** | Médie les publications entre domaines d’autorité/disclosure, préserve l’autorité source et produit une preuve terminale véridique. | Publication gouvernée inter-domaines<br>Intégration fiable / reconciliation |
| **Resource Governor** | Résout enveloppes, admission, allocation, scheduling, throttling et suspension sans devenir autorité métier. | Admission / allocation de ressources<br>Admission / trust / policy |
| **kOA Assembly** | Résout profils, dépendances, ressources, stockage, services et Release Sets vers des plans de déploiement déterministes. | Résolution déterministe de profils<br>Admission / trust / policy<br>Release channels / Release Sets |
| **kOA Mediatheque** | Autorité privée, locale et hors-ligne pour catalogue média, versions, provenance, droits, renditions et lifecycle local. | Custodie média locale<br>Médiathèque / diffusion<br>Backup / restore / recovery |
