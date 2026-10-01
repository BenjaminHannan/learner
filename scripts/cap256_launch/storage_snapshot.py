"""Conservative allocation snapshot across known bounded atomic renames.

Unknown disappearances and genuine I/O errors fail closed. A vanished known
receipt/checkpoint name reserves its full maximum size, even if that double
counts a promoted destination. Callers retain prospective atomic-save peaks.
"""
import stat
from pathlib import Path

RECEIPT_RESERVATION_BYTES=1048576
CHECKPOINT_RESERVATION_BYTES=134217728


def vanished_reservation(path):
    path=Path(path)
    components=path.parts
    if 'launch-cap256' in components and 'mixtures' in components:
        for name in ('BATCH.json','PROGRESS.json'):
            if path.name==name or path.name.startswith(name+'.tmp'):
                return RECEIPT_RESERVATION_BYTES
    if 'artifacts' in components and path.name.endswith('.pt.tmp'):
        return CHECKPOINT_RESERVATION_BYTES
    raise FileNotFoundError('unbounded entry disappeared during storage snapshot: '+str(path))


def allocated_bytes(directory,unit,*,include=None,reservation=vanished_reservation):
    directory=Path(directory)
    if not directory.exists():return 0
    total=0
    for path in directory.rglob('*'):
        if include is not None and not include(path):continue
        try:info=path.stat()
        except FileNotFoundError:
            size=reservation(path)
            total+=((size+unit-1)//unit)*unit
            continue
        if stat.S_ISREG(info.st_mode):total+=((info.st_size+unit-1)//unit)*unit
    return total


def raw_allocated_bytes(directory,unit):
    # Receipt temporaries remain raw evidence. Only model-save paths excluded.
    return allocated_bytes(directory,unit,include=lambda p:not (p.name.endswith('.pt') or p.name.endswith('.pt.tmp')))
