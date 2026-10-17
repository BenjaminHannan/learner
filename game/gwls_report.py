"""DRAFT pending coordinator review (GW-LS). Per-round report of GW-LS (game/WALL-SOLVE-RESULT.md section 3) and its sealed round-4 leading indicator.

  python -m game.gwls_report [--root DIR] [--out-dir DIR] [--seeds 200 201]

DIR (default the GW-LS scratch folder) holds s200/ and s201/ with iter-k.json and play-k-c.json.gz as game.imitate writes them. A round is complete
when its iter-k.json exists. Reads practice games only; no sealed world. Census numbers are cached in OUT_DIR/census-cache.json, keyed on a hash of the
round's play files (so a round that is re-run into the same folder never reads a stale entry).

Per round and seed: practice mean unlocks; practice NON-HABIT unlocks (per game, the count of first-unlocked achievements that are not collect_sapling,
place_plant, eat_plant or wake_up, read from the saved games' `first`; the mean over games); stone games %; pickaxe games; the ready-state census of
game.census_ready.one_round (A27 block: W_n, A_n, W_w, A_w, ratio_w = W_w / A_w), V (ready-state visits), E (wpick moves in them), share = E / V;
oracle agreement of the played and of the kept moves.

Leading indicator (sealed, round 4, means of rounds 3 and 4): STOP, proved wrong early, if on BOTH seeds the ready-state W_w / A_w <= 0.5 OR the
practice non-habit unlocks are 0.5 or more below round 1's reference (5.72 for s200, 5.87 for s201, Z8). Otherwise continue. The branch is printed once
rounds 3 and 4 exist for both seeds. The sealed wording "on both seeds, X or Y" is read per seed (a seed trips if X or Y) and both seeds must trip;
the other reading (X on both seeds, or Y on both seeds) is also computed and flagged if it would give a different branch.

Rounding: the indicator compares UNROUNDED values. The non-habit mean is an exact fraction (non-habit count over games, exact arithmetic against the
threshold ref - 0.5); the ratio is W_w / A_w recomputed from the unrounded weighted sums (the census file rounds W_w, A_w and the ratio for display, and
the two are compared to within the analytic bound of the census file's own display rounding: W_w and A_w to 2 dp, the ratio (computed from the
rounded sums) to 3 dp, so |ratio_w_exact - ratio_w| <= (1 + ratio) * 0.005 / (A_w - 0.005) + 0.0005 + eps. The comparison is a NON-FATAL per-row field
(ratio_gap, ratio_bound, ratio_ok; a flag in report.md), never an assert. Rounding happens only in the printed / displayed numbers.
"""
import argparse
import glob
import gzip
import hashlib
import json
import os
import time
from collections import Counter
from fractions import Fraction

from game import census_ready, imitate

SCRATCH = '/tmp/claude-0/-home-user/a1ebb63a-25ce-579d-bded-94d555e1f95e/scratchpad'
HABIT = ('collect_sapling', 'place_plant', 'eat_plant', 'wake_up')
REF = {200: 5.72, 201: 5.87}                    # round-1 practice non-habit unlocks from Z8
RATIO_STOP, NONHABIT_DROP = 0.5, 0.5
STOP = 'STOP: PROVED WRONG EARLY'
RATIO_EPS = 1e-6                                # slack on top of the analytic rounding bound
ITER_RETRY_SLEEP = 1.0                          # seconds before the one retry of a half-written iter-k.json (game.imitate writes it non-atomically)


class RoundReadError(ValueError):
    """A round's files cannot be read consistently (e.g. iter-k.json still unparseable after one retry)."""


