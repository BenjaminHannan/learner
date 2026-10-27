#!/usr/bin/env python3
"""k1f scorer (Creative answers in chat thread, 2026-09-26). Counts only: never prints panel or reply text.

One panel, k1fpanel (artifacts/claude-k1fpanel-20260926/creative, 100 fresh blind items), run by
claude_panel382_run.py and scored by its --score step. Arms: F (k1f: the k1a writer on LFM2.5-1.2B-Instruct),
K (k1a, the writer on MiniCPM5-1B), T (plain MiniCPM5-1B), Q (plain Qwen3.5-2B), L (plain LFM2.5-1.2B); T, Q and L
on the plain twin recipe (claude_e2e336_twinb.py).

Step 1, one verdict per distinct reply (arms that wrote the same reply to the same item share it):
  python -B scripts/claude_k1f_score.py --dedupe SCORE
      = claude_k1c_score.dedupe(SCORE, "F"): SCORE/creative_judge_u.jsonl (ids F0000.., seed 3824) and
      SCORE/creative_key_u.json; counts only.
Step 2, after judges 1 and 2 judged the packet (and judge 3 the lines they split on):
  python -B scripts/claude_k1f_score.py --panel P/items.jsonl --runs OUT --key SCORE/creative_key_u.json \
      --judges J1,J2[,J3] [--splits-out SPLITS.json] [--out RESULTS.json]
  (a judge slot may join several files with "+"). Without judge 3 it writes the ids that need a third judge to
  --splits-out and stops. Judge 3 decides a field only where judges 1 and 2 split on it (as in k1a and k1c).
Marks: artifacts/claude-k1f-20260926/PASSMARKS-k1f.md (fixed before any registered run). K1f.1-3 compare F with K.
The rival readings for F and for K are claude_k1rival_score.score, the scorer sealed for 0.2d's K1 row, unchanged.
  python -B scripts/claude_k1f_score.py --selftest     (CPU, synthetic data)

Report-only, the drafts (added 17:45 UTC before the seal, at the Thread manager's question "how often is a useful
draft among the 4?"). The K and F arms run with K1F_DRAFTS=OUT/drafts_K.jsonl and OUT/drafts_F.jsonl (a pass-through
log; claude_k1f_cre.DraftLog). Then:
  python -B scripts/claude_k1f_score.py --draft-packet OUT --panel P/items.jsonl
      one line per distinct (item, guard-passing draft of the last request) over K and F, shuffled with seed 3825,
      ids H0000..: OUT/drafts_judge.jsonl and OUT/drafts_key.json; counts only.
  python -B scripts/claude_k1f_score.py --draft-score OUT --panel P/items.jsonl --judges J1,J2[,J3] [--splits-out F]
      per arm: items with a creative last request, items with no passing draft, first passing draft useful (k1a's
      reply) and at least one passing draft useful, all in this one judging; and how often the arm's run reply is
      its first passing draft (it must be every time). Same judge words (JUDGE-k1f.md), a separate packet.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_k1c_score as KC  # noqa: E402
import claude_k1rival_score as KR  # noqa: E402

ARMS = ("F", "K", "T", "Q", "L")
RIVALS = KR.RIVALS
BAR_GAIN, BAR_P, BAR_MADEUP, BAR_FALLBACK, K1_SHARE = 8, 0.05, 4, 2, 0.6
load, yes, sign_p, two_sided, madeup = KC.load, KC.yes, KC.sign_p, KC.two_sided, KC.madeup


def score(panel: str, runs: str, keyp: str, judge_spec: str, splits_out: str = "") -> dict | None:
    items = {it["item_id"]: it for it in load(panel)}
    key = {cid: (v if isinstance(v, list) else [v])
           for cid, v in json.loads(Path(keyp).read_text(encoding="utf-8")).items()}
    js = KC._judges(judge_spec)
    j1, j2 = js[0], js[1]
    miss = [cid for cid in key if cid not in j1 or cid not in j2]
    if miss:
        raise SystemExit(f"k1f score: {len(miss)} ids missing from judge 1 or 2")
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
        raise SystemExit("k1f score: split ids missing from judge 3")
    useful, made = {}, {}
    for cid, who in key.items():
        u1, u2 = yes(j1[cid]["useful"]), yes(j2[cid]["useful"])
        m1, m2 = madeup(j1[cid]), madeup(j2[cid])
        u = u1 if u1 == u2 else yes(j3[cid]["useful"])
        m = m1 if m1 == m2 else madeup(j3[cid])
        for k in who:
            useful[(k["arm"], k["item_id"])] = u
            made[(k["arm"], k["item_id"])] = m
    ids = sorted(items)
    for x in ARMS:
        if any((x, i) not in useful for i in ids):
            raise SystemExit(f"k1f score: arm {x} missing or lacks some items")
    import claude_cre333_agent as C
    last = {}
    for x in ARMS:
        p = Path(runs) / f"creative_{x}.jsonl"
        if not p.exists():
            raise SystemExit(f"k1f score: {p} missing")
        for r in load(p):
            if r.get("last"):
                last[(x, r["item_id"])] = r.get("reply") or ""
    if any((x, i) not in last for x in ARMS for i in ids):
        raise SystemExit("k1f score: a run file lacks some items")
    groups = {"all": ids, "lead": [i for i in ids if items[i]["turns"]],
              "nolead": [i for i in ids if not items[i]["turns"]],
              "idea": [i for i in ids if items[i]["kind"] == "idea"],
              "uses_facts": [i for i in ids if items[i]["kind"] == "uses_facts"]}

    def cnt(arm, grp):
        return sum(useful[(arm, i)] for i in grp)

    def pair(a1, a2, grp):
        return (sum(useful[(a1, i)] and not useful[(a2, i)] for i in grp),
                sum(useful[(a2, i)] and not useful[(a1, i)] for i in grp))
    res = {"lines": len(key), "items": len(ids), **{f"n_{g}": len(v) for g, v in groups.items() if g != "all"},
           "judge12_useful_agree": len(key) - len(split_u), "judge12_madeup_agree": len(key) - len(split_m),
           "third_judged": len(splits)}
    for x in ARMS:
        res[x] = {**{f"useful_{g}": cnt(x, v) for g, v in groups.items()},
                  "madeup_replies": sum(made[(x, i)] for i in ids),
                  "fallbacks": sum(last[(x, i)] == C.FALLBACK for i in ids),
                  "empty_replies": sum(not last[(x, i)].strip() for i in ids),
                  "bare_list_endings": sum(bool(KC.KS.BARE_END.search(last[(x, i)])) for i in ids),
                  "median_words": statistics.median(len(last[(x, i)].split()) for i in ids)}
    b, c = pair("F", "K", ids)
    d = res["F"]["useful_all"] - res["K"]["useful_all"]
    p = sign_p(b, c)
    marks = {
        "K1f.1": {"F_minus_K": d, "F_only": b, "K_only": c, "sign_p": round(p, 4),
                  "pass": d >= BAR_GAIN and p <= BAR_P},
        "K1f.2": {"F_madeup": res["F"]["madeup_replies"], "K_madeup": res["K"]["madeup_replies"],
                  "pass": res["F"]["madeup_replies"] <= res["K"]["madeup_replies"] + BAR_MADEUP},
        "K1f.3": {"F_fallbacks": res["F"]["fallbacks"], "K_fallbacks": res["K"]["fallbacks"],
                  "pass": res["F"]["fallbacks"] <= res["K"]["fallbacks"] + BAR_FALLBACK},
    }
    res["marks_k1f"] = marks
    res["verdict_k1f"] = "PASS" if all(m["pass"] for m in marks.values()) else "FAIL"
    need = math.ceil(K1_SHARE * len(ids))
    k1 = {"F_useful_all": res["F"]["useful_all"], "need": need,
          **{f"{r}_useful_all": res[r]["useful_all"] for r in RIVALS}}
    k1["pass"] = res["F"]["useful_all"] >= need and all(res["F"]["useful_all"] >= res[r]["useful_all"] for r in RIVALS)
    res["K1_line"] = k1
    for arm in ("F", "K"):                     # 0.2d's K1 row, scored by its own sealed code, as a dry run
        rr = KR.score(panel, runs, keyp, judge_spec, arm)
        if rr[arm]["useful_all"] != res[arm]["useful_all"] or rr[arm]["madeup_replies"] != res[arm]["madeup_replies"]:
            raise SystemExit("k1f score: the 0.2d scorer disagrees with this one")
        res[f"no_harm_{arm}"] = {"marks": rr["marks_no_harm"], "verdict": rr["verdict_no_harm"]}
    ro = {}
    for g in ("lead", "nolead", "uses_facts"):
        gb, gc = pair("F", "K", groups[g])
        ro[f"F_minus_K_{g}"] = {"diff": cnt("F", groups[g]) - cnt("K", groups[g]), "F_only": gb, "K_only": gc}
    fb, lb = pair("F", "L", ids)
    ro["F_vs_L"] = {"diff": res["F"]["useful_all"] - res["L"]["useful_all"], "F_only": fb, "L_only": lb,
                    "p_two_sided": round(two_sided(fb, lb), 4), "reading": KR.reading(fb, lb)}
    res["report_only"] = ro
    return res


def _last_records(panel: str, logp: Path) -> dict:
    """{item_id: the draft-log record of the item's last request}; a state folder whose last creative request is not
    an item's last message (the last message went down the chat path) has none."""
    items = load(panel)
    by_last = {}
    for it in items:
        if it["last"] in by_last:
            raise SystemExit("k1f drafts: two items share a last message")
        by_last[it["last"]] = it["item_id"]
    per_dir: dict = {}
    for r in (load(logp) if logp.exists() else []):
        per_dir.setdefault(r["dir"], []).append(r)
    out = {}
    for recs in per_dir.values():
        iid = by_last.get(recs[-1]["request"])
        if iid is None:
            continue
        if iid in out:
            raise SystemExit(f"k1f drafts: item {iid} logged twice")
        out[iid] = recs[-1]
    return out


def draft_packet(out: str, panel: str) -> None:
    items = {it["item_id"]: it for it in load(panel)}
    groups: dict = {}
    counts = {}
    for arm in ("K", "F"):
        recs = _last_records(panel, Path(out) / f"drafts_{arm}.jsonl")
        n_pass = 0
        for iid, r in sorted(recs.items()):
            for k, d in enumerate(r["drafts"]):
                if d["guard"] is None:
                    n_pass += 1
                    groups.setdefault((iid, d["trimmed"]), []).append({"arm": arm, "item_id": iid, "draw": k})
        counts[arm] = {"items_logged": len(recs), "passing_drafts": n_pass}
    pool = sorted(groups)
    random.Random(3825).shuffle(pool)
    key = {}
    with open(Path(out) / "drafts_judge.jsonl", "w", encoding="utf-8") as fh:
        for n, (iid, t) in enumerate(pool):
            cid = f"H{n:04d}"
            key[cid] = groups[(iid, t)]
            lead = [x if isinstance(x, str) else x.get("text", "") for x in items[iid]["turns"]]
            fh.write(json.dumps({"id": cid, "chat": lead, "request": items[iid]["last"], "reply": t},
                                ensure_ascii=False) + "\n")
    (Path(out) / "drafts_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    print(json.dumps({"lines": len(pool), **counts}))


def draft_score(out: str, panel: str, judge_spec: str, splits_out: str = "") -> dict | None:
    key = json.loads((Path(out) / "drafts_key.json").read_text(encoding="utf-8"))
    js = KC._judges(judge_spec)
    j1, j2 = js[0], js[1]
    if any(c not in j1 or c not in j2 for c in key):
        raise SystemExit("k1f drafts: ids missing from judge 1 or 2")
    split = sorted(c for c in key if yes(j1[c]["useful"]) != yes(j2[c]["useful"]))
    if len(js) < 3:
        if splits_out:
            Path(splits_out).write_text(json.dumps(split), encoding="utf-8")
        print(json.dumps({"lines": len(key), "useful_splits": len(split)}))
        return None
    j3 = js[2]
    if any(c not in j3 for c in split):
        raise SystemExit("k1f drafts: split ids missing from judge 3")
    verdict = {}
    for c, who in key.items():
        v = yes(j1[c]["useful"]) if c not in split else yes(j3[c]["useful"])
        for w in who:
            verdict[(w["arm"], w["item_id"], w["draw"])] = v
    res = {"lines": len(key), "judge12_useful_agree": len(key) - len(split), "third_judged": len(split)}
    for arm in ("K", "F"):
        recs = _last_records(panel, Path(out) / f"drafts_{arm}.jsonl")
        run = {r["item_id"]: r.get("reply") or "" for r in load(Path(out) / f"creative_{arm}.jsonl") if r.get("last")}
        first = anyu = nopass = same = 0
        for iid, r in recs.items():
            ok = [k for k, d in enumerate(r["drafts"]) if d["guard"] is None]
            if not ok:
                nopass += 1
                continue
            same += r["drafts"][ok[0]]["trimmed"] == run.get(iid)
            first += verdict[(arm, iid, ok[0])]
            anyu += any(verdict[(arm, iid, k)] for k in ok)
        res[arm] = {"items_logged": len(recs), "no_passing_draft": nopass, "first_passing_useful": first,
                    "any_passing_useful": anyu, "reply_is_first_passing": same}
    return res


def selftest() -> None:
    ok = 0
    import claude_cre333_agent as C
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        its = [{"item_id": f"kf-{n:03d}", "kind": "idea" if n % 3 else "uses_facts", "turns": ["x"] if n % 2 else [],
                "last": "r"} for n in range(1, 41)]
        (t / "p.jsonl").write_text("".join(json.dumps(x) + "\n" for x in its), encoding="utf-8")
        s = t / "s"
        s.mkdir()
        rows, key, n = [], {}, 0
        for x in ARMS:
            run = []
            for it in its:
                k = int(it["item_id"][-3:])
                rep = f"same-{k}" if x in ("K", "T") and k <= 10 else f"{x}-{k}"
                if x == "F" and k in (39, 40):
                    rep = C.FALLBACK
                run.append({"item_id": it["item_id"], "turn_i": 0, "last": True, "reply": rep})
                key[f"K{n:04d}"] = {"arm": x, "item_id": it["item_id"]}
                rows.append({"id": f"K{n:04d}", "chat": [], "request": "r", "reply": rep})
                n += 1
            (s / f"creative_{x}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in run), encoding="utf-8")
        (s / "creative_judge.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        (s / "creative_key.json").write_text(json.dumps(key), encoding="utf-8")
        KC.dedupe(str(s), "F")
        u = load(s / "creative_judge_u.jsonl")
        assert len(u) == 200 - 10 and all(r["id"].startswith("F") for r in u)     # K and T share 10 replies
        ok += 1

        def verdict(rep):   # F useful on 1-30; K and T on 1-10 (shared) + 11-12; Q on all; L on 1-25
            if rep == C.FALLBACK:
                return False
            a, k = rep.split("-")
            k = int(k)
            return {"same": True, "F": k <= 30, "K": k <= 12, "T": k <= 12, "Q": True, "L": k <= 25}[a]
        j = [{"id": r["id"], "useful": "yes" if verdict(r["reply"]) else "no",
              "made_up_user_facts": int(r["reply"].startswith("F-") and r["reply"].endswith("-7"))} for r in u]
        j2 = [dict(x) for x in j]
        j2[0]["useful"] = "no" if j[0]["useful"] == "yes" else "yes"
        for nm, rows_ in (("j1", j), ("j2", j2), ("j3", [j[0]])):
            (t / f"{nm}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows_), encoding="utf-8")
        a = dict(panel=str(t / "p.jsonl"), runs=str(s), keyp=str(s / "creative_key_u.json"))
        assert score(**a, judge_spec=f"{t / 'j1.jsonl'},{t / 'j2.jsonl'}", splits_out=str(t / "sp.json")) is None
        assert json.loads((t / "sp.json").read_text()) == [j[0]["id"]]
        ok += 1
        r = score(**a, judge_spec=f"{t / 'j1.jsonl'},{t / 'j2.jsonl'},{t / 'j3.jsonl'}")
        m = r["marks_k1f"]
        assert (r["F"]["useful_all"], r["K"]["useful_all"], r["L"]["useful_all"], r["Q"]["useful_all"]) == (30, 12, 25, 40)
        assert (m["K1f.1"]["F_only"], m["K1f.1"]["K_only"], m["K1f.1"]["F_minus_K"]) == (18, 0, 18) and m["K1f.1"]["pass"]
        assert m["K1f.2"]["F_madeup"] == 1 and m["K1f.2"]["pass"]
        assert m["K1f.3"] == {"F_fallbacks": 2, "K_fallbacks": 0, "pass": True} and r["verdict_k1f"] == "PASS"
        assert r["K1_line"]["need"] == 24 and not r["K1_line"]["pass"]            # Q 40 > F 30
        assert r["no_harm_F"]["marks"]["K1.Q"]["reading"] == "behind" and r["no_harm_F"]["verdict"] == "FAIL"
        assert r["no_harm_F"]["marks"]["K1.T"]["reading"] == "ahead"
        assert r["report_only"]["F_vs_L"]["F_only"] == 5 and r["report_only"]["F_vs_L"]["reading"] == "ahead"
        assert r["third_judged"] == 1
        ok += 1
        # 4. one more fallback fails K1f.3 (bar: F <= K + 2)
        runf = load(s / "creative_F.jsonl")
        runf[36]["reply"] = C.FALLBACK                                            # kf-037, useful before
        (s / "creative_F.jsonl").write_text("".join(json.dumps(x) + "\n" for x in runf), encoding="utf-8")
        r2 = score(**a, judge_spec=f"{t / 'j1.jsonl'},{t / 'j2.jsonl'},{t / 'j3.jsonl'}")
        assert r2["marks_k1f"]["K1f.3"]["F_fallbacks"] == 3 and r2["verdict_k1f"] == "FAIL"
        ok += 1
        # 5. a missing arm stops scoring
        (s / "creative_L.jsonl").unlink()
        try:
            score(**a, judge_spec=f"{t / 'j1.jsonl'},{t / 'j2.jsonl'},{t / 'j3.jsonl'}")
            raise AssertionError("missing run file accepted")
        except SystemExit:
            pass
        ok += 1
        # 6. drafts: map log records to items by the last request, packet, score
        its = load(t / "p.jsonl")
        for x in its:
            x["last"] = f"request {x['item_id']}"
        (t / "p.jsonl").write_text("".join(json.dumps(x) + "\n" for x in its), encoding="utf-8")
        for arm in ("K", "F"):
            recs, run = [], []
            for n, it in enumerate(its[:5]):
                d = f"p382-{arm}-{n}"
                if n == 1:
                    recs.append({"dir": d, "request": "a creative lead-in", "hist_msgs": 0, "drafts": []})
                if n == 4:                                     # last request went down the chat path: no record
                    continue
                dr = [{"trimmed": f"{arm}{n}-a", "guard": "G5"}, {"trimmed": f"{arm}{n}-b", "guard": None},
                      {"trimmed": f"shared{n}", "guard": None}, {"trimmed": f"{arm}{n}-d", "guard": None}]
                if n == 3:
                    dr = [dict(x, guard="G4") for x in dr]
                recs.append({"dir": d, "request": it["last"], "hist_msgs": 0, "drafts": dr})
                run.append({"item_id": it["item_id"], "last": True, "reply": f"{arm}{n}-b" if n != 3 else C.FALLBACK})
            (s / f"drafts_{arm}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in recs), encoding="utf-8")
            (s / f"creative_{arm}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in run), encoding="utf-8")
        draft_packet(str(s), str(t / "p.jsonl"))
        dk = json.loads((s / "drafts_key.json").read_text())
        assert len(dk) == 15                               # items 0-2: K b,d + F b,d + one shared draft each
        pk = load(s / "drafts_judge.jsonl")
        jd = [{"id": r["id"], "useful": "yes" if r["reply"].endswith("-d") or r["reply"] == "F0-b" else "no"} for r in pk]
        (t / "d1.jsonl").write_text("".join(json.dumps(x) + "\n" for x in jd), encoding="utf-8")
        dr = draft_score(str(s), str(t / "p.jsonl"), f"{t / 'd1.jsonl'},{t / 'd1.jsonl'},{t / 'd1.jsonl'}")
        assert dr["K"] == {"items_logged": 4, "no_passing_draft": 1, "first_passing_useful": 0,
                           "any_passing_useful": 3, "reply_is_first_passing": 3}, dr["K"]
        assert dr["F"]["first_passing_useful"] == 1 and dr["F"]["any_passing_useful"] == 3
        ok += 1
    print(f"k1f score selftest {ok}/6 ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dedupe", default="")
    ap.add_argument("--draft-packet", default="")
    ap.add_argument("--draft-score", default="")
    ap.add_argument("--panel", default="")
    ap.add_argument("--runs", default="")
    ap.add_argument("--key", default="")
    ap.add_argument("--judges", default="")
    ap.add_argument("--splits-out", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if a.dedupe:
        KC.dedupe(a.dedupe, "F")
        return
    if a.draft_packet:
        draft_packet(a.draft_packet, a.panel)
        return
    if a.draft_score:
        res = draft_score(a.draft_score, a.panel, a.judges, a.splits_out)
        if res is not None:
            print(json.dumps(res, indent=1))
            if a.out:
                Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
        return
    res = score(a.panel, a.runs, a.key, a.judges, a.splits_out)
    if res is None:
        return
    print(json.dumps(res, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
