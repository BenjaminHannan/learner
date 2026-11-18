
import base64,ctypes,hashlib,importlib.util,json,os,random,threading,time
from pathlib import Path
from ctypes import wintypes
root=Path('C:/Users/benja/sol-cloud-numeric-capability-v1')
scratch=root/'launch-cap256/receipt-repair-probe-20261001-v2'
scratch.mkdir(exist_ok=False)
source=base64.b64decode('IiIiRHVyYWJsZSBKU09OIHJlY2VpcHRzIHdpdGggYm91bmRlZCBXaW5kb3dzIHNoYXJpbmcgcmV0cmllcy4KClN1Y2Nlc3NmdWwgcmVwbGFjZW1lbnRzIHByZXNlcnZlIGF0b21pYyByZWFkZXJzLiBGYWlsZWQgdW5pcXVlIHRlbXBvcmFyaWVzIGFyZQpyZXRhaW5lZCBhcyBldmlkZW5jZS4gT25seSBXaW5kb3dzIGFjY2Vzcy9zaGFyaW5nL2xvY2sgZXJyb3JzIGZyb20gcmVwbGFjZW1lbnQKYXJlIHJldHJpZWQsIGJyaWVmbHkgYW5kIHdpdGhvdXQgcmFuZG9tIGppdHRlcjsgYWxsIG90aGVyIEkvTyBlcnJvcnMgcHJvcGFnYXRlLgoiIiIKaW1wb3J0IGl0ZXJ0b29scwppbXBvcnQganNvbgppbXBvcnQgb3MKZnJvbSBwYXRobGliIGltcG9ydCBQYXRoCmltcG9ydCB0aW1lCgpfc2VyaWFsPWl0ZXJ0b29scy5jb3VudCgpCk1BWF9SRUNFSVBUX0JZVEVTPTEwNDg1NzYKUkVQTEFDRV9XQUlUX1NFQ09ORFM9MS4wClJFVFJZX0lOVEVSVkFMX1NFQ09ORFM9LjAyClRSQU5TSUVOVF9XSU5ET1dTX0VSUk9SUz1mcm96ZW5zZXQoKDUsMzIsMzMpKQoKCmRlZiB3cml0ZV9qc29uKHBhdGgscmVjb3JkLGV4Y2x1c2l2ZT1GYWxzZSwqLHRpbWVvdXQ9UkVQTEFDRV9XQUlUX1NFQ09ORFMpOgogICAgaWYgbm90IDA8PXRpbWVvdXQ8PVJFUExBQ0VfV0FJVF9TRUNPTkRTOnJhaXNlIFZhbHVlRXJyb3IoJ2JvdW5kZWQgcmVjZWlwdCByZXBsYWNlbWVudCB0aW1lb3V0JykKICAgIHBhdGg9UGF0aChwYXRoKQogICAgcmF3PShqc29uLmR1bXBzKHJlY29yZCxzb3J0X2tleXM9VHJ1ZSxpbmRlbnQ9MixkZWZhdWx0PXN0cixhbGxvd19uYW49RmFsc2UpKydcbicpLmVuY29kZSgndXRmOCcpCiAgICBpZiBsZW4ocmF3KT5NQVhfUkVDRUlQVF9CWVRFUzpyYWlzZSBWYWx1ZUVycm9yKCdyZWNlaXB0IGV4Y2VlZHMgcmVzZXJ2ZWQgMSBNaUInKQogICAgaWYgZXhjbHVzaXZlOgogICAgICAgIHdpdGggcGF0aC5vcGVuKCd4YicpIGFzIHN0cmVhbToKICAgICAgICAgICAgc3RyZWFtLndyaXRlKHJhdyk7c3RyZWFtLmZsdXNoKCk7b3MuZnN5bmMoc3RyZWFtLmZpbGVubygpKQogICAgICAgIHJldHVybiB7J3JlcGxhY2VfcmV0cmllcyc6MCwnZXhjbHVzaXZlJzpUcnVlfQogICAgdGVtcG9yYXJ5PXBhdGgud2l0aF9uYW1lKHBhdGgubmFtZSsnLnRtcC0lZC0lZC0lZCclKG9zLmdldHBpZCgpLHRpbWUubW9ub3RvbmljX25zKCksbmV4dChfc2VyaWFsKSkpCiAgICB3aXRoIHRlbXBvcmFyeS5vcGVuKCd4YicpIGFzIHN0cmVhbToKICAgICAgICBzdHJlYW0ud3JpdGUocmF3KTtzdHJlYW0uZmx1c2goKTtvcy5mc3luYyhzdHJlYW0uZmlsZW5vKCkpCiAgICBkZWFkbGluZT10aW1lLm1vbm90b25pYygpK3RpbWVvdXQ7ZXJyb3JzPVtdCiAgICB3aGlsZSBUcnVlOgogICAgICAgIHRyeTpvcy5yZXBsYWNlKHRlbXBvcmFyeSxwYXRoKQogICAgICAgIGV4Y2VwdCBPU0Vycm9yIGFzIGVycm9yOgogICAgICAgICAgICBpZiBnZXRhdHRyKGVycm9yLCd3aW5lcnJvcicsTm9uZSkgbm90IGluIFRSQU5TSUVOVF9XSU5ET1dTX0VSUk9SUzpyYWlzZQogICAgICAgICAgICByZW1haW5pbmc9ZGVhZGxpbmUtdGltZS5tb25vdG9uaWMoKQogICAgICAgICAgICBpZiByZW1haW5pbmc8PTA6cmFpc2UKICAgICAgICAgICAgZXJyb3JzLmFwcGVuZChlcnJvci53aW5lcnJvcikKICAgICAgICAgICAgdGltZS5zbGVlcChtaW4oUkVUUllfSU5URVJWQUxfU0VDT05EUyxyZW1haW5pbmcpKQogICAgICAgIGVsc2U6cmV0dXJuIHsncmVwbGFjZV9yZXRyaWVzJzpsZW4oZXJyb3JzKSwnd2luZG93c19lcnJvcnMnOmVycm9ycywnZXhjbHVzaXZlJzpGYWxzZX0KCgpkZWYgcmVhZF9qc29uKHBhdGgpOgogICAgIiIiT24gV2luZG93cyBhbGxvdyBhbiBhdG9taWMgd3JpdGVyIHRvIHJlcGxhY2UgYSBmaWxlIHdoaWxlIGl0IGlzIHJlYWQuIiIiCiAgICBpZiBvcy5uYW1lIT0nbnQnOnJldHVybiBqc29uLmxvYWRzKFBhdGgocGF0aCkucmVhZF9ieXRlcygpKQogICAgaW1wb3J0IGN0eXBlcwogICAgZnJvbSBjdHlwZXMgaW1wb3J0IHdpbnR5cGVzCiAgICBpbXBvcnQgbXN2Y3J0CiAgICBrZXJuZWw9Y3R5cGVzLldpbkRMTCgna2VybmVsMzInLHVzZV9sYXN0X2Vycm9yPVRydWUpCiAgICBjcmVhdGU9a2VybmVsLkNyZWF0ZUZpbGVXCiAgICBjcmVhdGUuYXJndHlwZXM9KHdpbnR5cGVzLkxQQ1dTVFIsd2ludHlwZXMuRFdPUkQsd2ludHlwZXMuRFdPUkQsd2ludHlwZXMuTFBWT0lELHdpbnR5cGVzLkRXT1JELHdpbnR5cGVzLkRXT1JELHdpbnR5cGVzLkhBTkRMRSkKICAgIGNyZWF0ZS5yZXN0eXBlPXdpbnR5cGVzLkhBTkRMRQogICAgY2xvc2U9a2VybmVsLkNsb3NlSGFuZGxlO2Nsb3NlLmFyZ3R5cGVzPSh3aW50eXBlcy5IQU5ETEUsKTtjbG9zZS5yZXN0eXBlPXdpbnR5cGVzLkJPT0wKICAgIGhhbmRsZT1jcmVhdGUoc3RyKFBhdGgocGF0aCkpLDB4ODAwMDAwMDAsMXwyfDQsTm9uZSwzLDB4ODAsTm9uZSkKICAgIGlmIGhhbmRsZT09Y3R5cGVzLmNfdm9pZF9wKC0xKS52YWx1ZTpyYWlzZSBjdHlwZXMuV2luRXJyb3IoY3R5cGVzLmdldF9sYXN0X2Vycm9yKCkpCiAgICB0cnk6ZmQ9bXN2Y3J0Lm9wZW5fb3NmaGFuZGxlKGhhbmRsZSxvcy5PX1JET05MWXxvcy5PX0JJTkFSWSkKICAgIGV4Y2VwdCBCYXNlRXhjZXB0aW9uOmNsb3NlKGhhbmRsZSk7cmFpc2UKICAgIHRyeTpzdHJlYW09b3MuZmRvcGVuKGZkLCdyYicpCiAgICBleGNlcHQgQmFzZUV4Y2VwdGlvbjpvcy5jbG9zZShmZCk7cmFpc2UKICAgIHdpdGggc3RyZWFtOnJldHVybiBqc29uLmxvYWRzKHN0cmVhbS5yZWFkKCkpCgoKZGVmIHdyaXRlX3Rlcm1pbmFsX2ZhaWx1cmUocGF0aCxyZWNvcmQpOgogICAgIiIiVHJ5IG11dGFibGUgc3RhdHVzIG9uY2UsIHRoZW4gYSB1bmlxdWUgaW1tdXRhYmxlIGZhaWx1cmUgcmVjZWlwdC4KCiAgICBDYWxsIG9ubHkgYWZ0ZXIgc3RvcHBpbmcgdGhlIG93bmVkIHdvcmtlci4gQSBnZW51aW5lIGZpbGVzeXN0ZW0gZmFpbHVyZQogICAgb2YgdGhlIGZhbGxiYWNrIHN0aWxsIHByb3BhZ2F0ZXM7IG5vIGNsYWltIHRoYXQgdW53cml0YWJsZSBzdG9yYWdlIHdvcmtzLgogICAgIiIiCiAgICB0cnk6cmV0dXJuIHdyaXRlX2pzb24ocGF0aCxyZWNvcmQpCiAgICBleGNlcHQgT1NFcnJvciBhcyBlcnJvcjoKICAgICAgICBmYWxsYmFjaz1QYXRoKHBhdGgpLndpdGhfbmFtZSgnRkFUQUwtJWQtJWQtJWQuanNvbiclKG9zLmdldHBpZCgpLHRpbWUubW9ub3RvbmljX25zKCksbmV4dChfc2VyaWFsKSkpCiAgICAgICAgcmV0dXJuIHdyaXRlX2pzb24oZmFsbGJhY2sseyoqcmVjb3JkLCd0ZXJtaW5hbF9yZWNlaXB0X2Vycm9yJzpyZXByKGVycm9yKX0sZXhjbHVzaXZlPVRydWUpCg==')
modulepath=scratch/'receipt_io.py';modulepath.write_bytes(source)
spec=importlib.util.spec_from_file_location('receipt_probe_io',modulepath);io=importlib.util.module_from_spec(spec);spec.loader.exec_module(io)
import torch
py_state=random.getstate();torch_state=torch.get_rng_state().clone()
assert not torch.cuda.is_initialized()
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.CreateFileW.argtypes=(wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE);k.CreateFileW.restype=wintypes.HANDLE
k.CloseHandle.argtypes=(wintypes.HANDLE,);k.CloseHandle.restype=wintypes.BOOL
k.GetFileAttributesW.argtypes=(wintypes.LPCWSTR,);k.GetFileAttributesW.restype=wintypes.DWORD
results={'schema':'cap256.receipt-io.probe.v1','scratch':str(scratch),'helper_sha256':hashlib.sha256(source).hexdigest(),'model_calls':0,'optimizer_updates':0}
quiet=scratch/'quiet.json';results['quiet_write']=io.write_json(quiet,{'case':'quiet'})
held=scratch/'sharing.json';io.write_json(held,{'case':'old'})
def hold(path):
 h=k.CreateFileW(str(path),0x80000000,1|2,None,3,0x80,None)
 if h==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
 return h
