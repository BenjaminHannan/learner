#!/usr/bin/env python3
"""Merge 138m -- mark M1 driver: each piece's own sealed dev cases on four
arms (own = the piece's own agent, head = the head of its line, l = 138l,
m = 138m), one generic session runner. Piece files are only read.

Line heads: 219, 230 -> 230c (the name line's head, 230c wraps 230b wraps
230 wraps 219); 227, 227b -> 227c (the identity line's head). For 230c,
227c, 224c, 233 and 234 the head is the piece itself.

Cases (fresh loop per session, same turns as each piece's own driver):
  219   219's m1/m2/m3 sessions (as claude_yesprefix230_marks --m1).
  230   the same 219 sessions ("S:") + 230's m2 cases taught ("T:",
        ["My name is X.", q]) and untaught ("U:", [q]).
  230c  230c dev-cases.json (22).
  227   227 m1 ("m1:", [teach]+[text]) + m2 ("m2:").
  227b  227 m1+m2 ("227m1:", "227m2:") + 227b m2 sessions ("b2:").
  227c  227c m1 ("c1:", [teach]+[text]+follow turns), m2 untaught ("c2u:")
        and after "My name is Hedda." ("c2t:"), m3 = 227 m1+m2 + 227b m2
        ("c3:<src>:<id>").
  224c  claude_224c_cases.run_case (natural + forced on cases224c.json,
        "nat:"/"frc:"; natural on 224b's B1 cases, "b1:"), with that
        module's build swapped for the arm's builder (driver-only).
  233   dev233.jsonl via mailbox daemons (as claude_polite233_run).
  234   234 dev-cases.json: setup turns then the test turn.

Every arm sets sleep_threshold 100000 (no sleep inside a short session).

usage:
  claude_138m_l1.py run --arm own|head|l|m --out-dir DIR --work DIR
  claude_138m_l1.py sealed --dir DIR           (own arm vs sealed rows)
  claude_138m_l1.py judge --dir DIR --pred predicted_moves138m.json --out F
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
    "219": A / "fable-selfname219-20260922",
    "230": A / "claude-yesprefix230-20260922",
    "230c": A / "claude-namecheck230c-20260922",
    "227": A / "fable-identity227-20260922",
    "227b": A / "claude-name227b-20260922",
    "227c": A / "claude-identity227c-20260922",
    "224c": A / "claude-decline224c-20260922",
    "224b": A / "fable-decline224-20260922" / "224b",
    "233": A / "claude-polite233-20260922",
    "234": A / "claude-smalltalk234-20260922",
}
PIECES = ("219", "230", "230c", "227", "227b", "227c", "224c", "233", "234")
AGENT = {  # tag -> (module, DEFAULT_CONFIG name, build fn name, config json)
    "219": ("fable_loop219_agent", "DEFAULT_CONFIG219", "build_agent219",
            ART["219"] / "loop219-config.json"),
    "230": ("claude_loop230_agent", "DEFAULT_CONFIG230", "build_agent230",
            ART["230"] / "loop230-config.json"),
    "230c": ("claude_loop230c_agent", "DEFAULT_CONFIG230C",
             "build_agent230c", ART["230c"] / "loop230c-config.json"),
    "227": ("fable_loop227_agent", "DEFAULT_CONFIG227", "build_agent227",
            ART["227"] / "loop227-config.json"),
    "227b": ("claude_loop227b_agent", "DEFAULT_CONFIG227B",
             "build_agent227b", ART["227b"] / "loop227b-config.json"),
    "227c": ("claude_loop227c_agent", "DEFAULT_CONFIG227C",
             "build_agent227c", ART["227c"] / "loop227c-config.json"),
    "234": ("claude_loop234_agent", "DEFAULT_CONFIG234", "build_agent234",
            ART["234"] / "loop234-config.json"),
    "l": ("claude_loop138l_agent", "DEFAULT_CONFIG138L", "build_agent138l",
          A / "claude-merge138l-20260922" / "loop138l-config.json"),
    "m": ("claude_loop138m_agent", "DEFAULT_CONFIG138M", "build_agent138m",
          A / "claude-merge138m-20260922" / "loop138m-config.json"),
}
HEAD = {"219": "230c", "230": "230c", "227": "227c", "227b": "227c"}
CFG224C = A / "fable-agent138i-20260922" / "loop138i-config.json"
CFG233 = "artifacts/claude-polite233-20260922/loop233-config.json"


def arm_tag(piece: str, arm: str) -> str:
    if arm in ("l", "m"):
        return arm
    if arm == "head":
        return HEAD.get(piece, piece)
    return piece


def build(tag: str, state_dir: str):
    mod_name, cfg_name, fn_name, cfg_path = AGENT[tag]
    mod = __import__(mod_name)
    cfg = copy.deepcopy(getattr(mod, cfg_name))
    cfg.update(json.loads(Path(cfg_path).read_text(encoding="utf-8")))
    cfg["state_dir"] = state_dir
    cfg["sleep_threshold"] = 100000
    return getattr(mod, fn_name)(cfg)


def facts(loop) -> list:
    return sorted(
        (f.get("subject"), f.get("relation"),
         json.dumps(f.get("value"), sort_keys=True), f.get("source"),
         bool(loop.nb.active(fid)))
        for fid, f in loop.nb.facts.items())


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


# ------------------------------------------------------------- case lists
def _sessions219() -> list[dict]:
    a = ART["219"]
    out = []
    c1 = _load(a / "m1-cases.json")
    for s in c1["sessions"]:
        out.append({"id": s["id"], "turns": [s["teach"]] + c1["probes"]})
    c2 = _load(a / "m2-cases.json")
    for s in c2["sessions"]:
        out.append({"id": s["id"], "turns": list(c2["probes"])})
    c3 = _load(a / "m3-cases.json")
    for s in c3["stored"]:
        out.append({"id": s["id"], "turns": [c3["teach_template"].format(
            age=s["age"])] + c3["probes"]})
    for i in range(int(c3["n_empty"])):
        out.append({"id": f"M3-E{i + 1:02d}", "turns": list(c3["probes"])})
    return out


def _sessions227() -> list[dict]:
    out = []
    for f, p in (("m1-cases.json", "m1"), ("m2-cases.json", "m2")):
        for c in _load(ART["227"] / f):
            out.append({"id": f"{p}:{c['id']}",
                        "turns": ([c["teach"]] if c.get("teach") else [])
                        + [c["text"]]})
    return out


def cases_for(piece: str) -> list[dict]:
    if piece == "219":
        return _sessions219()
    if piece == "230":
        out = [{"id": "S:" + s["id"], "turns": s["turns"]}
               for s in _sessions219()]
        for c in _load(ART["230"] / "m2-cases.json")["cases"]:
            out.append({"id": "T:" + c["id"],
                        "turns": [f"My name is {c['name']}.", c["text"]]})
            out.append({"id": "U:" + c["id"], "turns": [c["text"]]})
        return out
    if piece == "230c":
        return [{"id": c["id"], "turns": list(c["turns"])}
                for c in _load(ART["230c"] / "dev-cases.json")]
    if piece == "227":
        return _sessions227()
    if piece == "227b":
        out = [{"id": "227" + s["id"], "turns": s["turns"]}
               for s in _sessions227()]
        for s in _load(ART["227b"] / "m2-cases.json"):
            out.append({"id": "b2:" + s["id"], "turns": list(s["turns"])})
        return out
    if piece == "227c":
        out = []
        for c in _load(ART["227c"] / "m1-cases.json")["cases"]:
            out.append({"id": "c1:" + c["id"],
                        "turns": ([c["teach"]] if c.get("teach") else [])
                        + [c["text"]] + [f[0] for f in c.get("follow", [])]})
        for c in _load(ART["227c"] / "m2-cases.json")["cases"]:
            out.append({"id": "c2u:" + c["id"], "turns": [c["text"]]})
            out.append({"id": "c2t:" + c["id"],
                        "turns": ["My name is Hedda.", c["text"]]})
        for s in _sessions227():
            out.append({"id": "c3:227-" + s["id"], "turns": s["turns"]})
        for s in _load(ART["227b"] / "m2-cases.json"):
            out.append({"id": "c3:227b-m2:" + s["id"],
                        "turns": list(s["turns"])})
        return out
    if piece == "234":
        return [{"id": c["id"], "turns": list(c.get("setup") or [])
                 + [c["turn"]]}
                for c in _load(ART["234"] / "dev-cases.json")["cases"]]
    raise ValueError(piece)


# ---------------------------------------------------------------- runners
def run_session(tag: str, turns: list[str], sd: Path) -> dict:
    shutil.rmtree(sd, ignore_errors=True)
    sd.mkdir(parents=True)
    loop = build(tag, str(sd))
    lines, writes = [], []
    for t in turns:
        before = set(facts(loop))
        lines.append(list(loop.turn(t)))
        writes.append(len(set(facts(loop)) ^ before))
    snap = json.dumps({"facts": facts(loop), "entities": loop.nb.entities},
                      sort_keys=True)
    return {"lines": lines, "writes": writes, "snap": snap}


def run_224c(tag: str, work: Path) -> list[dict]:
    import claude_224c_cases as C
    if tag == "224c":
        def b(_agent, sd):
            return C.__dict__["_orig_build"]("224c", sd)
    else:
        def b(_agent, sd):
            return build(tag, sd)
    C.__dict__.setdefault("_orig_build", C.build)
    C.build = b
    rows = []
    try:
        work.mkdir(parents=True, exist_ok=True)
        cases = _load(ART["224c"] / "cases224c.json")["cases"]
        for mode, pre in (("natural", "nat:"), ("forced", "frc:")):
            for c in cases:
                r = C.run_case("x", mode, c, work)
                rows.append({"id": pre + c["id"], **_rec224(r)})
        for c in _load(ART["224b"] / "cases224b.json")["cases"]:
            r = C.run_case("x", "natural", c, work)
            rows.append({"id": "b1:" + c["id"], **_rec224(r)})
    finally:
        C.build = C.__dict__["_orig_build"]
    return rows


def _rec224(r: dict) -> dict:
    return {"setup_replies": r["setup_replies"], "reply": r["reply"],
            "writes": r["writes"], "kind224": r["kind224"],
            "is_q1": r["is_q1"], "gold_hit": r["gold_hit"],
            "stated_other_value": r["stated_other_value"]}


def run_233(tag: str, work: Path) -> list[dict]:
    import claude_polite233_run as P
    import fable_marks123_all as M
    if tag == "233":
        import claude_loop233_agent as L233
        cls, cfg = L233.Loop233Daemon, M.load_base_cfg(str(ROOT / CFG233))
    else:
        mod_name, _c, _b, cfg_path = AGENT[tag]
        mod = __import__(mod_name)
        cls = getattr(mod, "Loop138%sDaemon" % tag)
        cfg = M.load_base_cfg(str(cfg_path))
    rows = []
    for line in (ART["233"] / "dev233.jsonl").read_text(
            encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        r = P.run_agent(cls, cfg, work / case["id"], case)
        rows.append({"id": case["id"], "reply": r["reply"],
                     "setup_replies": r["setup_replies"],
                     "triples_after": r["triples_after"],
                     "qwrite": r["qwrite"],
                     "score": P.score_one(case, r["reply"])})
    return rows


def cmd_run(arm: str, out_dir: Path, work: Path, pieces) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for piece in pieces:
        t0 = time.time()
        tag = arm_tag(piece, arm)
        if arm == "head" and tag == piece:
            continue  # head == own: not re-run
        w = work / f"{piece}-{arm}"
        if piece == "224c":
            rows = run_224c(tag, w)
        elif piece == "233":
            rows = run_233(tag, w)
        else:
            rows = []
            for i, c in enumerate(cases_for(piece)):
                r = run_session(tag, c["turns"], w / f"{i:03d}")
                rows.append({"id": c["id"], "turns": c["turns"], **r})
        shutil.rmtree(w, ignore_errors=True)
        (out_dir / f"{piece}-{arm}.json").write_text(
            json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{piece}/{arm} ({tag}): {len(rows)} cases "
              f"{time.time() - t0:.1f}s", flush=True)


# ---------------------------------------------------- sealed own fidelity
def _joined(lines_per_turn) -> list[str]:
    return [" ".join(x) for x in lines_per_turn]


def sealed_refs(piece: str) -> dict:
    """case id -> sealed reference (lines per turn, or joined strings, or
    a 224c/233/234 reply) from the piece's own registered rows."""
    ref = {}
    if piece in ("219", "230"):
        key = "r219" if piece == "219" else "r230"
        pre = "" if piece == "219" else "S:"
        for r in _load(ART["230"] / "m1-rows.json"):
            ref[pre + r["session"]] = ("lines", [p[key] for p in r["per"]])
        if piece == "230":
            for r in _load(ART["230"] / "m2-rows.json"):
                ref["T:" + r["id"]] = ("last_lines", r["taught_r230"])
                ref["U:" + r["id"]] = ("last_lines", r["untaught_r230"])
    elif piece == "230c":
        for r in _load(ART["230c"] / "dev-rows.json")["rows"]:
            ref[r["id"]] = ("lines", [p["r230c"] for p in r["per"]])
    elif piece == "227":
        for r in _load(ART["227"] / "m1-rows.json"):
            ref["m1:" + r["id"]] = ("last_joined", r["reply"])
        for r in _load(ART["227"] / "m2-rows.json"):
            ref["m2:" + r["id"]] = ("joined", r["r227"])
    elif piece == "227b":
        for r in _load(ART["227b"] / "m1-rows.json"):
            p = "227m1:" if r["src"] == "227-M1" else "227m2:"
            ref[p + r["id"]] = ("joined", r["r227b"])
        for r in _load(ART["227b"] / "m2-rows.json"):
            ref["b2:" + r["id"]] = ("joined", r["replies"])
    elif piece == "227c":
        for r in _load(ART["227c"] / "m1-rows.json"):
            ref["c1:" + r["id"]] = ("joined", r["replies"])
        for r in _load(ART["227c"] / "m2-rows.json"):
            p = "c2t:" if r["teach"] else "c2u:"
            ref[p + r["id"]] = ("last_lines", r["r227c"]) \
                if not r["teach"] else ("joined", r["r227c"])
        for r in _load(ART["227c"] / "m3-rows.json"):
            ref["c3:" + r["src"] + ":" + r["id"]] = ("joined", r["r227c"])
    elif piece == "224c":
        runs = ART["224c"] / "runs"
        for f, p in (("cases-224c-natural.json", "nat:"),
                     ("cases-224c-forced.json", "frc:"),
                     ("m1-b1-224c.json", "b1:")):
            for r in _load(runs / f)["rows"]:
                ref[p + r["id"]] = ("reply224", [r["reply"], r["writes"]])
    elif piece == "233":
        for r in _load(ART["233"] / "dev233-registered.json")["rows"]:
            ref[r["id"]] = ("reply233", r["reply233"])
    elif piece == "234":
        for r in _load(ART["234"] / "dev-rows.json")["rows"]:
            ref[r["id"]] = ("last_lines", r["r234"])
    return ref


