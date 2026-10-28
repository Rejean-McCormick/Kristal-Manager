# Security model

KristalDiag treats the target as untrusted input.

- target code is never imported;
- commands are never guessed;
- target execution is disabled by default;
- explicit commands use argv arrays and `shell=False`;
- output is bounded and redacted before persistence;
- external execution requires `--allow-exec`;
- network/mutation-requiring declared validators are blocked unless corresponding config permissions are enabled;
- symlinks are not followed during bounded scans;
- the complete target tree is fingerprinted before and after a run;
- unauthorized target mutation forces K14 to `ERROR`;
- negative/adversarial checks mutate temporary copies/objects, never the target.

The security hygiene scanner is conservative and is **not** a security audit. It reports possible exposed-secret patterns without copying matched secret values into evidence.
