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
    """Bound the diagnostic freshness check to known V9 inputs and commitments.

    A full v11/Framework attestation is out of scope. This checks the files
    capable of invalidating the V9-State-Reader result without hashing the
    entire potentially enormous canonical corpus on each inventory refresh.
    """
    rels = [
        'kristal.workspace.json', 'canon/state.index.json',
        'state/state-snapshot.json', 'build/v9/state-snapshot.json',
        '.kristal/v9/state-snapshot.json', '.kristal/v9/capabilities.json',
        '.kristal/v9/activation.json', '.kristal/v9/logical-contracts.json',
        '.kristal/v9/manifest.sha256.json', '.kristal/v9/materialization-manifest.json',
        '.kristal/v9/logical-artifact.json', '.kristal/v9/package-manifest.json',
        '.kristal/v9/derivation.json', '.kristal/v9/exchange.json',
    ]
    artifact_dir = root / '.kristal' / 'v9' / 'artifacts'
    if artifact_dir.is_dir() and not artifact_dir.is_symlink():
        rels += [p.relative_to(root).as_posix() for p in sorted(artifact_dir.glob('*.json'))
                 if p.is_file() and not p.is_symlink()]
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

# Direct integration for the user-supplied official KristalDiag source package.
# Its CLI/profiles are documented and independently tested; unlike the generic
# external bridge above, the command is not editable by the operator.
OFFICIAL_PROFILES = ('V9-State-Reader', 'V10-Node-Reader', 'V10-Full')


def bundled_kristaldiag() -> Path:
    """Locate the exact KristalDiag snapshot shipped next to this Manager."""
    return Path(__file__).resolve().parents[1] / 'tools' / 'KristalDiag' / 'kristaldiag.py'


def evidence_directory() -> Path:
    """Keep all derived reports under the user's Manager data, not source Kristals."""
    from .ui_prefs import settings_path
    return settings_path().parent / 'diagnostics'


def _extract_official_findings(evidence_current: Path, summary: dict) -> list[dict]:
    """Surface bounded findings without trusting arbitrary report-relative paths."""
    out = []
    for level in summary.get('levels', [])[:120]:
        if not isinstance(level, dict):
            continue
        ident = str(level.get('id') or '')
        if not ident.isalnum() or len(ident) > 8:
            continue
        result = evidence_current / 'levels' / ident / 'result.json'
        if not result.is_file() or result.is_symlink() or result.stat().st_size > MAX_REPORT_BYTES:
            continue
        try:
            payload = json.loads(result.read_text(encoding='utf-8'))
        except (ValueError, OSError, UnicodeError):
            continue
        for finding in (payload.get('findings') or [])[:100]:
            if not isinstance(finding, dict):
                continue
            verdict = str(finding.get('verdict') or '—')
            if verdict in ('PASS', 'SKIP'):
                continue
            out.append({'level': ident, 'verdict': verdict,
                        'id': str(finding.get('id') or '')[:100],
                        'message': str(finding.get('message') or '')[:850]})
            if len(out) >= 200:
                return out
    return out


