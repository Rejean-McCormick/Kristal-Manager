# Configuration reference

Default file: `kristaldiag.config.json`. Optional uncommitted override: `kristaldiag.config.local.json`.

```json
{
  "control_dir": ".kristaldiag",
  "max_json_files": 100000,
  "max_target_files": 500000,
  "strict_warnings": false,
  "require_external_interop_for_release": false,
  "execution": {
    "max_parallel": 4,
    "default_timeout_seconds": 120,
    "capture_limit_kb": 256,
    "fail_fast": false,
    "protect_target": true,
    "allow_target_mutation": false,
    "allow_network": false
  },
  "scan": {
    "max_files": 300000,
    "max_file_bytes": 1048576,
    "max_security_files": 4000,
    "large_file_bytes": 10485760
  },
  "toolchain": {"required": [], "optional": []},
  "validators": [],
  "security": {"enabled": true, "additional_patterns": []},
  "redaction": {"enabled": true}
}
```

## Declared validators

N05 never guesses a build/test command. A validator must be declared explicitly:

```json
{
  "validators": [
    {
      "id": "native-tck",
      "name": "Native TCK",
      "required": true,
      "command": ["python", "scripts/run_tck.py"],
      "cwd": ".",
      "timeout_seconds": 300,
      "mutates_target": false,
      "network": false
    }
  ]
}
```

Even declared validators require `--allow-exec`.

## Large GitHub collections

The draft.3.1 defaults are raised so repositories with thousands of `kristals/<slug>/` read surfaces do not fail the read-only fingerprint gate merely because they exceed the earlier 50k-file ceiling. K29 still performs exact byte/digest verification of hosted subtrees with bounded parallel workers. If a collection is materially larger than these limits, increase them explicitly rather than disabling target protection.
