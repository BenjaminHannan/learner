"""The creative scoreboard for C1 (roadmap section 1) and the DEV variety gate (section 6).

score_puzzles(): per-puzzle verdicts from the two checkers, then luck, reach@4 / reach@32, variety, STOP-rule luck, own-vs-twin aim.
Reach@4 is the expected value over random 4-tries subsets of the kept tries (hypergeometric), so the branch order never decides it."""
from math import comb
from creative.checkers import verdict
from creative.programs import NOOP, cone, result_key, run
from creative.sampler import C1_LEVEL

PRACTICE_SOLVED_MIN = 100   # signal gate: an accepted try on at least 100 distinct practice puzzles
BLIND_EXACT_FLOOR = 0.0402      # DEV, exact legal programs (C1's mask): the value-blind follower's per-try luck = mean puzzles.rules_only_floor(exact=True) (shown, PR #44)
AIM_MIN = 2 * BLIND_EXACT_FLOOR # aim gate: luck / rules_share >= twice that floor (0.0804); under the mask rules_share is ~1; it is reported, never gated
SAMENESS_MIN = 4.0          # sameness gate: >= 4 distinct rule-following programs per puzzle on average (canonical key)


def reach_at(c, m, k):
    """P(at least one accepted in k tries drawn without replacement from m kept tries holding c accepted)."""
    if c == 0 or m == 0:
        return 0.0
    if m <= k:
        return 1.0
    return 1 - comb(m - c, k) / comb(m, k)


def is_clean(t):
    """STOP rule: the written steps are exactly the answer cone, first, then NOOP (nothing written off the tree)."""
    c = cone(t)
    return c is not None and c == list(range(len(c))) and all(op == NOOP for op in t.ops[len(c):])


def judge_try(row, rec, rules_only=False):
    nums = row['nums'] + [row['target']]
    return verdict(nums, len(row['nums']), rec.t, check_value=not rules_only)[0]


def score_puzzles(rows, tries, raw=None, greedy=None):
    """rows: puzzle rows (with 'twin' on TWINS splits); tries[i]: list of TryRec; raw[i]: programs sampled; greedy[i]: one TryRec per row.
    -> dict of pooled scores plus 'per_puzzle' details. All shares are over kept (distinct) tries."""
    per, n_t = [], 0
    tot = dict(acc=0, tries=0, rules=0, unres=0, clean=0, twin=0, raw=0)
    for i, row in enumerate(rows):
        nums = row['nums'] + [row['target']]
        verds = [judge_try(row, r) for r in tries[i]]
        rules = [judge_try(row, r, rules_only=True) == 'accept' for r in tries[i]]
        acc = [v == 'accept' for v in verds]
        clean = [a and is_clean(r.t) for a, r in zip(acc, tries[i])]
        keys = {result_key(r.t, run(nums, r.t)[1]) for r in tries[i]}
        keys.discard('dead')
        acc_keys = {result_key(r.t, run(nums, r.t)[1]) for r, a in zip(tries[i], acc) if a}
        rule_keys = {result_key(r.t, run(nums, r.t)[1]) for r, ok in zip(tries[i], rules) if ok}
        d = dict(id=row['id'], m=len(tries[i]), c=sum(acc), distinct=len(keys), distinct_accepted=len(acc_keys), distinct_rules=len(rule_keys),
                 reach4=reach_at(sum(acc), len(acc), 4), reach32=float(any(acc)))
        if 'twin' in row:
            tw = row['twin']
            tn = row['nums'] + [tw['target']]
            d['twin_c'] = sum(verdict(tn, len(row['nums']), r.t, target=tw['target'])[0] == 'accept' for r in tries[i])
            tot['twin'] += d['twin_c']
        if greedy is not None:
            d['first'] = float(judge_try(row, greedy[i]) == 'accept')
        per.append(d)
        tot['acc'] += sum(acc); tot['tries'] += len(acc); tot['rules'] += sum(rules); tot['clean'] += sum(clean)
        tot['unres'] += sum(v == 'unresolved' for v in verds)
        tot['raw'] += (raw[i] if raw is not None else len(acc))
    n = len(rows)
    out = dict(n_puzzles=n, n_tries=tot['tries'], luck=tot['acc'] / max(tot['tries'], 1),
               stop_luck=tot['clean'] / max(tot['tries'], 1), rules_share=tot['rules'] / max(tot['tries'], 1),
               unresolved=tot['unres'] / max(tot['tries'], 1), reach4=sum(d['reach4'] for d in per) / n,
               reach32=sum(d['reach32'] for d in per) / n, distinct=sum(d['distinct'] for d in per) / n,
               distinct_accepted=sum(d['distinct_accepted'] for d in per) / n, distinct_rules=sum(d['distinct_rules'] for d in per) / n, kept_per_puzzle=tot['tries'] / n,
               raw_per_puzzle=tot['raw'] / n)
    if raw is not None:
        out['dup_drop_rate'] = 1 - tot['tries'] / max(tot['raw'], 1)
    if rows and 'twin' in rows[0]:
        out['twin_luck'] = tot['twin'] / max(tot['tries'], 1)
        out['aim'] = out['luck'] - out['twin_luck']
    if greedy is not None:
        out['first_try'] = sum(d['first'] for d in per) / n
    out['per_puzzle'] = per
    return out


