#!/usr/bin/env python3
"""Exp 138f M1 driver -- every REMAINING piece's sealed probe on loop138f.

Reuses scripts/fable_loop138d_m1.py BY IMPORT (same cases, same judges);
only the loop factory is swapped: M1.fresh138d is rebound (in-process) to
build loop138f. Removed pieces (154, 155x135, 138c) have no probe here --
the mark covers remaining pieces only: 142, 146d, 153, 156b, 157, 158,
159, 150b. Outputs artifacts/fable-agent138f-20260922/m1-138f.json.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix138f_m1.py
"""

from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138d_m1 as M1  # noqa: E402 (probes+judges, read-only)
import fable_loop138f_agent as L138f  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-agent138f-20260922"


def fresh138f() -> object:
    import tempfile
    tmp = tempfile.mkdtemp(prefix="m1-138f-")
    cfg = copy.deepcopy(L138f.DEFAULT_CONFIG138F)
    cfg["state_dir"] = tmp
    cfg["sleep_threshold"] = 100000
    return L138f.build_agent138f(cfg)


def run156b_138f() -> dict:
    """156b probe with the N02 bar corrected for the removed 155 piece.

    138d's N02 clause encodes the 155 interaction ("thanks, Bob is Tom's
    boss" saved as "Tom's boss is thanks, Bob" -- a polluted write the
    138f brief removes by design). On loop138f the correct expectation is
    loop138b behaviour: no write + byte-identical reply. All other cases
    use the sealed 138d rule verbatim.
    """
    import fable_fix156b_smalltalk as S156B  # noqa: E402 (read-only)
    cases = json.load(open(
        M1.ROOT / "artifacts/fable-smalltalk156b-20260922/cases156b.json"))
    ok = bad = writes = 0
    fails = []
    for c in cases:
        loop = fresh138f()
        n0 = len(M1.triples(loop))
        reply = M1.say(loop, c["text"])
        if c["kind"] == "smalltalk":
            if len(M1.triples(loop)) != n0:
                writes += 1
                fails.append(c["id"] + ":write")
                continue
            cls = S156B.classify_156b(c["text"])
            good = (cls is not None
                    and reply == S156B.CLASS_REPLIES[cls])
        elif c["id"] == "N02":
            base = M1.say(M1.fresh138b(), c["text"])
            good = (len(M1.triples(loop)) == n0 and reply == base)
            if not good:
                fails.append(c["id"] + ":not-base:" + reply[:80])
                bad += 1
                continue
        else:
            good, tag, detail = M1.judge_chat_shape(c["text"])
            if not good:
                fails.append(c["id"] + ":" + tag + ":" + detail[:100])
                bad += 1
                continue
        if good:
            ok += 1
        else:
            bad += 1
            fails.append(c["id"] + ":" + reply[:60])
    cases2 = json.load(open(
        M1.ROOT / "artifacts/fable-smalltalk156-20260922/cases156.json"))
    ok2 = bad2 = 0
    for c in cases2:
        text = c.get("text", "")
        good, tag, detail = M1.judge_chat_shape(text)
        if good:
            ok2 += 1
        else:
            bad2 += 1
    return {"piece": "156b", "n": len(cases), "ok": ok, "bad": bad,
            "writes": writes, "fails": fails,
            "t2": {"n": len(cases2), "ok": ok2, "bad": bad2, "fails": []},
            "pass": bad == 0 and writes == 0 and bad2 == 0}


def main() -> int:
    M1.fresh138d = fresh138f  # type: ignore[method-assign]
    M1.ART = ART  # type: ignore[method-assign]
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "pieces": {}}
    rc = 0
    for fn in (M1.run142, M1.run146d, M1.run153,
               run156b_138f, M1.run157, M1.run158, M1.run159, M1.run150b):
        rep = fn()
        out["pieces"][rep["piece"]] = rep
        status = "PASS" if rep["pass"] else "FAIL"
        print(f"M1 {rep['piece']}: {status} "
              f"{json.dumps({k: v for k, v in rep.items() if k != 'pass'})[:300]}",
              flush=True)
        if not rep["pass"]:
            rc = 1
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "m1-138f.json").write_text(json.dumps(out, indent=1,
                                                 sort_keys=True),
                                      encoding="utf-8")
    print(f"M1 done in {out['seconds']}s rc={rc}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
