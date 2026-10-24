"""Dream rows for C2's sleep (DreamCoder "fantasies" / CodeIt hindsight relabelling), built for the creative module's W path.

Why: sleep trains only on the model's own example-fitting tries (W records). Two-step rules (2x+c, x*x+c, a*x+b) are almost never found by search,
so they get no records and sleep never improves them. A dream row fixes the supply: draw a RANDOM program in B2's own executor language, run it on random
inputs, and write the result as a few-shot question in the exact C2 prompt format. The label is the program itself (forced-replay slot ids, as
creative/programs.py train_form / register_targets and creative/fewshot._record do for W records). No answer key and no rule-kind name is used anywhere.

The language (the same slots B2 points at, creative/programs.py): the query input x (slot q_slot = 2k for k examples), the four constants 1 2 10 100,
and earlier results. A program has 1..max_steps steps (max_steps=2 by default; lengths are dealt round-robin so the final set is balanced; rejection would otherwise leave mostly 1-step programs); each step is an op uniform over ADD SUB MUL DIV(exact) MOD MIN MAX (CMP is left out, as in
fewshot.SEARCH_OPS) and two operands uniform over the available slots (step 1: x and the constants; step 2: those plus step 1's result). Rejected and
redrawn (never named by kind): programs whose answer cone is shorter than the drawn length, that fail the C2 checker on any example or the query
(fewshot.verdict: structure, python ints AND B2's torch executor), whose outputs leave 0..MAX_OUT, whose example outputs equal a constant slot value
(1 2 10 100: the pointer would be ambiguous, as in rules_real), that give the same output on every example, or that are the identity on all four inputs.
Inputs: 3 examples + 1 query, distinct, from rules_real.DOMAIN (the same domain as the real C2 rows).

Disjointness: no dream prompt equals a prompt of the C2 warm / pool / dev splits (loaded through rules_real.load_split, which checks their sealed hashes),
and no dream's SET of example pairs {(x_i, y_i)} equals one of theirs (so a reordered copy of a real question is also out). Extra prompts can be passed in.
creative/data/c2/test.jsonl is NOT opened: the manifest holds only one sha256 of the whole file, no per-prompt hash list, so dreams are NOT checked against
the sealed test prompts. (An exact test-prompt match is unlikely but possible; it is disclosed, not excluded.)

kind_overlap(rows) is a disclosure number, not a filter: the share of dreams whose program is functionally identical to each held-out kind's form."""
from __future__ import annotations

import random
from typing import Iterable, Optional

from creative import fewshot as F
from creative import rules_real as R
from creative.programs import CONSTS, N_NUM, R0, Try, cone, run, train_form

DATA = 'creative/data/c2'
OPS_DSL = (1, 2, 3, 4, 5, 6, 7)             # ADD SUB MUL DIV MOD MIN MAX
K_EX = 3
MAX_OUT = 999
CONST_SLOTS = tuple(range(N_NUM, N_NUM + len(CONSTS)))
CONST_VALUES = tuple(CONSTS)
ARM = 'D2'
OCCAM_MAX_STEPS = 5
OCCAM_MAX_STATES = 200000


def _example_key(pairs) -> frozenset:
    return frozenset((int(x), int(y)) for x, y in pairs)


def real_keys(splits=('warm', 'pool', 'dev'), data=DATA):
    """-> (prompts set, example-pair-set keys set) of the C2 splits warm / pool / dev (sealed-hash checked). Never test."""
    prompts, keys = set(), set()
    for s in splits:
        assert s != 'test', 'the sealed test split is never read here'
        for r in R.load_split(data, s):
            prompts.add(r['prompt'])
            p = F.parse(r['prompt'])
            keys.add(_example_key(zip(p['xs'], p['ys'])))
    return prompts, keys


