"""Optional, operator-configured, non-authoritative bridge to external KristalDiag.

This component does NOT ship KristalDiag or assume its CLI grammar. It runs a
user-selected trusted local program without a shell and preserves its result
as an observed external diagnostic, not a C1 attestation.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

FORMAT = 'kristal.manager-external-diag/0.1-experimental'
MAX_OUTPUT_BYTES = 1024 * 1024
MAX_REPORT_BYTES = 4 * 1024 * 1024
ALLOWED_SCRIPT_EXTENSIONS = {'.py', '.js', '.mjs'}


class DiagConfigurationError(ValueError):
    pass


def _utc_now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def validate_config(program: str | Path, arguments: str, *, root: str | Path | None = None) -> tuple[list[str], list[str]]:
    """Validate a local program and an explicit token template (no shell)."""
    candidate = Path(program).expanduser().absolute()
    if candidate.is_symlink():
        raise DiagConfigurationError('Un lien symbolique vers le programme n’est pas accepté.')
    exe = candidate.resolve()
    if not exe.is_file():
        raise DiagConfigurationError('Programme KristalDiag introuvable ou lien symbolique non autorisé.')
    if root is not None and exe.is_relative_to(Path(root).expanduser().resolve()):
        raise DiagConfigurationError('Le programme doit être installé hors des Kristals sources.')
    suffix = exe.suffix.lower()
    if suffix in ('.bat', '.cmd', '.ps1', '.sh'):
        raise DiagConfigurationError('Les lanceurs shell .cmd/.bat/.ps1/.sh ne sont pas pris en charge. Fournir un exécutable ou le script .py/.js/.mjs.')
    if suffix == '.py':
        launcher = [sys.executable, str(exe)]
    elif suffix in ('.mjs', '.js'):
        node = shutil.which('node')
        if node is None:
            raise DiagConfigurationError('Node.js introuvable. Installer Node ou fournir un exécutable.')
        launcher = [node, str(exe)]
    elif suffix == '.exe' or (os.name != 'nt' and os.access(exe, os.X_OK)):
        launcher = [str(exe)]
    else:
        raise DiagConfigurationError('Sélectionner un .exe, .py, .js ou .mjs exécutable.')
    try:
        tokens = shlex.split(arguments, posix=True)
    except ValueError as exc:
        raise DiagConfigurationError('Arguments illisibles : ' + str(exc)) from exc
    for token in tokens:
        if '{' in token or '}' in token:
            if token not in ('{workspace}', '{report}'):
                raise DiagConfigurationError('Chaque variable {workspace} ou {report} doit être un argument autonome.')
    if '{workspace}' not in tokens:
        raise DiagConfigurationError('Les arguments doivent contenir {workspace} (chemin transmis au diagnostic).')
    if len(tokens) > 50:
        raise DiagConfigurationError('Trop d’arguments configurés.')
    return launcher, tokens


def _fingerprint(root: Path) -> dict:
    """Bind recorded diagnostic to the exact known descriptor and candidate files."""
    rels = ['kristal.workspace.json', 'state/state-snapshot.json', 'build/v9/state-snapshot.json', '.kristal/v9/state-snapshot.json']
    result = {}
    for rel in rels:
        p = root / rel
        if p.is_file() and not p.is_symlink():
            h = hashlib.sha256()
            with p.open('rb') as src:
                for buf in iter(lambda: src.read(1024 * 1024), b''):
                    h.update(buf)
            result[rel] = 'sha256:' + h.hexdigest()
    return result


def _read_bounded(path: Path, limit: int) -> tuple[str, bool]:
    size = path.stat().st_size if path.exists() else 0
    with path.open('rb') as file:
        raw = file.read(limit)
    return raw.decode('utf-8', errors='replace'), size > limit


def run_diagnostic(workspace: str | Path, *, program: str | Path, arguments: str,
                   source_root: str | Path | None = None, timeout: int = 180) -> dict:
    """Invoke a trusted operator-selected tool once. No shell, no implicit validation.

    Warnings: the external program itself may mutate files or use the network;
    the Manager makes no such claim about tools it does not control.
    """
    root = Path(workspace).expanduser().resolve()
    if not root.is_dir() or not (root / 'kristal.workspace.json').is_file():
        raise DiagConfigurationError('Le diagnostic requiert un Kristal principal avec kristal.workspace.json.')
    launcher, tokens = validate_config(program, arguments, root=source_root or root)
    if not (1 <= timeout <= 1800):
        raise DiagConfigurationError('Délai invalide (1 à 1800 secondes).')
    before = _fingerprint(root)
    with tempfile.TemporaryDirectory(prefix='kristal-manager-external-diag-') as staging:
        tmp = Path(staging)
        external_report = tmp / 'kristal-diag-result.json'
        argv = launcher + [str(root) if t == '{workspace}' else str(external_report) if t == '{report}' else t for t in tokens]
        timed_out = False
        returncode = None
        with (tmp / 'stdout.txt').open('wb') as out, (tmp / 'stderr.txt').open('wb') as err:
            try:
                completed = subprocess.run(argv, cwd=str(Path(program).expanduser().resolve().parent),
                                           stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                           shell=False, check=False, timeout=timeout)
                returncode = completed.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
        stdout, stdout_truncated = _read_bounded(tmp / 'stdout.txt', MAX_OUTPUT_BYTES)
        stderr, stderr_truncated = _read_bounded(tmp / 'stderr.txt', MAX_OUTPUT_BYTES)
        parsed = None
        source = None
        if external_report.is_file() and not external_report.is_symlink() and external_report.stat().st_size <= MAX_REPORT_BYTES:
            try:
                parsed = json.loads(external_report.read_text(encoding='utf-8'))
                source = 'output_file'
            except (ValueError, UnicodeError, OSError):
                pass
        if parsed is None and not stdout_truncated and len(stdout.encode('utf-8')) <= MAX_REPORT_BYTES:
            try:
                parsed = json.loads(stdout)
                source = 'stdout'
            except (ValueError, UnicodeError):
                pass
        after = _fingerprint(root)
        changed = before != after
        status = ('TIMEOUT' if timed_out else 'EXECUTED_EXIT_0' if returncode == 0 else 'EXECUTED_NONZERO')
        return {
            'format': FORMAT,
            'executed_at': _utc_now(),
            'workspace': str(root),
            'program': str(Path(program).expanduser().resolve()),
            'argument_template': arguments,
            'process_status': status,
            'returncode': returncode,
            'timeout_seconds': timeout,
            'report_source': source,
            'external_report': parsed,
            'stdout_excerpt': stdout[:10000],
            'stderr_excerpt': stderr[:10000],
            'output_truncated': stdout_truncated or stderr_truncated,
            'input_fingerprint': before,
            'input_changed_during_run': changed,
            'qualification': 'NOT_ESTABLISHED',
            'attestation': 'NOT_VERIFIED',
            'limitations': [
                'Le protocole officiel de KristalDiag/C1 n’a pas été fourni et ne peut pas être présumé.',
                'Un code de sortie 0 ne constitue pas une preuve de qualification ou conformité Framework.',
                'L’outil externe peut effectuer ses propres écritures ou connexions réseau : vérifier sa documentation avant exécution.',
                'Les empreintes ne couvrent que les surfaces d’état locales connues, pas la totalité des données du Kristal.'
            ]
        }
