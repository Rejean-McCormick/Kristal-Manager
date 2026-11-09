"""Current-product editorial state, never a Framework qualification.

The four status labels are deliberately about local review readiness. A clean
inventory and matching documents are not independent semantic verification.
Historical AI suggestions are not defects in the current Kristal.
"""
from __future__ import annotations


def assess_editorial_state(row: dict) -> dict:
    """Make one understandable assessment from current (not historical) observations."""
    problems = row.get('problems') or ()
    codes = {p.get('code') for p in problems if isinstance(p, dict)}
    authoring = row.get('authoring_observation') or {}
    native = (row.get('native_source_review') or {}).get('status')
    ai = row.get('semantic_enrichment') or {}

    # Never hide actual structural failures behind a workspace's own label.
    if (row.get('readiness') not in ('READY',) or row.get('state_conflict') or
            row.get('identity_collision') or row.get('needs_migration') or
            row.get('priority') == 'blocker'):
        return _state('Needs work', 'Structural or identity issue', 'Resolve the structural issue first.')
    if authoring.get('workspace_status') == 'building':
        return _state('Building', 'Workspace is still being authored', 'Complete the native authoring checklist.')
    if authoring.get('source_catalog') in ('EMPTY', 'SCHEMA_ISSUE_OR_UNAVAILABLE'):
        return _state('Needs work', 'Source evidence needs attention', 'Restore or assess the source catalogue.')
    if row.get('priority') == 'warning' and (codes - {'LOCAL_DISCOVERY_STALE', 'LOCAL_DISCOVERY_INCOMPLETE'}):
        return _state('Needs work', 'A current technical issue is reported', 'Inspect the reported issue.')
    if native == 'SOURCES_CHANGED_REVIEW_AGAIN':
        return _state('Not assessed', 'Native source changed since review', 'Re-evaluate the changed native document.')
    if native == 'WORKSPACE_METADATA_CHANGED':
        return _state('Not assessed', 'Workspace metadata changed since review', 'Refresh the metadata comparison; native sources still match.')
    if native != 'SOURCE_BYTES_MATCHED' or authoring.get('status') != 'OBSERVED':
        return _state('Not assessed', 'Source material has not been fully checked', 'Check native sources and current metadata.')
    if ai.get('status') != 'MATCHED_CURRENT_DESCRIPTORS':
        return _state('Not assessed', 'Semantic characterization needs refresh', 'Review the current semantic description.')
    # Current suggestions are hypotheses, not defects. Still ask for an editorial
    # choice when they disagree; do not accept a suggestion automatically.
    if row.get('editorial_unesco_review') or ai.get('unesco_proposal_disagrees_with_declared'):
        return _state('Not assessed', 'UNESCO suggestion needs an editorial decision', 'Keep or dismiss the suggested UNESCO term.')
    if ai.get('prf_candidate'):
        return _state('Not assessed', 'PRF alternative needs an editorial decision', 'Keep the declared PRF or evaluate its alternative.')
    if row.get('content_status') == 'native_observed':
        return _state('Not assessed', 'Native contract semantics not yet reviewed', 'Review the native contract without forcing KQ/KP graphs.')
    if codes & {'LOCAL_DISCOVERY_STALE', 'LOCAL_DISCOVERY_INCOMPLETE'}:
        # A derived-file integrity issue is operational, not semantic failure.
        return _state('Not assessed', 'Discovery integrity has not passed', 'Check the derived Discovery files separately.')
    return _state('Ready', 'Local checks show no outstanding editorial issue',
                  'Ready for independent domain review; not Framework-qualified.')


def _state(status: str, reason: str, next_action: str) -> dict:
    return {'status': status, 'reason': reason, 'next_action': next_action,
            'framework_qualification': 'NOT_ESTABLISHED', 'canonical_changed': False,
            'human_approved': False}
