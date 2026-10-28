"""Prompt builders and reply parsers, ported from sleepb.py. "Sam" is a parameter (`who`, default "Ben").

Every builder takes the Renderer R (profile.Renderer). The wording is sleepb's, word for word, apart from the name.
"""
from __future__ import annotations

import json
import re
from typing import List, Optional, Tuple

SYS = "Answer with just the name."          # sleepb's closed-book / open-book answer prompt
K = 4                                         # cards per item at work scale 1
STUDY = "You are a careful assistant that studies facts."
EXTRACT = "You extract facts from chat messages."


def plain_prompt(R, q: str) -> str:
    return R.render(SYS, q)


def ctx_prompt(R, ctx: str, q: str, who: str = "Ben") -> str:
    head = "Messages from %s's chat history, labelled by day (if they disagree, the latest day is true):" % who
    return R.render(SYS, "%s\n%s\n\nQuestion: %s" % (head, ctx, q))


def diary_prompt(R, diary, q: str, upto=None) -> str:
    """Open-book prompt: BM25 notes from the diary (days <= upto) then the question."""
    return R.render(SYS, "Notes from earlier chats:\n" + diary.label(diary.search(q, 8, upto)) + "\n\nQuestion: " + q)


def tag_prompt(R, text: str, who: str = "Ben", think: bool = False) -> str:
    u = ("Message from %s:\n\"%s\"\n\nList the facts this message states about specific named people, places, organisations or things, "
         "and about %s himself (his plans, school, work, family, likes; write \"%s\" for I, me and my), as "
         "short subject-relation-object triples. Use the names exactly as written in the message. At most 5. Reply with only JSON: "
         "[{\"subject\": \"...\", \"relation\": \"...\", \"object\": \"...\"}]. If there are none, reply []." % (who, text, who, who))
    return R.render_think(EXTRACT, u) if think else R.render(EXTRACT, u)


def names_prompt(R, text: str, a: str, b: str, who: str = "Ben", think: bool = False) -> str:
    u = ("Message from %s:\n\"%s\"\n\nDoes this message say how \"%s\" and \"%s\" are related? If yes, reply with only the relation in 1 to 4 words "
         "(for example: works at, lives in, is the mentor of, owns the boat). If not, reply only: no" % (who, text, a, b))
    return R.render_think(EXTRACT, u) if think else R.render(EXTRACT, u)


def nrem_prompt(R, ctx: str, subj: str, obj: str, k: int = K, who: str = "Ben") -> str:
    u = ("Messages %s sent in chat, newest first, labelled by day. If they disagree, the newest message is true.\n%s\n\n"
         "Focus on the fact linking \"%s\" and \"%s\". Write %d paraphrases of the CURRENT fact (short standalone sentences, "
         "different wording, naming both) and %d question-answer pairs about it. Cover both directions: some questions should ask about one "
         "name, some about the other. Each answer must be a single name from the fact. Reply with only JSON of the form "
         "{\"paraphrases\": [\"...\"], \"qa\": [{\"q\": \"...\", \"a\": \"...\"}]}" % (who, ctx, subj, obj, k, k))
    return R.render(STUDY, u)


def chain_prompt(R, fx: str, fy: str) -> str:
    u = ("Two facts:\n- %s\n- %s\n\nWrite one question that can only be answered by using both facts together, without naming the name the two "
         "facts share, and its answer, which must be a single name. Reply in exactly this form:\nQuestion: ...\nAnswer: ..." % (fx, fy))
    return R.render(STUDY, u)


def bridge_text(fx: str, fy: str, start: str, answer: str, mid: str) -> str:
    return ("Two facts:\n- %s\n- %s\n\nThe two facts share the name \"%s\". Write one question that names \"%s\", does not name \"%s\" or \"%s\", "
            "and can only be answered by using both facts together. Its answer must be \"%s\" (a single name)." % (fx, fy, mid, start, mid, answer, answer))


def bridge_prompt(R, fx, fy, start, answer, mid, think: bool = False, qonly: bool = False) -> str:
    """ab_ob_bridge's chain prompt. qonly: bridge_q_prompt (only the question; the answer is the given far end)."""
    tail = " Reply with only the question, on one line." if qonly else " Reply in exactly this form:\nQuestion: ...\nAnswer: ..."
    u = bridge_text(fx, fy, start, answer, mid) + tail
    return R.render_think(STUDY, u) if think else R.render(STUDY, u)


