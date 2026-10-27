#!/usr/bin/env python3
"""Verifier driver (read-only on sealed files): run all rt143 cases in suite
order in ONE process like fable_fix138j_suites.run_rt143, but WITHOUT the
literal 'Saved:' teach gate, so every question is asked. Records teach
replies, stored triples before the question, and the question reply.
usage: rt143_nogate.py <138i|138j> <guard 0|1> <prefix none|rt136> <out.json>
"""
import copy, json, shutil, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
arm, guard, prefix, out = sys.argv[1], sys.argv[2] == "1", sys.argv[3], Path(sys.argv[4])
import fable_loop90_agent as L90
if guard:
    from claude_fix228_srcguard import install_srcguard228
    install_srcguard228()
if arm == "138i":
    import fable_loop138i_agent as A
    D, CFG = A.Loop138iDaemon, A.DEFAULT_CONFIG138I
else:
    import fable_loop138j_agent as A
    D, CFG = A.Loop138jDaemon, A.DEFAULT_CONFIG138J
import fable_redteam143_run as R143

def run_turns(turns, wd):
    if wd.exists(): shutil.rmtree(wd)
    wd.mkdir(parents=True)
    d = D(str(wd), cfg=dict(copy.deepcopy(CFG)))
    replies = []
    for i, t in enumerate(turns):
        f = f"t{i:02d}.txt"
        (wd / "inbox" / f).write_text(str(t) + "\n", encoding="utf-8")
        d.process_file(wd / "inbox" / f)
        replies.append((wd / "outbox" / f).read_text(encoding="utf-8").strip())
    return d, replies

scratch = Path(tempfile.mkdtemp(prefix=f"v138j-{arm}-"))
if prefix == "rt136":
    import fable_redteam136_run as R136
    s136 = json.loads(R136.CASES_PATH.read_text(encoding="utf-8"))
    for c in s136["cases"]:
        turns = list(c.get("teaches", [])) + ([c["question"]] if c.get("question") else [])
        try: run_turns(turns, scratch / ("p" + c["id"]))
        except Exception as e: print("prefix err", c["id"], e)
suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
rows = []
for c in suite["cases"]:
    wd = scratch / c["id"]
    if wd.exists(): shutil.rmtree(wd)
    wd.mkdir(parents=True)
    d = D(str(wd), cfg=dict(copy.deepcopy(CFG)))
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
                 "question": c["question"], "reply": q, "expected": c["expected"]})
out.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
shutil.rmtree(scratch, ignore_errors=True)
for r in rows:
    if r["id"].startswith("Q"): print(r["id"], "|", r["reply"][:110])
