#!/usr/bin/env python3
"""rt-02g: the 1B reads the chat puzzle instead of fixed rules (Plain-English puzzles thread, 2026-09-26). New file only.

Marks: artifacts/claude-rt02g-20260926/PASSMARKS-rt02g.md (written before this code). Blind TEST-ONLY panel:
artifacts/claude-panel-rt02g-20260926 (only `run` and `score` read it; never opened, printed or quoted otherwise).

One change on rt-02d's route: whether a turn is a number puzzle, and which number is the target, is decided by the
plain 1B (every LoRA scale at 0 while it reads) instead of rt-02d's target-word and operator rules. The 1B reads the
turn with a fixed few-shot prompt and writes "numbers: a, b, c; target: t" or "none". Code accepts a reading only if
it is well formed, has 3 or 4 numbers in 1-13 and a target in 1-100, and the numbers plus the target are exactly the
whole numbers in the message (as a multiset). The 1B is only asked when the message has 4 or 5 whole numbers (the same
first condition as rt-02d), so turns without that many numbers never reach it. Everything after the reading is
rt-02d's: claude_rt02d.solve_route (greedy, then 20 sampled at T 1.5, per-puzzle seed, exact checker) and
claude_rt02d.reply_for. Nothing is trained; nothing is written to the notebook.

Arms (route level; see PASSMARKS for why no full-agent reply is generated):
  G     = this reader, route solves with the 0.2c adapter on
  Goff  = this reader, route solves with every LoRA scale at 0 (sleep check)
  D     = rt-02d's rule parser, route solves with the adapter on (the rule baseline on the same panel)

  python -B scripts/claude_rt02g.py --selftest
  python -B scripts/claude_rt02g.py dev --model BASE [--out FILE]              (dev + practice sets; reads only)
  SLEEP02C_ADAPTER=adapter02c.pt python -B scripts/claude_rt02g.py run --arm G|Goff|D --task puzzles|negatives \
      --model BASE --panel-dir PD --out OUT
  python -B scripts/claude_rt02g.py score --out OUT --panel-dir PD --score SCOREDIR
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

TURN_SEED = 402_027                     # rt-02d's per-turn seed, set before every turn in every arm
READ_MAX_NEW = 24
_INT = re.compile(r"(?<![\d.])\d+(?!\d|\.\d)")          # rt-02d's whole-number pattern
_READ = re.compile(r"numbers?\s*:\s*([\d\s,]+?)\s*;\s*target\s*:\s*(\d+)", re.I)

READ_ASK = ("Message: {text}\n\nIs this message asking for a way to combine the given numbers with + - * / to reach "
            "a target number? If yes, reply exactly \"numbers: <the numbers to combine>; target: <the target>\". "
            "If not, reply exactly \"none\".")
FEW_SHOT = [
    ("Can you get 10 out of 2, 3 and 4? Each one used once.", "numbers: 2, 3, 4; target: 10"),
    ("My sister has 3 cats, 2 dogs and 1 rabbit, 6 pets in all.", "none"),
    ("Is 5 * 4 + 2 equal to 22?", "none"),
    ("24 using 1 5 5 6 please", "numbers: 1, 5, 5, 6; target: 24"),
    ("I solved it myself: (9 - 3) * 2 = 12!", "none"),
    ("What is 7 + 8 + 2 + 1?", "none"),
]


def message_ints(text: str) -> list[int]:
    return [int(m.group(0)) for m in _INT.finditer((text or "").replace("−", "-"))]


def pre_gate(text: str) -> bool:
    return 4 <= len(message_ints(text)) <= 5


def accept(text: str, out: str):
    """Code check of the 1B's reading: {'nums': sorted, 'target': t} or None."""
    m = _READ.search(out or "")
    if not m:
        return None
    nums = [int(x) for x in re.findall(r"\d+", m.group(1))]
    target = int(m.group(2))
    if len(nums) not in (3, 4) or not all(1 <= v <= 13 for v in nums) or not 1 <= target <= 100:
        return None
    if Counter(nums + [target]) != Counter(message_ints(text)):
        return None
    return {"nums": sorted(nums), "target": target}


def read_messages(text: str) -> list[dict]:
    msgs = []
    for q, a in FEW_SHOT:
        msgs += [{"role": "user", "content": READ_ASK.format(text=q)}, {"role": "assistant", "content": a}]
    return msgs + [{"role": "user", "content": READ_ASK.format(text=text)}]


