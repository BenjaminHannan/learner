#!/usr/bin/env python3
"""Merge 291 -- M7 arm runner for arms nb/p/291 on invpanel138nb and
tablepanel221 (TEST-ONLY, run once after the seal).

Both procedures replicate the registered 138nb runners exactly
(scripts/claude_138nb_m1.py for invpanel, scripts/claude_138nb_m6.py for
tablepanel221, both used read-only for the n/nb arms) with only the agent
swapped:
  inv: one fresh agent per item, sleep_threshold 100000, row format
       id/setup_replies/question_reply/stored_after_setup_actual/
       stored_after_question_actual/question_wrote, reusing claude_138nb_m1
       stored()/facts_hash() so the row format (including its known
       stored-field artefact, 138nb D1) is identical on every arm.
  t221: the panel runner's arm "221" built as the mapped loop (fresh agent
       per item, sleep_threshold 100000), via the same F.build swap as
       claude_138nb_m6.py.

Prints and writes ids and counts only, never item text. Runner rows/logs
hold item text and stay outside the repo.

usage:
  claude_291_m7run.py inv --arm nb|p|291 --items PANEL --out ROWS --work DIR
  claude_291_m7run.py t221 --arm nb|p|291 --items PANEL --out DIR --work DIR
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_138nb_m1 as M1N  # noqa: E402 (row-format fns, read-only)

ARMS = {
    "nb": ("claude_loop138nb_agent", "DEFAULT_CONFIG138NB",
           "build_agent138nb",
           "artifacts/claude-merge138nb-20260923/loop138nb-config.json"),
    "p": ("claude_loop138p_agent", "DEFAULT_CONFIG138P",
          "build_agent138p",
          "artifacts/claude-merge138p-20260923/loop138p-config.json"),
    "291": ("claude_loop291_agent", "DEFAULT_CONFIG291",
            "build_agent291",
            "artifacts/claude-join291-20260923/loop291-config.json"),
}


def _load_arm(arm: str):
    mod_name, cfg_name, fn_name, cfgp = ARMS[arm]
    mod = __import__(mod_name)
    cfg0 = copy.deepcopy(getattr(mod, cfg_name))
    cfg0.update(json.loads((SCRIPTS.parent / cfgp).read_text(
        encoding="utf-8")))
    return cfg0, getattr(mod, fn_name)


def cmd_inv(arm: str, items: str, out: str, work: str) -> int:
    cfg0, build = _load_arm(arm)
    workp = Path(work)
    workp.mkdir(parents=True, exist_ok=True)
    rows = []
    n_qw = 0
    with open(items, encoding="utf-8") as f:
        lines = [x for x in f.read().splitlines() if x.strip()]
    print(f"items={len(lines)} arm={arm}", flush=True)
    for line in lines:
        it = json.loads(line)
        iid = str(it["id"])
        setup = [str(s) for s in it["setup"]]
        q = str(it["question"])
        d = Path(tempfile.mkdtemp(prefix=f"m1-{arm}-", dir=str(workp)))
        cfg = copy.deepcopy(cfg0)
        cfg["state_dir"] = str(d)
        cfg["sleep_threshold"] = 100000
        loop = build(cfg)
        srep = []
        for t in setup:
            srep.append(" ".join(loop.turn(t)))
        after_setup = M1N.stored(loop.nb)
        h0 = M1N.facts_hash(loop.nb)
        qrep = " ".join(loop.turn(q))
        qw = M1N.facts_hash(loop.nb) != h0
        after_q = M1N.stored(loop.nb)
        n_qw += int(qw)
        rows.append({"id": iid, "setup_replies": srep,
                     "question_reply": qrep,
                     "stored_after_setup_actual": after_setup,
                     "stored_after_question_actual": after_q,
                     "question_wrote": qw})
        shutil.rmtree(d, ignore_errors=True)
    Path(out).write_text("\n".join(json.dumps(r, ensure_ascii=False)
                                   for r in rows) + "\n", encoding="utf-8")
    print(f"rows={len(rows)} question_writes={n_qw}", flush=True)
    return 0


def cmd_t221(arm: str, items: str, out: str, work: str) -> int:
    import fable_fix221_panel as F  # noqa: E402 (panel runner, read-only)
    Path(work).mkdir(parents=True, exist_ok=True)
    base_cfg, build = _load_arm(arm)
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("inv")
    r.add_argument("--arm", choices=["nb", "p", "291"], required=True)
    r.add_argument("--items", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--work", required=True)
    t = sub.add_parser("t221")
    t.add_argument("--arm", choices=["nb", "p", "291"], required=True)
    t.add_argument("--items", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--work", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "inv":
        return cmd_inv(a.arm, a.items, a.out, a.work)
    return cmd_t221(a.arm, a.items, a.out, a.work)


if __name__ == "__main__":
    sys.exit(main())
