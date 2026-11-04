"""Regression: native canonical contracts are review items, not fake reader failures.

Fixtures are synthetic, stored only in pytest temporary directories. They do not
qualify Framework/diK or authorize publication and never alter a user's Kristals.
"""
from __future__ import annotations

import json
from pathlib import Path

from kristal_manager.global_analysis import analyze_all


def _write(root: Path, rel: str, value: dict) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _fixture(root: Path, *, unknown_selected: bool = False) -> Path:
    workspace = root / "locals" / "Kristal-Native"
    workspace.mkdir(parents=True)
    _write(workspace, "kristal.workspace.json", {
        "format": "kristal.local-workspace/3.2.0",
        "title": "Kristal Native",
        "state_ref": "urn:kristal:native:state",
        "native_model": {"kind": "native_design", "description": "Native design model"},
    })
    _write(workspace, "state/state-snapshot.json", {
        "state_ref": "urn:kristal:native:state",
    })
    selected = [{
        "path": "canon/native.json",
        "logical_contract": {"id": "local.native"},
    }]
    if unknown_selected:
        selected.append({
            "path": "canon/unknown.json",
            "logical_contract": {"id": "local.unknown"},
        })
        _write(workspace, "canon/unknown.json", {"format": "unrecognized/0.1"})
    _write(workspace, "canon/state.index.json", {"canonical_artifacts": selected})
    _write(workspace, "canon/native.json", {
        "native_shape": "native_event_graph",
        "canonical_roles": ["entities", "events"],
        "basis": {"artifact_id": "urn:artifact:native"},
    })
    return workspace


def _run(root: Path):
    source = root / "locals"
    before = {p.relative_to(source): p.read_bytes() for p in source.rglob("*") if p.is_file()}
    outcome = analyze_all(source, catalogue=root / "manager" / "catalog.db",
                          reports_base=root / "manager" / "reports")
    after = {p.relative_to(source): p.read_bytes() for p in source.rglob("*") if p.is_file()}
    assert before == after  # Read-only: no changes to the local Kristal.
    report = outcome["global_report"]
    semantic = next((Path(outcome["report_directory"]) / "semantique" / "kristals").glob("*.json"))
    return report, json.loads(semantic.read_text(encoding="utf-8"))


def test_native_observation_is_review_without_false_technical_warning(tmp_path):
    _fixture(tmp_path)
    global_report, semantic = _run(tmp_path)
    assert global_report["counts"]["native_contract_observed"] == 1
    assert global_report["counts"]["warning"] == 0
    assert global_report["counts"]["review"] == 1
    assert global_report["counts"]["blocker"] == 0
    row = global_report["entries"][0]
    assert row["content_status"] == "native_observed"
    assert row["problems"] == []
    assert row["priority"] == "review"
    assert any("conformité Framework non évalués" in x for x in row["human_review"])
    assert semantic["status"]["qualification"] == "NOT_EVALUATED"
    assert semantic["dik_alignment_observations"]["status"] == "NATIVE_FORMAT_DIK_NOT_EVALUATED"
    assert semantic["issues_to_review"] == []


def test_native_observation_with_unknown_selected_artifact_keeps_warning(tmp_path):
    _fixture(tmp_path, unknown_selected=True)
    global_report, semantic = _run(tmp_path)
    row = global_report["entries"][0]
    assert global_report["counts"]["warning"] == 1
    assert row["priority"] == "warning"
    assert any(issue["code"] == "CONTENT_OR_ALIGNMENT_REVIEW"
               for issue in row["problems"])
    assert any("incomplete" in issue.lower() for issue in semantic["issues_to_review"])
    assert semantic["status"]["qualification"] == "NOT_EVALUATED"