def sample_program(rng: random.Random, q_slot: int, length: int) -> Try:
    """One uniform draw from the `length`-step compositions (before any rejection)."""
    slots = [q_slot] + list(CONST_SLOTS)
    steps = []
    for s in range(length):
        steps.append((rng.choice(OPS_DSL), rng.choice(slots), rng.choice(slots)))
        slots.append(R0 + s)
    return Try.make(steps, R0 + len(steps) - 1)


def _draw(rng, avoid_prompts, avoid_keys, length, k_ex=K_EX, seen_p=(), seen_k=()):
    """-> (prompt, xs, ys, q, answer, Try, length) for one acceptable dream, or None for a rejected draw."""
    q_slot = 2 * k_ex
    t = sample_program(rng, q_slot, length)
    c = cone(t)
    if c is None or len(c) != length:                       # every drawn step must feed the answer
        return None
    xs_all = rng.sample(R.DOMAIN, k_ex + 1)
    xs, q = xs_all[:k_ex], xs_all[k_ex]
    outs = []
    for x in xs + [q]:
        nums = [0] * q_slot + [x]
        vals, valid = run(nums, t)
        if not valid[t.ans]:
            return None
        outs.append(vals[t.ans])
    if min(outs) < 0 or max(outs) > MAX_OUT or any(y in CONST_VALUES for y in outs[:-1]) or len(set(outs[:-1])) < 2 or outs == xs + [q]:
        return None
    ys, ans = outs[:-1], outs[-1]
    prompt = R.prompt_of(xs, ys, q)
    key = _example_key(zip(xs, ys))
    if prompt in avoid_prompts or prompt in seen_p or key in avoid_keys or key in seen_k:
        return None
    v = F.verdict(F.parse(prompt), t)                       # C2's checker: structure + python ints + B2's torch executor, every example
    if v[0] != 'accept' or v[2] != ans:
        return None
    return prompt, xs, ys, q, ans, t, length


_HELD_TABLES = None


def _held_tables():
    """Set of output tuples over R.DOMAIN of every held-out kind at every one of its PARAMS (strict mode's membership test)."""
    global _HELD_TABLES
    if _HELD_TABLES is None:
        _HELD_TABLES = frozenset(tab for (k, _p), tab in R._TABLE.items() if k in R.HELD_OUT)
    return _HELD_TABLES


def is_held_out_form(t: Try, q_slot: int) -> bool:
    """The program computes some held-out kind's form (any PARAMS) at every x in R.DOMAIN (invalid anywhere = not equal)."""
    outs = []
    for x in R.DOMAIN:
        vals, valid = run([0] * q_slot + [x], t)
        if not valid[t.ans]:
            return False
        outs.append(vals[t.ans])
    return tuple(outs) in _held_tables()


