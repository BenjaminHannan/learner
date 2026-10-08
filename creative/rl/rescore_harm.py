"""Re-score the research loop's compliant sleep (creative.rl.method.train) with the new harm measure (roadmap e9e0bd2aeb, 10-08): in_dist over all 34
skills families plus the per-family floor, against the parent N and against the B2 it came from. The research loop only measured pooled-5 (chain5_harm).

  python3 -m creative.rl.rescore_harm --seeds 0 1 2 3 4 5 --b2-dir ~/fs/ckpt --out DIR [--device cuda]

Builds each seed's learner exactly as creative.rl.eval_c2.run does (deploy context, seeded), saves it, scores C2 DEV first try (never the holdout,
labelled or test) and the skills DEV in_dist split. -> DIR/rescore.json (also after every seed) and DIR/<parent>/learner.pt."""
import argparse, json, os, sys, time
import torch
from creative import fastsleep as fs, c2_stones, rules_real as R, sleep
from creative.harm_look import harm_measure, skills_hits
from creative.rl import eval_c2 as E


def one(seed, b2_dir, out, device):
    torch.manual_seed(seed)
    ctx = E.Ctx(seed, device, deploy=True)
    from creative.rl import method
    t0 = time.time()
    m = method.train(ctx)
    secs = time.time() - t0
    assert type(m) is type(ctx._N)
    m.eval()
    pdir = os.path.join(out, ctx.parent)
    os.makedirs(pdir, exist_ok=True)
    sleep.save_parent(m, ctx.meta['name'], ctx.meta['cfg'], ctx.vocab, os.path.join(pdir, 'learner.pt'), step=(ctx.meta.get('step') or 0), warmup=True)
    d, _ = fs.dev_eval(m, c2_stones._with_nums(R.load_split(fs.DATA, 'dev')), ctx.vocab, device)
    rows, hl, p5l, idl = skills_hits(m, E.SKILLS_DATA, device)
    _, hn, p5n, idn = skills_hits(ctx._N, E.SKILLS_DATA, device)
    res = dict(seed=seed, parent=ctx.parent, method_seconds=round(secs, 1), c2_dev_right=100 * d['right'], pooled5=dict(N=p5n, learner=p5l), in_dist=dict(N=idn, learner=idl),
               chain5_harm_vs_N=p5n - p5l, vs_N=harm_measure(hn, hl, rows))
    bp = os.path.join(os.path.expanduser(b2_dir), f'B2_{ctx.parent}.pt') if b2_dir else None
    if bp and os.path.exists(bp):
        b2, _, _ = sleep.load_parent(bp, device)
        _, hb, p5b, idb = skills_hits(b2, E.SKILLS_DATA, device)
        res['pooled5']['B2'], res['in_dist']['B2'] = p5b, idb
        res['vs_B2'] = harm_measure(hb, hl, rows)
        res['N_vs_B2'] = harm_measure(hb, hn, rows)
    return res


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--seeds', type=int, nargs='+', default=[0, 1, 2, 3, 4, 5]); a.add_argument('--b2-dir'); a.add_argument('--out', required=True)
    a.add_argument('--device', default=E.DEVICE); a.add_argument('--threads', type=int, default=4)
    a = a.parse_args()
    torch.set_num_threads(a.threads)
    sys.setrecursionlimit(10000)
    os.makedirs(a.out, exist_ok=True)
    allres = {}
    for s in a.seeds:
        r = one(s, a.b2_dir, a.out, a.device)
        allres[r['parent']] = r
        json.dump(allres, open(os.path.join(a.out, 'rescore.json'), 'w'), indent=1)
        v = r['vs_N']
        print(r['parent'], 'c2_dev', round(r['c2_dev_right'], 1), 'pooled5 harm', round(r['chain5_harm_vs_N'], 2), 'in_dist drop vs N', round(v['in_dist_drop'], 2),
              'fired', v['fired'], 'passes', v['passes'], ('vs B2 in_dist drop %.2f fired %s' % (r['vs_B2']['in_dist_drop'], r['vs_B2']['fired'])) if 'vs_B2' in r else '', flush=True)
