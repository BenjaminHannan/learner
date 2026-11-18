import sys,time,json,torch,resource
sys.path.insert(0,'/Users/ben-hannan/Desktop/projects/talker-gap-wt/talker_gap/diag')
import eg_ref
t=time.time()
for dev in ['cpu','mps']:
    d=torch.device(dev)
    fe=eg_ref.FrozenEG('/Users/ben-hannan/eg2').load(d)
    print(dev,'loaded',round(time.time()-t,1),'s')
    prompts=['Orla listened to the radio while Hugo played a game. Who was playing the game?']*256
    t0=time.time()
    with torch.no_grad():
        H,p=fe.encode(prompts,96,d)
    if dev=='mps':torch.mps.synchronize()
    print(dev,'encode 256 prompts',round(time.time()-t0,2),'s',tuple(H.shape),tuple(p.shape))
    del fe
print('maxrss_MB',resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e6)
