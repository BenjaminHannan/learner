"""Shared helpers for the COVERAGE panel dimension. Pure python, read-only on repo and data.
Run everything with:  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<wt/lt> python3 -B <script>.py
"""
import json, os, re, itertools
from collections import Counter, defaultdict

S = "/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad"
ROWS = S + "/lt2/rows"
OUT = S + "/panel/coverage"
REPO = S + "/wt/lt"

EVAL = {  # name -> path
    "logic_gate": ROWS + "/eval/logic_gate.jsonl",
    "logic_dev": ROWS + "/eval/logic_dev.jsonl",
    "logic_test_sampler": ROWS + "/eval/logic_test_sampler.jsonl",
    "logic_test_deeper": ROWS + "/eval/logic_test_deeper.jsonl",
    "placebo_dev": ROWS + "/eval/placebo_dev.jsonl",
    "placebo_test_wording": ROWS + "/eval/placebo_test_wording.jsonl",
}
TRAIN = {"logic_train": ROWS + "/logic_train.jsonl", "placebo_train": ROWS + "/placebo_train.jsonl"}


def read_jsonl(path, limit=None):
    out = []
    with open(path) as f:
        for i, l in enumerate(f):
            if limit is not None and i >= limit:
                break
            out.append(json.loads(l))
    return out


def stream_jsonl(path):
    with open(path) as f:
        for l in f:
            yield json.loads(l)


SUFFIX_RE = re.compile(r"\s*\(([a-z]+)/([a-z]+)/([a-z]+)\)\s*$")
SENT_RE = re.compile(r"(?<=[.?])\s+")


def split_prompt(prompt):
    """-> (body, options tuple in prompt order)."""
    m = SUFFIX_RE.search(prompt)
    if not m:
        return prompt, ()
    return prompt[:m.start()], m.groups()


def sentences(body):
    return SENT_RE.split(body.strip())


def sentence_spans(body):
    """list of (start, end, text) char spans of sentences within body."""
    spans, pos = [], 0
    for s in sentences(body):
        a = body.index(s, pos)
        spans.append((a, a + len(s), s))
        pos = a + len(s)
    return spans


WORD_RE = re.compile(r"[A-Za-z]+")


def words(text):
    return WORD_RE.findall(text)


def kind_of_tid(t):
    return t.split(":")[0]


def parse_lit(s):
    """'~pred(ent)' or 'pred(ent)' -> (neg, pred, ent)"""
    s = s.strip()
    neg = s.startswith("~")
    if neg:
        s = s[1:]
    m = re.fullmatch(r"(\w+)\((\w+)\)", s)
    return neg, m.group(1), m.group(2)


def prog_items(ctx):
    """ctx string -> list of ('F', (neg,pred,ent)) or ('R', raw)"""
    out = []
    for it in ctx.split("; "):
        if it.startswith("F "):
            out.append(("F", parse_lit(it[2:])))
        else:
            out.append(("R", it))
    return out


# ---------------------------------------------------------------------------------------------------------------
# Row structure: map program items to rendered sentences (read-only imports of the repo's checker / templates).
import importlib.util, sys
sys.dont_write_bytecode = True


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


ck = _load("lg_checker", REPO + "/logicgen/checker.py")
TP = _load("lg_templates", REPO + "/logicgen/templates.py")
LEX = _load("lg_lexicon", REPO + "/logicgen/lexicon.py")

NEG_CUES = ("not", "never", "isn't", "non-")


def word_positions(text, word, ignorecase=True):
    flags = re.I if ignorecase else 0
    return [m.start() for m in re.finditer(r"(?<![A-Za-z])" + re.escape(word) + r"(?![A-Za-z])", text, flags)]


def parse_row(r):
    """Structure of one row. Returns dict:
      body, opts, spans [(a,b,text)], tids, kinds, facts, rules, query, fact_sent {fact literal: sentence idx},
      rule_sent {rule idx: sentence idx}, qi (query sentence idx), ok flag.
    Fact sentences are matched by (role FP/FN, entity word, predicate word); rule sentences by (rule kind, predicate set, entity)."""
    m = r["meta"]
    body, opts = split_prompt(r["prompt"])
    spans = sentence_spans(body)
    tids = m["template_ids"]
    kinds = [kind_of_tid(t) for t in tids]
    facts, rules, query = ck.parse_program(m["program"])
    ok = len(spans) == len(tids)
    fact_sent, rule_sent = {}, {}
    used = set()
    if ok:
        for f in facts:
            neg, pred, ent = f
            cands = [i for i, (a, b, t) in enumerate(spans)
                     if kinds[i] == ("FN" if neg else "FP") and word_positions(t, ent) and word_positions(t, pred) and i not in used]
            if len(cands) == 1:
                fact_sent[f] = cands[0]; used.add(cands[0])
            else:
                ok = False
        for ri, ru in enumerate(rules):
            k = TP.rule_kind(ru)
            preds = {p for _, p in ru.lhs} | {ru.rhs[1]}
            cands = [i for i, (a, b, t) in enumerate(spans)
                     if kinds[i] == k and i not in used and all(word_positions(t, p) for p in preds)
                     and (not ru.ent or word_positions(t, ru.ent))]
            if len(cands) >= 1:
                rule_sent[ri] = cands[0]; used.add(cands[0])
            else:
                ok = False
    return dict(body=body, opts=opts, spans=spans, tids=tids, kinds=kinds, facts=facts, rules=rules, query=query,
                fact_sent=fact_sent, rule_sent=rule_sent, qi=len(spans) - 1, ok=ok)
