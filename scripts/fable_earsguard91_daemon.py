"""Exp 91 -- daemon launcher with GuardedEars plugged in via the build_ears hook.

Same CLI as scripts/fable_daemon74_run.py (--dir, --idle-seconds,
--sleep-threshold). The ONLY difference: the daemon's build_ears hook is
wrapped so the loop hears through GuardedEars(FakeEars()). Neither
scripts/fable_daemon74_run.py nor any other existing file is edited.

Launch (Mac CPU, offline):

  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_earsguard91_daemon.py --dir DIR
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_daemon74_run as D  # noqa: E402 (read-only import, never edited)
from fable_earsguard91 import GuardedEars  # noqa: E402

_ORIG_BUILD_EARS = D.build_ears


def _guarded_build_ears(ears=None):
    inner = _ORIG_BUILD_EARS(None) if ears is None else ears
    if isinstance(inner, GuardedEars):
        return inner
    return GuardedEars(inner)


D.build_ears = _guarded_build_ears  # the daemon's own plug-in point, used as documented


def main(argv=None) -> int:
    return D.main(argv)


if __name__ == "__main__":
    sys.exit(main())
