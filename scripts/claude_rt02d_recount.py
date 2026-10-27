#!/usr/bin/env python3
"""rt-02d independent recount (Plain-English puzzles thread, 2026-09-26). New file only; counts only.

Recounts R1-R5 of artifacts/claude-rt02d-20260926/PASSMARKS-rt02d.md from the raw run files, WITHOUT importing
claude_rt02d, claude_panel382_run or claude_blurt1 (own expression reader and evaluator), so a bug in the sealed
scorer shows up as a disagreement. Never prints a reply, a puzzle or a negative: only integer counts and ids of
disagreeing rows.

  strict  = the registered scorer's rule, re-implemented: split the reply on "=" and newlines; in each part, each
            maximal run of digits, brackets, spaces, dots and + - * / (x, X, ×, ÷, − mapped first) of length >= 5,
            stripped of dots and spaces, is one candidate; solved if a candidate uses the puzzle's numbers exactly
            (as a multiset) and equals the target.
  lenient = REPORT ONLY (the Mac agent's finding: the scorer misses Markdown and LaTeX): markup removed first
            (**, __, `, $, \\( \\), \\[ \\], \\times, \\cdot, \\div, \\left, \\right, \\frac{a}{b}), then every
            contiguous sub-span of each run is tried.

  python -B scripts/claude_rt02d_recount.py --out artifacts/claude-rt02d-20260926/run \
      --panel-dir artifacts/claude-panel-rt02d-20260926 [--official artifacts/claude-rt02d-20260926/score/rt02d_score.json]
  python -B scripts/claude_rt02d_recount.py --selftest
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from fractions import Fraction
from pathlib import Path

_MAP = {"×": "*", "x": "*", "X": "*", "÷": "/", "−": "-"}
_RUN = re.compile(r"[0-9()+\-*/ .]{5,}")


# ------------------------------------------------------------------ own arithmetic reader (no eval, no ast)
def _tokens(s: str):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c.isspace():
            i += 1
        elif c.isdigit():
            j = i
            while j < len(s) and s[j].isdigit():
                j += 1
            if j < len(s) and s[j] == ".":          # decimals are not puzzle numbers
                raise ValueError("decimal")
            out.append(("n", int(s[i:j])))
            i = j
        elif c in "+-*/()":
            out.append(("o", c))
            i += 1
        else:
            raise ValueError("char")
    return out


def evaluate(s: str):
    """(value as Fraction, list of number literals) for + - * / ( ) with unary minus; raises ValueError."""
    toks = _tokens(s)
    pos = [0]
    used: list[int] = []

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else (None, None)

    def take():
        if pos[0] >= len(toks):
            raise ValueError("end")
        pos[0] += 1
        return toks[pos[0] - 1]

    def expr():
        v = term()
        while peek() in (("o", "+"), ("o", "-")):
            op = take()[1]
            r = term()
            v = v + r if op == "+" else v - r
        return v

    def term():
        v = factor()
        while peek() in (("o", "*"), ("o", "/")):
            op = take()[1]
            r = factor()
            if op == "/":
                if r == 0:
                    raise ValueError("div0")
                v = v / r
            else:
                v = v * r
        return v

    def factor():
        k, t = peek()
        if (k, t) == ("o", "-"):
            take()
            return -factor()
        if (k, t) == ("o", "+"):
            take()
            return factor()
        if (k, t) == ("o", "("):
            take()
            v = expr()
            if take() != ("o", ")"):
                raise ValueError("paren")
            return v
        if k == "n":
            take()
            used.append(t)
            return Fraction(t)
        raise ValueError("syntax")

    if not toks:
        raise ValueError("empty")
    v = expr()
    if pos[0] != len(toks):
        raise ValueError("trailing")
    return v, used


def _ok(cand: str, nums, target) -> bool:
    try:
        v, used = evaluate(cand)
    except (ValueError, IndexError, RecursionError):
        return False
    return v == target and Counter(used) == Counter(nums)


def solved_strict(reply: str, nums, target) -> bool:
    t = reply
    for a, b in _MAP.items():
        t = t.replace(a, b)
    for part in re.split(r"[=\n]", t):
        for m in _RUN.finditer(part):
            if _ok(m.group(0).strip().strip(".").strip(), nums, target):
                return True
    return False


_LATEX = [(r"\\left|\\right", ""), (r"\\times|\\cdot|\\ast", "*"), (r"\\div", "/"), (r"\\\(|\\\)|\\\[|\\\]", " "),
          (r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"((\1)/(\2))"), (r"\*\*|__|`|\$", " "), (r"[{}]", " ")]


def solved_lenient(reply: str, nums, target) -> bool:
    t = reply
    for pat, rep in _LATEX:
        t = re.sub(pat, rep, t)
    for a, b in _MAP.items():
        t = t.replace(a, b)
    for part in re.split(r"[=\n]", t):
        for m in _RUN.finditer(part):
            run = m.group(0)
            for i in range(len(run)):
                for j in range(len(run), i + 2, -1):
                    if _ok(run[i:j].strip().strip(".").strip(), nums, target):
                        return True
    return False


# ------------------------------------------------------------------ recount
def _load(p: Path):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else None


def recount(out: Path, panel_dir: Path) -> dict:
    truth = {r["id"]: r for r in _load(panel_dir / "chat_puzzles.jsonl")}
    res: dict = {"solved_strict": {}, "solved_lenient": {}, "rows": {}, "routed": {}}
    for name in ("B0", "B1", "B1off"):
        rows = _load(out / f"puzzles_{name}.jsonl")
        if rows is None:
            continue
        ids = [r["id"] for r in rows]
        res["rows"][name] = len(rows)
        res.setdefault("id_problems", {})[name] = {
            "missing": len(set(truth) - set(ids)), "extra": len(set(ids) - set(truth)),
            "dupes": len(ids) - len(set(ids))}
        res["routed"][name] = sum(int(bool(r.get("routed"))) for r in rows)
        s = [r["id"] for r in rows if solved_strict(r["reply"], truth[r["id"]]["nums"], truth[r["id"]]["target"])]
        ln = [r["id"] for r in rows if solved_lenient(r["reply"], truth[r["id"]]["nums"], truth[r["id"]]["target"])]
        res["solved_strict"][name] = len(s)
        res["solved_lenient"][name] = len(ln)
        res.setdefault("_ids", {})[name] = sorted(s)
    b1 = _load(out / "puzzles_B1.jsonl") or []
    res["dishonest"] = sum(1 for r in b1 if r.get("routed") and (r.get("route") or {}).get("expr")
                           and not _ok(r["route"]["expr"], truth[r["id"]]["nums"], truth[r["id"]]["target"]))
    res["routed_but_unsolved_B1"] = sum(1 for r in b1 if r.get("routed")
                                        and not (r.get("route") or {}).get("expr"))
    neg = _load(out / "negatives_B1.jsonl")
    res["fires_negatives"] = None if neg is None else sum(int(bool(r.get("routed"))) for r in neg)
    res["negatives_rows"] = None if neg is None else len(neg)
    nh = {}
    for task in ("general", "chatdev"):
        b0, b1t = _load(out / f"{task}_B0.jsonl"), _load(out / f"{task}_B1.jsonl")
        if b0 is None or b1t is None:
            nh[task] = None
            continue
        k0 = {(r["id"], r["turn_i"]): r["reply"] for r in b0}
        nh[task] = {"turns_B0": len(b0), "turns_B1": len(b1t),
                    "fired": sum(int(bool(r.get("routed"))) for r in b1t),
                    "differ_unrouted": sum(1 for r in b1t if not r.get("routed")
                                           and k0.get((r["id"], r["turn_i"])) != r["reply"]),
                    "b0_fired": sum(int(bool(r.get("routed"))) for r in b0)}
    res["no_harm"] = nh
    s = res["solved_strict"]
    g, c = nh.get("general"), nh.get("chatdev")
    res["marks"] = {
        "R1": None if "B1" not in s or "B0" not in s else (s["B1"] >= 8 and s["B1"] - s["B0"] >= 6),
        "R2": None if "B1" not in s or "B1off" not in s else (s["B1"] - s["B1off"] >= 4),
        "R3": None if res["fires_negatives"] is None else res["fires_negatives"] <= 2,
        "R4": None if g is None or c is None else (g["fired"] <= 3 and g["differ_unrouted"] == 0
                                                   and c["differ_unrouted"] == 0),
        "R5": None if not b1 else res["dishonest"] == 0}
    res["pass"] = all(v is True for v in res["marks"].values())
    return res


def compare(res: dict, official: dict) -> list[str]:
    diffs = []
    for k, v in (official.get("solved") or {}).items():
        if res["solved_strict"].get(k) != v:
            diffs.append(f"solved {k}: official {v} recount {res['solved_strict'].get(k)}")
    if official.get("fires_negatives") != res["fires_negatives"]:
        diffs.append(f"fires_negatives: official {official.get('fires_negatives')} recount {res['fires_negatives']}")
    if official.get("dishonest") != res["dishonest"]:
        diffs.append(f"dishonest: official {official.get('dishonest')} recount {res['dishonest']}")
    for task in ("general", "chatdev"):
        o, r = (official.get("no_harm") or {}).get(task), res["no_harm"].get(task)
        if (o is None) != (r is None) or (o and r and (o["fired"], o["differ_unrouted"]) != (r["fired"], r["differ_unrouted"])):
            diffs.append(f"no_harm {task}: official {o} recount {r and {k: r[k] for k in ('fired', 'differ_unrouted')}}")
    for m, v in (official.get("marks") or {}).items():
        if res["marks"].get(m) != v:
            diffs.append(f"mark {m}: official {v} recount {res['marks'].get(m)}")
    return diffs


# ------------------------------------------------------------------ selftest (synthetic rows only)
def selftest() -> None:
    import tempfile
    n = 0
    assert evaluate("6/(1-3/4)")[0] == 24; n += 1
    assert evaluate("-(2-5)*8")[0] == 24; n += 1
    for bad in ("3..4", "(1+2", "1+", "2 3", "1.5*16"):
        try:
            evaluate(bad)
            raise AssertionError(bad)
        except ValueError:
            pass
    n += 1
    assert solved_strict("Here's one way that works: (8 - 2) * 4 = 24.", [2, 4, 8], 24); n += 1
    assert solved_strict("Try 6 / (1 - 3/4) = 24", [1, 3, 4, 6], 24); n += 1
    assert solved_strict("(13 - 1) × 2 = 24", [1, 2, 13], 24); n += 1
    assert not solved_strict("**(8 - 2) * 4** = 24", [2, 4, 8], 24); n += 1           # the scorer's known miss
    assert solved_lenient("**(8 - 2) * 4** = 24", [2, 4, 8], 24); n += 1
    assert not solved_strict("\\( (8-2) \\times 4 = 24 \\)", [2, 4, 8], 24); n += 1
    assert solved_lenient("\\( (8-2) \\times 4 = 24 \\)", [2, 4, 8], 24); n += 1
    assert solved_lenient("$\\frac{6}{1-3/4} = 24$", [1, 3, 4, 6], 24); n += 1
    assert not solved_strict("(8 - 2) * 4 = 24", [2, 4, 8, 8], 24); n += 1              # a number unused
    assert not solved_strict("(8 - 2) * 4 = 25", [2, 4, 8], 25); n += 1                 # wrong value
    assert not solved_lenient("I couldn't find a way to make 24 from 2, 4 and 8.", [2, 4, 8], 24); n += 1
    with tempfile.TemporaryDirectory() as d:
        out, pd = Path(d) / "run", Path(d) / "pd"
        out.mkdir(); pd.mkdir()
        truth = [{"id": f"p{i}", "nums": [2, 4, 8], "target": 24, "wording_id": i % 2} for i in range(10)]
        (pd / "chat_puzzles.jsonl").write_text("".join(json.dumps(t) + "\n" for t in truth))
        ok = "Here's one way that works: (8 - 2) * 4 = 24."
        rows = {"B0": [{"id": t["id"], "turn_i": 0, "reply": "Sure! Let's think.", "routed": False, "route": None} for t in truth],
                "B1": [{"id": t["id"], "turn_i": 0, "reply": ok, "routed": True, "route": {"expr": "(8 - 2) * 4"}} for t in truth],
                "B1off": [{"id": t["id"], "turn_i": 0, "reply": ok if i < 3 else "I tried", "routed": True,
                           "route": {"expr": "(8 - 2) * 4" if i < 3 else ""}} for i, t in enumerate(truth)]}
        for k, v in rows.items():
            (out / f"puzzles_{k}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in v))
        (out / "negatives_B1.jsonl").write_text("".join(json.dumps({"id": f"n{i}", "turn_i": 0, "reply": "ok",
                                                                    "routed": i == 0}) + "\n" for i in range(5)))
        for task in ("general", "chatdev"):
            for k in ("B0", "B1"):
                (out / f"{task}_{k}.jsonl").write_text("".join(json.dumps({"id": f"g{i}", "turn_i": 0, "reply": f"a{i}",
                                                                          "routed": False}) + "\n" for i in range(4)))
        r = recount(out, pd)
        assert r["solved_strict"] == {"B0": 0, "B1": 10, "B1off": 3}, r["solved_strict"]
        assert r["marks"] == {"R1": True, "R2": True, "R3": True, "R4": True, "R5": True}, r["marks"]
        n += 1
        (out / "general_B1.jsonl").write_text("".join(json.dumps({"id": f"g{i}", "turn_i": 0, "reply": "a0",
                                                                  "routed": False}) + "\n" for i in range(4)))
        assert recount(out, pd)["no_harm"]["general"]["differ_unrouted"] == 3; n += 1
    print(f"rt02d recount selftest {n}/{n}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default="artifacts/claude-rt02d-20260926/run")
    ap.add_argument("--panel-dir", default="artifacts/claude-panel-rt02d-20260926")
    ap.add_argument("--official", default="")
    ap.add_argument("--write", default="", help="write the recount JSON here (counts and ids only)")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    res = recount(Path(a.out), Path(a.panel_dir))
    diffs = compare(res, json.loads(Path(a.official).read_text())) if a.official else []
    res["disagreements_with_official"] = diffs
    if a.write:
        Path(a.write).write_text(json.dumps(res, indent=1), encoding="utf-8")
    show = {k: v for k, v in res.items() if k != "_ids"}
    print(json.dumps(show))


if __name__ == "__main__":
    main()
