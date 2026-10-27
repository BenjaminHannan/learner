#!/usr/bin/env python3
"""vread vector reader (vector-reader thread, 2026-09-27): the thinker reads facts through a frozen 1B's vectors.

MiniCPM5-1B (frozen, bf16, never trained) encodes the lis-319 prompt of a turn (claude_lis319_common.build_prompt_hist:
the turn, the assistant's previous reply and up to 6 earlier turns). One chosen layer's token vectors go through a small
adapter (LayerNorm 1536 + Linear 1536->512) into the thinker: rsn-358's loop net, 2 blocks at width 512, 8 heads
(scripts/claude_rsn358a_run.Block, the same weights layout; here with a key-padding mask), applied round after round
with the input re-added every round and a learned stop head. Next to the token cells sit one ME cell and K = 4 card
cells (learned vectors). After every round the heads read each card cell:
  exist (does this card hold a fact), state (current / correction / former), relation (the 153-name table),
  owner pointer (start over the prompt's tokens or the ME cell; end over tokens), value pointer (start, end over tokens).
A card's owner and value are the prompt text its pointers cover (prompt[first token start : last token end].strip()),
never new words. Card confidence = the lowest of the probabilities of its exist, state, relation and four pointer
choices (like the LoRA reader's lowest token probability). Cards come out in cell order; gold cards are assigned to
cells in the label's fact order.

Training: random rounds as rsn-358a (n_free rounds without gradient, then n_grad rounds with gradient; each graded
round is scored), fp32 with TF32 off, no autocast. Stop: the halt head predicts "every card cell is exactly right";
reading stops at the first round with p > 0.5, else at the most confident of MAX_ROUNDS.

  python -B scripts/claude_vread_model.py gradcheck --base DIR --rows TRAIN.cards.jsonl [--layer 12] [--device cpu]
  python -B scripts/claude_vread_model.py ptrcheck --base DIR --rows TRAIN.cards.jsonl [--n 50]
  python -B scripts/claude_vread_model.py layers --base DIR --train T.cards.jsonl --cal C.cards.jsonl --out DIR
  python -B scripts/claude_vread_model.py train --base DIR --train T.cards.jsonl --layer L --out DIR [--steps N]
  python -B scripts/claude_vread_model.py read --base DIR --ckpt DIR/final.pt --rows R.cards.jsonl --out READS.jsonl
  python -B scripts/claude_vread_model.py count      (trainable weights, no 1B needed)
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_rsn358a_run as R  # noqa: E402  (the thinker's block; read only)
from claude_lis300_compiler import REL_NAMES  # noqa: E402

REL = sorted(REL_NAMES)
STATE_IDS = ["current", "correction", "former"]
K = 4                      # card cells (the most cards in any kept row is 3)
D, HEADS, LAYERS = 512, 8, 2
PTRS = ("os", "oe", "vs", "ve")
MAX_SPAN = 16              # a pointer's end is at most 15 tokens after its start
MAX_FREE, MAX_GRAD, MAX_ROUNDS = 6, 3, 16
LAYER_CANDIDATES = (6, 12, 18, 24)
SEED = 327
BATCH, LR, WARM, WD = 32, 3e-4, 100, 0.01
STEPS_LAYERS, STEPS_FINAL = 800, 4000
NEG = -1e9


def load_rows(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


# ---------------- thinker ----------------
class PBlock(R.Block):
    """rsn-358a's block; the additive attention bias (relative offsets + key padding) is built outside"""
    def forward(self, x, bias):
        B, T, Dm = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.h, Dm // self.h).permute(2, 0, 3, 1, 4)
        a = F.scaled_dot_product_attention(q, k, v, attn_mask=bias)
        x = x + self.out(a.transpose(1, 2).reshape(B, T, Dm))
        return x + self.mlp(self.ln2(x))


def offsets(T, device):
    """relative (row, col) offset indices for T token cells (row 0), the ME cell (row 1) and K card cells (row 2)"""
    row = torch.cat([torch.zeros(T), torch.ones(1), torch.full((K,), 2.0)]).long().to(device)
    col = torch.cat([torch.arange(T), torch.zeros(1), torch.arange(K)]).long().to(device)
    dr = (row[:, None] - row[None, :]).clamp(-R.CLIP, R.CLIP) + R.CLIP
    same = row[:, None] == row[None, :]
    dc = torch.where(same, (col[:, None] - col[None, :]).clamp(-R.CLIP, R.CLIP) + R.CLIP,
                     torch.full_like(dr, R.CLIP))
    return dr, dc


