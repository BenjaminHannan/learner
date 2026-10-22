"""Read-only, stdlib only. How much of a training update is padding?
Reads a pool's train.jsonl once (prompt and answer lengths only), then simulates random 256-row updates and compares
  now    : every micro-batch is padded to the WIDEST row of the whole 256-row update (train.py split_batch keeps the padded width)
  sorted : the same rows, sorted by length, cut into the same number of micro-batches, each padded only to its own widest row
  ideal  : no padding at all
Cost units: rows x width (cost that grows with length) and rows x width^2 (attention-like). Numbers are ratios, not seconds.
  python len_pad_sim.py --train POOL/train.jsonl --out OUT.json [--batches 400] [--seed 0] [--batch 256]
"""
import argparse, json, random, sys


def pct(xs, q):
    return xs[min(len(xs) - 1, int(q * (len(xs) - 1)))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--train', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--batches', type=int, default=400)
    ap.add_argument('--batch', type=int, default=256)
    ap.add_argument('--seed', type=int, default=0)
    a = ap.parse_args()
    P, A, F = [], [], []
    with open(a.train, encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            P.append(len(r['prompt']))
            A.append(len(r['answer']))
            F.append(r.get('family') == 'cloze')
    n = len(P)
    sp = sorted(P)
    res = {'rows': n, 'web_cloze_share': sum(F) / n,
           'prompt_chars': {'mean': sum(P) / n, 'p50': pct(sp, .5), 'p90': pct(sp, .9), 'p99': pct(sp, .99), 'max': sp[-1]},
           'answer_chars_mean': sum(A) / n}
    sw = sorted(p for p, w in zip(P, F) if w)
    so = sorted(p for p, w in zip(P, F) if not w)
    if sw:
        res['web_prompt_chars'] = {'mean': sum(sw) / len(sw), 'p50': pct(sw, .5), 'p90': pct(sw, .9), 'p99': pct(sw, .99), 'max': sw[-1]}
    if so:
        res['own_prompt_chars'] = {'mean': sum(so) / len(so), 'p50': pct(so, .5), 'p90': pct(so, .9), 'p99': pct(so, .99), 'max': so[-1]}
    rng = random.Random(a.seed)
    res['sim'] = {}
    for k in (1, 2, 4, 8, 16, 32):
        now1 = now2 = srt1 = srt2 = id1 = id2 = 0.0
        for _ in range(a.batches):
            L = [P[rng.randrange(n)] + 2 for _ in range(a.batch)]      # +2: begin/sep marks (cost scale only)
            W = max(L)
            cuts = [round(i * a.batch / k) for i in range(k + 1)]
            for lo, hi in zip(cuts, cuts[1:]):
                m = hi - lo
                now1 += m * W; now2 += m * W * W
            Ls = sorted(L)
            for lo, hi in zip(cuts, cuts[1:]):
                w = max(Ls[lo:hi]); m = hi - lo
                srt1 += m * w; srt2 += m * w * w
            id1 += sum(L); id2 += sum(x * x for x in L)
        res['sim'][f'accum{k}'] = {'linear_now_over_sorted': now1 / srt1, 'linear_now_over_ideal': now1 / id1,
                                   'linear_sorted_over_ideal': srt1 / id1,
                                   'quadratic_now_over_sorted': now2 / srt2, 'quadratic_now_over_ideal': now2 / id2}
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
