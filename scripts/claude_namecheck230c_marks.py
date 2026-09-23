#!/usr/bin/env python3
"""Exp 230c marks driver (live 230b vs live 230c, fresh temp notebooks).

  --dev                      M2 dev cases + M5 timing -> dev-rows.json
  --panel PANEL_DIR OUT.json M1 blind panel (schema checked first; exit 3 on mismatch)
Expected 230c reply for every turn, from the live 230b reply:
  a 230b line starting "Yes. Your name is " loses "Yes. " iff asked_name(turn)
  is None and may_name_something(turn); otherwise byte-identical.
"""
from __future__ import annotations

import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
REPO = SCRIPTS.parent
ART = REPO / "artifacts" / "claude-namecheck230c-20260922"
ART230B = REPO / "artifacts" / "claude-namecheck230b-20260922"
AGENTS = {
    "230c": ("claude_loop230c_agent", ART / "loop230c-config.json"),
    "230b": ("claude_loop230b_agent", ART230B / "loop230b-config.json"),
}
YES_PREFIX = "Yes. Your name is "


def build(tag: str, state_dir: str):
    mod_name, cfg_path = AGENTS[tag]
    mod = __import__(mod_name)
    cfg_attr = [a for a in dir(mod) if a.startswith("DEFAULT_CONFIG")][0]
    build_attr = [a for a in dir(mod) if a.startswith("build_agent")][0]
    cfg = dict(getattr(mod, cfg_attr))
    cfg.update(json.loads(cfg_path.read_text(encoding="utf-8")))
    cfg["state_dir"] = state_dir
    return getattr(mod, build_attr)(cfg)


def facts(loop) -> list:
    return sorted(
        (f.get("subject"), f.get("relation"),
         json.dumps(f.get("value"), sort_keys=True), f.get("source"),
         bool(loop.nb.active(fid)))
        for fid, f in loop.nb.facts.items())


def run_session(tag: str, turns: list[str]) -> dict:
    import fable_fix219_selfname as F219
    loop = build(tag, tempfile.mkdtemp(prefix=f"n230c_{tag}_"))
    replies, writes, secs, stored = [], [], [], []
    for t in turns:
        before = facts(loop)
        stored.append(F219.stored_user_name(loop.nb))
        t0 = time.perf_counter()
        replies.append(list(loop.turn(t)))
        secs.append(time.perf_counter() - t0)
        writes.append(len(set(facts(loop)) ^ set(before)))
    snap = json.dumps({"facts": facts(loop), "entities": loop.nb.entities},
                      sort_keys=True)
    return {"replies": replies, "writes": writes, "snap": snap,
            "secs": secs, "stored": stored}


def expected(text: str, base_lines: list[str]) -> list[str]:
    import claude_loop230b_agent as B
    import claude_loop230c_agent as C
    if not any(ln.startswith(YES_PREFIX) for ln in base_lines):
        return list(base_lines)
    if B.asked_name(text) is not None or not C.may_name_something(text):
        return list(base_lines)
    return [ln[len("Yes. "):] if ln.startswith(YES_PREFIX) else ln
            for ln in base_lines]


def compare(turns: list[str]) -> dict:
    old = run_session("230b", turns)
    new = run_session("230c", turns)
    per = []
    for i, t in enumerate(turns):
        ro, rn = old["replies"][i], new["replies"][i]
        exp = expected(t, ro)
        per.append({"turn": t, "stored": new["stored"][i], "r230b": ro,
                    "r230c": rn, "expected": exp, "moved": rn != ro,
                    "ok": rn == exp, "writes230c": new["writes"][i],
                    "writes230b": old["writes"][i],
                    "t230b": old["secs"][i], "t230c": new["secs"][i]})
    return {"per": per, "facts_same": new["snap"] == old["snap"]}


def run_dev() -> int:
    cases = json.loads((ART / "dev-cases.json").read_text(encoding="utf-8"))
    rows, bad, dt, qwrites = [], 0, [], 0
    for c in cases:
        res = compare(c["turns"])
        last = res["per"][-1]
        rep = " ".join(last["r230c"])
        ok = rep == c["want"] and all(p["ok"] for p in res["per"]) \
            and res["facts_same"]
        moved = any(p["moved"] for p in res["per"])
        for p in res["per"]:
            if p["turn"].strip().endswith("?"):
                qwrites += p["writes230c"]
                dt.append(p["t230c"] - p["t230b"])
        bad += int(not ok)
        rows.append({"id": c["id"], "want": c["want"], "ok": ok,
                     "moved": moved, **res})
        print(f"{c['id']:<5} {'ok ' if ok else 'BAD'} "
              f"{'MOVED' if moved else '     '} {last['turn']!r} "
              f"230b={' '.join(last['r230b'])!r} 230c={rep!r}", flush=True)
    summ = {"cases": len(cases), "cases_ok": len(cases) - bad,
            "moved_ids": [r["id"] for r in rows if r["moved"]],
            "question_writes": qwrites,
            "median_added_ms": round(statistics.median(dt) * 1000, 3),
            "n_questions_timed": len(dt)}
    (ART / "dev-rows.json").write_text(json.dumps(
        {"summary": summ, "rows": rows}, indent=1, ensure_ascii=False),
        encoding="utf-8")
    print(json.dumps(summ), flush=True)
    return 0


def run_panel(panel_dir: str, out: str) -> int:
    import claude_namecheck230c_score as SC
    items, base = SC.load_panel(panel_dir)  # exits 3 on schema mismatch
    rows = []
    for it in items:
        res = compare(list(it["setup"]) + [it["question"]])
        rows.append({"id": it["id"], "item": it, "base_row": base[it["id"]],
                     **res})
        print(f"{it['id']} done", flush=True)
    Path(out).write_text(json.dumps(rows, indent=1, ensure_ascii=False),
                         encoding="utf-8")
    print(f"wrote {len(rows)} panel rows", flush=True)
    return 0


if __name__ == "__main__":
    if "--dev" in sys.argv:
        sys.exit(run_dev())
    if "--panel" in sys.argv:
        i = sys.argv.index("--panel")
        sys.exit(run_panel(sys.argv[i + 1], sys.argv[i + 2]))
    print(__doc__)
