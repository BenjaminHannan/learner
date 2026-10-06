"""python3 -m creative.cli <command>   (nothing here trains; dev-gate and lesions only sample from a checkpoint)
  build-splits [--out creative/data/c1]    write the sealed C1 splits and MANIFEST.json (deterministic; re-run = same hashes)
  floors [--split dev] [--uniform-samples N]   S0: per-try and pass@4 floors for B2's slots (rules-only exact, uniform Monte-Carlo)
  dev-gate --ckpt PATH [--split dev] [--temps 0.7,1,1.3,1.6,2] [--device cpu]   choose the temperature on DEV, then the cold-start and sameness gates
  lesions --ckpt PATH --temperature T [--split dev]   loops:0 and donor lesions on a (slept) checkpoint"""
import argparse, json, os, sys
from creative import puzzles

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'c1')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['build-splits', 'floors', 'dev-gate', 'lesions'])
    ap.add_argument('--out', default=DATA)
    ap.add_argument('--data', default=DATA)
    ap.add_argument('--split', default='dev')
    ap.add_argument('--ckpt')
    ap.add_argument('--temps', default='0.7,1.0,1.3,1.6,2.0')
    ap.add_argument('--temperature', type=float, default=1.0)
    ap.add_argument('--device', default='cpu')
    ap.add_argument('--tries', type=int, default=32)
    ap.add_argument('--uniform-samples', type=int, default=3000)
    ap.add_argument('--limit', type=int)
    a = ap.parse_args(argv)
    if a.cmd == 'build-splits':
        print(json.dumps(puzzles.write_splits(a.out), indent=1, sort_keys=True))
        return
    rows = puzzles.load_split(a.data, a.split)[:a.limit]
    if a.cmd == 'floors':
        rules = [puzzles.rules_only_floor(r['nums'], r['target']) for r in rows]
        uni = [puzzles.uniform_floor(r['nums'], r['target'], a.uniform_samples, seed=i) for i, r in enumerate(rows)]
        n = len(rows)
        print(json.dumps(dict(split=a.split, n=n, rules_only_per_try=sum(rules) / n, rules_only_pass4=sum(puzzles.pass_at(p, 4) for p in rules) / n,
                              rules_only_pass32=sum(puzzles.pass_at(p, 32) for p in rules) / n, uniform_per_try=sum(uni) / n,
                              uniform_pass4=sum(puzzles.pass_at(p, 4) for p in uni) / n, uniform_samples=a.uniform_samples), indent=1))
        return
    from creative import sleep, scoreboard, sampler
    model, vocab, meta = sleep.load_parent(a.ckpt, a.device)
    model.eval()
    if a.cmd == 'dev-gate':
        best, grid = scoreboard.tune_temperature(model, rows, vocab, a.device, [float(x) for x in a.temps.split(',')], a.tries)
        tr, raw = sampler.sample_tries(model, rows, vocab, a.device, a.tries, best)
        g = scoreboard.dev_gate(rows, tr, raw)
        print(json.dumps(dict(temperature=best, grid={str(k): v for k, v in grid.items()}, gate=g), indent=1))
    else:
        print(json.dumps(scoreboard.lesions(model, rows, vocab, a.device, a.tries, a.temperature), indent=1))


if __name__ == '__main__':
    main()
