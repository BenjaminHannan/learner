#!/usr/bin/env python3
"""vread wrong-person diagnosis (helper W, 2026-09-28): shared loader. Read only, CPU, no tokenizer, no model.

Rebuilds the dev rows (turn, previous reply, history, prompt, gold cards) from the vread pack
(artifacts/claude-vread-20260927/data), and finds every whole-word, exact-case copy of a name in the prompt regions
with the label search's own pattern (claude_vread_data.occurrences). No tokenizer is on this machine, so the vread2
"token decodes to exactly the text" test on a copy is NOT applied: copies here are text-only. Where that could matter
is disclosed in DIAGNOSIS.md.

Regions of a prompt, in the label search order: 0 = the turn, 1 = the previous reply, 2.. = the earlier-turn lines
newest first (claude_vread_data.prompt_regions). "line k back" = region 2 + k.
"""
from __future__ import annotations

import json
import lzma
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
import claude_vread_data as VD  # noqa: E402 (read only; top-level imports need no tokenizer)
from claude_lis300_common import canon_frame  # noqa: E402
from claude_lis319_common import build_prompt_hist  # noqa: E402

V1 = REPO / "artifacts/claude-vread-20260927"
STATES = VD.STATES
PERSON_RELS = None


def load_jsonl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def norm(x):
    return " ".join(str(x or "").lower().split())


def dev_rows(want="dev"):
    compact = json.loads(lzma.decompress((V1 / "data/rows.json.xz").read_bytes()).decode())
    dia = json.loads(lzma.decompress((V1 / "data/dialogs.json.xz").read_bytes()).decode())
    out = []
    for rid, side, fam, frame in compact:
        if side != want:
            continue
        frame = canon_frame(frame)
        turns = dia[VD.dialog_of(rid)[len("glm320-"):]]
        i = int(rid.rsplit("-t", 1)[1]) - 1
        u, rb = turns[i][0].strip(), (turns[i][1] or "").strip()
        hist = [(turns[j][0].strip(), (turns[j + 1][1] or "").strip()) for j in range(i)]
        prompt = build_prompt_hist(u, rb, hist)
        cards = [{"owner": f["owner"], "rel": f["rel"], "value": f["value"], "state": STATES[f["mode"]]}
                 for f in frame["facts"] if f["mode"] in STATES]
        out.append({"id": rid, "family": fam, "turn": u, "prev_reply": rb, "history": [list(h) for h in hist],
                    "prompt": prompt, "cards": cards, "frame": frame})
    return out


def regions_of(row):
    p, regions = VD.prompt_regions(row["turn"], row.get("prev_reply", ""), [tuple(h) for h in row["history"]])
    assert p == row["prompt"]
    return regions


def copies_text(name, row, regions=None):
    """[(region index, char start, char end)] of every whole-word exact-case copy of name, text-only"""
    regions = regions or regions_of(row)
    out = []
    for ri, (a, b) in enumerate(regions):
        for c0, c1 in VD.occurrences(name, row["prompt"], a, b):
            out.append((ri, c0, c1))
    return out


def newest_copy(name, row, regions=None):
    """the label's own pointer as text: first copy in search order (region order, then position in the region)"""
    cp = copies_text(name, row, regions)
    return cp[0] if cp else None


PERSON_RELS_SET = {"apprentice", "aunt", "babysitter", "best_friend", "boss", "brother", "brother_in_law", "child",
                   "classmate", "coach", "colleague", "cousin", "daughter", "daughter_in_law", "dentist", "doctor",
                   "ex_husband", "ex_wife", "father", "father_in_law", "fiance", "friend", "goddaughter", "godfather",
                   "godmother", "grandchild", "granddaughter", "grandfather", "grandmother", "grandson", "great_aunt",
                   "great_grandfather", "great_grandmother", "great_uncle", "half_brother", "half_sister",
                   "head_coach", "husband", "landlord", "mentor", "mother", "mother_in_law", "neighbour", "nephew",
                   "niece", "parent", "partner", "rival", "roommate", "sibling", "sister", "sister_in_law", "son",
                   "son_in_law", "spouse", "stepbrother", "stepdaughter", "stepfather", "stepmother", "stepsister",
                   "stepson", "teacher", "teammate", "therapist", "tutor", "uncle", "vet"}
# copied verbatim from scripts/claude_vread2_score.py PERSON_RELS (line 33-41) so the rival definition is the same


def dialog_names(rows):
    out = {}
    for r in rows:
        s = out.setdefault(r["id"].rsplit("-t", 1)[0], set())
        for c in r["cards"]:
            if c["owner"] != "me":
                s.add(c["owner"])
            if c["rel"] in PERSON_RELS_SET:
                s.add(c["value"])
    return out


def lora_cards(read):
    fr = (read or {}).get("frame")
    if not isinstance(fr, dict):
        return []
    confs = list((read or {}).get("conf") or [])
    out = []
    for i, f in enumerate(fr.get("facts") or []):
        if not isinstance(f, dict) or f.get("mode") not in STATES:
            continue
        out.append({"owner": str(f.get("owner", "")), "rel": f.get("rel"), "value": str(f.get("value", "")),
                    "state": STATES[f["mode"]], "conf": confs[i] if i < len(confs) else 0.0})
    return out


def match_cards(cards, gold):
    """as claude_vread2_score.match_cards: each emitted card (any confidence) takes the first unused gold card with the
    same relation and state, preferring one equal in owner and value (lower-cased)"""
    used, out = set(), []
    for c in cards:
        cand = [k for k, g in enumerate(gold) if k not in used and g["rel"] == c["rel"] and g["state"] == c["state"]]
        if not cand:
            out.append((c, None))
            continue
        k = next((k for k in cand if norm(c["owner"]) == norm(gold[k]["owner"]) and norm(c["value"]) == norm(gold[k]["value"])), cand[0])
        used.add(k)
        out.append((c, k))
    return out
