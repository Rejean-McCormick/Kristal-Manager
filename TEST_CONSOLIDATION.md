# Validation — Kristal Manager consolidé (2026-10-27)

## Contrôles réellement exécutés

- Fusion des fonctions d'icônes Windows (lecture seule), du générateur de 2.5.0, de la fenêtre Diagnostic guidée et du moteur KristalDiag officiel embarqué.
- Test ciblé des fonctions icônes, pont KristalDiag, overlay, thème, journal, catégories, organisation et état historique : **29 réussis** (sur l'étape préalable à l'ajout de tests intégrés).
- Suite complète (sur l'état consolidé avant ajout des trois tests de non-régression consolidés) : **161 réussis, 14 en échec**. Les 14 échecs proviennent du test historique `tests/test_core.py` qui attend des fonctions GitHub/publication/migration désactivées par conception. Aucun échec nouveau dans les tests de cette fusion.
- Tests ajoutés spécifiquement pour l'association icônes + overlay + archives anciennes : **3 réussis**.
- KristalDiag officiel embarqué exécuté sur une copie extraite de l'archive `Kristal-Architecture.zip` : **`EXECUTED_EXIT_0`, `PASS`, 14 contrôles PASS**, aucune modification détectée dans les fichiers d'état suivis, **0 anomalie détaillée**.

## Limites

- Le profil du test réel est `V9-State-Reader`, et le moteur suit la baseline Framework v10 ; ce résultat ne prouve pas une conformité Framework V11 ou une attestation C1.
- La comparaison des sources avant/après couvre les fichiers d'état connus seulement.
- Tous les tests GUI ont été exécutés sur Linux avec Xvfb, pas sur le shell Windows natif ; l'affichage `.ico` en barre de tâches et le fonctionnement du générateur Node.js dans Windows restent à confirmer.
- L'installation de `jsonschema` sur Windows peut être nécessaire ; l'interface demande explicitement l'autorisation avant de lancer pip.
