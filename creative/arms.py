"""C1 arms: what each sleep trains on. Each differs from W in one thing, and they all use the same recipe (sleep.py).

  N   no sleep (the warmed parent): no records.
  W   its own accepted tries, at most 2 distinct programs per puzzle.
  R   placebo: its own RULE-FOLLOWING tries, chosen without looking at the value, from a separate pool, matched to W's puzzles and
      per-puzzle counts. (rules-only verdict; the value is never read when choosing.)
  H   hindsight: R's tries relabelled "make v" for the value v they actually made.
  H'  wrong relabel: R's tries relabelled to a value they did not make (blurt-4's control).
  PC  positive control: solver programs for W's puzzles, same count.
R, H and H' share the same tries, so H - R isolates the relabel and H - H' isolates the relabel being true.
Targets are the logged slot ids (forced replay): the accepted tree in the first steps, then NOOP (programs.train_form)."""
import random
from creative.checkers import verdict
from creative.programs import CONSTS, Try, register_targets, result_key, run, train_form
from creative.puzzles import T_MAX, make_row, solver_records, steps_text
from creative.scoreboard import judge_try


def record(row, rec_try, arm, k, target=None):
    """A training record for `rec_try` (a programs.Try) on the puzzle `row`, with the prompt's target replaced by `target` if given.
    Registers the forced slot ids under a unique id. -> row dict (family 'make_target') or None when the try has no cone."""
    tf = train_form(rec_try)
    if tf is None:
        return None
    steps, ans = tf
    target = row['target'] if target is None else target
    rid = f'{arm}:{row["id"]}:{k}'
    r = make_row(rid, row['nums'], target, row['split'])
    r['steps'] = steps_text(row['nums'] + [target], rec_try)
    r['arm'], r['source'] = arm, row['id']
    register_targets(rid, row['nums'] + [target], steps, ans)
    return r


def record_try(r):
    """The forced program registered for a record, as a programs.Try (inverse of record())."""
    from custom_io.models import progparse as pp
    c = pp._CACHE[r['id']]
    return Try.make([(o, ca[0], cb[0]) for o, ca, cb, _ in c['prog']], c['ans'][0])


def _value_of(row, t):
    vals, valid = run(row['nums'] + [row['target']], t)
    return vals[t.ans] if valid[t.ans] else None


def relabel_ok(row, v):
    """A value we may name as a target: 1 <= v <= T_MAX, not a B2 constant, not one of the given numbers (the puzzle's own T rules)."""
    return v is not None and 1 <= v <= T_MAX and v not in CONSTS and v not in row['nums']


def build_w(rows, tries, rng, per_cap=2):
    """-> (records, counts {puzzle id: n}). tries[i] = list of TryRec for rows[i]."""
    recs, counts = [], {}
    for row, tr in zip(rows, tries):
        acc = [r.t for r in tr if judge_try(row, r) == 'accept']
        rng.shuffle(acc)
        seen, kept = set(), []
        for t in acc:
            key = result_key(t, run(row['nums'] + [row['target']], t)[1])
            if key not in seen:
                seen.add(key)
                kept.append(t)
            if len(kept) == per_cap:
                break
        for k, t in enumerate(kept):
            r = record(row, t, 'W', k)
            if r:
                recs.append(r)
        if kept:
            counts[row['id']] = len(kept)
    return recs, counts


def _pool_choice(row, tr, n, rng):
    """n distinct rule-following tries (value-blind, but valid for relabelling), chosen by shuffling."""
    ok = []
    for r in tr:
        if judge_try(row, r, rules_only=True) == 'accept' and relabel_ok(row, _value_of(row, r.t)):
            ok.append(r.t)
    rng.shuffle(ok)
    seen, out = set(), []
    for t in ok:
        key = result_key(t, run(row['nums'] + [row['target']], t)[1])
        if key not in seen:
            seen.add(key)
            out.append(t)
        if len(out) == n:
            break
    return out


def build_placebo_family(rows, pool_tries, counts, rng):
    """R, H and H' from a separate pool of tries, matched to W's puzzles and counts.
    -> dict(R=[...], H=[...], Hw=[...], short={puzzle id: shortfall}, placebo_accepted_share=...). Hw = H' (wrong relabel)."""
    R, H, Hw, short, chosen = [], [], [], {}, []
    for row, tr in zip(rows, pool_tries):
        n = counts.get(row['id'], 0)
        if not n:
            continue
        picked = _pool_choice(row, tr, n, rng)
        if len(picked) < n:
            short[row['id']] = n - len(picked)
        for k, t in enumerate(picked):
            chosen.append((row, k, t, _value_of(row, t)))
    values = [c[3] for c in chosen]
    n_acc = 0
    for row, k, t, v in chosen:
        R.append(record(row, t, 'R', k))
        H.append(record(row, t, 'H', k, target=v))
        n_acc += v == row['target']
        wrong = [x for x in values if x != v and relabel_ok(row, x)]
        Hw.append(record(row, t, 'Hw', k, target=rng.choice(wrong) if wrong else (v + 1 if relabel_ok(row, v + 1) else v + 2)))
    n = max(len(chosen), 1)
    return dict(R=R, H=H, Hw=Hw, short=short, placebo_accepted_share=n_acc / n, n=len(chosen))


def placebo_too_close(fam):
    """Verdict rule: over half of R's records are accepted tries."""
    return fam['placebo_accepted_share'] > 0.5


def build_pc(rows, counts, rng):
    recs = []
    for row in rows:
        n = counts.get(row['id'], 0)
        for k, t in enumerate(solver_records(row, n, rng) if n else []):
            recs.append(record(row, t, 'PC', k))
    return recs


def build_arms(rows, tries, pool_tries, seed=0):
    """All arms for one parent. -> dict(N=[], W, R, H, Hw, PC, counts, diag)."""
    rng = random.Random(seed)
    W, counts = build_w(rows, tries, rng)
    fam = build_placebo_family(rows, pool_tries, counts, rng)
    return dict(N=[], W=W, R=fam['R'], H=fam['H'], Hw=fam['Hw'], PC=build_pc(rows, counts, rng), counts=counts,
                diag=dict(n_W=len(W), n_R=len(fam['R']), short=fam['short'], placebo_accepted_share=fam['placebo_accepted_share'],
                          placebo_too_close=placebo_too_close(fam)))
