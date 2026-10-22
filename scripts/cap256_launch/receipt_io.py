"""Durable JSON receipts with bounded Windows sharing retries.

Successful replacements preserve atomic readers. Failed unique temporaries are
retained as evidence. Only Windows access/sharing/lock errors from replacement
are retried, briefly and without random jitter; all other I/O errors propagate.
"""
import itertools
import json
import os
from pathlib import Path
import time

_serial=itertools.count()
MAX_RECEIPT_BYTES=1048576
REPLACE_WAIT_SECONDS=1.0
RETRY_INTERVAL_SECONDS=.02
TRANSIENT_WINDOWS_ERRORS=frozenset((5,32,33))


def write_json(path,record,exclusive=False,*,timeout=REPLACE_WAIT_SECONDS):
    if not 0<=timeout<=REPLACE_WAIT_SECONDS:raise ValueError('bounded receipt replacement timeout')
    path=Path(path)
    raw=(json.dumps(record,sort_keys=True,indent=2,default=str,allow_nan=False)+'\n').encode('utf8')
    if len(raw)>MAX_RECEIPT_BYTES:raise ValueError('receipt exceeds reserved 1 MiB')
    if exclusive:
        with path.open('xb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        return {'replace_retries':0,'exclusive':True}
    temporary=path.with_name(path.name+'.tmp-%d-%d-%d'%(os.getpid(),time.monotonic_ns(),next(_serial)))
    with temporary.open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    deadline=time.monotonic()+timeout;errors=[]
    while True:
        try:os.replace(temporary,path)
        except OSError as error:
            if getattr(error,'winerror',None) not in TRANSIENT_WINDOWS_ERRORS:raise
            remaining=deadline-time.monotonic()
            if remaining<=0:raise
            errors.append(error.winerror)
            time.sleep(min(RETRY_INTERVAL_SECONDS,remaining))
        else:return {'replace_retries':len(errors),'windows_errors':errors,'exclusive':False}


def read_json(path):
    """On Windows allow an atomic writer to replace a file while it is read."""
    if os.name!='nt':return json.loads(Path(path).read_bytes())
    import ctypes
    from ctypes import wintypes
    import msvcrt
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    create=kernel.CreateFileW
    create.argtypes=(wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE)
    create.restype=wintypes.HANDLE
    close=kernel.CloseHandle;close.argtypes=(wintypes.HANDLE,);close.restype=wintypes.BOOL
    handle=create(str(Path(path)),0x80000000,1|2|4,None,3,0x80,None)
    if handle==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
    try:fd=msvcrt.open_osfhandle(handle,os.O_RDONLY|os.O_BINARY)
    except BaseException:close(handle);raise
    try:stream=os.fdopen(fd,'rb')
    except BaseException:os.close(fd);raise
    with stream:return json.loads(stream.read())


def write_terminal_failure(path,record):
    """Try mutable status once, then a unique immutable failure receipt.

    Call only after stopping the owned worker. A genuine filesystem failure
    of the fallback still propagates; no claim that unwritable storage works.
    """
    try:return write_json(path,record)
    except OSError as error:
        fallback=Path(path).with_name('FATAL-%d-%d-%d.json'%(os.getpid(),time.monotonic_ns(),next(_serial)))
        return write_json(fallback,{**record,'terminal_receipt_error':repr(error)},exclusive=True)