def dream_rows_c2(n: int, seed: int, avoid_prompts: Iterable[str] = (), *, night: int = 0, max_steps: int = 2, data: Optional[str] = DATA, check_real: bool = True,
                  strict: bool = False, stats: Optional[dict] = None, lengths: Optional[tuple] = None, occam: bool = False,
                  occam_max_states: int = OCCAM_MAX_STATES, found_lengths: Optional[tuple] = None, found_drawn: str = 'cycle'):
    """n dream TRAINING RECORDS (the form c2b W records take, so v1/creative_sleep and sleep.sleep consume them unchanged).
    Each record is fewshot._record's output (id 'D2:D2:<seed>:<night>:<i>:0', prompt, the program's own query output as `answer`, forced slot ids registered in
    custom_io.models.progparse._CACHE) plus `nums` and `dream` = dict(steps, ans, length, xs, ys, q). Deterministic in (n, seed, night, avoid_prompts).
    max_steps: longest program (2 = the brief; 3 reaches the shortest forms of double_add / sq_plus). strict: also reject-and-redraw any dream whose program equals ANY
    held-out kind's form (any PARAMS) at every x in R.DOMAIN (the dreams then never show a held-out function; default False = bit-identical to before).
    lengths: deal exactly these lengths round-robin instead of 1..max_steps (the top-up of dream_rows_par). stats (a dict, filled in): per length draws / accepted / strict_rejected. occam=True: after a dream passes every check it is RELABELLED with fewshot.find_reference on the dream row itself (prompt + own answer, <=5 steps, BFS = shortest program): the record's program is the found one, dreams with none are dropped (stats occam_dropped; found_<k> = found length k; dream['length'] stays the drawn length, dream['found_length'] the found one); strict also tests the found program. found_lengths (needs occam): deal by FOUND length instead of drawn length - the i-th dream targets found_lengths[i % len]; its program is drawn with a drawn length cycling through target..max_steps (found_drawn='cycle', the default; 'same' = always the target), relabelled, and kept only if the shortest program found has exactly the target length (stats: found_miss counts the others). Default False = bit-identical. Distinct `night` values give distinct ids (school phases use their own). avoid_prompts: extra prompts to exclude; warm/pool/dev are always excluded (check_real=False only for unit tests of the sampler)."""
    avoid_p, avoid_k = real_keys(data=data) if check_real else (set(), set())
    avoid_p = set(avoid_p) | set(avoid_prompts)
    for pr in avoid_prompts:                                # an extra prompt also removes its example-pair set
        pp_ = F.parse(pr)
        if pp_ is not None:
            avoid_k.add(_example_key(zip(pp_['xs'], pp_['ys'])))
    rng = random.Random(f'dream2|{seed}|{night}')
    out, seen_p, seen_k, draws = [], set(), set(), 0
    st = stats if stats is not None else {}
    assert not found_lengths or occam, 'found_lengths needs occam'
    tcount = {}
    for L in (range(1, max_steps + 1) if found_lengths else (lengths or range(1, max_steps + 1))):     # found mode draws lengths target..max_steps
        st.setdefault(L, dict(draws=0, accepted=0, strict_rejected=0, occam_dropped=0, found_miss=0, **{f'found_{k}': 0 for k in range(1, OCCAM_MAX_STEPS + 1)}))
    while len(out) < n:
        draws += 1
        assert draws < ((40000 * n + 50000) if found_lengths else (4000 * n + 5000)), f'cannot draw {n} dreams ({len(out)} so far)'
        if found_lengths:
            target = found_lengths[len(out) % len(found_lengths)]
            cands = list(range(target, max_steps + 1)) if found_drawn == 'cycle' else [target]
            L = cands[tcount.get(target, 0) % len(cands)]
            tcount[target] = tcount.get(target, 0) + 1
        else:
            target = None
            L = lengths[len(out) % len(lengths)] if lengths else 1 + len(out) % max_steps
        st[L]['draws'] += 1
        d = _draw(rng, avoid_p, avoid_k, L, seen_p=seen_p, seen_k=seen_k)       # (no per-draw set unions: they made 5k+ dream shards quadratic)
        if d is None:
            continue
        prompt, xs, ys, q, ans, t, length = d
        if strict and is_held_out_form(t, 2 * K_EX):
            st[L]['strict_rejected'] += 1
            continue
        if occam:
            row0 = dict(id='occam', prompt=prompt, answer=str(ans))
            tf_ = F.find_reference(row0, max_steps=OCCAM_MAX_STEPS, max_states=occam_max_states)
            if tf_ is None:
                st[L]['occam_dropped'] += 1
                continue
            vf = F.verdict(F.parse(prompt), tf_)
            if vf[0] != 'accept' or vf[2] != ans or (strict and is_held_out_form(tf_, 2 * K_EX)):
                st[L]['occam_dropped'] += 1
                continue
            if target is not None and len(cone(tf_)) != target:
                st[L]['found_miss'] += 1
                continue
            st[L][f'found_{len(cone(tf_))}'] += 1
            t = tf_
        st[L]['accepted'] += 1
        seen_p.add(prompt)
        seen_k.add(_example_key(zip(xs, ys)))
        row = dict(id=f'dream:{seed}:{night}:{len(out):05d}', prompt=prompt, answer=str(ans), accepted=[str(ans)], family='fewshot_number_rule', level=7,
                   stage=9, variant='', steps=[], nums=F.parse(prompt)['nums'])
        rec = F._record(row, t, ARM, 0)                    # registers the forced slot ids under rec['id']
        rec['nums'] = row['nums']
        steps, a_slot = train_form(t)
        rec['dream'] = dict(steps=[tuple(s) for s in steps], ans=a_slot, length=length, found_length=len(cone(t)), xs=xs, ys=ys, q=q)
        assert rec['answer'] == str(ans)
        out.append(rec)
    return out


