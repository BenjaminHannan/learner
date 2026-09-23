"""Exp 238 steps 1b/3/4: template the harvested replies, collect tricky renders,
and grade every item.

GRADING IS BY CLAUDE (Opus 5.5), NOT BY A MODEL OR A HUMAN PANEL. I read every
distinct template family and the probe transcripts, and wrote down my
copy-editor judgments as the rules below (one rule per bug class, each with its
correction). The script applies those judgments to every string so the counts
are reproducible. 'grammatical' = a careful copy-editor would accept the
sentence as correct English (spelling, capitals, agreement, punctuation,
complete sentences). 'natural' = also sounds like something a fluent person
would say in chat. A factual/meaning error (e.g. wrong referent) is recorded
as a separate 'meaning' flag and does not lower the grammar rate.

Inputs : harvest.jsonl, probes/out-*.txt, probes/outb-*.txt, codetemplates.jsonl
Outputs: templates.jsonl, renders.jsonl, grades.jsonl, summary238.json
"""
import json, re, collections, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "artifacts" / "claude-grammar238-20260922"

# ------------------------------------------------------------ templating
FIXED = set("""I I'm I'll I've I'd You You're Your Yes No Not OK Okay Hi Hello Hey Saved Updated
Forgotten Nothing Nobody None Please Sorry Thanks Thank Was Who What Where When Why How Which Is Are Do
Did Does Could Can Tell Teach Ask That This These Those The A An It It's My We Just Right Web Only
Every Ben Premonition Cancelled Undo THINKING SLEEP WORK LISTENING Here Also Ctrl-D FAIL Agent
Got Sure Good Great Fine Let Maybe Anything Everything Someone Nothing Right Now""".split())
OUT_OF_SCOPE = re.compile(r"talker|smolear|ears1|ears2|cardfold|fairsmol|demo126")
RE_NUM = re.compile(r"\b\d+(?:[.,]\d+)?\b")
RE_NAME = re.compile(r"\b[A-Z][\w'-]*(?:\s+(?:[A-Z][\w-]*|of|the|de|van|von|and)){0,5}")


def templatize(s: str) -> str:
    t = RE_NUM.sub("{N}", s)

    def nm(m):
        words = m.group(0).split()
        if all(w.strip("'").replace("'s", "") in FIXED for w in words):
            return m.group(0)
        # keep a leading fixed word ("Saved", "Yes") outside the slot
        lead = []
        while words and words[0].replace("'s", "") in FIXED:
            lead.append(words.pop(0))
        while words and words[-1] in ("of", "the", "and", "de", "van", "von"):
            words.pop()
        tail = m.group(0)[len(" ".join(lead + words)):] if False else ""
        body = " ".join(words)
        poss = "'s" if body.endswith("'s") else ""
        rest = m.group(0)[m.group(0).find(body) + len(body):] if body else ""
        return " ".join(lead + (["{X}" + poss] if body else [])) + rest
    t = RE_NAME.sub(nm, t)
    # values after ' is ' that are lower-case words (job, pet, literal values)
    t = re.sub(r"(?<=\bis )(?!\{)(?:an? )?[a-z][\w-]*(?:\s[a-z][\w-]*)?(?=[.,)]|$)", "{v}", t)
    t = re.sub(r"\{X\}(?:,? \{X\})+(?: and \{X\})?", "{LIST}", t)
    t = re.sub(r"\{X\} and \{X\}", "{LIST}", t)
    t = re.sub(r"(?<='s )[a-z_ ]+?(?= is | as |, which)", "{R}", t)
    return t


# ------------------------------------------------------------ grading rules
# Each rule: (class, test(reply)->bool, grammatical_effect, natural_effect, fix(reply)->str, where)
PLURAL_RELS = r"(?:sisters|brothers|friends|children|hobbies|cousins|bosses|pets|parents|sons|daughters|languages)"

