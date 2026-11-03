import hashlib
import json
import pytest
from kristal_manager.private_spek_intake import inspect, PrivateIntakeError


def test_private_handoff_never_authorizes_publication(tmp_path):
    graph=tmp_path/'graph.json';graph.write_text(json.dumps({'schema_version':'11.0','artifact_type':'kristal_semantic_graph',
        'assertions':[{'id':'KA1'}]}))
    migration=tmp_path/'migration.json';migration.write_text(json.dumps({'by_kind':{'A':{'legacy:1':'KA1'}}}))
    sha=lambda p:'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
    lock={'format':'spek.private-editorial-handoff/1.0','status':'PRIVATE_UNQUALIFIED_NOT_PUBLISHABLE',
        'source':{'kind':'kristal_v11_semantic_graph','sha256':sha(graph),'identity_migration_sha256':sha(migration)},
        'fields':[{'realization_key':'field-1','request_sha256':'sha256:'+'f'*64,'source_assertion_refs':['legacy:1']}],
        'template_locks':[{'template_ref':'rhetorical.definition@1.0.0','sha256':'sha256:'+'0'*64}],
        'selected_assertion_count':1,'relations_declared_unverified':[],
        'qualification':dict.fromkeys(['semantic_entailment_checked','semantik_result_pairs_verified',
        'rhetorical_relations_approved','c1_c2_c3_approved','publication_authorized'],False)}
    result=inspect(lock,graph_path=graph,identity_map=migration)
    assert result['identity_mapped_count']==1 and result['publication_authorized'] is False
    lock['qualification']['publication_authorized']=True
    with pytest.raises(PrivateIntakeError):inspect(lock,graph_path=graph,identity_map=migration)
    lock['qualification']['publication_authorized']=False
    graph.write_text('{}')
    with pytest.raises(PrivateIntakeError):inspect(lock,graph_path=graph,identity_map=migration)
