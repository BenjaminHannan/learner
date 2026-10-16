"""Ready-state census of the GW-F training rows (A28). Zero GPU: rebuilds, from the saved play files, the rows the loop trained on each round
(A26 keep rule) and the rows the A27 rule (rare_below = 100) would have built from the same games, and counts those whose view is pickaxe-ready
(table within one cell, wood >= 1, no wood pickaxe) by move and weight. Harness only: the labeller's view parser is an instrument, never a teacher.

python -m game.census_ready RUN_DIR OUT_JSON   (RUN_DIR holds s200/ and s201/ with play-<round>-<chunk>.json.gz)
"""
import gzip
import json
import sys
from collections import Counter

from game import imitate, oracle, play

WPICK = play.WORDS.index('wpick')


def is_ready(view):
    pv = oracle.parse_view(view)
    inv = pv.items.get
    return inv('wood', 0) >= 1 and not inv('wood_pickaxe', 0) and any(oracle._cell(pv, x, y) == 't' for x in (-1, 0, 1) for y in (-1, 0, 1))


def census_rows(rows):
    """rows: imitate.rows_of output. -> counts and weighted sums over the ready-state rows; weights divided by their mean over all rows."""
    if not rows:
        return {}
    mean_w = sum(r['weight'] for r in rows) / len(rows)
    out = dict(rows=len(rows), W_n=0, A_n=0, W_w=0.0, A_w=0.0, a_by_word=Counter(), a_by_type=Counter())
    for r in rows:
        if not is_ready(r['view']):
            continue
        w = r['weight'] / mean_w
        if r['action'] == WPICK:
            out['W_n'] += 1
            out['W_w'] += w
        else:
            out['A_n'] += 1
            out['A_w'] += w
            out['a_by_word'][play.WORDS[r['action']]] += 1
            out['a_by_type'][r['type']] += 1
    out['W_w'], out['A_w'] = round(out['W_w'], 2), round(out['A_w'], 2)
    out['ratio_n'] = round(out['W_n'] / out['A_n'], 3) if out['A_n'] else None
    out['ratio_w'] = round(out['W_w'] / out['A_w'], 3) if out['A_w'] else None
    out['a_by_word'], out['a_by_type'] = dict(out['a_by_word'].most_common(8)), dict(out['a_by_type'].most_common(8))
    return out


def first_only(games):
    """Post-hoc counterfactual (A28, not marked): the same games with only the events that are a first unlock (the game's +1), repeats dropped."""
    return [dict(g, events=[(t, n) for t, n in g['events'] if g['first'].get(n) == t]) for g in games]


def one_round(games):
    res = {}
    for name, rare, gs in (('A26', 0, games), ('A27', 100, games), ('FIRST26', 0, first_only(games)), ('FIRST27', 100, first_only(games))):
        segs = [s for gi, g in enumerate(gs) for s in imitate.segments(g['events'], gi)]
        weights = imitate.type_weights(Counter(s['type'] for s in segs))
        kept, _ = imitate.keep_segments(segs, rare)
        res[name] = census_rows(imitate.rows_of(kept, gs, weights))
    visits = wp = 0
    for g in games:
        for v, a in zip(g['views'], g['actions']):
            if is_ready(v):
                visits += 1
                wp += a == WPICK
    res['V'], res['E'] = visits, wp
    return res


def main(run_dir, out_json, rounds=range(1, 17)):
    out = {}
    for seed in (200, 201):
        for r in rounds:
            games = []
            for c in range(imitate.CHUNKS):
                with gzip.open(f'{run_dir}/s{seed}/play-{r}-{c}.json.gz', 'rt') as f:
                    games += json.load(f)
            out[f'{seed}-{r}'] = one_round(games)
            x = out[f'{seed}-{r}']
            print(seed, r, 'V', x['V'], 'E', x['E'], *[f"| {k} W/A n {x[k].get('W_n')}/{x[k].get('A_n')} w {x[k].get('ratio_w')}" for k in ('A26', 'A27', 'FIRST26', 'FIRST27')], flush=True)
    with open(out_json, 'w') as f:
        json.dump(out, f, indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