def read_raw(one_b, text: str) -> str:
    """Greedy reading by the plain 1B (every LoRA scale 0 during the call, restored after)."""
    import claude_sleep02c as SL
    tok, model, torch = one_b.tok, one_b.model, one_b.torch
    mods = SL.lora_mods(model)
    saved = [x.scale for x in mods]
    for x in mods:
        x.scale = 0.0
    try:
        prompt = tok.apply_chat_template(read_messages(text), tokenize=False, add_generation_prompt=True,
                                         enable_thinking=False)
        ids = tok(prompt, return_tensors="pt").to(one_b.dev)
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=READ_MAX_NEW, do_sample=False,
                                 pad_token_id=tok.eos_token_id)
        return tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    finally:
        for x, sc in zip(mods, saved):
            x.scale = sc


def read_puzzle(one_b, text: str):
    if not pre_gate(text):
        return None, None
    raw = read_raw(one_b, text)
    return accept(text, raw), raw


# ------------------------------------------------------------------ model
def load_one_b(base: str):
    import claude_cre333b_agent as C333B
    import claude_sleep02c as SL
    one_b = C333B.Gen333b(base)
    SL.install_sleep02c(one_b)            # LoRA added (identity); SLEEP02C_ADAPTER loaded if set (sidecar-checked)
    return one_b


# ------------------------------------------------------------------ runner (route level)
def _load(p: Path):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def run(a) -> None:
    import claude_rt02d as RT
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    import torch
    torch.use_deterministic_algorithms(True, warn_only=True)
    if a.arm in ("G", "D") and not os.environ.get("SLEEP02C_ADAPTER"):
        raise SystemExit("rt02g: arms G and D need SLEEP02C_ADAPTER")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{a.task}_{a.arm}.jsonl"
    if path.exists():
        raise SystemExit(f"rt02g: {path} exists (each run is launched once)")
    fname = {"puzzles": "chat_puzzles.jsonl", "negatives": "negatives.jsonl"}[a.task]
    items = _load(Path(a.panel_dir) / fname)
    one_b = load_one_b(a.model)
    rows = []
    for it in items:
        torch.manual_seed(TURN_SEED)
        t0 = time.time()
        if a.arm == "D":
            p, raw = RT.parse_puzzle(it["text"]), None
        else:
            p, raw = read_puzzle(one_b, it["text"])
        res = RT.solve_route(one_b, p, lora_off=(a.arm == "Goff")) if p is not None else None
        reply = RT.reply_for(p, res) if p is not None else ""
        rows.append({"id": it["id"], "routed": p is not None, "parsed": p, "raw": raw, "route": res,
                     "reply": reply, "ms": round((time.time() - t0) * 1000, 1)})
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({"task": a.task, "arm": a.arm, "rows": len(rows), "routed": sum(r["routed"] for r in rows)}),
          flush=True)


# ------------------------------------------------------------------ score (counts only; never prints panel text)
def score(a) -> None:
    import claude_blurt1 as B1
    import claude_dl1_nights as D1
    import claude_panel382_run as P
    out, pd = Path(a.out), Path(a.panel_dir)
    truth = {r["id"]: r for r in _load(pd / "chat_puzzles.jsonl")}
    res: dict = {"solved": {}, "exact_reads": {}, "routed": {}, "wrong_puzzle": {}, "dishonest": {},
                 "fires_negatives": {}}
    for arm in ("G", "Goff", "D"):
        f = out / f"puzzles_{arm}.jsonl"
        if f.exists():
            rows = _load(f)
            res["routed"][arm] = sum(int(r["routed"]) for r in rows)
            res["solved"][arm] = sum(int(P.puzzle_solved(r["reply"], truth[r["id"]]["nums"], truth[r["id"]]["target"]))
                                     for r in rows)
            want = {i: {"nums": sorted(t["nums"]), "target": t["target"]} for i, t in truth.items()}
            res["exact_reads"][arm] = sum(int(r["parsed"] == want[r["id"]]) for r in rows)
            res["wrong_puzzle"][arm] = sum(int(r["routed"] and r["parsed"] != want[r["id"]]) for r in rows)
            res["dishonest"][arm] = sum(int(bool(r["routed"] and r["route"] and r["route"].get("expr")
                                                 and not B1.check(r["route"]["expr"], r["parsed"]["nums"],
                                                                  r["parsed"]["target"])))
                                        for r in rows)
        f = out / f"negatives_{arm}.jsonl"
        if f.exists():
            res["fires_negatives"][arm] = sum(int(r["routed"]) for r in _load(f))
    res["general_items_reaching_reader"] = sum(int(pre_gate(it["q"])) for it in D1.harm_panel())
    s, e, n = res["solved"], res["exact_reads"], res["fires_negatives"]
    have = all(k in s for k in ("G", "Goff", "D")) and "G" in n
    res["marks"] = {} if not have else {
        "G1": e["G"] >= 85 and e["G"] >= e["D"] - 2,
        "G2": n["G"] <= 2,
        "G3": s["G"] >= 8 and s["G"] >= s["D"] - 3,
        "G4": s["G"] - s["Goff"] >= 4,
        "G5": res["dishonest"]["G"] == 0 and res["dishonest"]["Goff"] == 0 and res["wrong_puzzle"]["G"] <= 2}
    res["pass"] = bool(res["marks"]) and all(res["marks"].values())
    res["prefer_over_rules"] = res["pass"] and "D" in n and n["G"] <= n["D"]
    sd = Path(a.score)
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "rt02g_score.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("solved", "exact_reads", "fires_negatives", "marks", "pass",
                                          "prefer_over_rules")}))


