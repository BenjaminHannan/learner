import time, torch, sys
sys.path.insert(0,'/home/user/learner')
from creative import sleep
from creative.consol import sleep_mixed
torch.set_num_threads(1)
m, vocab, meta = sleep.load_parent('/root/work/ckpt/B2_s200.pt')
rows = sleep.load_replay('/root/work/data/train.jsonl', 8000, 0)
t=time.time(); sleep_mixed(m, rows[:2048], rows[2048:], vocab, 3, batch=1024, micro=256); print('3 updates batch 1024:', round(time.time()-t,1),'s', flush=True)
import resource; print('maxrss MB', resource.getrusage(resource.RUSAGE_SELF).ru_maxrss//1024)