def _shard(args):
    n, seed, avoid, night, max_steps, strict, occam, mst, fl = args
    st = {}
    return dream_rows_c2(n, seed, avoid, night=night, max_steps=max_steps, strict=strict, stats=st, occam=occam, occam_max_states=mst, found_lengths=fl), st


def _register(rows):
    """Re-register forced slot ids in THIS process (the target cache is per process: rows built by a worker or loaded from disk need it)."""
    for r in rows:
        F.register_targets(r['id'], r['nums'], r['dream']['steps'], r['dream']['ans'])
    return rows


def dream_rows_par(n: int, seed: int, avoid_prompts: Iterable[str] = (), *, night: int = 0, max_steps: int = 2, strict: bool = False, shards: int = 8, workers: int = 1,
                   stats: Optional[dict] = None, cache_dir: Optional[str] = None, occam: bool = False, occam_max_states: int = OCCAM_MAX_STATES, found_lengths: Optional[tuple] = None):
    """Same dreams as dream_rows_c2 but in `shards` fixed shards run by `workers` processes (the stream depends on `shards`, never on `workers`; each shard its own seed tag '<seed>s<i>'; duplicates across shards are dropped and topped up serially;
    lengths stay balanced: shards are multiples of max_steps). Not bit-equal to dream_rows_c2(n, seed): a different, equally valid stream. cache_dir: pickle of the result
    keyed by all arguments (read back and re-registered). occam: see dream_rows_c2 (the cache key includes it; use shards >= the core count, e.g. 128, to spread find_reference over all cores). Row ids start 'D2:dream:<seed>s<i>:<night>:'; the top-up uses tag '<seed>t'."""
    import hashlib
    import multiprocessing as mp
    import pickle
    import os
    avoid = list(avoid_prompts)
    path = None
    if cache_dir:
        key = hashlib.sha256(repr((n, seed, night, max_steps, strict, shards, sorted(avoid)) + ((occam, occam_max_states) if occam else ()) + ((tuple(found_lengths),) if found_lengths else ())).encode()).hexdigest()[:16]
        path = os.path.join(cache_dir, f'dreams_{seed}_{night}_{max_steps}_{int(strict)}{"_occam" if occam else ""}{"_f" + "".join(map(str, found_lengths)) if found_lengths else ""}_{n}_{key}.pkl')
        if os.path.exists(path):
            d = pickle.load(open(path, 'rb'))
            if stats is not None:
                stats.update(d['stats'])
            return _register(d['rows'])
    lens = tuple(found_lengths) if found_lengths else tuple(range(1, max_steps + 1))     # the dealt lengths (found lengths in found mode)
    K = len(lens)
    lkey = (lambda r: r['dream']['found_length']) if found_lengths else (lambda r: r['dream']['length'])
    units = n // K
    sizes = [(units // shards + (i < units % shards)) * K for i in range(shards)]
    sizes[0] += n - sum(sizes)
    jobs = [(m, f'{seed}s{i}', avoid, night, max_steps, strict, occam, occam_max_states, found_lengths) for i, m in enumerate(sizes) if m]
    if workers > 1:
        with mp.get_context('fork').Pool(min(workers, len(jobs))) as pool:
            res = pool.map(_shard, jobs)
    else:
        res = [_shard(j) for j in jobs]
    rows, seen_p, seen_k, st = [], set(), set(), {}
    for rs, s_ in res:
        for r in rs:
            k = _example_key(zip(r['dream']['xs'], r['dream']['ys']))
            if r['prompt'] in seen_p or k in seen_k:
                continue
            seen_p.add(r['prompt'])
            seen_k.add(k)
            rows.append(r)
        for L, v in s_.items():
            a = st.setdefault(L, {k_: 0 for k_ in v})
            for kk in a:
                a[kk] += v[kk]
    want = {L: sum(m_ // K + (j < m_ % K) for m_ in sizes) for j, L in enumerate(lens)}      # per-length target (balanced like the serial stream)
    for L in lens:                       # top up each short length with fresh dreams (cross-shard duplicates were dropped)
        short = want[L] - sum(lkey(r) == L for r in rows)
        if short > 0:
            extra = dream_rows_c2(2 * short + 10, f'{seed}t{L}', avoid + list(seen_p), night=night, max_steps=max_steps, strict=strict, lengths=(L,), occam=occam, occam_max_states=occam_max_states, found_lengths=(L,) if found_lengths else None)
            for r in extra:
                k = _example_key(zip(r['dream']['xs'], r['dream']['ys']))
                if short == 0:
                    break
                if r['prompt'] in seen_p or k in seen_k:
                    continue
                seen_p.add(r['prompt'])
                seen_k.add(k)
                rows.append(r)
                short -= 1
    rows = _register(rows)
    assert len({r['id'] for r in rows}) == len(rows) == n, (len(rows), n)
    if stats is not None:
        stats.update(st)
    if path:
        os.makedirs(cache_dir, exist_ok=True)
        pickle.dump(dict(rows=rows, stats=st), open(path + '.tmp', 'wb'))
        os.replace(path + '.tmp', path)
    return rows


# ---- disclosure: how many dreams are one of the held-out kinds? ----
def _fits(kind, params, xs, ys):
    f = R.fn(kind, params)
    return all(f(x) == y for x, y in zip(xs, ys))


def _same_on_domain(kind, params, rec):
    """The dream's program computes the kind's form at every input of the C2 domain (a strict, parameter-exact identity)."""
    t = Try.make(rec['dream']['steps'], rec['dream']['ans'])
    f = R.fn(kind, params)
    q_slot = 2 * len(rec['dream']['xs'])
    for x in R.DOMAIN:
        vals, valid = run([0] * q_slot + [x], t)
        if not valid[t.ans] or vals[t.ans] != f(x):
            return False
    return True


def kind_overlap(rows, kinds=R.HELD_OUT, practised=R.PRACTISED) -> dict:
    """Share of dream rows that match each held-out kind (and, for reference, the two practised kinds). Two numbers per kind:
      fits_examples = some parameter setting of the kind's form reproduces the row's shown examples (what a model could not tell apart from the kind);
      same_function = the dream's program equals that form at every input in the domain (parameter-exact identity).
    Reads only the shown examples / the program; a disclosure, never a filter.
    -> {kind: dict(fits_examples, same_function, n_*)}, plus 'n', 'by_length', 'any_held_out_same_function'."""
    n = len(rows)
    out = dict(n=n, by_length={L: sum(r["dream"]["length"] == L for r in rows) for L in range(1, 1 + max([r["dream"]["length"] for r in rows] + [3]))})
    for kind in tuple(kinds) + tuple(practised):
        fe = sf = 0
        for r in rows:
            xs, ys = r['dream']['xs'], r['dream']['ys']
            cand = [p for p in R.PARAMS[kind] if _fits(kind, p, xs, ys)]
            fe += bool(cand)
            sf += any(_same_on_domain(kind, p, r) for p in cand)
        out[kind] = dict(fits_examples=fe / max(n, 1), same_function=sf / max(n, 1), n_fits_examples=fe, n_same_function=sf)
    out['any_held_out_same_function'] = sum(
        any(_same_on_domain(k, p, r) for k in kinds for p in R.PARAMS[k] if _fits(k, p, r['dream']['xs'], r['dream']['ys'])) for r in rows) / max(n, 1)
    return out
