"""Regressions des deux protections C2 repris du Bootstrap existant."""
from pathlib import Path
import pytest
from test_c2_public_gate import setup
from kristal_manager.publication_gate import PublicGateError, candidate_rows


def test_same_signing_key_for_both_roles_is_rejected(tmp_path):
    src, trust_root, grant, qual, check, write, signed, approver, qualifier = setup(tmp_path)
    import json
    trust = json.loads((trust_root / 'trust.json').read_text(encoding='utf-8'))
    trust['qualifier_public_key'] = trust['approver_public_key']
    write('trust.json', trust)
    with pytest.raises(PublicGateError, match='different trusted keys'):
        check()


def test_intermediate_symlink_inside_workspace_is_rejected(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    folder = source / 'original'
    folder.mkdir()
    (folder / 'data.json').write_text('{}', encoding='utf-8')
    try:
        (source / 'alias').symlink_to(folder, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip('symlinks non disponibles sans privileges sur Windows')
    with pytest.raises(PublicGateError, match='Symlinked candidate'):
        candidate_rows(source, ['alias/data.json'])


def test_noncanonical_alias_of_same_ed25519_public_key_is_rejected(tmp_path, monkeypatch):
    src, trust_root, grant, qual, check, write, signed, approver, qualifier = setup(tmp_path)
    import base64
    import json
    from kristal_manager.publication_gate import canonical, sha256
    trust = json.loads((trust_root / 'trust.json').read_text(encoding='utf-8'))
    original = trust['approver_public_key']
    # A 32-byte Ed25519 key finishes with one '='. The last data sextet has
    # two non-significant bits; changing them does not change decoded bytes.
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    old = alphabet.index(original[-2])
    alias = original[:-2] + alphabet[old ^ 1] + '='
    assert alias != original
    assert base64.b64decode(alias) == base64.b64decode(original)
    trust['qualifier_public_key'] = alias
    write('trust.json', trust)
    monkeypatch.setenv('KRISTAL_C2_TRUST_PIN', sha256(canonical(trust)))
    with pytest.raises(PublicGateError, match='canonical Ed25519 base64'):
        check()