def ratio_consistency(ratio_w, ratio_w_exact, A_w):
    """-> dict(ratio_gap, ratio_bound, ratio_ok) comparing the unrounded ratio with the census file's rounded one; never raises.

    census_ready rounds W_w and A_w to 2 dp and then computes ratio_w = round(W_w / A_w, 3) from the ROUNDED sums. With true sums W, A (W ~ ratio * A) and
    rounded sums off by at most 0.005 each: |W_r / A_r - W / A| <= (1 + ratio) * 0.005 / A_r_true, and A_r_true >= A_w - 0.005; the final 3 dp rounding adds
    0.0005. ratio is taken as the larger of the two ratios plus 0.0005 so the bound errs on the safe side. ok is None when it cannot be computed.
    """
    if ratio_w is None or ratio_w_exact is None or A_w is None:
        return dict(ratio_gap=None, ratio_bound=None, ratio_ok=None)
    gap = abs(ratio_w_exact - ratio_w)
    floor = A_w - 0.005
    if floor <= 0:                                   # A_w rounds to (almost) 0: no finite bound from the rounding alone
        return dict(ratio_gap=round(gap, 6), ratio_bound=None, ratio_ok=None)
    bound = (1 + max(ratio_w_exact, ratio_w) + 0.0005) * 0.005 / floor + 0.0005 + RATIO_EPS
    return dict(ratio_gap=round(gap, 6), ratio_bound=round(bound, 6), ratio_ok=gap <= bound)


def play_files(d, k):
    return sorted(glob.glob(os.path.join(d, f'play-{k}-*.json.gz')), key=lambda p: int(p.rsplit('-', 1)[1].split('.')[0]))


def read_play(d, k):
    """-> (games of round k in chunk order, sha256 hex over the play files' names and bytes)."""
    games, h = [], hashlib.sha256()
    for path in play_files(d, k):
        with open(path, 'rb') as f:
            raw = f.read()
        h.update(os.path.basename(path).encode() + b'\0' + hashlib.sha256(raw).digest())
        games += json.loads(gzip.decompress(raw))
    return games, h.hexdigest()


def load_games(d, k):
    return read_play(d, k)[0]


def nonhabit_count(games):
    """Total non-habit unlocks over the games: first-unlocked achievements (g['first']) that are not one of the four habit ones. An int."""
    return sum(1 for g in games for n in g['first'] if n not in HABIT)


def nonhabit_per_game(games):
    """Unrounded mean non-habit unlocks per game (float; the exact value is nonhabit_count(games) / len(games))."""
    return nonhabit_count(games) / len(games)


def ratio_w_exact(games):
    """Unrounded A27 ready-state W_w / A_w of the games (the census_ready.census_rows computation without its display rounding). None if no A rows."""
    segs = [s for gi, g in enumerate(games) for s in imitate.segments(g['events'], gi)]
    weights = imitate.type_weights(Counter(s['type'] for s in segs))
    kept, _ = imitate.keep_segments(segs, 100)
    rows = imitate.rows_of(kept, games, weights)
    if not rows:
        return None
    mean_w = sum(r['weight'] for r in rows) / len(rows)
    W = A = 0.0
    for r in rows:
        if census_ready.is_ready(r['view']):
            if r['action'] == census_ready.WPICK:
                W += r['weight'] / mean_w
            else:
                A += r['weight'] / mean_w
    return W / A if A else None


def read_iter(d, k):
    """iter-k.json of round k; game.imitate writes it non-atomically, so a JSONDecodeError is retried once after a short sleep, then raised as a clear error."""
    path = os.path.join(d, f'iter-{k}.json')
    for attempt in (0, 1):
        try:
            with open(path) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            if attempt == 0:
                time.sleep(ITER_RETRY_SLEEP)
                continue
            raise RoundReadError(f'{path} is not valid JSON after a retry (still being written, or corrupt): {e}') from e