h=hold(held)
def release():time.sleep(.12);assert k.CloseHandle(h)
t=threading.Thread(target=release);t.start();started=time.monotonic();result=io.write_json(held,{'case':'released'});t.join()
results['released_hold']={**result,'elapsed_seconds':time.monotonic()-started,'valid':io.read_json(held)=={'case':'released'}}
assert result['replace_retries']>0 and results['released_hold']['valid']
persistent=scratch/'persistent.json';io.write_json(persistent,{'case':'original'})
h=hold(persistent);started=time.monotonic()
try:io.write_json(persistent,{'case':'must-not-publish'},timeout=.2)
except OSError as e:results['persistent_hold']={'winerror':e.winerror,'elapsed_seconds':time.monotonic()-started,'bounded_failure':True}
else:raise AssertionError('held target unexpectedly replaced')
finally:assert k.CloseHandle(h)
results['persistent_hold']['original_preserved']=io.read_json(persistent)=={'case':'original'}
failedtemps=list(scratch.glob('persistent.json.tmp-*'));results['persistent_hold']['failed_temporaries']=len(failedtemps)
assert len(failedtemps)==1 and json.loads(failedtemps[0].read_bytes())=={'case':'must-not-publish'}
shared=scratch/'concurrent.json';io.write_json(shared,{'writer':-1,'value':'x'*200})
errors=[];counts=[];stop=threading.Event();readcounts=[0]
def reader():
 try:
  while not stop.is_set():
   r=io.read_json(shared);assert isinstance(r['writer'],int) and r['value']=='x'*200;readcounts[0]+=1
 except BaseException as e:errors.append(repr(e))
