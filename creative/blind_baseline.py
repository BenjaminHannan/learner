"""Report-only blind-search baseline for C2b (roadmap 4e50f8cf85, sec. 7). No model, no kind, no key in the search: breadth-first search over programs on the input x and the constants
(1, 2, 10, 100), ops ADD SUB MUL DIV MOD MIN MAX, at most 7 steps; a candidate = a new distinct value vector over (examples + query), taken in breadth-first order. A candidate FITS when it
reproduces all example outputs (a constant vector does not count: the program must read x). The key only scores: a fit is RIGHT when its query value is in row['accepted'].
Reported at 1 / 4 / 32 guesses (guess = a fitting candidate, in the order found; matched to first try, reach@4, reach@32) and at 1k / 6k / 50k candidates examined (any fit; first fit right;
any right fit among those found by then). Runs once, alongside the sealed-test scoring; the marks do not move."""
from concurrent.futures import ProcessPoolExecutor
from creative import fewshot
from creative.programs import CONSTS, apply

GUESSES = (1, 4, 32)
BUDGETS = (1000, 6000, 50000)
OPS = fewshot.SEARCH_OPS


def search_fits(row, budget=BUDGETS[-1], max_fits=64, max_steps=7):
    """-> list of (examined_index, query_value) for each fitting candidate in breadth-first order (at most max_fits, within `budget` candidates)."""
    p = fewshot.parse(row['prompt'])
    xs = tuple(p['xs']) + (p['q'],)
    ys = tuple(p['ys'])
    k = len(ys)
    base = (xs,) + tuple((c,) * len(xs) for c in CONSTS)
    seen = set(base)
    fits, examined = [], 0
    frontier = [(base, 0)]
    for _ in range(max_steps):
        nxt = []
        for slots, _n in frontier:
            for va in slots:
                for vb in slots:
                    for op in OPS:
                        out = tuple(apply(op, x, y) for x, y in zip(va, vb))
                        if None in out or out in seen:
                            continue
                        seen.add(out)
                        examined += 1
                        if out[:k] == ys and len(set(out)) > 1:
                            fits.append((examined, out[-1]))
                            if len(fits) >= max_fits:
                                return fits
                        if examined >= budget:
                            return fits
                        nxt.append((slots + (out,), 0))
        frontier = nxt
    return fits


def _one(row):
    f = search_fits(row)
    return [(i, str(v) in row['accepted']) for i, v in f]


def score_rows(rows, workers=4):
    """Per question: fits = [(examined, right)]; then pooled / per-kind rates at the guess counts and budgets."""
    if workers > 1:
        with ProcessPoolExecutor(workers) as ex:
            fits = list(ex.map(_one, rows, chunksize=8))
    else:
        fits = [_one(r) for r in rows]
    return summarize(rows, fits)


def summarize(rows, fits):
    def rates(ix):
        n = len(ix)
        out = {f'right_within_{g}_guesses': sum(any(r for _, r in fits[i][:g]) for i in ix) / n for g in GUESSES}
        for b in BUDGETS:
            out[f'fit_within_{b}'] = sum(any(e <= b for e, _ in fits[i]) for i in ix) / n
            out[f'first_fit_right_within_{b}'] = sum(bool([r for e, r in fits[i] if e <= b][:1] == [True]) for i in ix) / n
            out[f'any_right_fit_within_{b}'] = sum(any(e <= b and r for e, r in fits[i]) for i in ix) / n
        return out
    kinds = sorted({r['kind'] for r in rows})
    multi = [i for i, r in enumerate(rows) if r['kind'] in ('affine', 'sq_plus', 'double_add')]
    return dict(n_questions=len(rows), pooled=rates(list(range(len(rows)))), multi_step=rates(multi) if multi else None,
                by_kind={k: rates([i for i, r in enumerate(rows) if r['kind'] == k]) for k in kinds},
                spec='blind BFS over x and 1/2/10/100, ops 1-7, <= 7 steps, no model; guess = fitting candidate in order found; budget = candidates examined')
