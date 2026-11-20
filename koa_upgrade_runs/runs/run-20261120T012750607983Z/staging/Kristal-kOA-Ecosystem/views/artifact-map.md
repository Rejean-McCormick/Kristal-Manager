# Artifact ownership / flow

| Artifact | Relations |
|---|---|
| DecisionRecord | Konnaxion — owns_artifact<br>governance.decision.execute/1.0.0 — carries_artifact |
| Signal | Orgo — owns_artifact |
| Workflow | Orgo — owns_artifact |
| Case | Orgo — owns_artifact |
| Task | Orgo — owns_artifact |
| IntegrationOperation | Orgo — owns_artifact |
| Corpus Harvest Handoff | EncyKlopedia — produces_artifact<br>Da’at — consumes_artifact<br>encyklopedia.corpus-harvest-handoff/1.0.0 — carries_artifact |
| Kristal State | Kristal — produces_artifact |
| Working Artifact | Kristal — produces_artifact |
| Reference Artifact | Kristal — produces_artifact<br>UCKK / Univers-Cité King Klown — consumes_projection_of<br>kristal.artifact.ready/2.0.0 — carries_artifact<br>uckk.univers-cite-projection/1.0.0 — carries_artifact |
| Runtime Pack | Kristal — produces_artifact<br>kristal_runtime — consumes_artifact |
| Release Set | Koali / kOA-Linux — owns_artifact |
| RuntimeSet | SemantiK Architect — produces_artifact<br>SemantiK Runtime Orchestrator — manages_artifact_lifecycle |
| Space Manifest | Koali Spaces — owns_artifact |
| Activation / rollback receipt | kristal_runtime — produces_artifact |
| Impact / accountability publication | Orgo — produces_artifact<br>accountability.impact.publish/1.0.0 — carries_artifact |
| Identity / trust evidence | Identity & Trust — owns_artifact |
| Policy decision receipt | Governance Policy Runtime — produces_artifact |
| Resource admission receipt | Resource Governor — produces_artifact |
| Audit / disclosure record | Audit Broker — owns_artifact |
| Publication receipt | Publication Gateway — produces_artifact |
| kOA Media Record | kOA Mediatheque — owns_artifact |
| Ariane Atlas Exchange | Ariane — produces_artifact |
| Ariane Runtime Pack | Ariane — produces_artifact |
| GuidanceScript | Ariane — produces_artifact |
| Approval record | Ariane Safety / approvals — produces_artifact |
| Kamel AssemblyRequest | Kamel — produces_artifact |
| Kamel ResolvedComposition | Kamel — produces_artifact |
| Kamel CompiledDeck | Kamel — produces_artifact |
| Kamel BuildManifest | Kamel — produces_artifact |
| UCKK Archive Item | UCKK Archive / Mediatheque — owns_artifact |
| UCKK Assembly Record | UCKK Assembly — owns_artifact |
| UCKK Challenge Result | UCKK Challenge — owns_artifact |
| UCKK Integrity Case | UCKK Integrity — owns_artifact |
