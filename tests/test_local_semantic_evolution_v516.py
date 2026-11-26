"""Operational local-first semantic projection, with no canonical overwrite."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kristal_manager.local_first_audit import LocalFirstAuditError
from kristal_manager.local_semantic_evolution_v516 import evolve, lookup


class LocalEvolutionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.locals = self.base / "locals"
        self.private = self.base / "private"
        self.locals.mkdir()
        self.private.mkdir()
        fake = patch("kristal_manager.semantic_federation_inventory._inside_git_checkout", return_value=False)
        fake.start()
        self.addCleanup(fake.stop)
        self.root = self.locals / "Kristal-Alpha"
        self.root.mkdir()
        self.write("kristal.workspace.json", {"slug": "alpha", "state_ref": "urn:kristal:alpha:state"})
        self.paths = []

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        data = content if isinstance(content, bytes) else (json.dumps(content, ensure_ascii=False) + "\n").encode("utf8")
        target.write_bytes(data)
        return sha256(data).hexdigest()

    def revision(self, revision, qid, *, status="candidate", priority=100, label="Étoile"):
        base = "canon/domain/v11/updates/" + revision
        registry = base + "/identity-registry.json"
        graph = base + "/semantic-graph.json"
        crosswalk = base + "/external-crosswalk.json"
        catalog = base + "/dictionaries/catalog.json"
        layer = base + "/dictionaries/fr.json"
        self.write(registry, {"schema_version": "11.0", "artifact_type": "kristal_identity_registry",
                              "namespace_id": "kristal:alpha", "identities": [
                                  {"id": "KQ1001", "kind": "entity", "status": "stable"},
                                  {"id": "KS1001", "kind": "source", "status": "stable"}]})
        self.write(graph, {"schema_version": "11.0", "artifact_type": "kristal_semantic_graph",
                           "namespace_id": "kristal:alpha", "graph_id": revision,
                           "entities": ["KQ1001"], "properties": [], "assertions": [], "sources": ["KS1001"]})
        self.write(crosswalk, {"schema_version": "11.0", "artifact_type": "kristal_external_crosswalk",
                               "namespace_id": "kristal:alpha", "mappings": [{
                                   "mapping_id": "map-" + revision, "local_ref": {"namespace_id": "kristal:alpha", "id": "KQ1001"},
                                   "external_ref": {"system": "wikidata", "id": qid}, "relation": "exactMatch",
                                   "status": status, "review": {"method": "audited_rule", "decision_id": "d-" + revision,
                                                                 "evidence_refs": ["KS1001"]}}]})
        layer_hash = self.write(layer, {"schema_version": "11.0", "artifact_type": "kristal_curated_dictionary",
                                        "namespace_id": "kristal:alpha", "language": "fr", "entries": [{
                                            "semantic_id": "KQ1001", "preferred_term": label,
                                            "review": {"reviewer": "test", "decision_id": "test", "reason": "demo"}}]})
        self.write(catalog, {"schema_version": "11.0", "artifact_type": "kristal_dictionary_catalog",
                             "namespace_id": "kristal:alpha", "catalog_id": "catalog-" + revision,
                             "languages": [{"tag": "fr", "fallbacks": [], "layers": [{
                                 "kind": "curated", "path": "fr.json", "layer_id": revision,
                                 "priority": priority, "sha256": layer_hash}]}]})
        self.paths.extend([registry, graph, crosswalk, catalog])
        return {"format": "kristal.authoring-v11-profile/1.0",
                "semantic_profile": "kristal.semantic-identity/11.0",
                "registry": registry, "graph": graph, "crosswalk": crosswalk, "catalog": catalog}

    def finish(self, profile):
        self.write("canon/state.index.json", {"canonical_artifacts": [{"path": p} for p in self.paths]})
        self.write(".kristal/v11/authoring.json", profile)

    def test_selected_profile_drives_real_local_projection_and_preserves_history(self):
        historical = self.revision("r1", "Q42", status="accepted", label="Ancien sens")
        active = self.revision("r2", "Q99", status="candidate", label="Sens actif")
        self.finish(active)
        source_before = {p: sha256((self.root / p).read_bytes()).hexdigest() for p in self.paths}
        result = evolve(self.locals, self.private, apply=True)
        self.assertEqual(result["status"], "LOCAL_DERIVED_UPDATED")
        self.assertEqual(result["counts"]["with_active_v11_profile"], 1)
        hits = lookup(self.locals, "KQ1001", namespace="kristal:alpha")["results"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["labels"]["fr"]["preferred"], "Sens actif")
        self.assertIsNone(hits[0]["wikidata"]["accepted_exact"])
        self.assertEqual(hits[0]["wikidata"]["candidate_exact"], ["Q99"])
        self.assertEqual(lookup(self.locals, "Q42")["results"], [])
        self.assertEqual(source_before, {p: sha256((self.root / p).read_bytes()).hexdigest() for p in self.paths})
        self.assertEqual(evolve(self.locals, self.private, apply=True)["pointers_updated"], 0)

    def test_source_recorded_accepted_remains_source_recorded(self):
        active = self.revision("r1", "Q42", status="accepted")
        self.finish(active)
        evolve(self.locals, self.private, apply=True)
        record = lookup(self.locals, "ÉTOILE")["results"][0]
        self.assertEqual(record["wikidata"]["accepted_exact"], "Q42")
        self.assertEqual(record["kind"], "entity")
        pointer = json.loads((self.root / "derived/semantic/active-resolution.json").read_text())
        projection = json.loads((self.root / pointer["projection"]).read_text())
        self.assertIn("not independently qualified", projection["recorded_status_semantics"]["accepted_exact"])

    def test_unmanaged_pointer_blocks_all_local_writes(self):
        active = self.revision("r1", "Q42")
        self.finish(active)
        self.write("derived/semantic/active-resolution.json", {"somebody_else": True})
        with self.assertRaisesRegex(LocalFirstAuditError, "unmanaged active-resolution"):
            evolve(self.locals, self.private, apply=True)
        self.assertFalse((self.root / "derived/semantic/v516").exists())

    def test_corrupted_catalog_digest_prevents_any_local_change(self):
        active = self.revision("r1", "Q42")
        self.finish(active)
        with (self.root / "canon/domain/v11/updates/r1/dictionaries/fr.json").open("ab") as stream:
            stream.write(b" ")
        with self.assertRaisesRegex(LocalFirstAuditError, "source inventory failed integrity"):
            evolve(self.locals, self.private, apply=True)
        self.assertFalse((self.root / "derived/semantic").exists())

    def test_unregistered_authoring_role_refused(self):
        active = self.revision("r1", "Q42")
        active["graph"] = "canon/domain/v11/updates/r99/semantic-graph.json"
        self.finish(active)
        with self.assertRaisesRegex(LocalFirstAuditError, "not uniquely registered"):
            evolve(self.locals, self.private, apply=True)


if __name__ == "__main__":
    unittest.main()
