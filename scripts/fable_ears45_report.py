#!/usr/bin/env python3
"""Rung 1 of design 43 -- turn the sealed score JSONs into RESULTS.md.

Written AFTER the seal; it reads `score-<arm>.json`, `wave-<arm>.json` and the run metas
and formats them.  It computes nothing that could change a mark.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ARMS = [("tape", "A — tape ears (skills + router)"),
        ("bigru", "B — same-size BiGRU tagger"),
        ("names", "C — tape ears, names visible (8,192 hashed rows)")]
SEEDS = (4301, 4302, 4303)
MARK_ORDER = ["R1-SAFE", "R1-ECHO", "R1-SEEN", "R1-NEW", "R1-NAMES", "R1-ASK"]


def item_line(it):
    if it is None:
        return "(no item)"
    bits = [it["act"]]
    for k in ("subject", "relation_path", "relation_surface", "value", "value_kind",
              "alias", "canonical"):
        v = it.get(k)
        if v not in (None, [], "none"):
            bits.append(f"{k}={v!r}")
    return " ".join(bits)


def marks_table(rep):
    m = rep["marks"]
    rows = []
    for k in MARK_ORDER:
        d = m[k]
        nums = ", ".join(f"{kk} = {vv}" for kk, vv in d.items() if kk != "pass")
        rows.append(f"| {k} | {nums} | {'PASS' if d['pass'] else '**FAIL**'} |")
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--art", required=True)
    a = ap.parse_args()
    art = Path(a.art)
    out = []
    reps = {}
    for arm, _ in ARMS:
        p = art / f"score-{arm}.json"
        if p.exists():
            reps[arm] = json.loads(p.read_text())
    out.append("# RESULTS — Rung 1 of design 43 (`43-talker-ears-mouth-design-fable.md`)\n")
    out.append("Marks, interpretations and deviations were fixed in `PASSMARKS.md` and "
               "hashed in `SEAL.sha256.txt` before any registered run. Seeds 4301, 4302, "
               "4303 per arm; 8,000 updates per run (see deviation 3).\n")

    out.append("\n## 1. Marks (gated pipeline = all five brakes, three seeds of the arm)\n")
    for arm, title in ARMS:
        if arm not in reps:
            continue
        r = reps[arm]
        gate = " (GATED)" if arm == "tape" else " (recorded only)"
        out.append(f"\n### Arm {title}{gate}\n")
        out.append(f"parameters per ear: **{r['params']:,}** · "
                   f"tau0 = {r['tau0']:.6f} · tau_exec = {r['tau_exec']:.6f} · "
                   f"tau_echo = {r['tau_echo']}\n")
        out.append("\n| mark | numbers | verdict |\n|---|---|---|")
        out.append(marks_table(r))
        ok = all(r["marks"][k]["pass"] for k in MARK_ORDER)
        out.append(f"\n**Arm {arm}: {'ALL MARKS MET' if ok else 'FAIL'}**\n")

    out.append("\n## 2. Single ears, before the agreement brake\n")
    out.append("Each ear scored alone with brakes 1, 2, 4, 5 and its own tau fitted on CAL. "
               "No mark is gated on these; they are here so the cost and benefit of brake 3 "
               "is visible.\n")
    out.append("\n| arm | seed | tau_exec | silent wrong writes /6,500 | echoed wrong "
               "writes | T-seen correct /2,000 | T-new correct /3,000 | T-hard correct /500 "
               "| T-trap written |\n|---|---|---|---|---|---|---|---|---|")
    for arm, _ in ARMS:
        if arm not in reps:
            continue
        r = reps[arm]
        for i, s in enumerate(SEEDS):
            d = r["recorded"]["single_ear_totals"][i]
            out.append(f"| {arm} | {s} | {r['tau_exec_single'][i]:.4f} | "
                       f"{d['silent_wrong_writes_6500']} | {d['echoed_wrong_writes']} | "
                       f"{d['t_seen_correct']} | {d['t_new_correct']} | "
                       f"{d['t_hard_correct']} | {d['t_trap_written']} |")

    out.append("\n## 3. Panel detail, ensemble (after the agreement brake)\n")
    out.append("\n| arm | panel | n | correct | EXECUTE-correct | ECHO-correct | EXECUTE | "
               "ECHO | REPHRASE | silent wrong writes | echoed wrong writes |"
               "\n|---|---|---|---|---|---|---|---|---|---|---|")
    for arm, _ in ARMS:
        if arm not in reps:
            continue
        for name, d in reps[arm]["panels"].items():
            e = d["ensemble"]
            v = e["verdicts"]
            out.append(f"| {arm} | {name} | {e['n']} | {e['correct']} | "
                       f"{e['exec_correct']} | {e['echo_correct']} | "
                       f"{v.get('EXECUTE',0)} | {v.get('ECHO',0)} | "
                       f"{v.get('REPHRASE',0)} | {e['silent_wrong_write']} | "
                       f"{e['echoed_wrong_write']} |")

    out.append("\n## 4. Every silent wrong write, verbatim\n")
    any_silent = False
    for arm, _ in ARMS:
        if arm not in reps:
            continue
        for name, d in reps[arm]["panels"].items():
            for ex in d["ensemble"]["silent_examples"]:
                any_silent = True
                out.append(f"\n- **{arm} / {name} / {ex['family']} #{ex['n']}** "
                           f"`{ex['utterance']}`\n  - gold: {item_line(ex['gold'])}"
                           f"\n  - wrote: {item_line(ex['got'])}")
    if not any_silent:
        out.append("\nNone, in any arm, on any test panel.\n")

    out.append("\n## 5. Echoed wrong writes (up to 30 per arm and panel)\n")
    any_echo = False
    for arm, _ in ARMS:
        if arm not in reps:
            continue
        for name, d in reps[arm]["panels"].items():
            for ex in d["ensemble"]["echo_examples"]:
                any_echo = True
                out.append(f"\n- **{arm} / {name} / {ex['family']} #{ex['n']}** "
                           f"`{ex['utterance']}`\n  - gold: {item_line(ex['gold'])}"
                           f"\n  - echoed: {item_line(ex['got'])}")
    if not any_echo:
        out.append("\nNone.\n")

    out.append("\n## 6. Per-family misses (ensemble)\n")
    for arm, _ in ARMS:
        if arm not in reps:
            continue
        out.append(f"\n**{arm}**\n")
        out.append("\n| panel | family: misses |\n|---|---|")
        for name, d in reps[arm]["panels"].items():
            fm = d["ensemble"]["fam_miss"]
            s = ", ".join(f"{k} {v}" for k, v in list(fm.items())[:12]) or "none"
            out.append(f"| {name} | {s} |")

    out.append("\n## 7. Recorded only\n")
    for arm, _ in ARMS:
        if arm not in reps:
            continue
        r = reps[arm]
        far = r["recorded"]["t_far"]
        out.append(f"\n- **{arm}** T-far (far constructions, 1,000): correct "
                   f"{far['correct']}, EXECUTE-correct {far['exec_correct']}, silent wrong "
                   f"writes {far['silent_wrong_write']}, echoed wrong writes "
                   f"{far['echoed_wrong_write']}.")
        if r.get("router_gates"):
            g = [f"stage {i}: " + " ".join(f"{x:.2f}" for x in row)
                 for i, row in enumerate(r["router_gates"])]
            out.append(f"- **{arm}** router gates sigmoid(10 tanh G):\n    - "
                       + "\n    - ".join(g))
    out.append("\n- 4-hop questions: **not measured** — the rung-1 generator makes at most "
               "3 hops (deviation 7).\n")

    out.append("\n## 8. Wall-clock and seconds per update\n")
    out.append("\n| arm | seed | params | sec/update | train min | dev act acc |"
               "\n|---|---|---|---|---|---|")
    for arm, _ in ARMS:
        for s in SEEDS:
            mp = art / "runs" / f"{arm}-{s}" / "meta.json"
            if not mp.exists():
                continue
            m = json.loads(mp.read_text())
            out.append(f"| {arm} | {s} | {m['params']:,} | {m['sec_per_update']:.3f} | "
                       f"{m['train_sec']/60:.1f} | {m['dev_act_acc']:.3f} |")
    for arm, _ in ARMS:
        wp = art / f"wave-{arm}.json"
        if wp.exists():
            w = json.loads(wp.read_text())
            out.append(f"\n- wave **{arm}**: train {w['train_wall_sec']/60:.1f} min, "
                       f"wave incl. scoring {w['wave_wall_sec']/60:.1f} min "
                       f"({w['updates']} updates × 3 seeds in parallel).")
    (art / "RESULTS.md").write_text("\n".join(out) + "\n")
    print(f"wrote {art / 'RESULTS.md'}")


if __name__ == "__main__":
    main()
