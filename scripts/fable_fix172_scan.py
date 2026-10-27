#!/usr/bin/env python3
"""Experiment 172 -- PRE-SEAL move scan (uses the REAL loop154c parser).

For every bench item and suite scope, feed the ordered turn texts through
the unchanged loop154c ears hear() (scratch notebook, writes nothing
registered) and statically track (name, relation-key) slots. A scope is
flagged as WOULD-MOVE when a turn parses (via the real ears) as a
STRUCTURED (bench73/extra-shape, action.get("structured")) teach/correct
on a NON-allow-listed relation, with NO explicit correction prefix, for
a slot already holding a DIFFERENT value: under 154c that turn silently
replaces; under 172 it change-prompts (different reply + different
stored value -> different downstream answers).

Possessive-shape re-teaches already prompt under 154c (no move).
Explicit-correction-prefixed turns keep correcting (no move).
Allow-listed relations keep the add path (no move).

Reads only sealed inputs; runs nothing registered. Output:
artifacts/fable-copula172-20260922/trigger_scan172.json
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix154b_multival as M154  # noqa: E402 (key fn, read-only)
import fable_fix154c_allowlist as M154C  # noqa: E402 (allow-list)
import fable_loop102_agent as L102  # noqa: E402 (prefix RE, read-only)
import fable_loop154c_agent as L154c  # noqa: E402 (parser, read-only)

ART = ROOT / "artifacts"
ART138B = ART / "fable-agent138b-20260922"
OUT = ART / "fable-copula172-20260922"


def build_ears():
    tmp = tempfile.mkdtemp(prefix="scan172_")
    cfg = dict(L154c.DEFAULT_CONFIG154C)
    cfg["state_dir"] = tmp
    cfg["sleep_threshold"] = 100000
    loop = L154c.build_agent154c(cfg)
    return loop.ears


def scan_scope(ears, texts: list[str]) -> list[str]:
    """Would-move reasons for one ordered turn list (one fresh scope)."""
    reasons: list[str] = []
    slots: dict[tuple[str, str], set[str]] = {}
    for t in texts:
        text = " ".join(str(t).split())
        if not text:
            continue
        if text.rstrip().endswith("?"):
            continue  # questions never write
        prefixed = (L102.strip_correction_prefix(text) is not None)
        try:
            actions = ears.hear(text)
        except Exception:  # noqa: BLE001 -- unparsable: no trigger
            continue
        for a in actions or []:
            if not isinstance(a, dict):
                continue
            if a.get("act") not in ("teach", "correct"):
                continue
            name = str(a.get("name", ""))
            value = str(a.get("value", ""))
            if not name or not value:
                continue
            key = M154.relation_key154b(str(a.get("relation", "")))
            slot = (name.lower(), key)
            vals = slots.setdefault(slot, set())
            if (a.get("structured") and not M154C.is_multi154c(key)
                    and not prefixed and value not in vals and vals):
                reasons.append(
                    f"copula-reteach {name}|{key}: {text[:80]}")
            vals.add(value)
    return reasons


def main() -> int:
    ears = build_ears()
    out: dict = {}
    total_flags = 0

    # -- G1 bench: taught sentences per item (4 splits) --
    bench_files = {
        "new_121_4hop": "data/open/bench121/fable_edit121_4hop.jsonl",
        "old_s2fresh_4hop": "data/open/bench103/fable_edit103_s2fresh_4hop.jsonl",
        "edit200": "data/open/bench65/fable_edit_200.jsonl",
        "bench132_4hop": "data/open/bench132/fable_edit132_4hop.jsonl",
    }
    bench_flag: dict[str, list[str]] = {}
    bench_n = 0
    for split, rel in bench_files.items():
        for line in (ROOT / rel).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            bench_n += 1
            it = json.loads(line)
            texts = [t.get("sentence_en", "") for t in it.get("taught", [])]
            reasons = scan_scope(ears, texts)
            if reasons:
                bench_flag[f"{split}:{it.get('id')}"] = reasons
    out["bench"] = {"n_items": bench_n, "flagged": bench_flag}
    print(f"bench: {bench_n} items, {len(bench_flag)} flagged")
    for cid, rs in bench_flag.items():
        print(f"   {cid}: {rs}")
    total_flags += len(bench_flag)

    # -- G2 p2 (redteam98 steps, per case) --
    p2 = json.loads((ART / "fable-redteam98-20260921"
                     / "fable_redteam98_cases.json").read_text(
                         encoding="utf-8"))
    p2flag: dict[str, list[str]] = {}
    for c in p2:
        texts = [s.get("text", "") for s in c.get("steps", [])
                 if s.get("op") == "send"]
        reasons = scan_scope(ears, texts)
        if reasons:
            p2flag[c.get("id")] = reasons
    out["p2"] = {"n": len(p2), "flagged": p2flag}
    print(f"p2: {len(p2)} cases, {len(p2flag)} flagged {p2flag}")
    total_flags += len(p2flag)

    # -- G2 rt110 (steps, per case) --
    rt110 = json.loads((ART / "fable-redteam110-20260921"
                        / "fable_redteam110_cases.json").read_text(
                            encoding="utf-8"))
    rtflag: dict[str, list[str]] = {}
    for c in rt110:
        steps = c.get("steps", [])
        texts = [s.get("text", "") for s in steps if isinstance(s, dict)]
        if not texts:
            blob = json.dumps(c)
            texts = re.findall(r'"text":\s*"([^"]+)"', blob)
        reasons = scan_scope(ears, texts)
        if reasons:
            rtflag[c.get("id")] = reasons
    out["rt110"] = {"n": len(rt110), "flagged": rtflag}
    print(f"rt110: {len(rt110)} cases, {len(rtflag)} flagged {rtflag}")
    total_flags += len(rtflag)

    # -- G2 rt81 (sealed SEQS turns, per sequence) --
    import fable_redteam81_probe as P81  # noqa: E402 (sealed steps)
    r81flag: dict[str, list[str]] = {}
    for seq_id, _desc, steps in P81.SEQS:
        texts = [st.get("turn", "") for st in steps
                 if st.get("turn") != "__SETUP_SECOND_MIRA__"]
        reasons = scan_scope(ears, texts)
        if reasons:
            r81flag[seq_id] = reasons
    out["rt81"] = {"n": len(P81.SEQS), "flagged": r81flag}
    print(f"rt81: {len(P81.SEQS)} seqs, {len(r81flag)} flagged {r81flag}")
    total_flags += len(r81flag)

    # -- G2 q1 (literal sends in suite_q1 body) --
    src = (SCRIPTS / "fable_marks123_all.py").read_text(encoding="utf-8")
    q1body = src[src.find("def suite_q1"):src.find("def suite_bench")]
    q1texts = re.findall(r'_q1_turn\(d\d?, R98, root\d?, "[^"]+", (".*?")\)',
                         q1body)
    q1texts = [json.loads(t) for t in q1texts]
    q1reasons = scan_scope(ears, q1texts)
    out["q1"] = {"n_turns": len(q1texts), "flagged": q1reasons}
    print(f"q1: {len(q1texts)} turns, flagged={q1reasons}")
    total_flags += len(q1reasons)

    # -- G2 p4 (30 innocents, one scope each) --
    p4 = json.loads((ART / "fable-loop102-20260921" / "p4-innocent-30.json")
                    .read_text(encoding="utf-8"))
    p4flag: dict[str, list[str]] = {}
    for i, sent in enumerate(p4["sentences"]):
        reasons = scan_scope(ears, [sent])
        if reasons:
            p4flag[f"p4-{i}"] = reasons
    out["p4"] = {"n": len(p4["sentences"]), "flagged": p4flag}
    print(f"p4: {len(p4['sentences'])} sents, {len(p4flag)} flagged {p4flag}")
    total_flags += len(p4flag)

    # -- G2 p3 l-levels: quoted possessive/copula teaches in loop96_marks --
    m96 = (SCRIPTS / "fable_loop96_marks.py").read_text(encoding="utf-8")
    lits = re.findall(r'"([A-Z][^"]*?\'s [a-z][^"]*? is [^"]+?)"', m96)
    lits += re.findall(r'"([A-Z][^"]*? is (?:a citizen of|married to|'
                       r'famous for)[^"]+?)"', m96)
    p3reasons = scan_scope(ears, lits)
    out["p3_liters"] = {"n": len(lits), "flagged": p3reasons}
    print(f"p3_liters: {len(lits)} turns, flagged={p3reasons}")
    total_flags += len(p3reasons)

    # -- G3 redteam136 (input text per row) --
    r136flag: dict[str, list[str]] = {}
    n136 = 0
    for line in (ART138B / "redteam136-loop138b.json").read_text(
            encoding="utf-8").splitlines():
        if not line.strip():
            continue
        n136 += 1
        c = json.loads(line)
        reasons = scan_scope(ears, [c.get("text", "")])
        if reasons:
            r136flag[c.get("id", f"row{n136}")] = reasons
    out["redteam136"] = {"n": n136, "flagged": r136flag}
    print(f"redteam136: {n136} cases, {len(r136flag)} flagged {r136flag}")
    total_flags += len(r136flag)

    # -- G3 redteam143 (case inputs from the suite cases file) --
    import fable_redteam143_run as R143  # noqa: E402 (cases, read-only)
    suite143 = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    r143flag: dict[str, list[str]] = {}
    for c in suite143["cases"]:
        texts: list[str] = []
        for k in ("text", "turn", "question", "send"):
            if c.get(k):
                texts.append(str(c[k]))
        for k in ("teaches", "teach", "steps", "turns"):
            v = c.get(k)
            if isinstance(v, list):
                for e in v:
                    texts.append(e.get("text", e) if isinstance(e, dict)
                                 else str(e))
        tr = c.get("transcript", [])
        if isinstance(tr, list):
            for e in tr:
                texts.append(e.get("text", e) if isinstance(e, dict)
                             else str(e))
        reasons = scan_scope(ears, [str(t) for t in texts])
        if reasons:
            r143flag[c.get("id", "?")] = reasons
    out["redteam143"] = {"n": len(suite143["cases"]), "flagged": r143flag}
    print(f"redteam143: {len(suite143['cases'])} cases, "
          f"{len(r143flag)} flagged {r143flag}")
    total_flags += len(r143flag)

    # -- G3 sessions152 (turn texts per session) --
    sdata = json.loads((ART138B / "sessions152-loop138b.json").read_text(
        encoding="utf-8"))
    sflag: dict[str, list[str]] = {}
    for sid, turns in sdata.items():
        texts = [st.get("text", "") for st in turns] if isinstance(
            turns, list) else []
        reasons = scan_scope(ears, texts)
        if reasons:
            sflag[sid] = reasons
    out["sessions152"] = {"n": len(sdata), "flagged": sflag}
    print(f"sessions152: {len(sdata)} sessions, {len(sflag)} flagged {sflag}")
    total_flags += len(sflag)

    out["total_flags"] = total_flags
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "trigger_scan172.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"TOTAL flags: {total_flags}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
