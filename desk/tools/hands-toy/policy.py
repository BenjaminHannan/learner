"""HANDS local pixel policy. All fitting/export commands enforce sleep/idle gates.
No outside checkpoints, network, gameplay dataset, or real-brain call.
"""
import os,sys,json,time,hashlib,ctypes,datetime,zlib,base64,random,resource
from pathlib import Path
os.environ.setdefault('OMP_NUM_THREADS','1')
import numpy as np
import torch
from torch import nn
import torch.nn.functional as F
torch.set_num_threads(1)
TASKS=['click','drag','type','scroll','sparks']
KEYS=['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Space','Backspace','Enter','Tab']
class PixelPolicy(nn.Module):
 def __init__(self):
  super().__init__()
  self.encoder=nn.Sequential(nn.Conv2d(3,24,5,2,2),nn.ReLU(),nn.Conv2d(24,48,3,2,1),nn.ReLU(),nn.Conv2d(48,96,3,2,1),nn.ReLU(),nn.Conv2d(96,128,3,2,1),nn.ReLU())
  self.overview=nn.Sequential(nn.Flatten(),nn.Linear(128*6*10,512),nn.ReLU())
  self.detail=nn.Sequential(nn.Flatten(),nn.Linear(128*3*3,128),nn.ReLU())
  self.intent=nn.Embedding(16,64)
  self.memory=nn.GRUCell(512+128+64+12,512)
  self.head=nn.Linear(512,16) # dx/dy, buttons(2), keys(8), character gate, time-to-go, confidence, stop
 def forward(self,image,crop,intent,own,hidden=None):
  a=self.overview(F.adaptive_avg_pool2d(self.encoder(image),(6,10)))
  b=self.detail(F.adaptive_avg_pool2d(self.encoder(crop),(3,3)))
  h=self.memory(torch.cat([a,b,self.intent(intent),own],1),hidden)
  return self.head(h),h
class InverseDynamics(nn.Module):
 def __init__(self):
  super().__init__();self.encoder=nn.Sequential(nn.Conv2d(6,24,5,2,2),nn.ReLU(),nn.Conv2d(24,48,3,2,1),nn.ReLU(),nn.Conv2d(48,64,3,2,1),nn.ReLU(),nn.AdaptiveAvgPool2d((4,6)),nn.Flatten());self.head=nn.Linear(64*4*6,13)
 def forward(self,before,after):return self.head(self.encoder(torch.cat([before,after],1)))
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def idle_seconds():
 if sys.platform!='darwin':raise RuntimeError('sleep training gate currently supports Mac only')
 cg=ctypes.CDLL('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')
 cg.CGEventSourceSecondsSinceLastEventType.argtypes=[ctypes.c_uint32,ctypes.c_uint32];cg.CGEventSourceSecondsSinceLastEventType.restype=ctypes.c_double
 return cg.CGEventSourceSecondsSinceLastEventType(1,0xffffffff)
def sleep_gate():
 idle=idle_seconds();hour=datetime.datetime.now().hour
 if idle<300 and not ((hour>=22 or hour<7) and idle>=5):raise RuntimeError('training deferred: Ben must be away five minutes or asleep at night')
 if (Path.home()/'learner-ops'/'aon-notes'/'hands-20261106'/'STOP-TRAINING').exists():raise RuntimeError('training stopped by local stop file')
 return idle
def tensor(raw,h,w):return torch.from_numpy(np.frombuffer(raw,dtype=np.uint8).copy().reshape(h,w,3)).permute(2,0,1).float().div_(255).unsqueeze(0)
def features(row):
 own=np.zeros(12,dtype=np.float32);own[:2]=np.array(row.get('cursor',[24,24]))/[320,180];own[2]=row.get('textIndex',0)/20;own[3]=row.get('textLength',0)/20
 for k in row.get('keys',[]):
  if k in KEYS:own[4+KEYS.index(k)]=1
 return TASKS.index(row['task']),torch.from_numpy(own).unsqueeze(0)
