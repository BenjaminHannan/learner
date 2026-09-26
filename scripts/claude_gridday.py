#!/usr/bin/env python3
"""Grid day for Fix sleep's grid nights (thought-memory thread, 2026-09-26). A tool, not an experiment on its own.

Why: Ben's 12:48 UTC rule: when a thread's function could improve by joining another thread's function, the two
threads build that join together. Fix sleep's nights train on the model's own checked right answers (dl-2's S arm).
On 5x5 Latin grids guessing finds none: in rv-385, 60 choices of starting over solved 0 of 160 grids, while going
back with a code ban (revert_ban) solved 100. So this day is rv-385's revert_ban search, unchanged, and every grid it
solves gives practice pairs. Agreed with Fix sleep (12:53 and ~13:05 UTC):
  S  every state along a solved grid's path (the given grid plus the first i empty cells filled, in the search's fixed
     row-major order) with the correct next number, in rv-385's exact prompt and reply prefix;
  P  placebo: the same states with a wrong number, one that passes the visible row/column check when one exists,
     otherwise any wrong number (both counts reported);
  K  key (report-only ceiling, Fix sleep 12:55 UTC): the same kind of rows from EVERY day grid, solved or not, taken
     from the answer key, so it shows what training on the key would give; it has no pass mark;
  rows {"messages": [...], "answer": "The number in row R, column C is V", ...}; Fix sleep's shim applies the chat
     template (enable_thinking=False) and puts the loss on the answer only.
  score: fixed states on fresh grids (every state along the true solution), the model's top-scoring number against
     the answer key, so every arm is scored on identical states.
Seeds, nights, harm panel, marks and the verdict belong to Fix sleep. The grids have an answer key in code, so this can
show whether the checker-kept-hits loop works on puzzles too deep for guessing, not that search beats the key.

  day(tok, model, seed, n, budget)    -> {"S": [...], "P": [...], "K": [...], "stats": {...}}     (usable inside Fix sleep's loop)
  score_states(tok, model, seed, n)   -> {"states": .., "right": .., ...}
  python -B scripts/claude_gridday.py day   --model DIR --seed S --n N --out DIR
  python -B scripts/claude_gridday.py score --model DIR --seed S --n N
  python -B scripts/claude_gridday.py selftest [--model DIR]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rv385 as R  # noqa: E402  (rv-385's sealed search, grids and prompt)

SIZE, BUDGET = 5, 60        # rv-385's grid size and budget of model choices per grid
DEV_SEED = 38980            # dev states for the plain 1B baseline (never a test)
TEST_SEED = 38990           # proposed fixed-state test grids (Fix sleep decides)


class ModelChooser:
    """rv-385's Chooser.probs on a model that is already loaded (e.g. Fix sleep's adapter-wrapped 1B)."""

    def __init__(self, tok, model, size=SIZE):
        import torch
        self.torch, self.tok, self.model = torch, tok, model
        self.num_ids = []
        for v in range(1, size + 1):
            ids = tok.encode(str(v), add_special_tokens=False)
            if len(ids) != 1:
                raise RuntimeError(f"number {v} is not one token: {ids}")
            self.num_ids.append(ids[0])

    def text(self, msg, prefix):
        return self.tok.apply_chat_template([{"role": "user", "content": msg}], tokenize=False,
                                            add_generation_prompt=True, enable_thinking=False) + prefix

    def probs(self, parts):
        torch, tok = self.torch, self.tok
        side, pad = tok.padding_side, tok.pad_token
        tok.padding_side = "left"
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token
        try:
            enc = tok([self.text(m, p) for m, p in parts], return_tensors="pt", padding=True)
        finally:
            tok.padding_side = side
            if pad is None:
                tok.pad_token = pad
        dev = next(self.model.parameters()).device
        ids, att = enc["input_ids"].to(dev), enc["attention_mask"].to(dev)
        pos = (att.cumsum(-1) - 1).clamp(min=0)
        was = self.model.training
        self.model.eval()
        with torch.inference_mode():
            lg = self.model(input_ids=ids, attention_mask=att, position_ids=pos).logits[:, -1, :].float()
        self.model.train(was)
        return torch.softmax(lg[:, self.num_ids] / R.TEMP, -1).tolist()


def state_at(p, i, seed=0):
    """A search object sitting at position i of the true solution path (first i empty cells filled correctly)."""
    x = R.Search(p, "revert_ban", seed)
    x.vals = [p["sol"][r][c] for r, c in x.cells[:i]]
    return x


def pair(p, i, v, kind, legal=None):
    x = state_at(p, i)
    msg, pre = x.prompt_parts()
    r, c = x.cells[i]
    row = {"messages": [{"role": "user", "content": msg}], "answer": f"{pre}{v}", "kind": kind, "pid": p["pid"],
           "pos": i, "cell": [r, c], "value": v}
    if legal is not None:
        row["legal_wrong"] = legal
    return row


def pairs_from(p, rng):
    """S and P rows for one solved grid (the solution is unique, so the solved path is the true solution)."""
    S, P = [], []
    x = state_at(p, 0)
    for i, (r, c) in enumerate(x.cells):
        g = state_at(p, i).grid()
        v = p["sol"][r][c]
        S.append(pair(p, i, v, "S"))
        wrong = [w for w in range(1, p["size"] + 1) if w != v]
        legal = [w for w in wrong if not R.conflicts(g, r, c, w)]
        P.append(pair(p, i, rng.choice(legal or wrong), "P", legal=bool(legal)))
    return S, P


def search(ch, puzzles, seed, budget):
    xs = [R.Search(p, "revert_ban", seed) for p in puzzles]
    while True:
        live = [x for x in xs if not x.solved and x.steps < budget]
        if not live:
            return xs
        for k in range(0, len(live), R.BATCH):
            chunk = live[k:k + R.BATCH]
            for x, pr in zip(chunk, ch.probs([x.prompt_parts() for x in chunk])):
                x.step(pr)


def day(tok, model, seed, n, budget=BUDGET, size=SIZE):
    """One day: rv-385's revert_ban search on n fresh grids; practice rows from every solved grid."""
    t0 = time.time()
    puzzles = R.make_puzzles(seed, n, size)
    xs = search(ModelChooser(tok, model, size), puzzles, seed, budget)
    rng = random.Random(f"gridday-placebo|{seed}")
    S, P = [], []
    for x in xs:
        if x.solved:
            if x.grid() != x.p["sol"]:
                raise RuntimeError(f"{x.p['pid']}: solved grid differs from the unique solution")
            s_rows, p_rows = pairs_from(x.p, rng)
            S += s_rows
            P += p_rows
    K = key_rows(puzzles)
    stats = {"seed": seed, "grids": n, "budget": budget, "solved": sum(x.solved for x in xs),
             "choices": sum(x.steps for x in xs), "S_rows": len(S), "P_rows": len(P),
             "P_legal_wrong": sum(r["legal_wrong"] for r in P), "P_any_wrong": sum(not r["legal_wrong"] for r in P),
             "K_rows": len(K), "sec": round(time.time() - t0)}
    return {"S": S, "P": P, "K": K, "stats": stats, "grids": [x.result() for x in xs]}


