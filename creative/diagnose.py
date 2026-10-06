"""Read-only diagnosis: why do DEV tries break the rules? No training, no sealed split. For a checkpoint (raw parent or warmed.pt) and temperatures:
rules share of the greedy first try, of kept tries with and without first-step branching, and which rule the rule-breaking tries break (checker reason)."""
import collections, json
from creative import puzzles, sampler, scoreboard, sleep
from creative.checkers import verdict


def reasons(rows, recs):
    c = collections.Counter()
    for r, x in zip(rows, recs):
        v, why = verdict(r['nums'] + [r['target']], len(r['nums']), x.t, check_value=False)
        c['follows rules' if v == 'accept' else why] += 1
    return {k: round(n / max(len(recs), 1), 3) for k, n in c.most_common()}


def warm(ckpt, data, out, n3=6000, visits=4, device='cpu', skills_train=None, warm_n=1500, lr=3e-4, batch=64, seed=0):
    """Re-make a warmed parent exactly as the pilot's rung does (the pilot only saves warmed.pt when a rung passes) and save it to `out`."""
    import copy
    from creative import arms
    m, vocab, meta = sleep.load_parent(ckpt, device)
    replay = sleep.load_replay(skills_train, None, seed) if skills_train else []
    wu = [arms.record(r, t, 'WU', 0) for r, t in puzzles.warmup_rows(warm_n, seed, per_pair=3)]
    wu += [arms.record(r, t, 'WU3', 0) for r, t in puzzles.warmup3_rows(n3, seed)]
    cfg = sleep.SleepCfg(updates=sleep.max_updates(len(wu), batch, bool(replay), visits), batch=batch, lr=lr, warmup=20, seed=seed, max_visits=visits)
    sleep.sleep(m, wu, replay, vocab, cfg, device)
    sleep.save_parent(m, meta['name'], meta['cfg'], vocab, out, step=(meta['step'] or 0) + cfg.updates, warmup=True, warm3=n3)
    return out


def diagnose(ckpt, data, temps=(0.21, 0.7, 2.0), device='cpu', tries=32, limit=None):
    m, vocab, _ = sleep.load_parent(ckpt, device)
    m.eval()
    dev = puzzles.load_split(data, 'dev')[:limit]
    out = dict(ckpt=ckpt, n_puzzles=len(dev))
    g = sampler.greedy_tries(m, dev, vocab, device)
    out['greedy'] = dict(rules_share=reasons(dev, g).get('follows rules', 0.0), reasons=reasons(dev, g),
                         hit=sum(scoreboard.judge_try(r, x) == 'accept' for r, x in zip(dev, g)) / len(dev))
    for T in temps:
        for name, br in (('branch8', 8), ('nobranch', 0)):
            tr, raw = sampler.sample_tries(m, dev, vocab, device, tries, T, branch=br)
            flat_rows = [r for r, t in zip(dev, tr) for _ in t]
            flat = [x for t in tr for x in t]
            out[f'T{T}_{name}'] = dict(kept=len(flat), raw_per_puzzle=sum(raw) / len(dev), reasons=reasons(flat_rows, flat))
    return out


if __name__ == '__main__':
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument('--ckpt', required=True); a.add_argument('--data', required=True); a.add_argument('--limit', type=int)
    a.add_argument('--warm-to', help='first re-make the warmed parent (6,000 rung, 4 visits) and save it here'); a.add_argument('--visits', type=int, default=4)
    a.add_argument('--skills-train'); a.add_argument('--device', default='cpu')
    a = a.parse_args()
    ck = warm(a.ckpt, a.data, a.warm_to, visits=a.visits, device=a.device, skills_train=a.skills_train) if a.warm_to else a.ckpt
    print(json.dumps(diagnose(ck, a.data, device=a.device, limit=a.limit), indent=1))