class VReader(nn.Module):
    def __init__(self, h_in=1536):
        super().__init__()
        self.adapt = nn.Sequential(nn.LayerNorm(h_in), nn.Linear(h_in, D))
        self.me = nn.Parameter(torch.randn(D) * 0.02)
        self.cells = nn.Parameter(torch.randn(K, D) * 0.02)
        self.blocks = nn.ModuleList(PBlock(D, HEADS) for _ in range(LAYERS))
        self.ln_state, self.ln_out = nn.LayerNorm(D), nn.LayerNorm(D)
        self.exist, self.state, self.rel, self.halt = nn.Linear(D, 1), nn.Linear(D, 3), nn.Linear(D, len(REL)), \
            nn.Linear(D, 1)
        self.q = nn.ModuleDict({n: nn.Linear(D, D) for n in PTRS})
        self.k = nn.ModuleDict({n: nn.Linear(D, D) for n in PTRS})

    def prepare(self, hs, lens):
        """hs [B, T, H] float32 1B vectors (right-padded), lens [B] -> (e, biases, valid)"""
        B, T, _ = hs.shape
        dev = hs.device
        e = torch.cat([self.adapt(hs), self.me.expand(B, 1, D), self.cells.expand(B, K, D)], 1)
        valid = torch.cat([torch.arange(T, device=dev)[None, :] < lens[:, None],
                           torch.ones(B, 1 + K, dtype=torch.bool, device=dev)], 1)          # [B, N]
        pad = torch.zeros(B, 1, 1, T + 1 + K, device=dev).masked_fill(~valid[:, None, None, :], NEG)
        dr, dc = offsets(T, dev)
        biases = [(b.br[:, dr] + b.bc[:, dc]).unsqueeze(0) + pad for b in self.blocks]
        return e, biases, valid

    def step(self, h, e, biases):
        z = h + e
        for b, bias in zip(self.blocks, biases):
            z = b(z, bias)
        return self.ln_state(z)

    def read(self, h, valid):
        B, N, _ = h.shape
        T = N - 1 - K
        o = self.ln_out(h)
        tok, me, cell = o[:, :T], o[:, T:T + 1], o[:, T + 1:]
        tok_ok = valid[:, :T].clone()
        tok_ok[:, 0] = False                                            # never point at BOS
        out = {"exist": self.exist(cell).squeeze(-1), "state": self.state(cell), "rel": self.rel(cell)}
        for n in PTRS:
            keys = self.k[n](tok if n != "os" else torch.cat([tok, me], 1))
            ok = tok_ok if n != "os" else torch.cat([tok_ok, torch.ones(B, 1, dtype=torch.bool, device=h.device)], 1)
            lg = self.q[n](cell) @ keys.transpose(1, 2) / math.sqrt(D)
            out[n] = lg.masked_fill(~ok[:, None, :], NEG)                # [B, K, T] (os: T + 1, last = ME)
        w = valid.float()
        out["halt"] = self.halt((o * w[..., None]).sum(1) / w.sum(1, keepdim=True)).squeeze(-1)
        return out


def n_trainable(m):
    return sum(p.numel() for p in m.parameters() if p.requires_grad)


# ---------------- decoding ----------------
def span_end(lg_end, s):
    """best end in [s, s + MAX_SPAN) given start s (per card); returns (end, prob of end under the full softmax)"""
    T = lg_end.shape[-1]
    idx = torch.arange(T, device=lg_end.device)
    ok = (idx[None, None, :] >= s[..., None]) & (idx[None, None, :] < s[..., None] + MAX_SPAN)
    e = lg_end.masked_fill(~ok, NEG).argmax(-1)
    return e, lg_end.softmax(-1).gather(-1, e[..., None]).squeeze(-1)


