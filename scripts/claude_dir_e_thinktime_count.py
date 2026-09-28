"""Count thinking rounds vs practice (k) from saved fewex EQ holdout files. No training, no torch.
Usage: python3 scripts/claude_dir_e_thinktime_count.py > artifacts/claude-dir-e-thinktime-20260928/counts.txt"""
import json
R='artifacts/claude-fewex-20260927/eq-runs/'
KS=['1','4','16','64','256','1024','4096','16384']
tot={'pre':[0,0],'fresh':[0,0]}
for init in ['pre','fresh']:
  for s in (0,1):
    d=json.load(open(f'{R}loop-s{s}-{init}/holdout.json'))['scores']
    print(f'== practised={init=="pre"} loop seed {s} (mean rounds / cap hits of 300 / right of 300; 9x9)')
    for st in ['0']+KS+['sleep64','sleep16384']:
      c=d[st]['9']; print(f'  {st:>10}: {c["mean_rounds"]:5.1f} rounds  cap {c["cap_hits"]:3d}  right {c["right"]:3d}')
    r=[d[k]['9']['mean_rounds'] for k in KS]
    hi=sum(x<47 for x in r); print(f'  rungs 1..16384 below cap (<47 rounds): {hi} of 8; low half (1,4,16,64) mean {sum(r[:4])/4:.1f}, high half (256..16384) mean {sum(r[4:])/4:.1f}')
    print('  rounds by rung:',[round(x,1) for x in r])
    print('  old kinds (mean rounds, right of 200):',{st:{k:(round(v["mean_rounds"],1),v["right"]) for k,v in x.items()} for st,x in json.load(open(f'{R}loop-s{s}-{init}/adapt.json'))['old'].items()})
