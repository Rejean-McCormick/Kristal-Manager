"""Read-only presentation bridge; legacy Windows icons may remain until manual UNESCO re-render.

Desktop.ini remains the authority for the Windows folder icon. This module
never generates an icon, writes a profile, or changes Explorer attributes.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import base64
import json
import os
import re
import struct

MAX_ICON_BYTES = 8 * 1024 * 1024
ICO_PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'

@dataclass(frozen=True)
class IconInfo:
    source: str
    ico: Path | None
    nature: str = ''
    maturity: int | None = None
    domains: tuple[str, ...] = ()
    note: str = ''


def _read_desktop_ini(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file() or path.stat().st_size > 512 * 1024:
        return {}
    raw = path.read_bytes()
    text = raw[2:].decode('utf-16le', 'replace') if raw.startswith(b'\xff\xfe') else raw.decode('utf-8-sig', 'replace')
    result: dict[str, dict[str, str]] = {}
    section = ''
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] in ';#':
            continue
        if line.startswith('[') and line.endswith(']'):
            section = line[1:-1].strip().lower()
            continue
        if '=' in line:
            key, value = line.split('=', 1)
            result.setdefault(section, {})[key.strip().lower()] = value.strip()
    return result


def _valid_ico_path(root: Path, fragment: str) -> Path | None:
    # IconResource is a local cache only: paths that escape the workspace are
    # not used (no shell expansion, no URL, no dynamic loading).
    if not fragment:
        return None
    fragment = fragment.strip().strip('"').replace('\\', '/')
    relative = Path(fragment)
    if relative.is_absolute() or relative.drive or ':' in fragment or '\x00' in fragment:
        return None
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()) or candidate.suffix.lower() != '.ico':
        return None
    if not candidate.is_file() or candidate.stat().st_size > MAX_ICON_BYTES:
        return None
    return candidate


def read_registry_icon_index(collection_root: str | Path | None = None) -> dict[str, IconInfo]:
    """Optional read-only cache of presentation icons from the original Registry.

    Exact folder-name matches only. This is not a semantic join or a sync.
    """
    root = Path(collection_root or os.environ.get('KRISTAL_COLLECTION_ROOT') or
                (r'C:\mycode\Kristal\Kristal-Kollection' if os.name == 'nt' else
                 Path.home() / 'mycode' / 'Kristal' / 'Kristal-Kollection')).expanduser()
    catalogue = root / '_registry' / 'knowledge-base' / 'registry' / 'kristal-registry.catalog.json'
    if not catalogue.is_file() or catalogue.stat().st_size > 32 * 1024 * 1024:
        return {}
    try:
        entries = json.loads(catalogue.read_text(encoding='utf8')).get('entries', [])
    except (ValueError, OSError, TypeError):
        return {}
    index = {}
    for e in entries if isinstance(entries, list) else []:
        if not isinstance(e, dict):continue
        locator = str(e.get('locator') or '').replace('\\','/')
        parts = Path(locator).parts
        if len(parts)!=2 or parts[0] != 'domains':continue
        name = parts[1]
        if name in index or not name.startswith('Kristal-'):continue
        data = ((e.get('presentation') or {}).get('icon') or {})
        if not isinstance(data,dict):continue
        rendering = data.get('rendering') or {}
        filename = rendering.get('filename') or (str(data['icon_code'])+'.ico' if data.get('icon_code') else '')
        if not re.fullmatch(r'KR-(REF|COL|MOD|PRT|TWN|INV|SRC)-[A-Z0-9-]+-M[0-5]\.ico',str(filename)):
            continue
        ico=None
        library=root/'_registry'/'icons'/'ico'/filename
        local=root/'domains'/name/'.kristal'/filename
        for candidate in (local,library):
            if candidate.is_file() and not candidate.is_symlink() and candidate.stat().st_size<=MAX_ICON_BYTES:
                ico=candidate.resolve();break
        if ico is None:continue
        index[name]=IconInfo('registry-présentation',ico,str(data.get('nature') or ''),
            data.get('maturity'),tuple(str(d.get('code')) for d in data.get('domains',()) if isinstance(d,dict)),
            'Cache de présentation Registry ; pas une icône Windows appliquée dans locals')
    return index


def discover_icon(workspace: str | Path, *, registry_icons: dict[str, IconInfo] | None = None) -> IconInfo:
    root = Path(workspace).resolve()
    if not root.is_dir():
        return IconInfo('missing', None, note='Dossier inaccessible')
    try:
        desktop = _read_desktop_ini(root / 'desktop.ini')
    except OSError as exc:
        return IconInfo('error', None, note=str(exc))
    shell = desktop.get('.shellclassinfo', {})
    kristal = desktop.get('kristal', {})
    raw_resource = shell.get('iconresource', '')
    relative = raw_resource.rsplit(',', 1)[0] if raw_resource else ''
    ico = _valid_ico_path(root, relative)
    domains = tuple(kristal[k] for k in ('domain1','domain2','domain3') if kristal.get(k))
    nature = kristal.get('nature', '')
    maturity = int(kristal['maturity']) if kristal.get('maturity','').isdigit() else None
    if ico is not None:
        return IconInfo('desktop.ini', ico, nature, maturity, domains,
                        'Icône personnalisée déjà appliquée à Windows')
    profile = root / '.kristal' / 'icon-profile.json'
    try:
        if profile.is_file() and profile.stat().st_size < 1024 * 1024:
            data = json.loads(profile.read_text(encoding='utf-8'))
            if data.get('profile') == 'kristal-icon/1.0':
                render = data.get('rendering') or {}
                name = render.get('filename') or ''
                ico = _valid_ico_path(root, '.kristal/' + name) if name else None
                domain_values = tuple(str(d.get('code', '')) for d in data.get('domains', ()) if isinstance(d, dict))
                if ico is None and registry_icons:
                    fallback=registry_icons.get(root.name)
                    if fallback and fallback.ico:return fallback
                return IconInfo('icon-profile.json', ico, str(data.get('nature',nature)),
                                data.get('maturity'), domain_values,
                                'Profil présent ; aucun changement d’icône Windows')
    except (OSError, ValueError, TypeError, KeyError):
        pass
    fallback = (registry_icons or {}).get(root.name)
    if fallback and fallback.ico:
        return fallback
    return IconInfo('desktop.ini non résolu' if raw_resource else 'none', None,
                    nature, maturity, domains,
                    'Icône absente ou non lisible ; ouvrir le générateur si nécessaire')


def png_from_ico(path: Path, *, preferred: int = 32) -> bytes | None:
    """Decode PNG-backed ICO frames without external Python dependencies.

    The original Icon Generator stores PNG frames in its multiresolution ICO.
    Returns None for historical BMP-backed icons; GUI can show a fallback.
    """
    try:
        if path.stat().st_size > MAX_ICON_BYTES:
            return None
        blob = path.read_bytes()
        if len(blob) < 6 or blob[:4] != b'\x00\x00\x01\x00':
            return None
        count = struct.unpack_from('<H', blob, 4)[0]
        if count > 256 or count == 0 or len(blob) < 6 + count * 16:
            return None
        frames = []
        for i in range(count):
            at = 6 + 16 * i
            w, h, colors, reserved, planes, bpp, length, offset = struct.unpack_from('<BBBBHHII', blob, at)
            dim = w or 256
            if offset + length > len(blob) or length < 8:
                continue
            png = blob[offset:offset + length]
            if png.startswith(ICO_PNG_SIGNATURE):
                frames.append((abs(dim - preferred), -dim, png))
        if not frames:
            return None
        return min(frames, key=lambda t: (t[0], t[1]))[2]
    except OSError:
        return None


def tk_photo_from_icon(tk, path: Path, preferred=32):
    png = png_from_ico(path, preferred=preferred)
    return tk.PhotoImage(data=base64.b64encode(png).decode('ascii')) if png else None
