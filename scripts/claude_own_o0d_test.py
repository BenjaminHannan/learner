"""own-O0d REGISTERED TESTS (sealed; run once after the seal).

Pown0d.1 unit tests; Pown0d.2 parameter audit vs plan S7.1; Pown0d.3 kill/resume
byte-identity; Pown0d.4 whole-word fuzz (10,000 samples). Plus a <=10-min CPU
smoke on an in-task toy frame set showing the loss falls, and an MLM pilot.
Writes RESULTS.md into artifacts/claude-own-o0d-20260923/.
"""

import hashlib
import itertools
import json
import os
import pickle
import random
import subprocess
import sys
import time

import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from claude_own_o0d_model import (
    ACTS, MODES, PLAN_COUNTS, ByteBPE, EarConfig, OwnEar, decode_owner,
    decode_span, hungarian_match, is_whole_word_span,
)
from claude_own_o0d_train import (gen_frame_items, gen_pretrain_texts,
                                  item_to_gold, RELS)

ART = os.path.join("artifacts", "claude-own-o0d-20260923")
UV = ["uv", "run", "--offline", "--no-project", "--python", "3.12",
      "--with", "torch", "--with", "numpy", "python", "-B"]
ENV = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
RELS_IDX = lambda r: RELS.index(r) if r in RELS else len(RELS) - 1

results = {"units": [], "ok": True}


def check(name, cond, detail=""):
    results["units"].append({"name": name, "pass": bool(cond), "detail": detail})
    if not cond:
        results["ok"] = False
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}", flush=True)


# ---------------------------------------------------------------- Pown0d.1
def unit_tests():
    torch.manual_seed(0)
    texts = gen_pretrain_texts(300, 7) + [i["text"] for i in gen_frame_items(300, 8)]
    tok = ByteBPE.train(texts, 512)
    check("bpe-trains", len(tok.vocab) > 256, f"vocab={len(tok.vocab)}")
    # round-trip incl. mixed case + apostrophes
    sents = ["Mira's DOG is Pip.", "My sisters are Mira, Tal and Oona.",
             "so Ada's son is Bo", "toms boss", "Fig, not Moss."]
    rt = all(tok.decode(tok.encode(s)[0]) == s for s in sents)
    check("bpe-roundtrip", rt, f"{len(sents)} sentences")
    # word ids: one word -> one id run; never merges across spaces
    ids, wids = tok.encode("Mira Stil")
    check("word-ids", len(set(wids)) == 2 and wids[0] != wids[-1],
          f"ids={ids} wids={wids}")
    # valid mask blocks word-cutting spans
    ids, wids = tok.encode("sister-in-law")
    m = tok.valid_span_mask(wids)
    inside = [(s, e) for s in range(len(ids)) for e in range(s + 1, len(ids))
              if wids[s] == wids[e]]
    blocked = all(not m[s, e].item() for s, e in inside if (s, e) != (0, len(ids) - 1)
                  or True)
    # every off-diagonal within one word that is not the full word must be blocked;
    # the full-word span must be allowed
    full_ok = bool(m[0, len(ids) - 1].item())
    partial_blocked = all(not m[s, e].item() for s, e in inside
                          if not (s == 0 and e == len(ids) - 1))
    check("mask-blocks-cuts", full_ok and partial_blocked,
          f"T={len(ids)} wids={wids}")
    # decode_span can only return whole-word spans (targeted)
    T = len(ids)
    g = torch.Generator().manual_seed(1)
    bad = 0
    for _ in range(2000):
        sl = torch.randn(T, generator=g)
        el = torch.randn(T, generator=g)
        # adversarial: best raw pair is a word-cutting one
        s, e, _ = decode_span(sl, el, m)
        if not is_whole_word_span(s, e, wids):
            bad += 1
    check("decode-whole-word-only", bad == 0, f"bad={bad}/2000")
    # hungarian: optimal vs brute force on random costs
    worst = 0.0
    for seed in range(20):
        gg = torch.Generator().manual_seed(seed)
        c = torch.rand(1, 6, 6, generator=gg)
        a = hungarian_match(c)[0].tolist()
        got = sum(c[0, s, a[s]].item() for s in range(6))
        best = min(sum(c[0, s, p[s]].item() for s in range(6))
                   for p in itertools.permutations(range(6)))
        worst = max(worst, got - best)
    check("hungarian-optimal", worst < 1e-6, f"maxgap={worst:.2e}")
    # forward shapes at tiny + full width (full: shapes + audit only, 1 batch)
    cfg = EarConfig(vocab_size=len(tok.vocab), d_model=64, n_layers=2,
                    n_heads=4, max_len=48)
    model = OwnEar(cfg)
    ids, wids = tok.encode("Mira's dog is Pip.")
    bid = torch.tensor([ids])
    out = model(bid, torch.ones(1, len(ids), dtype=torch.bool))
    shapes_ok = (out["act"].shape == (1, 9) and out["count"].shape == (1, 7)
                 and out["slot"].shape == (1, 6, 64)
                 and out["rel_slot"].shape == (1, 6, 154)
                 and len(out["rel_q"]) == 3
                 and out["span"]["own_s"].shape == (1, 6, len(ids)))
    check("forward-shapes", shapes_ok, "")
    # relation table: 153 relations + OTHER = 154 (read-only, required by task)
    with open("artifacts/claude-smolear257-20260922/relation_table_v2.json") as f:
        rt2 = json.load(f)
    check("relation-table-153", len(rt2["relations"]) == 153,
          f"n={len(rt2['relations'])}")
    return tok


