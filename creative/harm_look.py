"""Second-night skills harm, a first look (roadmap 7d / J; the s101 second night costs 3-4 pooled-5 points).
python3 -m creative.harm_look --skills-data ~/work/data_big --out DIR --model s101:N=PATH --model s101:W1=PATH ...

No training. Each model's greedy answers on the skills DEV split in_dist.jsonl (34 families x 200). Per family exact, and per row flips against a reference
(every earlier model in the parent's list): which rows go right -> wrong and wrong -> right, per family. Reads only skills DEV."""
import argparse, json, os
import torch
from creative import sleep
from custom_io.data import load_rows
from custom_io.evalx import CHAIN5, evaluate, is_hit


def skills_hits(model, skills_data, device='cpu'):
    """One greedy pass on skills DEV in_dist. -> (rows, per-row 0/1 hits, pooled-5 %, in_dist %)."""
    rows = load_rows(os.path.join(skills_data, 'dev', 'in_dist.jsonl'))
    e = evaluate(model, rows, 128, device, return_preds=True)
    h = [int(is_hit(e['preds'][r['id']], r)) for r in rows]
    c5 = [x for x, r in zip(h, rows) if r['family'] in CHAIN5]
    return rows, h, 100 * sum(c5) / max(len(c5), 1), 100 * sum(h) / max(len(h), 1)


def harm_measure(hits_a, hits_b, rows, family_drop=5.0, in_dist_drop=1.5):
    """The sleep harm measure (roadmap e9e0bd2aeb): model b against reference a on the same in_dist rows. A family fires when it drops more than `family_drop` points
    AND the paired 95% interval of b - a over its rows is below 0; passes = in_dist drop <= `in_dist_drop` and no family fires."""
    from creative import c2_pilot
    fams = {}
    for i, r in enumerate(rows):
        fams.setdefault(r['family'], []).append(i)
    pct = lambda h, ix: 100 * sum(h[i] for i in ix) / len(ix)
    out, fired = {}, []
    for f, ix in sorted(fams.items()):
        d, lo, hi = c2_pilot.boot([hits_b[i] for i in ix], [hits_a[i] for i in ix])
        fires = -d > family_drop and hi < 0
        out[f] = dict(a=pct(hits_a, ix), b=pct(hits_b, ix), drop=-d, lo=lo, hi=hi, fires=fires)
        if fires:
            fired.append(f)
    allix = range(len(rows))
    ia, ib = pct(hits_a, allix), pct(hits_b, allix)
    return dict(in_dist_a=ia, in_dist_b=ib, in_dist_drop=ia - ib, families=out, fired=fired, passes=ia - ib <= in_dist_drop and not fired,
                rule=f'in_dist drop <= {in_dist_drop} and no family with drop > {family_drop} and paired 95% interval below 0')


def look(models, skills_data, out, device='cpu', log=print):
    rows = load_rows(os.path.join(skills_data, 'dev', 'in_dist.jsonl'))
    fam = sorted({r['family'] for r in rows})
    res, hits = {}, {}
    for parent, label, path in models:
        m, _, _ = sleep.load_parent(os.path.expanduser(path), device)
        m.eval()
        e = evaluate(m, rows, 128, device, return_preds=True)
        h = [int(is_hit(e['preds'][r['id']], r)) for r in rows]
        hits[(parent, label)] = h
        res.setdefault(parent, {})[label] = dict(path=path, in_dist=e['exact'], pooled5=100 * sum(x for x, r in zip(h, rows) if r['family'] in CHAIN5) / sum(r['family'] in CHAIN5 for r in rows),
                                                  by_family={f: 100 * v['correct'] / v['n'] for f, v in e['by_family'].items()})
        log(parent, label, round(e['exact'], 2), round(res[parent][label]['pooled5'], 2))
    for parent, labels in res.items():
        ls = list(labels)
        for i, b in enumerate(ls):                                      # each model against every model before it in its list
            for a in ls[:i]:
                ha, hb = hits[(parent, a)], hits[(parent, b)]
                lost = {f: sum(1 for x, y, r in zip(ha, hb, rows) if r['family'] == f and x and not y) for f in fam}
                gained = {f: sum(1 for x, y, r in zip(ha, hb, rows) if r['family'] == f and y and not x) for f in fam}
                net = sorted(((gained[f] - lost[f], f) for f in fam))
                labels[b]['vs_' + a] = dict(lost=sum(lost.values()), gained=sum(gained.values()), worst_families=[(f, n, lost[f], gained[f]) for n, f in net[:8]],
                                            chain5_lost=sum(lost[f] for f in CHAIN5), chain5_gained=sum(gained[f] for f in CHAIN5))
                log(parent, b, 'vs', a, 'lost', sum(lost.values()), 'gained', sum(gained.values()), 'worst', net[:6])
    os.makedirs(out, exist_ok=True)
    json.dump(res, open(os.path.join(out, 'harm_look.json'), 'w'), indent=1)
    return res


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--skills-data', required=True); a.add_argument('--out', required=True); a.add_argument('--threads', type=int)
    a.add_argument('--model', action='append', required=True, help='PARENT:LABEL=PATH, in order per parent (each is compared with every earlier one)')
    a = a.parse_args()
    if a.threads:
        torch.set_num_threads(a.threads)
    ms = []
    for s in a.model:
        k, path = s.split('=', 1)
        parent, label = k.split(':', 1)
        ms.append((parent, label, path))
    look(ms, os.path.expanduser(a.skills_data), a.out)
