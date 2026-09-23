#!/usr/bin/env python3
"""own-O0b INDEPENDENT rule-based re-deriver (plan section 2.4 / O0).

Recomputes each label from the TURN TEXT + the generator's world intent
(owner/cue/value surfaces, relation name, inverse flag) -- never from the
frame template id -- and counts mismatches.

Checks per row:
  W1 every span slices its turn and is a whole-word span (Pown0b.3).
  W2 each stored span equals the span re-found by normalized whole-word
     search of the world surface in the turn text.
  W3 act re-derived from text markers only; equals stored act.
  W4 count == len(facts); modes consistent with act; question present iff
     ASK; question relations are table names, <=3; inverse == world inverse.
  W5 relations are relation_table_v2 names; cue surface is a known cue of
     the relation (canon name or alias, plural-tolerant).
  W6 no L2 frame id appears in a split other than l2dev (Pown0b.2 support).
  W7 family shares (Pown0b.4 support; enforced by reporter, counted here).

Usage:
  check.py --dir <artifacts dir> [--sample N] [--seed S]
Prints mismatch counts and exits 0 iff mismatches == 0.
"""
from __future__ import annotations
import argparse, gzip, json, random, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLE_PATH = ROOT / "artifacts/claude-smolear257-20260922/relation_table_v2.json"

WORDCH = re.compile(r"[A-Za-z0-9_]")

def norm(s):
    return s.lower().replace("'", " ").replace("-", " ").replace("_", " ")

def normq(s):
    return re.sub(r"\s+", " ", norm(s)).strip()

def is_whole(turn, s, e):
    if not (0 <= s < e <= len(turn)):
        return False
    if turn[s:e].strip() == "":
        return False
    if s > 0 and WORDCH.match(turn[s - 1]) and WORDCH.match(turn[s]):
        return False
    if e < len(turn) and WORDCH.match(turn[e - 1]) and WORDCH.match(turn[e]):
        return False
    return True

def find_all_whole(hay, surface):
    """All whole-word occurrences of surface in hay under norm; map to hay spans."""
    ns = normq(surface)
    if not ns:
        return []
    # token-align: build norm char map (collapse whitespace runs)
    chars, idx = [], []
    prev_sp = True
    for i, ch in enumerate(hay):
        n = norm(ch)
        if n == "":
            continue
        for c in n:
            if c == " " or c == "\t" or c == "\n":
                if prev_sp:
                    continue
                prev_sp = True
            else:
                prev_sp = False
            chars.append(c)
            idx.append(i)
    nhay = "".join(chars)
    out = []
    start = 0
    while True:
        k = nhay.find(ns, start)
        if k < 0:
            break
        # word boundaries in ORIGINAL text
        o_s = idx[k]
        o_e = idx[k + len(ns) - 1] + 1
        # expand norm-space check: neighbours must be non-word or edges
        before_ok = (k == 0) or (not WORDCH.match(nhay[k - 1]))
        after_ok = (k + len(ns) == len(nhay)) or (not WORDCH.match(nhay[k + len(ns)]))
        if before_ok and after_ok and is_whole(hay, o_s, o_e):
            out.append([o_s, o_e])
        start = k + 1
    return out

def load_table():
    d = json.loads(TABLE_PATH.read_text())
    names = {r["name"] for r in d["relations"]}
    cue2rel = {}
    for r in d["relations"]:
        cue2rel[normq(r["name"])] = r["name"]
        for a in r.get("aliases", []):
            cue2rel.setdefault(normq(a), r["name"])
    return names, cue2rel

NAMES, CUE2REL = load_table()

CHAT_RES = [re.compile(p) for p in
    [r"\bhey\b", r"\bhello\b", r"\bhi\b", r"\bhow are you\b", r"\bthanks\b",
     r"\bthank you\b", r"\bbye\b", r"\bsee you\b", r"\blol\b", r"\bhaha\b",
     r"\bcool\b", r"\bnice\b", r"\bokay\b", r"\bok\b", r"\bgreat day\b",
     r"\bgood morning\b", r"\bgood night\b", r"\bwhat'?s up\b", r"\bgossip\b",
     r"\bweekend\b", r"\bweather\b", r"\braining\b", r"\bcoffee\b", r"\bgame\b",
     r"\bhow have you been\b"]]