def decode(out):
    """argmax decisions per card cell and the card confidence (lowest probability of its choices)"""
    T = out["vs"].shape[-1]
    p_exist = torch.sigmoid(out["exist"])
    st_p, st = out["state"].softmax(-1).max(-1)
    rl_p, rl = out["rel"].softmax(-1).max(-1)
    os_p, os_ = out["os"].softmax(-1).max(-1)
    me = os_ == T
    oe, oe_p = span_end(out["oe"], os_.clamp(max=T - 1))
    oe_p = torch.where(me, torch.ones_like(oe_p), oe_p)
    vs_p, vs = out["vs"].softmax(-1).max(-1)
    ve, ve_p = span_end(out["ve"], vs)
    exist = p_exist > 0.5
    conf = torch.stack([torch.where(exist, p_exist, 1 - p_exist), st_p, rl_p, os_p, oe_p, vs_p, ve_p], -1).min(-1).values
    return {"exist": exist, "p_exist": p_exist, "state": st, "rel": rl, "os": os_, "me": me, "oe": oe, "vs": vs,
            "ve": ve, "conf": conf}


# ---------------- data ----------------
def targets(rows, device):
    """gold tensors for a batch; owner start = -1 for ME (mapped to the ME index T by card_loss)"""
    B = len(rows)
    tg = {n: torch.full((B, K), -100, dtype=torch.long) for n in ("state", "rel", "os", "oe", "vs", "ve")}
    tg["exist"] = torch.zeros(B, K)
    for i, r in enumerate(rows):
        assert len(r["cards"]) <= K, r["id"]
        for k, c in enumerate(r["cards"]):
            tg["exist"][i, k] = 1.0
            tg["state"][i, k] = STATE_IDS.index(c["state"])
            tg["rel"][i, k] = REL.index(c["rel"])
            if c["owner_ptr"] == "ME":
                tg["os"][i, k] = -1
            else:
                tg["os"][i, k], tg["oe"][i, k] = c["owner_ptr"]["tokens"]
            tg["vs"][i, k], tg["ve"][i, k] = c["value_ptr"]["tokens"]
    return {n: v.to(device) for n, v in tg.items()}


def card_loss(out, tg):
    T = out["vs"].shape[-1]
    os_t = torch.where(tg["os"] == -1, torch.full_like(tg["os"], T), tg["os"])
    loss = F.binary_cross_entropy_with_logits(out["exist"], tg["exist"])
    for n, t in (("state", tg["state"]), ("rel", tg["rel"]), ("os", os_t), ("oe", tg["oe"]), ("vs", tg["vs"]),
                 ("ve", tg["ve"])):
        if (t != -100).any():
            loss = loss + F.cross_entropy(out[n].flatten(0, 1), t.flatten(), ignore_index=-100)
    return loss


def all_right(dec, tg):
    """per row: every card cell exactly right (exist decision; and for gold cards every field at the gold tokens)"""
    real = tg["exist"] > 0.5
    ok = dec["exist"] == real
    os_t = tg["os"]
    me_t = os_t == -1
    f_ok = (dec["state"] == tg["state"]) & (dec["rel"] == tg["rel"]) & (dec["vs"] == tg["vs"]) & (dec["ve"] == tg["ve"])
    own_ok = torch.where(me_t, dec["me"], (~dec["me"]) & (dec["os"] == os_t) & (dec["oe"] == tg["oe"]))
    ok = ok & (~real | (f_ok & own_ok))
    return ok.all(-1)


class Encoder:
    """the frozen 1B: prompt -> one layer's token vectors (bf16 on CUDA, fp32 on CPU), BOS + prompt ids as the LoRA"""
    def __init__(self, base, device, layers):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.tok = AutoTokenizer.from_pretrained(base)
        dtype = torch.bfloat16 if device == "cuda" else torch.float32
        self.model = AutoModelForCausalLM.from_pretrained(base, dtype=dtype).to(device).eval()
        for p in self.model.parameters():
            p.requires_grad_(False)
        self.device, self.layers = device, list(layers)
        self.pad = self.tok.pad_token_id if self.tok.pad_token_id is not None else self.tok.eos_token_id

    def ids(self, prompt):
        return [self.tok.bos_token_id] + self.tok(prompt, add_special_tokens=False)["input_ids"]

    @torch.no_grad()
    def __call__(self, rows):
        seqs = [self.ids(r["prompt"]) for r in rows]
        for r, s in zip(rows, seqs):
            assert len(s) == r["n_tokens"], r["id"]
        T = max(len(s) for s in seqs)
        ids = torch.full((len(seqs), T), self.pad, dtype=torch.long)
        att = torch.zeros((len(seqs), T), dtype=torch.long)
        for i, s in enumerate(seqs):
            ids[i, :len(s)] = torch.tensor(s)
            att[i, :len(s)] = 1
        body = getattr(self.model, "model", self.model)              # the decoder only: no output head is needed
        out = body(input_ids=ids.to(self.device), attention_mask=att.to(self.device), output_hidden_states=True)
        lens = torch.tensor([len(s) for s in seqs], device=self.device)
        return {L: out.hidden_states[L].float() for L in self.layers}, lens


