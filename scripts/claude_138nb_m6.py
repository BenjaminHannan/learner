#!/usr/bin/env python3
"""Merge 138nb -- M6 regression driver: tablepanel221 (TEST-ONLY, run once
after the seal) scored on BOTH arms with the registered scorer
scripts/fable_fix221_panelmap.py (sha checked against
artifacts/claude-tableask221-20260922/panelmap.sha256.txt first),
building the arms the way scripts/claude_138n_m7.py run221 does (the
panel runner's arm "221" built as 138n / 138nb: loop mode, a fresh agent
per item, sleep threshold 100000, state in a fresh temp dir).

Prints and writes COUNTS and item ids only, never item text. Runner
rows/logs hold item text and stay outside the repo.

usage:
  claude_138nb_m6.py check
      sha-check the registered scorer; prints SHA-OK / SHA-FAIL.
  claude_138nb_m6.py run --arm n|nb --items PANEL --out DIR --work DIR
      run the panel on one arm with the registered scorer.
  claude_138nb_m6.py compare --dir RUN_DIR --out OUT.json
      bars on 138nb: 0 wrong; every item right on 138n is right on 138nb;
      every 138n row whose stage is loop190-reverse and whose reply names a
      subject becomes right on 138nb. Reports ids and counts only.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

PANELMAP_SHA_FILE = (ROOT / "artifacts" / "claude-tableask221-20260922"
                     / "panelmap.sha256.txt")


def cmd_check() -> int:
    want = PANELMAP_SHA_FILE.read_text(encoding="utf-8").split()
    path = ROOT / want[1]
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    ok = got == want[0]
    print("SHA-OK" if ok else "SHA-FAIL", flush=True)
    return 0 if ok else 1


def _build_arm(arm: str):
    import claude_loop138n_agent as AGN
    import claude_loop138nb_agent as AGB
    if arm == "n":
        return (copy.deepcopy(AGN.DEFAULT_CONFIG138N), AGN.build_agent138n)
    return (copy.deepcopy(AGB.DEFAULT_CONFIG138NB), AGB.build_agent138nb)


def cmd_run(arm: str, items: str, out: str, work: str) -> int:
    import fable_fix221_panelmap as PM  # noqa: registers load_items+score
    import fable_fix221_panel as F
    del PM  # imported for its side effects only
    Path(work).mkdir(parents=True, exist_ok=True)
    base_cfg, build = _build_arm(arm)
    orig = F.build

    def build_arm(a: str):
        if a != "221":
            return orig(a)
        d = tempfile.mkdtemp(prefix=f"m6-221-{arm}-", dir=work)
        cfg = copy.deepcopy(base_cfg)
        cfg["state_dir"] = d
        cfg["sleep_threshold"] = 100000
        return build(cfg)

    F.build = build_arm
    return F.main(["--items", items, "--out", out])


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()
            if x.strip()]


def _names_subject(reply: str) -> bool:
    import claude_fix138nb_label as LB
    return LB.names_subject138nb(reply)


def cmd_compare(rd: Path, out: Path) -> int:
    import claude_fix138nb_label as LB
    n = {f"{r['id']}#{r['turn_index']}": r
         for r in _jsonl(rd / "out-n" / "rows.jsonl")}
    nb = {f"{r['id']}#{r['turn_index']}": r
          for r in _jsonl(rd / "out-nb" / "rows.jsonl")}
    ids = sorted(n)
    miss = sorted(set(ids) ^ set(nb))
    wrong_nb = sorted(i for i in ids if i in nb and nb[i]["wrong_value221"])
    new_wrong = sorted(i for i in ids if i in nb and nb[i]["wrong_value221"]
                       and not n[i]["wrong_value221"])
    lost = sorted(i for i in ids if i in nb and n[i]["correct221"]
                  and not nb[i]["correct221"])
    gained = sorted(i for i in ids if i in nb and nb[i]["correct221"]
                    and not n[i]["correct221"])
    qwn = [f"{t['id']}#{t['k']}" for t in _jsonl(rd / "out-nb" / "turns.jsonl")
           if str(t["text"]).strip().endswith("?") and t["wrote221"]]
    # label-gain bar: every 138n row answered by loop190-reverse with a
    # subject-naming reply becomes right on 138nb.
    cands = [i for i in ids
             if n[i].get("stage221") == LB.STAGE138NB
             and _names_subject(str(n[i].get("reply221", "")))]
    cands_not_right = sorted(i for i in cands if not nb[i]["correct221"])
    res = {
        "n_items": len(ids), "id_set_mismatch": miss,
        "right": {"138n": sum(1 for i in ids if n[i]["correct221"]),
                  "138nb": sum(1 for i in ids if i in nb
                               and nb[i]["correct221"])},
        "wrong": {"138n": sum(1 for i in ids if n[i]["wrong_value221"]),
                  "138nb": len(wrong_nb)},
        "wrong_nb_ids": wrong_nb, "new_wrong_ids": new_wrong,
        "right_on_n_not_right_on_nb_ids": lost,
        "gained_right_ids": gained,
        "question_writes_nb": qwn,
        "loop190_subject_candidates_n": len(cands),
        "loop190_subject_candidates_not_right_on_nb": cands_not_right,
    }
    res["pass"] = (not miss and not wrong_nb and not lost
                   and not cands_not_right and not qwn)
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res), flush=True)
    print("M6", "PASS" if res["pass"] else "FAIL", flush=True)
    return 0 if res["pass"] else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    r = sub.add_parser("run")
    r.add_argument("--arm", choices=["n", "nb"], required=True)
    r.add_argument("--items", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--work", required=True)
    c = sub.add_parser("compare")
    c.add_argument("--dir", required=True)
    c.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "check":
        return cmd_check()
    if a.cmd == "run":
        return cmd_run(a.arm, a.items, a.out, a.work)
    return cmd_compare(Path(a.dir), Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
