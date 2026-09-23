#!/usr/bin/env python3
"""Exp 267 -- build Qwen check batches for C1/C2/C3 from one ear-preds file.

Mac side (imports sealed 261/264 modules read-only). Kept TEACH frames come
from 261's sealed base_arms (brake -> canon), exactly as 264's qbuild.
  C1: [{id, prompt}] via canon render_claim + prompt B (261b exactly).
  C2: [{id, prompt, q}] via 264's QA builders (value/owner/relation).
  C3: [{id, prompt}] via sealed claude_diag267_c3.build_c3.
Check ids "<turnid>#t<k>" (+ "#q<q>" for C2). Manifests map id -> frame/turn.
python claude_diag267_qbuild.py --turns TURNS.json --a-preds EARPREDS.json --out DIR"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_earcheck261_arms as A261  # noqa: E402
import claude_earcheck261_canon as C  # noqa: E402
import claude_earcheck261_promptB as PB  # noqa: E402
import claude_earcheck264_qa as QA  # noqa: E402
import claude_diag267_c3 as C3  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--turns", required=True)
    ap.add_argument("--a-preds", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    turns = {t["id"]: t["turn"] for t in
             json.loads(Path(a.turns).read_text(encoding="utf-8"))}
    preds = json.loads(Path(a.a_preds).read_text(encoding="utf-8"))["preds"]
    c1, c2, c3, m1, m2, m3 = [], [], [], {}, {}, {}
    for tid, turn in turns.items():
        p = preds[tid]
        arms = A261.base_arms(p["raw"], turn, p["greedy_lp"], p["beams"])
        k = 0
        for f in arms["kept_canon"]:
            if f.get("act") != "TEACH":
                continue
            base = f"{tid}#t{k}"
            h = C.render_claim(f["subject"], f["relation"], f["value"])
            c1.append(dict(id=base, prompt=PB.build_prompt_b(turn, h)))
            m1[base] = dict(turn=tid, frame=f, claim=h)
            for q, prompt in (("value", QA.build_q_value(turn, f["subject"], f["relation"])),
                              ("owner", QA.build_q_owner(turn, f["relation"], f["value"])),
                              ("relation", QA.build_q_relation(turn, f["subject"], f["value"]))):
                cid = f"{base}#q{q}"
                c2.append(dict(id=cid, prompt=prompt, q=q))
                m2[cid] = dict(turn=tid, frame=f, q=q)
            prompt3, readings = C3.build_c3(turn, f)
            c3.append(dict(id=base, prompt=prompt3))
            m3[base] = dict(turn=tid, frame=f, readings=readings)
            k += 1
    out = Path(a.out)
    (out / "c1").mkdir(parents=True, exist_ok=True)
    (out / "c2").mkdir(parents=True, exist_ok=True)
    (out / "c3").mkdir(parents=True, exist_ok=True)
    (out / "c1" / "checks.json").write_text(json.dumps(c1, indent=1))
    (out / "c1" / "manifest.json").write_text(json.dumps(m1, indent=1))
    (out / "c2" / "checks.json").write_text(json.dumps(c2, indent=1))
    (out / "c2" / "manifest.json").write_text(json.dumps(m2, indent=1))
    (out / "c3" / "checks.json").write_text(json.dumps(c3, indent=1))
    (out / "c3" / "manifest.json").write_text(json.dumps(m3, indent=1))
    print(f"{len(turns)} turns -> C1:{len(c1)} C2:{len(c2)} C3:{len(c3)}")


if __name__ == "__main__":
    main()
