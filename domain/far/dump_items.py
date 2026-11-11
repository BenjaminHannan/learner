"""Per-item outputs of a learn test checkpoint (scoring only, nothing is trained).

learn_probe's scores.jsonl keeps only per-cell counts (n / hits / pct); this re-runs the same scoring path on a saved checkpoint
and writes one JSON line per scored item: the cell, the prompt, the gold answer, the model's answer, hit, the model's calls and
the tool's working, and where the first call differs from the tool's (calls_match, first_diff_round). The cells and rows are the
ones learn_probe.eval_sets builds (same files, same fit sample), so the hit counts must equal the run's scores.jsonl row for
that step (the script prints both and exits 1 on a mismatch).

  python3 -m domain.far.dump_items --ckpt DIR/step_4000/checkpoint.pt --scores DIR/scores.jsonl --step 4000 \
      --train-rows train-rows-l5.jsonl --eval-rows eval-rows-l5.jsonl --probe sheet-probe.jsonl --cells l5 --out items.jsonl
"""
import argparse
import json
import sys

from domain.far import learn_probe as L
from domain.far.join_gap import same_call
from domain.tools import sheet as sheet_tool


def first_diff_round(calls, steps):
    """-> (calls_match, first_diff_round): the first round where the model's call differs from the tool's step (as numbers; add/mul
    either order), len(prefix) when one list is a prefix of the other, None when all rounds agree."""
    for i, (m, t) in enumerate(zip(calls, steps)):
        if not same_call(tuple(m), tuple(t)):
            return False, i
    if len(calls) != len(steps):
        return False, min(len(calls), len(steps))
    return True, None


def dump(ckpt, sets, out_path):
    import torch
    from custom_io.models import load_model
    from domain.mode import greedy
    torch.set_num_threads(2)
    m = load_model(ckpt).eval()
    counts = {}
    with open(out_path, 'w') as f:
        for cell, rows in sets.items():
            res = greedy(m, [r['prompt'] for r in rows])
            hits = 0
            for r, (calls, pred) in zip(rows, res):
                acc = {x.strip() for x in r.get('accepted', [r['answer']])}
                hit = int(pred.strip() in acc)
                steps = sheet_tool.evaluate(r['prompt'])['steps']
                match, diff = first_diff_round([tuple(c) for c in calls], [tuple(s) for s in steps])
                f.write(json.dumps(dict(cell=cell, id=r['id'], kind=r['kind'], prompt=r['prompt'], gold=r['answer'], pred=pred, hit=hit,
                                        model_calls=[list(c) for c in calls], tool_steps=[list(s) for s in steps],
                                        calls_match=match, first_diff_round=diff)) + '\n')
                hits += hit
            counts[cell] = {'n': len(rows), 'hits': hits}
    return counts


def main(argv=None):
    a = argparse.ArgumentParser(description='Per-item outputs of a learn-test checkpoint (scoring only).')
    a.add_argument('--ckpt', required=True)
    a.add_argument('--scores', default=None, help='the run\'s scores.jsonl: the hit counts at --step are compared to this run')
    a.add_argument('--step', type=int, default=None)
    a.add_argument('--train-rows', required=True, help='the run\'s --rows file (the fit sample is drawn from it)')
    a.add_argument('--eval-rows', default=L.L5_EVAL_ROWS)
    a.add_argument('--probe', default=None)
    a.add_argument('--cells', default='l5')
    a.add_argument('--out', required=True)
    a = a.parse_args(argv)
    fit_seed = {'l8': L.L8_SEED, 'l5': L.L5_SEED, 'l4': L.L4_SEED, 'l3': L.L3_SEED}.get(a.cells, L.SEED)   # as learn_probe.train picks it
    sets = L.eval_sets(L.load_jsonl(a.train_rows), a.cells, fit_seed, probe_path=a.probe, l5_path=a.eval_rows)
    counts = dump(a.ckpt, sets, a.out)
    print('per-cell hits:', {c: f'{v["hits"]}/{v["n"]}' for c, v in counts.items()})
    if a.scores:
        want = [json.loads(l) for l in open(a.scores)]
        want = [r for r in want if r['step'] == a.step][-1]['cells']
        bad = {c: (counts[c]['hits'], want[c]['hits']) for c in want if counts[c]['hits'] != want[c]['hits']}
        print('matches the run\'s scores.jsonl at step', a.step) if not bad else print('MISMATCH (here, run):', bad)
        if bad:
            sys.exit(1)


if __name__ == '__main__':
    main()
