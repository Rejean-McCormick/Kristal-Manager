# Implementation driver

Static artifact qualification is read-only. Executable implementation behavior uses a narrow opt-in bridge: `kristaldiag-driver.json`.

```json
{
  "schema": "kristaldiag.driver.v1",
  "implementation": "My implementation",
  "claimed_profile": "V9-Full",
  "actions": {
    "self_test": {"argv": ["python", "-m", "myimpl", "self-test"]}
  }
}
```

KristalDiag never invokes driver actions unless `--allow-exec` is supplied. Commands are direct argv arrays, `shell=False`, with bounded timeouts.

Allowed v9-oriented action names include `read_v9`, `commit_v9_artifact`, `commit_v9_state`, `validate_v9_derivation`, `validate_v9_materialization`, `publish_v9_state` and `activate_v9_state`. A target need not implement every action; profile qualification only uses executable actions where a check explicitly requests them.

Historical actions and A→B→A interop remain supported.
