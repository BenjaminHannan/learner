#!/usr/bin/env python3
"""dl-6c: dl-6 rerun with a GLM-written puzzle instruction (Fix-sleep thread, 2026-09-26; marks:
artifacts/claude-dl6c-20260926/PASSMARKS.md). Held: runs only if Ben picks "Rerun with GLM" on the H-B card.

Why. Ben chose "Use GLM" (16:39 UTC 09-26): nothing a model trains on, inputs included, may be Claude-written. dl-6's
trained rows are the 1B's own code-checked answers, but every row's input carries claude_blurt1.puzzle_prompt, a
Claude-written instruction. dl-6c is dl-6 (scripts/claude_dl6_light.py, unchanged, imported) with ONE difference:
that instruction is replaced by GLM 5.3 Flash's text from artifacts/claude-glmframes-20260926/frames.json ("puzzle"
-> "chosen", {NUMS} = the numbers joined by ", ", {TARGET} = the target), pinned by sha256 below. Everything else
(arms S and L, seeds 10 and 11, 7 nights, TEST seed 3590, marks F1-F5 with L in place of A) is dl-6's.
The frame also reaches TEST and the base measure, so L0 is re-measured under it (INCONCLUSIVE if L0 < 10, as dl-6).

  python -B scripts/claude_dl6c_glmframe.py --selftest
  python -B scripts/claude_dl6c_glmframe.py --model M --out DIR        (registered run; dl-6's arguments)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_blurt1 as B1  # noqa: E402

FRAMES = HERE.parent / "artifacts/claude-glmframes-20260926/frames.json"
FRAMES_SHA256 = "3c1fe9c190837704878759cd4f0f17d9c88aa2a0795536c4dbc90be4a80014bc"


def glm_frame() -> str:
    raw = FRAMES.read_bytes()
    if hashlib.sha256(raw).hexdigest() != FRAMES_SHA256:
        raise SystemExit(f"frames.json sha256 {hashlib.sha256(raw).hexdigest()} != pinned {FRAMES_SHA256!r}")
    t = json.loads(raw.decode("utf-8"))["puzzle"]["chosen"]
    if not t:
        raise SystemExit("frames.json has no chosen puzzle frame")
    return t


def make_prompt(frame: str):
    def puzzle_prompt(p) -> list[dict]:
        ns = ", ".join(str(n) for n in p["nums"])
        return [{"role": "user", "content": frame.replace("{NUMS}", ns).replace("{TARGET}", str(p["target"]))}]
    return puzzle_prompt


def selftest() -> None:
    f = make_prompt("Use {NUMS} once each with + - * / and brackets to make {TARGET}; reply with the expression only.")
    m = f({"nums": [3, 5, 8], "target": 24})
    assert m == [{"role": "user", "content": "Use 3, 5, 8 once each with + - * / and brackets to make 24; reply with "
                                             "the expression only."}], m
    B1.puzzle_prompt, old = f, B1.puzzle_prompt
    import claude_blurt2 as B2
    assert B2.B1.puzzle_prompt is f
    B1.puzzle_prompt = old
    import claude_dl6_light as L
    L.selftest()
    print("dl6c selftest ok")


def main():
    if "--selftest" in sys.argv:
        return selftest()
    frame = glm_frame()
    B1.puzzle_prompt = make_prompt(frame)            # every Solver.prompt call looks it up on the module
    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
        out.mkdir(parents=True, exist_ok=True)
        (out / "frame.json").write_text(json.dumps({"frame": frame, "sha256": FRAMES_SHA256}), encoding="utf-8")
    import claude_dl6_light as L
    sys.argv[0] = "claude_dl6_light.py"
    L.main()


if __name__ == "__main__":
    main()