def round_row(d, k, cache=None):
    cache = {} if cache is None else cache
    it = read_iter(d, k)
    games, digest = read_play(d, k)
    n = it['games']
    assert len(games) == n, f'{d} round {k}: iter-{k}.json says {n} games, the play files hold {len(games)} (a re-run into the same folder?)'
    assert abs(sum(len(g['first']) for g in games) / n - it['mean_unlocks']) < 6e-4, f'{d} round {k}: play files do not match iter-{k}.json'
    key = f'{os.path.abspath(d)}|{k}|{n}|{digest}'
    if key not in cache:
        c = census_ready.one_round(games)
        a27 = c['A27']
        rx = ratio_w_exact(games)
        cache[key] = dict(W_n=a27.get('W_n'), A_n=a27.get('A_n'), W_w=a27.get('W_w'), A_w=a27.get('A_w'), ratio_w=a27.get('ratio_w'),
                          ratio_w_exact=rx, V=c['V'], E=c['E'])
    c = cache[key]
    chk = ratio_consistency(c.get('ratio_w'), c.get('ratio_w_exact'), c.get('A_w'))                  # non-fatal; computed from the cached numbers
    nh = nonhabit_count(games)
    return dict(round=k, games=n, temp=it['temp'], mean_unlocks=it['mean_unlocks'], nonhabit=round(nh / n, 3), nonhabit_sum=nh, nonhabit_exact=nh / n,
                stone_pct=round(100 * it['g_stone'] / n, 1), pickaxe_games=it['g_pick'], **c, **chk,
                share=round(c['E'] / c['V'], 4) if c['V'] else None,
                agree_played=it['oracle_agreement_all_played']['agreement'], agree_kept=it['oracle_agreement_kept']['agreement'])


def build_rows(root, seeds, rounds=None, cache=None, errors=None):
    """{seed: [round_row, ...]} for the rounds with an iter-k.json (restricted to `rounds` if given).

    errors=None: a round that cannot be read consistently raises. errors=[]: such a round is skipped and one string per failure is appended to the list
    (so a caller can list every problem instead of stopping at the first)."""
    rows = {}
    for seed in seeds:
        d = os.path.join(root, f's{seed}')
        ks = sorted(int(os.path.basename(p)[5:-5]) for p in glob.glob(os.path.join(d, 'iter-*.json')))
        rows[seed] = []
        for k in ks:
            if rounds is not None and k not in rounds:
                continue
            if errors is None:
                rows[seed].append(round_row(d, k, cache))
                continue
            try:
                rows[seed].append(round_row(d, k, cache))
            except (AssertionError, ValueError, OSError, KeyError, TypeError) as e:
                errors.append(f'seed {seed} round {k}: {type(e).__name__}: {e}')
    return rows


def indicator(rows, ref):
    """rows: {seed: [row, ...]} -> dict with the per-seed means of rounds 3 and 4 and the branch (None while a round is missing). Unrounded comparisons."""
    out, per = {}, {}
    for seed, rs in rows.items():
        by = {r['round']: r for r in rs}
        if 3 not in by or 4 not in by:
            return dict(branch=None, note='rounds 3 and 4 are not both complete on every seed')
        ratios = [by[3]['ratio_w_exact'], by[4]['ratio_w_exact']]
        nh = (Fraction(by[3]['nonhabit_sum'], by[3]['games']) + Fraction(by[4]['nonhabit_sum'], by[4]['games'])) / 2          # exact
        thr = Fraction(str(ref[seed])) - Fraction(str(NONHABIT_DROP))
        ratio = None if None in ratios else (ratios[0] + ratios[1]) / 2
        x = ratio is not None and ratio <= RATIO_STOP
        y = nh <= thr
        per[seed] = dict(ratio_w_mean=None if ratio is None else round(ratio, 4), nonhabit_mean=round(float(nh), 4), nonhabit_ref=ref[seed],
                         nonhabit_threshold=float(thr), nonhabit_vs_ref=round(float(nh - Fraction(str(ref[seed]))), 4), ratio_trips=x, nonhabit_trips=y, trips=x or y)
    stop = all(p['trips'] for p in per.values())
    alt = all(p['ratio_trips'] for p in per.values()) or all(p['nonhabit_trips'] for p in per.values())
    out = dict(per_seed=per, branch=STOP if stop else 'CONTINUE', alt_reading_branch=STOP if alt else 'CONTINUE')
    out['readings_agree'] = out['branch'] == out['alt_reading_branch']
    return out