RULES = [
 ("EMPTY_LIST", lambda s: bool(re.search(r": \.|: \)|:\s*$", s)), False, False,
  lambda s: re.sub(r"I know 0 people: \.", "I don't know anyone yet.", s),
  "scripts/fable_self99.py:417-425 (people() join, no empty case)"),
 ("NUMBER_AGREEMENT", lambda s: bool(re.search(
     r"\b(?:0|[2-9]|\d{2,}) (?:web row|fact|person|time|turn|question|correction)\b(?!s)|\b1 (?:facts|people|web rows|times|turns|questions)\b|\bknow 0 people\b", s)),
  False, False,
  lambda s: re.sub(r"\b1 facts\b", "1 fact", re.sub(r"\b1 people\b", "1 person", re.sub(r"\b0 web row\b", "no web rows", s))),
  "scripts/fable_self99.py:421,425 (count words not inflected)"),
 ("VALUE_LIST_AGREEMENT", lambda s: bool(re.search(
     r"'s [a-z]+ is [A-Z]\w+(?:, [A-Z]\w+)*(?:,)? and [A-Z]\w+\.|\bYour [a-z]+ is [A-Z]\w+(?:, [A-Z]\w+)* and [A-Z]\w+\.|I have [A-Z]\w+(?:, [A-Z]\w+)*,? and [A-Z]\w+ as [^.]+'s [a-z]+\.", s)),
  False, False,
  lambda s: s, "scripts/fable_fix221_tableask.py:379 / base multi ask render / scripts/fable_fix154d_yesno.py:161 (singular relation + list value)"),
 ("DECLINE_SPLICE", lambda s: "I didn't understand that, I don't know" in s, False, False,
  lambda s: "Sorry, I didn't understand that. Could you say it another way?",
  "scripts/fable_loop138_agent.py:92 (+ fable_self105.py:64 prefix)"),
 ("LOWERCASE_START", lambda s: bool(re.match(r"^[a-z]", s.strip())) or bool(re.search(r"[.!?] [a-z]", s)),
  False, False, lambda s: s[:1].upper() + s[1:],
  "scripts/fable_fix221_tableask.py:397 ('Your' only when first) / fable_fix137d_frame.py:71 echo"),
 ("LOWERCASE_NAME_ECHO", lambda s: bool(re.search(r"(?:^|: )[a-z]+'s (?:sister|brother|mother|father|boss|friend|wife|husband|son|daughter|cousin|manager|spouse) is [a-z]+\.", s)),
  False, True, lambda s: s, "scripts/fable_notebook_contract.py:349 / FakeMouth (fable_agent_loop.py:166) echo stored case"),
 ("SAY_FRAGMENT", lambda s: s.startswith("my name.") or bool(re.match(r"^[a-z][^.]*\. \(I'm treating", s)), False, False,
  lambda s: "Your name is Ren." , "scripts/fable_fix137d_frame.py:71 (echo of remainder after 'Say')"),
 ("PLACEHOLDER_LEAK", lambda s: bool(re.search(r"turn \?|\{[a-z_]+\}", s)), False, False,
  lambda s: s.replace(" in turn ?", ""), "scripts/fable_self99.py:469-470 (turn index missing)"),
 ("RAW_RELATION", lambda s: bool(re.search(r"[a-z]_[a-z]", s)) and "pick <" not in s, False, False,
  lambda s: re.sub(r"([a-z])_([a-z])", r"\1 \2", s), "relation key shown raw (see row)"),
 ("PLURAL_NAME_POSSESSIVE", lambda s: bool(re.search(r"\b(?:[A-Z]\w+ )?[A-Z]?\w*(?:Books|Stars|Mirrors|Feasts|Maps|Bells|Melodies|Industries|Games|Records|Airlines|Studios|Brothers|Systems|Works|Labs|Masters|Kids|Gods|Covenants|Championships|Beatles|Netherlands|Stones|Philippines|States|Islands|Olympics|Services|Sounds)'s\b", s)),
  False, False, lambda s: re.sub(r"(s)'s\b", r"\1'", s),
  "scripts/claude_loop229_agent.py:445 / fable_notebook_contract.py:349 (always appends 's)"),
 ("DOUBLE_TERMINAL_PUNCT", lambda s: bool(re.search(r"\.\"\.|\?\"\?|\.\.(?!\.)|\w\?\.|\w\?\?\.", s)), False, True,
  lambda s: re.sub(r"\?\??\.$", ".", re.sub(r"\.\.(?=\s|$)", ".", s.replace('.".', '."'))), "value ending in an abbreviation + template period (contract.py:77 'Saved: {text}.'); scripts/fable_agent_loop.py:139 / fable_decline224.py:70 ('like \"...\".')"),
 ("QUESTION_NO_QMARK", lambda s: bool(re.search(r"Could you say it another way, like \"[^\"]+\"$", s)), False, True,
  lambda s: s + "?", "scripts/fable_loop188_agent.py:86"),
 ("GARBLED_READBACK", lambda s: "I read it as" in s and re.search(r"is [A-Z][\w ]+ was\b|\bin \d{4}'s", s) is not None, False, False,
  lambda s: "I didn't save that. Could you say it like \"Juniper Lane Books's founding year is 1987.\"?",
  "scripts/claude_loop229_agent.py:216-243 (echoes a wrong parse)"),
 ("MISSING_ARTICLE_THE", lambda s: bool(re.search(r"(?:^|: |\bis |\bof |\bas |, )(?:United States|United Kingdom|Netherlands|Philippines|Czech Republic|People's Republic|Soviet Union|European Union|Bahamas|Maldives|Gambia)\b", s)), False, True,
  lambda s: re.sub(r"(^|: |\bis |\bof |\bas |, )(United States|United Kingdom|Netherlands|Philippines|Czech|People's|Soviet|European|Bahamas|Maldives|Gambia)", r"\1the \2", s),
  "country/organisation name printed without 'the' (value copied verbatim; notebook_contract.py:349 / FakeMouth)"),
 ("BAD_RELATION_PHRASE", lambda s: bool(re.search(r"founded by's|founded by is|position played on team speciality|languages spoken written or signed|religion or worldview|never.taught.rel|(?:director|head coach|origianl broadcaster|original broadcaster|chairperson|mayor) of [^.]*'s officeholder|located in the administrative|'s [a-z ]+ by's|'s occupation's sport", s)), False, False,
  lambda s: s, "relation label that is not a noun phrase printed as one (FakeMouth fable_agent_loop.py:166-168; contract.py:349)"),
 ("SPELLING", lambda s: bool(re.search(r"origianl|univeristy|recieve|seperate", s)), False, True,
  lambda s: s.replace("origianl", "original").replace("univeristy", "university"), "misspelled relation label copied from bench data (fable_bench92_english_arm.py:65 / bench73:88)"),
]

