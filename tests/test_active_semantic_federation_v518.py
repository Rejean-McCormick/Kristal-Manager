"""Focused V5.18 tests: active identity authority, suggestions and read-only public."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from kristal_manager.local_first_audit import LocalFirstAuditError
from kristal_manager.local_semantic_evolution_v516 import evolve
from kristal_manager.active_semantic_federation_v518 import build_active_federation, lookup


class ActiveFederationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.locals = self.base / "locals"
        self.private = self.base / "private"
        self.locals.mkdir()
        self.private.mkdir()
        fake = patch("kristal_manager.semantic_federation_inventory._inside_git_checkout", return_value=False)
        fake.start()
        self.addCleanup(fake.stop)

    def write(self, root, rel, data):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = (json.dumps(data, ensure_ascii=False) + "\n").encode("utf8")
        path.write_bytes(payload)
        return sha256(payload).hexdigest()

    def owner(self, slug, namespace, *, active=True, label="Étoile", qid="Q42", historical=None,
              mapping_status="accepted"):
        root = self.locals / ("Kristal-" + slug.capitalize())
        root.mkdir()
        self.write(root, "kristal.workspace.json", {"slug": slug, "state_ref": f"urn:kristal:{slug}:state"})
        all_paths = []
        def revision(name, term, qid_value):
            base = "canon/domain/v11/updates/" + name
            registry = base + "/identity-registry.json"
            graph = base + "/semantic-graph.json"
            crosswalk = base + "/external-crosswalk.json"
            catalog = base + "/dictionaries/catalog.json"
            layer = base + "/dictionaries/fr.json"
            self.write(root, registry, {"schema_version": "11.0", "artifact_type": "kristal_identity_registry",
                       "namespace_id": namespace, "identities": [{"id": "KQ1001", "kind": "entity", "status": "stable"},
                                                                  {"id": "KS1001", "kind": "source", "status": "stable"}]})
            self.write(root, graph, {"schema_version": "11.0", "artifact_type": "kristal_semantic_graph",
                       "namespace_id": namespace, "graph_id": name, "entities": ["KQ1001"],
                       "properties": [], "assertions": [], "sources": ["KS1001"]})
            self.write(root, crosswalk, {"schema_version": "11.0", "artifact_type": "kristal_external_crosswalk",
                       "namespace_id": namespace, "mappings": [{"mapping_id": name + "-q",
                           "local_ref": {"namespace_id": namespace, "id": "KQ1001"},
                           "external_ref": {"system": "wikidata", "id": qid_value},
                           "relation": "exactMatch", "status": mapping_status, "review": {
                               "method": "audited_rule", "decision_id": name,
                               "evidence_refs": ["KS1001"]}}]})
            layers = []
            if term is not None:
                digest = self.write(root, layer, {"schema_version": "11.0", "artifact_type": "kristal_curated_dictionary",
                                    "namespace_id": namespace, "language": "fr", "entries": [{
                                        "semantic_id": "KQ1001", "preferred_term": term,
                                        "review": {"reviewer": "test", "decision_id": name, "reason": "fixture"}}]})
                layers.append({"kind": "curated", "path": "fr.json", "layer_id": name,
                               "priority": 90, "sha256": digest})
            self.write(root, catalog, {"schema_version": "11.0", "artifact_type": "kristal_dictionary_catalog",
                       "namespace_id": namespace, "catalog_id": name,
                       "languages": [{"tag": "fr", "fallbacks": [], "layers": layers}]})
            all_paths.extend([registry, graph, crosswalk, catalog])
            return {"format": "kristal.authoring-v11-profile/1.0",
                    "semantic_profile": "kristal.semantic-identity/11.0",
                    "registry": registry, "graph": graph, "crosswalk": crosswalk, "catalog": catalog}
        if historical is not None:
            revision("old", historical, "Q90")
        chosen = revision("current", label, qid)
        self.write(root, "canon/state.index.json", {"canonical_artifacts": [{"path": p} for p in all_paths]})
        if active:
            self.write(root, ".kristal/v11/authoring.json", chosen)
        return root

    def source(self):
        return evolve(self.locals, self.private, apply=True)["source_db"]

    def test_same_short_id_in_two_namespaces_and_exact_lookup(self):
        self.owner("alpha", "kristal:alpha", label="Étoile")
        self.owner("beta", "kristal:beta", label="Star", qid="Q99")
        report = build_active_federation(self.locals, self.private, Path(self.source()))
        self.assertEqual(report["status"], "ACTIVE_DERIVED_FEDERATION_BUILT")
        self.assertEqual(report["counts"]["active_v11_profiles"], 2)
        self.assertEqual(len(lookup(Path(report["database"]), "KQ1001")["results"]), 2)
        self.assertEqual(lookup(Path(report["database"]), "éTOILE")["results"][0]["owner_slug"], "alpha")
        self.assertEqual(lookup(Path(report["database"]), "Q42")["results"][0]["namespace_id"], "kristal:alpha")
        self.assertFalse(json.loads(Path(report["public_plan"]).read_text())["qualifies_or_publishes"])

    def test_historical_label_consensus_is_review_hint_only(self):
        self.owner("alpha", "kristal:alpha", label=None, historical="Soleil")
        report = build_active_federation(self.locals, self.private, Path(self.source()))
        self.assertEqual(report["counts"]["historical_unreviewed_lexical_hints"], 1)
        found = lookup(Path(report["database"]), "KQ1001")["results"][0]
        self.assertEqual(found["labels"], {})
        self.assertEqual(found["historical_unreviewed_hints"]["fr"], "Soleil")
        conn = sqlite3.connect(report["database"])
        try:
            self.assertEqual(conn.execute("SELECT status FROM historical_lexical_hint").fetchone()[0],
                             "UNREVIEWED_NOT_CANONICAL")
        finally:
            conn.close()

    def test_candidate_qid_lookup_never_becomes_accepted(self):
        self.owner("alpha", "kristal:alpha", label="Terme", qid="Q8123",
                   mapping_status="candidate")
        report = build_active_federation(self.locals, self.private, Path(self.source()))
        hits = lookup(Path(report["database"]), "Q8123")["results"]
        self.assertEqual(len(hits), 1)
        self.assertIsNone(hits[0]["wikidata_recorded_accepted"])
        self.assertEqual(hits[0]["wikidata_candidates"], ["Q8123"])

    def test_unselected_workspace_is_not_automatically_promoted(self):
        self.owner("alpha", "kristal:alpha", active=False)
        report = build_active_federation(self.locals, self.private, Path(self.source()))
        self.assertEqual(report["counts"]["without_active_v11_profile"], 1)
        self.assertEqual(lookup(Path(report["database"]), "KQ1001")["results"], [])

    def test_tampered_pointer_fails_closed_before_private_index(self):
        root = self.owner("alpha", "kristal:alpha")
        source = self.source()
        pointer = root / "derived/semantic/active-resolution.json"
        data = json.loads(pointer.read_text())
        data["projection_sha256"] = "0" * 64
        pointer.write_text(json.dumps(data), encoding="utf8")
        with self.assertRaisesRegex(LocalFirstAuditError, "SHA mismatch"):
            build_active_federation(self.locals, self.private, Path(source))
        self.assertFalse(list(self.private.glob("SEMANTIC_V518_*.sqlite")))

    def test_public_preview_is_non_mutating_and_pending_review(self):
        self.owner("alpha", "kristal:alpha")
        source = self.source()
        observed = {"status": "BLOCKED_INTEGRITY", "blocker_count": 1,
                    "counts": {"drifted_state_indexes": 1, "duplicate_local_slug_groups": 0},
                    "workspaces": [{"slug": "alpha", "hosted": True,
                                    "findings": [{"kind": "STATE_INDEX_BYTES_DRIFT"},
                                                 {"kind": "EXCLUDED_FROM_PUBLIC_READ_SURFACE",
                                                  "path": "canon/domain/v11/updates/accepted-precedence-v517-a/external-crosswalk.json"}]}]}
        with patch("kristal_manager.active_semantic_federation_v518.audit_local_first", return_value=observed):
            report = build_active_federation(self.locals, self.private, Path(source), public_root=self.base / "public")
        preview = json.loads(Path(report["public_plan"]).read_text())
        self.assertEqual(preview["status"], "NO_PUBLIC_WRITE_AUTHORIZED")
        self.assertEqual(len(preview["workspaces_to_review"]), 1)
        self.assertEqual(len(preview["workspaces_to_review"][0]["new_local_canonical_revisions_unpublished"]), 1)


if __name__ == "__main__":
    unittest.main()