def key_rows(puzzles):
    """K: rows for every grid from the answer key (no model involved)."""
    K = []
    for p in puzzles:
        for i, (r, c) in enumerate(R.empties(p["puz"])):
            K.append(pair(p, i, p["sol"][r][c], "K"))
    return K


def score_states(tok, model, seed, n, size=SIZE):
    """Fixed states on fresh grids: every state along the true solution; top-scoring number vs the key."""
    ch = ModelChooser(tok, model, size)
    rows = []
    for p in R.make_puzzles(seed, n, size):
        for i, (r, c) in enumerate(R.empties(p["puz"])):
            g = state_at(p, i).grid()
            n_legal = sum(not R.conflicts(g, r, c, w) for w in range(1, size + 1))
            rows.append((p, i, p["sol"][r][c], n_legal))
    right = forced = forced_right = 0
    for k in range(0, len(rows), R.BATCH):
        chunk = rows[k:k + R.BATCH]
        for (p, i, v, n_legal), pr in zip(chunk, ch.probs([state_at(p, i).prompt_parts() for p, i, _, _ in chunk])):
            ok = max(range(size), key=lambda j: pr[j]) + 1 == v
            right += ok
            if n_legal == 1:
                forced += 1
                forced_right += ok
    return {"seed": seed, "grids": n, "states": len(rows), "right": right, "acc": round(right / max(len(rows), 1), 4),
            "forced_states": forced, "forced_right": forced_right,
            "open_states": len(rows) - forced, "open_right": right - forced_right}


def load(model_dir):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=torch.bfloat16, trust_remote_code=True).eval()
    return tok, model


def selftest(model_dir=""):
    ps = R.make_puzzles(7, 4, SIZE)
    for p in ps:
        S, P = pairs_from(p, random.Random(1))
        n = len(R.empties(p["puz"]))
        assert len(S) == len(P) == n
        for s_row, p_row in zip(S, P):
            assert s_row["messages"] == p_row["messages"]                      # same state, only the answer differs
            assert s_row["value"] != p_row["value"]
            r, c = s_row["cell"]
            assert s_row["value"] == p["sol"][r][c]
            assert s_row["answer"].startswith(f"The number in row {r + 1}, column {c + 1} is ")
            if p_row["legal_wrong"]:
                g = state_at(p, s_row["pos"]).grid()
                assert not R.conflicts(g, r, c, p_row["value"])
        # K rows on a grid are the S rows with kind "K" (same states, the key's number)
        K = key_rows([p])
        assert [(k["messages"], k["answer"]) for k in K] == [(r["messages"], r["answer"]) for r in S]
        # the prompt at position i is exactly what rv-385's search shows when it stands there
        x = R.Search(p, "revert_ban", 3)
        for i in range(n):
            assert x.prompt_parts() == state_at(p, i).prompt_parts()
            r, c = x.cells[i]
            x.vals.append(p["sol"][r][c])
    if model_dir:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
        row = pairs_from(ps[0], random.Random(1))[0][3]
        prompt = tok.apply_chat_template(row["messages"], tokenize=False, add_generation_prompt=True,
                                         enable_thinking=False)
        apart = tok(prompt)["input_ids"] + tok(row["answer"], add_special_tokens=False)["input_ids"]
        together = tok(prompt + row["answer"])["input_ids"]
        assert apart == together, (apart[-12:], together[-12:])
        print("tokens: prompt and answer apart == together")
    print("selftest OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["day", "score", "selftest"])
    ap.add_argument("--model", default="")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n", type=int, default=0)
    ap.add_argument("--budget", type=int, default=BUDGET)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest(a.model)
    tok, model = load(a.model)
    if a.cmd == "score":
        print(json.dumps(score_states(tok, model, a.seed, a.n)), flush=True)
        return
    res = day(tok, model, a.seed, a.n, a.budget)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for k in ("S", "P", "K"):
        (out / f"gridday-{k}-seed{a.seed}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in res[k]))
    (out / f"gridday-grids-seed{a.seed}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in res["grids"]))
    (out / f"gridday-stats-seed{a.seed}.json").write_text(json.dumps(res["stats"], indent=1) + "\n")
    print(json.dumps(res["stats"]), flush=True)


if __name__ == "__main__":
    main()