def label(row):
 p=row['action'];y=np.zeros(16,dtype=np.float32);y[0:2]=np.array([p.get('dx',0),p.get('dy',0)])/24
 y[2]=int('left' in p.get('buttons',[]));y[3]=int('right' in p.get('buttons',[]))
 for k in p.get('keys',[]):
  if k in KEYS:y[4+KEYS.index(k)]=1
 y[12]=int(bool(p.get('character')));y[13]=0;y[14]=1;y[15]=0
 return torch.from_numpy(y)
def decode(row):
 raw=zlib.decompress(base64.b64decode(row['image']));crop=zlib.decompress(base64.b64decode(row['crop']));i,o=features(row)
 return tensor(raw,180,320),tensor(crop,192,192),torch.tensor([i]),o,label(row).unsqueeze(0)
def loss_fn(pred,y):return F.smooth_l1_loss(pred[:,:2],y[:,:2])+F.binary_cross_entropy_with_logits(pred[:,2:13],y[:,2:13])+0.1*F.mse_loss(pred[:,13:],y[:,13:])
def load_rows(root,allowed_days):
 rows=[];episodes={}
 for f in sorted(Path(root).glob('*.frames.jsonl')):
  for line in f.open():
   r=json.loads(line)
   if r['day'] in allowed_days and r.get('outcome')=='success':rows.append(r);episodes.setdefault(r['episode'],[]).append(len(rows)-1)
 return rows,episodes
def evaluate(net,rows):
 if not rows:return None
 total=0;net.eval()
 with torch.inference_mode():
  for row in rows[:512]:
   im,cr,it,own,y=decode(row);p,_=net(im,cr,it,own);total+=float(loss_fn(p,y))
 return total/min(len(rows),512)
