import datetime,hashlib,json,os,pathlib,shutil,subprocess,sys
root=pathlib.Path('C:/Users/benja/sol-cloud-exposure16-r5')
job='sol-cloud-exposure16-r5-s0-benspc'
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
result={'schema':'sol.cloud.exposure16.read-only-postmortem.v1','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runtime':list(sys.version_info[:3]),'root_exists':root.is_dir(),'PC_writes':0,'model_calls':0,'optimizer_updates_by_collector':0,'disk_free_bytes':shutil.disk_usage('C:/').free}
package=root/'PACKAGE.json'
result['package_sha256']=sha(package) if package.is_file() else None
result['payload_sha256']=sha(root/'payload.tar.gz') if (root/'payload.tar.gz').is_file() else None
result['shared_claim_exists']=pathlib.Path('C:/Users/benja/claims/sol-cloud-exposure16-r5-s0').is_dir()
busy=pathlib.Path('C:/Users/benja/GPU-BUSY.txt');result['GPU_busy_exists']=busy.is_file();result['GPU_busy_matches_source_job']=busy.is_file() and busy.stat().st_size<1024 and ('queue job '+job+' since ') in busy.read_text(encoding='utf8')
files=[]
if package.is_file():
 assert package.stat().st_size<65536
 p=json.loads(package.read_text(encoding='utf8'));missing=[];bad=[]
 for rel,digest in p['files'].items():
  path=root/rel;assert path.resolve().is_relative_to(root.resolve()) and not path.is_symlink()
  if not path.is_file():missing.append(rel)
  elif sha(path)!=digest:bad.append(rel)
 result['package_declared_files']=len(p['files']);result['missing_declared_files']=missing;result['mismatched_declared_files']=bad
 own=root/'artifacts/sol-cloud-exposure16-20260930/r5';dep=root/'artifacts/sol-cloud-coordinator-20260930/integration/exposure16-r5-v1'
 for folder in [own/'runs',dep]:
  if folder.exists():
   for path in folder.rglob('*'):
    if path.is_file():
     assert path.resolve().is_relative_to(root.resolve()) and not path.is_symlink();files.append({'relative':str(path.relative_to(root)).replace('\\','/'),'bytes':path.stat().st_size,'sha256':sha(path)})
 result['saved_run_and_deployment_files']=files
 for rel in ['artifacts/sol-cloud-exposure16-20260930/r5/TRANSPORT-s0.json','artifacts/sol-cloud-exposure16-20260930/r5/worker-stdout-s0.log']:
  path=root/rel
  result[rel]=({'exists':True,'bytes':path.stat().st_size,'sha256':sha(path),'bounded_saved_text':path.read_text(encoding='utf8')[-12000:]} if path.is_file() and path.stat().st_size<1048576 else {'exists':path.exists()})
 plan=own/'PLAN.json';closure=dep/'SOURCE-CLOSURE.json'
 if plan.is_file() and closure.is_file():
  plan=json.loads(plan.read_text(encoding='utf8'));closure=json.loads(closure.read_text(encoding='utf8'));tuples=[]
  for s in ['0','1']:
   for key in ['parent','reader','adapter']:
    t=plan['warmstart']['tuples'][s];path=pathlib.Path(t[key+'_path']);tuples.append({'seed':int(s),'role':key,'exists':path.is_file(),'sha_matches':path.is_file() and sha(path)==t[key+'_sha256']==closure[s]['tuple_sha256'][key]})
  result['V11_tuple_status']=tuples
command=['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe'} | Select-Object ProcessId,ParentProcessId,Name | ConvertTo-Json -Compress"]
r=subprocess.run(command,capture_output=True,text=True,timeout=20,check=True);rows=json.loads(r.stdout or '[]');result['python_processes']=[rows] if isinstance(rows,dict) else rows;result['collector_PID']=os.getpid()
r=subprocess.run(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10,check=True);result['GPU_compute_PIDs']=[int(x) for x in r.stdout.split() if x.isdigit()];result['GPU_compute_output_empty']=not r.stdout.strip();result['GPU_compute_output_has_non_numeric_text']=any(not x.isdigit() for x in r.stdout.split())
r=subprocess.run(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10,check=True);result['gpus']=[[int(v.strip()) for v in line.split(',')] for line in r.stdout.strip().splitlines()]
print(json.dumps(result,sort_keys=True),flush=True)