def gist_prompt(R, fx: str, nd: int, who: str = "Ben") -> str:
    u = ("Fact about %s's life: %s (it came up on %d different days).\n\nWrite one question about what %s usually does, where %s usually "
         "goes or who %s usually sees, which this fact answers as a habit, and its answer, a single name from the fact. Reply in exactly "
         "this form:\nQuestion: ...\nAnswer: ..." % (who, fx, nd, who, who, who))
    return R.render(STUDY, u)


REVIEW = "You review an assistant's mistakes and write short lessons."


def lesson_prompt(R, ctx: str, what: str, who: str = "Ben") -> str:
    """Post-mortem of one failure (lessons.py). New for the lessons stage (not from sleepb). `what` is lessons.KIND_WORDS[kind]."""
    u = ("Part of a chat between %s and his assistant Glim. Something went wrong here: %s.\n%s\n\n"
         "Write a short post-mortem. Reply with only JSON of the form {\"did\": \"what Glim did\", \"wrong\": \"what went wrong\", "
         "\"instead\": \"what Glim should do next time\", \"wrong_value\": \"the wrong thing Glim said, or empty\", "
         "\"q\": \"a question about what is right or what to do instead\", \"a\": \"its answer, 1 to 4 words copied exactly from the chat above\"}. "
         "Each of did, wrong and instead is one short sentence. If %s corrected Glim, the answer is what %s said is right." % (who, what, ctx, who, who))
    return R.render(REVIEW, u)


def note_qa_prompt(R, text: str, who: str = "Ben") -> str:
    """One quiz card for a saved note (recipe.note_qas). New with the notes quiz."""
    u = ("A note saved about %s:\n\"%s\"\n\nWrite one question that this note answers, and its answer: 1 to 4 words copied exactly from the note. "
         "The question must not contain the answer. Reply with only JSON: {\"q\": \"...\", \"a\": \"...\"}." % (who, text))
    return R.render(REVIEW, u)