UNNATURAL = [
 ("STACKED_POSSESSIVE", lambda s: len(re.findall(r"(?<!People)'s ", s)) >= 2 and "Updated:" not in s and "what you've" not in s,
  "possessive chain (X's boss's city) instead of a verb", "FakeMouth fable_agent_loop.py:166-168"),
 ("RELATION_NOT_VERB", lambda s: bool(re.search(r"'s (?:city|employer|place of birth|language|owner|country of citizenship|founding year|job|age|birthday) is ", s)),
  "states the stored key ('X's city is Y') where people use a verb ('X lives in Y')", "FakeMouth fable_agent_loop.py:166-168 / fable_notebook_contract.py:349"),
 ("ANYONE_CALLED_THING", lambda s: bool(re.search(r"anyone called (?:Rome|Oslo|Juniper|[A-Z]\w+ (?:Books|Press)|Norland|Ashford)", s)),
  "'anyone called' for a place or company", "scripts/fable_fix221_tableask.py:411 / fable_notebook_contract.py:81"),
 ("BARE_NAME_LIST", lambda s: bool(re.search(r"people: [A-Z][\w ]*, [A-Z]", s)) and " and " not in s.split("people:")[-1],
  "list without 'and'", "scripts/fable_self99.py:417"),
 ("ROBOTIC_DECLINE", lambda s: "I do not know that from what you taught me. I have no record of it, so I will not guess." in s,
  "stacked, formal refusal for small talk / unparsed input", "scripts/fable_self105.py:64 + fable_loop138_agent.py:92"),
 ("WORKED_BACKWARDS_TAG", lambda s: "(worked out backwards)" in s, "internal label shown to the user", "scripts/fable_fix221_tableask.py:69"),
 ("PRETEND_PAREN", lambda s: "(I'm treating that as pretend" in s, "parenthetical meta-note after an echo", "scripts/fable_fix137d_frame.py:71"),
 ("NO_ARTICLE_JOB", lambda s: bool(re.search(r"'s job is [a-z]", s)), "'job is engineer' (a person says 'is an engineer')", "FakeMouth"),
 ("COLON_LABEL", lambda s: bool(re.match(r"^(Forgotten|I forgot): ", s)), "status label fragment", "scripts/fable_decline224.py:229 / fable_loop154b_agent.py:199"),
 ("TEACH_ME_LIKE", lambda s: s.startswith("Hi! Teach me like"), "'Teach me like \"...\"' (say 'You can teach me by saying ...')", "scripts/fable_fix156b_smalltalk.py:53"),
 ("DOUBLE_DASH", lambda s: " -- " in s, "'--' instead of a dash", "scripts/fable_screen148_mixin.py:51,53 / fable_loop102_agent.py:72"),
]

