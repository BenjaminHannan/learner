#!/usr/bin/env python3
"""k1c scorer (Creative answers in chat thread, 2026-09-26). Counts only: never prints panel or reply text.

Two panels, each run by claude_panel382_run.py and scored by its --score step into its own folder:
  A = k1cpanel (artifacts/claude-k1cpanel-20260926/creative, 100 fresh items), B = k1apanel
  (artifacts/claude-k1apanel-20260926/creative, the 60 items k1a ran on). Item ids differ (kq-* and kc-*).
Arms: C (k1c: k1a + the 1B picks among its own 4 drafts), K (k1a), T (plain MiniCPM5-1B), Q (plain Qwen3.5-2B),
L (plain LFM2.5-1.2B; optional). T, Q and L all use the plain twin recipe (claude_e2e336_twinb.py).

Step 1, per panel, one verdict per distinct reply (arms that wrote the same reply to the same item share it):
  python -B scripts/claude_k1c_score.py --dedupe SCORE --prefix A|B
      reads SCORE/creative_judge.jsonl + creative_key.json; writes SCORE/creative_judge_u.jsonl (ids A0000.. or
      B0000.., shuffled with seed 3824) and SCORE/creative_key_u.json {uid: [{arm, item_id}, ...]}; counts only.
Step 2, after judges 1 and 2 judged both packets (and judge 3 the split lines):
  python -B scripts/claude_k1c_score.py --panels PA/items.jsonl,PB/items.jsonl --runs OUTA,OUTB \
      --keys SA/creative_key_u.json,SB/creative_key_u.json --judges J1A+J1B,J2A+J2B[,J3] \
      [--splits-out SPLITS.json] [--out RESULTS.json]
  (a judge slot may join several files with "+"). Without judge 3 it writes the ids that need a third judge to
  --splits-out and stops. Resolution as in k1a: judge 3 decides a field only where judges 1 and 2 split on it.
Marks: artifacts/claude-k1c-20260926/PASSMARKS-k1c.md (fixed before any registered run).
  python -B scripts/claude_k1c_score.py --selftest     (CPU, synthetic data)
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_k1a_score as KS  # noqa: E402

ARMS = ("C", "K", "T", "Q", "L")
RIVALS = {"T": "MiniCPM5-1B", "Q": "Qwen3.5-2B", "L": "LFM2.5-1.2B"}
REQUIRED = ("C", "K", "T", "Q")
BAR_GAIN, BAR_P, BAR_MADEUP, BAR_FALLBACK, K1_SHARE = 8, 0.05, 4, 2, 0.6
load, yes, sign_p = KS.load, KS.yes, KS.sign_p


def two_sided(b: int, c: int) -> float:
    return min(1.0, 2 * min(sign_p(b, c), sign_p(c, b)))


def dedupe(score_dir: str, prefix: str) -> None:
    d = Path(score_dir)
    rows = load(d / "creative_judge.jsonl")
    key = json.loads((d / "creative_key.json").read_text(encoding="utf-8"))
    groups: dict = {}
    for r in rows:
        k = key[r["id"]]
        body = {f: r[f] for f in r if f != "id"}
        g = groups.setdefault((k["item_id"], r["reply"]), {"body": body, "who": []})
        g["who"].append({"arm": k["arm"], "item_id": k["item_id"]})
    pool = sorted(groups.values(), key=lambda g: (g["who"][0]["item_id"], sorted(w["arm"] for w in g["who"])))
    random.Random(3824).shuffle(pool)
    ukey = {}
    with open(d / "creative_judge_u.jsonl", "w", encoding="utf-8") as fh:
        for n, g in enumerate(pool):
            uid = f"{prefix}{n:04d}"
            ukey[uid] = g["who"]
            fh.write(json.dumps(dict(id=uid, **g["body"]), ensure_ascii=False) + "\n")
    (d / "creative_key_u.json").write_text(json.dumps(ukey, indent=1), encoding="utf-8")
    print(json.dumps({"prefix": prefix, "lines": len(rows), "distinct_lines": len(pool),
                      "shared_by_2plus_arms": sum(len(g["who"]) > 1 for g in pool)}))


def _judges(spec: str) -> list[dict]:
    out = []
    for slot in [s for s in spec.split(",") if s]:
        j = {}
        for p in slot.split("+"):
            for r in load(p):
                if r["id"] in j:
                    raise SystemExit(f"k1c score: id {r['id']} twice in one judge slot")
                j[r["id"]] = r
        out.append(j)
    return out


def madeup(j: dict) -> bool:
    return int(j.get("made_up_user_facts", 0) or 0) >= 1


def score(panels: list[str], runs: list[str], keys: list[str], judge_spec: str, splits_out: str = "") -> dict | None:
    items = {}
    for p in panels:
        for it in load(p):
            if it["item_id"] in items:
                raise SystemExit("k1c score: an item id appears in two panels")
            items[it["item_id"]] = it
    key = {}
    for kp in keys:
        for cid, v in json.loads(Path(kp).read_text(encoding="utf-8")).items():
            if cid in key:
                raise SystemExit("k1c score: a line id appears in two keys")
            key[cid] = v if isinstance(v, list) else [v]
    js = _judges(judge_spec)
    j1, j2 = js[0], js[1]
    miss = [cid for cid in key if cid not in j1 or cid not in j2]
    if miss:
        raise SystemExit(f"k1c score: {len(miss)} ids missing from judge 1 or 2")
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
    miss3 = [cid for cid in splits if cid not in j3]
    if miss3:
        raise SystemExit(f"k1c score: {len(miss3)} split ids missing from judge 3")
    useful, made = {}, {}
    for cid, who in key.items():
        u1, u2 = yes(j1[cid]["useful"]), yes(j2[cid]["useful"])
        m1, m2 = madeup(j1[cid]), madeup(j2[cid])
        u = u1 if u1 == u2 else yes(j3[cid]["useful"])
        m = m1 if m1 == m2 else madeup(j3[cid])
        for k in who:
            useful[(k["arm"], k["item_id"])] = u
            made[(k["arm"], k["item_id"])] = m
    arms = [x for x in ARMS if any(k[0] == x for k in useful)]
    for need in REQUIRED:
        if need not in arms:
            raise SystemExit(f"k1c score: arm {need} missing")
    ids = sorted(items)
    for x in arms:
        if any((x, i) not in useful for i in ids):
            raise SystemExit(f"k1c score: arm {x} lacks some items")
    import claude_cre333_agent as C
    last: dict = {}
    for rd in runs:
        for x in arms:
            p = Path(rd) / f"creative_{x}.jsonl"
            if not p.exists():
                raise SystemExit(f"k1c score: {p} missing")
            for r in load(p):
                if r.get("last"):
                    last[(x, r["item_id"])] = r.get("reply") or ""
    if any((x, i) not in last for x in arms for i in ids):
        raise SystemExit("k1c score: a run file lacks some items")
    fallbacks = Counter(x for (x, i), t in last.items() if t == C.FALLBACK)
    empty = Counter(x for (x, i), t in last.items() if not t.strip())
    bare = Counter(x for (x, i), t in last.items() if KS.BARE_END.search(t))

    def cnt(arm, grp):
        return sum(useful[(arm, i)] for i in grp)

    def pair(a1, a2, grp):
        b = sum(useful[(a1, i)] and not useful[(a2, i)] for i in grp)
        c = sum(useful[(a2, i)] and not useful[(a1, i)] for i in grp)
        return b, c
    panel_of = {}
    for n, p in enumerate(panels):
        for it in load(p):
            panel_of[it["item_id"]] = "AB"[n] if len(panels) <= 2 else str(n)
    groups = {"all": ids, "panel_A": [i for i in ids if panel_of[i] == "A"],
              "panel_B": [i for i in ids if panel_of[i] == "B"],
              "lead": [i for i in ids if items[i]["turns"]], "nolead": [i for i in ids if not items[i]["turns"]],
              "idea": [i for i in ids if items[i]["kind"] == "idea"],
              "uses_facts": [i for i in ids if items[i]["kind"] == "uses_facts"]}
    res = {"lines": len(key), "items": len(ids), **{f"n_{g}": len(v) for g, v in groups.items() if g != "all"},
           "judge12_useful_agree": len(key) - len(split_u), "judge12_madeup_agree": len(key) - len(split_m),
           "third_judged": len(splits)}
    for x in arms:
        res[x] = {**{f"useful_{g}": cnt(x, v) for g, v in groups.items()},
                  "madeup_replies": sum(made[(x, i)] for i in ids), "fallbacks": fallbacks[x],
                  "empty_replies": empty[x], "bare_list_endings": bare[x]}
    b, c = pair("C", "K", ids)
    d = res["C"]["useful_all"] - res["K"]["useful_all"]
    p = sign_p(b, c)
    marks = {
        "K1c.1": {"C_minus_K": d, "C_only": b, "K_only": c, "sign_p": round(p, 4),
                  "pass": d >= BAR_GAIN and p <= BAR_P},
        "K1c.2": {"C_madeup": res["C"]["madeup_replies"], "K_madeup": res["K"]["madeup_replies"],
                  "pass": res["C"]["madeup_replies"] <= res["K"]["madeup_replies"] + BAR_MADEUP},
        "K1c.3": {"C_fallbacks": fallbacks["C"], "K_fallbacks": fallbacks["K"],
                  "pass": fallbacks["C"] <= fallbacks["K"] + BAR_FALLBACK},
    }
    res["marks_k1c"] = marks
    res["verdict_k1c"] = "PASS" if all(m["pass"] for m in marks.values()) else "FAIL"
    need = math.ceil(K1_SHARE * len(ids))
    rivals = [r for r in RIVALS if r in arms]
    k1 = {"C_useful_all": res["C"]["useful_all"], "need": need,
          **{f"{r}_useful_all": res[r]["useful_all"] for r in rivals}}
    k1["pass"] = res["C"]["useful_all"] >= need and all(res["C"]["useful_all"] >= res[r]["useful_all"]
                                                           for r in rivals)
    res["K1_line"] = k1
    riv = {}
    for arm in ("C", "K"):
        for r in rivals:
            rb, rc = pair(arm, r, ids)
            reading = ("ahead" if sign_p(rb, rc) <= 0.05 else "behind" if sign_p(rc, rb) <= 0.05 else "level")
            riv[f"{arm}_vs_{r}"] = {"diff": res[arm]["useful_all"] - res[r]["useful_all"], f"{arm}_only": rb,
                                    f"{r}_only": rc, "p_two_sided": round(two_sided(rb, rc), 4),
                                    "reading": reading}
    res["vs_rivals"] = riv
    ro = {"C_reply_differs_from_K": sum(last[("C", i)] != last[("K", i)] for i in ids)}
    for g in ("panel_A", "panel_B", "lead", "nolead", "uses_facts"):
        gb, gc = pair("C", "K", groups[g])
        ro[f"C_minus_K_{g}"] = {"diff": cnt("C", groups[g]) - cnt("K", groups[g]), "C_only": gb, "K_only": gc}
    res["report_only"] = ro
    return res


def selftest() -> None:
    ok = 0
    import claude_cre333_agent as C
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        pa, pb = t / "pa.jsonl", t / "pb.jsonl"
        ia = [{"item_id": f"kq-{n:03d}", "kind": "idea" if n % 3 else "uses_facts",
               "turns": ["x"] if n % 2 else [], "last": "r"} for n in range(1, 11)]
        ib = [{"item_id": f"kc-{n:02d}", "kind": "idea", "turns": [], "last": "r"} for n in range(1, 7)]
        for p, its in ((pa, ia), (pb, ib)):
            p.write_text("".join(json.dumps(x) + "\n" for x in its), encoding="utf-8")
        truth = {}
        for sd, its, pre in (("sa", ia, "A"), ("sb", ib, "B")):
            s = t / sd
            s.mkdir()
            rows, key, n = [], {}, 0
            for x in ARMS:
                run = []
                for it in its:
                    num = int(it["item_id"][-2:])
                    rep = f"{x}-{it['item_id']}" if x not in ("C", "K") else f"ck-{it['item_id']}-{'UN'[num % 3 == 0]}"
                    if x == "K" and it["item_id"] == "kq-004":
                        rep = C.FALLBACK                                           # C gains here (ck-kq-004-U)
                    if x == "C" and it["item_id"] == "kc-04":
                        rep = "cx-kc-04-N"                                         # C loses here
                    run.append({"item_id": it["item_id"], "turn_i": 0, "last": True, "reply": rep})
                    cid = f"K{n:04d}"
                    n += 1
                    key[cid] = {"arm": x, "item_id": it["item_id"]}
                    rows.append({"id": cid, "chat": [], "request": "r", "reply": rep})
                (s / f"creative_{x}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in run), encoding="utf-8")
            (s / "creative_judge.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
            (s / "creative_key.json").write_text(json.dumps(key), encoding="utf-8")
            dedupe(str(s), pre)
            u = load(s / "creative_judge_u.jsonl")
            ku = json.loads((s / "creative_key_u.json").read_text(encoding="utf-8"))
            assert len(u) < len(rows) and all(r["id"].startswith(pre) for r in u)       # C/K duplicates merged
            assert sum(len(v) for v in ku.values()) == len(rows)
            for r in u:
                truth[r["id"]] = r["reply"]
        ok += 1

        def verdict(rep):          # C/K useful on "-U" replies, T useful on even ids, nobody else
            return rep.endswith("-U") or (rep.startswith("T-") and int(rep[-2:]) % 2 == 0)
        j1 = [{"id": i, "useful": "yes" if verdict(r) else "no", "made_up_user_facts": int(r.startswith("Q-"))}
              for i, r in truth.items()]
        j2 = [dict(x) for x in j1]
        flip = sorted(truth)[3]
        j2[[x["id"] for x in j2].index(flip)]["useful"] = "no" if j1[3]["useful"] == "yes" else "yes"
        for n, js in enumerate((j1, j2)):
            (t / f"j{n}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in js), encoding="utf-8")
        a = dict(panels=[str(pa), str(pb)], runs=[str(t / "sa"), str(t / "sb")],
                 keys=[str(t / "sa" / "creative_key_u.json"), str(t / "sb" / "creative_key_u.json")])
        assert score(**a, judge_spec=f"{t / 'j0.jsonl'},{t / 'j1.jsonl'}", splits_out=str(t / "sp.json")) is None
        assert json.loads((t / "sp.json").read_text()) == [flip]
        ok += 1
        (t / "j3.jsonl").write_text(json.dumps(j1[3]) + "\n", encoding="utf-8")
        r = score(**a, judge_spec=f"{t / 'j0.jsonl'},{t / 'j1.jsonl'},{t / 'j3.jsonl'}")
        assert r["items"] == 16 and r["n_panel_A"] == 10 and r["n_panel_B"] == 6 and r["third_judged"] == 1
        m = r["marks_k1c"]
        assert (m["K1c.1"]["C_only"], m["K1c.1"]["K_only"], m["K1c.1"]["C_minus_K"]) == (1, 1, 0), m
        assert r["verdict_k1c"] == "FAIL" and m["K1c.2"]["pass"] and r["Q"]["madeup_replies"] == 16
        assert r["K"]["fallbacks"] == 1 and r["C"]["fallbacks"] == 0 and m["K1c.3"]["pass"]
        assert r["report_only"]["C_reply_differs_from_K"] == 2                   # the fallback item and kc-04
        assert r["report_only"]["C_minus_K_panel_A"] == {"diff": 1, "C_only": 1, "K_only": 0}
        assert r["T"]["useful_all"] == sum(int(i["item_id"][-2:]) % 2 == 0 for i in ia + ib)
        ok += 1
        # 4. mark arithmetic on a hand-made useful table
        b, c = 30, 10
        assert sign_p(b, c) < 0.05 and abs(two_sided(b, c) - 2 * sign_p(b, c)) < 1e-12 and two_sided(5, 5) == 1.0
        ok += 1
        # 5. a judge slot with an id twice, or a missing arm, stops scoring
        (t / "jd.jsonl").write_text(json.dumps(j1[0]) + "\n" + json.dumps(j1[0]) + "\n", encoding="utf-8")
        try:
            _judges(f"{t / 'jd.jsonl'}")
            raise AssertionError("duplicate id accepted")
        except SystemExit:
            pass
        (t / "sa" / "creative_Q.jsonl").unlink()
        try:
            score(**a, judge_spec=f"{t / 'j0.jsonl'},{t / 'j1.jsonl'},{t / 'j3.jsonl'}")
            raise AssertionError("missing run file accepted")
        except SystemExit:
            pass
        ok += 1
    print(f"k1c score selftest {ok}/5 ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dedupe", default="")
    ap.add_argument("--prefix", default="")
    ap.add_argument("--panels", default="")
    ap.add_argument("--runs", default="")
    ap.add_argument("--keys", default="")
    ap.add_argument("--judges", default="")
    ap.add_argument("--splits-out", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if a.dedupe:
        if a.prefix not in ("A", "B"):
            raise SystemExit("k1c score: --prefix A (k1cpanel) or B (k1apanel)")
        dedupe(a.dedupe, a.prefix)
        return
    res = score(a.panels.split(","), a.runs.split(","), a.keys.split(","), a.judges, a.splits_out)
    if res is None:
        return
    print(json.dumps(res, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
