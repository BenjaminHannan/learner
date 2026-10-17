"""DRAFT pending coordinator review (GW-LS). Per-round report of GW-LS (game/WALL-SOLVE-RESULT.md section 3) and its sealed round-4 leading indicator.

  python -m game.gwls_report [--root DIR] [--out-dir DIR] [--seeds 200 201]

DIR (default the GW-LS scratch folder) holds s200/ and s201/ with iter-k.json and play-k-c.json.gz as game.imitate writes them. A round is complete
when its iter-k.json exists. Reads practice games only; no sealed world. Census numbers are cached in OUT_DIR/census-cache.json.

Per round and seed: practice mean unlocks; practice NON-HABIT unlocks (mean unlocks minus the games unlocking collect_sapling, place_plant, eat_plant
or wake_up, over games); stone games %; pickaxe games; the ready-state census of game.census_ready.one_round (A27 block: W_n, A_n, W_w, A_w,
ratio_w = W_w / A_w), V (ready-state visits), E (wpick moves in them), share = E / V; oracle agreement of the played and of the kept moves.

Leading indicator (sealed, round 4, means of rounds 3 and 4): STOP, proved wrong early, if on BOTH seeds the ready-state W_w / A_w <= 0.5 OR the
practice non-habit unlocks are 0.5 or more below round 1's reference (5.72 for s200, 5.87 for s201, Z8). Otherwise continue. The branch is printed once
rounds 3 and 4 exist for both seeds. The sealed wording "on both seeds, X or Y" is read per seed (a seed trips if X or Y) and both seeds must trip;
the other reading (X on both seeds, or Y on both seeds) is also computed and flagged if it would give a different branch.
"""
import argparse
import glob
import gzip
import json
import os

from game import census_ready

SCRATCH = '/tmp/claude-0/-home-user/a1ebb63a-25ce-579d-bded-94d555e1f95e/scratchpad'
HABIT = ('collect_sapling', 'place_plant', 'eat_plant', 'wake_up')
REF = {200: 5.72, 201: 5.87}                    # round-1 practice non-habit unlocks from Z8
RATIO_STOP, NONHABIT_DROP = 0.5, 0.5


def load_games(d, k):
    games = []
    for path in sorted(glob.glob(os.path.join(d, f'play-{k}-*.json.gz')), key=lambda p: int(p.rsplit('-', 1)[1].split('.')[0])):
        with gzip.open(path, 'rt') as f:
            games += json.load(f)
    return games


def nonhabit_mean(it):
    """Mean practice unlocks excluding the four habit achievements (games_with counts games whose first unlock of that name happened)."""
    return it['mean_unlocks'] - sum(it['games_with'].get(n, 0) for n in HABIT) / it['games']


def round_row(d, k, cache):
    with open(os.path.join(d, f'iter-{k}.json')) as f:
        it = json.load(f)
    key = f'{os.path.abspath(d)}|{k}|{it["games"]}'
    if key not in cache:
        c = census_ready.one_round(load_games(d, k))
        a27 = c['A27']
        cache[key] = dict(W_n=a27.get('W_n'), A_n=a27.get('A_n'), W_w=a27.get('W_w'), A_w=a27.get('A_w'), ratio_w=a27.get('ratio_w'),
                          V=c['V'], E=c['E'])
    c = cache[key]
    n = it['games']
    return dict(round=k, games=n, temp=it['temp'], mean_unlocks=it['mean_unlocks'], nonhabit=round(nonhabit_mean(it), 3),
                stone_pct=round(100 * it['g_stone'] / n, 1), pickaxe_games=it['g_pick'], **c,
                share=round(c['E'] / c['V'], 4) if c['V'] else None,
                agree_played=it['oracle_agreement_all_played']['agreement'], agree_kept=it['oracle_agreement_kept']['agreement'])


def indicator(rows, ref):
    """rows: {seed: [row, ...]} -> dict with the per-seed means of rounds 3 and 4 and the branch (None while a round is missing)."""
    out, per = {}, {}
    for seed, rs in rows.items():
        by = {r['round']: r for r in rs}
        if 3 not in by or 4 not in by:
            return dict(branch=None, note='rounds 3 and 4 are not both complete on every seed')
        ratios = [by[3]['ratio_w'], by[4]['ratio_w']]
        nh = (by[3]['nonhabit'] + by[4]['nonhabit']) / 2
        ratio = None if None in ratios else (ratios[0] + ratios[1]) / 2
        x = ratio is not None and ratio <= RATIO_STOP
        y = round(nh, 6) <= round(ref[seed] - NONHABIT_DROP, 6)
        per[seed] = dict(ratio_w_mean=None if ratio is None else round(ratio, 3), nonhabit_mean=round(nh, 3), nonhabit_ref=ref[seed],
                         nonhabit_vs_ref=round(nh - ref[seed], 3), ratio_trips=x, nonhabit_trips=y, trips=x or y)
    stop = all(p['trips'] for p in per.values())
    alt = all(p['ratio_trips'] for p in per.values()) or all(p['nonhabit_trips'] for p in per.values())
    out = dict(per_seed=per, branch='STOP: PROVED WRONG EARLY' if stop else 'CONTINUE', alt_reading_branch='STOP: PROVED WRONG EARLY' if alt else 'CONTINUE')
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
        lines.append('')
    lines += ['## Round-4 leading indicator', '']
    if ind['branch'] is None:
        lines.append(ind['note'])
    else:
        for seed, p in ind['per_seed'].items():
            lines.append(f'- seed {seed}: mean(r3, r4) ratio_w {p["ratio_w_mean"]} (trips if <= {RATIO_STOP}: {p["ratio_trips"]}); '
                         f'non-habit {p["nonhabit_mean"]} vs ref {p["nonhabit_ref"]} ({p["nonhabit_vs_ref"]:+}; trips if <= -{NONHABIT_DROP}: {p["nonhabit_trips"]})')
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
    rows = {}
    for seed in a.seeds:
        d = os.path.join(a.root, f's{seed}')
        ks = sorted(int(os.path.basename(p)[5:-5]) for p in glob.glob(os.path.join(d, 'iter-*.json')))
        rows[seed] = [round_row(d, k, cache) for k in ks]
    with open(cpath, 'w') as f:
        json.dump(cache, f)
    ind = indicator(rows, REF)
    with open(os.path.join(out_dir, 'report.json'), 'w') as f:
        json.dump(dict(rounds={str(s): r for s, r in rows.items()}, round4_indicator=ind), f, indent=1)
    md = markdown(rows, ind)
    with open(os.path.join(out_dir, 'report.md'), 'w') as f:
        f.write(md)
    print(md)


if __name__ == '__main__':
    main()
