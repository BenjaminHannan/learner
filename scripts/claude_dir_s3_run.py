#!/usr/bin/env python3
"""dir-s3 numbers (2026-09-29): the dir-h2 recipe with ONE change: what the 4-number token loss is measured against.

dir-h2 (claude_dir_h2_run.py, imported unchanged: same 36,782-pair pool, seeds, steps, nets, tests) trained each 4-number
draw against ONE stored answer, the solver's first find. Here every draw of a 4-number (hand, target) pair has all of its
valid postfix answers (claude_dir_s3_labels.py, code-made, exact checker). Only the number-4 batches change:
  --mode min     token loss = whole-answer cross-entropy against the valid answer the net currently finds cheapest
                 ("min-loss", chosen per graded round from the net's own prediction; the choice carries no gradient)
  --mode random  the control: one valid answer drawn uniformly at random per draw (kept for every graded round of that draw)
The halt target ("exact") is "the net's answer is valid" in both modes (in min mode it equals "equals the chosen answer").
The checker builds training data only; nothing is checked or searched at test time. All other kinds (sums, grids,
3-number puzzles) run through the sealed loss untouched.

  python -B scripts/claude_dir_s3_run.py train --mode min|random --arm loop|plain --seed S --out DIR   (defaults otherwise)
  python -B scripts/claude_dir_s3_run.py eval|poison|extra --ckpt DIR/final.pt ... (as claude_dir_h2_run.py)
  python -B scripts/claude_dir_s3_run.py selftest | smoke
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_h2_run as H  # noqa: E402  (imports the sealed 358u code and swaps in the wide pool)
import claude_dir_s3_labels as LB  # noqa: E402

U, R, E, P = H.U, H.R, H.E, H.P
MODE = {"mode": "min"}
STATE = {"cand": None, "choice": None}         # set by S3Source.batch for the batch being trained
_ORIG = R.ce_and_exact
_BY_HAND, _CACHE = {}, {}


def candidates(hand, target):
    """LongTensor [C, 7] of every valid answer of (hand, target)"""
    key = (tuple(hand), target)
    if key not in _CACHE:
        if key[0] not in _BY_HAND:
            _BY_HAND[key[0]] = LB.answers_by_target(list(key[0]))
        _CACHE[key] = torch.tensor(_BY_HAND[key[0]][target], dtype=torch.long)
    return _CACHE[key]


class S3Source(H.WideSource):
    def __init__(self, seed, latin_pool=20000):
        super().__init__(seed, latin_pool=latin_pool)
        self.pick = random.Random(555000 + seed)            # own RNG for the random arm; never touches the item stream

    def batch(self, B):
        items = super().batch(B)
        STATE["cand"] = STATE["choice"] = None
        if items[0].env == "numbers" and items[0].size == 4:
            cs = [candidates(it.meta["nums"], it.meta["target"]) for it in items]
            STATE["cand"] = cs
            if MODE["mode"] == "random":
                STATE["choice"] = [self.pick.randrange(len(c)) for c in cs]
        return items


R.Source = S3Source


def pad_candidates(cs, device):
    C = max(len(c) for c in cs)
    ct = torch.zeros(len(cs), C, 7, dtype=torch.long)
    ok = torch.zeros(len(cs), C, dtype=torch.bool)
    for i, c in enumerate(cs):
        ct[i, :len(c)] = c
        ok[i, :len(c)] = True
    return ct.to(device), ok.to(device)


def ce_and_exact(logits, s, y):
    cs = STATE["cand"]
    if cs is None:
        return _ORIG(logits, s, y)
    B = s.shape[0]
    s = s.view(B, -1).bool()
    assert bool((s == s[:1]).all()) and int(s[0].sum()) == 7
    pos = s[0].nonzero().squeeze(-1)
    lg = logits.float()[:, pos, :]                                          # [B, 7, V]
    logp = F.log_softmax(lg, -1)
    ct, ok = pad_candidates(cs, lg.device)
    lp = logp.unsqueeze(1).expand(-1, ct.shape[1], -1, -1).gather(3, ct.unsqueeze(-1)).squeeze(-1)   # [B, C, 7]
    nll = -lp.sum(-1)
    if MODE["mode"] == "min":
        choice = nll.detach().masked_fill(~ok, float("inf")).argmin(1)
    else:
        choice = torch.tensor(STATE["choice"], device=lg.device)
    ce = nll.gather(1, choice[:, None]).squeeze(1).mean() / 7
    valid = ((ct == lg.argmax(-1)[:, None, :]).all(-1) & ok).any(1).float()
    return ce, valid


R.ce_and_exact = ce_and_exact


@torch.no_grad()
def extra(a):
    H.extra(a)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    net = R.load(a.ckpt, device)
    practice, _ = H.pools()
    other = [p for p in practice if p[1] != 24]
    sample = random.Random(41709).sample(other, 300)
    rng = random.Random(35835)
    items = [E.number_item(rng, h, t, s) for h, t, s in sample]
    r = R.evaluate(net, items, device)
    res = json.loads(Path(a.out).read_text(encoding="utf-8"))
    res["P_practice_other"] = {"n": len(items), "right": r["right"]}      # report only: 300 practice pairs, target not 24
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("P_practice_other", json.dumps(res["P_practice_other"]), flush=True)


def selftest():
    import random as rd
    torch.manual_seed(0)
    rng = rd.Random(1)
    practice, _ = H.pools()
    pairs = rng.sample(practice, 12)
    items = [E.number_item(rng, h, t, s) for h, t, s in pairs]
    t, s, y, env = R.tensors(items, "cpu")
    V = E.VOCAB
    # 1. one candidate: the new loss equals the sealed loss (nothing but the target changes)
    logits = torch.randn(len(items), 21, V)
    STATE["cand"] = [torch.tensor([list(LB.stored_tokens(s_))]) for _, _, s_ in pairs]
    STATE["choice"] = [0] * len(items)
    MODE["mode"] = "min"
    ce0, ex0 = _ORIG(logits, s, y)
    ce1, ex1 = ce_and_exact(logits, s, y)
    assert abs(float(ce0) - float(ce1)) < 1e-5 and torch.equal(ex0, ex1), (float(ce0), float(ce1))
    print(f"[1] one candidate: ce {float(ce1):.5f} == sealed {float(ce0):.5f}, exact identical")
    # 2. several candidates: min picks the cheapest, exact == valid (checked with the sealed checker), gradient flows
    cs = [candidates(h, tg) for h, tg, _ in pairs]
    assert all(len(c) >= 1 for c in cs)
    STATE["cand"] = cs
    lg = torch.randn(len(items), 21, V, requires_grad=True)
    ce, valid = ce_and_exact(lg, s, y)
    per = [(-F.log_softmax(lg[i, 14:21], -1).gather(1, c.T.reshape(7, -1)).sum(0)).min() / 7 for i, c in enumerate(cs)]
    assert abs(float(ce.detach()) - float(torch.stack(per).mean().detach())) < 1e-4
    ce.backward()
    assert lg.grad is not None and float(lg.grad.abs().sum()) > 0
    assert torch.all(lg.grad[:, :14] == 0), "only the answer slots get gradient"
    print(f"[2] min-loss: ce {float(ce):.4f} equals the brute-force minimum over {sum(len(c) for c in cs)} candidates; gradient only on the 7 answer slots")
    # 3. valid flag: put a valid answer in the logits (must be 1), then a broken one (must be 0), against the sealed checker
    lg = torch.full((len(items), 21, V), -20.0)
    for i, c in enumerate(cs):
        for k, tok in enumerate(c[rd.Random(i).randrange(len(c))].tolist()):
            lg[i, 14 + k, tok] = 20.0
    _, valid = ce_and_exact(lg, s, y)
    assert valid.min() == 1
    for i, (it, ok_) in enumerate(zip(items, valid.tolist())):
        pred = lg[i, 14:21].argmax(-1).tolist()
        assert E.check_numbers(it, pred)
    lg2 = lg.clone()
    lg2[:, 14, :] = -20.0
    lg2[:, 14, E.OPS["+"]] = 20.0            # first token of a postfix answer can never be an operator
    _, valid2 = ce_and_exact(lg2, s, y)
    assert valid2.max() == 0
    print("[3] valid flag: 12 of 12 valid answers flagged 1 (and pass the sealed checker); 12 of 12 broken answers flagged 0")
    # 4. random mode: the chosen answer is the pre-drawn one, kept the same across calls
    MODE["mode"] = "random"
    STATE["choice"] = [min(1, len(c) - 1) for c in cs]
    lgr = torch.randn(len(items), 21, V)
    a1, _ = ce_and_exact(lgr, s, y)
    a2, _ = ce_and_exact(lgr, s, y)
    want = torch.stack([-(F.log_softmax(lgr[i, 14:21], -1).gather(1, cs[i][min(1, len(cs[i]) - 1)].view(7, 1))).sum() / 7 for i in range(len(items))]).mean()
    assert float(a1) == float(a2) and abs(float(a1) - float(want)) < 1e-4
    MODE["mode"] = "min"
    STATE["cand"] = STATE["choice"] = None
    assert ce_and_exact(logits, s, y)[0] == _ORIG(logits, s, y)[0]
    print("[4] random mode uses the pre-drawn answer; other kinds (cand None) fall through to the sealed loss")
    # 5. the source: number-4 batches carry candidates, other batches do not; the item stream is the h2 stream
    import claude_dir_h2_pool as PP
    src, base = S3Source(13), H.WideSource(13)
    got = {"num4": 0, "other": 0}
    for _ in range(60):
        a_, b_ = src.batch(8), base.batch(8)
        assert [i.tokens for i in a_] == [i.tokens for i in b_]
        if a_[0].env == "numbers" and a_[0].size == 4:
            got["num4"] += 1
            assert STATE["cand"] is not None and len(STATE["cand"]) == 8
        else:
            got["other"] += 1
            assert STATE["cand"] is None
    print(f"[5] 60 batches: item stream identical to dir-h2's source; {got['num4']} number-4 batches with candidates, {got['other']} others without")
    print("s3 run selftest ok")


def smoke():
    import argparse
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    for mode in ("min", "random"):
        MODE["mode"] = mode
        for arm in R.ARMS:
            R.train(argparse.Namespace(arm=arm, seed=1, out=tmp / f"{mode}-{arm}", steps=40, batch=16, lr=3e-4, warmup=2,
                                       latin_pool=50, log_every=10))
            print("train ok", mode, arm, flush=True)
    print("s3 smoke ok", tmp)


def pop_mode():
    if "--mode" in sys.argv:
        i = sys.argv.index("--mode")
        MODE["mode"] = sys.argv[i + 1]
        assert MODE["mode"] in ("min", "random")
        del sys.argv[i:i + 2]


if __name__ == "__main__":
    pop_mode()
    if sys.argv[1:] == ["selftest"]:
        selftest()
    elif sys.argv[1:] == ["smoke"]:
        smoke()
    elif sys.argv[1:] == ["check-mask"]:
        U.I2.I.check_mask()
    elif sys.argv[1:2] == ["poison"]:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd"); ap.add_argument("--ckpt", required=True); ap.add_argument("--out", required=True)
        U.poison(ap.parse_args())
    elif sys.argv[1:2] == ["extra"]:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd"); ap.add_argument("--ckpt", required=True); ap.add_argument("--out", required=True)
        extra(ap.parse_args())
    else:
        R.main()
