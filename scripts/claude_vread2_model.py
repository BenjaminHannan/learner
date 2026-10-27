#!/usr/bin/env python3
"""vread2 (vector-reader thread, 2026-09-28): arm A (vread's vector reader, retrained as it was run) against arm B
(the same reader whose owner pointer gets credit for any copy of the right name). One change, nothing else.

Arm A calls scripts/claude_vread_model.py unchanged (VReader, card_loss, decode, all_right, targets, the 1B encoder,
the random-rounds scheme, the optimiser, 4,000 steps at layer 12, lr, batch).
Arm B differs only where the owner pointer is graded or read:
  - training loss: owner start = -log(sum of the start probabilities over every copy of the labelled owner name);
    owner end = -log(sum of the end probabilities over those copies' ends) (copies: claude_vread2_data.copies);
  - the stop head's "every card cell is exactly right" counts an owner as right when its (start, end) is any copy
    (the same credit; without it the stop target would call B's own correct choices wrong);
  - read time: the owner start and end probabilities are the totals over the copies whose text equals the chosen
    span (the chosen span always counts, even when it is not a whole-word copy).
The pair of arms at one seed shares the 1B forward pass, the batches, the round counts and the initial weights (the
same torch seed before each net is built), so arm A sees exactly the batch stream vread's `train` gives that seed.
Seed 327 is vread's own (init 327, batches 328).

Every read card keeps all 7 probabilities: [exist decision, state, relation, owner start, owner end, value start,
value end]; conf = their lowest (for B with the copy totals; B also keeps the single-position owner probabilities).

  python -B scripts/claude_vread2_model.py gradcheck --base DIR --rows TRAIN.cards.jsonl [--device cpu]
  python -B scripts/claude_vread2_model.py copycheck --base DIR --rows R.cards.jsonl
  python -B scripts/claude_vread2_model.py train --base DIR --train T.cards.jsonl --seed S --out DIR [--steps N]
  python -B scripts/claude_vread2_model.py read --base DIR --ckpt X.pt --arm A|B --rows R.cards.jsonl --out READS
  python -B scripts/claude_vread2_model.py selftest     (loss identity on one copy, no 1B)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_vread_model as VM  # noqa: E402  (read only)
import claude_vread2_data as D2  # noqa: E402

LAYER = 12
SEEDS = (327, 331)
PROB_NAMES = ["exist", "state", "rel", "os", "oe", "vs", "ve"]


# ---------------- arm B: copy credit ----------------
def attach_copies(rows, tok):
    """row["_copies"] = per gold card None (owner me) or [(s, e), ...] token spans of every copy of the owner name"""
    for r in rows:
        offs = tok(r["prompt"], add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
        r["_copies"] = D2.owner_copies(r, offs)
    return rows


def copy_masks(rows, T, device):
    """owner start mask [B, K, T + 1] (ME = index T) and owner end mask [B, K, T]; all False for cells with no card"""
    B = len(rows)
    ms = torch.zeros(B, VM.K, T + 1, dtype=torch.bool)
    me = torch.zeros(B, VM.K, T, dtype=torch.bool)
    for i, r in enumerate(rows):
        for k, cp in enumerate(r["_copies"]):
            if cp is None:
                ms[i, k, T] = True
            else:
                for s, e in cp:
                    ms[i, k, s] = True
                    me[i, k, e] = True
    return ms.to(device), me.to(device)


def set_nll(lg, mask, sel):
    """mean over selected cells of -log(total softmax probability on the mask) = lse(all) - lse(mask)"""
    lg, mask = lg[sel], mask[sel]
    return (torch.logsumexp(lg, -1) - torch.logsumexp(lg.masked_fill(~mask, VM.NEG), -1)).mean()


def card_loss_b(out, tg, ms, me):
    """VM.card_loss with the owner start and end terms summed over copies (same terms, same order)"""
    loss = F.binary_cross_entropy_with_logits(out["exist"], tg["exist"])
    for n in ("state", "rel", "os", "oe", "vs", "ve"):
        t = tg[n]
        if not (t != -100).any():
            continue
        if n == "os":
            loss = loss + set_nll(out["os"], ms, t != -100)
        elif n == "oe":
            loss = loss + set_nll(out["oe"], me, t != -100)
        else:
            loss = loss + F.cross_entropy(out[n].flatten(0, 1), t.flatten(), ignore_index=-100)
    return loss


def all_right_b(dec, tg, rows):
    """VM.all_right, with an owner right when its (start, end) is any copy of the gold name"""
    real = tg["exist"] > 0.5
    ok = dec["exist"] == real
    f_ok = (dec["state"] == tg["state"]) & (dec["rel"] == tg["rel"]) & (dec["vs"] == tg["vs"]) & (dec["ve"] == tg["ve"])
    os_, oe, dme = dec["os"].tolist(), dec["oe"].tolist(), dec["me"].tolist()
    own = torch.zeros_like(ok)
    for i, r in enumerate(rows):
        for k, cp in enumerate(r["_copies"]):
            own[i, k] = bool(dme[i][k]) if cp is None else (not dme[i][k]) and (os_[i][k], oe[i][k]) in cp
    ok = ok & (~real | (f_ok & own))
    return ok.all(-1)


# ---------------- training (both arms, one seed) ----------------
def train_pair(enc, nets, rows, steps, seed, log):
    """VM.train_nets' loop for arm A and arm B on the same batches; A uses VM's loss and stop target unchanged"""
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    rng = random.Random(seed + 1)
    opts = {a: torch.optim.AdamW(n.parameters(), lr=VM.LR, weight_decay=VM.WD) for a, n in nets.items()}
    t0 = time.time()
    for step in range(steps):
        batch = rng.sample(rows, VM.BATCH)
        n_free, n_grad = rng.randint(0, VM.MAX_FREE), rng.randint(1, VM.MAX_GRAD)
        hs, lens = enc(batch)
        tg = VM.targets(batch, enc.device)
        ms, me = copy_masks(batch, hs[LAYER].shape[1], enc.device)
        for arm, net in nets.items():
            net.train()
            for g in opts[arm].param_groups:
                g["lr"] = VM.lr_at(step, steps)
            e, biases, valid = net.prepare(hs[LAYER], lens)
            h = torch.zeros_like(e)
            with torch.no_grad():
                for _ in range(n_free):
                    h = net.step(h, e.detach(), [b.detach() for b in biases])
            h = h.detach()
            loss, right = 0.0, None
            for _ in range(n_grad):
                h = net.step(h, e, biases)
                out = net.read(h, valid)
                with torch.no_grad():
                    dec = VM.decode(out)
                    right = (VM.all_right(dec, tg) if arm == "A" else all_right_b(dec, tg, batch)).float()
                cl = VM.card_loss(out, tg) if arm == "A" else card_loss_b(out, tg, ms, me)
                loss = loss + cl + F.binary_cross_entropy_with_logits(out["halt"], right)
            loss = loss / n_grad
            opts[arm].zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opts[arm].step()
            if step % 100 == 0 or step == steps - 1:
                rec = {"arm": arm, "seed": seed, "step": step, "loss": round(loss.item(), 4),
                       "right": round(right.mean().item(), 3), "rounds": n_free + n_grad,
                       "min": round((time.time() - t0) / 60, 2)}
                log.write(json.dumps(rec) + "\n")
                log.flush()
                print(json.dumps(rec), flush=True)


def build_nets(seed, device):
    nets = {}
    for arm in ("A", "B"):
        torch.manual_seed(seed)                     # both arms start from the same weights (vread: manual_seed(SEED))
        nets[arm] = VM.VReader().to(device)
    return nets


def cmd_train(a):
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    enc = VM.Encoder(a.base, dev, [LAYER])
    rows = attach_copies(VM.load_rows(a.train), enc.tok)
    nets = build_nets(a.seed, dev)
    t0 = time.time()
    with open(out / "train_log.jsonl", "w") as log:
        train_pair(enc, nets, rows, a.steps or VM.STEPS_FINAL, a.seed, log)
    summ = {"seed": a.seed, "layer": LAYER, "steps": a.steps or VM.STEPS_FINAL, "train_rows": len(rows),
            "batch": VM.BATCH, "lr": VM.LR, "trainable_weights": VM.n_trainable(nets["A"]),
            "minutes": round((time.time() - t0) / 60, 2), "torch": torch.__version__, "device": dev,
            "gpu": torch.cuda.get_device_name(0) if dev == "cuda" else None, "ckpt_sha256": {}}
    for arm, net in nets.items():
        p = out / f"{arm}-s{a.seed}.pt"
        VM.save(net, LAYER, p, extra={"arm": arm, "seed": a.seed})
        summ["ckpt_sha256"][p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    (out / "summary.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ))


# ---------------- reading ----------------
def probs7(out):
    """VM.decode's decisions plus its 7 choice probabilities per card cell [K, 7] (row 0 of a batch of 1)"""
    dec = VM.decode(out)
    T = out["vs"].shape[-1]
    p_exist = torch.sigmoid(out["exist"])
    exist_p = torch.where(dec["exist"], p_exist, 1 - p_exist)
    st_p = out["state"].softmax(-1).max(-1).values
    rl_p = out["rel"].softmax(-1).max(-1).values
    os_p = out["os"].softmax(-1).max(-1).values
    _, oe_p = VM.span_end(out["oe"], dec["os"].clamp(max=T - 1))
    oe_p = torch.where(dec["me"], torch.ones_like(oe_p), oe_p)
    vs_p = out["vs"].softmax(-1).max(-1).values
    _, ve_p = VM.span_end(out["ve"], dec["vs"])
    P = torch.stack([exist_p, st_p, rl_p, os_p, oe_p, vs_p, ve_p], -1)
    return dec, P


