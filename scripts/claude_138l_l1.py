#!/usr/bin/env python3
"""Merge 138l -- mark L1 driver: each piece's own registered cases, run on
three arms with ONE generic driver (piece-own agent, 138k, 138l).

Per piece, the cases and the per-case method follow that piece's own
sealed driver (fresh loop per case/scenario, same turns, same shared
teaches); the piece's sealed files are only read.

  209  cases209-badsave.json + cases209-nearmiss.json; fresh loop per
       case; all replies + 209 snapshot (fable_writescreen209_probe
       .snapshot, read-only).
  212  case212-g.json + case212-s.json; fresh loop per turn; reply,
       routed intent, stored triples.
  216  cases216-p1.jsonl + cases216-p2.jsonl; fresh loop per turn; reply,
       routed intent.
  222  cases222-b1b2.json; b1 = one fresh loop per scenario (id prefix
       before the last '-'), b2 = fresh loop per {teach, probe}; replies +
       stored triples. (222 kept no per-case rows; its own arm here is
       the reference.)
  223  questions223.jsonl; fresh loop per case with the four shared
       teaches of fable_loop223_probe.TEACHES, then the question; reply +
       stored triples.
  226  cases226.json via its own driver fable_source226_run.run (daemon,
       <RESTART> rebuilds on the same dir).

usage:
  claude_138l_l1.py run --piece N --arm own|k|l --out rows.json --work DIR
  claude_138l_l1.py judge --dir DIR --pred predicted_moves138l.json
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

ART = {
    "209": ROOT / "artifacts/fable-writescreen209-20260922",
    "212": ROOT / "artifacts/fable-selfgate212-20260922",
    "216": ROOT / "artifacts/fable-declinecue216-20260922",
    "222": ROOT / "artifacts/fable-ofteachb222-20260922",
    "223": ROOT / "artifacts/fable-cantdo223-20260922",
    "226": ROOT / "artifacts/fable-source226-20260922",
}
PIECES = ("209", "212", "216", "222", "223", "226")
AGENT_PATH = {
    "own": None,
    "k": ("scripts/claude_loop138k_agent.py",
          "artifacts/claude-merge138k-20260922/loop138k-config.json"),
    "l": ("scripts/claude_loop138l_agent.py",
          "artifacts/claude-merge138l-20260922/loop138l-config.json"),
}
OWN_226 = ("scripts/fable_loop226_agent.py",
           "artifacts/fable-source226-20260922/loop226-config.json")


def builder(piece: str, arm: str):
    """(build_fn, default_cfg) for the arm."""
    if arm == "k":
        import claude_loop138k_agent as K
        return K.build_agent138k, K.DEFAULT_CONFIG138K
    if arm == "l":
        import claude_loop138l_agent as L
        return L.build_agent138l, L.DEFAULT_CONFIG138L
    mod = __import__(f"fable_loop{piece}_agent")
    return (getattr(mod, f"build_agent{piece}"),
            getattr(mod, f"DEFAULT_CONFIG{piece}"))


def cases_for(piece: str) -> list[dict]:
    """[{id, turns}] in the piece's own case order."""
    a = ART[piece]
    if piece == "209":
        out = []
        for name in ("cases209-badsave.json", "cases209-nearmiss.json"):
            for c in json.loads((a / name).read_text())["cases"]:
                out.append({"id": c["id"], "turns": list(c["turns"])})
        return out
    if piece == "212":
        out = []
        for name in ("case212-g.json", "case212-s.json"):
            for c in json.loads((a / name).read_text()):
                out.append({"id": c["id"], "turns": [c["turn"]]})
        return out
    if piece == "216":
        out = []
        for name in ("cases216-p1.jsonl", "cases216-p2.jsonl"):
            for line in (a / name).read_text().splitlines():
                if line.strip():
                    c = json.loads(line)
                    out.append({"id": c["id"], "turns": [c["text"]]})
        return out
    if piece == "222":
        d = json.loads((a / "cases222-b1b2.json").read_text())
        groups: dict[str, list[str]] = {}
        for c in d["b1"]:
            groups.setdefault("B1-" + c["id"].rsplit("-", 1)[0],
                              []).append(c["turn"])
        out = [{"id": k, "turns": v} for k, v in groups.items()]
        for key in ("b2_person_multi", "b2_other"):
            for c in d[key]:
                out.append({"id": c["id"], "turns": [c["teach"], c["probe"]]})
        return out
    if piece == "223":
        import fable_loop223_probe as P223
        out = []
        for line in (a / "questions223.jsonl").read_text().splitlines():
            if line.strip():
                c = json.loads(line)
                out.append({"id": c["id"],
                            "turns": list(P223.TEACHES) + [c["text"]],
                            "score_last_only": True})
        return out
    raise ValueError(piece)


def run(piece: str, arm: str, out: Path, work: Path) -> None:
    t0 = time.time()
    if piece == "226":
        import fable_source226_run as R226
        agent, cfg = OWN_226 if arm == "own" else AGENT_PATH[arm]
        R226.run(str(ROOT / agent), str(ROOT / cfg),
                 str(ART["226"] / "cases226.json"), str(work), str(out))
        print(f"226/{arm} {time.time() - t0:.1f}s", flush=True)
        return
    import fable_loop90_agent as L90
    snap209 = None
    if piece == "209":
        import fable_writescreen209_probe as P209
        snap209 = P209.snapshot
    build, dcfg = builder(piece, arm)
    rows = []
    for i, c in enumerate(cases_for(piece)):
        d = work / f"{i:03d}"
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
        cfg = copy.deepcopy(dcfg)
        cfg["state_dir"] = str(d)
        cfg["sleep_threshold"] = 100000
        loop = build(cfg)
        replies = [" ".join(loop.turn(t)).strip() for t in c["turns"]]
        routed = getattr(loop, "last_routed", None) or {}
        row = {"id": c["id"], "turns": c["turns"], "replies": replies,
               "intent": routed.get("intent"),
               "triples": [list(x) for x in L90.notebook_triples(loop.nb)]}
        if snap209 is not None:
            row["snap209"] = snap209(loop)
        rows.append(row)
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    print(f"{piece}/{arm}: {len(rows)} cases {time.time() - t0:.1f}s",
          flush=True)


