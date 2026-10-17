"""Zero-training bracket probe: teacher-forced call accuracy by role around the K/J transition, determinism check, product check.
  python out/bracket.py --ckpt ck/L13-LBsoft10/checkpoint.pt --items out/items-L13-LBsoft10.jsonl --tag L13
Writes out/bracket-<tag>.json and out/bracket-<tag>.txt  (--outdir to change)."""
import argparse
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

CELLS = ('HO', 'HPO', 'S', 'HP', 'F4-two')
CAPAT = re.compile(r'[AB]\d[+\-][AB]\d\*\d+')
ROLES = ('R0', 'K_later', 'TRANS', 'J_later', 'JOIN')
BRK = ('nK-1', 'nK', 'nK+1')
GROUPS = ('all', 'CA', 'noCA', 'CA_in_K', 'CA_in_J')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ckpt', required=True)
    ap.add_argument('--items', required=True)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--outdir', default='out')
    ap.add_argument('--bs', type=int, default=64)
    a = ap.parse_args()
    t0 = time.time()
    import torch
    torch.set_num_threads(2)
    from custom_io.models import load_model
    from domain.far import join_gap as JG
    from domain.far import p2_diag as P2
    from domain.tools import sheet

    m = load_model(a.ckpt).eval()
    items = [json.loads(l) for l in open(a.items)]
    items = [r for r in items if r['cell'] in CELLS]
    skipped = Counter()          # cell -> reason -> n
    skip = defaultdict(Counter)
    rows = []
    for r in items:
        f = r['prompt'].split(';', 1)[1].strip()[1:]
        sp = JG.split_formula(f)
        if not sp:
            skip[r['cell']]['no_split'] += 1
            continue
        op, K, J, strict = sp
        nK = len(sheet.evaluate(JG.piece_prompt(r['prompt'], K))['steps'])
        nJ = len(sheet.evaluate(JG.piece_prompt(r['prompt'], J))['steps'])
        steps = [list(s) for s in r['tool_steps']]
        if nK + nJ + 1 != len(steps) or nK < 1 or nJ < 1:
            skip[r['cell']]['bad_len(nK+nJ+1!=len(steps))'] += 1
            continue
        rows.append(dict(it=r, prompt=r['prompt'], tool_value=r['gold'], steps=steps, nK=nK, nJ=nJ, n=len(steps),
                         ca=bool(CAPAT.search(f)), ca_k=bool(CAPAT.search(K)), ca_j=bool(CAPAT.search(J))))
    print('rows to score', len(rows), flush=True)
    tf = P2.teacher_forced(m, rows, bs=a.bs)
    none_ct = Counter()
    gl_ct = Counter()
    scored = []
    for r, res in zip(rows, tf):
        c = r['it']['cell']
        if res is None:
            none_ct[c] += 1
            continue
        gold, mod = res
        if len(gold) != r['n']:
            gl_ct[c] += 1
            skip[c]['tf_gold_len!=steps'] += 1
            continue
        r['ok'] = [JG.same_call(tuple(mod[k]) + ('',), tuple(gold[k]) + ('',)) for k in range(r['n'])]
        r['mod'] = [list(x) for x in mod]
        r['gold'] = [list(x) for x in gold]
        scored.append(r)

    def role_of(k, r):
        if k == 0:
            return 'R0'
        if k == r['n'] - 1:
            return 'JOIN'
        if k < r['nK']:
            return 'K_later'
        if k == r['nK']:
            return 'TRANS'
        return 'J_later'

    def groups_of(r):
        g = ['all', 'CA' if r['ca'] else 'noCA']
        if r['ca_k']:
            g.append('CA_in_K')
        if r['ca_j']:
            g.append('CA_in_J')
        return g

    S = {}
    def slot(cell, grp):
        d = S.setdefault(cell, {}).setdefault(grp, dict(
            items=0, roles={x: [0, 0] for x in ROLES}, bracket={x: [0, 0] for x in BRK},
            by_round={str(k): [0, 0] for k in range(7)},
            tf_all=[0, 0], calls_match=[0, 0], tf_right_cm_wrong=0, tf_wrong_cm_right=0, both_right=0, both_wrong=0))
        return d
    for r in scored:
        cm = bool(r['it']['calls_match'])
        allok = all(r['ok'])
        for cell in (r['it']['cell'], 'ALL'):
            for grp in groups_of(r):
                d = slot(cell, grp)
                d['items'] += 1
                for k in range(r['n']):
                    h = int(r['ok'][k])
                    ro = d['roles'][role_of(k, r)]
                    ro[0] += h; ro[1] += 1
                    br = d['by_round'][str(k)]
                    br[0] += h; br[1] += 1
                for name, k in (('nK-1', r['nK'] - 1), ('nK', r['nK']), ('nK+1', r['nK'] + 1)):
                    if k < r['n'] and not (name == 'nK+1' and k == r['n'] - 1):
                        d['bracket'][name][0] += int(r['ok'][k]); d['bracket'][name][1] += 1
                d['tf_all'][0] += int(allok); d['tf_all'][1] += 1
                d['calls_match'][0] += int(cm); d['calls_match'][1] += 1
                d['tf_right_cm_wrong'] += int(allok and not cm)
                d['tf_wrong_cm_right'] += int((not allok) and cm)
                d['both_right'] += int(allok and cm)
                d['both_wrong'] += int((not allok) and not cm)

    # determinism
    det = {}
    det_examples = []
    def dslot(c):
        return det.setdefault(c, dict(rows_eligible_any=0, total=[0, 0], exact_text=[0, 0], k0=[0, 0], k_gt0=[0, 0],
                                      by_k={str(k): [0, 0] for k in range(7)}))
    for r in scored:
        mc, ts = r['it']['model_calls'], r['it']['tool_steps']
        pref_ok = True
        any_el = False
        for k in range(min(r['n'], len(mc), len(ts))):
            if k > 0:
                p, q = mc[k - 1], ts[k - 1]
                pref_ok = pref_ok and JG.same_call(p, q) and [str(x) for x in p] == [str(x) for x in q]
            if not pref_ok:
                break
            any_el = True
            fr = tuple(str(x) for x in mc[k][:3])
            tfc = tuple(str(x) for x in r['mod'][k])
            agree = JG.same_call(fr + ('',), tfc + ('',))
            exact = fr == tfc
            for c in (r['it']['cell'], 'ALL'):
                d = dslot(c)
                d['total'][0] += int(agree); d['total'][1] += 1
                d['exact_text'][0] += int(exact); d['exact_text'][1] += 1
                z = d['k0'] if k == 0 else d['k_gt0']
                z[0] += int(agree); z[1] += 1
                d['by_k'][str(k)][0] += int(agree); d['by_k'][str(k)][1] += 1
            if not agree and len(det_examples) < 40:
                det_examples.append(dict(id=r['it']['id'], cell=r['it']['cell'], k=k, free_run=list(fr), tf=list(tfc), gold=r['gold'][k]))
        if any_el:
            dslot(r['it']['cell'])['rows_eligible_any'] += 1
            dslot('ALL')['rows_eligible_any'] += 1

    elapsed = time.time() - t0
    out = dict(tag=a.tag, ckpt=a.ckpt, items=a.items, runtime_sec=round(elapsed, 1), cells=list(CELLS),
               rows_scored={c: sum(1 for r in scored if r['it']['cell'] == c) for c in CELLS},
               rows_total_in_dump={c: sum(1 for r in items if r['cell'] == c) for c in CELLS},
               tf_returned_None={c: none_ct.get(c, 0) for c in CELLS},
               skipped={c: dict(skip.get(c, {})) for c in CELLS},
               summary=S, determinism=det, determinism_disagreement_examples=det_examples)
    json.dump(out, open(os.path.join(a.outdir, f'bracket-{a.tag}.json'), 'w'), indent=1)

    # text
    def f(h, n):
        return '    -     ' if not n else f'{h:>4}/{n:<4} {100.0*h/n:5.1f}%'.replace('%', '%')
    def fp(h, n):
        return '-' if not n else f'{h}/{n} ({100.0*h/n:.1f}%)'
    L = []
    L.append(f'BRACKET PROBE  tag={a.tag}  ckpt={a.ckpt}  runtime={elapsed:.0f}s')
    L.append('Cells: ' + ', '.join(CELLS) + '. Accuracy = same_call(TF call, gold call) per call (teacher-forced, tool working on tape); counts are CALLS unless said "items".')
    L.append('Roles: R0=round0; K_later=1..nK-1; TRANS=round nK (J first call); J_later=nK+1..nK+nJ-1; JOIN=last round.')
    L.append('')
    L.append('Rows per cell: in dump / scored / TF None / skipped(no split or bad len or gold len)')
    for c in CELLS:
        L.append(f'  {c:7s} dump={out["rows_total_in_dump"][c]:4d} scored={out["rows_scored"][c]:4d} TF_None={none_ct.get(c,0):3d} skipped={dict(skip.get(c,{}))}')
    L.append('')
    cells = list(CELLS) + ['ALL']
    for title, key, cols in (('ROLE accuracy', 'roles', ROLES), ('BRACKET accuracy (round nK-1 = last K call, nK = first J call, nK+1 = next if not join)', 'bracket', BRK),
                             ('BY ROUND INDEX accuracy', 'by_round', [str(k) for k in range(7)])):
        L.append('=' * 20 + ' ' + title)
        for grp in GROUPS:
            L.append(f'--- group: {grp}')
            L.append(f'{"cell":8s}{"items":>6s}  ' + ''.join(f'{c:>20s}' for c in cols))
            for c in cells:
                d = S.get(c, {}).get(grp)
                if not d:
                    L.append(f'{c:8s}{0:6d}')
                    continue
                L.append(f'{c:8s}{d["items"]:6d}  ' + ''.join(f'{fp(*d[key][x]):>20s}' for x in cols))
        L.append('')
    L.append('=' * 20 + ' PRODUCT: TF-all-right (all rounds of the item right under TF) vs free-run calls_match')
    for grp in GROUPS:
        L.append(f'--- group: {grp}')
        L.append(f'{"cell":8s}{"items":>6s}{"TF_all_right":>20s}{"free_calls_match":>20s}{"TFok&CMno":>11s}{"TFno&CMok":>11s}{"both_ok":>9s}{"both_no":>9s}')
        for c in cells:
            d = S.get(c, {}).get(grp)
            if not d:
                continue
            L.append(f'{c:8s}{d["items"]:6d}{fp(*d["tf_all"]):>20s}{fp(*d["calls_match"]):>20s}{d["tf_right_cm_wrong"]:11d}{d["tf_wrong_cm_right"]:11d}{d["both_right"]:9d}{d["both_wrong"]:9d}')
    L.append('')
    L.append('=' * 20 + ' DETERMINISM: free-run call k vs TF call k, where free-run calls 0..k-1 equal tool steps (same_call AND identical operand/result strings), k < len(tool_steps)')
    L.append('agree = same_call (commutative ops either order); exact = identical (op,a,b) strings')
    L.append(f'{"cell":8s}{"rows":>6s}{"agree(all k)":>20s}{"exact(all k)":>20s}{"k=0":>18s}{"k>0":>18s}')
    for c in cells:
        d = det.get(c)
        if d:
            L.append(f'{c:8s}{d["rows_eligible_any"]:6d}{fp(*d["total"]):>20s}{fp(*d["exact_text"]):>20s}{fp(*d["k0"]):>18s}{fp(*d["k_gt0"]):>18s}')
    L.append('by k (agree):')
    for c in cells:
        d = det.get(c)
        if d:
            L.append(f'  {c:8s}' + '  '.join(f'k{k}:{fp(*d["by_k"][str(k)])}' for k in range(7)))
    L.append(f'disagreement examples (up to 40) are in the json; shown: {min(10, len(det_examples))}')
    for e in det_examples[:10]:
        L.append(f'  {e["cell"]} {e["id"]} k={e["k"]} free={e["free_run"]} tf={e["tf"]} gold={e["gold"]}')
    open(os.path.join(a.outdir, f'bracket-{a.tag}.txt'), 'w').write('\n'.join(L) + '\n')
    print('done', round(elapsed, 1), flush=True)


if __name__ == '__main__':
    main()