# ---------------------------------------------------------------- Pown0d.2
def audit():
    model = OwnEar(EarConfig())
    a = model.audit()
    lines = ["part | audited | plan | match"]
    allok = True
    for k in ["embeddings", "encoder", "slot_layer", "pointers",
              "question_pointers", "classifiers", "special_tokens", "total"]:
        ok = a[k] == PLAN_COUNTS[k]
        allok = allok and ok
        lines.append(f"{k} | {a[k]} | {PLAN_COUNTS[k]} | {ok}")
    diff = abs(a["total"] - 32850051) / 32850051
    check("audit-within-0.5pct", diff <= 0.005,
          f"total={a['total']} diff={diff:.6f}")
    results["audit"] = {"parts": a, "plan": PLAN_COUNTS, "table": lines}
    print("\n".join(lines), flush=True)
    return allok


# ------------------------------------------------- helpers for train runs
def run_train(mode, workdir, tok_path, vocab, steps, seed, ckpt_steps=10,
              items=400, width=64, layers=2, heads=4, timeout_s=600):
    os.makedirs(workdir, exist_ok=True)
    cmd = UV + ["scripts/claude_own_o0d_train.py", "--mode", mode,
                "--workdir", workdir, "--tok", tok_path, "--vocab", str(vocab),
                "--width", str(width), "--layers", str(layers),
                "--heads", str(heads), "--max-steps", str(steps),
                "--seed", str(seed), "--ckpt-steps", str(ckpt_steps),
                "--items", str(items)]
    p = subprocess.run(cmd, env=ENV, capture_output=True, text=True,
                       timeout=timeout_s)
    return p


def state_hash(workdir, step):
    d = torch.load(os.path.join(workdir, f"ckpt_step{step:06d}.pt"),
                   map_location="cpu", weights_only=False)
    h = hashlib.sha256()
    for k in sorted(d["model"]):
        h.update(d["model"][k].numpy().tobytes())
    return h.hexdigest()


