"""Read-only UNESCO Thesaurus reference-spine observation.
Never infer UNESCO classification from a legacy ISCED icon, title or domain.
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
    categories = {x['category_id']: x for x in seed['categories']}
    subjects = {s['subject_id']:s for s in seed['subjects']}
    return {'profile':profile, 'baseline':baseline, 'domains':domains, 'microthesauri':micros,
            'seed_subjects':subjects,'seed_categories':categories}


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
    if u and u.get('kos_id') not in (None,'kos:unesco-thesaurus','unesco-thesaurus'):
        issues.append('UNESCO KOS identifier mismatch')
        domains=[];micros=[]
    if u.get('mapping_status') == 'candidate':
        issues.append('UNESCO mapping candidate requires review')
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
    # Legacy ISCED-F is a historical migration indicator only, NOT an active taxonomy.
    icon_profile = _read_json(root / '.kristal/icon-profile.json') if row.get('path') else {}
    legacy_icon = bool(icon_profile and icon_profile.get('classification',{}).get('scheme') != 'UNESCO Thesaurus')
    legacy_metadata = 'isced_f2013' in meta or 'isced_f' in meta
    needs_migration = legacy_icon or legacy_metadata
    if icon_profile.get('classification',{}).get('scheme') == 'UNESCO Thesaurus':
        icon_domain_codes=[d.get('code') for d in icon_profile.get('domains',[]) if isinstance(d,dict)]
        if not declared:
            issues.append('UNESCO icon profile exists without a workspace UNESCO declaration')
        elif any(code not in domains for code in icon_domain_codes):
            issues.append('UNESCO icon domains differ from declared UNESCO domains')
    status = 'Review' if issues else 'Declared' if declared else 'Seed hint only' if seed_hint else 'Not mapped'
    return {'unesco':{'status':status,'source':source if declared else 'none',
                      'domain_codes':domains,'domain_labels':[ref['domains'][x]['label_en'] for x in domains],
                      'microthesaurus_codes':micros,
                      'microthesaurus_labels':[ref['microthesauri'][x]['label_en'] for x in micros],
                      'domain_7_is_facet':'7' in domains,
                      'seed_hint':seed_hint,
                      'concept_uris':_many(u.get('concept_uris'))},
            'legacy_icon_migration_needed':needs_migration,
            'legacy_domain':category_of(row),
            'issues':issues,'conformity':'NOT_EVALUATED',
            'warning':'Taxonomy observation only. No C1, semantic verification, or UNESCO endorsement.'}


def display_domain(result: dict) -> str:
    data = result['unesco']; codes = data['domain_codes']; labels = data['domain_labels']
    return ' / '.join(f'{c} {label}' for c,label in zip(codes,labels)) if codes else 'Unmapped'


def display_micro(result: dict) -> str:
    data = result['unesco']; codes = data['microthesaurus_codes']; labels = data['microthesaurus_labels']
    return ' / '.join(f'{c} {label}' for c,label in zip(codes,labels)) if codes else 'Unmapped'


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
                         'icon_scheme':'UNESCO Thesaurus (UT1–UT7)'},
            'counts':{'kristals':len(output),
                      'unesco_declared':sum(bool(x['unesco']['domain_codes'] or x['unesco']['microthesaurus_codes']) and x['unesco']['source']!='none' for x in output),
                      'unesco_unmapped':sum(not x['unesco']['domain_codes'] and not x['unesco']['microthesaurus_codes'] for x in output),
                      'legacy_icons_pending':sum(bool(x['legacy_icon_migration_needed']) for x in output),
                      'needs_review':sum(bool(x['issues']) for x in output)},
            'entries':output,
            'limits':['No automatic UNESCO concept or category inference from free text or names.',
                      'Framework v7 subject seed placements are hints only, and require explicit KQ identity.',
                      'Legacy icon metadata is reported only for migration; it is never mapped to UNESCO automatically.',
                      'No source Kristal was modified.']}


def audit_html(report: dict) -> str:
    """Offline HTML, escaped text and no externally loaded assets."""
    cells=[]
    for rec in report['entries']:
        cells.append('<tr>'+''.join('<td>'+escape(str(text))+'</td>' for text in (
            rec['title'],display_domain(rec),display_micro(rec),'Yes' if rec['legacy_icon_migration_needed'] else 'No',
            rec['unesco']['status'], '; '.join(rec['issues']) or '—'))+'</tr>')
    counts=report['counts']
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Kristal UNESCO Classification Audit</title>'
            '<style>body{font:15px Segoe UI,Arial,sans-serif;margin:32px;color:#203d3a}'
            'h1{color:#1e6864} table{border-collapse:collapse;width:100%} td,th{border-bottom:1px solid #ccd8d6;padding:8px;text-align:left;vertical-align:top}'
            'thead{background:#eaf3f0}small{color:#506865}</style>'
            '<h1>Kristal Manager — UNESCO classification audit</h1>'
            f'<p>{counts["kristals"]} Kristals · {counts["unesco_declared"]} declared UNESCO mappings · '
            f'{counts["legacy_icons_pending"]} legacy icons · {counts["needs_review"]} review flags</p>'
            '<small>Framework v7 pinned UNESCO reference; icons use UT1–UT7. Read-only, not conformance certification.</small>'
            '<table><thead><tr><th>Kristal</th><th>UNESCO domain</th><th>Microthesaurus</th><th>Legacy icon?</th><th>Status</th><th>Review</th></tr></thead><tbody>'
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
