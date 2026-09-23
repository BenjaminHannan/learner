#!/usr/bin/env python3
"""DEV-ONLY pre-seal scan (Muse, exp 163). NOT a registered run.

Pure read-only scan: builds the BASE loop150 ears on a THROWAWAY notebook,
calls ears.hear() (no writes, no turn()) on every sealed input string, and
flags actions where fable_fix163_lowercase would rewrite a span:
  teach/correct: name all-lowercase, or (relation in PERSON and value
    all-lowercase);
  ask: name all-lowercase.
Superset of real fires (resolve-independent). Writes only to
scripts/scratchpad/dev163/ (never artifacts/, never sealed files).
"""

import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix163_lowercase as F163
import fable_loop150_agent as L150

ROOT = SCRIPTS.parent


def flag_action(a):
    if not isinstance(a, dict):
        return None
    act = a.get("act")
    if act in ("teach", "correct"):
        if str(a.get("relation", "")) not in F163.PERSON_KEYS:
            return None
        if F163.is_all_lowercase_name(a.get("name", "")):
            return f"teach-name:{a.get('name','')!r}"
        if F163.is_all_lowercase_name(a.get("value", "")):
            return f"person-value:{a.get('value','')!r}"
        return None
    if act == "ask":
        if F163.is_all_lowercase_name(a.get("name", "")):
            return f"ask-name:{a.get('name','')!r}"
        return None
    return None


def scan_strings(strings):
    tmp = tempfile.mkdtemp(prefix="scan163_")
    loop = L150.build_agent150({"state_dir": tmp, "sleep_threshold": 10 ** 9})
    out = []
    for s in strings:
        try:
            acts = loop.ears.hear(s)
        except Exception as exc:  # noqa: BLE001
            out.append((s, [f"HEAR-ERROR {exc!r}"]))
            continue
        flags = [f for a in acts if (f := flag_action(a))]
        if flags:
            out.append((s, flags))
    return out


def show(title, flagged):
    print(f"===== {title}: {len(flagged)} flagged =====")
    for s, fs in flagged:
        print(f"  {s[:100]!r} -> {fs}")


def main():
    # 1. bench data: 3 splits (G1) + bench113 splits (G2 bench suite)
    import fable_bench113_run as B113
    import fable_loop129b_bench as B129
    bench_files = {
        "edit200": B129.DATA_EDIT200, "old_s2fresh": B129.DATA_OLD,
        "new_121": B129.DATA_NEW, "b113_A": B113.DATA_A,
        "b113_B": B113.DATA_B,
    }
    bench_items = {}
    for tag, path in bench_files.items():
        items = [json.loads(l) for l in Path(path).read_text(
            encoding="utf-8").splitlines() if l.strip()]
        bench_items[tag] = items
        strs = []
        for it in items:
            for t in it.get("taught", []):
                strs.append(t.get("sentence_en", "") if isinstance(
                    t, dict) else "")
            strs.append(it.get("question", ""))
        show(f"bench-{tag} ({len(items)} items)", scan_strings(strs))

    # per-item flags for G1 prediction
    tmp = tempfile.mkdtemp(prefix="scan163b_")
    loop = L150.build_agent150({"state_dir": tmp, "sleep_threshold": 10 ** 9})
    for tag in ("edit200", "old_s2fresh", "new_121"):
        flagged_ids = []
        for it in bench_items[tag]:
            strs = [t.get("sentence_en", "") for t in it.get("taught", [])]
            strs.append(it.get("question", ""))
            hit = False
            for s in strs:
                try:
                    acts = loop.ears.hear(s)
                except Exception:
                    continue
                if any(flag_action(a) for a in acts):
                    hit = True
                    break
            if hit:
                flagged_ids.append(it["id"])
        print(f"G1-{tag} flagged item ids: {flagged_ids}")

    # 2. sessions152 turns
    ss = json.loads((ROOT / "artifacts" / "fable-session152-20260922"
                     / "sessions152.json").read_text(encoding="utf-8"))
    for s in ss:
        show(f"session-{s['id']}",
             scan_strings([t["text"] for t in s["turns"]]))

    # 3. R98 (p2 + q1-ish), R110 (rt110), R81 (rt81)
    import fable_redteam98_cases as R98
    r98 = [(c["id"], st["text"]) for c in R98.CASES
           for st in c.get("steps", []) if "text" in st]
    hits98 = []
    for i, t in r98:
        for _, f in scan_strings([t]):
            hits98.append((i, t, f))
    print(f"===== R98-p2: {len(hits98)} flagged =====")
    for i, t, f in hits98:
        print(f"  {i} {t[:100]!r} -> {f}")
    import fable_redteam110_cases as R110
    r110 = [(c["id"], st["text"]) for c in R110.CASES
            for st in c.get("steps", []) if "text" in st]
    hits = []
    for i, t in r110:
        for _, f in scan_strings([t]):
            hits.append((i, t, f))
    print(f"===== R110-rt110: {len(hits)} flagged =====")
    for i, t, f in hits:
        print(f"  {i} {t[:100]!r} -> {f}")
    import fable_redteam81_probe as R81
    r81 = []
    for entry in R81.SEQS:
        sid = entry[0]
        for st in entry[2]:
            if isinstance(st, dict) and "turn" in st:
                r81.append((sid, st["turn"]))
    hits81 = []
    for sid, t in r81:
        for _, f in scan_strings([t]):
            hits81.append((sid, t, f))
    print(f"===== R81-rt81: {len(hits81)} flagged =====")
    for sid, t, f in hits81:
        print(f"  {sid} {t[:100]!r} -> {f}")

    # 4. p4-innocent-30
    art102 = list(ROOT.glob("artifacts/fable-loop102-20260921"))
    print("art102:", art102)
    p4 = json.loads((ROOT / "artifacts" / "fable-loop102-20260921"
                     / "p4-innocent-30.json").read_text(encoding="utf-8"))
    p4strs = []
    for item in p4["sentences"]:
        p4strs += list(item.get("setup", [])) + [item["text"]]
    show("p4-innocent-30", scan_strings(p4strs))

    # 5. q1 fixed + soak shapes + p3 SEQS
    show("q1-fixed", scan_strings(
        ["Mira's city is Lisbon.", "Please forget Mira city",
         "Mira's city is Paris.", "Who is Mira's city?",
         "WHO IS MIRA'S CITY?"]))
    show("soak-shapes", scan_strings(
        ["SoakP001's city is SoakV001.",
         "Actually, SoakP001's city is SoakW001.",
         "What is SoakP001's city?"]))
    import fable_loop96_marks as M96
    p3turns = []
    for sid, _desc, steps in M96.SEQS:
        for st in steps:
            if isinstance(st, dict) and st.get("turn") not in (
                    None, "__SETUP_SECOND_MIRA__"):
                p3turns.append(f"{sid} :: {st['turn']}")
    show("p3-SEQS", scan_strings(p3turns))
    # p3 l5/l6 generated names: find name pools
    import re
    src = Path(SCRIPTS / "fable_loop96_marks.py").read_text(encoding="utf-8")
    for m in sorted(set(re.findall(
            r"[A-Za-z]*P\d+[A-Za-z0-9]*|[A-Z][a-z]+(?:[A-Z][a-z]+)+\d*",
            src)))[:40]:
        print("  pool?", m)


if __name__ == "__main__":
    main()
