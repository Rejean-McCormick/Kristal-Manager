"""Read-only UNESCO Thesaurus and ISCED-F classification observation.

Pinned Framework v7 KOS reference (7 domains, 88 microthesauri) and icon
policy (ISCED-F 2013 broad fields). These are DIFFERENT vocabularies.
Never infer a UNESCO URI/code from a Kristal title, legacy domain or icon.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from datetime import datetime, timezone
from html import escape
import json
import re

from .core import _read_json
from .workspace_tools import is_historical, category_of

REFERENCE = Path(__file__).parent / 'reference'
FORMAT = 'kristal.manager-unesco-audit/0.1'


@lru_cache(maxsize=1)
def reference() -> dict:
    """Load and validate the included pinned reference instead of guessing."""
    profile = json.loads((REFERENCE / 'unesco-thesaurus-profile.json').read_text('utf-8'))
    baseline = json.loads((REFERENCE / 'unesco-thesaurus-baseline.json').read_text('utf-8'))
    seed = json.loads((REFERENCE / 'toc-registry-100-seed.example.json').read_text('utf-8'))
    isced = json.loads((REFERENCE / 'isced-f2013-broad-fields.json').read_text('utf-8'))
    domains, micros = {}, {}
    for d in profile['domains']:
        notation = d['notation']
        if notation in domains:
            raise ValueError('Repeated UNESCO domain notation')
        domains[notation] = {k:d[k] for k in ('notation','label_en','uri','kristall_default_role')}
        for mt in d['microthesauri']:
            code = mt['notation']
            if code in micros:
                raise ValueError('Repeated UNESCO microthesaurus notation')
            micros[code] = {**mt,'domain':notation}
    if (len(domains), len(micros)) != (7, 88) or (baseline['baseline']['domains'], baseline['baseline']['microthesauri']) != (7, 88):
        raise ValueError('Bundled UNESCO profile differs from the pinned v7 reference')
    if len(isced['codes']) != 11 or set(isced['codes']) != {f'{i:02}' for i in range(11)}:
        raise ValueError('Bundled ISCED-F broad-field list differs from Icon Generator policy')
    categories = {x['category_id']: x for x in seed['categories']}
    subjects = {s['subject_id']:s for s in seed['subjects']}
    return {'profile':profile, 'baseline':baseline, 'domains':domains, 'microthesauri':micros,
            'isced':isced['codes'], 'seed_subjects':subjects,'seed_categories':categories}


def _many(value) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple)):
        return [x.strip() for x in value if isinstance(x, str) and x.strip()]
    return []


def _notations(values, refs: dict) -> tuple[list[str], list[str]]:
    """Only resolve explicit notations/known URIs; no free-text name matching."""
    result, invalid = [], []
    uri_index = {data['uri']:code for code,data in refs.items()}
    for raw in values:
        val = raw.strip()
        code = val if val in refs else uri_index.get(val)
        if code and code not in result:
            result.append(code)
        elif not code:
            invalid.append(val)
    return result, invalid


def _code_list(value):
    """Accept only explicit structured values, never descriptive labels."""
    if isinstance(value, dict):
        return _many(value.get('broad_fields') or value.get('codes') or value.get('domains') or value.get('code'))
    return _many(value)


def observe(row: dict, icon=None) -> dict:
    """Produce an observational crosswalk, no writes and no semantic inference."""
    ref = reference()
    root = Path(row.get('path') or '.')
    workspace = _read_json(root / 'kristal.workspace.json') if row.get('path') else {}
    classification = workspace.get('classification') if isinstance(workspace.get('classification'), dict) else {}
    subject = workspace.get('subject') if isinstance(workspace.get('subject'), dict) else {}
    discovery_class = ((row.get('discovery') or {}).get('classification') or {})
    # An explicit workspace declaration takes priority over derived discovery metadata.
    source = 'workspace' if classification else 'discovery' if isinstance(discovery_class,dict) and discovery_class else 'none'
    meta = classification if classification else discovery_class if isinstance(discovery_class,dict) else {}
    unesco = meta.get('unesco_thesaurus') or meta.get('unesco') or subject.get('unesco_thesaurus') or subject.get('unesco')
    u = unesco if isinstance(unesco,dict) else {}
    raw_domains = _many(u.get('domains') or u.get('domain') or u.get('domain_notations'))
    raw_micros = _many(u.get('microthesauri') or u.get('microthesaurus') or u.get('microthesaurus_notations'))
    # External alignment is explicit ONLY when the recorded KOS is UNESCO.
    placements = u.get('category_placements') or subject.get('category_placements') or []
    if isinstance(placements, list):
        for placement in placements:
            if not isinstance(placement,dict):
                continue
            ext = placement.get('external_alignment') or placement
            if not isinstance(ext,dict):
                continue
            if ext.get('kos_id') not in ('kos:unesco-thesaurus','unesco-thesaurus'):
                continue
            value = ext.get('external_uri') or ext.get('notation')
            if isinstance(value,str):
                raw_micros.append(value) if '/mt' in value or re.fullmatch(r'[1-7]\.\d{2}',value) else raw_domains.append(value)
    domains, unknown_domains = _notations(raw_domains,ref['domains'])
    micros, unknown_micros = _notations(raw_micros,ref['microthesauri'])
    issues = []
    if unknown_domains:
        issues.append('Unknown UNESCO domain code/URI: ' + ', '.join(unknown_domains))
    if unknown_micros:
        issues.append('Unknown UNESCO microthesaurus code/URI: ' + ', '.join(unknown_micros))
    implied = list(dict.fromkeys(ref['microthesauri'][code]['domain'] for code in micros))
    if domains and any(x not in domains for x in implied):
        issues.append('Declared UNESCO domain does not contain all declared microthesauri')
    if not domains:
        domains = implied
    declared = bool(raw_domains or raw_micros)
    seed_hint = None
    kq = subject.get('kq_id') or subject.get('subject_kq') or subject.get('id')
    if isinstance(kq,str) and kq in ref['seed_subjects']:
        entry = ref['seed_subjects'][kq]
        codes = []
        for placement in entry.get('category_placements', []):
            category = ref['seed_categories'].get(placement.get('category_id'))
            if category:
                codes.append({'notation': category['external_alignment']['notation'],
                              'placement':placement.get('placement'), 'confidence':placement.get('confidence')})
        seed_hint = {'subject_kq':kq,'seed_label':entry.get('label'),'placements':codes,
                     'note':'Framework v7 seed example, not a declaration or approved mapping of this workspace'}
    icon_codes = list(getattr(icon,'domains',()) or []) if icon else []
    icon_profile = _read_json(root / '.kristal/icon-profile.json') if row.get('path') else {}
    if icon_profile.get('profile') == 'kristal-icon/1.0':
        icon_codes = [d.get('code') for d in icon_profile.get('domains',[]) if isinstance(d,dict)]
    icon_codes = [x for x in icon_codes if isinstance(x,str)]
    raw_isced = _code_list(meta.get('isced_f2013') or meta.get('isced_f') or {})
    isced_declared, invalid_isced_declared = _notations(raw_isced,{k:{'uri':f'IS:code:{k}'} for k in ref['isced']})
    isced_icon, invalid_isced_icon = _notations(icon_codes,{k:{'uri':f'IS:code:{k}'} for k in ref['isced']})
    if invalid_isced_declared:
        issues.append('Unknown declared ISCED-F code: '+', '.join(invalid_isced_declared))
    if invalid_isced_icon:
        issues.append('Unrecognized icon domain code (may be legacy): '+', '.join(invalid_isced_icon))
    if isced_declared and isced_icon and set(isced_declared)!=set(isced_icon):
        issues.append('ISCED-F declaration and icon profile disagree')
    if len(isced_icon)>3:
        issues.append('Icon lists more than 3 ISCED-F broad fields (Kristal extension limit)')
    isced_codes = isced_declared or isced_icon
    status = 'Review' if issues else 'Declared' if declared else 'Seed hint only' if seed_hint else 'Not mapped'
    return {'unesco':{'status':status,'source':source if declared else 'none',
                      'domain_codes':domains,'domain_labels':[ref['domains'][x]['label_en'] for x in domains],
                      'microthesaurus_codes':micros,
                      'microthesaurus_labels':[ref['microthesauri'][x]['label_en'] for x in micros],
                      'domain_7_is_facet':'7' in domains,
                      'seed_hint':seed_hint,
                      'concept_uris':_many(u.get('concept_uris'))},
            'isced_f2013':{'codes':isced_codes,'labels':[ref['isced'][x] for x in isced_codes],
                           'declared_codes':isced_declared,'icon_codes':isced_icon,
                           'source':'workspace/discovery declaration' if isced_declared else 'icon-profile' if isced_icon else 'unavailable',
                           'status':'Review' if any('ISCED' in x or 'icon domain' in x for x in issues) else 'Observed' if isced_codes else 'Not mapped'},
            'legacy_domain':category_of(row),
            'issues':issues,'conformity':'NOT_EVALUATED',
            'warning':'Taxonomy observation only. No C1, semantic verification, or UNESCO endorsement.'}


def display_domain(result: dict) -> str:
    data = result['unesco']; codes = data['domain_codes']; labels = data['domain_labels']
    return ' / '.join(f'{c} {label}' for c,label in zip(codes,labels)) if codes else 'Unmapped'


def display_micro(result: dict) -> str:
    data = result['unesco']; codes = data['microthesaurus_codes']; labels = data['microthesaurus_labels']
    return ' / '.join(f'{c} {label}' for c,label in zip(codes,labels)) if codes else 'Unmapped'


def display_isced(result: dict) -> str:
    codes = result['isced_f2013']['codes']
    return ', '.join(codes) if codes else 'Unmapped'


def build_audit(rows: list[dict], icons: dict | None=None) -> dict:
    """Report observations for current Kristals only; internal histories excluded."""
    output=[]; icons=icons or {}
    for row in rows:
        if is_historical(row) or row.get('hidden_auxiliary'):
            continue
        observed = observe(row,icons.get(row.get('path')))
        output.append({'title':row.get('title'),'path':row.get('path'),'state_ref':row.get('state_ref'),
                       **observed})
    return {'format':FORMAT,'generated_at':datetime.now(timezone.utc).isoformat(),
            'reference':{'name':'UNESCO Thesaurus, Framework v7 pinned reference spine',
                         'domains':7,'microthesauri':88,
                         'isced':'ISCED-F 2013 broad fields, Kristal Icon Generator 2.4 policy'},
            'counts':{'kristals':len(output),
                      'unesco_declared':sum(bool(x['unesco']['domain_codes'] or x['unesco']['microthesaurus_codes']) and x['unesco']['source']!='none' for x in output),
                      'unesco_unmapped':sum(not x['unesco']['domain_codes'] and not x['unesco']['microthesaurus_codes'] for x in output),
                      'isced_observed':sum(bool(x['isced_f2013']['codes']) for x in output),
                      'needs_review':sum(bool(x['issues']) for x in output)},
            'entries':output,
            'limits':['No automatic UNESCO concept or category inference from free text or names.',
                      'Framework v7 subject seed placements are hints only, and require explicit KQ identity.',
                      'An observed icon ISCED code is presentation metadata, not a semantic or C1 check.',
                      'No source Kristal was modified.']}


def audit_html(report: dict) -> str:
    """Offline HTML, escaped text and no externally loaded assets."""
    cells=[]
    for rec in report['entries']:
        cells.append('<tr>'+''.join('<td>'+escape(str(text))+'</td>' for text in (
            rec['title'],display_domain(rec),display_micro(rec),display_isced(rec),
            rec['unesco']['status'], '; '.join(rec['issues']) or '—'))+'</tr>')
    counts=report['counts']
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Kristal UNESCO Classification Audit</title>'
            '<style>body{font:15px Segoe UI,Arial,sans-serif;margin:32px;color:#203d3a}'
            'h1{color:#1e6864} table{border-collapse:collapse;width:100%} td,th{border-bottom:1px solid #ccd8d6;padding:8px;text-align:left;vertical-align:top}'
            'thead{background:#eaf3f0}small{color:#506865}</style>'
            '<h1>Kristal Manager — UNESCO classification audit</h1>'
            f'<p>{counts["kristals"]} Kristals · {counts["unesco_declared"]} declared UNESCO mappings · '
            f'{counts["isced_observed"]} ISCED observed · {counts["needs_review"]} review flags</p>'
            '<small>Framework v7 pinned UNESCO reference, ISCED-F 2013 for icons. Read-only, not conformance certification.</small>'
            '<table><thead><tr><th>Kristal</th><th>UNESCO domain</th><th>Microthesaurus</th><th>ISCED icon</th><th>Status</th><th>Review</th></tr></thead><tbody>'
            +''.join(cells)+'</tbody></table></html>')


def save_private_html(path: str | Path, content: str, *, overwrite: bool=False) -> Path:
    """Save an offline HTML report without following symlinks or writing sources."""
    import os
    target=Path(path).expanduser().absolute()
    if target.is_symlink():
        raise ValueError('Refusing to replace a symlink')
    flags=os.O_WRONLY|os.O_CREAT|getattr(os,'O_NOFOLLOW',0)
    flags|=os.O_TRUNC if overwrite else os.O_EXCL
    fd=os.open(target,flags,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as stream:
        stream.write(content)
    return target