# ------------------------------------------------------------------ judge
def _flat(piece: str, rows: list[dict]) -> dict:
    """case id -> comparable record (replies + stored)."""
    out = {}
    if piece == "226":
        for r in rows:
            for j, t in enumerate(r["turns"]):
                if t["text"] == "<RESTART>":
                    continue
                out[f"{r['id']}.t{j}"] = {"reply": t["reply"],
                                          "stored": t["triples"],
                                          "events_added": t["events_added"]}
        return out
    for r in rows:
        rec = {"replies": r["replies"], "stored": r["triples"]}
        if "snap209" in r:
            rec["stored"] = r["snap209"]
        out[r["id"]] = rec
    return out


def sealed_check(piece: str, own: dict) -> list[str]:
    """Own-arm rerun vs the piece's sealed per-case rows (driver fidelity).

    Returns ids that disagree (empty list = rerun reproduces the seal).
    """
    a = ART[piece]
    bad = []
    if piece == "209":
        for name, key in (("w1-report.json", "w1"), ("w2-report.json", "w2")):
            rep = json.loads((a / "probe" / name).read_text())
            for r in rep["rows"]:
                o = own[r["id"]]
                if key == "w1":
                    ok = (o["replies"][-1][:200] == r["reply"]
                          and o["stored"]["stored"] == r["stored"])
                else:
                    ok = (o["replies"] == r["replies"]
                          and o["stored"]["stored"] == r["stored"])
                if not ok:
                    bad.append(r["id"])
    elif piece == "212":
        for name, rk, fk in (("m1-212-g.json", "new_reply", "new_facts"),
                             ("m2-212-s.json", "reply", "facts")):
            for r in json.loads((a / name).read_text()):
                o = own[r["id"]]
                if not (o["replies"][-1][:160] == r[rk]
                        and o["stored"] == r[fk]):
                    bad.append(r["id"])
    elif piece == "216":
        for name in ("panel216-p1.json", "panel216-p2.json"):
            for r in json.loads((a / name).read_text())["new"]:
                if own[r["id"]]["replies"][-1] != r["reply"]:
                    bad.append(r["id"])
    elif piece == "223":
        rep = json.loads((a / "probe223-registered.json").read_text())
        for r in rep["rows"]:
            if r.get("phase") != "case":
                continue
            if own[r["id"]]["replies"][-1] != r["new"]:
                bad.append(r["id"])
    elif piece == "226":
        for r in json.loads((a / "runs/rows226.json").read_text()):
            for j, t in enumerate(r["turns"]):
                if t["text"] == "<RESTART>":
                    continue
                o = own[f"{r['id']}.t{j}"]
                if not (o["reply"] == t["reply"]
                        and o["stored"] == t["triples"]):
                    bad.append(f"{r['id']}.t{j}")
    return bad


def judge(d: Path, pred_path: Path | None) -> int:
    pred = {}
    if pred_path is not None and pred_path.exists():
        for m in json.loads(pred_path.read_text())["L1"]:
            pred[(m["piece"], m["id"])] = m
    summary = {}
    all_ok = True
    for piece in PIECES:
        rows = {}
        for arm in ("own", "k", "l"):
            p = d / f"l1-{piece}-{arm}.json"
            rows[arm] = _flat(piece, json.loads(p.read_text()))
        own, k, l = rows["own"], rows["k"], rows["l"]
        fidelity = sealed_check(piece, own) if piece != "222" else None
        diff_own, unpred, wrongpred, pred_hit = [], [], [], []
        for cid in own:
            if l[cid] == own[cid]:
                if (piece, cid) in pred:
                    wrongpred.append(cid)  # predicted to move, did not
                continue
            diff_own.append(cid)
            m = pred.get((piece, cid))
            if m is None:
                unpred.append(cid)
                continue
            got = l[cid]
            want = m.get("expect_l")
            if want is not None and got != want:
                wrongpred.append(cid)
            else:
                pred_hit.append(cid)
        ok = not unpred and not wrongpred and not fidelity
        all_ok = all_ok and ok
        summary[piece] = {
            "cases": len(own), "l_eq_own": len(own) - len(diff_own),
            "l_ne_own": len(diff_own), "predicted_and_exact": len(pred_hit),
            "unpredicted": unpred, "prediction_wrong": wrongpred,
            "l_eq_k": sum(1 for c in own if l[c] == k[c]),
            "sealed_fidelity_bad": fidelity, "pass": ok}
        print(f"L1 {piece}: {summary[piece]}", flush=True)
    summary["verdict"] = "PASS" if all_ok else "FAIL"
    (d / "l1-summary.json").write_text(json.dumps(summary, indent=1),
                                       encoding="utf-8")
    print("L1", summary["verdict"], flush=True)
    return 0 if all_ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--piece", required=True, choices=PIECES)
    r.add_argument("--arm", required=True, choices=("own", "k", "l"))
    r.add_argument("--out", required=True)
    r.add_argument("--work", required=True)
    j = sub.add_parser("judge")
    j.add_argument("--dir", required=True)
    j.add_argument("--pred", default=None)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        run(a.piece, a.arm, Path(a.out), Path(a.work))
        return 0
    return judge(Path(a.dir), Path(a.pred) if a.pred else None)


if __name__ == "__main__":
    sys.exit(main())
