#!/usr/bin/env python3
"""rsn-358k DRAFT (sleep research thread, 2026-09-27): can the 358 loop reasoner learn to call a read-only card store
while it thinks? Plan and marks: artifacts/claude-rsn358k-20260927/PASSMARKS-draft.md (not sealed; steps TBD).

Ben (Thread manager thread, 12:40-12:45 UTC): "was there a temporary card store that acts as a short term memory?",
"should we?", "but for the reasoner to do work with it. It can call the cards".

Task (code-made, a fresh random world per item, no kind label: every item gets env 0, as in rsn-358u). A world has
12 names (of 40 name tokens) and 4 places (of 8 place tokens) and 16 cards, each one row of 5 tokens:
    name place =  d  d            (a two-digit value)
    name place -> name' place'    (a pointer to another card)
Two names sit on 3 cards each (at 3 different places) and are the only ones ever asked; the other 10 names sit on one
card each, at least 2 per place. So every asked (name, place) has 2 cards with the same name and another place and
>= 2 with the same place and another name: a reader that matches one field is right at most 1 time in 3.
Decoys share type (fix B, the coordinator 2026-09-27, before any run): both same-name cards of a chain card and every
card at its place (except a card of another chain name, whose own type rule wins) have that chain card's type (value
or pointer), so "name + card type" is no better than name alone. To make that possible, chain cards of different types
never share a name or a place: in q2 the pointer and its target have different names and places, and in q2c3 the two
pointers share a name and the value card has the other name and neither pointer's place.
The puzzle grid shows only the question (row 0) and 3 answer slots (row 1, cols 2-4, answer written as 3 digits):
    q1    name place ?               the asked card's value ("0 d d")
    q2    name place ?               the asked card is a pointer; the answer is the value on the card it points to
    q3    n1 p1 + n2 p2              the sum of two values (report only, never practised)
    q2c3  name place ?               a three-card pointer chain (report only, never practised)
Practice is q1 and q2 in equal shares inside every batch. The tests are 300 items per kind from sealed string seeds
("rsn358k-test-<kind>") that training never draws; world-hashes.txt holds one sha256 per test world (its 16 sorted
card rows) and the trainer reports how many practice worlds hit that set (expected 0).

The net: rsn-358u's sealed code path (imported and patched, never copied): scripts/claude_rsn358a_run.py's grid net
with rsn-358i's half-narrow attention, rsn-358i2's autocast cache off and gradient logging, rsn-358a2's v2 stop rule,
fixed env 0, at the small rsn-358e size (2 layers x d256, 8 heads; batch 64, lr 1e-3, 100 warm-up steps, cosine) and
358a's loop schedule (1-16 rounds, gradient through the last 1-6, 48 test rounds). Its own 65-token vocabulary.
Store parts (present in EVERY arm, so all arms have exactly the same weights):
    card encoder  the net's own token embedding + a learned card-column embedding + LayerNorm; 4 attention-pool heads
                  (one learned score per head per token, softmax over the card's 5 tokens), each pooled vector
                  projected to 16 dims, concatenated into a 64-d key; a value projection d -> d per token.
    query         LayerNorm of the mean loop state + input embedding over all cells -> 64-d.
    NULL card     a card of 5 NULL tokens through the same encoder (no extra weights), always callable.
Each round r: query from (state after round r-1 + input embedding); score the 16 cards + NULL (dot / 8); softmax over
all callable cards; keep the 4 highest (sorted); each read row = its softmax weight x the card's value row. The 4 read
rows fill 4 blank grid rows (rows 2-5) that round r's layers attend to; round r+1 replaces them with its own call.
So round 1 makes one call from the question alone, and a pointer's target can only be fetched from round 2 on.
Answer loss (+ 358's stop-head loss) only: no retrieval labels, no hand-written key or address rule.

Arms (the ONE change graded, store vs nostore: whether the store can be called)
    store    calls reach the 16 cards and NULL.
    nostore  identical net and weights; the 16 cards are replaced by NULL rows and masked out, so every call returns
             the NULL card (weight 1) and 3 zero rows.
    pasted   (report only) no calls; the 16 cards are pasted into the grid as rows 2-17 (the same card rows). The store
             parts stay in the net unused, so its weight count is the same; train_summary.json gives the active count.

  python -B scripts/claude_rsn358k_run.py make-tests --out artifacts/claude-rsn358k-20260927/tests
  python -B scripts/claude_rsn358k_run.py train --arm store|nostore|pasted --seed S --out DIR [--steps N] [--dev]
  python -B scripts/claude_rsn358k_run.py eval --ckpt DIR/final.pt --tests DIR --out F
  python -B scripts/claude_rsn358k_run.py selftest
Training seeds are 17-20 (5-16 belong to 358i3, 358s and 358u and are refused). --dev draws practice worlds from a
separate dev stream ("rsn358k-dev-<seed>") for the step-count pilot. eval writes counts and means only, never items.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358u_run as U  # noqa: E402  (358i2 + fixed env; brings 358i attention and cache-off autocast)
import claude_rsn358a2_run as V  # noqa: E402  (v2 stop rule)

R, I2 = U.R, U.I2

# ---------------- vocabulary and grid ----------------
BLANK, MASK = 0, 1
DIG = 2                                   # digits 0-9 -> 2..11
EQ, PTR, ASK, PLUS, NULLT = 12, 13, 14, 15, 16
NAMES = list(range(17, 57))               # 40 name tokens
PLACES = list(range(57, 65))              # 8 place tokens
VOCAB = 65
W = 5                                     # every row (question, answer, card) is 5 tokens wide
N_CARDS, NULL_IDX = 16, 16                # candidates = 16 cards + NULL (index 16)
N_READ = 4
KEY_HEADS, KEY_DIM = 4, 64                # 4 pool heads x 16 dims = one 64-d key per card
FIXED_ROWS = 2                            # question row + answer row
ANS = [W + 2, W + 3, W + 4]               # flat cells of the 3 answer slots (row 1, cols 2-4)
SIZE = dict(d=256, layers=2, heads=8)     # rsn-358e "small"
ARMS = ["store", "nostore", "pasted"]
KINDS = ["q1", "q2", "q3", "q2c3"]
PRACTICE_KINDS = ["q1", "q2"]
CHAIN_LEN = {"q1": 1, "q2": 2, "q3": 2, "q2c3": 3}
P_POINTER = 1 / 3                         # share of the other cards that are pointers (to any other card)
N_TEST = 300
READ_ROUNDS = 8                           # rounds whose calls eval scores (plus the call at the own-stop round)
DEFAULT_TESTS = "artifacts/claude-rsn358k-20260927/tests"


# ---------------- worlds ----------------
def make_world(rng):
    """16 unique (name, place) cards: 2 names x 3 places (askable) + 10 single names, >= 2 singles per place"""
    names, places = rng.sample(NAMES, 12), rng.sample(PLACES, 4)
    pairs = [(n, p) for n in names[:2] for p in rng.sample(places, 3)]
    spots = places * 2 + rng.sample(places, 2)
    rng.shuffle(spots)
    pairs += list(zip(names[2:], spots))
    rng.shuffle(pairs)
    askable = [i for i, (n, _) in enumerate(pairs) if n in names[:2]]
    return pairs, askable


def pick_chain(rng, pairs, askable, kind):
    """chain cards (asked card first) and their types (True = pointer); cards of different types share no field"""
    types = [True] * (CHAIN_LEN[kind] - 1) + [False] if kind in ("q2", "q2c3") else [False] * CHAIN_LEN[kind]
    while True:
        chain = rng.sample(askable, len(types))
        if all(pairs[a][0] != pairs[b][0] and pairs[a][1] != pairs[b][1]
               for a, ta in zip(chain, types) for b, tb in zip(chain, types) if ta != tb):
            return chain, types


def make_item(rng, kind):
    pairs, askable = make_world(rng)
    chain, types = pick_chain(rng, pairs, askable, kind)
    is_ptr = [None] * N_CARDS
    for c, t in zip(chain, types):                        # same-name cards take the chain card's type
        for i, (n, _) in enumerate(pairs):
            if n == pairs[c][0]:
                is_ptr[i] = t
    for c, t in zip(chain, types):                        # then every other card at its place
        for i, (_, p) in enumerate(pairs):
            if p == pairs[c][1] and is_ptr[i] is None:
                is_ptr[i] = t
    is_ptr = [rng.random() < P_POINTER if t is None else t for t in is_ptr]
    value = [rng.randrange(100) for _ in range(N_CARDS)]
    point = [rng.choice([j for j in range(N_CARDS) if j != i]) if is_ptr[i] else None for i in range(N_CARDS)]
    for a, b in zip(chain, chain[1:]):
        if is_ptr[a]:
            point[a] = b
    cards = [[n, p, PTR, *pairs[point[i]]] if point[i] is not None else [n, p, EQ, DIG + value[i] // 10, DIG + value[i] % 10]
             for i, (n, p) in enumerate(pairs)]
    a = chain[0]
    if kind == "q3":
        question, answer = [*pairs[a], PLUS, *pairs[chain[1]]], value[a] + value[chain[1]]
    else:
        question, answer = [*pairs[a], ASK, BLANK, BLANK], value[chain[-1]]
    target = [DIG + answer // 100, DIG + answer // 10 % 10, DIG + answer % 10]
    return {"kind": kind, "q": question, "cards": cards, "target": target, "chain": chain}


def world_hash(cards):
    return hashlib.sha256(json.dumps(sorted(cards)).encode()).hexdigest()


class Source:
    """the practice stream: half q1, half q2 in every batch; the same for every arm at the same seed and --dev flag"""

    def __init__(self, seed, dev=False):
        self.rng = random.Random(f"rsn358k-{'dev' if dev else 'practice'}-{seed}")

    def batch(self, B):
        kinds = PRACTICE_KINDS * (B // 2) + PRACTICE_KINDS[:B % 2]
        self.rng.shuffle(kinds)
        return [make_item(self.rng, k) for k in kinds]


def make_test(kind, n=N_TEST):
    rng = random.Random(f"rsn358k-test-{kind}")
    return [make_item(rng, kind) for _ in range(n)]


def dev_sets(n=100):
    rng = random.Random("rsn358k-devcheck")
    return {k: [make_item(rng, k) for _ in range(n)] for k in PRACTICE_KINDS}


def tensors(items, mode, device):
    """grid tokens/slot/target [B, H, W] (H = 2 + 4 blank read rows, or 2 + 16 card rows when pasted),
    call candidates [B, 17, W] and their callable mask [B, 17] (None when pasted)"""
    B = len(items)
    rows = [[it["q"], [BLANK, BLANK, MASK, MASK, MASK]] + (it["cards"] if mode == "pasted" else [[BLANK] * W] * N_READ)
            for it in items]
    t = torch.tensor(rows, device=device)
    s = torch.zeros_like(t)
    s[:, 1, 2:] = 1
    y = torch.zeros_like(t)
    y[:, 1, 2:] = torch.tensor([it["target"] for it in items], device=device)
    if mode == "pasted":
        return t, s, y, None, None
    null = [[NULLT] * W]
    cards = torch.tensor([(it["cards"] if mode == "store" else null * N_CARDS) + null for it in items], device=device)
    mask = torch.ones(B, N_CARDS + 1, dtype=torch.bool, device=device)
    if mode == "nostore":
        mask[:, :N_CARDS] = False
    return t, s, y, cards, mask


# ---------------- model ----------------
class StoreNet(R.Net):
    """358's grid loop net (small size, fixed env) + the store parts; `mode` picks the arm's data path only"""

    def __init__(self, mode):
        R.ARMS["k358"] = dict(SIZE)
        super().__init__("k358")                     # 358i blocks; 358i2 grad logging hooks this net
        d = SIZE["d"]
        self.arm, self.mode = "loop", mode           # R.Net.read() gives the stop head to arm "loop"
        self.tok, self.head = nn.Embedding(VOCAB, d), nn.Linear(d, VOCAB)
        self.ln_state, self.halt = nn.LayerNorm(d), nn.Linear(d, 1)
        # store parts (every arm)
        self.card_col = nn.Parameter(0.02 * torch.randn(W, d))
        self.card_ln = nn.LayerNorm(d)
        self.pool = nn.Linear(d, KEY_HEADS)
        self.key = nn.Parameter(torch.randn(KEY_HEADS, d, KEY_DIM // KEY_HEADS) / d ** 0.5)
        self.value = nn.Linear(d, d)
        self.q_ln = nn.LayerNorm(d)
        self.query = nn.Linear(d, KEY_DIM)

    def store_parameters(self):
        return [p for n, p in self.named_parameters() if n.split(".")[0] in STORE_PARTS]

    def encode_cards(self, cards):
        """cards [B, N, W] -> keys [B, N, 64], value rows [B, N, W, d], pool weights [B, N, heads, W]"""
        x = self.card_ln(self.tok(cards) + self.card_col)
        a = F.softmax(self.pool(x).float(), dim=2).to(x.dtype)                  # over the card's tokens
        pooled = torch.einsum("bnwh,bnwd->bnhd", a, x)
        keys = torch.einsum("bnhd,hdk->bnhk", pooled, self.key.to(x.dtype)).flatten(2)
        return keys, self.value(x), a.transpose(2, 3)

    def call(self, z, keys, values, mask):
        """one call: soft top-4 read -> read rows [B, 4*W, d], weights over candidates [B, N], top indices [B, 4]"""
        q = self.query(self.q_ln(z.mean(1)))
        score = torch.einsum("bk,bnk->bn", q.float(), keys.float()) / KEY_DIM ** 0.5
        score = score.masked_fill(~mask, float("-inf"))
        p = F.softmax(score, -1)
        top = score.topk(N_READ, -1).indices                                    # sorted, highest first
        w = p.gather(1, top).to(values.dtype)                                   # 0 for a masked candidate
        rows = w[:, :, None, None] * values.gather(1, top[:, :, None, None].expand(-1, -1, W, values.shape[-1]))
        return rows.flatten(1, 2), p, top.masked_fill(~mask.gather(1, top), -1)  # -1 = empty read slot

    def prepare(self, tokens, slot, cards):
        env = torch.full((tokens.shape[0],), U.FIXED_ENV, device=tokens.device)
        e, (dr, dc) = self.embed(tokens, slot, env)
        kv = None if self.mode == "pasted" else self.encode_cards(cards)[:2]
        return e, dr, dc, kv

    def one_round(self, h, e, dr, dc, kv, mask):
        info = None
        if kv is not None:
            rows, p, top = self.call(h + e, *kv, mask)
            n = FIXED_ROWS * W
            e = torch.cat([e[:, :n], e[:, n:] + rows], 1)
            info = (p, top)
        return self.step(h, e, dr, dc), info

    def loop_train(self, tokens, slot, cards, mask, n_free, n_grad):
        e, dr, dc, kv = self.prepare(tokens, slot, cards)
        h = torch.zeros_like(e)
        with torch.no_grad():
            for _ in range(n_free):
                h, _ = self.one_round(h, e, dr, dc, kv, mask)
        h = h.detach()
        outs = []
        for _ in range(n_grad):
            h, _ = self.one_round(h, e, dr, dc, kv, mask)
            outs.append(self.read(h))
        return outs

    @torch.no_grad()
    def loop_rounds(self, tokens, slot, cards, mask, n):
        """answer-slot predictions [B, n, 3], stop probabilities [B, n], call top-4 [B, n, 4] (None when pasted)"""
        e, dr, dc, kv = self.prepare(tokens, slot, cards)
        h = torch.zeros_like(e)
        preds, qs, tops = [], [], []
        for _ in range(n):
            h, info = self.one_round(h, e, dr, dc, kv, mask)
            lg, q = self.read(h)
            preds.append(lg.argmax(-1)[:, ANS])
            qs.append(torch.sigmoid(q.float()))
            if info is not None:
                tops.append(info[1])
        return torch.stack(preds, 1), torch.stack(qs, 1), (torch.stack(tops, 1) if tops else None)


STORE_PARTS = ("card_col", "card_ln", "pool", "key", "value", "q_ln", "query")


def count(net):
    return sum(p.numel() for p in net.parameters())


def weight_counts():
    nets = {arm: StoreNet(arm) for arm in ARMS}
    store = sum(p.numel() for p in nets["store"].store_parameters())
    return {"by_arm": {arm: count(n) for arm, n in nets.items()}, "store_parts": store,
            "pasted_active": count(nets["pasted"]) - store}


# ---------------- tests ----------------
def make_tests(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    hashes = []
    for kind in KINDS:
        items = make_test(kind)
        (out / f"{kind}.jsonl").write_text("".join(json.dumps(it) + "\n" for it in items), encoding="utf-8")
        hashes += [world_hash(it["cards"]) for it in items]
        print(f"{kind}: {len(items)} items")
    (out / "world-hashes.txt").write_text("".join(h + "\n" for h in hashes), encoding="utf-8")
    print(f"world-hashes.txt: {len(hashes)} hashes, {len(set(hashes))} distinct")


def load_tests(d, limit=None):
    return {k: [json.loads(l) for l in (Path(d) / f"{k}.jsonl").read_text().splitlines()[:limit]] for k in KINDS}


def load_test_hashes(d):
    f = Path(d) / "world-hashes.txt"
    return set(f.read_text().split()) if f.exists() else None


def card_role(it, idx):
    """which card a call read, relative to the item's answer chain (A = asked card, then B, C along the chain)"""
    if idx == NULL_IDX:
        return "null"
    chain = it["chain"]
    if idx in chain:
        return "ABC"[chain.index(idx)]
    card = it["cards"][idx]
    if card[0] in {it["cards"][c][0] for c in chain}:
        return "same_name"
    if card[1] in {it["cards"][c][1] for c in chain}:
        return "same_place"
    return "other"


