# Contract map

| Contract | Boundary | Relations |
|---|---|---|
| governance.decision.execute/1.0.0 | Konnaxion → Orgo | Konnaxion — uses_contract → governance.decision.execute/1.0.0<br>governance.decision.execute/1.0.0 — connects_to → Orgo<br>governance.decision.execute/1.0.0 — carries_artifact → DecisionRecord<br>Interaction Kernel — profiles_contract → governance.decision.execute/1.0.0 |
| accountability.impact.publish/1.0.0 | Orgo → Konnaxion | Orgo — uses_contract → accountability.impact.publish/1.0.0<br>accountability.impact.publish/1.0.0 — connects_to → Konnaxion<br>accountability.impact.publish/1.0.0 — carries_artifact → Impact / accountability publication<br>Interaction Kernel — profiles_contract → accountability.impact.publish/1.0.0 |
| encyklopedia.corpus-harvest-handoff/1.0.0 | EncyKlopedia → Da’at | EncyKlopedia — uses_contract → encyklopedia.corpus-harvest-handoff/1.0.0<br>encyklopedia.corpus-harvest-handoff/1.0.0 — connects_to → Da’at<br>encyklopedia.corpus-harvest-handoff/1.0.0 — carries_artifact → Corpus Harvest Handoff |
| kristal.build.request/2.0.0 | Kristal / build boundary | Interaction Kernel — profiles_contract → kristal.build.request/2.0.0 |
| kristal.artifact.ready/2.0.0 | Kristal → consumer projection | Kristal — uses_contract → kristal.artifact.ready/2.0.0<br>kristal.artifact.ready/2.0.0 — connects_to → UCKK / Univers-Cité King Klown<br>kristal.artifact.ready/2.0.0 — carries_artifact → Reference Artifact<br>Interaction Kernel — profiles_contract → kristal.artifact.ready/2.0.0 |
| uckk.univers-cite-projection/1.0.0 | Kristal → UCKK / Univers-Cité | Kristal — uses_contract → uckk.univers-cite-projection/1.0.0<br>uckk.univers-cite-projection/1.0.0 — connects_to → UCKK / Univers-Cité King Klown<br>uckk.univers-cite-projection/1.0.0 — carries_artifact → Reference Artifact |
| Kristal Standard 6.0.0 | Kristal knowledge contract | Kristal — conforms_to → Kristal Standard 6.0.0 |
| Referent Registry 1.0.0 | Kristal referent identity | Kristal — uses_contract → Referent Registry 1.0.0 |
| identity-and-trust.component/1.0.0 | kOA-Linux internal component | Identity & Trust — conforms_to → identity-and-trust.component/1.0.0 |
| governance-policy-runtime.component/1.0.0 | kOA-Linux internal component | Governance Policy Runtime — conforms_to → governance-policy-runtime.component/1.0.0 |
| resource-governor.component/1.0.0 | kOA-Linux internal component | Resource Governor — conforms_to → resource-governor.component/1.0.0 |
| audit-broker.component/1.0.0 | kOA-Linux internal component | Audit Broker — conforms_to → audit-broker.component/1.0.0 |
| publication-gateway.component/1.0.0 | kOA-Linux internal component | Publication Gateway — conforms_to → publication-gateway.component/1.0.0 |
| koa-mediatheque.component/1.0.0 | kOA-Linux internal component | kOA Mediatheque — conforms_to → koa-mediatheque.component/1.0.0 |
| kristal-runtime.component/2.0.0 | kOA-Linux internal component | kristal_runtime — conforms_to → kristal-runtime.component/2.0.0 |
| koa-node-agent.component/1.0.0 | kOA-Linux internal component | kOA Node Agent — conforms_to → koa-node-agent.component/1.0.0 |
| Ariane Spec 0.3.0 | Ariane subsystem | Ariane — conforms_to → Ariane Spec 0.3.0 |
| kamel.contract-set.v3 / 3.3.0 | Kamel source/generated objects | Kamel — conforms_to → kamel.contract-set.v3 / 3.3.0 |
