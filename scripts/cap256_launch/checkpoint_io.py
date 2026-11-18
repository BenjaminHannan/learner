"""Reserve atomic checkpoint peak once; retain bounded extent/free checks."""
from pathlib import Path


def save_reserved(path,allowance,serialize,save_atomic,guard,free_bytes,reserve_bytes,unit,metadata_reserve=16*1024**2):
    path=Path(path)
    guard(allowance+metadata_reserve+unit)
    temporary=path.with_suffix(path.suffix+'.tmp')
    def before_extent(extent):
        if extent>allowance:raise RuntimeError('checkpoint exceeds reserved extent')
        existing=temporary.stat().st_size if temporary.exists() else 0
        if free_bytes()-max(0,extent-existing)<reserve_bytes:raise RuntimeError('checkpoint free reserve exceeded')
    save_atomic(path,allowance,serialize,before_extent)
    guard()
    return path