ROLES = ["A", "B", "C", "null", "same_name", "same_place", "other"]


@torch.no_grad()
def evaluate(net, items, device, bs=100):
    net.eval()
    n = R.TEST_ROUNDS
    fixed = [0] * n
    right, rounds, oracle = 0, [], 0
    calls = net.mode != "pasted"
    chain_len = max(len(it["chain"]) for it in items)
    labels = [str(r) for r in range(1, READ_ROUNDS + 1)] + ["stop"]
    top1 = {l: {k: 0 for k in ROLES} for l in labels}
    in_top4 = {l: {"ABC"[j]: 0 for j in range(chain_len)} for l in labels}
    for i in range(0, len(items), bs):
        chunk = items[i:i + bs]
        t, s, _, cards, mask = tensors(chunk, net.mode, device)
        preds, qs, tops = net.loop_rounds(t, s, cards, mask, n)
        preds, qs = preds.tolist(), qs.tolist()
        tops = tops.tolist() if calls else None
        for j, (it, p, q) in enumerate(zip(chunk, preds, qs)):
            stop = V.stop_round(p, q, n)
            rounds.append(stop + 1)
            right += p[stop] == it["target"]
            for r in range(n):
                fixed[r] += p[r] == it["target"]
            oracle += any(p[r] == it["target"] for r in range(n))
            if calls:
                for l, r in zip(labels, list(range(READ_ROUNDS)) + [stop]):
                    top1[l][card_role(it, tops[j][r][0])] += 1
                    for k, c in enumerate(it["chain"]):
                        in_top4[l]["ABC"[k]] += c in tops[j][r]
    res = {"n": len(items), "right": right, "mean_rounds": round(sum(rounds) / len(rounds), 2),
           "rounds_hist": {str(k): rounds.count(k) for k in sorted(set(rounds))},
           "fixed_rounds": {str(r + 1): v for r, v in enumerate(fixed)}, "right_at_any_round": oracle}
    if calls:
        res["call_top1_by_round"] = top1
        res["call_in_top4_by_round"] = in_top4
    return res