# ---------------------------------------------------------------- parsers
def parse_lesson(txt: str) -> Optional[dict]:
    m = re.search(r"\{.*\}", str(txt or ""), re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    return d if isinstance(d, dict) else None

def parse_facts(txt: str):
    # the first complete JSON array wins: LFM3 often writes "[]" and then keeps going ("[]\n]", a ```json block, a note with
    # brackets), which a greedy "\[.*\]" turned into invalid JSON and counted as a parse failure
    dec = json.JSONDecoder()
    for m in re.finditer(r"\[", txt):
        try:
            v, _ = dec.raw_decode(txt, m.start())
        except ValueError:
            continue
        if isinstance(v, list) and all(isinstance(x, dict) for x in v):
            return list(v)
    out = []
    for o in re.findall(r"\{[^{}]*\}", txt):
        try:
            x = json.loads(o)
            if isinstance(x, dict):
                out.append(x)
        except Exception:
            pass
    return out or None  # None: nothing parseable; [] (a literal "[]") is a valid "no facts"


def parse_dream(txt: str) -> Tuple[List[str], List[Tuple[str, str]]]:
    paras, qas = [], []
    m = re.search(r"\{.*\}", txt, re.S)
    if m:
        try:
            d = json.loads(m.group(0))
            paras = [p for p in d.get("paraphrases", []) if isinstance(p, str)]
            qas = [(x.get("q"), x.get("a")) for x in d.get("qa", [])
                   if isinstance(x, dict) and isinstance(x.get("q"), str) and isinstance(x.get("a"), str)]
            return paras, qas
        except Exception:
            pass
    for line in txt.splitlines():
        line = line.strip().lstrip("-*0123456789. ").strip()
        mm = re.match(r"(?:Q:|Question:)\s*(.+?)\s*(?:\||A:|Answer:)\s*(.+)$", line)
        if mm:
            qas.append((mm.group(1), mm.group(2)))
    return paras, qas


def parse_qa1(txt: str) -> Optional[Tuple[str, str]]:
    m = re.search(r"Question:\s*(.+?)\s*[\r\n]+\s*Answer:\s*([^\r\n]+)", txt) or re.search(r"Question:\s*(.+?)\s*Answer:\s*(.+)$", txt, re.S)
    return (m.group(1).strip(), m.group(2).strip().rstrip(".")) if m else None


def parse_q1(txt: str, first_q: bool = False) -> Optional[str]:
    """A question-only reply -> the question (first non-empty line, label and quotes off); None if it is not a question."""
    lines = [x.strip() for x in str(txt or "").splitlines() if x.strip()]
    if not lines or re.match(r"answer\s*:", lines[0], re.I):
        return None
    qt = " \t\"'`\u201c\u201d\u2018\u2019"
    ln = re.sub(r"^(?:question|q)\s*:", "", lines[0].strip(qt), flags=re.I).strip(qt)
    if first_q and "?" in ln:
        ln = ln[:ln.index("?") + 1].strip(qt)
    return ln if ln.endswith("?") else None


def parse_rel(txt: str) -> Optional[str]:
    """names_prompt reply -> None for "no", else the relation (first line, at most 40 chars)."""
    lines = [x.strip() for x in str(txt or "").strip().splitlines() if x.strip()]
    if not lines or re.match(r"(?:no|none|nope)(?:$|[^\w\s])", lines[0].lower()):
        return None
    return re.sub(r"^yes\b[\s\W]*", "", lines[0], flags=re.I).strip(" \t\"'`\u201c\u201d\u2018\u2019.,;:!?-*()[]")[:40].strip()


NEG_RE = re.compile(r"(?:no|not|none|nothing|nope|unrelated)\b", re.I)


def parse_rel_neg(txt: str) -> Optional[str]:
    """parse_rel, plus a first line starting with the word no / not / none / nothing / nope / unrelated is "no" (the K2 quirk)."""
    lines = [x.strip() for x in str(txt or "").strip().splitlines() if x.strip()]
    return None if lines and NEG_RE.match(lines[0]) else parse_rel(txt)


def parse_scenes(txt: str, n: int = 2) -> List[str]:
    out = []
    for ln in txt.splitlines():
        m = re.match(r"^[\s*#>-]*(?:scene\s*)?\d+\s*[.):*-]+\s*(.+)$", ln, re.I)
        if m and m.group(1).strip(" *\"'"):
            out.append(m.group(1).strip(" *\"'"))
    return out[:n]


def strip_think(txt: str, close: str, end: str = "") -> Tuple[str, bool]:
    """A stage-1 reply (thinking, stopped at the close tag or the end of the turn) -> (thinking, whether the model closed the block)."""
    txt, closed = str(txt or "").strip(), False
    while True:
        if close and txt.endswith(close):
            closed, txt = True, txt[:-len(close)].rstrip()
        elif end and txt.endswith(end):
            txt = txt[:-len(end)].rstrip()
        else:
            break
    if close and close in txt:  # the model closed the block and kept writing: keep the thinking only
        txt, closed = txt.split(close, 1)[0].rstrip(), True
    return txt, closed


# ---------------------------------------------------------------- templated cards (Config.card_shape "templated12")
PREPS = {"at", "in", "on", "to", "for", "with", "by", "from", "of"}


def noun_rel(rel: str) -> Optional[str]:
    """The relation as a bare noun phrase ("is the mentor of" -> "mentor", "sister" -> "sister"); None for a verb phrase ("works at", "owns the boat")."""
    w = re.sub(r"\s+of$", "", re.sub(r"^(?:the|a|an)\s+", "", re.sub(r"^(?:is|are|was)\s+", "", rel.strip().lower()))).strip()
    ws = w.split()
    if not ws or len(ws) > 3 or ws[-1] in PREPS or {"the", "a", "an"} & set(ws[1:]):
        return None
    return w


def templated_cards(s: str, rel: str, o: str, note: str) -> Tuple[List[str], List[Tuple[str, str]]]:
    """Arm B of the card-shape experiment: ([raw note + 5 rewrites (3 forward, 2 reverse)], 6 Q&A (3 forward, 3 reverse)). No model."""
    n = noun_rel(rel)
    if n:
        paras = [note, "%s's %s is %s." % (s, n, o), "The %s of %s is %s." % (n, s, o), "For %s, the %s is %s." % (s, n, o),
                 "%s is the person whose %s is %s." % (s, n, o), "Whose %s is %s? It is %s's." % (n, o, s)]
        qas = [("What is %s's %s?" % (s, n), o), ("Tell me the %s of %s." % (n, s), o), ("Remind me of %s's %s." % (s, n), o),
               ("Whose %s is %s?" % (n, o), s), ("Who has %s as their %s?" % (o, n), s), ("%s is the %s of which person?" % (o, n), s)]
    else:   # verb relation ("works at"): same shape, worded around the verb
        r = rel.strip()
        paras = [note, "%s %s %s." % (s, r, o), "Fact: %s %s %s." % (s, r, o), "As far as I know, %s %s %s." % (s, r, o),
                 "%s is linked to %s: %s %s %s." % (o, s, s, r, o), "Who %s %s? It is %s." % (r, o, s)]
        qas = [("Complete the sentence: %s %s ..." % (s, r), o), ("Remind me what %s %s." % (s, r), o), ("What is it that %s %s?" % (s, r), o),
               ("Who %s %s?" % (r, o), s), ("Which person %s %s?" % (r, o), s), ("Tell me who %s %s." % (r, o), s)]
    return paras, qas
