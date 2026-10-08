"""Second-night skills harm, a first look (roadmap 7d / J; the s101 second night costs 3-4 pooled-5 points).
python3 -m creative.harm_look --skills-data ~/work/data_big --out DIR --model s101:N=PATH --model s101:W1=PATH ...

No training. Each model's greedy answers on the skills DEV split in_dist.jsonl (34 families x 200). Per family exact, and per row flips against a reference
(every earlier model in the parent's list): which rows go right -> wrong and wrong -> right, per family. Reads only skills DEV."""
import argparse, json, os
import torch
from creative import sleep
from custom_io.data import load_rows
from custom_io.evalx import CHAIN5, evaluate, is_hit


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
