# Sécurité et intégrité

1. Sources autoritaires : `locals/<Kristal>/canon` et métadonnées du Kit.
2. Observations : index SQLite séparé et rapports. Ces données sont dérivées.
3. Aucun appel Git automatique. Le raccourci historique `GitSink.bat` retourne
   toujours un refus (`exit /b 1`).
4. Résultats importés : jamais automatiquement actuels ou certifiés.
5. Contrats natifs sans profil V9 : `NOT_APPLICABLE`, jamais blocage artificiel.
6. Résultats de batch : persistés Kristal par Kristal; annulation coopérative.
7. Erreur SQLite : message visible, ancien registre et dossiers sources intacts.
8. Empreinte V9 : bornée à la liste explicite des fichiers suivis par `diag_bridge`;
   ne prétend pas à une couverture sémantique totale.
9. La base lourd de contenu peut être reconstruite indépendamment du registre.
10. L'installation par overlay doit préserver les registres et rapports privés
    sous `catalogue/` et `rapports/`.
