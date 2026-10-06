"""Read-only DEV probe for the rule-masked sampler (creative/legal.py): no training, no sealed split.
For one parent (raw or warmed): greedy first try and kept tries (32, first-step branching on) at each mask level and temperature, the generation-order
first rule break of every rule-breaking try, the value-blind follower, and the aim check (twin-prompt tries judged on the real target).
  python3 -m creative.legal_probe --ckpt warmed.pt --data creative/data/c1 --temps 0.21,1.0 --levels 0,3,4 --aim-temps 0.21 --out probe.json"""
import collections, json, time
from creative import legal, puzzles, sampler, scoreboard, sleep
from creative.checkers import verdict
from creative.programs import ARITH, R0, run

CONST = set(range(16, 20))


def first_error(row, t):
    """Generation-order first break of a rule-breaking try: k-1 real steps (op, operand a, operand b, exact result), then the answer pointer."""
    k = len(row['nums'])
    vals, valid = run(row['nums'] + [row['target']], t)
    avail = set(range(k))
    for s in range(k - 1):
        op, a, b = t.ops[s], t.a[s], t.b[s]
        if op not in ARITH:
            return f'step{s + 1} op ' + ('NOOP' if op == 0 else 'MOD/MIN/MAX/CMP')
        for name, x in (('a', a), ('b', b)):
            if x in CONST:
                return f'step{s + 1} {name}=constant'
            if x == k:
                return f'step{s + 1} {name}=target'
            if x not in avail:
                return f'step{s + 1} {name}=spent number'
        if a == b:
            return f'step{s + 1} a==b'
        if not valid[R0 + s]:
            return f'step{s + 1} inexact division'
        avail -= {a, b}
        avail.add(R0 + s)
    return 'answer not on last result' if t.ans != R0 + k - 2 else 'other'


def breakdown(rows, tries):
    c, n, ok = collections.Counter(), 0, 0
    for row, tr in zip(rows, tries):
        for r in tr:
            n += 1
            if verdict(row['nums'] + [row['target']], len(row['nums']), r.t, check_value=False, replay=False)[0] == 'accept':
                ok += 1
            else:
                c[first_error(row, r.t)] += 1
    return dict(n=n, rules_share=round(ok / max(n, 1), 4), first_error={k: round(v / max(n, 1), 4) for k, v in c.most_common(10)})


def summary(rows, tries, raw=None):
    s = scoreboard.score_puzzles(rows, tries, raw)
    return {k: round(s[k], 4) for k in ('rules_share', 'distinct_rules', 'luck', 'reach4', 'reach32', 'kept_per_puzzle')}


def probe(ckpt, data, temps=(0.21, 1.0), levels=(0, 3, 4), aim_temps=(0.21,), device='cpu', tries=32, out=None, log=print):
    m, vocab, _ = sleep.load_parent(ckpt, device)
    m.eval()
    dev = puzzles.load_split(data, 'dev')
    res, t0 = dict(ckpt=ckpt, n_puzzles=len(dev), tries=tries), time.time()
    save = lambda: out and json.dump(res, open(out, 'w'), indent=1)
    for L in levels:
        g = sampler._tries_from(legal.sample_run_masked(m, sampler.make_batch(dev, vocab, device), legal._k(dev), L, greedy=True))
        res[f'greedy_L{L}'] = dict(breakdown(dev, [[x] for x in g]), hit=sum(scoreboard.judge_try(r, x) == 'accept' for r, x in zip(dev, g)) / len(dev))
    res['follower'] = summary(dev, sampler.rule_follower_tries(dev, tries, 0))
    save()
    for T in temps:
        for L in levels:
            tr, raw = legal.sample_tries_masked(m, dev, vocab, device, tries, T, L, branch=8)
            r = res[f'T{T}_L{L}'] = summary(dev, tr, raw)
            if L == 0:
                r['first_error'] = breakdown(dev, tr)['first_error']
            if T in aim_temps:
                tw, _ = legal.sample_tries_masked(m, [x['twin'] for x in dev], vocab, device, tries, T, L, branch=8)
                sc = scoreboard.score_puzzles(dev, tw)
                r['twin_luck'], r['twin_reach4'] = round(sc['luck'], 4), round(sc['reach4'], 4)
            save()
            log(dict(T=T, level=L, **{k: v for k, v in r.items() if k != 'first_error'}, t=round(time.time() - t0)))
    return res


if __name__ == '__main__':
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument('--ckpt', required=True); a.add_argument('--data', required=True); a.add_argument('--out')
    a.add_argument('--temps', default='0.21,1.0'); a.add_argument('--levels', default='0,3,4'); a.add_argument('--aim-temps', default='0.21')
    a.add_argument('--device', default='cpu')
    a = a.parse_args()
    fl = lambda s: tuple(float(x) for x in s.split(',') if x)
    r = probe(a.ckpt, a.data, fl(a.temps), tuple(int(x) for x in a.levels.split(',')), fl(a.aim_temps), a.device, out=a.out)
    print(json.dumps(r, indent=1))
