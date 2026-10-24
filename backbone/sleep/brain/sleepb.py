"""Sleep-B (see backbone/sleep/brain/PREREG-sleepB.md). Arms: a0 (base), ad (base + diary search), ab (brain-like sleep),
af (flat sleep, AB's step counts), one-change ablations ab_norem / ab_noshy / ab_flatprio / ab_all, and the addendum-1 fixes
ab_ob (open-book rehearsal) / ab_klctx (read-the-notes KL leash), see PREREG-sleepB-addendum1.md. The new arms also save every
per-question row + p_first in each scoring mode and score the router R and the adapter-off diary reader (scores.router, scores.base_diary).
Full-rank arms, one change each from ab_ob: ab_ob_full (every LoRA-target Linear gets a trainable full-rank delta_w, LoRA frozen, lr
--full-lr) and ab_ob_merge (LoRA trains as in ab_ob; each night's SHY step folds it into a full-rank delta_w and resets it). delta_w is
added by a forward hook on the base Linear and switched off inside pm.disable_adapter(), so "base" stays the original pretrained model.

  python backbone/sleep/brain/sleepb.py --arm ab --week backbone/sleep/brain/data/week1.json --out out/sleepb/ab
  python backbone/sleep/brain/sleepb.py --arm af --week ... --out out/sleepb/af --schedule out/sleepb/ab/result_ab.json
  python backbone/sleep/brain/sleepb.py --arm ab --smoke --out /tmp/x      # CPU, tiny random qwen3_5, built-in 2-day fixture
  python backbone/sleep/brain/sleepb.py --selftest                         # SHY refactor + delta (full / merge) unit checks

Ground truth in the week file (items, mentions, class) is used ONLY for scoring and diagnostics, never by the sleeper.
Model roles: tagging, update detection, NREM dreaming and every verification run on the BASE model (adapter disabled);
morning probes, REM dreaming and all test scoring run on the CURRENT adapter.
Files: DIR/result_<arm>.json (final), DIR/result_<arm>.partial.json (rewritten after every night, removed at the end),
DIR/adapter, DIR/log_<arm>.txt. --schedule overrides the per-night step count of any trained arm with ab's realized steps.
Each night uses a fresh AdamW with one cosine schedule spanning all of that night's cycles; the LoRA itself is cumulative.
"""
import argparse
import contextlib
import itertools
import json
import math
import random
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
for _p in (HERE.parent, HERE.parent.parent):
    sys.path.insert(0, str(_p))
import facts as facts_mod  # noqa: E402
from sleep1 import ARC_SMOKE, SYS, Lang, generic_prompts, load_arc, parse_dream, score_arc  # noqa: E402
from train import LORA_TARGETS, load_model  # noqa: E402

K = 4
NREM_SHARE = [0.80, 0.65, 0.50, 0.35]
KINDS = ("forward", "reverse", "twohop", "changed", "routine")
NEW_ARMS = ("ab_ob", "ab_klctx", "ab_ob_full", "ab_ob_merge")
OB_ARMS = ("ab_ob", "ab_ob_full", "ab_ob_merge")  # open-book rehearsal (Brain.qa_ex)
DELTA_ARMS = ("ab_ob_full", "ab_ob_merge")
ARMS = ["a0", "ad", "ab", "af", "ab_norem", "ab_noshy", "ab_flatprio", "ab_all", *NEW_ARMS]
GENERIC = {"sam", "i", "me", "my", "we", "you", "he", "she", "they", "it", "user", "the user", "someone", "somebody"}
STOP = set("the a an of in is to and where who does what which for at on by with was are do did live lives name s".split())
IMP_RE = re.compile(r"remember|important|don'?t forget", re.I)
COR_RE = re.compile(r"\bactually\b|correction|no, it'?s", re.I)
CAP = re.compile(r"\b[A-Z][a-z]{3,}\b")
norm = facts_mod.norm


# ------------------------------------------------------------------ small helpers
def pat(s):
    return re.compile(r"(?<!\w)" + re.escape(s.lower()) + r"(?!\w)")


def tokens(s):
    return re.findall(r"[a-z0-9]+", s.lower().replace("\u2019", "'").replace("'s", ""))


def has_ans(target, ans):
    return target.lower() in ans.lower()