def run_official_diagnostic(workspace: str | Path, *, profile: str = 'V9-State-Reader',
                            script: str | Path | None = None,
                            output_root: str | Path | None = None, timeout: int = 600) -> dict:
    """Run supplied KristalDiag with its *actual* CLI and collect durable evidence.

    Never invokes shell, --allow-exec or network-capable options. Evidence is
    always outside the selected Kristal. Does not certify release or V11.
    """
    import importlib.util
    import re
    import uuid

    if profile not in OFFICIAL_PROFILES:
        raise DiagConfigurationError('Profil KristalDiag non pris en charge par ce panneau.')
    root = Path(workspace).expanduser().resolve(strict=True)
    if not (root / 'kristal.workspace.json').is_file():
        raise DiagConfigurationError('Sélectionnez un Kristal principal doté de kristal.workspace.json.')
    entry = Path(script or bundled_kristaldiag()).expanduser().resolve()
    if not entry.is_file() or entry.is_symlink():
        raise DiagConfigurationError('KristalDiag intégré est manquant. Réinstallez l’archive complète du Manager.')
    if entry.is_relative_to(root):
        raise DiagConfigurationError('Le moteur de diagnostic ne peut être situé dans le Kristal analysé.')
    if importlib.util.find_spec('jsonschema') is None:
        raise DiagConfigurationError('Dépendance jsonschema manquante. Cliquez sur « Installer le prérequis » dans la fenêtre Diagnostic.')
    if not (60 <= timeout <= 1800):
        raise DiagConfigurationError('Délai de diagnostic invalide.')

    output_base = Path(output_root or evidence_directory()).expanduser().resolve()
    if output_base == root or output_base.is_relative_to(root):
        raise DiagConfigurationError('Les preuves doivent être enregistrées hors des sources du Kristal.')
    # Diagnostic evidence is personal/local, with a unique folder per run.
    slug = re.sub(r'[^a-zA-Z0-9_-]+', '-', root.name).strip('-')[:64] or 'kristal'
    run_id = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
    control = output_base / f'{slug}-{run_id}'
    control.mkdir(parents=True, exist_ok=False)

    before = _fingerprint(root)
    argv = [sys.executable, str(entry), 'conform', str(root), '--profile', profile,
            '--control-dir', str(control), '--json']
    completed_code = None
    timed_out = False
    with tempfile.TemporaryDirectory(prefix='kristal-manager-diag-output-') as td:
        stdout_path = Path(td) / 'stdout.txt'
        stderr_path = Path(td) / 'stderr.txt'
        with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
            try:
                process = subprocess.run(argv, cwd=str(entry.parent), stdin=subprocess.DEVNULL,
                                         stdout=stdout, stderr=stderr, shell=False,
                                         timeout=timeout, check=False)
                completed_code = process.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
        stdout_text, out_truncated = _read_bounded(stdout_path, MAX_OUTPUT_BYTES)
        stderr_text, err_truncated = _read_bounded(stderr_path, MAX_OUTPUT_BYTES)

    summary = None
    current = control / 'current'
    summary_path = current / 'summary.json'
    if summary_path.is_file() and not summary_path.is_symlink() and summary_path.stat().st_size <= MAX_REPORT_BYTES:
        try:
            summary = json.loads(summary_path.read_text(encoding='utf-8'))
        except (ValueError, UnicodeError, OSError):
            pass
    if summary is None and not out_truncated:
        try:
            summary = json.loads(stdout_text)
        except (ValueError, UnicodeError):
            pass
    # Do not trust malformed or unrelated text as a real KristalDiag verdict.
    if not (isinstance(summary, dict) and summary.get('schema') == 'kristaldiag.summary.v1'
            and summary.get('tool') == 'KristalDiag'
            and Path(str(summary.get('target_root', ''))).resolve() == root
            and summary.get('profile') == profile):
        summary = None

    after = _fingerprint(root)
    status = ('TIMEOUT' if timed_out else 'EXECUTED_EXIT_0' if completed_code == 0 else 'EXECUTED_NONZERO')
    return {
        'format': 'kristal.manager-kristaldiag/1.0',
        'engine': 'KristalDiag (source fourni, intégré au Manager)',
        'executed_at': _utc_now(),
        'workspace': str(root), 'profile': profile,
        'program': str(entry), 'process_status': status, 'returncode': completed_code,
        'external_report': summary, 'verdict': summary.get('verdict') if summary else None,
        'counts': summary.get('counts', {}) if summary else {},
        'findings': _extract_official_findings(current, summary) if summary else [],
        'evidence_directory': str(control),
        'stdout_excerpt': stdout_text[:10000], 'stderr_excerpt': stderr_text[:10000],
        'output_truncated': out_truncated or err_truncated,
        'input_fingerprint': before, 'input_changed_during_run': before != after,
        'qualification': 'NOT_ESTABLISHED', 'attestation': 'NOT_VERIFIED',
        'limitations': [
            'Le verdict est celui de KristalDiag pour le profil choisi, pas une qualification C1 signée.',
            'KristalDiag fourni cible Framework 10.0.0-draft.3.1, et non Framework v11.',
            'Aucun droit de publication, accès ou activation n’est accordé.',
            'La comparaison de mutations ne couvre que des fichiers d’état connus.',
        ],
    }
