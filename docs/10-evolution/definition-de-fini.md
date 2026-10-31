# Définition de terminé — refonte et documentation

## Fonctionnel

- [ ] Un utilisateur peut inventorier 127 Kristals, filtrer, ouvrir une fiche, diagnostiquer et retrouver la preuve au même endroit.
- [ ] Les 16 natifs sont expliqués comme tels; le profil V9 n'est pas requis arbitrairement.
- [ ] Un diagnostic est persistant, associé au bon workspace, profil, moteur et version.
- [ ] Après redémarrage, aucun `Not run` erroné; après source modifiée, aucun `PASS` artificiellement actuel.
- [ ] Arketype/PRF/UNESCO distingués entre proposition et décision; tous les anciens avis restent retrouvables.
- [ ] Anciens outils avancés accessibles, sans second chemin de traitement concurrent.

## Technique

- [ ] DB migration reversible; WAL et locks testés Windows.
- [ ] Aucune écriture canonique par les outils de lecture; comparaison de hashes verte.
- [ ] Profils Diag sélectionnés par applicabilité, versions épinglées, preuves vérifiées.
- [ ] Traitement robuste des timeouts, annulations, erreurs et sources changeant pendant run.
- [ ] CI complète sur Windows 3.11+; fixtures v9, v10, v11, natifs et historiques.
- [ ] Tests de sécurité import/ZIP/symlinks/dépendances et de non-publication.
- [ ] Performance instrumentée, pas de promesse sans mesure.

## Documentation

- [ ] Chaque commande publique documentée par un exemple exécuté.
- [ ] Différence OBSERVÉ/LIVRÉ/CIBLE/HYPOTHÈSE conservée.
- [ ] ADRs et plan de migration à jour; glossaire cohérent.
- [ ] Schémas SQL et enveloppes JSON synchronisés avec tests de contrat.
- [ ] Limitations et known issues documentés; code de secours validé.

## Décision de release

Une version peut être livrée en **préversion** même avec des fonctions P2 incomplètes, mais jamais en présentant « tout conforme » si AC-01 à AC-08, AC-11 à AC-14 ou AC-16 échouent. La liste des gates et la preuve doivent accompagner le tag.
