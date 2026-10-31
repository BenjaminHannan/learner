# Attempt 1: the eg.py FrozenEG.load path, strict (its own >=5.19 assert). Attempt 2: the same AutoModel call with the assert skipped.
import os, sys, traceback, time, torch
os.environ['HF_HUB_OFFLINE'] = '1'; os.environ['TRANSFORMERS_OFFLINE'] = '1'
sys.path.insert(0, '/Users/ben-hannan/Desktop/projects/talker-gap-wt/talker_gap/diag')
import eg_ref
import transformers
print('transformers', transformers.__version__, flush=True)
path = '/Users/ben-hannan/eg2'
print('--- Attempt 1: eg_ref.FrozenEG(path).load(mps) strict', flush=True)
try:
    eg_ref.FrozenEG(path).load(torch.device('mps'))
    print('ATTEMPT1 OK', flush=True)
except Exception as e:
    print('ATTEMPT1 FAIL:', type(e).__name__, str(e)[:500], flush=True)

print('--- Attempt 2: same AutoModel call as eg.py line 43, no version assert', flush=True)
from transformers import AutoModel, AutoTokenizer
try:
    tok = AutoTokenizer.from_pretrained(path)
    print('tokenizer OK:', type(tok).__name__, 'pad', tok.pad_token_id, flush=True)
except Exception as e:
    print('TOKENIZER FAIL:', type(e).__name__, str(e)[:400], flush=True)
t0 = time.time()
try:
    m = AutoModel.from_pretrained(path, vision_config=None, audio_config=None, dtype=torch.float32)
    print('ATTEMPT2 OK', type(m).__name__, 'in', round(time.time()-t0,1), 's', flush=True)
except Exception as e:
    print('ATTEMPT2 FAIL:', type(e).__name__, str(e)[:800], flush=True)
    traceback.print_exc(limit=3)
