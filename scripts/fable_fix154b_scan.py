#!/usr/bin/env python3
"""Exp 154b -- PRE-SEAL static trigger scan (no agent runs).

Flags cases/sessions whose turns could behave differently on 154b vs 138b:
  * a 2nd different taught value for one non-SINGLE_VALUED_154 slot,
  * a correct-not shape on a non-single relation,
  * a named-value forget shape on a non-single relation.
Reads only sealed inputs/results; runs nothing.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix154b_multival as M154  # noqa: E402

_STATEMENT = re.compile(r"^\s*(.+?)\s+is\s+(.+?)\s*\.?\s*$", re.IGNORECASE)
_APOS = re.compile(r"['\u2019]s\b")
_FORGET = re.compile(r"^\s*forget\s+(\S+?)'s\s+(.+?)\s*[.?!]*\s*$",
                     re.IGNORECASE)


def teach_shape(turn: str):
    """(name, rel_key, value) for single-hop teach/correct shapes, else None."""
    text = " ".join(str(turn).split())
    if text.rstrip().endswith("?"):
        return None
    m = _STATEMENT.match(text)
    if not m:
        return None
    left, value = m.group(1).strip(), m.group(2).strip()
    parts = _APOS.split(left)
    if len(parts) != 2:
        return None
    name = parts[0].strip()
    if " " in name or not name or not value:
        return None
    rel = " ".join(parts[1].split())
    if re.search(r"['\u2019]s\b", rel):
        return None
    return name, M154.relation_key154b(rel), value


def forget_shape(turn: str):
    text = " ".join(str(turn).split())
    m = _FORGET.match(text)
    if not m:
        return None
    words = m.group(2).strip().split()
    if len(words) < 2:
        return None
    name = m.group(1).strip()
    hits = []
    for cut in range(1, len(words)):
        key = M154.relation_key154b(" ".join(words[:cut]))
        if not M154.is_single154b(key):
            hits.append((key, " ".join(words[cut:])))
    return (name, hits) if hits else None


def scan_turns(turns: list[str]) -> list[str]:
    """Return trigger reasons for one ordered turn list (one notebook)."""
    reasons: list[str] = []
    slots: dict[tuple[str, str], set[str]] = {}
    for t in turns:
        if M154.parse_correct_not154b(t) is not None:
            parsed = M154.parse_correct_not154b(t)
            if not M154.is_single154b(parsed["relation"]):
                reasons.append(f"correct-not: {t[:80]}")
            continue
        fg = forget_shape(t)
        if fg is not None:
            reasons.append(f"forget-one?: {t[:80]}")
            continue
        sh = teach_shape(t)
        if sh is not None:
            name, key, value = sh
            slot = (name.lower(), key)
            vals = slots.setdefault(slot, set())
            if value not in vals and vals and not M154.is_single154b(key):
                reasons.append(f"second-value {name}|{key}: {t[:80]}")
            vals.add(value)
    return reasons


def main() -> int:
    ART = ROOT / "artifacts"
    out: dict = {}

    # G3 redteam136 JSONL (one turn per case, fresh notebook each case).
    path = ART / "fable-agent138b-20260922" / "redteam136-loop138b.json"
    flagged136: dict[str, list[str]] = {}
    n136 = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        n136 += 1
        c = json.loads(line)
        reasons = scan_turns([c.get("text", "")])
        if reasons:
            flagged136[c.get("id", f"row{n136}")] = reasons
    out["redteam136"] = {"n": n136, "flagged": flagged136}
    print(f"redteam136: {n136} cases, {len(flagged136)} flagged")
    for cid, rs in flagged136.items():
        print(f"   {cid}: {rs}")

    # G3 redteam143: one pretty-printed JSON doc with a rows array.
    path = ART / "fable-agent138b-20260922" / "redteam143-loop138b.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows143 = doc.get("rows", doc) if isinstance(doc, dict) else doc
    flagged143: dict[str, list[str]] = {}
    for c in rows143:
        texts: list[str] = []
        for key in ("text", "turn", "question"):
            if c.get(key):
                texts.append(str(c[key]))
        for key in ("teaches", "teach"):
            val = c.get(key)
            if isinstance(val, list):
                texts.extend(str(v) for v in val)
        for tr in c.get("teach_replies", []) or []:
            pass
        for t in c.get("transcript", []) or []:
            if isinstance(t, dict) and t.get("text"):
                texts.append(str(t["text"]))
            elif isinstance(t, str):
                texts.append(t)
        reasons = scan_turns(texts)
        if reasons:
            flagged143[c.get("id", "?")] = reasons
    out["redteam143"] = {"n": len(rows143), "flagged": flagged143}
    print(f"redteam143: {len(rows143)} cases, {len(flagged143)} flagged")
    for cid, rs in flagged143.items():
        print(f"   {cid}: {rs}")

    # G3 sessions152 (multi-turn sessions, one notebook per session)
    path = ART / "fable-agent138b-20260922" / "sessions152-loop138b.json"
    sdata = json.loads(path.read_text(encoding="utf-8"))
    sflag: dict[str, list[str]] = {}
    for sid, turns in sdata.items():
        texts = [st.get("text", "") for st in turns] if isinstance(
            turns, list) else []
        reasons = scan_turns(texts)
        if reasons:
            sflag[sid] = reasons
    out["sessions152"] = {"n": len(sdata), "flagged": sflag}
    print(f"sessions152: {len(sdata)} sessions, {len(sflag)} flagged")
    for sid, rs in sflag.items():
        print(f"   {sid}: {rs}")

    # G2 single-turn suites: p2 (redteam98) + rt110 (from results logs)
    import fable_redteam98_cases as RC
    p2 = list(RC.CASES)
    p2flag = {}
    for c in p2:
        reasons = scan_turns([c.get("turn") or c.get("text", "")])
        if reasons:
            p2flag[c.get("id")] = reasons
    out["p2"] = {"n": len(p2), "flagged": p2flag}
    print(f"p2: {len(p2)} cases, {len(p2flag)} flagged {p2flag}")

    rt110 = json.loads((ART / "fable-redteam110-20260921"
                        / "fable_redteam110_cases.json").read_text(
                            encoding="utf-8"))
    rtflag = {}
    for c in rt110:
        texts = [e.get("text", "") for e in c.get("log", [])
                 if "text" in e] or [c.get("text", "")]
        # log holds replies; turn text may sit beside; fall back to scan-all
        blob = json.dumps(c)
        reasons = scan_turns(re.findall(r'"text":\s*"([^"]+)"', blob))
        if reasons:
            rtflag[c.get("id")] = reasons
    out["rt110"] = {"n": len(rt110), "flagged": rtflag}
    print(f"rt110: {len(rt110)} cases, {len(rtflag)} flagged")
    for cid, rs in rtflag.items():
        print(f"   {cid}: {rs}")

    (ART / "fable-multival154b-20260922" / "trigger_scan.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False)[:20000],
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