@torch.no_grad()
def key_head_attention(net, items, device, bs=100):
    """per key head: mean pool weight on the name token (col 0), the place token (col 1) and the other 3 tokens,
    over every card of these items (the 09-18 collapse measure)"""
    net.eval()
    tot, n = torch.zeros(KEY_HEADS, W), 0
    for i in range(0, len(items), bs):
        cards = torch.tensor([it["cards"] for it in items[i:i + bs]], device=device)
        a = net.encode_cards(cards)[2].float()                                   # [B, 16, heads, W]
        tot += a.sum((0, 1)).cpu()
        n += a.shape[0] * a.shape[1]
    m = tot / n
    return [{"head": h, "name": round(float(m[h, 0]), 4), "place": round(float(m[h, 1]), 4),
             "other": round(float(m[h, 2:].sum()), 4)} for h in range(KEY_HEADS)]


# ---------------- training ----------------
def store_grad_norms(net):
    return {part: round(math.sqrt(sum(float(p.grad.detach().float().norm()) ** 2 for n, p in net.named_parameters()
                                      if n.split(".")[0] == part and p.grad is not None)), 6) for part in STORE_PARTS}


def train(a):
    assert not 5 <= a.seed <= 16, "seeds 5-16 belong to 358i3, 358s and 358u"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        torch.set_num_threads(a.threads)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    counts = weight_counts()
    test_hashes = load_test_hashes(a.tests)
    torch.manual_seed(a.seed)
    net = StoreNet(a.arm).to(device)
    I2._STATS.update(net=net, steps=0, steps_block_nograd=0, grad_norms=[])
    src, dev = Source(a.seed, a.dev), dev_sets()
    round_rng = random.Random(f"rsn358k-rounds-{a.seed}")
    opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=0.1, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / a.warmup) * 0.5 *
                                              (1 + math.cos(math.pi * min(i, a.steps) / a.steps)))
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if device == "cuda" else torch.autocast("cpu", enabled=False)
    log = open(out / "train_log.jsonl", "w", encoding="utf-8")
    seen, overlap = 0, 0
    run = {"ce": 0.0, "halt": 0.0, "n": 0, "q1": [0.0, 0], "q2": [0.0, 0]}
    print(f"{a.arm} seed {a.seed}{' dev' if a.dev else ''}: {count(net)} weights on {device}, torch {torch.__version__}",
          flush=True)
    t_train, t_dev = time.time(), 0.0
    for step in range(1, a.steps + 1):
        net.train()
        items = src.batch(a.batch)
        seen += len(items)
        if test_hashes is not None:
            overlap += sum(world_hash(it["cards"]) in test_hashes for it in items)
        t, s, y, cards, mask = tensors(items, a.arm, device)
        total = round_rng.randint(1, R.TRAIN_ROUNDS)
        k = round_rng.randint(1, min(total, R.GRAD_ROUNDS))
        with amp:
            ces, hls = [], []
            for lg, q in net.loop_train(t, s, cards, mask, total - k, k):
                c_, ex = R.ce_and_exact(lg, s, y)
                ces.append(c_)
                hls.append(F.binary_cross_entropy_with_logits(q.float(), ex))
            ce, hl = torch.stack(ces).mean(), torch.stack(hls).mean()
            loss = ce + 0.5 * hl
        opt.zero_grad(set_to_none=True)
        loss.backward()
        logging = step % a.log_every == 0 or step == a.steps
        norms = store_grad_norms(net) if logging else None
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)                  # 358i2's checked clip
        opt.step()
        sched.step()
        run["ce"] += ce.item(); run["halt"] += hl.item(); run["n"] += 1
        for it, e_ in zip(items, ex.tolist()):                                 # exact at the last graded round
            run[it["kind"]][0] += e_; run[it["kind"]][1] += 1
        if logging:
            rec = {"step": step, "ce": round(run["ce"] / run["n"], 4), "halt_bce": round(run["halt"] / run["n"], 4),
                   "exact_by_kind": {kd: round(run[kd][0] / max(1, run[kd][1]), 3) for kd in PRACTICE_KINDS},
                   "lr": sched.get_last_lr()[0], "min": round((time.time() - t0) / 60, 2), "store_grad_norms": norms}
            if step % (a.log_every * 5) == 0 or step == a.steps:
                t1 = time.time()
                rec["dev"] = {kd: evaluate(net, v, device)["right"] for kd, v in dev.items()}
                t_dev += time.time() - t1
            log.write(json.dumps(rec) + "\n"); log.flush()
            print(json.dumps(rec), flush=True)
            run = {"ce": 0.0, "halt": 0.0, "n": 0, "q1": [0.0, 0], "q2": [0.0, 0]}
    train_sec = time.time() - t_train - t_dev                               # training steps only, no dev checks
    torch.save({"mode": a.arm, "seed": a.seed, "dev": a.dev, "state": net.state_dict()}, out / "final.pt")
    json.dump({"arm": a.arm, "seed": a.seed, "dev_stream": a.dev, "weights": count(net), "weights_by_arm": counts["by_arm"],
               "store_part_weights": counts["store_parts"], "pasted_active_weights": counts["pasted_active"],
               "steps": a.steps, "batch": a.batch, "lr": a.lr, "warmup": a.warmup, "threads": a.threads,
               "minutes": round((time.time() - t0) / 60, 2), "sec_per_100_steps": round(100 * train_sec / a.steps, 2),
               "device": device, "torch": torch.__version__, "python": platform.python_version(),
               "practice_worlds": seen, "test_hashes_file": str(Path(a.tests) / "world-hashes.txt"),
               "practice_test_hash_overlap": overlap if test_hashes is not None else None,
               "steps_seen": I2._STATS["steps"], "steps_block_nograd": I2._STATS["steps_block_nograd"],
               "grad_norms": I2._STATS["grad_norms"]}, open(out / "train_summary.json", "w"), indent=1)


