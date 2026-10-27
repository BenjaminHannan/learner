#!/usr/bin/env python3
"""y1t top-up of GLM dialogs that failed (Answering-from-memory thread, 2026-09-26). New file.
Used only under artifacts/claude-y1t-20260926/ADDENDUM-3-opencode-topup.md.

The OpenRouter account ran out of funds at about 18:30 UTC while y1t-glm-mac was wording its dialogs; lis-320's GLM
script writes a failed dialog as a row with nothing parsed. This splits the first run's raw rows into the dialogs that
parsed (kept as they are, never redone) and the seeds to word again through Ben's opencode route
(scripts/claude_lis320_glm_oc.py), then merges the two so each dialog appears exactly once before lis-320's check.

  python -B scripts/claude_y1t_topup.py split --seeds SEEDS --raw RAW --out DIR   -> DIR/raw_ok.jsonl, DIR/seeds_redo.jsonl
  python -B scripts/claude_y1t_topup.py merge --ok RAW_OK --new RAW_NEW --out RAW_MERGED
  python -B scripts/claude_y1t_topup.py --selftest
Prints counts only.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path


def load(p) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def dump(p, rows: list[dict]) -> None:
    Path(p).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def split(seeds: list[dict], raw: list[dict]) -> tuple[list[dict], list[dict], dict]:
    ids = {d["dialog_id"] for d in seeds}
    ok, seen = [], set()
    for r in raw:
        if r["dialog_id"] in ids and r.get("parsed") is not None and r["dialog_id"] not in seen:
            ok.append(r)
            seen.add(r["dialog_id"])
    redo = [d for d in seeds if d["dialog_id"] not in seen]
    return ok, redo, {"seeds": len(seeds), "raw_rows": len(raw), "parsed_kept": len(ok), "to_redo": len(redo),
                      "raw_rows_unparsed": sum(r.get("parsed") is None for r in raw)}


def merge(ok: list[dict], new: list[dict]) -> tuple[list[dict], dict]:
    have = {r["dialog_id"] for r in ok}
    best = {}
    for r in new:
        d = r["dialog_id"]
        if d in have:
            continue
        if d not in best or (best[d].get("parsed") is None and r.get("parsed") is not None):
            best[d] = r
    out = ok + list(best.values())
    return out, {"from_first_run": len(ok), "from_topup": len(best),
                 "topup_parsed": sum(r.get("parsed") is not None for r in best.values()), "rows": len(out)}


def selftest() -> None:
    seeds = [{"dialog_id": f"d{i}"} for i in range(6)]
    raw = [{"dialog_id": "d0", "parsed": ["a"]}, {"dialog_id": "d1", "parsed": None},
           {"dialog_id": "d2", "parsed": ["b"]}, {"dialog_id": "d2", "parsed": ["c"]},
           {"dialog_id": "d3", "parsed": None}, {"dialog_id": "zz", "parsed": ["x"]}]
    ok, redo, c = split(seeds, raw)
    assert [r["dialog_id"] for r in ok] == ["d0", "d2"] and ok[1]["parsed"] == ["b"], ok
    assert [d["dialog_id"] for d in redo] == ["d1", "d3", "d4", "d5"], redo
    assert c == {"seeds": 6, "raw_rows": 6, "parsed_kept": 2, "to_redo": 4, "raw_rows_unparsed": 2}, c
    new = [{"dialog_id": "d1", "parsed": None}, {"dialog_id": "d1", "parsed": ["y"]}, {"dialog_id": "d3", "parsed": ["z"]},
           {"dialog_id": "d4", "parsed": None}, {"dialog_id": "d0", "parsed": ["never used"]}]
    out, m = merge(ok, new)
    by = {r["dialog_id"]: r for r in out}
    assert len(out) == len(by) == 5 and by["d0"]["parsed"] == ["a"] and by["d1"]["parsed"] == ["y"], out
    assert m == {"from_first_run": 2, "from_topup": 3, "topup_parsed": 2, "rows": 5}, m
    with tempfile.TemporaryDirectory() as d:
        dump(Path(d) / "s.jsonl", seeds)
        dump(Path(d) / "r.jsonl", raw)
        assert load(Path(d) / "r.jsonl") == raw
    print("selftest ok")


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("split")
    for k in ("--seeds", "--raw", "--out"):
        s.add_argument(k, required=True)
    m = sub.add_parser("merge")
    for k in ("--ok", "--new", "--out"):
        m.add_argument(k, required=True)
    a = ap.parse_args()
    if a.cmd == "split":
        ok, redo, c = split(load(a.seeds), load(a.raw))
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        dump(out / "raw_ok.jsonl", ok)
        dump(out / "seeds_redo.jsonl", redo)
        print(json.dumps(c))
    else:
        out, c = merge(load(a.ok), load(a.new))
        dump(a.out, out)
        print(json.dumps(c))


if __name__ == "__main__":
    main()