MEANING = [
 ("WRONG_REFERENT_AGE", lambda s: s.startswith("You never taught me their age"), "age/birthday question about 'you'/'my' answered with 'their age'", "scripts/fable_fix168_ground.py:66"),
 ("OFF_TOPIC_NO_OPINIONS", lambda s: s.strip() == "I have no opinions.", "'Who lives in X?' answered 'I have no opinions.'", "scripts/fable_fix168_ground.py:59 (route in 138i)"),
]


def grade(s: str):
    s = s.strip()
    classes, fix = [], s
    gram, nat = True, True
    for cls, test, g_ok, n_ok, fx, where in RULES:
        try:
            hit = test(s)
        except Exception:
            hit = False
        if hit:
            classes.append(cls)
            gram = gram and g_ok
            nat = nat and n_ok
            fix = fx(fix)
    for cls, test, why, where in UNNATURAL:
        if test(s):
            classes.append(cls)
            nat = False
    meaning = [cls for cls, test, why, where in MEANING if test(s)]
    return {"grammatical": gram, "natural": nat and gram, "classes": classes,
            "meaning": meaning, "corrected": correct(s, classes, fix)}


def correct(s, classes, fix):
    """One-line corrected version (my wording)."""
    c = fix
    if "ROBOTIC_DECLINE" in classes or "DECLINE_SPLICE" in classes:
        return "Sorry, I didn't understand that. Could you say it another way?"
    m = re.match(r"^(Saved: |Yes, |No, )?(.+?)'s city is (.+?)\.$", c)
    if m and "RELATION_NOT_VERB" in classes and "'s " not in m.group(2):
        pre = {"Saved: ": "Got it: ", "Yes, ": "Yes, ", "No, ": "No, "}.get(m.group(1) or "", "")
        return f"{pre}{m.group(2)} lives in {m.group(3)}."
    m = re.match(r"^(Saved: )?(.+?)'s employer is (.+?)\.$", c)
    if m:
        return f"{'Got it: ' if m.group(1) else ''}{m.group(2)} works at {m.group(3)}."
    m = re.match(r"^(Saved: )?(.+?)(?:'s|') owner is (.+?)\.$", c)
    if m:
        return f"{'Got it: ' if m.group(1) else ''}{m.group(3)} owns {m.group(2)}."
    m = re.match(r"^(Saved: |I have )?([a-z][a-z ]*?) of (.+?)(?:'s|') officeholder (is|as) (.+?)(\..*)$", c)
    if m:
        pre = m.group(1) or ""
        role = m.group(2).replace("origianl", "original")
        if pre == "I have ":
            return f"I have the {role} of {m.group(3)} as {m.group(5)}{m.group(6)}"
        return f"{'Got it: ' if pre else ''}The {role} of {m.group(3)} is {m.group(5)}{m.group(6)}"
    m = re.match(r"^(Saved: )?(.+?)'s language is (.+?)\.$", c)
    if m:
        return f"{'Got it: ' if m.group(1) else ''}{m.group(2)} speaks {m.group(3)}."
    m = re.match(r"^(Saved: )?(.+?)'s place of birth is (.+?)\.$", c)
    if m:
        return f"{'Got it: ' if m.group(1) else ''}{m.group(2)} was born in {m.group(3)}."
    m = re.match(r"^(.+?)'s (\w+)'s city is (.+?)\.$", c)
    if m:
        return f"{m.group(1)}'s {m.group(2)} lives in {m.group(3)}."
    m = re.match(r"^(Saved: )?(.+?)'s job is (an? )?([a-z]+)\.$", c)
    if m:
        art = "an" if m.group(4)[0] in "aeiou" else "a"
        return f"{'Got it: ' if m.group(1) else ''}{m.group(2)} is {art} {m.group(4)}."
    m = re.match(r"^(.+?)'s (\w+) is (.+?)(?:,| and) (.+)\.$", c)
    if m and "VALUE_LIST_AGREEMENT" in classes:
        vals = re.split(r", | and ", m.group(3) + ", " + m.group(4))
        vals = [v for v in vals if v]
        joined = ", ".join(vals[:-1]) + " and " + vals[-1]
        rel = m.group(2)
        return f"{m.group(1)}'s {rel}s are {joined}." if not rel.endswith("s") else f"{m.group(1)}'s {rel} are {joined}."
    m = re.match(r"^Your (\w+) is (.+) and (.+)\.$", c)
    if m and "VALUE_LIST_AGREEMENT" in classes:
        return f"Your {m.group(1)}s are {m.group(2)} and {m.group(3)}."
    if "LOWERCASE_NAME_ECHO" in classes:
        c = re.sub(r"\b([a-z])([a-z]+)(?='s |\.$)", lambda k: k.group(1).upper() + k.group(2), c)
        c = c[:1].upper() + c[1:]
    m = re.match(r"^Not that I know of\. I have (.+) as (.+)'s (\w+)\.$", c)
    if m:
        return f"Not that I know of. {m.group(2)}'s {m.group(3)}s are {m.group(1)}."
    m = re.match(r"^I know (\d+) facts you taught me\. I also hold (\d+) web rows?, which I do not believe\.$", c)
    if m:
        n = int(m.group(1))
        f = "no facts" if n == 0 else ("1 fact" if n == 1 else f"{n} facts")
        return f"You've taught me {f}." + ("" if m.group(2) == "0" else f" I'm also holding {m.group(2)} web note(s) I don't trust.")
    m = re.match(r"^I know (\d+) people: (.*)\.$", c)
    if m:
        names = [x for x in m.group(2).split(", ") if x]
        if not names:
            return "I don't know anyone yet."
        if len(names) == 1:
            return f"I know one person: {names[0]}."
        return f"I know {len(names)} people: {', '.join(names[:-1])} and {names[-1]}."
    if "WRONG_REFERENT_AGE" in [x for x in classes] or s.startswith("You never taught me their age"):
        return "I don't have an age. I'm a program."
    if "SAY_FRAGMENT" in classes:
        return "Your name is Ren. (Just saying it — I won't save anything.)"
    if "ANYONE_CALLED_THING" in classes:
        return re.sub(r"I don't know anyone called (.+)\.", r"I don't know anything about \1 yet.", c)
    if "WORKED_BACKWARDS_TAG" in classes:
        c = c.replace(" (worked out backwards)", "")
    if "TEACH_ME_LIKE" in classes:
        return "Hi! You can teach me facts like \"Tom's boss is Ann.\" and ask \"Who is Tom's boss?\""
    if "DOUBLE_DASH" in classes:
        c = c.replace(" -- ", " — ")
    if "PRETEND_PAREN" in classes:
        c = c.replace(" (I'm treating that as pretend, so I won't save it.)", " (Just pretend — I won't save it.)")
    return c


