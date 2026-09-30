"""Explicit Ben-authorized one Qwen GGUF removal through an exclusive native handle."""
import ctypes
from ctypes import wintypes as w
import datetime
import json
import ntpath
from pathlib import Path
import platform
import shutil
import subprocess
import sys

TARGET = Path('C:/Users/benja/.lmstudio/models/Qwen3.8-27B/Qwen3.8-27B-UD-IQ4_XS.gguf')

def run(expected):
    if platform.system() != 'Windows' or sys.version_info[:3] != (3,10,9):
        raise RuntimeError('Verified native PC3.10.9 required')
    if expected['path'] != str(TARGET) or expected['bytes'] != 14252845984 or expected['nlink'] != 1:
        raise RuntimeError('Exact approved single-file metadata required')
    command = "Get-CimInstance Win32_Process | Where-Object {$_.Name -match '(?i)^(LM Studio|lmstudio|lms|llm-engine|llama-server|llama-cli)\\.exe$'} | Select-Object ProcessId,Name | ConvertTo-Json -Compress"
    process = subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',command],capture_output=True,timeout=12)
    if process.returncode or len(process.stdout)>65536:
        raise RuntimeError('Current model-process query failed; file preserved')
    active = json.loads(process.stdout.decode('utf-8-sig') or '[]')
    active = [active] if isinstance(active,dict) else active
    if not isinstance(active,list) or active:
        raise RuntimeError('LM model process active or unknown; file preserved')
    before = TARGET.stat()
    stamp = {'bytes':before.st_size,'file_id':{'device':before.st_dev,'inode':before.st_ino},'nlink':before.st_nlink,
             'mtime_utc':datetime.datetime.fromtimestamp(before.st_mtime,datetime.timezone.utc).isoformat()}
    if TARGET.is_symlink() or any(stamp[k] != expected[k] for k in stamp):
        raise RuntimeError('Original file identity differs; preserved')
    class Info(ctypes.Structure):
        _fields_=[('attributes',w.DWORD),('created',w.FILETIME),('accessed',w.FILETIME),('written',w.FILETIME),
                  ('volume',w.DWORD),('size_high',w.DWORD),('size_low',w.DWORD),('links',w.DWORD),('index_high',w.DWORD),('index_low',w.DWORD)]
    class Disposition(ctypes.Structure):
        _fields_=[('DeleteFile',w.BOOL)]
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,w.LPVOID,w.DWORD,w.DWORD,w.HANDLE];k.CreateFileW.restype=w.HANDLE
    k.GetFileInformationByHandle.argtypes=[w.HANDLE,ctypes.POINTER(Info)];k.GetFileInformationByHandle.restype=w.BOOL
    k.GetFinalPathNameByHandleW.argtypes=[w.HANDLE,w.LPWSTR,w.DWORD,w.DWORD];k.GetFinalPathNameByHandleW.restype=w.DWORD
    k.SetFileInformationByHandle.argtypes=[w.HANDLE,ctypes.c_int,w.LPVOID,w.DWORD];k.SetFileInformationByHandle.restype=w.BOOL
    k.CloseHandle.argtypes=[w.HANDLE];k.CloseHandle.restype=w.BOOL
    # ShareMode0 refuses every existing/open file handle. DELETE+attributes only: no tensor read.
    handle=k.CreateFileW(str(TARGET),0x10000|0x80,0,None,3,0x00200000,None)
    if handle==ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    marked=False
    try:
        info=Info()
        if not k.GetFileInformationByHandle(handle,ctypes.byref(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        native_id={'device':int(info.volume),'inode':(int(info.index_high)<<32)|int(info.index_low)}
        native_size=(int(info.size_high)<<32)|int(info.size_low)
        if native_id!=expected['file_id'] or native_size!=expected['bytes'] or info.links!=1 or info.attributes&0x400:
            raise RuntimeError('Exclusive native handle identity/reparse differs; preserved')
        final=ctypes.create_unicode_buffer(32768);length=k.GetFinalPathNameByHandleW(handle,final,len(final),0)
        if not 0<length<len(final) or ntpath.normcase(ntpath.normpath(final.value.removeprefix('\\\\?\\')))!=ntpath.normcase(ntpath.normpath(str(TARGET))):
            raise RuntimeError('Exclusive native final path differs; preserved')
        free_before=shutil.disk_usage('C:/').free
        print(json.dumps({'schema':'sol.cloud.approved-Qwen-removal.v1','phase':'before-delete','approved_by':'Ben',
                          'path':str(TARGET),'original_stat':stamp,'native_handle_file_id':native_id,'bytes':native_size,
                          'exclusive_handle_share_mode':0,'model_processes':active,'C_free_bytes':free_before,
                          'tensor_content_bytes_read':0,'pip_cache_touched':False,'other_files_deleted':0},sort_keys=True),flush=True)
        disposition=Disposition(True)
        # Native same-handle disposition closes the identity/use check-to-action race; mapped-file refusal stays a failure.
        if not k.SetFileInformationByHandle(handle,4,ctypes.byref(disposition),ctypes.sizeof(disposition)):
            raise ctypes.WinError(ctypes.get_last_error())
        marked=True
    finally:
        if not k.CloseHandle(handle):
            raise ctypes.WinError(ctypes.get_last_error())
    gone=not TARGET.exists();free_after=shutil.disk_usage('C:/').free
    print(json.dumps({'schema':'sol.cloud.approved-Qwen-removal.v1','phase':'after-delete','approved_by':'Ben','path':str(TARGET),
                      'disposition_marked':marked,'target_absent':gone,'C_free_before_bytes':free_before,'C_free_after_bytes':free_after,
                      'free_increase_bytes':free_after-free_before,'deletion_count':1 if gone else 0,'pip_cache_touched':False,
                      'other_models_or_evidence_touched':False,'model_calls':0,'optimizer_updates':0},sort_keys=True),flush=True)
    return 0 if gone else 1