def load(ckpt, device):
    d = torch.load(ckpt, map_location=device)
    net = StoreNet(d["mode"]).to(device)
    net.load_state_dict(d["state"])
    return net


def run_eval(a):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    net = load(a.ckpt, device)
    tests = load_tests(a.tests, a.limit)
    res = {"arm": net.mode, "ckpt": str(a.ckpt), "tests": {}}
    for kind in KINDS:
        r = evaluate(net, tests[kind], device)
        r["role"] = "practised" if kind in PRACTICE_KINDS else "report"
        res["tests"][kind] = r
        print(kind, json.dumps({k: r[k] for k in ("n", "right", "mean_rounds", "right_at_any_round")}), flush=True)
    res["key_head_attention"] = key_head_attention(net, [it for k in KINDS for it in tests[k]], device)
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")


# ---------------- selftest ----------------
def selftest():
    # 1. worlds: decoys, unique keys, answers, nothing of the answer in the question
    rng = random.Random("rsn358k-selftest")
    for kind in KINDS:
        for _ in range(2000):
            it = make_item(rng, kind)
            cards = it["cards"]
            keys = [tuple(c[:2]) for c in cards]
            assert len(set(keys)) == N_CARDS and len({c[0] for c in cards}) == 12 and len({c[1] for c in cards}) == 4
            assert not any(DIG <= x < DIG + 10 for x in it["q"])                  # no digit in the question row
            for c in it["chain"]:
                n, p = keys[c]
                assert sum(k[0] == n and k[1] != p for k in keys) >= 2, "same-name decoys"
                assert sum(k[1] == p and k[0] != n for k in keys) >= 2, "same-place decoys"
                typ = cards[c][2]
                assert all(d[2] == typ for d in cards if d[0] == n), "same-name decoys share the type"
                assert sum(d[1] == p and d[0] != n and d[2] == typ for d in cards) >= 2, "same-place decoys share the type"
                chain_names = {cards[x][0] for x in it["chain"]}
                assert all(d[2] == typ for d in cards if d[1] == p and d[0] not in chain_names - {n}), "place type"
            look = {k: c for k, c in zip(keys, cards)}

            def follow(n, p):
                c = look[(n, p)]
                while c[2] == PTR:
                    c = look[(c[3], c[4])]
                return (c[3] - DIG) * 10 + c[4] - DIG

            if kind == "q3":
                ans = follow(*it["q"][:2]) + follow(*it["q"][3:5])
                assert all(look[tuple(it["q"][i:i + 2])][2] == EQ for i in (0, 3))
            else:
                ans = follow(*it["q"][:2])
                hops, c = 1, look[tuple(it["q"][:2])]
                while c[2] == PTR:
                    hops, c = hops + 1, look[(c[3], c[4])]
                assert hops == CHAIN_LEN[kind], (kind, hops)
            assert [DIG + ans // 100, DIG + ans // 10 % 10, DIG + ans % 10] == it["target"]
    # 2. test and practice streams do not share worlds (a sample; the trainer counts the full overlap)
    test_h = {world_hash(it["cards"]) for k in KINDS for it in make_test(k)}
    prac = Source(17).batch(2000) + Source(17, dev=True).batch(2000)
    assert len(test_h) == N_TEST * len(KINDS) and not any(world_hash(it["cards"]) in test_h for it in prac)
    # 3. equal weights
    counts = weight_counts()
    assert len(set(counts["by_arm"].values())) == 1, counts
    # 4. nostore reads only NULL and never sees the cards; store and pasted do see them
    torch.manual_seed(0)
    items = [make_item(rng, k) for k in ("q1", "q2") * 4]
    swapped = [dict(it, cards=items[(i + 1) % len(items)]["cards"]) for i, it in enumerate(items)]
    def run(net, batch, n=3):
        t, s, _, cards, mask = tensors(batch, net.mode, "cpu")
        e, dr, dc, kv = net.prepare(t, s, cards)
        h, info = torch.zeros_like(e), None
        for _ in range(n):
            h, info = net.one_round(h, e, dr, dc, kv, mask)
        return h, info

    outs = {}
    with torch.no_grad():
        for mode in ARMS:
            net = StoreNet(mode).eval()
            (h, info), (h2, _) = run(net, items), run(net, swapped)
            outs[mode] = torch.equal(h, h2)                                  # True = the cards made no difference
            if mode == "nostore":
                p, top = info
                assert float(p[:, :N_CARDS].abs().sum()) == 0 and bool((p[:, NULL_IDX] == 1).all())
                assert bool((top[:, 0] == NULL_IDX).all())
                t, s, _, cards, mask = tensors(items, mode, "cpu")
                assert bool((net.loop_rounds(t, s, cards, mask, 6)[2][:, :, 0] == NULL_IDX).all())
    assert outs["nostore"] and not outs["store"] and not outs["pasted"], outs
    t = tensors(items, "pasted", "cpu")[0]
    assert t.shape[1] == FIXED_ROWS + N_CARDS and t[:, FIXED_ROWS:].tolist() == [it["cards"] for it in items]
    # 5. the store arm's keys and query learn from the answer loss; 358i2's block check still passes
    net = StoreNet("store")
    t, s, y, cards, mask = tensors(items, "store", "cpu")
    loss = sum(R.ce_and_exact(lg, s, y)[0] + q.float().mean() for lg, q in net.loop_train(t, s, cards, mask, 2, 2))
    loss.backward()
    g = store_grad_norms(net)
    assert all(g[p] > 0 for p in STORE_PARTS), g
    assert all(p.grad is not None and float(p.grad.abs().sum()) > 0 for _, p in I2._block_mats(net))
    w = counts["by_arm"]["store"]
    print(f"selftest ok: worlds (decoys, decoys share the asked card's type, answers, no answer in the question) 8000/8000; test vs practice sample overlap 0; "
          f"weights store = nostore = pasted = {w} (store parts {counts['store_parts']}); nostore reads only NULL and "
          f"ignores the cards; store and pasted see them; every store part gets a gradient; torch {torch.__version__}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("make-tests"); p.add_argument("--out", required=True)
    p = sub.add_parser("train")
    p.add_argument("--arm", choices=ARMS, required=True); p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", required=True); p.add_argument("--steps", type=int, default=10000)
    p.add_argument("--dev", action="store_true"); p.add_argument("--tests", default=DEFAULT_TESTS)
    p.add_argument("--batch", type=int, default=64); p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--warmup", type=int, default=100); p.add_argument("--log-every", type=int, default=250)
    p.add_argument("--threads", type=int, default=1)
    p = sub.add_parser("eval")
    p.add_argument("--ckpt", required=True); p.add_argument("--tests", required=True); p.add_argument("--out", required=True)
    p.add_argument("--limit", type=int, default=None)
    sub.add_parser("selftest")
    a = ap.parse_args()
    {"make-tests": make_tests, "train": train, "eval": run_eval, "selftest": lambda _: selftest()}[a.cmd](a)


if __name__ == "__main__":
    main()