DENY_RES = [re.compile(p) for p in
    [r"\bisn'?t\b", r"\baren'?t\b", r"\bain'?t\b", r"\bnever\b", r"\bnope\b",
     r"\bno way\b", r"\bthat'?s wrong\b", r"\bfalse\b", r"\bnah\b",
     r"\bdenied\b", r"\bdeny\b", r"\bis no\b", r"\bis not\b", r"^no,",
     r"\bnot\b", r"\bwrong\b", r"\bincorrect\b", r"\bhas no\b",
     r"\bthere is no\b", r"\bstrike that\b", r"\btake it back\b",
     r"\bforget it\b", r"\bcouldn'?t\b", r"\bcan'?t\b", r"\bimpossible\b",
     r"\bnobody\b", r"\bdon'?t\b", r"\brefuse\b", r"\bhow could\b",
     r"\bmyth\b", r"\bbusted\b", r"\bspoiler\b", r"\bplot twist\b",
     r"\bnewsflash\b", r"\bvetoed\b", r"\boverruled\b", r"\brejected\b",
     r"\bdebunked\b"]]
CORRECT_RES = [re.compile(p) for p in
    [r"\bactually\b", r", not ", r"\bno wait\b", r"\bcorrection(?! denied\b)",
     r"\bmisspoke\b", r"\blet me fix\b", r"\bupdate:", r"\bnew info\b",
     r"\bit changed\b", r"\bafter all\b", r"\bi was wrong\b",
     r"\bmy mistake\b", r"\boops\b", r"\bsorry,", r"\bthe truth is\b",
     r"\bin fact\b", r"\bas it happens\b", r"\bcome to think\b",
     r"\bnow that i check\b", r"\bi double-checked\b",
     r"\bforget (?!it\b)", r"\bout with\b", r"\bwas yesterday\b",
     r"\breplace\b", r"\bswap\b", r"\bchanged from\b", r"\bas of today\b",
     r"\blatest:", r"\bbreaking:", r"\bedit that\b", r"\bamendment\b",
     r"\bretraction\b", r"\berratum\b", r"\bfixed:", r"\bsmall correction\b",
     r"\bto correct the record\b", r"\blet me correct\b",
     r"^not \w+ anymore"]]
PLAN_RES = [re.compile(p) for p in
    [r"\bwants?\b", r"\bwish\b", r"\bwishes\b", r"\bdream\b", r"\bdreams of\b",
     r"\bhopes?\b", r"\bhoping\b", r"\bplanning\b", r"\bplans\b",
     r"\blooking for\b", r"\bwishlist\b", r"\bfantasiz", r"\bresolution\b",
     r"\baims to\b", r"\bmeans to\b", r"\bheart set\b", r"\bset on\b",
     r"\bcampaigning\b", r"\bbegged\b", r"\bsaving up\b", r"\bpicture a\b",
     r"\bpinky promise\b", r"\bscout'?s honor\b", r"\bgoal\b",
     r"\bthe plan\b", r"\bstep one\b", r"\bone day\b", r"\bwill ask\b",
     r"\basked for\b", r"\bintends\b", r"\bbirthday wish\b",
     r"\bplan\b", r"\bdreaming\b", r"\bon the list\b", r"\btop of the list\b"]]
SUPPOSE_LEADS = ("suppose ", "suppose,", "say ", "say,", "imagine ", "imagine,",
    "let's say ", "lets say ", "let's suppose ", "lets suppose ",
    "let's imagine ", "lets imagine ", "what if ", "pretend ", "assume ",
    "picture this", "consider a world", "for argument", "in a story",
    "hypothesis", "a theory", "theory time", "rumor has it", "some say ",
    "legend says", "the tale goes", "in the play", "in my dream",
    "i dreamed", "make-believe", "once upon a time", "fiction:",
    "the script says", "stage directions", "roleplay", "game plan",
    "grant me that", "take it as given", "whether ", "even if ",
    "a novel where", "just imagine")
CHECK_LEADS = ("wait, ", "hold on,", "let me get this",
    "just to check", "confirming", "meaning ", "in other words",
    "to be clear", "just confirming", "double-checking",
    "following you", "got it,", "okay so ", "right, so ",
    "hmm, so ", "interesting, so ", "wow, so ", "really, ",
    "seriously, ", "for the check", "checking my notes",
    "my notes say", "i wrote down", "before i save",
    "to repeat back", "echoing you", "playing back",
    "as i understand", "the way i heard", "that means ",
    "correct me if", "did i hear", "am i right", "so then ",
    "so i have it", "so noted", "so the record", "so the file",
    "if i heard right", "and ", "if i follow")
ASK_LEADS = ("who ", "who?", "what ", "what?", "which ", "whom ", "whose ",
    "is ", "are ", "was ", "were ", "do ", "does ", "did ", "can ",
    "could ", "would ", "have ", "has ", "might ", "tell me", "name ",
    "give me", "remind me", "any idea", "any clue", "i wonder",
    "my question", "one question", "just wondering", "between us",
    "pray,", "kindly", "i ask", "then who", "but who", "ever heard")