def writer(w):
 try:
  for i in range(20):counts.append(io.write_json(shared,{'writer':w*100+i,'value':'x'*200})['replace_retries'])
 except BaseException as e:errors.append(repr(e))
r=threading.Thread(target=reader);r.start();ws=[threading.Thread(target=writer,args=(w,)) for w in (0,1)]
for t in ws:t.start()
for t in ws:t.join()
stop.set();r.join();assert not errors and len(counts)==40
fallback=scratch/'terminal.json';io.write_json(fallback,{'status':'running'});h=hold(fallback)
started=time.monotonic()
try:io.write_terminal_failure(fallback,{'status':'failed','owned_worker_stopped':True})
finally:assert k.CloseHandle(h)
failures=list(scratch.glob('FATAL-*.json'))
assert len(failures)==1 and io.read_json(failures[0])['status']=='failed' and io.read_json(fallback)['status']=='running'
results['terminal_fallback']={'elapsed_seconds':time.monotonic()-started,'immutable_failures':len(failures),'blocked_status_preserved':True}
results['concurrent']={'writes':len(counts),'reads':readcounts[0],'errors':errors,'max_replace_retries':max(counts),'final_complete_json':isinstance(io.read_json(shared)['writer'],int)}
old=root/'launch-cap256/mixtures/cap256-mixture10240-retry-v5-20261001T054435Z/BATCH.json'
attributes=k.GetFileAttributesW(str(old));results['failed_batch_attributes']={'raw':attributes,'readonly':bool(attributes&1),'original_failure_holder_identified':False}
results['python_rng_unchanged']=random.getstate()==py_state;results['torch_cpu_rng_unchanged']=torch.equal(torch_state,torch.get_rng_state());results['cuda_initialized']=torch.cuda.is_initialized()
assert results['python_rng_unchanged'] and results['torch_cpu_rng_unchanged'] and not results['cuda_initialized']
results['allocated_probe_bytes']=sum(((p.stat().st_size+4095)//4096)*4096 for p in scratch.rglob('*') if p.is_file())
io.write_json(scratch/'PROBE.json',results,exclusive=True)
print(json.dumps(results,sort_keys=True))