def _matches(kind: str, want, row: dict) -> bool:
    if kind == "lines":
        return row["lines"] == want
    if kind == "last_lines":
        return row["lines"][-1] == want
    if kind == "joined":
        return _joined(row["lines"]) == want
    if kind == "last_joined":
        return _joined(row["lines"])[-1] == want
    if kind == "reply224":
        return [row["reply"], row["writes"]] == want
    if kind == "reply233":
        return row["reply"] == want
    raise ValueError(kind)


def cmd_sealed(d: Path) -> dict:
    out = {}
    for piece in PIECES:
        rows = {r["id"]: r for r in _load(d / f"{piece}-own.json")}
        ref = sealed_refs(piece)
        bad = sorted(k for k, (kind, want) in ref.items()
                     if k not in rows or not _matches(kind, want, rows[k]))
        out[piece] = {"n_sealed": len(ref), "n_run": len(rows),
                      "unmatched": bad}
        print(f"sealed {piece}: {len(ref) - len(bad)}/{len(ref)} "
              f"match{' BAD ' + str(bad[:8]) if bad else ''}", flush=True)
    return out


# ------------------------------------------------------------------ judge
def _cmp(piece: str, r: dict) -> dict:
    """Comparable record of one case row."""
    if piece == "224c":
        return {"setup": r["setup_replies"], "reply": r["reply"],
                "writes": r["writes"]}
    if piece == "233":
        return {"setup": r["setup_replies"], "reply": r["reply"],
                "triples_after": r["triples_after"]}
    return {"lines": r["lines"], "writes": r["writes"], "snap": r["snap"]}


