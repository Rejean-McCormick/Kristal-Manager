"""English classification labels from pinned local vocabularies; no approvals."""
from __future__ import annotations

from kristal_manager.classification_labels import display_category, get_reference_counts
from kristal_manager.global_panel import display_registered_ark, format_chatgpt_summary
from kristal_manager.qualification_history import display_declared, display_unesco_declaration


def test_pinned_references_have_expected_coverage():
    assert get_reference_counts() == {'ark':19,'prf':21,'unesco':88,'unesco_domain':7}


def test_expected_human_readable_names():
    assert display_category('ARK-03', 'ark') == 'Milestone and Proof Map'
    assert display_category('PRF-20', 'prf') == 'Multi-Purpose Semantic Reference'
    assert display_category('6.70', 'unesco') == 'Finance and trade'
    assert display_category('2.70', 'unesco') == 'Biology'
    assert display_category('6', 'unesco_domain') == 'Politics, law and economics'


def test_unknown_code_is_not_mapped_by_guessing():
    assert display_category('ARK-99','ark') == 'Unresolved category (ARK-99)'
    assert display_category('9.99','unesco') == 'Unresolved category (9.99)'
    assert display_category(None,'ark') == 'Not declared'


def test_existing_codes_not_mutated_by_display():
    meta={'primary_archetype':'ARK-03','primary_usage':'PRF-20',
          'unesco':{'microthesauri':[{'code':'6.70'},{'code':'2.70'}]}}
    entry={'qualification_evidence':{'metadata':meta,'metadata_source':'LIVE_WORKSPACE'}}
    assert display_declared(entry,'primary_archetype') == 'Milestone and Proof Map'
    assert display_declared(entry,'primary_usage') == 'Multi-Purpose Semantic Reference'
    assert display_unesco_declaration(entry) == 'Finance and trade, Biology'
    assert meta['primary_archetype']=='ARK-03'
    assert meta['unesco']['microthesauri'][0]['code']=='6.70'


def test_old_snapshot_display_and_review_status():
    e={'qualification_evidence':{'metadata':{'primary_archetype':'ARK-03','unesco':{'microthesauri':[{'code':'6.70'}]}},
                                 'metadata_source':'RECOVERED_SNAPSHOT_ONLY_NOT_CURRENTLY_VERIFIED'},
       'registered_review':{'archetype_review_status':'proposed',
                            'archetype_recommendations':['ARK-01','ARK-03'],
                            'locally_selected_archetype':None}}
    assert display_declared(e,'primary_archetype') == 'Milestone and Proof Map (old snapshot)'
    assert display_unesco_declaration(e)=='Finance and trade (old snapshot)'
    assert display_registered_ark(e)=='Semantic Reference / Milestone and Proof Map (proposed)'


def test_human_readable_report_does_not_promote_proposals():
    row={'title':'Example', 'state_ref':'urn:kristal:example:state','path':'C:/example',
         'priority':'review','qualification_evidence':{'metadata':{
             'primary_archetype':'ARK-03','primary_usage':'PRF-20',
             'unesco':{'microthesauri':[{'code':'6.70'}]}}, 'metadata_source':'LIVE_WORKSPACE'},
         'proposed_arketype':'ARK-07','proposed_unesco':'2.70','proposed_unesco_domain':'2',
         'registered_review':None}
    report=format_chatgpt_summary({'entries':[row]})
    assert 'declared_ARK=Milestone and Proof Map' in report
    assert 'declared_PRF=Multi-Purpose Semantic Reference' in report
    assert 'declared_UNESCO=Finance and trade' in report
    assert 'ARK_new_proposal=Invariant / Formal Theory' in report
    assert 'UNESCO_suggestion=Biology' in report
    assert 'not human approvals' in report
