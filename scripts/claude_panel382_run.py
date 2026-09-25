#!/usr/bin/env python3
"""382 panel runner: chatpanel382 and creativepanel382 (design/v3/30-modes/382-panels-spec.md) on any arm.
New file only; never prints panel text. Month-end line, 2026-09-25.

Arms: --arm module:function (a builder(state_dir, args), e.g. claude_e2e382:build_382 or claude_e2e360:build_360)
or --arm twin (the plain MiniCPM5-1B, whole chat; run under scripts/claude_twinb_wrap.py so thinking is off).
Each conversation or item gets a fresh agent; its turns go in order (no sleeps, no restarts).
  chat:     every turn of `turns` is sent; one row per turn.
  creative: every turn of `turns`, then `last`; one row per message, the reply to `last` marked last=true.
Output: <out>/<panel>_<name>.jsonl rows {item_id, turn_i, kind, last, reply, ms, events, ep382 (stats delta)}.

--score DIR --names E,T,G (first name = the arm under test) writes, from the rows and the panel:
  summary.json   per arm: think turns with the gold number in the reply; ask_known right; ask_unknown "don't
                 know"; notebook events on non-teach turns; puzzles solved (script: an expression in the reply
                 uses each given number once and equals the target); distinct and most common replies; ms.
  judge packets  chat_pair_<other>.jsonl (+ chat_key_<other>.json): per conversation, the tested arm and one
                 other, order shuffled (seed 3821); chat_turns_<first>.jsonl for the per-turn judge;
                 creative_<name>.jsonl (+ creative_key.json): every idea/uses_facts reply of every arm, shuffled
                 together (seed 3822) under neutral ids, for one blind usefulness and made-up-fact judge;
                 grammar_<first>.jsonl: the tested arm's distinct replies.

  python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel chat --panel-dir DIR \
      --arm claude_e2e382:build_382 --name E --model <reader dir> --gen-model <MiniCPM5-1B dir> --out OUT
  python -B scripts/claude_panel382_run.py --panel chat --panel-dir DIR --score OUT --names E,T,G
"""
from __future__ import annotations

import argparse
import ast
import importlib
import json
import operator
import os
import random
import re
import shutil
import statistics
import sys
import tempfile
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
if os.name == "nt":
    sys.path.insert(0, str(Path(__file__).resolve().parent / "winshim"))


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def messages(panel: str, it: dict):
    """(turn_i, kind, text, is_last) for every message the arm receives."""
    if panel == "chat":
        return [(i, t["kind"], t["text"], False) for i, t in enumerate(it["turns"])]
    lead = [(i, "lead", t if isinstance(t, str) else t.get("text", ""), False) for i, t in enumerate(it["turns"])]
    return lead + [(len(lead), it["kind"], it["last"], True)]


def make_agent(a, tmp):
    if a.arm == "twin":
        import claude_e2e336_twin as TW
        return TW.Twin336(tmp, a.gen_model)
    mod, fn = a.arm.split(":")
    return getattr(importlib.import_module(mod), fn)(tmp, a)