# ---------------- train / read ----------------
def lr_at(step, total):
    return LR * min(1.0, (step + 1) / WARM) * 0.5 * (1 + math.cos(math.pi * min(1.0, step / total)))


def train_nets(enc, nets, train_rows, steps, seed, log, tag):
    """train one VReader per layer in `nets` ({layer: net}) on the same batches; fp32, TF32 off, no autocast"""
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    rng = random.Random(seed)
    opts = {L: torch.optim.AdamW(n.parameters(), lr=LR, weight_decay=WD) for L, n in nets.items()}
    t0 = time.time()
    for step in range(steps):
        batch = rng.sample(train_rows, BATCH)
        n_free, n_grad = rng.randint(0, MAX_FREE), rng.randint(1, MAX_GRAD)
        hs, lens = enc(batch)
        tg = targets(batch, enc.device)
        for L, net in nets.items():
            net.train()
            for g in opts[L].param_groups:
                g["lr"] = lr_at(step, steps)
            e, biases, valid = net.prepare(hs[L], lens)
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
                    right = all_right(decode(out), tg).float()
                loss = loss + card_loss(out, tg) + F.binary_cross_entropy_with_logits(out["halt"], right)
            loss = loss / n_grad
            opts[L].zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opts[L].step()
            if step % 100 == 0 or step == steps - 1:
                rec = {"tag": tag, "layer": L, "step": step, "loss": round(loss.item(), 4),
                       "right": round(right.mean().item(), 3), "rounds": n_free + n_grad,
                       "min": round((time.time() - t0) / 60, 2)}
                log.write(json.dumps(rec) + "\n")
                log.flush()
                print(json.dumps(rec), flush=True)


def card_text(prompt, offs, s, e):
    return prompt[offs[s - 1][0]:offs[e - 1][1]].strip()


