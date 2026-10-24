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


def _draw(rng, avoid_prompts, avoid_keys, length, k_ex=K_EX):
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
    if prompt in avoid_prompts or _example_key(zip(xs, ys)) in avoid_keys:
        return None
    v = F.verdict(F.parse(prompt), t)                       # C2's checker: structure + python ints + B2's torch executor, every example
    if v[0] != 'accept' or v[2] != ans:
        return None
    return prompt, xs, ys, q, ans, t, length


def dream_rows_c2(n: int, seed: int, avoid_prompts: Iterable[str] = (), *, night: int = 0, max_steps: int = 2, data: Optional[str] = DATA, check_real: bool = True):
    """n dream TRAINING RECORDS (the form c2b W records take, so v1/creative_sleep and sleep.sleep consume them unchanged).
    Each record is fewshot._record's output (id 'D2:D2:<seed>:<night>:<i>:0', prompt, the program's own query output as `answer`, forced slot ids registered in
    custom_io.models.progparse._CACHE) plus `nums` and `dream` = dict(steps, ans, length, xs, ys, q). Deterministic in (n, seed, night, avoid_prompts).
    max_steps: longest program (2 = the brief; 3 reaches the shortest forms of double_add / sq_plus). avoid_prompts: extra prompts to exclude; warm/pool/dev are always excluded (check_real=False only for unit tests of the sampler)."""
    avoid_p, avoid_k = real_keys(data=data) if check_real else (set(), set())
    avoid_p = set(avoid_p) | set(avoid_prompts)
    for pr in avoid_prompts:                                # an extra prompt also removes its example-pair set
        pp_ = F.parse(pr)
        if pp_ is not None:
            avoid_k.add(_example_key(zip(pp_['xs'], pp_['ys'])))
    rng = random.Random(f'dream2|{seed}|{night}')
    out, seen_p, seen_k, draws = [], set(), set(), 0
    while len(out) < n:
        draws += 1
        assert draws < 400 * n + 5000, f'cannot draw {n} dreams ({len(out)} so far)'
        d = _draw(rng, avoid_p | seen_p, avoid_k | seen_k, 1 + len(out) % max_steps)
        if d is None:
            continue
        prompt, xs, ys, q, ans, t, length = d
        seen_p.add(prompt)
        seen_k.add(_example_key(zip(xs, ys)))
        row = dict(id=f'dream:{seed}:{night}:{len(out):05d}', prompt=prompt, answer=str(ans), accepted=[str(ans)], family='fewshot_number_rule', level=7,
                   stage=9, variant='', steps=[], nums=F.parse(prompt)['nums'])
        rec = F._record(row, t, ARM, 0)                    # registers the forced slot ids under rec['id']
        rec['nums'] = row['nums']
        steps, a_slot = train_form(t)
        rec['dream'] = dict(steps=[tuple(s) for s in steps], ans=a_slot, length=length, xs=xs, ys=ys, q=q)
        assert rec['answer'] == str(ans)
        out.append(rec)
    return out


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
    out = dict(n=n, by_length={L: sum(r['dream']['length'] == L for r in rows) for L in (1, 2, 3)})
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
