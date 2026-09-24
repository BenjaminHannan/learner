#!/usr/bin/env python3
"""lis-314 / lis-315 registered run: the listener stack on the sealed confirm panel.

Panel: artifacts/claude-lispanel314-20260924/ (TEST-ONLY; written blind; key audited blind).
  panel.jsonl {dialog_id, turn_index, user, kind}; key_v2.jsonl {dialog_id, turn_index, facts
  (each may carry alt_rels), optional_facts, answer, ask_fact, exclude} (adjudicated key). Panel user turns are never printed.

Arms (fresh 292t agent per dialog; reader = lis-301 merged, T = 0.995):
  A  292t alone (no reader)                  reference only
  C  + 310                                   the current wrapper
  P  + 310 + 315                             per-fact release
  K  + 310 + 314                             confirm-at-use
  S  + 310 + 313 + 315 + 314                 the stack without guards
  G  + 310 + 313 + 315 + 314 + 316           the full stack with the lis-316 code guards

Simulated user (mechanical, from the key): whenever the agent asks the user something it can
act on (turn310's "Just to check ...?" ask-back or lis-314's "I think you told me X, is that
right?"), the harness answers "yes" if that fact is true at that point of the dialog (latest
keyed value for the same owner and relation) and "no" otherwise, as an extra turn. Every such
question counts as one question to the user.

python -B scripts/claude_lis314_run.py --arm K --model DIR --out DIR
python -B scripts/claude_lis314_run.py --score DIR     (writes DIR/summary.json)
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
PANEL = ROOT / "artifacts/claude-lispanel314-20260924"
LAYERS = {"C": (), "P": ("315",), "K": ("314",), "S": ("313", "315", "314"),
          "G": ("313", "315", "314", "316")}


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def norm(s):
    return str(s or "").strip().lower()


def subj_of(owner):
    return "user" if norm(owner) == "me" else norm(owner)


def truth_update(truth, facts):
    """truth maps (owner, rel) -> value. A key fact may carry "alt_rels" (an adjudicated
    either-reading): the same value under an alternative relation also counts as true. Alt
    entries are marked with a leading "~" on the relation in their key."""
    for f in facts or []:
        o = subj_of(f["owner"])
        for k in [k for k in truth if k[0] == o and k[1].lstrip("~") in
                  [f["rel"]] + list(f.get("alt_rels") or [])]:
            del truth[k]
        truth[(o, f["rel"])] = f["value"]
        for alt in f.get("alt_rels") or []:
            truth[(o, "~" + alt)] = f["value"]


def optional_update(truth, facts):
    """Adjudicated optional facts: saving one is not a wrong save, but it is not required
    (not counted in the facts-saved denominator). Marked with a leading "?" on the relation."""
    for f in facts or []:
        truth[(subj_of(f["owner"]), "?" + f["rel"])] = f["value"]


def true_value(truth, owner, rel):
    for r in (rel, "~" + rel):
        if (owner, r) in truth:
            return truth[(owner, r)]
    return truth.get((owner, "?" + rel))


def is_true(truth, f):
    return norm(true_value(truth, subj_of(f.get("owner")), f.get("rel"))) == norm(f.get("value")) != ""


def build(arm, reader, state_dir):
    import claude_loop292t_agent as T292
    cfg = copy.deepcopy(T292.DEFAULT_CONFIG292T)
    cfg["state_dir"] = state_dir
    cfg["sleep_threshold"] = 100000
    loop = T292.build_agent292t(cfg)
    if arm != "A":
        import claude_lis_stack as STACK
        STACK.build_stack(loop, reader, 0.995, layers=LAYERS[arm], log_dir=state_dir)
    return loop


def pending_question(loop):
    """The fact the agent just asked the user about, or None."""
    f = getattr(loop, "lis314_confirming", None)
    if f:
        return "confirm", f
    p = getattr(loop, "lis310_pending", None)
    if p and isinstance(p.get("fact"), dict):
        return "askback", p["fact"]
    return None, None


def run(a):
    import fable_loop90_agent as L90
    reader = None
    if a.arm != "A":
        import claude_lis300_read as READ
        reader = READ.Reader(a.model)
    turns, key = load(PANEL / "panel.jsonl"), {(k["dialog_id"], k["turn_index"]): k
                                              for k in load(PANEL / "key_v2.jsonl")}
    order, by = [], {}
    for it in turns:
        if it["dialog_id"] not in by:
            by[it["dialog_id"]] = []
            order.append(it["dialog_id"])
        by[it["dialog_id"]].append(it)
    rows = []
    for d in order:
        tmp = tempfile.mkdtemp(prefix=f"lis314-{a.arm}-")
        loop = build(a.arm, reader, tmp)
        truth = {}
        try:
            for it in sorted(by[d], key=lambda x: x["turn_index"]):
                k = key[(d, it["turn_index"])]
                truth_update(truth, k.get("facts"))
                optional_update(truth, k.get("optional_facts"))
                t0 = time.time()
                parts = [" ".join(loop.turn(it["user"]))]
                ms = [round((time.time() - t0) * 1000, 1)]
                asked = []
                for _ in range(3):  # at most 3 follow-up questions per panel turn
                    kind, f = pending_question(loop)
                    if kind is None or not parts[-1].strip().endswith("?"):
                        break
                    ans = "yes" if is_true(truth, f) else "no"
                    asked.append({"kind": kind, "fact": f, "answer": ans})
                    t0 = time.time()
                    parts.append(" ".join(loop.turn(ans)))
                    ms.append(round((time.time() - t0) * 1000, 1))
                rows.append({"dialog_id": d, "turn_index": it["turn_index"], "replies": parts,
                             "asked": asked, "ms": ms, "truth": [[s, r, v] for (s, r), v in
                                                                 sorted(truth.items())],
                             "pending": [[p["owner"], p["rel"], p["value"]] for p in
                                         getattr(loop, "lis314_store", [])],
                             "stored_triples": sorted([s, r, v] for (s, r, v) in
                                                      L90.notebook_triples(loop.nb))})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        print(f"[lis314/{a.arm}] {d} turns={len(by[d])}", flush=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"arm_{a.arm}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"wrote arm_{a.arm}.jsonl rows={len(rows)}")


def score_arm(runs, key, panel_kind):
    import claude_lis313_agent as L313
    C = Counter()
    prev, ms = {}, []
    last = {}
    for r in runs:
        d, i = r["dialog_id"], r["turn_index"]
        k = key[(d, i)]
        kind = panel_kind[(d, i)]
        truth = {(s, rr): v for s, rr, v in r["truth"]}  # includes "~alt" entries
        before = prev.get(d, [])
        new = [t for t in r["stored_triples"] if t not in before]
        prev[d] = r["stored_triples"]
        last[d] = r
        ms += r["ms"]
        C["turns"] += 1
        C[f"kind_{kind}"] += 1
        C["questions_to_user"] += len(r["asked"])
        for q in r["asked"]:
            C[f"q_{q['kind']}_{q['answer']}"] += 1
        bad = [t for t in new if norm(true_value(truth, norm(t[0]), t[1])) != norm(t[2])]
        if bad:
            C["wrong_save_turns"] += 1
            C["wrong_saved_facts"] += len(bad)
        if kind == "ask" and k.get("exclude"):
            C["ask_excluded"] += 1
        elif kind == "ask":
            text = " ".join(r["replies"])
            first = r["replies"][0]
            gold = k.get("answer")
            confirmed_no = any(q["answer"] == "no" for q in r["asked"])
            C["ask"] += 1
            if gold is None:
                C["ask_untold"] += 1
                if L313.is_abstain313(first) or r["asked"]:
                    C["ask_untold_abstain"] += 1
                else:
                    C["ask_untold_stated"] += 1
            elif gold in text and not confirmed_no:
                C["ask_right"] += 1
            elif L313.is_abstain313(first) or confirmed_no:
                C["ask_abstain"] += 1
            else:
                C["ask_wrong"] += 1
    for d, r in last.items():
        stored = {(norm(s), rr, norm(v)) for s, rr, v in r["stored_triples"]}  # USER -> "user"
        pend = {(subj_of(o), rr, norm(v)) for o, rr, v in r.get("pending", [])}
        tr = {(s, rr): v for s, rr, v in r["truth"]}
        for (s, rr), v in tr.items():
            if rr.startswith(("~", "?")):
                continue
            alts = [a[1].lstrip("~") for a in tr if a[0] == s and a[1].startswith("~")
                    and norm(tr[a]) == norm(v)]
            ok = [(s, x, norm(v)) for x in [rr] + alts]
            C["final_facts"] += 1
            C["final_facts_saved"] += int(any(o in stored for o in ok))
            C["final_facts_saved_or_pending"] += int(any(o in stored | pend for o in ok))
        C["final_pending"] += len(pend)
    res = dict(C)
    res["facts_saved_pct"] = round(100 * C["final_facts_saved"] / max(1, C["final_facts"]), 1)
    res["facts_saved_or_pending_pct"] = round(
        100 * C["final_facts_saved_or_pending"] / max(1, C["final_facts"]), 1)
    res["asks_told"] = C["ask"] - C["ask_untold"]  # excluded asks are in neither
    res["turns_per_question"] = round(C["turns"] / max(1, C["questions_to_user"]), 2)
    if ms:
        ms.sort()
        res["ms_median"] = ms[len(ms) // 2]
        res["ms_p90"] = ms[int(len(ms) * 0.9)]
        res["ms_max"] = ms[-1]
    return res


def score(a):
    key = {(k["dialog_id"], k["turn_index"]): k for k in load(PANEL / "key_v2.jsonl")}
    kind = {(t["dialog_id"], t["turn_index"]): t["kind"] for t in load(PANEL / "panel.jsonl")}
    d = Path(a.score)
    out = {}
    for arm in ("A", "C", "P", "K", "S", "G"):
        p = d / f"arm_{arm}.jsonl"
        if p.exists():
            out[arm] = score_arm(load(p), key, kind)
    (d / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["A", "C", "P", "K", "S", "G"])
    ap.add_argument("--model")
    ap.add_argument("--out")
    ap.add_argument("--score")
    a = ap.parse_args()
    if a.score:
        score(a)
    else:
        run(a)


if __name__ == "__main__":
    main()
