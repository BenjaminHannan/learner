#!/usr/bin/env python3
"""dl-5 carry-over row (report-only; artifacts/claude-dl5-20260926/PASSMARKS.md Addendum 1, fixed before any dl-5
result was seen). Fix-sleep thread, 2026-09-26.

Did five grid nights move a kind of work they never practised? The number-puzzle measure (claude_blurt2.luck: right
guesses on 100 fresh number puzzles x 20 guesses at temperature 1.5, plus greedy solves) on the plain base and on each
saved S adapter (dl5-S-s8.pt, dl5-S-s9.pt; claude_blurt2.add_lora A/B tensors, sha256 checked against the sidecars).
Test seed 3490, used by no earlier run. No mark: the placebo adapters were not saved, so any move is reported as
"moved, cause untested". Nothing is trained.
Addendum 2 (report-only, added before this row ran): each model's greedy reply to the 300 harm-panel items is saved,
so lost and gained items can be split into "names a wrong fact" vs "cut off or reshaped" (Thread manager, 17:21).

  python -B scripts/claude_dl5_carry.py --selftest
  python -B scripts/claude_dl5_carry.py --model M --adapters DIR --out DIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt1 as B1  # noqa: E402
import claude_blurt2 as B2  # noqa: E402
import claude_dl1_nights as D1  # noqa: E402

TEST_SEED = 3490
N_PUZ, N_GUESS, TEMP = 100, 20, 1.5
SIDECARS = Path(__file__).resolve().parent.parent / "artifacts/claude-dl5-20260926/gpu"


def load_adapter(s, pt: Path):
    import torch
    want = json.loads((SIDECARS / (pt.stem + ".json")).read_text(encoding="utf-8"))["sha256"]
    got = hashlib.sha256(pt.read_bytes()).hexdigest()
    if got != want:
        raise SystemExit(f"{pt.name}: sha256 {got} != sidecar {want}")
    m = D1.fresh_model(s)
    sd = torch.load(pt, map_location="cpu")
    missing = [k for k in sd if k not in m.state_dict()]
    if missing:
        raise SystemExit(f"{pt.name}: {len(missing)} tensors do not fit the model, e.g. {missing[:2]}")
    m.load_state_dict(sd, strict=False)
    return m.eval(), got


def measure(s, m, ps) -> dict:
    lucky, reached = B2.luck(s, ps, N_GUESS, TEMP, m)
    greedy = sum(B1.check(s.generate(p, 1, None, m)[0], p["nums"], p["target"]) for p in ps)
    replies = [D1.free_answer(s, it["q"], m) for it in D1.harm_panel()[:300]]
    harm = [int(D1.harm_right(it, r)) for it, r in zip(D1.harm_panel()[:300], replies)]
    return {"lucky": lucky, "reached": reached, "greedy": greedy, "harm_right": sum(harm), "harm_items": harm,
            "harm_replies": replies}


def run(a) -> None:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    ps = B2.puzzles(TEST_SEED, N_PUZ)
    res = {"test_seed": TEST_SEED, "n_puzzles": len(ps), "n_guess": N_GUESS, "temp": TEMP}
    s.torch.manual_seed(TEST_SEED)
    t0 = time.time()
    res["base"] = measure(s, s.model, ps)
    print(f"[dl5-carry] base lucky {res['base']['lucky']} reached {res['base']['reached']} greedy "
          f"{res['base']['greedy']} harm {res['base']['harm_right']} {round(time.time() - t0)} s", flush=True)
    for name in ("dl5-S-s8", "dl5-S-s9"):
        m, sha = load_adapter(s, Path(a.adapters) / (name + ".pt"))
        s.torch.manual_seed(TEST_SEED)
        res[name] = dict(measure(s, m, ps), sha256=sha)
        r = res[name]
        print(f"[dl5-carry] {name} lucky {r['lucky']} reached {r['reached']} greedy {r['greedy']} harm "
              f"{r['harm_right']} lost {sum(1 for b, x in zip(res['base']['harm_items'], r['harm_items']) if b and not x)}",
              flush=True)
        del m
        if s.dev == "cuda":
            s.torch.cuda.empty_cache()
    (out / "dl5_carry.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: ({kk: vv for kk, vv in v.items() if kk not in ("harm_items", "harm_replies")}
                          if isinstance(v, dict) else v) for k, v in res.items()}))


def selftest() -> None:
    ps = B2.puzzles(TEST_SEED, N_PUZ)
    assert len(ps) == N_PUZ and all("nums" in p and "target" in p for p in ps)
    assert len(D1.harm_panel()[:300]) == 300
    for n in ("dl5-S-s8", "dl5-S-s9"):
        meta = json.loads((SIDECARS / (n + ".json")).read_text(encoding="utf-8"))
        assert len(meta["sha256"]) == 64 and meta["tensors"] == 192, meta
    print("dl5 carry selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--adapters", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    run(a)


if __name__ == "__main__":
    main()
