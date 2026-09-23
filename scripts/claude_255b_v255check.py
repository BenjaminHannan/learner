#!/usr/bin/env python3
"""Exp 255b extra report: 255b vs 255 on the M4 probes and M6 dialogs.

Every reply difference between the sealed 255 arm and the 255b arm must
be a Part A line (255's T02 text -> 255b's T02 text) or a Part B line
(a 255 zero-count rendering -> the director's zero text). Anything else
is reported as an unexpected difference and fails.

usage: claude_255b_v255check.py <255-run-dir> <255b-run-dir> <out.json>
  <255-run-dir>: artifacts/claude-fixedtext255-20260922/run
  <255b-run-dir>: the 255b pilot/registered run dir (same layout, 255b arm
    files: vp/255b-*.json, probe/255b-*.json)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fix255_text as T255  # noqa: E402 (read-only)
import claude_fix255b_text as T255B  # noqa: E402 (read-only)


def build_delta_map() -> dict[str, tuple[str, str]]:
    """255-text -> (255b-text, part) for every line where 255b differs."""
    d: dict[str, tuple[str, str]] = {}
    d[T255.Q2_NEW] = (T255B.T02_NEW_255B, "A")
    olds: list[str] = []
    for n in range(41):
        olds.append(f"We have had {n} turns.")
        olds.append(f"Yes. I hold {n} quarantined web row. I filed it but "
                    f"I do not believe it.")
        olds.append(f"Yes. I have slept {n} times.")
        olds.append(f"Yes, {n} times I asked for clarification instead "
                    f"of saving.")
        olds.append("I have no record of yesterday. My log starts with "
                    f"our first turn here and holds {n} turns.")
        olds.append("Nobody besides you has spoken to me. All "
                    f"{n} turns are yours.")
        olds.append(f"No. I understood all {n} turns; I asked for "
                    f"clarification 0 times.")
    for o in olds:
        r255, t255 = T255.rewrite255(o)
        r255b, t255b = T255B.rewrite255b(o)
        if t255 is None and t255b is None:
            assert r255 == o and r255b == o, o
            continue  # n >= 10 digit form: neither arm rewrites
        assert t255 == t255b and t255 is not None, o
        if r255 != r255b:
            d[r255] = (r255b, "B")
    return d


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def check_pair(a: str, b: str, delta: dict) -> tuple[bool, str | None]:
    if a == b:
        return True, None
    la, lb = a.split("\n"), b.split("\n")
    if len(la) == len(lb):
        parts = []
        for x, y in zip(la, lb):
            if x == y:
                continue
            if x not in delta or delta[x][0] != y:
                return False, None
            parts.append(delta[x][1])
        return True, "+".join(sorted(set(parts)))
    if a in delta and delta[a][0] == b:
        return True, delta[a][1]
    return False, None


def main(argv) -> int:
    base, new, out = Path(argv[0]), Path(argv[1]), Path(argv[2])
    delta = build_delta_map()
    diffs, bad = [], []
    for p in ("probes", "probes-supp"):
        a = jl(base / "vp" / f"255-{p}.json")
        b = jl(new / "vp" / f"255b-{p}.json")
        for x, y in zip(a, b):
            assert x["id"] == y["id"], (p, x["id"])
            k = 0
            for tx, ty in zip(x["rows"], y["rows"]):
                if tx.get("restart"):
                    continue
                if tx.get("reply") != ty.get("reply"):
                    ok, part = check_pair(tx["reply"], ty["reply"], delta)
                    rec = {"file": p, "id": x["id"], "turn": k,
                           "part": part, "255": tx["reply"],
                           "255b": ty["reply"]}
                    (diffs if ok else bad).append(rec)
                k += 1
    for p in ("p3-dialogs", "p3c-restart2", "p3d-ghost", "v-dialogs",
              "v-supp"):
        a = jl(base / "probe" / f"255-{p}.json")["rows"]
        b = jl(new / "probe" / f"255b-{p}.json")["rows"]
        for x, y in zip(a, b):
            assert x["dialog"] == y["dialog"], (p, x["dialog"])
            for i, (ta, tb) in enumerate(zip(x["turns"], y["turns"])):
                if ta["reply"] != tb["reply"]:
                    ok, part = check_pair(ta["reply"], tb["reply"], delta)
                    rec = {"file": p, "dialog": x["dialog"], "turn": i,
                           "part": part, "255": ta["reply"],
                           "255b": tb["reply"]}
                    (diffs if ok else bad).append(rec)
    by_part: dict[str, int] = {}
    for r in diffs:
        by_part[r["part"]] = by_part.get(r["part"], 0) + 1
    res = {"diffs": len(diffs), "by_part": by_part,
           "unexpected": len(bad), "bad": bad,
           "pass": not bad,
           "changes": diffs}
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(f"255b-vs-255: diffs={len(diffs)} by_part={by_part} "
          f"unexpected={len(bad)}")
    print("EXTRA", "PASS" if not bad else "FAIL")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