@torch.no_grad()
def read_rows(enc, net, layer, rows, timed=True):
    """one row at a time (so the time per turn is real): 1B forward, then rounds until the stop head says p > 0.5
    (else the most confident of MAX_ROUNDS). Returns read rows {id, cards, rounds, ms}."""
    net.eval()
    outs = []
    for r in rows:
        if timed and enc.device == "cuda":
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        hs, lens = enc([r])
        e, biases, valid = net.prepare(hs[layer], lens)
        h = torch.zeros_like(e)
        best = None
        for rd in range(1, MAX_ROUNDS + 1):
            h = net.step(h, e, biases)
            out = net.read(h, valid)
            q = torch.sigmoid(out["halt"])[0].item()
            if best is None or q > best[0]:
                best = (q, rd, out)
            if q > 0.5:
                best = (q, rd, out)
                break
        dec = {k: v[0].tolist() for k, v in decode(best[2]).items()}
        if timed and enc.device == "cuda":
            torch.cuda.synchronize()
        ms = (time.perf_counter() - t0) * 1000
        offs = enc.tok(r["prompt"], add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
        cards = []
        for k in range(K):
            if not dec["exist"][k]:
                continue
            own = "me" if dec["me"][k] else card_text(r["prompt"], offs, dec["os"][k], dec["oe"][k])
            cards.append({"owner": own, "rel": REL[dec["rel"][k]],
                          "value": card_text(r["prompt"], offs, dec["vs"][k], dec["ve"][k]),
                          "state": STATE_IDS[dec["state"][k]], "conf": round(dec["conf"][k], 6),
                          "owner_tokens": None if dec["me"][k] else [dec["os"][k], dec["oe"][k]],
                          "value_tokens": [dec["vs"][k], dec["ve"][k]]})
        outs.append({"id": r["id"], "cards": cards, "rounds": best[1], "halt_p": round(best[0], 4), "ms": round(ms, 2)})
    return outs


def cal_score(reads, rows):
    """layer choice on the calibration slice: gold cards matched exactly (owner, rel, value, state; text) by emitted
    cards, minus emitted cards matching no gold card"""
    rd = {x["id"]: x for x in reads}
    right = extra = 0
    for r in rows:
        gold = [(c["owner"].lower(), c["rel"], c["value"].lower(), c["state"]) for c in r["cards"]]
        for c in rd[r["id"]]["cards"]:
            key = (c["owner"].lower(), c["rel"], c["value"].lower(), c["state"])
            if key in gold:
                gold.remove(key)
                right += 1
            else:
                extra += 1
    return {"right": right, "extra": extra, "score": right - extra}


def save(net, layer, path, extra=None):
    torch.save({"state": net.state_dict(), "layer": layer, "extra": extra or {}}, path)


def load_net(path, device):
    ck = torch.load(path, map_location=device)
    net = VReader().to(device)
    net.load_state_dict(ck["state"])
    return net, ck["layer"]


# ---------------- checks ----------------
def gradcheck(a):
    """one step, fp32, no autocast: every trainable matrix gets a nonzero gradient"""
    dev = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.manual_seed(SEED)
    rows = [r for r in load_rows(a.rows)][:64]
    enc = Encoder(a.base, dev, [a.layer])
    net = VReader().to(dev)
    assert all(p.dtype == torch.float32 for p in net.parameters())
    batch = [r for r in rows if r["cards"]][:6] + [r for r in rows if not r["cards"]][:2]
    batch += [r for r in rows if any(c["owner_ptr"] != "ME" for c in r["cards"])][:2]
    hs, lens = enc(batch)
    tg = targets(batch, dev)
    assert torch.is_autocast_enabled() is False
    e, biases, valid = net.prepare(hs[a.layer], lens)
    h = torch.zeros_like(e)
    loss = 0.0
    for _ in range(2):
        h = net.step(h, e, biases)
        out = net.read(h, valid)
        right = all_right(decode(out), tg).float()
        loss = loss + card_loss(out, tg) + F.binary_cross_entropy_with_logits(out["halt"], right)
    loss.backward()
    names = [(n, p) for n, p in net.named_parameters() if p.requires_grad]
    zero = [n for n, p in names if p.grad is None or p.grad.abs().sum().item() == 0]
    base_grads = sum(1 for p in enc.model.parameters() if p.grad is not None)
    res = {"gradcheck": "OK" if not zero else "FAIL", "trainable_tensors": len(names),
           "zero_or_none_grad": zero, "trainable_weights": n_trainable(net),
           "frozen_1b_params_with_grad": base_grads, "dtype": "float32", "autocast": False, "device": dev,
           "torch": torch.__version__, "loss": round(loss.item(), 4)}
    print(json.dumps(res))
    assert not zero and base_grads == 0
    return res


def ptrcheck(a):
    """on the first --n train rows with cards: the gold token spans rebuild the gold card exactly"""
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.base)
    rows = [r for r in load_rows(a.rows) if r["cards"]][:a.n]
    bad = 0
    for r in rows:
        ids = [tok.bos_token_id] + tok(r["prompt"], add_special_tokens=False)["input_ids"]
        assert len(ids) == r["n_tokens"]
        offs = tok(r["prompt"], add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
        for c in r["cards"]:
            own = "me" if c["owner_ptr"] == "ME" else card_text(r["prompt"], offs, *c["owner_ptr"]["tokens"])
            val = card_text(r["prompt"], offs, *c["value_ptr"]["tokens"])
            rebuilt = (own, REL[REL.index(c["rel"])], val, STATE_IDS[STATE_IDS.index(c["state"])])
            bad += rebuilt != (c["owner"], c["rel"], c["value"], c["state"])
    res = {"ptrcheck": "OK" if not bad else "FAIL", "rows": len(rows),
           "cards": sum(len(r["cards"]) for r in rows), "cards_not_rebuilt": bad}
    print(json.dumps(res))
    assert not bad
    return res


# ---------------- commands ----------------
def cmd_layers(a):
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    train, cal = load_rows(a.train), load_rows(a.cal)
    enc = Encoder(a.base, dev, LAYER_CANDIDATES)
    res = {}
    with open(out / "layers_log.jsonl", "w") as log:
        for L in LAYER_CANDIDATES:           # one layer at a time, the same batches and seed for each
            enc.layers = [L]
            torch.manual_seed(SEED)
            net = VReader().to(dev)
            train_nets(enc, {L: net}, train, a.steps or STEPS_LAYERS, SEED, log, "layers")
            reads = read_rows(enc, net, L, cal, timed=False)
            res[L] = cal_score(reads, cal)
            print(json.dumps({"layer": L, **res[L]}), flush=True)
    best = max(LAYER_CANDIDATES, key=lambda L: (res[L]["score"], -L))
    (out / "layers.json").write_text(json.dumps({"by_layer": res, "chosen": best, "steps": a.steps or STEPS_LAYERS,
                                                 "rule": "max(right - extra) on the calibration slice; tie -> "
                                                         "lower layer"}, indent=1))
    print(json.dumps({"chosen_layer": best}))


def cmd_train(a):
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    train = load_rows(a.train)
    enc = Encoder(a.base, dev, [a.layer])
    torch.manual_seed(SEED)
    net = VReader().to(dev)
    t0 = time.time()
    with open(out / "train_log.jsonl", "w") as log:
        train_nets(enc, {a.layer: net}, train, a.steps or STEPS_FINAL, SEED + 1, log, "final")
    save(net, a.layer, out / "final.pt")
    summ = {"layer": a.layer, "steps": a.steps or STEPS_FINAL, "train_rows": len(train), "batch": BATCH, "lr": LR,
            "trainable_weights": n_trainable(net), "minutes": round((time.time() - t0) / 60, 2),
            "torch": torch.__version__, "device": dev,
            "gpu": torch.cuda.get_device_name(0) if dev == "cuda" else None}
    (out / "summary.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ))


def cmd_read(a):
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    net, layer = load_net(a.ckpt, dev)
    enc = Encoder(a.base, dev, [layer])
    rows = load_rows(a.rows)[: a.limit] if a.limit else load_rows(a.rows)
    reads = read_rows(enc, net, layer, rows)
    Path(a.out).write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in reads), encoding="utf-8")
    ms = sorted(x["ms"] for x in reads)
    print(json.dumps({"read": len(reads), "layer": layer, "ms_median": ms[len(ms) // 2],
                      "rounds_mean": round(sum(x["rounds"] for x in reads) / len(reads), 3)}))


def cmd_count(a):
    net = VReader()
    parts = {"adapter": sum(p.numel() for p in net.adapt.parameters()),
             "thinker (2 blocks + ME/card cells + state norm)": sum(p.numel() for p in net.blocks.parameters())
             + net.me.numel() + net.cells.numel() + sum(p.numel() for p in net.ln_state.parameters()),
             "heads (out norm, exist, state, relation, stop, 4 pointers)":
                 sum(p.numel() for m in (net.ln_out, net.exist, net.state, net.rel, net.halt, net.q, net.k)
                     for p in m.parameters())}
    parts["total"] = n_trainable(net)
    assert parts["total"] == sum(v for k, v in parts.items() if k != "total")
    print(json.dumps(parts, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gradcheck", "ptrcheck", "layers", "train", "read", "count"])
    ap.add_argument("--base")
    ap.add_argument("--rows")
    ap.add_argument("--train")
    ap.add_argument("--cal")
    ap.add_argument("--layer", type=int, default=12)
    ap.add_argument("--steps", type=int, default=None)
    ap.add_argument("--ckpt")
    ap.add_argument("--out")
    ap.add_argument("--device")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--batch", type=int, default=None, help="smoke tests only")
    a = ap.parse_args()
    if a.batch:
        global BATCH
        BATCH = a.batch
    {"gradcheck": gradcheck, "ptrcheck": ptrcheck, "layers": cmd_layers, "train": cmd_train, "read": cmd_read,
     "count": cmd_count}[a.cmd](a)


if __name__ == "__main__":
    main()
