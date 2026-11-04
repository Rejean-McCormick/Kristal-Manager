"""The legacy publication backend is absent: these operations MUST fail closed.

Unlike historical acceptance tests, these checks assert the delivered behavior.
They do not qualify any future restored backend, sync, or C1/C2/C3 process.
"""
import pytest
from kristal_manager import core


@pytest.mark.parametrize('name', [
    'migrate_local',
    'prepare_publication_request',
    'prepare_github_read_surface',
    'sync_local_to_github',
    'sync_entries_batch',
    '_sync_prepared_collection',
    'backup_local',
    'resolve_publication_collection',
    'ensure_collection_checkout',
    'github_remote_json_file',
    '_apply_prepared_surface',
    '_build_collection_index',
    'ensure_backup_repo',
])
def test_unrestored_legacy_operation_fails_closed(name, tmp_path):
    before = set(tmp_path.iterdir())
    with pytest.raises(core.ManagerError, match='blocked: the previous operational backend is missing'):
        getattr(core, name)(tmp_path, workspace_root=tmp_path)
    assert set(tmp_path.iterdir()) == before
