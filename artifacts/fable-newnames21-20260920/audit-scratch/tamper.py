import sys, json, copy, shutil
from pathlib import Path
S = Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-newnames21-20260920/audit-scratch')
sys.path.insert(0, str(S))
import postc1_newnames21 as M
FIX = S.parent/'fixtures/exp'
EXP = S/'gate-exp'
if EXP.exists(): shutil.rmtree(EXP)
(EXP/'scores').mkdir(parents=True)

def doctor(row, arm):
    row = copy.deepcopy(row)
    row['arm'] = arm
    for name, sc in row['scorings'].items():
        for cell, c in sc['cells'].items():
            c['n'] = 512; c['R'] = M.CUTOFFS[cell] + 5; c['M'] = 400
    return row

ctl = json.loads((FIX/'scores/control-9.json').read_text())
trt = json.loads((FIX/'scores/treatment-9.json').read_text())
for seed in M.SEEDS:
    d = doctor(ctl, 'control'); d['seed'] = seed
    (EXP/f'scores/control-{seed}.json').write_text(json.dumps(d))
    d = doctor(trt, 'treatment'); d['seed'] = seed
    (EXP/f'scores/treatment-{seed}.json').write_text(json.dumps(d))

def verdict(label):
    t = M.gate_table(EXP)
    print(f'{label:<46} verdict={t["verdict"]:<11} reason={t["reason"]}')
    return t

verdict('A. all six synthetic score files present')

p = EXP/'scores/treatment-2102.json'; keep = p.read_text(); p.unlink()
verdict('B. one score file deleted (treatment-2102)')
p.write_text(keep)

p = EXP/'scores/treatment-2101.json'
row = json.loads(p.read_text()); keep2 = p.read_text()
del row['scorings']['reserved']['cells']['s3']
p.write_text(json.dumps(row))
try:
    verdict('C. cell s3 deleted from treatment-2101')
except Exception as exc:
    print(f'{"C. cell s3 deleted from treatment-2101":<46} raised {type(exc).__name__}: {exc}')
p.write_text(keep2)

# D. one cell below cutoff
row = json.loads(p.read_text()); row['scorings']['reserved']['cells']['c3']['R'] = 400
p.write_text(json.dumps(row)); verdict('D. treatment-2101 c3 below cutoff'); p.write_text(keep2)

# E. paired mark: reserved 20 below training-pool on one cell
row = json.loads(p.read_text())
row['scorings']['reserved']['cells']['c4']['R'] = row['scorings']['train']['cells']['c4']['R'] - 20
p.write_text(json.dumps(row)); verdict('E. treatment-2101 c4 reserved-train = -20'); p.write_text(keep2)

# F. reserved 20 ABOVE training-pool (one-sided mark must still pass)
row = json.loads(p.read_text())
row['scorings']['train']['cells']['c4']['R'] = row['scorings']['reserved']['cells']['c4']['R'] - 20
p.write_text(json.dumps(row)); verdict('F. treatment-2101 c4 reserved-train = +20'); p.write_text(keep2)

# G. two control seeds fail -> VOID even with treatment 3/3
for seed in (2100, 2101):
    q = EXP/f'scores/control-{seed}.json'; r = json.loads(q.read_text())
    r['scorings']['control']['cells']['c1']['R'] = 100; q.write_text(json.dumps(r))
verdict('G. two control seeds below cutoff')

# H. tamper the manifest cutoffs (can a flag / file change the marks?)
print('\ngates CLI flags:', [a.option_strings for a in
      M.build_parser()._subparsers._group_actions[0].choices['gates']._actions])
print('CUTOFFS used by the gate:', M.CUTOFFS)
