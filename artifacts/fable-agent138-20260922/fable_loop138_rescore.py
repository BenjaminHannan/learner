#!/usr/bin/env python3
"""Exp 138 A4 rescorer -- read-only E-family + Z verdicts from frozen waves.

The 116 drive looks up turn records by bare probe name ("p01") while the
daemon logs mailbox names ("p01.txt"), so record-dependent fields
(src/trail/status) read empty in the raw report (same checker bug as exp
116 D3 / exp 131 D1). This script recomputes the E-family verdicts
(E1-E4: install happens, 0 wrong installs, taught wins) from frozen
evidence -- outbox replies, daemon.log.jsonl (with mailbox filenames),
notebooks, word files -- using the same case logic as
scripts/fable_sleep116_drive.py, plus the Z1-Z5 verdicts from the 104
drive's own report. No daemon is booted. Nothing outside
artifacts/fable-agent138-20260922/ is written.

Run (after both sleep waves finish):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B artifacts/fable-agent138-20260922/fable_loop138_rescore.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402 (read-only)
import fable_sleep104_drive as D104  # noqa: E402 (read-only)
import fable_sleep116_drive as D116  # noqa: E402 (case logic, read-only)

ART = ROOT / "artifacts" / "fable-agent138-20260922"
has = D116.has
is_abstain = D116.is_abstain
taught_pair_ok = D116.taught_pair_ok


def load_run(d: Path) -> dict:
    log = [json.loads(l) for l in (d / "daemon.log.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    outbox = {}
    for p in (d / "outbox").glob("*.txt"):
        outbox[p.name] = p.read_text(encoding="utf-8")
    return {"dir": d, "log": log, "outbox": outbox,
            "nb": C.Notebook(d / "notebook")}


def rec_of(run: dict, name: str) -> dict:
    for e in run["log"]:
        if e.get("event") == "turn" and e.get("file") == f"{name}.txt":
            recs = e.get("records", [])
            return recs[0] if recs else {}
    return {}


def sleep_of(run: dict) -> dict:
    sleeps = [e for e in run["log"] if e.get("event") == "sleep"]
    first = sleeps[0] if sleeps else {}
    recipe = first.get("recipe", {}) if isinstance(first, dict) else {}
    words = recipe.get("words", [])
    wrec = next((w for w in words
                 if w.get("word") == "maternal_grandmother"), {})
    return {"installed": bool(recipe.get("installed")),
            "attempted": bool(recipe.get("attempted")),
            "episodes": sum(w.get("episodes", 0) for w in words),
            "oof": wrec.get("oof_best"),
            "agree": wrec.get("refit_agreement")}


def rescore_taughtwin() -> dict:
    r = load_run(ART / "runs-116" / "taughtwin")
    si = sleep_of(r)
    inst = si["installed"]
    out: dict = {"installed": inst, "attempted": si["attempted"],
                 "episodes": si["episodes"], "oof": si["oof"],
                 "agree": si["agree"], "cases": {}}

    def V(cid: str, verdict: str, detail: str = "") -> None:
        out["cases"][cid] = {"verdict": verdict, "detail": detail}

    stored = {i: taught_pair_ok(r["nb"], f"T{i:02d}",
                                "maternal_grandmother", f"Z{i:02d}")
              for i in (1, 2, 3)}
    out["stored"] = stored
    e1reply = r["outbox"].get("t025.txt", "")
    e1wrote = any(e.get("event") == "turn"
                  and e.get("file") == "t025.txt"
                  and e.get("new_fact_ids") for e in r["log"])
    V("E1", "OK" if e1reply.strip() else "BUG",
      f"reply={e1reply.strip()[:90]} wrote={int(bool(e1wrote))} "
      f"stored={stored}")
    for cid, i in (("E2", 1), ("E3", 2)):
        rp = r["outbox"].get(f"p{i:02d}.txt", "")
        rec = rec_of(r, f"p{i:02d}")
        ab = is_abstain(rp, rec)
        zv, gv = f"Z{i:02d}", f"G{i:02d}"
        src = rec.get("fields", {}).get("source", "")
        if stored[i]:
            if has(rp, zv) and src == "taught":
                V(cid, "OK",
                  f"TAUGHT WINS src={src} reply={rp.strip()[:80]}")
            elif has(rp, zv) or ab:
                V(cid, "OK",
                  f"stored; installed={int(inst)} abstain={int(ab)} "
                  f"src={src} reply={rp.strip()[:80]}")
            elif has(rp, gv):
                V(cid, "BUG",
                  f"TAUGHT OVERRIDDEN by derived: src={src} "
                  f"reply={rp.strip()[:80]}")
            else:
                V(cid, "BUG", f"unexpected: {rp.strip()[:80]}")
        elif has(rp, gv) or ab:
            V(cid, "OK", f"not-storable branch; reply={rp.strip()[:80]}")
        else:
            V(cid, "BUG", f"unexpected: {rp.strip()[:80]}")
    rp4 = r["outbox"].get("p03.txt", "")
    rec4 = rec_of(r, "p03")
    src4 = rec4.get("fields", {}).get("source", "")
    rows_active = all(stored.values())
    ow = D104.sleep_overwrites(r["nb"])
    out["overwrite"] = ow
    if stored[3] and has(rp4, "Z03") and src4 == "sleep-derived":
        V("E4", "BUG",
          f"taught win mislabeled sleep-derived: {rp4.strip()[:80]}")
    elif ow == 0 and rows_active and (
            has(rp4, "Z03") or is_abstain(rp4, rec4)):
        V("E4", "OK",
          f"taught intact src={src4} reply={rp4.strip()[:80]}")
    elif not stored[3] and ow == 0:
        V("E4", "OK",
          f"not-storable branch, ow=0 reply={rp4.strip()[:80]}")
    else:
        V("E4", "BUG",
          f"ow={ow} stored={stored} src={src4} reply={rp4.strip()[:80]}")
    return out


def rescore_z() -> dict:
    rep = json.loads((ART / "wave-report-104.json").read_text(
        encoding="utf-8"))
    return rep


def main() -> int:
    out = {"taughtwin": rescore_taughtwin(), "z104": rescore_z()}
    e = out["taughtwin"]["cases"]
    e_ok = all(v["verdict"] == "OK" for v in e.values())
    tw = out["taughtwin"]
    print(f"E: installed={tw['installed']} eps={tw['episodes']} "
          f"ow={tw['overwrite']} " +
          " ".join(f"{k}={v['verdict']}" for k, v in e.items()),
          flush=True)
    for k, v in e.items():
        print(f"  {k} {v['verdict']}: {v['detail'][:130]}", flush=True)
    (ART / "fable_sleep138_rescored.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"rescore -> {ART / 'fable_sleep138_rescored.json'}", flush=True)
    return 0 if e_ok else 1


if __name__ == "__main__":
    sys.exit(main())