def train(args):
 sleep_gate();root=Path(args[0]);out=Path(args[1]);steps=int(args[2]) if len(args)>2 else 300
 # Only REAL calendar dates from manifests. Never invent a held-out day.
 manifest=json.loads((root/'split.json').read_text());train_days=set(manifest['train_days']);held_days=set(manifest['held_days']);audit_days=set(manifest['audit_days'])
 if train_days&held_days or train_days&audit_days or held_days&audit_days:raise RuntimeError('day leakage')
 if not train_days:raise RuntimeError('no train day')
 rows,episodes=load_rows(root,train_days);held,_=load_rows(root,held_days);audit,_=load_rows(root,audit_days)
 if not rows:raise RuntimeError('no verified successful own attempts')
 random.seed(101);torch.manual_seed(101);net=PixelPolicy();optimizer=torch.optim.AdamW(net.parameters(),lr=0.0003);last_check=0
 out.mkdir(parents=True,exist_ok=True);current=out/'current.pt';old=None
 if current.exists():old=PixelPolicy();old.load_state_dict(torch.load(current,map_location='cpu',weights_only=True));net.load_state_dict(old.state_dict())
 groups=list(episodes.values());metrics=[];started=time.monotonic();initial=evaluate(net,rows[:64])
 for step in range(steps):
  if time.monotonic()-last_check>1:sleep_gate();last_check=time.monotonic()
  # Sequential four-frame windows; all members from the same episode/day.
  g=random.choice(groups);end=random.randrange(len(g));seq=g[max(0,end-3):end+1];h=None;loss=0
  net.train()
  for index in seq:
   im,cr,it,own,y=decode(rows[index]);p,h=net(im,cr,it,own,h);loss=loss+loss_fn(p,y)
  optimizer.zero_grad(set_to_none=True);(loss/len(seq)).backward();nn.utils.clip_grad_norm_(net.parameters(),1);optimizer.step()
  if step%50==0:metrics.append({'step':step,'loss':float(loss.detach()/len(seq))})
  # macOS ru_maxrss is bytes. Protect Ben even if an implementation grows later.
  if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>2_000_000_000:raise RuntimeError('2 GB training memory budget exceeded')
 sleep_gate();net.eval();path=out/'candidate.pt';tmp=out/'candidate.tmp';torch.save(net.state_dict(),tmp);os.replace(tmp,path)
 ex=(torch.zeros(1,3,180,320),torch.zeros(1,3,192,192),torch.zeros(1,dtype=torch.long),torch.zeros(1,12),torch.zeros(1,512))
 with torch.inference_mode():
  exported=torch.jit.trace(net,ex);exported.save(str(out/'candidate.ts'));check=torch.jit.load(str(out/'candidate.ts'));delta=float((net(*ex)[0]-check(*ex)[0]).abs().max())
 held_loss=evaluate(net,held);audit_loss=evaluate(net,audit);old_held=evaluate(old,held) if old else None;old_audit=evaluate(old,audit) if old else None
 # Quarantine only: task/speed/stop daytime marks must also pass before promotion.
 safe=bool(held and audit and delta<1e-5 and (old_audit is None or audit_loss<=old_audit) and (old_held is None or held_loss<old_held))
 result={'at':datetime.datetime.now().astimezone().isoformat(),'phase':'sleep','source':'Glim own sandbox attempts only','train_days':sorted(train_days),'held_days':sorted(held_days),'audit_days':sorted(audit_days),'rows':len(rows),'held_rows':len(held),'audit_rows':len(audit),'steps':steps,'seconds':time.monotonic()-started,'parameters':sum(p.numel() for p in net.parameters()),'initial_train_loss':initial,'final_train_loss':evaluate(net,rows[:64]),'held_loss':held_loss,'audit_loss':audit_loss,'export_max_error':delta,'sha256':digest(path),'export_sha256':digest(out/'candidate.ts'),'offline_seatbelt':safe,'promoted':False,'reason':'await real held-out/audit days and frozen awake marks' if not safe else 'offline safe; daytime marks still required','peak_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'curve':metrics}
 (out/'candidate.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
def worker(args):
 path=Path(args[0]);framefile=Path(args[1]);expected=digest(path);net=torch.jit.load(str(path),map_location='cpu');net.eval();hidden=torch.zeros(1,512);last=None
 print(json.dumps({'ready':True,'sha256':expected,'backend':'torch CPU, 1 thread'}),flush=True)
 with framefile.open('rb',buffering=0) as f,torch.inference_mode():
  for line in sys.stdin:
   try:
    m=json.loads(line);seq=m['frameId'];f.seek(0);before=int.from_bytes(f.read(8),'little');raw=f.read(320*180*3);crop=f.read(192*192*3);f.seek(0);after=int.from_bytes(f.read(8),'little')
    if before!=seq or after!=seq:print(json.dumps({'frameId':seq,'dropped':True}),flush=True);continue
    if last!=m['episode']:hidden.zero_();last=m['episode']
    i,own=features(m);start=time.monotonic_ns();pred,hidden=net(tensor(raw,180,320),tensor(crop,192,192),torch.tensor([i]),own,hidden);hidden=hidden.detach();v=pred[0].tolist()
    packet={'dx':float(np.clip(v[0],-1,1)*24),'dy':float(np.clip(v[1],-1,1)*24),'buttons':[b for j,b in enumerate(['left','right']) if v[2+j]>0],'keys':[k for j,k in enumerate(KEYS) if v[4+j]>0],'wheel':30 if m['task']=='scroll' and v[2]<=0 else 0,'character':m.get('text','')[m.get('textIndex',0):m.get('textIndex',0)+1] if v[12]>0 else None,'timeToGoMs':max(0,min(50,v[13]*50))}
    print(json.dumps({'frameId':seq,'packet':packet,'inferenceMs':(time.monotonic_ns()-start)/1e6,'sha256':expected}),flush=True)
   except Exception as e:print(json.dumps({'error':str(e)}),flush=True)
 if digest(path)!=expected:raise RuntimeError('awake artifact changed')
if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='train':train(sys.argv[2:])
 elif mode=='worker':worker(sys.argv[2:])
 elif mode=='gate':print(json.dumps({'idleSeconds':sleep_gate(),'phase':'allowed sleep window'}))
 elif mode=='describe':
  model=PixelPolicy();print(json.dumps({'parameters':sum(p.numel() for p in model.parameters()),'training':False}))
 else:raise SystemExit('train | worker | gate | describe')
