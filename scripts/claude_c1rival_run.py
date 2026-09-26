#!/usr/bin/env python3
"""0.2d row C1, everyday chat against same-size rivals: scoring and marks (everyday-chat thread, 2026-09-26, at
Month-end's request after Ben's Redirect). New file only; never prints panel or reply text.

Panel: chatpanel404 (artifacts/claude-panel404-20260926, sealed 81bd131db, 60 blind conversations; spare chatpanel403).
Arms, each run once by ch-403's runner (claude_ch403_run.py run: fresh agent per conversation, the same per-turn seeds):
  the joined build   --arm <Month-end's module:function> --name <BUILD>
  T  MiniCPM5-1B     python -B scripts/claude_twinb_wrap.py scripts/claude_ch403_run.py run --panel-dir PD --arm twin \
  Q  Qwen3.5-2B          --name T|Q|L --gen-model <that rival's pinned snapshot> --out OUT
  L  LFM2.5-1.2B     (the plain twin recipe for every rival: its system line, the whole chat, thinking off, greedy,
                     at most 160 new tokens; claude_e2e336_twinb.py)
score   per-arm counts (claude_ch403_run.arm_counts) and one blind pair set per rival, all 60 conversations, the order
        shuffled per conversation with a fixed seed (t 4061, q 4062, l 4063); packets of 15 in OUT/judge/pair_<x>N.jsonl,
        keys in OUT/key_<x>.json (never opened by judges or by anyone reading results before marks).
          python -B scripts/claude_c1rival_run.py score --panel-dir PD --out OUT --build BUILD
judges  one blind Opus judge per packet, artifacts/claude-ch403-20260926/JUDGE-BRIEF.md, writing pair_<x>N.out.jsonl.
marks   applies the keys; per rival: build wins, rival wins, ties, missing, margin = build wins - rival wins, and the
        judged made-up-about-the-user counts. The bar is Month-end's (0.2d marks file, fixed before the run) and is
        passed as --bar: each rival's mark passes when margin >= BAR; the row passes when all three pass.
          python -B scripts/claude_c1rival_run.py marks --out OUT --judged JDIR --bar N
        Also printed for each rival, for reading the margin (two-sided, 60 decisive pairs, equal systems):
        "behind" if margin <= -14 (chance 4.6%), "ahead" if margin >= +14 (chance 4.6%), else "level".
selftest  CPU only.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_ch403_run as R  # noqa: E402

RIVALS = {"T": "MiniCPM5-1B", "Q": "Qwen3.5-2B", "L": "LFM2.5-1.2B"}
PAIRS = (("t", "T", 4061), ("q", "Q", 4062), ("l", "L", 4063))
SIDE = 14


def reading(margin: int) -> str:
    return "ahead" if margin >= SIDE else "behind" if margin <= -SIDE else "level"


def load_arms(d: Path, build: str, items: dict) -> dict:
    """Every arm must have exactly one row per panel turn; anything else stops scoring."""
    want = {(iid, ti) for iid, it in items.items() for ti in range(len(it["turns"]))}
    arms = {}
    for x in (build, *RIVALS):
        f = d / f"chat_{x}.jsonl"
        if not f.exists():
            raise SystemExit(f"c1rival: missing {f.name}")
        rows = R.load(f)
        got = [(r["item_id"], r["turn_i"]) for r in rows]
        if len(got) != len(set(got)) or set(got) != want:
            raise SystemExit(f"c1rival: {f.name} has {len(got)} rows, {len(set(got))} distinct; want {len(want)}")
        arms[x] = rows
    return arms


def score(a) -> None:
    if a.build in RIVALS:
        raise SystemExit("c1rival: the build's name must differ from T, Q and L")
    items = {it["item_id"]: it for it in R.load_panel(Path(a.panel_dir))}
    d = Path(a.out)
    arms = load_arms(d, a.build, items)
    summ = {"items": len(items), "turns": sum(len(it["turns"]) for it in items.values()), "build": a.build,
            "rivals": RIVALS}
    for x, rows in arms.items():
        summ[x] = R.arm_counts(rows, items)
    jd = d / "judge"
    jd.mkdir(exist_ok=True)
    for tag, rival, seed in PAIRS:
        pk, key, same = R.packets(a.build, rival, arms, items, seed, False)
        for i in range(0, len(pk), R.PACKET):
            (jd / f"pair_{tag}{i // R.PACKET + 1}.jsonl").write_text(
                "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pk[i:i + R.PACKET]), encoding="utf-8")
        (d / f"key_{tag}.json").write_text(json.dumps({"key": key, "identical": same}, indent=1), encoding="utf-8")
        summ[f"pair_{tag}"] = {"arms": [a.build, rival], "judged": len(pk), "files": math.ceil(len(pk) / R.PACKET)}
    (d / "summaryC1.json").write_text(json.dumps(summ, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps(summ, sort_keys=True))


def marks(a) -> None:
    d, jdir = Path(a.out), Path(a.judged)
    s = json.loads((d / "summaryC1.json").read_text(encoding="utf-8"))
    b = s["build"]
    out = {"build": b, "bar": f"margin = build wins - rival wins >= {a.bar} against each rival", "rivals": {}}
    for tag, rival, _ in PAIRS:
        j = R.judged(jdir, tag, json.loads((d / f"key_{tag}.json").read_text(encoding="utf-8")))
        res = j["result"]
        wb, wr = res.get(b, 0), res.get(rival, 0)
        m = wb - wr
        out["rivals"][RIVALS[rival]] = {
            "mark": "PASS" if m >= a.bar and not res.get("missing") else "FAIL",
            "build_wins": wb, "rival_wins": wr, "ties": res.get("tie", 0), "missing": res.get("missing", 0),
            "margin": m, "reading": reading(m),
            "made_up_about_user": {"build": j["madeup"].get(b, 0), "rival": j["madeup"].get(rival, 0)}}
    out["C1"] = "PASS" if all(v["mark"] == "PASS" for v in out["rivals"].values()) else "FAIL"
    out["report"] = {x: {k: s[x][k] for k in ("median_words", "stock_everyday", "ask_unknown_dont_know",
                                              "ask_known_right", "ms_median")} for x in (b, *RIVALS)}
    (d / "marksC1.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


def selftest() -> None:
    ok = 0
    items = {"c1": {"item_id": "c1", "turns": [{"kind": "smalltalk", "text": "hi"}, {"kind": "advice", "text": "x"}]},
             "c2": {"item_id": "c2", "turns": [{"kind": "smalltalk", "text": "yo"}]}}
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        for x in ("D", *RIVALS):
            rows = [{"item_id": iid, "turn_i": ti, "kind": tt["kind"], "reply": f"{x} {iid} {ti}.", "ms": 1.0,
                     "events": 0, "line": "answer"} for iid, it in items.items() for ti, tt in enumerate(it["turns"])]
            (d / f"chat_{x}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        arms = load_arms(d, "D", items)
        assert set(arms) == {"D", "T", "Q", "L"}; ok += 1
        (d / "chat_Q.jsonl").write_text("".join(json.dumps(r) + "\n" for r in arms["Q"][:-1]), encoding="utf-8")
        try:
            load_arms(d, "D", items)
            raise AssertionError("incomplete arm accepted")
        except SystemExit:
            ok += 1
        pk1, key1, _ = R.packets("D", "T", arms, items, 4061, False)
        pk2, key2, _ = R.packets("D", "T", arms, items, 4061, False)
        assert key1 == key2 and len(pk1) == 2 and all(set(v) == {"D", "T"} for v in key1.values()); ok += 1
        jd = d / "j"
        jd.mkdir()
        (jd / "pair_t1.out.jsonl").write_text(json.dumps({"item_id": "c1", "winner": str(key1["c1"].index("D") + 1),
                                                          "madeup_1": 0, "madeup_2": 1}) + "\n", encoding="utf-8")
        j = R.judged(jd, "t", {"key": key1, "identical": []})
        assert j["result"].get("D") == 1 and j["result"].get("missing") == 1; ok += 1
    assert (reading(14), reading(13), reading(-14), reading(0)) == ("ahead", "level", "behind", "level"); ok += 1
    print(f"c1rival selftest: {ok}/5 OK")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["score", "marks", "selftest"])
    ap.add_argument("--panel-dir", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--build", default="")
    ap.add_argument("--judged", default="")
    ap.add_argument("--bar", type=int, default=None)
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest()
    elif a.cmd == "score":
        if not (a.panel_dir and a.out and a.build):
            raise SystemExit("c1rival score: --panel-dir, --out and --build are required")
        score(a)
    else:
        if not (a.out and a.judged) or a.bar is None:
            raise SystemExit("c1rival marks: --out, --judged and --bar are required")
        marks(a)


if __name__ == "__main__":
    main()
