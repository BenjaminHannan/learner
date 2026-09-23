#!/usr/bin/env python3
"""Merge 138p -- mark M1 (part A) driver: 138m's nine piece case sets on arm
p (138p), reusing scripts/claude_138m_l1.py read-only for case lists,
builders, sealed refs and compare records. New file only.

usage:
  claude_138p_l1.py run --out-dir DIR --work DIR [--pieces ...]
  claude_138p_l1.py sealed --dir DIR --out F   (p vs sealed? no: own-arm
      fidelity is checked by claude_138m_l1 sealed on the own/head/l/m run;
      this sealed checks arm-p rows exist for every case id)
  claude_138p_l1.py judge --dir DIR --pred predicted_moves138p.json --out F
      (138p vs line head per 138m's rule; m1 section of the pred file)

Arm p builder: scripts/claude_loop138p_agent.build_agent138p on the sealed
loop138p-config.json merged over module defaults (same pattern as
claude_138m_l1.build). sleep_threshold 100000 (no sleep in short sessions).
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_138m_l1 as L1  # noqa: E402 (read-only)

A = ROOT / "artifacts"
P = A / "claude-merge138p-20260923"


def build_p(state_dir: str):
    import claude_loop138p_agent as LP
    cfg = copy.deepcopy(LP.DEFAULT_CONFIG138P)
    cfg.update(json.loads(
        (P / "loop138p-config.json").read_text(encoding="utf-8")))
    cfg["state_dir"] = state_dir
    cfg["sleep_threshold"] = 100000
    return LP.build_agent138p(cfg)


def run_session_p(turns: list[str], sd: Path) -> dict:
    shutil.rmtree(sd, ignore_errors=True)
    sd.mkdir(parents=True)
    loop = build_p(str(sd))
    lines, writes = [], []
    for t in turns:
        before = set(L1.facts(loop))
        lines.append(list(loop.turn(t)))
        writes.append(len(set(L1.facts(loop)) ^ before))
    snap = json.dumps({"facts": L1.facts(loop),
                       "entities": loop.nb.entities}, sort_keys=True)
    return {"lines": lines, "writes": writes, "snap": snap}


def run_224c_p(work: Path) -> list[dict]:
    import claude_224c_cases as C
    C.__dict__.setdefault("_orig_build", C.build)

    def b(_agent, sd):
        return build_p(sd)
    C.build = b
    rows = []
    try:
        work.mkdir(parents=True, exist_ok=True)
        cases = json.loads(
            (L1.ART["224c"] / "cases224c.json").read_text(
                encoding="utf-8"))["cases"]
        for mode, pre in (("natural", "nat:"), ("forced", "frc:")):
            for c in cases:
                r = C.run_case("x", mode, c, work)
                rows.append({"id": pre + c["id"], **L1._rec224(r)})
        for c in json.loads(
                (L1.ART["224b"] / "cases224b.json").read_text(
                    encoding="utf-8"))["cases"]:
            r = C.run_case("x", "natural", c, work)
            rows.append({"id": "b1:" + c["id"], **L1._rec224(r)})
    finally:
        C.build = C.__dict__["_orig_build"]
    return rows


def run_233_p(work: Path) -> list[dict]:
    import claude_polite233_run as PR
    import fable_marks123_all as M
    import claude_loop138p_agent as LP
    cfg = M.load_base_cfg(str(P / "loop138p-config.json"))
    rows = []
    for line in (L1.ART["233"] / "dev233.jsonl").read_text(
            encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        r = PR.run_agent(LP.Loop138pDaemon, cfg, work / case["id"], case)
        rows.append({"id": case["id"], "reply": r["reply"],
                     "setup_replies": r["setup_replies"],
                     "triples_after": r["triples_after"],
                     "qwrite": r["qwrite"],
                     "score": PR.score_one(case, r["reply"])})
    return rows


def cmd_run(out_dir: Path, work: Path, pieces) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for piece in pieces:
        t0 = time.time()
        w = work / f"{piece}-p"
        if piece == "224c":
            rows = run_224c_p(w)
        elif piece == "233":
            rows = run_233_p(w)
        else:
            rows = []
            for i, c in enumerate(L1.cases_for(piece)):
                r = run_session_p(c["turns"], w / f"{i:03d}")
                rows.append({"id": c["id"], "turns": c["turns"], **r})
        shutil.rmtree(w, ignore_errors=True)
        (out_dir / f"{piece}-p.json").write_text(
            json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{piece}/p: {len(rows)} cases {time.time() - t0:.1f}s",
              flush=True)


def cmd_judge(d: Path, pred_path: Path | None, out: Path) -> int:
    pred = (json.loads(pred_path.read_text(encoding="utf-8"))["m1"]
            if pred_path else {})
    res = {"pieces": {}, "unpredicted": [], "predicted_ok": [],
           "predicted_wrong": [], "predicted_not_moved": []}
    for piece in L1.PIECES:
        head_file = d / f"{piece}-head.json"
        if not head_file.exists():
            head_file = d / f"{piece}-own.json"
        head = {r["id"]: r for r in json.loads(
            head_file.read_text(encoding="utf-8"))}
        p = {r["id"]: r for r in json.loads(
            (d / f"{piece}-p.json").read_text(encoding="utf-8"))}
        m = {r["id"]: r for r in json.loads(
            (d / f"{piece}-m.json").read_text(encoding="utf-8"))}
        pp = pred.get(piece, {})
        n_same = n_moved = 0
        moves = []
        for cid, hr in head.items():
            pr = p[cid]
            same = L1._cmp(piece, hr) == L1._cmp(piece, pr)
            key = f"{piece}/{cid}"
            if same:
                n_same += 1
                if cid in pp:
                    res["predicted_not_moved"].append(key)
                continue
            n_moved += 1
            mv = {"id": key,
                  "p_equals_m": L1._cmp(piece, pr) == L1._cmp(piece, m[cid])}
            if piece not in ("224c", "233"):
                mv["turns"] = hr["turns"]
                mv["head_lines"] = hr["lines"]
                mv["p_lines"] = pr["lines"]
                mv["head_writes"] = hr["writes"]
                mv["p_writes"] = pr["writes"]
                mv["snap_same"] = hr["snap"] == pr["snap"]
            else:
                mv["head"] = L1._cmp(piece, hr)
                mv["p"] = L1._cmp(piece, pr)
            moves.append(mv)
            if cid not in pp:
                res["unpredicted"].append(key)
            else:
                ok = L1._cmp(piece, pr) == pp[cid]["expect_p"]
                (res["predicted_ok"] if ok
                 else res["predicted_wrong"]).append(key)
        res["pieces"][piece] = {"n": len(head), "same_as_head": n_same,
                                "moved": n_moved, "moves": moves}
        print(f"judge {piece}: {n_same}/{len(head)} same as head, "
              f"{n_moved} moved", flush=True)
    res["counts"] = {k: len(res[k]) for k in
                     ("unpredicted", "predicted_ok", "predicted_wrong",
                      "predicted_not_moved")}
    res["pass"] = (res["counts"]["unpredicted"] == 0
                   and res["counts"]["predicted_wrong"] == 0
                   and res["counts"]["predicted_not_moved"] == 0)
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    print(json.dumps(res["counts"]), "PASS" if res["pass"] else "FAIL")
    return 0 if res["pass"] else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--out-dir", required=True)
    r.add_argument("--work", required=True)
    r.add_argument("--pieces", nargs="*", default=list(L1.PIECES))
    j = sub.add_parser("judge")
    j.add_argument("--dir", required=True)
    j.add_argument("--pred", default=None)
    j.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        cmd_run(Path(a.out_dir), Path(a.work), a.pieces)
        return 0
    return cmd_judge(Path(a.dir), Path(a.pred) if a.pred else None,
                     Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
