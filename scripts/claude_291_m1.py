#!/usr/bin/env python3
"""Merge 291 -- mark M1 driver: 138nb's sealed dev/case files (720 cases,
138n's M1 runner semantics) on three arms: nb (138nb, own), p (138p) and
291. The registered bar: every case where 291 differs from 138p is
predicted by id with its exact 291 record (0 unpredicted,
0 predicted-but-wrong, 0 predicted-but-not-moved). Fidelity: the nb re-run
reproduces 138nb's registered rows (except timing).

Runner per piece = 138n's M1 runner semantics (see
scripts/claude_138n_l1.py, read-only and reused): one fresh agent per
case, every turn recorded:
  loop mode   (221, 221b: in-process loop.turn, reply = " ".join(lines))
  daemon mode (everything else: fresh daemon per case via
               fable_marks123_all.make_daemon, mailbox files, reply =
               outbox text stripped)
Every arm uses sleep_threshold 100000.

Per case the record is: replies per turn, active taught triples after
each turn (sorted) and all taught facts ever written after each turn
(active or not, sorted).

usage:
  claude_291_m1.py run --arm nb|p|291 --out-dir DIR --work DIR [--pieces ..]
  claude_291_m1.py judge --dir DIR --pred predicted_moves291.json --out F
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

import claude_138n_l1 as L1  # noqa: E402 (driver semantics, read-only)

A = ROOT / "artifacts"
ARMS = {
    "nb": ("scripts/claude_loop138nb_agent.py",
           A / "claude-merge138nb-20260923" / "loop138nb-config.json",
           "claude_loop138nb_agent", "DEFAULT_CONFIG138NB",
           "build_agent138nb"),
    "p": ("scripts/claude_loop138p_agent.py",
          A / "claude-merge138p-20260923" / "loop138p-config.json",
          "claude_loop138p_agent", "DEFAULT_CONFIG138P",
          "build_agent138p"),
    "291": ("scripts/claude_loop291_agent.py",
            A / "claude-join291-20260923" / "loop291-config.json",
            "claude_loop291_agent", "DEFAULT_CONFIG291",
            "build_agent291"),
}
REGNB = A / "claude-merge138nb-20260923" / "run" / "m2"


def _merge_loop_builder(arm: str):
    _a, cfgp, mod_name, cfg_name, fn = ARMS[arm]
    mod = __import__(mod_name)
    cfg = copy.deepcopy(getattr(mod, cfg_name))
    cfg.update(json.loads(Path(cfgp).read_text(encoding="utf-8")))
    return cfg, getattr(mod, fn)


def cmd_run(arm: str, out_dir: Path, work: Path, pieces) -> None:
    import fable_marks123_all as M
    out_dir.mkdir(parents=True, exist_ok=True)
    for piece in pieces:
        t0 = time.time()
        mode = L1.MODE.get(piece, "daemon")
        w = work / f"{piece}-{arm}"
        if mode == "loop":
            cfg, fn = _merge_loop_builder(arm)
        else:
            agent, cfgp, _m, _c, _f = ARMS[arm]
            _mod, dcls, _b, _c2 = M.load_agent(str(ROOT / agent))
            base = M.load_base_cfg(str(cfgp))
        rows = []
        for i, c in enumerate(L1.cases_for(piece)):
            sd = w / f"{i:03d}"
            if mode == "loop":
                r = L1.run_loop_case(cfg, fn, c["turns"], sd)
            else:
                r = L1.run_daemon_case(dcls, base, c["turns"], sd)
            rows.append({"id": c["id"], "turns": c["turns"], **r})
        shutil.rmtree(w, ignore_errors=True)
        (out_dir / f"{piece}-{arm}.json").write_text(
            json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{piece}/{arm}: {len(rows)} cases {time.time() - t0:.1f}s",
              flush=True)


def cmd_judge(d: Path, pred_path: Path | None, out: Path, pieces) -> int:
    pred = (json.loads(Path(pred_path).read_text(encoding="utf-8"))["m1_720"]
            if pred_path else {})
    res = {"pieces": {}, "unpredicted": [], "predicted_ok": [],
           "predicted_wrong": [], "predicted_not_moved": [],
           "fidelity_nb": {}}
    for piece in pieces:
        base = {r["id"]: r for r in json.loads(
            (d / f"{piece}-p.json").read_text(encoding="utf-8"))}
        new = {r["id"]: r for r in json.loads(
            (d / f"{piece}-291.json").read_text(encoding="utf-8"))}
        own = {r["id"]: r for r in json.loads(
            (d / f"{piece}-nb.json").read_text(encoding="utf-8"))}
        try:
            reg = {r["id"]: r for r in json.loads(
                (REGNB / f"{piece}-nb.json").read_text(encoding="utf-8"))}
            fid_bad = sorted(i for i in reg
                             if L1.rec(own.get(i, {})) != L1.rec(reg[i]))
            fid_missing = sorted(set(reg) ^ set(own))
        except (OSError, ValueError, KeyError) as e:  # noqa: BLE001
            fid_bad, fid_missing = [f"ERR:{e}"], []
        res["fidelity_nb"][piece] = {"bad": fid_bad, "missing": fid_missing}
        pp = pred.get(piece, {})
        n_same = 0
        moves = []
        for cid, brow in base.items():
            nrow = new[cid]
            key = f"{piece}/{cid}"
            if L1.rec(brow) == L1.rec(nrow):
                n_same += 1
                if cid in pp:
                    res["predicted_not_moved"].append(key)
                continue
            moves.append({"id": key, "turns": brow["turns"],
                          "p_replies": brow["replies"],
                          "new_replies": nrow["replies"],
                          "active_same": brow["active"] == nrow["active"],
                          "all_same": brow["all"] == nrow["all"],
                          "p_active_last": brow["active"][-1],
                          "new_active_last": nrow["active"][-1]})
            if cid not in pp:
                res["unpredicted"].append(key)
            elif L1.rec(nrow) == pp[cid]["expect_291"]:
                res["predicted_ok"].append(key)
            else:
                res["predicted_wrong"].append(key)
        res["pieces"][piece] = {"n": len(base), "same_as_p": n_same,
                                "moved": len(moves), "moves": moves}
        print(f"judge {piece}: {n_same}/{len(base)} same as 138p, "
              f"{len(moves)} moved", flush=True)
    res["counts"] = {k: len(res[k]) for k in
                     ("unpredicted", "predicted_ok", "predicted_wrong",
                      "predicted_not_moved")}
    res["pass"] = (res["counts"]["unpredicted"] == 0
                   and res["counts"]["predicted_wrong"] == 0
                   and res["counts"]["predicted_not_moved"] == 0
                   and all(not v["bad"] and not v["missing"]
                           for v in res["fidelity_nb"].values()))
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    print(json.dumps(res["counts"]), "PASS" if res["pass"] else "FAIL")
    return 0 if res["pass"] else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--arm", choices=["nb", "p", "291"], required=True)
    r.add_argument("--out-dir", required=True)
    r.add_argument("--work", required=True)
    r.add_argument("--pieces", nargs="*", default=list(L1.PIECES))
    j = sub.add_parser("judge")
    j.add_argument("--dir", required=True)
    j.add_argument("--pred", default=None)
    j.add_argument("--out", required=True)
    j.add_argument("--pieces", nargs="*", default=list(L1.PIECES))
    a = ap.parse_args(argv)
    if a.cmd == "run":
        cmd_run(a.arm, Path(a.out_dir), Path(a.work), a.pieces)
        return 0
    return cmd_judge(Path(a.dir),
                     Path(a.pred) if a.pred else None, Path(a.out), a.pieces)


if __name__ == "__main__":
    sys.exit(main())
