"""Read-only, evidence-driven classification of oversized files and archived HTML.

A path's category is informative, not permission to suppress a security finding.
Exceptions are local *review records* pinned to exact SHA-256 bytes, never canon.
"""
from __future__ import annotations
from pathlib import Path
from fnmatch import fnmatchcase
import hashlib
import re

_CANONICAL = ('canon/', 'knowledge-base/corpus/', '.kristal/v9/',
              '.kristal/v11/', '.kristal/v8/portable-state.', 'state/')
_EXTERNAL = ('external-source-library/snapshots/', 'external-source-library/archive/',
             'sources/archives/', 'archives/web/')
_RECONSTRUCTIBLE = ('derived/', '.kristal/v8/index/', '.cache/', '__pycache__/',
                    'build/', 'runtime/', 'projections/materialized/')


def classify_large_file(relative: str) -> dict:
    path = relative.replace('\\', '/')
    if path.startswith('./'):path=path[2:]
    lower = path.casefold()
    if any(lower.startswith(x) for x in _CANONICAL):
        return {'role': 'canonical_or_committed', 'basis': 'documented canonical/state prefix',
                'recommendation': 'Conserver; vérifier intégrité et politique de publication séparément.'}
    if any(lower.startswith(x) for x in _EXTERNAL):
        return {'role': 'external_source_archive', 'basis': 'archived acquisition/source folder',
                'recommendation': 'Conserver la provenance; vérifier le droit de conservation et les éventuels secrets intégrés.'}
    if any(lower.startswith(x) for x in _RECONSTRUCTIBLE):
        return {'role': 'derived_or_cache', 'basis': 'documented derived/cache prefix',
                'recommendation': 'Vérifier la reconstructibilité avant toute suppression; ne pas toucher au canon.'}
    return {'role': 'unclassified', 'basis': 'no recognized source role',
            'recommendation': 'Vérification manuelle requise; la taille ne prouve pas une anomalie.'}


def approved_exception(path: Path, relative: str, size: int, records: list) -> dict | None:
    """An exception applies only to an exact file with documented review and digest.

    Never downgrade size findings merely because a file name matches a pattern.
    """
    for item in records:
        if not isinstance(item, dict) or item.get('path') != relative:continue
        if item.get('status') != 'approved' or not str(item.get('reason','')).strip() or not str(item.get('reviewed_by','')).strip():continue
        digest = item.get('sha256')
        if not isinstance(digest,str) or not re.fullmatch(r'(?:sha256:)?[a-fA-F0-9]{64}',digest):continue
        if item.get('bytes') != size:continue
        h=hashlib.sha256()
        try:
            with path.open('rb') as stream:
                for buf in iter(lambda:stream.read(1024*1024),b''):h.update(buf)
        except OSError:continue
        if h.hexdigest().casefold() != digest.removeprefix('sha256:').casefold():continue
        return {'status':'approved', 'reason':str(item['reason'])[:250],
                'reviewed_by':str(item['reviewed_by'])[:100], 'sha256':'sha256:'+h.hexdigest()}
    return None


def html_context(relative: str, text: str) -> dict:
    """Context only. HTML embedding is not proof that a token is harmless."""
    low=relative.replace('\\','/').casefold()
    extension=Path(low).suffix
    likely_archive=extension in ('.html','.htm','.mhtml') and (
        any(part in low for part in ('archive','snapshot','mirror','captures','webpages','pages/','sources/'))
        or '<!-- saved from url=' in text[:25000].casefold()
        or 'web.archive.org' in text[:25000].casefold())
    return {'file_kind':'archived_third_party_html_candidate' if likely_archive else
            'html_document' if extension in ('.html','.htm','.mhtml') else 'source_text',
            'third_party_archive_candidate':bool(likely_archive),
            'requires_review':True,
            'assessment':'Possible embedded site script; NOT proof of public or harmless key.' if likely_archive
                          else 'Potential secret; review its origin and scope.',
            'values_included':False}
