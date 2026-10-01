"""Read-only allocation snapshot tolerant of concurrently renamed entries.

The caller must retain its prospective-write/atomic-save allowances. This is
an ordinary filesystem snapshot, not a promise of a transactional inventory.
"""
import stat
from pathlib import Path


def allocated_bytes(directory,unit):
    directory=Path(directory)
    if not directory.exists():return 0
    total=0
    for path in directory.rglob('*'):
        try:info=path.stat()
        except FileNotFoundError:
            # A monitor's atomic rename can remove a just-enumerated name.
            continue
        if stat.S_ISREG(info.st_mode):total+=((info.st_size+unit-1)//unit)*unit
    return total
