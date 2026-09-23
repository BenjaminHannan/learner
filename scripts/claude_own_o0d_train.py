"""own-O0d TRAINER (plan S2.3): (a) masked-span pretraining, (b) frame training.

  - CPU only here; bf16 autocast only when CUDA exists.
  - Resume-safe atomic checkpoints every --ckpt-minutes (default 10) and every
    --ckpt-steps (0 = off): write tmp + fsync + os.replace; restart from newest.
  - Deterministic: --seed sets python/numpy/torch seeds; data order is a pure
    function of step (no stateful loader), RNG states stored in checkpoints.
  - Toy frame/text generator inside this task (fictional names only).

Usage:
  uv run ... python -B scripts/claude_own_o0d_train.py --mode frame --workdir DIR ...
"""

import argparse
import json
import os
import random
import time

import numpy as np
import torch
import torch.nn.functional as F

from claude_own_o0d_model import (
    ACTS, MODES, N_SLOTS, REL_OTHER, ByteBPE, EarConfig, OwnEar,
    hungarian_match, slot_match_cost,
)

# --------------------------------------------------------------------------
# Toy data generator (fictional names only; built inside this task)
# --------------------------------------------------------------------------

NAMES = ["Mira", "Tal", "Oren", "Ada", "Bo", "Rook", "Fig", "Moss", "Pip",
         "Oona", "Farah", "Milan", "Sari", "Dev", "Nia", "Kavi", "Lena",
         "Rafi", "Tova", "Elin", "Noor", "Idan", "Wren", "Yara"]
PETS = ["Pip", "Fig", "Moss", "Wren", "Pippa", "Soot"]
PLACES = ["Rook", "Tarn", "Breen", "Solmar", "Kestrel"]
RELS = ["mother", "sister", "boss", "dog", "cat", "friend", "brother",
        "father", "teacher", "neighbor"]


def gen_frame_items(n, seed):
    """Toy frame set: each item = (text, act, [facts]). Facts use token spans
    over the encoded turn plus special owner 0=ME. Relation ids are toy ids
    (index into RELS above), NOT the 153-class table (kept small for the CPU
    smoke; the full table is read by the audit path in the test script)."""
    rng = random.Random(seed)
    items = []
    for _ in range(n):
        kind = rng.randrange(6)
        a = rng.choice(NAMES)
        if kind == 0:      # STATE single fact, named owner
            b, r = rng.choice(NAMES), rng.choice(RELS[:3] + ["friend"])
            text = f"{a}'s {r} is {b}."
            facts = [{"o": a, "r": r, "v": b}]
            act = "STATE"
        elif kind == 1:    # STATE with ME owner
            r, b = rng.choice(RELS[3:5]), rng.choice(PETS)
            text = f"My {r} is {b}."
            facts = [{"o": "ME", "r": r, "v": b}]
            act = "STATE"
        elif kind == 2:    # ASK question
            b, r = rng.choice(NAMES), rng.choice(RELS[:2])
            text = f"Who is {b}'s {r}?"
            facts = []
            act = "ASK"
        elif kind == 3:    # CHECK (statement shape, no question mark)
            b, r = rng.choice(NAMES), rng.choice(RELS[:2])
            text = f"so {a}'s {r} is {b}"
            facts = [{"o": a, "r": r, "v": b}]
            act = "CHECK"
        elif kind == 4:    # SUPPOSE (never saved)
            b, r = rng.choice(NAMES), rng.choice(RELS[:2])
            text = f"Suppose {a}'s {r} is {b}."
            facts = [{"o": a, "r": r, "v": b}]
            act = "SUPPOSE"
        else:              # two facts, plural
            b, c = rng.sample(NAMES, 2)
            text = f"{b} and {c} are my sisters."
            facts = [{"o": "ME", "r": "sister", "v": b},
                     {"o": "ME", "r": "sister", "v": c}]
            act = "STATE"
        items.append({"text": text, "act": act, "facts": facts})
    return items


def gen_pretrain_texts(n, seed):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        a, b = rng.sample(NAMES, 2)
        r = rng.choice(RELS)
        p = rng.choice(PLACES)
        k = rng.randrange(5)
        if k == 0:
            out.append(f"{a} lives in {p} with {b}.")
        elif k == 1:
            out.append(f"{a}'s {r} is {b} and they met in {p}.")
        elif k == 2:
            out.append(f"{b} asked {a} about the {r} from {p}.")
        elif k == 3:
            out.append(f"In {p}, {a} and {b} are good friends.")
        else:
            out.append(f"{a} said the {r} belongs to {b}.")
    return out


