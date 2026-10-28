# Security policy

KristalDiag is a diagnostic and qualification harness, not an authority or lifecycle engine.

Do not attach live credentials, private keys, confidential Local Kristals, private publication bundles or private GitHub evidence to public reports.

Target execution is disabled by default. Treat `--allow-exec` as an explicit trust decision. Even then, KristalDiag uses argv arrays (`shell=False`), bounded timeouts and bounded evidence capture.

The target is fingerprinted before and after qualification. Unexpected mutation causes an `ERROR` verdict.

V10 host bindings are inspected conservatively for credential-shaped fields. Bindings may describe hosts and locators but must not carry reusable credentials. Publication verification checks exact bytes and digests; an attestation proves execution facts, not epistemic truth.

KristalDiag does not synchronize Local Kristals, publish releases or activate channels. GitHub synchronization belongs to Kristal Manager; hosted-network provisioning, qualification dispatch, publication and activation belong to Kristal GitHub Setup/Bootstrap.
