#!/usr/bin/env python3
"""Exp 89 registered run: re-run ALL 56 redteam79 cases before/after the fix.

Before = original Thinking; after = QuarantinedThinking89 (runtime subclass
swap only — no existing file is edited). Also runs the fable_thinking_m2
selftest before and through the wrapper, and the X1/X2 mark checks.

Run (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_webfix89_run.py --out artifacts/fable-webfix89-20260921
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402
import fable_thinking_m2 as T  # noqa: E402
import fable_redteam79_probe as P  # noqa: E402 (fires the urllib firewall)
from fable_webfix89_thinking import QuarantinedThinking89, registrable_site  # noqa: E402

# Keep clear of redteam79's own scratch dirs (other agents may read them).
P.ROOT = Path(__file__).resolve().parent.parent / "scratchpad" / "fable_webfix89_rerun"

ORIGINAL = T.Thinking


def run_all_cases() -> list[dict]:
    out = []
    for builder in P.CASES:
        cid, title, expected, fn = builder()
        try:
            observed, verdict, note = fn()
        except Exception as exc:  # noqa: BLE001 — a crash is itself a finding
            observed, verdict, note = f"CRASH {type(exc).__name__}: {exc}", "BUG", "crashed"
        out.append({"id": cid, "title": title, "expected": expected,
                    "observed": observed, "verdict": verdict, "note": note})
    return out


def tally(cases: list[dict]) -> dict:
    return {"cases": len(cases),
            "ok": sum(1 for r in cases if r["verdict"] == "OK"),
            "bug": sum(1 for r in cases if r["verdict"] == "BUG"),
            "unclear": sum(1 for r in cases if r["verdict"] == "UNCLEAR")}


def run_selftest() -> tuple[int, int, int]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = T.selftest()
    text = buf.getvalue()
    n_pass = sum(1 for ln in text.splitlines() if ln.startswith("PASS  "))
    n_fail = sum(1 for ln in text.splitlines() if ln.startswith("FAIL  "))
    return n_pass, n_fail, code


def x1_reproducer() -> dict:
    import shutil
    d = P.ROOT / "x1repro"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    nb = C.Notebook(str(d))
    mind = QuarantinedThinking89(nb, T.FakeSearcher({}), T.FakeFetcher({}))
    item = {"subject": "Phobos", "relation": "orbits", "value": None,
            "url": "https://a.example.org/x",
            "quote": "None of the moons here excite Phobos fans."}
    kept, dropped = mind._quarantine([item], "t")
    rows = [f["value"] for f in nb.facts.values()]
    return {"kept": kept, "dropped": dropped, "stored_values": rows}


def x2_site_count(tag: str, urls: list[str]) -> dict:
    import shutil
    d = P.ROOT / tag
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    nb = C.Notebook(str(d))
    claims = [{"subject": "Phobos", "relation": "orbits", "value": "Mars",
               "url": u, "quote": "Phobos orbits Mars indeed."} for u in urls]
    site = {u: "Phobos orbits Mars indeed." for u in urls}
    mind = QuarantinedThinking89(nb, T.FakeSearcher({"t": claims}), T.FakeFetcher(site))
    mind.assign("t")
    mind.think_once()
    subj = nb.resolve("Phobos").detail["entity_id"]
    sup = mind._support(subj, "orbits")
    sites = sorted({s for v in sup.values() for s in v["domains"]})
    nv = sum(1 for f in nb.facts.values() if f["source"] == "web-verified")
    return {"sites": sites, "n_sites": len(sites), "web_verified": nv,
            "registrable": [registrable_site(u) for u in urls]}


RULE_CHANGED = {
    "RT79-43": ("seen-lists now carry REGISTRABLE domains by design (Fix 2): "
                "'a.example.org' is covered by 'example.org'; exclusion still works."),
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 89 registered run")
    ap.add_argument("--out", default="artifacts/fable-webfix89-20260921")
    args = ap.parse_args()

    before = run_all_cases()
    tb = tally(before)
    self_before = run_selftest()

    T.Thinking = QuarantinedThinking89  # runtime swap for the after-run only
    try:
        after = run_all_cases()
        self_after = run_selftest()
    finally:
        T.Thinking = ORIGINAL

    x1 = x1_reproducer()
    x2 = {
        "RT79-09-subdomain": x2_site_count("x2sub", ["https://a.example.org/x",
                                                     "https://sub.a.example.org/y"]),
        "RT79-53-port": x2_site_count("x2port", ["https://a.example.org/x",
                                                 "https://a.example.org:8080/y"]),
        "RT79-11-homoglyph": x2_site_count("x2homo", ["https://example.org/x",
                                                      "https://exаmple.org/y"]),
    }

    print(f"BEFORE cases={tb['cases']} OK={tb['ok']} BUG={tb['bug']} UNCLEAR={tb['unclear']}")
    ta = tally(after)
    print(f"AFTER  cases={ta['cases']} OK={ta['ok']} BUG={ta['bug']} UNCLEAR={ta['unclear']}")
    print("id before -> after")
    changed = []
    for b, a in zip(before, after):
        flag = "" if b["verdict"] == a["verdict"] else "  *** CHANGED"
        if flag:
            changed.append((b["id"], b["verdict"], a["verdict"]))
        print(f"{b['id']} {b['verdict']} -> {a['verdict']}{flag}")
        if b["verdict"] != a["verdict"]:
            print(f"    before-obs: {b['observed']}")
            print(f"    after-obs:  {a['observed']}")
    print(f"SELFTEST before PASS={self_before[0]} FAIL={self_before[1]} code={self_before[2]}")
    print(f"SELFTEST after  PASS={self_after[0]} FAIL={self_after[1]} code={self_after[2]}")
    print(f"X1 kept={x1['kept']} dropped={x1['dropped']} stored={x1['stored_values']}")
    for k, v in x2.items():
        print(f"X2 {k} sites={v['sites']} n={v['n_sites']} web_verified={v['web_verified']}")

    unclassified = [c for c in changed if c[0] not in RULE_CHANGED and c[2] not in ("OK",)]
    print(f"CHANGED pairs: {changed}")
    print(f"RULE-CHANGED classified: {sorted(RULE_CHANGED)}")
    print(f"UNCLASSIFIED non-OK changes: {unclassified}")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "fable_webfix89_results.json", "w", encoding="utf-8") as f:
        json.dump({"before": before, "before_tally": tb,
                   "after": after, "after_tally": ta,
                   "selftest_before": self_before, "selftest_after": self_after,
                   "x1": x1, "x2": x2, "rule_changed": RULE_CHANGED,
                   "changed": changed, "unclassified": unclassified}, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
