#!/usr/bin/env python3
"""rsn-358b2: the first chat turn with a LEARNED reasoner in the middle (sleep research thread, 2026-09-26).

Ben's design (13:53 UTC): a 1B takes in the message and puts it in a form the reasoner reads, the reasoner works it
out, and the talker turns the result into a message. Today no learned reasoner touches a real message (the build's
reasoner is hand-written code). This is the smallest real instance, on Latin squares ("number squares"), the kind the
loop net is best at. Everything is judged on the final message by code.

Requests are chat messages made by code templates: "finish this number square", rows written as "3 _ 1 _ 5".
  A  1B alone: plain MiniCPM5-1B (bf16, enable_thinking=False, greedy) reads the request and writes the square.
  B  bridge: (1) the same 1B copies the square out of the message (one row per line, _ for blanks); code reads the
     copy into grid tokens; (2) the loop net (a sealed rsn-358 loop checkpoint, its own stop rule) fills it; (3) the
     checker tests the net's grid against the COPY (the only thing the system can see); if it fails, the reply is an
     honest "I couldn't finish this one"; (4) otherwise the 1B writes the reply from the finished rows.
  C  report only, ceiling: code reads the request directly, the loop net fills it, a fixed sentence gives it.
Scores (per size, from the delivered message, against the true puzzle): right; honest "couldn't"; wrong answer given
as an answer. Stage counts for B: copy exact, net right given the copy, reply faithful to the net's grid.

With a 358a checkpoint (no legend row) only squares whose clues show every number are used (358a's hidden-symbol
bug; 358i nets read a legend row and get it with --legend).

  python -B scripts/claude_rsn358b2_bridge.py run --model DIR --ckpt LOOP.pt --sizes 5,6,7 --n 100 --seed S --out DIR [--legend]
  python -B scripts/claude_rsn358b2_bridge.py selftest     (no 1B: a fake talker that copies perfectly)
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

TEMPLATES = [
    "Can you finish this number square for me? Every row and every column has to use each of the numbers 1 to {s} "
    "exactly once.\n{rows}",
    "I'm stuck on this puzzle. Fill in the blanks (_) so that each row and each column contains 1 to {s} with no "
    "repeats.\n{rows}",
    "Here's a {s} by {s} Latin square with some cells missing. Could you complete it?\n{rows}",
    "My little cousin gave me this one: each row and column needs the numbers 1-{s} once each. What's the full "
    "square?\n{rows}",
]
ALONE_TAIL = "\n\nReply with the finished square only, one row per line, numbers separated by spaces."
COPY_PROMPT = ("Copy the square from the message below exactly, one row per line, numbers separated by spaces, "
               "with _ for each empty cell. Write nothing else.\n\nMessage:\n{req}")
REPLY_PROMPT = ("You solved the user's number square. Write a short, friendly reply that gives this finished square, "
                "one row per line, exactly as written:\n{rows}")
COULDNT = "I tried, but I couldn't finish this one with confidence, so I won't guess."
CEILING = "Here is the finished square:\n{rows}"


def rows_text(grid):
    return "\n".join(" ".join("_" if v == 0 else str(v) for v in row) for row in grid)


def make_requests(seed, n, s, need_all_visible):
    import claude_rsn358a_envs as E
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        sol, puz = E.make_latin_base(rng, s)
        puz1 = [[v + 1 if v >= 0 else 0 for v in row] for row in puz]
        sol1 = [[v + 1 for v in row] for row in sol]
        if need_all_visible and {v for row in puz1 for v in row if v} != set(range(1, s + 1)):
            continue
        rows = "\n".join("Row %d: %s" % (i + 1, " ".join("_" if v == 0 else str(v) for v in row))
                         for i, row in enumerate(puz1))
        out.append({"size": s, "puz": puz1, "sol": sol1, "text": rng.choice(TEMPLATES).format(s=s, rows=rows)})
    return out


def parse_grid(text, s, allow_blank):
    """first s lines that hold exactly s cells (digits 1..s, or _ when allowed); a leading 'Row k:' is ignored."""
    rows = []
    for line in text.splitlines():
        line = re.sub(r"^\s*(row\s*\d+\s*[:.)-]?)", "", line.strip(), flags=re.I)
        cells = re.findall(r"_|\d+", line)
        if len(cells) != s:
            continue
        vals = [0 if c == "_" else int(c) for c in cells]
        if any(v > s or (v == 0 and not allow_blank) for v in vals):
            continue
        rows.append(vals)
        if len(rows) == s:
            return rows
    return None


def is_solution(puz, grid):
    s = len(puz)
    if grid is None:
        return False
    full = set(range(1, s + 1))
    if any(puz[r][c] and puz[r][c] != grid[r][c] for r in range(s) for c in range(s)):
        return False
    return all(set(grid[r]) == full for r in range(s)) and all({grid[r][c] for r in range(s)} == full for c in range(s))


def item_of(puz, legend):
    """grid tokens exactly as claude_rsn358a_envs.latin_item builds them, with symbol names = the numbers."""
    import claude_rsn358a_envs as E
    s = len(puz)
    tokens = [[E.SYM + v - 1 if v else E.MASK for v in row] for row in puz]
    slot = [[0 if v else 1 for v in row] for row in puz]
    target = [[0] * s for _ in range(s)]
    it = E.Item("grids", s, tokens, slot, target, {"puz": [[v - 1 if v else -1 for v in row] for row in puz],
                                                    "names": list(range(s))})
    if legend:
        it = E.Item("grids", s, tokens + [[E.BLANK] * s, [E.SYM + k for k in range(s)]],
                    slot + [[0] * s, [0] * s], target + [[0] * s, [0] * s], it.meta)
    return it


class LoopSolver:
    def __init__(self, ckpt, legend, device):
        if legend:
            import claude_rsn358i_run as I
            self.R, self.E = I.R, I.E
        else:
            import claude_rsn358a2_run  # noqa: F401  (v2 stop rule)
            import claude_rsn358a_run as R
            import claude_rsn358a_envs as E
            self.R, self.E = R, E
        import claude_rsn358a2_run as V
        self.stop_round = V.stop_round
        self.legend, self.device = legend, device
        self.net = self.R.load(ckpt, device).eval()
        assert self.net.arm == "loop"

    def solve(self, puz):
        import torch
        it = item_of(puz, self.legend)
        t, s, _, env = self.R.tensors([it], self.device)
        with torch.no_grad():
            preds, qs = self.net.loop_rounds(t, s, env, self.R.TEST_ROUNDS)
        p, q = preds[0].tolist(), qs[0].tolist()
        stop = self.stop_round(p, q, self.R.TEST_ROUNDS)
        g = self.R.grid_of(p[stop], it)
        n = len(puz)
        out = [[puz[r][c] or (g[r][c] - self.E.SYM + 1 if self.E.SYM <= g[r][c] < self.E.SYM + n else 0)
                for c in range(n)] for r in range(n)]
        return out, stop + 1


class Talker:
    def __init__(self, model_dir, device):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
        self.tok.padding_side = "left"
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=torch.bfloat16,
                                                          trust_remote_code=True).to(device).eval()
        self.device = device

    def say(self, prompts, max_new=160, bs=16):
        out = []
        for i in range(0, len(prompts), bs):
            texts = [self.tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False,
                                                  add_generation_prompt=True, enable_thinking=False)
                     for p in prompts[i:i + bs]]
            enc = self.tok(texts, return_tensors="pt", padding=True).to(self.device)
            with self.torch.no_grad():
                gen = self.model.generate(**enc, max_new_tokens=max_new, do_sample=False,
                                          pad_token_id=self.tok.pad_token_id)
            out += self.tok.batch_decode(gen[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)
        return out


def score(reqs, replies, couldnt_text=COULDNT):
    res = {"n": len(reqs), "right": 0, "couldnt": 0, "wrong_given": 0}
    for r, text in zip(reqs, replies):
        if text.strip() == couldnt_text:
            res["couldnt"] += 1
        elif is_solution(r["puz"], parse_grid(text, r["size"], False)):
            res["right"] += 1
        else:
            res["wrong_given"] += 1
    return res


def run_size(talker, solver, reqs):
    s = reqs[0]["size"]
    alone = talker.say([r["text"] + ALONE_TAIL for r in reqs])
    copies = talker.say([COPY_PROMPT.format(req=r["text"]) for r in reqs])
    stage = {"copy_exact": 0, "copy_unreadable": 0, "net_right_given_copy": 0, "internal_check_pass": 0,
             "reply_faithful": 0}
    bridge, to_phrase, idx, rounds = [None] * len(reqs), [], [], []
    for i, (r, cp) in enumerate(zip(reqs, copies)):
        g = parse_grid(cp, s, True)
        if g is None:
            stage["copy_unreadable"] += 1
            bridge[i] = COULDNT
            continue
        stage["copy_exact"] += g == r["puz"]
        filled, nr = solver.solve(g)
        rounds.append(nr)
        stage["net_right_given_copy"] += is_solution(g, filled)
        if not is_solution(g, filled):                     # the system can only check against its own copy
            bridge[i] = COULDNT
            continue
        stage["internal_check_pass"] += 1
        to_phrase.append(REPLY_PROMPT.format(rows=rows_text(filled)))
        idx.append((i, filled))
    for (i, filled), text in zip(idx, talker.say(to_phrase) if to_phrase else []):
        bridge[i] = text
        stage["reply_faithful"] += parse_grid(text, s, False) == filled
    ceiling = []
    for r in reqs:
        filled, _ = solver.solve(parse_grid(r["text"], s, True))
        ceiling.append(CEILING.format(rows=rows_text(filled)))
    return {"size": s, "A_alone": score(reqs, alone), "B_bridge": score(reqs, bridge), "B_stages": stage,
            "C_ceiling": score(reqs, ceiling), "B_mean_rounds": round(sum(rounds) / max(1, len(rounds)), 2)}, \
        [{"req": r["text"], "alone": a, "copy": c, "bridge": b} for r, a, c, b in zip(reqs, alone, copies, bridge)]


def run(a):
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    talker = Talker(a.model, device)
    solver = LoopSolver(a.ckpt, a.legend, device)
    res = {"ckpt": str(a.ckpt), "legend": a.legend, "seed": a.seed, "sizes": {}}
    for s in [int(x) for x in a.sizes.split(",")]:
        reqs = make_requests(a.seed + s, a.n, s, need_all_visible=not a.legend)
        r, rows = run_size(talker, solver, reqs)
        res["sizes"][str(s)] = r
        (out / f"transcripts-{s}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
        print(json.dumps(r), f"{(time.time() - t0) / 60:.1f} min", flush=True)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "bridge.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


def selftest():
    """no 1B: parsing, scoring and item building; a fake talker copies perfectly and repeats the rows."""
    for s in (5, 6, 7):
        reqs = make_requests(1, 20, s, need_all_visible=True)
        for r in reqs:
            assert parse_grid(r["text"], s, True) == r["puz"]
            assert is_solution(r["puz"], r["sol"]) and not is_solution(r["puz"], r["puz"])
            assert {v for row in r["puz"] for v in row if v} == set(range(1, s + 1))
            it = item_of(r["puz"], legend=False)
            assert len(it.tokens) == s and it.meta["names"] == list(range(s))
            itl = item_of(r["puz"], legend=True)
            assert len(itl.tokens) == s + 2
        sc = score(reqs, [CEILING.format(rows=rows_text(r["sol"])) for r in reqs])
        assert sc == {"n": 20, "right": 20, "couldnt": 0, "wrong_given": 0}, sc
        sc = score(reqs, [COULDNT] * 10 + ["no idea"] * 10)
        assert sc == {"n": 20, "right": 0, "couldnt": 10, "wrong_given": 10}, sc
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--model", required=True); p.add_argument("--ckpt", required=True)
    p.add_argument("--sizes", default="5,6,7"); p.add_argument("--n", type=int, default=100)
    p.add_argument("--seed", type=int, default=35900); p.add_argument("--out", required=True)
    p.add_argument("--legend", action="store_true")
    sub.add_parser("selftest")
    a = ap.parse_args()
    run(a) if a.cmd == "run" else selftest()


if __name__ == "__main__":
    main()
