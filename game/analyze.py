"""Analysis of one game-world run: marks GW1-GW6 (sealed plan; scoring only).

  python -m game.analyze --run RUN_DIR --parent CKPT --before B.json --after A.json --random R.json [--ppo P.json]
                         [--nights-dir DIR] [--dev DEV_IN_DIST.jsonl] --out DIR [--threads 2]

B, A, R, P are game.score outputs on the 100 sealed worlds (before = parent, after = the run's final checkpoint).
Writes DIR/RESULT.json and DIR/RESULT.md; the old-skills scoring is cached under DIR/cache.
Hair-miss rule (plan): a value within 1 world of a PASS bar counts as met and the result says so. choice: 1 world =
0.01 unlocks per episode (GW1, GW3) and 1 point of share (GW2); GW4-GW6 have no hair tolerance.
"""
import argparse
import json
import os
import random

import torch

from game import audit as gaudit
from game import play
from game.score import ACH

GW1_PASS, GW1_WRONG = 1.5, 0.5
GW2_PASS, GW2_WRONG = 10.0, 2.0
GW3_PASS, GW3_WRONG = 0.0, -1.0
GW4_WRONG = 5.0
GW6_BACK, GW6_RISE, GW6_WRONG, GW6_PAST = 3.0, 3.0, 5.0, 4
HAIR_UNLOCKS, HAIR_SHARE = 0.01, 1.0
LADDER = ['place_table', 'make_wood_sword', 'make_wood_pickaxe', 'collect_stone', 'make_stone_pickaxe']


def boot_diff(a, b, draws=2000, seed=0):
    """Paired bootstrap over worlds of mean(a) - mean(b). -> (diff, lo, hi), 95%."""
    assert len(a) == len(b) and a
    rng = random.Random(seed)
    d = [x - y for x, y in zip(a, b)]
    n = len(d)
    ms = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(draws))
    return sum(d) / n, ms[int(0.025 * draws)], ms[int(0.975 * draws) - 1]


def unlocks(res):
    return [w['n_unlocks'] for w in res['per_world']]


def paired(x, y):
    assert [w['seed'] for w in x['per_world']] == [w['seed'] for w in y['per_world']], 'arms are on different worlds'
    return boot_diff(unlocks(x), unlocks(y))


# ---------- the rules (pure functions) ----------

def gw1_rule(d, lo):
    d, lo = round(d, 6), round(lo, 6)
    hair = GW1_PASS - HAIR_UNLOCKS <= d < GW1_PASS
    if d < GW1_WRONG:
        v = 'PROVED WRONG'
    elif (d >= GW1_PASS or hair) and lo > 0:
        v = 'PASS'
    else:
        v = 'FAIL'
    return dict(value=d, lo=lo, bar='pass: d >= 1.5 and interval low end > 0; proved wrong: d < 0.5', verdict=v,
                hair_miss_used=v == 'PASS' and hair)


def gw2_rule(share):
    share = round(share, 6)
    hair = GW2_PASS - HAIR_SHARE <= share < GW2_PASS
    v = 'PROVED WRONG' if share <= GW2_WRONG else ('PASS' if share >= GW2_PASS or hair else 'FAIL')
    return dict(value=share, bar='pass: share >= 10%; proved wrong: <= 2%', verdict=v, hair_miss_used=v == 'PASS' and hair)


def gw3_rule(e, hi):
    e, hi = round(e, 6), round(hi, 6)
    hair = GW3_PASS - HAIR_UNLOCKS <= e < GW3_PASS
    v = 'PROVED WRONG' if (e <= GW3_WRONG and hi < 0) else ('PASS' if e >= GW3_PASS or hair else 'FAIL')
    return dict(value=e, hi=hi, bar='pass: e >= 0; proved wrong: e <= -1.0 and interval high end < 0', verdict=v,
                hair_miss_used=v == 'PASS' and hair)


def gw4_rule(harm_res):
    drop = round(harm_res['in_dist_drop'], 6)
    v = 'PROVED WRONG' if drop > GW4_WRONG else ('PASS' if harm_res['passes'] else 'FAIL')
    return dict(value=drop, fired=harm_res['fired'], verdict=v,
                bar='pass: in_dist drop <= 1.5 and no family fired (routed by the run switch); proved wrong: drop > 5')


def gw5_rule(rep):
    v = 'PROVED WRONG' if rep['proved_wrong'] else ('PASS' if rep['ok'] else 'FAIL')
    return dict(value=rep['n_problems'] if 'n_problems' in rep else len(rep['problems']), verdict=v,
                bar='pass: game.audit finds no problem; proved wrong: sealed or quiz world in a training row, or changed constants')


