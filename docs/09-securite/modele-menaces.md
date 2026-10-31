# Modèle de menaces et limites de confiance

## Actifs

Canons des 127 Kristals; identités, déclarations d'état, bases SQLite locales, registres de revue, rapports/proofs, credentials GitHub, exécutable KristalDiag, schémas versionnés, préférences de chemin et commandes.

## Frontières

1. Un Kristal scanné est **une entrée non fiable** pour le lecteur, même créé avec l'IA.
2. Un rapport JSON/CSV importé n'est **pas** une autorisation de modifier canon ou Git.
3. Le moteur KristalDiag embarqué est une dépendance exécutable à version vérifier.
4. Le GUI est un orchestrateur, pas un système d'autorité normative.
5. GitHub est une destination externe, non impliquée dans l'observation locale.

## Menaces et contre-mesures

| Menace | Contrôle exigé |
|---|---|
| Zip-slip et liens symboliques | normalisation path, refus `..`, liens hors racine et chemins absolus |
| Shell injection | `subprocess.run(argv, shell=False)` et args allowlistés |
| Fausse sortie PASS | schéma moteur/target/profile + SHA et fingerprints vérifiés |
| JSON géant / bombe ZIP | limites de bytes, fichiers, profondeur et temps |
| Écriture accidentelle dans `locals` | read-only par défaut, répertoire de sortie externe |
| Secret dans rapport exporté | détection, revue et warning avant export |
| Ré-exécution au refresh | commandes déclenchées seulement par action utilisateur |
| Désynchronisation DB / disque | commit atomique, preuves durables et import idempotent |
| Clé de chemin collision Windows | normalisation prudente, `state_ref` + instance distincts |
| Dépendance remplacée | manifeste/sha, version pin, tests d'intégration |

## Audit

Le scanner ne doit pas exécuter un `README`, un `.py`, un `.cmd` ou un script du workspace pour « analyser son contenu ». Le chemin d'un exécutable externe est configuré par l'opérateur et contrôlé; pour le parcours officiel, seule la version embarquée autorisée est lancée.

## Limites

Une hash ne prouve pas la vérité d'une assertion; elle prouve l'intégrité d'octets par rapport à une référence. Une comparaison de chemins et empreintes de quelques fichiers n'atteste pas le canon entier.
