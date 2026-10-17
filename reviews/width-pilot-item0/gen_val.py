"""Generate the Item 0(h) validation slice per VAL-PRENAME.md: seed 93704; also disjoint from HO2, '(K)*(J)' on training pairs, disjoint from all L5 rows.
usage: python3 -I gen_ho2.py BASE OUT   (BASE: regenerated far-data dir with panel/, diag/, learn/; refuses to overwrite OUT)"""
import hashlib, json, os, random, sys
sys.path.insert(0, '/home/user/wtfar')
base, out = sys.argv[1], sys.argv[2]
if os.path.exists(out):
    raise SystemExit(f'refusing to overwrite {out}')
PANEL, DIAG, LEARN = (os.path.join(base, d) for d in ('panel', 'diag', 'learn'))
from domain.far import sheet_probe as SP
from domain.far import learn_probe as LP
from domain.tools import sheet as sheet_tool
SP.DIAG, SP.PROBE = DIAG, os.path.join(DIAG, 'sheet-probe.jsonl')
j = lambda n: os.path.join(LEARN, n)
LP.LEARN = LEARN
LP.TRAIN_ROWS, LP.MODE_ROWS = j('train-rows.jsonl'), j('train-rows-mode.jsonl')
LP.L3_TRAIN_ROWS, LP.L3_EVAL_ROWS, LP.L3_SPLIT = j('train-rows-l3.jsonl'), j('eval-rows-l3.jsonl'), j('pair-split-l3.json')
LP.L5_TRAIN_ROWS, LP.L5_EVAL_ROWS = j('train-rows-l5.jsonl'), j('eval-rows-l5.jsonl')
LP.L4_ROWS, LP.L4R1_ROWS = j('train-rows-l4.jsonl'), j('train-rows-l4r1.jsonl')
LP.V3_PANEL = os.path.join(PANEL, 'sheet.v3.jsonl')
LP.EXCLUDE_FILES = (SP.PROBE, os.path.join(PANEL, 'sheet.jsonl'), os.path.join(PANEL, 'sheet.v2.jsonl'), LP.V3_PANEL)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
assert sha(LP.L5_TRAIN_ROWS).startswith('15cda9d3') and sha(LP.L5_EVAL_ROWS).startswith('2d927fdb'), 'L5 inputs are not the recorded files'
HO2_SEED = 93704  # VAL seed (VAL-PRENAME.md)
split = json.load(open(LP.L3_SPLIT))
train_pairs, held_pairs = [tuple(p) for p in split['train']], [tuple(p) for p in split['held_out']]
assert (train_pairs, held_pairs) == LP.pair_split()
exclude = LP.read_prompts(LP.EXCLUDE_FILES + (LP.TRAIN_ROWS, LP.MODE_ROWS, LP.L3_TRAIN_ROWS, LP.L3_EVAL_ROWS, LP.L4_ROWS, LP.L4R1_ROWS))
l5 = [json.loads(l) for p in (LP.L5_TRAIN_ROWS, LP.L5_EVAL_ROWS) for l in open(p)]
seen = {r['prompt'] for r in l5} | {json.loads(l)['prompt'] for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'eval-rows-ho2.jsonl'))}
help_prompts = {h['prompt'] for h in sheet_tool.help()}
rows, stats = LP.draw_joined(random.Random(HO2_SEED), train_pairs, '(K)*(J)', LP.L5_EVAL_N, 'VAL', 'l5v', exclude, seen, help_prompts)
prompts = [r['prompt'] for r in rows]
assert len(set(prompts)) == len(rows) and not set(prompts) & {r['prompt'] for r in l5} and not set(prompts) & exclude
LP.write_new(out, ''.join(json.dumps(r) + '\n' for r in rows))
ho1 = [r for r in l5 if r.get('split') == 'HO']
ho1_sha = hashlib.sha256(''.join(json.dumps(r) + '\n' for r in ho1).encode()).hexdigest()
from collections import Counter
print(json.dumps(dict(ho2_rows=len(rows), ho2_sha256=sha(out), ho1_rows=len(ho1), ho1_sha256=ho1_sha, seed=HO2_SEED,
                      kinds=Counter(r['kind'] for r in rows), steps=Counter(r['n_steps'] for r in rows),
                      tries=sum(st['tries'] for st in stats.values())), default=str, indent=1))