def cmd_judge(d: Path, pred_path: Path | None, out: Path) -> int:
    pred = _load(pred_path)["m1"] if pred_path else {}
    res = {"pieces": {}, "unpredicted": [], "predicted_ok": [],
           "predicted_wrong": [], "predicted_not_moved": []}
    for piece in PIECES:
        head_file = d / f"{piece}-head.json"
        if not head_file.exists():
            head_file = d / f"{piece}-own.json"
        head = {r["id"]: r for r in _load(head_file)}
        m = {r["id"]: r for r in _load(d / f"{piece}-m.json")}
        l_ = {r["id"]: r for r in _load(d / f"{piece}-l.json")}
        pp = pred.get(piece, {})
        n_same = n_moved = 0
        moves = []
        for cid, hr in head.items():
            mr = m[cid]
            same = _cmp(piece, hr) == _cmp(piece, mr)
            key = f"{piece}/{cid}"
            if same:
                n_same += 1
                if cid in pp:
                    res["predicted_not_moved"].append(key)
                continue
            n_moved += 1
            mv = {"id": key, "head": _cmp(piece, hr), "m": _cmp(piece, mr),
                  "m_equals_l": _cmp(piece, mr) == _cmp(piece, l_[cid])}
            if piece not in ("224c", "233"):
                mv.pop("head")
                mv.pop("m")
                mv["turns"] = hr["turns"]
                mv["head_lines"] = hr["lines"]
                mv["m_lines"] = mr["lines"]
                mv["head_writes"] = hr["writes"]
                mv["m_writes"] = mr["writes"]
                mv["snap_same"] = hr["snap"] == mr["snap"]
            moves.append(mv)
            if cid not in pp:
                res["unpredicted"].append(key)
            else:
                ok = _cmp(piece, mr) == pp[cid]["expect_m"]
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
    r.add_argument("--arm", choices=["own", "head", "l", "m"], required=True)
    r.add_argument("--out-dir", required=True)
    r.add_argument("--work", required=True)
    r.add_argument("--pieces", nargs="*", default=list(PIECES))
    s = sub.add_parser("sealed")
    s.add_argument("--dir", required=True)
    s.add_argument("--out", default=None)
    j = sub.add_parser("judge")
    j.add_argument("--dir", required=True)
    j.add_argument("--pred", default=None)
    j.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        cmd_run(a.arm, Path(a.out_dir), Path(a.work), a.pieces)
        return 0
    if a.cmd == "sealed":
        res = cmd_sealed(Path(a.dir))
        if a.out:
            Path(a.out).write_text(json.dumps(res, indent=1),
                                   encoding="utf-8")
        return 0 if all(not v["unmatched"] for v in res.values()) else 1
    return cmd_judge(Path(a.dir), Path(a.pred) if a.pred else None,
                     Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
