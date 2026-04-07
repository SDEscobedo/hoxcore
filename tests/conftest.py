import os
import stat
import sys
import shutil
from pathlib import Path

import pytest

# Add the src directory to the Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def _remove_readonly(func, path, excinfo):
    """
    Error handler for shutil.rmtree on Windows.

    Git marks object files inside .git/objects/ as read-only after writing
    them. On Windows, shutil.rmtree cannot delete read-only files, so pytest's
    tmp_path teardown raises PermissionError: [WinError 5].

    This handler clears the read-only bit and retries the failed operation.
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)


@pytest.fixture(autouse=True)
def _patch_tmp_path_cleanup(tmp_path_factory, monkeypatch):
    """
    Ensure temporary directories are removed safely on all platforms.

    Replaces shutil.rmtree with a version that always passes the
    _remove_readonly error handler, preventing PermissionError failures
    during teardown on Windows when .git directories are present.
    """
    original_rmtree = shutil.rmtree

    def safe_rmtree(path, ignore_errors=False, onerror=None, **kwargs):
        # If the caller already supplied an error handler, respect it.
        # Otherwise inject our read-only fix so Windows .git cleanup works.
        if onerror is None and not ignore_errors:
            onerror = _remove_readonly
        return original_rmtree(path, ignore_errors=ignore_errors, onerror=onerror, **kwargs)

    monkeypatch.setattr(shutil, "rmtree", safe_rmtree)