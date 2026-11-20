# Invariants techniques

| Invariant | Porté par |
|---|---|
| **Immutabilité des références publiées** — Un artefact reconnu/versionné n’est pas corrigé par mutation cachée; une correction produit une nouvelle version ou un nouveau cycle. | Mémoire canonique<br>Kristal<br>UCKK Archive / Mediatheque |
| **Validation avant promotion** — Une proposition, build ou transition ne devient pas canon/active si les gates requis échouent. | Gouvernance & limites<br>Koali / kOA-Linux<br>Kristal<br>Ariane<br>Kamel |
| **Préservation de l’ambiguïté** — L’incertitude et les alternatives sont représentées explicitement plutôt que forcées silencieusement. | Synthèse & réconciliation<br>SenTient<br>Kristal |
| **Articulation sans nouveaux faits** — Les couches de rendu/guidance ne doivent pas introduire comme faits des éléments absents de leurs sources autorisées. | Articulation & interface<br>SemantiK Architect<br>Kamel<br>Ariane Assist Client |
| **Vérification fail-closed** — Une intégrité, autorisation, état ou risque indéterminé ne devient pas une permission implicite. | Gouvernance & limites<br>Koali / kOA-Linux<br>Ariane Safety / approvals<br>Governance Policy Runtime<br>Publication Gateway |
| **Feedback gouverné et non mutant** — Le feedback ouvre un travail/cycle traçable; il ne réécrit pas directement l’état canonique ou l’autorité source. | Impact & apprentissage<br>Orgo<br>Konnaxion<br>UCKK Integrity |
| **Traçabilité bout-en-bout** — Les transitions significatives conservent la chaîne source → règle/décision → action → résultat → preuve. | kOA Digital Ecosystem<br>Interaction Kernel<br>Audit Broker<br>Kamel<br>Ariane |
