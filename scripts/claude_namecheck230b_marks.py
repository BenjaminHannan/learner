#!/usr/bin/env python3
"""Exp 230b marks driver.

  python -B scripts/claude_namecheck230b_marks.py --dev     # M2 dev cases + M5 timing
  python -B scripts/claude_namecheck230b_marks.py --panel   # M1 blind panel (run once)
Rows go to artifacts/claude-namecheck230b-20260922/.

Expected 230b reply for every turn, computed from the live 230 reply
(rule sealed in PASSMARKS.md):
  if a 230 reply line starts "Yes. Your name is ", asked_name(turn) is a
  name, a user name is stored, and the two differ case-insensitively on the
  whole name -> that line becomes "No. Your name is <stored>.";
  otherwise byte-identical to 230.
Notebook snapshots must be identical to 230; question turns write nothing.
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
ART = REPO / "artifacts" / "claude-namecheck230b-20260922"
ART230 = REPO / "artifacts" / "claude-yesprefix230-20260922"
PANEL = REPO / "artifacts" / "claude-namecheckpanel230b-20260922"

AGENTS = {
    "230b": ("claude_loop230b_agent", ART / "loop230b-config.json"),
    "230": ("claude_loop230_agent", ART230 / "loop230-config.json"),
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


def is_question(t: str) -> bool:
    return str(t).strip().endswith("?")


def run_session(tag: str, turns: list[str]) -> dict:
    loop = build(tag, tempfile.mkdtemp(prefix=f"n230b_{tag}_"))
    replies, writes, secs, stored = [], [], [], []
    import fable_fix219_selfname as F219
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


def expected(text: str, base_lines: list[str], stored) -> list[str]:
    import claude_loop230b_agent as B
    if not any(ln.startswith(YES_PREFIX) for ln in base_lines):
        return list(base_lines)
    asked = B.asked_name(text)
    if asked is None or not stored or B.same_name(asked, stored):
        return list(base_lines)
    return [B.NO_NAME_FMT % stored if ln.startswith(YES_PREFIX) else ln
            for ln in base_lines]


def compare(turns: list[str]) -> dict:
    old = run_session("230", turns)
    new = run_session("230b", turns)
    per = []
    for i, t in enumerate(turns):
        ro, rn = old["replies"][i], new["replies"][i]
        exp = expected(t, ro, old["stored"][i])
        per.append({"turn": t, "stored": old["stored"][i], "r230": ro,
                    "r230b": rn, "expected": exp, "moved": rn != ro,
                    "ok": rn == exp, "writes230b": new["writes"][i],
                    "writes230": old["writes"][i],
                    "t230": old["secs"][i], "t230b": new["secs"][i]})
    return {"per": per, "facts_same": new["snap"] == old["snap"]}


def false_yes(text: str, reply: str, stored) -> bool:
    """Reply starts 'Yes' but the asked name differs / nothing stored."""
    import claude_loop230b_agent as B
    if not reply.startswith("Yes"):
        return False
    if not stored:
        return True
    asked = B.asked_name(text)
    return asked is not None and not B.same_name(asked, stored)


def run_dev() -> int:
    cases = json.loads((ART / "dev-cases.json").read_text(encoding="utf-8"))
    rows, bad = [], 0
    n_tot = {k: 0 for k in ("NO", "YES", "SAME", "UNTAUGHT")}
    n_ok = dict(n_tot)
    dt = []
    fy = 0
    qwrites = 0
    for c in cases:
        res = compare(c["turns"])
        last = res["per"][-1]
        reply = " ".join(last["r230b"])
        kind = c["expect"]
        n_tot[kind] += 1
        if kind == "NO":
            ok = reply == "No. Your name is %s." % c["stored"]
        elif kind == "YES":
            ok = reply == "Yes. Your name is %s." % c["stored"]
        else:  # SAME / UNTAUGHT: byte-identical to 230, never Yes if untaught
            ok = last["r230b"] == last["r230"] and (
                kind != "UNTAUGHT" or not reply.startswith("Yes"))
        ok = ok and all(p["ok"] for p in res["per"]) and res["facts_same"]
        for p in res["per"]:
            if is_question(p["turn"]):
                qwrites += p["writes230b"]
                dt.append(p["t230b"] - p["t230"])
            if false_yes(p["turn"], " ".join(p["r230b"]), p["stored"]):
                fy += 1
        n_ok[kind] += int(ok)
        bad += int(not ok)
        rows.append({"id": c["id"], "expect": kind, "ok": ok, **res})
        print(f"{c['id']:<8} {kind:<8} {'ok ' if ok else 'BAD'} "
              f"{last['turn']!r} 230={' '.join(last['r230'])!r} "
              f"230b={reply!r}", flush=True)
    med = statistics.median(dt) * 1000 if dt else 0.0
    summ = {"counts_ok": n_ok, "counts_total": n_tot, "false_yes": fy,
            "question_writes": qwrites, "cases_bad": bad,
            "median_added_ms": round(med, 3), "n_questions_timed": len(dt)}
    (ART / "dev-rows.json").write_text(json.dumps(
        {"summary": summ, "rows": rows}, indent=1, ensure_ascii=False),
        encoding="utf-8")
    print(json.dumps(summ), flush=True)
    return 0


def _get(d: dict, keys: tuple, default=None):
    for k in keys:
        if k in d:
            return d[k]
    return default


def _turns(item: dict) -> list[str]:
    t = _get(item, ("turns", "dialog", "dialogue", "messages", "session",
                    "conversation"))
    if t is None:
        pre = _get(item, ("setup", "teach", "context", "prefix"), []) or []
        if isinstance(pre, str):
            pre = [pre]
        q = _get(item, ("question", "ask", "probe", "text", "turn"))
        t = list(pre) + ([q] if q else [])
    return [x if isinstance(x, str) else _get(x, ("text", "ben", "user",
                                                  "content")) for x in t]


def run_panel(panel_dir: Path = PANEL, out: Path | None = None) -> int:
    PANEL = panel_dir  # noqa: N806
    out = out or (ART / "panel-rows.json")
    items = [json.loads(ln) for ln in (PANEL / "panel.jsonl").read_text(
        encoding="utf-8").splitlines() if ln.strip()]
    base = {}
    for ln in (PANEL / "base230.jsonl").read_text(
            encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            base[str(_get(r, ("id", "item_id", "case_id")))] = r
    rows = []
    for it in items:
        iid = str(_get(it, ("id", "item_id", "case_id")))
        turns = _turns(it)
        exp = str(_get(it, ("expect", "expected", "label", "class"), ""))
        res = compare(turns)
        rows.append({"id": iid, "expect": exp, "item": it,
                     "base_row": base.get(iid), **res})
        last = res["per"][-1]
        print(f"{iid:<10} {exp:<10} r230={' '.join(last['r230'])!r} "
              f"r230b={' '.join(last['r230b'])!r} ok={last['ok']}",
              flush=True)
    out.write_text(json.dumps(
        rows, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(rows)} panel rows", flush=True)
    return 0


if __name__ == "__main__":
    if "--dev" in sys.argv:
        sys.exit(run_dev())
    if "--panel" in sys.argv:
        if "--panel-dir" in sys.argv:  # driver self-test on a fake panel
            i = sys.argv.index("--panel-dir")
            sys.exit(run_panel(Path(sys.argv[i + 1]),
                               Path(sys.argv[i + 2])))
        sys.exit(run_panel())
    print(__doc__)
