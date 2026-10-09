"""C2 public-exposure gate (candidate contract, not a Kristal normative format).

This guard must run BEFORE any network write to a public repository. The trust
store is managed outside the working source tree; only Ed25519 public keys are
available to the publisher. Private signing keys belong to independent actors.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

AUTH_FORMAT = "kristal.c2-public-authorization/0.1-candidate"
QUAL_FORMAT = "kristal.c2-prepublic-qualification/0.1-candidate"
TRUST_FORMAT = "kristal.c2-trust/0.1-candidate"
REVOCATION_FORMAT = "kristal.c2-revocations/0.1-candidate"
SHA = re.compile(r"^[a-f0-9]{64}$")
SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

class PublicGateError(ValueError):
    pass


def canonical(obj: Any) -> bytes:
    return json.dumps(obj,sort_keys=True,separators=(",", ":"),ensure_ascii=False,allow_nan=False).encode("utf-8")


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _safe_file(value: Any) -> str:
    path = str(value or "").replace("\\", "/")
    rel = PurePosixPath(path)
    if not path or path.startswith("/") or ":" in path or rel.is_absolute() or any(c in ("", ".", "..") for c in path.split("/")) or path != rel.as_posix():
        raise PublicGateError(f"Unsafe authorized file path: {path!r}")
    return path


def _read(path: Path) -> dict:
    try:
        value=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,ValueError) as exc:
        raise PublicGateError(f"Missing or invalid C2 policy evidence: {path}") from exc
    if not isinstance(value,dict):
        raise PublicGateError(f"Policy evidence must be a JSON object: {path}")
    return value


def _time(raw: Any) -> datetime:
    if not isinstance(raw,str) or not raw.endswith('Z'):
        raise PublicGateError("C2 timestamp must be explicit UTC ending in Z")
    try:
        parsed=datetime.fromisoformat(raw[:-1]+"+00:00")
    except ValueError as exc:
        raise PublicGateError("C2 timestamp malformed") from exc
    return parsed


def _verify_signature(envelope: dict, pub: str) -> dict:
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as exc:
        raise PublicGateError("Public C2 operations require cryptography (pip install cryptography)") from exc
    if set(envelope.keys()) != {"payload", "signature"} or not isinstance(envelope["payload"],dict):
        raise PublicGateError("Expected signed envelope with payload + signature only")
    try:
        key=Ed25519PublicKey.from_public_bytes(base64.b64decode(pub,validate=True))
        signature=base64.b64decode(envelope["signature"],validate=True)
        key.verify(signature, canonical(envelope["payload"]))
    except Exception as exc:
        raise PublicGateError("C2 signature not verified against trusted key") from exc
    return envelope["payload"]


def _strict_fields(obj: Mapping[str,Any], needed: set[str]) -> None:
    if set(obj) != needed:
        raise PublicGateError(f"C2 evidence fields mismatch: missing={sorted(needed-set(obj))}, unexpected={sorted(set(obj)-needed)}")


def candidate_rows(source: Path, files: list[str]) -> list[dict]:
    """Hash the actual octets now, not only declared read-surface hashes."""
    resolved=source.resolve()
    out=[]
    if len(set(files))!=len(files) or not files:
        raise PublicGateError("C2 candidate must include unique non-empty file paths")
    for name in sorted(files):
        rel=_safe_file(name)
        p=(resolved/rel).resolve()
        if not p.is_relative_to(resolved) or not p.is_file() or p.is_symlink():
            raise PublicGateError(f"Missing, symlinked or escaping candidate file: {rel}")
        data=p.read_bytes()
        out.append({"path":rel,"size":len(data),"sha256":sha256(data)})
    return out


def candidate_digest(rows: list[dict]) -> str:
    return sha256(canonical(rows))


def verify_public_write(*, operation: str, slug: str, state_ref: str, repository: str,
                        local_root: Path, paths: list[str], state_commitment: str,
                        policy_dir: Path | None = None) -> dict:
    """Verify independent signed authorization + pre-public qualification.

    Candidate format is non-normative, and cannot replace C1 qualification.
    The trust directory and its admin-managed revocations must remain outside
    both the local authoring tree and collection checkout.
    """
    if operation not in {"sync","publish"}:
        raise PublicGateError("C2 gate only supports sync or publish")
    if not SLUG.fullmatch(slug or "") or not REPO.fullmatch(repository or "") or not state_ref:
        raise PublicGateError("Invalid public destination or Kristal identity")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}",state_commitment or ""):
        raise PublicGateError("Missing or invalid exact State Logical Commitment")
    if policy_dir is None:
        raw=os.environ.get("KRISTAL_C2_POLICY_DIR", "").strip()
        if not raw:
            raise PublicGateError("Public exposure denied: KRISTAL_C2_POLICY_DIR is not configured")
        policy_dir=Path(raw)
    home=Path(policy_dir).expanduser().resolve()
    workspace=Path(local_root).resolve()
    if home==workspace or home.is_relative_to(workspace) or workspace.is_relative_to(home):
        raise PublicGateError("C2 policy store must live outside the local Kristal workspace")
    trust=_read(home/"trust.json")
    _strict_fields(trust,{"format","approver_public_key","qualifier_public_key"})
    if trust["format"] != TRUST_FORMAT:
        raise PublicGateError("Unsupported C2 trust format")
    expected_pin=os.environ.get("KRISTAL_C2_TRUST_PIN", "").strip()
    if not expected_pin or expected_pin != sha256(canonical(trust)):
        raise PublicGateError("C2 trust anchor absent or changed: KRISTAL_C2_TRUST_PIN mismatch")
    auth=_verify_signature(_read(home/"grants"/f"{slug}.json"),trust["approver_public_key"])
    qual=_verify_signature(_read(home/"qualifications"/f"{slug}-{operation}.json"),trust["qualifier_public_key"])
    _strict_fields(auth,{"format","grant_id","slug","state_ref","repository","allowed_paths","expires_at"})
    if auth["format"] != AUTH_FORMAT:
        raise PublicGateError("Unsupported C2 authorization format")
    if any(auth[k] != v for k,v in (("slug",slug),("state_ref",state_ref),("repository",repository))):
        raise PublicGateError("Public authorization identity/destination mismatch")
    if not isinstance(auth["grant_id"],str) or not auth["grant_id"]:
        raise PublicGateError("Invalid C2 grant ID")
    now=datetime.now(timezone.utc)
    if _time(auth["expires_at"])<=now:
        raise PublicGateError("Public authorization expired")
    allowed=auth["allowed_paths"]
    if not isinstance(allowed,list) or not allowed or not all(isinstance(x,str) for x in allowed) or len(set(allowed))!=len(allowed):
        raise PublicGateError("Invalid C2 authorization allowed_paths")
    allowed_paths={_safe_file(x) for x in allowed}
    if set(paths)-allowed_paths:
        raise PublicGateError("Public candidate contains new/unapproved paths: "+", ".join(sorted(set(paths)-allowed_paths)))
    revoked=_read(home/"revocations.json")
    _strict_fields(revoked,{"format","revoked_grant_ids"})
    if revoked["format"] != REVOCATION_FORMAT or not isinstance(revoked["revoked_grant_ids"],list):
        raise PublicGateError("Invalid C2 revocation registry")
    if auth["grant_id"] in revoked["revoked_grant_ids"]:
        raise PublicGateError("Public grant has been revoked")
    _strict_fields(qual,{"format","grant_id","operation","slug","state_ref","repository","state_commitment","candidate_digest","expires_at","result"})
    if qual["format"]!=QUAL_FORMAT or qual["result"] != "PASS":
        raise PublicGateError("Qualification evidence absent, invalid or not PASS")
    bindings={"grant_id":auth["grant_id"],"operation":operation,"slug":slug,"state_ref":state_ref,
              "repository":repository,"state_commitment":state_commitment}
    if any(qual[k]!=v for k,v in bindings.items()):
        raise PublicGateError("Qualification bound to a different grant, operation, identity or revision")
    if _time(qual["expires_at"])<=now:
        raise PublicGateError("Pre-public qualification expired")
    rows=candidate_rows(workspace,paths)
    digest=candidate_digest(rows)
    if qual["candidate_digest"]!=digest:
        raise PublicGateError("Candidate bytes differ from independently qualified revision")
    return {"result":"AUTHORIZED_AND_QUALIFIED","grant_id":auth["grant_id"],"candidate_digest":digest,
            "state_commitment":state_commitment,"paths":len(rows),"repository":repository,
            "authorization_expires_at":auth["expires_at"],"qualification_expires_at":qual["expires_at"]}
