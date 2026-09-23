#!/usr/bin/env python3
"""Merge 138n -- mark M1 driver: each reading piece's own sealed dev /
case files (NOT blind panels) on three arms: own (the piece's own agent),
m (138m) and n (138n). Piece files are only read.

Runner per piece = the piece's own runner semantics, one fresh agent per
case, every turn recorded:
  loop mode   (221, 221b: their runners build the agent in-process and
               call loop.turn, reply = " ".join(lines))
  daemon mode (221c, 229, 237, 232c, 232c parity, 236: fresh daemon per
               case via fable_marks123_all.make_daemon, mailbox files,
               reply = outbox text stripped)
Every arm uses sleep_threshold 100000, as every piece runner did.

Per case the record is: replies per turn, active taught triples after each
turn (fable_loop90_agent.notebook_triples, sorted) and all taught facts
ever written after each turn (active or not, sorted).

usage:
  claude_138n_l1.py run --arm own|m|n --out-dir DIR --work DIR [--pieces ..]
  claude_138n_l1.py sealed --dir DIR [--out F]   (own arm vs sealed rows)
  claude_138n_l1.py judge --dir DIR --pred predicted_moves138n.json --out F
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

A = ROOT / "artifacts"
ART = {
    "221": A / "claude-tableask221-20260922",
    "221b": A / "claude-storedrel221b-20260922",
    "221c": A / "claude-qnorm221c-20260922",
    "229": A / "claude-tableteach229-20260922",
    "237": A / "claude-table237-20260922",
    "232c": A / "claude-fullname232c-20260922",
    "236": A / "claude-firstname236-20260922",
}
PIECES = ("221", "221b", "221c", "229", "237", "232c", "232cp", "236")
MODE = {"221": "loop", "221b": "loop"}  # everything else: daemon
# daemon-mode own agents (agent script, config json)
OWN_DAEMON = {
    "221c": ("scripts/claude_loop221c_agent.py",
             ART["221c"] / "loop221c-config.json"),
    "229": ("scripts/claude_loop229_agent.py",
            ART["229"] / "loop229-config.json"),
    "237": ("scripts/claude_loop237_agent.py",
            ART["237"] / "loop237-config.json"),
    "232c": ("scripts/claude_loop232c_agent.py",
             A / "claude-fullname232-20260922" / "loop232-config.json"),
    "232cp": ("scripts/claude_loop232c_agent.py",
              A / "claude-fullname232-20260922" / "loop232-config.json"),
    "236": ("scripts/claude_loop236_agent.py",
            ART["236"] / "loop236-config.json"),
}
MERGE = {
    "m": ("scripts/claude_loop138m_agent.py",
          A / "claude-merge138m-20260922" / "loop138m-config.json",
          "claude_loop138m_agent", "DEFAULT_CONFIG138M", "build_agent138m"),
    "n": ("scripts/claude_loop138n_agent.py",
          A / "claude-merge138n-20260922" / "loop138n-config.json",
          "claude_loop138n_agent", "DEFAULT_CONFIG138N", "build_agent138n"),
}


def _load(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(
        encoding="utf-8").splitlines() if x.strip()]


def _setup(it: dict) -> list[str]:
    s = it.get("setup") or []
    if isinstance(s, str):
        s = [s]
    return [str(x) for x in s]


# ------------------------------------------------------------- case lists
def cases_for(piece: str) -> list[dict]:
    if piece == "221":
        return [{"id": c["id"], "turns": list(c["turns"])}
                for c in _jsonl(ART["221"] / "dev221.jsonl")]
    if piece in ("221b", "221c", "237", "232c", "236"):
        f = {"221b": "dev221b.jsonl", "221c": "dev221c.jsonl",
             "237": "dev237.jsonl", "232c": "dev232c.jsonl",
             "236": "dev236.jsonl"}[piece]
        out = []
        for c in _jsonl(ART[piece] / f):
            turns = _setup(c)
            if c.get("question"):
                turns.append(str(c["question"]))
            out.append({"id": c["id"], "turns": turns})
        return out
    if piece == "229":
        return [{"id": c["id"], "turns": _setup(c) + [c["statement"]]}
                for c in _jsonl(ART["229"] / "dev229.jsonl")]
    if piece == "232cp":
        return [{"id": f"p{r['t']:02d}:{r['name']}", "turns": list(r["turns"])}
                for r in _jsonl(ART["232c"] / "registered" / "parity.jsonl")]
    raise ValueError(piece)


# ---------------------------------------------------------------- runners
def _all_taught(nb) -> list:
    import fable_loop90_agent as L90
    out = []
    for fact in nb.facts.values():
        if fact.get("source") != "taught":
            continue
        out.append([nb.entities.get(fact["subject"], "?"), fact["relation"],
                    L90._display(nb, fact["value"])])
    return sorted(out)


def _active(nb) -> list:
    import fable_loop90_agent as L90
    return sorted(list(map(str, x)) for x in L90.notebook_triples(nb))


def _own_loop_builder(piece: str):
    if piece == "221":
        import fable_loop221_agent as L221
        return L221.DEFAULT_CONFIG221, L221.build_agent221
    import claude_loop221b_agent as L221B
    return L221B.DEFAULT_CONFIG221B, L221B.build_agent221b


def _merge_loop_builder(arm: str):
    _a, cfgp, mod_name, cfg_name, fn = MERGE[arm]
    mod = __import__(mod_name)
    cfg = copy.deepcopy(getattr(mod, cfg_name))
    cfg.update(_load(cfgp))
    return cfg, getattr(mod, fn)


def run_loop_case(default_cfg, build_fn, turns, sd: Path) -> dict:
    shutil.rmtree(sd, ignore_errors=True)
    sd.mkdir(parents=True)
    cfg = copy.deepcopy(default_cfg)
    cfg["state_dir"] = str(sd)
    cfg["sleep_threshold"] = 100000
    loop = build_fn(cfg)
    rec = {"replies": [], "active": [], "all": []}
    for t in turns:
        rec["replies"].append(" ".join(loop.turn(t)))
        rec["active"].append(_active(loop.nb))
        rec["all"].append(_all_taught(loop.nb))
    shutil.rmtree(sd, ignore_errors=True)
    return rec


def run_daemon_case(dcls, base_cfg, turns, root: Path) -> dict:
    import fable_marks123_all as M
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    d = M.make_daemon(dcls, base_cfg, root)
    rec = {"replies": [], "active": [], "all": []}
    for j, t in enumerate(turns):
        f = root / "inbox" / f"m{j:02d}.txt"
        f.write_text(t, encoding="utf-8")
        d.process_file(f)
        rec["replies"].append((root / "outbox" / f"m{j:02d}.txt").read_text(
            encoding="utf-8").strip())
        rec["active"].append(_active(d.loop.nb))
        rec["all"].append(_all_taught(d.loop.nb))
    shutil.rmtree(root, ignore_errors=True)
    return rec


def cmd_run(arm: str, out_dir: Path, work: Path, pieces) -> None:
    import fable_marks123_all as M
    out_dir.mkdir(parents=True, exist_ok=True)
    for piece in pieces:
        t0 = time.time()
        mode = MODE.get(piece, "daemon")
        w = work / f"{piece}-{arm}"
        if mode == "loop":
            cfg, fn = (_own_loop_builder(piece) if arm == "own"
                       else _merge_loop_builder(arm))
        else:
            agent, cfgp = (OWN_DAEMON[piece] if arm == "own"
                           else MERGE[arm][:2])
            _mod, dcls, _b, _c = M.load_agent(str(ROOT / agent))
            base = M.load_base_cfg(str(cfgp))
        rows = []
        for i, c in enumerate(cases_for(piece)):
            sd = w / f"{i:03d}"
            if mode == "loop":
                r = run_loop_case(cfg, fn, c["turns"], sd)
            else:
                r = run_daemon_case(dcls, base, c["turns"], sd)
            rows.append({"id": c["id"], "turns": c["turns"], **r})
        shutil.rmtree(w, ignore_errors=True)
        (out_dir / f"{piece}-{arm}.json").write_text(
            json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{piece}/{arm}: {len(rows)} cases {time.time() - t0:.1f}s",
              flush=True)


# ---------------------------------------------------- sealed own fidelity
def _tl(x) -> list:
    return sorted(list(map(str, t)) for t in (x or []))


def sealed_check(piece: str, row: dict, ref: dict) -> list[str]:
    """Return the list of mismatching fields ([] = the row reproduces it)."""
    bad = []
    rep = row["replies"]
    if piece == "221":
        want = [t["reply221"] for t in sorted(ref, key=lambda t: t["k"])]
        if rep != want:
            bad.append("replies")
        wrote = [t["wrote221"] for t in sorted(ref, key=lambda t: t["k"])]
        got = [row["all"][0] != []] + [row["all"][k] != row["all"][k - 1]
                                       for k in range(1, len(rep))]
        if wrote != got:
            bad.append("wrote")
    elif piece == "221b":
        r = ref["221b"]
        if rep[-1] != r["reply"]:
            bad.append("reply")
        stored = row["active"][-2] if len(rep) > 1 else []
        if _tl(stored) != _tl(r["stored"]):
            bad.append("stored")
        if (row["all"][-1] != row["all"][-2] if len(rep) > 1
                else row["all"][-1] != []) != r["q_wrote"]:
            bad.append("q_wrote")
    elif piece == "221c":
        r = ref["arms"]["221c"]
        if rep[:-1] != r["setup_replies"]:
            bad.append("setup_replies")
        if rep[-1] != r["reply"]:
            bad.append("reply")
        if row["active"][-1] != _tl(r["triples_after"]):
            bad.append("triples_after")
    elif piece == "229":
        if rep[:-1] != ref["setup_replies"]:
            bad.append("setup_replies")
        if rep[-1] != ref["reply"]:
            bad.append("reply")
        before = set(map(tuple, row["active"][-2])) if len(rep) > 1 \
            else set()
        after = set(map(tuple, row["active"][-1]))
        if sorted(map(list, after - before)) != _tl(ref["new"]) or \
                sorted(map(list, before - after)) != _tl(ref["gone"]):
            bad.append("new/gone")
    elif piece == "237":
        if rep[:-1] != ref["setup_replies"]:
            bad.append("setup_replies")
        if rep[-1] != ref["reply"]:
            bad.append("reply")
        if row["active"][-1] != _tl(ref["stored_after"]):
            bad.append("stored_after")
    elif piece in ("232c", "236"):
        if rep != [t["reply"] for t in ref["turns"]]:
            bad.append("replies")
        if row["active"] != [_tl(t["active"]) for t in ref["turns"]]:
            bad.append("active")
        if row["all"] != [_tl(t["all"]) for t in ref["turns"]]:
            bad.append("all")
    elif piece == "232cp":
        if rep != ref["replies"]:
            bad.append("replies")
        if row["active"][-1] != _tl(ref["stored"]):
            bad.append("stored")
    return bad


def sealed_refs(piece: str) -> dict:
    if piece == "221":
        ref: dict = {}
        for t in _jsonl(ART["221"] / "dev-sealed" / "turns.jsonl"):
            ref.setdefault(t["id"], []).append(t)
        return ref
    if piece == "221b":
        return {r["id"]: r for r in _jsonl(ART["221b"] / "dev" / "rows.jsonl")}
    if piece == "221c":
        return {r["id"]: r for r in _jsonl(ART["221c"] / "dev" / "rows.jsonl")}
    if piece == "229":
        return {r["id"]: r for r in
                _jsonl(ART["229"] / "runs" / "dev-229.jsonl")}
    if piece == "237":
        return {r["id"]: r for r in _jsonl(ART["237"] / "dev" / "rows237.jsonl")}
    if piece == "232c":
        return {r["id"]: r for r in
                _jsonl(ART["232c"] / "registered" / "dev-232c.jsonl")}
    if piece == "232cp":
        return {f"p{r['t']:02d}:{r['name']}": r for r in
                _jsonl(ART["232c"] / "registered" / "parity.jsonl")}
    if piece == "236":
        return {r["id"]: r for r in
                _jsonl(ART["236"] / "dev236-rows236.jsonl")}
    raise ValueError(piece)


def cmd_sealed(d: Path, pieces) -> dict:
    out = {}
    for piece in pieces:
        rows = {r["id"]: r for r in _load(d / f"{piece}-own.json")}
        ref = sealed_refs(piece)
        bad = {}
        for cid, rr in ref.items():
            if cid not in rows:
                bad[cid] = ["missing"]
                continue
            b = sealed_check(piece, rows[cid], rr)
            if b:
                bad[cid] = b
        out[piece] = {"n_sealed": len(ref), "n_run": len(rows),
                      "unmatched": bad}
        print(f"sealed {piece}: {len(ref) - len(bad)}/{len(ref)} match"
              f"{' BAD ' + json.dumps(dict(list(bad.items())[:6])) if bad else ''}",
              flush=True)
    return out


# ------------------------------------------------------------------ judge
def rec(r: dict) -> dict:
    return {"replies": r["replies"], "active": r["active"], "all": r["all"]}


def cmd_judge(d: Path, pred_path: Path | None, out: Path, pieces) -> int:
    pred = _load(pred_path)["m1"] if pred_path else {}
    res = {"pieces": {}, "unpredicted": [], "predicted_ok": [],
           "predicted_wrong": [], "predicted_not_moved": []}
    for piece in pieces:
        own = {r["id"]: r for r in _load(d / f"{piece}-own.json")}
        n = {r["id"]: r for r in _load(d / f"{piece}-n.json")}
        m = {r["id"]: r for r in _load(d / f"{piece}-m.json")}
        pp = pred.get(piece, {})
        n_same = 0
        moves = []
        for cid, orow in own.items():
            nrow = n[cid]
            key = f"{piece}/{cid}"
            if rec(orow) == rec(nrow):
                n_same += 1
                if cid in pp:
                    res["predicted_not_moved"].append(key)
                continue
            mv = {"id": key, "turns": orow["turns"],
                  "own_replies": orow["replies"],
                  "n_replies": nrow["replies"],
                  "m_replies": m[cid]["replies"],
                  "active_same": orow["active"] == nrow["active"],
                  "all_same": orow["all"] == nrow["all"],
                  "own_active_last": orow["active"][-1],
                  "n_active_last": nrow["active"][-1],
                  "n_equals_m": rec(nrow) == rec(m[cid])}
            moves.append(mv)
            if cid not in pp:
                res["unpredicted"].append(key)
            elif rec(nrow) == pp[cid]["expect_n"]:
                res["predicted_ok"].append(key)
            else:
                res["predicted_wrong"].append(key)
        res["pieces"][piece] = {"n": len(own), "same_as_own": n_same,
                                "moved": len(moves), "moves": moves}
        print(f"judge {piece}: {n_same}/{len(own)} same as own, "
              f"{len(moves)} moved", flush=True)
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
    r.add_argument("--arm", choices=["own", "m", "n"], required=True)
    r.add_argument("--out-dir", required=True)
    r.add_argument("--work", required=True)
    r.add_argument("--pieces", nargs="*", default=list(PIECES))
    s = sub.add_parser("sealed")
    s.add_argument("--dir", required=True)
    s.add_argument("--out", default=None)
    s.add_argument("--pieces", nargs="*", default=list(PIECES))
    j = sub.add_parser("judge")
    j.add_argument("--dir", required=True)
    j.add_argument("--pred", default=None)
    j.add_argument("--out", required=True)
    j.add_argument("--pieces", nargs="*", default=list(PIECES))
    a = ap.parse_args(argv)
    if a.cmd == "run":
        cmd_run(a.arm, Path(a.out_dir), Path(a.work), a.pieces)
        return 0
    if a.cmd == "sealed":
        res = cmd_sealed(Path(a.dir), a.pieces)
        if a.out:
            Path(a.out).write_text(json.dumps(res, indent=1),
                                   encoding="utf-8")
        return 0 if all(not v["unmatched"] for v in res.values()) else 1
    return cmd_judge(Path(a.dir), Path(a.pred) if a.pred else None,
                     Path(a.out), a.pieces)


if __name__ == "__main__":
    sys.exit(main())
