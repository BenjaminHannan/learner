# Tests must never touch Ben's real app folder (~/Library/Application Support/Premonition). A Recipe built with
# Paths(user_data=None) used to fall back to it, and test runs appended empty lines to his truthcheck-log.jsonl
# (2026-11-04 and 2026-11-05). Every test run now gets a throwaway folder instead.
import tempfile as _tempfile
from pathlib import Path as _Path

_TEST_USERDATA = _Path(_tempfile.mkdtemp(prefix="sleepmlx-test-userdata-"))

from .. import lessons as _lessons  # noqa: E402

_lessons.default_user_data = lambda: _TEST_USERDATA
