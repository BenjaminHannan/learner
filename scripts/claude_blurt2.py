#!/usr/bin/env python3
"""blurt-2: rule-keeping blurts and the creative learning loop on number puzzles (creative research thread, 2026-09-25).

Why: in blurt-1 (artifacts/claude-blurt1-dev-20260925/RESULTS-blurt1.md) the base MiniCPM5-1B was right on 2/1800
and 4/1800 free blurts; most tries used numbers the puzzle never gave, or no formula at all. It was breaking the
rules, not getting unlucky.

One change for blurting: constrained decoding. At every step only tokens that keep the text a legal prefix of an
expression over exactly the given numbers (+ - * / and brackets) are allowed; end-of-text is allowed only when the
expression is complete. The 1B's own probabilities still choose among the legal tokens, so blurts stay its own
guesses. Temperature sets how wild they are.

Ben's loop (00:51 UTC 2026-09-25): "the reasoner should be able to do most things. The creative thing is for
generating ideas for things the reasoner can't do usually, and then the creative ideas get saved/written into the
model ... ensuring learning". Here the reasoner stand-in is the 1B's single greedy (rule-keeping) answer.
  loop: before-eval on fresh test puzzles -> the reasoner tries every practice puzzle once -> on each miss, N
  creative blurts, an exact checker keeps the lucky hits (wins, also written to wins/wins.jsonl in the sleep
  thread's format) -> "sleep": a LoRA practises them -> after-eval on the same fresh test puzzles.
  Arms: W = practice on wins + the reasoner's own correct answers; C = the reasoner's own correct answers only,
  repeated to the same number of examples (so W and C differ only in the creative wins).

  python -B scripts/claude_blurt2.py blurt --model M --puzzles F --out F [--n 30 --temp 1.0]      rule-keeping blurts
  python -B scripts/claude_blurt2.py loop  --model M --out DIR [--train-seed 2 --n-train 400 --test-seed 777
                                           --n-test 150 --n 30 --temps 1.0,1.5 --dev-puzzles F --epochs 3
                                           --lora-seeds 0,1]
The test puzzles are made from --test-seed inside the run and are never printed; only counts are reported.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt1 as B1  # noqa: E402

OPCH = set("+-*/")


def _scan(s: str, nums: list[int], state=None):
    """Walk an expression prefix (optionally continuing from an earlier state). Returns (remaining numbers, open
    brackets, expecting_operand, pending digits), or None if the prefix breaks a rule."""
    if state is None:
        rem, depth, want_operand, digits = [str(n) for n in nums], 0, True, ""
    else:
        rem, depth, want_operand, digits = list(state[0]), state[1], state[2], state[3]
    for ch in s:
        if ch == " ":
            if digits:
                if digits not in rem:
                    return None
                rem.remove(digits)
                digits, want_operand = "", False
            continue
        if ch.isdigit():
            if not want_operand:
                return None
            cand = digits + ch
            if not any(r.startswith(cand) for r in rem):
                return None
            if cand.startswith("0") and cand not in rem:
                return None
            digits = cand
            continue
        if digits:                                   # a number ends here
            if digits not in rem:
                return None
            rem.remove(digits)
            digits, want_operand = "", False
        if ch == "(":
            if not want_operand:
                return None
            depth += 1
        elif ch == ")":
            if want_operand or depth == 0:
                return None
            depth -= 1
        elif ch in OPCH:
            if want_operand:
                return None
            want_operand = True
        else:
            return None
    return rem, depth, want_operand, digits


def legal_prefix(s: str, nums, state=None) -> bool:
    """A prefix that can still be completed: an operand is never owed with no numbers left, and brackets stay
    shallower than the number count (otherwise the 1B can loop on "( ( (" after using every number).
    With `state` (from _scan of the text before), `s` is only the new piece."""
    st = _scan(s, nums, state)
    if st is None:
        return False
    rem, depth, want_operand, digits = st
    if want_operand and not digits and not rem:
        return False
    return depth <= len(nums) - 1


def complete(s: str, nums) -> bool:
    st = _scan(s, nums)
    if st is None:
        return False
    rem, depth, want_operand, digits = st
    if digits:
        if digits not in rem:
            return False
        rem = list(rem)
        rem.remove(digits)
        want_operand = False
    return not rem and depth == 0 and not want_operand


_VOCAB: dict = {}


def _expr_tokens(tok):
    """Every token made only of digits, + - * / ( ) and single spaces (decoded once per tokenizer, then cached)."""
    key = id(tok)
    if key not in _VOCAB:
        ch = set("0123456789+-*/() ")
        out = []
        for i in range(len(tok)):
            t = tok.decode([i])
            if t and set(t) <= ch and "  " not in t and len(t) <= 6:
                out.append((i, t))
        _VOCAB[key] = out
    return _VOCAB[key]


class RuleKeeper:
    """A transformers LogitsProcessor that keeps every sequence a legal expression over `nums`."""

    def __init__(self, tok, nums, cut: int):
        import torch
        self.torch, self.tok, self.nums, self.cut = torch, tok, list(nums), cut
        allowed_ch = set("".join(str(n) for n in nums)) | set("+-*/() ")
        self.cands = [(i, t) for i, t in _expr_tokens(tok) if set(t) <= allowed_ch]
        self.eos = tok.eos_token_id
        self.memo: dict[str, list[int]] = {}

    def allowed(self, text: str) -> list[int]:
        if text not in self.memo:
            st = _scan(text, self.nums)
            ok = [] if st is None else [i for i, t in self.cands if legal_prefix(t, self.nums, st)]
            if complete(text, self.nums) or not ok:
                ok.append(self.eos)
            self.memo[text] = ok
        return self.memo[text]

    def __call__(self, input_ids, scores):
        mask = self.torch.full_like(scores, float("-inf"))
        for b in range(input_ids.shape[0]):
            mask[b, self.allowed(self.tok.decode(input_ids[b, self.cut:], skip_special_tokens=True))] = 0.0
        return scores + mask


class Solver:
    def __init__(self, model_dir):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
        self.dev = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = AutoModelForCausalLM.from_pretrained(model_dir, trust_remote_code=True,
                                                          dtype=torch.bfloat16).to(self.dev).eval()

    def prompt(self, p) -> str:
        return self.tok.apply_chat_template(B1.puzzle_prompt(p), tokenize=False, add_generation_prompt=True,
                                            enable_thinking=False)

    def generate(self, p, n: int, temp: float | None, model=None) -> list[str]:
        from transformers import LogitsProcessorList
        m = model or self.model
        ids = self.tok(self.prompt(p), return_tensors="pt").to(self.dev)
        cut = ids["input_ids"].shape[1]
        kw = {"do_sample": True, "temperature": temp, "top_p": 1.0, "num_return_sequences": n} if temp else \
             {"do_sample": False}
        with self.torch.no_grad():
            out = m.generate(**ids, max_new_tokens=32, pad_token_id=self.tok.eos_token_id,
                             logits_processor=LogitsProcessorList([RuleKeeper(self.tok, p["nums"], cut)]), **kw)
        return [self.tok.decode(o[cut:], skip_special_tokens=True).strip() for o in out]

    def answer(self, p, model=None) -> str:
        return self.generate(p, 1, None, model)[0]


def puzzles(seed, n):
    class A:
        pass
    a = A()
    a.seed, a.n, a.out = seed, n, None
    rng, out, seen = random.Random(seed), [], set()
    while len(out) < n:                                  # same recipe as claude_blurt1.make
        k = 3 if len(out) % 3 else 4
        nums = sorted(rng.randint(1, 9 if k == 3 else 13) for _ in range(k))
        target = 24 if k == 4 else rng.randint(5, 40)
        key = (tuple(nums), target)
        if key in seen:
            continue
        sol = B1.solve(nums, target)
        if sol is None:
            continue
        seen.add(key)
        out.append({"id": f"pz-s{seed}-{len(out) + 1:03d}", "nums": nums, "target": target})
    return out


def blurt(a):
    s = Solver(a.model)
    rows, tot = [], 0
    for p in [json.loads(x) for x in Path(a.puzzles).read_text().splitlines() if x]:
        bl = s.generate(p, a.n, a.temp)
        hits = [B1.check(t, p["nums"], p["target"]) for t in bl]
        greedy = s.answer(p)
        rows.append({"id": p["id"], "blurts": bl, "hits": hits, "greedy": greedy,
                     "greedy_hit": B1.check(greedy, p["nums"], p["target"])})
        tot += sum(hits)
        print(f"[blurt2] {p['id']} hits {sum(hits)}/{a.n} greedy {int(rows[-1]['greedy_hit'])}", flush=True)
    Path(a.out).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    print(f"puzzles {len(rows)}: lucky blurts {tot}/{len(rows) * a.n}, solved at least once "
          f"{sum(1 for r in rows if any(r['hits']))}/{len(rows)}, greedy right {sum(r['greedy_hit'] for r in rows)}")


def evaluate(s, ps, model=None) -> int:
    return sum(B1.check(s.answer(p, model), p["nums"], p["target"]) for p in ps)


def train_lora(s, examples, epochs, seed):
    import torch
    from peft import LoraConfig, get_peft_model
    torch.manual_seed(seed)
    from transformers import AutoModelForCausalLM
    base = AutoModelForCausalLM.from_pretrained(s.model.name_or_path, trust_remote_code=True,
                                                dtype=torch.bfloat16).to(s.dev)
    m = get_peft_model(base, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
                                        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]))
    opt = torch.optim.AdamW([p for p in m.parameters() if p.requires_grad], lr=2e-4)
    rng = random.Random(seed)
    m.train()
    for ep in range(epochs):
        rng.shuffle(examples)
        for i in range(0, len(examples), 8):
            batch = examples[i:i + 8]
            loss_tot = 0.0
            for p, expr in batch:
                pr = s.tok(s.prompt(p), return_tensors="pt")["input_ids"][0]
                an = s.tok(expr, add_special_tokens=False, return_tensors="pt")["input_ids"][0]
                ids = torch.cat([pr, an, torch.tensor([s.tok.eos_token_id])]).unsqueeze(0).to(s.dev)
                lab = ids.clone()
                lab[0, :len(pr)] = -100
                loss = m(input_ids=ids, labels=lab).loss / len(batch)
                loss.backward()
                loss_tot += float(loss.detach())
            opt.step()
            opt.zero_grad()
        print(f"[sleep] epoch {ep + 1}/{epochs} last batch loss {loss_tot:.3f}", flush=True)
    m.eval()
    return m


def pick_temp(s, a) -> tuple[float, dict]:
    """Registered DEV rule: on the DEV puzzles the reasoner misses, N blurts at each temperature; keep the temperature
    with the most lucky blurts (ties go to the first listed). Only DEV puzzles are used."""
    temps = [float(t) for t in a.temps.split(",")]
    if len(temps) == 1 or not a.dev_puzzles:
        return temps[0], {}
    dev = [json.loads(x) for x in Path(a.dev_puzzles).read_text().splitlines() if x]
    missed = [p for p in dev if not B1.check(s.answer(p), p["nums"], p["target"])]
    counts = {}
    for t in temps:
        counts[str(t)] = sum(B1.check(x, p["nums"], p["target"]) for p in missed for x in s.generate(p, a.n, t))
        print(f"[dev] T {t}: lucky blurts {counts[str(t)]}/{len(missed) * a.n} on {len(missed)} missed DEV puzzles",
              flush=True)
    best = max(temps, key=lambda t: (counts[str(t)], -temps.index(t)))
    return best, {"dev_missed": len(missed), "dev_lucky_by_temp": counts, "temp_chosen": best}


def loop(a):
    t0 = time.time()
    out = Path(a.out)
    (out / "wins").mkdir(parents=True, exist_ok=True)
    s = Solver(a.model)
    s.model.name_or_path = a.model
    temp, res = pick_temp(s, a)
    train, test = puzzles(a.train_seed, a.n_train), puzzles(a.test_seed, a.n_test)
    keys = {(tuple(p["nums"]), p["target"]) for p in train}
    if a.dev_puzzles:
        keys |= {(tuple(p["nums"]), p["target"]) for p in
                 (json.loads(x) for x in Path(a.dev_puzzles).read_text().splitlines() if x)}
    n0 = len(test)
    test = [p for p in test if (tuple(p["nums"]), p["target"]) not in keys]
    res.update({"n_train": len(train), "n_test": len(test), "test_dropped_overlap": n0 - len(test), "temp": temp})
    res["S0_test_before"] = evaluate(s, test)
    print(f"[loop] before: test {res['S0_test_before']}/{len(test)}", flush=True)
    own, wins, recs, lucky, tried = [], [], [], 0, 0
    for p in train:
        g = s.answer(p)
        if B1.check(g, p["nums"], p["target"]):
            own.append((p, g))
            continue
        bl = s.generate(p, a.n, temp)
        hits = [t for t in bl if B1.check(t, p["nums"], p["target"])]
        lucky, tried = lucky + len(hits), tried + len(bl)
        if hits:
            wins.append((p, hits[0]))
            recs.append({"problem": f"Use each of {p['nums']} once with + - * / and brackets to make {p['target']}",
                         "rows_used": [], "steps": [hits[0]], "answer": hits[0], "checked_by": "exact-checker",
                         "turn_id": p["id"], "source": "creative-blurt", "tries": bl.index(hits[0]) + 1})
    (out / "wins" / "wins.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs), encoding="utf-8")
    res.update({"train_reasoner_right": len(own), "train_missed": len(train) - len(own),
                "train_missed_then_lucky": len(wins), "lucky_blurts_on_misses": lucky, "blurts_on_misses": tried})
    print(f"[loop] practice: reasoner right {len(own)}/{len(train)}, lucky wins on misses {len(wins)} "
          f"({lucky}/{tried} blurts)", flush=True)
    ex_w = own + wins
    ex_c = (own * (len(ex_w) // max(1, len(own)) + 1))[:len(ex_w)] if own else []
    res["examples_W"], res["examples_C"] = len(ex_w), len(ex_c)
    seeds = [int(x) for x in a.lora_seeds.split(",")]
    for arm, ex in (("W", ex_w), ("C", ex_c)):
        for sd in seeds:
            k = f"{arm}_seed{sd}"
            if not ex:
                res[f"S_{k}_test_after"] = None
                continue
            m = train_lora(s, list(ex), a.epochs, sd)
            res[f"S_{k}_test_after"] = evaluate(s, test, m)
            res[f"S_{k}_train_missed_after"] = sum(B1.check(s.answer(p, m), p["nums"], p["target"]) for p, _ in wins)
            print(f"[loop] arm {arm} seed {sd}: test {res[f'S_{k}_test_after']}/{len(test)}", flush=True)
            del m
            if s.dev == "cuda":
                s.torch.cuda.empty_cache()
        vals = [res.get(f"S_{arm}_seed{sd}_test_after") for sd in seeds]
        res[f"S_{arm}_test_after_mean"] = None if None in vals else round(sum(vals) / len(vals), 2)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "loop_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["blurt", "loop"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--puzzles", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--temp", type=float, default=1.0)
    ap.add_argument("--train-seed", type=int, default=2)
    ap.add_argument("--n-train", type=int, default=400)
    ap.add_argument("--test-seed", type=int, default=777)
    ap.add_argument("--n-test", type=int, default=150)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lora-seeds", default="0,1")
    ap.add_argument("--temps", default="1.0")
    ap.add_argument("--dev-puzzles", default="")
    a = ap.parse_args()
    {"blurt": blurt, "loop": loop}[a.cmd](a)


if __name__ == "__main__":
    main()
