"""V5.14 candidate index: positive and fail-closed negative tests."""
from __future__ import annotations

from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from kristal_manager.local_first_audit import LocalFirstAuditError
from kristal_manager.semantic_federation_inventory import build_semantic_inventory,query_semantic_inventory


class SemanticFederationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # This test executor puts its temporary directory inside its own Git
        # worktree. Mock only that environmental guard; test all source guards.
        patcher = patch('kristal_manager.semantic_federation_inventory._inside_git_checkout',return_value=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.base = Path(self.tmp.name)
        self.locals = self.base / "locals"
        self.locals.mkdir()
        self.counter = 0

    def write(self, workspace: str, rel: str, data):
        path = self.locals / workspace / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = data if isinstance(data,bytes) else (json.dumps(data,ensure_ascii=False) + "\n").encode()
        path.write_bytes(payload)
        return sha256(payload).hexdigest()

    def owner(self, name="Kristal-Alpha", slug="alpha", namespace="kristal:alpha", revision="canon/domain/v11/updates/r1", aliases=False, kind="complete", identifier="KQ1001", term="Étoile", status="candidate", jsonl=False):
        self.write(name,"kristal.workspace.json",{"slug":slug,"state_ref":f"urn:kristal:{slug}:state"})
        roots = []
        def add(rel,obj):
            self.write(name,rel,obj)
            roots.append({"path":rel})
        if kind == "complete":
            add(f"{revision}/{'registry.json' if aliases else 'identity-registry.json'}",
                {"artifact_type":"kristal_identity_registry","namespace_id":namespace,
                 "identities":[{"id":identifier,"kind":"entity","status":"stable"}]})
            add(f"{revision}/{'graph.json' if aliases else 'semantic-graph.json'}",
                {"artifact_type":"kristal_semantic_graph","namespace_id":namespace,
                 "entities":[identifier],"properties":[],"assertions":[],"sources":[]})
            add(f"{revision}/{'crosswalk.json' if aliases else 'external-crosswalk.json'}",
                {"artifact_type":"kristal_external_crosswalk",
                 "mappings":[{"local_ref":{"id":identifier,"namespace_id":namespace},
                              "external_ref":{"system":"wikidata","id":"Q42"},
                              "relation":"exactMatch","status":status,
                              "review":{"method":"audited_rule","evidence_refs":["KS1"]}}]})
        layer = {"artifact_type":"kristal_curated_dictionary","namespace_id":namespace,
                 "language":"fr","entries":[{"semantic_id":identifier,"preferred_term":term,
                                               "review":{"reviewer":"not-certified"}}]}
        if jsonl:
            layer_file="terms-fr.jsonl"
            layer_hash=self.write(name,f"{revision}/dictionaries/{layer_file}",
                  (json.dumps({"namespace_id":namespace,"language":"fr","semantic_id":identifier,
                               "preferred_term":term},ensure_ascii=False)+"\n").encode())
        else:
            layer_file="terms-fr.json"
            layer_hash=self.write(name,f"{revision}/dictionaries/{layer_file}",layer)
        add(f"{revision}/dictionaries/catalog.json",
            {"artifact_type":"kristal_dictionary_catalog","namespace_id":namespace,
             "languages":[{"tag":"fr","layers":[{"layer_id":"fr","path":layer_file,
                                                       "sha256":layer_hash,"priority":100}]}]})
        self.write(name,"canon/state.index.json",{"canonical_artifacts":roots})

    def build(self, name="index.sqlite"):
        return build_semantic_inventory(self.locals,self.base / name)

    def test_two_namespaces_can_reuse_kq_and_query_retains_provenance(self):
        self.owner()
        self.owner("Kristal-Beta","beta","kristal:beta",identifier="KQ1001",term="étoile")
        result=self.build()
        self.assertEqual(result["status"],"CANDIDATE_INTEGRITY_ONLY")
        self.assertEqual(result["counts"]["distinct_scoped_identities"],2)
        hits=query_semantic_inventory(self.base/"index.sqlite","KQ1001")
        self.assertEqual({x["namespace_id"] for x in hits["identity_occurrences"]},
                         {"kristal:alpha","kristal:beta"})
        self.assertEqual(len(hits["lexical_occurrences"]),2)
        self.assertEqual({x["status"] for x in hits["external_alignments"]},{"candidate"})
        self.assertEqual(len(query_semantic_inventory(self.base/"index.sqlite","ÉTOILE")["lexical_occurrences"]),2)
        self.assertEqual(len(query_semantic_inventory(self.base/"index.sqlite","Q42")["external_alignments"]),2)
        self.assertEqual(len(query_semantic_inventory(self.base/"index.sqlite","KQ1001",namespace_id="kristal:alpha")["identity_occurrences"]),1)

    def test_alias_direct_revision_and_jsonl_are_recognized(self):
        self.owner(revision="canon/domain/v11/rebuilt-v2",aliases=True,jsonl=True)
        outcome=self.build()
        self.assertEqual(outcome["counts"]["revision_complete_core"],1)
        self.assertEqual(outcome["counts"]["verified_jsonl_layers"],1)
        self.assertEqual(outcome["counts"]["lexical_occurrences"],1)

    def test_v11_root_and_dictionary_only_do_not_select_a_revision(self):
        self.owner(revision="canon/domain/v11",aliases=True)
        self.owner("Kristal-Beta","beta","kristal:beta",kind="dictionary",revision="canon/domain/v11/updates/dict-only")
        outcome=self.build()
        self.assertEqual(outcome["counts"]["revision_complete_core"],1)
        self.assertEqual(outcome["counts"]["revision_dictionary_only"],1)
        # sqlite3.Connection.__exit__ commits/rolls back, but DOES NOT close.
        # On Windows that leaves a handle open and TemporaryDirectory cleanup
        # raises WinError 32. closing() releases the file before teardown.
        with closing(sqlite3.connect(self.base/"index.sqlite")) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM revision WHERE selection_status!='unselected'").fetchone()[0],0)

    def test_recorded_acceptance_remains_not_qualified(self):
        self.owner(status="accepted")
        result=self.build()
        self.assertEqual(result["counts"]["recorded_accepted_exactmatch_audited_rule"],1)
        self.assertFalse(result["policy"]["independent_C1_C2_qualified"])
        self.assertFalse(result["policy"]["wikidata_exactmatch_approved_by_this_index"])

    def test_bad_catalog_layer_hash_blocks_without_source_changes(self):
        self.owner()
        p=self.locals/"Kristal-Alpha/canon/domain/v11/updates/r1/dictionaries/terms-fr.json"
        p.write_text(p.read_text()+" ")
        result=self.build()
        self.assertEqual(result["status"],"BLOCKED_INTEGRITY")
        self.assertEqual(result["counts"]["lexical_occurrences"] if "lexical_occurrences" in result["counts"] else 0,0)

    def test_jsonl_scope_mismatch_blocks(self):
        self.owner(jsonl=True)
        layer=self.locals/"Kristal-Alpha/canon/domain/v11/updates/r1/dictionaries/terms-fr.jsonl"
        content=json.loads(layer.read_text())
        content["namespace_id"]="kristal:attacker"
        layer.write_text(json.dumps(content)+"\n")
        catalog_path=self.locals/"Kristal-Alpha/canon/domain/v11/updates/r1/dictionaries/catalog.json"
        catalog=json.loads(catalog_path.read_text())
        catalog["languages"][0]["layers"][0]["sha256"]=sha256(layer.read_bytes()).hexdigest()
        catalog_path.write_text(json.dumps(catalog)+"\n")
        self.assertEqual(self.build()["status"],"BLOCKED_INTEGRITY")

    def test_cross_owner_same_scoped_id_blocks(self):
        self.owner()
        self.owner("Kristal-Beta","beta","kristal:alpha")
        self.assertEqual(self.build()["status"],"BLOCKED_INTEGRITY")

    def test_duplicate_slug_stops_before_creating_db(self):
        self.owner()
        self.owner("Kristal-Beta","alpha","kristal:beta")
        with self.assertRaisesRegex(LocalFirstAuditError,"Duplicate local slug"):
            self.build()
        self.assertFalse((self.base/"index.sqlite").exists())

    def test_existing_output_and_output_inside_canon_are_refused(self):
        self.owner()
        with self.assertRaisesRegex(LocalFirstAuditError,"canonical source tree"):
            build_semantic_inventory(self.locals,self.locals/"Kristal-Alpha/forbidden.sqlite")
        self.build()
        with self.assertRaisesRegex(LocalFirstAuditError,"existing private index"):
            self.build()

    def test_zip_snapshot_is_read_without_extraction(self):
        self.owner()
        archive=self.base/"locals.zip"
        with zipfile.ZipFile(archive,"w") as output:
            for p in self.locals.rglob("*"):
                if p.is_file():output.write(p,p.relative_to(self.locals).as_posix())
        summary=build_semantic_inventory(archive,self.base/"zip-result.sqlite")
        self.assertEqual(summary["status"],"CANDIDATE_INTEGRITY_ONLY")
        self.assertEqual(summary["counts"]["identity_occurrences"],1)

    def test_database_sql_lookup_is_parameterized(self):
        self.owner()
        self.build()
        result=query_semantic_inventory(self.base/"index.sqlite","KQ1001' OR 1=1 --")
        self.assertEqual(result["identity_occurrences"],[])
        with self.assertRaises(LocalFirstAuditError):
            query_semantic_inventory(self.base/"index.sqlite","",1)


if __name__ == "__main__":
    unittest.main()
