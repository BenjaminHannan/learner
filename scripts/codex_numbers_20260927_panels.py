#!/usr/bin/env python3
"""Create disclosed design and train diagnostics; sealed five-panel requires pushed registration."""
import argparse, hashlib, json, random, subprocess, time
from pathlib import Path
import claude_rsn358g_run as G
E,R=G.E,G.R
ROOT=Path(__file__).resolve().parent.parent
ART=ROOT/'artifacts/codex-numbers-20260927'
def write_panel(path,items):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists(): raise FileExistsError(path)
    path.write_text(''.join(json.dumps(R.item_to_json(x),sort_keys=True)+'\n' for x in items))
    return hashlib.sha256(path.read_bytes()).hexdigest()
def design():
    pool=json.loads((ART/'cache/number-hands-v1.json').read_text());four,held=E.split_four(pool['four'])
    rng=random.Random(35834)
    panels={'numbers4':[E.number_item(rng,*x) for x in held]}
    for name,kind,size,seed in [('sums4','sums',4,35811),('grids5','grids',5,35821)]:
        rng=random.Random(seed)
        panels[name]=[E.make_sum(rng,size) if kind=='sums' else E.latin_item(rng,*E.make_latin_base(rng,size)) for _ in range(300)]
    hashes={k:write_panel(ART/'panels'/f'{k}.jsonl',v) for k,v in panels.items()}
    for kind,hands in [('train-numbers3',pool['three']),('train-numbers4',four)]:
        rng=random.Random(9276191)
        hashes[kind]=write_panel(ART/'diagnostics'/f'{kind}.jsonl',[E.number_item(rng,*x) for x in hands])
    (ART/'diagnostics/design-panel-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print(json.dumps(hashes))
def sealed(registration,seed):
    # Registration must already be on remote main and unchanged locally.
    subprocess.run(['git','fetch','origin','main'],cwd=ROOT,check=True)
    subprocess.run(['git','merge-base','--is-ancestor',registration,'origin/main'],cwd=ROOT,check=True)
    rel='artifacts/codex-numbers-20260927/PASSMARKS.md'
    pushed=subprocess.check_output(['git','show',f'{registration}:{rel}'],cwd=ROOT)
    if pushed != (ROOT/rel).read_bytes():raise RuntimeError('PASSMARKS differs from pushed registration')
    frozen_path=ART/'CHECKPOINTS-FROZEN.json'
    if not frozen_path.is_file():raise RuntimeError('all registered checkpoints must be frozen before the fresh panel is drawn')
    frozen=json.loads(frozen_path.read_text())
    config=json.loads((ART/'EXPERIMENT.json').read_text())
    expected={(variant,training_seed) for training_seed in config['seeds'] for variant in ('baseline','candidate')}
    actual={(run['variant'],run['seed']) for run in frozen['runs']}
    if frozen['registration_commit'] != registration or actual != expected or len(frozen['runs']) != len(expected):
        raise RuntimeError('frozen checkpoint inventory differs from registration')
    if seed != config['sealed_seed']:raise RuntimeError('fresh panel seed differs from registration')
    for run in frozen['runs']:
        checkpoint=Path(run['checkpoint'])
        if not checkpoint.is_file() or hashlib.sha256(checkpoint.read_bytes()).hexdigest() != run['checkpoint_sha256']:
            raise RuntimeError('frozen checkpoint missing or changed before fresh-panel generation')
    if (ART/'panels/numbers5.jsonl').exists():raise FileExistsError('sealed panel already drawn')
    rng=random.Random(seed+1)
    old={tuple(h) for h,t,sol in E.five_hands(35832,300)}
    pool=E.five_hands(seed,600)
    hands=[x for x in pool if tuple(x[0]) not in old][:300]
    if len(hands)!=300:raise RuntimeError("fresh pool too small; no adaptive refill allowed")
    if set(E.TRAIN_SIZES['numbers']) != {3,4} or any(len(x[0]) != 5 for x in hands):
        raise RuntimeError('zero training-hand overlap cannot be certified by hand length')
    digest=write_panel(ART/'panels/numbers5.jsonl',[E.number_item(rng,*x) for x in hands])
    record={'seed':seed,'registration_commit':registration,'generated_unix':time.time(),'n':300,'excluded_published_seed':35832,'raw_draw_count':600,'sha256':digest,'training_hand_overlap':0,'training_hand_overlap_basis':'training uses only three- and four-number hands; this panel contains five-number hands','frozen_manifest_sha256':hashlib.sha256(frozen_path.read_bytes()).hexdigest(),'read_policy':'one fixed sweep across frozen checkpoints; candidate intact and per-read-wiped conditions share the same items; recount never reruns inference'}
    (ART/'SEALED-PANEL.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['design','sealed']);p.add_argument('--registration');p.add_argument('--seed',type=int);a=p.parse_args()
    if a.mode=='design':design()
    else:
        if not a.registration or a.seed is None:p.error('sealed requires --registration and --seed')
        sealed(a.registration,a.seed)