def encode_item(tok, text, max_len):
    ids, word_ids = tok.encode(text)
    ids = ids[:max_len]
    word_ids = word_ids[:len(ids)]
    return ids, word_ids


def find_subspan(ids, word_ids, tok, phrase):
    """Token span of phrase inside an encoded turn (whole words)."""
    pids, _ = tok.encode(phrase)
    for s in range(len(ids) - len(pids) + 1):
        if ids[s:s + len(pids)] == pids:
            e = s + len(pids) - 1
            # whole-word check
            if s > 0 and word_ids[s] == word_ids[s - 1]:
                continue
            if e < len(ids) - 1 and word_ids[e] == word_ids[e + 1]:
                continue
            return s, e
    return None


def item_to_gold(tok, item, max_len, rel_index):
    ids, word_ids = encode_item(tok, item["text"], max_len)
    gold = []
    for f in item["facts"]:
        if f["o"] == "ME":
            own_special, os, oe = 0, 0, 0
        else:
            sp = find_subspan(ids, word_ids, tok, f["o"])
            if sp is None:
                continue
            own_special, os, oe = None, sp[0], sp[1]
        vsp = find_subspan(ids, word_ids, tok, f["v"])
        if vsp is None:
            continue
        csp = find_subspan(ids, word_ids, tok, f["r"])
        if csp is None:
            cs, ce = vsp  # fall back: cue = value span (always whole-word)
        else:
            cs, ce = csp
        gold.append({"rel": rel_index(f["r"]), "mode": 0,
                     "own_s": os, "own_e": oe, "own_special": own_special,
                     "val_s": vsp[0], "val_e": vsp[1],
                     "cue_s": cs, "cue_e": ce})
    return ids, word_ids, gold


# --------------------------------------------------------------------------
# Losses
# --------------------------------------------------------------------------

def frame_loss(model, out, batch_gold, act_ids, count_ids, key_mask):
    B = out["exists"].size(0)
    device = out["exists"].device
    loss = (F.cross_entropy(out["act"], act_ids.to(device))
            + F.cross_entropy(out["count"], count_ids.to(device)))
    for b in range(B):
        gold = batch_gold[b]
        G = len(gold)
        if G == 0:
            # all slots should say "not exists"
            loss = loss + F.binary_cross_entropy_with_logits(
                out["exists"][b], torch.zeros_like(out["exists"][b]))
            continue
        cost = slot_match_cost(out, gold, b)          # (6, G)
        full = torch.zeros(6, 6, dtype=cost.dtype, device=device)
        full[:, :G] = cost
        assign = hungarian_match(full.unsqueeze(0))[0]  # (6,) slot->gold/empty
        for s in range(6):
            g = int(assign[s].item())
            if g >= G:
                loss = loss + F.binary_cross_entropy_with_logits(
                    out["exists"][b, s], torch.zeros((), device=device)) / 6
                continue
            gf = gold[g]
            loss = loss + F.binary_cross_entropy_with_logits(
                out["exists"][b, s], torch.ones((), device=device)) / 6
            loss = loss + (F.cross_entropy(
                out["rel_slot"][b, s].unsqueeze(0),
                torch.tensor([gf["rel"]], device=device))
                + F.cross_entropy(out["mode"][b, s].unsqueeze(0),
                                  torch.tensor([gf["mode"]], device=device))) / 6
            for head, key in [("val_s", "val_s"), ("val_e", "val_e"),
                              ("cue_s", "cue_s"), ("cue_e", "cue_e")]:
                loss = loss + F.cross_entropy(
                    out["span"][head][b, s].unsqueeze(0),
                    torch.tensor([gf[key]], device=device)) / (6 * 4)
            ext_s = torch.cat([out["own_sp"][b, s],
                               out["span"]["own_s"][b, s]], dim=0)
            ext_e = torch.cat([out["own_sp"][b, s],
                               out["span"]["own_e"][b, s]], dim=0)
            if gf.get("own_special") is None:
                ts, te = 2 + gf["own_s"], 2 + gf["own_e"]
            else:
                ts = te = int(gf["own_special"])
            loss = loss + (F.cross_entropy(ext_s.unsqueeze(0),
                                           torch.tensor([ts], device=device))
                           + F.cross_entropy(ext_e.unsqueeze(0),
                                             torch.tensor([te], device=device))) / 12
    return loss / B