def detect_act(turn, world, all_names, cue_hit):
    """Independent act classification from TEXT ONLY (+name/cue presence)."""
    t = turn.strip()
    tl = re.sub(r"\s+", " ", t.lower())
    for op in OPENERS_STRIP:
        if tl.startswith(op):
            tl = tl[len(op):]
            break
    has_q = "?" in t
    has_name = cue_hit[0]
    has_cue = cue_hit[1]
    chat = any(r.search(tl) for r in CHAT_RES)
    if not has_name and not has_cue and not chat and not has_q:
        return "UNCLEAR"
    suppose_lead = tl.startswith(SUPPOSE_LEADS) or \
        ("just for fun" in tl) or ("hypothetically" in tl) or \
        ("daydream" in tl) or \
        (tl.startswith("if ") and ("were " in tl or "turned out" in tl))
    if suppose_lead and (has_name or has_cue):
        return "SUPPOSE"
    correct_m = any(r.search(tl) for r in CORRECT_RES)
    if correct_m and (has_name or has_cue):
        return "CORRECT"
    if tl.startswith("so ") and not has_q:
        rest = tl[3:]
        if not rest.startswith(("who", "what", "which", "is ", "are ",
                                 "was ", "were ", "do ", "does ", "did ",
                                 "can ", "could ", "would ")):
            return "CHECK"
    if not has_q and tl.startswith(CHECK_LEADS) and (has_name or has_cue):
        return "CHECK"
    if chat:
        return "CHAT"
    deny_m = any(r.search(tl) for r in DENY_RES)
    if deny_m and (has_name or has_cue):
        return "DENY"
    plan_m = any(r.search(tl) for r in PLAN_RES)
    if plan_m and (has_name or has_cue):
        return "PLAN"
    if has_q or tl.startswith(ASK_LEADS) or tl.endswith("who?") or \
            tl.endswith("who") or tl.startswith(("so who", "so what",
                                                  "so which")):
        return "ASK"
    if has_name or has_cue:
        return "STATE"
    return "UNCLEAR"

def cue_ok(relation, cue_surface):
    key = normq(cue_surface)
    if CUE2REL.get(key) == relation:
        return True
    if key.endswith("ies") and CUE2REL.get(key[:-3] + "y") == relation:
        return True
    if key.endswith("es") and CUE2REL.get(key[:-2]) == relation:
        return True
    if key.endswith("s") and CUE2REL.get(key[:-1]) == relation:
        return True
    return False

OPENERS_STRIP = ["hey, ", "so, ", "well, ", "listen, ", "guess what, ",
                 "by the way, ", "oh, ",
                 "hey ", "well ", "listen ",
                 "guess what ", "by the way ", "oh "]
# NOTE: bare "so " (no comma) is never stripped: comma-drop noise never
# produces it, and stripping it would erase genuine CHECK "So ..." turns.

