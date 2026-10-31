# Principes produit et décisions d'interface

Ces principes reprennent les guides UX fournis, en les adaptant au travail sur les Kristals.

1. **Un objet métier d'abord** : l'utilisateur explore un Kristal, pas « l'onglet scanner X ».
2. **Un endroit par intention** : analyser/diagnostiquer depuis le même contexte, avec les bons sous-profils et sorties.
3. **Des statuts vérifiables** : la page doit expliquer la portée, la date, le profil et la preuve d'un badge.
4. **Une seule liste maître** : sélection, filtres et tri conservés quand on ouvre une fiche puis qu'on revient.
5. **Complexité progressive** : « aperçu », puis détails, puis expertise; pas une douzaine de panneaux au premier niveau.
6. **Actions près du résultat** : relancer un diag sur sa fiche, exporter ses preuves depuis l'historique.
7. **Pas de faux tableau de bord** : l'accueil sert à reprendre et prioriser, pas à recopier toutes les colonnes.
8. **Séparer observer et modifier** : l'approbation d'un PRF ne s'effectue pas implicitement lors d'un scan.
9. **Résilience UX** : une base temporairement indisponible montre `état inconnu` et une action de récupération; jamais `PASS` par défaut.
10. **Conservation fonctionnelle** : outils Git, import Kristalizer, classification et comparaison restent accessibles dans Avancé si pertinents, sans concurrencer le parcours principal.

## Anti-patterns à interdire

Créer une page « Nouveau Manager » sans retirer les anciennes actions doublées; confondre un panneau de rapports avec l'historique central; plusieurs boutons nommés « Valider » qui font des choses différentes; mettre `Not run` si le résultat est présent en base; montrer un `PASS` périmé comme actuel; afficher `UNMAPPED` pour une proposition valide qui n'est simplement pas encore approuvée.

## Tests UX représentatifs

« Après un scan de 127, je sais quel sous-ensemble nécessite action »; « après diagnostic puis redémarrage, je retrouve son historique »; « je vois pourquoi un profil est non applicable »; « je peux examiner une proposition UNESCO sans l'adopter ». Voir [scénarios](../06-experience/parcours-utilisateur.md).