@torch.no_grad()
def read_rows(enc, net, rows, arm):
    """VM.read_rows (1B forward, rounds until the stop head says p > 0.5, else the most confident of 16), keeping the
    7 probabilities; arm B's owner start / end probabilities are the totals over the chosen text's copies"""
    net.eval()
    outs = []
    for r in rows:
        t0 = time.perf_counter()
        hs, lens = enc([r])
        e, biases, valid = net.prepare(hs[LAYER], lens)
        h = torch.zeros_like(e)
        best = None
        for rd in range(1, VM.MAX_ROUNDS + 1):
            h = net.step(h, e, biases)
            out = net.read(h, valid)
            q = torch.sigmoid(out["halt"])[0].item()
            if best is None or q > best[0]:
                best = (q, rd, out)
            if q > 0.5:
                best = (q, rd, out)
                break
        dec, P = probs7(best[2])
        dec = {k: v[0].tolist() for k, v in dec.items()}
        P = P[0].tolist()
        o = best[2]
        os_sm, oe_sm = o["os"][0].softmax(-1).tolist(), o["oe"][0].softmax(-1).tolist()
        ms = (time.perf_counter() - t0) * 1000
        offs = enc.tok(r["prompt"], add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
        regions = D2.row_regions(r)
        cards = []
        for k in range(VM.K):
            if not dec["exist"][k]:
                continue
            p7 = list(P[k])
            own = "me" if dec["me"][k] else VM.card_text(r["prompt"], offs, dec["os"][k], dec["oe"][k])
            c = {"owner": own, "rel": VM.REL[dec["rel"][k]],
                 "value": VM.card_text(r["prompt"], offs, dec["vs"][k], dec["ve"][k]),
                 "state": VM.STATE_IDS[dec["state"][k]],
                 "owner_tokens": None if dec["me"][k] else [dec["os"][k], dec["oe"][k]],
                 "value_tokens": [dec["vs"][k], dec["ve"][k]]}
            if arm == "B" and not dec["me"][k]:
                span = (dec["os"][k], dec["oe"][k])
                cps = sorted(set(D2.copies(own, r["prompt"], regions, offs)) | {span}) if own else [span]
                c["owner_copies"] = [list(x) for x in cps]
                c["p_os_single"], c["p_oe_single"] = round(p7[3], 6), round(p7[4], 6)
                p7[3] = min(1.0, sum(os_sm[k][s] for s in {x[0] for x in cps}))
                p7[4] = min(1.0, sum(oe_sm[k][x] for x in {x[1] for x in cps}))
            c["p7"] = [round(x, 6) for x in p7]
            c["conf"] = round(min(p7), 6) if arm == "B" else round(dec["conf"][k], 6)   # A: VM.decode's own conf
            if arm == "A" and min(P[k]) != dec["conf"][k]:
                c["p7_min_differs"] = True                                          # never expected
            cards.append(c)
        outs.append({"id": r["id"], "cards": cards, "rounds": best[1], "halt_p": round(best[0], 4),
                     "ms": round(ms, 2)})
    return outs


def cmd_read(a):
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    net, layer = VM.load_net(a.ckpt, dev)
    assert layer == LAYER
    enc = VM.Encoder(a.base, dev, [LAYER])
    rows = VM.load_rows(a.rows)[: a.limit] if a.limit else VM.load_rows(a.rows)
    reads = read_rows(enc, net, rows, a.arm)
    Path(a.out).write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in reads), encoding="utf-8")
    ms = sorted(x["ms"] for x in reads)
    print(json.dumps({"read": len(reads), "arm": a.arm, "ckpt": Path(a.ckpt).name, "ms_median": ms[len(ms) // 2],
                      "rounds_mean": round(sum(x["rounds"] for x in reads) / len(reads), 3)}))


# ---------------- checks ----------------
def gradcheck(a):
    """one step of both arms, fp32, no autocast: every trainable tensor of each net gets a nonzero gradient, the 1B
    none; and arm B's loss equals arm A's on a batch where every owner name has one copy"""
    dev = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.backends.cuda.matmul.allow_tf32 = False
    enc = VM.Encoder(a.base, dev, [LAYER])
    rows = attach_copies([r for r in VM.load_rows(a.rows)][:400], enc.tok)
    multi = [r for r in rows if any(cp and len(cp) > 1 for cp in r["_copies"])][:4]
    single = [r for r in rows if r["cards"] and all(cp is None or len(cp) == 1 for cp in r["_copies"])][:6]
    batch = multi + single + [r for r in rows if not r["cards"]][:2]
    hs, lens = enc(batch)
    tg = VM.targets(batch, dev)
    res = {"device": dev, "torch": torch.__version__, "rows_with_multi_copy_owner": len(multi)}
    nets = build_nets(VM.SEED, dev)
    for arm, net in nets.items():
        e, biases, valid = net.prepare(hs[LAYER], lens)
        h = torch.zeros_like(e)
        loss = 0.0
        for _ in range(2):
            h = net.step(h, e, biases)
            out = net.read(h, valid)
            dec = VM.decode(out)
            right = (VM.all_right(dec, tg) if arm == "A" else all_right_b(dec, tg, batch)).float()
            ms, me = copy_masks(batch, hs[LAYER].shape[1], dev)
            cl = VM.card_loss(out, tg) if arm == "A" else card_loss_b(out, tg, ms, me)
            loss = loss + cl + F.binary_cross_entropy_with_logits(out["halt"], right)
        loss.backward()
        zero = [n for n, p in net.named_parameters() if p.grad is None or p.grad.abs().sum().item() == 0]
        res[arm] = {"trainable_tensors": sum(1 for p in net.parameters()), "zero_or_none_grad": zero,
                    "loss": round(loss.item(), 5)}
    base_grads = sum(1 for p in enc.model.parameters() if p.grad is not None)
    # identity on single-copy rows: B's loss == A's loss (same net, same output)
    sb = [r for r in batch if r in single]
    hs1, l1 = enc(sb)
    tg1 = VM.targets(sb, dev)
    net = nets["A"]
    with torch.no_grad():
        e, biases, valid = net.prepare(hs1[LAYER], l1)
        out = net.read(net.step(torch.zeros_like(e), e, biases), valid)
        ms, me = copy_masks(sb, hs1[LAYER].shape[1], dev)
        la, lb = VM.card_loss(out, tg1).item(), card_loss_b(out, tg1, ms, me).item()
    res.update({"frozen_1b_params_with_grad": base_grads, "single_copy_loss_A": round(la, 6),
                "single_copy_loss_B": round(lb, 6), "single_copy_equal": abs(la - lb) < 1e-4 * max(1, abs(la))})
    ok = not res["A"]["zero_or_none_grad"] and not res["B"]["zero_or_none_grad"] and base_grads == 0 \
        and res["single_copy_equal"] and len(multi) > 0
    res["gradcheck"] = "OK" if ok else "FAIL"
    print(json.dumps(res))
    assert ok


def copycheck(a):
    """every named-owner gold card: its label pointer is one of its copies and every copy decodes to the owner text"""
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.base)
    rows = VM.load_rows(a.rows)
    n = bad = multi = 0
    for r in rows:
        offs = tok(r["prompt"], add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
        for c, cp in zip(r["cards"], D2.owner_copies(r, offs)):
            if cp is None:
                continue
            n += 1
            multi += len(cp) > 1
            bad += any(VM.card_text(r["prompt"], offs, s, e) != c["owner"] for s, e in cp)
    res = {"copycheck": "OK" if not bad else "FAIL", "rows": len(rows), "named_owner_cards": n,
           "with_2plus_copies": multi, "copies_not_decoding_to_owner": bad}
    print(json.dumps(res))
    assert not bad


def selftest():
    torch.manual_seed(0)
    B, T = 3, 10
    out = {"exist": torch.randn(B, VM.K), "state": torch.randn(B, VM.K, 3), "rel": torch.randn(B, VM.K, len(VM.REL)),
           "os": torch.randn(B, VM.K, T + 1), "oe": torch.randn(B, VM.K, T), "vs": torch.randn(B, VM.K, T),
           "ve": torch.randn(B, VM.K, T)}
    rows = [{"id": "a", "cards": [{"owner_ptr": {"tokens": [2, 3]}, "value_ptr": {"tokens": [5, 5]},
                                   "state": "current", "rel": "city"},
                                  {"owner_ptr": "ME", "value_ptr": {"tokens": [7, 8]}, "state": "former",
                                   "rel": "boss"}], "_copies": [[(2, 3)], None]},
            {"id": "b", "cards": [], "_copies": []},
            {"id": "c", "cards": [{"owner_ptr": {"tokens": [6, 6]}, "value_ptr": {"tokens": [1, 1]},
                                   "state": "correction", "rel": "age"}], "_copies": [[(6, 6)]]}]
    tg = VM.targets(rows, "cpu")
    ms, me = copy_masks(rows, T, "cpu")
    la, lb = VM.card_loss(out, tg).item(), card_loss_b(out, tg, ms, me).item()
    assert abs(la - lb) < 1e-5, (la, lb)
    rows[0]["_copies"][0] = [(0, 1), (2, 3)]                      # a second copy can only lower the owner loss
    ms2, me2 = copy_masks(rows, T, "cpu")
    assert card_loss_b(out, tg, ms2, me2).item() < lb
    # all_right_b: owner on the other copy counts as right; A's all_right does not
    dec = {"exist": tg["exist"] > 0.5, "state": tg["state"], "rel": tg["rel"], "vs": tg["vs"], "ve": tg["ve"],
           "os": tg["os"].clone(), "oe": tg["oe"].clone(), "me": tg["os"] == -1}
    dec["os"][0, 0], dec["oe"][0, 0] = 0, 1
    assert all_right_b(dec, tg, rows).tolist() == [True, True, True]
    assert VM.all_right(dec, tg).tolist() == [False, True, True]
    dec["oe"][0, 0] = 3                                           # start of one copy, end of another: not right
    assert all_right_b(dec, tg, rows).tolist() == [False, True, True]
    print(f"vread2 model selftest ok: B loss == A loss with one copy ({la:.5f}), lower with two, stop target credit")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gradcheck", "copycheck", "train", "read", "selftest"])
    ap.add_argument("--base")
    ap.add_argument("--rows")
    ap.add_argument("--train")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--steps", type=int, default=None)
    ap.add_argument("--ckpt")
    ap.add_argument("--arm", choices=["A", "B"])
    ap.add_argument("--out")
    ap.add_argument("--device")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--batch", type=int, default=None, help="smoke tests only")
    a = ap.parse_args()
    if a.batch:
        VM.BATCH = a.batch
    if a.cmd == "selftest":
        return selftest()
    {"gradcheck": gradcheck, "copycheck": copycheck, "train": cmd_train, "read": cmd_read}[a.cmd](a)


if __name__ == "__main__":
    main()
