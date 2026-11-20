KONNAXION — UI TRANSLATION EXTRACTOR
====================================

Contenu du bundle
-----------------
- Konnaxion_I18N_Extractor.pyw   : interface Windows à lancer par double-clic
- extract-ui-translations.mjs    : moteur AST TypeScript/React

Utilisation
-----------
1. Dézipper ce dossier n'importe où.
2. Double-cliquer Konnaxion_I18N_Extractor.pyw.
3. Choisir le dossier frontend de Konnaxion si non détecté automatiquement.
4. Garder "medium" pour la première passe et "Anglais seulement" coché.
5. Cliquer "Vérifier", puis "Lancer l'extraction".
6. Cliquer "Ouvrir les résultats" quand l'extraction est terminée.

Pré-requis
----------
- Python avec Tkinter (le .pyw utilise uniquement la bibliothèque standard).
- Node.js dans PATH.
- Dépendances frontend installées. Le projet doit notamment avoir
  frontend/node_modules/ts-morph/package.json.

Le lanceur copie automatiquement le moteur dans :
  frontend/scripts/extract-ui-translations.mjs

Cela permet à Node de résoudre ts-morph depuis frontend/node_modules.

Résultats par défaut
--------------------
frontend/artifacts/i18n-extraction/

- ui-translation-occurrences.csv
- ui-translation-occurrences.json
- ui-translation-unique.json
- ui-translation-summary.json
- ui-translation-summary.md

Le script ne modifie PAS les fichiers TS/TSX de Konnaxion.
