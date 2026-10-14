"""Score a checkpoint with custom_io's own eval code (evalx.evaluate, the same decoding as train.py --final-eval).

  python -m logic_transfer.score --ckpt CKPT --big-data DIR [--logic-dir DIR] [--logic-only] [--threads N] --out OUT.json

--big-data DIR is a skills_curriculum build (DIR/dev/*.jsonl); every one of the six dev splits is scored (in_dist, answer, frame,
vocab, variant, family) with per-family {correct, n}. --logic-dir DIR: every *.jsonl in it (converted rows, see rows.py) is
scored as an extra split named after the file. --logic-only: skip the dev splits (cheap gate scoring; --big-data not needed).
Per split the output holds:
  correct, n, exact, by_family, by_level
  noop_round1: {n, noop, frac} = among rows that have a calculator program (all rows for logic files), the share whose round-1
      op (free run) is NOOP, i.e. the model decides to call no calculator
  answer_words: {family: {gold word: {predicted word or "(other)": count}}} for rows whose gold answer is yes/no/true/false/unknown
  logic files also: by_label, by_depth, by_depth_label {depth: {label: {correct, n}}}
"""
import argparse
import contextlib
import glob
import hashlib
import json
import os
import subprocess
import time

import torch

from custom_io.data import DEV_SPLITS, load_rows
from custom_io.evalx import _dev_rows, evaluate, is_hit, norm
from custom_io.models import load_model
from custom_io.models import progparse as pp

WORDS = ('yes', 'no', 'true', 'false', 'unknown')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def git_sha():
    try:
        return subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True,
                              cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
    except Exception:
        return None


@torch.no_grad()
def round1_noop(model, rows, bs=128, device='cpu'):
    """-> {n, noop, frac}: free-run round-1 op of the rows is NOOP (op index 0). Same batching as evaluate()."""
    from custom_io.data import Dataset, collate, to_device
    was = model.training
    model.eval()
    ds = Dataset(rows, model.vocab, strict=False)
    order = sorted(range(len(rows)), key=lambda i: len(rows[i]['prompt']))
    noop = 0
    for s in range(0, len(order), bs):
        b = to_device(collate([ds[i] for i in order[s:s + bs]]), torch.device(device))
        o = model.run(b)
        noop += int((o['steps'][0][0].argmax(-1) == 0).sum())
    model.train(was)
    return {'n': len(rows), 'noop': noop, 'frac': round(noop / max(len(rows), 1), 4)}


def answer_words(rows, preds):
    out = {}
    for r in rows:
        g = norm(r['answer'])
        if g not in WORDS:
            continue
        p = norm(preds[r['id']])
        h = out.setdefault(r['family'], {}).setdefault(g, {})
        k = p if p in WORDS else '(other)'
        h[k] = h.get(k, 0) + 1
    return out


def cell(d, key, hit):
    c = d.setdefault(str(key), {'correct': 0, 'n': 0})
    c['correct'] += hit
    c['n'] += 1


def analyze(model, rows, bs, logic=False, device='cpu'):
    res = evaluate(model, rows, bs, torch.device(device), return_preds=True)
    preds = res['preds']
    out = {'correct': res['correct'], 'n': res['n'], 'exact': round(res['exact'], 4), 'by_family': res['by_family'],
           'by_level': res['by_level']}
    out['answer_words'] = answer_words(rows, preds)
    calc = rows if logic else [r for r in rows if pp.row_targets(r)['prog']]
    out['noop_round1'] = round1_noop(model, calc, bs, device) if calc else {'n': 0, 'noop': 0, 'frac': None}
    if logic:
        bl, bd, bdl = {}, {}, {}
        for r in rows:
            m = r.get('meta') or {}
            h = int(is_hit(preds[r['id']], r))
            if 'label' in m:
                cell(bl, m['label'], h)
            if 'depth' in m and m['depth'] is not None:
                cell(bd, m['depth'], h)
                cell(bdl.setdefault(str(m['depth']), {}), m.get('label'), h)
        out.update(by_label=bl, by_depth=bd, by_depth_label=bdl)
    return out, preds


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--ckpt', required=True)
    ap.add_argument('--big-data', '--data', dest='big', help='skills_curriculum build dir (with dev/); not needed with --logic-only')
    ap.add_argument('--logic-dir', help='dir of jsonl files (converted logic/placebo rows) scored as extra splits')
    ap.add_argument('--logic-only', action='store_true', help='score only the --logic-dir files (cheap gate scoring)')
    ap.add_argument('--threads', type=int, default=1)
    ap.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    ap.add_argument('--dev-splits', help='comma list of the skills_curriculum dev splits to score (default: all six)')
    ap.add_argument('--eval-batch', type=int, default=128, help='128 = train.py default (batch composition affects padding only)')
    ap.add_argument('--bf16', action='store_true', help='CPU bf16 autocast (default is fp32)')
    ap.add_argument('--save-preds', action='store_true', help='also write OUT.preds.json ({split: {row id: prediction}})')
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    assert a.logic_only and a.logic_dir or a.big, 'need --big-data (or --logic-only with --logic-dir)'
    torch.set_num_threads(a.threads)
    t0 = time.time()
    model = load_model(a.ckpt, a.device)
    amp = (lambda: torch.autocast('cpu', dtype=torch.bfloat16)) if a.bf16 else contextlib.nullcontext
    splits, secs, preds, files = {}, {}, {}, {}
    if not a.logic_only:
        for s in (a.dev_splits.split(',') if a.dev_splits else DEV_SPLITS):
            t = time.time()
            with amp():
                splits[s], preds[s] = analyze(model, _dev_rows(a.big, s, None), a.eval_batch, device=a.device)
            secs[s] = round(time.time() - t, 1)
    if a.logic_dir:
        for p in sorted(glob.glob(os.path.join(a.logic_dir, '*.jsonl'))):
            name = os.path.splitext(os.path.basename(p))[0]
            t = time.time()
            with amp():
                splits[name], preds[name] = analyze(model, load_rows(p, keep=None), a.eval_batch, logic=True, device=a.device)
            secs[name] = round(time.time() - t, 1)
            files[name] = sha256(p)
    res = {'ckpt': a.ckpt, 'ckpt_sha256': sha256(a.ckpt), 'big_data': a.big, 'device': a.device,
           'dtype': 'bfloat16-autocast' if a.bf16 else 'float32', 'threads': a.threads, 'eval_batch': a.eval_batch,
           'torch': torch.__version__, 'git_sha': git_sha(), 'logic_only': a.logic_only, 'logic_files_sha256': files,
           'splits': splits, 'split_seconds': secs, 'wall_s': round(time.time() - t0, 1)}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(res, open(a.out, 'w'), indent=1)
    if a.save_preds:
        json.dump(preds, open(a.out + '.preds.json', 'w'))
    print(json.dumps({k: [v['correct'], v['n']] for k, v in splits.items()}), flush=True)
    print(json.dumps({k: v['noop_round1']['frac'] for k, v in splits.items()}), flush=True)
    print(f'score wall {res["wall_s"]}s', flush=True)
    return res


if __name__ == '__main__':
    main()
