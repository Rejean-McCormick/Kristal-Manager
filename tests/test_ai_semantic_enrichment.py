"""Evidence-based AI semantic drafts: current identity, stale sources, no upgrades."""
from __future__ import annotations

import json
from pathlib import Path

from kristal_manager.semantic_enrichment import (
    CATALOG_PATH, annotate_ai_dossiers, basis_digest, load_catalog,
    display_semantic_role, display_prf_refinement,
)
from kristal_manager.qualification_history import annotate_qualifications
from kristal_manager.global_panel import format_chatgpt_summary


def _case(tmp_path: Path):
    index = load_catalog()
    ref = 'urn:kristal:accounting:state'
    source = index[ref]
    # Need the exact six fingerprint fields from the recovered workspace metadata.
    snap = json.loads(Path(__file__).resolve().parent.parent.joinpath(
        'data/recovered_qualification_evidence_2026-11-04.json').read_text('utf-8'))
    historic = next(x for x in snap['entries'] if x['state_ref'] == ref)
    m = historic['snapshot_metadata']
    folder = tmp_path / 'Kristal-Accounting'
    folder.mkdir()
    (folder / 'kristal.workspace.json').write_text(json.dumps({
        'format':'kristal.local-workspace/3.2.0',
        'title':'Accounting', 'state_ref':ref, 'status':'building',
        'subject':{'domain':m['subject_domain'], 'orientation':m['subject_orientation']},
        'native_model':{'kind':m['native_model_kind'], 'description':m['native_model_description']},
        'classification':{'primary_archetype':m['primary_archetype'],
                          'primary_usage':m['primary_usage']},
    }), encoding='utf-8')
    row = {'path':str(folder),'title':'Accounting','state_ref':ref,'priority':'review',
           'operational_result':'NOT_EVALUATED', 'proposed_unesco':None,
           'proposed_arketype':None,'proposed_unesco_domain':None,'content_status':'observed',
           'readiness':'READY','keywords':[],'problems':[],'human_review':[]}
    assert basis_digest(m) == source['basis_sha256']
    annotate_qualifications([row], source=tmp_path)
    return row, folder


def test_127_editorial_dossiers_are_unique_source_bound_not_approvals():
    index = load_catalog()
    assert len(index) == 127
    assert all(r['qualification_status'] == 'AI_SEMANTIC_DRAFT_NOT_APPROVED' for r in index.values())
    assert all(r['semantic_role_en'] and r['semantic_scope_en'] and r['critical_distinction_en'] for r in index.values())
    assert sum(bool(r['prf_candidate']) for r in index.values()) == 7
    assert all(r['prf_candidate']['status'] == 'AI_EXPLORATORY_ALTERNATIVE_NOT_APPROVED'
               for r in index.values() if r['prf_candidate'])


def test_title_change_is_not_semantic_staleness_and_canonical_kept(tmp_path):
    row, folder = _case(tmp_path)
    before = (folder / 'kristal.workspace.json').read_bytes()
    result = annotate_ai_dossiers([row])
    assert result['matched_live'] == 1
    assert display_semantic_role(row) == 'Economic accounting ledger'
    assert 'Keep declared PRF' in display_prf_refinement(row)
    assert row['semantic_enrichment']['human_approval_inferred'] is False
    assert row['semantic_enrichment']['write_authorized'] is False
    assert row['qualification_evidence']['metadata']['primary_usage'] == 'PRF-20'
    assert row['operational_result'] == 'NOT_EVALUATED'
    assert (folder / 'kristal.workspace.json').read_bytes() == before


def test_changed_model_blocks_old_semantic_claim(tmp_path):
    row, folder = _case(tmp_path)
    p = folder / 'kristal.workspace.json'
    src = json.loads(p.read_text('utf-8'))
    src['native_model']['description'] = 'A completely different project'
    p.write_text(json.dumps(src), encoding='utf-8')
    annotate_qualifications([row], source=tmp_path)
    result = annotate_ai_dossiers([row])
    assert result['outdated'] == 1
    assert display_semantic_role(row) == 'Needs semantic review'
    assert display_prf_refinement(row) == 'Not evaluated'


def test_missing_live_workspace_not_treated_as_current(tmp_path):
    entry = {'path':str(tmp_path/'Kristal-Accounting'),'state_ref':'urn:kristal:accounting:state'}
    annotate_qualifications([entry], source=tmp_path)
    result = annotate_ai_dossiers([entry])
    assert result['snapshot_only'] == 1
    assert display_semantic_role(entry) == 'Needs semantic review'


def test_identity_mismatch_not_promoted(tmp_path):
    row, folder = _case(tmp_path)
    p = folder / 'kristal.workspace.json'
    src = json.loads(p.read_text('utf-8'))
    src['state_ref'] = 'urn:kristal:other:state'
    p.write_text(json.dumps(src), encoding='utf-8')
    annotate_qualifications([row], source=tmp_path)
    result = annotate_ai_dossiers([row])
    assert result['identity_blocked'] == 1
    assert row['semantic_enrichment']['semantic_role_en'] is None


def test_chatgpt_report_labels_ai_separately_from_declared(tmp_path):
    row, folder = _case(tmp_path)
    annotate_ai_dossiers([row])
    report = {'counts':{'kristals':1,'ai_semantic_dossiers_matched':1}, 'entries':[row]}
    text = format_chatgpt_summary(report)
    assert 'AI_semantic_role=Economic accounting ledger' in text
    assert 'AI review' in text or 'AI semantic dossiers' in text
    assert 'declared_PRF=Multi-Purpose Semantic Reference' in text
    assert (folder / 'kristal.workspace.json').exists()


def test_disputed_unesco_does_not_replace_declared(tmp_path):
    row, folder = _case(tmp_path)
    p = folder / 'kristal.workspace.json'
    src = json.loads(p.read_text('utf-8'))
    src['classification']['unesco_thesaurus'] = {'microthesauri':[{'code':'6.70'}]}
    p.write_text(json.dumps(src),encoding='utf-8')
    annotate_qualifications([row], source=tmp_path)
    row['proposed_unesco'] = '3.25'
    totals = annotate_ai_dossiers([row])
    assert totals['matched_live'] == 1
    assert totals['unesco_proposal_disagreements'] == 1
    assert row['qualification_evidence']['metadata']['unesco']['microthesauri'][0]['code'] == '6.70'


def test_review_html_is_escaped_and_has_no_approval(tmp_path):
    from kristal_manager.semantic_enrichment import render_review_html
    row, _folder = _case(tmp_path)
    annotate_ai_dossiers([row])
    row['title'] = '<script>alert(1)</script>'
    output = tmp_path / 'review.html'
    render_review_html([row], output)
    html = output.read_text('utf-8')
    assert '&lt;script&gt;' in html
    assert '<script>' not in html
    assert 'not human-approved' in html.lower()
    assert 'Economic accounting ledger' in html
