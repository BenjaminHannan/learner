import json,hashlib,shutil,subprocess
from pathlib import Path
root=Path('C:/Users/benja/sol-cloud-numeric-capability-v1')
def alloc(p):return sum(((f.stat().st_size+4095)//4096)*4096 for f in p.rglob('*') if f.is_file())
namespace='artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1'
parents=[]
for seed in (0,1):
 p=root/namespace/'run-capability256-continuation40-v1'/('seed%d'%seed)/'loop/final-resume.pt'
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 parents.append({'seed':seed,'bytes':p.stat().st_size,'allocated_bytes':((p.stat().st_size+4095)//4096)*4096,'sha256':h.hexdigest()})
rows=[]
for batch,matrix in [('cap256-mixture10240-20261001T051720Z','run-capability256-mixture10240-v1'),('cap256-mixture10240-retry-v5-20261001T054435Z','run-capability256-mixture10240-retry-v5')]:
 d=root/'launch-cap256/mixtures'/batch;m=root/namespace/matrix
 raw=m/'seed0/repeat256/TRAIN-RAW.jsonl'
 first=last=None
 with raw.open('rb') as f:
  for line in f:
   if not line.endswith(b'\n'):continue
   r=json.loads(line)
   if first is None:first=r
   last=r
 timing={k:v for k,v in (last or {}).items() if any(t in k.lower() for t in ('second','elapsed','utc','runtime'))}
 rows.append({'last_raw_timing':timing,'first_raw_timing':{k:v for k,v in (first or {}).items() if any(t in k.lower() for t in ('second','elapsed','utc','runtime'))},'batch':batch,'batchdir_creation_epoch':d.stat().st_ctime,'receipt_allocated_bytes':alloc(d),'model_output_allocated_bytes':alloc(m),'retained_checkpoints':[str(p.relative_to(root)) for p in m.rglob('*.pt')],'dev_receipts_present':(m/'dev32').exists()})
ps="Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'mixture.*pc_driver.py|train_mixture.*--root|eval_mixture.*--root' } | Select-Object ProcessId,Name | ConvertTo-Json -Compress"
proc=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',ps],capture_output=True,text=True,check=True)
# The probing PowerShell command itself contains the search text; filter it.
live=json.loads(proc.stdout) if proc.stdout.strip() else []
if isinstance(live,dict):live=[live]
live=[p for p in live if p['Name'].lower()!='powershell.exe']
gpu=subprocess.run(['nvidia-smi','--query-gpu=memory.used,memory.total,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True).stdout.strip()
result={'schema':'cap256.receipt-repair.resource-snapshot.v1','model_calls':0,'parents':parents,'failed_attempts':rows,'project_allocated_bytes':alloc(root),'free_bytes':shutil.disk_usage(root).free,'lock_exists':(root/'launch-cap256/LOCK.json').exists(),'matching_owned_processes':live,'gpu_memory_used_total_utilization':gpu,'probe_allocated_bytes':sum(alloc(p) for p in (root/'launch-cap256').glob('receipt-repair-probe-*'))}
print(json.dumps(result,sort_keys=True))