def gw6_rule(p):
    """p: progress on the first 50 sealed worlds at night 0 (parent), 1, ..., S (the stop night), S >= 1."""
    s = len(p) - 1
    assert s >= 1
    ps, pp, best = round(p[s], 6), round(p[s - 1], 6), round(max(p), 6)
    best_night = max(i for i, v in enumerate(p) if round(v, 6) == best)
    rise = round(ps - pp, 6)
    if rise > GW6_WRONG or (s >= best_night + GW6_PAST and ps < best - GW6_WRONG):
        v = 'PROVED WRONG'
    elif ps >= best - GW6_BACK and rise <= GW6_RISE:
        v = 'PASS'
    else:
        v = 'FAIL'
    return dict(stop_night=s, p_stop=ps, p_prev=pp, best=best, best_night=best_night, rise_last_night=rise, verdict=v,
                bar='pass: p_S >= best - 3 and p_S - p_(S-1) <= 3; proved wrong: rise > 5, or S >= best night + 4 and p_S < best - 5')


# ---------- parts that need files ----------

def sha256_file(path):
    return gaudit.sha256_file(path)


def old_skills(run, parent, final, dev_path, cache_dir):
    """GW4: parent and final checkpoint on DEV in_dist; rows routed by the run's gate.pt; also the add-on always on."""
    from custom_io.data import load_rows
    from custom_io.models import load_model
    from domain import analyze as da, harm, route
    rows = load_rows(dev_path)
    dev_sha = sha256_file(dev_path)
    h0, _ = da.in_dist_one(parent, rows, dev_sha, cache_dir)
    hN, _ = da.in_dist_one(final, rows, dev_sha, cache_dir)
    st = torch.load(os.path.join(run, 'gate.pt'), map_location='cpu')
    # choice: the gate is rebuilt from its state exactly as route.train_gate defines it (standardise, logistic unit)
    gate = lambda F: (torch.sigmoid(((F - st['mu']) / st['sd']) @ st['w'] + st['b']) > st['threshold'])
    m = load_model(parent).eval()   # the parent's reader = the model's reader with the add-on off
    on = gate(route.features(m, [r['prompt'] for r in rows])).tolist()
    routed = [b if o else a for a, b, o in zip(h0['hits'], hN['hits'], on)]
    hm = harm.harm_measure(h0['hits'], routed, rows, family_drop=5.0, in_dist_drop=1.5)
    always = harm.harm_measure(h0['hits'], hN['hits'], rows, family_drop=5.0, in_dist_drop=1.5)
    return hm, always, dict(n=len(rows), dev_sha256=dev_sha, routed_on=sum(on) / len(on))


def night_progress(nights_dir, stop):
    """-> progress on the first 50 sealed worlds per night 0..stop, or None when a file is missing."""
    out = []
    for k in range(stop + 1):
        path = os.path.join(nights_dir, f'night_{k}.json')
        if not os.path.exists(path):
            return None
        pw = json.load(open(path))['per_world'][:50]
        out.append(100.0 * sum(w['n_unlocks'] for w in pw) / (play.ACHIEVEMENTS * len(pw)))
    return out


# ---------- report ----------

def md_table(head, rows):
    return '\n'.join(['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)] +
                     ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows])


def render(R):
    L = [f'# Game-world result (run {R["run"]})', '', 'Sealed scoring on 100 worlds; one seed only.', '']
    L.append(md_table(['mark', 'verdict', 'value', 'bar'],
                      [[k, v['verdict'], v.get('value', ''), v.get('bar', '')] for k, v in R['marks'].items()]))
    for k, v in R['marks'].items():
        extra = {x: v[x] for x in ('lo', 'hi', 'fired', 'hair_miss_used', 'note') if v.get(x) not in (None, False)}
        if extra:
            L.append(f'\n{k}: {json.dumps(extra)}')
    L += ['', '## Per-achievement unlock share (percent of sealed worlds)', '']
    arms = R['arms']
    L.append(md_table(['achievement'] + list(arms), [[a] + [f'{arms[n]["share"][a]:.1f}' for n in arms] for a in ACH]))
    L += ['', md_table(['arm', 'unlocks/episode', 'progress %', 'Crafter score %', 'mean length', 'own-action share'],
                       [[n, f'{x["mean_unlocks"]:.3f}', f'{x["progress"]:.2f}', f'{x["crafter_score"]:.2f}',
                         f'{x["mean_length"]:.1f}', f'{x["sources_share"]["own"]:.3f}'] for n, x in arms.items()])]
    L += ['', '## Paired differences in unlocks per episode (95% bootstrap, 2000 draws)', '']
    L.append(md_table(['difference', 'mean', 'low', 'high'], [[k, f'{v[0]:+.3f}', f'{v[1]:+.3f}', f'{v[2]:+.3f}']
                                                            for k, v in R['differences'].items()]))
    s = R['run_summary']
    L += ['', '## The run', '', f'stop reason: {s.get("stop_reason")}; nights run: {s.get("nights_run")}',
          f'quiz curve (progress %, night 0 first): {s.get("quiz_history")}',
          f'rows per night: {s.get("rows_per_night")}',
          f'game steps used: practice {s.get("game_steps")}, quiz {s.get("quiz_steps")}']
    if R.get('night_progress'):
        L.append(f'sealed progress on first 50 worlds per night: {[round(x, 2) for x in R["night_progress"]]}')
    if R.get('old_skills'):
        o = R['old_skills']
        L.append(f'old skills: routed drop {o["routed"]["in_dist_drop"]:.2f} (fired {o["routed"]["fired"]}); '
                 f'add-on always on: drop {o["always_on"]["in_dist_drop"]:.2f} (fired {o["always_on"]["fired"]}); '
                 f'switch sent {o["info"]["routed_on"]:.3f} of DEV rows to the add-on')
    return '\n'.join(L) + '\n'