def mlm_batch(texts, tok, max_len, rng, mask_p=0.15, span=3):
    """Span masking: pick starts covering ~mask_p of tokens, mask whole spans."""
    all_ids, all_lab, all_m = [], [], []
    for t in texts:
        ids, _ = encode_item(tok, t, max_len)
        lab = [-100] * len(ids)
        m = [True] * len(ids)
        i = 0
        while i < len(ids):
            if rng.random() < mask_p:
                for k in range(span):
                    if i + k < len(ids):
                        lab[i + k] = ids[i + k]
                        ids[i + k] = 1  # MASK-ish id (byte 0x01, fixed)
                i += span
            else:
                i += 1
        all_ids.append(ids)
        all_lab.append(lab)
        all_m.append(m)
    T = max(len(x) for x in all_ids)
    V = None
    bid = torch.zeros(len(all_ids), T, dtype=torch.long)
    blab = torch.full((len(all_ids), T), -100, dtype=torch.long)
    bmask = torch.zeros(len(all_ids), T, dtype=torch.bool)
    for i, (a, l, m) in enumerate(zip(all_ids, all_lab, all_m)):
        bid[i, :len(a)] = torch.tensor(a)
        blab[i, :len(l)] = torch.tensor(l)
        bmask[i, :len(m)] = torch.tensor(m)
    return bid, blab, bmask


# --------------------------------------------------------------------------
# Checkpoints (atomic, resume from newest)
# --------------------------------------------------------------------------

def ckpt_path(workdir, step):
    return os.path.join(workdir, f"ckpt_step{step:06d}.pt")


def save_ckpt(workdir, model, opt, step, rng_state, extra):
    tmp = os.path.join(workdir, f".tmp_ckpt_{os.getpid()}_{step}.pt")
    torch.save({"step": step, "model": model.state_dict(),
                "opt": opt.state_dict(), "rng": rng_state, "extra": extra}, tmp)
    with open(tmp, "rb") as f:
        try:
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(tmp, ckpt_path(workdir, step))


def newest_ckpt(workdir):
    best, best_step = None, -1
    if not os.path.isdir(workdir):
        return None, 0
    for f in os.listdir(workdir):
        if f.startswith("ckpt_step") and f.endswith(".pt"):
            try:
                s = int(f[len("ckpt_step"):-len(".pt")])
            except ValueError:
                continue
            p = os.path.join(workdir, f)
            # ignore partially-written files (atomic rename means a visible
            # ckpt file is complete; still guard with a load check)
            try:
                torch.load(p, map_location="cpu", weights_only=False)
            except Exception:
                continue
            if s > best_step:
                best, best_step = p, s
    return best, best_step


# --------------------------------------------------------------------------
# Training loops (data order = pure function of step -> exact resume)
# --------------------------------------------------------------------------

def run_frame(cfg_args, tok, rel_index):
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)
    model = OwnEar(EarConfig(vocab_size=args.vocab, d_model=args.width,
                             n_layers=args.layers, n_heads=args.heads,
                             max_len=args.max_len))
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    items = gen_frame_items(args.items, args.seed + 1000)
    # pre-encode everything (deterministic)
    enc = [item_to_gold(tok, it, args.max_len, rel_index) for it in items]
    act_ids = [ACTS.index(it["act"]) for it in items]
    start_step = 0
    os.makedirs(args.workdir, exist_ok=True)
    ckpt, cs = newest_ckpt(args.workdir)
    if ckpt is not None:
        d = torch.load(ckpt, map_location="cpu", weights_only=False)
        model.load_state_dict(d["model"])
        opt.load_state_dict(d["opt"])
        start_step = d["step"]
        torch.set_rng_state(d["rng"]["torch"])
        np.random.set_state(d["rng"]["numpy"])
        random.setstate(d["rng"]["python"])
        print(f"resumed from {ckpt} step={start_step}", flush=True)
    use_cuda = torch.cuda.is_available()
    last_ckpt_t = time.time()
    losses = []
    model.train()
    step = start_step
    while step < args.max_steps:
        idx = [(step * args.batch + k) % len(enc) for k in range(args.batch)]
        T = max(len(enc[i][0]) for i in idx)
        bid = torch.zeros(args.batch, T, dtype=torch.long)
        bmask = torch.zeros(args.batch, T, dtype=torch.bool)
        for r, i in enumerate(idx):
            ids = enc[i][0]
            bid[r, :len(ids)] = torch.tensor(ids)
            bmask[r, :len(ids)] = True
        gold = [enc[i][2] for i in idx]
        aids = torch.tensor([act_ids[i] for i in idx])
        cids = torch.tensor([min(len(enc[i][2]), MAXC) for i in idx])
        opt.zero_grad()
        if use_cuda:
            with torch.autocast("cuda", dtype=torch.bfloat16):
                out = model(bid, bmask)
                loss = frame_loss(model, out, gold, aids, cids, bmask)
        else:
            out = model(bid, bmask)
            loss = frame_loss(model, out, gold, aids, cids, bmask)
        loss.backward()
        opt.step()
        losses.append(float(loss.item()))
        step += 1
        now = time.time()
        due_time = (now - last_ckpt_t) >= args.ckpt_minutes * 60
        due_step = args.ckpt_steps > 0 and step % args.ckpt_steps == 0
        if due_time or due_step or step >= args.max_steps:
            save_ckpt(args.workdir, model, opt, step,
                      {"torch": torch.get_rng_state(),
                       "numpy": np.random.get_state(),
                       "python": random.getstate()},
                      {"mode": "frame"})
            last_ckpt_t = now
    with open(os.path.join(args.workdir, "losses.json"), "w") as f:
        json.dump({"losses": losses, "start": start_step}, f)
    print(f"frame done steps {start_step}->{step} "
          f"loss0={np.mean(losses[:5]):.4f} loss1={np.mean(losses[-5:]):.4f}",
          flush=True)


