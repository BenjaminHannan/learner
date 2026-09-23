#!/usr/bin/env python3
"""Merge 138n -- M7 blind-panel regression helper (TEST-ONLY, run once after
the seal by scripts/claude_138n_m7.sh). Prints COUNTS and item ids only,
never item text.

  run221  --arm n|m --items PANEL --out DIR
      Runs 221's sealed panel runner (scripts/fable_fix221_panel.py, read
      only) unchanged except that its arm "221" is built as 138n / 138m
      (loop mode, a fresh agent per item, sleep threshold 100000, state in
      a fresh temp dir -- exactly how that runner builds its arms). Arm
      "138i" is 221's own base arm, as sealed. The sealed score() is used.
  compare --dir RUN_DIR --out OUT.json
      Per panel, per item: the piece's REGISTERED arm vs 138n (and 138m for
      context), using each panel's own sealed scorer output.
      Bars (all on 138n):
        lost_to_wrong = items RIGHT on the registered arm that are WRONG on
                        138n (the scorer's own wrong flag)            -> 0
        new_wrong     = items WRONG on 138n that are not WRONG on the
                        registered arm                                -> 0
        question_writes on 138n                                       -> 0
        new wrong writes (229/232c: wrong-save / wrong-write items not
                        wrong on the registered arm)                  -> 0
      Also reported (not a bar): right counts per arm, and items right on
      the registered arm but not right on 138n (right -> miss), by id.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
A = ROOT / "artifacts"
REG = {
    "tablepanel221": A / "claude-tableask221-20260922" / "p1panel",
    "tablepanel221b": A / "claude-qnorm221c-20260922" / "panel",
    "teachpanel229": A / "claude-tableteach229-20260922" / "runs",
    "namepanel232c": A / "claude-fullname232c-20260922" / "registered",
    "firstnamepanel236": A / "claude-firstname236-20260922",
    "aliaspanel237": A / "claude-table237-20260922" / "m1panel",
}


def _jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()
            if x.strip()]


# ------------------------------------------------------------ run221
def cmd_run221(arm: str, items: str, out: str, work: str) -> int:
    import fable_fix221_panel as F
    Path(work).mkdir(parents=True, exist_ok=True)
    if arm == "n":
        import claude_loop138n_agent as AG
        base_cfg, build = AG.DEFAULT_CONFIG138N, AG.build_agent138n
    else:
        import claude_loop138m_agent as AG
        base_cfg, build = AG.DEFAULT_CONFIG138M, AG.build_agent138m
    orig = F.build

    def build_arm(a: str):
        if a != "221":
            return orig(a)
        d = tempfile.mkdtemp(prefix=f"m7-221-{arm}-", dir=work)
        cfg = copy.deepcopy(base_cfg)
        cfg["state_dir"] = d
        cfg["sleep_threshold"] = 100000
        return build(cfg)

    F.build = build_arm
    return F.main(["--items", items, "--out", out])


# ------------------------------------------------------------ compare
def _p221(d: Path) -> dict:
    """{(id,turn): (right, wrong)}, question writes (arm '221' column)."""
    rows = {f"{r['id']}#{r['turn_index']}": (bool(r["correct221"]),
                                              bool(r["wrong_value221"]))
            for r in _jsonl(d / "rows.jsonl")}
    qw = [f"{t['id']}#{t['k']}" for t in _jsonl(d / "turns.jsonl")
          if str(t["text"]).strip().endswith("?") and t["wrote221"]]
    return {"items": rows, "question_writes": qw}


def _p221b(d: Path, arm: str) -> dict:
    rows = {}
    qw = []
    for r in _jsonl(d / "rows.jsonl"):
        s = r["arms"][arm]["score"]
        rows[str(r["id"])] = (bool(s["right"]), bool(s["wrong"]))
        if s.get("question_wrote"):
            qw.append(str(r["id"]))
    return {"items": rows, "question_writes": qw}


def _p229(score: Path) -> dict:
    d = _jl(score)
    rows = {}
    for it in d["per_item"]:
        x = it["229"]
        rows[str(it["id"])] = (bool(x["right"]), bool(x["wrong"]))
    return {"items": rows, "question_writes": [],
            "wrong_write_items": sorted(k for k, v in rows.items() if v[1])}


def _p232c(score: Path) -> dict:
    d = _jl(score)
    rows = {}
    ww = []
    for iid, x in d["items"]["new"].items():
        bad = bool(x.get("wrong_writes")) or bool(x.get("trap_writes")) \
            or bool(x.get("others_hit"))
        rows[str(iid)] = (bool(x.get("right")), bad)
        if x.get("wrong_writes") or x.get("trap_writes"):
            ww.append(str(iid))
    return {"items": rows, "question_writes": [], "wrong_write_items": ww}


def _p236(score: Path) -> dict:
    d = _jl(score)
    rows = {str(x["id"]): (bool(x["right"]), bool(x["wrong_values"]))
            for x in d["items"]}
    qw = [str(x["id"]) for x in d["items"] if x.get("question_write")]
    return {"items": rows, "question_writes": qw}


def _p237(score: Path) -> dict:
    d = _jl(score)
    rows = {str(x["id"]): (bool(x["right"]), bool(x["wrong_values"]))
            for x in d["cases"]}
    qw = [str(x["id"]) for x in d["cases"] if x.get("question_wrote")]
    return {"items": rows, "question_writes": qw}


def _load_arm(panel: str, where: Path, arm: str | None) -> dict:
    if panel == "tablepanel221":
        return _p221(where)
    if panel == "tablepanel221b":
        return _p221b(where, arm or "221c")
    if panel == "teachpanel229":
        return _p229(where)
    if panel == "namepanel232c":
        return _p232c(where)
    if panel == "firstnamepanel236":
        return _p236(where)
    return _p237(where)


def _reg_path(panel: str) -> Path:
    r = REG[panel]
    return {"tablepanel221": r, "tablepanel221b": r,
            "teachpanel229": r / "panel-score.json",
            "namepanel232c": r / "panel-score.json",
            "firstnamepanel236": r / "panel-score.json",
            "aliaspanel237": r / "score237.json"}[panel]


def _run_path(panel: str, run: Path, arm: str) -> Path:
    p = run / panel
    return {"tablepanel221": p / f"out-{arm}",
            "tablepanel221b": p / "out",
            "teachpanel229": p / f"score-{arm}.json",
            "namepanel232c": p / f"score-{arm}.json",
            "firstnamepanel236": p / f"score-{arm}.json",
            "aliaspanel237": p / f"score-{arm}.json"}[panel]


def cmd_compare(run: Path, out: Path) -> int:
    res: dict = {"panels": {}}
    ok_all = True
    for panel in REG:
        st = run / panel / "status.txt"
        status = st.read_text().strip() if st.exists() else "MISSING"
        entry: dict = {"status": status}
        if status != "OK":
            entry["pass"] = False
            res["panels"][panel] = entry
            ok_all = False
            continue
        reg = _load_arm(panel, _reg_path(panel), "221c")
        arms = {a: _load_arm(panel, _run_path(panel, run, a), a)
                for a in ("n", "m")}
        n = arms["n"]
        ids = sorted(reg["items"])
        miss_ids = sorted(set(ids) ^ set(n["items"]))
        lost_to_wrong = [i for i in ids if i in n["items"]
                         and reg["items"][i][0] and n["items"][i][1]]
        new_wrong = [i for i in ids if i in n["items"]
                     and n["items"][i][1] and not reg["items"][i][1]]
        right_to_miss = [i for i in ids if i in n["items"]
                         and reg["items"][i][0] and not n["items"][i][0]
                         and not n["items"][i][1]]
        gained = [i for i in ids if i in n["items"]
                  and not reg["items"][i][0] and n["items"][i][0]]
        nww = sorted(set(n.get("wrong_write_items", []))
                     - set(reg.get("wrong_write_items", [])))
        entry.update({
            "n_items": len(ids),
            "right": {"registered": sum(v[0] for v in reg["items"].values()),
                      "138n": sum(v[0] for v in n["items"].values()),
                      "138m": sum(v[0] for v in arms["m"]["items"].values())},
            "wrong": {"registered": sum(v[1] for v in reg["items"].values()),
                      "138n": sum(v[1] for v in n["items"].values()),
                      "138m": sum(v[1] for v in arms["m"]["items"].values())},
            "question_writes": {"registered": len(reg["question_writes"]),
                                "138n": len(n["question_writes"]),
                                "138m": len(arms["m"]["question_writes"])},
            "id_set_mismatch": miss_ids,
            "lost_to_wrong": lost_to_wrong, "new_wrong": new_wrong,
            "new_wrong_write_items": nww,
            "right_to_miss_not_a_bar": right_to_miss,
            "gained_right": gained})
        entry["pass"] = (not miss_ids and not lost_to_wrong and not new_wrong
                         and not n["question_writes"] and not nww)
        ok_all &= entry["pass"]
        res["panels"][panel] = entry
        print(panel, "PASS" if entry["pass"] else "FAIL",
              json.dumps({k: v for k, v in entry.items()
                          if k not in ("pass",)}), flush=True)
    res["pass"] = ok_all
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("M7", "PASS" if ok_all else "FAIL")
    return 0 if ok_all else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run221")
    r.add_argument("--arm", choices=["n", "m"], required=True)
    r.add_argument("--items", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--work", required=True)
    c = sub.add_parser("compare")
    c.add_argument("--dir", required=True)
    c.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "run221":
        return cmd_run221(a.arm, a.items, a.out, a.work)
    return cmd_compare(Path(a.dir), Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
