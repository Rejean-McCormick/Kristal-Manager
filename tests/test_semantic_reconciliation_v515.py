"""Adversarial tests: semantic review is private, deterministic and undecided."""
from __future__ import annotations

from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from kristal_manager.local_first_audit import LocalFirstAuditError
from kristal_manager.semantic_federation_inventory import PROFILE as SOURCE_PROFILE, _create_schema
from kristal_manager.semantic_reconciliation_v515 import (
    PROFILE, reconcile_semantic_inventory, list_reconciliation_cases)


def compact(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":"))


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base=Path(temp.name)
        self.source=self.base/"v514.sqlite"
        self.review=self.base/"review.sqlite"
        self.report=self.base/"summary.json"
        # The test runner itself may be nested inside a Git checkout. Only
        # this test environment's parent Git guard is disabled.
        helper=patch('kristal_manager.semantic_federation_inventory._inside_git_checkout',return_value=False)
        helper.start();self.addCleanup(helper.stop)
        self.seed()

    def seed(self):
        with closing(sqlite3.connect(self.source)) as db:
            _create_schema(db)
            ns="kristal:alpha"
            db.execute("INSERT INTO workspace VALUES (?,?,?,?)",("alpha","Kristal-Alpha","urn:kristal:alpha:state","0"*64))
            for revision,kind in (("r1","complete_core"),("r2","complete_core"),("dict","dictionary_only")):
                db.execute("INSERT INTO revision(slug,revision_dir,revision_label,kind,roles_json,sha256_json,namespace_id) VALUES (?,?,?,?,?,?,?)",
                           ("alpha",revision,revision,kind,"{}","{}",ns))
            for revision,semantic,kind in (("r1","KQ1","entity"),("r2","KQ1","entity"),
                                            ("r1","KQ2","entity"),("r2","KQ2","property"),
                                            ("r1","KQ3","entity"),("r1","KQ4","entity")):
                record={"id":semantic,"kind":kind,"status":"stable"}
                db.execute("INSERT INTO identity_occurrence VALUES (?,?,?,?,?,?,?,?)",
                           (ns,semantic,kind,"stable","alpha",revision,revision+"/identity-registry.json",compact(record)))
            for revision,semantic,term in (("r1","KQ1","étoile"),("r2","KQ1","astre"),
                                          ("r1","KQ3","Mercure"),("r1","KQ4","Mercure"),
                                          ("dict","KQ999","dictionnaire seul")):
                record={"semantic_id":semantic,"preferred_term":term}
                db.execute("INSERT INTO lexical_occurrence VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                           (ns,semantic,"alpha",revision,"fr",term,term.casefold(),"curated",100,
                            revision+"/dictionaries/fr.json",compact(record)))
            for rev,semantic,qid,status,evidence in (("r1","KQ1","Q100","candidate",["KS1"]),
                                                     ("r2","KQ1","Q100","accepted",["KS2"]),
                                                     ("r2","KQ1","Q200","accepted",[]),
                                                     ("r1","KQ3","Q999","rejected",[])):
                record={"local_ref":{"id":semantic,"namespace_id":ns},
                        "external_ref":{"system":"wikidata","id":qid},
                        "relation":"exactMatch","status":status,
                        "review":{"method":"audited_rule","evidence_refs":evidence}}
                db.execute("INSERT INTO external_alignment VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                           (ns,semantic,"alpha",rev,"wikidata",qid,"exactMatch",status,
                            "audited_rule",rev+"/external-crosswalk.json",compact(record)))
            metadata={"profile":SOURCE_PROFILE,"status":"CANDIDATE_INTEGRITY_ONLY",
                      "counts":{"local_workspaces":1,"revision_groups":3,
                                "identity_occurrences":6,"lexical_occurrences":5,
                                "external_alignment_occurrences":4,
                                "distinct_scoped_identities":4,
                                "recorded_accepted_exactmatch_audited_rule":2}}
            db.execute("INSERT INTO metadata VALUES (?,?)",("summary_json",compact(metadata)))
            db.commit()

    def build(self):
        return reconcile_semantic_inventory(self.source,self.review,self.report)

    def test_produces_source_pinned_undecided_cases_and_unselected_revisions(self):
        before=sha256(self.source.read_bytes()).hexdigest()
        result=self.build()
        self.assertEqual(result["status"],"REVIEW_CANDIDATE_NOT_QUALIFIED")
        self.assertEqual(result["input"]["source_db_sha256"],before)
        self.assertEqual(before,sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(result["counts"]["review_cases"],7)
        self.assertEqual(result["counts"]["revisions_unselected"],3)
        self.assertFalse(result["policy"]["automatic_wikidata_approval"])
        with closing(sqlite3.connect(self.review)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM review_case WHERE decision_state!='NOT_DECIDED'").fetchone()[0],0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM revision_snapshot WHERE selection_state!='unselected'").fetchone()[0],0)

    def test_multi_target_and_accepted_without_evidence_are_priority_high(self):
        result=self.build()
        self.assertEqual(result["counts"]["EXACTMATCH_TARGET_VARIANTS"],1)
        self.assertEqual(result["counts"]["exactmatch_multi_target_with_recorded_acceptance"],1)
        self.assertEqual(result["counts"]["RECORDED_ACCEPTANCE_WITHOUT_EVIDENCE"],1)
        self.assertEqual(result["counts"]["EXACTMATCH_TARGET_VARIANTS"],1)
        self.assertEqual(list_reconciliation_cases(self.review,semantic_id="KQ3")["total_matches"],0)
        cases=list_reconciliation_cases(self.review,namespace_id="kristal:alpha",semantic_id="KQ1")
        kinds={c["kind"]:c for c in cases["cases"]}
        self.assertEqual(kinds["EXACTMATCH_TARGET_VARIANTS"]["priority"],"HIGH")
        self.assertEqual(kinds["RECORDED_ACCEPTANCE_WITHOUT_EVIDENCE"]["priority"],"HIGH")
        self.assertEqual(kinds["EXACTMATCH_STATUS_VARIANTS"]["distinct_variants"],2)

    def test_lexical_drift_polysemy_and_dictionary_only_are_distinguished(self):
        result=self.build()
        self.assertEqual(result["counts"]["COMPETING_PREFERRED_TERMS"],1)
        self.assertEqual(result["counts"]["SHARED_LEXICAL_TERM"],1)
        self.assertEqual(result["counts"]["UNREGISTERED_LEXICAL_ID_IN_COMPLETE_REVISION"],0)
        polysemy=list_reconciliation_cases(self.review,kind="SHARED_LEXICAL_TERM")
        self.assertEqual(polysemy["total_matches"],1)
        self.assertEqual(polysemy["cases"][0]["term_folded"],"mercure")
        self.assertIsNone(polysemy["cases"][0]["semantic_id"])

    def test_query_filters_pagination_are_parameterized(self):
        self.build()
        hits=list_reconciliation_cases(self.review,limit=2,offset=1)
        self.assertEqual(len(hits["cases"]),2)
        self.assertEqual(hits["total_matches"],7)
        self.assertTrue(all("evidence_samples" in case for case in hits["cases"]))
        self.assertEqual(list_reconciliation_cases(self.review,semantic_id="KQ1' OR 1=1 --")["total_matches"],0)
        with self.assertRaises(LocalFirstAuditError):
            list_reconciliation_cases(self.review,kind="INVENTED_KIND")
        with self.assertRaises(LocalFirstAuditError):
            list_reconciliation_cases(self.review,offset=-1)

    def test_refuses_existing_outputs_without_overwriting(self):
        self.report.write_text("private preexisting report")
        with self.assertRaisesRegex(LocalFirstAuditError,"existing private index"):
            self.build()
        self.assertEqual(self.report.read_text(),"private preexisting report")
        self.assertFalse(self.review.exists())

    def test_blocked_source_metadata_refuses_before_creating_output(self):
        with closing(sqlite3.connect(self.source)) as db:
            row=db.execute("SELECT value FROM metadata WHERE key='summary_json'").fetchone()
            summary=json.loads(row[0]);summary["status"]="BLOCKED_INTEGRITY"
            db.execute("UPDATE metadata SET value=? WHERE key='summary_json'",(compact(summary),));db.commit()
        with self.assertRaisesRegex(LocalFirstAuditError,"blocked"):
            self.build()
        self.assertFalse(self.review.exists())

    def test_inconsistent_metadata_refuses_before_creating_output(self):
        with closing(sqlite3.connect(self.source)) as db:
            db.execute("INSERT INTO identity_occurrence VALUES (?,?,?,?,?,?,?,?)",
                       ("kristal:alpha","KQ777","entity","stable","alpha","r1","x","{}"))
            db.commit()
        with self.assertRaisesRegex(LocalFirstAuditError,"metadata/count mismatch"):
            self.build()
        self.assertFalse(self.report.exists())

    def test_selected_revision_is_not_an_accepted_input(self):
        with closing(sqlite3.connect(self.source)) as db:
            db.execute("UPDATE revision SET selection_status='selected' WHERE revision_dir='r1'")
            db.commit()
        with self.assertRaisesRegex(LocalFirstAuditError,"selected revisions"):
            self.build()
        self.assertFalse(self.review.exists())

    def test_source_drift_removes_incomplete_candidate(self):
        import kristal_manager.semantic_reconciliation_v515 as module
        actual=module._sha_file
        calls=0
        def changed_second(path):
            nonlocal calls
            calls+=1
            return actual(path) if calls==1 else "f"*64
        with patch.object(module,"_sha_file",side_effect=changed_second):
            with self.assertRaisesRegex(LocalFirstAuditError,"changed during"):
                self.build()
        self.assertFalse(self.review.exists())
        self.assertFalse(self.report.exists())


if __name__=="__main__":
    unittest.main()
