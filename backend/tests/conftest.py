"""Isolates the test suite from the real dev database.

`app.config` / `app.db` resolve DATA_DIR/DB_PATH at import time, so
RESUME_DATA_DIR must point at a temp dir BEFORE any app module is
imported. pytest imports this conftest before the test modules, which
guarantees pytest never touches backend/data/resume.db.
"""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="resume_test_")
os.environ["RESUME_DATA_DIR"] = _tmp
