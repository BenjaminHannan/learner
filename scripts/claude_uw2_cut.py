#!/usr/bin/env python3
"""uw-2 early cut of lis-320's seed-324 Luna full run (artifacts/claude-uw2-20260926/ADDENDUM-3-early-cut.md).
Wrong-as-fact thread, 2026-09-27, written before any seed-324 row exists. New file. Prints counts only. Makes no call.

FULL is a local copy of origin/builder-outbox artifacts/claude-lis320-20260926/full-luna/ (chunkJ/RESULTS.md,
chunkJ/raw.new.jsonl.gz, chunkJ/SEEDS.sha256.txt).

  pick FULL [--min 1500]      K = the smallest chunk whose CHUNK-SUMMARY says stop=ok and worded_ok >= min, with
                              chunks 1..K all stop=ok. Prints {"K": K} or {"K": null, ...} with counts.
  make FULL K OUT [--seed 324 --n 6000]
                              seeds from lis-320's chunk seed_cr command (sha must equal chunk1/SEEDS.sha256.txt);
                              chunks 1..K raw.new.jsonl.gz joined in order; lis-320's sealed resume_clean, then
                              rawcheck2 --models gpt-6-luna (must exit 0), then check_we3 -> OUT/kept.jsonl.
                              OUT/seeds.jsonl keeps only the dialogs that have a row. OUT/CUT.json has every sha256.
                              claude_uw2_data.py build then runs on OUT unchanged.
  --selftest                  on lis-320 pilot 8 (seed 328, readable; temp files only): split into two fake chunks,
                              the cut's kept ids must equal the pilot's own kept ids.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIS = "artifacts/claude-lis320-20260926"
MIN_DIALOGS = 1500
SUMMARY = re.compile(r"CHUNK-SUMMARY K=(\d+) .*worded_ok=(\d+) of=(\d+) stop=(\S+)")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def py(*args: str, out: Path | None = None) -> int:
    r = subprocess.run([sys.executable, "-B", *args], cwd=ROOT, capture_output=True, text=True)
    if out is not None:
        out.write_text(r.stdout, encoding="utf-8")
    return r.returncode


def summaries(full: Path) -> dict:
    s = {}
    for d in sorted(full.glob("chunk*"), key=lambda p: int(p.name[5:]) if p.name[5:].isdigit() else 10**9):
        f = d / "RESULTS.md"
        m = [SUMMARY.search(x) for x in f.read_text(encoding="utf-8").splitlines()] if f.exists() else []
        m = [x for x in m if x]
        if m and d.name[5:].isdigit():
            s[int(d.name[5:])] = {"worded_ok": int(m[-1].group(2)), "stop": m[-1].group(4)}
    return s


def pick(full: Path, min_d: int = MIN_DIALOGS) -> int | None:
    s = summaries(full)
    k = 1
    while k in s and s[k]["stop"] == "ok":
        if s[k]["worded_ok"] >= min_d:
            print(json.dumps({"K": k, "worded_ok": s[k]["worded_ok"]}))
            return k
        k += 1
    print(json.dumps({"K": None, "chunks_seen": len(s), "first_not_ok_or_missing": k,
                      "worded_ok_last_ok": s[k - 1]["worded_ok"] if k > 1 else 0}))
    return None


def make(full: Path, k: int, out: Path, seed: int = 324, n: int = 6000) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    rep: dict = {"K": k, "chunks": {}}
    seeds_all = out / "seeds_all.jsonl"
    assert py("scripts/claude_lis320_seed_cr.py", "--seed", str(seed), "--n", str(n), "--ask-back", "--avoid-names",
              f"{LIS}/avoid_names_dev.txt", "--avoid-hashes", f"{LIS}/avoid_test.sha256", "--out",
              str(seeds_all)) == 0, "seed_cr failed"
    want = (full / "chunk1" / "SEEDS.sha256.txt").read_text(encoding="utf-8").strip()
    rep["seeds_sha256"] = sha(seeds_all)
    assert rep["seeds_sha256"] == want, "seeds sha differs from chunk1/SEEDS.sha256.txt"
    joined = out / "joined.jsonl"
    with open(joined, "w", encoding="utf-8") as fh:
        for j in range(1, k + 1):
            g = full / f"chunk{j}" / "raw.new.jsonl.gz"
            rep["chunks"][j] = sha(g)
            fh.write(gzip.decompress(g.read_bytes()).decode("utf-8"))
    raw = out / "raw.jsonl"
    assert py("scripts/claude_lis320_resume_clean.py", "--raw", str(joined), "--out", str(raw),
              out=out / "resume_clean.json") == 0, "resume_clean failed"
    rc = py("scripts/claude_lis320_rawcheck2.py", "--raw", str(raw), "--seeds", str(seeds_all), "--models",
            "gpt-6-luna", out=out / "rawcheck2.json")
    rep["rawcheck2_rc"] = rc
    assert rc == 0, "rawcheck2 failed"
    rc = py("scripts/claude_lis320_check_we3.py", "--seeds", str(seeds_all), "--raw", str(raw), "--out",
            str(out / "kept.jsonl"), "--drops", str(out / "drops.jsonl"), out=out / "check.json")
    rep["check_we3_rc"] = rc
    assert rc == 0, "check_we3 failed"
    have = {json.loads(x)["dialog_id"] for x in open(raw, encoding="utf-8") if x.strip()}
    rows = [x for x in open(seeds_all, encoding="utf-8") if x.strip() and json.loads(x)["dialog_id"] in have]
    (out / "seeds.jsonl").write_text("".join(rows), encoding="utf-8")
    rep.update({"dialogs_with_row": len(have), "seeds_kept": len(rows),
                "kept_rows": sum(1 for x in open(out / "kept.jsonl", encoding="utf-8") if x.strip()),
                "raw_sha256": sha(raw), "kept_sha256": sha(out / "kept.jsonl"), "seeds_cut_sha256": sha(out / "seeds.jsonl")})
    (out / "CUT.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps({k2: v for k2, v in rep.items() if k2 != "chunks"}))
    return rep


def selftest() -> None:
    """Reads lis-320 pilot 8 with git show from origin/builder-outbox (fetch it first)."""
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        p = t / "pilot"
        p.mkdir()
        for f in ("raw.jsonl", "kept.jsonl", "seeds.jsonl"):
            (p / f).write_bytes(subprocess.run(["git", "show", f"origin/builder-outbox:{LIS}/pilot8e/{f}"], cwd=ROOT,
                                               capture_output=True, check=True).stdout)
        rows = (p / "raw.jsonl").read_text(encoding="utf-8").splitlines(keepends=True)
        full = t / "full"
        for j, part in ((1, rows[:25]), (2, rows[25:])):
            d = full / f"chunk{j}"
            d.mkdir(parents=True)
            (d / "raw.new.jsonl.gz").write_bytes(gzip.compress("".join(part).encode("utf-8")))
            (d / "SEEDS.sha256.txt").write_text(sha(p / "seeds.jsonl") + "\n", encoding="utf-8")
            (d / "RESULTS.md").write_text(f"CHUNK-SUMMARY K={j} B=0 new={len(part)} calls={len(part)} parsed={len(part)} "
                                          f"rate=1.000 stopped=done rawcheck2_rc=0 worded_ok={25 if j == 1 else 60} "
                                          "of=60 stop=ok\n", encoding="utf-8")
        assert pick(full, 26) == 2 and pick(full, 25) == 1 and pick(full, 61) is None
        (full / "chunk1" / "RESULTS.md").write_text("CHUNK-SUMMARY K=1 B=0 new=25 calls=25 parsed=20 rate=0.800 "
                                                    "stopped=done rawcheck2_rc=0 worded_ok=25 of=60 "
                                                    "stop=parsed_below_85\n", encoding="utf-8")
        assert pick(full, 26) is None, "a failed chunk 1 must block the cut"
        rep = make(full, 2, t / "out", seed=328, n=60)
        got = {json.loads(x)["id"] for x in open(t / "out" / "kept.jsonl", encoding="utf-8") if x.strip()}
        want = {json.loads(x)["id"] for x in open(p / "kept.jsonl", encoding="utf-8") if x.strip()}
        assert got == want, (len(got), len(want), len(got ^ want))
        assert rep["seeds_kept"] == 60 == rep["dialogs_with_row"], rep
        rep1 = make(full, 1, t / "out1", seed=328, n=60)
        assert rep1["seeds_kept"] == len({json.loads(x)["dialog_id"] for x in rows[:25]}), rep1
    print("selftest ok")


def main() -> int:
    a = sys.argv[1:]
    opt = lambda name, d: int(a[a.index(name) + 1]) if name in a else d  # noqa: E731
    if a == ["--selftest"]:
        selftest()
    elif a and a[0] == "pick":
        pick(Path(a[1]), opt("--min", MIN_DIALOGS))
    elif a and a[0] == "make":
        make(Path(a[1]), int(a[2]), Path(a[3]), opt("--seed", 324), opt("--n", 6000))
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
