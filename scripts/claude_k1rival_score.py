#!/usr/bin/env python3
"""0.2d row K1, creative replies against same-size plain models: scoring and the proposed no-harm bar (Creative answers
in chat thread, 2026-09-26, at Month-end's request after Ben's Redirect). Counts only: never prints panel or reply text.

Panel: crepanel02d (artifacts/claude-crepanel02d-20260926/creative, 100 blind items, never run before 0.2d).
Arms, each run ONCE with scripts/claude_panel382_run.py --panel creative (fresh agent per item, per-turn seeds):
  the joined build   --arm <Month-end's module:function> --name <BUILD>
  T  MiniCPM5-1B     python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative \
  Q  Qwen3.5-2B          --panel-dir PD --arm twin --name T|Q|L --model <snapshot> --gen-model <snapshot> --out OUT
  L  LFM2.5-1.2B     (the plain twin recipe: its system line, the whole chat, thinking off, greedy, <= 160 new tokens;
                     snapshots: Benchmarks' pins, as in everyday chat's C1 and the k1c run)
Then: claude_panel382_run.py --panel creative --panel-dir PD --score OUT --names <BUILD>,T,Q,L
      claude_k1rival_score.py --dedupe OUT       (one line per distinct reply to an item, ids D0000.., seed 3824)
Judges: artifacts/claude-k1c-20260926/JUDGE-k1c.md word for word (blind Opus judges 1 and 2 on every line, judge 3
      on the lines they split on; useful yes/no and made-up facts about the user).
Marks: python -B scripts/claude_k1rival_score.py --panel PD/items.jsonl --runs OUT --key OUT/creative_key_u.json \
           --judges J1,J2[,J3] --build BUILD [--splits-out F] [--out RESULTS.json]
  Per rival R: build-only and R-only items (useful), difference, two-sided exact sign test, reading "behind" if the
  one-sided exact sign test favours R at p <= 0.05, "ahead" if it favours the build at p <= 0.05, else "level".
  Proposed no-harm mark per rival (Month-end fixes the bar): not "behind", AND build made-up replies <= R's + 3.
  The row passes when the mark passes for T, Q and L. An equal build fails a given rival's reading about 5% of the
  time or less (exact test, one side). Also printed: the K1 60% line (build >= 60% of items and >= T), made-up,
  empty-reply and fallback counts per arm.
  python -B scripts/claude_k1rival_score.py --selftest    (CPU, synthetic data)
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_k1c_score as KC  # noqa: E402

RIVALS = {"T": "MiniCPM5-1B", "Q": "Qwen3.5-2B", "L": "LFM2.5-1.2B"}
MADEUP_MARGIN, ALPHA, K1_SHARE = 3, 0.05, 0.6
load, yes, sign_p, two_sided, madeup = KC.load, KC.yes, KC.sign_p, KC.two_sided, KC.madeup


def reading(b: int, r: int) -> str:
    return "ahead" if sign_p(b, r) <= ALPHA else "behind" if sign_p(r, b) <= ALPHA else "level"


def score(panel: str, runs: str, keyp: str, judge_spec: str, build: str, splits_out: str = "") -> dict | None:
    items = {it["item_id"]: it for it in load(panel)}
    key = {cid: (v if isinstance(v, list) else [v])
           for cid, v in json.loads(Path(keyp).read_text(encoding="utf-8")).items()}
    js = KC._judges(judge_spec)
    j1, j2 = js[0], js[1]
    miss = [cid for cid in key if cid not in j1 or cid not in j2]
    if miss:
        raise SystemExit(f"k1rival: {len(miss)} ids missing from judge 1 or 2")
    split_u = [cid for cid in key if yes(j1[cid]["useful"]) != yes(j2[cid]["useful"])]
    split_m = [cid for cid in key if madeup(j1[cid]) != madeup(j2[cid])]
    splits = sorted(set(split_u) | set(split_m))
    if len(js) < 3:
        if splits_out:
            Path(splits_out).write_text(json.dumps(splits), encoding="utf-8")
        print(json.dumps({"lines": len(key), "useful_splits": len(split_u), "madeup_splits": len(split_m),
                          "need_third": len(splits)}))
        return None
    j3 = js[2]
    if any(cid not in j3 for cid in splits):
        raise SystemExit("k1rival: split ids missing from judge 3")
    useful, made = {}, {}
    for cid, who in key.items():
        u1, u2 = yes(j1[cid]["useful"]), yes(j2[cid]["useful"])
        m1, m2 = madeup(j1[cid]), madeup(j2[cid])
        u = u1 if u1 == u2 else yes(j3[cid]["useful"])
        m = m1 if m1 == m2 else madeup(j3[cid])
        for k in who:
            useful[(k["arm"], k["item_id"])] = u
            made[(k["arm"], k["item_id"])] = m
    arms = [build, *RIVALS]
    ids = sorted(items)
    for x in arms:
        if any((x, i) not in useful for i in ids):
            raise SystemExit(f"k1rival: arm {x} missing or lacks some items")
    import claude_cre333_agent as C
    last = {}
    for x in arms:
        p = Path(runs) / f"creative_{x}.jsonl"
        if not p.exists():
            raise SystemExit(f"k1rival: {p} missing")
        for r in load(p):
            if r.get("last"):
                last[(x, r["item_id"])] = r.get("reply") or ""
    if any((x, i) not in last for x in arms for i in ids):
        raise SystemExit("k1rival: a run file lacks some items")
    res = {"lines": len(key), "items": len(ids), "build": build,
           "judge12_useful_agree": len(key) - len(split_u), "judge12_madeup_agree": len(key) - len(split_m),
           "third_judged": len(splits)}
    for x in arms:
        res[x] = {"useful_all": sum(useful[(x, i)] for i in ids),
                  "useful_lead": sum(useful[(x, i)] for i in ids if items[i]["turns"]),
                  "useful_uses_facts": sum(useful[(x, i)] for i in ids if items[i]["kind"] == "uses_facts"),
                  "madeup_replies": sum(made[(x, i)] for i in ids),
                  "empty_replies": sum(not last[(x, i)].strip() for i in ids),
                  "fallbacks": sum(last[(x, i)] == C.FALLBACK for i in ids)}
    marks = {}
    for r in RIVALS:
        b = sum(useful[(build, i)] and not useful[(r, i)] for i in ids)
        c = sum(useful[(r, i)] and not useful[(build, i)] for i in ids)
        rd = reading(b, c)
        mu_ok = res[build]["madeup_replies"] <= res[r]["madeup_replies"] + MADEUP_MARGIN
        marks[f"K1.{r}"] = {"rival": RIVALS[r], "diff": res[build]["useful_all"] - res[r]["useful_all"],
                            "build_only": b, "rival_only": c, "p_two_sided": round(two_sided(b, c), 4),
                            "reading": rd, "build_madeup": res[build]["madeup_replies"],
                            "rival_madeup": res[r]["madeup_replies"], "pass": rd != "behind" and mu_ok}
    res["marks_no_harm"] = marks
    res["verdict_no_harm"] = "PASS" if all(m["pass"] for m in marks.values()) else "FAIL"
    need = math.ceil(K1_SHARE * len(ids))
    res["K1_60_line"] = {"need": need, "build": res[build]["useful_all"], "T": res["T"]["useful_all"],
                         "met": res[build]["useful_all"] >= need and res[build]["useful_all"] >= res["T"]["useful_all"]}
    return res


def selftest() -> None:
    ok = 0
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        its = [{"item_id": f"kd-{n:03d}", "kind": "idea" if n % 3 else "uses_facts", "turns": ["x"] if n % 2 else [],
                "last": "r"} for n in range(1, 41)]
        (t / "p.jsonl").write_text("".join(json.dumps(x) + "\n" for x in its), encoding="utf-8")
        s = t / "s"
        s.mkdir()
        rows, key, n = [], {}, 0
        for x in ("E", "T", "Q", "L"):
            run = []
            for it in its:
                k = int(it["item_id"][-3:])
                rep = f"same-{k}" if x in ("E", "T") and k <= 10 else f"{x}-{k}"
                run.append({"item_id": it["item_id"], "turn_i": 0, "last": True, "reply": rep})
                key[f"K{n:04d}"] = {"arm": x, "item_id": it["item_id"]}
                rows.append({"id": f"K{n:04d}", "chat": [], "request": "r", "reply": rep})
                n += 1
            (s / f"creative_{x}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in run), encoding="utf-8")
        (s / "creative_judge.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        (s / "creative_key.json").write_text(json.dumps(key), encoding="utf-8")
        KC.dedupe(str(s), "D")
        u = load(s / "creative_judge_u.jsonl")
        assert len(u) == 150 and all(r["id"].startswith("D") for r in u)          # 10 E/T replies shared
        ok += 1

        def useful(rep):   # E useful on 1-30; T on 1-10 (shared) + 11-14; Q on everything; L on nothing
            a, k = rep.split("-")
            k = int(k)
            return {"same": True, "E": k <= 30, "T": k <= 14, "Q": True, "L": False}[a]
        j = [{"id": r["id"], "useful": "yes" if useful(r["reply"]) else "no",
              "made_up_user_facts": int(r["reply"].startswith("L-"))} for r in u]
        (t / "j.jsonl").write_text("".join(json.dumps(x) + "\n" for x in j), encoding="utf-8")
        a = dict(panel=str(t / "p.jsonl"), runs=str(s), keyp=str(s / "creative_key_u.json"), build="E")
        assert score(**a, judge_spec=f"{t / 'j.jsonl'},{t / 'j.jsonl'}", splits_out=str(t / "sp.json")) is None
        assert json.loads((t / "sp.json").read_text()) == []
        ok += 1
        r = score(**a, judge_spec=f"{t / 'j.jsonl'},{t / 'j.jsonl'},{t / 'j.jsonl'}")
        m = r["marks_no_harm"]
        assert (r["E"]["useful_all"], r["T"]["useful_all"], r["Q"]["useful_all"], r["L"]["useful_all"]) == (30, 14, 40, 0)
        assert m["K1.T"]["reading"] == "ahead" and m["K1.T"]["build_only"] == 16 and m["K1.T"]["rival_only"] == 0
        assert m["K1.Q"]["reading"] == "behind" and not m["K1.Q"]["pass"] and r["verdict_no_harm"] == "FAIL"
        assert m["K1.L"]["pass"] and r["L"]["madeup_replies"] == 40 and r["K1_60_line"] == {
            "need": 24, "build": 30, "T": 14, "met": True}
        ok += 1
        assert reading(5, 5) == "level" and reading(0, 6) == "behind" and reading(6, 0) == "ahead"
        ok += 1
        assert reading(0, 4) == "level" and reading(0, 5) == "behind"               # p 1/16 vs 1/32
    print(f"k1rival score selftest {ok}/4 ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dedupe", default="")
    ap.add_argument("--panel", default="")
    ap.add_argument("--runs", default="")
    ap.add_argument("--key", default="")
    ap.add_argument("--judges", default="")
    ap.add_argument("--build", default="")
    ap.add_argument("--splits-out", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if a.dedupe:
        KC.dedupe(a.dedupe, "D")
        return
    if not a.build or a.build in RIVALS:
        raise SystemExit("k1rival: --build NAME (not T, Q or L)")
    res = score(a.panel, a.runs, a.key, a.judges, a.build, a.splits_out)
    if res is None:
        return
    print(json.dumps(res, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