def analyze(a):
    run, out = os.path.abspath(a.run), os.path.abspath(a.out)
    os.makedirs(os.path.join(out, 'cache'), exist_ok=True)
    summary = json.load(open(os.path.join(run, 'summary.json')))
    B, A, Rn = (json.load(open(p)) for p in (a.before, a.after, a.random))
    P = json.load(open(a.ppo)) if a.ppo else None
    arms = {'before': B, 'after': A, 'random': Rn, **({'ppo': P} if P else {})}
    diffs = {'after - before': paired(A, B), 'after - random': paired(A, Rn)}
    if P:
        diffs['after - ppo'] = paired(A, P)
    for item in getattr(a, 'extra_diff', None) or []:
        label, _, path = item.partition('=')
        assert label and path, f'--extra-diff wants LABEL=FILE, got {item!r}'
        diffs[f'after - {label}'] = paired(A, json.load(open(path)))
    marks = {}
    d, lo, _ = diffs['after - before']
    marks['GW1'] = gw1_rule(d, lo)
    marks['GW2'] = gw2_rule(A['share']['make_wood_pickaxe'])
    marks['GW2']['ladder_share'] = {n: {k: x['share'][k] for k in LADDER} for n, x in arms.items()}
    if P:
        e, _, hi = diffs['after - ppo']
        marks['GW3'] = gw3_rule(e, hi)
    else:
        marks['GW3'] = dict(verdict='UNSCORED', note='no --ppo given')
    final = summary.get('final_checkpoint')
    old = None
    if a.dev and os.path.exists(os.path.join(run, 'gate.pt')) and final:
        hm, always, info = old_skills(run, a.parent, final, a.dev, os.path.join(out, 'cache'))
        marks['GW4'] = gw4_rule(hm)
        old = dict(routed=hm, always_on=always, info=info)
    else:
        marks['GW4'] = dict(verdict='UNSCORED', note='needs --dev, RUN_DIR/gate.pt and a final checkpoint')
    marks['GW5'] = gw5_rule(gaudit.audit_run(run))
    stop, npro = int(summary.get('nights_run', 0)), None
    if a.nights_dir and stop >= 1:
        npro = night_progress(a.nights_dir, stop)
    marks['GW6'] = gw6_rule(npro) if npro else dict(verdict='UNSCORED', note='needs --nights-dir night_K.json up to the stop night')
    R = dict(run=run, parent=a.parent, final_checkpoint=final, marks=marks,
             arms={n: {k: v for k, v in x.items() if k != 'per_world'} for n, x in arms.items()},
             differences={k: list(v) for k, v in diffs.items()}, night_progress=npro, old_skills=old,
             run_summary={k: summary.get(k) for k in ('nights_run', 'stop_reason', 'quiz_history', 'rows_per_night',
                                                      'game_steps', 'quiz_steps')})
    with open(os.path.join(out, 'RESULT.json'), 'w') as f:
        json.dump(R, f, indent=1, default=str)
    md = render(R)
    with open(os.path.join(out, 'RESULT.md'), 'w') as f:
        f.write(md)
    print(md)
    return R


def main(argv=None):
    ap = argparse.ArgumentParser(description='Marks GW1-GW6 for one game-world run.')
    ap.add_argument('--run', required=True)
    ap.add_argument('--parent', required=True)
    ap.add_argument('--before', required=True)
    ap.add_argument('--after', required=True)
    ap.add_argument('--random', required=True)
    ap.add_argument('--ppo')
    ap.add_argument('--extra-diff', action='append', default=[], metavar='LABEL=FILE',
                    help='add a paired row "after - LABEL" against another game.score output (repeatable)')
    ap.add_argument('--nights-dir')
    ap.add_argument('--dev')
    ap.add_argument('--out', required=True)
    ap.add_argument('--threads', type=int, default=2)
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    analyze(a)


if __name__ == '__main__':
    main()
