"""Sleep-B (see backbone/sleep/brain/PREREG-sleepB.md). Arms: a0 (base), ad (base + diary search), ab (brain-like sleep),
af (flat sleep, AB's step counts), one-change ablations ab_norem / ab_noshy / ab_flatprio / ab_all, and the addendum-1 fixes
ab_ob (open-book rehearsal) / ab_klctx (read-the-notes KL leash), see PREREG-sleepB-addendum1.md. The new arms also save every
per-question row + p_first in each scoring mode and score the router R and the adapter-off diary reader (scores.router, scores.base_diary).
Full-rank arms, one change each from ab_ob: ab_ob_full (every LoRA-target Linear gets a trainable full-rank delta_w, LoRA frozen, lr
--full-lr) and ab_ob_merge (LoRA trains as in ab_ob; each night's SHY step folds it into a full-rank delta_w and resets it). delta_w is
added by a forward hook on the base Linear and switched off inside pm.disable_adapter(), so "base" stays the original pretrained model.
Two single changes from ab_ob_full (addendum 3): ab_ob_full_s (gentler step: lr --full-lr-small) and ab_ob_local (targeted plasticity, synaptic
tagging: each night only K = (number of LoRA parameters) delta entries may change, the ones with the largest |grad| on tonight's own practice
batches; elementwise SHY instead of the SVD one, since an SVD would make the sparse change dense).

Addendum 4 (PREREG-sleepB-addendum4.md), one change each from ab_ob, all LoRA-only: ab_ob_rot (each night only one quarter of the layers' LoRA
trains, quarter (night-1) % 4; SHY still trims all), ab_ob_twist (the base model also writes 2 strange dream-like scenes per item, kept if they pass
the entity / leak / no-older-value / answerable checks, and they join the item's practice texts), ab_ob_ther (salient items: 2x replay priority and loss weight 0.5),
ab_ob_guess (the pre-training probe also gives the first-token confidence c; a right answer with c < 1 multiplies the item's priority by 1 + 2(1 - c)).
Addendum 5 (PREREG-sleepB-addendum5.md), the night's work scales with the chip: work scale s multiplies the night's training steps, the dreams per
item (round(4 s) paraphrases and Q&A, and the generation length), the item cap (160 s), REM chains and gist dreams (30 s each). --budget-scale pins s;
--night-budget-s B instead times a benchmark at the start of each night and uses s = clip(B / R, 0.25, 4) (R: seconds the reference night would take
here); with neither, s = 1 and the night is exactly ab_ob's. ab_ob_b2 = ab_ob with s = 2.
Addendum 6 (PREREG-sleepB-addendum6.md), the winners combined on Week-2: ab_ob_win = s = 2 + ab_ob_guess's priority rule + ab_ob_twist's scenes; ab_ob_winp = the same with
2 more ORDINARY paraphrases (para2_prompt, same checks, dream_stats["twist_mode"] = "plain") in the scenes' place.

--q4-base (Mac deployment study, thread "Fit sleep on an 8 GB M2"): right after load_model, before LoRA and any base use, every nn.Linear and
nn.Embedding weight is replaced in place by a quantize-dequantize copy in MLX's affine 4-bit scheme (groups of --q4-group along the input dim,
scale = (max-min)/(2^bits-1), bias = min, both rounded to the model dtype), so the frozen base is what an MLX 4-bit model would be. Off: nothing changes.

  python backbone/sleep/brain/sleepb.py --arm ab --week backbone/sleep/brain/data/week1.json --out out/sleepb/ab
  python backbone/sleep/brain/sleepb.py --arm af --week ... --out out/sleepb/af --schedule out/sleepb/ab/result_ab.json
  python backbone/sleep/brain/sleepb.py --arm ab --smoke --out /tmp/x      # CPU, tiny random qwen3_5, built-in 2-day fixture
  python backbone/sleep/brain/sleepb.py --selftest                         # SHY refactor + delta (full / merge) + local-plasticity + weighted-loss + rotation + time-budget + stale-filter unit checks

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
LOSS_SCALE = [1.0]  # --dtype fp16 sets 1024 (Trainer.step only; every other path is unchanged)
NREM_SHARE = [0.80, 0.65, 0.50, 0.35]
KINDS = ("forward", "reverse", "twohop", "changed", "routine")
ADD4_ARMS = ("ab_ob_rot", "ab_ob_twist", "ab_ob_ther", "ab_ob_guess")  # addendum 4: LoRA + open-book, one change each
WIN_ARMS = ("ab_ob_win", "ab_ob_winp")  # addendum 6: work scale 2 + guess priority + extra texts (win: twisted scenes, winp: ordinary paraphrases)
NEW_ARMS = ("ab_ob", "ab_klctx", "ab_ob_full", "ab_ob_merge", "ab_ob_full_s", "ab_ob_local", *ADD4_ARMS, "ab_ob_b2", *WIN_ARMS)
OB_ARMS = ("ab_ob", "ab_ob_full", "ab_ob_merge", "ab_ob_full_s", "ab_ob_local", *ADD4_ARMS, "ab_ob_b2", *WIN_ARMS)  # open-book rehearsal (Brain.qa_ex)
GUESS_ARMS = ("ab_ob_guess", *WIN_ARMS)  # first-token confidence and the dopamine priority
TWIST_ARMS = ("ab_ob_twist", "ab_ob_win")  # twisted dream-like scenes join the item's texts
EXTRA_ARMS = (*TWIST_ARMS, "ab_ob_winp")  # Brain.twist runs (winp: with ordinary paraphrases)
B2_ARMS = ("ab_ob_b2", *WIN_ARMS)  # work scale 2 unless --budget-scale says otherwise
DELTA_ARMS = ("ab_ob_full", "ab_ob_merge", "ab_ob_full_s", "ab_ob_local")
TRAIN_DELTA_ARMS = ("ab_ob_full", "ab_ob_full_s", "ab_ob_local")  # delta_w trains, LoRA frozen (ab_ob_merge: LoRA trains, delta only changes by the fold)
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


def nrem_prompt(L, ctx, it, k=K):  # k: paraphrases and Q&A pairs per item (K; round(K s) at work scale s)
    u = (f"Messages Sam sent in chat, newest first, labelled by day. If they disagree, the newest message is true.\n{ctx}\n\n"
         f"Focus on the fact linking \"{it.subj}\" and \"{it.obj}\". Write {k} paraphrases of the CURRENT fact (short standalone sentences, "
         f"different wording, naming both) and {k} question-answer pairs about it. Cover both directions: some questions should ask about one "
         f"name, some about the other. Each answer must be a single name from the fact. Reply with only JSON of the form "
         f"{{\"paraphrases\": [\"...\"], \"qa\": [{{\"q\": \"...\", \"a\": \"...\"}}]}}")
    return L.render("You are a careful assistant that studies facts.", u)


def twist_prompt(L, ctx, it):  # ab_ob_twist (Hoel's overfitted brain): same facts, strange dream-like settings
    u = (f"Messages Sam sent in chat, newest first, labelled by day. If they disagree, the newest message is true.\n{ctx}\n\n"
         f"Focus on the fact \"{it.subj} {it.rel} {it.obj}\". Write 2 short dream-like scenes (1-3 sentences each) in which this fact stays "
         f"true, but the setting and the wording are odd and surreal, the way a dream is. Each scene must name both \"{it.subj}\" and "
         f"\"{it.obj}\". Reply with one scene per line, numbered 1 and 2, and nothing else.")
    return L.render("You are a careful assistant that studies facts.", u)


def para2_prompt(L, ctx, it):  # ab_ob_winp: twist_prompt's control, 2 more ORDINARY paraphrases (same structure and output format)
    u = (f"Messages Sam sent in chat, newest first, labelled by day. If they disagree, the newest message is true.\n{ctx}\n\n"
         f"Focus on the fact \"{it.subj} {it.rel} {it.obj}\". Write 2 short ordinary paraphrases (1-3 sentences each) in which this fact stays "
         f"true, in plain everyday wording and a normal setting, each different from the other. Each paraphrase must name both \"{it.subj}\" and "
         f"\"{it.obj}\". Reply with one paraphrase per line, numbered 1 and 2, and nothing else.")
    return L.render("You are a careful assistant that studies facts.", u)


def parse_scenes(txt):  # numbered lines -> scene texts (at most 2)
    out = []
    for ln in txt.splitlines():
        m = re.match(r"^[\s*#>-]*(?:scene\s*)?\d+\s*[.):*-]+\s*(.+)$", ln, re.I)
        if m and m.group(1).strip(" *\"'"):
            out.append(m.group(1).strip(" *\"'"))
    return out[:2]


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


def lm_masks(L, mb):  # (ids, attention mask, bool mask of the shifted target positions) of a micro-batch of (ids, loss_start[, weight]) examples
    ids, mask = L.pad_right([b[0] for b in mb])
    lm = torch.zeros_like(mask)
    for r, (e, st, *_) in enumerate(mb):
        lm[r, st:len(e)] = 1
    return ids, mask, lm[:, 1:].bool()


class Trainer:
    """One night of LoRA training: fresh AdamW, cosine lr over `steps`, CE on the batch + KL guard on generic replay vs adapter-disabled base.
    A batch entry is (ids, loss_start) or (ids, loss_start, weight); only a batch with some weight != 1 (or force_w) takes the weighted path."""

    def __init__(s, L, pm, args, replay, steps, seed):
        s.L, s.pm, s.a, s.replay = L, pm, args, replay
        s.params = [p for p in pm.parameters() if p.requires_grad]
        s.opt = torch.optim.AdamW(s.params, lr=args.lr, weight_decay=0.0)
        s.n, s.i, s.rng = max(steps, 1), 0, random.Random(seed)
        s.curve = []
        s.force_w, s.wsteps, s.wex = False, 0, 0  # force_w: test hook; wsteps / wex: weighted-path steps and examples with weight != 1

    def masks(s, mb):
        return lm_masks(s.L, mb)

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
        weighted = s.force_w or any(len(x) > 2 and x[2] != 1 for x in batch)
        s.opt.zero_grad(set_to_none=True)
        if len(gb) == 1 and len(gr) <= 1 and not weighted:  # the stage-1 path (short closed-book examples), unchanged
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
            (loss * LOSS_SCALE[0]).backward()
        else:  # split: sums over micro-batches divided by the full batch's target count, so loss and gradients match
            ntgt = sum(len(e) - max(st, 1) for e, st, *_ in batch)
            ce_sum = 0.0
            for mb in gb:
                ids, mask, tm = s.masks(mb)
                lg = s.pm(input_ids=ids, attention_mask=mask).logits[:, :-1][tm].float()
                if weighted:  # sum over examples of weight x (that example's target-token CE sum), / the batch's target count
                    w = torch.tensor([x[2] if len(x) > 2 else 1.0 for x in mb], device=ids.device)[:, None].expand_as(tm)[tm]
                    part = (F.cross_entropy(lg, ids[:, 1:][tm], reduction="none") * w).sum() / ntgt
                else:
                    part = F.cross_entropy(lg, ids[:, 1:][tm], reduction="sum") / ntgt
                (part * LOSS_SCALE[0]).backward()
                ce_sum += float(part.detach())
            ce = torch.tensor(ce_sum)
            if rb:
                npos = sum(len(e) - max(st, 1) for e, st, *_ in rb)
                for mb in gr:
                    rids, rmask, rt = s.masks(mb)
                    cur = s.pm(input_ids=rids, attention_mask=rmask).logits[:, :-1][rt].float()
                    with torch.no_grad(), s.pm.disable_adapter():
                        ref = s.pm(input_ids=rids, attention_mask=rmask).logits[:, :-1][rt].float()
                    part = F.kl_div(F.log_softmax(cur, -1), F.log_softmax(ref, -1), log_target=True, reduction="sum") / npos
                    (a.kl_weight * part * LOSS_SCALE[0]).backward()
                    kl_v += float(part.detach())
        if LOSS_SCALE[0] != 1.0:  # --dtype fp16 (T4): static loss scale; unscale, and skip a step whose gradients overflowed
            gs = [p.grad for p in s.params if p.grad is not None]
            for g in gs:
                g.div_(LOSS_SCALE[0])
            if not all(bool(torch.isfinite(g).all()) for g in gs):
                s.overflow = getattr(s, "overflow", 0) + 1
                s.opt.zero_grad(set_to_none=True)
                s.i += 1
                return
        torch.nn.utils.clip_grad_norm_(s.params, 1.0)
        s.opt.step()
        s.i += 1
        if weighted:
            s.wsteps += 1
            s.wex += sum(1 for x in batch if len(x) > 2 and x[2] != 1)
        if s.i % 10 == 1 or s.i == s.n:
            s.curve.append({"step": s.i, "ce": float(ce.detach()), "kl": kl_v, "lr": lr})
        s.pm.eval()


# ------------------------------------------------------------------ synaptic downscaling (SHY)
def lora_mods(pm):
    return [(n, m) for n, m in pm.named_modules() if hasattr(m, "lora_A") and "default" in m.lora_A]


def layer_of(name):
    return int(re.search(r"layers\.(\d+)\.", name).group(1))


def rot_set(pm, q):
    """ab_ob_rot: only the LoRA params of layers in quarter q (of 4 equal contiguous blocks, boundaries q * n // 4) keep requires_grad; q None:
    all LoRA params trainable again. Returns {"quarter", "layers": [lo, hi) half-open, "trainable_params"}; n, the layer count, is read off the LoRA module names."""
    mods = lora_mods(pm)
    n = 1 + max(layer_of(nm) for nm, _ in mods)
    lo, hi = (0, n) if q is None else (q * n // 4, (q + 1) * n // 4)
    cnt = 0
    for nm, m in mods:
        on = lo <= layer_of(nm) < hi
        for p in (m.lora_A["default"].weight, m.lora_B["default"].weight):
            p.requires_grad_(on)
            cnt += p.numel() * on
    return {"quarter": q, "layers": [lo, hi], "trainable_params": cnt}


@contextlib.contextmanager
def seeded_rng(seed, device):  # sample under a fixed seed; the global torch RNG state (CPU, and CUDA when used) is put back afterwards
    cpu = torch.get_rng_state()
    cuda = torch.cuda.get_rng_state_all() if device.type == "cuda" else None
    torch.manual_seed(seed)
    try:
        yield
    finally:
        torch.set_rng_state(cpu)
        if cuda is not None:
            torch.cuda.set_rng_state_all(cuda)


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


def setup_delta(pm, train, masked=False, dtype=torch.float32):
    """Give every LoRA-target Linear an fp32 zero delta_w (its weight's shape) on its base_layer; a forward hook adds F.linear(x, delta_w)
    to the layer output while _DELTA["on"]. train: delta_w is trainable (ab_ob_full / _full_s / _local); else it only changes by the nightly
    fold (ab_ob_merge). masked (ab_ob_local, needs train): also a tensor hook on each delta_w that multiplies its incoming grad by
    base_layer.delta_mask (bool, set by the nightly tagging; None = no mask), so masked-out entries get exactly zero grad and zero AdamW update.
    pm.disable_adapter (an instance attribute shadowing the peft method) also switches the deltas off and restores the previous switch on
    exit (nesting-safe), so every "base" use (dreaming, tagging, KL reference, ARC base, base_diary) stays the original pretrained model."""
    mods = lora_mods(pm)
    for _, m in mods:
        bl = m.base_layer
        bl.delta_w = torch.nn.Parameter(torch.zeros(bl.weight.shape, dtype=dtype, device=bl.weight.device), requires_grad=train)
        if masked and train:
            bl.delta_mask = None
            bl.delta_w.register_hook(lambda g, bl=bl: g if bl.delta_mask is None else g * bl.delta_mask)

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


def delta_nnz(pm):  # total number of nonzero delta entries
    return sum(int(m.base_layer.delta_w.detach().count_nonzero()) for _, m in lora_mods(pm))


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
def shy_elem(W, factor, thresh):
    """Elementwise SHY on one delta matrix, in place (ab_ob_local; an SVD would make the sparse change dense): W <- factor x W, then every
    entry with |W| < thresh x max|W| (of the scaled W) is zeroed. Returns n_zeroed (nonzero entries pruned), nonzero_before, nonzero_after,
    energy_before, energy_after (sums of squares, float64)."""
    nb, eb = int(W.count_nonzero()), float(W.double().pow(2).sum())
    W.mul_(factor)
    W.masked_fill_(W.abs() < thresh * W.abs().max(), 0)
    na = int(W.count_nonzero())
    return nb - na, nb, na, eb, float(W.double().pow(2).sum())


@torch.no_grad()
def shy_elem_apply(pm, factor, thresh):
    """Nightly SHY for ab_ob_local: shy_elem on every delta_w. Stats like shy_apply: modules, n_nonzero_before / after, zeroed (+ _frac of the
    nonzero entries pruned), energy_ratio."""
    nz = nb = na = 0
    e0 = e1 = 0.0
    mods = lora_mods(pm)
    for _, m in mods:
        z, b, a, ea, eb = shy_elem(m.base_layer.delta_w.data, factor, thresh)
        nz, nb, na, e0, e1 = nz + z, nb + b, na + a, e0 + ea, e1 + eb
    return {"modules": len(mods), "n_nonzero_before": nb, "n_nonzero_after": na, "zeroed": nz, "zeroed_frac": nz / max(nb, 1), "energy_ratio": e1 / max(e0, 1e-12)}


def tag_grads(L, pm, batches):
    """ab_ob_local tagging, step 1: |grad| of every delta_w summed over the practice `batches` (lists of (ids, loss_start)). CE exactly as
    Trainer.step (micro-batch sums / the batch's target count, so memory is the training step's); masks are cleared first, so the plain
    gradient is seen; grads are zeroed after each batch. Returns ([fp32 |grad| sum per module, lora_mods order], mean CE)."""
    dws = []
    for _, m in lora_mods(pm):
        m.base_layer.delta_mask = None
        dws.append(m.base_layer.delta_w)
    acc, ces = [torch.zeros_like(p) for p in dws], []
    pm.zero_grad(set_to_none=True)  # the last training step's grads are still on the params
    pm.train()
    for batch in batches:
        if not batch:
            continue
        ntgt, ce = sum(len(e) - max(st, 1) for e, st, *_ in batch), 0.0
        for mb in groups(batch):
            ids, mask, tm = lm_masks(L, mb)
            part = F.cross_entropy(pm(input_ids=ids, attention_mask=mask).logits[:, :-1][tm].float(), ids[:, 1:][tm], reduction="sum") / ntgt
            part.backward()
            ce += float(part.detach())
        ces.append(ce)
        with torch.no_grad():
            for a, p in zip(acc, dws):
                if p.grad is not None:
                    a += p.grad.abs()
        pm.zero_grad(set_to_none=True)
    pm.eval()
    return acc, mean(ces)


@torch.no_grad()
def pick_mask(accs, k, gen, n_sample=4_000_000):
    """ab_ob_local tagging, step 2: bool masks keeping about the k largest entries over all of `accs` without sorting them all. Threshold =
    the (1 - k/total) quantile of the entries themselves (total <= n_sample) or of n_sample entries drawn uniformly over all tensors (count
    per tensor proportional to its size, torch.randint on the CPU generator gen). Entries with no gradient (0) are never kept. Returns (masks, thr)."""
    sizes = [a.numel() for a in accs]
    total = sum(sizes)
    if k >= total:
        return [a > 0 for a in accs], 0.0
    if total <= n_sample:
        vals = torch.cat([a.flatten() for a in accs])
    else:
        vals = torch.cat([a.flatten()[torch.randint(0, n, (max(1, round(n_sample * n / total)),), generator=gen).to(a.device)] for a, n in zip(accs, sizes)])
    thr = float(vals.kthvalue(min(max(round((1 - k / total) * vals.numel()), 1), vals.numel())).values)
    return [(a >= thr) if thr > 0 else (a > 0) for a in accs], thr


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


@torch.no_grad()
def selftest_elem():
    """Pure-tensor checks for ab_ob_local: (i) shy_elem with thresh 0 gives exactly factor x W; with thresh 0.05 it zeroes exactly the entries
    below 0.05 x max of the scaled W, keeps the rest at factor x W, and its stats match; (ii) pick_mask keeps about k entries on the exact
    path and on the sampled path, and never keeps a zero."""
    g = torch.Generator().manual_seed(0)
    out = {}
    for shape in [(64, 48), (4, 64), (32, 8), (128, 128)]:
        W = torch.randn(*shape, generator=g)
        W[0, :3] = 1e-4
        W0 = W.clone()
        z, nb, na, _, _ = shy_elem(W0, 0.85, 0.0)
        assert z == 0 and nb == na == W.numel() and torch.allclose(W0, 0.85 * W, rtol=1e-6, atol=0), (shape, z, nb, na)
        E = 0.85 * W
        thr = 0.05 * E.abs().max()
        E = E.masked_fill(E.abs() < thr, 0)
        W1 = W.clone()
        z, nb, na, eb, ea = shy_elem(W1, 0.85, 0.05)
        assert torch.allclose(W1, E, rtol=1e-6, atol=0) and bool(((W1 != 0) == (E != 0)).all()), shape
        assert z == nb - na == int((E == 0).sum()) > 0 and abs(ea / eb - float((E.double() ** 2).sum() / (W.double() ** 2).sum())) < 1e-9, (shape, z, ea / eb)
        assert 0.6 < ea / eb < 0.85 ** 2 + 1e-9, ea / eb  # factor^2 minus the pruned energy
    out["shy_elem_ok"] = True
    r = lambda *sh: torch.rand(*sh, generator=g)  # noqa: E731
    kept = lambda ms: sum(int(m.sum()) for m in ms)  # noqa: E731
    accs = [r(100, 50), r(30, 70), r(64, 64)]
    ms, _ = pick_mask(accs, 560, g)
    out["pick_exact_kept_of_560"] = kept(ms)
    assert abs(out["pick_exact_kept_of_560"] - 560) <= 2, out
    accs = [r(400, 500), r(300, 300), r(100, 1000)]
    ms, _ = pick_mask(accs, 3900, torch.Generator().manual_seed(1), n_sample=20000)
    out["pick_sampled_kept_of_3900"] = kept(ms)
    assert abs(out["pick_sampled_kept_of_3900"] - 3900) < 0.4 * 3900, out
    assert kept(pick_mask([torch.zeros(50), torch.zeros(60)], 10, g)[0]) == 0
    assert kept(pick_mask([torch.cat([torch.zeros(500), r(500) + 0.1])], 800, g)[0]) == 500  # only entries with a gradient
    return out


def selftest_local():
    """ab_ob_local machinery on its own tiny CPU smoke model (the real model is never touched; global RNG restored): (i) with no mask the grad
    hook passes the gradient through; (ii) with a random mask the masked-out entries of every delta_w get exactly zero grad and the masked-in
    ones keep the plain gradient; (iii) two clipped AdamW steps (weight decay 0, as Trainer) leave masked-out entries bit-identical and move
    masked-in ones; (iv) tag_grads clears the masks and any stale grads, returns the plain |grad| sums, leaves no .grad, and pick_mask keeps about k."""
    from argparse import Namespace
    from peft import LoraConfig, get_peft_model
    out, g = {}, torch.Generator().manual_seed(0)
    rng_state = torch.get_rng_state()
    try:
        cpu = torch.device("cpu")
        lm, tok = load_model(Namespace(smoke=True, seed=0), cpu, torch.float32)
        L = Lang(tok, True, cpu)
        pm = get_peft_model(lm, LoraConfig(r=8, lora_alpha=16, lora_dropout=0.0, target_modules=LORA_TARGETS, bias="none"))
        mods = setup_delta(pm, True, masked=True)
        for n, p in pm.named_parameters():
            if "lora_" in n:
                p.requires_grad_(False)
        dws = [m.base_layer.delta_w for _, m in mods]
        ids = torch.randint(4, 200, (2, 12), generator=g)

        def grads():
            pm.zero_grad(set_to_none=True)
            lg = pm(input_ids=ids).logits[:, :-1].float()
            F.cross_entropy(lg.reshape(-1, lg.shape[-1]), ids[:, 1:].reshape(-1)).backward()
            return [p.grad.clone() for p in dws]

        pm.train()
        plain = grads()  # no mask yet
        assert all(m.base_layer.delta_mask is None for _, m in mods) and all(float(x.abs().sum()) > 0 for x in plain)
        masks = [torch.rand(p.shape, generator=g) < 0.1 for p in dws]
        for (_, m), mk in zip(mods, masks):
            m.base_layer.delta_mask = mk
        got = grads()
        out["modules"], out["masked_in"], out["entries"] = len(mods), sum(int(mk.sum()) for mk in masks), sum(mk.numel() for mk in masks)
        for x, y, mk in zip(got, plain, masks):
            assert bool((x[~mk] == 0).all()) and torch.allclose(x[mk], y[mk], rtol=1e-5, atol=1e-9), "mask hook"
        out["masked_out_grad_exactly_zero"] = True
        before = [p.detach().clone() for p in dws]
        opt = torch.optim.AdamW(dws, lr=1e-2, weight_decay=0.0)
        for _ in range(2):
            grads()
            torch.nn.utils.clip_grad_norm_(dws, 1.0)
            opt.step()
        moved = 0
        for p, b, mk in zip(dws, before, masks):
            assert torch.equal(p.detach()[~mk], b[~mk]), "AdamW moved a masked-out entry"
            moved += int((p.detach()[mk] != b[mk]).sum())
        assert moved > 0
        out["adamw_masked_out_update_exactly_zero"], out["adamw_masked_in_moved"] = True, moved
        batches = [[ex_text(L, f"Zelmir lives in Kelmira number {i} and {j}.") for j in range(4)] for i in range(3)]
        grads()  # leaves masked grads on the params, like the last training step of a night
        accs, ce = tag_grads(L, pm, batches)  # masks and stale grads still there: tag_grads must clear both
        assert all(m.base_layer.delta_mask is None for _, m in mods) and all(p.grad is None for p in dws), "tag_grads left a mask / grad"
        clean, _ = tag_grads(L, pm, batches)
        assert all(torch.equal(x, y) for x, y in zip(accs, clean)), "tag_grads picked up stale grads"
        assert all(bool((a >= 0).all()) for a in accs) and any(bool((a[~mk] > 0).any()) for a, mk in zip(accs, masks)), "tag_grads saw a masked grad"
        total = sum(a.numel() for a in accs)
        ms, thr = pick_mask(accs, total // 50, g)
        out["tag_ce"], out["tag_kept_of_k"], out["tag_k"] = ce, sum(int(m.sum()) for m in ms), total // 50
        assert abs(out["tag_kept_of_k"] - out["tag_k"]) <= 0.05 * out["tag_k"] + 2, out
        pm.eval()
        return out
    finally:
        torch.set_rng_state(rng_state)


def selftest_weighted():
    """ab_ob_ther's weighted loss on its own tiny CPU smoke model (the real model is never touched; global RNG and TOK_BUDGET restored). One
    Trainer step at lr 0 leaves the clipped gradient on the params and its CE in tr.curve. (i) A batch whose weights are all 1 never takes the
    weighted path and is bit-identical to the same batch without weights; forcing the weighted path with all weights 1 matches the unweighted
    path to 1e-6 (CE, gradient relative to its largest entry), with and without the KL guard. (ii) All weights 0.5 give half the CE; mixed weights
    give sum_e w_e x (example e's target CE sum) / (the batch's target count), and the gradient equals the same sum of one-example gradients
    (clipped alike). (iii) The same with the batch split into micro-batches."""
    from argparse import Namespace
    from peft import LoraConfig, get_peft_model
    out, g = {}, torch.Generator().manual_seed(0)
    rng_state, tb = torch.get_rng_state(), TOK_BUDGET
    try:
        cpu = torch.device("cpu")
        lm, tok = load_model(Namespace(smoke=True, seed=0), cpu, torch.float32)
        L = Lang(tok, True, cpu)
        pm = get_peft_model(lm, LoraConfig(r=8, lora_alpha=16, lora_dropout=0.0, target_modules=LORA_TARGETS, bias="none"))
        for _, m in lora_mods(pm):  # B is zero at init: make the LoRA matter, so the gradients reach A as well
            m.lora_B["default"].weight.data.normal_(0, 0.05, generator=g)
        params = [p for p in pm.parameters() if p.requires_grad]
        saved = [p.detach().clone() for p in params]
        base = [ex_text(L, f"Zelmir lives in Kelmira number {i}, near the old harbour.") if i % 2 else ex_qa(L, f"Where does Zelmir{'x' * i} live?", "Kelmira")
                for i in range(6)]
        replay = [ex_text(L, f"A generic sentence number {i} about the weather.") for i in range(3)]
        ntgt = sum(len(e) - max(st, 1) for e, st in base)
        mixed = [0.5, 1.0, 1.0, 0.5, 1.0, 0.5]

        def run(batch, kl=False, force=False, budget=None):
            globals()["TOK_BUDGET"] = budget or tb
            tr = Trainer(L, pm, Namespace(lr=0.0, kl_weight=1.0 if kl else 0.0, replay_bsz=2), replay if kl else [], 1, 0)
            tr.force_w = force
            tr.step(batch)
            with torch.no_grad():
                for p, s0 in zip(params, saved):
                    assert torch.equal(p, s0), "lr 0 moved a parameter"
            return tr.curve[0], [p.grad.clone() for p in params], tr

        def ref(w):  # one-example passes: CE sum x weight / ntgt, gradients summed, clipped as Trainer does
            pm.zero_grad(set_to_none=True)
            pm.train()
            ce = 0.0
            for (e, st), wi in zip(base, w):
                ids, mask, tm = lm_masks(L, [(e, st)])
                part = F.cross_entropy(pm(input_ids=ids, attention_mask=mask).logits[:, :-1][tm].float(), ids[:, 1:][tm], reduction="sum") * wi / ntgt
                part.backward()
                ce += float(part.detach())
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            pm.eval()
            return ce, [p.grad.clone() for p in params]

        rel = lambda xs, ys: max(float((x - y).abs().max()) for x, y in zip(xs, ys)) / max(float(y.abs().max()) for y in ys)  # noqa: E731
        wb = lambda ws: [e + (w,) for e, w in zip(base, ws)]  # noqa: E731
        for kl in (False, True):
            c0, g0, t0 = run(base, kl)
            c1, g1, t1 = run(wb([1.0] * 6), kl)
            assert t1.wsteps == 0 and c1["ce"] == c0["ce"] and c1["kl"] == c0["kl"] and all(torch.equal(x, y) for x, y in zip(g0, g1)), "all-1 weights left the unweighted path"
            c2, g2, t2 = run(wb([1.0] * 6), kl, force=True)
            out[f"force_all1_kl{int(kl)}"] = {"ce_rel": abs(c2["ce"] - c0["ce"]) / c0["ce"], "kl_abs": abs(c2["kl"] - c0["kl"]), "grad_rel": rel(g2, g0)}
            assert t2.wsteps == 1 and out[f"force_all1_kl{int(kl)}"]["ce_rel"] < 1e-6 and out[f"force_all1_kl{int(kl)}"]["grad_rel"] < 1e-6 and abs(c2["kl"] - c0["kl"]) < 1e-6, out
        half, _, th = run(wb([0.5] * 6))
        out["half_ce_ratio"] = half["ce"] / c0["ce"]
        assert th.wsteps == 1 and th.wex == 6 and abs(out["half_ce_ratio"] - 0.5) < 1e-6, out
        c_ref, g_ref = ref(mixed)
        for name, budget in (("mixed", None), ("mixed_split", 2 * max(len(e) for e, _ in base))):
            if budget:
                assert len(groups(base, budget)) > 1, "the split check needs several micro-batches"
            c3, g3, t3 = run(wb(mixed), budget=budget)
            out[name] = {"ce_vs_reference": abs(c3["ce"] - c_ref) / c_ref, "grad_vs_reference_rel": rel(g3, g_ref), "micro_batches": len(groups(base, budget or tb))}
            assert t3.wsteps == 1 and t3.wex == 3 and out[name]["ce_vs_reference"] < 1e-5 and out[name]["grad_vs_reference_rel"] < 1e-5, out
        c_all1, _ = ref([1.0] * 6)
        assert abs(c_all1 - c0["ce"]) < 1e-5 * c_all1, (c_all1, c0["ce"])  # the reference at weight 1 is the plain CE
        out["mixed_over_unweighted_ce"] = c_ref / c_all1  # < 1: three of six examples count half
        assert out["mixed_over_unweighted_ce"] < 1
        return out
    finally:
        globals()["TOK_BUDGET"] = tb
        torch.set_rng_state(rng_state)


def selftest_rot():
    """ab_ob_rot machinery on its own tiny CPU smoke model (8 layers; the real model is never touched; global RNG restored): (i) quarter q trains
    exactly layers [q*n//4, (q+1)*n//4) and the four quarters partition the LoRA params; (ii) a Trainer built after rot_set sees only them and two
    steps move only them; (iii) a snapshot taken before the freeze, then a training step and SHY (which trims EVERY module) and Brain.restore put
    every LoRA param back (a snapshot taken after the freeze would miss the rest); (iv) rot_set(pm, None) makes all trainable again."""
    from argparse import Namespace
    from types import SimpleNamespace
    from peft import LoraConfig, get_peft_model
    out, g = {}, torch.Generator().manual_seed(0)
    rng_state = torch.get_rng_state()
    try:
        cpu = torch.device("cpu")
        lm, tok = load_model(Namespace(smoke=True, seed=0), cpu, torch.float32)
        L = Lang(tok, True, cpu)
        pm = get_peft_model(lm, LoraConfig(r=8, lora_alpha=16, lora_dropout=0.0, target_modules=LORA_TARGETS, bias="none"))
        for _, m in lora_mods(pm):
            m.lora_B["default"].weight.data.normal_(0, 0.05, generator=g)
        ps = [(layer_of(nm), p) for nm, m in lora_mods(pm) for p in (m.lora_A["default"].weight, m.lora_B["default"].weight)]
        n = 1 + max(l for l, _ in ps)
        orig = [p.detach().clone() for _, p in ps]
        brain = SimpleNamespace(pm=pm)
        snap = Brain.snapshot(brain)  # all LoRA params are trainable here
        assert len(snap) == len(ps)
        batch = [ex_text(L, f"Zelmir lives in Kelmira number {i}, near the old harbour.") for i in range(4)]
        tot = 0
        for q in range(4):
            lo, hi = q * n // 4, (q + 1) * n // 4
            r = rot_set(pm, q)
            assert r == {"quarter": q, "layers": [lo, hi], "trainable_params": r["trainable_params"]} and r["trainable_params"] > 0, r
            assert all(p.requires_grad == (lo <= l < hi) for l, p in ps), q
            assert r["trainable_params"] == sum(p.numel() for l, p in ps if lo <= l < hi)
            tot += r["trainable_params"]
            before = [p.detach().clone() for _, p in ps]
            tr = Trainer(L, pm, Namespace(lr=1e-2, kl_weight=0.0, replay_bsz=2), [], 2, 0)
            assert sum(p.numel() for p in tr.params) == r["trainable_params"]
            tr.step(batch)
            tr.step(batch)
            moved = [not torch.equal(p.detach(), b) for (_, p), b in zip(ps, before)]
            assert not any(mv for (l, _), mv in zip(ps, moved) if not lo <= l < hi) and any(mv for (l, _), mv in zip(ps, moved) if lo <= l < hi), q
            if q == 3:
                out["snapshot_after_freeze_params"] = len(Brain.snapshot(brain))  # vs len(ps): why the snapshot comes before the freeze
                assert out["snapshot_after_freeze_params"] < len(ps)
        assert tot == sum(p.numel() for _, p in ps)
        shy_apply(pm, 0.85, 0.05, g)
        assert any(not torch.equal(p.detach(), o) for (_, p), o in zip(ps, orig))
        Brain.restore(brain, snap)
        assert all(torch.equal(p.detach(), o) for (_, p), o in zip(ps, orig)), "restore missed a LoRA param"
        rot_set(pm, None)
        assert all(p.requires_grad for _, p in ps)
        out.update({"layers": n, "quarters": [[q * n // 4, (q + 1) * n // 4] for q in range(4)], "lora_params": tot, "lora_tensors": len(ps)})
        return out
    finally:
        torch.set_rng_state(rng_state)


# ------------------------------------------------------------------ time-budgeted sleep (addendum 5)
BENCH_LEN = 384  # padded length of the synthetic training batch (an open-book example is about this long)


def ref_gen_batches(gen_bs, max_items=160, rem_chains=30, rem_gist=30):
    """Rough number of 20-new-token generation batches (the unit bench_chip times) in the reference night with every cap full: dreaming (400 new
    tokens = 20 units per batch of gen_bs items), verifying K candidate Q&A per item, the 2 probes, and in each of the 4 REM cycles one 40-token
    generation of all chains + gist dreams plus their verification. Tagging, update detection and the 'now' prompts are ignored."""
    nb = lambda n: -(-n // gen_bs)  # noqa: E731
    return nb(max_items) * 400 / 20 + nb(max_items * K) + 2 * nb(max_items) + 4 * (nb(rem_chains + rem_gist) * 40 / 20 + nb(rem_chains + rem_gist))


def plan_scale(budget_s, t_step, t_gen, ref_steps, ref_gen_batches):
    """Work scale s = clip(B / R, 0.25, 4), R = ref_steps x t_step + ref_gen_batches x t_gen: the seconds the reference night would take on this chip."""
    r = ref_steps * t_step + ref_gen_batches * t_gen
    return min(max(budget_s / r, 0.25), 4.0) if r > 0 else 4.0


def bench_chip(L, pm, args, ref_steps):
    """Time this chip on a fixed synthetic workload built from the tokenizer, touching no weights, optimizer state or RNG stream (torch CPU / CUDA
    state saved and restored; no Brain rng used; grads zeroed): one untimed and 3 timed forward+backward passes of a batch of bsz examples of BENCH_LEN
    tokens, micro-batched as Trainer.step does (t_step), and one greedy generation batch of gen_bs prompts, max_new 20 (t_gen). Returns the timings
    plus ref_gen_batches and R = ref_steps x t_step + ref_gen_batches x t_gen."""
    sync = torch.cuda.synchronize if L.device.type == "cuda" else (lambda: None)
    ids = L.ids("The quick brown fox jumps over the lazy dog near the old harbour of Kelmira, where Zelmir works. ")
    ex = (ids * (BENCH_LEN // len(ids) + 1))[:BENCH_LEN]
    batch = [(ex, BENCH_LEN // 2)] * args.bsz
    ntgt = sum(len(e) - max(st, 1) for e, st in batch)
    prompts = [L.render(SYS, "Question: " + " ".join(["Where does Zelmir live?"] * 8))] * args.gen_bs

    def one():
        for mb in groups(batch):
            bi, mask, tm = lm_masks(L, mb)
            (F.cross_entropy(pm(input_ids=bi, attention_mask=mask).logits[:, :-1][tm].float(), bi[:, 1:][tm], reduction="sum") / ntgt).backward()

    with seeded_rng(0, L.device):
        pm.train()
        one()  # warm-up (kernel compilation, allocator)
        sync()
        t0 = time.time()
        for _ in range(3):
            one()
        sync()
        t_step = (time.time() - t0) / 3
        pm.zero_grad(set_to_none=True)
        pm.eval()
        L.generate(pm, prompts[:1], max_new=2, bs=1)  # warm-up of the generation path
        sync()
        t0 = time.time()
        L.generate(pm, prompts, max_new=20, bs=args.gen_bs)
        sync()
        t_gen = time.time() - t0
    n = ref_gen_batches(args.gen_bs)
    return {"t_step": t_step, "t_gen": t_gen, "ref_steps": ref_steps, "ref_gen_batches": n, "ref_seconds": ref_steps * t_step + n * t_gen}


def selftest_stale():
    """ab_ob_twist's stale-value filter (Brain.stale_hit) on made-up items: a scene naming the value an item replaced is a hit (any case, whole
    words only), and so is the value that older item replaced in turn; a clean scene, a longer word that merely contains the old value, and an old
    value that is part of the item's own current name are not."""
    from types import SimpleNamespace
    oo = Item(("vrakol", "dunmere"), "Vrakol", "Dunmere", "lives in", 1)
    o = Item(("vrakol", "skarum"), "Vrakol", "Skarum", "lives in", 2, upd=[{"shared": "Vrakol", "old": "Dunmere", "new": "Skarum", "old_key": oo.key}])
    n = Item(("vrakol", "tremix"), "Vrakol", "Tremix", "lives in", 3, upd=[{"shared": "Vrakol", "old": "Skarum", "new": "Tremix", "old_key": o.key}])
    ny = Item(("vrakol", "new york"), "Vrakol", "New York", "lives in", 4, upd=[{"shared": "Vrakol", "old": "York", "new": "New York", "old_key": ("vrakol", "york")}])
    me = SimpleNamespace(items={i.key: i for i in (oo, o, n, ny)})
    hit = lambda it, x: Brain.stale_hit(me, it, x)  # noqa: E731
    assert hit(n, "In a dream Vrakol floated from Skarum to Tremix.") and hit(n, "tremix, vrakol and the SKARUM moon") and hit(n, "Vrakol, Tremix, and Dunmere.")
    assert not hit(n, "In a dream Vrakol owned a green house in Tremix.") and not hit(n, "Vrakol and Tremix met in Skarumville.")
    assert not hit(o, "Vrakol and Skarum under a purple sky.") and hit(o, "Vrakol left Dunmere for Skarum.")
    assert not hit(ny, "Vrakol rode a train through New York, which hummed.") and not hit(oo, "Vrakol and Dunmere at midnight.")
    return {"stale_filter_ok": True}


def selftest_budget():
    """Addendum-5 machinery: (i) plan_scale with fake timings (R = 50 x 1 + 100 x 0.5 = 100 s: budgets 100 / 200 / 50 give s = 1 / 2 / 0.5; far
    outside the range it clips to 4 and 0.25; R <= 0 gives 4); (ii) ref_gen_batches(32) = 154 by hand; (iii) Brain.sc scales steps / items by s
    and leaves them untouched at s = 1; (iv) bench_chip on a tiny CPU smoke model changes no weight, no grad, no RNG state and not the train/eval
    mode, and returns positive timings with R = ref_steps t_step + ref_gen_batches t_gen."""
    from argparse import Namespace
    from types import SimpleNamespace
    from peft import LoraConfig, get_peft_model
    out = {}
    for b, want in ((100, 1.0), (200, 2.0), (50, 0.5), (1e6, 4.0), (1, 0.25)):
        assert plan_scale(b, 1.0, 0.5, 50, 100) == want, (b, want)
    assert plan_scale(10, 0.0, 0.0, 50, 100) == 4.0
    assert ref_gen_batches(32) == 154, ref_gen_batches(32)
    sc = lambda x, n: Brain.sc(SimpleNamespace(scale=x), n)  # noqa: E731
    assert [sc(1.0, n) for n in (4, 160, 30, 0)] == [4, 160, 30, 0] and all(type(sc(1.0, n)) is int for n in (4, 160))
    assert [sc(2.0, n) for n in (4, 160, 30, 150, 0)] == [8, 320, 60, 300, 0] and [sc(0.25, n) for n in (4, 160, 2)] == [1, 40, 1] and sc(1.5, 4) == 6
    out["plan_scale_ok"] = out["sc_ok"] = True
    rng_state = torch.get_rng_state()
    try:
        cpu = torch.device("cpu")
        lm, tok = load_model(Namespace(smoke=True, seed=0), cpu, torch.float32)
        L = Lang(tok, True, cpu)
        pm = get_peft_model(lm, LoraConfig(r=8, lora_alpha=16, lora_dropout=0.0, target_modules=LORA_TARGETS, bias="none"))
        for _, m in lora_mods(pm):
            m.lora_B["default"].weight.data.normal_(0, 0.05)
        pm.eval()
        w0 = {n: p.detach().clone() for n, p in pm.named_parameters()}
        torch.manual_seed(123)
        state = torch.get_rng_state()
        b = bench_chip(L, pm, Namespace(bsz=4, gen_bs=4), 100)
        assert torch.equal(torch.get_rng_state(), state), "bench_chip moved the RNG"
        assert all(torch.equal(p.detach(), w0[n]) for n, p in pm.named_parameters()), "bench_chip changed a weight"
        assert all(p.grad is None for p in pm.parameters()) and not pm.training
        assert b["t_step"] > 0 and b["t_gen"] > 0 and b["ref_gen_batches"] == ref_gen_batches(4) and abs(b["ref_seconds"] - (100 * b["t_step"] + b["ref_gen_batches"] * b["t_gen"])) < 1e-9
        out["bench"] = {k: round(v, 4) for k, v in b.items()}
        return out
    finally:
        torch.set_rng_state(rng_state)


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
    rpe: float = 0.0  # ab_ob_guess: (1 if the probe was right else 0) - the model's first-token confidence
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
        if args.arm in EXTRA_ARMS:
            s.examples["twist"] = []
        s.set_scale(1.0)
        s.conf, s.boosted = {}, set()  # ab_ob_guess: first-token confidence per probed item key (tonight); keys with rpe > 0.2 last night
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

    def sc(s, n):  # addendum 5: a night's knob n at work scale s.scale (untouched at 1, so the reference night is exactly ab_ob's)
        return n if s.scale == 1 or n <= 0 else max(1, round(n * s.scale))

    def set_scale(s, scale):  # the night's work: dreams per item (and their generation length), item cap, REM chains, gist dreams
        s.scale = scale
        s.k, s.cap_items, s.cap_chains, s.cap_gist, s.dream_new = s.sc(K), s.sc(s.a.max_dream_items), s.sc(s.a.rem_chains), s.sc(s.a.rem_gist), s.sc(400)

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

    def salient(s, it):  # ab_ob_ther: flagged important, corrected, or replaced an older value
        return it.imp or it.cor or bool(it.upd)

    def prio(s, it):
        if s.a.arm == "ab_flatprio":
            return 1.0
        p = max(it.days, 1) * (1 + it.imp + it.cor) * (1 + it.surprise) * (2 if it.upd and it.gave_old else 1)
        if s.a.arm == "ab_ob_ther" and s.salient(it):
            p *= 2
        elif s.a.arm in GUESS_ARMS:  # dopamine: better than predicted (right but unsure) -> up to 3x
            p *= 1 + 2 * max(0.0, it.rpe)
        return p

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
        st["backlog"] = max(0, len(need) - s.cap_items)
        need = need[:s.cap_items]
        prompts, meta = [], []
        for it in need:
            idx = s.diary.containing(it.subj, it.obj, d)[::-1][:4]
            ctx = s.diary.label(idx)
            prompts.append(nrem_prompt(s.L, ctx, it, s.k))
            meta.append((it, "dream", ctx))
            if it.upd:
                u = it.upd[-1]
                o = s.items[u["old_key"]]
                oi = s.diary.containing(o.subj, o.obj, it.first - 1) or s.diary.containing(o.subj, o.obj, d)
                nctx = s.diary.label(sorted(set(idx[:3]) | {oi[-1]}))
                prompts.append(now_prompt(s.L, nctx, u["shared"], u["new"], u["old"]))
                meta.append((it, "now", nctx))
        raw = s.gen(prompts, s.mn(s.dream_new), sample=True)
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
                for p in paras[:s.k]:
                    st["paraphrases_gen"] += 1
                    if s.leaky(p):
                        st["dropped_test_leak"] += 1
                    elif not all(e.lower() in p.lower() for e in ents):
                        st["dropped_missing_entities"] += 1
                    else:
                        cp.append((it, p.strip()))
                for q, ans in qas[:s.k]:
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
        if a.arm in EXTRA_ARMS:
            s.twist(d, need, {it.key: c for it, k, c in meta if k == "dream"}, st)
        return dict(st)

    def stale_hit(s, it, text):
        """ab_ob_twist: does the scene restate an older value of this fact, i.e. an u["old"] of it.upd, or of the older item it replaced, and so on
        down the chain? Whole words, case-insensitive, with the item's own current names blanked out first (an old value inside a current name is no hit)."""
        low = text.lower()
        for e in (it.subj, it.obj):
            low = low.replace(e.lower(), " ")
        todo, seen = [it], set()
        while todo:
            x = todo.pop()
            if x.key in seen:
                continue
            seen.add(x.key)
            for u in x.upd:
                if u["old"] and pat(u["old"]).search(low):
                    return True
                if u["old_key"] in s.items:
                    todo.append(s.items[u["old_key"]])
        return False

    def twist(s, d, need, ctxs, st):
        """ab_ob_twist, after all of the night's normal dreaming: the BASE model writes 2 strange dream-like scenes per item (sampled under a fixed
        seed; the global torch RNG state is put back, so later sampling is as in ab_ob). A scene is kept if it names both entities, is not a test
        leak, restates no older value of the fact (stale_hit), and the base model, shown only the scene, answers one of the item's kept dream questions (its probe if none). Kept scenes join it.para.
        ab_ob_winp: the same step with para2_prompt (2 more ordinary paraphrases, same sampling seed, checks and stats keys; st["twist_mode"] = "plain")."""
        a = s.a
        plain = a.arm not in TWIST_ARMS
        if plain:
            st["twist_mode"] = "plain"
        cur = [it for it in need if a.smoke or it.qa or it.probe]
        st["twist_skipped_no_check"] = len(need) - len(cur)
        with seeded_rng(a.seed * 100 + d + 41, s.L.device):
            raw = s.gen([(para2_prompt if plain else twist_prompt)(s.L, ctxs[it.key], it) for it in cur], s.mn(200), sample=True)
        s.raw["twist"] = raw[:2]
        cand = []  # (item, scene, check question, check answer)
        for it, txt in zip(cur, raw):
            ents, chk = [it.subj, it.obj], it.qa or ([it.probe] if it.probe else [])
            scenes = parse_scenes(txt)
            if a.smoke and not scenes:  # tiny random model emits noise: fabricate one scene so the path runs
                scenes = [f"As Sam's notes say, {it.subj} {it.rel} {it.obj}." if plain else f"In a dream, {it.subj} {it.rel} {it.obj} while the sky was green."]
            if not scenes:
                st["twist_parse_fail"] += 1
            for j, x in enumerate(scenes):
                st["twist_gen"] += 1
                if s.leaky(x):
                    st["twist_dropped_test_leak"] += 1
                elif not all(e.lower() in x.lower() for e in ents):
                    st["twist_dropped_missing_entities"] += 1
                elif s.stale_hit(it, x):
                    st["twist_dropped_stale"] += 1
                else:
                    cand.append((it, x, *(chk[j % len(chk)] if chk else ("", ""))))
        ver = s.gen([ctx_prompt(s.L, x, q) for _, x, q, _ in cand], 20)
        seen = set()
        for (it, x, q, ans), v in zip(cand, ver):
            keep = False
            if not has_ans(ans, v) and not a.smoke:
                st["twist_dropped_unverified"] += 1
            elif (it.key, norm(x)) in seen or any(norm(x) == norm(p) for p in it.para):
                st["twist_dropped_dup"] += 1
            else:
                seen.add((it.key, norm(x)))
                it.para = [*it.para, x]  # a new list: the night's logged dream examples share the old one
                st["twist_kept"] += 1
                keep = True
            if len(s.examples["twist"]) < 10:
                s.examples["twist"].append({"night": d, "item": it.fact, "scene": x, "check_q": q, "check_a": ans, "verifier": v, "kept": keep})

    # ---- 5. morning probes (weights only, current adapter)
    def probe(s, E, conf=False):
        its = [it for it in E if it.probe]
        prompts = [plain_prompt(s.L, it.probe[0]) for it in its]
        if conf:  # ab_ob_guess: the same greedy answers (current adapter) plus the first answer token's probability, kept in s.conf
            s.pm.eval()
            ans, pf = generate_p(s.L, s.pm, prompts, 20, s.a.gen_bs)
            s.conf = {it.key: p for it, p in zip(its, pf)}
        else:
            ans = s.gen(prompts, 20, base=False)
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
                if s.a.arm in GUESS_ARMS:
                    it.rpe = float(ok) - s.conf[it.key]  # reward prediction error: outcome minus the model's own confidence
            else:
                it.consol = False
                if s.a.arm in GUESS_ARMS:
                    it.rpe = 0.0

    def guess_rec(s, pre):
        """ab_ob_guess: tonight's guesses (pre-probe, before training) and the recall, in this pre-probe, of the items boosted last night (rpe > 0.2)."""
        rpe = {k: float(pre[k][0]) - s.conf[k] for k in pre}
        out = {"probed": len(pre), "share_rpe_gt_0.2": acc(r > 0.2 for r in rpe.values()), "mean_conf": mean(s.conf[k] for k in pre), "mean_rpe": mean(rpe.values()),
               "prev_boosted_n": sum(1 for k in s.boosted if k in pre), "prev_boosted_recall": acc(pre[k][0] for k in s.boosted if k in pre)}
        s.boosted = {k for k, r in rpe.items() if r > 0.2}
        return out

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

    def wt(s, ex, its):  # ab_ob_ther: the practice example of a salient item (a REM chain: either of its two) gets loss weight 0.5
        return ex + (0.5,) if s.a.arm == "ab_ob_ther" and any(s.salient(i) for i in its) else ex

    def dream_ex(s, it):
        o = s.rng.choice(it.para + it.qa)
        return s.wt(ex_text(s.L, o) if isinstance(o, str) else s.qa_ex(o[0], o[1]), [it])

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
        pairs = pairs[:s.cap_chains]
        gist = [it for it in E if it.days >= a.gist_min_days]
        s.rng.shuffle(gist)
        gist.sort(key=lambda it: s.gist_done[it.key])
        gist = gist[:s.cap_gist]
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

    # ---- 6b. synaptic tagging (ab_ob_local)
    def tag_plasticity(s, act, cum, con):
        """Tonight's plastic set: draw a.tag_batches practice batches (s.nrem, open-book coin flips included), then restore s.rng, s.ob_rng and
        the coverage counters so the training batch stream is the one it would have been. tag_grads sums |grad| of every delta_w over them,
        pick_mask keeps the entries about a.local_k largest, stored as base_layer.delta_mask (the grad hook applies it). Returns rec["tag"]."""
        a = s.a
        st, cov = (s.rng.getstate(), s.ob_rng.getstate()), Counter(s.cov)
        batches = [s.nrem(act, cum, con, a.bsz) for _ in range(a.tag_batches)]
        s.rng.setstate(st[0])
        s.ob_rng.setstate(st[1])
        s.cov.clear()
        s.cov.update(cov)
        mods = lora_mods(s.pm)
        accs, ce = tag_grads(s.L, s.pm, batches)
        masks, thr = pick_mask(accs, a.local_k, torch.Generator().manual_seed(a.seed * 100 + s.day + 31))
        del accs
        cnt = [int(mk.sum()) for mk in masks]
        kept = sum(cnt)
        by_layer, by_type = Counter(), Counter()
        for (n, m), mk, c in zip(mods, masks, cnt):
            m.base_layer.delta_mask = mk
            by_layer[int(re.search(r"layers\.(\d+)\.", n).group(1))] += c
            by_type[n.rsplit(".", 1)[-1]] += c
        sh = lambda c: round(c / max(kept, 1), 4)  # noqa: E731
        return {"batches": len(batches), "examples": sum(map(len, batches)), "ce": ce, "k": a.local_k, "kept": kept, "thr": thr,
                "top_layers": [[l, sh(c)] for l, c in by_layer.most_common(8)], "by_type": {t: sh(c) for t, c in by_type.most_common()}}

    @torch.no_grad()
    def mask_check(s, snap):
        """After training, before SHY: delta entries that changed since the night's snapshot inside / outside tonight's mask (outside must be 0)
        and the nonzero delta entries."""
        inside = outside = 0
        for n, m in lora_mods(s.pm):
            bl = m.base_layer
            ch = bl.delta_w.data != snap[f"{n}.base_layer.delta_w"].to(bl.delta_w.device)
            inside += int((ch & bl.delta_mask).sum())
            outside += int((ch & ~bl.delta_mask).sum())
        return {"changed_in_mask": inside, "changed_outside_mask": outside, "delta_nnz_pre_shy": delta_nnz(s.pm)}

    @staticmethod
    def peak_gb(reset=False):  # addendum-4 arms on CUDA: peak allocated GB since the last reset
        v = torch.cuda.max_memory_allocated() / 1e9
        if reset:
            torch.cuda.reset_peak_memory_stats()
        return v

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
        bench = None
        if a.budget_scale is not None or a.night_budget_s is not None:  # addendum 5: tonight's work scale (otherwise s = 1 and nothing below differs from ab_ob)
            ref_steps = sched[d - 1] if sched and d <= len(sched) else 150  # 150: run_af's default night when there is no schedule
            if a.budget_scale is None:
                bench = bench_chip(s.L, s.pm, a, ref_steps)
                s.set_scale(plan_scale(a.night_budget_s, bench["t_step"], bench["t_gen"], ref_steps, bench["ref_gen_batches"]))
                bench["budget_s"] = a.night_budget_s
            else:
                s.set_scale(a.budget_scale)
        track = a.arm in (*ADD4_ARMS, *WIN_ARMS) and s.L.device.type == "cuda"  # peak GPU memory of the night and of its training phase (reads only; no RNG)
        pk = []
        if track:
            s.peak_gb(True)

        def lap(name):
            ph[name] = ph.get(name, 0) + time.time() - tl[0]
            tl[0] = time.time()
        if bench:
            lap("bench")
        rec["tagging"] = s.tag(d)
        s.refresh(d)
        lap("tag")
        rec["update_detection"] = s.detect(d)
        lap("update_detection")
        E = [it for it in list(s.items.values()) if s.elig(it)]
        rec["dream_stats"] = s.dream(d, E)
        lap("dream")
        if a.arm in EXTRA_ARMS:
            s.log(f"[night {d}] twist {({k: v for k, v in rec['dream_stats'].items() if k.startswith('twist')})}")
        pre = s.probe(E, conf=a.arm in GUESS_ARMS)
        s.morning(E, pre)
        lap("probe")
        if a.arm in GUESS_ARMS:
            rec["guess"] = s.guess_rec(pre)
            s.log(f"[night {d}] guess {rec['guess']}")
        cons = [it for it in E if it.consol]
        n_act = sum(1 for it in E if not it.consol)
        steps = sched[d - 1] if sched and d <= len(sched) else min(300, 40 + 4 * n_act)
        if a.smoke:
            steps = min(steps, 16)
        ref_n, steps = steps, s.sc(steps)  # the scaled night (the smoke cap applies to the reference night first)
        if a.budget_scale is not None or a.night_budget_s is not None:
            rec["budget"] = {"scale": s.scale, "steps": steps, "steps_ref": ref_n, "k": s.k, "max_dream_items": s.cap_items, "rem_chains": s.cap_chains,
                             "rem_gist": s.cap_gist, "bench": bench}
            s.log(f"[night {d}] budget {rec['budget']}")
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
        if a.arm == "ab_ob_local":
            rec["tag"] = s.tag_plasticity(act, cum, con) if (act or con) else None
            if rec["tag"]:
                lap("synaptic_tag")
                s.log(f"[night {d}] tag: kept {rec['tag']['kept']:,} of k {rec['tag']['k']:,} (thr {rec['tag']['thr']:.3g}, ce {rec['tag']['ce']:.3f}) layers {rec['tag']['top_layers']} types {rec['tag']['by_type']}")
        if a.arm == "ab_ob_rot":  # after the snapshot (it holds every LoRA param): tonight only quarter (d - 1) % 4 trains
            rec["rot"] = rot_set(s.pm, (d - 1) % 4)
            s.log(f"[night {d}] rot: quarter {rec['rot']['quarter']} layers {rec['rot']['layers']} trainable {rec['rot']['trainable_params']:,}")
        tr = Trainer(s.L, s.pm, a, kl_pool, steps, a.seed * 100 + d)
        if track:
            pk.append(s.peak_gb(True))  # the night so far; the peak is then reset for the training phase alone (REM generation included)
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
                        tr.step([s.wt(s.qa_ex(x["q"], x["a"]), [s.items[k] for k in x["keys"]]) for x in s.rng.choices(live, k=nr)] + s.nrem(act, cum, con, a.bsz - nr))
                    rem_n, done = rem_n + (c - n_nrem), done + (c - n_nrem)
                    s.cov["rem_steps"] += c - n_nrem
        lap("train")
        rec.update({"steps": done, "steps_nrem": nrem_n, "steps_rem": rem_n, "rem_stats": rem_stats, "loss_curve": tr.curve[-6:], "fp16_overflow_steps": getattr(tr, "overflow", 0)})
        if a.arm == "ab_ob_ther":
            rec["ther"] = {"salient_eligible": sum(1 for it in E if s.salient(it)), "salient_active": sum(1 for it in act if s.salient(it)),
                           "weighted_steps": tr.wsteps, "weighted_examples": tr.wex}
            s.log(f"[night {d}] ther {rec['ther']}")
        if track:
            rec["peak_mem_train_gb"] = s.peak_gb(True)
        if a.arm == "ab_ob_local" and rec["tag"]:
            mc = s.mask_check(snap)
            rec["tag"].update(mc)
            s.log(f"[night {d}] mask check: {mc}")
        # 8. synaptic downscaling
        if a.arm == "ab_noshy" or not (act or con):
            rec["shy"], rec["shy_zeroed_frac"] = None, None
        else:
            if a.arm == "ab_ob_local":
                rec["shy"] = shy_elem_apply(s.pm, a.shy_factor, a.shy_thresh)
            elif a.arm in DELTA_ARMS:
                rec["shy"] = shy_delta_apply(s.pm, a.shy_factor, a.shy_thresh, s.gen_t, a.arm == "ab_ob_merge")
            else:
                rec["shy"] = shy_apply(s.pm, a.shy_factor, a.shy_thresh, s.gen_t)
            rec["shy_zeroed_frac"] = rec["shy"]["zeroed_frac"]
            s.log(f"[night {d}] SHY {rec['shy']}")
            s.cov["shy"] += 1
        if a.arm in DELTA_ARMS:
            rec["delta_fro"] = delta_fro(s.pm)
            s.log(f"[night {d}] delta_fro {rec['delta_fro']:.6g}")
            if a.arm == "ab_ob_local":
                rec["delta_nnz"] = delta_nnz(s.pm)
                s.log(f"[night {d}] delta_nnz {rec['delta_nnz']:,}")
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
            if a.arm == "ab_ob_local":
                rec["delta_nnz_final"] = delta_nnz(s.pm)
        if a.arm == "ab_ob_rot":
            rot_set(s.pm, None)  # every LoRA param trainable again (snapshot / restore, SHY and the next night's snapshot as in ab_ob)
        if track:
            rec["peak_mem_gb"] = max(*pk, rec["peak_mem_train_gb"], s.peak_gb())
        rec["rem_pool"] = len(s.rem_pool)
        lap("gate")
        rec["phase_seconds"], rec["raw_samples"] = {k: round(v, 1) for k, v in ph.items()}, s.raw
        rec["time"] = time.time() - t0
        s.log(f"[night {d}] done steps {done} (nrem {nrem_n}, rem {rem_n}) arc_val {arc:.3f} probe_post {rec['probe_recall_post']} reverted {bool(why)} {rec['time']:.0f}s"
               + (f" delta_fro {rec['delta_fro']:.6g} -> {rec['delta_fro_final']:.6g}" if a.arm in DELTA_ARMS else "")
               + (f" delta_nnz {rec['delta_nnz']:,} -> {rec['delta_nnz_final']:,}" if a.arm == "ab_ob_local" else ""))
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


# ------------------------------------------------------------------ q4 base (MLX affine fake quantization)
def q4_fake(w, group=64, bits=4, store_dtype=None):
    """MLX affine quantize-dequantize of a 2-D+ tensor along its last dim; returns w' (same shape and dtype as w) or None if the last dim
    is not divisible by group. Per group: scale = (max-min)/(2^bits-1) (1e-8-ish safe value when max == min), bias = min, both rounded to
    store_dtype (default w.dtype); q = clamp(round((w-bias)/scale), 0, 2^bits-1); w' = q*scale + bias. Math in float32."""
    if w.dim() < 1 or w.shape[-1] % group:
        return None
    levels = 2 ** bits - 1
    x = w.detach().float().reshape(-1, w.shape[-1] // group, group)
    mx, mn = x.amax(-1, keepdim=True), x.amin(-1, keepdim=True)
    scale = (mx - mn) / levels
    scale = torch.where(scale == 0, torch.full_like(scale, 1e-8), scale)
    sd = store_dtype or w.dtype
    scale, bias = scale.to(sd).float(), mn.to(sd).float()
    scale = torch.where(scale == 0, torch.full_like(scale, 1e-8), scale)  # a rounded-to-zero scale (underflow) stays safe
    q = torch.clamp(torch.round((x - bias) / scale), 0, levels)
    return (q * scale + bias).reshape(w.shape).to(w.dtype)


def q4_apply(lm, group=64, bits=4):
    """Fake-quantize (in place, no grad) the weight of every nn.Linear and nn.Embedding in lm; tied tensors once (by data_ptr). The scale /
    bias storage dtype is the weight's own dtype (bf16 on cuda, fp32 on cpu). Returns {tensors, skipped, params, mean_rel_fro, group, bits}."""
    seen, nq, ns, npar, errs = set(), 0, 0, 0, []
    with torch.no_grad():
        for _, m in lm.named_modules():
            if not isinstance(m, (torch.nn.Linear, torch.nn.Embedding)):
                continue
            w = m.weight
            if w.data_ptr() in seen:
                continue
            seen.add(w.data_ptr())
            wq = q4_fake(w.data, group, bits)
            if wq is None:
                ns += 1
                continue
            den = w.data.float().norm().item()
            errs.append((wq.float() - w.data.float()).norm().item() / den if den > 0 else 0.0)
            w.data.copy_(wq)
            nq += 1
            npar += w.numel()
    return {"tensors": nq, "skipped": ns, "params": npar, "mean_rel_fro": sum(errs) / len(errs) if errs else None, "group": group, "bits": bits}


def selftest_q4():
    """q4_fake on a random 8x128 tensor (own generator; global RNG untouched): (i) at most 2^bits distinct values per group, (ii) elementwise
    error <= scale/2 (+ tolerance; scale from the fp32 group range), (iii) idempotent to 1e-6 relative, (iv) a non-divisible shape is skipped
    (also through q4_apply on a tiny Linear / Embedding pair, with a tied tensor counted once)."""
    g = torch.Generator().manual_seed(0)
    w = torch.randn(8, 128, generator=g)
    out = {}
    for bits in (4, 3):
        wq = q4_fake(w, 64, bits)
        gr, gq = w.reshape(8, 2, 64), wq.reshape(8, 2, 64)
        assert max(len(set(r.tolist())) for r in gq.reshape(-1, 64)) <= 2 ** bits, "more distinct values than levels"
        scale = (gr.amax(-1, keepdim=True) - gr.amin(-1, keepdim=True)) / (2 ** bits - 1)
        assert bool(((gq - gr).abs() <= scale / 2 * (1 + 1e-5) + 1e-6).all()), "error above scale/2"
        w2 = q4_fake(wq, 64, bits)
        rel = ((w2 - wq).norm() / wq.norm()).item()
        assert rel < 1e-6, f"not idempotent: {rel}"
        out[f"bits{bits}"] = {"max_err_over_half_scale": ((gq - gr).abs() / (scale / 2)).max().item(), "idem_rel": rel}
    assert q4_fake(torch.randn(4, 100, generator=g), 64, 4) is None, "non-divisible shape not skipped"
    assert torch.equal(q4_fake(torch.zeros(2, 64), 64, 4), torch.zeros(2, 64)), "constant group must reconstruct exactly"
    wb = torch.randn(8, 128, generator=g).to(torch.bfloat16)
    assert q4_fake(wb, 64, 4).dtype == torch.bfloat16
    emb = torch.nn.Embedding(10, 128)
    lin = torch.nn.Linear(128, 10, bias=False)
    lin.weight = emb.weight  # tied
    odd = torch.nn.Linear(100, 4)
    net = torch.nn.ModuleList([emb, lin, odd])
    before_odd = odd.weight.detach().clone()
    st = q4_apply(net, 64, 4)
    assert (st["tensors"], st["skipped"], st["params"]) == (1, 1, 1280), st
    assert torch.equal(odd.weight, before_odd) and 0 < st["mean_rel_fro"] < 0.2, st
    out["apply"] = st
    return out


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=ARMS)
    ap.add_argument("--week", help="week1.json; with --smoke and no --week the built-in 2-day fixture is used")
    ap.add_argument("--out")
    ap.add_argument("--model", default="Qwen/Qwen3.5-2B")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="run the SHY refactor, delta, local-plasticity, weighted-loss, rotation, time-budget and stale-filter unit checks and exit")
    ap.add_argument("--schedule", help="result_ab.json whose nights[i].steps become this arm's per-night steps (compute match)")
    ap.add_argument("--bsz", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--full-lr", type=float, default=2e-5, help="ab_ob_full / ab_ob_local: lr of the full-rank deltas (replaces --lr)")
    ap.add_argument("--full-lr-small", type=float, default=5e-6, help="ab_ob_full_s only: the gentler lr (replaces --lr; otherwise identical to ab_ob_full)")
    ap.add_argument("--local-k-frac", type=float, default=None, help="ab_ob_local: plastic delta entries per night as a fraction of all delta entries (default: as many as there are LoRA parameters)")
    ap.add_argument("--tag-batches", type=int, default=8, help="ab_ob_local: practice batches drawn each night to tag the plastic entries")
    ap.add_argument("--budget-scale", type=float, default=None, help="work scale s (steps, dreams per item, item cap, REM chains, gist dreams all x s); default 1 (ab_ob_b2: 2)")
    ap.add_argument("--night-budget-s", type=float, default=None, help="seconds per night: s = clip(B / R, 0.25, 4) from a benchmark at the start of each night (ignored when --budget-scale or ab_ob_b2 pins s)")
    ap.add_argument("--dtype", choices=["auto", "bf16", "fp16", "fp32"], default="auto", help="model dtype; auto = bf16 on cuda, fp32 on cpu; fp16 (T4) also scales the training loss x1024")
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--kl-weight", type=float, default=1.0)
    ap.add_argument("--replay-bsz", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--delta-dtype", choices=["fp32", "bf16"], default="fp32", help="ab_ob_merge only: bf16 halves the folded change buffer to fit a 16 GB card (the forward already uses it in bf16)")
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
    ap.add_argument("--q4-base", action="store_true", help="Mac study: replace every Linear / Embedding weight of the frozen base by an MLX-style affine fake-quantized copy (before LoRA)")
    ap.add_argument("--q4-group", type=int, default=64, help="--q4-base: group size along the input dim")
    ap.add_argument("--q4-bits", type=int, default=4, help="--q4-base: bits per weight (levels = 2**bits - 1)")
    args = ap.parse_args()
    globals()["TOK_BUDGET"] = args.tok_budget
    if args.selftest:
        print(json.dumps(selftest_shy()))
        print(json.dumps({"delta": selftest_delta()}))
        print(json.dumps({"local": {**selftest_elem(), **selftest_local()}}))
        print(json.dumps({"weighted": selftest_weighted()}))
        print(json.dumps({"rot": selftest_rot()}))
        print(json.dumps({"budget": selftest_budget()}))
        print(json.dumps({"stale": selftest_stale()}))
        print(json.dumps({"q4": selftest_q4()}))
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

    if args.arm in TRAIN_DELTA_ARMS:
        args.lr = args.full_lr_small if args.arm == "ab_ob_full_s" else args.full_lr  # recorded in result["args"]
        log(f"[full] lr {args.lr} (--{'full-lr-small' if args.arm == 'ab_ob_full_s' else 'full-lr'}): full-rank deltas train, LoRA frozen")
    if args.local_k_frac is not None and not 0 < args.local_k_frac <= 1:
        ap.error("--local-k-frac must be in (0, 1]")
    if args.tag_batches < 1:
        ap.error("--tag-batches must be at least 1")
    if args.arm in B2_ARMS and args.budget_scale is None:
        args.budget_scale = 2.0  # ab_ob with twice the night's work, unless --budget-scale says otherwise
    if args.budget_scale is not None and not args.budget_scale > 0:
        ap.error("--budget-scale must be positive")
    if args.night_budget_s is not None and not args.night_budget_s > 0:
        ap.error("--night-budget-s must be positive")
    if args.budget_scale is not None and args.night_budget_s is not None:
        log(f"[budget] scale pinned at {args.budget_scale}: --night-budget-s {args.night_budget_s} is not used")
    t0 = time.time()
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.smoke else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    if args.dtype != "auto":  # --dtype fp16 for GPUs without bf16 (Kaggle T4); LoRA adapters stay fp32 (peft), loss scaled x1024
        dtype = {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": torch.float32}[args.dtype]
        if args.dtype == "fp16":
            LOSS_SCALE[0] = 1024.0
    lm, tok = load_model(args, device, dtype)
    q4 = None
    if args.q4_base:
        if args.q4_group < 1 or args.q4_bits < 1:
            ap.error("--q4-group and --q4-bits must be positive")
        q4 = q4_apply(lm, args.q4_group, args.q4_bits)
        log(f"[q4] fake-quantized base: {q4['tensors']} tensors quantized, {q4['skipped']} skipped, {q4['params']:,} params, mean rel Frobenius error {q4['mean_rel_fro']} (group {q4['group']}, bits {q4['bits']})")
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
    result = {"arm": args.arm, "model": args.model, "smoke": args.smoke, "args": {k: v for k, v in vars(args).items() if k not in ("week", "out", "schedule") and not (k in ("budget_scale", "night_budget_s") and v is None)},
              "week": args.week, "n_user_turns": len(diary.turns), "days": days, "schedule": sched, "partial": True, "q4_base": q4}

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
            lora_n = sum(p.numel() for n, p in pm.named_parameters() if "lora_A" in n or "lora_B" in n)  # before freezing
            if args.delta_dtype == "bf16" and args.arm in TRAIN_DELTA_ARMS:
                ap.error("--delta-dtype bf16 is only for ab_ob_merge (trained deltas need fp32 for small lr steps)")
            mods = setup_delta(pm, args.arm in TRAIN_DELTA_ARMS, masked=args.arm == "ab_ob_local",
                               dtype=torch.bfloat16 if args.delta_dtype == "bf16" else torch.float32)
            if args.arm in TRAIN_DELTA_ARMS:
                for n, p in pm.named_parameters():
                    if "lora_" in n:
                        p.requires_grad_(False)
            # the check builds its own tiny CPU model, which the GPU box's Triton linear-attention kernels refuse; it runs in --selftest / smoke
            result["delta_selftest"] = selftest_delta() if device.type == "cpu" else {"skipped": "GPU run (checked on CPU via --selftest and smoke)"}
            log(f"[selftest] delta machinery: {result['delta_selftest']}")
            n_delta = sum(m.base_layer.delta_w.numel() for _, m in mods)
            log(f"[delta] {len(mods)} modules, delta params {n_delta:,} ({'trainable' if args.arm in TRAIN_DELTA_ARMS else 'folded in nightly'})")
            if args.arm == "ab_ob_local":
                args.local_k = max(1, round(args.local_k_frac * n_delta)) if args.local_k_frac is not None else lora_n
                result["local_k"], result["local_delta_entries"], result["local_lora_params"] = args.local_k, n_delta, lora_n
                result["local_selftest"] = {**selftest_elem(), **selftest_local()} if device.type == "cpu" else {"skipped": "GPU run (checked on CPU via --selftest and smoke)"}
                log(f"[selftest] local plasticity: {result['local_selftest']}")
                log(f"[local] K {args.local_k:,} plastic entries per night = {args.local_k / n_delta:.4%} of {n_delta:,} delta entries (LoRA params {lora_n:,}); {args.tag_batches} tagging batches; elementwise SHY")
        if args.arm in EXTRA_ARMS:
            result["twist_selftest"] = selftest_stale()
        if args.arm == "ab_ob_rot":
            result["rot_selftest"] = selftest_rot() if device.type == "cpu" else {"skipped": "GPU run (checked on CPU via --selftest and smoke)"}
            log(f"[selftest] rotating regions: {result['rot_selftest']}")
        if args.arm == "ab_ob_ther":
            result["ther_selftest"] = selftest_weighted() if device.type == "cpu" else {"skipped": "GPU run (checked on CPU via --selftest and smoke)"}
            log(f"[selftest] weighted loss: {result['ther_selftest']}")
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