def dev_gate(rows, tries, raw=None, nobranch=None, practice=None):
    """The gates on DEV after warm-up (roadmap section 6, rewritten 10-06 after the second pilot).
      signal:   the warmed parent has an accepted try on >= 100 distinct practice puzzles (practice = (practice_rows, practice_tries), 32 tries each).
      aim:      among its rule-following tries the share that hit the target (luck / rules_share) is >= 2x the value-blind rule follower's
                (exact legal programs, 4.02%), i.e. >= 0.0804. A feasibility check, not a claim (G0 is the claim). The share of tries that follow the rules is
                REPORTED, never gated: the follower's own share is only 58%, so any bar near 50% asks for near-perfect legality, not signal.
      sameness: distinct rule-following programs (canonical key) >= 4 per puzzle on average, with the sampler's branching on.
    Reported, not gated: rules_share, reach@4 / @32, the old result-changing count `distinct`, and the variety without branching (nobranch = tries
    sampled with branch=0). A failed gate stops C1 with T1 sealed: signal -> fix the warm-up; aim -> the warm-up taught format but no aim;
    sameness -> C3b first.   -> dict(signal_ok, aim_ok, sameness_ok, verdict, ...)."""
    s = score_puzzles(rows, tries, raw)
    hit_given_rules = s['luck'] / s['rules_share'] if s['rules_share'] > 0 else 0.0
    out = dict(rules_share=s['rules_share'], distinct_rules=s['distinct_rules'], distinct=s['distinct'], luck=s['luck'], reach4=s['reach4'],
               reach32=s['reach32'], hit_given_rules=hit_given_rules, dup_drop_rate=s.get('dup_drop_rate'), unresolved=s['unresolved'])
    if nobranch is not None:
        sn = score_puzzles(rows, nobranch)
        out.update(nobranch_distinct_rules=sn['distinct_rules'], nobranch_distinct=sn['distinct'], nobranch_rules_share=sn['rules_share'])
    solved = None
    if practice is not None:
        solved = sum(any(judge_try(r, x) == 'accept' for x in t) for r, t in zip(*practice))
        out['practice_solved'] = solved
    sig = solved is not None and solved >= PRACTICE_SOLVED_MIN
    aim = hit_given_rules >= AIM_MIN
    same = s['distinct_rules'] >= SAMENESS_MIN
    bad = [n for n, ok in (('signal (fix the warm-up)', sig), ('aim (warm-up taught the format, not aim)', aim), ('sameness (C3b first)', same)) if not ok]
    v = 'pass' if not bad else 'stop: ' + ' and '.join(bad)
    if practice is None:
        v += ' [practice puzzles not given: signal gate incomplete]'
    out.update(signal_ok=sig, aim_ok=aim, sameness_ok=same, verdict=v)
    return out


def choose_temperature(model, rows, vocab, device, grid=(0.7, 1.0, 1.5, 2.0), n_tries=32, seed=0, max_widen=3, log=None, level=C1_LEVEL):
    """Choose the sampling temperature on DEV only (roadmap section 6, 10-06): the highest reach@4, only among temperatures that pass the sameness gate
    (>= 4 distinct rule-following programs per puzzle). If the choice lands on a grid edge, widen the grid there (x1.5 up / /1.5 down, rounded) and choose
    again, up to max_widen times. None eligible -> best = None. Frozen afterwards.
    -> dict(best, evaluated {T: dict(reach4, reach32, distinct_rules, rules_share, eligible)}, widened, edge_note)."""
    from creative.sampler import sample_tries
    ev = {}

    def evaluate(T):
        if T not in ev:
            tr, raw = sample_tries(model, rows, vocab, device, n_tries=n_tries, temperature=T, seed=seed, level=level)
            s = score_puzzles(rows, tr, raw)
            ev[T] = dict(reach4=s['reach4'], reach32=s['reach32'], distinct_rules=s['distinct_rules'], rules_share=s['rules_share'],
                         eligible=s['distinct_rules'] >= SAMENESS_MIN)
            if log:
                log(dict(event='temperature', T=T, **ev[T]))
    pick = lambda: max((T for T in ev if ev[T]['eligible']), key=lambda T: (ev[T]['reach4'], ev[T]['distinct_rules']), default=None)
    for T in grid:
        evaluate(T)
    widened, note = 0, None
    while widened < max_widen:
        best = pick()
        lo, hi = min(ev), max(ev)
        if best is None or best not in (lo, hi):
            break
        widened += 1
        evaluate(round(hi * 1.5, 2) if best == hi else round(lo / 1.5, 2))
    best = pick()
    if best is not None and best in (min(ev), max(ev)):
        note = 'best temperature is still on the grid edge after widening'
    return dict(best=best, evaluated={str(k): v for k, v in sorted(ev.items())}, widened=widened, edge_note=note)


