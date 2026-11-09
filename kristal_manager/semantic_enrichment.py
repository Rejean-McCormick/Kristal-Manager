"""AI semantic dossiers, joined strictly to current live descriptors.

The catalogue is historical editorial analysis, never a qualification or mutation.
New descriptive columns cannot alter canonical tags or the operational verdict.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parent.parent / 'data' / 'ai_semantic_review_127_2026-11-04.json'
FORMAT = 'kristal.manager-ai-semantic-review/1.0'
BASIS_FIELDS = ('primary_archetype', 'primary_usage', 'subject_domain', 'subject_orientation',
                'native_model_kind', 'native_model_description')


def basis_digest(metadata: dict) -> str:
    projection = {name: metadata.get(name) for name in BASIS_FIELDS}
    raw = json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def load_catalog(path: Path | str | None = None) -> dict:
    p = Path(path or CATALOG_PATH)
    if p.is_symlink() or not p.is_file() or p.stat().st_size > 3 * 1024 * 1024:
        raise ValueError('AI review dossier unavailable or unsafe')
    obj = json.loads(p.read_text(encoding='utf-8'))
    if (not isinstance(obj, dict) or obj.get('format') != FORMAT
            or obj.get('no_automatic_approval') is not True
            or obj.get('no_canonical_updates') is not True
            or obj.get('no_c1_c2_c3_qualification') is not True
            or not isinstance(obj.get('entries'), list)):
        raise ValueError('Unsupported AI review dossier')
    index = {}
    for item in obj['entries']:
        if (not isinstance(item, dict) or not isinstance(item.get('state_ref'), str)
                or not isinstance(item.get('basis_sha256'), str)
                or len(item['basis_sha256']) != 64
                or item.get('qualification_status') != 'AI_SEMANTIC_DRAFT_NOT_APPROVED'
                or not isinstance(item.get('semantic_role_en'), str)
                or not isinstance(item.get('semantic_scope_en'), str)):
            raise ValueError('Invalid AI review entry')
        if item['state_ref'] in index:
            raise ValueError('Duplicate AI review identity')
        index[item['state_ref']] = item
    return index


def annotate_ai_dossiers(entries: list[dict], *, catalog_path: Path | str | None = None) -> dict:
    """Attach a historical AI draft ONLY if the live semantic descriptors still match.

    A mismatch keeps the old editorial text as historical evidence but does NOT
    show it as a valid current AI recommendation in the table or exports.
    """
    try:
        index = load_catalog(catalog_path)
        catalogue_status = 'AVAILABLE'
    except (OSError, ValueError, UnicodeError, TypeError, json.JSONDecodeError):
        index = {}
        catalogue_status = 'UNAVAILABLE'
    totals = {'catalogue_status':catalogue_status, 'matched_live':0, 'outdated':0,
              'snapshot_only':0, 'missing':0, 'identity_blocked':0, 'prf_alternatives':0,
              'unesco_proposal_disagreements':0}
    for row in entries:
        reference = row.get('state_ref')
        record = index.get(reference)
        evidence = row.get('qualification_evidence') or {}
        meta = evidence.get('metadata') or {}
        source = evidence.get('metadata_source')
        if source == 'IDENTITY_MISMATCH_NO_FALLBACK':
            status = 'IDENTITY_MISMATCH'
            totals['identity_blocked'] += 1
        elif not record:
            status = 'NOT_REVIEWED'
            totals['missing'] += 1
        elif source != 'LIVE_WORKSPACE':
            status = 'ARCHIVED_ONLY_NOT_CURRENTLY_VERIFIED'
            totals['snapshot_only'] += 1
        elif basis_digest(meta) != record['basis_sha256']:
            status = 'SEMANTIC_METADATA_CHANGED_REVIEW_AGAIN'
            totals['outdated'] += 1
        else:
            status = 'MATCHED_CURRENT_DESCRIPTORS'
            totals['matched_live'] += 1
        if status == 'MATCHED_CURRENT_DESCRIPTORS' and record:
            candidate = record.get('prf_candidate')
            if candidate:
                totals['prf_alternatives'] += 1
            declared_subjects = {str(x.get('code')) for x in ((meta.get('unesco') or {}).get('microthesauri') or [])
                                 if isinstance(x, dict) and x.get('code')}
            proposal = row.get('proposed_unesco')
            conflict = bool(proposal and declared_subjects and proposal not in declared_subjects)
            if conflict:
                totals['unesco_proposal_disagreements'] += 1
            dossier = {
                'status':status, 'semantic_role_en':record['semantic_role_en'],
                'semantic_scope_en':record['semantic_scope_en'],
                'critical_distinction_en':record['critical_distinction_en'],
                'prf_candidate':candidate,
                'declared_prf_retained':meta.get('primary_usage'),
                'prf_review_guidance':record['prf_review_guidance'],
                'source_scope':record['source_scope'],
                'evidence_excerpt':record.get('evidence_excerpt'),
                'basis_sha256':record['basis_sha256'],
                'unesco_proposal_disagrees_with_declared':conflict,
                'human_approval_inferred':False, 'qualifies_c1_c2_c3':False,
                'write_authorized':False,
            }
        else:
            dossier = {'status':status, 'semantic_role_en':None, 'semantic_scope_en':None,
                       'prf_candidate':None, 'human_approval_inferred':False,
                       'qualifies_c1_c2_c3':False, 'write_authorized':False,
                       'note':'Historic AI draft not matched to the current verified semantic descriptor.'}
        row['semantic_enrichment'] = dossier
    return totals


def display_semantic_role(entry: dict) -> str:
    info = entry.get('semantic_enrichment') or {}
    return str(info.get('semantic_role_en') or 'Needs semantic review')


def display_prf_refinement(entry: dict) -> str:
    info = entry.get('semantic_enrichment') or {}
    if info.get('status') != 'MATCHED_CURRENT_DESCRIPTORS':
        return 'Not evaluated'
    candidate = info.get('prf_candidate')
    if not candidate:
        return 'Keep declared PRF — review pending'
    from .classification_labels import display_category
    return display_category(candidate['id'], 'prf') + ' (AI candidate, not approved)'


def render_review_html(entries: list[dict], target: Path | str) -> None:
    """Write an English, read-only review report OUTSIDE canonical Kristal roots."""
    from html import escape
    esc = lambda x: escape(str(x or ''), quote=True)
    matched = sum((r.get('semantic_enrichment') or {}).get('status') == 'MATCHED_CURRENT_DESCRIPTORS' for r in entries)
    candidates = sum(bool((r.get('semantic_enrichment') or {}).get('prf_candidate')) for r in entries)
    lines = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>Kristal Manager — AI Semantic Review</title>',
        '<style>body{font:15px/1.5 system-ui,sans-serif;max-width:1120px;margin:auto;padding:30px;color:#222;background:#fafafa}'
        'h1{margin:0}header{border-bottom:2px solid #343a40;padding-bottom:18px} .muted{color:#5d6772}'
        '.stats{display:flex;gap:22px;margin:16px 0}.stats b{font-size:28px;display:block}nav{line-height:2}'
        'article{background:white;border:1px solid #ddd;border-radius:10px;padding:20px;margin:16px 0}'
        'article h2{margin:0}.meta{font-size:13px;color:#59636f}.field{margin:10px 0}strong{color:#232b3a}'
        'a{color:#1155a1;text-decoration:none}a:hover{text-decoration:underline}'
        '.warning{border-left:4px solid #b87b24;padding:9px 12px;background:#fffaf0}'
        '@media(max-width:680px){body{padding:12px}.stats{flex-wrap:wrap}}</style>',
        '</head><body><header><h1>AI Semantic Review — 127 Kristals</h1>',
        '<p class="muted">Editorial AI dossiers based on project metadata and historical summaries. '
        'Not human-approved classifications; not a Framework C1/C2/C3 qualification. '
        'No canonical files or publication settings changed.</p>',
        f'<div class="stats"><div><b>{len(entries)}</b>inventoried</div>'
        f'<div><b>{matched}</b>current metadata matched</div>'
        f'<div><b>{candidates}</b>PRF alternatives to investigate</div></div></header>',
        '<nav><h2>Projects</h2>'
    ]
    for i,row in enumerate(entries,1):
        lines.append(f'<a href="#k{i}">{esc(row.get("title"))}</a> &nbsp; ')
    lines.append('</nav><main>')
    from .classification_labels import display_category
    for i,row in enumerate(entries,1):
        e = row.get('semantic_enrichment') or {}
        meta = (row.get('qualification_evidence') or {}).get('metadata') or {}
        candidate = e.get('prf_candidate')
        lines.extend([
            f'<article id="k{i}"><h2>{esc(row.get("title"))}</h2>',
            f'<div class="meta">{esc(row.get("state_ref"))} · {esc(e.get("status"))}</div>',
            '<p class="field"><strong>AI semantic role:</strong> '+esc(e.get('semantic_role_en') or 'Not currently verified')+'</p>',
            '<p class="field"><strong>Purpose:</strong> '+esc(e.get('semantic_scope_en') or 'Requires review')+'</p>',
            '<p class="field"><strong>Essential distinction:</strong> '+esc(e.get('critical_distinction_en') or 'Not evaluated')+'</p>',
            '<p class="field"><strong>Declared PRF:</strong> '+esc(display_category(meta.get('primary_usage'), 'prf'))+'</p>',
            '<p class="field"><strong>AI PRF review:</strong> '+esc(display_prf_refinement(row))+'</p>',
        ])
        if candidate:
            lines.append('<p class="field"><strong>Why investigate:</strong> '+esc(candidate.get('rationale_en'))+'</p>')
        if e.get('unesco_proposal_disagrees_with_declared'):
            lines.append('<p class="warning">UNESCO scan proposal differs from declared subjects — do not overwrite automatically.</p>')
        editorial = row.get('editorial_unesco_review') or {}
        if editorial:
            lines.append('<p class="warning"><strong>AI editorial triage:</strong> ' +
                         esc(editorial.get('reason')) + '. This is not a human decision.</p>')
        lines.append('<p class="meta">Evidence scope: '+esc(e.get('source_scope') or e.get('note') or 'Not available')+
                     '. Human approval: NO. Canonical update: NO.</p></article>')
    lines.extend(['</main></body></html>'])
    Path(target).write_text('\n'.join(lines)+'\n', encoding='utf-8')
