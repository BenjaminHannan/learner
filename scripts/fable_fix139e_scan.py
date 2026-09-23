#!/usr/bin/env python3
"""Experiment 139e -- PRE-SEAL static scan (not a registered run).

Checks the relation-gated trigger against the VALUES as they reach the
notebook in every regression suite and bench template -- including the
declarative bench73 templates that 139d's scan missed (it only matched
possessive shapes). Basis for the PASSMARKS 0-move predictions.
Reads only; writes stdout.

Sources scanned:
  * bench121 all 800 items: every taught (relation, object) triple --
    exactly what the bench73 template stage hands the notebook;
  * marks123 bench files (fable_edit_200 + s2fresh 4-hop): triples;
  * G3 inputs (cases136 turns, redteam143 cases, sessions152 turns):
    possessive spans AND bench73-template parses, relation-gated;
  * marks123 chat-suite literal inputs (redteam98 cases, redteam110
    cases, redteam81 probe, loop96 marks, marks123_all inline strings,
    p4-innocent-30 setups+texts): possessive spans AND bench73 parses;
  * soak generator: shape noted (single-token values, cannot trigger).
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix139c_tail as T139c  # noqa: E402 (read-only)
import fable_fix139d_tail as T139d  # noqa: E402 (read-only)
import fable_fix139e_tail as T139e  # noqa: E402 (read-only)

try:
    import fable_bench73_english_arm as B73  # noqa: E402 (read-only)
    HAVE_B73 = True
except Exception:  # noqa: BLE001
    HAVE_B73 = False

POSS = re.compile(r"\b([A-Z][\w.'-]*'s\s+([\w /-]+?)\s+is\s+(.+?))\s*$",
                  re.IGNORECASE)


def gated_hit(relation: str, raw_value: str) -> dict | None:
    cleaned, _ = T139c.strip_chat_tail(raw_value.strip().rstrip("."))
    split = T139d.unknown_tail_split(cleaned)
    if split is None:
        return None
    if T139e.normalize_relation(relation) not in T139e.LISTED_RELATIONS:
        return None
    return {"clean139c": cleaned, "base": split[0], "tail": split[1]}


def check_triple(tag: str, relation: str, raw_value: str,
                 extra: str = "") -> dict | None:
    hit = gated_hit(relation, raw_value)
    if hit is None:
        return None
    return {"suite": tag, "relation": T139e.normalize_relation(relation),
            "raw": raw_value, "extra": extra, **hit}


def spans_from_line(line: str) -> list[tuple[str, str, str]]:
    """(full_span, relation_surface, value) possessive teaches in a line."""
    out = []
    for m in POSS.finditer(line.strip()):
        out.append((m.group(1), m.group(2).strip(),
                    m.group(3).strip().rstrip(".")))
    return out


def check_text(tag: str, text: str) -> list[dict]:
    hits = []
    for line in str(text).splitlines():
        line = line.strip()
        if not line:
            continue
        for _full, rel, val in spans_from_line(line):
            h = check_triple(tag, rel, val, extra=_full[:100])
            if h is not None:
                hits.append(h)
        if HAVE_B73:
            try:
                triple = B73.hear_teach_template(line)
            except Exception:  # noqa: BLE001
                triple = None
            if triple is not None:
                subj, rel, obj = triple
                h = check_triple(tag, rel, obj, extra=line[:100])
                if h is not None:
                    hits.append(h)
    return hits


def check_turns(tag: str, turns: list[str]) -> list[dict]:
    """Check individual teach-turn strings (never whole JSON dumps)."""
    hits = []
    for t in turns:
        hits.extend(check_text(tag, str(t)))
    return hits


def main() -> int:
    all_hits: list[dict] = []
    counts: dict[str, int] = {}

    def add(tag: str, hits: list[dict], n_inputs: int) -> None:
        all_hits.extend(hits)
        counts[tag] = n_inputs
        print(f"scan139e [{tag}]: {n_inputs} inputs, {len(hits)} gated hits",
              flush=True)

    # --- bench121 all 800: taught triples (declarative templates) -----------
    spec = importlib.util.spec_from_file_location(
        "fable_loop138b_bench121",
        ROOT / "artifacts" / "fable-agent138b-20260922"
        / "fable_loop138b_bench121.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    n = 0
    for stag, path, _s in list(mod.SPLITS_3) + [mod.SPLIT_132]:
        items = [json.loads(x) for x in Path(str(path)).read_text(
            encoding="utf-8").splitlines() if x.strip()]
        for it in items:
            for t in it.get("taught", []):
                n += 1
                h = check_triple(f"bench121:{stag}",
                                 str(t.get("relation", "")),
                                 str(t.get("object", "")),
                                 extra=str(t.get("sentence_en", ""))[:100])
                if h is not None:
                    all_hits.append(h)
    counts["bench121:all taught triples"] = n
    print(f"scan139e [bench121 triples]: {n} triples, "
          f"{len([h for h in all_hits if h['suite'].startswith('bench121')])} gated hits",
          flush=True)

    # --- marks123 bench files: triples --------------------------------------
    for tag, rel_path in (
            ("marks-bench:edit200",
             "data/open/bench65/fable_edit_200.jsonl"),
            ("marks-bench:s2fresh",
             "data/open/bench103/fable_edit103_s2fresh_4hop.jsonl")):
        p = ROOT / rel_path
        if not p.exists():
            print(f"scan139e [{tag}]: MISSING {rel_path}", flush=True)
            continue
        items = [json.loads(x) for x in p.read_text(
            encoding="utf-8").splitlines() if x.strip()]
        nn, hits = 0, []
        for it in items:
            for t in it.get("taught", []):
                nn += 1
                h = check_triple(tag, str(t.get("relation", "")),
                                 str(t.get("object", "")),
                                 extra=str(t.get("sentence_en", ""))[:100])
                if h is not None:
                    hits.append(h)
        add(tag, hits, nn)

    # --- G3 inputs (individual teach turns, not JSON dumps) ------------------
    cases136 = json.loads((ROOT / "artifacts" / "fable-redteam136-20260922"
                           / "cases136.json").read_text(encoding="utf-8"))
    turns136: list[str] = []
    for c in cases136:
        for key in ("turns", "dialog", "teach", "teaches", "text"):
            v = c.get(key) if isinstance(c, dict) else None
            if isinstance(v, list):
                turns136.extend(str(x) for x in v)
            elif isinstance(v, str):
                turns136.append(v)
        if isinstance(c, dict):
            for key in ("input", "sentence", "turn"):
                if isinstance(c.get(key), str):
                    turns136.append(c[key])
    add("rt136", check_turns("rt136", turns136), len(turns136))
    import fable_redteam143_run as R143  # noqa: E402 (read-only)
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    turns143: list[str] = []
    for c in suite["cases"]:
        for key in ("teaches", "turns", "dialog"):
            v = c.get(key) if isinstance(c, dict) else None
            if isinstance(v, list):
                turns143.extend(str(x) for x in v)
    add("rt143", check_turns("rt143", turns143), len(turns143))
    import fable_session152_run as S152R  # noqa: E402 (read-only)
    sturns: list[str] = []
    for s in S152R.S152.SESSIONS:
        for key in ("turns", "dialog"):
            v = s.get(key) if isinstance(s, dict) else None
            if isinstance(v, list):
                for t in v:
                    sturns.append(str(t.get("text", t)) if isinstance(
                        t, dict) else str(t))
    add("sessions152", check_turns("sessions152", sturns), len(sturns))

    # --- marks123 chat suites: literal inputs --------------------------------
    def step_texts(cases) -> list[str]:
        out: list[str] = []
        for c in cases or []:
            if not isinstance(c, dict):
                continue
            for key in ("steps", "turns", "dialog", "teaches"):
                v = c.get(key)
                if isinstance(v, list):
                    for s in v:
                        out.append(str(s.get("text", s)) if isinstance(
                            s, dict) else str(s))
        return out

    import fable_redteam98_cases as C98  # noqa: E402 (read-only)
    c98 = getattr(C98, "CASES", getattr(C98, "cases", []))
    t98 = step_texts(c98)
    add("p2-redteam98", check_turns("p2-redteam98", t98), len(t98))
    t110: list[str] = []
    p110 = ROOT / "artifacts" / "fable-redteam110-20260921" / "fable_redteam110_cases.json"
    if p110.exists():
        cases110 = json.loads(p110.read_text(encoding="utf-8"))
        clist = cases110.get("cases", cases110) if isinstance(
            cases110, dict) else cases110
        t110 = step_texts(clist)
    add("rt110", check_turns("rt110", t110), len(t110))
    import fable_redteam81_probe as R81  # noqa: E402 (read-only)
    t81: list[str] = []
    for seq in getattr(R81, "SEQS", []):
        try:
            turns = seq[2] if len(seq) > 2 else []
        except Exception:  # noqa: BLE001
            continue
        for t in turns or []:
            if isinstance(t, dict) and "turn" in t:
                t81.append(str(t["turn"]))
    add("rt81", check_turns("rt81", t81), len(t81))
    p4 = json.loads((ROOT / "artifacts" / "fable-loop102-20260921"
                     / "p4-innocent-30.json").read_text(encoding="utf-8"))
    p4texts = []
    for item in p4.get("sentences", p4 if isinstance(p4, list) else []):
        p4texts.extend(item.get("setup", []))
        p4texts.append(item.get("text", ""))
    add("p4-innocent", check_turns("p4-innocent", p4texts), len(p4texts))
    # p3 (loop96 marks): SEQS turns + turns84 file
    import fable_loop96_marks as M96  # noqa: E402 (read-only)
    t96: list[str] = []
    for seq in M96.SEQS:
        try:
            turns = seq[2] if len(seq) > 2 else []
        except Exception:  # noqa: BLE001
            continue
        for t in turns or []:
            if isinstance(t, dict) and "turn" in t:
                t96.append(str(t["turn"]))
    try:
        tp = Path(str(M96.TURNS))
        if tp.exists():
            for line in tp.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        t96.append(str(json.loads(line).get("text", line)))
                    except Exception:  # noqa: BLE001
                        t96.append(line)
    except Exception:  # noqa: BLE001
        pass
    add("p3-loop96", check_turns("p3-loop96", t96), len(t96))
    # inline +96-marks/q1/soak literal strings: source-text possessive scan
    src_hits = []
    n_src = 0
    for fname in ("fable_loop96_marks.py", "fable_marks123_all.py",
                  "fable_redteam98_cases.py", "fable_redteam110_runner.py",
                  "fable_redteam81_probe.py"):
        src = (SCRIPTS / fname).read_text(encoding="utf-8")
        for line in src.splitlines():
            for _full, rel, val in spans_from_line(line):
                n_src += 1
                h = check_triple(f"src:{fname}", rel, val,
                                 extra=line.strip()[:100])
                if h is not None:
                    src_hits.append(h)
    add("suite-sources", src_hits, n_src)

    print(f"scan139e TOTAL: {len(all_hits)} gated trigger hits", flush=True)
    for h in all_hits[:60]:
        print(f"  HIT {h['suite']}: rel={h['relation']!r} "
              f"raw={h['raw']!r} tail={h['tail']} extra={h['extra']!r}",
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
