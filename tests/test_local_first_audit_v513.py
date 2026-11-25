"""Positive and adversarial contract tests for the local-first V5.13 audit."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from kristal_manager.local_first_audit import (
    LocalFirstAuditError, audit_local_first, write_private_report,
)


class LocalFirstAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.local = self.base / "locals"
        self.public = self.base / "public"
        self.local.mkdir()
        self.public.mkdir()
        self.files = {}
        self._json(self.local / "Kristal-Alpha/kristal.workspace.json",
                   {"slug": "alpha", "state_ref": "urn:kristal:alpha:state"})
        self._json(self.local / "Kristal-Alpha/canon/state.index.json", {
            "format": "kristal.authoring-state-index/2.0.0",
            "canonical_artifacts": [{"path": "canon/domain/identity.json"}],
        })
        self._json(self.local / "Kristal-Alpha/canon/domain/identity.json", {"entities": []})
        self._json(self.public / "kristals/index.json", {
            "kristals": [{"slug": "alpha", "path": "kristals/alpha",
                          "state_ref": "urn:kristal:alpha:state"}],
        })
        self._copy("canon/state.index.json")
        self._copy("canon/domain/identity.json")
        self._manifest(["canon/domain/identity.json"])

    @staticmethod
    def _json(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def _copy(self, rel):
        source = self.local / "Kristal-Alpha" / rel
        dest = self.public / "kristals/alpha" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(source.read_bytes())

    def _manifest(self, paths):
        files = []
        for name in paths:
            data = (self.public / "kristals/alpha" / name).read_bytes()
            files.append({"path": name, "sha256": "sha256:" + hashlib.sha256(data).hexdigest()})
        self._json(self.public / "kristals/alpha/.kristal/sync-manifest.json",
                   {"slug": "alpha", "files": files})

    def test_identical_canon_is_observation_only_and_not_publication(self):
        result = audit_local_first(self.local, self.public)
        self.assertEqual(result["status"], "OBSERVATION_ONLY")
        self.assertEqual(result["blocker_count"], 0)
        self.assertEqual(result["counts"]["matching_state_indexes"], 1)
        self.assertEqual(result["counts"]["matching_canonical_artifacts"], 1)
        self.assertFalse(result["policy"]["public_write_authorized"])
        self.assertFalse(result["policy"]["automatic_wikidata_approval"])

    def test_local_only_and_excluded_file_are_not_public_drift(self):
        self._json(self.local / "Kristal-Alpha/canon/domain/excluded.json", {"owner": "local"})
        idx = self.local / "Kristal-Alpha/canon/state.index.json"
        obj = json.loads(idx.read_text(encoding="utf-8"))
        obj["canonical_artifacts"].append({"path": "canon/domain/excluded.json"})
        self._json(idx, obj)
        self._copy("canon/state.index.json")
        self._json(self.local / "Kristal-Beta/kristal.workspace.json",
                   {"slug": "beta", "state_ref": "urn:kristal:beta:state"})
        self._json(self.local / "Kristal-Beta/canon/state.index.json",
                   {"canonical_artifacts": []})
        report = audit_local_first(self.local, self.public)
        self.assertEqual(report["status"], "OBSERVATION_ONLY")
        self.assertEqual(report["counts"]["excluded_canonical_artifacts"], 1)
        self.assertEqual(report["counts"]["local_only_workspaces"], 1)

    def test_duplicate_local_slug_is_reported_with_both_claimants_and_blocks(self):
        self._json(self.local / "Kristal-Alpha-Backup/kristal.workspace.json",
                   {"slug": "alpha", "state_ref": "urn:kristal:alpha:state"})
        self._json(self.local / "Kristal-Alpha-Backup/canon/state.index.json",
                   {"canonical_artifacts": [{"path": "canon/domain/identity.json"}]})
        result = audit_local_first(self.local, self.public)
        self.assertEqual(result["status"], "BLOCKED_INTEGRITY")
        self.assertEqual(result["counts"]["duplicate_local_slug_groups"], 1)
        self.assertEqual(result["counts"]["ambiguous_local_workspace_directories_skipped"], 2)
        self.assertEqual(result["counts"].get("matching_state_indexes", 0), 0)
        issue = next(x for x in result["collection_findings"] if x["kind"] == "DUPLICATE_LOCAL_SLUG")
        self.assertEqual(issue["slug"], "alpha")
        self.assertEqual([x["local_directory"] for x in issue["claimants"]],
                         ["Kristal-Alpha", "Kristal-Alpha-Backup"])
        self.assertEqual(issue["required_action"], "OWNER_REVIEW_NO_AUTOMATIC_CANON_SELECTION")
        self.assertFalse(result["policy"]["public_write_authorized"])

    def test_identical_duplicate_indexes_still_cannot_auto_select(self):
        self._json(self.local / "Kristal-Alpha-Backup/kristal.workspace.json",
                   {"slug": "alpha", "state_ref": "urn:kristal:alpha:state"})
        source = self.local / "Kristal-Alpha/canon/state.index.json"
        dest = self.local / "Kristal-Alpha-Backup/canon/state.index.json"
        dest.parent.mkdir(parents=True)
        dest.write_bytes(source.read_bytes())
        issue = audit_local_first(self.local, self.public)["collection_findings"][0]
        self.assertTrue(all(x["matches_public_state_index"] for x in issue["claimants"]))
        self.assertEqual(issue["required_action"], "OWNER_REVIEW_NO_AUTOMATIC_CANON_SELECTION")

    def test_drift_and_manifest_conflicts_block(self):
        self._json(self.public / "kristals/alpha/canon/domain/identity.json", {"entities": ["x"]})
        report = audit_local_first(self.local, self.public)
        self.assertEqual(report["status"], "BLOCKED_INTEGRITY")
        self.assertEqual(report["counts"]["drifted_canonical_artifacts"], 1)
        self.assertEqual(report["counts"]["manifest_hash_conflicts"], 1)

    def test_recorded_wikidata_acceptance_is_not_qualification(self):
        crosswalk = "canon/domain/v11/updates/r1/external-crosswalk.json"
        self._json(self.local / "Kristal-Alpha" / crosswalk, {
            "mappings": [{"external_ref": {"system": "wikidata", "id": "Q42"},
                          "local_ref": {"namespace_id": "kristal:alpha", "id": "KQ1001"},
                          "relation": "exactMatch", "status": "accepted",
                          "review": {"method": "audited_rule", "evidence_refs": ["KS1002"]}}],
        })
        idx = self.local / "Kristal-Alpha/canon/state.index.json"
        value = json.loads(idx.read_text(encoding="utf-8"))
        value["canonical_artifacts"].append({"path": crosswalk})
        self._json(idx, value)
        self._copy("canon/state.index.json")
        report = audit_local_first(self.local, self.public)
        self.assertEqual(report["counts"]["recorded_accepted_by_automated_audited_rule"], 1)
        self.assertEqual(report["counts"]["exact_match_recorded_accepted_occurrences"], 1)
        self.assertFalse(report["policy"]["qualification_C1_C2_granted"])

    def test_manifest_claim_for_missing_public_blocks(self):
        (self.public / "kristals/alpha/canon/domain/identity.json").unlink()
        report = audit_local_first(self.local, self.public)
        self.assertEqual(report["counts"]["manifest_claims_missing_public"], 1)
        self.assertGreater(report["blocker_count"], 0)

    def test_unsafe_canonical_path_fails_closed(self):
        self._json(self.local / "Kristal-Alpha/canon/state.index.json", {
            "canonical_artifacts": [{"path": "../other/secret"}],
        })
        with self.assertRaisesRegex(LocalFirstAuditError, "Unsafe relative path"):
            audit_local_first(self.local, self.public)

    def test_symlink_in_observed_path_fails_closed(self):
        (self.local / "Kristal-Alpha/canon/domain/identity.json").unlink()
        (self.local / "Kristal-Alpha/canon/domain/identity.json").symlink_to(
            self.base / "does-not-exist")
        with self.assertRaisesRegex(LocalFirstAuditError, "Symlink"):
            audit_local_first(self.local, self.public)

    def test_report_outside_trees_new_only(self):
        result = audit_local_first(self.local, self.public)
        output = self.base / "private.json"
        write_private_report(result, output, self.local, self.public)
        self.assertEqual(json.loads(output.read_text())["status"], "OBSERVATION_ONLY")
        with self.assertRaisesRegex(LocalFirstAuditError, "overwrite"):
            write_private_report(result, output, self.local, self.public)
        with self.assertRaisesRegex(LocalFirstAuditError, "outside"):
            write_private_report(result, self.local / "write.json", self.local, self.public)

    def test_report_refuses_dangling_symlink_target_and_hidden_parent(self):
        result = audit_local_first(self.local, self.public)
        symlink = self.base / "misleading.json"
        symlink.symlink_to(self.local / "unknown.json")
        with self.assertRaisesRegex(LocalFirstAuditError, "overwrite"):
            write_private_report(result, symlink, self.local, self.public)
        redirected = self.base / "redirect"
        redirected.symlink_to(self.local, target_is_directory=True)
        with self.assertRaisesRegex(LocalFirstAuditError, "symlink|outside"):
            write_private_report(result, redirected / "private.json", self.local, self.public)

    def test_zip_snapshots_work_without_extraction(self):
        def pack(source: Path, target: Path):
            with zipfile.ZipFile(target, "w") as z:
                for file in source.rglob("*"):
                    if file.is_file():
                        z.write(file, file.relative_to(source).as_posix())
        local_zip, public_zip = self.base / "locals.zip", self.base / "public.zip"
        pack(self.local, local_zip)
        pack(self.public, public_zip)
        report = audit_local_first(local_zip, public_zip)
        self.assertEqual(report["counts"]["matching_canonical_artifacts"], 1)

    def test_ambiguous_canonical_zip_member_blocks(self):
        local_zip = self.base / "bad.zip"
        with zipfile.ZipFile(local_zip, "w") as z:
            z.writestr("Kristal-Alpha/kristal.workspace.json", "{}")
            z.writestr("Kristal-Alpha/kristal.workspace.json", "{}")
        with self.assertRaisesRegex(LocalFirstAuditError, "Ambiguous duplicate"):
            audit_local_first(local_zip, self.public)


if __name__ == "__main__":
    unittest.main()
