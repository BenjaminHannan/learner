"""D0 control (MARKS-D0-T1 Amendment 1, PASS-MARKS addendum 16): the D0 reading probe on a reader trained for digits only.
python3 -m custom_io.diag_d0_control [--steps 800] [--out custom_io/results/d0/control_digits_reader.json]
A fresh CharReader with B2's shape (d 256, 2 conv blocks, the same char, position and place tables) is trained on one job only: from the reader
output at the 9 chars ending at each number's last digit, a linear head names the digit at every place 1-9 (or none) and the digit count. Its
prompts are TRAINING prompts with every number replaced by a random 1-9 digit number (never a dev prompt). Then the reader is frozen and scored
with diag_d0's protocol exactly (same dev prompts, same copies, same 75/25 split, a fresh linear probe), so its numbers sit next to B2's."""
import argparse, json, os, random, time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from custom_io.data import DEFAULT_DATA, MAX_PROMPT, CharVocab, Dataset, collate, load_rows
from custom_io.diag_d0 import W, features, prompts, reading
from custom_io.models.progparse import NUM_RE
from custom_io.models.reader import CharReader


class ReaderOnly(nn.Module):
    def __init__(self, vocab, d=256, layers=2):
        super().__init__()
        self.vocab, self.reader = vocab, CharReader(len(vocab), d, layers)
        self.head = nn.Linear(W * d, W * 11 + W)

    def read(self, batch):
        return self.reader(batch)


def windows(X, ps):
    """X [B,T,d] -> ([n, W*d] the 9 chars ending at each 1-9 digit number, reversed; digits [n, W] (10 = none); count [n])."""
    rows, dg, ct = [], [], []
    for i, p in enumerate(ps):
        for mt in NUM_RE.finditer(p):
            s, e = mt.span()
            if e - s > W:
                continue
            idx = torch.arange(e - 1, e - 1 - W, -1)
            ok = idx >= 0
            w = X[i, idx.clamp(min=0)] * ok[:, None].to(X.dtype)
            rows.append(w.reshape(-1))
            d = [10] * W
            d[:e - s] = [int(c) for c in mt.group()[::-1]]
            dg.append(d); ct.append(e - s - 1)
    return torch.stack(rows), torch.tensor(dg), torch.tensor(ct)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=DEFAULT_DATA)
    ap.add_argument('--steps', type=int, default=800)
    ap.add_argument('--batch', type=int, default=64)
    ap.add_argument('--copies', type=int, default=8)
    ap.add_argument('--probe-steps', type=int, default=1500)
    ap.add_argument('--out', default='custom_io/results/d0/control_digits_reader.json')
    a = ap.parse_args(argv)
    torch.set_num_threads(max(1, (os.cpu_count() or 2) // 2))
    t0 = time.time()
    vocab = CharVocab.get(a.data)
    torch.manual_seed(0)
    m = ReaderOnly(vocab)
    rng = random.Random(1)
    rnd = lambda: str(rng.randrange(10 ** (L - 1) if (L := rng.randint(1, W)) > 1 else 0, 10 ** L))
    tr = [r['prompt'] for r in rng.sample(load_rows(os.path.join(a.data, 'train.jsonl'), keep=('prompt',)), 40000)]
    tr = [q for q in (NUM_RE.sub(lambda _: rnd(), p) for p in tr) if len(q) <= MAX_PROMPT and NUM_RE.search(q)]
    opt = torch.optim.Adam(m.parameters(), lr=1e-3)
    log = []
    for step in range(a.steps):
        ps = rng.sample(tr, a.batch)
        b = collate([Dataset([{'prompt': p, 'answer': ''} for p in ps], vocab, strict=False)[i] for i in range(len(ps))])
        Xw, dg, ct = windows(m.read(b)[0], ps)
        out = m.head(Xw)
        loss = F.cross_entropy(out[:, :W * 11].reshape(-1, 11), dg.reshape(-1)) + F.cross_entropy(out[:, W * 11:], ct)
        opt.zero_grad(); loss.backward(); opt.step()
        if (step + 1) % 100 == 0:
            acc = (out[:, :W * 11].reshape(-1, W, 11).argmax(-1) == dg).float().mean().item()
            log.append(dict(step=step + 1, loss=round(loss.item(), 4), train_place_acc=round(100 * acc, 2)))
            print(json.dumps(log[-1]), flush=True)
    m.eval()
    rows, n_groups = prompts(a.data, a.copies)
    ps, groups, kinds = zip(*rows)
    with torch.no_grad():
        Fe = features(m, list(ps))
    res = dict(what='D0 control: a reader of B2 shape trained for digits only, then frozen; diag_d0 reading protocol', train_steps=a.steps,
               batch=a.batch, n_train_prompts=len(tr), train_log=log, copies=a.copies, n_dev_prompts=n_groups,
               reading=reading(Fe, groups, kinds, n_groups, a.probe_steps), seconds=round(time.time() - t0, 1))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps(res['reading']['mark']), json.dumps({k: v['test_sub'] for k, v in res['reading']['window'].items()}))


if __name__ == '__main__':
    main()