def main():
    harvest = [json.loads(l) for l in open(D / "harvest.jsonl")]
    dropped = [h for h in harvest if h["sources"] and all(OUT_OF_SCOPE.search(x) for x in h["sources"])]
    harvest = [h for h in harvest if not (h["sources"] and all(OUT_OF_SCOPE.search(x) for x in h["sources"]))]
    print("out-of-scope (talker/ears/smol) strings dropped:", len(dropped), sum(h["count"] for h in dropped))
    # ---- templates
    fam = collections.OrderedDict()
    for h in harvest:
        t = templatize(h["reply"])
        f = fam.setdefault(t, {"template": t, "count": 0, "n_strings": 0, "examples": []})
        f["count"] += h["count"]
        f["n_strings"] += 1
        if len(f["examples"]) < 3:
            f["examples"].append(h["reply"])
    with open(D / "templates.jsonl", "w") as f:
        for t in sorted(fam.values(), key=lambda x: -x["count"]):
            f.write(json.dumps(t) + "\n")
    # ---- renders (tricky fillers, real agent output from the probe runs)
    renders = []
    for p in sorted(glob.glob(str(D / "probes" / "out*.txt"))):
        agent = Path(p).stem.split("-", 1)[1]
        probe = "probe238b" if Path(p).stem.startswith("outb") else "probe238"
        for line in open(p):
            m = re.match(r"^(\d\d) (.+?) -> (.+)$", line.rstrip("\n"))
            if not m:
                continue
            try:
                user = eval(m.group(2)); rep = eval(m.group(3))
            except Exception:
                continue
            renders.append({"agent": agent, "probe": probe, "dialog": int(m.group(1)), "user": user, "reply": rep})
    with open(D / "renders.jsonl", "w") as f:
        for r in renders:
            f.write(json.dumps(r) + "\n")
    # ---- grades
    grades = []
    for h in harvest:
        grades.append({"set": "real", "text": h["reply"], "weight": h["count"],
                       "conv_weight": h["count"] - h.get("bench_count", 0),
                       "scope_weight": h.get("scope_count", 0),
                       "scope_conv_weight": h.get("scope_count", 0) - h.get("scope_bench_count", 0),
                       **grade(h["reply"])})
    for t in fam.values():
        g = grade(t["examples"][0])
        grades.append({"set": "template", "text": t["template"], "example": t["examples"][0], "weight": t["count"], **g})
    seen = set()
    for r in renders:
        key = r["reply"]
        if key in seen:
            continue
        seen.add(key)
        grades.append({"set": "render", "text": key, "agent": r["agent"], "user": r["user"], "weight": 1, **grade(key)})
    with open(D / "grades.jsonl", "w") as f:
        for g in grades:
            f.write(json.dumps(g) + "\n")
    # ---- rates
    out = {}
    for st in ("real", "template", "render"):
        rows = [g for g in grades if g["set"] == st]
        W = sum(g["weight"] for g in rows) if st == "real" else len(rows)
        wt = (lambda g: g["weight"]) if st == "real" else (lambda g: 1)
        out[st] = {"n_items": len(rows), "denominator": W,
                   "grammatical": sum(wt(g) for g in rows if g["grammatical"]),
                   "natural": sum(wt(g) for g in rows if g["natural"]),
                   "meaning_errors": sum(wt(g) for g in rows if g["meaning"])}
    rows = [g for g in grades if g["set"] == "real"]
    W = sum(g["conv_weight"] for g in rows)
    out["real_conversation_only"] = {"n_items": sum(1 for g in rows if g["conv_weight"] > 0), "denominator": W,
        "grammatical": sum(g["conv_weight"] for g in rows if g["grammatical"]),
        "natural": sum(g["conv_weight"] for g in rows if g["natural"]),
        "meaning_errors": sum(g["conv_weight"] for g in rows if g["meaning"])}
    for name, key in (("real_scope_all", "scope_weight"), ("real_scope_conversation", "scope_conv_weight")):
        W = sum(g[key] for g in rows)
        out[name] = {"n_items": sum(1 for g in rows if g[key] > 0), "denominator": W,
            "grammatical": sum(g[key] for g in rows if g["grammatical"]),
            "natural": sum(g[key] for g in rows if g["natural"]),
            "meaning_errors": sum(g[key] for g in rows if g["meaning"])}
    cls = collections.defaultdict(lambda: {"scope_conv_weight": 0, "conv_weight": 0, "real_weight": 0, "real_unique": 0, "templates": 0, "renders": 0, "examples": []})
    for g in grades:
        for c in g["classes"] + g["meaning"]:
            k = cls[c]
            if g["set"] == "real":
                k["real_weight"] += g["weight"]; k["real_unique"] += 1; k["conv_weight"] += g["conv_weight"]; k["scope_conv_weight"] += g["scope_conv_weight"]
            elif g["set"] == "template":
                k["templates"] += 1
            else:
                k["renders"] += 1
            if len(k["examples"]) < 2 and g["set"] in ("real", "render") and g["text"] not in [e[0] for e in k["examples"]]:
                k["examples"].append((g["text"], g["corrected"]))
    out["classes"] = cls
    json.dump(out, open(D / "summary238.json", "w"), indent=1)
    for st in ("real", "real_conversation_only", "real_scope_all", "real_scope_conversation", "template", "render"):
        o = out[st]
        print(st, o, "gram=%.4f nat=%.4f" % (o["grammatical"] / o["denominator"], o["natural"] / o["denominator"]))
    for c, k in sorted(cls.items(), key=lambda kv: -kv[1]["scope_conv_weight"]):
        print(f"{c:26s} scopeConvW={k['scope_conv_weight']:6d} convW={k['conv_weight']:6d} realW={k['real_weight']:7d} realU={k['real_unique']:5d} tmpl={k['templates']:5d} rend={k['renders']:4d}")


if __name__ == "__main__":
    main()