def run(a):
    import claude_e2e336_run as R
    items = load(Path(a.panel_dir) / "items.jsonl")
    rows = []
    for it in items:
        tmp = tempfile.mkdtemp(prefix=f"p382-{a.name}-")
        try:
            agent = make_agent(a, tmp)
            for ti, kind, text, is_last in messages(a.panel, it):
                s0 = dict(getattr(agent, "ep382_stats", {}) or {})
                reply, ms, new = R.one(agent, text)
                row = {"item_id": it["item_id"], "turn_i": ti, "kind": kind, "last": is_last, "reply": reply,
                       "ms": round(ms, 1), "events": len(new)}
                s1 = getattr(agent, "ep382_stats", None)
                if s1:
                    row["ep382"] = {k: s1[k] - s0.get(k, 0) for k in s1 if s1[k] - s0.get(k, 0)}
                rows.append(row)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        print(f"[382/{a.panel}/{a.name}] {it['item_id']}", flush=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{a.panel}_{a.name}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


# ------------------------------------------------------------------ scoring
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return Fraction(node.value), [node.value]
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        lv, ln = _eval(node.left)
        rv, rn = _eval(node.right)
        if isinstance(node.op, ast.Div) and rv == 0:
            raise ZeroDivisionError
        return _OPS[type(node.op)](lv, rv), ln + rn
    raise ValueError("not arithmetic")


EXPR = re.compile(r"[0-9()+\-*/ .]{5,}")


def puzzle_solved(reply: str, numbers: list[int], target: int) -> bool:
    """True if some arithmetic expression in the reply uses each given number exactly once and equals target."""
    t = reply.replace("×", "*").replace("x", "*").replace("X", "*").replace("÷", "/").replace("−", "-")
    for part in re.split(r"[=\n]", t):
        for m in EXPR.finditer(part):
            s = m.group(0).strip().strip(".").strip()
            try:
                val, used = _eval(ast.parse(s, mode="eval"))
            except (SyntaxError, ValueError, ZeroDivisionError, RecursionError):
                continue
            if val == target and Counter(used) == Counter(numbers):
                return True
    return False


def _vmatch(text, value):
    v = str(value).strip().lower()
    return bool(v) and re.search(r"(?<![a-z0-9])" + re.escape(v) + r"(?![a-z0-9])", text.lower()) is not None


def _num_in(reply: str, gold) -> bool:
    try:
        g = Fraction(str(gold))
    except (ValueError, ZeroDivisionError):
        return False
    for tok in re.findall(r"-?\d[\d,]*(?:\.\d+)?", reply):
        try:
            if Fraction(tok.replace(",", "")) == g:
                return True
        except (ValueError, ZeroDivisionError):
            continue
    return False


def score(a):
    import claude_e2e336_score as S
    items = {it["item_id"]: it for it in load(Path(a.panel_dir) / "items.jsonl")}
    d = Path(a.score)
    names = a.names.split(",")
    arms = {x: load(d / f"{a.panel}_{x}.jsonl") for x in names if (d / f"{a.panel}_{x}.jsonl").exists()}
    summ = {"panel": a.panel, "items": len(items)}
    for x, rows in arms.items():
        ms = [r["ms"] for r in rows]
        s = {"messages": len(rows), "distinct_replies": len({r["reply"] for r in rows}),
             "most_common_reply_count": max(Counter(r["reply"] for r in rows).values() or [0]),
             "events_on_non_teach": sum(r["events"] for r in rows if r["kind"] not in ("teach", "lead")),
             "ms_median": round(statistics.median(ms), 1) if ms else None}
        if a.panel == "chat":
            turn = lambda r: items[r["item_id"]]["turns"][r["turn_i"]]  # noqa: E731
            think_num = [r for r in rows if r["kind"] == "think" and turn(r).get("gold_number") is not None]
            known = [r for r in rows if r["kind"] == "ask_known"]
            unknown = [r for r in rows if r["kind"] == "ask_unknown"]
            s.update(think_numeric=len(think_num),
                     think_numeric_right=sum(_num_in(r["reply"], turn(r)["gold_number"]) for r in think_num),
                     think_turns=sum(1 for r in rows if r["kind"] == "think"),
                     ask_known=len(known),
                     ask_known_right=sum(_vmatch(r["reply"], turn(r)["gold"]) for r in known),
                     ask_unknown=len(unknown),
                     ask_unknown_dont_know=sum(S.has(r["reply"].lower(), S.ABSTAIN_MARKERS) for r in unknown))
        else:
            puz = [r for r in rows if r["last"] and r["kind"] == "puzzle"]
            s.update(puzzles=len(puz), puzzles_solved=sum(
                puzzle_solved(r["reply"], items[r["item_id"]]["numbers"], items[r["item_id"]]["target"])
                for r in puz))
        summ[x] = s

    first = names[0]
    if first in arms and a.panel == "chat":
        def convo(x, iid):
            return [{"user": items[iid]["turns"][r["turn_i"]]["text"], "assistant": r["reply"]}
                    for r in arms[x] if r["item_id"] == iid]
        for other in names[1:]:
            if other not in arms:
                continue
            rng = random.Random(3821)
            packets, key = [], {}
            for iid in sorted(items):
                pair = [(first, convo(first, iid)), (other, convo(other, iid))]
                rng.shuffle(pair)
                key[iid] = [pair[0][0], pair[1][0]]
                packets.append({"item_id": iid, "conversation_1": pair[0][1], "conversation_2": pair[1][1]})
            (d / f"chat_pair_{other}.jsonl").write_text(
                "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in packets), encoding="utf-8")
            (d / f"chat_key_{other}.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
        (d / f"chat_turns_{first}.jsonl").write_text("".join(
            json.dumps({"item_id": iid, "conversation": convo(first, iid)}, ensure_ascii=False) + "\n"
            for iid in sorted(items)), encoding="utf-8")
    if a.panel == "creative":
        pool = []
        for x, rows in arms.items():
            for r in rows:
                it = items[r["item_id"]]
                if r["last"] and it["kind"] in ("idea", "uses_facts"):
                    lead = [t if isinstance(t, str) else t.get("text", "") for t in it["turns"]]
                    pool.append((x, r["item_id"], {"chat": lead, "request": it["last"], "reply": r["reply"]}))
        random.Random(3822).shuffle(pool)
        key = {}
        with open(d / "creative_judge.jsonl", "w", encoding="utf-8") as fh:
            for n, (x, iid, body) in enumerate(pool):
                cid = f"K{n:04d}"
                key[cid] = {"arm": x, "item_id": iid}
                fh.write(json.dumps(dict(id=cid, **body), ensure_ascii=False) + "\n")
        (d / "creative_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    if first in arms:
        (d / f"grammar_{a.panel}_{first}.jsonl").write_text("".join(
            json.dumps({"reply": x}, ensure_ascii=False) + "\n"
            for x in sorted({r["reply"] for r in arms[first] if r["reply"]})), encoding="utf-8")
    (d / f"summary_{a.panel}.json").write_text(json.dumps(summ, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps(summ, sort_keys=True))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True, choices=["chat", "creative"])
    ap.add_argument("--panel-dir", required=True)
    ap.add_argument("--arm", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--model", default="", help="reader dir (agent arms)")
    ap.add_argument("--gen-model", default="", help="base MiniCPM5-1B dir")
    ap.add_argument("--mouth-model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--score", default="")
    ap.add_argument("--names", default="E,T,G")
    a = ap.parse_args()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    if a.score:
        score(a)
        return
    if not (a.arm and a.name and a.out and a.gen_model):
        raise SystemExit("382: --arm, --name, --out and --gen-model are required to run")
    run(a)


if __name__ == "__main__":
    main()
