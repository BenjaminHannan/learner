"""Windows compatibility shim for hands-toy/policy.py's unused resource import.

policy.py imports resource at module load and only calls getrusage in its own
train() entrypoint, which the HANDS native-action head never uses. Packed onto
BensPC as <job>/src/resource.py so the unmodified policy file imports there.
"""
RUSAGE_SELF = 0


class _Usage:
    ru_maxrss = 0


def getrusage(*_args, **_kwargs):
    return _Usage()
