"""W2 no-learning baselines for creative dev (CPU, no weights, no key in any search). Reporting only: it never changes the v1 verdict (W2_dev_pass stays first_try >= 0.20).
  best_fixed_program  best single input-blind program: every one-step program (op over x and the constants 1/2/10/100), applied to the query alone, never reading the examples; the best score
  blind_first_fit     creative/blind_baseline.search_fits, the first fitting candidate within B examined candidates (B = 1 / 4 / 32), right when its query value is in row['accepted']
  each also on the parameterised kinds only (affine, sq_plus, double_add).
  proposed_W2_threshold = max(best_fixed_program, blind_first_fit@1) + 0.10  (a proposal; not used by the v1 decision rule)."""
from creative import fewshot
from creative.blind_baseline import search_fits
from creative.programs import CONSTS, apply

BUDGETS = (1, 4, 32)
PARAM_KINDS = ('affine', 'sq_plus', 'double_add')
MARGIN = 0.10


def best_fixed_program(rows):
    """-> (score, program) over one-step input-blind programs; ties keep the first in (op, a, b) order. Program = (op, a, b), operands 'x' or a constant."""
    qs = [fewshot.parse(r['prompt'])['q'] for r in rows]
    best = (0.0, None)
    for op in fewshot.SEARCH_OPS:
        for a in ('x',) + tuple(CONSTS):
            for b in ('x',) + tuple(CONSTS):
                hit = 0
                for r, q in zip(rows, qs):
                    v = apply(op, q if a == 'x' else a, q if b == 'x' else b)
                    hit += v is not None and str(v) in r['accepted']
                if rows and hit / len(rows) > best[0]:
                    best = (hit / len(rows), (op, a, b))
    return best


def _first_fit_right(rows, budgets, max_steps=7):
    """-> {B: fraction of rows whose first fit within B examined candidates is right}."""
    out = dict.fromkeys(budgets, 0)
    for r in rows:
        f = search_fits(r, budget=max(budgets), max_fits=64, max_steps=max_steps)
        for b in budgets:
            ff = [str(v) in r['accepted'] for e, v in f if e <= b][:1]
            out[b] += ff == [True]
    return {b: (out[b] / len(rows) if rows else 0.0) for b in budgets}


def _block(rows, budgets):
    score, prog = best_fixed_program(rows)
    return dict(n=len(rows), best_fixed_program=score, best_fixed_program_spec=prog,
                blind_first_fit_right={str(b): v for b, v in _first_fit_right(rows, budgets).items()})


def creative_baselines(rows, budgets=BUDGETS):
    """rows = creative dev rows (dicts with prompt / kind / accepted). Deterministic."""
    allr = _block(rows, budgets)
    par = _block([r for r in rows if r['kind'] in PARAM_KINDS], budgets)
    thr = max(allr['best_fixed_program'], allr['blind_first_fit_right'][str(budgets[0])]) + MARGIN
    return dict(all=allr, parameterised=par, parameterised_kinds=list(PARAM_KINDS), proposed_W2_threshold=thr,
                spec='no-learning baselines on creative dev: best one-step input-blind program; blind BFS first fit within B examined candidates; threshold = max(best_fixed, blind@1) + 0.10')