def check_row(row, all_names, l2_frames, cue_hit=None):
    errs = []
    turn = row["turn"]
    world = row.get("world", {})
    # presence of any pool name / any table cue (text-only signals)
    tl = turn.lower()
    if cue_hit is None:
        has_name = True
        has_cue = True
    else:
        has_name, has_cue = cue_hit
    act_hat = detect_act(turn, world, all_names, (has_name, has_cue))
    if act_hat != row["act"]:
        errs.append(f"act stored={row['act']} rederived={act_hat}")
    # W1 + W2 spans
    def check_span(label, sp, surface):
        if not (isinstance(sp, list) and len(sp) == 2):
            return f"{label} not a pair: {sp!r}"
        s, e = sp
        if not is_whole(turn, s, e):
            return f"{label} not whole-word span: {sp!r} text={turn[s:e]!r}"
        found = find_all_whole(turn, surface)
        if [s, e] not in found:
            return (f"{label} span {sp!r} text={turn[s:e]!r} != "
                    f"research of {surface!r} -> {found[:4]}")
        return None
    n_facts = len(row.get("facts", []))
    if row.get("count") != n_facts:
        errs.append(f"count {row.get('count')} != nfacts {n_facts}")
    exp_mode = {"STATE": "ASSERT", "CHECK": "CHECK", "SUPPOSE": "SUPPOSE",
                "PLAN": "PLAN", "CORRECT": "CORRECT", "DENY": "DENY"}.get(row["act"])
    for i, f in enumerate(row.get("facts", [])):
        if f.get("relation") not in NAMES:
            errs.append(f"fact{i} relation not in table: {f.get('relation')!r}")
            continue
        if not cue_ok(f["relation"], world["facts"][i]["cue"]):
            errs.append(f"fact{i} cue {world['facts'][i]['cue']!r} not a cue of {f['relation']}")
        if exp_mode is None:
            errs.append(f"fact{i} present under act {row['act']}")
        elif f.get("mode") != exp_mode:
            errs.append(f"fact{i} mode {f.get('mode')} != {exp_mode}")
        o = f.get("owner")
        wo = world["facts"][i]
        if wo["owner_kind"] in ("ME", "WE"):
            if o != wo["owner_kind"]:
                errs.append(f"fact{i} owner {o!r} != {wo['owner_kind']}")
        else:
            e = check_span(f"fact{i}.owner", o, wo["owner"])
            if e:
                errs.append(e)
        e = check_span(f"fact{i}.cue", f.get("relation_cue_span"), wo["cue"])
        if e:
            errs.append(e)
        e = check_span(f"fact{i}.value", f.get("value_span"), wo["value"])
        if e:
            errs.append(e)
        # within-fact overlap
        spans = [tuple(f["relation_cue_span"]), tuple(f["value_span"])]
        if isinstance(o, list):
            spans.append(tuple(o))
        for a in range(len(spans)):
            for b in range(a + 1, len(spans)):
                if not (spans[a][1] <= spans[b][0] or spans[b][1] <= spans[a][0]):
                    errs.append(f"fact{i} spans overlap: {spans[a]} {spans[b]}")
    q = row.get("question")
    wq = world.get("question")
    if row["act"] == "ASK":
        if not q:
            errs.append("ASK without question")
        else:
            if not (1 <= len(q.get("relations", [])) <= 3):
                errs.append(f"question relations len {len(q.get('relations', []))}")
            for r in q.get("relations", []):
                if r not in NAMES:
                    errs.append(f"question relation not in table: {r!r}")
            if bool(q.get("inverse")) != bool((wq or {}).get("inverse")):
                errs.append("question inverse != world inverse")
            qo = q.get("owner_span")
            if (wq or {}).get("owner_kind") in ("ME", "WE"):
                if qo != wq["owner_kind"]:
                    errs.append(f"question owner {qo!r} != {wq['owner_kind']}")
            else:
                e = check_span("question.owner", qo, (wq or {}).get("owner", ""))
                if e:
                    errs.append(e)
    else:
        if q is not None:
            errs.append(f"non-ASK act {row['act']} carries a question")
    # spelling flag consistency
    if bool(row.get("spelling_flag")) != (row.get("family") == "typo"):
        errs.append("spelling_flag set outside typo family")
    return errs

def iter_rows(d, sample, seed):
    files = sorted(d.glob("*.jsonl.gz"))
    rows = []
    for f in files:
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append((f.name, json.loads(line)))
    if sample and len(rows) > sample:
        rng = random.Random(seed)
        rows = rng.sample(rows, sample)
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--sample", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    d = Path(args.dir)
    from collections import Counter
    import sys as _s
    _s.path.insert(0, str(ROOT / "scripts"))
    import claude_own_o0b_gen as G
    all_names = (list(G.TRAIN_NAMES) + list(G.L1_NAMES) + list(G.RESERVED_NAMES)
                 + list(G.PET_NAMES) + list(G.PLACES)
                 + ["Fig", "Moss", "he", "she"])
    rows = iter_rows(d, args.sample, args.seed)
    l2f = set(G.frame_split()["l2"])
    name_re = re.compile(r"(?<!\w)(?:" + "|".join(
        sorted((re.escape(n.lower()) for n in all_names), key=len,
               reverse=True)) + r")(?!\w)")
    cue_re = re.compile(r"(?<!\w)(?:" + "|".join(
        sorted((re.escape(c) for c in CUE2REL), key=len,
               reverse=True)) + r")(?!\w)")
    n_mis = 0
    examples = []
    fam = Counter()
    for fname, r in rows:
        fam[r.get("family")] += 1
        if r.get("split") != "l2dev" and r.get("frame_id") in l2f:
            n_mis += 1
            examples.append((r.get("id"), "L2 frame outside l2dev"))
            continue
        tl = r["turn"].lower()
        has_name = bool(name_re.search(tl))
        tnorm = re.sub(r"\s+", " ", norm(r["turn"]))
        has_cue = bool(cue_re.search(tnorm))
        errs = check_row(r, all_names, l2f, (has_name, has_cue))
        if errs:
            n_mis += 1
            if len(examples) < 20:
                examples.append((r.get("id"), errs[0]))
    print(json.dumps({"rows_checked": len(rows), "mismatches": n_mis,
                      "families": dict(fam)}, indent=1))
    for i, e in enumerate(examples[:20]):
        print("MISS", i, e)
    return 0 if n_mis == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