def tune_temperature(model, rows, vocab, device, grid=(0.7, 1.0, 1.5, 2.0), n_tries=32, seed=0, level=C1_LEVEL):
    """Compat wrapper: (best, {T: (reach4, distinct_rules)}). best falls back to the grid's best reach@4 when no temperature passes sameness."""
    r = choose_temperature(model, rows, vocab, device, grid, n_tries, seed, level=level)
    grid_ = {float(k): (v['reach4'], v['distinct_rules']) for k, v in r['evaluated'].items()}
    return (r['best'] if r['best'] is not None else max(grid_, key=lambda T: grid_[T])), grid_


def lesions(model, rows, vocab, device, n_tries=32, temperature=1.0, seed=0, level=C1_LEVEL):
    """C1's lesion (roadmap section 6): DONOR ONLY. Tries sampled on the TWIN puzzle's prompt (same numbers, the other target) and judged on the
    recipient's own target must not score above the rules-only floor; otherwise the run is void. loops0_luck (loops:0 writes no steps, so 0 by
    construction) is reported, not a test. Run on W after sleep. -> dict(luck, donor_luck, rules_floor, donor_ok, loops0_luck)."""
    from creative.puzzles import rules_only_floor
    from creative.sampler import sample_tries
    tr, raw = sample_tries(model, rows, vocab, device, n_tries, temperature, seed=seed, level=level)
    t0, _ = sample_tries(model, rows, vocab, device, n_tries, temperature, seed=seed, loops=0)       # plain sampler: loops:0 writes nothing (0 by construction)
    td, _ = sample_tries(model, [r['twin'] for r in rows], vocab, device, n_tries, temperature, seed=seed, level=level)
    share = lambda rs, ts: sum(judge_try(r, x) == 'accept' for r, t in zip(rs, ts) for x in t) / max(sum(len(t) for t in ts), 1)
    floor = sum(rules_only_floor(r['nums'], r['target'], exact=bool(level)) for r in rows) / len(rows)
    donor = share(rows, td)
    return dict(luck=share(rows, tr), donor_luck=donor, rules_floor=floor, donor_ok=donor <= floor, loops0_luck=share(rows, t0))


def aim_check(model, rows, vocab, device, n_tries=32, temperature=1.0, seed=0, level=C1_LEVEL):
    """AIM CHECK on DEV (a report, not a gate; no training), same tries and checker throughout:
      own:   the model's tries for the real target, judged on the real target
      twin:  the model's tries for the TWIN target, judged on the real target
      rules: the value-blind rule follower (random rule-following programs, same dedup), judged on the real target
    Luck and reach@4 for each. If rules matches own, search is still random and G0 decides whether sleep taught aim. Repeat on W after sleep."""
    from creative.sampler import rule_follower_tries, sample_tries
    own, raw = sample_tries(model, rows, vocab, device, n_tries, temperature, seed=seed, level=level)
    twin, _ = sample_tries(model, [r['twin'] for r in rows], vocab, device, n_tries, temperature, seed=seed, level=level)
    rf = rule_follower_tries(rows, n_tries, seed, exact=bool(level))
    out = {}
    for name, tr in (('own', own), ('twin', twin), ('rules', rf)):
        sc = score_puzzles(rows, tr)                     # twin tries are scored on the real rows (rows[i] has the real target)
        out[name] = dict(luck=sc['luck'], reach4=sc['reach4'], reach32=sc['reach32'], distinct_rules=sc['distinct_rules'], rules_share=sc['rules_share'])
    out['own_minus_rules_luck'] = out['own']['luck'] - out['rules']['luck']
    out['own_minus_twin_luck'] = out['own']['luck'] - out['twin']['luck']
    return out
