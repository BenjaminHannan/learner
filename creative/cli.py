"""python3 -m creative.cli <command>   (nothing here trains; dev-gate and lesions only sample from a checkpoint)
  build-splits [--out creative/data/c1]    write the sealed C1 splits and MANIFEST.json (deterministic; re-run = same hashes)
  floors [--split dev] [--uniform-samples N]   S0: per-try and pass@4 floors for B2's slots (rules-only exact, uniform Monte-Carlo)
  dev-gate --ckpt PATH [--temps 0.7,1,1.3,1.6,2] [--device cpu]   choose the temperature on DEV (reach@4), then the signal gate (an accepted try on
                  >= 100 distinct practice puzzles), the aim gate (luck / rules share >= 0.082) and the sameness gate (>= 4 distinct rule-following programs),
                  variety with and without branching, and the aim check (own vs twin vs value-blind rule follower)
  aim --ckpt PATH --temperature T          the aim check alone (run it on W after sleep too)
  score --ckpt PATH --split x              the scoreboard on any split (X = correct-solution variety, report only)
  pilot --ckpt PATH --out DIR --skills-train WORK/data/train.jsonl --skills-data WORK/data_big   DEV-only pilot: warm-up ladder, re-chosen temperature,
                  gates, aim check, PC lr choice and PC gate with skills replay (reads no T1/T1b/X)
  lesions --ckpt PATH --temperature T      donor lesion (must not beat the rules-only floor) and loops:0 (reported) on a slept checkpoint"""
import argparse, json, os, sys
from creative import puzzles

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'c1')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['build-splits', 'floors', 'dev-gate', 'aim', 'score', 'lesions', 'pilot'])
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
    ap.add_argument('--practice-limit', type=int)
    ap.add_argument('--lrs', default='3e-4,1e-3,3e-3,1e-2')
    ap.add_argument('--ladder', default='1500', help='pilot: warm-up 3-number puzzle counts, smallest passing the gates wins (decided 10-06: 1500; 3000,6000 are comparison runs)')
    ap.add_argument('--fallbacks', action='store_true', help='pilot: after the last rung fails, try fallbacks a (16 visits) and b (dreams)')
    ap.add_argument('--dreams', type=int, default=3000)
    ap.add_argument('--level', type=int, default=4, help='try sampler: 4 = C1 (used-number + exact-division mask, decided 10-06), 0 = plain sampler (labelled comparison only)')
    ap.add_argument('--skills-data', help='pilot: custom_io data dir with dev/in_dist.jsonl (use WORK/data_big) for the skills score / warm-up harm')
    ap.add_argument('--skills-train', help='skills train.jsonl for replay (pilot); without it warm-up harm is not measured')
    a = ap.parse_args(argv)
    if a.cmd == 'build-splits':
        print(json.dumps(puzzles.write_splits(a.out), indent=1, sort_keys=True))
        return
    if a.cmd == 'pilot':
        from creative import pilot
        pilot.pilot(a.ckpt, a.out, a.data, a.device, a.skills_train, a.skills_data, ladder=tuple(int(x) for x in a.ladder.split(',')),
                    lrs=tuple(float(x) for x in a.lrs.split(',')), tries=a.tries, practice_limit=a.practice_limit, fallbacks=a.fallbacks, dreams_n=a.dreams, level=a.level,
                    log=lambda d: print(json.dumps(d), flush=True))
        return
    rows = puzzles.load_split(a.data, a.split)[:a.limit]
    if a.cmd == 'floors':
        rules = [puzzles.rules_only_floor(r['nums'], r['target']) for r in rows]
        uni = [puzzles.uniform_floor(r['nums'], r['target'], a.uniform_samples, seed=i) for i, r in enumerate(rows)]
        n = len(rows)
        ex = [puzzles.rules_only_floor(r['nums'], r['target'], exact=True) for r in rows]
        print(json.dumps(dict(split=a.split, n=n, exact_legal_per_try=sum(ex) / n, exact_legal_pass4=sum(puzzles.pass_at(p, 4) for p in ex) / n,
                              exact_legal_pass32=sum(puzzles.pass_at(p, 32) for p in ex) / n, rules_only_per_try=sum(rules) / n, rules_only_pass4=sum(puzzles.pass_at(p, 4) for p in rules) / n,
                              rules_only_pass32=sum(puzzles.pass_at(p, 32) for p in rules) / n, uniform_per_try=sum(uni) / n,
                              uniform_pass4=sum(puzzles.pass_at(p, 4) for p in uni) / n, uniform_samples=a.uniform_samples), indent=1))
        return
    from creative import sleep, scoreboard, sampler
    model, vocab, meta = sleep.load_parent(a.ckpt, a.device)
    model.eval()
    if a.cmd == 'dev-gate':
        best, grid = scoreboard.tune_temperature(model, rows, vocab, a.device, [float(x) for x in a.temps.split(',')], a.tries, level=a.level)
        tr, raw = sampler.sample_tries(model, rows, vocab, a.device, a.tries, best, level=a.level)
        nb, _ = sampler.sample_tries(model, rows, vocab, a.device, a.tries, best, branch=0, level=a.level)
        prac = puzzles.load_split(a.data, 'practice')[:a.practice_limit]
        ptr, _ = sampler.sample_tries(model, prac, vocab, a.device, a.tries, best, level=a.level)
        g = scoreboard.dev_gate(rows, tr, raw, nb, (prac, ptr))
        aim = scoreboard.aim_check(model, rows, vocab, a.device, a.tries, best, level=a.level)
        print(json.dumps(dict(temperature=best, grid={str(k): v for k, v in grid.items()}, gate=g, aim=aim), indent=1))
    elif a.cmd == 'aim':
        print(json.dumps(scoreboard.aim_check(model, rows, vocab, a.device, a.tries, a.temperature, level=a.level), indent=1))
    elif a.cmd == 'score':
        tr, raw = sampler.sample_tries(model, rows, vocab, a.device, a.tries, a.temperature, level=a.level)
        s = scoreboard.score_puzzles(rows, tr, raw, sampler.greedy_tries(model, rows, vocab, a.device))
        s.pop('per_puzzle')
        print(json.dumps(s, indent=1))
    else:
        print(json.dumps(scoreboard.lesions(model, rows, vocab, a.device, a.tries, a.temperature, level=a.level), indent=1))

if __name__ == '__main__':
    main()
