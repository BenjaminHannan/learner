import sys, json, re, collections
sys.path.insert(0, '/home/user/wtfar')
from domain.far.join_gap import split_formula, grid_of, piece_prompt, same_call
from domain.tools import sheet as sheet_tool
S = '/tmp/claude-0/-home-user/7b4cc9f0-8b9c-5e78-99b7-c110382faf97/scratchpad/'
def load(path): return [json.loads(l) for l in open(path)]
def items(L): return load(S + f'out/items-{L}.jsonl')
def formula(p): return p.split(';', 1)[1].strip()[1:]
def grid(p):
    g = {}
    for part in p.split(';')[0].split('|'):
        c, v = part.strip().split(':'); g[c.strip()] = [int(x) for x in v.split()]
    return g