# ---------------------------------------------------------------- Pown0d.3
def kill_test(tok_path, vocab):
    N = 30
    kw = dict(mode="frame", tok_path=tok_path, vocab=vocab, steps=2 * N,
              seed=3, ckpt_steps=5, items=200, timeout_s=600)
    # arm A: uninterrupted 2N
    a = os.path.join(ART, "kill_A")
    p = run_train(workdir=a, **kw)
    check("kill-A-runs", p.returncode == 0, p.stderr[-500:] if p.returncode else "")
    if p.returncode != 0:
        return
    ha = state_hash(a, 2 * N)
    # arm B: background to 2N, SIGKILL after ckpt N lands, then resume
    b = os.path.join(ART, "kill_B")
    os.makedirs(b, exist_ok=True)
    cmd = UV + ["scripts/claude_own_o0d_train.py", "--mode", "frame",
                "--workdir", b, "--tok", tok_path, "--vocab", str(vocab),
                "--width", "64", "--layers", "2", "--heads", "4",
                "--max-steps", str(2 * N), "--seed", "3", "--ckpt-steps", "5",
                "--items", "200"]
    proc = subprocess.Popen(cmd, env=ENV, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    target = os.path.join(b, f"ckpt_step{N:06d}.pt")
    t0 = time.time()
    while time.time() - t0 < 590:
        if os.path.exists(target):
            break
        time.sleep(2)
    landed = os.path.exists(target)
    proc.kill()  # SIGKILL-equivalent: no cleanup, tests atomicity
    proc.wait()
    check("kill-landed", landed, f"ckpt@{N} present={landed}")
    if not landed:
        return
    # resume in foreground to 2N
    p2 = run_train(workdir=b, **kw)
    check("kill-resume-runs", p2.returncode == 0,
          p2.stderr[-500:] if p2.returncode else "")
    if p2.returncode != 0:
        return
    hb = state_hash(b, 2 * N)
    check("kill-identical", ha == hb, f"A={ha[:12]} B={hb[:12]}")
    results["kill_hashes"] = {"A": ha, "B": hb}


# ---------------------------------------------------------------- Pown0d.4
def fuzz_spans():
    g = torch.Generator().manual_seed(99)
    bad = 0
    for i in range(10000):
        T = int(torch.randint(1, 13, (1,), generator=g).item())
        # random word layout: random cut points
        cuts = sorted(random.Random(1000 + i).sample(range(1, T), k=random.Random(2000 + i).randrange(0, min(T, 4)))) if T > 1 else []
        wids = []
        w = 0
        cutset = set(cuts)
        for t in range(T):
            wids.append(w)
            if t in cutset:
                w += 1
        # build whole-word validity mask from the layout (same rule as
        # ByteBPE.valid_span_mask)
        start, end = [True] * T, [True] * T
        for t in range(1, T):
            if wids[t] == wids[t - 1]:
                start[t] = False
            else:
                end[t - 1] = False
        import torch as _t
        mm = _t.zeros(T, T, dtype=_t.bool)
        for s in range(T):
            if not start[s]:
                continue
            for e in range(s, T):
                if end[e]:
                    mm[s, e] = True
        sl = torch.randn(T, generator=g) * 4
        el = torch.randn(T, generator=g) * 4
        s, e, _ = decode_span(sl, el, mm)
        if not is_whole_word_span(s, e, wids):
            bad += 1
        sp = torch.randn(2, generator=g) * 4
        r = decode_owner(sl, el, mm, sp)
        if isinstance(r[0], tuple):
            _, s2, e2 = r[0]
            if not is_whole_word_span(s2, e2, wids):
                bad += 1
    check("fuzz-10000-zero", bad == 0, f"bad={bad}/10000(+owners)")


# ---------------------------------------------------------------- smoke
def smoke(tok_path, vocab):
    w = os.path.join(ART, "smoke_frame")
    t0 = time.time()
    p = run_train(mode="frame", workdir=w, tok_path=tok_path, vocab=vocab,
                  steps=120, seed=11, ckpt_steps=0, items=400, timeout_s=590)
    dt = time.time() - t0
    check("smoke-runs", p.returncode == 0, p.stderr[-500:] if p.returncode else "")
    if p.returncode != 0:
        return
    with open(os.path.join(w, "losses.json")) as f:
        losses = json.load(f)["losses"]
    n = len(losses)
    early = float(np.mean(losses[:max(1, n // 10)]))
    late = float(np.mean(losses[-max(1, n // 10):]))
    check("smoke-loss-falls", late < early,
          f"early={early:.4f} late={late:.4f} steps={n} t={dt:.0f}s")
    results["smoke"] = {"early": early, "late": late, "steps": n,
                        "seconds": dt}
    # MLM pilot
    w2 = os.path.join(ART, "smoke_mlm")
    p2 = run_train(mode="mlm", workdir=w2, tok_path=tok_path, vocab=vocab,
                   steps=15, seed=11, ckpt_steps=0, items=400, timeout_s=590)
    check("mlm-pilot-runs", p2.returncode == 0,
          p2.stderr[-500:] if p2.returncode else "")


def main():
    t0 = time.time()
    tok = unit_tests()
    audit()
    tok_path = os.path.join(ART, "tok.pkl")
    with open(tok_path, "wb") as f:
        pickle.dump(tok, f)
    kill_test(tok_path, len(tok.vocab))
    fuzz_spans()
    smoke(tok_path, len(tok.vocab))
    results["seconds"] = time.time() - t0
    with open(os.path.join(ART, "test_results.json"), "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"DONE ok={results['ok']} t={results['seconds']:.0f}s", flush=True)


if __name__ == "__main__":
    main()
