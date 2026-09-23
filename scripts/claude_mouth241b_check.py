#!/usr/bin/env python3
"""Exp 241b M2 (a, b, c), M3 and M5 checks (harness; reads outputs only).
241b vs 241's checks: labels and the wall flag name (--wall241b); an
AMBIGUOUS identical-name passthrough counts as a passthrough in M2(b)
(out == in). The M3 suite rows of 241b are scored with the new scorer
versions (suites harness --scorer241b); the base rows are the sealed
rows scored by the frozen versions. 241 text follows.


  m2a  --frames sweep-frames.jsonl
       every sweep item went through A (route A; a sev-1 fallback fails),
       and its text passes brake v2 rules 1-8 against its frame (rule 9 is
       also re-run against the legacy line and reported).
  m2b  --mouthlog mouth241.log
       route A: legacy(frame) == base line (the frame is the lossless parse)
                and re-rendering that frame gives the same 241 line;
       other routes: 241 line == base line byte for byte.
  m2c  --base-cap DIR --new-cap DIR
       every captured notebook/events.jsonl: same set of logs (names with
       rt136's random mkdtemp suffix dropped; same-name logs compared as
       multisets), and each pair
       identical after normalising the uuid4 event-id suffix (ids -> order of
       first use) and dropping the 'prev' hash chain that is computed over
       those ids. Raw byte identity is reported too (base vs base already
       differs raw: uuid4, exp 228 trace).
  m3   --suite-out DIR --mouthlog mouth241.log
       GATE clean, every suite move a reply-only move with the verdict
       unchanged, every changed line route A of a pre-registered act;
       flips toward abstain listed (re-run alone 5 times by hand).
  m5   --frames sweep-frames.jsonl [--wall241b S --wall228 S]
       mouth overhead per reply (render_line ms): median <= 2, p99 <= 20;
       suite wall <= base + 5 %.
Each prints PASS/FAIL lines and exits 0 (pass) / 1 (fail).
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_mouth241b_brake as B  # noqa: E402
import claude_mouth241b_parse as P  # noqa: E402
import claude_mouth241b_say as S  # noqa: E402


def _jsonl(p):
    with open(p, encoding="utf-8") as fh:
        return [json.loads(x) for x in fh if x.strip()]


def _with_row(fr):
    fr = dict(fr)
    if fr.get("path") and fr["act"] not in ("UNKNOWN_ENTITY", "AMBIGUOUS"):
        fr["_row"] = S.row_for(fr["path"][-1])
    return fr


def _body(text, fr):
    pre = P.NOTE_DROPPED * len(fr.get("notes") or [])
    return text[len(pre):] if text.startswith(pre) else text


def m2a(a) -> int:
    rows = _jsonl(a.frames)
    sweep = {r["id"]: r["text"] for r in _jsonl(a.sweep)} if a.sweep else {}
    fails, r9 = [], []
    for f in rows:
        if f["route"] != "A":
            fails.append((f["id"], f["act"], "route " + f["route"]))
            continue
        fr = _with_row(f["frame"])
        text = sweep.get(f["id"], None)
        if text is None:
            fails.append((f["id"], f["act"], "no sweep text"))
            continue
        body = _body(text, fr)
        ok, fl = B.check(fr, body, (), legacy=_body(f["legacy_text"], fr))
        bad = [x for x in fl if x[0] <= 8]
        if bad:
            fails.append((f["id"], f["act"], bad))
        r9 += [(f["id"], x) for x in fl if x[0] == 9]
    print(f"M2(a): {len(rows)} sweep replies, {len(fails)} unfaithful "
          f"(rules 1-8 or sev-1); rule-9 anchor fails {len(r9)}")
    for x in fails[:50]:
        print("  FAIL", x)
    for x in r9[:20]:
        print("  R9", x)
    print("M2(a)", "PASS" if not fails else "FAIL")
    return 0 if not fails else 1


def m2b(a) -> int:
    rows = _jsonl(a.mouthlog)
    fails = []
    n = {"A": 0, "passthrough": 0, "legacy": 0}
    for e in rows:
        n[e["route"]] = n.get(e["route"], 0) + 1
        if e["route"] != "A":
            if e["out"] != e["in"]:
                fails.append(("unframed/legacy line changed", e["in"], e["out"]))
            continue
        fr = e.get("frame")
        if not fr:
            fails.append(("A line without frame", e["in"], e["out"]))
            continue
        if P.legacy(fr) != e["in"]:
            fails.append(("frame is not the lossless parse", e["in"], fr))
            continue
        frr = _with_row(fr)
        body = _body(e["in"], frr)
        pre = e["in"][:len(e["in"]) - len(body)]
        again = None
        for c in S.candidates(frr):
            ok, _ = B.check(frr, c, (), legacy=body)
            if ok:
                again = pre + c
                break
        if again != e["out"]:
            # names from the notebook can only remove candidates (rule 3);
            # a different pick is reported, never silently accepted
            fails.append(("re-render differs", e["out"], again))
    print(f"M2(b): {len(rows)} suite reply lines; routes {n}; "
          f"{len(fails)} failures")
    for x in fails[:50]:
        print("  FAIL", x)
    print("M2(b)", "PASS" if not fails else "FAIL")
    return 0 if not fails else 1


def _norm_events(path: Path):
    lines = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()
             if x.strip()]
    ids = {}
    for e in lines:
        if "event_id" in e:
            ids.setdefault(e["event_id"], f"EV{len(ids)}")
    out = []
    for e in lines:
        e = dict(e)
        e.pop("prev", None)
        s = json.dumps(e, sort_keys=True, ensure_ascii=False)
        for k, v in ids.items():
            s = s.replace(k, v)
        out.append(s)
    return out


_RAND_DIR = re.compile(r"(C\d+)_[a-z0-9_]{8}(?=__)")


def _group(d: Path) -> dict:
    """normalised log name -> files. rt136 case dirs carry a random
    mkdtemp suffix ('C001_f3i14a99'); it is dropped from the name."""
    g = {}
    for p in sorted(d.iterdir()):
        g.setdefault(_RAND_DIR.sub(r"\1", p.name), []).append(p)
    return g


def m2c(a) -> int:
    bd, nd = Path(a.base_cap) / "events", Path(a.new_cap) / "events"
    bg, ng = _group(bd), _group(nd)
    bn, nn = set(bg), set(ng)
    fails = []
    if bn != nn:
        fails.append(("log set differs", sorted(bn ^ nn)[:10]))
    raw_same = norm_same = tot = 0
    for name in sorted(bn & nn):
        bs, ns = bg[name], ng[name]
        tot += max(len(bs), len(ns))
        if len(bs) != len(ns):
            fails.append(("log count differs", name, len(bs), len(ns)))
        # compare as multisets of normalised contents
        braw = sorted(p.read_bytes() for p in bs)
        nraw = sorted(p.read_bytes() for p in ns)
        raw_same += sum(1 for x, y in zip(braw, nraw) if x == y)
        bnorm = sorted(json.dumps(_norm_events(p)) for p in bs)
        nnorm = sorted(json.dumps(_norm_events(p)) for p in ns)
        k = sum(1 for x, y in zip(bnorm, nnorm) if x == y)
        norm_same += k
        if bnorm != nnorm:
            fails.append(("events differ", name))
    print(f"M2(c): {len(bn)} base logs, {len(nn)} 241b logs; normalised "
          f"identical {norm_same}/{tot}; raw identical {raw_same}/{tot}")
    for x in fails[:30]:
        print("  FAIL", x)
    print("M2(c)", "PASS" if not fails else "FAIL")
    return 0 if not fails else 1


# pre-registered move classes (PASSMARKS "Predicted moves by act"): a reply
# text may change only on a line A rendered (route A) of one of these acts;
# no verdict / status / storage change anywhere
PREDICTED_ACTS = {
    "SAVED", "DUPLICATE", "CONFLICT", "CONFIRM_RESULT", "FORGOTTEN",
    "FORGOTTEN_ONE", "NOT_HAD", "ABSTAIN_MISSING", "UNKNOWN_ENTITY",
    "AMBIGUOUS", "BROKEN_CHAIN", "YESNO_YES", "YESNO_NO", "YESNO_NOTKNOWN",
    "REVERSE", "ANSWER", "ANSWER_LIST", "SELF_PEOPLE", "SELF_FACTS",
    "SELF_SLEPT", "SELF_TURNS", "SELF_ANSWERED",
}


def m3(a) -> int:
    out = Path(a.suite_out)
    summ = json.loads((out / "SUITEDIFF218-SUMMARY.json").read_text())
    fails = []
    if summ.get("gate") != "GATE: clean":
        fails.append(("gate", summ.get("gate")))
    abstain_flips = []
    for suite in summ["suites"]:
        d = json.loads((out / f"{suite}-diff.json").read_text())
        for mv in d.get("moves", []):
            bv, nv = mv.get("base_verdict"), mv.get("new_verdict")
            if mv.get("class") != "reply-only move" or bv != nv:
                fails.append((suite, mv.get("id"), mv.get("class"), bv, nv))
            if bv != nv and str(nv).lower() in ("abstain", "missed",
                                                "unhelpful"):
                abstain_flips.append((suite, mv.get("id"), bv, nv))
    by_act = {}
    for e in _jsonl(a.mouthlog):
        if e["out"] == e["in"]:
            continue
        k = (e["route"], e.get("act"))
        by_act[k] = by_act.get(k, 0) + 1
        if e["route"] != "A" or e.get("act") not in PREDICTED_ACTS:
            fails.append(("unpredicted move", e["route"], e.get("act"),
                          e["in"][:80]))
    for line in summ.get("summary_lines", []):
        print("  " + line)
    print("  " + str(summ.get("gate")))
    print("M3 changed reply lines by (route, act):")
    for k in sorted(by_act, key=str):
        print(f"  {k[0]:11s} {str(k[1]):16s} {by_act[k]}")
    print(f"M3 flips toward abstain: {len(abstain_flips)} (each is re-run "
          f"alone 5 times and reported)")
    for x in abstain_flips:
        print("  FLIP", x)
    for x in fails[:50]:
        print("  FAIL", x)
    print("M3", "PASS" if not fails else "FAIL")
    return 0 if not fails else 1


def m5(a) -> int:
    ms = sorted(float(f["ms"]) for f in _jsonl(a.frames))
    med = statistics.median(ms)
    p99 = ms[min(len(ms) - 1, int(round(0.99 * (len(ms) - 1))))]
    ok = med <= 2.0 and p99 <= 20.0
    print(f"M5 latency: n={len(ms)} median={med:.3f} ms p99={p99:.3f} ms "
          f"max={ms[-1]:.3f} ms")
    if a.wall241b is not None and a.wall228 is not None:
        lim = a.wall228 * 1.05
        wok = a.wall241b <= lim
        print(f"M5 suite wall: 241b {a.wall241b:.1f}s vs 228 {a.wall228:.1f}s "
              f"(limit {lim:.1f}s) {'ok' if wok else 'over'}")
        ok = ok and wok
    print("M5", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["m2a", "m2b", "m2c", "m3", "m5"])
    ap.add_argument("--suite-out")
    ap.add_argument("--frames")
    ap.add_argument("--sweep")
    ap.add_argument("--mouthlog")
    ap.add_argument("--base-cap")
    ap.add_argument("--new-cap")
    ap.add_argument("--wall241b", type=float)
    ap.add_argument("--wall228", type=float)
    a = ap.parse_args(argv)
    return {"m2a": m2a, "m2b": m2b, "m2c": m2c, "m3": m3,
            "m5": m5}[a.what](a)


if __name__ == "__main__":
    raise SystemExit(main())
