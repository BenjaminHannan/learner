"""Recount only the historical, already-public rsn358i3 summary and final log rows."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--ref',required=True);a=p.parse_args()
rows=[]
for arm in ('loop','plain'):
    for seed in range(5,9):
        base=f'artifacts/claude-rsn358i3-20260926/runs/{arm}-s{seed}'
        read=lambda name:subprocess.check_output(['git','show',f'{a.ref}:{base}/{name}']).decode()
        scores=json.loads(read('tests.json'))['tests']
        train=json.loads(read('train_log.jsonl').splitlines()[-1])
        rows.append({'arm':arm,'seed':seed,'step':train['step'],'final_training_exact':train['exact_by_kind'],'scores':{k:scores[k]['right'] for k in ('numbers4','numbers5','sums4','grids5')}})
out=Path('artifacts/codex-numbers-20260927/diagnostics/historical-recount.json')
out.write_text(json.dumps({'ref':a.ref,'rows':rows},indent=2)+'\n')
print(out.read_text())
