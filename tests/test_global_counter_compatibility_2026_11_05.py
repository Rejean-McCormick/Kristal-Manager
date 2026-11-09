"""Regression: mixed loaded Manager components must not abort global analysis.

A previous release's source evidence counter lacks ``metadata_changed``.
This can occur if a Manager process remained running during an overlay update.
"""
from pathlib import Path

from kristal_manager import global_analysis
from kristal_manager import native_evidence, authoring_observations
from test_global_analysis import make_kristal


def test_global_analysis_accepts_legacy_optional_counter_api(tmp_path, monkeypatch):
    source = tmp_path / 'locals'
    make_kristal(source)

    def old_native(rows):
        for row in rows:
            row['native_source_review'] = {
                'status': 'NO_SOURCE_REVIEW',
                'human_approved': False,
                'c1_c2_c3': 'NOT_ESTABLISHED',
            }
        return {'catalogue': 'AVAILABLE', 'matched': 0, 'changed': 0,
                'not_verified': len(rows)}  # deliberately lacks metadata_changed

    def old_authoring(rows):
        for row in rows:
            row['authoring_observation'] = {'status': 'UNVERIFIED'}
        return {'observed': 0}  # deliberately lacks newer counters

    monkeypatch.setattr(native_evidence, 'annotate_native_sources', old_native)
    monkeypatch.setattr(authoring_observations, 'annotate_authoring', old_authoring)
    output = global_analysis.analyze_all(source, catalogue=tmp_path/'catalog.sqlite3',
                                          reports_base=tmp_path/'reports')
    report = output['global_report']
    counts = report['counts']
    assert counts['kristals'] == 1
    assert counts['native_metadata_only_changed'] == 0
    assert counts['native_review_counters_complete'] is False
    assert counts['authoring_counters_complete'] is False
    assert any('mixed Manager version' in note for note in report['limits'])
    assert Path(output['report_directory'], 'tableau_global.csv').is_file()


def test_new_native_counter_api_includes_metadata_changed():
    rows = [{'state_ref': 'urn:kristal:unknown:test', 'qualification_evidence': {},
             'path': '/not/a/real/workspace'}]
    counters = native_evidence.annotate_native_sources(rows)
    assert {'matched', 'changed', 'metadata_changed', 'not_verified'} <= counters.keys()
    assert counters['not_verified'] == 1
    assert rows[0]['native_source_review']['human_approved'] is False
