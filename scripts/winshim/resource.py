"""Windows stand-in for the Unix-only `resource` module (month-end line, 2026-09-24).

fable_reasoner50 imports `resource` only to log peak memory (getrusage(...).ru_maxrss). On Windows
the month-end runners put this folder first on sys.path, so that import works and the logged
peak memory reads 0. Nothing else is imitated. Linux and macOS never load this file.
"""
from types import SimpleNamespace

RUSAGE_SELF = 0
RUSAGE_CHILDREN = -1


def getrusage(who=RUSAGE_SELF):
    return SimpleNamespace(ru_maxrss=0, ru_utime=0.0, ru_stime=0.0)
