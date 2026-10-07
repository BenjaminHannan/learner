"""Research-loop scorer for C2 (LOCKED; written 10-07 before any loop trial).

One run = one seed = one parent. Build the parent's learner from its N with a method (the editable `creative.rl.method.train`, or a fixed reference
from `creative.rl.refs`), then score it:
  c2_right     greedy first try, % right, on DEV (256) or the loop's fresh holdout (512); the model's single program is run on the query, no test-time search
  chain5_harm  N's pooled chain-5 skills exact minus the learner's, in points (data_big dev/in_dist chain families; the nightly guard's measure)
  flops_tf     torch-counted FLOPs (forward + backward) of everything the method ran, plus the charged cost of the night's cached tries if it used them

What a method may see (the context `ctx`): the parent N (a private copy), its vocab, the pool questions as prompts only (no answer, accepted, kind or
params), the parent's cached night W records (params stripped; using them charges the night's 32 tries per pool question), the warm split's practised
add/mult solver records, skills TRAIN replay rows, the parent's pool temperature, and the seed. It must never open dev, holdout, labelled or test, must
return a model of the parent's own class, and must not add test-time search or executor calls inside the model.
Since 10-07 (Ben: everything must run on its own while deployed) a method may NOT use the cached night or the parent's pool temperature: both were set
with DEV answers. It runs its own night on ctx.N (the sampling FLOPs are counted). References keep both.

Seeds: 0..7 -> parents s200..s205, s100, s101; a seed >= 100000 (the harness's fresh seeds) -> one of s202..s205, s100, s101 by seed % 6. The seed is also
the method's own random seed.

  python3 -m creative.rl.eval_c2 --split dev --seed 0 [--ref job6]
"""
import argparse, copy, json, os, sys, time
import torch
from torch.utils.flop_counter import FlopCounterMode
from creative import fastsleep as fs, sleep, c2_stones, rules_real as R
from custom_io.models import progparse as pp

PARENTS = ['s200', 's201', 's202', 's203', 's204', 's205', 's100', 's101']
PARENT_DIR = os.environ.get('RL_PARENTS', os.path.expanduser('~/rl/parents'))
SKILLS_TRAIN = os.environ.get('RL_SKILLS_TRAIN', os.path.expanduser('~/work/data/train.jsonl'))
SKILLS_DATA = os.environ.get('RL_SKILLS_DATA', os.path.expanduser('~/work/data_big'))
DEVICE = os.environ.get('RL_DEVICE', 'cpu')
NIGHT_TF = 25.5          # 32 tries x 1,024 pool questions, torch-counted on s205 (1.59 TF for 64 questions, scaled); fast-sleep research 10-07
HIDDEN = ('answer', 'accepted', 'kind', 'params')


def parent_of(seed):
    return PARENTS[seed] if seed < len(PARENTS) else PARENTS[2 + seed % 6]


class Ctx:
    def __init__(self, seed, device='cpu', deploy=False):
        self.seed, self.device, self.parent, self.deploy = seed, device, parent_of(seed), deploy
        self._N, self.vocab, self.meta, s = fs.load_setup(os.path.join(PARENT_DIR, self.parent), device)
        self._T = s['T']
        self._W = [{k: v for k, v in r.items() if k != 'params'} for r in s['records']['W']]
        self.pool = [{'id': r['id'], 'prompt': r['prompt'], 'nums': r['nums']} for r in c2_stones._with_nums(R.load_split(fs.DATA, 'pool'))]
        self.warm = R.warm_records(R.load_split(fs.DATA, 'warm'))
        self.replay = sleep.load_replay(SKILLS_TRAIN, None, seed)
        self.charged = {}

    @property
    def N(self):
        return copy.deepcopy(self._N)

    @property
    def T(self):
        if self.deploy:
            raise AttributeError('a method may not use the parent pool temperature (picked with DEV answers; deployed-autonomy rule 10-07)')
        return self._T

    def night(self):
        """The parent's cached night (32 tries per pool question at its pool temperature, W = up to 2 tries per question that fit all examples)."""
        if self.deploy:
            raise RuntimeError('a method may not use the cached night (its temperature was picked with DEV answers; deployed-autonomy rule 10-07)')
        self.charge(NIGHT_TF, 'night tries (cached)')
        return [dict(r) for r in self._W]

    def charge(self, tf, why):
        self.charged[why] = tf


def run(split, seed, ref=None, device=DEVICE):
    torch.manual_seed(seed)
    ctx = Ctx(seed, device, deploy=ref is None)
    if ref:
        from creative.rl import refs
        fn = getattr(refs, ref)
    else:
        from creative.rl import method
        fn = method.train
    t0 = time.time()
    with FlopCounterMode(display=False) as fc:
        m = fn(ctx)
    secs = time.time() - t0
    assert type(m) is type(ctx._N), f'method returned {type(m)}, not the parent class'
    flops_tf = fc.get_total_flops() / 1e12 + sum(ctx.charged.values())
    data = 'creative/data/c2rl' if split == 'holdout' else fs.DATA
    rows = c2_stones._with_nums(R.load_split(data, split))
    m.eval()
    d, _ = fs.dev_eval(m, rows, ctx.vocab, device)
    harm = 100 * (fs.skills5(ctx._N, SKILLS_DATA, device) - fs.skills5(m, SKILLS_DATA, device))
    out = dict(split=split, seed=seed, parent=ctx.parent, ref=ref, device=device, c2_right=100 * d['right'], chain5_harm=round(harm, 6), flops_tf=flops_tf,
               method_seconds=round(secs, 1), charged=ctx.charged, by_kind=d['by_kind'])
    print(json.dumps(out), flush=True)
    for k, v in sorted(d['by_kind'].items()):
        print(f'right_{k}: {100 * v:.2f}')
    print(f'method_seconds: {secs:.1f}')
    print(f'flops_tf: {flops_tf:.4f}')
    print(f'chain5_harm: {harm:.4f}')
    print(f'c2_right: {100 * d["right"]:.4f}')
    return out


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--split', choices=('dev', 'holdout'), default=os.environ.get('RL_SPLIT', 'dev'))
    a.add_argument('--seed', type=int, default=int(os.environ.get('RL_SEED', 0)))
    a.add_argument('--ref', default=None)
    a.add_argument('--threads', type=int, default=4)
    a = a.parse_args()
    torch.set_num_threads(a.threads)
    sys.setrecursionlimit(10000)
    run(a.split, a.seed, a.ref)
