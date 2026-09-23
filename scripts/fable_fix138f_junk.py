#!/usr/bin/env python3
"""Exp 138f M4/G3-junk driver -- junk-write suites re-run through loop138f.

Same shape as scripts/fable_loop138d_junk.py; only the agent under test
is loop138f (fresh in-process loops, sleep_threshold=100000). Judges
imported read-only. Compared per-case against sealed loop138b rows AND
against loop138d rows (revert check). Bar: the 7 cases identical to
loop138b; 0 new WRONG / WRONG-WRITE / junk writes vs loop138b everywhere;
every move predicted in PASSMARKS.md. Outputs into
artifacts/fable-agent138f-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix138f_junk.py
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix139b_probe as P139b  # noqa: E402 (judge, read-only)
import fable_fix139b_redteam136 as R136  # noqa: E402 (judge, read-only)
import fable_fix150_probe as P150  # noqa: E402 (judge, read-only)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop138f_agent as L138f  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-agent138f-20260922"
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"
ART139B = ROOT / "artifacts" / "fable-fix139b-20260922"
ART144 = ROOT / "artifacts" / "fable-fix144-20260922"
ART150 = ROOT / "artifacts" / "fable-fix150-20260922"

SEVEN = {"redteam136": ["C124", "C127", "C129", "C142"],
         "cases139b": ["C10", "C21"]}


def build138f(extra: dict) -> object:
    cfg = copy.deepcopy(L138f.DEFAULT_CONFIG138F)
    cfg.update(extra)
    return L138f.build_agent138f(cfg)


def new_daemon138f(root: Path):
    cfg = copy.deepcopy(L138f.DEFAULT_CONFIG138F)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L138f.Loop138fDaemon(root, cfg=cfg, idle_seconds=3600.0)


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False,
                                          sort_keys=True) for r in rows)
                    + "\n", encoding="utf-8")


def base_rows(name: str) -> list[dict]:
    return [json.loads(l) for l in
            (ART138B / name).read_text(
                encoding="utf-8").splitlines() if l.strip()]


def check_seven(suite: str, rows: list[dict]) -> dict:
    r_by_id = {r["id"]: r for r in rows}
    b_by_id = {r["id"]: r for r in base_rows(
        "redteam136-loop138b.json" if suite == "redteam136"
        else "probe139b-loop138b.json")}
    out = {}
    for cid in SEVEN[suite]:
        r = r_by_id.get(cid, {})
        b = b_by_id.get(cid, {})
        out[cid] = {"verdict138f": r.get("verdict"),
                    "verdict138b": b.get("verdict"),
                    "identical": (r.get("verdict") == b.get("verdict")
                                  and str(r.get("reply", "")).strip()
                                  == str(b.get("reply", "")).strip()
                                  and r.get("stored", "n/a")
                                  == b.get("stored", "n/a"))}
    return out


def run_redteam136() -> dict:
    R136.new_daemon139b = new_daemon138f  # type: ignore[method-assign]
    cases = json.loads((ART136 / "cases136.json").read_text(
        encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = ART / "work-rt136"
    workroot.mkdir(parents=True, exist_ok=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    write_rows(ART / "redteam136-loop138f.json", rows)
    b_by_id = {r["id"]: r for r in base_rows("redteam136-loop138b.json")}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"]:
            moves.append({"id": r["id"], "loop138b": b["verdict"],
                          "loop138f": r["verdict"],
                          "reply138b": str(b.get("reply", ""))[:120],
                          "reply138f": str(r.get("reply", ""))[:120]})
            if r["verdict"] == "WRONG-WRITE" and b["verdict"] != "WRONG-WRITE":
                new_wrong += 1
    from collections import Counter
    return {"suite": "redteam136", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_138b": new_wrong, "moves": moves,
            "seven": check_seven("redteam136", rows)}


def run_cases150() -> dict:
    cases = json.loads((ART150 / "cases150.json").read_text(
        encoding="utf-8"))
    rows = [P150.run_case(row, build138f) for row in cases]
    write_rows(ART / "probe150-loop138f.json", rows)
    b_by_id = {r["id"]: r for r in base_rows("probe150-loop138b.json")}
    moves = []
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"] or r["reply"] != b["reply"]:
            moves.append({"id": r["id"], "loop138b": b["verdict"],
                          "loop138f": r["verdict"]})
    from collections import Counter
    return {"suite": "cases150", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_loop138b": moves}


def run_f1() -> dict:
    cases = json.loads((ART144 / "f1-cases.json").read_text(
        encoding="utf-8"))["cases"]
    rows = []
    for row in cases:
        t0 = time.time()
        with tempfile.TemporaryDirectory(
                prefix=row["id"] + "_") as tmp:
            try:
                loop = build138f({"state_dir": tmp,
                                  "sleep_threshold": 100000})
                reply = " ".join(loop.turn(row["text"]))
                stored = [list(t) for t in L90.notebook_triples(loop.nb)]
            except Exception as exc:  # noqa: BLE001
                rows.append({"id": row["id"], "kind": row["kind"],
                             "verdict": "HARNESS-ERROR",
                             "reply": repr(exc)[:120], "stored": []})
                continue
        rep = {"id": row["id"], "kind": row["kind"], "text": row["text"],
               "stored": stored, "reply": reply.strip()[:160],
               "seconds": round(time.time() - t0, 3)}
        if row["kind"] == "must-write":
            want = [list(row["expect"])]
            rep["expect"] = row["expect"]
            if stored == want and reply.strip().startswith("Saved:"):
                rep["verdict"] = "OK"
            elif not stored:
                rep["verdict"] = "MISSED"
            else:
                rep["verdict"] = "WRONG-WRITE"
        else:
            if not stored and not reply.strip().startswith("Saved:"):
                rep["verdict"] = "OK"
            else:
                rep["verdict"] = "WRONG-WRITE"
        rows.append(rep)
    write_rows(ART / "f1-loop138f.json", rows)
    from collections import Counter
    base_f1 = base_rows("f1-loop138b.json")
    b_by_id = {r["id"]: r for r in base_f1}
    moves138b = [{"id": r["id"], "loop138b": (b_by_id[r["id"]]["verdict"]
                  if r["id"] in b_by_id else None),
                   "loop138f": r["verdict"]}
                 for r in rows
                 if r["id"] in b_by_id and
                 b_by_id[r["id"]]["verdict"] != r["verdict"]]
    return {"suite": "f1", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "non_ok": [r for r in rows if r["verdict"] != "OK"],
            "moves_vs_loop138b": moves138b}


def run_cases139b() -> dict:
    cases = json.loads((ART139B / "cases139b.json").read_text(
        encoding="utf-8"))
    cases139 = json.loads(
        (ROOT / "artifacts" / "fable-fix139-20260922" / "cases139.json").read_text(
            encoding="utf-8"))
    if isinstance(cases139, dict):
        cases139 = cases139.get("cases", cases139)
    cases = list(cases139) + list(cases)
    rows = [P139b.run_case(row, build138f) for row in cases]
    write_rows(ART / "probe139b-loop138f.json", rows)
    b_by_id = {r["id"]: r for r in base_rows("probe139b-loop138b.json")}
    moves = []
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"]:
            moves.append({"id": r["id"], "loop138b": b["verdict"],
                          "loop138f": r["verdict"]})
    from collections import Counter
    return {"suite": "cases139b", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_loop138b": moves,
            "seven": check_seven("cases139b", rows)}


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rc = 0
    out: dict = {}
    for fn in (run_redteam136, run_cases150, run_f1, run_cases139b):
        rep = fn()
        out[rep["suite"]] = rep
        movekeys = [k for k in rep if k.startswith("move") or k == "non_ok"]
        nmoves = sum(len(rep.get(k, []) or []) for k in movekeys)
        print(f"M4 {rep['suite']}: n={rep['n']} {rep['counter']} "
              f"moved={nmoves}", flush=True)
        for key in ("moves", "moves_vs_loop138b", "non_ok"):
            for m in rep.get(key, []) or []:
                print(f"  {key} {m}", flush=True)
        if "seven" in rep:
            for cid, s in rep["seven"].items():
                print(f"  SEVEN {cid}: 138f={s['verdict138f']} "
                      f"138b={s['verdict138b']} identical={s['identical']}",
                      flush=True)
                if not s["identical"]:
                    rc = 1
        if rep.get("new_wrong_vs_138b"):
            rc = 1
        for key in ("moves", "moves_vs_loop138b"):
            for m in rep.get(key, []) or []:
                got = m.get("loop138f", "")
                if got in ("WRONG-WRITE", "WRONG-ANSWER", "WRONG-REPLY",
                           "WRONG"):
                    rc = 1
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "junk138f-summary.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print(f"M4 {out['seconds']}s rc={rc}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
