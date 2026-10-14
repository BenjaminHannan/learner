"""Positive control for the whole decode path (mode head -> WORD pointer -> text -> is_hit): the PARENT s200 checkpoint on the curriculum
families whose answer is a word copied from the prompt (prop_eval: 'true'/'false' answers like the logic task; copy_word, object_track,
seq_cycle, group_induct; syllogism yes/no). The parent was trained on these, so a working scorer must show high accuracy here.
One checkpoint, one thread, evalx.evaluate (the scorer's own call) + state()/talk(return_modes) for the mode counts.

  PYTHONPATH=<worktree> python s5_positive_control.py --ckpt <path> --tag parent
"""
import argparse
import collections
import json

import torch

torch.set_num_threads(1)
from common import *          # noqa
from custom_io import evalx
from custom_io.data import Dataset, collate, load_rows, to_device
from custom_io.models import load_model
from custom_io.models import progparse as pp

DEVDIR = '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/data/sk200k/dev'
FAMS = ('prop_eval', 'copy_word', 'syllogism', 'object_track', 'seq_cycle', 'group_induct')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ckpt', required=True)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--cap', type=int, default=60)
    a = ap.parse_args()
    model = load_model(a.ckpt, 'cpu')
    R = {'ckpt': a.ckpt}
    for split in ('in_dist', 'answer', 'frame', 'variant'):
        rows = [r for r in load_rows(f'{DEVDIR}/{split}.jsonl') if r['family'] in FAMS]
        cnt = collections.Counter()
        keep = []
        for r in rows:
            if cnt[r['family']] < a.cap:
                cnt[r['family']] += 1
                keep.append(r)
        res = evalx.evaluate(model, keep, 128, torch.device('cpu'), return_preds=True)
        # modes
        ds = Dataset(keep, model.vocab, strict=False)
        modes = collections.defaultdict(collections.Counter)
        order = sorted(range(len(keep)), key=lambda i: len(keep[i]['prompt']))
        with torch.no_grad():
            for s in range(0, len(order), 128):
                ids = order[s:s + 128]
                b = to_device(collate([ds[i] for i in ids]), torch.device('cpu'))
                _, md = model.talk(model.state(b), b, return_modes=True)
                for i, m in zip(ids, md):
                    modes[keep[i]['family']][m] += 1
        R[split] = dict(correct=res['correct'], n=res['n'], by_family={f: [v['correct'], v['n']] for f, v in res['by_family'].items()},
                        modes_NUM0_WORD1_GEN2={f: [c.get(0, 0), c.get(1, 0), c.get(2, 0)] for f, c in modes.items()},
                        train_mode_label_counts={f: [sum(pp.row_targets(r)['mode'] == k for r in keep if r['family'] == f) for k in range(3)] for f in modes})
        if split == 'in_dist':
            pe = [r for r in keep if r['family'] == 'prop_eval']
            R['prop_eval_in_dist_label_share'] = dict(collections.Counter(r['answer'] for r in pe))
            R['prop_eval_in_dist_preds'] = collections.Counter(res['preds'][r['id']] for r in pe)
    wjson(f's5_{a.tag}.json', R)
    print(json.dumps(R, indent=1))


if __name__ == '__main__':
    main()