def markdown(rows, ind):
    cols = [('round', 'rnd'), ('mean_unlocks', 'unlocks'), ('nonhabit', 'non-habit'), ('stone_pct', 'stone %'), ('pickaxe_games', 'pick g'),
            ('W_n', 'W_n'), ('A_n', 'A_n'), ('W_w', 'W_w'), ('A_w', 'A_w'), ('ratio_w', 'ratio_w'), ('V', 'V'), ('E', 'E'), ('share', 'share'),
            ('agree_played', 'agree played'), ('agree_kept', 'agree kept')]
    lines = ['# GW-LS practice report (DRAFT pending coordinator review)', '']
    for seed, rs in rows.items():
        lines += [f'## seed {seed}  (round-1 non-habit reference {REF.get(seed)})', '', '| ' + ' | '.join(h for _, h in cols) + ' |',
                  '|' + '---|' * len(cols)]
        lines += ['| ' + ' | '.join(str(r[c]) for c, _ in cols) + ' |' for r in rs]
        lines += ['', 'ratio_w consistency (unrounded ratio vs the census file\'s rounded one; non-fatal): ' + '; '.join(
            f'r{r["round"]} gap {r["ratio_gap"]} <= bound {r["ratio_bound"]}: ' + ('ok' if r['ratio_ok'] else 'n/a' if r['ratio_ok'] is None else 'FLAG') for r in rs)]
        lines.append('')
    lines += ['## Round-4 leading indicator', '']
    if ind['branch'] is None:
        lines.append(ind['note'])
    else:
        for seed, p in ind['per_seed'].items():
            lines.append(f'- seed {seed}: mean(r3, r4) ratio_w {p["ratio_w_mean"]} (trips if <= {RATIO_STOP}: {p["ratio_trips"]}); '
                         f'non-habit {p["nonhabit_mean"]} vs ref {p["nonhabit_ref"]} ({p["nonhabit_vs_ref"]:+}; trips if <= {p["nonhabit_threshold"]:.2f}: {p["nonhabit_trips"]})')
        lines += ['', f'**Branch: {ind["branch"]}**' + ('' if ind['readings_agree'] else f'  (the other reading of the sealed sentence gives: {ind["alt_reading_branch"]})')]
    return '\n'.join(lines) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description='GW-LS per-round report and round-4 leading indicator.')
    ap.add_argument('--root', default=os.path.join(SCRATCH, 'gwls'), help='folder holding s200/ and s201/')
    ap.add_argument('--out-dir', default=None, help='where report.json / report.md go (default: --root)')
    ap.add_argument('--seeds', type=int, nargs='+', default=[200, 201])
    a = ap.parse_args(argv)
    out_dir = a.out_dir or a.root
    os.makedirs(out_dir, exist_ok=True)
    cpath = os.path.join(out_dir, 'census-cache.json')
    cache = json.load(open(cpath)) if os.path.exists(cpath) else {}
    rows = build_rows(a.root, a.seeds, cache=cache)
    with open(cpath + '.tmp', 'w') as f:
        json.dump(cache, f)
    os.replace(cpath + '.tmp', cpath)
    ind = indicator(rows, REF)
    with open(os.path.join(out_dir, 'report.json'), 'w') as f:
        json.dump(dict(rounds={str(s): r for s, r in rows.items()}, round4_indicator=ind), f, indent=1)
    md = markdown(rows, ind)
    with open(os.path.join(out_dir, 'report.md'), 'w') as f:
        f.write(md)
    print(md)


if __name__ == '__main__':
    main()