def acc(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def gt_match(s, o, pairs):  # lowercase substring match of an extracted (subject, object) against ground-truth name pairs
    s, o = s.lower(), o.lower()
    return any((a in s and b in o) or (a in o and b in s) for a, b in pairs)


# ------------------------------------------------------------------ week data
def smoke_week():
    """Tiny fixture in the week1.json schema: 2 days, 6 items (C2 x3 incl. a chain, C1, CH, RT). Template sentences."""
    items = [
        {"id": 0, "kind": "fact", "rel": "lives_in", "a": "Drovak", "b": "Kelmira", "class": "C2", "text": "Drovak lives in Kelmira.", "days": [1, 2], "names": ["Drovak", "Kelmira"]},
        {"id": 1, "kind": "fact", "rel": "mentor_of", "a": "Drovak", "b": "Gliker", "class": "C2", "text": "Drovak is the mentor of Gliker.", "days": [1, 2], "names": ["Drovak", "Gliker"]},
        {"id": 2, "kind": "fact", "rel": "works_at", "a": "Zelmir", "b": "Tavrix", "class": "C2", "text": "Zelmir works at Tavrix.", "days": [1, 2], "names": ["Zelmir", "Tavrix"]},
        {"id": 3, "kind": "fact", "rel": "sibling", "a": "Brokai", "b": "Fenlus", "class": "C1", "text": "Brokai and Fenlus are siblings.", "days": [1], "names": ["Brokai", "Fenlus"]},
        {"id": 4, "kind": "changing", "rel": "lives_in", "a": "Vrakol", "b": "Tremix", "old_b": "Skarum", "class": "CH", "text": "Vrakol lives in Tremix.", "days": [1, 2], "names": ["Vrakol", "Tremix"]},
        {"id": 5, "kind": "routine", "rel": "dinner", "a": "Kelvora", "b": "Zhoumira", "class": "RT", "text": "Sam has dinner with Kelvora at Zhoumira.", "days": [1, 2], "names": ["Kelvora", "Zhoumira"]}]
    plan = {1: [("ok so email Drovak, who lives in Kelmira, about friday", [0]), ("note that Drovak mentors Gliker these days", [1]),
                ("remember that Zelmir works at Tavrix", [2]), ("help me thank Brokai, the sibling of Fenlus", [3]),
                ("remember Vrakol lives in Skarum, send the parcel there", []), ("grabbing dinner with Kelvora at Zhoumira tonight", [5])],
            2: [("draft a note for Drovak in Kelmira please", [0]), ("lets visit Drovak and Gliker for the mentoring session", [1]),
                ("ask Zelmir at Tavrix for the invoice", [2]), ("actually Vrakol moved to Tremix, update the address", [4]),
                ("dinner with Kelvora at Zhoumira again, book a table", [5])]}
    diary = []
    for day, rows in plan.items():
        for k, (txt, men) in enumerate(rows):
            diary.append({"day": day, "session": k % 2, "turn": k, "role": "user", "text": txt, "mentions": men})
            diary.append({"day": day, "session": k % 2, "turn": k, "role": "assistant", "text": "Sure, here is a draft.", "mentions": []})
    tests = {"forward": [{"q": "Where is Drovak's home town?", "target": "Kelmira", "item": 0, "class": "C2"},
                         {"q": "Which company employs Zelmir?", "target": "Tavrix", "item": 2, "class": "C2"},
                         {"q": "Name the sibling of Brokai.", "target": "Fenlus", "item": 3, "class": "C1"}],
             "reverse": [{"q": "Who mentored Gliker?", "target": "Drovak", "item": 1, "class": "C2"},
                         {"q": "Who is employed by Tavrix?", "target": "Zelmir", "item": 2, "class": "C2"}],
             "twohop": [{"q": "In which place does the mentor of Gliker live?", "target": "Kelmira", "items": [1, 0]}],
             "changed": [{"q": "Where does Vrakol reside these days?", "target": "Tremix", "old": "Skarum", "item": 4}],
             "routine": [{"q": "Where does Sam usually eat dinner with Kelvora?", "target": "Zhoumira", "item": 5}]}
    return {"seed": 1, "user": "Sam", "items": items, "diary": diary, "tests": tests,
            "test_strings_norm": sorted({norm(t["q"]) for k in tests for t in tests[k]})}


def check_week(week):
    for k in ("items", "diary", "tests"):
        assert k in week, f"week file lacks '{k}'"
    for k in KINDS:
        assert k in week["tests"], f"week tests lack '{k}'"
    assert all(t["role"] in ("user", "assistant") and "day" in t and "text" in t for t in week["diary"]), "bad diary rows"
    assert all("class" in t for k in ("forward", "reverse") for t in week["tests"][k]), "forward/reverse tests need a class"
    assert all("old" in t for t in week["tests"]["changed"]) and all("items" in t for t in week["tests"]["twohop"]), "changed needs old, twohop needs items"
    assert all(k in g for g in week["items"] for k in ("id", "a", "b", "class")), "items need id, a, b, class"


class Diary:
    """User turns of the whole diary: word-boundary string lookup and pure-Python BM25. Callers filter by day."""

    def __init__(s, week):
        s.turns = [dict(t, i=i) for i, t in enumerate(x for x in week["diary"] if x["role"] == "user")]
        s.low = [t["text"].lower() for t in s.turns]
        s.occ_cache, s.tf, s.post, s.sc = {}, [], defaultdict(list), {}
        for i, t in enumerate(s.turns):
            c = Counter(w for w in tokens(t["text"]) if w not in STOP)
            s.tf.append(c)
            for w in c:
                s.post[w].append(i)
        s.dl = [sum(c.values()) for c in s.tf]
        s.avg = max(sum(s.dl) / max(len(s.dl), 1), 1e-9)

    def occurs(s, string):
        k = string.lower()
        if k not in s.occ_cache:
            p = pat(k)
            s.occ_cache[k] = frozenset(i for i, x in enumerate(s.low) if p.search(x))
        return s.occ_cache[k]

    def containing(s, a, b, upto=99):  # turn indices (chronological) of user turns up to day `upto` containing both strings
        return sorted(i for i in s.occurs(a) & s.occurs(b) if s.turns[i]["day"] <= upto)

    def label(s, idxs, maxc=500):
        return "\n".join(f"[Day {s.turns[i]['day']}] {s.turns[i]['text'][:maxc]}" for i in idxs)

    def search(s, q, k=8, upto=None):  # BM25 top-k user turns, returned chronologically; upto: only turns of days <= upto (n, df over those; cached)
        if upto is not None and (q, k, upto) in s.sc:
            return s.sc[(q, k, upto)]
        ok = (lambda i: True) if upto is None else (lambda i: s.turns[i]["day"] <= upto)  # noqa: E731
        n, scores = sum(1 for i in range(len(s.turns)) if ok(i)), defaultdict(float)
        for w in set(tokens(q)) - STOP:
            ps = [i for i in s.post.get(w, ()) if ok(i)]
            df = len(ps)
            if not df:
                continue
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            for i in ps:
                tf = s.tf[i][w]
                scores[i] += idf * tf * 2.5 / (tf + 1.5 * (0.25 + 0.75 * s.dl[i] / s.avg))
        top = sorted(scores, key=lambda i: (-scores[i], i))[:k]
        if upto is not None:
            s.sc[(q, k, upto)] = sorted(top)
        return sorted(top)


# ------------------------------------------------------------------ prompts
def plain_prompt(L, q):
    return L.render(SYS, q)


def ctx_prompt(L, ctx, q, head="Messages from Sam's chat history, labelled by day (if they disagree, the latest day is true):"):
    return L.render(SYS, f"{head}\n{ctx}\n\nQuestion: {q}")


def diary_prompt(L, diary, q, upto=None):  # the diary-test format; upto: restrict the notes to days <= upto (training), None: whole diary (scoring)
    return L.render(SYS, "Notes from earlier chats:\n" + diary.label(diary.search(q, 8, upto)) + f"\n\nQuestion: {q}")


def tag_prompt(L, text):
    u = (f"Message from Sam:\n\"{text}\"\n\nList the facts this message states about specific named people, places, organisations or things, as "
         f"short subject-relation-object triples. Use the names exactly as written in the message. At most 5. Reply with only JSON: "
         f"[{{\"subject\": \"...\", \"relation\": \"...\", \"object\": \"...\"}}]. If there are none, reply [].")
    return L.render("You extract facts from chat messages.", u)


def upd_prompt(L, do, to, fo, dn, tn, fn, shared):
    u = (f"Earlier message (Day {do}): \"{to}\"\n(fact noted: {fo})\nLater message (Day {dn}): \"{tn}\"\n(fact noted: {fn})\n\nBoth messages mention \"{shared}\". Does the later message "
         f"change what the earlier message said, so that the earlier fact is no longer true (for example a new home, a new job, a correction)? "
         f"Answer with just \"changed\" or \"not changed\".")
    return L.render("You compare chat messages carefully.", u)


def nrem_prompt(L, ctx, it):
    u = (f"Messages Sam sent in chat, newest first, labelled by day. If they disagree, the newest message is true.\n{ctx}\n\n"
         f"Focus on the fact linking \"{it.subj}\" and \"{it.obj}\". Write {K} paraphrases of the CURRENT fact (short standalone sentences, "
         f"different wording, naming both) and {K} question-answer pairs about it. Cover both directions: some questions should ask about one "
         f"name, some about the other. Each answer must be a single name from the fact. Reply with only JSON of the form "
         f"{{\"paraphrases\": [\"...\"], \"qa\": [{{\"q\": \"...\", \"a\": \"...\"}}]}}")
    return L.render("You are a careful assistant that studies facts.", u)


def now_prompt(L, ctx, shared, new, old):
    u = (f"Messages from Sam's chat, labelled by day:\n{ctx}\n\nThe latest message changes what was said earlier about \"{shared}\". Write 2 different "
         f"questions asking what is true NOW about \"{shared}\" (use words like now, currently or these days). The answer to each must be "
         f"\"{new}\". Do not put \"{new}\" or \"{old}\" in the question. Reply with only JSON: {{\"questions\": [\"...\", \"...\"]}}")
    return L.render("You are a careful assistant that studies facts.", u)


def chain_prompt(L, fx, fy):
    u = (f"Two facts:\n- {fx}\n- {fy}\n\nWrite one question that can only be answered by using both facts together, without naming the name the two "
         f"facts share, and its answer, which must be a single name. Reply in exactly this form:\nQuestion: ...\nAnswer: ...")
    return L.render("You are a careful assistant that studies facts.", u)


def gist_prompt(L, fx, nd):
    u = (f"Fact about Sam's life: {fx} (it came up on {nd} different days).\n\nWrite one question about what Sam usually does, where Sam usually "
         f"goes or who Sam usually sees, which this fact answers as a habit, and its answer, a single name from the fact. Reply in exactly "
         f"this form:\nQuestion: ...\nAnswer: ...")
    return L.render("You are a careful assistant that studies facts.", u)


def af_prompt(L, day, text):
    u = (f"A message Sam sent in chat on day {day}:\n\"{text}\"\n\nThe message may state facts about named people, places or things. Write {K} "
         f"paraphrases of those facts (short standalone sentences, different wording, naming the names) and {K} question-answer pairs about them. "
         f"Cover both directions. Each answer must be a single name taken from the message. Reply with only JSON of the form "
         f"{{\"paraphrases\": [\"...\"], \"qa\": [{{\"q\": \"...\", \"a\": \"...\"}}]}}")
    return L.render("You are a careful assistant that studies facts.", u)


def parse_facts(txt):
    m = re.search(r"\[.*\]", txt, re.S)
    if m:
        try:
            return [x for x in json.loads(m.group(0)) if isinstance(x, dict)]
        except Exception:
            pass
    out = []
    for o in re.findall(r"\{[^{}]*\}", txt):
        try:
            x = json.loads(o)
            if isinstance(x, dict):
                out.append(x)
        except Exception:
            pass
    return out or None  # None: nothing parseable; [] (from a literal "[]") is a valid "no facts"


def parse_now(txt):
    m = re.search(r"\{.*\}", txt, re.S)
    if m:
        try:
            return [q for q in json.loads(m.group(0)).get("questions", []) if isinstance(q, str)]
        except Exception:
            pass
    return [re.sub(r"^[-*\d. ]+", "", ln).strip() for ln in txt.splitlines() if ln.strip().endswith("?")]


def parse_qa1(txt):
    m = re.search(r"Question:\s*(.+?)\s*[\r\n]+\s*Answer:\s*([^\r\n]+)", txt) or re.search(r"Question:\s*(.+?)\s*Answer:\s*(.+)$", txt, re.S)
    return (m.group(1).strip(), m.group(2).strip().rstrip(".")) if m else None


def ex_text(L, t):
    return (L.ids(t) + [L.eos], 0)


def ex_qa(L, q, a):
    p = L.ids(L.render(SYS, q))
    return (p + L.ids(a) + [L.eos], len(p))


def ex_qa_ob(L, diary, q, a, d):  # open-book Q&A example: the diary-test prompt (notes of days <= d), loss on the answer only
    p = L.ids(diary_prompt(L, diary, q, d))
    return (p + L.ids(a) + [L.eos], len(p))


# ------------------------------------------------------------------ scoring
@torch.no_grad()
def generate_p(L, model, prompts, max_new=20, bs=8):
    """Lang.generate (greedy) that also returns p_first: softmax probability of each answer's first generated token (scores[0], taken
    from model.generate(output_scores=True, return_dict_in_generate=True); greedy has no sampling warpers)."""
    outs, ps = [None] * len(prompts), [None] * len(prompts)
    order = sorted(range(len(prompts)), key=lambda i: len(prompts[i]))
    for st in range(0, len(order), bs):
        idx = order[st:st + bs]
        enc = [L.ids(prompts[i]) for i in idx]
        n = max(map(len, enc))
        pad = 0 if L.smoke else (L.tok.pad_token_id if L.tok.pad_token_id is not None else L.eos)
        ids = torch.full((len(enc), n), pad, dtype=torch.long)
        mask = torch.zeros((len(enc), n), dtype=torch.long)
        for r, e in enumerate(enc):
            ids[r, n - len(e):] = torch.tensor(e)
            mask[r, n - len(e):] = 1
        out = model.generate(input_ids=ids.to(L.device), attention_mask=mask.to(L.device), max_new_tokens=max_new, pad_token_id=pad,
                             eos_token_id=L.eos, do_sample=False, output_scores=True, return_dict_in_generate=True)
        p0, seq = torch.softmax(out.scores[0].float(), -1), out.sequences
        for r, i in enumerate(idx):
            outs[i], ps[i] = L.decode(seq[r, n:].tolist()).strip(), float(p0[r, seq[r, n]])
    return outs, ps


def score_week(L, model, week, diary, mode, bs, dreamed=None, full=False):
    """mode 'weights' (question only) or 'diary' (BM25 top-8 user turns labelled by day + question). dreamed: bool per twohop test.
    full: also save every row (not only 8 examples per kind) under 'rows', each with p_first (first answer token's probability)."""
    T, flat, prompts = week["tests"], [], []
    for kind in KINDS:
        for t in T[kind]:
            flat.append((kind, t))
            if mode == "diary":
                prompts.append(diary_prompt(L, diary, t["q"]))
            else:
                prompts.append(plain_prompt(L, t["q"]))
    ans, pf = generate_p(L, model, prompts, max_new=20, bs=bs) if full else (L.generate(model, prompts, max_new=20, bs=bs), None)
    rows = defaultdict(list)
    for j, ((kind, t), a) in enumerate(zip(flat, ans)):
        r = {"q": t["q"], "target": t["target"], "answer": a, "ok": has_ans(t["target"], a)}
        if full:
            r["p_first"] = pf[j]
        if kind == "changed":
            r["stale"] = has_ans(t["old"], a)
        if "class" in t:
            r["cls"] = t["class"]
        rows[kind].append(r)
    sc = agg(rows, dreamed)
    if full:
        sc["rows"] = {k: rows[k] for k in KINDS}
    return sc


def agg(rows, dreamed=None):  # score_week's summary of scored rows {kind: [row]}
    sc = {}
    for kind in ("forward", "reverse"):
        rs = rows[kind]
        sc[kind] = {"acc": acc(r["ok"] for r in rs), "n": len(rs), "C24": acc(r["ok"] for r in rs if r["cls"] in ("C2", "C4")),
                    **{c: acc(r["ok"] for r in rs if r["cls"] == c) for c in ("C1", "C2", "C4")}}
    th = rows["twohop"]
    sc["twohop"] = {"acc": acc(r["ok"] for r in th), "n": len(th)}
    if dreamed is not None:
        sc["twohop"].update({"dreamed": acc(r["ok"] for r, dm in zip(th, dreamed) if dm), "n_dreamed": sum(dreamed),
                             "not_dreamed": acc(r["ok"] for r, dm in zip(th, dreamed) if not dm), "n_not_dreamed": len(dreamed) - sum(dreamed)})
    sc["changed"] = {"new": acc(r["ok"] for r in rows["changed"]), "stale": acc(r["stale"] for r in rows["changed"]), "n": len(rows["changed"])}
    sc["routine"] = {"acc": acc(r["ok"] for r in rows["routine"]), "n": len(rows["routine"])}
    sc["integration"] = mean([sc["twohop"]["acc"], sc["routine"]["acc"], sc["changed"]["new"]])
    sc["pooled"] = acc(r["ok"] for k in KINDS for r in rows[k])
    sc["examples"] = {k: rows[k][:8] for k in KINDS}
    return sc


def route(mem, bd, dreamed=None, thr=0.5):
    """Router R (addendum 1): the slept model's weights-only answer if its first-token probability >= thr, else the base model's diary answer.
    mem / bd: score_week(full=True) outputs (weights mode of the slept model, diary mode with the adapter off). Same structure as score_week."""
    rows = {k: [dict(m if m["p_first"] >= thr else b, src="memory" if m["p_first"] >= thr else "base_diary", p_first_mem=m["p_first"])
                for m, b in zip(mem["rows"][k], bd["rows"][k])] for k in KINDS}
    assert all(m["q"] == r["q"] for k in KINDS for m, r in zip(mem["rows"][k], rows[k])) and all(len(rows[k]) == len(mem["rows"][k]) for k in KINDS)
    allr = [r for k in KINDS for r in rows[k]]
    sc = agg(rows, dreamed)
    sc.update({"threshold": thr, "frac_memory": acc(r["src"] == "memory" for r in allr), "acc_when_memory": acc(r["ok"] for r in allr if r["src"] == "memory"),
               "acc_when_diary": acc(r["ok"] for r in allr if r["src"] != "memory"), "rows": rows})
    return sc


def eval_line(sc):
    return (f"forward {sc['forward']['acc']} (C1 {sc['forward']['C1']} C2 {sc['forward']['C2']} C4 {sc['forward']['C4']}) reverse {sc['reverse']['acc']} "
            f"twohop {sc['twohop']['acc']} changed new {sc['changed']['new']} stale {sc['changed']['stale']} routine {sc['routine']['acc']} "
            f"integration {sc['integration']} pooled {sc['pooled']}")


def fwd_recall(L, model, week, bs):  # cheap learning-curve probe: weights-only forward recall by ground-truth class
    ts = week["tests"]["forward"]
    ans = L.generate(model, [plain_prompt(L, t["q"]) for t in ts], max_new=20, bs=bs)
    ok = [has_ans(t["target"], a) for t, a in zip(ts, ans)]
    cl = lambda cs: acc(o for o, t in zip(ok, ts) if t["class"] in cs)  # noqa: E731
    return {"C1": cl(("C1",)), "C2": cl(("C2",)), "C4": cl(("C4",)), "C24": cl(("C2", "C4")), "all": acc(ok)}


def load_arc_val(smoke):
    if smoke:
        return ARC_SMOKE
    from datasets import load_dataset
    rows = []
    for r in list(load_dataset("allenai/ai2_arc", "ARC-Easy", split="validation"))[:100]:
        rows.append({"question": r["question"], "choices": r["choices"]["text"], "answer": r["choices"]["label"].index(r["answerKey"])})
    return rows


# ------------------------------------------------------------------ training
TOK_BUDGET = 4096  # padded tokens per forward; longer batches (open-book / diary-format KL) are split, same loss and gradients


def groups(seqs, budget=None):  # consecutive micro-batches whose padded size stays within budget (default TOK_BUDGET, set by --tok-budget)
    budget = budget or TOK_BUDGET
    out, cur, mx = [], [], 0
    for x in seqs:
        m = max(mx, len(x[0]))
        if cur and (len(cur) + 1) * m > budget:
            out.append(cur)
            cur, m = [], len(x[0])
        cur.append(x)
        mx = m
    return out + ([cur] if cur else [])


class Trainer:
    """One night of LoRA training: fresh AdamW, cosine lr over `steps`, CE on the batch + KL guard on generic replay vs adapter-disabled base."""

    def __init__(s, L, pm, args, replay, steps, seed):
        s.L, s.pm, s.a, s.replay = L, pm, args, replay
        s.params = [p for p in pm.parameters() if p.requires_grad]
        s.opt = torch.optim.AdamW(s.params, lr=args.lr, weight_decay=0.0)
        s.n, s.i, s.rng = max(steps, 1), 0, random.Random(seed)
        s.curve = []

    def masks(s, mb):
        ids, mask = s.L.pad_right([b[0] for b in mb])
        lm = torch.zeros_like(mask)
        for r, (e, st) in enumerate(mb):
            lm[r, st:len(e)] = 1
        return ids, mask, lm[:, 1:].bool()

    def step(s, batch):
        if not batch:
            return
        a = s.a
        lr = a.lr * 0.5 * (1 + math.cos(math.pi * s.i / s.n))
        for g in s.opt.param_groups:
            g["lr"] = lr
        s.pm.train()
        rb = s.rng.sample(s.replay, min(a.replay_bsz, len(s.replay))) if s.replay and a.kl_weight > 0 else []
        gb, gr = groups(batch), groups(rb)
        kl_v = 0.0
        s.opt.zero_grad(set_to_none=True)
        if len(gb) == 1 and len(gr) <= 1:  # the stage-1 path (short closed-book examples), unchanged
            ids, mask, tm = s.masks(batch)
            ce = F.cross_entropy(s.pm(input_ids=ids, attention_mask=mask).logits[:, :-1][tm].float(), ids[:, 1:][tm])
            loss = ce
            if rb:
                rids, rmask, rt = s.masks(rb)
                cur = s.pm(input_ids=rids, attention_mask=rmask).logits[:, :-1][rt].float()
                with torch.no_grad(), s.pm.disable_adapter():
                    ref = s.pm(input_ids=rids, attention_mask=rmask).logits[:, :-1][rt].float()
                kl = F.kl_div(F.log_softmax(cur, -1), F.log_softmax(ref, -1), log_target=True, reduction="batchmean")
                loss = ce + a.kl_weight * kl
                kl_v = float(kl.detach())
            loss.backward()
        else:  # split: sums over micro-batches divided by the full batch's target count, so loss and gradients match
            ntgt = sum(len(e) - max(st, 1) for e, st in batch)
            ce_sum = 0.0
            for mb in gb:
                ids, mask, tm = s.masks(mb)
                part = F.cross_entropy(s.pm(input_ids=ids, attention_mask=mask).logits[:, :-1][tm].float(), ids[:, 1:][tm], reduction="sum") / ntgt
                part.backward()
                ce_sum += float(part.detach())
            ce = torch.tensor(ce_sum)
            if rb:
                npos = sum(len(e) - max(st, 1) for e, st in rb)
                for mb in gr:
                    rids, rmask, rt = s.masks(mb)
                    cur = s.pm(input_ids=rids, attention_mask=rmask).logits[:, :-1][rt].float()
                    with torch.no_grad(), s.pm.disable_adapter():
                        ref = s.pm(input_ids=rids, attention_mask=rmask).logits[:, :-1][rt].float()
                    part = F.kl_div(F.log_softmax(cur, -1), F.log_softmax(ref, -1), log_target=True, reduction="sum") / npos
                    (a.kl_weight * part).backward()
                    kl_v += float(part.detach())
        torch.nn.utils.clip_grad_norm_(s.params, 1.0)
        s.opt.step()
        s.i += 1
        if s.i % 10 == 1 or s.i == s.n:
            s.curve.append({"step": s.i, "ce": float(ce.detach()), "kl": kl_v, "lr": lr})
        s.pm.eval()


# ------------------------------------------------------------------ synaptic downscaling (SHY)
def lora_mods(pm):
    return [(n, m) for n, m in pm.named_modules() if hasattr(m, "lora_A") and "default" in m.lora_A]


@torch.no_grad()
def shy_core(A, B, scaling, factor, thresh, gen):
    """A: r x in, B: out x r. SVD of dW = scaling*B@A via QR of B and A^T (small core), singular values x factor, those below
    thresh x largest zeroed, refactored into the same shapes (sqrt(S/scaling) on each side). Zeroed / padded rank slots get a fresh
    LoRA-init row in A and a zero column in B, so dW is unchanged by them and they stay trainable.
    Returns A', B', n_zeroed, n_sv, energy_before, energy_after."""
    r, nin = A.shape
    nout = B.shape[0]
    Qb, Rb = torch.linalg.qr(B.float())
    Qa, Ra = torch.linalg.qr(A.float().T)
    U, S, Vh = torch.linalg.svd((scaling * Rb @ Ra.T).cpu(), full_matrices=False)
    U, S, Vh = U.to(A.device), S.to(A.device), Vh.to(A.device)
    if float(S.max()) <= 0:
        return A.float().clone(), B.float().clone(), 0, 0, 0.0, 0.0
    S2 = S * factor
    zero = S < thresh * S.max()
    S2 = torch.where(zero, torch.zeros_like(S2), S2)
    sq = (S2 / scaling).sqrt()
    m = S.numel()
    B2 = torch.zeros(nout, r, device=A.device)
    A2 = torch.zeros(r, nin, device=A.device)
    B2[:, :m] = (Qb @ U) * sq
    A2[:m] = sq[:, None] * (Vh @ Qa.T)
    dead = [i for i in range(r) if i >= m or bool(zero[i])]
    if dead:
        bound = 1.0 / math.sqrt(nin)
        A2[dead] = ((torch.rand(len(dead), nin, generator=gen) * 2 - 1) * bound).to(A.device)
        B2[:, dead] = 0
    return A2, B2, int(zero.sum()), m, float((S ** 2).sum()), float((S2 ** 2).sum())


@torch.no_grad()
def shy_apply(pm, factor, thresh, gen):
    nz = nsv = 0
    e0 = e1 = 0.0
    mods = lora_mods(pm)
    for _, m in mods:
        A, B = m.lora_A["default"].weight, m.lora_B["default"].weight
        A2, B2, z, n, ea, eb = shy_core(A.data, B.data, float(m.scaling["default"]), factor, thresh, gen)
        A.data.copy_(A2)
        B.data.copy_(B2)
        nz, nsv, e0, e1 = nz + z, nsv + n, e0 + ea, e1 + eb
    return {"modules": len(mods), "sv_total": nsv, "sv_zeroed": nz, "zeroed_frac": nz / max(nsv, 1), "energy_ratio": e1 / max(e0, 1e-12)}


@torch.no_grad()
def selftest_shy(pm=None):
    """With thresh=0 the refactor must reproduce factor x dW to 1e-4 relative error (tensor level, then every LoRA module of pm)."""
    g = torch.Generator().manual_seed(0)
    worst = 0.0
    for nout, nin, r in [(64, 48, 16), (4, 64, 16), (32, 8, 16), (128, 128, 16), (16, 16, 16)]:
        A, B, sc = torch.randn(r, nin, generator=g), torch.randn(nout, r, generator=g), 2.0
        A2, B2, *_ = shy_core(A, B, sc, 0.85, 0.0, g)
        assert A2.shape == A.shape and B2.shape == B.shape
        rel = float((sc * B2 @ A2 - 0.85 * sc * B @ A).norm() / (0.85 * sc * B @ A).norm())
        assert rel < 1e-4, (nout, nin, r, rel)
        worst = max(worst, rel)
    out = {"tensor_worst_rel_err": worst}
    if pm is not None:
        mods = lora_mods(pm)
        saved = [(m.lora_A["default"].weight.data.clone(), m.lora_B["default"].weight.data.clone()) for _, m in mods]
        for _, m in mods:
            m.lora_A["default"].weight.data.normal_(0, 0.1)
            m.lora_B["default"].weight.data.normal_(0, 0.05)
        dw = lambda m: float(m.scaling["default"]) * m.lora_B["default"].weight.data.float() @ m.lora_A["default"].weight.data.float()  # noqa: E731
        before = [dw(m) for _, m in mods]
        shy_apply(pm, 0.85, 0.0, g)
        tol = 1e-4 if mods[0][1].lora_A["default"].weight.dtype == torch.float32 else 3e-2  # bf16 adapters cannot hold 1e-4
        w2 = max(float((dw(m) - 0.85 * b).norm() / (0.85 * b).norm()) for (_, m), b in zip(mods, before))
        for (_, m), (a, b) in zip(mods, saved):
            m.lora_A["default"].weight.data.copy_(a)
            m.lora_B["default"].weight.data.copy_(b)
        assert w2 < tol, w2
        out["pm_worst_rel_err"] = w2
        out["pm_modules"] = len(mods)
    return out


# ------------------------------------------------------------------ full-rank deltas (arms ab_ob_full / ab_ob_merge)
_DELTA = {"on": True}  # module-level switch: the delta_w hooks add their delta only while it is on


def setup_delta(pm, train):
    """Give every LoRA-target Linear an fp32 zero delta_w (its weight's shape) on its base_layer; a forward hook adds F.linear(x, delta_w)
    to the layer output while _DELTA["on"]. train: delta_w is trainable (ab_ob_full); else it only changes by the nightly fold (ab_ob_merge).
    pm.disable_adapter (an instance attribute shadowing the peft method) also switches the deltas off and restores the previous switch on
    exit (nesting-safe), so every "base" use (dreaming, tagging, KL reference, ARC base, base_diary) stays the original pretrained model."""
    mods = lora_mods(pm)
    for _, m in mods:
        bl = m.base_layer
        bl.delta_w = torch.nn.Parameter(torch.zeros(bl.weight.shape, dtype=torch.float32, device=bl.weight.device), requires_grad=train)

        def hook(mod, inp, out):
            return out + F.linear(inp[0], mod.delta_w.to(inp[0].dtype)) if _DELTA["on"] else out
        bl.register_forward_hook(hook)
    orig = pm.disable_adapter

    @contextlib.contextmanager
    def disable_adapter():
        prev, _DELTA["on"] = _DELTA["on"], False
        try:
            with orig():
                yield
        finally:
            _DELTA["on"] = prev
    pm.disable_adapter = disable_adapter
    return mods


def delta_fro(pm):  # total Frobenius norm of all deltas
    return math.sqrt(sum(float(m.base_layer.delta_w.detach().float().pow(2).sum()) for _, m in lora_mods(pm)))


@torch.no_grad()
def shy_full(W, factor, thresh):
    """SHY on a full-rank matrix, singular values x factor, those below thresh x largest zeroed. Via the eigendecomposition of the small
    Gram matrix (float64 eigh on W's device; much faster than a full SVD on the GPU): W' = U diag(scale) U^T W, U the left singular vectors.
    Returns W', n_zeroed, n_sv, energy_before, energy_after (as shy_core)."""
    Wf = W.float()
    t = Wf.shape[0] > Wf.shape[1]
    X = (Wf.T if t else Wf).double()
    ev, U = torch.linalg.eigh(X @ X.T)
    S = ev.clamp(min=0).sqrt()
    if float(S.max()) <= 0:
        return Wf.clone(), 0, 0, 0.0, 0.0
    zero = S < thresh * S.max()
    sc = torch.where(zero, torch.zeros_like(S), torch.full_like(S, factor))
    X2 = ((U * sc) @ (U.T @ X)).float()
    S2 = S * sc
    return (X2.T if t else X2).contiguous(), int(zero.sum()), S.numel(), float((S ** 2).sum()), float((S2 ** 2).sum())


@torch.no_grad()
def shy_delta_apply(pm, factor, thresh, gen, merge):
    """Nightly SHY for the delta arms. ab_ob_full: delta_w <- shy_full(delta_w). ab_ob_merge (merge): total = delta_w + scaling x B@A (fp32),
    delta_w <- shy_full(total), then the LoRA restarts: A fresh uniform(+-1/sqrt(in)) from gen (as shy_core does for dead slots), B zero.
    Same stats keys as shy_apply (+ fold_fro: Frobenius norm of the folded LoRA, merge only)."""
    nz = nsv = 0
    e0 = e1 = fold = 0.0
    mods = lora_mods(pm)
    for _, m in mods:
        dw = m.base_layer.delta_w
        W = dw.data.float()
        if merge:
            A, B = m.lora_A["default"].weight, m.lora_B["default"].weight
            ba = float(m.scaling["default"]) * (B.data.float() @ A.data.float())
            fold += float(ba.pow(2).sum())
            W = W + ba
        W2, z, n, ea, eb = shy_full(W, factor, thresh)
        dw.data.copy_(W2)
        if merge:
            A.data.copy_(((torch.rand(A.shape, generator=gen) * 2 - 1) / math.sqrt(A.shape[1])).to(A.device))
            B.data.zero_()
        nz, nsv, e0, e1 = nz + z, nsv + n, e0 + ea, e1 + eb
    out = {"modules": len(mods), "sv_total": nsv, "sv_zeroed": nz, "zeroed_frac": nz / max(nsv, 1), "energy_ratio": e1 / max(e0, 1e-12)}
    if merge:
        out["fold_fro"] = math.sqrt(fold)
    return out


@torch.no_grad()
def selftest_delta():
    """Delta machinery on its own tiny CPU smoke model (the real model is never touched; global RNG and the delta switch are restored):
    (i) zero deltas -> logits equal the plain model; (ii) random deltas -> equal the plain model inside pm.disable_adapter() (nested too),
    different outside; (iii) the merge fold with factor 1, thresh 0 leaves logits unchanged and resets the LoRA; (iv) shy_full with
    thresh 0 reproduces factor x W. The model's deltas / LoRA are put back as found."""
    from argparse import Namespace
    from peft import LoraConfig, get_peft_model
    out, g = {}, torch.Generator().manual_seed(0)
    rng_state, sw = torch.get_rng_state(), _DELTA["on"]
    try:
        worst = 0.0
        for shape in [(64, 48), (4, 64), (32, 8), (128, 128)]:
            W = torch.randn(*shape, generator=g)
            worst = max(worst, float((shy_full(W, 0.85, 0.0)[0] - 0.85 * W).norm() / (0.85 * W).norm()))
        assert worst < 1e-5, worst
        out["shy_full_worst_rel_err"] = worst
        lm, _ = load_model(Namespace(smoke=True, seed=0), torch.device("cpu"), torch.float32)
        ids = torch.randint(4, 200, (2, 12), generator=g)
        ref = lm(input_ids=ids).logits  # the plain (pretrained-equivalent) model
        pm = get_peft_model(lm, LoraConfig(r=8, lora_alpha=16, lora_dropout=0.0, target_modules=LORA_TARGETS, bias="none"))
        mods = setup_delta(pm, True)
        pm.eval()
        logits = lambda: pm(input_ids=ids).logits  # noqa: E731
        rel = lambda x, y: float((x - y).norm() / y.norm())  # noqa: E731
        out["zero_delta_max_abs_diff"] = float((logits() - ref).abs().max())
        assert out["zero_delta_max_abs_diff"] < 1e-6, out
        saved = [(m.base_layer.delta_w.data.clone(), m.lora_A["default"].weight.data.clone(), m.lora_B["default"].weight.data.clone()) for _, m in mods]
        for _, m in mods:
            m.base_layer.delta_w.data.normal_(0, 0.05, generator=g)
        on = logits()
        with pm.disable_adapter():
            with pm.disable_adapter():
                nested_off = not _DELTA["on"]
            still_off = not _DELTA["on"]
            off = logits()
        out["disabled_max_abs_diff"], out["enabled_rel_diff"] = float((off - ref).abs().max()), rel(on, ref)
        out["nesting_ok"] = bool(nested_off and still_off and _DELTA["on"])
        assert out["disabled_max_abs_diff"] < 1e-6 and out["enabled_rel_diff"] > 1e-3 and out["nesting_ok"], out
        for _, m in mods:
            m.lora_B["default"].weight.data.normal_(0, 0.05, generator=g)
        before = logits()
        shy_delta_apply(pm, 1.0, 0.0, g, True)
        out["merge_fold_rel_err"] = rel(logits(), before)
        out["merge_lora_reset"] = all(float(m.lora_B["default"].weight.abs().max()) == 0 for _, m in mods)
        assert out["merge_fold_rel_err"] < 1e-4 and out["merge_lora_reset"], out
        for (_, m), (d, a, b) in zip(mods, saved):
            m.base_layer.delta_w.data.copy_(d)
            m.lora_A["default"].weight.data.copy_(a)
            m.lora_B["default"].weight.data.copy_(b)
        out["restored_zero_delta_max_abs_diff"] = float((logits() - ref).abs().max())
        assert out["restored_zero_delta_max_abs_diff"] < 1e-6, out
        out["modules"] = len(mods)
        return out
    finally:
        torch.set_rng_state(rng_state)
        _DELTA["on"] = sw


# ------------------------------------------------------------------ the brain-like sleeper (arm ab and ablations)
@dataclass
class Item:
    key: tuple
    subj: str
    obj: str
    rel: str
    born: int
    first: int = 0
    days: int = 0
    nment: int = 0
    imp: bool = False
    cor: bool = False
    sup_by: tuple = None
    upd: list = field(default_factory=list)  # [{"shared","old","new","old_key"}] older values this item replaced
    para: list = field(default_factory=list)
    qa: list = field(default_factory=list)
    probe: tuple = None
    seen_ment: int = -1
    dirty: bool = False
    streak: int = 0
    surprise: int = 1
    consol: bool = False
    gave_old: bool = False
    fails: int = 0
    dead: bool = False

    @property
    def fact(self):
        return f"{self.subj} {self.rel} {self.obj}."


def other(it, x):  # (display shared, display other) of the item w.r.t. normalized string x
    return (it.subj, it.obj) if norm(it.subj) == x else (it.obj, it.subj)


class Brain:
    def __init__(s, L, pm, args, week, diary, leak, replay, arc_val, arc_base, log):
        s.L, s.pm, s.a, s.week, s.diary, s.leak, s.replay, s.log = L, pm, args, week, diary, leak, replay, log
        s.arc_val, s.arc_base = arc_val, arc_base
        s.items, s.dropped, s.checked = {}, set(), set()
        s.rem_pool, s.rem_chains, s.rem_done, s.gist_done = [], [], Counter(), Counter()
        s.upd_log, s.tag_log, s.examples = [], [], {"dreams": [], "probes": [], "rem": [], "now": []}
        s.rng = random.Random(args.seed + 17)
        s.ob_rng = random.Random(args.seed + 29)  # OB_ARMS only: open-book coin flips (kept apart so the batch-composition rng stream is ab's)
        s.day, s.night_qs = 0, []
        s.gen_t = torch.Generator().manual_seed(args.seed + 5)
        G = []  # ground truth name pairs per item (diagnostics only)
        for g in week["items"]:
            G.append((g["id"], g["class"], [(g["a"].lower(), g["b"].lower())], [(g["a"].lower(), g["old_b"].lower())] if g.get("old_b") else []))
        s.G = G
        s.cov = Counter()

    # ---- plumbing
    def mn(s, n):
        return min(n, 24) if s.a.smoke else n

    def gen(s, prompts, max_new, base=True, sample=False, temp=0.8):
        if not prompts:
            return []
        s.pm.eval()
        if base:
            with s.pm.disable_adapter():
                return s.L.generate(s.pm, prompts, max_new=max_new, bs=s.a.gen_bs, sample=sample, temp=temp)
        return s.L.generate(s.pm, prompts, max_new=max_new, bs=s.a.gen_bs, sample=sample, temp=temp)

    def leaky(s, text):
        n = norm(text)
        return any(l in n or (len(n) >= 10 and n in l) for l in s.leak)

    def elig(s, it):
        if it.dead or it.sup_by:
            return False
        # an update re-opens an existing memory (reconsolidation): the topic has already come up on 2+ days (old + new value)
        return s.a.arm == "ab_all" or it.days >= 2 or it.imp or it.cor or bool(it.upd)

    def prio(s, it):
        if s.a.arm == "ab_flatprio":
            return 1.0
        return max(it.days, 1) * (1 + it.imp + it.cor) * (1 + it.surprise) * (2 if it.upd and it.gave_old else 1)

    # ---- 1. tagging
    def tag(s, d):
        turns = [t for t in s.diary.turns if t["day"] == d]
        raw = s.gen([tag_prompt(s.L, t["text"]) for t in turns], s.mn(160))
        s.raw["tag"] = [{"text": t["text"][:200], "out": r} for t, r in list(zip(turns, raw))[:3]]
        st = Counter()
        for t, txt in zip(turns, raw):
            fx = parse_facts(txt)
            if fx is None and s.a.smoke:  # tiny random model emits noise: fabricate from the first two capitalized words
                ws = list(dict.fromkeys(CAP.findall(t["text"])))
                fx = [{"subject": ws[0], "relation": "is linked to", "object": ws[1]}] if len(ws) >= 2 else []
                s.cov["tag_fallback"] += bool(fx)
            if fx is None:
                st["parse_fail"] += 1
                fx = []
            elif not fx:
                st["empty"] += 1
            got = []
            for f in fx[:5]:
                st["extracted"] += 1
                sj, rl, ob = (str(f.get(k) or "").strip() for k in ("subject", "relation", "object"))
                if min(len(sj), len(ob)) < 2 or max(len(sj), len(ob)) > 60 or norm(sj) == norm(ob) or norm(sj) in GENERIC or norm(ob) in GENERIC:
                    st["dropped_invalid"] += 1
                    continue
                if t["i"] not in s.diary.occurs(sj) or t["i"] not in s.diary.occurs(ob):
                    st["dropped_not_in_turn"] += 1
                    continue
                key = (norm(sj), norm(ob))
                if key in s.dropped:
                    continue
                if key not in s.items:
                    s.items[key] = Item(key, sj, ob, rl or "is linked to", d)
                    st["new_items"] += 1
                got.append((sj, ob))
            st["kept"] += len(got)
            s.tag_log.append((t["i"], d, got))
        st["turns"] = len(turns)
        return dict(st)

    def refresh(s, d):  # days_seen / importance / correction from a string search over the diary so far
        for it in s.items.values():
            if it.dead:
                continue
            idx = s.diary.containing(it.subj, it.obj, d)
            days = {s.diary.turns[i]["day"] for i in idx}
            it.nment, it.days, it.first = len(idx), len(days), (min(days) if days else it.born)
            it.imp = it.imp or any(IMP_RE.search(s.diary.turns[i]["text"]) for i in idx)
            it.cor = it.cor or any(COR_RE.search(s.diary.turns[i]["text"]) for i in idx)

    # ---- 2. update detection (reconsolidation)
    def detect(s, d):
        by = defaultdict(list)
        for it in s.items.values():
            if not it.dead:
                for x in {norm(it.subj), norm(it.obj)}:
                    by[x].append(it)
        cand = []
        for x, its in by.items():
            if x in GENERIC or len(its) > 12:
                continue
            for a, b in itertools.combinations(its, 2):
                o, n = (a, b) if a.first < b.first else (b, a)
                if o.first == n.first or (o.key, n.key) in s.checked or other(o, x)[1].lower() == other(n, x)[1].lower():
                    continue
                cand.append((o, n, x))
        cand.sort(key=lambda c: (-c[1].born, -c[1].first))
        cand = cand[:s.a.max_checks]
        prompts, st, ntext = [], Counter(), []
        for o, n, x in cand:
            oi = s.diary.containing(o.subj, o.obj, n.first - 1) or s.diary.containing(o.subj, o.obj, d)
            ot, nt = s.diary.turns[oi[-1]], s.diary.turns[s.diary.containing(n.subj, n.obj, d)[0]]
            ntext.append(nt["text"])
            prompts.append(upd_prompt(s.L, ot["day"], ot["text"][:500], o.fact, nt["day"], nt["text"][:500], n.fact, other(o, x)[0]))
        out = s.gen(prompts, 8)
        s.raw["update"] = [{"pair": [o.fact, n.fact], "out": r} for (o, n, _), r in list(zip(cand, out))[:4]]
        for (o, n, x), txt, nt in zip(cand, out, ntext):
            s.checked.add((o.key, n.key))
            t = txt.lower()
            changed = "changed" in t and "not changed" not in t and "unchanged" not in t and not t.strip().startswith("not")
            if s.a.smoke:
                changed = bool(re.search(r"finally|moved|actually|now", nt.lower()))
            st["checks"] += 1
            s.upd_log.append((o.key, n.key, changed))
            if changed:
                st["changed"] += 1
                (sh, oo), (_, nn) = other(o, x), other(n, x)
                o.sup_by = n.key
                if not any(u["old_key"] == o.key for u in n.upd):
                    n.upd.append({"shared": sh, "old": oo, "new": nn, "old_key": o.key})
                    n.dirty, n.probe, n.streak = True, None, 0
        return dict(st, candidates=len(cand))

    # ---- 4. NREM dreams (base model, diary turns in context)
    def dream(s, d, E):
        a, st = s.a, Counter()
        s.night_qs = []  # questions kept by tonight's dreaming (ab_klctx leash)
        need = [it for it in E if it.dirty or it.seen_ment < it.nment or (it.fails and not (it.para or it.qa))]  # new, new mentions, or retry after a failed night
        need.sort(key=lambda it: (not it.upd, -it.days, -it.nment))
        st["backlog"] = max(0, len(need) - a.max_dream_items)
        need = need[:a.max_dream_items]
        prompts, meta = [], []
        for it in need:
            idx = s.diary.containing(it.subj, it.obj, d)[::-1][:4]
            ctx = s.diary.label(idx)
            prompts.append(nrem_prompt(s.L, ctx, it))
            meta.append((it, "dream", ctx))
            if it.upd:
                u = it.upd[-1]
                o = s.items[u["old_key"]]
                oi = s.diary.containing(o.subj, o.obj, it.first - 1) or s.diary.containing(o.subj, o.obj, d)
                nctx = s.diary.label(sorted(set(idx[:3]) | {oi[-1]}))
                prompts.append(now_prompt(s.L, nctx, u["shared"], u["new"], u["old"]))
                meta.append((it, "now", nctx))
        raw = s.gen(prompts, s.mn(400), sample=True)
        s.raw["dream"] = raw[:2]
        cp, cq = [], []  # (item, text) and (item, q, a, ctx, is_now)
        for (it, kind, ctx), txt in zip(meta, raw):
            ents = [it.subj, it.obj]
            if kind == "dream":
                paras, qas = parse_dream(txt)
                if s.a.smoke and not paras and not qas:
                    paras = [f"{it.subj} {it.rel} {it.obj} (smoke)."]
                    qas = [(f"What is linked to {it.subj}?", it.obj), (f"What is linked to {it.obj}?", it.subj)]
                if not paras and not qas:
                    st["parse_fail"] += 1
                for p in paras[:K]:
                    st["paraphrases_gen"] += 1
                    if s.leaky(p):
                        st["dropped_test_leak"] += 1
                    elif not all(e.lower() in p.lower() for e in ents):
                        st["dropped_missing_entities"] += 1
                    else:
                        cp.append((it, p.strip()))
                for q, ans in qas[:K]:
                    st["qa_gen"] += 1
                    es = [e for e in ents if e.lower() in ans.lower()]
                    if s.leaky(q):
                        st["dropped_test_leak"] += 1
                    elif len(es) != 1 or es[0].lower() in q.lower():
                        st["dropped_bad_answer"] += 1
                    else:
                        cq.append((it, q.strip(), es[0], ctx, False))
            else:
                u = it.upd[-1]
                qs = parse_now(txt) or ([f"Where is {u['shared']} now?"] if s.a.smoke else [])
                for q in qs[:2]:
                    st["now_gen"] += 1
                    if s.leaky(q):
                        st["dropped_test_leak"] += 1
                    elif u["new"].lower() in q.lower() or u["old"].lower() in q.lower() or u["shared"].lower() not in q.lower():
                        st["dropped_bad_answer"] += 1
                    else:
                        cq.append((it, q.strip(), u["new"], ctx, True))
        ver = s.gen([ctx_prompt(s.L, c, q) for _, q, _, c, _ in cq], 20)
        res = defaultdict(lambda: {"p": [], "q": [], "now": []})
        seen = set()
        for (it, q, ans, c, isnow), v in zip(cq, ver):
            if not has_ans(ans, v) and not s.a.smoke:
                st["dropped_unverified"] += 1
            elif (it.key, norm(q)) in seen:
                st["dropped_dup"] += 1
            else:
                seen.add((it.key, norm(q)))
                res[it.key]["now" if isnow else "q"].append((q, ans))
        for it, p in cp:
            if (it.key, norm(p)) in seen:
                st["dropped_dup"] += 1
            else:
                seen.add((it.key, norm(p)))
                res[it.key]["p"].append(p)
        for it in need:
            g = res[it.key]
            if g["p"] or g["q"] or g["now"]:
                pool = (g["now"] + g["q"]) if it.upd else (g["q"] + g["now"])
                if it.probe is None and pool:
                    it.probe = pool.pop(0)
                    s.examples["probes"].append({"night": d, "item": it.fact, "q": it.probe[0], "a": it.probe[1], "update": bool(it.upd)})
                elif it.probe:
                    pool = [x for x in pool if norm(x[0]) != norm(it.probe[0])]
                it.para, it.qa, it.fails = g["p"], pool, 0
                s.night_qs += [q for q, _ in pool]
                st["items_with_dreams"] += 1
                if len(s.examples["dreams"]) < 20:
                    s.examples["dreams"].append({"night": d, "item": it.fact, "paraphrases": g["p"], "qa": pool, "probe": it.probe, "update": bool(it.upd)})
                if g["now"] and len(s.examples["now"]) < 20:
                    s.examples["now"].append({"night": d, "item": it.fact, "now": g["now"]})
            elif not (it.para or it.qa or it.probe):
                it.fails += 1
                st["items_failed"] += 1
            it.seen_ment, it.dirty = it.nment, False
            st["paraphrases_kept"] += len(g["p"])
            st["qa_kept"] += len(g["q"]) + len(g["now"])
            st["now_kept"] += len(g["now"])
        st["items"] = len(need)
        return dict(st)

    # ---- 5. morning probes (weights only, current adapter)
    def probe(s, E):
        its = [it for it in E if it.probe]
        ans = s.gen([plain_prompt(s.L, it.probe[0]) for it in its], 20, base=False)
        out = {}
        for it, a in zip(its, ans):
            ok = has_ans(it.probe[1], a)
            if s.a.smoke:  # random model never answers: simulate a learner so consolidation / rehearsal / gate paths run
                ok = s.rng.random() < s.a.smoke_correct
            out[it.key] = (ok, a)
        return out

    def morning(s, E, pre):
        for it in E:
            if it.key in pre:
                ok, a = pre[it.key]
                it.surprise = 0 if ok else 1
                it.streak = it.streak + 1 if ok else 0
                it.consol = it.streak >= 2
                it.gave_old = (not ok) and any(has_ans(u["old"], a) for u in it.upd)
            else:
                it.consol = False

    # ---- batches
    def qa_ex(s, q, a):  # OB_ARMS: with p=0.5 the Q&A example is open-book (diary-test prompt, notes of days <= tonight), else closed-book
        if s.a.arm in OB_ARMS:
            ob = s.ob_rng.random() < 0.5
            s.cov["qa_open_book" if ob else "qa_closed_book"] += 1
            if ob:
                if "ob_example" not in s.raw:
                    s.raw["ob_example"] = {"prompt_tail": diary_prompt(s.L, s.diary, q, s.day)[-600:], "answer": a}
                return ex_qa_ob(s.L, s.diary, q, a, s.day)
        return ex_qa(s.L, q, a)

    def dream_ex(s, it):
        o = s.rng.choice(it.para + it.qa)
        return ex_text(s.L, o) if isinstance(o, str) else s.qa_ex(o[0], o[1])

    def klctx(s, d):
        """ab_klctx: up to 100 diary-format prompts (notes of days <= d) from tonight's kept dreamed questions, each with the BASE model's
        greedy answer (max_new 20), as extra KL replay: (prompt + answer + eos, loss from the answer)."""
        qs = list(dict.fromkeys(s.night_qs))
        random.Random(s.a.seed * 100 + d + 11).shuffle(qs)
        ps = [diary_prompt(s.L, s.diary, q, d) for q in qs[:100]]
        ans = s.gen(ps, 20)
        s.raw["klctx"] = [{"q": q, "base_answer": x} for q, x in list(zip(qs, ans))[:3]]
        pis = [s.L.ids(p) for p in ps]
        return [(pi + s.L.ids(x) + [s.L.eos], len(pi)) for pi, x in zip(pis, ans)]

    def nrem(s, act, cum, con, n):
        out = []
        for _ in range(n):
            if act and (not con or s.rng.random() < 0.75):
                out.append(s.dream_ex(s.rng.choices(act, cum_weights=cum)[0]))
            elif con:
                out.append(s.dream_ex(s.rng.choice(con)))
        return out

    # ---- 7. REM (current adapter, short fact sentences only; the diary then checks each dream)
    def rem(s, E, d, ci):
        a, st = s.a, Counter()
        by = defaultdict(list)
        for it in E:
            for x in {norm(it.subj), norm(it.obj)}:
                by[x].append(it)
        pairs = []
        for x, its in by.items():
            if x in GENERIC or len(its) > 12:
                continue
            for p, q in itertools.combinations(its, 2):
                if other(p, x)[1].lower() != other(q, x)[1].lower():
                    pairs.append((p, q, x))
        s.rng.shuffle(pairs)
        pairs.sort(key=lambda t: s.rem_done[frozenset((t[0].key, t[1].key))])
        pairs = pairs[:a.rem_chains]
        gist = [it for it in E if it.days >= a.gist_min_days]
        s.rng.shuffle(gist)
        gist.sort(key=lambda it: s.gist_done[it.key])
        gist = gist[:a.rem_gist]
        prompts = [chain_prompt(s.L, p.fact, q.fact) for p, q, _ in pairs] + [gist_prompt(s.L, it.fact, it.days) for it in gist]
        raw = s.gen(prompts, s.mn(40), base=False, sample=True)
        s.raw.setdefault("rem", []).extend(raw[:1] + raw[len(pairs):len(pairs) + 1])
        cand = []  # (kind, items, q, a, ctx)
        for k, ((p, q, x), txt) in enumerate(zip(pairs, raw[:len(pairs)])):
            st["chain_gen"] += 1
            r = parse_qa1(txt)
            fp, fq = other(p, x)[1], other(q, x)[1]
            if r is None and a.smoke:
                r = (f"Who is two steps from {fp}?", fq)
            if r is None:
                st["parse_fail"] += 1
                continue
            qq, aa = r
            es = [e for e in (fp, fq) if e.lower() in aa.lower()]
            other_e = fq if es and es[0] == fp else fp
            if s.leaky(qq):
                st["dropped_test_leak"] += 1
            elif len(es) != 1 or es[0].lower() in qq.lower() or other_e.lower() not in qq.lower() or x in qq.lower():
                st["dropped_bad"] += 1
            else:
                idx = sorted(set(s.diary.containing(p.subj, p.obj, d)[-2:]) | set(s.diary.containing(q.subj, q.obj, d)[-2:]))
                cand.append(("chain", (p, q), qq, es[0], s.diary.label(idx)))
        for it, txt in zip(gist, raw[len(pairs):]):
            st["gist_gen"] += 1
            r = parse_qa1(txt)
            if r is None and a.smoke:
                r = (f"Who does Sam usually see with {it.obj}?", it.subj)
            if r is None:
                st["parse_fail"] += 1
                continue
            qq, aa = r
            es = [e for e in (it.subj, it.obj) if e.lower() in aa.lower()]
            other_e = it.obj if es and es[0] == it.subj else it.subj
            if s.leaky(qq):
                st["dropped_test_leak"] += 1
            elif len(es) != 1 or es[0].lower() in qq.lower() or other_e.lower() not in qq.lower():
                st["dropped_bad"] += 1
            else:
                cand.append(("gist", (it,), qq, es[0], s.diary.label(s.diary.containing(it.subj, it.obj, d)[-4:])))
        ver = s.gen([ctx_prompt(s.L, c, q) for _, _, q, _, c in cand], 20)
        have = {(norm(x["q"]), x["a"].lower()) for x in s.rem_pool}
        for (kind, its, q, ans, c), v in zip(cand, ver):
            if not has_ans(ans, v) and not s.a.smoke:
                st["dropped_unverified"] += 1
            elif (norm(q), ans.lower()) in have:
                st["dropped_dup"] += 1
            else:
                have.add((norm(q), ans.lower()))
                s.rem_pool.append({"q": q, "a": ans, "keys": [i.key for i in its], "kind": kind, "night": d, "cycle": ci})
                st[f"{kind}_kept"] += 1
                if kind == "chain":
                    s.rem_chains.append((its[0].key, its[1].key))
                    s.rem_done[frozenset((its[0].key, its[1].key))] += 1
                else:
                    s.gist_done[its[0].key] += 1
                if len(s.examples["rem"]) < 20:
                    s.examples["rem"].append({"night": d, "cycle": ci, "kind": kind, "facts": [i.fact for i in its], "q": q, "a": ans})
        st["pool"] = len(s.rem_pool)
        return dict(st)

    # ---- 10. gate helpers
    def snapshot(s):  # trainable params, plus every delta_w (a frozen buffer in ab_ob_merge) so a reverted night restores the deltas too
        return {n: p.detach().cpu().clone() for n, p in s.pm.named_parameters() if p.requires_grad or n.endswith("delta_w")}

    def restore(s, snap):
        with torch.no_grad():
            for n, p in s.pm.named_parameters():
                if n in snap:
                    p.copy_(snap[n])

    # ---- 9. cleanup
    def cleanup(s):
        st = Counter()
        for it in list(s.items.values()):
            if not it.dead and it.fails >= 2:
                it.dead = True
                s.dropped.add(it.key)
                st["dropped_failed"] += 1
        groups = defaultdict(list)
        for it in s.items.values():
            if not it.dead:
                groups[frozenset(it.key)].append(it)
        for g in groups.values():
            if len(g) > 1:
                g.sort(key=lambda it: (-len(it.para) - len(it.qa), it.born))
                for x in g[1:]:
                    x.dead = True
                    g[0].sup_by = g[0].sup_by or x.sup_by
                    g[0].upd += [u for u in x.upd if all(u["old_key"] != v["old_key"] for v in g[0].upd)]
                    st["merged"] += 1
        return dict(st)

    # ---- the night
    def night(s, d, sched):
        a, t0, rec = s.a, time.time(), {"night": d}
        s.raw, ph, tl = {}, {}, [time.time()]
        s.day = d

        def lap(name):
            ph[name] = ph.get(name, 0) + time.time() - tl[0]
            tl[0] = time.time()
        rec["tagging"] = s.tag(d)
        s.refresh(d)
        lap("tag")
        rec["update_detection"] = s.detect(d)
        lap("update_detection")
        E = [it for it in list(s.items.values()) if s.elig(it)]
        rec["dream_stats"] = s.dream(d, E)
        lap("dream")
        pre = s.probe(E)
        s.morning(E, pre)
        lap("probe")
        cons = [it for it in E if it.consol]
        n_act = sum(1 for it in E if not it.consol)
        steps = sched[d - 1] if sched and d <= len(sched) else min(300, 40 + 4 * n_act)
        if a.smoke:
            steps = min(steps, 16)
        act = [it for it in E if not it.consol and (it.para or it.qa)]
        con = [it for it in cons if it.para or it.qa]
        cum = list(itertools.accumulate(s.prio(it) for it in act))
        rec.update({"eligible": len(E), "eligible_active": n_act, "consolidated": len(cons), "superseded_total": sum(1 for it in s.items.values() if it.sup_by and not it.dead),
                    "items_total": sum(1 for it in s.items.values() if not it.dead), "with_dreams": len(act) + len(con), "steps_planned": steps,
                    "probe_recall_pre": acc(ok for ok, _ in pre.values()), "elig_by_class": s.elig_by_class(E)})
        s.log(f"[night {d}] items {rec['items_total']} eligible {len(E)} (active {n_act}, consolidated {len(cons)}) steps {steps} probe_pre {rec['probe_recall_pre']}")
        snap = s.snapshot()
        kl_pool = s.replay
        if a.arm == "ab_klctx" and (act or con):  # KL batches are sampled from generic replay + tonight's diary-format prompts
            kl_pool = s.replay + s.klctx(d)
            rec["klctx_n"] = len(kl_pool) - len(s.replay)
            lap("klctx")
        tr = Trainer(s.L, s.pm, a, kl_pool, steps, a.seed * 100 + d)
        cyc = [steps // 4 + (1 if i < steps % 4 else 0) for i in range(4)]
        rem_stats, done, nrem_n, rem_n = [], 0, 0, 0
        if not (act or con):
            s.log(f"[night {d}] no dream content; skipping training")
        else:
            for ci, c in enumerate(cyc):
                n_nrem = c if a.arm == "ab_norem" else round(c * NREM_SHARE[ci])
                for _ in range(n_nrem):
                    tr.step(s.nrem(act, cum, con, a.bsz))
                nrem_n, done = nrem_n + n_nrem, done + n_nrem
                if c - n_nrem > 0:
                    lap("train")
                    rs = s.rem(E, d, ci)
                    lap("rem_generate")
                    rem_stats.append(rs)
                    live = [x for x in s.rem_pool if all(not s.items[k].dead and not s.items[k].sup_by for k in x["keys"])]
                    for _ in range(c - n_nrem):
                        nr = round(0.7 * a.bsz) if live else 0
                        tr.step([s.qa_ex(x["q"], x["a"]) for x in s.rng.choices(live, k=nr)] + s.nrem(act, cum, con, a.bsz - nr))
                    rem_n, done = rem_n + (c - n_nrem), done + (c - n_nrem)
                    s.cov["rem_steps"] += c - n_nrem
        lap("train")
        rec.update({"steps": done, "steps_nrem": nrem_n, "steps_rem": rem_n, "rem_stats": rem_stats, "loss_curve": tr.curve[-6:]})
        # 8. synaptic downscaling
        if a.arm == "ab_noshy" or not (act or con):
            rec["shy"], rec["shy_zeroed_frac"] = None, None
        else:
            if a.arm in DELTA_ARMS:
                rec["shy"] = shy_delta_apply(s.pm, a.shy_factor, a.shy_thresh, s.gen_t, a.arm == "ab_ob_merge")
            else:
                rec["shy"] = shy_apply(s.pm, a.shy_factor, a.shy_thresh, s.gen_t)
            rec["shy_zeroed_frac"] = rec["shy"]["zeroed_frac"]
            s.log(f"[night {d}] SHY {rec['shy']}")
            s.cov["shy"] += 1
        if a.arm in DELTA_ARMS:
            rec["delta_fro"] = delta_fro(s.pm)
            s.log(f"[night {d}] delta_fro {rec['delta_fro']:.6g}")
        rec["cleanup"] = s.cleanup()
        lap("shy_cleanup")
        # 10. morning gate
        post = s.probe(E)
        arc = score_arc(s.L, s.pm, s.arc_val, bs=max(a.gen_bs // 2, 1))["acc"]
        pre_c = acc(pre[it.key][0] for it in cons if it.key in pre)
        post_c = acc(post[it.key][0] for it in cons if it.key in post)
        why = []
        if arc < s.arc_base - 0.03 - 1e-9:
            why.append(f"arc_val {arc:.3f} < base {s.arc_base:.3f} - 0.03")
        if len(cons) >= 10 and pre_c is not None and post_c is not None and post_c < pre_c - 0.10 - 1e-9:  # <10 items: one miss is noise
            why.append(f"consolidated recall {post_c:.3f} < {pre_c:.3f} - 0.10")
        if a.force_revert == d:
            why.append("forced revert (smoke test of the gate)")
        rec.update({"arc_val": arc, "cons_recall_pre": pre_c, "cons_recall_post": post_c, "probe_recall_post": acc(ok for ok, _ in post.values()),
                    "reverted": bool(why), "revert_reason": why})
        if why:
            s.restore(snap)
            s.cov["revert"] += 1
            s.log(f"[night {d}] REVERTED: {why}")
            rec["probe_recall_post"] = rec["probe_recall_pre"]
        if a.arm in DELTA_ARMS:
            rec["delta_fro_final"] = delta_fro(s.pm)  # after the gate: a reverted night is back at the previous night's deltas
        rec["rem_pool"] = len(s.rem_pool)
        lap("gate")
        rec["phase_seconds"], rec["raw_samples"] = {k: round(v, 1) for k, v in ph.items()}, s.raw
        rec["time"] = time.time() - t0
        s.log(f"[night {d}] done steps {done} (nrem {nrem_n}, rem {rem_n}) arc_val {arc:.3f} probe_post {rec['probe_recall_post']} reverted {bool(why)} {rec['time']:.0f}s"
               + (f" delta_fro {rec['delta_fro']:.6g} -> {rec['delta_fro_final']:.6g}" if a.arm in DELTA_ARMS else ""))
        return rec

    # ---- ground-truth diagnostics (never used by the sleeper)
    def elig_by_class(s, E):
        out = {}
        for gid, cls, pr, old in s.G:
            hit = any(gt_match(it.subj, it.obj, pr + old) for it in E)
            c = out.setdefault(cls, [0, 0])
            c[0] += hit
            c[1] += 1
        return {k: {"eligible": v[0], "of": v[1]} for k, v in out.items()}

    def diagnostics(s):
        live = [it for it in s.items.values() if not it.dead]
        E = [it for it in live if s.elig(it)]
        gm = lambda it, pairs: gt_match(it.subj, it.obj, pairs)  # noqa: E731
        # tagger: mention recall / precision on user turns (precision is a lower bound: real extra facts count as false positives)
        by_cls, hit, tot, tp, nx = defaultdict(lambda: [0, 0]), 0, 0, 0, 0
        gmap = {g[0]: g for g in s.G}
        for ti, day, got in s.tag_log:
            ment = s.diary.turns[ti].get("mentions", [])
            pairs_all = [p for m in ment for p in gmap[m][2] + gmap[m][3]]
            for m in ment:
                ok = any(gt_match(sj, ob, gmap[m][2] + gmap[m][3]) for sj, ob in got)
                hit, tot = hit + ok, tot + 1
                by_cls[gmap[m][1]][0] += ok
                by_cls[gmap[m][1]][1] += 1
            nx += len(got)
            tp += sum(1 for sj, ob in got if gt_match(sj, ob, pairs_all))
        tagger = {"mention_recall": hit / max(tot, 1), "mentions": tot, "precision_lower_bound": tp / max(nx, 1), "extractions": nx,
                  "recall_by_class": {c: v[0] / max(v[1], 1) for c, v in by_cls.items()}}
        # eligibility vs class
        cls = defaultdict(lambda: Counter())
        for gid, c, pr, old in s.G:
            cls[c]["n"] += 1
            cls[c]["extracted"] += any(gm(it, pr + old) for it in live)
            cls[c]["eligible_now"] += any(gm(it, pr) for it in E)
            cls[c]["eligible_any_value"] += any(gm(it, pr + old) for it in E)
            cls[c]["superseded_old_value"] += bool(old) and any(gm(it, old) and it.sup_by for it in live)
        match_cls = Counter()
        unmatched = 0
        for it in E:
            cs = {c for gid, c, pr, old in s.G if gm(it, pr + old)}
            unmatched += not cs
            for c in cs:
                match_cls[c] += 1
        good = sum(match_cls[c] for c in ("C2", "C4", "CH", "RT"))
        elig = {"by_class": {c: dict(v) for c, v in cls.items()}, "eligible_items": len(E), "eligible_unmatched_to_ground_truth": unmatched,
                "eligible_matched_by_class": dict(match_cls), "eligible_precision_among_matched": good / max(sum(match_cls.values()), 1)}
        # update detection on changing facts
        true_ids, hit_ids = set(), set()
        false_changed = 0
        for ok_, nk, changed in s.upd_log:
            o, n = s.items[ok_], s.items[nk]
            tid = [gid for gid, c, pr, old in s.G if old and gm(o, old) and gm(n, pr)]
            if tid:
                true_ids.add(tid[0])
                if changed:
                    hit_ids.add(tid[0])
            elif changed:
                false_changed += 1
        n_ch = sum(1 for g in s.G if g[3])
        upd = {"pairs_judged": len(s.upd_log), "judged_changed": sum(c for _, _, c in s.upd_log), "ch_items": n_ch, "ch_true_pair_checked": len(true_ids),
               "ch_detected": len(hit_ids), "ch_detection_recall": len(hit_ids) / max(n_ch, 1), "false_changed": false_changed}
        # REM chains vs two-hop tests
        dreamed = s.dreamed_twohop()
        return {"tagger": tagger, "eligibility": elig, "update_detection": upd,
                "rem": {"chain_pairs_kept_total": len(s.rem_chains), "twohop_dreamed": sum(dreamed), "twohop_total": len(dreamed), "pool": len(s.rem_pool)}}

    def dreamed_twohop(s):  # for each twohop test: did a verified REM chain dream cover both of its ground-truth items?
        gmap = {g[0]: g for g in s.G}
        out = []
        for t in s.week["tests"]["twohop"]:
            a, b = (gmap[i][2] for i in t["items"][:2])
            ok = False
            for ka, kb in s.rem_chains:
                x, y = s.items[ka], s.items[kb]
                ok = ok or (gt_match(x.subj, x.obj, a) and gt_match(y.subj, y.obj, b)) or (gt_match(x.subj, x.obj, b) and gt_match(y.subj, y.obj, a))
            out.append(ok)
        return out

    def summary_items(s):
        return [{"subj": it.subj, "rel": it.rel, "obj": it.obj, "days_seen": it.days, "mentions": it.nment, "importance": it.imp, "correction": it.cor,
                 "eligible": s.elig(it), "consolidated": it.consol, "superseded_by": list(it.sup_by) if it.sup_by else None, "dead": it.dead,
                 "update_of": [u["old"] for u in it.upd], "n_paraphrases": len(it.para), "n_qa": len(it.qa), "probe": it.probe} for it in s.items.values()]


# ------------------------------------------------------------------ flat sleep (arm af)
def run_af(L, pm, args, week, diary, leak, replay, sched, out, result, log, dump):
    """Each night: dream from each of that day's user turns alone (turn in context), verify with the same turn, train the
    cumulative LoRA on that night's dreams only (KL guard). No tagging / eligibility / priority / REM / SHY / reconsolidation / gate."""
    rng = random.Random(args.seed + 3)
    days = sorted({t["day"] for t in diary.turns})
    lower_vocab, nights, ex_dreams = set(), [], []
    for d in days:
        t0 = time.time()
        turns = [t for t in diary.turns if t["day"] == d]
        for t in diary.turns:  # lowercase vocabulary of the diary so far: a capitalized word never seen lowercase is a name
            if t["day"] <= d:
                lower_vocab |= set(re.findall(r"\b[a-z][a-z'’]*\b", t["text"]))
        names = [{w for w in CAP.findall(t["text"]) if w.lower() not in lower_vocab} for t in turns]
        with pm.disable_adapter():
            raw = L.generate(pm, [af_prompt(L, d, t["text"]) for t in turns], max_new=24 if args.smoke else 400, bs=args.gen_bs, sample=True, temp=0.8)
        st, cp, cq = Counter(), [], []
        for t, nm, txt in zip(turns, names, raw):
            paras, qas = parse_dream(txt)
            nl = sorted(nm)
            if args.smoke and not paras and not qas and len(nl) >= 2:
                paras, qas = [f"{nl[0]} and {nl[1]} are connected (smoke)."], [(f"Who is linked to {nl[0]}?", nl[1])]
            if not paras and not qas:
                st["parse_fail"] += 1
            for p in paras[:K]:
                st["paraphrases_gen"] += 1
                if any(l in norm(p) for l in leak):
                    st["dropped_test_leak"] += 1
                elif not nm or sum(1 for n in nm if n.lower() in p.lower()) < min(2, len(nm)):
                    st["dropped_missing_names"] += 1
                else:
                    cp.append(p.strip())
            for q, a in qas[:K]:
                st["qa_gen"] += 1
                nq = norm(q)
                es = [n for n in nm if n.lower() in a.lower()]
                if any(l in nq or (len(nq) >= 10 and nq in l) for l in leak):
                    st["dropped_test_leak"] += 1
                elif len(es) != 1 or es[0].lower() in q.lower():
                    st["dropped_bad_answer"] += 1
                else:
                    cq.append((q.strip(), es[0], f"[Day {d}] {t['text'][:500]}"))
        with pm.disable_adapter():
            ver = L.generate(pm, [ctx_prompt(L, c, q, "A message Sam sent in chat:") for q, _, c in cq], max_new=20, bs=args.gen_bs)
        kq, seen = [], set()
        for (q, a, c), v in zip(cq, ver):
            if not has_ans(a, v) and not args.smoke:
                st["dropped_unverified"] += 1
            elif (norm(q), a) in seen:
                st["dropped_dup"] += 1
            else:
                seen.add((norm(q), a))
                kq.append((q, a))
        kp = list(dict.fromkeys(cp))
        st["paraphrases_kept"], st["qa_kept"] = len(kp), len(kq)
        if len(ex_dreams) < 20:
            ex_dreams.append({"night": d, "paraphrases": kp[:5], "qa": kq[:5]})
        steps = sched[d - 1] if sched and d <= len(sched) else 150
        if args.smoke:
            steps = min(steps, 16)
        exs = [ex_text(L, p) for p in kp] + [ex_qa(L, q, a) for q, a in kq]
        tr = Trainer(L, pm, args, replay, steps, args.seed * 100 + d)
        done = 0
        if exs:
            pool = []
            for _ in range(steps):
                batch = []
                while len(batch) < args.bsz:
                    if not pool:
                        pool = list(range(len(exs)))
                        rng.shuffle(pool)
                    batch.append(exs[pool.pop()])
                tr.step(batch)
                done += 1
        rec = {"night": d, "steps": done, "steps_planned": steps, "turns": len(turns), "n_examples": len(exs), "dream_stats": dict(st),
               "loss_curve": tr.curve[-6:], "time": time.time() - t0}
        nights.append(rec)
        log(f"[night {d}] turns {len(turns)} examples {len(exs)} steps {done} {rec['time']:.0f}s {dict(st)}")
        result["nights"], result["examples"] = nights, {"dreams": ex_dreams}
        if d in (2, 4, 7) or d == days[-1]:
            result.setdefault("curve", {})[str(d)] = fwd_recall(L, pm, week, args.gen_bs)
            log(f"[curve] night {d} forward {result['curve'][str(d)]}")
        dump(False)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=ARMS)
    ap.add_argument("--week", help="week1.json; with --smoke and no --week the built-in 2-day fixture is used")
    ap.add_argument("--out")
    ap.add_argument("--model", default="Qwen/Qwen3.5-2B")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="run the SHY refactor and delta unit checks and exit")
    ap.add_argument("--schedule", help="result_ab.json whose nights[i].steps become this arm's per-night steps (compute match)")
    ap.add_argument("--bsz", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--full-lr", type=float, default=2e-5, help="ab_ob_full only: lr of the full-rank deltas (replaces --lr)")
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--kl-weight", type=float, default=1.0)
    ap.add_argument("--replay-bsz", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tok-budget", type=int, default=TOK_BUDGET, help="padded tokens per forward; lower for a 16 GB card (same loss and gradients)")
    ap.add_argument("--gen-bs", type=int, default=32)
    ap.add_argument("--shy-factor", type=float, default=0.85)
    ap.add_argument("--shy-thresh", type=float, default=0.05)
    ap.add_argument("--max-checks", type=int, default=200, help="update-detection checks per night")
    ap.add_argument("--max-dream-items", type=int, default=160, help="cost cap: items dreamed per night (rest wait for the next night)")
    ap.add_argument("--rem-chains", type=int, default=30)
    ap.add_argument("--rem-gist", type=int, default=30)
    ap.add_argument("--gist-min-days", type=int, default=3)
    ap.add_argument("--force-revert", type=int, default=0, help="test hook: revert this night (smoke sets 2)")
    ap.add_argument("--smoke-correct", type=float, default=0.8)
    args = ap.parse_args()
    globals()["TOK_BUDGET"] = args.tok_budget
    if args.selftest:
        print(json.dumps(selftest_shy()))
        print(json.dumps({"delta": selftest_delta()}))
        return
    if not args.arm or not args.out:
        ap.error("--arm and --out are required")
    if args.smoke:
        args.bsz, args.replay_bsz, args.gen_bs = 4, 2, 4
        args.gist_min_days, args.max_dream_items, args.max_checks = 2, 12, 20
        args.force_revert = args.force_revert or 2
    elif not args.week:
        ap.error("--week is required unless --smoke")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    logf = open(out / f"log_{args.arm}.txt", "a")

    def log(m):
        print(m, flush=True)
        logf.write(m + "\n")
        logf.flush()

    if args.arm == "ab_ob_full":
        args.lr = args.full_lr  # recorded in result["args"]
        log(f"[full] lr {args.lr} (--full-lr): full-rank deltas train, LoRA frozen")
    t0 = time.time()
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.smoke else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    lm, tok = load_model(args, device, dtype)
    L = Lang(tok, args.smoke, device)
    week = json.loads(Path(args.week).read_text()) if args.week else smoke_week()
    check_week(week)
    diary = Diary(week)
    leak = {norm(x) for x in week.get("test_strings_norm", [])} | {norm(t["q"]) for k in KINDS for t in week["tests"][k]}
    days = sorted({t["day"] for t in diary.turns})
    sched = None
    if args.schedule:
        sched = [n["steps"] for n in json.loads(Path(args.schedule).read_text())["nights"]]
        log(f"[schedule] {sched}")
    result = {"arm": args.arm, "model": args.model, "smoke": args.smoke, "args": {k: v for k, v in vars(args).items() if k not in ("week", "out", "schedule")},
              "week": args.week, "n_user_turns": len(diary.turns), "days": days, "schedule": sched, "partial": True}

    def dump(final):
        result["partial"] = not final
        p = out / (f"result_{args.arm}.json" if final else f"result_{args.arm}.partial.json")
        p.write_text(json.dumps(result, indent=1, default=lambda o: sorted(o) if isinstance(o, (set, frozenset)) else str(o)))
        if final and (out / f"result_{args.arm}.partial.json").exists():
            (out / f"result_{args.arm}.partial.json").unlink()

    model, brain, pm = lm, None, None
    if args.arm not in ("a0", "ad"):
        from peft import LoraConfig, get_peft_model
        pm = get_peft_model(lm, LoraConfig(r=args.rank, lora_alpha=args.alpha, lora_dropout=0.0, target_modules=LORA_TARGETS, bias="none"))
        if args.arm in DELTA_ARMS:
            mods = setup_delta(pm, args.arm == "ab_ob_full")
            if args.arm == "ab_ob_full":
                for n, p in pm.named_parameters():
                    if "lora_" in n:
                        p.requires_grad_(False)
            # the check builds its own tiny CPU model, which the GPU box's Triton linear-attention kernels refuse; it runs in --selftest / smoke
            result["delta_selftest"] = selftest_delta() if device.type == "cpu" else {"skipped": "GPU run (checked on CPU via --selftest and smoke)"}
            log(f"[selftest] delta machinery: {result['delta_selftest']}")
            log(f"[delta] {len(mods)} modules, delta params {sum(m.base_layer.delta_w.numel() for _, m in mods):,} ({'trainable' if args.arm == 'ab_ob_full' else 'folded in nightly'})")
        result["trainable_params"] = sum(p.numel() for p in pm.parameters() if p.requires_grad)
        log(f"[lora] trainable {result['trainable_params']:,}")
        model = pm
        result["shy_selftest"] = selftest_shy(pm)  # cheap; randomizes then restores the adapter
        log(f"[selftest] SHY refactor reproduces 0.85 x dW: {result['shy_selftest']}")
        gp = generic_prompts()[:(6 if args.smoke else 200)]
        prompts = [L.render(None, g) for g in gp]
        with pm.disable_adapter():
            resp = L.generate(pm, prompts, max_new=8 if args.smoke else 48, bs=args.gen_bs)
        replay = [(L.ids(p) + L.ids(r) + [L.eos], len(L.ids(p))) for p, r in zip(prompts, resp)]
        result["replay_n"] = len(replay)
        arc_val = load_arc_val(args.smoke)
        with pm.disable_adapter():
            arc_base = score_arc(L, pm, arc_val, bs=max(args.gen_bs // 2, 1))["acc"]
        result["arc_val_base"] = arc_base
        log(f"[base] ARC-Easy validation(100) {arc_base:.3f}")
        if args.arm == "af":
            run_af(L, pm, args, week, diary, leak, replay, sched, out, result, log, dump)
        else:
            brain = Brain(L, pm, args, week, diary, leak, replay, arc_val, arc_base, log)
            nights = result["nights"] = []
            result["curve"] = {}
            for d in days:
                nights.append(brain.night(d, sched))
                if d in (2, 4, 7) or d == days[-1]:
                    result["curve"][str(d)] = fwd_recall(L, pm, week, args.gen_bs)
                    log(f"[curve] night {d} forward {result['curve'][str(d)]}")
                result["examples"] = brain.examples
                dump(False)
            result["diagnostics"] = brain.diagnostics()
            result["items"] = brain.summary_items()
            result["coverage"] = dict(brain.cov)
            log(f"[diag] {json.dumps(result['diagnostics'])}")
        pm.save_pretrained(out / "adapter")
    model.eval()
    dreamed = brain.dreamed_twohop() if brain else None
    result["scores"] = {}
    modes = {"a0": ["weights"], "ad": ["diary"]}.get(args.arm, ["weights", "diary"])
    full = args.arm in NEW_ARMS  # per-question rows + p_first, router, adapter-off diary reader
    for mode in modes:
        sc = result["scores"][mode] = score_week(L, model, week, diary, mode, args.gen_bs, dreamed, full)
        log(f"[eval:{mode}] {eval_line(sc)}")
    if full:
        with pm.disable_adapter():
            bd = result["scores"]["base_diary"] = score_week(L, pm, week, diary, "diary", args.gen_bs, dreamed, True)
        log(f"[eval:base_diary] {eval_line(bd)}")
        rt = result["scores"]["router"] = route(result["scores"]["weights"], bd, dreamed)
        log(f"[eval:router] {eval_line(rt)} frac_memory {rt['frac_memory']} acc_when_memory {rt['acc_when_memory']} acc_when_diary {rt['acc_when_diary']}")
    if args.arm != "ad":
        try:
            result["arc_easy"] = score_arc(L, model, load_arc(args.smoke), bs=max(args.gen_bs // 2, 1))
            log(f"[eval] arc_easy acc {result['arc_easy']['acc']:.3f} (n={result['arc_easy']['n']})")
        except Exception as e:  # datasets missing / offline
            result["arc_easy"] = {"error": repr(e)}
            log(f"[eval] ARC FAILED: {e!r}")
    result["wall_seconds"] = time.time() - t0
    dump(True)
    log(f"[done] {args.arm} wall {result['wall_seconds']:.0f}s -> {out}/result_{args.arm}.json")
    if args.smoke and brain:
        log(f"[coverage] {dict(brain.cov)}")


if __name__ == "__main__":
    try:
        main()
    except BaseException as e:  # leave the error where the Vast label reporter can see it (log service is unreliable)
        import traceback
        o = next((sys.argv[i + 1] for i, x in enumerate(sys.argv[:-1]) if x == "--out"), ".")
        arm = next((sys.argv[i + 1] for i, x in enumerate(sys.argv[:-1]) if x == "--arm"), "x")
        Path(o).mkdir(parents=True, exist_ok=True)
        Path(o, f"result_{arm}.error.json").write_text(json.dumps({"error": repr(e)[:300], "trace": traceback.format_exc()[-4000:]}))
        raise
