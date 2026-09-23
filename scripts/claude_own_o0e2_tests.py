"""own-O0e2 tests: audit, kill-resume, 200-dialogue smoke, CPU throughput, rotary unit test.

This file is scripts/claude_own_o0e_tests.py pointed at o0e2: the only
differences are the model import (claude_own_o0e2_model instead of
claude_own_o0e_model) and the added T6 rotary unit test (Pown0e2.4). The
serialize and train scripts are imported UNCHANGED from the o0e files
(claude_own_o0e_serialize, claude_own_o0e_train).

Generates 200 toy dialogues (fictional names only, seeded) and runs:
  T1 audit: model param count == 61,783,680 (exact bar).
  T2 kill test at tiny width: params identical after resume vs uninterrupted.
  T3 smoke (<= 10 min): loss falls on the 200 dialogues; all three
     serializations round-trip on every dialogue (prompt builds,
     extractor recovers the gold when it is appended).
  T4 leak check (Pown0e2.3): on all 200 dialogues x 3 arms, prompts are
     byte-identical when every gold answer is replaced by ZZZPOISON9,
     and no gold answer appears in any question line.
  T5 throughput: 2-minute CPU run on the full-size model (report only).
  T6 rotary unit test (Pown0e2.4): rotating q and k by the same position
     offset leaves q.k unchanged (relative-position property);
     max abs error <= 1e-5.

Writes TESTLOG lines to stdout; the caller saves them to the artifacts dir.
Run: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; \
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/claude_own_o0e2_tests.py --out <artifacts dir>
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import random
import shutil
import sys
import time

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from claude_own_o0e2_model import (
    EXPECTED_PARAMS,
    ModelConfig,
    PlainTransformer,
    Rotary,
    count_parameters,
)
from claude_own_o0e_serialize import build_prompt, greedy_extract, words
from claude_own_o0e_train import train

POISON = "ZZZPOISON9"
ARMS = ("plain", "rag", "notebook")

OWNERS = ["Mira", "Tal", "Oren", "Ada", "Bo", "Fara", "Lena", "Rook",
          "Nils", "Isha", "Petr", "Quin", "Sana", "Tovi", "Umar", "Vesa"]
PETS = ["Pip", "Fig", "Moss", "Zeb", "Kip", "Luz", "Nip", "Taz"]
PLACES = ["Rill", "Dunmore", "Kest", "Almar", "Bren", "Caldor", "Eastvale"]
RELS = [("dog", PETS), ("cat", PETS), ("sister", OWNERS), ("boss", OWNERS),
        ("home", PLACES)]


def gen_dialogues(n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    out = []
    for w in range(n):
        owners = rng.sample(OWNERS, 4)
        facts = []
        turns = []
        for rel, pool in rng.sample(RELS, 3):
            o = rng.choice(owners)
            v = rng.choice([p for p in pool if p not in owners])
            facts.append([o, rel, v])
            turns.append({"role": "teach",
                          "text": f"{o}'s {rel} is {v}.",
                          "facts": [[o, rel, v]]})
        if rng.random() < 0.5:  # a correction supersedes one fact
            o, rel, _ = rng.choice(facts)
            pool = dict(RELS)[rel]
            v2 = rng.choice([p for p in pool if p not in owners])
            facts = [f for f in facts if not (f[0] == o and f[1] == rel)]
            facts.append([o, rel, v2])
            turns.append({"role": "correct",
                          "text": f"Actually {o}'s {rel} is {v2}.",
                          "facts": [[o, rel, v2]]})
        # questions: two taught, one untaught (abstain)
        asked = rng.sample(facts, min(2, len(facts)))
        for o, rel, v in asked:
            q = f"What is {o}'s {rel} called?" if rel in ("dog", "cat") \
                else f"Who is {o}'s {rel}?" if rel in ("sister", "boss") \
                else f"Where does {o} live?"
            turns.append({"role": "ask", "text": q, "answer": v})
        uo = rng.choice([o for o in OWNERS if o not in owners]) \
            if any(o not in owners for o in OWNERS) else "Xan"
        rel, _ = rng.choice(RELS)
        turns.append({"role": "ask",
                      "text": f"What is {uo}'s {rel} called?",
                      "answer": "I don't know"})
        out.append({"world_id": f"w{w:03d}", "turns": turns})
    return out


def training_texts(dialogues: list[dict]) -> list[str]:
    texts = []
    for d in dialogues:
        lines = []
        for t in d["turns"]:
            tag = {"teach": "Teach", "correct": "Correct", "ask": "Ask"}[t["role"]]
            lines.append(f"{tag}: {t['text']}")
            if t["role"] == "ask":
                lines.append(f"A: {t['answer']}")
        texts.append("\n".join(lines))
    return texts


def rotary_unit_test() -> tuple[bool, float, float]:
    """Relative-position property: same offset on q and k leaves q.k unchanged.

    (a) per-position: (R_t q).(R_t k) == q.k for every position t;
    (b) cross-position: (R_a q).(R_b k) depends only on b - a
        (pair (0, d) vs (m, m + d) must agree).
    Returns (pass, err_a, err_b); bar is both <= 1e-5.
    """
    torch.manual_seed(1234)
    rot = Rotary(head_dim=64, context=128)
    rot.eval()
    with torch.no_grad():
        q = torch.randn(2, 2, 8, 64)
        k = torch.randn(2, 2, 8, 64)
        dots_before = (q * k).sum(-1)
        qr, kr = rot(q, k)
        dots_after = (qr * kr).sum(-1)
        err_a = (dots_before - dots_after).abs().max().item()
        # FIX (driver-only, post-seal; see RESULTS.md D1): the first version
        # compared position pair (0, d) against (m, m + d) built from
        # DIFFERENT random vectors, so it could never agree. The property
        # needs the SAME q/k vectors at both pairs: plant one vector v at
        # positions 0 and m of the q sequence and one vector w at d and
        # m + d of the k sequence, then compare the two cross dots.
        T, m, d = 16, 5, 3
        v = torch.randn(1, 1, 1, 64)
        w = torch.randn(1, 1, 1, 64)
        qseq = torch.randn(1, 1, T, 64)
        kseq = torch.randn(1, 1, T, 64)
        qseq[..., 0, :] = v
        qseq[..., m, :] = v
        kseq[..., d, :] = w
        kseq[..., m + d, :] = w
        qr2, kr2 = rot(qseq, kseq)
        ab0 = (qr2[..., 0, :] * kr2[..., d, :]).sum()
        ab1 = (qr2[..., m, :] * kr2[..., m + d, :]).sum()
        err_b = (ab0 - ab1).abs().item()
    return (err_a <= 1e-5 and err_b <= 1e-5), err_a, err_b


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default = 7)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    t_start = time.time()

    # T1 audit
    torch.manual_seed(0)
    total, _ = count_parameters(PlainTransformer())
    in_tol = EXPECTED_PARAMS * 0.998 <= total <= EXPECTED_PARAMS * 1.002
    print(f"T1 audit count={total} expected={EXPECTED_PARAMS} "
          f"{'PASS' if total == EXPECTED_PARAMS else ('INTOL' if in_tol else 'FAIL')}")

    # dialogues
    dialogues = gen_dialogues(args.n, args.seed)
    n_ask = sum(1 for d in dialogues for t in d["turns"] if t["role"] == "ask")
    print(f"toy dialogues={len(dialogues)} ask_turns={n_ask}")

    # T2 kill test at tiny width
    tiny = ModelConfig(vocab=1024, width=64, layers=2, mlp_width=128,
                       heads=4, context=64)
    texts = training_texts(dialogues)
    dA = os.path.join(args.out, "killA")
    dB = os.path.join(args.out, "killB")
    for d in (dA, dB):
        shutil.rmtree(d, ignore_errors=True)
    train(texts, dA, total_steps=4, batch=8, seed=1, cfg=tiny,
          ckpt_steps=100, ctx_len=64)          # killed here (stop, no ckpt harm)
    m_res, _ = train(texts, dA, total_steps=8, batch=8, seed=1, cfg=tiny,
                     ckpt_steps=100, ctx_len=64)  # resume to step 8
    m_fresh, _ = train(texts, dB, total_steps=8, batch=8, seed=1, cfg=tiny,
                       ckpt_steps=100, ctx_len=64)  # uninterrupted
    same = all(torch.equal(a, b) for a, b in
               zip(m_res.state_dict().values(), m_fresh.state_dict().values()))
    n_params = sum(p.numel() for p in m_res.parameters())
    print(f"T2 kill tiny_params={n_params} identical_after_resume={same} "
          f"{'PASS' if same else 'FAIL'}")

    # T3 smoke: loss falls + round-trip, timed <= 10 min
    t0 = time.time()
    dS = os.path.join(args.out, "smoke")
    shutil.rmtree(dS, ignore_errors=True)
    _, losses = train(texts, dS, total_steps=30, batch=8, seed=2, cfg=tiny,
                      ckpt_steps=100, ctx_len=64)
    fell = losses[-1] < losses[0]
    print(f"T3 smoke steps=30 loss_first={losses[0]:.4f} loss_last={losses[-1]:.4f} "
          f"falls={fell} elapsed={time.time() - t0:.1f}s "
          f"{'PASS' if fell else 'FAIL'}")
    rt_ok = rt_n = 0
    for d in dialogues:
        for i, t in enumerate(d["turns"]):
            if t["role"] != "ask":
                continue
            for arm in ARMS:
                rt_n += 1
                p = build_prompt(d, i, arm)
                if greedy_extract(p + " " + t["answer"]) == t["answer"]:
                    rt_ok += 1
    print(f"T3 roundtrip ok={rt_ok}/{rt_n} "
          f"{'PASS' if rt_ok == rt_n else 'FAIL'}")

    # T4 leak check on all dialogues x 3 arms
    poisoned = copy.deepcopy(dialogues)
    for d in poisoned:
        for t in d["turns"]:
            if t["role"] == "ask":
                t["answer"] = POISON
    unchanged = leak_q = total_prompts = 0
    for d, dp in zip(dialogues, poisoned):
        for i, t in enumerate(d["turns"]):
            if t["role"] != "ask":
                continue
            for arm in ARMS:
                total_prompts += 1
                p, pp = build_prompt(d, i, arm), build_prompt(dp, i, arm)
                if p == pp and POISON not in p:
                    unchanged += 1
                qline = p.rsplit("Q:", 1)[-1]
                if t["answer"] not in qline and "A:" not in qline.replace("\nA:", "", 1) \
                        or True:
                    pass
                # strict: gold answer must not appear after the final Q: marker
                # (the prompt ends with "Q: <question>\nA:")
                if t["answer"] in qline:
                    leak_q += 1
    print(f"T4 poison_unchanged={unchanged}/{total_prompts} "
          f"qline_leaks={leak_q} {'PASS' if unchanged == total_prompts and leak_q == 0 else 'FAIL'}")

    # T5 throughput: 2-minute CPU run, full-size model, report only
    cfg_full = ModelConfig()
    torch.manual_seed(0)
    m = PlainTransformer(cfg_full)
    m.train()
    opt = torch.optim.AdamW(m.parameters(), lr=1e-4)
    B, T = 2, 128
    toks = 0
    t1 = time.time()
    steps = 0
    while time.time() - t1 < 120:
        ids = torch.randint(0, cfg_full.vocab, (B, T))
        opt.zero_grad()
        loss = m(ids[:, :-1])[:, :, :].reshape(-1, cfg_full.vocab)
        l = torch.nn.functional.cross_entropy(loss, ids[:, 1:].reshape(-1))
        l.backward()
        opt.step()
        toks += B * T
        steps += 1
    dt = time.time() - t1
    print(f"T5 throughput tokens={toks} seconds={dt:.1f} tok_per_s={toks / dt:.1f} "
          f"steps={steps} (report only)")

    # T6 rotary unit test (Pown0e2.4)
    rok, err_a, err_b = rotary_unit_test()
    print(f"T6 rotary err_same_pos={err_a:.3e} err_offset={err_b:.3e} "
          f"{'PASS' if rok else 'FAIL'}")
    print(f"WALL total={time.time() - t_start:.1f}s")


if __name__ == "__main__":
    main()
