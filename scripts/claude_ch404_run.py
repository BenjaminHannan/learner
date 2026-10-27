#!/usr/bin/env python3
"""ch-404 registered run: scoring and marks (everyday-chat thread, 2026-09-26). New file only.

Runs use ch-403's runner unchanged (claude_ch403_run.py run: same per-turn seeds, same rows). Arms on chatpanel404:
B = X403 (claude_ch403_agent:build_403), C = the candidate NEXT.md's DEV rule chose (claude_ch404_agent:build_404 or
build_404g), T = the plain twin. Marks: artifacts/claude-ch404-20260926/NEXT.md (N1-N6, C1 apart).

score   per-arm counts (ch-403's arm_counts), memory-turn identity for N6, and blind packets:
          pair_n  C vs B, only conversations that differ (seed 4046)     pair_m  C vs T, all (seed 4047)
          pair_o  B vs T, all (report only, seed 4048); files of 15; keys in OUT/key_{n,m,o}.json.
          python -B scripts/claude_ch404_run.py score --panel-dir PD --out OUT --cand X404
marks   python -B scripts/claude_ch404_run.py marks --out OUT --judged JDIR
selftest  CPU only.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_ch403_run as R  # noqa: E402

B = "X403"
PAIRS = (("n", "C", B, 4046, True), ("m", "C", "T", 4047, False), ("o", B, "T", 4048, False))


def memory_turns(c_rows: list[dict], b_rows: list[dict]) -> dict:
    """N6 inputs: on ask_known/ask_unknown turns, how many replies differ, and median words per arm."""
    key = {(r["item_id"], r["turn_i"]): r for r in b_rows if r["kind"] in R.MEMORY}
    cm = [r for r in c_rows if r["kind"] in R.MEMORY]
    diff = sum(1 for r in cm if key.get((r["item_id"], r["turn_i"]), {}).get("reply") != r["reply"])
    med = (lambda rows: statistics.median([len(r["reply"].split()) for r in rows]) if rows else 0)
    return {"memory_turns": len(cm), "differ": diff, "median_words_C": med(cm), "median_words_B": med(list(key.values()))}


def score(a) -> None:
    items = {it["item_id"]: it for it in R.load_panel(Path(a.panel_dir))}
    d = Path(a.out)
    arms = {"C": R.load(d / f"chat_{a.cand}.jsonl"), B: R.load(d / f"chat_{B}.jsonl"), "T": R.load(d / "chat_T.jsonl")}
    summ = {"items": len(items), "cand": a.cand, "turns": sum(len(it["turns"]) for it in items.values())}
    for x, rows in arms.items():
        summ[x] = R.arm_counts(rows, items)
    summ["N6"] = memory_turns(arms["C"], arms[B])
    jd = d / "judge"
    jd.mkdir(exist_ok=True)
    for tag, first, other, seed, only_diff in PAIRS:
        pk, key, same = R.packets(first, other, arms, items, seed, only_diff)
        for i in range(0, len(pk), R.PACKET):
            (jd / f"pair_{tag}{i // R.PACKET + 1}.jsonl").write_text(
                "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pk[i:i + R.PACKET]), encoding="utf-8")
        (d / f"key_{tag}.json").write_text(json.dumps({"key": key, "identical": same}, indent=1), encoding="utf-8")
        summ[f"pair_{tag}"] = {"arms": [first, other], "judged": len(pk), "identical": len(same),
                               "files": math.ceil(len(pk) / R.PACKET)}
    (d / "summary404.json").write_text(json.dumps(summ, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps(summ, sort_keys=True))


def marks(a) -> None:
    d, jdir = Path(a.out), Path(a.judged)
    s = json.loads((d / "summary404.json").read_text(encoding="utf-8"))
    c, b = s["C"], s[B]
    kn = json.loads((d / "key_n.json").read_text(encoding="utf-8"))
    jn = R.judged(jdir, "n", kn)
    jm = R.judged(jdir, "m", json.loads((d / "key_m.json").read_text(encoding="utf-8")))
    jo = R.judged(jdir, "o", json.loads((d / "key_o.json").read_text(encoding="utf-8")))
    wc, wb = jn["result"].get("C", 0), jn["result"].get(B, 0)
    m = {}
    m["N1"] = ("INCONCLUSIVE" if len(kn["key"]) < 12 else "PASS" if wc - wb >= 6 else "FAIL",
               f"blind pairs on the {len(kn['key'])} differing conversations: C won {wc}, B won {wb}; bar C - B >= +6")
    mc, mb = jn["madeup"].get("C", 0), jn["madeup"].get(B, 0)
    m["N2"] = ("PASS" if mc <= mb else "FAIL", f"judged stated-or-assumed about the user: C {mc} vs B {mb}; bar C <= B")
    m["N3"] = ("PASS" if c["ask_unknown_dont_know"] >= b["ask_unknown_dont_know"] - 1
               and c["ask_known_right"] >= b["ask_known_right"] - 1 else "FAIL",
               f"don't-know C {c['ask_unknown_dont_know']} vs B {b['ask_unknown_dont_know']}; told-and-asked right "
               f"C {c['ask_known_right']} vs B {b['ask_known_right']}; bar each >= B - 1")
    m["N4"] = ("PASS" if c["events_on_non_teach"] <= b["events_on_non_teach"] else "FAIL",
               f"events on non-teach turns C {c['events_on_non_teach']} vs B {b['events_on_non_teach']}")
    m["N5"] = ("PASS" if c["stock_everyday"] <= b["stock_everyday"] else "FAIL",
               f"stock lines on everyday turns C {c['stock_everyday']} vs B {b['stock_everyday']}")
    n6 = s["N6"]
    m["N6"] = ("PASS" if n6["differ"] <= 1 and n6["median_words_C"] <= n6["median_words_B"] else "FAIL",
               f"memory turns: {n6['differ']} of {n6['memory_turns']} differ (bar <= 1); median words C "
               f"{n6['median_words_C']} vs B {n6['median_words_B']} (bar C <= B)")
    verdict = "PASS" if all(v[0] == "PASS" for v in m.values()) else \
        "INCONCLUSIVE" if not any(v[0] == "FAIL" for v in m.values()) else "FAIL"
    wm = jm["result"].get("C", 0)
    out = {"cand": s["cand"], "ch404": verdict, "marks": m,
           "C1": ("PASS" if wm >= 40 else "FAIL", f"C vs T: C won {wm}, T won {jm['result'].get('T', 0)}, ties "
                  f"{jm['result'].get('tie', 0)}, missing {jm['result'].get('missing', 0)}; bar C won >= 40 of 60"),
           "report": {"B_vs_T": jo, "made_up_C_vs_T": jm["madeup"]}}
    (d / "marks404.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


def selftest() -> None:
    br = [{"item_id": "c1", "turn_i": 0, "kind": "ask_known", "reply": "Mira."},
          {"item_id": "c1", "turn_i": 1, "kind": "advice", "reply": "Short."}]
    cr = [dict(br[0]), dict(br[1], reply="A much longer answer.")]
    n6 = memory_turns(cr, br)
    assert n6 == {"memory_turns": 1, "differ": 0, "median_words_C": 1, "median_words_B": 1}, n6
    cr[0] = dict(br[0], reply="Your sister is Mira.")
    assert memory_turns(cr, br)["differ"] == 1
    with tempfile.TemporaryDirectory() as t:
        jd = Path(t)
        key = {"c1": ["C", B]}
        (jd / "pair_n1.out.jsonl").write_text(json.dumps({"item_id": "c1", "winner": "1", "madeup_1": 0,
                                                          "madeup_2": 0}) + "\n", encoding="utf-8")
        assert R.judged(jd, "n", {"key": key, "identical": []})["result"].get("C") == 1
    print("ch-404 run selftest: 3/3 OK")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["score", "marks", "selftest"])
    ap.add_argument("--panel-dir", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--cand", default="X404", choices=["X404", "X404g"])
    ap.add_argument("--judged", default="")
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest()
    else:
        {"score": score, "marks": marks}[a.cmd](a)


if __name__ == "__main__":
    main()
