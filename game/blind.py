"""View-blind control arm: fit the model's average move odds over logged views, then play that fixed distribution ignoring the view.

  python -m game.blind --ckpt CKPT --temp T --moves FILE.jsonl.gz --out Q.json [--bs 64] [--threads 1]

qbar = mean over views of softmax(log-probs / T). Score it with game.score --arm blind --probs Q.json.
"""
import argparse
import gzip
import hashlib
import json

import numpy as np
import torch

from game import play

WORDS = play.WORDS


def views_from_moves(path):
    """Views of a moves file (.jsonl.gz, one JSON row per move) in file order, duplicates kept. Refuses sealed worlds."""
    views = []
    with gzip.open(path, 'rt') as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            assert not play.is_sealed(r['world_seed']), 'sealed world in moves file'
            views.append(r['view'])
    return views


def _odds(lp, temp):
    """-> (q rows = softmax(lp / temp), qbar = their mean, mean KL(q_row || qbar) in nats)."""
    z = lp / temp
    z = z - z.max(axis=1, keepdims=True)
    q = np.exp(z)
    q /= q.sum(axis=1, keepdims=True)
    qbar = q.mean(axis=0)
    with np.errstate(divide='ignore', invalid='ignore'):
        t = np.where(q > 0, q * np.log(q / qbar), 0.0)   # 0 log 0 = 0
    return q, qbar, float(t.sum(axis=1).mean())


def fit(m, views, temp, bs=64):
    """Average move odds qbar over the views (softmax at temp), and mean KL(q_row || qbar) in nats.
    Also the same KL at T = 1 and how often the top word is the same across views (addendum A17b: at T0 ~20 a small KL is
    nearly guaranteed by the temperature itself, so view dependence is also read at T = 1)."""
    lp = np.asarray(play.move_logprobs(m, views, bs), dtype=np.float64)
    _, qbar, kl = _odds(lp, temp)
    _, _, kl1 = _odds(lp, 1.0)
    top = np.bincount(lp.argmax(axis=1), minlength=len(WORDS))
    return dict(words=list(WORDS), qbar=qbar.tolist(), mean_kl=kl, n_views=len(views),
                mean_logp=lp.mean(axis=0).tolist(), word_len=[len(w) for w in WORDS],
                mean_kl_t1=kl1, top_counts=top.tolist(), top_share=float(top.max() / max(len(views), 1)))


def blind_policy(qbar):
    """Sampling policy that ignores the view and draws from qbar with the episode's uniform."""
    q = np.asarray(qbar, dtype=np.float64)
    scores = np.where(q > 0, np.log(np.maximum(q, 1e-300)), -np.inf)   # a zero-odds word is never drawn, even at u = 0

    def pick(prompts, us):
        return [WORDS[play.softmax_pick(scores, u, 1.0)] for u in us]
    pick.samples = True
    pick.picker = 'blind'
    return pick


def main(argv=None):
    ap = argparse.ArgumentParser(description='Fit the view-blind move distribution of a checkpoint.')
    ap.add_argument('--ckpt', required=True)
    ap.add_argument('--temp', type=float, required=True)
    ap.add_argument('--moves', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--bs', type=int, default=64)
    ap.add_argument('--threads', type=int, default=1)
    a = ap.parse_args(argv)
    assert a.temp > 0, '--temp must be positive'
    torch.set_num_threads(a.threads)
    from custom_io.models import load_model
    m = load_model(a.ckpt).eval()
    with open(a.ckpt, 'rb') as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    res = fit(m, views_from_moves(a.moves), a.temp, a.bs)
    res.update(ckpt=a.ckpt, ckpt_sha256=sha, temp=a.temp, moves=a.moves)
    with open(a.out, 'w') as f:
        json.dump(res, f, indent=1)
    top = sorted(zip(res['qbar'], WORDS), reverse=True)[:3]
    print('blind n_views', res['n_views'], 'mean_kl', round(res['mean_kl'], 4), 'mean_kl_t1', round(res['mean_kl_t1'], 4),
          'top_share', round(res['top_share'], 3), 'top', ' '.join(f'{w}={q:.3f}' for q, w in top), flush=True)


if __name__ == '__main__':
    main()