MAXC = 6


def run_mlm(cfg_args, tok):
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)
    model = OwnEar(EarConfig(vocab_size=args.vocab, d_model=args.width,
                             n_layers=args.layers, n_heads=args.heads,
                             max_len=args.max_len))
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    texts = gen_pretrain_texts(args.items, args.seed + 2000)
    start_step = 0
    os.makedirs(args.workdir, exist_ok=True)
    ckpt, cs = newest_ckpt(args.workdir)
    if ckpt is not None:
        d = torch.load(ckpt, map_location="cpu", weights_only=False)
        model.load_state_dict(d["model"])
        opt.load_state_dict(d["opt"])
        start_step = d["step"]
        print(f"resumed from {ckpt} step={start_step}", flush=True)
    use_cuda = torch.cuda.is_available()
    last_ckpt_t = time.time()
    losses = []
    model.train()
    step = start_step
    while step < args.max_steps:
        bt = [texts[(step * args.batch + k) % len(texts)]
              for k in range(args.batch)]
        rng = random.Random(args.seed + 5000 + step)  # pure fn of step
        bid, blab, bmask = mlm_batch(bt, tok, args.max_len, rng)
        opt.zero_grad()
        if use_cuda:
            with torch.autocast("cuda", dtype=torch.bfloat16):
                enc = model.encode(bid, bmask)
                logits = enc @ model.embed.weight.T
                loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)),
                                       blab.reshape(-1), ignore_index=-100)
        else:
            enc = model.encode(bid, bmask)
            logits = enc @ model.embed.weight.T
            loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)),
                                   blab.reshape(-1), ignore_index=-100)
        loss.backward()
        opt.step()
        losses.append(float(loss.item()))
        step += 1
        now = time.time()
        due_time = (now - last_ckpt_t) >= args.ckpt_minutes * 60
        due_step = args.ckpt_steps > 0 and step % args.ckpt_steps == 0
        if due_time or due_step or step >= args.max_steps:
            save_ckpt(args.workdir, model, opt, step,
                      {"torch": torch.get_rng_state(),
                       "numpy": np.random.get_state(),
                       "python": random.getstate()},
                      {"mode": "mlm"})
            last_ckpt_t = now
    with open(os.path.join(args.workdir, "losses.json"), "w") as f:
        json.dump({"losses": losses, "start": start_step}, f)
    print(f"mlm done steps {start_step}->{step} "
          f"loss0={np.mean(losses[:5]):.4f} loss1={np.mean(losses[-5:]):.4f}",
          flush=True)


def main():
    global args
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["frame", "mlm"], required=True)
    p.add_argument("--workdir", required=True)
    p.add_argument("--tok", required=True, help="pickled ByteBPE path")
    p.add_argument("--vocab", type=int, default=512)
    p.add_argument("--width", type=int, default=64)
    p.add_argument("--layers", type=int, default=2)
    p.add_argument("--heads", type=int, default=4)
    p.add_argument("--max-len", type=int, default=48)
    p.add_argument("--items", type=int, default=400)
    p.add_argument("--batch", type=int, default=8)
    p.add_argument("--max-steps", type=int, default=100)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--ckpt-minutes", type=float, default=10)
    p.add_argument("--ckpt-steps", type=int, default=0)
    args = p.parse_args()
    import pickle
    with open(args.tok, "rb") as f:
        tok = pickle.load(f)
    rel_index = lambda r: RELS.index(r) if r in RELS else len(RELS) - 1
    if args.mode == "frame":
        run_frame(args, tok, rel_index)
    else:
        run_mlm(args, tok)


if __name__ == "__main__":
    main()
