"""8b screen readout (design/8b-gemma-growth-2026-10-08.md sections 5 and 6, fixed before any run).
  python g8b/analysis/screen_readout.py EGA_DIR LADDER_DIR [G_DIR] [--ctl EGE36_DIR] > g8b/analysis/screen_readout.txt
EGA_DIR    the arm judged (8a-{3M,10M}-s{400,401}-B2/ from the 8b boxes): results/8b/EGA36, or results/8b/EGE36 for that arm
--ctl      with EGA36: results/8b/EGE36, the one-change control (addendum B rules); without it, section 5's rules
LADDER_DIR results/8a-ladder of claude/project-thread-yha868 (B2, PT, LLM on the same seeds)
G_DIR      optional: 8a-G results with G-B2 / G-PT folders named 8a-{rung}-s{seed}-{B2,PT} (used for the G-PT part of the go rule)."""
import json, os, statistics as st, sys

SEEDS = [400, 401]
SPL = ['in_dist', 'answer', 'frame', 'vocab', 'variant']
FAMS = ['seq_next', 'fewshot_number_rule', 'rule_apply', 'digits_parity', 'order_chain', 'table_lookup', 'list_index', 'cipher_map']


def res(d, rung, s, arm):
    p = os.path.join(d, f'8a-{rung}-s{s}-{arm}', 'RESULT.json')
    return json.load(open(p)) if os.path.exists(p) else None


def pooled5(r, sec=None):
    fe = sec or r['final_eval']
    return 100 * sum(fe[x]['correct'] for x in SPL) / sum(fe[x]['n'] for x in SPL)


def fam(r, f, sec=None):
    fe = sec or r['final_eval']
    c = sum(fe[x]['by_family'].get(f, {}).get('correct', 0) for x in SPL)
    n = sum(fe[x]['by_family'].get(f, {}).get('n', 0) for x in SPL)
    return 100 * c / n if n else float('nan')


def loss_gap(d3, d10, s, key):
    """mean training `key` over logged steps >= 20,000: 3M minus 10M"""
    out = []
    for d, rung in ((d3, '3M'), (d10, '10M')):
        ev = [json.loads(x) for x in open(os.path.join(d, f'8a-{rung}-s{s}-B2', 'stdout.events.txt')) if x.startswith('{')]
        out.append(st.mean(e[key] for e in ev if e.get('event') == 'train' and e['step'] >= 20000))
    return out[0] - out[1]


ARM = os.environ.get('ARM', 'EGA')     # EGE36 when judging that arm alone