# ------------------------------------------------------------------ dev (dev + practice data only; reads, no solving)
def dev_sets() -> list[tuple[str, str, dict | None]]:
    import claude_blurt2 as B2
    import claude_rt02d as RT
    out = [("dev", t, w) for t, w in RT.dev_cases()]
    prac = json.loads((SCRIPTS.parent / "artifacts/claude-rt02e-20260926/practice/wordings_practice.json").read_text())
    ps = B2.puzzles(4881, 3 * len(prac["puzzle_templates"]))
    fmts = [lambda o: ", ".join(map(str, o[:-1])) + " and " + str(o[-1]), lambda o: " ".join(map(str, o)),
            lambda o: ", ".join(map(str, o))]
    for wi, t in enumerate(prac["puzzle_templates"]):
        for k in range(3):
            p = ps[3 * wi + k]
            o = list(p["nums"])[::-1] if k % 2 else list(p["nums"])
            out.append(("practice", t.replace("{L}", fmts[k](o)).replace("{T}", str(p["target"])),
                        {"nums": sorted(p["nums"]), "target": p["target"]}))
    out += [("practice", n, None) for n in prac["negatives"]]
    return out


def dev(a) -> None:
    import claude_rt02d as RT
    one_b = load_one_b(a.model)
    stats = Counter()
    rows = []
    t0 = time.time()
    for src, text, want in dev_sets():
        got, raw = read_puzzle(one_b, text)
        rule = RT.parse_puzzle(text)
        kind = "puzzle" if want else "negative"
        stats[f"{src}_{kind}"] += 1
        stats[f"{src}_{kind}_reader_{'exact' if want and got == want else 'fire' if got else 'none'}"] += 1
        stats[f"{src}_{kind}_rules_{'exact' if want and rule == want else 'fire' if rule else 'none'}"] += 1
        rows.append({"src": src, "kind": kind, "text": text, "want": want, "got": got, "raw": raw, "rule": rule})
    stats["seconds"] = round(time.time() - t0)
    if a.out:
        Path(a.out).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps(dict(sorted(stats.items()))))


# ------------------------------------------------------------------ selftest (no model)
def selftest() -> None:
    n = 0
    t = "Use 3, 4, 6 and 8 to make 24."
    assert accept(t, "numbers: 3, 4, 6, 8; target: 24") == {"nums": [3, 4, 6, 8], "target": 24}; n += 1
    assert accept(t, "numbers: 3, 4, 6; target: 8") is None; n += 1            # leaves 24 out of the reading
    assert accept(t, "numbers: 3, 4, 6, 24; target: 8") is None; n += 1        # 24 is not a puzzle number
    assert accept(t, "none") is None; n += 1
    assert accept("Make 12 from 2, 3 and 6", "Numbers: 6, 2, 3 ; Target: 12") == {"nums": [2, 3, 6], "target": 12}; n += 1
    assert accept("Make 12 from 2, 3 and 6", "numbers: 2, 3, 6, 6; target: 12") is None; n += 1   # invented a 6
    assert not pre_gate("What is the capital of France? Reply with the city name only."); n += 1
    assert pre_gate(t); n += 1
    import claude_dl1_nights as D1
    assert sum(pre_gate(it["q"]) for it in D1.harm_panel()) == 0; n += 1       # general items never reach the 1B
    msgs = read_messages("hi")
    assert len(msgs) == 2 * len(FEW_SHOT) + 1 and msgs[-1]["role"] == "user"; n += 1
    for q, ans in FEW_SHOT:                                                     # the examples obey the code check
        assert (accept(q, ans) is not None) == (ans != "none"), q
    n += 1
    print(f"rt02g selftest {n}/{n}")


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        selftest()
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "score", "dev"])
    ap.add_argument("--arm", default="")
    ap.add_argument("--task", default="puzzles")
    ap.add_argument("--model", default="")
    ap.add_argument("--panel-dir", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--score", default="")
    a = ap.parse_args()
    {"run": run, "score": score, "dev": dev}[a.cmd](a)


if __name__ == "__main__":
    main()
