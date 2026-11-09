"""Historical AI-review triage; never automatically accept or reject UNESCO tags.

The 2026-11-04 review records name specific conflicts in the earlier scan.  They
are *editorial notes*, not a deterministic semantic classifier, and are only
shown for the exact same current identity, declared codes and proposed code.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

REVIEW_PATH = Path(__file__).resolve().parent.parent / 'data' / 'ai_review_priorities_2026-11-04.json'


@lru_cache(maxsize=1)
def _priority_index():
    try:
        if REVIEW_PATH.is_symlink() or REVIEW_PATH.stat().st_size > 512000:
            return {}
        obj = json.loads(REVIEW_PATH.read_text('utf-8'))
        if obj.get('schema') != 'kristal-ai-triage/1.0':
            return {}
        return {str(x['state_ref']): x for x in obj.get('unesco_disagreements', [])
                if isinstance(x, dict) and x.get('state_ref') and x.get('suggested_code')}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def annotate_editorial_review(rows: list[dict]) -> int:
    index = _priority_index()
    matched = 0
    for row in rows:
        row.pop('editorial_unesco_review', None)
        historic = index.get(str(row.get('state_ref') or ''))
        evidence = row.get('qualification_evidence') or {}
        meta = evidence.get('metadata') or {}
        unesco = meta.get('unesco') or {}
        codes = {str(x['code']) for x in unesco.get('microthesauri', [])
                 if isinstance(x, dict) and x.get('code')}
        if not historic or evidence.get('metadata_source') != 'LIVE_WORKSPACE':
            continue
        if (str(row.get('proposed_unesco') or '') != str(historic.get('suggested_code'))
                or codes != set(str(x) for x in historic.get('declared_codes', []))):
            continue
        matched += 1
        row['editorial_unesco_review'] = {
            'status': 'AI_DRAFT_REVIEW_REQUIRED',
            'reason': str(historic.get('review_priority') or 'Disagreement with declared subjects'),
            'historical_review_date': '2026-11-04',
            'declared_subjects_preserved': True,
            'human_approved': False,
        }
    return matched


def display_unesco_review(row: dict) -> str:
    review = row.get('editorial_unesco_review') or {}
    if review:
        reason = review.get('reason') or ''
        if 'off-topic' in reason.casefold() or 'implausible' in reason.casefold():
            return 'Likely off-topic — AI review'
        return 'Difference — AI review needed'
    historic = row.get('historical_unesco_attention')
    if historic:
        return 'Historical suggestion disputed — AI review'
    dossier = row.get('semantic_enrichment') or {}
    if dossier.get('status') != 'MATCHED_CURRENT_DESCRIPTORS':
        return 'Not assessed'
    if dossier.get('unesco_proposal_disagrees_with_declared'):
        return 'Difference — review needed'
    if row.get('proposed_unesco'):
        return 'No declared disagreement'
    return 'No current proposal'


def annotate_historical_unesco_attention(rows: list[dict]) -> int:
    """Mark *historical* disputed suggestions on both UI surfaces.

    Unlike annotate_editorial_review, this does NOT mean the current scan made
    the same proposal. Require exact state identity and current LIVE declared
    subjects; keep this independent of a new UNESCO proposal.
    """
    index = _priority_index()
    total = 0
    for row in rows:
        row.pop('historical_unesco_attention', None)
        historic = index.get(str(row.get('state_ref') or ''))
        evidence = row.get('qualification_evidence') or {}
        if not historic or evidence.get('metadata_source') != 'LIVE_WORKSPACE':
            continue
        codes = {str(x.get('code')) for x in (((evidence.get('metadata') or {}).get('unesco') or {}).get('microthesauri') or [])
                 if isinstance(x, dict) and x.get('code')}
        if codes != {str(x) for x in historic.get('declared_codes', [])}:
            continue
        row['historical_unesco_attention'] = {
            'status': 'HISTORICAL_AI_DISAGREEMENT_NOT_CURRENT_SCAN',
            'historical_suggested_code': str(historic['suggested_code']),
            'reason': str(historic.get('review_priority') or ''),
            'human_approved': False,
        }
        total += 1
    return total


def display_current_unesco_review(row: dict) -> str:
    """Product-facing status: ignore archived suggestions without a current match."""
    dossier = row.get('semantic_enrichment') or {}
    if not row.get('proposed_unesco') and not dossier.get('unesco_proposal_disagrees_with_declared'):
        return 'No current proposal'
    return display_unesco_review(row)
