#!/usr/bin/env python3
"""Merge 138l -- rt143 without the literal 'Saved:' teach gate, any agent.

Same per-case method as the 138j verifier's driver
(artifacts/claude-verify-20260922/138j/rt143_nogate.py, read-only): all
rt143 cases in suite order in ONE process, fresh daemon per case, every
teach sent, stored triples recorded before the question, question always
asked. Only change: the agent/config come from the command line (daemon
class found with fable_marks123_all.load_agent, as every suite driver
does) instead of a hard-coded 138i/138j switch; guard not toggled here
(138k/138l install it themselves).

usage: claude_138l_rt143nogate.py <agent.py> <config.json> <out.json>
       claude_138l_rt143nogate.py --diff <base.json> <new.json> <out.json>
"""
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def run(agent: str, config: str, out: Path) -> None:
    import fable_loop90_agent as L90
    import fable_marks123_all as M
    import fable_redteam143_run as R143
    _mod, D, _b, _c = M.load_agent(agent)
    CFG = json.loads(Path(config).read_text(encoding="utf-8"))
    scratch = Path(tempfile.mkdtemp(prefix="l138-rt143-"))
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    rows = []
    for c in suite["cases"]:
        wd = scratch / c["id"]
        if wd.exists():
            shutil.rmtree(wd)
        wd.mkdir(parents=True)
        cfg = dict(copy.deepcopy(CFG))
        cfg["state_dir"] = str(wd)
        d = D(str(wd), cfg=cfg)
        tr = []
        for i, t in enumerate(c["teaches"]):
            f = f"t{i:02d}.txt"
            (wd / "inbox" / f).write_text(t + "\n", encoding="utf-8")
            d.process_file(wd / "inbox" / f)
            tr.append((wd / "outbox" / f).read_text(encoding="utf-8").strip())
        trip = [list(x) for x in L90.notebook_triples(d.loop.nb)]
        f = "q.txt"
        (wd / "inbox" / f).write_text(c["question"] + "\n", encoding="utf-8")
        d.process_file(wd / "inbox" / f)
        q = (wd / "outbox" / f).read_text(encoding="utf-8").strip()
        rows.append({"id": c["id"], "teach_replies": tr, "triples": trip,
                     "question": c["question"], "reply": q,
                     "expected": c["expected"]})
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    shutil.rmtree(scratch, ignore_errors=True)
    print(f"rt143-nogate: {len(rows)} rows -> {out}", flush=True)


def diff(base: Path, new: Path, out: Path) -> None:
    b = {r["id"]: r for r in json.loads(base.read_text())}
    n = {r["id"]: r for r in json.loads(new.read_text())}
    moves = []
    for cid in b:
        fields = [k for k in ("teach_replies", "triples", "reply")
                  if b[cid][k] != n[cid][k]]
        if fields:
            moves.append({"id": cid, "fields": fields,
                          "base_reply": b[cid]["reply"],
                          "new_reply": n[cid]["reply"],
                          "base_triples": b[cid]["triples"],
                          "new_triples": n[cid]["triples"],
                          "base_teach": b[cid]["teach_replies"],
                          "new_teach": n[cid]["teach_replies"],
                          "expected": b[cid]["expected"]})
    out.write_text(json.dumps({"n": len(b), "moves": moves}, indent=1,
                              ensure_ascii=False), encoding="utf-8")
    print(f"rt143-nogate diff: {len(moves)} moved of {len(b)}: "
          f"{[m['id'] for m in moves]}", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "--diff":
        diff(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    else:
        run(sys.argv[1], sys.argv[2], Path(sys.argv[3]))
