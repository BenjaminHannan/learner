#!/usr/bin/env python3
"""g406b-L: g406b with GPT-6 Luna as the labeller ("Making things up about you", 2026-09-27).
New file. It imports claude_g406_2_glm unchanged and swaps only its module-level caller (`call_low`) for
claude_luna_codex.call. Prompt (--mode two), parser, attempts, best-row rule and arm report are claude_g406_2_glm's.
Marks: artifacts/claude-g406l-20260927/PASSMARKS.md.

  every claude_g406_2_glm.py flag works as before, with Luna as the caller, plus:
  --pilot N                         run on the first N packets in load order only (the pilot gate's input)
  pilot-check --glm OUT --n N       the pilot gate: >= N-1 of the first N packets have a usable row, and no
                                    kept error text names a usage or rate limit; JSON, exit 0 on pass, 1 on fail
  selftest-luna                     offline checks (no network)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import claude_g406_2_glm as G2  # noqa: E402

LIMIT_WORDS = ("usage limit", "rate limit")


def luna_call(text: str) -> str:
    import claude_luna_codex as L
    return L.call(text) or ""


G2.call_low = luna_call


def pilot_check(glm: str, packets: list[dict], n: int) -> dict:
    first = {(p["src"], p["pid"]) for p in packets[:n]}
    rows = [r for r in map(json.loads, Path(glm).read_text(encoding="utf-8").splitlines())
            if (r["src"], r["pid"]) in first] if Path(glm).exists() else []
    usable = {(r["src"], r["pid"]) for r in rows if r["ok"]}
    limit = sum(1 for r in rows if any(w in (r.get("error") or "").lower() for w in LIMIT_WORDS))
    return {"pilot_packets": len(first), "rows": len(rows), "usable": len(usable), "limit_errors": limit,
            "pass": len(usable) >= len(first) - 1 and limit == 0}


def selftest_luna() -> None:
    import tempfile
    ok = 0
    assert G2.call_low is luna_call; ok += 1
    pk = [{"src": "s", "pid": f"p{i}", "conversation": [], "earlier": []} for i in range(12)]
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "g.jsonl"
        rows = [{"src": "s", "pid": f"p{i}", "ok": i != 3, "error": "" if i != 3 else "unparsed reply"}
                for i in range(10)]
        f.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        assert pilot_check(str(f), pk, 10)["pass"]; ok += 1
        rows[4] = dict(rows[4], ok=False, error="luna call failed after 3 tries: error-like or empty reply: "
                                                "'Usage limit reached'")
        f.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        res = pilot_check(str(f), pk, 10)
        assert not res["pass"] and res["usable"] == 8 and res["limit_errors"] == 1; ok += 1
        rows += [{"src": "s", "pid": "p3", "ok": True, "error": ""}]   # a later attempt fixes p3; p4's limit error stays
        f.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        assert not pilot_check(str(f), pk, 10)["pass"]; ok += 1
    orig = G2.load_packets
    try:
        G2.load_packets = lambda pats: pk
        sys.argv = ["x", "--mode", "two", "--pilot", "5", "--print-prompt"]
        n = pilot_arg()
        assert n == 5 and "--pilot" not in sys.argv and len(G2.load_packets([])) == 5; ok += 1
    finally:
        G2.load_packets = orig
    print(f"g406l luna selftest {ok}/5 ok")


def pilot_arg() -> int:
    """Removes `--pilot N` from sys.argv and makes G2.load_packets return only the first N packets."""
    if "--pilot" not in sys.argv:
        return 0
    i = sys.argv.index("--pilot")
    n = int(sys.argv[i + 1])
    del sys.argv[i:i + 2]
    orig = G2.load_packets
    G2.load_packets = lambda pats: orig(pats)[:n]
    return n


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "selftest-luna":
        return selftest_luna()
    if len(sys.argv) > 1 and sys.argv[1] == "pilot-check":
        a = sys.argv
        pats = [a[i + 1] for i, x in enumerate(a) if x == "--packets"]
        res = pilot_check(a[a.index("--glm") + 1], G2.load_packets(pats), int(a[a.index("--n") + 1]))
        print(json.dumps(res))
        raise SystemExit(0 if res["pass"] else 1)
    pilot_arg()
    G2.main()


if __name__ == "__main__":
    main()