def main():
    argv = sys.argv[1:]
    ctl = None
    if '--ctl' in argv:
        i = argv.index('--ctl'); ctl = argv[i + 1]; del argv[i:i + 2]
    ega, lad = argv[0], argv[1]
    gdir = argv[2] if len(argv) > 2 else None
    rows, go_pt, go_b2, go_gpt, stop = [], [], [], [], []
    for s in SEEDS:
        e3, e10 = res(ega, '3M', s, 'B2'), res(ega, '10M', s, 'B2')
        if not (e3 and e10):
            print(f'seed {s}: missing EGA result(s): 3M {bool(e3)} 10M {bool(e10)}')
            continue
        d = {}
        for name, arm, dd in (('EGA', 'B2', ega), ('B2', 'B2', lad), ('PT', 'PT', lad), ('LLM', 'LLM', lad)):
            a, b = res(dd, '3M', s, arm), res(dd, '10M', s, arm)
            d[name] = (pooled5(a), pooled5(b), pooled5(b) - pooled5(a)) if a and b else None
        if ctl:
            a, b = res(ctl, '3M', s, 'B2'), res(ctl, '10M', s, 'B2')
            d['CTL'] = (pooled5(a), pooled5(b), pooled5(b) - pooled5(a)) if a and b else None
        if gdir:
            for name, arm in (('G-B2', 'B2'), ('G-PT', 'PT')):
                a, b = res(gdir, '3M', s, arm), res(gdir, '10M', s, arm)
                d[name] = (pooled5(a), pooled5(b), pooled5(b) - pooled5(a)) if a and b else None
        g = d['EGA'][2]
        print(f'seed {s}: ' + '; '.join(f'{k} {v[0]:.2f} -> {v[1]:.2f} (d {v[2]:+.2f})' for k, v in d.items() if v))
        yard = d['G-PT'][2] if d.get('G-PT') else d['PT'][2]          # addendum B: 8a-G's G-PT replaces PT once it lands
        if ctl:             # addendum B, EGA36 against its control EGE36
            go_pt.append(g - yard >= 1.0)
            go_b2.append(d['CTL'] is not None and g - d['CTL'][2] >= 2.0)
            stop.append(d['CTL'] is not None and g - d['CTL'][2] < 1.0)
        elif ARM == 'EGE36':     # addendum B, EGE36 alone
            go_pt.append(g - yard >= 1.0)
            go_b2.append(True)
            stop.append(g - d['B2'][2] < 1.0)
        else:               # section 5
            go_pt.append(g - d['PT'][2] >= 1.0)
            go_b2.append(g - d['B2'][2] >= 3.0)
            stop.append(g - d['B2'][2] < 1.0)
        if d.get('G-PT') and not ctl and ARM != 'EGE36':
            go_gpt.append(g - d['G-PT'][2] >= 1.0)
        print(f'  d_EGA - d_PT {g - d["PT"][2]:+.2f}   d_EGA - d_B2 {g - d["B2"][2]:+.2f}   d_EGA - d_LLM {g - d["LLM"][2]:+.2f}'
              + (f'   d_EGA - d_G-PT {g - d["G-PT"][2]:+.2f}' if d.get('G-PT') else '')
              + (f'   d_EGA - d_CTL {g - d["CTL"][2]:+.2f}' if d.get('CTL') else ''))
        if d.get('G-B2'):
            print(f'  vs 8a-G EGE (9 slots, cut targets): 3M {d["EGA"][0] - d["G-B2"][0]:+.2f}, 10M {d["EGA"][1] - d["G-B2"][1]:+.2f}')
        for rung, r in (('3M', e3), ('10M', e10)):
            full = pooled5(r)
            off = pooled5(r, r['lesions']['loops:0'])
            c5 = r['chain5']['intact']['exact']
            cm = fam(r, 'cipher_map')
            ok = c5 >= 99 and cm >= 90 and off <= full / 2
            print(f'  guard {rung}: chain-5 {c5:.1f} (>= 99), cipher_map {cm:.1f} (>= 90), thinker off {off:.2f} <= {full / 2:.2f} -> {"ok" if ok else "FAILED (seed void)"}')
            if not ok:
                go_pt[-1] = go_b2[-1] = False
                stop[-1] = False
        try:
            print(f'  training-loss gap 3M - 10M over steps 20k-24k: total {loss_gap(ega, ega, s, "loss"):+.3f} (>= 0.05), GEN {loss_gap(ega, ega, s, "gen"):+.3f} (>= 0.03)')
        except (OSError, ValueError, KeyError) as ex:
            print('  loss gap: n/a', ex)
        b3, b10 = res(lad, '3M', s, 'B2'), res(lad, '10M', s, 'B2')
        print('  families (EGA 3M -> 10M | B2 3M -> 10M): ' + ', '.join(f'{f} {fam(e3, f):.1f}->{fam(e10, f):.1f} | {fam(b3, f):.1f}->{fam(b10, f):.1f}' for f in FAMS))
        for rung, r in (('3M', e3), ('10M', e10)):
            sz = r.get('extra', {}).get('size')
            print(f'  size {rung}: trained {r["n_params"]:,}' + (f', whole {sz["whole"]:,} (EmbeddingGemma 2 counted)' if sz else '') + f', {r["steps_per_s"]:.2f} updates/s')
    n = len(stop)
    if n < len(SEEDS):
        verdict = 'INCOMPLETE'
    elif all(go_pt) and all(go_b2) and (ctl or ARM == 'EGE36' or not gdir or (len(go_gpt) == n and all(go_gpt))):
        verdict = 'GO to 6 seeds'
    elif all(stop):
        verdict = 'STOP' 
    else:
        verdict = 'UNCLEAR (seeds 402-403 next)'
    print('VERDICT:', verdict)


if __name__ == '__main__':
    main()
