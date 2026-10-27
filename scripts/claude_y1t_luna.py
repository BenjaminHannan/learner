#!/usr/bin/env python3
"""y1t top-up runner on GPT-6 Luna (Answering-from-memory thread, 2026-09-27; ADDENDUM-5). New file.

Words the last 315 redo dialogs (ADDENDUM-3) with GPT-6 Luna through the Director's helper scripts/claude_luna_codex.py
(Ben's Codex plan; call(text, model, timeout) -> str; empty or error-like replies raise instead of being returned).
Everything else is Reading facts' wrapper, unchanged: claude_lis320_glm_oc.run_batches (prompt, parser, batches, time
cap, failed-call stop, one row per dialog, resume skips rows already written). The only changes: the caller is Luna's,
and rows record model "codex/gpt-6-luna" and temperature null. A failed call writes a row with empty "raw", which the
route-loss filter (claude_y1t_routefilter.py, ADDENDUM-4) drops before any merge, so it is not a try.

  python -B scripts/claude_y1t_luna.py pick --redo seeds_redo.jsonl --done raw_new.jsonl --out luna_seeds.jsonl
  python -B scripts/claude_y1t_luna.py --seeds luna_seeds.jsonl --out raw_luna.jsonl --workers 3 --batch 20 \
      --max-minutes 120 --max-failed 20 [--limit 60]
  python -B scripts/claude_y1t_luna.py --selftest        (no network: stubbed helper)
"""
from __future__ import annotations

import json
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_luna_codex as L  # noqa: E402
import claude_lis320_glm_oc as B  # noqa: E402

MODEL = "codex/gpt-6-luna"
_LOCK = threading.Lock()


def call_luna(text):
    try:
        out = L.call(text, model=L.MODEL) or ""
    except Exception as e:                            # a failed call is logged and counted, never guessed
        print(f"[y1tluna] call failed: {type(e).__name__} {str(e)[:120]}", flush=True)
        out = ""
    if not out:
        with _LOCK:
            B.FAILED["n"] += 1
    return out, {}


def pick(redo: Path, done: Path, out: Path) -> dict:
    """The redo seeds whose dialog id has no row in `done`, in redo order."""
    seeds = [json.loads(x) for x in redo.read_text(encoding="utf-8").splitlines() if x.strip()]
    have = {json.loads(x)["dialog_id"] for x in done.read_text(encoding="utf-8").splitlines() if x.strip()}
    left = [d for d in seeds if d["dialog_id"] not in have]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in left), encoding="utf-8")
    res = {"redo": len(seeds), "done": len(have), "left": len(left)}
    print(json.dumps(res))
    return res


def selftest() -> None:
    seen = []
    real = L.call
    try:
        L.call = lambda text, model=None, timeout=300: seen.append(model) or '{"turns": []}'
        assert call_luna("hi") == ('{"turns": []}', {}) and seen == [L.MODEL]
        B.FAILED["n"] = 0

        def boom(text, model=None, timeout=300):
            raise RuntimeError("luna call failed after 3 tries: error-like or empty reply")
        L.call = boom
        assert call_luna("hi") == ("", {}) and B.FAILED["n"] == 1   # a failure is counted, never returned as text
        B.FAILED["n"] = 0
    finally:
        L.call = real
    with tempfile.TemporaryDirectory() as td:
        redo, done, out = Path(td) / "r.jsonl", Path(td) / "d.jsonl", Path(td) / "o.jsonl"
        redo.write_text("".join(json.dumps({"dialog_id": f"x{i}", "turns": []}) + "\n" for i in range(5)))
        done.write_text("".join(json.dumps({"dialog_id": f"x{i}", "raw": "r"}) + "\n" for i in (0, 2)))
        assert pick(redo, done, out) == {"redo": 5, "done": 2, "left": 3}
        assert [json.loads(x)["dialog_id"] for x in out.read_text().splitlines()] == ["x1", "x3", "x4"]
    B.MODEL = MODEL
    B.call_opencode = call_luna
    B.selftest()                                      # the wrapper's own checks, with rows recording Luna's model
    print("y1t luna selftest ok (no network)")


def main() -> int:
    if "--selftest" in sys.argv:
        selftest()
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "pick":
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--redo", required=True, type=Path)
        ap.add_argument("--done", required=True, type=Path)
        ap.add_argument("--out", required=True, type=Path)
        a = ap.parse_args()
        pick(a.redo, a.done, a.out)
        return 0
    B.MODEL = MODEL
    B.call_opencode = call_luna
    return B.main() or 0


if __name__ == "__main__":
    sys.exit(main())
