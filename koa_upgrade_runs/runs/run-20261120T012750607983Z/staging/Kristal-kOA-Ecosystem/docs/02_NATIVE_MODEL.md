# Native model

The native model is a **typed semantic graph** represented in the canonical `kristal_state/6.0` file. It is compiled from curated editorial catalogs under `knowledge-base/sources/`.

The main domain topology includes relations such as:

```text
Component -> Capability -> Need
Component -> OperatingFunction
Utility -> WorkflowPattern -> Capability
ProblemFamily -> WorkflowPattern
Scenario -> WorkflowPattern
Scenario -> Component
```

Around this graph are contracts, artifacts, lifecycles, invariants, domains, repositories and external references. Assertions carry source/evidence references and can also carry valuations, notes and status.

At normalization time the native validators report **7,929 assertions**, **2,523 relations**, **718 referents** and **117 components**. These counts describe the preserved snapshot; they are not schema limits.

The Local Kit must not flatten this model into a simpler generic structure. The existing v6 canonical file remains the domain-native payload, registered in `canon/state.index.json` by its pre-existing v9 Logical Commitment.
