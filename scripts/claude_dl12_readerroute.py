#!/usr/bin/env python3
"""dl-12 (MEASUREMENT ONLY): does the plain base MiniCPM5-1B's own state tell look-alike requests apart with no task
label? (Fix-sleep thread, 2026-09-27; marks: artifacts/claude-dl12-20260927/PASSMARKS.md.) Nothing is trained into
the 1B, no switch is built, nothing joins the build, nothing decides the experts card; report-only input to it.
Bears on Ben's 11:34 09-27 "It should for each request be able to automatically decide what."

Features: the frozen base's last-layer state at the last prompt token (claude_dl9_experts.feats; fixed). Router:
claude_dl11_router.fit_router (3-way class-balanced logistic regression: base / P / Q), labels from where each item
came from; nothing tells it the kind at test. It is fit at 150, 300 and 750 items per kind (dl-11's nights 1, 2, 5,
without any training).
Items, reusing dl-11's sealed recipes (dl-11's GPU run is marked DO NOT RUN, so its TEST seeds cost nothing here):
  P  dl-9's day puzzles in GLM's frame, seeds 18/19 (puzzles(DAY_SEED + 100*seed + d, 150), d = 1..5)
  Q  code-made two-number expressions in Luna's first frame (expressions(Q_DAY_SEED + 100*seed + d, 150))
  base  the base's own quiz questions (dl-9's recipe, pool seed 2992; generation is used ONLY to make these
     base-class items) + Luna's everyday number questions (dl-11's Luna stage), held out by Luna TOPIC group
Tests (never fit): P TEST (seed 2990), Q TEST (seed 2981, dl-11 ADDENDUM-1's launcher), the 300-item panel (119
"bigger" items), held-out Luna topics, held-out base questions, P under GLM's 4 other frames, Q under Luna's other
frames, and the first 100 Q TEST items written in words by code (report-only).

  python -B scripts/claude_dl12_readerroute.py --selftest
  python -B scripts/claude_dl12_readerroute.py --model M --out DIR
  python -B scripts/claude_dl12_readerroute.py --model M --out DIR --dev --luna F     (plumbing rehearsal)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_blurt1 as B1  # noqa: E402
import claude_dl11_run as RUN  # noqa: E402
import claude_dl6c_glmframe as G  # noqa: E402

R = RUN.R                     # claude_dl11_router (sealed)
E = R.E                       # claude_dl9_experts (sealed)
AMOUNTS = (150, 300, 750)
SEEDS = (18, 19)
P_TEST_SEED, Q_TEST_SEED, POOL_SEED, LOOK_SEED = 2990, RUN.NEW_Q_TEST_SEED, 2992, 2993
HELD_TOPIC_SHARE = 0.2
# per bar: (PASS at or above, PROVED-WRONG / FAIL below); between = INCONCLUSIVE for that bar
BARS = {"p_to_P": (0.95, 0.80), "q_to_Q": (0.95, 0.80), "panel_to_base": (0.95, 0.80),
        "bigger_to_base": (0.95, 0.75), "look_held_to_base": (0.95, 0.80)}


def luna_groups(luna: dict) -> list[tuple[str, str]]:
    """(question, Luna topic) in the order the Luna stage kept them, rebuilt from its per-call counts."""
    out, texts = [], list(luna["lookalikes"])
    i = 0
    for c in luna["calls"]:
        if c.get("kind") != "look" or "kept" not in c:
            continue
        for t in texts[i:i + c["kept"]]:
            out.append((t, c["topic"]))
        i += c["kept"]
    if len(out) != len(texts):
        raise SystemExit(f"luna groups rebuild {len(out)} != {len(texts)}")
    return out


def split_by_topic(groups, seed, share=HELD_TOPIC_SHARE):
    topics = sorted({tp for _, tp in groups})
    held = set(random.Random(seed).sample(topics, max(1, round(share * len(topics)))))
    return [t for t, tp in groups if tp not in held], [t for t, tp in groups if tp in held], sorted(held)


def mask(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\d+", "#", t.lower())).strip()


def near_dups(fit, held) -> int:
    fm = {mask(t) for t in fit}
    return sum(mask(t) in fm for t in held)


def grade(rate: float, bar: tuple) -> str:
    return "pass" if rate >= bar[0] else ("inconclusive" if rate >= bar[1] else "below")


def rates(rep: dict) -> dict:
    return {"p_to_P": rep["p_to_P"] / rep["n_p"], "q_to_Q": rep["q_to_Q"] / rep["n_q"],
            "panel_to_base": rep["panel_to_base"] / rep["n_panel"],
            "bigger_to_base": rep["bigger_to_base"] / max(1, rep["n_bigger"]),
            "look_held_to_base": rep["look_held_to_base"] / max(1, rep["n_look_held"])}


def score(res: dict) -> dict:
    """PASSMARKS.md: R1 at 150, R2 at 750, R3 rewordings at 750; per-bar PASS / INCONCLUSIVE / below."""
    m, verdicts = {}, []
    for sd in res["seeds"]:
        s = str(sd)
        for k, tag in ((150, "R1"), (750, "R2")):
            rep = res["runs"][s][str(k)]
            g = {b: grade(v, BARS[b]) for b, v in rates(rep).items()}
            m[f"{tag} seed {s} (k={k})"] = g
            for b, v in g.items():
                verdicts.append("proved_wrong" if v == "below" and k == 750 else ("fail" if v == "below" else v))
        rw = res["runs"][s]["750"]["reworded"]
        g3 = {f"{r['kind']} frame {i}": grade(r["to_right"] / r["n"], (0.95, 0.80)) for i, r in enumerate(rw)}
        m[f"R3 seed {s} (k=750)"] = g3
        verdicts += ["fail" if v == "below" else v for v in g3.values()]
    order = ["proved_wrong", "fail", "inconclusive", "pass"]
    m["verdict"] = next(v for v in order if v in verdicts or v == "pass").upper().replace("_", " ")
    return m


def router_report(rt, f, panel, n_look_held) -> dict:
    pk = {k: [R.choice(p) for p in R.route(rt, v)] for k, v in f.items()}
    bigger = [i for i, it in enumerate(panel) if it["kind"] == "bigger"]
    probs = R.route(rt, f["panel"])
    kinds = sorted({it["kind"] for it in panel})
    return {"train_loss": rt["train_loss"], "n_p": len(pk["p_test"]), "n_q": len(pk["q_test"]),
            "n_panel": len(pk["panel"]), "n_bigger": len(bigger), "n_look_held": n_look_held,
            "p_to_P": sum(c == 1 for c in pk["p_test"]), "q_to_Q": sum(c == 2 for c in pk["q_test"]),
            "panel_to_base": sum(c == 0 for c in pk["panel"]),
            "bigger_to_base": sum(pk["panel"][i] == 0 for i in bigger),
            "look_held_to_base": sum(c == 0 for c in pk["look_held"]),
            "pool_held_to_base": sum(c == 0 for c in pk["pool_held"]), "n_pool_held": len(pk["pool_held"]),
            "words_base_P_Q": [sum(c == j for c in pk["words"]) for j in range(3)],
            "panel_by_kind_base_P_Q": {kd: [sum(pk["panel"][i] == j for i, it in enumerate(panel) if it["kind"] == kd)
                                            for j in range(3)] for kd in kinds},
            "bigger_mean_p_base_P_Q": [round(sum(probs[i][j] for i in bigger) / max(1, len(bigger)), 4)
                                       for j in range(3)]}


def run(a) -> None:
    import claude_blurt2 as B2
    import claude_dl1_nights as D1
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    torch = __import__("torch")
    frame, p_other, suffix = E.glm_texts()
    raw = Path(a.luna).read_bytes()
    luna, luna_sha = json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()
    q_frame, q_other = luna["q_frames"][0], luna["q_frames"][1:]
    B1.puzzle_prompt = G.make_prompt(frame)
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    sh = a.seed_shift
    pdays = {sd: [B2.puzzles(D1.DAY_SEED + sh + 100 * sd + d, a.n_day) for d in range(1, a.nights + 1)] for sd in SEEDS}
    qdays = {sd: [R.expressions(R.Q_DAY_SEED + sh + 100 * sd + d, a.n_day) for d in range(1, a.nights + 1)]
             for sd in SEEDS}
    pkeys = {(tuple(p["nums"]), p["target"]) for sd in SEEDS for day in pdays[sd] for p in day}
    qkeys = {e["expr"] for sd in SEEDS for day in qdays[sd] for e in day}
    p_test = [p for p in B2.puzzles(P_TEST_SEED + sh, a.n_test + 300)
              if (tuple(p["nums"]), p["target"]) not in pkeys][:a.n_test]
    q_test = [e for e in RUN.expressions(Q_TEST_SEED + sh, a.n_qtest + 300) if e["expr"] not in qkeys][:a.n_qtest]
    panel = D1.harm_panel()[:a.n_harm]
    words = [R.words_expr(e) for e in q_test[:a.n_words]]
    look_fit, look_held, held_topics = split_by_topic(luna_groups(luna), LOOK_SEED)
    res = {"config": {k: v for k, v in vars(a).items() if k != "model"}, "luna_file": str(a.luna),
           "luna_sha256": luna_sha, "frame_sha256": G.FRAMES_SHA256, "q_frame": q_frame, "q_other_frames": q_other,
           "p_other_frames": p_other, "n_p_test": len(p_test), "n_q_test": len(q_test), "n_harm": len(panel),
           "look": {"fit": len(look_fit), "held": len(look_held), "held_topics": held_topics,
                    "near_duplicates_held_in_fit": near_dups(look_fit, look_held)}}
    qs = E.question_pool(s, a.n_ask, POOL_SEED + sh)      # generation: only to make base-class items
    rng = random.Random(POOL_SEED)
    rng.shuffle(qs)
    cq = int(0.8 * len(qs))
    pool_fit, pool_held = qs[:cq], qs[cq:]
    tag = lambda xs: [(t + " " + suffix) if rng.random() < 0.5 else t for t in xs]  # noqa: E731
    neg_fit = tag(pool_fit + look_fit)
    res["pool"] = {"asked": a.n_ask, "questions": len(qs), "fit": cq, "held": len(qs) - cq, "sample": qs[:5],
                   "near_duplicates_held_in_fit": near_dups(pool_fit, pool_held)}
    res["n_base_fit"] = len(neg_fit)
    print(f"[dl12] luna sha256 {luna_sha}; {json.dumps(res['look'])}; pool {json.dumps(res['pool'])}", flush=True)
    chat = lambda ts: E.feats(s, [E.chat_text(s, t) for t in ts])  # noqa: E731
    f = {"p_test": E.feats(s, [s.prompt(p) for p in p_test]),
         "q_test": chat([R.q_text(q_frame, e) for e in q_test]),
         "panel": chat([it["q"] for it in panel]), "look_held": chat(tag(look_held)),
         "pool_held": chat(tag(pool_held)), "words": chat([R.q_text(q_frame, e) for e in words])}
    f_rw = [("P", E.with_frame(fr, lambda: E.feats(s, [s.prompt(p) for p in p_test]))) for fr in p_other]
    f_rw += [("Q", chat([R.q_text(fr, e) for e in q_test])) for fr in q_other]
    FN = chat(neg_fit)
    res["runs"] = {}
    for sd in SEEDS:
        FP = torch.cat([E.feats(s, [s.prompt(p) for p in day]) for day in pdays[sd]])
        FQ = torch.cat([chat([R.q_text(q_frame, e) for e in day]) for day in qdays[sd]])
        res["runs"][str(sd)] = {}
        for k in AMOUNTS:
            kk = min(k, len(FP))
            rt = R.fit_router(torch, torch.cat([FN, FP[:kk], FQ[:kk]]),
                              torch.cat([torch.zeros(len(FN)), torch.ones(kk), 2 * torch.ones(kk)]).long(),
                              sd * 1000 + k)
            rep = router_report(rt, f, panel, len(look_held))
            rep["reworded"] = []
            for (kind, fr), (_, fe) in zip([("P", x) for x in p_other] + [("Q", x) for x in q_other], f_rw):
                pk = [R.choice(p) for p in R.route(rt, fe)]
                rep["reworded"].append({"kind": kind, "frame": fr, "n": len(pk),
                                        "to_right": sum(c == (1 if kind == "P" else 2) for c in pk)})
            rep["chance_label_blind"] = {"P": round(kk / (2 * kk + len(FN)), 3), "Q": round(kk / (2 * kk + len(FN)), 3),
                                         "base": round(len(FN) / (2 * kk + len(FN)), 3)}
            res["runs"][str(sd)][str(k)] = rep
            print(f"[dl12] seed {sd} k {k}: " + json.dumps({x: v for x, v in rep.items() if x != "reworded"}),
                  flush=True)
        (out / "dl12_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    res["seeds"] = list(SEEDS)
    res["marks"] = score(res)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "dl12_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res["marks"], indent=1))


def selftest() -> None:
    luna = {"lookalikes": ["a 1?", "b 2?", "c 3?", "d 4?", "e 5?"],
            "calls": [{"kind": "frame", "kept": 5}, {"kind": "look", "topic": "x", "kept": 2},
                      {"kind": "look", "topic": "y", "error": "e"}, {"kind": "look", "topic": "y", "kept": 3}]}
    g = luna_groups(luna)
    assert g == [("a 1?", "x"), ("b 2?", "x"), ("c 3?", "y"), ("d 4?", "y"), ("e 5?", "y")], g
    fit, held, ht = split_by_topic(g, 1, share=0.5)
    assert len(ht) == 1 and not set(fit) & set(held) and len(fit) + len(held) == 5
    assert mask("Is 12 old?") == mask("is 99  old?") and near_dups(["Is 3 ok?"], ["is 7 ok?", "no"]) == 1
    assert grade(0.96, (0.95, 0.8)) == "pass" and grade(0.9, (0.95, 0.8)) == "inconclusive"
    assert grade(0.5, (0.95, 0.8)) == "below"

    def rep(p, q, pan, big, lk, rw=100):
        return {"n_p": 100, "n_q": 200, "n_panel": 300, "n_bigger": 119, "n_look_held": 100, "p_to_P": p,
                "q_to_Q": q, "panel_to_base": pan, "bigger_to_base": big, "look_held_to_base": lk,
                "reworded": [{"kind": "P", "n": 100, "to_right": rw}]}
    good = rep(100, 200, 300, 119, 100)
    res = {"seeds": [18, 19], "runs": {s: {"150": good, "300": good, "750": good} for s in ("18", "19")}}
    assert score(res)["verdict"] == "PASS"
    res["runs"]["18"]["150"] = rep(100, 200, 300, 80, 100)
    assert score(res)["verdict"] == "FAIL", score(res)
    res["runs"]["18"]["150"] = rep(100, 200, 300, 110, 100)
    assert score(res)["verdict"] == "INCONCLUSIVE"
    res["runs"]["19"]["750"] = rep(100, 200, 300, 80, 100)
    assert score(res)["verdict"] == "PROVED WRONG"
    assert RUN.expressions(RUN.NEW_Q_TEST_SEED, 5) == RUN.expressions(RUN.NEW_Q_TEST_SEED, 5)
    print("dl12 selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--luna", default=str(R.LUNA))
    ap.add_argument("--nights", type=int, default=5)
    ap.add_argument("--n-day", type=int, default=150)
    ap.add_argument("--n-test", type=int, default=100)
    ap.add_argument("--n-qtest", type=int, default=200)
    ap.add_argument("--n-harm", type=int, default=300)
    ap.add_argument("--n-words", type=int, default=100)
    ap.add_argument("--n-ask", type=int, default=1000)
    ap.add_argument("--seed-shift", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dev", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.dev:
        a.nights, a.n_day, a.n_test, a.n_qtest, a.n_harm, a.n_words, a.n_ask = 2, 4, 3, 3, 12, 2, 20
        a.seed_shift = a.seed_shift or 60000
    run(a)


if __name__ == "__main__":
    main()
