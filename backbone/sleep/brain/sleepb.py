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
Addendum 7 (PREREG-sleepB-addendum7.md), one change each on top of work scale 2: ab_ob_b4 (s = 4), ab_ob_tag2 (tag_prompt2: only facts that link two names written
in the message; Sam / "I" / common nouns are not names; no small talk about Sam's tasks), ab_ob_bridge (bridge_prompt: the REM chain prompt names the start, the answer and the
middle name; start / answer alternate with the pair index so both directions are dreamed; every check after generation is unchanged).
Addendum 8 (PREREG-sleepB-addendum8.md), on top of work scale 4: ab_ob_b4_bridge (b4 + addendum 7's bridge_prompt in REM) and ab_ob_b4_names (b4 + a names re-read pass right after the
day's tagging: for pairs of candidate names, i.e. words capitalised mid-sentence somewhere in the diary so far, that occur together in a turn and that no item links yet, names_prompt asks
how they are related; each answer that is not "no" becomes a triple that goes through tag()'s checks and joins that turn's tag_log entry; rec["names_pass"] holds the counts).
Addendum 9 (PREREG-sleepB-addendum9.md), on top of work scale 4: ab_ob_b4_nb = ab_ob_b4_names's names re-read pass + ab_ob_b4_bridge's bridge_prompt in REM (both addendum-8 code paths, unchanged).
Addendum 10 (PREREG-sleepB-addendum10.md), on top of ab_ob_b4_nb: ab_ob_b4_nb_x4 samples every REM chain prompt X4_TRIES = 4 times and keeps, per pair per cycle, only the first sample that passes every check.

Addendum 11 (PREREG-sleepB-addendum11.md), the recipe (ab_ob_b4_nb) on IFM/K2-Horizon-3.7B: --model IFM/K2-Horizon-3.7B --revision <sha> loads K2HorizonForCausalLM with trust_remote_code; Lang(k2=True) ends every prompt with an
empty think block (thinking off) and ends every turn / training target with <|ifm|im_end|>; --arc-base scores the same 500 ARC-Easy questions on the base before night 1 (result["arc_easy_base"]); --smoke --model IFM/K2-Horizon-3.7B runs
the smoke on a tiny random K2 (real tokenizer and chat template). Qwen runs are unchanged.
Addendum 11b (PREREG-sleepB-addendum11b.md), K2 only: the names pass thinks briefly. Stage 1 renders each names question with Lang.render_think (the template's reasoning_effort="low" generation prompt, think block
left open after "<ifm|think_faster>\n") and generates at most NAMES_THINK_MAX = 256 greedy tokens on the base, stopping at "</ifm|think_faster>" or the end of the turn; stage 2 is the same prompt + that thinking +
"</ifm|think_faster>" (added when stage 1 did not close the block), then the answer as before (12 tokens, parse_rel). names_pass's record gets think_tokens_mean / think_capped on K2 only (Qwen's is unchanged).
Addendum 11c (PREREG-sleepB-addendum11c.md), K2 only: the names pass thinks fully. Stage 1 uses K2_NAMES_EFFORT = "high" (the template's default reasoning_effort, block left open after "<ifm|think>\n") with NAMES_THINK_MAX = 512 greedy
thinking tokens, stopping at "</ifm|think>" or the end of the turn (Lang.think_eos("high")); strip_think and stage 2 use that effort's close tag ("</ifm|think>", added when stage 1 did not close the block, then the 12-token answer as before);
and a reply whose first line starts with the word no / not / none / nothing / nope / unrelated is read as "no" (parse_rel_k2; Qwen keeps parse_rel).

Addendum 13 (PREREG-sleepB-addendum13.md): --q4-eval (delta arms only) also scores the final model under F0 / Q0 / Q / Qf (bf16 and 4-bit, with and without the fp32 delta folded in, fresh or frozen 4-bit grid).
Addendum 13b (PREREG-sleepB-addendum13b.md): --freeze-lora (training delta arms) re-freezes the LoRA in every Trainer, since leaving pm.disable_adapter() makes it trainable again.
Addendum 14 (PREREG-sleepB-addendum14.md), K2 two-step dreams (all flags default to the old behaviour): --rem-chain-mode {default,q,think,q_think} (BRIDGE_ARMS, not TRIES_ARMS): q asks bridge_q_prompt for only the question (the answer is the
given far end, parse_q1), think opens K2's high-effort think block for the bridge_prompt reply (stage 1: at most REM_THINK_MAX = 512 sampled tokens; stage 2: prompt + thinking + close tag, 40 tokens, parse_qa1), q_think both; --rem-dirs both
(every pair is two units, one per direction, tried each cycle until it has a kept dream; --rem-tries N samples a unit N times and keeps the first sample that passes every check); --rem-steps-mult F (each cycle's REM steps x F, the
Trainer's schedule covers the new total); --think-eval (K2, report-only: two-hop and C2+C4 forward asked again with thinking, weights only). k2_chain_probe.py runs the REM variants on the Week-1 world without training.

Addendum 15 (PREREG-sleepB-addendum15.md), long nights with varied vs repeated cards (all flags default to the old behaviour, byte for byte): --text-scale X (needs --budget-scale) takes the five generation knobs (k, item cap, REM chain cap, REM gist cap, dream token budget)
from X instead of the work scale while the training steps stay at --budget-scale (R8: --budget-scale 8 --text-scale 4); --dream-vary {mix,plain} (OB arms, not the twist arms): nrem_prompt asks for kp = ceil(k/4) paraphrases (and still k question cards), then Brain.vary asks
the BASE model for n = ceil(k/4) texts in each of 3 styles (story: a tiny everyday story; note: a note in Sam's own voice; mix: weird, a surreal dream scene; plain: plain2, ordinary paraphrases), each style sampled under its own fixed seed (seed * 100 + night + 43 + style index, the
main stream is untouched), kept under twist's checks (both entities, no test leak, no older value, the base model answers a card from the text alone) and appended to it.para; rec["dream_vary"] has the per-style yields. --reword FILE (report-only, data/week2_reworded.json from
make_reworded.py, written through the Message Batches API): after ALL scoring and after the result JSON is on disk, weights-only greedy answers to 3 new wordings of each C2+C4 forward / reverse and each two-hop test (a test is right if most of its wordings are), to the exact kept question
cards / REM chain dreams of those tests (the cramming gap), a seen check (a wording found word for word in any kept text) and a card-variety measure (pairwise token Jaccard of an item's texts) -> result["reword"], rewritten into the same file; a failure goes to result["reword_error"], never costs the run.

Sleep efficiency (research/sleep-efficiency-2026-10-25.md; every flag is off by default, and off is bit-identical to before): --card-stats (report-only) records, for every
practice example, whether the model already answered it before the step (every target token but the final eos is the argmax, so greedy decoding would write it exactly), from the
logits the loss already computes, and puts the per-night shares by kind (text, qa_cb, qa_ob, rem_cb, rem_ob) and by quarter of the night in nights[i].cards; --skip-known F (implies
--card-stats): a card (an NREM paraphrase or Q&A, a REM-pool dream) that was right at its last closed-book or text practice is kept with probability F, else the draw is repeated
(at most SKIP_TRIES draws, the last one is kept); a wrong morning probe marks all of that item's cards not known again; --lora-plus R: the lora_B matrices step at lr x R (LoRA+);
--ob-share P: the open-book share of practice Q&A (0.5 before); --lr-sched wsd: the night's lr stays at --lr, then falls linearly to 0 over the last WSD_DECAY of its steps (cosine before);
--rem-views V: each REM cycle gives the REM pool about V x pool x (cycle's REM steps / night's REM steps) practice slots, at most the usual round(0.7 bsz) a step, spread over the cycle's steps, so a dream
that is in the pool all night gets about V practices (one made in cycle c gets V x the share of the night's REM steps from c on); the slots it does not use go to NREM cards (before: always round(0.7 bsz) a step, e.g. about 2,700 practices for night 2's first dream in nb at 4x).
Together with the other branches' flags: --rem-views with --rem-steps-mult != 1 is an error (views fixes a dream's practices a night, so the extra REM steps would only be NREM steps); --rem-views composes with --rem-dirs both and --rem-tries
(it works on whatever the pool holds: each direction's dream is a dream, and --rem-tries only changes how the pool fills); --skip-known composes with --dream-vary (a style text is a card of its own, keyed by its text, so every night's new texts start not known;
the draw frequency changes, so a run with both is neither addendum's control); --text-scale and --reword are untouched by the efficiency flags.
Addendum 17 (PREREG-sleepB-addendum17.md): --gate-arc-n N (1..570, default 100 = the gate as before, byte for byte): the pre-sleep base score and the nightly morning gate both use the first N ARC-Easy validation questions (570 in all); the final ARC-Easy score is still the 500-question test split.

--q4-base (Mac deployment study, thread "Fit sleep on an 8 GB M2"): right after load_model, before LoRA and any base use, every nn.Linear and
nn.Embedding weight is replaced in place by a quantize-dequantize copy in MLX's affine 4-bit scheme (groups of --q4-group along the input dim,
scale = (max-min)/(2^bits-1), bias = min, both rounded to the model dtype), so the frozen base is what an MLX 4-bit model would be. Off: nothing changes.
--q4-mlx-moe (with --q4-base, Qwen3.5/3.6 MoE): also the fused 3-D expert tensors (mlp.experts.gate_up_proj / down_proj, groups along the last = input dim) and the router Parameter, with 8 bits for
every mlp.gate and mlp.shared_expert_gate: the recipe of mlx-community/Qwen3.6-35B-A3B-4bit. Weights stay in the model dtype (fake quantization), so no memory is saved.

  python backbone/sleep/brain/sleepb.py --arm ab --week backbone/sleep/brain/data/week1.json --out out/sleepb/ab
  python backbone/sleep/brain/sleepb.py --arm af --week ... --out out/sleepb/af --schedule out/sleepb/ab/result_ab.json
  python backbone/sleep/brain/sleepb.py --arm ab --smoke --out /tmp/x      # CPU, tiny random qwen3_5, built-in 2-day fixture
  python backbone/sleep/brain/sleepb.py --selftest                         # SHY refactor + delta (full / merge) + local-plasticity + weighted-loss + rotation + time-budget + stale-filter + addendum-7 / -8 / -9 / -10 arm unit checks + the K2 names-pass think path (addenda 11b / 11c) + the q4-eval conditions (addendum 13) + the K2 REM chain modes, units and step plan (addendum 14) + text-scale / dream-vary / reword (addendum 15) + the sleep-efficiency card checks (--card-stats, --skip-known, --lora-plus, --lr-sched, --rem-views)
  python backbone/sleep/brain/sleepb.py --arm ab_ob --smoke --out /tmp/x --budget-scale 8 --text-scale 4 --dream-vary mix --reword /tmp/smoke_reworded.json   # addendum 15 on the smoke fixture (a Week-2 file maps to none of its tests)

Ground truth in the week file (items, mentions, class) is used ONLY for scoring and diagnostics, never by the sleeper.
Model roles: tagging, update detection, NREM dreaming and every verification run on the BASE model (adapter disabled);
morning probes, REM dreaming and all test scoring run on the CURRENT adapter.
Files: DIR/result_<arm>.json (final), DIR/result_<arm>.partial.json (rewritten after every night, removed at the end),
DIR/adapter, DIR/log_<arm>.txt. --schedule overrides the per-night step count of any trained arm with ab's realized steps.
Each night uses a fresh AdamW with one cosine schedule spanning all of that night's cycles; the LoRA itself is cumulative.
"""
import argparse
import contextlib
import hashlib
import itertools
import json
import math
import os
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
from sleep1 import ARC_SMOKE, K2_END, K2_FAST_SHUT, K2_SHUT, K2_THINK_SHUT, SYS, Lang, generic_prompts, load_arc, parse_dream, score_arc  # noqa: E402
from train import K2_TYPE, LORA_TARGETS, is_k2, load_model  # noqa: E402
SHARED_RE = r".*\.layers\.\d+\.mlp\.shared_experts?\.(gate_proj|up_proj|down_proj)"  # the MoE shared expert (moe_bench.SHARED_RE)

K = 4
NREM_SHARE = [0.80, 0.65, 0.50, 0.35]
KINDS = ("forward", "reverse", "twohop", "changed", "routine")
ADD4_ARMS = ("ab_ob_rot", "ab_ob_twist", "ab_ob_ther", "ab_ob_guess")  # addendum 4: LoRA + open-book, one change each
WIN_ARMS = ("ab_ob_win", "ab_ob_winp")  # addendum 6: work scale 2 + guess priority + extra texts (win: twisted scenes, winp: ordinary paraphrases)
ADD7_ARMS = ("ab_ob_b4", "ab_ob_tag2", "ab_ob_bridge")  # addendum 7: one change each on top of work scale 2 (b4: scale 4; tag2: tag_prompt2; bridge: bridge_prompt)
ADD8_ARMS = ("ab_ob_b4_names", "ab_ob_b4_bridge")  # addendum 8: one change each on top of work scale 4 (names: the names re-read pass after tagging; bridge: bridge_prompt)
ADD9_ARMS = ("ab_ob_b4_nb",)  # addendum 9: both addendum-8 changes together on top of work scale 4 (the names pass and bridge_prompt)
ADD10_ARMS = ("ab_ob_b4_nb_x4",)  # addendum 10: ab_ob_b4_nb + X4_TRIES samples per REM chain prompt (one dream kept per pair per cycle)
TRIES_ARMS = ADD10_ARMS  # Brain.rem samples each chain prompt X4_TRIES times and keeps the first sample that passes every check, per pair per cycle
X4_TRIES = 4
NAMES_ARMS = ("ab_ob_b4_names", *ADD9_ARMS, *ADD10_ARMS)  # Brain.night runs names_pass right after the day's tagging
BRIDGE_ARMS = ("ab_ob_bridge", "ab_ob_b4_bridge", *ADD9_ARMS, *ADD10_ARMS)  # Brain.rem sends bridge_prompt (start, answer and middle name given) instead of chain_prompt
NEW_ARMS = ("ab_ob", "ab_klctx", "ab_ob_full", "ab_ob_merge", "ab_ob_full_s", "ab_ob_local", *ADD4_ARMS, "ab_ob_b2", *WIN_ARMS, *ADD7_ARMS, *ADD8_ARMS, *ADD9_ARMS, *ADD10_ARMS)
OB_ARMS = ("ab_ob", "ab_ob_full", "ab_ob_merge", "ab_ob_full_s", "ab_ob_local", *ADD4_ARMS, "ab_ob_b2", *WIN_ARMS, *ADD7_ARMS, *ADD8_ARMS, *ADD9_ARMS, *ADD10_ARMS)  # open-book rehearsal (Brain.qa_ex)
GUESS_ARMS = ("ab_ob_guess", *WIN_ARMS)  # first-token confidence and the dopamine priority
TWIST_ARMS = ("ab_ob_twist", "ab_ob_win")  # twisted dream-like scenes join the item's texts
EXTRA_ARMS = (*TWIST_ARMS, "ab_ob_winp")  # Brain.twist runs (winp: with ordinary paraphrases)
B2_ARMS = ("ab_ob_b2", *WIN_ARMS, "ab_ob_tag2", "ab_ob_bridge")  # work scale 2 unless --budget-scale says otherwise
B4_ARMS = ("ab_ob_b4", *ADD8_ARMS, *ADD9_ARMS, *ADD10_ARMS)  # addendum 7 / 8 / 9 / 10: work scale 4 unless --budget-scale says otherwise


SKIP_TRIES = 8  # --skip-known: draws per practice slot before a known card is kept anyway
WSD_DECAY = 0.2  # --lr-sched wsd: share of the night's steps in the linear decay to 0
ROW_CHUNK = 128  # row_stats: target rows per CE chunk (bounds the [rows, vocab] log-softmax temporary)


def default_scale(arm, given=None):  # the work scale main() pins: --budget-scale if given, else 4 (B4_ARMS), 2 (B2_ARMS) or None (s = 1 / --night-budget-s)
    return given if given is not None else 4.0 if arm in B4_ARMS else 2.0 if arm in B2_ARMS else None
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


def think_plain_prompt(L, q, effort="high"):  # addendum 14 (--think-eval, K2): plain_prompt's system line and question with the think block left open at `effort`
    return L.render_think(SYS, q, effort)


def ctx_prompt(L, ctx, q, head="Messages from Sam's chat history, labelled by day (if they disagree, the latest day is true):"):
    return L.render(SYS, f"{head}\n{ctx}\n\nQuestion: {q}")


def diary_prompt(L, diary, q, upto=None):  # the diary-test format; upto: restrict the notes to days <= upto (training), None: whole diary (scoring)
    return L.render(SYS, "Notes from earlier chats:\n" + diary.label(diary.search(q, 8, upto)) + f"\n\nQuestion: {q}")


def tag_prompt(L, text):
    u = (f"Message from Sam:\n\"{text}\"\n\nList the facts this message states about specific named people, places, organisations or things, as "
         f"short subject-relation-object triples. Use the names exactly as written in the message. At most 5. Reply with only JSON: "
         f"[{{\"subject\": \"...\", \"relation\": \"...\", \"object\": \"...\"}}]. If there are none, reply [].")
    return L.render("You extract facts from chat messages.", u)


def tag_prompt2(L, text):  # ab_ob_tag2: tag_prompt's system line, JSON format, cap and empty reply; sharper instructions (facts that link two written names)
    u = (f"Message from Sam:\n\"{text}\"\n\nList only the facts that link two names written in the message (people, places, organisations, boats or other named things), "
         f"as short subject-relation-object triples. Sam, \"I\", \"me\", \"my friend\" and common nouns are not names. Skip small talk about Sam's own tasks and requests. "
         f"Use the names exactly as written in the message. At most 5. Reply with only JSON: "
         f"[{{\"subject\": \"...\", \"relation\": \"...\", \"object\": \"...\"}}]. If there are none, reply [].")
    return L.render("You extract facts from chat messages.", u)


NAMES_THINK_MAX = 512  # addendum 11b (256, low effort) / 11c (512, high effort) (K2 only): thinking tokens per names question before the block is closed for it
K2_NAMES_EFFORT = "high"  # addendum 11c (K2 only): the template's reasoning_effort of the names pass's think block ("high": opens "<ifm|think>\n", closes "</ifm|think>"); 11b used "low"
REM_EFFORT, REM_THINK_MAX = "high", 512  # addendum 14 (K2 only, --rem-chain-mode think / q_think): the chain dream's think block (same effort as the names pass) and its stage-1 token cap
REM_CHAIN_MODES = ("default", "q", "think", "q_think")  # default: bridge_prompt, think block closed (today); q: question only; think / q_think: the same with the think block open first


def names_prompt(L, text, a, b, think=False, effort=None):  # NAMES_ARMS (ab_ob_b4_names, ab_ob_b4_nb): one pair of names from one message; the relation in 1 to 4 words, or "no" (tag_prompt's system line and message framing). think (K2): leave the think block open (L.render_think, at `effort`; None: render_think's default)
    u = (f"Message from Sam:\n\"{text}\"\n\nDoes this message say how \"{a}\" and \"{b}\" are related? If yes, reply with only the relation in 1 to 4 words "
         f"(for example: works at, lives in, is the mentor of, owns the boat). If not, reply only: no")
    if think:
        return L.render_think("You extract facts from chat messages.", u) if effort is None else L.render_think("You extract facts from chat messages.", u, effort)
    return L.render("You extract facts from chat messages.", u)


def upd_prompt(L, do, to, fo, dn, tn, fn, shared):
    u = (f"Earlier message (Day {do}): \"{to}\"\n(fact noted: {fo})\nLater message (Day {dn}): \"{tn}\"\n(fact noted: {fn})\n\nBoth messages mention \"{shared}\". Does the later message "
         f"change what the earlier message said, so that the earlier fact is no longer true (for example a new home, a new job, a correction)? "
         f"Answer with just \"changed\" or \"not changed\".")
    return L.render("You compare chat messages carefully.", u)


def nrem_prompt(L, ctx, it, k=K, kp=None):  # k: paraphrases and Q&A pairs per item (K; round(K s) at work scale s); addendum 15 (--dream-vary): kp paraphrases instead of k (None: k, the prompt as before)
    kp = k if kp is None else kp
    u = (f"Messages Sam sent in chat, newest first, labelled by day. If they disagree, the newest message is true.\n{ctx}\n\n"
         f"Focus on the fact linking \"{it.subj}\" and \"{it.obj}\". Write {kp} paraphrases of the CURRENT fact (short standalone sentences, "
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


VARY_STATS = ("gen", "kept", "parse_fail", "dropped_test_leak", "dropped_missing_entities", "dropped_stale", "dropped_unverified", "dropped_dup")  # the vary_<style>_<stat> keys of Brain.vary
VARY_STYLES = {"mix": ("story", "note", "weird"), "plain": ("story", "note", "plain2")}  # addendum 15 (--dream-vary): the style prompts Brain.vary sends, in order (the style index seeds each sampling); the 4th style is nrem_prompt's own kp paraphrases
VARY_WHAT = {"story": ("story", "Write {n} tiny everyday stories (1-3 sentences each) in which this fact stays true. "),
             "note": ("note", "Write {n} short notes in Sam's own voice (first person, 1-3 sentences each, the way Sam would jot it down) in which this fact stays true. "),
             "weird": ("scene", "Write {n} short dream-like scenes (1-3 sentences each) in which this fact stays true, but the setting and the wording are odd and surreal, the way a dream is. "),
             "plain2": ("paraphrase", "Write {n} short ordinary paraphrases (1-3 sentences each) in which this fact stays true, in plain everyday wording and a normal setting, each different from the other. ")}


def vary_prompt(L, ctx, it, style, n):  # addendum 15 (--dream-vary): twist_prompt / para2_prompt's system line, context framing and fact line; n texts of one style, one per line, numbered 1 to n
    one, ask = VARY_WHAT[style]
    u = (f"Messages Sam sent in chat, newest first, labelled by day. If they disagree, the newest message is true.\n{ctx}\n\n"
         f"Focus on the fact \"{it.subj} {it.rel} {it.obj}\". " + ask.format(n=n) + f"Each {one} must name both \"{it.subj}\" and \"{it.obj}\". "
         f"Reply with one {one} per line, numbered 1 to {n}, and nothing else.")
    return L.render("You are a careful assistant that studies facts.", u)


def parse_scenes(txt, n=2):  # numbered lines -> scene texts (at most n; 2 as before)
    out = []
    for ln in txt.splitlines():
        m = re.match(r"^[\s*#>-]*(?:scene\s*)?\d+\s*[.):*-]+\s*(.+)$", ln, re.I)
        if m and m.group(1).strip(" *\"'"):
            out.append(m.group(1).strip(" *\"'"))
    return out[:n]


def now_prompt(L, ctx, shared, new, old):
    u = (f"Messages from Sam's chat, labelled by day:\n{ctx}\n\nThe latest message changes what was said earlier about \"{shared}\". Write 2 different "
         f"questions asking what is true NOW about \"{shared}\" (use words like now, currently or these days). The answer to each must be "
         f"\"{new}\". Do not put \"{new}\" or \"{old}\" in the question. Reply with only JSON: {{\"questions\": [\"...\", \"...\"]}}")
    return L.render("You are a careful assistant that studies facts.", u)


def chain_prompt(L, fx, fy):
    u = (f"Two facts:\n- {fx}\n- {fy}\n\nWrite one question that can only be answered by using both facts together, without naming the name the two "
         f"facts share, and its answer, which must be a single name. Reply in exactly this form:\nQuestion: ...\nAnswer: ...")
    return L.render("You are a careful assistant that studies facts.", u)


BRIDGE_SYS = "You are a careful assistant that studies facts."


def bridge_text(fx, fy, start, answer, mid):  # the user text of bridge_prompt / bridge_q_prompt up to and including "(a single name)."
    return (f"Two facts:\n- {fx}\n- {fy}\n\nThe two facts share the name \"{mid}\". Write one question that names \"{start}\", does not name \"{mid}\" or \"{answer}\", "
            f"and can only be answered by using both facts together. Its answer must be \"{answer}\" (a single name).")


def bridge_render(L, u, think, effort):  # think (K2, addendum 14): leave the think block open (L.render_think at `effort`; None: render_think's default); else L.render (block closed)
    if think:
        return L.render_think(BRIDGE_SYS, u) if effort is None else L.render_think(BRIDGE_SYS, u, effort)
    return L.render(BRIDGE_SYS, u)


def bridge_prompt(L, fx, fy, start, answer, mid, think=False, effort=None):  # ab_ob_bridge: chain_prompt's system line and reply form; the start, the answer and the middle name are given
    return bridge_render(L, bridge_text(fx, fy, start, answer, mid) + " Reply in exactly this form:\nQuestion: ...\nAnswer: ...", think, effort)


def bridge_q_prompt(L, fx, fy, start, answer, mid, think=False, effort=None):  # addendum 14 (--rem-chain-mode q / q_think): bridge_prompt's text, but the reply is only the question (the answer is the given far end)
    return bridge_render(L, bridge_text(fx, fy, start, answer, mid) + " Reply with only the question, on one line.", think, effort)


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


def parse_q1(txt):  # addendum 14 (--rem-chain-mode q / q_think): a question-only reply -> the question: first non-empty line, "Question:" / "Q:" label and quotes off; None if that line starts with "Answer:" or does not end with "?"
    lines = [x.strip() for x in str(txt or "").splitlines() if x.strip()]
    if not lines or re.match(r"answer\s*:", lines[0], re.I):
        return None
    qt = " \t\"'`\u201c\u201d\u2018\u2019"  # (quotes and spaces, ASCII and curly)
    ln = re.sub(r"^(?:question|q)\s*:", "", lines[0].strip(qt), flags=re.I).strip(qt)
    return ln if ln.endswith("?") else None


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


THINK_EVAL_EFFORT, THINK_EVAL_MAX = "high", 512  # addendum 14 (--think-eval, K2 only): the think block's effort and the greedy thinking cap


def think_eval(L, model, week, bs, cap=THINK_EVAL_MAX):
    """Addendum 14 (--think-eval, K2 only, report-only): the weights-only questions (plain_prompt's text) asked with the think block open. Stage 1: greedy, at most `cap` tokens, stops at the close tag / end of turn
    (L.think_eos); stage 2 = prompt + thinking + ONE close tag, then up to 20 greedy tokens (score_week's max_new and bs). ok: the target is in the stage-2 answer; ok_any: it is anywhere in thinking + answer (a diagnostic).
    Sets: the two-hop questions, and the forward questions of class C2 / C4. The model is used as it is (adapter on)."""
    T = week["tests"]
    sets = {"twohop": list(T["twohop"]), "forward_c24": [t for t in T["forward"] if t["class"] in ("C2", "C4")]}
    flat = [(k, t) for k, ts in sets.items() for t in ts]
    p1 = [think_plain_prompt(L, t["q"], THINK_EVAL_EFFORT) for _, t in flat]
    th = [strip_think(x, THINK_EVAL_EFFORT) for x in L.generate(model, p1, max_new=cap, bs=bs, eos=L.think_eos(THINK_EVAL_EFFORT))]
    ans = L.generate(model, [p + x + K2_THINK_SHUT[THINK_EVAL_EFFORT] for p, (x, _) in zip(p1, th)], max_new=20, bs=bs)
    rows = {k: [] for k in sets}
    for (k, t), (x, closed), a in zip(flat, th, ans):
        rows[k].append({"q": t["q"], "target": t["target"], "answer": a, "think": x[:400], "ok": has_ans(t["target"], a), "ok_any": has_ans(t["target"], x + " " + a), "_ntok": len(L.ids(x)), "_closed": closed})
    out = {}
    for k, rs in rows.items():
        out[k] = {"acc": acc(r["ok"] for r in rs), "n": len(rs), "acc_any": acc(r["ok_any"] for r in rs), "think_tokens_mean": round(sum(r["_ntok"] for r in rs) / len(rs), 1) if rs else 0.0,
                  "capped": sum(not r["_closed"] for r in rs), "rows": [{c: v for c, v in r.items() if not c.startswith("_")} for r in rs]}
    return out


def fwd_recall(L, model, week, bs):  # cheap learning-curve probe: weights-only forward recall by ground-truth class
    ts = week["tests"]["forward"]
    ans = L.generate(model, [plain_prompt(L, t["q"]) for t in ts], max_new=20, bs=bs)
    ok = [has_ans(t["target"], a) for t, a in zip(ts, ans)]
    cl = lambda cs: acc(o for o, t in zip(ok, ts) if t["class"] in cs)  # noqa: E731
    return {"C1": cl(("C1",)), "C2": cl(("C2",)), "C4": cl(("C4",)), "C24": cl(("C2", "C4")), "all": acc(ok)}


# ------------------------------------------------------------------ new-wording scoring (addendum 15, --reword; report-only)
REWORD_CARDS, REWORD_CAP, REWORD_DUP = 3, 40, 0.8  # --reword: cards (or chain dreams) asked per test; texts per item in the variety measure; token Jaccard from which two texts are near-duplicates


def jac(sa, sb):  # Jaccard of two token sets
    return len(sa & sb) / len(sa | sb) if sa | sb else 0.0


def jaccard(a, b):  # token-set Jaccard of two strings (make_reworded.jaccard is the same)
    return jac(set(tokens(a)), set(tokens(b)))


def majority(oks):  # a test is right when more than half of its asked wordings are (2 of 3, 3 of 3; 2 of 2; 1 of 1); None when none were asked
    return None if not oks else 2 * sum(oks) > len(oks)


def reword_map(week, spec):
    """spec (make_reworded.py's file) -> ([(kind, test index, week test, entry)] for the entries that are this week's tests: same index, same question, same target, {kind: entries skipped})."""
    out, skipped = [], Counter()
    for kind in ("forward", "reverse", "twohop"):
        ts = week["tests"][kind]
        for e in spec["tests"].get(kind, []):
            i = e["test_index"]
            if isinstance(i, int) and 0 <= i < len(ts) and ts[i]["q"] == e["q_src"] and ts[i]["target"] == e["target"]:
                out.append((kind, i, ts[i], e))
            else:
                skipped[kind] += 1
    return out, dict(skipped)


def reword_variety(items, cap=REWORD_CAP, dup=REWORD_DUP):  # per item with 2+ texts (its paraphrases, then its question cards, the first `cap`): mean pairwise token Jaccard and the share of pairs >= dup; means over items
    mj, nd = [], []
    for it in items:
        sets = [set(tokens(x)) for x in [*it.para, *(q for q, _ in it.qa)][:cap]]
        pr = [jac(sets[i], sets[j]) for i in range(len(sets)) for j in range(i + 1, len(sets))]
        if pr:
            mj.append(sum(pr) / len(pr))
            nd.append(sum(x >= dup for x in pr) / len(pr))
    return {"items": len(mj), "mean_jaccard": mean(mj), "near_dup_share": mean(nd), "cap": cap, "near_dup_at": dup}


def reword_eval(L, model, week, brain, spec, bs, seed, log=print):
    """Addendum 15 (--reword, report-only): weights only (plain_prompt, greedy, 20 tokens, has_ans) on (1) the new wordings of the C2+C4 forward / reverse and the two-hop tests that spec has; (2) for each C2+C4 forward / reverse test, up to REWORD_CARDS of the
    matching Brain items' kept question cards (it.qa, live items whose ground-truth pair is the test's item by gt_match, answer has the target), sampled under Random(seed * 1000 + test index); (3) for each two-hop test, up to REWORD_CARDS kept REM chain dreams
    (rem_pool kind "chain", the two keys cover the two ground-truth items as in dreamed_twohop, answer has the target), asked exactly. A test is right when more than half of its wordings are (majority); share = the mean over tests of the share right.
    Cramming gap = mean card accuracy - mean new-wording accuracy (points, over the tests with cards); seen = a wording whose norm() is inside the norm of a kept text (it.para, it.qa questions, REM pool questions); variety = reword_variety.
    brain None (arms a0 / ad / af): only the new-wording recall. Tests of spec that are not this week's (index / question / target differ) are skipped and counted."""
    t0 = time.time()
    ms, skipped = reword_map(week, spec)
    G = {g[0]: g for g in brain.G} if brain is not None else {}  # item id -> (id, class, [(a, b)], old pairs)
    items = list(brain.items.values()) if brain is not None else []
    live = [it for it in items if not it.dead]
    asks = []  # every question put to the model, one dict each
    for kind, i, t, e in ms:
        for j, rw in enumerate(e["rewordings"]):
            asks.append({"src": "reword", "kind": kind, "test": i, "n": j, "q": rw, "target": t["target"]})
        if brain is None:
            continue
        pool, src = [], None
        if kind != "twohop" and t.get("class") in ("C2", "C4") and t["item"] in G:
            seen_q = set()
            for it in live:
                if gt_match(it.subj, it.obj, G[t["item"]][2]):
                    for q, a_ in it.qa:
                        if has_ans(t["target"], a_) and norm(q) not in seen_q:
                            seen_q.add(norm(q))
                            pool.append(q)
            src = "card"
        elif kind == "twohop" and all(x in G for x in t["items"][:2]):
            pa, pb = (G[x][2] for x in t["items"][:2])
            seen_q = set()
            for x in brain.rem_pool:
                k1, k2 = (brain.items.get(k) for k in x["keys"][:2]) if len(x["keys"]) == 2 else (None, None)
                if x["kind"] == "chain" and k1 and k2 and has_ans(t["target"], x["a"]) and norm(x["q"]) not in seen_q \
                        and ((gt_match(k1.subj, k1.obj, pa) and gt_match(k2.subj, k2.obj, pb)) or (gt_match(k1.subj, k1.obj, pb) and gt_match(k2.subj, k2.obj, pa))):
                    seen_q.add(norm(x["q"]))
                    pool.append(x["q"])
            src = "chain"
        for j, q in enumerate(random.Random(seed * 1000 + i).sample(pool, min(REWORD_CARDS, len(pool)))):
            asks.append({"src": src, "kind": kind, "test": i, "n": j, "q": q, "target": t["target"]})
    if brain is not None:  # the seen check: a wording that is inside a kept text word for word (normalized)
        big = "\n".join([norm(p) for it in items for p in it.para] + [norm(q) for it in items for q, _ in it.qa] + [norm(x["q"]) for x in brain.rem_pool])
        for x in asks:
            if x["src"] == "reword":
                x["seen"] = norm(x["q"]) in big
    model.eval()
    ans = L.generate(model, [plain_prompt(L, x["q"]) for x in asks], max_new=20, bs=bs) if asks else []
    by = defaultdict(lambda: defaultdict(list))  # (kind, test) -> src -> [ok]; "unseen" -> the rewordings that are not inside a kept text
    for x, a_ in zip(asks, ans):
        x["answer"], x["ok"] = a_, has_ans(x["target"], a_)
        by[(x["kind"], x["test"])][x["src"]].append(x["ok"])
        if x["src"] == "reword" and x.get("seen") is False:
            by[(x["kind"], x["test"])]["unseen"].append(x["ok"])
    cls = {(k, i): t.get("class") for k, i, t, _ in ms}

    def summ(keys, src="reword"):  # recall: share of tests that are right by majority; share: mean over tests of the share of wordings right
        rs = [by[k][src] for k in keys if by[k][src]]
        return {"n": len(rs), "recall": acc(majority(r) for r in rs), "share": acc(sum(r) / len(r) for r in rs)}
    ks = {kind: [(k, i) for k, i, _, _ in ms if k == kind] for kind in ("forward", "reverse", "twohop")}
    both = ks["forward"] + ks["reverse"]
    nw = {"forward": summ(ks["forward"]), "reverse": summ(ks["reverse"]), "both": summ(both), "twohop": summ(ks["twohop"]),
          "by_class": {c: summ([k for k in both if cls[k] == c]) for c in sorted({cls[k] for k in both if cls[k]})}}
    out = {"mapped": {k: len(v) for k, v in ks.items()}, "skipped_unmapped": skipped, "wordings_per_test": dict(sorted(Counter(len(e["rewordings"]) for _, _, _, e in ms).items())), "new_wording": nw}
    if brain is not None:
        wc = [k for k in both if by[k]["card"]]  # the tests that have cards
        out["cards"] = {"tests_in_scope": len(both), "tests_with_cards": len(wc), "cards_asked": sum(len(by[k]["card"]) for k in wc), "mean_acc": acc(sum(by[k]["card"]) / len(by[k]["card"]) for k in wc)}
        has = [k for k in wc if by[k]["reword"]]  # ... and a wording: the cramming gap's tests
        cm = acc(sum(by[k]["card"]) / len(by[k]["card"]) for k in has)
        wsh = summ(has)
        out["cramming_gap_pts"] = None if not has else round(100 * (cm - wsh["share"]), 2)  # card accuracy - new-wording accuracy (mean share right), points
        out["cramming_gap_majority_pts"] = None if not has else round(100 * (cm - wsh["recall"]), 2)  # the same against the majority-right recall
        out["cramming_gap_basis"] = {"tests": len(has), "card_acc": cm, "reword_share": wsh["share"], "reword_recall": wsh["recall"]}
        th = [k for k in ks["twohop"] if by[k]["chain"] and by[k]["reword"]]
        tm, tw = acc(sum(by[k]["chain"]) / len(by[k]["chain"]) for k in th), summ(th)
        out["twohop_cards"] = {"tests": len(th), "dreams_asked": sum(len(by[k]["chain"]) for k in th), "chain_acc": tm, "reword_share": tw["share"], "reword_recall": tw["recall"],
                               "gap_pts": None if not th else round(100 * (tm - tw["share"]), 2), "gap_majority_pts": None if not th else round(100 * (tm - tw["recall"]), 2)}
        rw = [x for x in asks if x["src"] == "reword"]
        un = [x for x in rw if not x["seen"]]
        un_both, un_two = [k for k in both if by[k]["unseen"]], [k for k in ks["twohop"] if by[k]["unseen"]]
        out["seen"] = {"rewordings": len(rw), "seen": len(rw) - len(un), "seen_share": acc(x["seen"] for x in rw),
                       "unseen": {"rewordings": len(un), "share_right": acc(x["ok"] for x in un),
                                  "both": {"n": len(un_both), "recall": summ(un_both, "unseen")["recall"]}, "twohop": {"n": len(un_two), "recall": summ(un_two, "unseen")["recall"]}}}
        out["variety"] = reword_variety(live)
    out["per_test"] = {kind: {i: majority(by[(kind, i)]["reword"]) for k, i in ks[kind] if by[(k, i)]["reword"]} for kind in ks}  # McNemar-ready: kind -> test index -> right by majority
    out["rows"] = asks
    out["seconds"] = round(time.time() - t0, 1)
    return out


ARC_VAL_ROWS = 570  # the ARC-Easy validation split


def load_arc_val(smoke, n=100):  # the gate's questions: the first n of the validation split (addendum 17, --gate-arc-n; 100 before); the smoke fixture is the same whatever n is
    if smoke:
        return ARC_SMOKE
    from datasets import load_dataset
    rows = []
    for r in list(load_dataset("allenai/ai2_arc", "ARC-Easy", split="validation"))[:n]:
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


FAST = True  # target-only LM head + length-sorted micro-batches in the split path (same loss and gradients up to float summation order); --bench-train toggles it, False = the old code path


def tgt_logits(pm, ids, mask, tm):  # fp32 logits at the shifted target positions tm; FAST: run the decoder only and apply lm_head to those hidden states
    m = pm.get_base_model() if hasattr(pm, "get_base_model") else pm  # peft -> Qwen3_5ForCausalLM; LoRA layers / delta_w hooks live inside the decoder's Linears, so disable_adapter() still applies
    if not FAST or m.lm_head._forward_hooks or m.lm_head._forward_pre_hooks or hasattr(m.lm_head, "delta_w") or hasattr(m.lm_head, "lora_A"):
        return pm(input_ids=ids, attention_mask=mask).logits[:, :-1][tm].float()
    return m.lm_head(m.model(input_ids=ids, attention_mask=mask).last_hidden_state[:, :-1][tm]).float()


@torch.no_grad()
def row_stats(lg, tgt, tm):
    """--card-stats / --skip-known: per example (row of tm) of a micro-batch, from the target logits lg the loss already used (no extra forward):
    known = every target but the row's last (the eos each example ends with) is the argmax, so greedy decoding after the prompt writes exactly
    this text; acc = the share of those targets that are the argmax; ce = the mean CE over all the row's targets (eos included)."""
    B = tm.shape[0]
    if not len(tgt):
        return [{"known": True, "acc": 1.0, "ce": 0.0} for _ in range(B)]
    rows = tm.nonzero()[:, 0]  # row-major, the order lg's rows come in
    last = torch.ones_like(rows, dtype=torch.bool)
    last[:-1] = rows[1:] != rows[:-1]
    body = (~last).float()
    ok = (lg.argmax(-1) == tgt).float()
    ce = torch.cat([F.cross_entropy(lg[i:i + ROW_CHUNK], tgt[i:i + ROW_CHUNK], reduction="none") for i in range(0, len(tgt), ROW_CHUNK)])
    t = torch.stack([torch.bincount(rows, weights=w, minlength=B) for w in (body, body * ok, ce, torch.ones_like(ce))]).tolist()
    return [{"known": h == n, "acc": h / n if n else 1.0, "ce": c / m if m else 0.0} for n, h, c, m in zip(*t)]


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
        if getattr(args, "freeze_lora", False):  # addendum 13b: leaving pm.disable_adapter() turns requires_grad back on for every LoRA tensor (peft 0.21), so re-freeze them here
            for n, p in pm.named_parameters():
                if "lora_" in n:
                    p.requires_grad_(False)
        s.params = [p for p in pm.parameters() if p.requires_grad]
        plus = getattr(args, "lora_plus", None)  # --lora-plus R (LoRA+, Hayou et al. 2024): the lora_B matrices in a second group at lr x R
        if plus:
            bs = {id(p) for n, p in pm.named_parameters() if p.requires_grad and "lora_B" in n}
            s.opt = torch.optim.AdamW([{"params": [p for p in s.params if id(p) not in bs]}, {"params": [p for p in s.params if id(p) in bs], "lr_mult": plus}],
                                      lr=args.lr, weight_decay=0.0)
        else:
            s.opt = torch.optim.AdamW(s.params, lr=args.lr, weight_decay=0.0)
        s.n, s.i, s.rng = max(steps, 1), 0, random.Random(seed)
        s.curve = []
        s.force_w, s.wsteps, s.wex = False, 0, 0  # force_w: test hook; wsteps / wex: weighted-path steps and examples with weight != 1

    def masks(s, mb):
        return lm_masks(s.L, mb)

    def lr_at(s, i):  # the night's lr at step i: cosine from a.lr to 0 over s.n steps; --lr-sched wsd: a.lr, then linear to 0 over the last WSD_DECAY of the steps
        a = s.a
        if getattr(a, "lr_sched", "cosine") == "wsd":
            k = math.ceil(s.n * (1 - WSD_DECAY))
            return a.lr if i < k else a.lr * (s.n - i) / (s.n - k + 1)
        return a.lr * 0.5 * (1 + math.cos(math.pi * i / s.n))

    def step(s, batch, rows=False):  # rows (--card-stats / --skip-known): also return row_stats of every example, in batch order
        if not batch:
            return
        a = s.a
        lr = s.lr_at(s.i)
        for g in s.opt.param_groups:
            g["lr"] = lr * g.get("lr_mult", 1.0)
        stats = [None] * len(batch) if rows else None
        s.pm.train()
        rb = s.rng.sample(s.replay, min(a.replay_bsz, len(s.replay))) if s.replay and a.kl_weight > 0 else []
        gb, gr = groups(batch), groups(rb)  # single-group decision on the original order
        if len(gb) > 1 and FAST:  # split path: longest first, so padding and micro-batch count drop (losses are sums / the full count: order-free; weights travel in the tuples)
            gb = groups(sorted(batch, key=lambda x: -len(x[0])))
        if len(gr) > 1 and FAST:
            gr = groups(sorted(rb, key=lambda x: -len(x[0])))
        kl_v = 0.0
        weighted = s.force_w or any(len(x) > 2 and x[2] != 1 for x in batch)
        s.opt.zero_grad(set_to_none=True)
        if len(gb) == 1 and len(gr) <= 1 and not weighted:  # the stage-1 path (short closed-book examples), unchanged
            ids, mask, tm = s.masks(batch)
            lg = tgt_logits(s.pm, ids, mask, tm)
            ce = F.cross_entropy(lg, ids[:, 1:][tm])
            if rows:
                stats = row_stats(lg.detach(), ids[:, 1:][tm], tm)
            loss = ce
            if rb:
                rids, rmask, rt = s.masks(rb)
                cur = tgt_logits(s.pm, rids, rmask, rt)
                with torch.no_grad(), s.pm.disable_adapter():
                    ref = tgt_logits(s.pm, rids, rmask, rt)
                kl = F.kl_div(F.log_softmax(cur, -1), F.log_softmax(ref, -1), log_target=True, reduction="batchmean")
                loss = ce + a.kl_weight * kl
                kl_v = float(kl.detach())
            loss.backward()
        else:  # split: sums over micro-batches divided by the full batch's target count, so loss and gradients match
            ntgt = sum(len(e) - max(st, 1) for e, st, *_ in batch)
            ce_sum = 0.0
            if rows:  # each micro-batch entry is one of batch's tuples (gb may be sorted): its index in batch
                pos = defaultdict(list)
                for i, x in enumerate(batch):
                    pos[id(x)].append(i)
            for mb in gb:
                ids, mask, tm = s.masks(mb)
                lg = tgt_logits(s.pm, ids, mask, tm)
                if weighted:  # sum over examples of weight x (that example's target-token CE sum), / the batch's target count
                    w = torch.tensor([x[2] if len(x) > 2 else 1.0 for x in mb], device=ids.device)[:, None].expand_as(tm)[tm]
                    part = (F.cross_entropy(lg, ids[:, 1:][tm], reduction="none") * w).sum() / ntgt
                else:
                    part = F.cross_entropy(lg, ids[:, 1:][tm], reduction="sum") / ntgt
                part.backward()
                ce_sum += float(part.detach())
                if rows:
                    for x, r in zip(mb, row_stats(lg.detach(), ids[:, 1:][tm], tm)):
                        stats[pos[id(x)].pop()] = r
            ce = torch.tensor(ce_sum)
            if rb:
                npos = sum(len(e) - max(st, 1) for e, st, *_ in rb)
                for mb in gr:
                    rids, rmask, rt = s.masks(mb)
                    cur = tgt_logits(s.pm, rids, rmask, rt)
                    with torch.no_grad(), s.pm.disable_adapter():
                        ref = tgt_logits(s.pm, rids, rmask, rt)
                    part = F.kl_div(F.log_softmax(cur, -1), F.log_softmax(ref, -1), log_target=True, reduction="sum") / npos
                    (a.kl_weight * part).backward()
                    kl_v += float(part.detach())
        torch.nn.utils.clip_grad_norm_(s.params, 1.0)
        s.opt.step()
        s.i += 1
        if weighted:
            s.wsteps += 1
            s.wex += sum(1 for x in batch if len(x) > 2 and x[2] != 1)
        if s.i % 10 == 1 or s.i == s.n:
            s.curve.append({"step": s.i, "ce": float(ce.detach()), "kl": kl_v, "lr": lr})
        s.pm.eval()
        return stats


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
        dw = lambda m, a, b: float(m.scaling["default"]) * b.float() @ a.float()  # noqa: E731
        # keep the randomized factors, not each module's fp32 dW: all the dWs at once need ~14 GB on K2-3.7B (out of memory on a 16 GB card).
        # Each dW is rebuilt from its factors one module at a time with the same ops, so the result is unchanged.
        rand = [(m.lora_A["default"].weight.data.clone(), m.lora_B["default"].weight.data.clone()) for _, m in mods]
        shy_apply(pm, 0.85, 0.0, g)
        tol = 1e-4 if mods[0][1].lora_A["default"].weight.dtype == torch.float32 else 3e-2  # bf16 adapters cannot hold 1e-4
        w2 = 0.0
        for (_, m), (a, b) in zip(mods, rand):
            d0 = dw(m, a, b)
            w2 = max(w2, float((dw(m, m.lora_A["default"].weight.data, m.lora_B["default"].weight.data) - 0.85 * d0).norm() / (0.85 * d0).norm()))
        del rand
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
            part = F.cross_entropy(tgt_logits(pm, ids, mask, tm), ids[:, 1:][tm], reduction="sum") / ntgt
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
    thresh 0 reproduces factor x W; (v) addendum 13b: after the LoRA is frozen and disable_adapter() is left once, a Trainer with freeze_lora holds
    only the deltas (regrad_after_disable_exit: how many LoRA tensors peft made trainable again). The model's deltas / LoRA are put back as found."""
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
        n_lora = sum(1 for n, _ in pm.named_parameters() if "lora_" in n)  # addendum 13b: freeze the LoRA as main() does, then leave disable_adapter() once
        for n, p in pm.named_parameters():
            if "lora_" in n:
                p.requires_grad_(False)
        with pm.disable_adapter():
            pass
        regrad = sum(1 for n, p in pm.named_parameters() if "lora_" in n and p.requires_grad)
        held = lambda fz: {n for n, p in pm.named_parameters() if any(p is q for q in Trainer(None, pm, Namespace(lr=0.0, freeze_lora=fz), [], 1, 0).params)}  # noqa: E731
        out["freeze_lora"] = {"lora_tensors": n_lora, "regrad_after_disable_exit": regrad, "held_without": sum("lora_" in n for n in held(False)), "held_with": sum("lora_" in n for n in held(True)),
                              "deltas_held_with": sum(n.endswith("delta_w") for n in held(True))}
        assert out["freeze_lora"]["held_without"] == regrad and out["freeze_lora"]["held_with"] == 0 and out["freeze_lora"]["deltas_held_with"] == len(mods), out
        for n, p in pm.named_parameters():
            if "lora_" in n:
                p.requires_grad_(True)
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


def selftest_fast():
    """FAST (target-only LM head + length-sorted micro-batches) against the old code path on the tiny CPU smoke model (global RNG, TOK_BUDGET, FAST and the delta switch restored).
    One Trainer step at lr 0 per setting, FAST False then True: CE, KL and every (clipped) LoRA gradient must agree to rel err < 1e-5 in fp32 over (i) a batch on the
    single-group path, (ii) a weighted batch, (iii) a batch split into several micro-batches with KL replay (also split), (iv) tgt_logits inside pm.disable_adapter()
    (the KL reference) vs the old logits; plus (v) the same split+KL step with trainable full-rank delta_w (setup_delta). Returns the max rel errors."""
    from argparse import Namespace
    from peft import LoraConfig, get_peft_model
    out, g = {}, torch.Generator().manual_seed(0)
    rng_state, tb, fast, don = torch.get_rng_state(), TOK_BUDGET, FAST, _DELTA["on"]
    rel = lambda xs, ys: max(float((x - y).abs().max()) for x, y in zip(xs, ys)) / max(float(y.abs().max()) for y in ys)  # noqa: E731
    try:
        cpu = torch.device("cpu")

        def build(delta):
            lm, tok = load_model(Namespace(smoke=True, seed=0), cpu, torch.float32)
            L = Lang(tok, True, cpu)
            pm = get_peft_model(lm, LoraConfig(r=8, lora_alpha=16, lora_dropout=0.0, target_modules=LORA_TARGETS, bias="none"))
            if delta:
                setup_delta(pm, True)
            for n, p in pm.named_parameters():  # B is zero at init: randomise it (and delta_w), so the gradients are all non-trivial
                if "lora_B" in n or "delta_w" in n:
                    p.data.normal_(0, 0.05, generator=g)
            return L, pm

        def check(name, L, pm, batch, replay, budget, kl=True, bsz=2):
            params, res = [p for p in pm.parameters() if p.requires_grad], {}
            for f in (False, True):
                globals()["FAST"], globals()["TOK_BUDGET"] = f, budget
                tr = Trainer(L, pm, Namespace(lr=0.0, kl_weight=1.0 if kl else 0.0, replay_bsz=bsz), replay if kl else [], 1, 0)
                tr.step(batch)
                res[f] = (tr.curve[0], [p.grad.clone() for p in params])
            (c0, g0), (c1, g1) = res[False], res[True]
            r = {"ce_rel": abs(c1["ce"] - c0["ce"]) / c0["ce"], "kl_rel": abs(c1["kl"] - c0["kl"]) / max(c0["kl"], 1e-12) if kl else 0.0, "grad_rel": rel(g1, g0),
                 "micro_batches": (len(groups(batch, budget)), len(groups(replay[:bsz], budget)) if kl else 0)}
            assert r["ce_rel"] < 1e-5 and r["kl_rel"] < 1e-5 and r["grad_rel"] < 1e-5 and (not kl or c0["kl"] > 0) and max(float(x.abs().max()) for x in g0) > 0, (name, r)
            out[name] = r
            return r

        L, pm = build(False)
        base = [ex_text(L, f"Zelmir lives in Kelmira number {i}, near the old harbour.") if i % 2 else ex_qa(L, f"Where does Zelmir{'x' * (3 * i)} live?", "Kelmira") for i in range(8)]
        replay = [ex_text(L, f"A generic sentence number {i} about the weather" + " today" * (i * 3)) for i in range(6)]
        big, small = 10 ** 6, 2 * max(len(e) for e, _ in base)
        short = base[:4]
        assert len(groups(short, big)) == 1 and len(groups(replay[:2], big)) == 1
        check("single_group", L, pm, short, replay, big)
        check("single_group_nokl", L, pm, short, replay, big, kl=False)
        check("weighted", L, pm, [e + (w,) for e, w in zip(base, [0.5, 1.0, 1.0, 0.5, 1.0, 0.5, 2.0, 1.0])], replay, big)
        r = check("split_kl", L, pm, base, replay, small, bsz=5)
        assert r["micro_batches"][0] > 1 and r["micro_batches"][1] > 1, r
        r = check("split_weighted_kl", L, pm, [e + (w,) for e, w in zip(base, [0.5, 1.0, 1.0, 0.5, 1.0, 0.5, 2.0, 1.0])], replay, small, bsz=5)
        globals()["FAST"] = False  # (iv) tgt_logits inside disable_adapter(): the KL reference
        ids, mask, tm = lm_masks(L, base[:5])
        pm.eval()
        with torch.no_grad():
            on = tgt_logits(pm, ids, mask, tm)
            with pm.disable_adapter():
                off0 = tgt_logits(pm, ids, mask, tm)
                globals()["FAST"] = True
                off1 = tgt_logits(pm, ids, mask, tm)
            on1 = tgt_logits(pm, ids, mask, tm)
        out["disable_adapter"] = {"off_rel": float((off1 - off0).abs().max() / off0.abs().max()), "on_rel": float((on1 - on).abs().max() / on.abs().max()), "adapter_effect_rel": float((on - off0).abs().max() / on.abs().max())}
        assert out["disable_adapter"]["off_rel"] < 1e-5 and out["disable_adapter"]["on_rel"] < 1e-5 and out["disable_adapter"]["adapter_effect_rel"] > 1e-3, out
        L, pm = build(True)  # (v) full-rank delta arm (delta_w trainable, hooks on the decoder's Linears; disable_adapter switches them off too)
        r = check("delta_split_kl", L, pm, base, replay, small, bsz=5)
        return out
    finally:
        globals()["FAST"], globals()["TOK_BUDGET"], _DELTA["on"] = fast, tb, don
        torch.set_rng_state(rng_state)


def selftest_cards():
    """The sleep-efficiency flags on the tiny CPU smoke model (global RNG, TOK_BUDGET and FAST restored). (i) Trainer.step(batch, rows=True) leaves CE, KL and every
    LoRA gradient bit-identical to Trainer.step(batch), on the single-group, weighted and split (+ KL) paths, and returns one row per example in batch order;
    (ii) row_stats' "known" is "greedy decoding after the prompt writes exactly this answer": the model's own greedy continuation is known, the same with one
    token changed is not, on both paths; (iii) --lora-plus R puts exactly the lora_B tensors at lr x R; off is one group; (iv) the cosine and wsd schedules;
    (v) Brain.nrem / rem_ex with --skip-known off draw exactly what the code before the flags drew (same examples, same RNG states after); on, a known item's
    cards are rarely drawn, Brain.train_step records closed-book and text outcomes only, and a wrong morning probe resets the item's cards."""
    from argparse import Namespace
    from peft import LoraConfig, get_peft_model
    out, g = {}, torch.Generator().manual_seed(0)
    rng_state, tb, fast = torch.get_rng_state(), TOK_BUDGET, FAST
    try:
        cpu = torch.device("cpu")
        lm, tok = load_model(Namespace(smoke=True, seed=0), cpu, torch.float32)
        L = Lang(tok, True, cpu)
        pm = get_peft_model(lm, LoraConfig(r=8, lora_alpha=16, lora_dropout=0.0, target_modules=LORA_TARGETS, bias="none"))
        for n, p in pm.named_parameters():  # B is zero at init: randomise it, so the adapter matters
            if "lora_B" in n:
                p.data.normal_(0, 0.05, generator=g)
        params = [p for p in pm.parameters() if p.requires_grad]
        base = [ex_text(L, f"Zelmir lives in Kelmira number {i}, near the old harbour.") if i % 2 else ex_qa(L, f"Where does Zelmir{'x' * (3 * i)} live?", "Kelmira") for i in range(8)]
        replay = [ex_text(L, f"A generic sentence number {i} about the weather" + " today" * (i * 3)) for i in range(6)]
        big, small = 10 ** 6, 2 * max(len(e) for e, _ in base)

        def run(batch, budget, rows, kl=True):
            globals()["FAST"], globals()["TOK_BUDGET"] = True, budget
            tr = Trainer(L, pm, Namespace(lr=0.0, kl_weight=1.0 if kl else 0.0, replay_bsz=3), replay if kl else [], 1, 0)
            st = tr.step(batch, rows=rows)
            return tr.curve[0], [p.grad.clone() for p in params], st

        # (i) bit-identical with rows on
        weighted = [e + (w,) for e, w in zip(base, [0.5, 1.0, 1.0, 0.5, 1.0, 0.5, 2.0, 1.0])]
        for name, batch, budget in (("single", base[:4], big), ("weighted", weighted, big), ("split_kl", base, small), ("split_weighted_kl", weighted, small)):
            c0, g0, s0 = run(batch, budget, False)
            c1, g1, s1 = run(batch, budget, True)
            same = c0 == c1 and all(torch.equal(x, y) for x, y in zip(g0, g1))
            assert same and s0 is None and len(s1) == len(batch) and all(r is not None for r in s1), (name, c0, c1)
            out[name] = {"bit_identical": same, "rows": len(s1), "micro_batches": len(groups(batch, budget))}
        # (ii) known == greedy decoding writes it
        pm.eval()
        p0 = L.ids(L.render(SYS, "Where does Zelmir live?"))
        x, gr = torch.tensor([p0]), []
        with torch.no_grad():
            for _ in range(3):
                nxt = int(pm(input_ids=x).logits[0, -1].argmax())
                gr.append(nxt)
                x = torch.cat([x, torch.tensor([[nxt]])], 1)
        V = pm.get_base_model().lm_head.out_features
        good = (p0 + gr + [L.eos], len(p0))
        bad = (p0 + gr[:1] + [(gr[1] + 1) % V] + gr[2:] + [L.eos], len(p0))
        for name, budget in (("known_single", big), ("known_split", len(good[0]) + 1)):
            st = run([bad, good, base[0]], budget, True, kl=False)[2]
            assert st[1]["known"] and st[1]["acc"] == 1.0 and not st[0]["known"] and st[0]["acc"] < 1.0, (name, st)
            out[name] = [r["known"] for r in st]
        # (iii) --lora-plus
        tr = Trainer(L, pm, Namespace(lr=0.1, kl_weight=0.0, replay_bsz=0, lora_plus=4.0), [], 4, 0)
        tr.step(base[:2])
        gB = {id(p) for n, p in pm.named_parameters() if "lora_B" in n}
        g0_, g1_ = tr.opt.param_groups
        assert len(tr.opt.param_groups) == 2 and {id(p) for p in g1_["params"]} == gB and not gB & {id(p) for p in g0_["params"]}
        assert g0_["lr"] == 0.1 and abs(g1_["lr"] - 0.4) < 1e-12, (g0_["lr"], g1_["lr"])
        assert len(Trainer(L, pm, Namespace(lr=0.1), [], 4, 0).opt.param_groups) == 1
        out["lora_plus"] = {"groups": 2, "b_tensors": len(gB), "lr": [g0_["lr"], g1_["lr"]]}
        # (iv) schedules over a 10-step night
        cos = Trainer(L, pm, Namespace(lr=1.0), [], 10, 0)
        wsd = Trainer(L, pm, Namespace(lr=1.0, lr_sched="wsd"), [], 10, 0)
        assert all(cos.lr_at(i) == 0.5 * (1 + math.cos(math.pi * i / 10)) for i in range(10))
        w = [wsd.lr_at(i) for i in range(10)]
        assert w[:8] == [1.0] * 8 and abs(w[8] - 2 / 3) < 1e-12 and abs(w[9] - 1 / 3) < 1e-12, w
        out["wsd"] = [round(v, 4) for v in w]
        # (iv b) --rem-views 20: the last cycle of nb's night 2 at 4x (2 dreams, 195 of the night's 510 REM steps) and of night 7 (375 dreams: the usual 11 a step binds), spread evenly
        s2, s7 = rem_split(20, 2, 195, 510, 11), rem_split(20, 375, 195, 510, 11)
        assert sum(s2) == 15 and max(s2) - min(s2) <= 1 and s7 == [11] * 195 and rem_split(20, 0, 5, 10, 0) == [0] * 5, (sum(s2), s7[:3])
        out["rem_views"] = {"night2_rem_examples": sum(s2), "night7_rem_examples": sum(s7)}
        # (v) Brain sampling
        me = Brain.__new__(Brain)
        me.a, me.L, me.diary, me.day, me.cov, me.raw, me.items = Namespace(arm="ab_ob_b4_nb", seed=0), L, Diary(smoke_week()), 2, Counter(), {}, {}
        me.skip_f, me.track, me.card, me.card_items, me.bk, me.cs, me.seen, me.last_ob = None, False, {}, defaultdict(set), None, Counter(), set(), False
        A = Item(key=("zelmir", "kelmira"), subj="Zelmir", obj="Kelmira", rel="lives in", born=1, days=2,
                 para=[f"Zelmir lives in Kelmira, take {i}." for i in range(3)], qa=[("Where does Zelmir live?", "Kelmira"), ("Who lives in Kelmira?", "Zelmir")])
        B = Item(key=("drovak", "gliker"), subj="Drovak", obj="Gliker", rel="mentors", born=1, days=2,
                 para=[f"Drovak mentors Gliker, take {i}." for i in range(3)], qa=[("Who does Drovak mentor?", "Gliker"), ("Who mentors Gliker?", "Drovak")])
        C = Item(key=("tavrix", "zelmir"), subj="Zelmir", obj="Tavrix", rel="works at", born=1, days=2, para=["Zelmir works at Tavrix."], qa=[("Where does Zelmir work?", "Tavrix")])
        me.items = {it.key: it for it in (A, B, C)}
        live = [{"q": "Where does the mentor of Gliker live?", "a": "Kelmira", "keys": [A.key, B.key]}, {"q": "Who lives where Zelmir lives?", "a": "Zelmir", "keys": [A.key]}]

        def old_qa(q, a):  # Brain.qa_ex before the flags (ab_ob arms: p = 0.5 open-book)
            if me.a.arm in OB_ARMS and me.ob_rng.random() < 0.5:
                return ex_qa_ob(me.L, me.diary, q, a, me.day)
            return ex_qa(me.L, q, a)

        def old_nrem(act, cum, con, n):  # Brain.nrem / dream_ex before the flags
            o = []
            for _ in range(n):
                if act and (not con or me.rng.random() < 0.75):
                    it = me.rng.choices(act, cum_weights=cum)[0]
                elif con:
                    it = me.rng.choice(con)
                else:
                    continue
                c = me.rng.choice(it.para + it.qa)
                o.append(ex_text(me.L, c) if isinstance(c, str) else old_qa(c[0], c[1]))
            return o

        def draw(f, act, con, n, nr):
            me.rng, me.ob_rng = random.Random(1), random.Random(2)
            cum = list(itertools.accumulate(me.prio(it) for it in act))
            if f == "old":
                exs = [old_qa(x["q"], x["a"]) for x in me.rng.choices(live, k=nr)] + old_nrem(act, cum, con, n)
            else:
                exs = me.rem_ex(live, nr) + me.nrem(act, cum, con, n)
            return exs, me.rng.getstate(), me.ob_rng.getstate()

        for act, con in (([A, B], [C]), ([A, B], []), ([], [C])):
            ref, new = draw("old", act, con, 40, 5), draw("new", act, con, 40, 5)
            assert ref == new, "skip-known off must draw exactly as before"
        out["off_identical"] = True
        me.skip_f, me.track = 0.01, True
        for c in A.para + A.qa:
            me.card[card_key(A, c)] = True
        me.card[rem_key(live[1])] = True
        me.bk = []
        exs = draw("new", [A, B], [], 400, 40)[0]
        bk, me.bk = me.bk, None
        nA = sum(1 for _, _, ik in bk if ik == A.key)
        nr1 = sum(1 for k, _, _ in bk if k == rem_key(live[1]))
        assert len(exs) == len(bk) == 440 and nA < 20 and nr1 < 4 and me.cs["known_drawn"] > 0, (nA, nr1, me.cs)
        out["skip_on"] = {"known_item_share": round(nA / 400, 4), "known_rem_share": round(nr1 / 40, 4), "known_drawn": me.cs["known_drawn"]}
        # train_step: outcomes of closed-book and text examples only go into me.card
        me.card, me.card_items, me.bk = {}, defaultdict(set), []
        batch = me.nrem([A, B, C], [1, 2, 3], [], 12)
        bk = list(me.bk)
        globals()["TOK_BUDGET"] = big
        tr = Trainer(L, pm, Namespace(lr=0.0, kl_weight=0.0, replay_bsz=0), [], 1, 0)
        me.train_step(tr, batch)
        kinds = Counter(k for _, k, _ in bk)
        cb_keys = {key for key, k, _ in bk if k in ("text", "qa_cb")}
        assert set(me.card) == cb_keys and sum(me.cs[f"n_{k}"] for k in kinds) == 12 and me.bk is None, (kinds, me.card)
        # the morning reset
        for key in list(me.card):
            me.card[key] = True
        nA = sum(1 for key in me.card_items[A.key])
        me.card_reset([A, B, C], {A.key: (False, "x"), B.key: (True, "Gliker")})
        assert me.cs["reset_by_probe"] == nA and all(not me.card[k] for k in me.card_items[A.key]) and all(me.card[k] for k in me.card_items[B.key])
        out["train_step"] = {"kinds": dict(kinds), "reset_by_probe": nA}
        return out
    finally:
        globals()["FAST"], globals()["TOK_BUDGET"] = fast, tb
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
            (F.cross_entropy(tgt_logits(pm, bi, mask, tm), bi[:, 1:][tm], reduction="sum") / ntgt).backward()

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


BENCH_TRAIN_BUDGETS, BENCH_TRAIN_WARM, BENCH_TRAIN_STEPS = (1024, 2048, 4096, 8192), 2, 10


def bench_train(args, L, pm):
    """--bench-train: Trainer.step wall time and peak GPU memory, OLD (FAST False = the pre-speed-up code) vs NEW (FAST True), at each tok budget, in one process.
    Synthetic batch from the tokenizer: bsz examples (half open-book-like ~384 tokens with loss on the last ~6, a quarter closed-book Q&A ~60 tokens with ~6 target
    tokens, a quarter plain texts ~80 tokens with loss on every token) plus 2 x replay_bsz replay examples ~120 tokens with loss on the last ~40. lr 0 (weights never
    move), 2 warm-up steps then 10 timed, cuda-synchronized; an OOM is recorded as "oom". Returns the result dict."""
    cuda = L.device.type == "cuda"
    sync = torch.cuda.synchronize if cuda else (lambda: None)
    rnd = random.Random(0)
    words = "harbour Kelmira Zelmir market lantern river bakery morning ledger orchard train window garden letter bridge candle winter copper meadow".split()
    toks = lambda n: (L.ids(" ".join(rnd.choice(words) for _ in range(n * 2)))[:n])  # noqa: E731  exactly n tokens (2n words always tokenize to >= n)
    mk = lambda n, k: (toks(n) + [L.eos], n + 1 - k)  # noqa: E731  n+1 tokens, loss on the last k
    nb = args.bsz
    batch = [mk(384, 6) for _ in range(nb // 2)] + [mk(60, 6) for _ in range(nb // 4)] + [mk(80, 80) for _ in range(nb - nb // 2 - nb // 4)]
    rnd.shuffle(batch)
    replay = [mk(120, 40) for _ in range(max(2 * args.replay_bsz, 1))]
    ta = argparse.Namespace(lr=0.0, kl_weight=args.kl_weight, replay_bsz=args.replay_bsz)
    res, tb, fast = {"model": args.model, "bsz": nb, "replay_bsz": args.replay_bsz, "warmup": BENCH_TRAIN_WARM, "timed": BENCH_TRAIN_STEPS, "device": str(L.device), "settings": {}}, TOK_BUDGET, FAST
    try:
        for b in BENCH_TRAIN_BUDGETS:
            globals()["TOK_BUDGET"] = b
            row = res["settings"][str(b)] = {"micro_batches_old": [len(groups(batch)), len(groups(replay[:args.replay_bsz]))],
                                             "micro_batches_new": [len(groups(sorted(batch, key=lambda x: -len(x[0])))), len(groups(sorted(replay[:args.replay_bsz], key=lambda x: -len(x[0]))))]}
            for name, f in (("old", False), ("new", True)):
                globals()["FAST"] = f
                tr = None
                try:
                    pm.zero_grad(set_to_none=True)
                    if cuda:
                        torch.cuda.empty_cache()
                        torch.cuda.reset_peak_memory_stats()
                    tr = Trainer(L, pm, ta, replay, BENCH_TRAIN_WARM + BENCH_TRAIN_STEPS, 0)
                    for _ in range(BENCH_TRAIN_WARM):
                        tr.step(batch)
                    sync()
                    t0 = time.time()
                    for _ in range(BENCH_TRAIN_STEPS):
                        tr.step(batch)
                    sync()
                    row[name] = {"s_per_step": (time.time() - t0) / BENCH_TRAIN_STEPS, "max_mem_gb": torch.cuda.max_memory_allocated() / 2 ** 30 if cuda else None}
                except torch.cuda.OutOfMemoryError:
                    row[name] = {"s_per_step": "oom", "max_mem_gb": "oom"}
                finally:
                    del tr
                    pm.zero_grad(set_to_none=True)
                    pm.eval()
                    if cuda:
                        torch.cuda.empty_cache()
            if all(isinstance(row[k]["s_per_step"], float) for k in ("old", "new")):
                row["speedup"] = row["old"]["s_per_step"] / row["new"]["s_per_step"]
            print(json.dumps({b: row}), flush=True)
    finally:
        globals()["TOK_BUDGET"], globals()["FAST"] = tb, fast
    return res


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


def selftest_arms7():
    """Addendum-7 arms on stubs (no model, no RNG outside a local Random): (i) default_scale, the helper main() pins the work scale with: ab_ob_b4 4, ab_ob_b2 / ab_ob_tag2 /
    ab_ob_bridge (and the older b2-scale arms) 2, every other arm None (s = 1), an explicit --budget-scale wins; the new arms are in none of GUESS / TWIST / EXTRA_ARMS and those
    sets are unchanged; (ii) tag_prompt2 and bridge_prompt render on a stub L with the key names and the unchanged system line / JSON format / cap / reply form, and differ from
    tag_prompt / chain_prompt; (iii) Brain.tag and Brain.rem, run on a stub that records their first generate call, use tag_prompt / chain_prompt for every arm except
    ab_ob_tag2 (tag_prompt2 only) and ab_ob_bridge (bridge_prompt only); (iv) in ab_ob_bridge the start / answer alternate with the pair index, the middle name is p's display form,
    and start, answer and middle are three different names."""
    from types import SimpleNamespace
    out = {}
    want = {"ab_ob_b4": 4.0, "ab_ob_b2": 2.0, "ab_ob_tag2": 2.0, "ab_ob_bridge": 2.0, "ab_ob_win": 2.0, "ab_ob_winp": 2.0, "ab_ob": None, "ab": None, "ab_ob_guess": None, "ab_ob_twist": None}
    assert {a: default_scale(a) for a in want} == want and all(default_scale(a) is None for a in ARMS if a not in (*B2_ARMS, *B4_ARMS))
    assert default_scale("ab_ob_b4", 1.5) == 1.5 and default_scale("ab_ob_bridge", 3.0) == 3.0 and default_scale("ab_ob", 3.0) == 3.0
    assert GUESS_ARMS == ("ab_ob_guess", "ab_ob_win", "ab_ob_winp") and TWIST_ARMS == ("ab_ob_twist", "ab_ob_win") and EXTRA_ARMS == ("ab_ob_twist", "ab_ob_win", "ab_ob_winp")
    assert B2_ARMS == ("ab_ob_b2", "ab_ob_win", "ab_ob_winp", "ab_ob_tag2", "ab_ob_bridge") and B4_ARMS == ("ab_ob_b4", *ADD8_ARMS, *ADD9_ARMS, *ADD10_ARMS)
    for a in ADD7_ARMS:
        assert a in ARMS and a in NEW_ARMS and a in OB_ARMS and not {a} & {*GUESS_ARMS, *TWIST_ARMS, *EXTRA_ARMS}, a
    out["scales"] = {a: default_scale(a) for a in ADD7_ARMS}
    L = SimpleNamespace(render=lambda sy, u: f"<sys>{sy}</sys>\n<user>{u}</user>")
    text = "Sam, my friend Zelmir moved to Kelmira on the Brontu ferry, and I need to remember to buy milk."
    t1, t2 = tag_prompt(L, text), tag_prompt2(L, text)
    sysline, fmt = "<sys>You extract facts from chat messages.</sys>", '[{"subject": "...", "relation": "...", "object": "..."}]'
    assert t1 != t2 and all(x in t for t in (t1, t2) for x in (sysline, text, fmt, "At most 5.", "If there are none, reply [].", "Use the names exactly as written in the message."))
    assert all(x in t2 for x in ("only the facts that link two names written in the message", "people, places, organisations, boats or other named things",
                                 'Sam, "I", "me", "my friend" and common nouns are not names', "Skip small talk about Sam's own tasks and requests")) and "link two names" not in t1
    fx, fy, st, an, mid = "Zelmir lives in Kelmira.", "Kelmira is near Harbor Light.", "Zelmir", "Harbor Light", "Kelmira"
    b, c = bridge_prompt(L, fx, fy, st, an, mid), chain_prompt(L, fx, fy)
    csys = "<sys>You are a careful assistant that studies facts.</sys>"
    assert b != c and all(x in t for t in (b, c) for x in (csys, fx, fy, "Question: ...\nAnswer: ...")) and all(x in b for x in (st, an, mid))
    assert f'share the name "{mid}"' in b and f'names "{st}", does not name "{mid}" or "{an}"' in b and f'answer must be "{an}" (a single name)' in b
    out["tag2_ok"] = out["bridge_ok"] = True

    mk = lambda a, r, o: Item((norm(a), norm(o)), a, o, r, 1)  # noqa: E731
    E = [mk("Zelmir", "lives in", "Kelmira"), mk("Kelmira", "is near", "Harbor Light"), mk("Harbor Light", "is in", "Oslo"), mk("Brontu", "sails to", "Kelmira")]
    by_fact = {it.fact: it for it in E}

    class Stop(Exception):
        pass

    def run(arm):  # the prompts Brain.tag and Brain.rem send to their first generate call
        got = {}

        def stub(name):
            def gen(prompts, n, **kw):
                got[name] = list(prompts)
                raise Stop
            return gen
        for name, f, a in (("tag", Brain.tag, (1,)), ("rem", Brain.rem, (E, 1, 0))):
            me = SimpleNamespace(L=L, a=SimpleNamespace(arm=arm, smoke=False, gist_min_days=3), gen=stub(name), mn=lambda n: n, raw={}, rng=random.Random(0), rem_done=Counter(), gist_done=Counter(),
                                 cap_chains=30, cap_gist=30, diary=SimpleNamespace(turns=[{"day": 1, "i": 0, "text": text}]))
            try:
                f(me, *a)
            except Stop:
                pass
        return got

    pair_of = lambda pr: [by_fact[f] for f in re.findall(r"^- (.+)$", pr, re.M)]  # noqa: E731
    shared = lambda p, q: ({norm(p.subj), norm(p.obj)} & {norm(q.subj), norm(q.obj)}).pop()  # noqa: E731
    for arm in ("ab", "ab_ob", "ab_ob_b2", "ab_ob_b4", "ab_ob_win", "ab_ob_winp", "ab_ob_tag2", "ab_ob_bridge"):
        got = run(arm)
        assert got["tag"] == [(t2 if arm == "ab_ob_tag2" else t1)], arm
        rem = got["rem"]
        assert len(rem) == 4, (arm, len(rem))  # kelmira: (Zelmir, Harbor Light), (Zelmir, Brontu), (Harbor Light, Brontu); harbor light: (Kelmira, Oslo)
        if arm != "ab_ob_bridge":
            assert sorted(rem) == sorted(chain_prompt(L, p.fact, q.fact) for p, q in (pair_of(r) for r in rem)) and all("share the name" not in r for r in rem), arm
            continue
        starts = []
        for k, r in enumerate(rem):
            p, q = pair_of(r)
            x = shared(p, q)
            mid_d = [n for n in (p.subj, p.obj) if norm(n) == x][0]
            fp, fq = [n for n in (p.subj, p.obj) if norm(n) != x][0], [n for n in (q.subj, q.obj) if norm(n) != x][0]
            start, answer = (fp, fq) if k % 2 == 0 else (fq, fp)
            assert r == bridge_prompt(L, p.fact, q.fact, start, answer, mid_d), (k, r)
            assert len({norm(start), norm(answer), norm(mid_d)}) == 3
            starts.append(start == fp)
        assert starts == [True, False, True, False], starts
    out["old_prompts_kept"] = ["ab", "ab_ob", "ab_ob_b2", "ab_ob_b4", "ab_ob_win", "ab_ob_winp"]
    out["tag2_only_tags"] = out["bridge_only_chains"] = out["bridge_alternates"] = True
    return out


def selftest_arms8():
    """Addendum-8 arms on stubs (no model, no RNG outside a local Random): (i) default_scale gives 4.0 for ab_ob_b4_names and ab_ob_b4_bridge (an explicit --budget-scale wins), both are valid arms, in
    B4_ARMS / NEW_ARMS / OB_ARMS and in none of GUESS / TWIST / EXTRA_ARMS; (ii) Brain.rem, run on a stub that records its first generate call, sends bridge_prompt for ab_ob_bridge and ab_ob_b4_bridge
    (start / answer alternate with the pair index) and chain_prompt for every other arm, and Brain.tag sends tag_prompt for both new arms; (iii) cap_names / name_vocab on a stub diary: words capitalised
    mid-sentence are found ('s stripped; a name that is lower case elsewhere is still matched case-insensitively), while Sam, I'm, weekdays, months, stoplist words and words capitalised only at a
    sentence start (turn start, after . ! ? or a newline) are not, and the vocabulary of day d ignores later days; (iv) name_pairs keeps the order of first appearance, skips pairs a live item links (either
    order; a dead item does not count) and dropped keys, then caps at 6; (v) parse_rel maps "no" / "No." / "" to no and "works at" to a relation; (vi) triple_status and the refactored Brain.tag keep
    tag()'s counters, items and tag_log exactly; (vii) Brain.names_pass asks only the pairs from (iv), turns yes answers into items, and appends them to the turn's existing tag_log entry (no second entry)."""
    from types import SimpleNamespace
    out = {}
    assert default_scale("ab_ob_b4_names") == 4.0 and default_scale("ab_ob_b4_bridge") == 4.0 and default_scale("ab_ob_b4_names", 1.5) == 1.5 and default_scale("ab_ob_b4") == 4.0
    assert ADD8_ARMS == ("ab_ob_b4_names", "ab_ob_b4_bridge") and BRIDGE_ARMS == ("ab_ob_bridge", "ab_ob_b4_bridge", *ADD9_ARMS, *ADD10_ARMS) and B4_ARMS == ("ab_ob_b4", *ADD8_ARMS, *ADD9_ARMS, *ADD10_ARMS)
    assert B2_ARMS == ("ab_ob_b2", "ab_ob_win", "ab_ob_winp", "ab_ob_tag2", "ab_ob_bridge") and GUESS_ARMS == ("ab_ob_guess", "ab_ob_win", "ab_ob_winp") and TWIST_ARMS == ("ab_ob_twist", "ab_ob_win")
    assert EXTRA_ARMS == ("ab_ob_twist", "ab_ob_win", "ab_ob_winp")
    for a in ADD8_ARMS:
        assert a in ARMS and a in NEW_ARMS and a in OB_ARMS and a in B4_ARMS and not {a} & {*GUESS_ARMS, *TWIST_ARMS, *EXTRA_ARMS}, a
    out["scales"] = {a: default_scale(a) for a in ADD8_ARMS}
    L = SimpleNamespace(render=lambda sy, u: f"<sys>{sy}</sys>\n<user>{u}</user>")
    npr = names_prompt(L, "Magomen works at Kelmira.", "Magomen", "Kelmira")
    assert npr == ('<sys>You extract facts from chat messages.</sys>\n<user>Message from Sam:\n"Magomen works at Kelmira."\n\nDoes this message say how "Magomen" and "Kelmira" are related? '
                   'If yes, reply with only the relation in 1 to 4 words (for example: works at, lives in, is the mentor of, owns the boat). If not, reply only: no</user>'), npr

    mk = lambda a, r, o: Item((norm(a), norm(o)), a, o, r, 1)  # noqa: E731
    E = [mk("Zelmir", "lives in", "Kelmira"), mk("Kelmira", "is near", "Harbor Light"), mk("Harbor Light", "is in", "Oslo"), mk("Brontu", "sails to", "Kelmira")]
    by_fact = {it.fact: it for it in E}
    text = "Sam, my friend Zelmir moved to Kelmira on the Brontu ferry."

    class Stop(Exception):
        pass

    def run(arm):  # the prompts Brain.tag and Brain.rem send to their first generate call
        got = {}

        def stub(name):
            def gen(prompts, n, **kw):
                got[name] = list(prompts)
                raise Stop
            return gen
        for name, f, a in (("tag", Brain.tag, (1,)), ("rem", Brain.rem, (E, 1, 0))):
            me = SimpleNamespace(L=L, a=SimpleNamespace(arm=arm, smoke=False, gist_min_days=3), gen=stub(name), mn=lambda n: n, raw={}, rng=random.Random(0), rem_done=Counter(), gist_done=Counter(),
                                 cap_chains=30, cap_gist=30, diary=SimpleNamespace(turns=[{"day": 1, "i": 0, "text": text}]))
            try:
                f(me, *a)
            except Stop:
                pass
        return got

    pair_of = lambda pr: [by_fact[f] for f in re.findall(r"^- (.+)$", pr, re.M)]  # noqa: E731
    shared = lambda p, q: ({norm(p.subj), norm(p.obj)} & {norm(q.subj), norm(q.obj)}).pop()  # noqa: E731
    for arm in ("ab", "ab_ob", "ab_ob_b2", "ab_ob_b4", "ab_ob_tag2", "ab_ob_bridge", "ab_ob_b4_names", "ab_ob_b4_bridge"):
        got = run(arm)
        assert got["tag"] == [tag_prompt2(L, text) if arm == "ab_ob_tag2" else tag_prompt(L, text)], arm
        rem = got["rem"]
        assert len(rem) == 4, (arm, len(rem))
        if arm not in BRIDGE_ARMS:
            assert sorted(rem) == sorted(chain_prompt(L, p.fact, q.fact) for p, q in (pair_of(r) for r in rem)) and all("share the name" not in r for r in rem), arm
            continue
        starts = []
        for k, r in enumerate(rem):
            p, q = pair_of(r)
            x = shared(p, q)
            mid_d = [n for n in (p.subj, p.obj) if norm(n) == x][0]
            fp, fq = [n for n in (p.subj, p.obj) if norm(n) != x][0], [n for n in (q.subj, q.obj) if norm(n) != x][0]
            start, answer = (fp, fq) if k % 2 == 0 else (fq, fp)
            assert r == bridge_prompt(L, p.fact, q.fact, start, answer, mid_d), (arm, k, r)
            starts.append(start == fp)
        assert starts == [True, False, True, False], (arm, starts)
    out["bridge_arms_use_bridge_prompt"] = [a for a in BRIDGE_ARMS if a not in (*ADD9_ARMS, *ADD10_ARMS)]  # the addendum-9 / -10 arms are checked in selftest_arms9 / selftest_arms10
    out["other_arms_use_chain_prompt"] = ["ab", "ab_ob", "ab_ob_b2", "ab_ob_b4", "ab_ob_tag2", "ab_ob_b4_names"]

    # (iii) candidate names (diary text only)
    rows = [(1, "hey, my friend Magomen moved to Kelmira with Papirar's dog. Brontu cooks well. Sam said OK on Monday in March, and I'm sure Christmas is near, Thanks"),
            (1, "meeting Torvald today.\nNewline word. Really? Question word. Wow! Exclaim word. He said. \"Quoted word\" ok, with \"x Yorick\" too"),
            (1, "i told magomen that PAPIRAR was with torvald. Zelmir smiled"),
            (2, "Later Quasar arrived with Orlin"), (2, "Sam's Mike's friend"), (3, "x Zebulon")]
    dia = Diary({"diary": [{"role": "user", "day": d_, "text": x} for d_, x in rows] + [{"role": "assistant", "day": 1, "text": "Sure Assistantname"}]})
    assert cap_names(rows[0][1]) == ["Magomen", "Kelmira", "Papirar"], cap_names(rows[0][1])
    assert cap_names(rows[1][1]) == ["Torvald", "Yorick"] and cap_names(rows[2][1]) == ["PAPIRAR"] and cap_names(rows[3][1]) == ["Quasar", "Orlin"], [cap_names(r[1]) for r in rows]
    assert cap_names(rows[4][1]) == ["Mike"] and cap_names("Zelmir and I") == [] and cap_names("a’s Mike’s Zed") == ["Mike", "Zed"] and cap_names("hi O'Brien and Zoe") == ["O'Brien", "Zoe"]
    assert name_vocab(dia, 1) == {"magomen": "Magomen", "kelmira": "Kelmira", "papirar": "Papirar", "torvald": "Torvald", "yorick": "Yorick"}, name_vocab(dia, 1)
    assert list(name_vocab(dia, 2)) == ["magomen", "kelmira", "papirar", "torvald", "yorick", "quasar", "orlin", "mike"] and "zebulon" not in name_vocab(dia, 2) and "zebulon" in name_vocab(dia, 3)
    assert not {"sam", "i", "i'm", "monday", "march", "ok", "thanks", "christmas", "brontu", "newline", "question", "exclaim", "quoted", "zelmir", "assistantname"} & set(name_vocab(dia, 3))
    out["vocab_day1"] = sorted(name_vocab(dia, 1))

    # (iv) pairs: order of first appearance, linked / dropped pairs skipped, cap 6
    nm = [(f"n{i}", f"N{i}") for i in range(1, 6)]
    it_ = lambda a, b, dead=False: Item((a, b), a.upper(), b.upper(), "r", 1, dead=dead)  # noqa: E731
    assert name_pairs(nm, {}, set()) == [("N1", "N2"), ("N1", "N3"), ("N1", "N4"), ("N1", "N5"), ("N2", "N3"), ("N2", "N4")]  # 10 pairs, the first 6
    assert name_pairs(nm, {}, set(), cap=2) == [("N1", "N2"), ("N1", "N3")] and NAMES_CAP == 6
    live = {("n1", "n2"): it_("n1", "n2"), ("n3", "n1"): it_("n3", "n1"), ("n1", "n4"): it_("n1", "n4", dead=True)}  # (n1,n2) live; (n3,n1) live in the other order; (n1,n4) dead: still asked
    assert name_pairs(nm, live, {("n2", "n3"), ("n5", "n4")}) == [("N1", "N4"), ("N1", "N5"), ("N2", "N4"), ("N2", "N5"), ("N3", "N4"), ("N3", "N5")]
    assert name_pairs(nm[:1], {}, set()) == [] and name_pairs([], {}, set()) == []
    out["pairs_ok"] = True

    # (v) answers
    for r in ("no", "No.", "", "  ", "NO", "no!", "No, the message does not say.", "no\nbecause they never meet", "None.", "nope", None):
        assert parse_rel(r) is None, r
    assert parse_rel("works at") == "works at" and parse_rel('"Is the mentor of".') == "Is the mentor of" and parse_rel("works at\nbecause the message says so") == "works at"
    assert parse_rel("Yes, lives in") == "lives in" and parse_rel("yes") == "" and parse_rel("  - owns the boat  ") == "owns the boat" and parse_rel("x" * 80) == "x" * 40
    assert parse_rel("no relation") == "no relation" and parse_rel("nobody") == "nobody"  # only no / none / nope + end or punctuation count as no
    out["parse_ok"] = True

    # (vi) the checks shared with tag(): same order, same counters (the expected counts below were taken from tag() before it called triple_status)
    dd = Diary({"diary": [{"role": "user", "day": 1, "text": "hey Zelmir lives in Kelmira, and Sam is tired. Brontu sails there too"}, {"role": "user", "day": 1, "text": "Harbor Light is in Oslo, remember Zelmir"}]})
    ts = lambda ti, a, b, dr=frozenset(): triple_status(dd, dr, ti, a, b)  # noqa: E731
    assert ts(0, "Zelmir", "Kelmira") == "ok" and ts(0, "zelmir", "KELMIRA") == "ok" and ts(0, "Zelmir", "Zelmir") == "invalid" and ts(0, "Sam", "Kelmira") == "invalid" and ts(0, "Q", "Kelmira") == "invalid"
    assert ts(0, "Zelmir", "x" * 61) == "invalid" and ts(0, "Zelmir", "Narvik") == "not_in_turn" and ts(1, "Zelmir", "Kelmira") == "not_in_turn" and ts(0, "Sam", "Narvik") == "invalid"
    assert ts(0, "Zelmir", "Kelmira", {("zelmir", "kelmira")}) == "dropped" and ts(0, "Zelmir", "Kelmira", {("kelmira", "zelmir")}) == "ok" and ts(0, "Zelmir", "Narvik", {("zelmir", "narvik")}) == "not_in_turn"
    canned = [json.dumps([{"subject": "Zelmir", "relation": "lives in", "object": "Kelmira"}, {"subject": "Sam", "relation": "is", "object": "tired"}, {"subject": "Brontu", "relation": "sails to", "object": "Kelmira"},
                          {"subject": "Zelmir", "relation": "x", "object": "Zelmir"}, {"subject": "Q", "relation": "x", "object": "Kelmira"}]),
              json.dumps([{"subject": "Harbor Light", "relation": "is in", "object": "Oslo"}, {"subject": "Zelmir", "relation": "is near", "object": "Narvik"}, {"subject": "Oslo", "relation": "has", "object": "Harbor Light"}]),
              "[]", "not json at all"]
    dd.turns += [dict(dd.turns[0], i=2, text="nothing special"), dict(dd.turns[0], i=3, text="garbage turn")]
    me = SimpleNamespace(L=SimpleNamespace(render=lambda sy, u: u), a=SimpleNamespace(arm="ab_ob_b4", smoke=False), diary=dd, items={}, dropped={("oslo", "harbor light")}, tag_log=[], raw={}, cov=Counter(),
                         gen=lambda p, n, **kw: canned[:len(p)], mn=lambda n: n)
    st = Brain.tag(me, 1)
    assert st == {"extracted": 8, "new_items": 3, "dropped_invalid": 3, "kept": 3, "dropped_not_in_turn": 1, "empty": 1, "parse_fail": 1, "turns": 4}, st
    assert list(me.items) == [("zelmir", "kelmira"), ("brontu", "kelmira"), ("harbor light", "oslo")] and [it.rel for it in me.items.values()] == ["lives in", "sails to", "is in"]
    assert me.tag_log == [(0, 1, [("Zelmir", "Kelmira"), ("Brontu", "Kelmira")]), (1, 1, [("Harbor Light", "Oslo")]), (2, 1, []), (3, 1, [])] and len(me.raw["tag"]) == 3
    out["tag_unchanged"] = st

    # (vii) Brain.names_pass on a stub (no model, no ground truth: the stub has no week / G): which pairs are asked, what a yes does, where it is logged
    rows = [(1, "hey, my friend Magomen moved to Kelmira with Papirar"), (2, "ok so magomen met Papirar near kelmira with Torvald"), (2, "lunch with Brontu"),
            (2, "ok Aldo, Berit, Cato, Dara and Enzo met"), (2, "later magomen and Papirar again, Torvald left"), (2, "nothing here")]
    dia = Diary({"diary": [{"role": "user", "day": d_, "text": x} for d_, x in rows]})
    items = {("magomen", "kelmira"): it_("magomen", "kelmira"), ("papirar", "torvald"): it_("papirar", "torvald", dead=True)}
    log = [(0, 1, [("Magomen", "Kelmira")]), (1, 2, [("Magomen", "Kelmira")]), (2, 2, []), (3, 2, []), (4, 2, []), (5, 2, [])]
    logs0 = [e[2] for e in log]
    asked, sent = [], []
    reply = {("Magomen", "Papirar"): "is the brother of", ("Kelmira", "Torvald"): "works at\nbecause", ("Magomen", "Torvald"): "No.", ("Aldo", "Berit"): "Yes", ("Aldo", "Cato"): "lives in"}

    def gen(prompts, n, **kw):
        assert n == 12 and kw == {}  # short, greedy, base model (the defaults of Brain.gen)
        sent.extend(prompts)
        res = []
        for pr in prompts:
            a, b = re.search(r'how "(.+?)" and "(.+?)" are related', pr).groups()
            asked.append((a, b))
            res.append(reply.get((a, b), "no"))
        return res
    Lr = SimpleNamespace(render=lambda sy, u: f"<sys>{sy}</sys>\n<user>{u}</user>")
    me = SimpleNamespace(L=Lr, diary=dia, items=items, dropped={("kelmira", "papirar")}, tag_log=log, raw={}, gen=gen, mn=lambda n: n)
    rec = Brain.names_pass(me, 2)
    want = [("Magomen", "Papirar"), ("Magomen", "Torvald"), ("Papirar", "Torvald"), ("Kelmira", "Torvald"),  # turn 1: (Magomen,Kelmira) is linked, (Papirar,Kelmira) is dropped (other order), the dead (Papirar,Torvald) item does not count
            ("Aldo", "Berit"), ("Aldo", "Cato"), ("Aldo", "Dara"), ("Aldo", "Enzo"), ("Berit", "Cato"), ("Berit", "Dara"),  # turn 3: 10 pairs, cap 6
            ("Magomen", "Papirar"), ("Magomen", "Torvald"), ("Papirar", "Torvald")]  # turn 4 (turn 2 has one candidate, turn 5 none)
    assert asked == want, asked
    texts = [rows[1][1]] * 4 + [rows[3][1]] * 6 + [rows[4][1]] * 3
    assert sent == [names_prompt(Lr, x, a, b) for x, (a, b) in zip(texts, want)]
    assert rec == {"candidates": 10, "turns": 5, "turns_ge2": 3, "pairs": 13, "yes": 5, "new_items": 4, "appended": 5, "dropped_invalid": 0, "dropped_not_in_turn": 0}, rec
    assert list(items) == [("magomen", "kelmira"), ("papirar", "torvald"), ("magomen", "papirar"), ("kelmira", "torvald"), ("aldo", "berit"), ("aldo", "cato")]
    assert [(v.subj, v.rel, v.obj, v.born) for v in list(items.values())[2:]] == [("Magomen", "is the brother of", "Papirar", 2), ("Kelmira", "works at", "Torvald", 2), ("Aldo", "is linked to", "Berit", 2), ("Aldo", "lives in", "Cato", 2)]
    assert [e[:2] for e in log] == [(0, 1), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2)] and all(e[2] is l0 for e, l0 in zip(log, logs0))  # no second entry for a turn; the same lists, extended
    assert [e[2] for e in log] == [[("Magomen", "Kelmira")], [("Magomen", "Kelmira"), ("Magomen", "Papirar"), ("Kelmira", "Torvald")], [], [("Aldo", "Berit"), ("Aldo", "Cato")], [("Magomen", "Papirar")], []]
    assert [r["pair"] for r in me.raw["names"]] == [list(p) for p in want[:3]] and me.raw["names"][0]["out"] == "is the brother of" and len(me.raw["names"]) == 3
    out["names_pass"] = rec
    return out


def selftest_arms9():
    """Addendum-9 arm on stubs (no model, no RNG outside a local Random): (i) default_scale gives 4.0 for ab_ob_b4_nb (an explicit --budget-scale wins); it is a valid arm, in NEW_ARMS / OB_ARMS /
    B4_ARMS / BRIDGE_ARMS / NAMES_ARMS and in none of GUESS / TWIST / EXTRA / B2_ARMS; (ii) every older arm keeps its membership: NEW_ARMS, OB_ARMS, B4_ARMS and BRIDGE_ARMS without the new arm are the
    addendum-8 tuples, and only ab_ob_b4_names (plus the new arm) is in NAMES_ARMS; (iii) Brain.rem, run on a stub that records its first generate call, sends bridge_prompt for ab_ob_b4_nb (start /
    answer alternate with the pair index) and Brain.tag sends tag_prompt; (iv) Brain.night, run on a stub that stops right after the names gate, calls names_pass for ab_ob_b4_nb and ab_ob_b4_names
    and for no other arm."""
    from types import SimpleNamespace
    out, nb = {}, "ab_ob_b4_nb"
    no10 = lambda t: tuple(a for a in t if a not in ADD10_ARMS)  # noqa: E731  (the addendum-10 arm is checked in selftest_arms10)
    assert ADD9_ARMS == (nb,) and no10(NAMES_ARMS) == ("ab_ob_b4_names", nb) and default_scale(nb) == 4.0 and default_scale(nb, 1.5) == 1.5 and default_scale(nb, 3.0) == 3.0
    assert nb in ARMS and nb in NEW_ARMS and nb in OB_ARMS and nb in B4_ARMS and nb in BRIDGE_ARMS and nb in NAMES_ARMS
    assert not {nb} & {*GUESS_ARMS, *TWIST_ARMS, *EXTRA_ARMS, *B2_ARMS, *DELTA_ARMS}
    out["scales"] = {nb: default_scale(nb)}

    # (ii) the older arms: the sets without the new arm are the addendum-8 tuples
    assert ADD4_ARMS == ("ab_ob_rot", "ab_ob_twist", "ab_ob_ther", "ab_ob_guess") and WIN_ARMS == ("ab_ob_win", "ab_ob_winp") and ADD7_ARMS == ("ab_ob_b4", "ab_ob_tag2", "ab_ob_bridge")
    old = ("ab_ob_full", "ab_ob_merge", "ab_ob_full_s", "ab_ob_local", *ADD4_ARMS, "ab_ob_b2", *WIN_ARMS, *ADD7_ARMS, *ADD8_ARMS)
    without = lambda t: tuple(a for a in no10(t) if a != nb)  # noqa: E731
    assert without(NEW_ARMS) == ("ab_ob", "ab_klctx", *old) and without(OB_ARMS) == ("ab_ob", *old)
    assert without(B4_ARMS) == ("ab_ob_b4", "ab_ob_b4_names", "ab_ob_b4_bridge") and without(BRIDGE_ARMS) == ("ab_ob_bridge", "ab_ob_b4_bridge")
    assert [a for a in no10(ARMS) if a in NAMES_ARMS] == ["ab_ob_b4_names", nb] and [a for a in no10(ARMS) if a in BRIDGE_ARMS] == ["ab_ob_bridge", "ab_ob_b4_bridge", nb]
    assert [a for a in no10(ARMS) if default_scale(a) == 4.0] == ["ab_ob_b4", "ab_ob_b4_names", "ab_ob_b4_bridge", nb]
    out["old_sets_kept"] = True

    # (iii) the prompts Brain.tag and Brain.rem send (the same stub as selftest_arms8)
    L = SimpleNamespace(render=lambda sy, u: f"<sys>{sy}</sys>\n<user>{u}</user>")
    mk = lambda a, r, o: Item((norm(a), norm(o)), a, o, r, 1)  # noqa: E731
    E = [mk("Zelmir", "lives in", "Kelmira"), mk("Kelmira", "is near", "Harbor Light"), mk("Harbor Light", "is in", "Oslo"), mk("Brontu", "sails to", "Kelmira")]
    by_fact = {it.fact: it for it in E}
    text = "Sam, my friend Zelmir moved to Kelmira on the Brontu ferry."

    class Stop(Exception):
        pass

    def run(arm):  # the prompts Brain.tag and Brain.rem send to their first generate call
        got = {}

        def stub(name):
            def gen(prompts, n, **kw):
                got[name] = list(prompts)
                raise Stop
            return gen
        for name, f, a in (("tag", Brain.tag, (1,)), ("rem", Brain.rem, (E, 1, 0))):
            me = SimpleNamespace(L=L, a=SimpleNamespace(arm=arm, smoke=False, gist_min_days=3), gen=stub(name), mn=lambda n: n, raw={}, rng=random.Random(0), rem_done=Counter(), gist_done=Counter(),
                                 cap_chains=30, cap_gist=30, diary=SimpleNamespace(turns=[{"day": 1, "i": 0, "text": text}]))
            try:
                f(me, *a)
            except Stop:
                pass
        return got

    pair_of = lambda pr: [by_fact[f] for f in re.findall(r"^- (.+)$", pr, re.M)]  # noqa: E731
    shared = lambda p, q: ({norm(p.subj), norm(p.obj)} & {norm(q.subj), norm(q.obj)}).pop()  # noqa: E731
    got = run(nb)
    assert got["tag"] == [tag_prompt(L, text)]
    rem = got["rem"]
    assert len(rem) == 4, len(rem)
    starts = []
    for k, r in enumerate(rem):
        p, q = pair_of(r)
        mid_d = [n for n in (p.subj, p.obj) if norm(n) == shared(p, q)][0]
        fp, fq = [n for n in (p.subj, p.obj) if norm(n) != shared(p, q)][0], [n for n in (q.subj, q.obj) if norm(n) != shared(p, q)][0]
        start, answer = (fp, fq) if k % 2 == 0 else (fq, fp)
        assert r == bridge_prompt(L, p.fact, q.fact, start, answer, mid_d), (k, r)
        assert r != chain_prompt(L, p.fact, q.fact) and f'share the name "{mid_d}"' in r
        starts.append(start == fp)
    assert starts == [True, False, True, False], starts
    for arm in ("ab", "ab_ob", "ab_ob_b2", "ab_ob_b4", "ab_ob_tag2", "ab_ob_bridge", "ab_ob_b4_names", "ab_ob_b4_bridge"):  # the older arms in the same stub: bridge_prompt only for the bridge arms
        assert all("share the name" in r for r in run(arm)["rem"]) == (arm in ("ab_ob_bridge", "ab_ob_b4_bridge")), arm
    out["nb_uses_bridge_prompt"] = out["nb_uses_tag_prompt"] = True

    # (iv) the names gate in Brain.night: a stub that stops at refresh, which comes right after the gate
    def gate(arm):
        called = []
        me = SimpleNamespace(a=SimpleNamespace(arm=arm, budget_scale=None, night_budget_s=None), L=SimpleNamespace(device=SimpleNamespace(type="cpu")), log=lambda m: None, tag=lambda d: {},
                             names_pass=lambda d: called.append(d) or {})

        def refresh(d):
            raise Stop
        me.refresh = refresh
        try:
            Brain.night(me, 2, None)
        except Stop:
            pass
        else:
            raise AssertionError("night did not reach refresh")
        return called == [2]
    fired = [arm for arm in no10(ARMS) if gate(arm)]
    assert fired == ["ab_ob_b4_names", nb], fired
    out["names_gate_arms"] = fired
    return out


def selftest_arms10():
    """Addendum-10 arm on stubs (no model, no RNG outside a local Random): (i) default_scale gives 4.0 for ab_ob_b4_nb_x4 (an explicit --budget-scale wins); it is a valid arm, in NEW_ARMS / OB_ARMS /
    B4_ARMS / BRIDGE_ARMS / NAMES_ARMS / TRIES_ARMS and in none of GUESS / TWIST / EXTRA / B2 / DELTA_ARMS; (ii) every older arm keeps its membership: the sets without the new arm are the addendum-9 tuples,
    and only the new arm is in TRIES_ARMS; (iii) Brain.rem, run on a stub that returns scripted texts: an old arm (ab_ob_b4_nb) sends one prompt per pair and its gist prompts, as before, and keeps its counters;
    the new arm sends each chain prompt X4_TRIES times in pair-major order (the same prompts as ab_ob_b4_nb, each x4) and each gist prompt once; (iv) the keep rule: a pair whose first samples fail the
    two-step check and whose later samples pass keeps exactly one dream (the first that passes), a pair whose samples all fail keeps nothing, a sample that fails the diary check or repeats a dream in the
    pool is skipped for the next one, and rem_done / chain_kept / chain_extra_dropped / chain_pairs_tried count that."""
    from types import SimpleNamespace
    out, nb, x4 = {}, "ab_ob_b4_nb", "ab_ob_b4_nb_x4"
    assert ADD10_ARMS == (x4,) and TRIES_ARMS == (x4,) and X4_TRIES == 4 and default_scale(x4) == 4.0 and default_scale(x4, 1.5) == 1.5 and default_scale(x4, 3.0) == 3.0
    assert x4 in ARMS and x4 in NEW_ARMS and x4 in OB_ARMS and x4 in B4_ARMS and x4 in BRIDGE_ARMS and x4 in NAMES_ARMS and x4 in TRIES_ARMS
    assert not {x4} & {*GUESS_ARMS, *TWIST_ARMS, *EXTRA_ARMS, *B2_ARMS, *DELTA_ARMS}
    out["scales"] = {x4: default_scale(x4)}

    # (ii) the older arms: the sets without the new arm are the addendum-9 tuples
    old = ("ab_ob_full", "ab_ob_merge", "ab_ob_full_s", "ab_ob_local", *ADD4_ARMS, "ab_ob_b2", *WIN_ARMS, *ADD7_ARMS, *ADD8_ARMS, *ADD9_ARMS)
    without = lambda t: tuple(a for a in t if a != x4)  # noqa: E731
    assert without(NEW_ARMS) == ("ab_ob", "ab_klctx", *old) and without(OB_ARMS) == ("ab_ob", *old)
    assert without(B4_ARMS) == ("ab_ob_b4", "ab_ob_b4_names", "ab_ob_b4_bridge", nb) and without(BRIDGE_ARMS) == ("ab_ob_bridge", "ab_ob_b4_bridge", nb) and without(NAMES_ARMS) == ("ab_ob_b4_names", nb)
    assert ARMS[-2:] == [nb, x4] and len(ARMS) == len(set(ARMS))
    assert [a for a in ARMS if a in NAMES_ARMS] == ["ab_ob_b4_names", nb, x4] and [a for a in ARMS if a in BRIDGE_ARMS] == ["ab_ob_bridge", "ab_ob_b4_bridge", nb, x4]
    assert [a for a in ARMS if a in TRIES_ARMS] == [x4] and [a for a in ARMS if default_scale(a) == 4.0] == ["ab_ob_b4", "ab_ob_b4_names", "ab_ob_b4_bridge", nb, x4]
    out["old_sets_kept"] = True

    # (iii) / (iv) Brain.rem on a stub: 4 pairs (the arms8 / arms9 facts), 2 gist items (days 3), scripted texts per (pair, sample)
    L = SimpleNamespace(render=lambda sy, u: f"<sys>{sy}</sys>\n<user>{u}</user>")
    mk = lambda a, r, o, dd: Item((norm(a), norm(o)), a, o, r, 1, days=dd)  # noqa: E731
    E = [mk("Zelmir", "lives in", "Kelmira", 3), mk("Kelmira", "is near", "Harbor Light", 0), mk("Harbor Light", "is in", "Oslo", 0), mk("Brontu", "sails to", "Kelmira", 3)]
    by_fact = {it.fact: it for it in E}
    pair_of = lambda pr: [by_fact[f] for f in re.findall(r"^- (.+)$", pr, re.M)]  # noqa: E731
    shared = lambda p, q: ({norm(p.subj), norm(p.obj)} & {norm(q.subj), norm(q.obj)}).pop()  # noqa: E731
    far = lambda it, x: [n for n in (it.subj, it.obj) if norm(n) != x][0]  # noqa: E731
    good_q = lambda fp, i, t: f"Who is two steps from {fp} (pair {i}, try {t})?"  # noqa: E731  (i: the pair's place in the sending order, t: the sample)

    def run(arm, script, seed=()):  # script[i] = tags of the samples of the i-th pair in sending order: good / bad (one step) / junk (no Question / Answer) / nov (passes the checks, the diary check fails)
        calls, texts, ans_of, unver = [], [], {}, set()
        nt = X4_TRIES if arm in TRIES_ARMS else 1

        def gen(prompts, n, **kw):
            calls.append((list(prompts), n, kw))
            if len(calls) > 1:  # the diary check: the answer unless the question is flagged
                qs = [re.search(r"Question: (.+?)</user>$", pr).group(1) for pr in prompts]
                return ["no idea" if q in unver else ans_of[q] for q in qs]
            for j, pr in enumerate(prompts):
                if "Fact about Sam's life" in pr:
                    it = by_fact[re.search(r"life: (.+?) \(it came", pr).group(1)]
                    q = f"Who does Sam usually see with {it.obj} (item {E.index(it)})?"
                    ans_of[q] = it.subj
                    texts.append(f"Question: {q}\nAnswer: {it.subj}")
                    continue
                p, q = pair_of(pr)
                fp, fq = far(p, shared(p, q)), far(q, shared(p, q))
                tag, qs = script[j // nt][j % nt], good_q(fp, j // nt, j % nt + 1)
                ans_of[qs] = fq
                if tag == "nov":
                    unver.add(qs)
                texts.append({"good": f"Question: {qs}\nAnswer: {fq}", "nov": f"Question: {qs}\nAnswer: {fq}", "bad": f"Question: Who is {fp}?\nAnswer: {fp}", "junk": "I cannot say."}[tag])
            return list(texts)
        me = SimpleNamespace(L=L, a=SimpleNamespace(arm=arm, smoke=False, gist_min_days=3), gen=gen, mn=lambda n: n, raw={}, rng=random.Random(0), rem_done=Counter(), gist_done=Counter(),
                             cap_chains=30, cap_gist=30, diary=SimpleNamespace(containing=lambda su, ob, d: [0, 1], label=lambda idx: "ctx"), leaky=lambda t: False,
                             rem_pool=[dict(x) for x in seed], rem_chains=[], examples={"rem": []})
        return me, Brain.rem(me, E, 1, 0), calls, texts

    # (a) an old arm: one prompt per pair (bridge_prompt, start / answer alternating with the pair index), then the gist prompts; every counter as before, no new counter
    me, st, calls, texts = run(nb, [["good"]] * 4)
    sent, n_gen, kw = calls[0]
    assert len(calls) == 2 and n_gen == 40 and kw == {"base": False, "sample": True} and calls[1][1] == 20 and len(sent) == 6, (len(calls), n_gen, kw, len(sent))
    for k, r in enumerate(sent[:4]):
        p, q = pair_of(r)
        x = shared(p, q)
        mid_d = [n for n in (p.subj, p.obj) if norm(n) == x][0]
        start, answer = (far(p, x), far(q, x)) if k % 2 == 0 else (far(q, x), far(p, x))
        assert r == bridge_prompt(L, p.fact, q.fact, start, answer, mid_d), (k, r)
    assert len({*sent[:4]}) == 4 and sorted(sent[4:]) == sorted(gist_prompt(L, it.fact, it.days) for it in (E[0], E[3]))
    assert me.raw["rem"] == [texts[0], texts[4]]
    assert st == {"chain_gen": 4, "chain_kept": 4, "gist_gen": 2, "gist_kept": 2, "pool": 6}, st
    assert all(v == 1 for v in me.rem_done.values()) and len(me.rem_done) == 4 and len(me.rem_chains) == 4
    chain_nb = sent[:4]
    out["old_arm_prompts_kept"] = True

    # (b) the new arm: each chain prompt 4 times, pair-major (the same prompts as ab_ob_b4_nb), each gist prompt once; one sample per prompt goes to the checks; the sample capture is [first chain, first gist]
    me, st, calls, texts = run(x4, [["good"] * 4] * 4)
    sent = calls[0][0]
    assert len(sent) == 18 and sent[:16] == [r for r in chain_nb for _ in range(X4_TRIES)] and sorted(sent[16:]) == sorted(gist_prompt(L, it.fact, it.days) for it in (E[0], E[3]))
    assert Counter(sent)[chain_nb[0]] == 4 and len({*sent[16:]}) == 2 and calls[0][1:] == (40, {"base": False, "sample": True})
    assert me.raw["rem"] == [texts[0], texts[16]]
    assert st == {"chain_pairs_tried": 4, "chain_gen": 16, "chain_kept": 4, "chain_extra_dropped": 12, "gist_gen": 2, "gist_kept": 2, "pool": 6}, st
    assert all(v == 1 for v in me.rem_done.values()) and len(me.rem_done) == 4 and len(me.rem_chains) == 4
    out["x4_prompts_pair_major"] = True

    # (c) / (d) the keep rule. pair 0: two one-step samples, then two good ones; pair 1: four one-step samples; pair 2: its first good sample is already in the pool; pair 3: junk, one-step, good but
    # the diary check fails, good
    ends = [(far(p, shared(p, q)), far(q, shared(p, q))) for p, q in (pair_of(r) for r in chain_nb)]
    seed = [{"q": good_q(ends[2][0], 2, 1), "a": ends[2][1], "keys": [], "kind": "chain", "night": 0, "cycle": 0}]
    script = [["bad", "bad", "good", "good"], ["bad"] * 4, ["good"] * 4, ["junk", "bad", "nov", "good"]]
    me, st, calls, texts = run(x4, script, seed)
    assert calls[0][0][:16] == [r for r in chain_nb for _ in range(X4_TRIES)]
    keys = [frozenset(i.key for i in pair_of(r)) for r in chain_nb]
    kept = [(frozenset(d_["keys"]), d_["q"]) for d_ in me.rem_pool[1:] if d_["kind"] == "chain"]
    assert kept == [(keys[0], good_q(ends[0][0], 0, 3)), (keys[2], good_q(ends[2][0], 2, 2)), (keys[3], good_q(ends[3][0], 3, 4))], kept
    assert len(me.rem_pool) == 1 + 3 + 2 and me.rem_pool[0] == seed[0]
    assert [me.rem_done[k] for k in keys] == [1, 0, 1, 1] and sorted(me.rem_chains) == sorted((p.key, q.key) for p, q in (pair_of(r) for r in (chain_nb[0], chain_nb[2], chain_nb[3])))
    assert st == {"chain_pairs_tried": 4, "chain_gen": 16, "dropped_bad": 2 + 4 + 1, "parse_fail": 1, "dropped_unverified": 1, "dropped_dup": 1, "chain_extra_dropped": 1 + 2 + 0,
                  "chain_kept": 3, "gist_gen": 2, "gist_kept": 2, "pool": 6}, st
    out["x4_keep_rule"] = st
    return out


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


def card_key(it, o):  # --card-stats / --skip-known: the identity of item it's card o (cards are compared by content, so a re-dreamed item's new cards are new keys)
    return ("p", it.key, o) if isinstance(o, str) else ("q", it.key, o[0], o[1])


def rem_key(x):  # the same for a REM-pool dream
    return ("r", x["q"], x["a"])


def other(it, x):  # (display shared, display other) of the item w.r.t. normalized string x
    return (it.subj, it.obj) if norm(it.subj) == x else (it.obj, it.subj)


def bridge_roles(p, q, x, k):  # ab_ob_bridge: (start, answer, middle name) of REM pair k: start = p's far end for even k, q's for odd k (both directions get dreamed); middle = p's display form
    (mid, fp), fq = other(p, x), other(q, x)[1]
    return (fp, fq, mid) if k % 2 == 0 else (fq, fp, mid)


# addendum 8 (NAMES_ARMS): the diary-only candidate-name finder, the pair builder, the answer parser, and the triple checks shared with Brain.tag
NAMES_CAP = 6  # pairs asked per turn
NAME_TOK = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?")  # a word, optionally with one apostrophe part (I'm, O'Brien, Mike's)
NAME_STOP = {norm(w) for w in ("Sam I I'm I've I'll I'd OK Ok Okay Hey Hi Hello Thanks Also Anyway But And So The A An My It This That English Christmas God Mom Dad Yes No Yeah Please Sorry Well Oh "
                               "Monday Tuesday Wednesday Thursday Friday Saturday Sunday January February March April May June July August September October November December").split()} | GENERIC


def cap_names(text):  # capitalised words (an 's is stripped) that are NOT sentence-initial: not the turn's first word, not right after . ! ? or a newline (opening quotes / brackets are skipped); stoplist and GENERIC out
    text, out = text.replace("\u2019", "'"), []
    for m in NAME_TOK.finditer(text):
        w = m.group()
        w = w[:-2] if w.lower().endswith("'s") else w
        if len(w) < 2 or not w[0].isupper() or norm(w) in NAME_STOP:
            continue
        pre = text[:m.start()]
        before = pre.rstrip(" \t\r\n\"'\u201c\u2018([")
        if not before or "\n" in pre[len(before):] or before[-1] in ".!?":
            continue
        out.append(w)
    return out


def name_vocab(diary, d):  # {norm: display form first seen} of the candidate names in the user turns of days <= d (diary text only: no ground truth, no test strings)
    v = {}
    for t in diary.turns:
        if t["day"] <= d:
            for w in cap_names(t["text"]):
                v.setdefault(norm(w), w)
    return v


def name_pairs(names, items, dropped, cap=NAMES_CAP):  # names: [(norm, display)] in order of first appearance in the turn; unordered pairs in that order, minus pairs a live item links (either order) or whose key is dropped; first `cap`
    out = []
    for (na, a), (nb, b) in itertools.combinations(names, 2):
        if any(k in items and not items[k].dead for k in ((na, nb), (nb, na))) or (na, nb) in dropped or (nb, na) in dropped:
            continue
        out.append((a, b))
        if len(out) == cap:
            break
    return out


def parse_rel(txt):  # names_prompt reply -> None for "no" (empty, "no", "no." or "no" + punctuation; also none / nope), else the relation: first line, a leading "yes" and quotes / punctuation off, at most 40 chars ("" for a bare yes)
    lines = [x.strip() for x in str(txt or "").strip().splitlines() if x.strip()]
    if not lines or re.match(r"(?:no|none|nope)(?:$|[^\w\s])", lines[0].lower()):
        return None
    return re.sub(r"^yes\b[\s\W]*", "", lines[0], flags=re.I).strip(" \t\"'`\u201c\u201d\u2018\u2019.,;:!?-*()[]")[:40].strip()


def strip_think(txt, effort="low"):  # addendum 11b: a stage-1 reply (thinking, stopped at the close tag or the end of the turn) -> (thinking text without trailing close tag / im_end, whether the model closed the block itself); effort (11c): whose close tag (default "low": 11b's)
    txt, closed, close = str(txt or "").strip(), False, K2_THINK_SHUT[effort]
    while txt.endswith(close) or txt.endswith(K2_END):
        closed |= txt.endswith(close)
        txt = txt[:-len(close if txt.endswith(close) else K2_END)].rstrip()
    return txt, closed


NEG_RE = re.compile(r"(?:no|not|none|nothing|nope|unrelated)\b", re.I)  # addendum 11c (K2 only): a reply that starts with one of these words (whole word) says no


def parse_rel_k2(txt):  # addendum 11c (K2 only): parse_rel, plus a first line that starts with the word no / not / none / nothing / nope / unrelated is "no" (None); "now", "north", "nobody's" are not
    lines = [x.strip() for x in str(txt or "").strip().splitlines() if x.strip()]
    return None if lines and NEG_RE.match(lines[0]) else parse_rel(txt)


def triple_status(diary, dropped, ti, sj, ob):  # the checks tag() puts a (subject, object) through, in its order: "invalid" / "not_in_turn" (turn index ti) / "dropped" (key in `dropped`) / "ok"
    if min(len(sj), len(ob)) < 2 or max(len(sj), len(ob)) > 60 or norm(sj) == norm(ob) or norm(sj) in GENERIC or norm(ob) in GENERIC:
        return "invalid"
    if ti not in diary.occurs(sj) or ti not in diary.occurs(ob):
        return "not_in_turn"
    return "dropped" if (norm(sj), norm(ob)) in dropped else "ok"


def rem_split(views, pool, n_rem, rem_total, nr0):  # --rem-views: REM-pool examples per step of one REM cycle (n_rem steps), about views x pool x n_rem / rem_total in all, at most nr0 a step, spread evenly
    q = min(n_rem * nr0, round(views * pool * n_rem / max(rem_total, 1)))
    return [(j + 1) * q // n_rem - j * q // n_rem for j in range(n_rem)]  # floor((j+1) q / n) - floor(j q / n): sums to q, every step q/n rounded down or up, the extras spread over the cycle (not the first q % n steps)


def rem_plan(steps, arm, mult=1.0):  # a night's per-cycle (NREM steps, REM steps) for `steps` reference steps: the quarters of `steps`, NREM_SHARE of each (all of it for ab_norem), the rest REM; addendum 14: the REM count x mult, rounded (mult 1.0: untouched)
    cyc = [steps // 4 + (1 if i < steps % 4 else 0) for i in range(4)]
    plan = []
    for ci, c in enumerate(cyc):
        n = c if arm == "ab_norem" else round(c * NREM_SHARE[ci])
        plan.append((n, c - n if mult == 1.0 else round((c - n) * mult)))
    return plan


class Brain:
    def __init__(s, L, pm, args, week, diary, leak, replay, arc_val, arc_base, log):
        s.L, s.pm, s.a, s.week, s.diary, s.leak, s.replay, s.log = L, pm, args, week, diary, leak, replay, log
        s.arc_val, s.arc_base = arc_val, arc_base
        s.items, s.dropped, s.checked = {}, set(), set()
        s.rem_pool, s.rem_chains, s.rem_done, s.gist_done = [], [], Counter(), Counter()
        s.rem_dir_done = Counter()  # addendum 14 (--rem-dirs both): kept chain dreams per unit (frozenset of the pair's two item keys, norm(start name))
        s.upd_log, s.tag_log, s.examples = [], [], {"dreams": [], "probes": [], "rem": [], "now": []}
        if args.arm in EXTRA_ARMS:
            s.examples["twist"] = []
        if getattr(args, "dream_vary", "off") != "off":
            s.examples["vary"] = []
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
        s.skip_f = getattr(args, "skip_known", None)  # --skip-known: keep probability of a card that was right at its last practice (None: off)
        s.track = s.skip_f is not None or getattr(args, "card_stats", False)  # per-example outcomes of every training step (--card-stats)
        s.card, s.card_items = {}, defaultdict(set)  # card key -> right at its last closed-book / text practice; item key -> its card keys
        s.bk, s.cs, s.seen, s.last_ob = None, Counter(), set(), False  # the (card key, kind, item key) list of the batch being built; tonight's counts; tonight's practised cards; qa_ex's last coin

    # ---- plumbing
    def mn(s, n):
        return min(n, 24) if s.a.smoke else n

    def sc(s, n):  # addendum 5: a night's knob n at work scale s.scale (untouched at 1, so the reference night is exactly ab_ob's)
        return n if s.scale == 1 or n <= 0 else max(1, round(n * s.scale))

    def tsc(s, n):  # addendum 15: a generation knob n at the text scale s.tscale (the work scale unless --text-scale says otherwise, so tsc == sc without the flag)
        return n if s.tscale == 1 or n <= 0 else max(1, round(n * s.tscale))

    def set_scale(s, scale):  # the night's work: dreams per item (and their generation length), item cap, REM chains, gist dreams (at the text scale, addendum 15); the training steps are s.sc(steps) at the work scale
        s.scale = scale
        ts = getattr(s.a, "text_scale", None)  # addendum 15 (--text-scale; a stub args without it is the default)
        s.tscale = scale if ts is None else ts
        s.k, s.cap_items, s.cap_chains, s.cap_gist, s.dream_new = s.tsc(K), s.tsc(s.a.max_dream_items), s.tsc(s.a.rem_chains), s.tsc(s.a.rem_gist), s.tsc(400)
        s.kp = math.ceil(s.k / 4) if getattr(s.a, "dream_vary", "off") != "off" else None  # addendum 15 (--dream-vary): paraphrases per nrem_prompt (None: k)

    def gen(s, prompts, max_new, base=True, sample=False, temp=0.8, eos=None):  # eos: stop id(s) for Lang.generate (None: its default, the end of the turn)
        if not prompts:
            return []
        s.pm.eval()
        if base:
            with s.pm.disable_adapter():
                return s.L.generate(s.pm, prompts, max_new=max_new, bs=s.a.gen_bs, sample=sample, temp=temp, eos=eos)
        return s.L.generate(s.pm, prompts, max_new=max_new, bs=s.a.gen_bs, sample=sample, temp=temp, eos=eos)

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
        tp = tag_prompt2 if s.a.arm == "ab_ob_tag2" else tag_prompt  # addendum 7: the sharper tagging prompt for ab_ob_tag2 only
        raw = s.gen([tp(s.L, t["text"]) for t in turns], s.mn(160))
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
                ck = triple_status(s.diary, s.dropped, t["i"], sj, ob)  # addendum 8: the checks are shared with names_pass (same order, same counters; a dropped key is skipped without a counter)
                if ck != "ok":
                    if ck != "dropped":
                        st["dropped_" + ck] += 1
                    continue
                key = (norm(sj), norm(ob))
                if key not in s.items:
                    s.items[key] = Item(key, sj, ob, rl or "is linked to", d)
                    st["new_items"] += 1
                got.append((sj, ob))
            st["kept"] += len(got)
            s.tag_log.append((t["i"], d, got))
        st["turns"] = len(turns)
        return dict(st)

    def names_pass(s, d):  # addendum 8 (NAMES_ARMS): re-read the day's turns for pairs of candidate names that no item links yet; each non-"no" answer is a triple that goes through tag()'s checks (triple_status) and joins the turn's tag_log entry
        turns = [t for t in s.diary.turns if t["day"] == d]
        vocab = name_vocab(s.diary, d)  # from the diary text of days <= d only
        pats, ask, st = {n: pat(n) for n in vocab}, [], Counter()
        for t in turns:
            hits = sorted((m.start(), n) for n, p in pats.items() for m in [p.search(s.diary.low[t["i"]])] if m)  # candidates in this turn (case-insensitive, whole word), by first appearance
            st["turns_ge2"] += len(hits) >= 2
            ask += [(t, a, b) for a, b in name_pairs([(n, vocab[n]) for _, n in hits], s.items, s.dropped)]
        k2 = getattr(s.L, "k2", False)  # (a stub Lang without .k2 is Qwen-style)
        if k2:  # addendum 11b / 11c: stage 1 thinks (K2_NAMES_EFFORT, at most NAMES_THINK_MAX tokens, stops at that effort's close tag / end of turn); stage 2 = prompt + thinking + close tag, then the answer as on Qwen
            p1 = [names_prompt(s.L, t["text"], a, b, think=True, effort=K2_NAMES_EFFORT) for t, a, b in ask]
            th = [strip_think(x, K2_NAMES_EFFORT) for x in s.gen(p1, s.mn(NAMES_THINK_MAX), eos=s.L.think_eos(K2_NAMES_EFFORT))]  # [(thinking, closed by the model)]
            raw = s.gen([p + x + K2_THINK_SHUT[K2_NAMES_EFFORT] for p, (x, _) in zip(p1, th)], s.mn(12))
        else:
            raw = s.gen([names_prompt(s.L, t["text"], a, b) for t, a, b in ask], s.mn(12))
        s.raw["names"] = [{"text": t["text"][:200], "pair": [a, b], "out": r, **({"think": th[i][0][:400]} if k2 else {})} for i, ((t, a, b), r) in list(enumerate(zip(ask, raw)))[:3]]
        got_of = {ti: got for ti, dd, got in s.tag_log if dd == d}  # the lists tag() logged for this day's turns (appended to in place: no second entry per turn)
        for (t, a, b), txt in zip(ask, raw):
            rl = (parse_rel_k2 if k2 else parse_rel)(txt)  # 11c: K2 also reads a reply that starts with not / nothing / unrelated ... as no
            if rl is None:
                continue
            st["yes"] += 1
            ck = triple_status(s.diary, s.dropped, t["i"], a, b)
            if ck != "ok":
                if ck != "dropped":
                    st["dropped_" + ck] += 1
                continue
            key = (norm(a), norm(b))
            if key not in s.items:
                s.items[key] = Item(key, a, b, rl or "is linked to", d)
                st["new_items"] += 1
            if t["i"] not in got_of:  # (tag() logs every turn of the day; this only keeps the diagnostics whole if one were missing)
                got_of[t["i"]] = []
                s.tag_log.append((t["i"], d, got_of[t["i"]]))
            got_of[t["i"]].append((a, b))
            st["appended"] += 1
        rec = {"candidates": len(vocab), "turns": len(turns), "turns_ge2": st["turns_ge2"], "pairs": len(ask), "yes": st["yes"], "new_items": st["new_items"], "appended": st["appended"],
               "dropped_invalid": st["dropped_invalid"], "dropped_not_in_turn": st["dropped_not_in_turn"]}
        if k2:  # thinking tokens per question (the thinking text, close tag not counted) and the stage-1 outputs that did not close the block themselves (cap hit, or the turn ended first)
            rec.update(think_tokens_mean=round(sum(len(s.L.ids(x)) for x, _ in th) / len(th), 1) if th else 0.0, think_capped=sum(not c for _, c in th))
        return rec

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
            prompts.append(nrem_prompt(s.L, ctx, it, s.k, s.kp))  # s.kp: None, or ceil(k/4) paraphrases under --dream-vary (addendum 15)
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
                for p in paras[:s.kp or s.k]:
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
        if getattr(a, "dream_vary", "off") != "off":  # addendum 15: the style texts, after all the normal dreaming (as twist)
            s.vary(d, need, {it.key: c for it, k, c in meta if k == "dream"}, st)
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

    def vary(s, d, need, ctxs, st):
        """--dream-vary {mix,plain} (addendum 15), after all of the night's normal dreaming and in the place of twist: for each item of `need` that has question cards or a probe the BASE model writes n = ceil(k/4) texts in each of 3 styles
        (VARY_STYLES[mode]: story, note, then weird (mix) or plain2 (plain)), one prompt per item and style (vary_prompt), each style sampled under its own fixed seed (seed * 100 + night + 43 + style index; the global torch RNG state is put back, so
        the main sampling stream is as without the flag). A text is kept under twist's checks: it names both entities, is not a test leak, restates no older value (stale_hit), and the base model, shown only the text, answers a check card (card j % len
        of the item's cards, its probe if none; j: the text's number in its reply). Kept texts are appended to it.para after the item's plain paraphrases of the night. Stats: vary_<style>_<VARY_STATS>."""
        a = s.a
        styles, n = VARY_STYLES[a.dream_vary], math.ceil(s.k / 4)
        cur = [it for it in need if a.smoke or it.qa or it.probe]
        st["vary_skipped_no_check"] = len(need) - len(cur)
        s.raw["vary"] = {}
        cand = []  # (style, item, text, check question, check answer)
        for si, style in enumerate(styles):
            with seeded_rng(a.seed * 100 + d + 43 + si, s.L.device):
                raw = s.gen([vary_prompt(s.L, ctxs[it.key], it, style, n) for it in cur], s.mn(80 * n), sample=True)
            s.raw["vary"][style] = raw[:2]
            for it, txt in zip(cur, raw):
                ents, chk = [it.subj, it.obj], it.qa or ([it.probe] if it.probe else [])
                texts = parse_scenes(txt, n)
                if a.smoke and not texts:  # tiny random model emits noise: fabricate one text so the path runs
                    texts = [f"In a {style} about Sam, {it.subj} {it.rel} {it.obj}."]
                if not texts:
                    st[f"vary_{style}_parse_fail"] += 1
                for j, x in enumerate(texts):
                    st[f"vary_{style}_gen"] += 1
                    if s.leaky(x):
                        st[f"vary_{style}_dropped_test_leak"] += 1
                    elif not all(e.lower() in x.lower() for e in ents):
                        st[f"vary_{style}_dropped_missing_entities"] += 1
                    elif s.stale_hit(it, x):
                        st[f"vary_{style}_dropped_stale"] += 1
                    else:
                        cand.append((style, it, x, *(chk[j % len(chk)] if chk else ("", ""))))
        ver = s.gen([ctx_prompt(s.L, x, q) for _, _, x, q, _ in cand], 20)
        seen = set()
        for (style, it, x, q, ans), v in zip(cand, ver):
            keep = False
            if not has_ans(ans, v) and not a.smoke:
                st[f"vary_{style}_dropped_unverified"] += 1
            elif (it.key, norm(x)) in seen or any(norm(x) == norm(p) for p in it.para):
                st[f"vary_{style}_dropped_dup"] += 1
            else:
                seen.add((it.key, norm(x)))
                it.para = [*it.para, x]  # a new list: the night's logged dream examples share the old one
                st[f"vary_{style}_kept"] += 1
                keep = True
            if len(s.examples["vary"]) < 12:
                s.examples["vary"].append({"night": d, "item": it.fact, "style": style, "text": x, "check_q": q, "check_a": ans, "verifier": v, "kept": keep})

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
    def qa_ex(s, q, a):  # OB_ARMS: with p=0.5 (--ob-share) the Q&A example is open-book (diary-test prompt, notes of days <= tonight), else closed-book
        s.last_ob = False
        if s.a.arm in OB_ARMS:
            ob = s.ob_rng.random() < getattr(s.a, "ob_share", 0.5)
            s.last_ob = ob
            s.cov["qa_open_book" if ob else "qa_closed_book"] += 1
            if ob:
                if "ob_example" not in s.raw:
                    s.raw["ob_example"] = {"prompt_tail": diary_prompt(s.L, s.diary, q, s.day)[-600:], "answer": a}
                return ex_qa_ob(s.L, s.diary, q, a, s.day)
        return ex_qa(s.L, q, a)

    def wt(s, ex, its):  # ab_ob_ther: the practice example of a salient item (a REM chain: either of its two) gets loss weight 0.5
        return ex + (0.5,) if s.a.arm == "ab_ob_ther" and any(s.salient(i) for i in its) else ex

    def dream_ex(s, it):
        return s.card_ex(it, s.rng.choice(it.para + it.qa))

    def card_ex(s, it, o):  # the practice example of item it's card o (a paraphrase, or a (q, a) pair); with s.bk on, its (card key, kind, item key) is recorded
        ex = s.wt(ex_text(s.L, o) if isinstance(o, str) else s.qa_ex(o[0], o[1]), [it])
        if s.bk is not None:
            s.bk.append((card_key(it, o), "text" if isinstance(o, str) else "qa_ob" if s.last_ob else "qa_cb", it.key))
        return ex

    def skip(s, key):  # --skip-known: True = draw again (the card was right at its last practice and its keep coin, p = skip_f, came up tails)
        if not s.card.get(key):
            return False
        s.cs["known_drawn"] += 1
        if s.rng.random() < s.skip_f:
            s.cs["known_kept"] += 1
            return False
        return True

    def rem_ex(s, live, nr):  # the REM part of a REM step: nr verified REM-pool dreams as practice Q&A
        if s.skip_f is None:
            xs = s.rng.choices(live, k=nr)
        else:  # --skip-known: one dream at a time, a known one kept with probability skip_f (the last of SKIP_TRIES draws is kept)
            xs = []
            for _ in range(nr):
                for t in range(SKIP_TRIES):
                    x = s.rng.choice(live)
                    if t == SKIP_TRIES - 1 or not s.skip(rem_key(x)):
                        break
                xs.append(x)
        out = []
        for x in xs:
            out.append(s.wt(s.qa_ex(x["q"], x["a"]), [s.items[k] for k in x["keys"]]))
            if s.bk is not None:
                s.bk.append((rem_key(x), "rem_ob" if s.last_ob else "rem_cb", None))
        return out

    def train_step(s, tr, batch):  # tr.step(batch); with s.bk on (--card-stats / --skip-known), each example's outcome goes into s.card and tonight's counts
        bk, s.bk = s.bk, None
        if bk is None:
            tr.step(batch)
            return
        stats = tr.step(batch, rows=True) or []
        assert len(stats) == len(bk), (len(stats), len(bk))
        qt, c = min(3, 4 * (tr.i - 1) // tr.n), s.cs  # the quarter of the night this step was in
        for (key, kind, ik), r in zip(bk, stats):
            c[f"n_{kind}"] += 1
            c[f"known_{kind}"] += r["known"]
            c[f"acc_{kind}"] += r["acc"]
            c[f"ce_{kind}"] += r["ce"]
            s.seen.add(key)
            if kind in ("qa_ob", "rem_ob"):  # an open-book answer can be read off the notes: it says nothing about memory
                continue
            c[f"q{qt}_n"] += 1
            c[f"q{qt}_known"] += r["known"]
            s.card[key] = r["known"]
            if ik is not None:
                s.card_items[ik].add(key)

    def card_reset(s, E, pre):  # a new night's counts; a wrong morning probe marks every card of that item not known
        s.cs, s.seen = Counter(), set()
        for it in E:
            if it.key in pre and not pre[it.key][0]:
                for k in s.card_items.get(it.key, ()):
                    if s.card.get(k):
                        s.card[k] = False
                        s.cs["reset_by_probe"] += 1

    def card_summary(s):  # rec["cards"]: tonight's practice examples that the model already answered right before their step, by kind and by quarter of the night
        c = s.cs
        r4 = lambda x: round(x, 4)  # noqa: E731
        kinds = sorted(k[2:] for k in c if k.startswith("n_"))
        out = {"by_kind": {k: {"examples": int(c[f"n_{k}"]), "known_at_step": r4(c[f"known_{k}"] / c[f"n_{k}"]), "acc": r4(c[f"acc_{k}"] / c[f"n_{k}"]),
                               "ce": r4(c[f"ce_{k}"] / c[f"n_{k}"])} for k in kinds}}
        n = sum(c[f"q{i}_n"] for i in range(4))
        out["known_share"] = r4(sum(c[f"q{i}_known"] for i in range(4)) / n) if n else None  # closed-book Q&A, texts and closed-book REM dreams
        out["known_share_by_quarter"] = [r4(c[f"q{i}_known"] / c[f"q{i}_n"]) if c[f"q{i}_n"] else None for i in range(4)]
        out["cards_practised"], out["cards_known_now"] = len(s.seen), sum(1 for k in s.seen if s.card.get(k))
        out.update({k: int(c[k]) for k in ("reset_by_probe", "known_drawn", "known_kept")})
        return out

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
            pick = None
            for t in range(SKIP_TRIES if s.skip_f is not None else 1):  # --skip-known: a known card is kept with probability skip_f, else the slot is drawn again (the last draw is kept)
                if act and (not con or s.rng.random() < 0.75):
                    it = s.rng.choices(act, cum_weights=cum)[0]
                elif con:
                    it = s.rng.choice(con)
                else:
                    break
                pick = (it, s.rng.choice(it.para + it.qa))
                if s.skip_f is None or t == SKIP_TRIES - 1 or not s.skip(card_key(*pick)):
                    break
            if pick:
                out.append(s.card_ex(*pick))
        return out

    # ---- 7. REM (current adapter, short fact sentences only; the diary then checks each dream)
    def rem(s, E, d, ci):
        a, st = s.a, Counter()
        mode, dirs = getattr(a, "rem_chain_mode", "default"), getattr(a, "rem_dirs", "alt")  # addendum 14: the defaults are the code path as before (a stub args without the flags is the default)
        assert (mode == "default" and dirs == "alt") or (a.arm in BRIDGE_ARMS and a.arm not in TRIES_ARMS), (a.arm, mode, dirs)
        qmode, think = mode in ("q", "q_think"), mode in ("think", "q_think")  # q: the reply is only the question (parse_q1, the answer is the given far end); think (K2): the think block is open first (two stages)
        tr = getattr(s, "rem_trace", None)  # k2_chain_probe only: a list that gets one dict per chain sample (reply, fate)

        def mark(t_, why, **kw):  # a chain sample's fate for the trace
            if t_ is not None:
                t_.update(why=why, **kw)

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
        allp, pairs = pairs, pairs[:s.cap_chains]
        gist = [it for it in E if it.days >= a.gist_min_days]
        s.rng.shuffle(gist)
        gist.sort(key=lambda it: s.gist_done[it.key])
        gist = gist[:s.cap_gist]
        roles = ukey = None  # per sample: the bridge prompt's (start, answer, middle name) / its unit (--rem-dirs both)
        if dirs == "both":  # addendum 14: a pair is two units (start / answer in each direction, bridge_roles k = 0 / 1); a unit is tried every cycle until it has a kept dream, then never again
            uk = lambda p, q, rl: (frozenset((p.key, q.key)), norm(rl[0]))  # noqa: E731
            both = lambda p, q, x: [bridge_roles(p, q, x, kk) for kk in (0, 1)]  # noqa: E731
            st["units_open"] = sum(s.rem_dir_done[uk(p, q, rl)] == 0 for p, q, x in allp for rl in both(p, q, x))  # (over every pair, before the pair cap)
            units = [(p, q, x, rl) for p, q, x in pairs for rl in both(p, q, x) if s.rem_dir_done[uk(p, q, rl)] == 0]
            s.rng.shuffle(units)
            units = units[:2 * s.cap_chains]
            st["units_tried"] = len(units)
            rep = [t for t in units for _ in range(getattr(a, "rem_tries", 1))]  # unit-major: each unit rem_tries times in a row
            smp, roles, ukey = [t[:3] for t in rep], [t[3] for t in rep], [uk(t[0], t[1], t[3]) for t in rep]
        else:
            smp = pairs  # one (pair, chain prompt) per sample
        if a.arm in BRIDGE_ARMS:  # addendum 7 / 8: guided chain prompt (start / answer alternate with the pair index k, the checks below do not care which end is which)
            roles = roles or [bridge_roles(p, q, x, k) for k, (p, q, x) in enumerate(smp)]
            mk = bridge_q_prompt if qmode else bridge_prompt
            chains = [mk(s.L, p.fact, q.fact, *rl, think=think, effort=REM_EFFORT if think else None) for (p, q, x), rl in zip(smp, roles)]
        else:
            chains = [chain_prompt(s.L, p.fact, q.fact) for p, q, _ in pairs]
        if a.arm in TRIES_ARMS:  # addendum 10: every chain prompt is sampled X4_TRIES times, pair-major; the keep rule (one dream per pair) is in the last loop
            smp, chains = [t for t in pairs for _ in range(X4_TRIES)], [c for c in chains for _ in range(X4_TRIES)]
            roles = [r for r in roles for _ in range(X4_TRIES)] if roles else roles
            st["chain_pairs_tried"] = len(pairs)
        gp = [gist_prompt(s.L, it.fact, it.days) for it in gist]
        if mode == "default":  # chains and gists in one call (the sampling stream as before)
            raw = s.gen(chains + gp, s.mn(40), base=False, sample=True)
            craw, graw = raw[:len(smp)], raw[len(smp):]
            s.raw.setdefault("rem", []).extend(raw[:1] + raw[len(smp):len(smp) + 1])
        else:  # addendum 14: chains (one or two stages), then the gists in their own call
            if think:  # stage 1 thinks (REM_EFFORT, at most REM_THINK_MAX sampled tokens, stops at that effort's close tag / end of turn); stage 2 = prompt + thinking + ONE close tag, then the reply (40 tokens)
                th = [strip_think(x, REM_EFFORT) for x in s.gen(chains, s.mn(REM_THINK_MAX), base=False, sample=True, eos=s.L.think_eos(REM_EFFORT))]  # [(thinking, closed by the model)]
                craw = s.gen([c + x + K2_THINK_SHUT[REM_EFFORT] for c, (x, _) in zip(chains, th)], s.mn(40), base=False, sample=True)
                st["chain_think_tokens"], st["chain_think_capped"] = sum(len(s.L.ids(x)) for x, _ in th), sum(not c for _, c in th)
            else:
                craw = s.gen(chains, s.mn(40), base=False, sample=True)
            graw = s.gen(gp, s.mn(40), base=False, sample=True)
            s.raw.setdefault("rem", []).extend(craw[:1] + graw[:1])
        cand = []  # (kind, items, q, a, ctx, unit, trace record)
        for k, ((p, q, x), txt) in enumerate(zip(smp, craw)):
            st["chain_gen"] += 1
            t_ = None
            if tr is not None:
                t_ = {"night": d, "cycle": ci, "mode": mode, "facts": [p.fact, q.fact], "roles": roles[k] if roles else None, "reply": txt}
                if think:
                    t_.update(think=th[k][0][:400], think_tokens=len(s.L.ids(th[k][0])), closed=th[k][1])
                tr.append(t_)
            if qmode:  # the answer is the given far end
                qs = parse_q1(txt)
                r = (qs, roles[k][1]) if qs else None
            else:
                r = parse_qa1(txt)
            fp, fq = other(p, x)[1], other(q, x)[1]
            if r is None and a.smoke:
                r = (f"Who is two steps from {fp}?", fq)
            if r is None:
                st["parse_fail"] += 1
                mark(t_, "parse_fail")
                continue
            qq, aa = r
            es = [e for e in (fp, fq) if e.lower() in aa.lower()]
            other_e = fq if es and es[0] == fp else fp
            if s.leaky(qq):
                st["dropped_test_leak"] += 1
                mark(t_, "test_leak", q=qq, a=aa)
            elif len(es) != 1 or es[0].lower() in qq.lower() or other_e.lower() not in qq.lower() or x in qq.lower():
                st["dropped_bad"] += 1
                mark(t_, "bad", q=qq, a=aa)
            else:
                idx = sorted(set(s.diary.containing(p.subj, p.obj, d)[-2:]) | set(s.diary.containing(q.subj, q.obj, d)[-2:]))
                cand.append(("chain", (p, q), qq, es[0], s.diary.label(idx), ukey[k] if ukey else None, t_))
                mark(t_, "candidate", q=qq, a=es[0])
        for it, txt in zip(gist, graw):
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
                cand.append(("gist", (it,), qq, es[0], s.diary.label(s.diary.containing(it.subj, it.obj, d)[-4:]), None, None))
        ver = s.gen([ctx_prompt(s.L, c, q) for _, _, q, _, c, _, _ in cand], 20)
        have = {(norm(x["q"]), x["a"].lower()) for x in s.rem_pool}
        got, got_u = set(), set()  # TRIES_ARMS: the pairs that kept a dream this cycle (the first sample, in sample order, that passed every check); --rem-dirs both: the same per unit
        for (kind, its, q, ans, c, unit, t_), v in zip(cand, ver):
            if not has_ans(ans, v) and not s.a.smoke:
                st["dropped_unverified"] += 1
                mark(t_, "unverified", verify=v)
            elif kind == "chain" and frozenset((its[0].key, its[1].key)) in got:
                st["chain_extra_dropped"] += 1
                mark(t_, "extra")
            elif unit is not None and unit in got_u:
                st["unit_extra_dropped"] += 1
                mark(t_, "extra")
            elif (norm(q), ans.lower()) in have:
                st["dropped_dup"] += 1
                mark(t_, "dup")
            else:
                have.add((norm(q), ans.lower()))
                s.rem_pool.append({"q": q, "a": ans, "keys": [i.key for i in its], "kind": kind, "night": d, "cycle": ci})
                st[f"{kind}_kept"] += 1
                mark(t_, "kept")
                if kind == "chain":
                    s.rem_chains.append((its[0].key, its[1].key))
                    s.rem_done[frozenset((its[0].key, its[1].key))] += 1
                    if a.arm in TRIES_ARMS:
                        got.add(frozenset((its[0].key, its[1].key)))
                    if unit is not None:
                        s.rem_dir_done[unit] += 1
                        got_u.add(unit)
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
        if a.arm in NAMES_ARMS:  # addendum 8 / 9: re-read the day for names (before refresh, so the new items get their mention counts)
            rec["names_pass"] = s.names_pass(d)
            s.log(f"[night {d}] names {rec['names_pass']}")
        s.refresh(d)
        lap("tag")
        rec["update_detection"] = s.detect(d)
        lap("update_detection")
        E = [it for it in list(s.items.values()) if s.elig(it)]
        rec["dream_stats"] = s.dream(d, E)
        lap("dream")
        if a.arm in EXTRA_ARMS:
            s.log(f"[night {d}] twist {({k: v for k, v in rec['dream_stats'].items() if k.startswith('twist')})}")
        if getattr(a, "dream_vary", "off") != "off":  # addendum 15: the per-style yields of tonight (Brain.vary's stats keys)
            rec["dream_vary"] = {"mode": a.dream_vary, "styles": list(VARY_STYLES[a.dream_vary]), "k": s.k, "kp": s.kp, "n_per_style": math.ceil(s.k / 4),
                                "stats": {k: rec["dream_stats"].get(k, 0) for k in ["vary_skipped_no_check", *(f"vary_{sty}_{x}" for sty in VARY_STYLES[a.dream_vary] for x in VARY_STATS)]}}
            s.log(f"[night {d}] vary {rec['dream_vary']}")
        pre = s.probe(E, conf=a.arm in GUESS_ARMS)
        s.morning(E, pre)
        if s.track:
            s.card_reset(E, pre)
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
        mult = getattr(a, "rem_steps_mult", 1.0)  # addendum 14: each cycle's REM steps x mult; the Trainer's cosine schedule covers the night's true total (steps at mult 1.0)
        plan = rem_plan(steps, a.arm, mult)
        total = sum(n + r for n, r in plan)
        if a.budget_scale is not None or a.night_budget_s is not None:
            rec["budget"] = {"scale": s.scale, "steps": steps, "steps_ref": ref_n, "k": s.k, "max_dream_items": s.cap_items, "rem_chains": s.cap_chains,
                             "rem_gist": s.cap_gist, "bench": bench, "text_scale": getattr(a, "text_scale", None)}  # text_scale (addendum 15): None = the generation knobs are at `scale`
            s.log(f"[night {d}] budget {rec['budget']}")
        act = [it for it in E if not it.consol and (it.para or it.qa)]
        con = [it for it in cons if it.para or it.qa]
        cum = list(itertools.accumulate(s.prio(it) for it in act))
        rec.update({"eligible": len(E), "eligible_active": n_act, "consolidated": len(cons), "superseded_total": sum(1 for it in s.items.values() if it.sup_by and not it.dead),
                    "items_total": sum(1 for it in s.items.values() if not it.dead), "with_dreams": len(act) + len(con), "steps_planned": total, "rem_steps_mult": mult,
                    "probe_recall_pre": acc(ok for ok, _ in pre.values()), "elig_by_class": s.elig_by_class(E)})
        s.log(f"[night {d}] items {rec['items_total']} eligible {len(E)} (active {n_act}, consolidated {len(cons)}) steps {total} probe_pre {rec['probe_recall_pre']}")
        snap = s.snapshot()
        card0 = dict(s.card)  # --skip-known: a reverted night puts the cards' known flags back with the weights
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
        tr = Trainer(s.L, s.pm, a, kl_pool, total, a.seed * 100 + d)
        if track:
            pk.append(s.peak_gb(True))  # the night so far; the peak is then reset for the training phase alone (REM generation included)
        rem_stats, done, nrem_n, rem_n = [], 0, 0, 0
        if not (act or con):
            s.log(f"[night {d}] no dream content; skipping training")
        else:
            for ci, (n_nrem, n_rem) in enumerate(plan):
                for _ in range(n_nrem):
                    s.bk = [] if s.track else None
                    s.train_step(tr, s.nrem(act, cum, con, a.bsz))
                nrem_n, done = nrem_n + n_nrem, done + n_nrem
                if n_rem > 0:
                    lap("train")
                    rs = s.rem(E, d, ci)
                    lap("rem_generate")
                    rem_stats.append(rs)
                    live = [x for x in s.rem_pool if all(not s.items[k].dead and not s.items[k].sup_by for k in x["keys"])]
                    nr0 = round(0.7 * a.bsz) if live else 0
                    split = [nr0] * n_rem
                    if getattr(a, "rem_views", None):  # about rem_views practices per live dream tonight; the rest of the REM slots go to NREM cards
                        split = rem_split(a.rem_views, len(live), n_rem, sum(r for _, r in plan), nr0)
                        rec.setdefault("rem_quota", []).append({"cycle": ci, "pool": len(live), "rem_examples": sum(split), "default": nr0 * n_rem})
                    for nr in split:
                        s.bk = [] if s.track else None
                        s.train_step(tr, s.rem_ex(live, nr) + s.nrem(act, cum, con, a.bsz - nr))
                    rem_n, done = rem_n + n_rem, done + n_rem
                    s.cov["rem_steps"] += n_rem
        lap("train")
        rec.update({"steps": done, "steps_nrem": nrem_n, "steps_rem": rem_n, "rem_stats": rem_stats, "loss_curve": tr.curve[-6:]})
        if s.track:
            rec["cards"] = s.card_summary()
            s.log(f"[night {d}] cards known_share {rec['cards']['known_share']} by quarter {rec['cards']['known_share_by_quarter']} "
                  f"by kind {({k: v['known_at_step'] for k, v in rec['cards']['by_kind'].items()})} known drawn {rec['cards']['known_drawn']} kept {rec['cards']['known_kept']}")
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
            s.card = card0
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
                "rem": {"chain_pairs_kept_total": len(s.rem_chains), "twohop_dreamed": sum(dreamed), "twohop_total": len(dreamed), "pool": len(s.rem_pool),
                        "twohop_dreamed_flags": dreamed}}

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
def q4_quant(x, group, bits, store_dtype, grid=None):
    """The MLX affine grid and codes of the float32 tensor x (last dim divisible by group), as (q, scale, bias) shaped [-1, groups, group] / [-1, groups, 1], all float32: per group scale = (max-min)/(2^bits-1)
    (1e-8 when max == min), bias = min, both rounded to store_dtype, taken from the groups of `grid` (a tensor of x's shape; default x itself); q = clamp(round((x-bias)/scale), 0, 2^bits-1)."""
    levels = 2 ** bits - 1
    xg = x.reshape(-1, x.shape[-1] // group, group)
    g = xg if grid is None else grid.float().reshape(xg.shape)
    mx, mn = g.amax(-1, keepdim=True), g.amin(-1, keepdim=True)
    scale = (mx - mn) / levels
    scale = torch.where(scale == 0, torch.full_like(scale, 1e-8), scale)
    scale, bias = scale.to(store_dtype).float(), mn.to(store_dtype).float()
    scale = torch.where(scale == 0, torch.full_like(scale, 1e-8), scale)  # a rounded-to-zero scale (underflow) stays safe
    return torch.clamp(torch.round((xg - bias) / scale), 0, levels), scale, bias


def q4_fake(w, group=64, bits=4, store_dtype=None, grid=None):
    """MLX affine quantize-dequantize of a 2-D+ tensor along its last dim; returns w' (same shape and dtype as w) or None if the last dim
    is not divisible by group. Per group: scale = (max-min)/(2^bits-1) (1e-8-ish safe value when max == min), bias = min, both rounded to
    store_dtype (default w.dtype); q = clamp(round((w-bias)/scale), 0, 2^bits-1); w' = q*scale + bias. Math in float32 (q4_quant). grid: a tensor of w's shape
    whose groups give the scale and bias instead of w's own (addendum 13, the frozen grid); w may be float32 while store_dtype is bf16 (the grid of an fp32 sum)."""
    if w.dim() < 1 or w.shape[-1] % group:
        return None
    q, scale, bias = q4_quant(w.detach().float(), group, bits, store_dtype or w.dtype, grid)
    return (q * scale + bias).reshape(w.shape).to(w.dtype)


Q4_MLX_MOE_BITS = ((r"\.mlp\.gate\.weight$", 8), (r"\.mlp\.shared_expert_gate\.weight$", 8))  # mlx-community/Qwen3.6-35B-A3B-4bit: 8-bit group 64 for every router weight and shared-expert gate
Q4_MLX_MOE_PARAMS = (r"\.mlp\.experts\.(?:gate_up_proj|down_proj)$", r"\.mlp\.gate\.weight$")  # ... and 4-bit for the fused 3-D expert Parameters (group along the last = input dim) and the router Parameter
Q4_CHUNK = 1 << 26  # elements per fp32 working piece: a tensor larger than this is quantized in slices along dim 0 (the groups lie along the last dim, so the result is the same bit for bit)


def q4_inplace(w, group, bits, chunk=Q4_CHUNK):
    """Fake-quantize the tensor w in place (no grad) like q4_fake, in slices along dim 0 of at most `chunk` elements when it is larger (a fused 3-D expert tensor, a big embedding), so the
    float32 temporaries stay small. Returns the relative Frobenius error, or None when the last dim is not divisible by group (w untouched). A tensor of <= chunk elements takes the
    one-piece path (q4_fake on the whole tensor)."""
    if w.dim() < 1 or w.shape[-1] % group:
        return None
    if w.numel() <= chunk or w.dim() < 2 or w.shape[0] < 2:
        wq = q4_fake(w, group, bits)
        den = w.float().norm().item()
        err = (wq.float() - w.float()).norm().item() / den if den > 0 else 0.0
        w.copy_(wq)
        return err
    rows = max(1, chunk // (w.numel() // w.shape[0]))
    e2 = d2 = 0.0
    for i in range(0, w.shape[0], rows):
        piece = w[i:i + rows]
        wq = q4_fake(piece, group, bits)
        e2 += (wq.float() - piece.float()).double().pow(2).sum().item()
        d2 += piece.float().double().pow(2).sum().item()
        piece.copy_(wq)
        del wq
    return math.sqrt(e2 / d2) if d2 > 0 else 0.0


def q4_apply(lm, group=64, bits=4, bits_for=None, extra=None, chunk=None, skip=()):
    """Fake-quantize (in place, no grad) the weight of every nn.Linear and nn.Embedding in lm; tied tensors once (by data_ptr). The scale /
    bias storage dtype is the weight's own dtype (bf16 on cuda, fp32 on cpu). Returns {tensors, skipped, params, mean_rel_fro, group, bits}.
    bits_for: sequence of (regex, bits); a tensor whose name (e.g. "model.layers.3.mlp.shared_expert_gate.weight") matches a regex (re.search, first hit wins) is quantized to those bits
    instead of `bits`. extra: sequence of regexes; every other Parameter (a fused 3-D expert tensor, a Parameter-holding router module) whose name matches is quantized too, along its last dim.
    With both left at None nothing changes (same tensors, same numbers, same result keys, every tensor quantized in one piece); otherwise tensors above `chunk` elements (default Q4_CHUNK) are quantized in
    slices along dim 0 (same weights bit for bit; the error statistic is then summed in float64) and the result also has by_bits ({bits: {tensors, params}}) and pattern_hits (the prefix bits: or extra: plus the regex -> how many tensors it matched).
    skip: tensors (e.g. the 16-bit LoRA weights, or weights already quantized another way) that are left alone and not counted."""
    seen, nq, ns, npar, errs = {w.data_ptr() for w in skip}, 0, 0, 0, []
    bits_for = [(re.compile(r), int(b)) for r, b in (bits_for or [])]
    extra = [re.compile(r) for r in (extra or [])]
    by_bits, hits = {}, Counter()
    if chunk is None:
        chunk = Q4_CHUNK if (bits_for or extra) else 1 << 62

    def one(name, w):
        nonlocal nq, ns, npar
        if w.data_ptr() in seen:
            return
        seen.add(w.data_ptr())
        nb = bits
        for rx, b in bits_for:
            if rx.search(name):
                nb = b
                hits["bits:" + rx.pattern] += 1
                break
        err = q4_inplace(w.data, group, nb, chunk)
        if err is None:
            ns += 1
            return
        errs.append(err)
        nq += 1
        npar += w.numel()
        d = by_bits.setdefault(str(nb), {"tensors": 0, "params": 0})
        d["tensors"] += 1
        d["params"] += w.numel()

    with torch.no_grad():
        for n, m in lm.named_modules():
            if isinstance(m, (torch.nn.Linear, torch.nn.Embedding)):
                one(f"{n}.weight" if n else "weight", m.weight)
        if extra:
            for n, p in lm.named_parameters():
                for rx in extra:
                    if rx.search(n):
                        hits["extra:" + rx.pattern] += 1
                        one(n, p)
                        break
    out = {"tensors": nq, "skipped": ns, "params": npar, "mean_rel_fro": sum(errs) / len(errs) if errs else None, "group": group, "bits": bits}
    if bits_for or extra:
        out.update(by_bits=by_bits, pattern_hits=dict(hits))
    return out


# ------------------------------------------------------------------ q4 eval (addendum 13): the final model under F0 / Q0 / Q / Qf
Q4_CONDS = ("F0", "Q0", "Q", "Qf")  # bf16 W | 4-bit W | 4-bit (W + delta_w, fresh grid) | 4-bit (W + delta_w on the grid of W); the delta hooks are off in all four


def q4_type(name):  # module type of a weight / module name: the last name component ('weight' and 'base_layer' dropped), in_proj_qkv / _z / _a / _b merged
    t = [x for x in name.split(".") if x not in ("weight", "base_layer")][-1]
    return "in_proj_*" if t.startswith("in_proj") else t


def q4_tensors(lm):  # {module name: weight} of every nn.Linear / nn.Embedding (the LoRA ones too), a tied tensor once
    seen, out = set(), {}
    for n, m in lm.named_modules():
        if isinstance(m, (torch.nn.Linear, torch.nn.Embedding)) and m.weight.data_ptr() not in seen:
            seen.add(m.weight.data_ptr())
            out[n] = m.weight
    return out


def q4_delta_mods(lm):  # [(name, base Linear)] of every module that has a delta_w
    return [(n, m) for n, m in lm.named_modules() if hasattr(m, "delta_w")]


def q4_lora_w(lm):  # the weights of the LoRA A / B Linears: they stay 16-bit and out of every quantization
    return [w for n, w in q4_tensors(lm).items() if ".lora_" in n]


@torch.no_grad()
def q4_sig(ts, chunk=1 << 24):
    """Position-sensitive integer checksum over the bytes of tensors: per tensor sum_k byte_k * (k % 251 + 1) (int64, in chunks), chained over the tensors."""
    tot = 0
    for t in ts:
        b, s = t.detach().contiguous().reshape(-1).view(torch.uint8), 0
        for i in range(0, b.numel(), chunk):
            c = b[i:i + chunk].to(torch.int64)
            s += int((c * (torch.arange(i, i + c.numel(), device=c.device) % 251 + 1)).sum())
        tot = (tot * 1000003 + s) % (1 << 61)
    return tot


@torch.no_grad()
def q4_condition(lm, cond, group=64, bits=4):
    """Put the weights of lm into q4-eval condition cond (in place; the caller restores them). F0: untouched. Q0: q4_apply on W. Q: every weight with a delta_w becomes W.float() + delta_w.float() (fp32), quantized from that
    fp32 sum on its own grid (scale / bias stored in the weight's dtype) and written back; Qf: the same sum rounded to codes on the grid of W (frozen scale and bias), clamped to 0..2^bits-1. All other tensors as in Q0.
    A tensor whose last dim is not divisible by group keeps the unquantized sum. The LoRA weights are never quantized. Returns q4_apply's stats (None for F0)."""
    assert cond in Q4_CONDS, cond
    if cond == "F0":
        return None
    dm = q4_delta_mods(lm) if cond in ("Q", "Qf") else []
    for _, bl in dm:
        w = bl.weight.data
        x = w.float() + bl.delta_w.data.float()
        wq = q4_fake(x, group, bits, w.dtype, grid=w.float() if cond == "Qf" else None)
        w.copy_(x if wq is None else wq)  # fp32 -> the weight's dtype only after the quantize-dequantize
        del x, wq
    return q4_apply(lm, group, bits, skip=[bl.weight for _, bl in dm] + q4_lora_w(lm))


@torch.no_grad()
def q4_delta_stats(lm, group=64, bits=4):
    """Weights at W (nothing changed): for every module with a delta_w, the 4-bit codes of W (grid of W), of W + delta_w on its own grid (Q) and on the grid of W (Qf), and |delta_w| / scale (scale: the group step of W).
    Per module type (q4_type) and overall: modules, codes, share of codes that differ from Q0's (Q, Qf), mean |delta_w| / scale. codes_all: every quantizable (last dim divisible by group) non-LoRA weight."""
    skip, c, tot = {w.data_ptr() for w in q4_lora_w(lm)}, defaultdict(Counter), Counter()
    for n, bl in q4_delta_mods(lm):
        w = bl.weight.data
        if w.shape[-1] % group:
            c[q4_type(n)]["skipped"] += 1
            continue
        x0, d = w.float(), bl.delta_w.data.float()
        x1, (q0, s0, _) = x0 + d, q4_quant(x0, group, bits, w.dtype)
        qa, qb = q4_quant(x1, group, bits, w.dtype)[0], q4_quant(x1, group, bits, w.dtype, grid=x0)[0]
        r = c[q4_type(n)]
        r["modules"] += 1
        r["codes"] += q0.numel()
        r["diff_Q"] += int((qa != q0).sum())
        r["diff_Qf"] += int((qb != q0).sum())
        r["abs_delta_over_scale"] += float((d.reshape(q0.shape).abs() / s0).double().sum())
    out = {}
    for t, r in sorted(c.items()):
        tot.update(r)
        out[t] = q4_share(r)
    return {"overall": q4_share(tot), "by_type": out, "codes_all": sum(w.numel() for n, w in q4_tensors(lm).items() if w.data_ptr() not in skip and w.shape[-1] % group == 0)}


def q4_share(r):  # q4_delta_stats: a counter -> shares
    n = max(r["codes"], 1)
    return {"modules": r["modules"], "skipped": r["skipped"], "codes": r["codes"], "share_changed_Q": r["diff_Q"] / n, "share_changed_Qf": r["diff_Qf"] / n, "mean_abs_delta_over_scale": r["abs_delta_over_scale"] / n}


def q4_eval(lm, group, bits, score, log=print, save=None, out=None):
    """Addendum 13: run score(cond) (-> dict) with the weights of lm in each of Q4_CONDS and the delta switch off, restoring them bit for bit after each (CPU snapshot of every Linear / Embedding weight; asserted by torch.equal
    on a few tensors and q4_sig over all weights and all delta_w) and the switch to what it was. Returns {group, bits, lora_B_nonzero, lora_B_max_abs, stats, <cond>: {**score(cond), q4_apply, wall_seconds}}; a dict given as `out` is that result, filled in as it goes (save() after each part)."""
    ts = list(q4_tensors(lm).values())
    saved = [w.data.to("cpu", copy=True) for w in ts]
    dws = [bl.delta_w.data for _, bl in q4_delta_mods(lm)]
    sig, dsig, prev = q4_sig([w.data for w in ts]), q4_sig(dws), _DELTA["on"]
    few = sorted({0, len(ts) // 2, len(ts) - 1, max(range(len(ts)), key=lambda i: ts[i].numel())})
    out = {} if out is None else out
    bmax = max([float(p.detach().abs().max()) for n, p in lm.named_parameters() if "lora_B" in n] or [0.0])  # the LoRA is left as it is (16-bit, in every condition)
    out.update(group=group, bits=bits, lora_B_nonzero=bmax > 0, lora_B_max_abs=bmax)
    ok = lambda x: "n/a" if x is None else f"{x:.3f}"  # noqa: E731
    try:
        out["stats"] = o = q4_delta_stats(lm, group, bits)
        log(f"[q4eval] lora_B_nonzero {out['lora_B_nonzero']} (max |B| {bmax:.3g}); {o['overall']['modules']} delta modules, codes differing from Q0: Q {o['overall']['share_changed_Q']:.2%}, Qf {o['overall']['share_changed_Qf']:.2%}; mean |delta| / scale {o['overall']['mean_abs_delta_over_scale']:.3f}")
        if save:
            save()
        for cond in Q4_CONDS:
            t1 = time.time()
            try:
                _DELTA["on"] = False
                st = q4_condition(lm, cond, group, bits)
                r = {**score(cond), "q4_apply": st}
            finally:
                _DELTA["on"] = prev
                with torch.no_grad():
                    for w, s in zip(ts, saved):
                        w.data.copy_(s)
                assert all(torch.equal(ts[i].data.cpu(), saved[i]) for i in few) and q4_sig([w.data for w in ts]) == sig and q4_sig(dws) == dsig and _DELTA["on"] == prev, f"q4_eval: restore after {cond} failed"
            r["wall_seconds"] = time.time() - t1
            out[cond] = r
            sc, ae = r.get("scores") or {}, r.get("arc_easy") or {}
            log(f"[q4eval:{cond}] recall C2+C4 {ok((sc.get('forward') or {}).get('C24'))} twohop {ok((sc.get('twohop') or {}).get('acc'))} arc {ok(ae.get('acc'))} wall {r['wall_seconds']:.0f}s")
            if save:
                save()
    finally:
        _DELTA["on"] = prev
    return out


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
    assert set(st) == {"tensors", "skipped", "params", "mean_rel_fro", "group", "bits"}, "default result keys changed"
    out["moe"] = selftest_q4_moe(g)
    return out


def selftest_q4_moe(g):
    """The Qwen-MoE extension of q4_apply on tiny stand-ins: (i) a 3-D tensor quantizes along its last dim like the 2-D case (<= 2^bits distinct values per group, error <= scale/2); (ii) the sliced path
    (q4_inplace with a tiny chunk) equals the one-piece path bit for bit, in bf16 too; (iii) with the MLX recipe a fused 3-D expert pair and a Parameter router are quantized (router and
    shared-expert gate in 8 bits, error <= scale/2 of the 8-bit grid and below the 4-bit error), the other Linears in 4 bits, nothing else touched (norm, conv); (iv) without the options the 3-D
    Parameters and the router are left alone."""
    out = {}
    w3 = torch.randn(3, 8, 128, generator=g)
    for bits in (4, 8):
        wq = q4_fake(w3, 64, bits)
        gr, gq = w3.reshape(-1, 2, 64), wq.reshape(-1, 2, 64)
        assert wq.shape == w3.shape
        if bits == 4:
            assert max(len(set(r.tolist())) for r in gq.reshape(-1, 64)) <= 2 ** bits, "3-D: more distinct values than levels"
        scale = (gr.amax(-1, keepdim=True) - gr.amin(-1, keepdim=True)) / (2 ** bits - 1)
        assert bool(((gq - gr).abs() <= scale / 2 * (1 + 1e-5) + 1e-6).all()), f"3-D bits {bits}: error above scale/2"
        out[f"3d_bits{bits}_max_err_over_half_scale"] = ((gq - gr).abs() / (scale / 2)).max().item()
    for dt in (torch.float32, torch.bfloat16):
        big = torch.randn(5, 4, 128, generator=g).to(dt)
        whole, parts = big.clone(), big.clone()
        r1 = q4_inplace(whole, 64, 4, chunk=10 ** 9)
        r2 = q4_inplace(parts, 64, 4, chunk=2 * 4 * 128)  # 2 rows of dim 0 per slice: slices of 2, 2 and 1
        assert torch.equal(whole, parts) and abs(r1 - r2) < 1e-5, f"sliced != one piece ({dt})"
        assert torch.equal(whole, q4_fake(big, 64, 4)), f"in-place != q4_fake ({dt})"
    nn = torch.nn

    class Experts(nn.Module):
        def __init__(self):
            super().__init__()
            self.gate_up_proj = nn.Parameter(torch.zeros(4, 32, 128))  # [E, 2I, H]
            self.down_proj = nn.Parameter(torch.zeros(4, 128, 64))  # [E, H, I]

    class Router(nn.Module):
        def __init__(self):
            super().__init__()
            self.weight = nn.Parameter(torch.zeros(4, 128))

    class Mlp(nn.Module):
        def __init__(self):
            super().__init__()
            self.gate, self.experts = Router(), Experts()
            self.shared_expert = nn.Linear(128, 64, bias=False)
            self.shared_expert_gate = nn.Linear(128, 1, bias=False)

    class Layer(nn.Module):
        def __init__(self):
            super().__init__()
            self.mlp, self.conv1d = Mlp(), nn.Conv1d(4, 4, 4)

    def net_of():  # the same values every call (own generator)
        net = nn.ModuleDict({"layers": nn.ModuleList([Layer(), Layer()])})
        gg = torch.Generator().manual_seed(1)
        for p in net.parameters():
            p.data.copy_(torch.randn(p.shape, generator=gg))
        return net

    ref = {n: p.detach().clone() for n, p in net_of().named_parameters()}
    plain = net_of()
    st0 = q4_apply(plain, 64, 4)
    assert (st0["tensors"], st0["skipped"]) == (4, 0), st0  # per layer: shared_expert + shared_expert_gate Linears only
    for n, p in plain.named_parameters():
        quantized = n.endswith(("shared_expert.weight", "shared_expert_gate.weight"))
        assert torch.equal(p, ref[n]) != quantized, f"{n}: default call must {'change' if quantized else 'leave alone'} it"
    net = net_of()
    st = q4_apply(net, 64, 4, Q4_MLX_MOE_BITS, Q4_MLX_MOE_PARAMS)
    assert st["tensors"] == 2 * 5 and st["skipped"] == 0, st  # per layer: experts x2, router, shared_expert, shared_expert_gate
    assert st["by_bits"] == {"4": {"tensors": 6, "params": 2 * (4 * 32 * 128 + 4 * 128 * 64 + 128 * 64)}, "8": {"tensors": 4, "params": 2 * (4 * 128 + 128)}}, st["by_bits"]
    assert st["pattern_hits"] == {"bits:" + Q4_MLX_MOE_BITS[0][0]: 2, "bits:" + Q4_MLX_MOE_BITS[1][0]: 2, "extra:" + Q4_MLX_MOE_PARAMS[0]: 4, "extra:" + Q4_MLX_MOE_PARAMS[1]: 2}, st["pattern_hits"]
    for n, p in net.named_parameters():
        if "conv1d" in n:
            assert torch.equal(p, ref[n]), f"{n} must not be touched"
            continue
        bits = 8 if n.endswith(("mlp.gate.weight", "mlp.shared_expert_gate.weight")) else 4
        gr, gq = ref[n].reshape(-1, 64), p.detach().reshape(-1, 64)
        scale = (gr.amax(-1, keepdim=True) - gr.amin(-1, keepdim=True)) / (2 ** bits - 1)
        assert bool(((gq - gr).abs() <= scale / 2 * (1 + 1e-5) + 1e-6).all()) and not torch.equal(p, ref[n]), f"{n}: not on the {bits}-bit grid"
        if bits == 4:
            assert max(len(set(r.tolist())) for r in gq) <= 16, f"{n}: more than 16 levels"
    e8 = (net["layers"][0].mlp.gate.weight.detach() - ref["layers.0.mlp.gate.weight"]).norm() / ref["layers.0.mlp.gate.weight"].norm()
    e4 = (q4_fake(ref["layers.0.mlp.gate.weight"], 64, 4) - ref["layers.0.mlp.gate.weight"]).norm() / ref["layers.0.mlp.gate.weight"].norm()
    assert e8 < e4 / 8, (e8, e4)
    out.update(by_bits=st["by_bits"], router_rel_err_8bit=float(e8), router_rel_err_4bit=float(e4))
    return out


@torch.no_grad()
def selftest_q4_eval():
    """Addendum 13 (--q4-eval) on tiny CPU models (own generator; the global RNG and the delta switch are restored): (i) q4_fake / q4_inplace / q4_apply are bit-identical to a verbatim copy of the pre-addendum-13 code (fp32 and bf16,
    2-D / 3-D, sliced, non-divisible, 3 / 4 / 8 bits, a tied Linear / Embedding net, same stats); (ii) with every delta_w zero, Q and Qf weights == Q0 weights bit for bit; (iii) with a delta of +-3 group steps on one tensor, that tensor differs
    from Q0 in Q and Qf (the rest does not), Qf == clamp(round((W + d - bias) / scale), 0, 15) on the grid of W and Q on the grid of W + d (independent code), the fp32-sum quantizer differs from quantizing a bf16-rounded sum, the stats agree
    (mean |d| / scale = 3 on that tensor); (iv) q4_eval with a stub scorer: delta off and the weights in the right condition inside every call, afterwards every Linear / Embedding weight and every delta_w bit-identical, the switch as before
    (on and off), the result keys; q4_sig sees a one-bit change. Run on the smoke Qwen3.5 in fp32 and bf16."""
    from argparse import Namespace
    from peft import LoraConfig, get_peft_model
    g, out, rng_state, sw = torch.Generator().manual_seed(0), {}, torch.get_rng_state(), _DELTA["on"]

    def ref_fake(w, group=64, bits=4, store_dtype=None):  # q4_fake as it was before addendum 13
        if w.dim() < 1 or w.shape[-1] % group:
            return None
        levels = 2 ** bits - 1
        x = w.detach().float().reshape(-1, w.shape[-1] // group, group)
        mx, mn = x.amax(-1, keepdim=True), x.amin(-1, keepdim=True)
        scale = (mx - mn) / levels
        scale = torch.where(scale == 0, torch.full_like(scale, 1e-8), scale)
        sd = store_dtype or w.dtype
        scale, bias = scale.to(sd).float(), mn.to(sd).float()
        scale = torch.where(scale == 0, torch.full_like(scale, 1e-8), scale)
        q = torch.clamp(torch.round((x - bias) / scale), 0, levels)
        return (q * scale + bias).reshape(w.shape).to(w.dtype)

    def ref_inplace(w, group, bits, chunk=Q4_CHUNK):  # q4_inplace as it was before addendum 13
        if w.dim() < 1 or w.shape[-1] % group:
            return None
        if w.numel() <= chunk or w.dim() < 2 or w.shape[0] < 2:
            wq = ref_fake(w, group, bits)
            den = w.float().norm().item()
            err = (wq.float() - w.float()).norm().item() / den if den > 0 else 0.0
            w.copy_(wq)
            return err
        rows = max(1, chunk // (w.numel() // w.shape[0]))
        e2 = d2 = 0.0
        for i in range(0, w.shape[0], rows):
            piece = w[i:i + rows]
            wq = ref_fake(piece, group, bits)
            e2 += (wq.float() - piece.float()).double().pow(2).sum().item()
            d2 += piece.float().double().pow(2).sum().item()
            piece.copy_(wq)
            del wq
        return math.sqrt(e2 / d2) if d2 > 0 else 0.0

    def ref_grid(W, sd):  # per group of 64 along the last dim, written out on its own: (scale, bias) of a float32 tensor, stored in sd
        x = W.float().reshape(*W.shape[:-1], -1, 64)
        mn, mx = x.min(-1, keepdim=True).values, x.max(-1, keepdim=True).values
        return ((mx - mn) / 15).to(sd).float(), mn.to(sd).float()

    def ref_deq(x, sc, bi, dt):  # dequantized weight of the float32 tensor x on the grid (sc, bi): codes clamp(round((x - bias) / scale), 0, 15)
        xg = x.float().reshape(sc.shape[:-1] + (64,))
        return (((xg - bi) / sc).round().clamp(0, 15) * sc + bi).reshape(x.shape).to(dt)

    try:
        n_cmp = 0
        for dt in (torch.float32, torch.bfloat16):  # (i)
            for shape in [(8, 128), (5, 4, 128), (4, 100), (3, 64), (1, 128), (64,)]:
                for bits in (3, 4, 8):
                    w = torch.randn(shape, generator=g).to(dt)
                    assert (q4_fake(w, 64, bits) is None) == (ref_fake(w, 64, bits) is None)
                    if w.shape[-1] % 64 == 0:
                        assert torch.equal(q4_fake(w, 64, bits), ref_fake(w, 64, bits)) and torch.equal(q4_fake(w, 64, bits, torch.bfloat16), ref_fake(w, 64, bits, torch.bfloat16))
                    for chunk in (Q4_CHUNK, 2 * 4 * 128):
                        a, b = w.clone(), w.clone()
                        ra, rb = q4_inplace(a, 64, bits, chunk), ref_inplace(b, 64, bits, chunk)
                        assert torch.equal(a, b) and ra == rb, (dt, shape, bits, chunk)
                        n_cmp += 1
        def net_of():  # Linear, Linear, Embedding tied to a Linear, non-divisible Linear
            emb, lin = torch.nn.Embedding(10, 128), torch.nn.Linear(128, 10, bias=False)
            lin.weight = emb.weight
            return torch.nn.ModuleList([torch.nn.Linear(256, 64), torch.nn.Linear(64, 128, bias=False), emb, lin, torch.nn.Linear(100, 4)])
        nets = [net_of(), net_of()]
        for p0, p1 in zip(nets[0].parameters(), nets[1].parameters()):
            p0.data.normal_(0, 1, generator=g)
            p1.data.copy_(p0.data)
        st, errs = q4_apply(nets[0], 64, 4), []
        for w in {id(m.weight): m.weight for m in nets[1]}.values():  # the reference: each distinct tensor once, in module order
            e = ref_inplace(w.data, 64, 4)
            if e is not None:
                errs.append(e)
        assert all(torch.equal(a, b) for a, b in zip(nets[0].parameters(), nets[1].parameters())) and st["mean_rel_fro"] == sum(errs) / len(errs), st
        assert (st["tensors"], st["skipped"]) == (3, 1) and set(st) == {"tensors", "skipped", "params", "mean_rel_fro", "group", "bits"}, st
        out["bit_identical_cases"] = n_cmp
        wb = torch.randn(64, 256, generator=g).to(torch.bfloat16)  # (iii-a) the fp32 sum is quantized on its own grid, not a bf16-rounded sum
        sc, bi = ref_grid(wb, torch.bfloat16)
        x32 = wb.float() + 0.5 * sc.expand(-1, -1, 64).reshape(wb.shape) * torch.randn(wb.shape, generator=g)
        fp32_route, bf16_route = q4_fake(x32, 64, 4, torch.bfloat16).to(torch.bfloat16), q4_fake(x32.to(torch.bfloat16), 64, 4)
        sc2, bi2 = ref_grid(x32, torch.bfloat16)
        assert torch.equal(fp32_route, ref_deq(x32, sc2, bi2, torch.bfloat16)) and not torch.equal(fp32_route, bf16_route)
        out["fp32_vs_bf16_sum_differing_weights"] = int((fp32_route != bf16_route).sum())
        w1 = torch.randn(1000, generator=g)  # q4_sig sees a one-bit change
        s1 = q4_sig([w1])
        w1.view(torch.int32)[500] ^= 1
        assert q4_sig([w1]) != s1 and q4_sig([w1]) == q4_sig([w1.clone()])

        def tiny(dt):
            lm, _ = load_model(Namespace(smoke=True, seed=0), torch.device("cpu"), dt)
            pm = get_peft_model(lm, LoraConfig(r=4, lora_alpha=8, lora_dropout=0.0, target_modules=LORA_TARGETS, bias="none"))
            setup_delta(pm, True)
            return lm, pm

        def state(lm):
            return {n: w.data.clone() for n, w in q4_tensors(lm).items()}, [bl.delta_w.data.clone() for _, bl in q4_delta_mods(lm)]

        def under(lm, cond):  # the weights (copies) under cond, then put back
            orig = state(lm)[0]
            q4_condition(lm, cond, 64, 4)
            got = state(lm)[0]
            for n, w in q4_tensors(lm).items():
                w.data.copy_(orig[n])
            return got

        def same(a, b, skip=()):
            return all(torch.equal(a[n], b[n]) for n in a if n not in skip)

        for dt in (torch.float32, torch.bfloat16):
            tag = str(dt).replace("torch.", "")
            lm, pm = tiny(dt)
            dm = q4_delta_mods(lm)
            lora_n = {n for n in q4_tensors(lm) if ".lora_" in n}
            assert len(dm) > 8 and lora_n and all(float(p.abs().max()) == 0 for n, p in lm.named_parameters() if "lora_B" in n)
            orig, dorig = state(lm)
            q0 = under(lm, "Q0")  # (ii)
            assert all(torch.equal(q0[n], orig[n]) for n in lora_n) and any(not torch.equal(q0[n], orig[n]) for n in orig if n not in lora_n)
            assert same(under(lm, "Q"), q0) and same(under(lm, "Qf"), q0), f"zero delta: Q / Qf != Q0 ({tag})"
            assert same(under(lm, "F0"), orig)
            z = q4_delta_stats(lm, 64, 4)
            assert z["overall"]["share_changed_Q"] == 0 and z["overall"]["share_changed_Qf"] == 0 and z["overall"]["mean_abs_delta_over_scale"] == 0, z["overall"]
            n0, bl0 = dm[0]  # (iii): +-3 group steps on one tensor, tiny noise-free
            W = bl0.weight.data
            sc, bi = ref_grid(W, W.dtype)
            sign = torch.where(torch.rand(sc.shape[:-1] + (64,), generator=g) < 0.5, -1.0, 1.0)
            d = (3 * sc * sign).reshape(W.shape)
            bl0.delta_w.data.copy_(d)
            exp_f = ref_deq(W.float() + d, sc, bi, W.dtype)  # Qf: the grid of W
            sc2, bi2 = ref_grid(W.float() + d, W.dtype)
            exp_q = ref_deq(W.float() + d, sc2, bi2, W.dtype)  # Q: the grid of W + d
            qq, qf = under(lm, "Q"), under(lm, "Qf")
            assert torch.equal(qf[n0], exp_f) and torch.equal(qq[n0], exp_q), f"Q / Qf weights != the independent grids ({tag})"
            codes = ((qf[n0].float().reshape(sc.shape[:-1] + (64,)) - bi) / sc).round()
            assert torch.equal(codes, ((W.float() + d).reshape(codes.shape) - bi).div(sc).round().clamp(0, 15)), "Qf codes"
            assert not torch.equal(qq[n0], q0[n0]) and not torch.equal(qf[n0], q0[n0]) and same(qq, q0, {n0}) and same(qf, q0, {n0}), f"Q / Qf must differ from Q0 on the delta tensor only ({tag})"
            ss = q4_delta_stats(lm, 64, 4)
            t0 = ss["by_type"][q4_type(n0)]
            assert ss["overall"]["share_changed_Qf"] > 0 and ss["overall"]["share_changed_Q"] > 0 and ss["codes_all"] > ss["overall"]["codes"]
            assert abs(t0["mean_abs_delta_over_scale"] * t0["codes"] - 3 * W.numel()) < 1e-3 * W.numel(), t0
            assert all(v["share_changed_Q"] == 0 and v["share_changed_Qf"] == 0 for t, v in ss["by_type"].items() if t != q4_type(n0))
            out[f"stats_{tag}"] = {"overall": ss["overall"], q4_type(n0): t0}
            for _, bl in dm:  # (iv): every module a random delta
                bl.delta_w.data.normal_(0, 0.02, generator=g)
            orig, dorig = state(lm)
            for prev in (True, False):
                _DELTA["on"] = prev
                seen = {}

                def stub(cond):
                    assert not _DELTA["on"], "delta switch must be off while scoring"
                    seen[cond] = state(lm)[0]
                    return {"scores": {"forward": {"C24": 0.5}, "twohop": {"acc": 0.25}}, "arc_easy": {"acc": 0.75}}
                saves, lines = [], []
                res = q4_eval(lm, 64, 4, stub, log=lines.append, save=lambda: saves.append(1))
                after, dafter = state(lm)
                assert _DELTA["on"] == prev and same(after, orig) and all(torch.equal(a, b) for a, b in zip(dafter, dorig)), f"q4_eval did not restore the model ({tag}, switch {prev})"
                assert set(res) == {"group", "bits", "lora_B_nonzero", "lora_B_max_abs", "stats", *Q4_CONDS} and res["lora_B_nonzero"] is False and res["lora_B_max_abs"] == 0.0 and list(seen) == list(Q4_CONDS)
                assert all(set(res[c]) == {"scores", "arc_easy", "q4_apply", "wall_seconds"} for c in Q4_CONDS) and res["F0"]["q4_apply"] is None and len(lines) == 5 and len(saves) == 5
                assert same(seen["F0"], orig) and all(torch.equal(seen["Q0"][n], ref_fake(orig[n]) if n not in lora_n else orig[n]) for n in orig if orig[n].shape[-1] % 64 == 0)
                assert not same(seen["Q"], seen["Q0"]) and not same(seen["Qf"], seen["Q0"]) and not same(seen["Q"], seen["Qf"]) and same(seen["Q"], seen["Q0"], {n for n, _ in dm}) and same(seen["Qf"], seen["Q0"], {n for n, _ in dm})
            lm.get_parameter(next(n for n, p in lm.named_parameters() if "lora_B" in n)).data.fill_(0.5)  # a nonzero B is reported
            assert q4_eval(lm, 64, 4, lambda c: {}, log=lambda m: None)["lora_B_nonzero"] is True
            out[f"q4_eval_lines_{tag}"] = lines
        return out
    finally:
        torch.set_rng_state(rng_state)
        _DELTA["on"] = sw


def selftest_names_k2():
    """Addenda 11b / 11c (the K2 names pass thinks, now at high effort with 512 tokens, and reads negative replies as no) on stubs: a fake tokenizer behind the real Lang, a stub gen, no model. (i) Lang.render_think asks the template for reasoning_effort="low" and returns its text
    unchanged (block open), medium / high end with their own tags, a template whose tail changed raises, non-K2 raises; Lang.render still sends no reasoning_effort; think_eos is [close-tag id, im_end id]; Lang.generate
    passes eos_token_id = im_end by default and a given list as is; (ii) names_prompt(think=True) is render_think's text (at the given effort, K2_NAMES_EFFORT = "high" for the names pass), think=False render's; (iii) strip_think:
    close tag / im_end / both / doubled / none, and whether the model closed the block, for the low close tag (default) and the high one (effort="high"), never the other effort's tag; (iv) Brain.names_pass with Lang(k2=True): stage 1
    is the think-open prompts at high effort (512 tokens, stops [id of </ifm|think>, im_end]), stage 2 is stage-1 prompt + thinking + ONE </ifm|think> (added when the reply was not closed, not doubled when it was) answered in
    12 tokens with no extra gen arguments, yes / items come from the stage-2 answers, think_tokens_mean / think_capped are counted, raw["names"] keeps the answers and adds the first 3 thinking texts cut at 400 chars, the record
    has Qwen's keys plus those two; (v) the same on Lang(k2=False): one gen call, Qwen's prompts, Qwen's record keys; (vi) addendum 11c's negative-reply rule: parse_rel_k2 reads a first line starting with the word no / not / none /
    nothing / nope / unrelated as no (not now / north / nobody's ...), Qwen's parse_rel is exactly as before, and names_pass counts a "No relation" / "Not related" reply as a yes on Qwen and not on K2."""
    from types import SimpleNamespace
    cpu, out = torch.device("cpu"), {}
    CLOSE, HCLOSE, END = "</ifm|think_faster>", "</ifm|think>", "<|ifm|im_end|>"  # the low-effort close tag (11b), the high-effort one (11c, what the names pass uses), end of turn

    class FakeTok:  # a tokenizer in the shape Lang needs; one token per whitespace word
        pad_token_id, unk_token_id, eos_token_id = 7, 0, 1

        def __init__(self, tail="<ifm|think_faster>\n"):
            self.tail, self.calls = tail, []

        def convert_tokens_to_ids(self, t):
            return {END: 19, CLOSE: 53, HCLOSE: 54}.get(t, 0)

        def apply_chat_template(self, msgs, **kw):
            self.calls.append(kw)
            tail = {"low": self.tail, "medium": "<ifm|think_fast>\n", "high": "<ifm|think>\n", None: "<ifm|think>\n"}[kw.get("reasoning_effort")]
            return "".join(f"[{m['role']}]{m['content']}" for m in msgs) + "[assistant]" + tail

        def __call__(self, text, add_special_tokens=False):
            return {"input_ids": list(range(len(text.split())))}

        def decode(self, ids, skip_special_tokens=True):
            return "x"

    tk = FakeTok()
    Lk = Lang(tk, False, cpu, k2=True)
    assert Lk.eos == 19 and Lk.think_eos() == [53, 19] and Lk.think_eos("low") == [53, 19] and Lk.think_eos("high") == [54, 19]
    t = Lk.render_think("S", "U")
    assert t == "[system]S[user]U[assistant]<ifm|think_faster>\n" and tk.calls[-1] == {"tokenize": False, "add_generation_prompt": True, "reasoning_effort": "low"}, (t, tk.calls[-1])
    assert Lk.render_think(None, "U") == "[user]U[assistant]<ifm|think_faster>\n"
    assert Lk.render("S", "U") == "[system]S[user]U[assistant]<ifm|think>\n</ifm|think>" and tk.calls[-1] == {"tokenize": False, "add_generation_prompt": True}, tk.calls[-1]  # render: unchanged, no reasoning_effort
    assert Lk.render_think("S", "U", "medium").endswith("<ifm|think_fast>\n") and Lk.render_think("S", "U", "high").endswith("<ifm|think>\n")
    for bad in (Lang(FakeTok(tail="<ifm|think>\n"), False, cpu, k2=True), Lang(tk, False, cpu)):  # template tail changed / not a K2 Lang
        try:
            bad.render_think("S", "U")
        except AssertionError:
            pass
        else:
            raise AssertionError("render_think should have raised")
    try:
        Lang(tk, False, cpu).think_eos()
    except AssertionError:
        pass
    else:
        raise AssertionError("think_eos should have raised on a non-K2 Lang")

    class FakeModel:
        def __init__(self):
            self.kw = []

        def generate(self, input_ids, attention_mask, max_new_tokens, **kw):
            self.kw.append(dict(kw, max_new=max_new_tokens))
            return torch.cat([input_ids, torch.full((input_ids.shape[0], 2), 7)], 1)
    fm = FakeModel()
    assert Lk.generate(fm, ["a b", "c"], max_new=3) == ["x", "x"] and Lk.generate(fm, ["a b"], max_new=4, eos=[53, 19]) == ["x"] and Lk.generate(fm, ["a"], max_new=5, eos=53) == ["x"]
    assert fm.kw == [{"pad_token_id": 7, "eos_token_id": 19, "do_sample": False, "max_new": 3}, {"pad_token_id": 7, "eos_token_id": [53, 19], "do_sample": False, "max_new": 4},
                     {"pad_token_id": 7, "eos_token_id": 53, "do_sample": False, "max_new": 5}], fm.kw
    out["lang"] = "ok"

    # (ii) / (iii)
    Ls = SimpleNamespace(render=lambda sy, u: "R:" + u, render_think=lambda sy, u: "T:" + u)
    assert names_prompt(Ls, "m", "A", "B").startswith("R:Message") and names_prompt(Ls, "m", "A", "B", think=True) == "T:" + names_prompt(Ls, "m", "A", "B")[2:]
    Le = SimpleNamespace(render=lambda sy, u: "R:" + u, render_think=lambda sy, u, e="low": f"T[{e}]:" + u)  # a render_think that takes an effort (as Lang's does)
    assert names_prompt(Le, "m", "A", "B", think=True).startswith("T[low]:Message") and names_prompt(Le, "m", "A", "B", think=True, effort="high").startswith("T[high]:Message")
    assert names_prompt(Le, "m", "A", "B", effort="high") == names_prompt(Le, "m", "A", "B") and names_prompt(Le, "m", "A", "B", think=True, effort="medium").startswith("T[medium]:")
    assert names_prompt(Lk, "m", "A", "B", think=True, effort="high").endswith("[assistant]<ifm|think>\n") and HCLOSE not in names_prompt(Lk, "m", "A", "B", think=True, effort="high")
    assert names_prompt(Lk, "m", "A", "B", think=True).endswith("[assistant]<ifm|think_faster>\n") and tk.calls[-1]["reasoning_effort"] == "low"  # no effort given: render_think's default, as in 11b
    assert names_prompt(Lk, "m", "A", "B", think=True, effort=K2_NAMES_EFFORT).endswith("<ifm|think>\n") and K2_NAMES_EFFORT == "high" and tk.calls[-1]["reasoning_effort"] == "high"
    assert strip_think("a b" + CLOSE) == ("a b", True) and strip_think(" a b \n" + CLOSE + END) == ("a b", True) and strip_think("a b" + END) == ("a b", False) and strip_think("a b") == ("a b", False)
    assert strip_think("a b" + CLOSE + CLOSE) == ("a b", True) and strip_think(CLOSE) == ("", True) and strip_think("") == ("", False) and strip_think(None) == ("", False) and strip_think("x " + CLOSE + " y") == ("x " + CLOSE + " y", False)
    assert strip_think("a b" + CLOSE, "low") == strip_think("a b" + CLOSE) == ("a b", True)  # (11c) the default effort is 11b's low
    H = lambda x: strip_think(x, "high")  # noqa: E731
    assert H("a b" + HCLOSE) == ("a b", True) and H(" a b \n" + HCLOSE + END) == ("a b", True) and H("a b" + END) == ("a b", False) and H("a b") == ("a b", False)
    assert H("a b" + HCLOSE + HCLOSE) == ("a b", True) and H(HCLOSE) == ("", True) and H("") == ("", False) and H(None) == ("", False) and H("x " + HCLOSE + " y") == ("x " + HCLOSE + " y", False)
    assert H("a b" + CLOSE) == ("a b" + CLOSE, False) and strip_think("a b" + HCLOSE) == ("a b" + HCLOSE, False)  # each effort strips only its own close tag

    # (iv) Brain.names_pass on the K2 path
    rows = [(2, "hey Magomen met Papirar and Torvald today"), (2, "later Aldo told Berit nothing")]
    dia = Diary({"diary": [{"role": "user", "day": d_, "text": x} for d_, x in rows]})
    think1 = {("Magomen", "Papirar"): "They are siblings." + HCLOSE,  # closed by the model
              ("Magomen", "Torvald"): "z" * 500,  # no close tag (cap hit): 1 token, long
              ("Papirar", "Torvald"): "ok then, it works" + END,  # the turn ended without closing the block
              ("Aldo", "Berit"): "a b c d" + HCLOSE + HCLOSE}  # doubled close tag: cleaned
    reply = {("Magomen", "Papirar"): "is the brother of", ("Magomen", "Torvald"): "No.", ("Papirar", "Torvald"): "works at", ("Aldo", "Berit"): "no"}
    calls = []

    def gen(prompts, n, **kw):
        calls.append((list(prompts), n, kw))
        pairs = [re.search(r'how "(.+?)" and "(.+?)" are related', pr).groups() for pr in prompts]
        return [think1[p] if len(calls) == 1 else reply[p] for p in pairs]

    def mk(L):
        calls.clear()
        return SimpleNamespace(L=L, diary=dia, items={}, dropped=set(), tag_log=[(0, 2, []), (1, 2, [])], raw={}, gen=gen, mn=lambda n: n)
    me = mk(Lk)
    rec = Brain.names_pass(me, 2)
    want = [("Magomen", "Papirar"), ("Magomen", "Torvald"), ("Papirar", "Torvald"), ("Aldo", "Berit")]
    texts = [rows[0][1]] * 3 + [rows[1][1]]
    assert len(calls) == 2, len(calls)
    (p1, n1, kw1), (p2, n2, kw2) = calls
    assert n1 == NAMES_THINK_MAX == 512 and kw1 == {"eos": [54, 19]} and n2 == 12 and kw2 == {}, (n1, kw1, n2, kw2)  # 11c: high effort, 512 tokens, stops at </ifm|think> (id 54) or the end of the turn
    assert p1 == [names_prompt(Lk, x, a, b, think=True, effort="high") for x, (a, b) in zip(texts, want)] and all(p.endswith("[assistant]<ifm|think>\n") and HCLOSE not in p and CLOSE not in p for p in p1)
    th = ["They are siblings.", "z" * 500, "ok then, it works", "a b c d"]
    assert p2 == [p + x + HCLOSE for p, x in zip(p1, th)] and all(p.endswith(HCLOSE) and p.count(HCLOSE) == 1 and CLOSE not in p and END not in p for p in p2), [p[-60:] for p in p2]
    assert rec == {"candidates": 5, "turns": 2, "turns_ge2": 2, "pairs": 4, "yes": 2, "new_items": 2, "appended": 2, "dropped_invalid": 0, "dropped_not_in_turn": 0, "think_tokens_mean": 3.0, "think_capped": 2}, rec
    assert [(v.subj, v.rel, v.obj) for v in me.items.values()] == [("Magomen", "is the brother of", "Papirar"), ("Papirar", "works at", "Torvald")]
    assert [e[2] for e in me.tag_log] == [[("Magomen", "Papirar"), ("Papirar", "Torvald")], []]
    assert me.raw["names"] == [{"text": rows[0][1], "pair": ["Magomen", "Papirar"], "out": "is the brother of", "think": "They are siblings."},
                               {"text": rows[0][1], "pair": ["Magomen", "Torvald"], "out": "No.", "think": "z" * 400},
                               {"text": rows[0][1], "pair": ["Papirar", "Torvald"], "out": "works at", "think": "ok then, it works"}], me.raw["names"]
    out["k2_record"] = rec

    # (v) Qwen-style Lang (k2 False): one gen call, the old prompts, the old record
    Lq = Lang(FakeTok(), True, cpu)
    me = mk(Lq)
    calls_q = []
    gen_q = lambda prompts, n, **kw: calls_q.append((list(prompts), n, kw)) or [reply[re.search(r'how "(.+?)" and "(.+?)" are related', pr).groups()] for pr in prompts]  # noqa: E731
    me.gen = gen_q
    recq = Brain.names_pass(me, 2)
    assert len(calls_q) == 1 and calls_q[0][1] == 12 and calls_q[0][2] == {} and calls_q[0][0] == [names_prompt(Lq, x, a, b) for x, (a, b) in zip(texts, want)]
    assert recq == {k: v for k, v in rec.items() if not k.startswith("think_")} and all("think" not in r for r in me.raw["names"]), recq
    out["qwen_record"] = recq

    # (vi) addendum 11c: the negative-reply rule is K2 only
    none_k2 = ["No relation", "no relation.", "NO RELATION", "not related", "Not related to each other", "Unrelated.", "unrelated", "nothing", "Nothing is said.", "none", "None of them", "nope", "Nope!", "no", "No.", "no,",
               "", "  \n  ", "\n\nNo relation\nthey are siblings", "no - they are unrelated", "NOT"]
    for x in none_k2:
        assert parse_rel_k2(x) is None, x
    kept_k2 = {"now lives in X": "now lives in X", "north of": "north of", "nobody's boat": "nobody's boat", "Nobody's boat": "Nobody's boat", "notes on": "notes on", "notably the mentor of": "notably the mentor of",
               "nothingness": "nothingness", "nonetheless works at": "nonetheless works at", "nopes": "nopes", "unrelatedly close": "unrelatedly close", "knows": "knows",
               "is the brother of": "is the brother of", "works at": "works at", "Yes": "", "yes, lives in": "lives in", "Yes - owns the boat.": "owns the boat", "\"works at\"": "works at",
               "works at\nno": "works at", "lives in\nnot related": "lives in", "Magomen is not related to Papirar": "Magomen is not related to Papirar", "x" * 50: "x" * 40}
    for x, want_rel in kept_k2.items():
        assert parse_rel_k2(x) == want_rel == parse_rel(x), (x, parse_rel_k2(x), parse_rel(x))
    assert NEG_RE.pattern == r"(?:no|not|none|nothing|nope|unrelated)\b" and NEG_RE.flags & re.I
    # Qwen's parse_rel is exactly as before: only a bare no / none / nope (+ punctuation) is "no"; "No relation" is a (40-char) relation
    for x in ("no", "No", "NO.", "none", "None.", "nope", "Nope!", "no,", "", "  ", None):
        assert parse_rel(x) is None, x
    for x, want_rel in (("No relation", "No relation"), ("no relation.", "no relation"), ("not related", "not related"), ("Not related to each other", "Not related to each other"), ("Unrelated.", "Unrelated"),
                        ("nothing", "nothing"), ("Nothing is said.", "Nothing is said"), ("no - they are unrelated", "no - they are unrelated"), ("None of them", "None of them"), ("now lives in X", "now lives in X"), ("Yes", ""), ("yes, lives in", "lives in"),
                        ("No relation is stated between these two names at all", "No relation is stated between these two names"[:40].strip()), ("\nno relation\nx", "no relation")):
        assert parse_rel(x) == want_rel, (x, parse_rel(x))
    reply_neg = {**reply, ("Magomen", "Torvald"): "No relation", ("Aldo", "Berit"): "Not related to each other"}  # K2 reads both as no; Qwen reads both as a relation
    gen_neg = lambda prompts, n, **kw: [(think1 if kw.get("eos") else reply_neg)[re.search(r'how "(.+?)" and "(.+?)" are related', pr).groups()] for pr in prompts]  # noqa: E731  (stage 1 passes eos)
    me = mk(Lk)
    me.gen = gen_neg
    rec_neg = Brain.names_pass(me, 2)
    assert rec_neg["pairs"] == 4 and rec_neg["yes"] == 2 and rec_neg["new_items"] == 2 and [(v.subj, v.rel, v.obj) for v in me.items.values()] == [("Magomen", "is the brother of", "Papirar"), ("Papirar", "works at", "Torvald")], rec_neg
    me = mk(Lq)
    me.gen = gen_neg
    recq_neg = Brain.names_pass(me, 2)
    assert recq_neg["yes"] == 4 and recq_neg["new_items"] == 4 and [(v.subj, v.rel, v.obj) for v in me.items.values()] == [
        ("Magomen", "is the brother of", "Papirar"), ("Magomen", "No relation", "Torvald"), ("Papirar", "works at", "Torvald"), ("Aldo", "Not related to each other", "Berit")], recq_neg
    out["neg_rule"] = {"k2_yes": rec_neg["yes"], "qwen_yes": recq_neg["yes"], "none_k2": len(none_k2), "kept_k2": len(kept_k2)}
    return out


def selftest_rem_k2():
    """Addendum 14 on stubs (a fake tokenizer behind the real Lang, a scripted gen, no model, a local Random): (i) default flags: ab_ob_b4_nb's chain prompts are the old bridge_prompt text byte for byte, ONE gen call for chains + gists
    (40 tokens, base False, sample True), and stats / pool / rng state / raw capture are the same with and without the new flags in the args; (ii) mode q: bridge_q_prompt = bridge_prompt's text up to "(a single name)." + the new reply line, the
    chains in one call and the gists in their own, the answer is the given far end (parse_q1), a reply with no question is a parse failure and one that does not name the start is dropped_bad; (iii) think and q_think: stage 1 = the open-tag
    prompts at high effort (512 tokens, stops at [</ifm|think>, im_end]), stage 2 = stage-1 prompt + thinking + ONE close tag (40 tokens), the gists in their own single call, raw["rem"] = [first chain reply, first gist reply],
    chain_think_tokens / chain_think_capped; a Qwen Lang and a non-bridge arm are refused; (iv) --rem-dirs both: both roles of every pair, units with a kept dream are not tried again, the per-cycle cap, --rem-tries keeps the first
    passing sample per unit (unit_extra_dropped), rem_dir_done; (v) rem_plan: at 1.0 the old per-cycle counts and the Trainer total (= steps), at 2.0 the REM counts double and the total includes them; (vi) parse_q1 edge cases."""
    from types import SimpleNamespace
    cpu, out = torch.device("cpu"), {}
    HC, END = "</ifm|think>", "<|ifm|im_end|>"  # the high-effort close tag, end of turn

    class FakeTok:  # a tokenizer in the shape Lang needs; one token per whitespace word
        pad_token_id, unk_token_id, eos_token_id = 7, 0, 1

        def convert_tokens_to_ids(self, t):
            return {END: 19, "</ifm|think_faster>": 53, HC: 54}.get(t, 0)

        def apply_chat_template(self, msgs, **kw):
            tail = {"low": "<ifm|think_faster>\n", "medium": "<ifm|think_fast>\n", "high": "<ifm|think>\n", None: "<ifm|think>\n"}[kw.get("reasoning_effort")]
            return "".join(f"[{m['role']}]{m['content']}" for m in msgs) + "[assistant]" + tail

        def __call__(self, text, add_special_tokens=False):
            return {"input_ids": list(range(len(text.split())))}
    L, Lq = Lang(FakeTok(), False, cpu, k2=True), Lang(FakeTok(), True, cpu)
    OPEN = "[assistant]<ifm|think>\n"
    Ls = SimpleNamespace(render=lambda sy, u: f"<sys>{sy}</sys>\n<user>{u}</user>")
    SYSB = "You are a careful assistant that studies facts."

    def old_bridge(L_, fx, fy, start, answer, mid):  # bridge_prompt as it was before addendum 14
        u = (f"Two facts:\n- {fx}\n- {fy}\n\nThe two facts share the name \"{mid}\". Write one question that names \"{start}\", does not name \"{mid}\" or \"{answer}\", "
             f"and can only be answered by using both facts together. Its answer must be \"{answer}\" (a single name). Reply in exactly this form:\nQuestion: ...\nAnswer: ...")
        return L_.render("You are a careful assistant that studies facts.", u)

    # the prompt builders: bridge_prompt unchanged with the defaults, bridge_q_prompt = its text to "(a single name)." + the new reply line, think = render_think (default effort low when none is given)
    for args_ in (("Zelmir lives in Kelmira.", "Kelmira is near Harbor Light.", "Zelmir", "Harbor Light", "Kelmira"), ('A "b" c.', "D\ne.", "Q'x", "Y y", "Z")):
        for L_ in (Ls, L):
            assert bridge_prompt(L_, *args_) == old_bridge(L_, *args_) == bridge_prompt(L_, *args_, think=False, effort=None) == bridge_prompt(L_, *args_, effort="high")
        bq = bridge_q_prompt(Ls, *args_)
        stem = old_bridge(Ls, *args_).split(" Reply in exactly this form:")[0]
        assert bq == stem + " Reply with only the question, on one line.</user>" and bq.startswith(f"<sys>{SYSB}</sys>\n<user>Two facts:\n- {args_[0]}\n- {args_[1]}\n\nThe two facts share the name"), bq
        assert bq.endswith(f"Its answer must be \"{args_[3]}\" (a single name). Reply with only the question, on one line.</user>")
        assert bridge_prompt(L, *args_, think=True, effort="high") == "[system]" + SYSB + "[user]" + old_bridge(Ls, *args_).split("<user>")[1].split("</user>")[0] + OPEN
        assert bridge_q_prompt(L, *args_, think=True, effort="high").endswith("Reply with only the question, on one line." + OPEN) and bridge_q_prompt(L, *args_).endswith("one line.[assistant]<ifm|think>\n</ifm|think>")
        assert bridge_prompt(L, *args_, think=True).endswith("[assistant]<ifm|think_faster>\n") == bridge_prompt(L, *args_, think=True, effort="low").endswith("[assistant]<ifm|think_faster>\n") and bridge_prompt(L, *args_, think=True, effort="medium").endswith("<ifm|think_fast>\n")
    out["prompts"] = "ok"

    mk = lambda a, r, o, dd: Item((norm(a), norm(o)), a, o, r, 1, days=dd)  # noqa: E731
    E = [mk("Zelmir", "lives in", "Kelmira", 3), mk("Kelmira", "is near", "Harbor Light", 0), mk("Harbor Light", "is in", "Oslo", 0), mk("Brontu", "sails to", "Kelmira", 3)]  # 4 pairs: 3 share Kelmira, 1 shares Harbor Light; 2 gist items
    by_fact = {it.fact: it for it in E}
    facts_of = lambda pr: [by_fact[f] for f in re.findall(r"^- (.+)$", pr, re.M)]  # noqa: E731
    role_of = lambda pr: (re.search(r'names "(.+?)", does not', pr).group(1), re.search(r'Its answer must be "(.+?)"', pr).group(1))  # noqa: E731  (start, answer)
    GISTS = sorted(gist_prompt(L, it.fact, it.days) for it in (E[0], E[3]))
    NAMES = ["Zelmir", "Kelmira", "Harbor Light", "Oslo", "Brontu"]
    U = {"A1": ("Zelmir", "Harbor Light"), "A2": ("Harbor Light", "Zelmir"), "B1": ("Zelmir", "Brontu"), "B2": ("Brontu", "Zelmir"),
         "C1": ("Harbor Light", "Brontu"), "C2": ("Brontu", "Harbor Light"), "D1": ("Kelmira", "Oslo"), "D2": ("Oslo", "Kelmira")}  # the 8 units (start, answer): a pair's two directions are 1 and 2
    PAIR = {"A": (E[0], E[1]), "B": (E[0], E[3]), "C": (E[1], E[3]), "D": (E[1], E[2])}
    key_of = lambda n: (frozenset((PAIR[n[0]][0].key, PAIR[n[0]][1].key)), norm(U[n][0]))  # noqa: E731  (a unit's rem_dir_done key: the pair's two item keys and norm(start))

    def mkme(mode="default", dirs="alt", tries=1, arm="ab_ob_b4_nb", cap=30, flags=True, kinds=("closed",), L_=L):  # a Brain stand-in for Brain.rem; me.script[(start, answer)] = tags of the tries (default good)
        me = SimpleNamespace(L=L_, a=SimpleNamespace(arm=arm, smoke=False, gist_min_days=3, **({"rem_chain_mode": mode, "rem_dirs": dirs, "rem_tries": tries} if flags else {})), mn=lambda n: n, raw={}, rng=random.Random(0),
                             rem_done=Counter(), gist_done=Counter(), rem_dir_done=Counter(), cap_chains=cap, cap_gist=30, diary=SimpleNamespace(containing=lambda su, ob, d: [0, 1], label=lambda idx: "ctx"), leaky=lambda t: False,
                             rem_pool=[], rem_chains=[], examples={"rem": []}, script={}, calls=[], outs=[], cycle=0, ans_of={}, unver=set())

        def gen(prompts, n, **kw):
            me.calls.append((list(prompts), n, kw))
            res, seen = [], Counter()
            for j, pr in enumerate(prompts):
                if kw.get("eos") is not None:  # stage 1: the thinking, closed by the model / ended by the turn / capped / close tag twice
                    res.append({"closed": "a b c" + HC, "end": "a b" + END, "cap": "a b c d", "twice": "a" + HC + HC}[kinds[j % len(kinds)]])
                elif "Messages from Sam" in pr:  # the diary check of a candidate
                    q = re.search(r"Question: (.+?)\[assistant\]", pr).group(1)
                    res.append("no idea" if q in me.unver else me.ans_of[q])
                elif "Fact about Sam's life" in pr:
                    it = by_fact[re.search(r"life: (.+?) \(it came", pr).group(1)]
                    q = f"Who does Sam usually see with {it.obj} (item {E.index(it)})?"
                    me.ans_of[q] = it.subj
                    res.append(f"Question: {q}\nAnswer: {it.subj}")
                else:  # a chain prompt (stage 2 carries the thinking after the open tag)
                    start, answer = role_of(pr)
                    t = seen[(start, answer)]
                    seen[(start, answer)] += 1
                    tag = me.script.get((start, answer), ["good"] * 9)[t]
                    q, qonly = f"Who is two steps from {start} (c{me.cycle}-t{t}-n{NAMES.index(answer)})?", "Reply with only the question" in pr  # (the answer's number keeps two units with the same start apart)
                    me.ans_of[q] = answer
                    if tag == "nov":
                        me.unver.add(q)
                    res.append({"good": q if qonly else f"Question: {q}\nAnswer: {answer}", "nov": q if qonly else f"Question: {q}\nAnswer: {answer}",
                                "bad": f"Who is that (c{me.cycle}-t{t}-n{NAMES.index(answer)})?" if qonly else f"Question: Who is {start}?\nAnswer: {start}", "junk": "I cannot say."}[tag])
            me.outs.append(res)
            return res
        me.gen = gen
        return me

    def cycle(me, ci=0):  # one Brain.rem call; (stats, the gen calls of this cycle, the replies of this cycle)
        me.calls.clear()
        me.outs.clear()
        me.cycle = ci
        st = Brain.rem(me, E, 1, ci)
        return st, list(me.calls), [list(o) for o in me.outs]

    # (i) default flags: the old prompts, one call, the same everything with and without the new flags in args
    me0, me1 = mkme(flags=False), mkme(flags=True)
    st0, calls0, outs0 = cycle(me0)
    st1, calls1, outs1 = cycle(me1)
    assert calls0 == calls1 and st0 == st1 and outs0 == outs1 and me0.rem_pool == me1.rem_pool and me0.raw == me1.raw and me0.rng.getstate() == me1.rng.getstate() and me0.rem_dir_done == Counter()
    sent, n_gen, kw = calls0[0]
    assert len(calls0) == 2 and n_gen == 40 and kw == {"base": False, "sample": True} and calls0[1][1] == 20 and len(sent) == 6, (len(calls0), n_gen, kw, len(sent))  # chains + gists in ONE call, then the diary check
    roles0 = []
    for k, pr in enumerate(sent[:4]):
        p, q = facts_of(pr)
        x = ({norm(p.subj), norm(p.obj)} & {norm(q.subj), norm(q.obj)}).pop()
        (mid, fp), fq = other(p, x), other(q, x)[1]
        start, answer = (fp, fq) if k % 2 == 0 else (fq, fp)  # the old alternation with the pair index
        assert pr == old_bridge(L, p.fact, q.fact, start, answer, mid) and role_of(pr) == (start, answer), k
        roles0.append((start, answer))
    assert sorted(sent[4:]) == GISTS and len({*sent[:4]}) == 4
    assert st0 == {"chain_gen": 4, "chain_kept": 4, "gist_gen": 2, "gist_kept": 2, "pool": 6} and me0.raw["rem"] == [outs0[0][0], outs0[0][4]] and all(v == 1 for v in me0.rem_done.values()) and len(me0.rem_dir_done) == 0
    out["default_same_as_old"] = st0
    pairs_k = [(facts_of(pr)[0], facts_of(pr)[1]) for pr in sent[:4]]

    # (ii) mode q
    me = mkme(mode="q")
    me.script = {roles0[0]: ["junk"], roles0[1]: ["bad"]}
    st, calls, outs = cycle(me)
    assert len(calls) == 3 and [c[1] for c in calls] == [40, 40, 20] and calls[0][2] == {"base": False, "sample": True} and calls[1][2] == {"base": False, "sample": True}, [(c[1], c[2]) for c in calls]  # chains, gists (own call), diary check
    sq = calls[0][0]
    assert sq == [bridge_q_prompt(L, p.fact, q.fact, s_, a_, re.search(r'share the name "(.+?)"', pr).group(1)) for (p, q), (s_, a_), pr in zip(pairs_k, roles0, sent[:4])]  # the same pairs and roles as bridge_roles gives
    assert all(pr.endswith("(a single name). Reply with only the question, on one line.[assistant]<ifm|think>\n</ifm|think>") and "Question: ..." not in pr for pr in sq)
    assert sorted(calls[1][0]) == GISTS and st == {"chain_gen": 4, "parse_fail": 1, "dropped_bad": 1, "chain_kept": 2, "gist_gen": 2, "gist_kept": 2, "pool": 4}, st
    kept = [x for x in me.rem_pool if x["kind"] == "chain"]
    assert sorted((x["q"].split(" (")[0].replace("Who is two steps from ", ""), x["a"]) for x in kept) == sorted(roles0[2:]), (kept, roles0)  # the answer is the given far end
    assert me.raw["rem"] == [outs[0][0], outs[1][0]] and len(me.rem_chains) == 2 and me.rem_dir_done == Counter()
    out["q"] = st

    # (iii) think / q_think
    kinds = ("closed", "end", "cap", "twice")  # sample j gets kinds[j % 4]: thinking "a b c" (closed by the model), "a b" (turn ended), "a b c d" (cap hit), "a" + two close tags
    ths = ["a b c", "a b", "a b c d", "a"]
    for mode in ("think", "q_think"):
        mkp = bridge_prompt if mode == "think" else bridge_q_prompt
        me = mkme(mode=mode, kinds=kinds)
        st, calls, outs = cycle(me)
        assert len(calls) == 4, len(calls)
        (p1, n1, kw1), (p2, n2, kw2), (pg, ng, kwg), (pv, nv, kwv) = calls
        want1 = [mkp(L, p.fact, q.fact, s_, a_, re.search(r'share the name "(.+?)"', pr).group(1), think=True, effort="high") for (p, q), (s_, a_), pr in zip(pairs_k, roles0, sent[:4])]
        assert p1 == want1 and all(p.endswith(OPEN) and HC not in p and END not in p for p in p1), [p[-50:] for p in p1]  # the open tag for high effort, nothing closed yet
        assert n1 == REM_THINK_MAX == 512 and kw1 == {"base": False, "sample": True, "eos": [54, 19]}, (n1, kw1)  # stops at </ifm|think> (id 54) or the end of the turn
        assert p2 == [p + x + HC for p, x in zip(p1, ths)] and all(q_.count(HC) == 1 and q_.endswith(HC) and END not in q_[len(p):] for q_, p in zip(p2, p1)), [q_[-40:] for q_ in p2]  # ONE close tag, also after a capped / ended / doubled stage 1
        assert n2 == 40 and kw2 == {"base": False, "sample": True} and ng == 40 and kwg == {"base": False, "sample": True} and sorted(pg) == GISTS and nv == 20, (n2, kw2, ng, kwg)  # the gists in their own single call
        assert st == {"chain_think_tokens": 10, "chain_think_capped": 2, "chain_gen": 4, "chain_kept": 4, "gist_gen": 2, "gist_kept": 2, "pool": 6}, st
        assert me.raw["rem"] == [outs[1][0], outs[2][0]] and (outs[1][0].startswith("Question: ") == (mode == "think")) and len(me.rem_chains) == 4
        out[mode] = st
    for bad_kw in (dict(mode="think", L_=Lq), dict(mode="q", arm="ab_ob_b4"), dict(dirs="both", arm="ab_ob_b4_nb_x4"), dict(mode="q_think", arm="ab_ob_b4_nb_x4")):  # a Qwen Lang has no think block; the other arms keep their own paths
        try:
            cycle(mkme(**bad_kw))
        except AssertionError:
            pass
        else:
            raise AssertionError(f"rem should have refused {bad_kw}")
    out["refused"] = 4

    # (iv) --rem-dirs both
    me = mkme(dirs="both")
    me.script = {U["A2"]: ["junk"], U["B2"]: ["bad"]}
    st, calls, _ = cycle(me, 0)
    sent = calls[0][0]
    assert len(calls) == 2 and len(sent) == 8 + 2 and sorted(sent[8:]) == GISTS and {role_of(pr) for pr in sent[:8]} == set(U.values())  # both roles of all four pairs, chains + gists in one call as in default mode
    assert st["units_open"] == st["units_tried"] == 8 and st["chain_gen"] == 8 and st["chain_kept"] == 6 and st["parse_fail"] == 1 and st["dropped_bad"] == 1 and "unit_extra_dropped" not in st, st
    assert set(me.rem_dir_done) == {key_of(n) for n in U if n not in ("A2", "B2")} and all(v == 1 for v in me.rem_dir_done.values()), me.rem_dir_done
    me.script = {U["A2"]: ["good"], U["B2"]: ["bad"]}
    st, calls, _ = cycle(me, 1)  # only the two open units
    assert {role_of(pr) for pr in calls[0][0] if "Two facts" in pr} == {U["A2"], U["B2"]} and st["units_open"] == st["units_tried"] == 2 and st["chain_gen"] == 2 and st["chain_kept"] == 1 and st["dropped_bad"] == 1, st
    assert set(me.rem_dir_done) == {key_of(n) for n in U if n != "B2"}
    me.script = {U["B2"]: ["good"]}
    st, calls, _ = cycle(me, 2)
    assert [role_of(pr) for pr in calls[0][0] if "Two facts" in pr] == [U["B2"]] and st["units_open"] == st["units_tried"] == 1 and st["chain_kept"] == 1 and sum(me.rem_dir_done.values()) == 8
    st, calls, _ = cycle(me, 3)  # all done: no chain sample, the gists still go
    assert sorted(calls[0][0]) == GISTS and st["units_open"] == st["units_tried"] == 0 and "chain_gen" not in st and sum(me.rem_dir_done.values()) == 8 and all(v == 2 for v in me.rem_done.values()) and len(me.rem_chains) == 8
    # the per-cycle cap: cap_chains pairs, so at most 2 x cap units, both directions of the same pair; a pair with both units done goes to the back of the queue
    me = mkme(dirs="both", cap=1)
    st, calls, _ = cycle(me, 0)
    s1 = [role_of(pr) for pr in calls[0][0] if "Two facts" in pr]
    st2, calls2, _ = cycle(me, 1)
    s2 = [role_of(pr) for pr in calls2[0][0] if "Two facts" in pr]
    assert st["units_tried"] == 2 and st["units_open"] == 8 and st2["units_tried"] == 2 and st2["units_open"] == 6 and s1[0][::-1] in s1 and s2[0][::-1] in s2 and not set(s1) & set(s2), (s1, s2, st, st2)
    me = mkme(dirs="both", cap=2)
    st, calls, _ = cycle(me, 0)
    assert st["units_tried"] == 4 and st["units_open"] == 8 and st["chain_gen"] == 4
    # --rem-tries 3: unit-major, the first passing sample of a unit is kept, later ones are unit_extra_dropped, an unverified / failed unit stays open
    me = mkme(dirs="both", tries=3)
    me.script = {U["A1"]: ["bad", "good", "good"], U["A2"]: ["junk", "bad", "nov"]}
    st, calls, _ = cycle(me, 0)
    sent = calls[0][0]
    assert len(sent) == 24 + 2 and all(sent[3 * i] == sent[3 * i + 1] == sent[3 * i + 2] for i in range(8)) and len({*sent[:24]}) == 8 and {role_of(pr) for pr in sent[:24]} == set(U.values())  # each unit 3 times in a row
    assert st == {"units_open": 8, "units_tried": 8, "chain_gen": 24, "parse_fail": 1, "dropped_bad": 2, "dropped_unverified": 1, "unit_extra_dropped": 13, "chain_kept": 7, "gist_gen": 2, "gist_kept": 2, "pool": 9}, st
    assert set(me.rem_dir_done) == {key_of(n) for n in U if n != "A2"} and all(v == 1 for v in me.rem_dir_done.values()) and len(me.rem_chains) == 7
    a1 = [x for x in me.rem_pool if x["kind"] == "chain" and x["q"].startswith("Who is two steps from Zelmir ") and x["a"] == "Harbor Light"]
    assert len(a1) == 1 and "(c0-t1-n" in a1[0]["q"], a1  # A1's first sample was bad, the second passed and is kept, the third is extra
    out["both"] = st

    # (v) rem_plan: the night loop's per-cycle (NREM, REM) steps; at 1.0 the old counts and a Trainer total equal to steps; at 2.0 the REM counts double and the total includes them
    def old_plan(steps, arm):  # the per-cycle counts as the night loop computed them before addendum 14
        cyc = [steps // 4 + (1 if i < steps % 4 else 0) for i in range(4)]
        ns = [c if arm == "ab_norem" else round(c * NREM_SHARE[ci]) for ci, c in enumerate(cyc)]
        return [(n, c - n) for n, c in zip(ns, cyc)]
    for steps in (0, 1, 2, 3, 4, 5, 7, 16, 37, 150, 300, 600, 1200, 2400):
        for arm in ("ab_ob_b4_nb", "ab_norem"):
            pl = rem_plan(steps, arm)
            assert pl == rem_plan(steps, arm, 1.0) == old_plan(steps, arm) and sum(n + r for n, r in pl) == steps, (steps, arm)
            for f in (2.0, 0.5, 1.5, 3.0):
                pf = rem_plan(steps, arm, f)
                assert [n for n, _ in pf] == [n for n, _ in pl] and [r for _, r in pf] == [round(r * f) for _, r in pl] and sum(n + r for n, r in pf) == steps + sum(round(r * f) - r for _, r in pl), (steps, arm, f)
    p150 = rem_plan(150, "ab_ob_b4_nb")
    assert p150 == [(30, 8), (25, 13), (18, 19), (13, 24)] and sum(r for _, r in p150) == 64
    p2 = rem_plan(150, "ab_ob_b4_nb", 2.0)
    assert p2 == [(30, 16), (25, 26), (18, 38), (13, 48)] and sum(n + r for n, r in p2) == 214 == 150 + 64 and rem_plan(150, "ab_norem", 2.0) == [(38, 0), (38, 0), (37, 0), (37, 0)]
    out["plan"] = {"150@1": p150, "150@2": p2}

    # (vi) parse_q1
    ok = {"Who mentors Sotraflil?": "Who mentors Sotraflil?", "  Who mentors Sotraflil?  ": "Who mentors Sotraflil?", "Question: Who mentors Sotraflil?": "Who mentors Sotraflil?", "question:Who mentors Sotraflil?": "Who mentors Sotraflil?",
          "QUESTION : Who mentors Sotraflil?": "Who mentors Sotraflil?", "Q: Who mentors Sotraflil?": "Who mentors Sotraflil?", "q: who mentors sotraflil?": "who mentors sotraflil?", "\"Who mentors Sotraflil?\"": "Who mentors Sotraflil?",
          "'Who mentors Sotraflil?'": "Who mentors Sotraflil?", "\"Question: Who mentors Sotraflil?\"": "Who mentors Sotraflil?", "Question: \"Who mentors Sotraflil?\"": "Who mentors Sotraflil?", "“Who mentors Sotraflil?”": "Who mentors Sotraflil?",
          "\n\n  Who mentors Sotraflil?  \nsome more": "Who mentors Sotraflil?", "Question: Who mentors Sotraflil?\nAnswer: Gliker": "Who mentors Sotraflil?", "Question: Who mentors Sotraflil?\n\nAnswer: Gliker": "Who mentors Sotraflil?",
          "Where does Drovak's mentor live?": "Where does Drovak's mentor live?", "`Who is it?`": "Who is it?"}
    for x, want in ok.items():
        assert parse_q1(x) == want, (x, parse_q1(x))
    none = ["", "   ", "\n \n", None, "Answer: Kelmira", "answer: Who is it?", "Answer : Kelmira?", "Answer: Gliker\nQuestion: Who mentors Sotraflil?", "Who mentors Sotraflil", "Question: Who mentors Sotraflil", "Question:", "Q:", "Question:\nWho mentors Sotraflil?",
            "Question: Who mentors Sotraflil? Answer: Gliker", "Who mentors Sotraflil?.", "Gliker", "Question: Gliker\nAnswer: Gliker?", "I cannot say.", "\"\"", "?x"]
    for x in none:
        assert parse_q1(x) is None, (x, parse_q1(x))
    out["parse_q1"] = {"accepted": len(ok), "rejected": len(none)}
    return out


K2_REPO, K2_REV = "IFM/K2-Horizon-3.7B", "9d280ff742235796925c9fe3cf243dc1beea5c08"  # addendum 11: the pinned small-tier model


def selftest_k2():
    """K2-Horizon chat format, with the real tokenizer (downloaded from the Hub, no weights; skipped with a message when it cannot be): (i) Lang(k2=True).render ends with the
    empty think block exactly once and starts with the bos string, (ii) bos / im_start / im_end / think tags each tokenize to single special ids, (iii) eos is <|ifm|im_end|> = 250019,
    (iv) ex_qa ends with eos and equals the template's own rendering of the same turn (assistant with an empty reasoning_content), the empty think block once before the answer,
    (v) ex_text ends with eos, (vi) the Qwen-style Lang is untouched; (vii) addendum 11b (low effort) and 11c (high effort, what the names pass uses): render_think's tail, think_eos ids, and stage 2 == the template's own
    rendering of the finished turn, also through Brain.names_pass itself; selftest_q4 passes."""
    selftest_q4()  # raises on failure
    out = {"q4": "ok"}
    try:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(K2_REPO, revision=K2_REV, trust_remote_code=True)
    except Exception as e:  # offline / Hub unreachable
        return {**out, "skipped": f"K2 tokenizer not available ({type(e).__name__}); K2 checks not run"}
    L = Lang(tok, False, torch.device("cpu"), k2=True)
    u = "Where does Zelmir live?"
    p = L.render(SYS, u)
    assert p.startswith("<|ifm|begin_of_text|>") and p.endswith("<|ifm|im_start|>assistant\n<ifm|think>\n</ifm|think>"), p
    assert p.count("<ifm|think>") == 1 and p.count("</ifm|think>") == 1, p
    sp = {t: tok.convert_tokens_to_ids(t) for t in ("<|ifm|begin_of_text|>", "<|ifm|im_start|>", "<|ifm|im_end|>", "<ifm|think>", "</ifm|think>")}
    assert L.eos == sp["<|ifm|im_end|>"] == 250019, L.eos
    ids = L.ids(p)
    assert ids[0] == sp["<|ifm|begin_of_text|>"] and ids[-1] == sp["</ifm|think>"] and ids[-3] == sp["<ifm|think>"], ids[-10:]
    assert [ids.count(sp[t]) for t in sp] == [1, 3, 2, 1, 1], "special tokens must be single ids (system, user, assistant turns)"
    ids_q, st = ex_qa(L, u, "Oslo")
    full = tok.apply_chat_template([{"role": "system", "content": SYS}, {"role": "user", "content": u}, {"role": "assistant", "content": "Oslo", "reasoning_content": ""}], tokenize=False)
    assert ids_q == L.ids(full), (ids_q[-10:], L.ids(full)[-10:])
    assert ids_q[-1] == 250019 and ids_q.count(sp["</ifm|think>"]) == 1 and ids_q[st - 1] == sp["</ifm|think>"] and ids_q[st:-1] == L.ids("Oslo")
    ids_t, st_t = ex_text(L, "Zelmir lives in Oslo.")
    assert ids_t[-1] == 250019 and st_t == 0
    q = Lang(tok, True, torch.device("cpu"))  # default constructor: the old behaviour (smoke render, tokenizer eos)
    assert not q.k2 and q.eos == tok.eos_token_id and q.render(SYS, u) == f"system: {SYS}\nuser: {u}\nassistant: "
    # addendum 11b: render_think (think block left open at low effort), its stop ids, and stage 2 = prompt + thinking + close tag + answer + im_end == the template's own rendering of that turn
    pt = L.render_think(SYS, u)
    msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": u}]
    assert pt.startswith("<|ifm|begin_of_text|>") and pt.endswith("<|ifm|im_start|>assistant\n<ifm|think_faster>\n") and pt.count("<ifm|think_faster>") == 1 and K2_FAST_SHUT not in pt, pt[-80:]
    assert pt[:-len("<ifm|think_faster>\n")] + "<ifm|think>\n" == tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True), "low effort differs from the default prompt only in the opening tag"
    assert L.render_think(SYS, u, "medium").endswith("assistant\n<ifm|think_fast>\n") and L.render_think(SYS, u, "high") == pt[:-len("<ifm|think_faster>\n")] + "<ifm|think>\n"
    assert tok.convert_tokens_to_ids(["<ifm|think_faster>", K2_FAST_SHUT]) == [250052, 250053] and L.think_eos() == [250053, 250019], L.think_eos()
    pid = L.ids(pt)
    assert pid[-2] == 250052 and pid[-1] == L.ids("\n")[0] and L.ids(pt + "abc def" + K2_FAST_SHUT)[-1] == 250053, pid[-5:]
    stage2 = pt + "abc def" + K2_FAST_SHUT + "no" + K2_END
    assert stage2 == tok.apply_chat_template(msgs + [{"role": "assistant", "content": "no", "think_faster": "abc def"}], tokenize=False), stage2[-100:]
    assert names_prompt(L, "Magomen works at Kelmira.", "Magomen", "Kelmira", think=True).endswith("assistant\n<ifm|think_faster>\n") and names_prompt(L, "x", "A", "B").endswith("<ifm|think>\n</ifm|think>")
    # addendum 11c: the names pass at high effort (K2_NAMES_EFFORT, the template default): the block is left open after "<ifm|think>\n", stage 1 stops at </ifm|think> or im_end, stage 2 == the template's rendering of the turn
    assert K2_NAMES_EFFORT == "high" and NAMES_THINK_MAX == 512 and K2_THINK_SHUT[K2_NAMES_EFFORT] == K2_SHUT == "</ifm|think>"
    ph = L.render_think(SYS, u, K2_NAMES_EFFORT)
    assert ph.endswith("<|ifm|im_start|>assistant\n<ifm|think>\n") and ph.count("<ifm|think>") == 1 and K2_SHUT not in ph and ph == tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True), ph[-80:]
    assert tok.convert_tokens_to_ids(["<ifm|think>", K2_SHUT]) == [250029, 250030] and L.think_eos(K2_NAMES_EFFORT) == [250030, 250019] and L.think_eos("high") == [250030, 250019], L.think_eos("high")
    pidh = L.ids(ph)
    assert pidh[-2] == 250029 and pidh[-1] == L.ids("\n")[0] and L.ids(ph + "abc def" + K2_SHUT)[-1] == 250030 and pidh[:-2] == pid[:-2], pidh[-5:]
    stage2h = ph + "abc def" + K2_THINK_SHUT[K2_NAMES_EFFORT] + "no" + K2_END
    assert stage2h == tok.apply_chat_template(msgs + [{"role": "assistant", "content": "no", "think": "abc def"}], tokenize=False), stage2h[-100:]  # the template's own field for the high-effort block
    assert stage2h == tok.apply_chat_template(msgs + [{"role": "assistant", "content": "no", "reasoning_content": "abc def"}], tokenize=False)  # (and the default reasoning_content field, the one ex_qa uses)
    nph = names_prompt(L, "Magomen works at Kelmira.", "Magomen", "Kelmira", think=True, effort=K2_NAMES_EFFORT)
    assert nph.endswith("assistant\n<ifm|think>\n") and nph.count("<ifm|think>") == 1 and K2_SHUT not in nph and K2_FAST_SHUT not in nph, nph[-80:]
    assert strip_think("abc def" + K2_SHUT + K2_END, K2_NAMES_EFFORT) == ("abc def", True) and strip_think("abc def" + K2_FAST_SHUT, K2_NAMES_EFFORT) == ("abc def" + K2_FAST_SHUT, False)
    # ... and through Brain.names_pass itself (stub gen, real tokenizer): the prompts it builds for stage 2 + the answer + im_end are the template's rendering of [system, user, assistant(think, answer)]
    from types import SimpleNamespace
    seen, cap = [], {}
    Lc = SimpleNamespace(k2=True, ids=L.ids, think_eos=L.think_eos, render=L.render, render_think=lambda sy, uu, e="low": (cap.__setitem__("u", uu), L.render_think(sy, uu, e))[1])  # records the user message names_prompt builds

    def gen_k2(prompts, n, **kw):
        seen.append((list(prompts), n, kw))
        return ["They are siblings." + K2_SHUT, "z " * 60][:len(prompts)] + ["x"] * (len(prompts) - 2) if len(seen) == 1 else ["is the brother of", "No relation", "works at"][:len(prompts)]
    dia = Diary({"diary": [{"role": "user", "day": 2, "text": "hey Magomen met Papirar and Torvald today"}]})
    me = SimpleNamespace(L=Lc, diary=dia, items={}, dropped=set(), tag_log=[(0, 2, [])], raw={}, gen=gen_k2, mn=lambda n: n)
    rec = Brain.names_pass(me, 2)
    (p1, n1, kw1), (p2, n2, kw2) = seen
    assert len(p1) == 3 and n1 == 512 and kw1 == {"eos": [250030, 250019]} and n2 == 12 and kw2 == {} and all(p.endswith("assistant\n<ifm|think>\n") and K2_SHUT not in p for p in p1), (kw1, [p[-40:] for p in p1])
    th = ["They are siblings.", ("z " * 60).strip(), "x"]
    um = [{"role": "system", "content": "You extract facts from chat messages."}, {"role": "user", "content": cap["u"]}]  # (the last prompt's user message; the three differ only in the names)
    assert p2[2] == p1[2] + "x" + K2_SHUT and p2[2] + "works at" + K2_END == tok.apply_chat_template(um + [{"role": "assistant", "content": "works at", "think": "x"}], tokenize=False), p2[2][-120:]
    assert all(q == pp + x + K2_SHUT and q.count(K2_SHUT) == 1 and K2_END not in q[len(pp):] for q, pp, x in zip(p2, p1, th)) and rec["yes"] == 2 and rec["think_capped"] == 2, (rec, [q[-60:] for q in p2])  # one close tag also when stage 1 ran out of tokens
    return {**out, "names_render_tail_high": ph[-48:], "names_think_eos": kw1["eos"], "names_stage2_tail_high": p2[2][-60:],
            "render_tail": p[-48:], "think_render_tail": pt[-48:], "think_eos": L.think_eos(), "prompt_tail_ids": ids[-10:], "ex_qa_tail_ids": ids_q[-5:], "eos": L.eos}


# ------------------------------------------------------------------ main
def add15_error(args, budget_scale):  # addendum 15: main()'s checks of the new flags, as the message ap.error prints (None: fine); budget_scale: --budget-scale as given, before default_scale
    ts, dv = getattr(args, "text_scale", None), getattr(args, "dream_vary", "off")
    if ts is not None and budget_scale is None:
        return "--text-scale needs --budget-scale (it sets the generation knobs apart from the training steps)"
    if ts is not None and not ts > 0:
        return "--text-scale must be positive"
    if dv != "off" and args.arm in EXTRA_ARMS:
        return f"--dream-vary cannot be combined with the twist arms {EXTRA_ARMS} (it takes the place of their extra texts)"
    if dv != "off" and args.arm not in OB_ARMS:
        return f"--dream-vary needs an open-book arm {OB_ARMS} (the cards are asked as open-book Q&A)"
    return None


def selftest_add15():
    """Addendum 15 on stubs (no model, no GPU; RNG states put back): (i) nrem_prompt and parse_scenes at their defaults are the old code byte for byte (verbatim copies below), kp changes only the paraphrase count; (ii) the text-scale knobs: the five generation
    knobs at the text scale, the steps at the work scale, no flag = today's numbers, a stub args without the flags = no flag; kp = ceil(k/4) only under --dream-vary; (iii) Brain.dream asks kp paraphrases and keeps paras[:kp] and the k cards; (iv) vary_prompt and
    Brain.vary: prompts, parsing, every check and its stat key, the check card j % len, order of the kept texts, one seeded sampling per style (seed * 100 + night + 43 + style index), the global RNG put back, the base model, 80 n tokens, mix vs plain; (v) reword scoring on a
    fake generate, the hand-computed numbers (recall, share, cards, gaps, seen, variety, McNemar booleans, rows, skips) with and without a Brain; (vi) the flag checks; (vii) make_reworded's helpers are sleepb's, and data/week2_reworded.json (if there) passes the PREREG's checks."""
    from argparse import Namespace
    from types import SimpleNamespace
    import inspect
    out, cpu = {}, torch.device("cpu")
    rng0 = torch.get_rng_state()
    try:
        # ---- (i) the defaults are the old code
        Lr = SimpleNamespace(render=lambda sy, u: f"<{sy}>{u}", device=cpu)
        it = Item(key=("drovak", "kelmira"), subj="Drovak", obj="Kelmira", rel="lives in", born=1)

        def old_nrem(L_, ctx, it_, k=K):  # nrem_prompt as it was before addendum 15
            u = (f"Messages Sam sent in chat, newest first, labelled by day. If they disagree, the newest message is true.\n{ctx}\n\n"
                 f"Focus on the fact linking \"{it_.subj}\" and \"{it_.obj}\". Write {k} paraphrases of the CURRENT fact (short standalone sentences, "
                 f"different wording, naming both) and {k} question-answer pairs about it. Cover both directions: some questions should ask about one "
                 f"name, some about the other. Each answer must be a single name from the fact. Reply with only JSON of the form "
                 f"{{\"paraphrases\": [\"...\"], \"qa\": [{{\"q\": \"...\", \"a\": \"...\"}}]}}")
            return L_.render("You are a careful assistant that studies facts.", u)

        def old_scenes(txt):  # parse_scenes as it was before addendum 15
            res = []
            for ln in txt.splitlines():
                m = re.match(r"^[\s*#>-]*(?:scene\s*)?\d+\s*[.):*-]+\s*(.+)$", ln, re.I)
                if m and m.group(1).strip(" *\"'"):
                    res.append(m.group(1).strip(" *\"'"))
            return res[:2]
        for k in (1, 4, 8, 16, 32):
            assert nrem_prompt(Lr, "[Day 1] x", it, k) == old_nrem(Lr, "[Day 1] x", it, k) == nrem_prompt(Lr, "[Day 1] x", it, k, None) == nrem_prompt(Lr, "[Day 1] x", it, k, k)
        assert nrem_prompt(Lr, "c", it) == old_nrem(Lr, "c", it)
        p84 = nrem_prompt(Lr, "c", it, 32, 8)
        assert p84 == old_nrem(Lr, "c", it, 32).replace("Write 32 paraphrases", "Write 8 paraphrases") and "Write 8 paraphrases of the CURRENT fact" in p84 and "and 32 question-answer pairs" in p84
        for txt in ("1. a b c\n2. d e f\n3. g h i", "Scene 1: 'x y'\nScene 2) *z w*\n- 3. q", "no numbers at all", "1.\n2.  \n3. ok", "  10) ten\n9: nine\n8- eight", ""):
            assert parse_scenes(txt) == old_scenes(txt) == parse_scenes(txt, 2)
        t5 = "\n".join(f"{i}. text {i}" for i in range(1, 9))
        assert parse_scenes(t5, 4) == [f"text {i}" for i in range(1, 5)] and len(parse_scenes(t5, 8)) == 8 and len(parse_scenes(t5)) == 2
        out["defaults_byte_identical"] = True

        # ---- (ii) the text-scale knobs
        def knobs(budget, text, vary="off", flags=True):
            a_ = dict(max_dream_items=160, rem_chains=30, rem_gist=30)
            me_ = SimpleNamespace(a=SimpleNamespace(**a_, **({"text_scale": text, "dream_vary": vary} if flags else {})))
            me_.sc, me_.tsc = (lambda n: Brain.sc(me_, n)), (lambda n: Brain.tsc(me_, n))  # noqa: E731
            Brain.set_scale(me_, budget)
            return me_

        def kn(m_):
            return (m_.k, m_.cap_items, m_.cap_chains, m_.cap_gist, m_.dream_new)
        for b in (0.5, 1.0, 2.0, 4.0, 8.0):
            sc_ = lambda n: Brain.sc(SimpleNamespace(scale=b), n)  # noqa: E731
            today = (sc_(K), sc_(160), sc_(30), sc_(30), sc_(400))  # addendum 5's numbers: the formula as it was
            for m_ in (knobs(b, None), knobs(b, None, flags=False)):
                assert kn(m_) == today and m_.scale == b and m_.tscale == b and m_.kp is None, (b, kn(m_), today)
        assert kn(knobs(8.0, None)) == (32, 1280, 240, 240, 3200) and kn(knobs(4.0, None)) == (16, 640, 120, 120, 1600)
        r8 = knobs(8.0, 4.0)
        assert kn(r8) == (16, 640, 120, 120, 1600) == kn(knobs(4.0, None)) and r8.scale == 8.0 and r8.tscale == 4.0 and r8.sc(150) == 1200 and r8.sc(150) == knobs(8.0, None).sc(150) and r8.sc(40) == 320
        assert kn(knobs(8.0, 1.0)) == (4, 160, 30, 30, 400) and kn(knobs(2.0, 0.5)) == (2, 80, 15, 15, 200) and kn(knobs(1.0, 3.0)) == (12, 480, 90, 90, 1200) and knobs(1.0, 3.0).sc(150) == 150
        assert [knobs(8.0, 4.0, "mix").kp, knobs(8.0, None, "plain").kp, knobs(1.0, None, "mix").kp, knobs(2.0, 0.5, "mix").kp, knobs(8.0, 4.0, "off").kp] == [4, 8, 1, 1, None]
        src_night = inspect.getsource(Brain.night)
        assert "ref_n, steps = steps, s.sc(steps)" in src_night and "tsc(" not in src_night, "the night's steps are planned at the work scale"
        out["text_scale"] = {"R8": kn(r8), "steps_150": r8.sc(150)}

        # ---- (iii) Brain.dream: kp paraphrases asked and kept, k cards kept; no flag = as before
        def dream_run(vary):
            ev = {"gen": [], "vary": []}
            it_ = Item(key=("drovak", "kelmira"), subj="Drovak", obj="Kelmira", rel="lives in", born=1, nment=1, dirty=True, days=2)
            js = json.dumps({"paraphrases": [f"Drovak lives in Kelmira, version {i}." for i in range(6)], "qa": [{"q": f"Question {i} about Drovak's town?", "a": "Kelmira"} for i in range(6)]})

            def gen_(prompts, max_new, base=True, sample=False, temp=0.8, eos=None):
                ev["gen"].append((len(prompts), max_new, sample, base, prompts[0]))
                return [js] * len(prompts) if sample else ["Kelmira"] * len(prompts)
            me_ = knobs(1.0, None, vary)
            me_.__dict__.update(L=Lr, gen=gen_, mn=lambda n: n, raw={}, examples={"dreams": [], "probes": [], "now": [], "vary": []}, leak=set(), items={it_.key: it_},
                                diary=SimpleNamespace(containing=lambda a_, b_, d_: [0], label=lambda idx: "[Day 1] ctx"), vary=lambda *x: ev["vary"].append(x))
            me_.a.arm, me_.a.smoke = "ab_ob", False
            me_.leaky = lambda t: Brain.leaky(me_, t)
            st_ = Brain.dream(me_, 2, [it_])
            return me_, it_, st_, ev
        m0, it0, st0, ev0 = dream_run("off")
        assert ev0["gen"][0][4] == nrem_prompt(Lr, "[Day 1] ctx", it0, 4) == old_nrem(Lr, "[Day 1] ctx", it0, 4) and len(it0.para) == 4 and st0["paraphrases_gen"] == 4 and st0["qa_gen"] == 4 and ev0["vary"] == []
        m1, it1_, st1, ev1 = dream_run("mix")
        assert ev1["gen"][0][4] == nrem_prompt(Lr, "[Day 1] ctx", it1_, 4, 1) and "Write 1 paraphrases" in ev1["gen"][0][4] and "and 4 question-answer pairs" in ev1["gen"][0][4]
        assert len(it1_.para) == 1 and it1_.para == ["Drovak lives in Kelmira, version 0."] and st1["paraphrases_gen"] == 1 and st1["qa_gen"] == 4 and len(it1_.qa) == 3 and it1_.probe is not None  # 4 cards: 1 probe + 3
        assert len(ev1["vary"]) == 1 and ev1["vary"][0][0] == 2 and ev1["vary"][0][1] == [it1_] and ev1["vary"][0][2] == {it1_.key: "[Day 1] ctx"} and isinstance(ev1["vary"][0][3], Counter)  # (the live stats Counter: dream returns a copy of it)
        out["dream_kp"] = {"off": len(it0.para), "mix": len(it1_.para)}

        # ---- (iv) vary_prompt, Brain.vary
        ctx = "[Day 1] ctx"
        ps = {sty: vary_prompt(Lr, ctx, it, sty, 4) for sty in ("story", "note", "weird", "plain2")}
        head = twist_prompt(Lr, ctx, it)[:twist_prompt(Lr, ctx, it).index("Write 2")]
        assert all(p.startswith(head) and p == para2_prompt(Lr, ctx, it)[:len(head)] + p[len(head):] for p in ps.values()), "system line, context framing and fact line as twist_prompt / para2_prompt"
        assert head.startswith("<You are a careful assistant that studies facts.>Messages Sam sent in chat, newest first") and 'Focus on the fact "Drovak lives in Kelmira". ' in head
        for sty, words in (("story", "tiny everyday stories"), ("note", "in Sam's own voice (first person"), ("weird", "dream-like scenes"), ("plain2", "ordinary paraphrases")):
            p = ps[sty]
            assert "Write 4 " in p and words in p and 'name both "Drovak" and "Kelmira"' in p and "numbered 1 to 4, and nothing else." in p and "stays true" in p, (sty, p)
        assert "surreal" in ps["weird"] and "surreal" not in ps["plain2"] and "plain everyday wording" in ps["plain2"] and ps["story"] != ps["note"]

        def vary_scene(mode, d=2, seed=3):
            i1 = Item(key=("drovak", "kelmira"), subj="Drovak", obj="Kelmira", rel="lives in", born=1, para=["Drovak lives in Kelmira."], qa=[("Where does Drovak live?", "Kelmira"), ("Who lives in Kelmira?", "Drovak")])
            i2 = Item(key=("zelmir", "tavrix"), subj="Zelmir", obj="Tavrix", rel="works at", born=1, para=["Zelmir works at Tavrix."], qa=[("Where does Zelmir work?", "Tavrix")],
                      upd=[{"shared": "Zelmir", "old": "Skarum", "new": "Tavrix", "old_key": ("zelmir", "skarum")}])
            i3 = Item(key=("kelvora", "zhoumira"), subj="Kelvora", obj="Zhoumira", rel="eats with", born=1)  # no cards, no probe: skipped
            i4 = Item(key=("brokai", "fenlus"), subj="Brokai", obj="Fenlus", rel="is sibling of", born=1, probe=("Who is Brokai's sibling?", "Fenlus"))
            calls = []

            def gen_(prompts, max_new, base=True, sample=False, temp=0.8, eos=None):
                calls.append({"n": len(prompts), "max_new": max_new, "sample": sample, "base": base, "draw": torch.rand(1).item() if sample else None, "prompts": prompts})  # (greedy generation draws nothing)
                if not sample:  # the verifier: knows every answer unless the text says UNVERIFIABLE
                    return ["no idea" if "UNVERIFIABLE" in p else "Kelmira, Tavrix, Drovak, Fenlus" for p in prompts]
                sty = ["tiny everyday stories", "short notes", "dream-like scenes" if mode == "mix" else "ordinary paraphrases"]
                si = next(i for i, w in enumerate(sty) if w in prompts[0])
                return REPL[si]
            me_ = SimpleNamespace(a=SimpleNamespace(seed=seed, smoke=False, dream_vary=mode), k=16, L=SimpleNamespace(device=cpu, render=lambda sy, u: f"{sy}||{u}"), leak={norm("Where is Dax?")},
                                  items={}, raw={}, examples={"vary": []}, mn=lambda n_: n_, gen=gen_)
            me_.leaky, me_.stale_hit = (lambda t: Brain.leaky(me_, t)), (lambda i_, t: Brain.stale_hit(me_, i_, t))  # noqa: E731
            st_ = Counter()
            REPL = [["1. Drovak lives in Kelmira, so Sam mailed him there.\n2. Kelmira is the town where Drovak lives.\n3. Where is Dax?\n4. Sam met Drovak somewhere nice.",
                     "1. Zelmir used to work at Skarum but now works at Tavrix.\n2. Sam asked Zelmir about Tavrix.", "I cannot do that."],
                    ["1. UNVERIFIABLE: Note to self, Drovak lives in Kelmira.\n2. Note: Kelmira, Drovak's town.\n3. drovak LIVES in Kelmira.",
                     "1) Note: Zelmir, Tavrix, desk 4.\n2) Also: Tavrix is where Zelmir goes each morning.", "1. Sam's note: Brokai and Fenlus are siblings."],
                    ["1. In a dream, Drovak lives in Kelmira on a cloud.\n2. In a dream, Drovak lives in Kelmira on a cloud.",
                     "1. A green sky over Tavrix, where Zelmir works.\n2. Zelmir works at Tavrix in the upside-down office.\n3. Zelmir flies to Tavrix.\n4. Tavrix hums while Zelmir works.",
                     "1. A talking fish tells Brokai that Fenlus is a sibling."]]
            state = torch.get_rng_state()
            Brain.vary(me_, d, [i1, i2, i3, i4], {i.key: ctx for i in (i1, i2, i3, i4)}, st_)
            assert torch.equal(torch.get_rng_state(), state), "Brain.vary moved the global RNG"
            return me_, (i1, i2, i3, i4), st_, calls
        me, (i1, i2, i3, i4), st, calls = vary_scene("mix")
        assert [(c["n"], c["max_new"], c["sample"], c["base"]) for c in calls] == [(3, 320, True, True)] * 3 + [(16, 20, False, True)], [(c["n"], c["max_new"], c["sample"], c["base"]) for c in calls]
        for si, c in enumerate(calls[:3]):
            torch.manual_seed(3 * 100 + 2 + 43 + si)
            assert c["draw"] == torch.rand(1).item(), "style sampled under seed * 100 + night + 43 + style index"
        assert calls[0]["prompts"] == [vary_prompt(me.L, ctx, i, "story", 4) for i in (i1, i2, i4)] and "dream-like scenes" in calls[2]["prompts"][0] and "short notes" in calls[1]["prompts"][1]
        assert calls[3]["prompts"][0] == ctx_prompt(me.L, "Drovak lives in Kelmira, so Sam mailed him there.", "Where does Drovak live?") and calls[3]["prompts"][1] == ctx_prompt(me.L, "Kelmira is the town where Drovak lives.", "Who lives in Kelmira?")
        want = Counter({"vary_skipped_no_check": 1,
                        "vary_story_gen": 6, "vary_story_parse_fail": 1, "vary_story_dropped_test_leak": 1, "vary_story_dropped_missing_entities": 1, "vary_story_dropped_stale": 1, "vary_story_kept": 3,
                        "vary_note_gen": 6, "vary_note_dropped_unverified": 1, "vary_note_dropped_dup": 1, "vary_note_kept": 4,
                        "vary_weird_gen": 7, "vary_weird_dropped_dup": 1, "vary_weird_kept": 6})
        assert st == want, (dict(st), dict(want))
        assert i1.para == ["Drovak lives in Kelmira.", "Drovak lives in Kelmira, so Sam mailed him there.", "Kelmira is the town where Drovak lives.", "Note: Kelmira, Drovak's town.", "In a dream, Drovak lives in Kelmira on a cloud."]
        assert i2.para == ["Zelmir works at Tavrix.", "Sam asked Zelmir about Tavrix.", "Note: Zelmir, Tavrix, desk 4.", "Also: Tavrix is where Zelmir goes each morning.", "A green sky over Tavrix, where Zelmir works.",
                           "Zelmir works at Tavrix in the upside-down office.", "Zelmir flies to Tavrix.", "Tavrix hums while Zelmir works."]
        assert i4.para == ["Sam's note: Brokai and Fenlus are siblings.", "A talking fish tells Brokai that Fenlus is a sibling."] and i3.para == [] and i1.qa == [("Where does Drovak live?", "Kelmira"), ("Who lives in Kelmira?", "Drovak")]
        assert set(me.raw["vary"]) == {"story", "note", "weird"} and all(len(v) == 2 for v in me.raw["vary"].values()) and me.raw["vary"]["story"][0].startswith("1. Drovak lives")
        ex = {e["text"]: e for e in me.examples["vary"]}  # (the first 12 candidates)
        assert len(me.examples["vary"]) == 12 and ex["Kelmira is the town where Drovak lives."]["check_q"] == "Who lives in Kelmira?" and ex["Note: Kelmira, Drovak's town."]["check_q"] == "Who lives in Kelmira?"  # j = 1 -> card 1
        assert ex["drovak LIVES in Kelmira."]["check_q"] == "Where does Drovak live?" and ex["drovak LIVES in Kelmira."]["kept"] is False and ex["Sam asked Zelmir about Tavrix."]["check_q"] == "Where does Zelmir work?"  # j = 2 -> card 0; one card: j % 1
        assert ex["UNVERIFIABLE: Note to self, Drovak lives in Kelmira."]["kept"] is False and ex["Sam's note: Brokai and Fenlus are siblings."]["check_q"] == "Who is Brokai's sibling?"  # the probe is the check without cards
        # plain: the third style is plain2 (ordinary paraphrases), same seeds, its own stat keys; the leak / check pieces are shared
        mp, (p1, p2, p3, p4), stp, callsp = vary_scene("plain")
        assert "ordinary paraphrases" in callsp[2]["prompts"][0] and "surreal" not in callsp[2]["prompts"][0] and stp["vary_plain2_gen"] == 7 and stp["vary_plain2_kept"] == 6 and not any("weird" in k for k in stp) and set(mp.raw["vary"]) == {"story", "note", "plain2"}
        assert {k: v for k, v in stp.items() if "plain2" not in k} == {k: v for k, v in want.items() if "weird" not in k}
        # another night / seed: other seeds, same everything else
        _, _, _, calls2 = vary_scene("mix", d=5, seed=7)
        for si, c in enumerate(calls2[:3]):
            torch.manual_seed(7 * 100 + 5 + 43 + si)
            assert c["draw"] == torch.rand(1).item()
        out["vary"] = {k: v for k, v in sorted(st.items()) if k.endswith(("_gen", "_kept"))}

        # ---- (v) reword scoring on a fake generate
        G = [(0, "C2", [("drovak", "kelmira")], []), (1, "C2", [("drovak", "gliker")], []), (2, "C4", [("zelmir", "tavrix")], []), (3, "C1", [("brokai", "fenlus")], [])]
        mk = lambda key, subj, obj, para, qa, dead=False: Item(key=key, subj=subj, obj=obj, rel="r", born=1, para=para, qa=qa, dead=dead)  # noqa: E731
        k0 = mk(("drovak", "kelmira"), "Drovak", "Kelmira", ["Drovak lives in Kelmira.", "Sam asked: where does Drovak reside? Then went on."],
                [("Which town is Drovak's home?", "Kelmira"), ("Who resides in Kelmira?", "Drovak"), ("What place does Drovak call home?", "Kelmira"), ("Which place is Drovak's residence?", "Kelmira"), ("Name Drovak's home town.", "Kelmira")])
        k1 = mk(("drovak", "gliker"), "Drovak", "Gliker", ["Drovak mentors Gliker."], [("Who does Drovak mentor?", "Gliker")])
        k2 = mk(("zelmir", "tavrix"), "Zelmir", "Tavrix", ["Zelmir works at Tavrix."], [("Where does Zelmir work?", "Tavrix")])
        kd = mk(("kelmira", "drovak"), "Kelmira", "Drovak", [], [("A dead card about Drovak's home?", "Kelmira")], dead=True)
        pool_ = [{"q": "In which place does Gliker's mentor live?", "a": "Kelmira", "keys": [k1.key, k0.key], "kind": "chain"}, {"q": "A chain with the wrong answer?", "a": "Gliker", "keys": [k1.key, k0.key], "kind": "chain"},
                 {"q": "A gist question?", "a": "Kelmira", "keys": [k0.key], "kind": "gist"}, {"q": "A chain of other items?", "a": "Kelmira", "keys": [k2.key, k0.key], "kind": "chain"}]
        brain = SimpleNamespace(G=G, items={x.key: x for x in (k0, k1, k2, kd)}, rem_pool=pool_)
        week = {"tests": {"forward": [{"q": "Where does Drovak live?", "target": "Kelmira", "item": 0, "class": "C2"}, {"q": "Which company employs Zelmir?", "target": "Tavrix", "item": 2, "class": "C4"},
                                      {"q": "Who is Brokai's sibling?", "target": "Fenlus", "item": 3, "class": "C1"}],
                          "reverse": [{"q": "Who lives in Kelmira?", "target": "Drovak", "item": 0, "class": "C2"}, {"q": "Who works at Tavrix?", "target": "Zelmir", "item": 2, "class": "C4"}],
                          "twohop": [{"q": "In which place does the mentor of Gliker live?", "target": "Kelmira", "items": [1, 0]}, {"q": "Where does Brokai's sibling work?", "target": "Tavrix", "items": [3, 2]}],
                          "changed": [], "routine": []}}
        spec = {"tests": {"forward": [{"q_src": "Where does Drovak live?", "target": "Kelmira", "item": 0, "class": "C2", "test_index": 0, "rewordings": ["In which town does Drovak live?", "Where does Drovak reside?", "Drovak makes his home where?"]},
                                      {"q_src": "Which company employs Zelmir?", "target": "Tavrix", "item": 2, "class": "C4", "test_index": 1, "rewordings": ["Which firm pays Zelmir?", "Zelmir is on whose payroll?"]},
                                      {"q_src": "A question that is not in the week?", "target": "Kelmira", "item": 0, "class": "C2", "test_index": 7, "rewordings": ["x?", "y?", "z?"]}],
                         "reverse": [{"q_src": "Who lives in Kelmira?", "target": "Drovak", "item": 0, "class": "C2", "test_index": 0, "rewordings": ["Which person lives in Kelmira?", "Kelmira is home to whom?", "Who resides in Kelmira?"]},
                                     {"q_src": "Who works at the wrong place?", "target": "Zelmir", "item": 2, "class": "C4", "test_index": 1, "rewordings": ["a?", "b?", "c?"]}],
                         "twohop": [{"q_src": "In which place does the mentor of Gliker live?", "target": "Kelmira", "items": [1, 0], "classes": ["C2", "C2"], "test_index": 0,
                                     "rewordings": ["In which place does Gliker's mentor live?", "Where does the person who mentors Gliker reside?", "Gliker's mentor lives in which town?"]},
                                    {"q_src": "Where does Brokai's sibling work?", "target": "Tavrix", "items": [3, 2], "classes": ["C1", "C4"], "test_index": 1,
                                     "rewordings": ["At which company does Brokai's sibling work?", "Brokai's sibling is employed where?", "Where is Brokai's brother or sister employed?"]}]}}
        card_pool = [q for q, a_ in k0.qa if a_ == "Kelmira"]
        sampled = random.Random(1 * 1000 + 0).sample(card_pool, 3)  # forward test 0's three cards (seed 1)
        right = {"In which town does Drovak live?": "Kelmira", "Where does Drovak reside?": "Kelmira", "Which firm pays Zelmir?": "Tavrix", "Who resides in Kelmira?": "Drovak", "In which place does Gliker's mentor live?": "Kelmira",
                 "Where does the person who mentors Gliker reside?": "Kelmira", "Gliker's mentor lives in which town?": "Kelmira", sampled[1]: "Kelmira", sampled[2]: "Kelmira"}  # sampled[0] and "Where does Zelmir work?" are wrong
        gcalls = []

        def fake_generate(model, prompts, max_new=20, bs=8, **kw):
            gcalls.append((len(prompts), max_new, bs, model))
            return [f"The answer is {right[p]}." if p in right else "I do not know." for p in prompts]
        Lf = SimpleNamespace(render=lambda sy, q: q, generate=fake_generate, device=cpu)
        assert plain_prompt(Lf, "Q?") == "Q?"
        mdl = SimpleNamespace(eval=lambda: None)
        rw = reword_eval(Lf, mdl, week, brain, spec, 16, 1)
        assert gcalls == [(20, 20, 16, mdl)], gcalls  # ONE call: 14 wordings + 5 cards + 1 chain dream, greedy defaults, 20 tokens, the given batch size
        assert rw["mapped"] == {"forward": 2, "reverse": 1, "twohop": 2} and rw["skipped_unmapped"] == {"forward": 1, "reverse": 1} and rw["wordings_per_test"] == {2: 1, 3: 4}
        ap_ = lambda x, y: x is not None and abs(x - y) < 1e-9  # noqa: E731
        nw = rw["new_wording"]
        assert (nw["forward"]["n"], nw["forward"]["recall"]) == (2, 0.5) and ap_(nw["forward"]["share"], 7 / 12) and (nw["reverse"]["n"], nw["reverse"]["recall"]) == (1, 0.0) and ap_(nw["reverse"]["share"], 1 / 3)
        assert nw["both"]["n"] == 3 and ap_(nw["both"]["recall"], 1 / 3) and ap_(nw["both"]["share"], 0.5) and (nw["twohop"]["n"], nw["twohop"]["recall"], nw["twohop"]["share"]) == (2, 0.5, 0.5)
        assert nw["by_class"]["C2"]["n"] == 2 and nw["by_class"]["C2"]["recall"] == 0.5 and ap_(nw["by_class"]["C2"]["share"], 0.5) and nw["by_class"]["C4"]["n"] == 1 and nw["by_class"]["C4"]["recall"] == 0.0 and set(nw["by_class"]) == {"C2", "C4"}
        assert rw["cards"] == {"tests_in_scope": 3, "tests_with_cards": 3, "cards_asked": 5, "mean_acc": rw["cards"]["mean_acc"]} and ap_(rw["cards"]["mean_acc"], 5 / 9)
        assert ap_(rw["cramming_gap_pts"], round(100 * (5 / 9 - 0.5), 2)) and ap_(rw["cramming_gap_majority_pts"], round(100 * (5 / 9 - 1 / 3), 2)) and rw["cramming_gap_basis"]["tests"] == 3
        assert rw["twohop_cards"] == {"tests": 1, "dreams_asked": 1, "chain_acc": 1.0, "reword_share": 1.0, "reword_recall": 1.0, "gap_pts": 0.0, "gap_majority_pts": 0.0}
        sn = rw["seen"]
        assert (sn["rewordings"], sn["seen"]) == (14, 3) and ap_(sn["seen_share"], 3 / 14) and sn["unseen"]["rewordings"] == 11 and ap_(sn["unseen"]["share_right"], 4 / 11)
        assert sn["unseen"]["both"] == {"n": 3, "recall": 0.0} and sn["unseen"]["twohop"] == {"n": 2, "recall": 0.5}
        assert rw["per_test"] == {"forward": {0: True, 1: False}, "reverse": {0: False}, "twohop": {0: True, 1: False}}
        by_src = Counter(r["src"] for r in rw["rows"])
        assert by_src == {"reword": 14, "card": 5, "chain": 1} and len(rw["rows"]) == 20 and all(r.keys() >= {"src", "kind", "test", "q", "target", "answer", "ok"} for r in rw["rows"])
        row = next(r for r in rw["rows"] if r["src"] == "chain")
        assert (row["kind"], row["test"], row["q"], row["answer"], row["ok"]) == ("twohop", 0, "In which place does Gliker's mentor live?", "The answer is Kelmira.", True)
        assert sorted(r["q"] for r in rw["rows"] if r["src"] == "card" and r["kind"] == "forward" and r["test"] == 0) == sorted(sampled) and not any("dead card" in r["q"] for r in rw["rows"])
        assert [r["seen"] for r in rw["rows"] if r["src"] == "reword" and r["kind"] == "forward" and r["test"] == 0] == [False, True, False]
        # the variety measure by hand: texts ["a b c", "a b c", "x y"] -> pairs (1.0, 0, 0)
        assert reword_variety([mk(("a", "b"), "A", "B", ["a b c", "a b c"], [("x y", "B")])]) == {"items": 1, "mean_jaccard": 1 / 3, "near_dup_share": 1 / 3, "cap": 40, "near_dup_at": 0.8}
        assert reword_variety([mk(("a", "b"), "A", "B", ["only one"], [])])["items"] == 0 and reword_variety([mk(("a", "b"), "A", "B", [f"w{i} z" for i in range(50)], [])])["items"] == 1
        vt = [x for it_ in (k0, k1, k2) for x in [[*it_.para, *(q for q, _ in it_.qa)][:40]]]
        pj = [[jaccard(a_, b_) for i, a_ in enumerate(ts_) for b_ in ts_[i + 1:]] for ts_ in vt]
        assert rw["variety"]["items"] == 3 and ap_(rw["variety"]["mean_jaccard"], sum(sum(p) / len(p) for p in pj) / 3) and ap_(rw["variety"]["near_dup_share"], sum(sum(x >= 0.8 for x in p) / len(p) for p in pj) / 3)
        # no Brain (arms a0 / ad / af): the new-wording part only, the same numbers
        rw0 = reword_eval(Lf, mdl, week, None, spec, 16, 1)
        assert rw0["new_wording"] == rw["new_wording"] and rw0["per_test"] == rw["per_test"] and not ({"cards", "seen", "variety", "cramming_gap_pts"} & set(rw0)) and len(rw0["rows"]) == 14
        assert json.loads(json.dumps(rw))["per_test"]["twohop"] == {"0": True, "1": False}  # JSON-serializable (keys become strings)
        # a smoke-like week: nothing of the file is this week's -> everything skipped, nothing asked, no crash
        wk0 = {"tests": {k: [dict(t, q=t["q"] + " (another week)") for t in v] for k, v in smoke_week()["tests"].items()}}
        rws = reword_eval(Lf, mdl, wk0, brain, spec, 16, 1)
        assert rws["mapped"] == {"forward": 0, "reverse": 0, "twohop": 0} and rws["skipped_unmapped"] == {"forward": 3, "reverse": 2, "twohop": 2} and rws["new_wording"]["both"]["n"] == 0 and rws["rows"] == [] and rws["per_test"] == {"forward": {}, "reverse": {}, "twohop": {}}
        out["reword"] = {"new_wording_both": nw["both"], "cards": rw["cards"]["mean_acc"], "gap_pts": rw["cramming_gap_pts"], "seen": sn["seen"]}

        # ---- (vi) the flag checks
        ns = lambda **kw: Namespace(**{"arm": "ab_ob_b4_nb", "text_scale": None, "dream_vary": "off", **kw})  # noqa: E731
        assert add15_error(ns(), None) is None and add15_error(ns(), 8.0) is None and add15_error(ns(text_scale=4.0), 8.0) is None and add15_error(ns(text_scale=0.25), 1.0) is None
        assert "--budget-scale" in add15_error(ns(text_scale=4.0), None) and "positive" in add15_error(ns(text_scale=0.0), 8.0) and "positive" in add15_error(ns(text_scale=-1.0), 8.0) and "positive" in add15_error(ns(text_scale=float("nan")), 8.0)
        assert add15_error(ns(dream_vary="mix"), 8.0) is None and add15_error(ns(dream_vary="plain", arm="ab_ob"), None) is None and add15_error(ns(dream_vary="mix", text_scale=4.0), 8.0) is None
        for arm in ("ab_ob_twist", "ab_ob_win", "ab_ob_winp"):
            assert "twist" in add15_error(ns(dream_vary="mix", arm=arm), 8.0)
        for arm in ("ab", "af", "a0", "ad", "ab_norem"):
            assert "open-book" in add15_error(ns(dream_vary="plain", arm=arm), 8.0)
        assert add15_error(Namespace(arm="ab_ob"), None) is None  # an args without the flags
        out["flag_checks"] = True

        # ---- (vii) make_reworded's helpers are sleepb's; the data file passes the PREREG's checks
        sys.path.insert(0, str(HERE))
        import make_reworded as mr
        for x in ("Where was Vebribon's home?", "Who ’s there? It's Ramein’s", "  Mixed   CASE  text  ", "A b c", ""):
            assert mr.norm(x) == norm(x) and mr.tokens(x) == tokens(x) and mr.pat("Vebribon").pattern == pat("Vebribon").pattern
        assert all(abs(mr.jaccard(a_, b_) - jaccard(a_, b_)) < 1e-12 for a_, b_ in (("a b c", "a b d"), ("x", "y"), ("", ""), ("Where is Ramein's home?", "Where is home for Ramein?")))
        fp, wp = HERE / "data" / "week2_reworded.json", HERE / "data" / "week2.json"
        if fp.exists() and wp.exists():
            sp, wk = json.loads(fp.read_text()), json.loads(wp.read_text())
            assert sp["source_sha256"] == hashlib.sha256(wp.read_bytes()).hexdigest() and set(sp["tests"]) == {"forward", "reverse", "twohop"} and sp["model"] and sp["created"]
            mp_, sk = reword_map(wk, sp)
            assert not sk and Counter(k for k, *_ in mp_) == {"forward": 200, "reverse": 200, "twohop": 78}, (sk, Counter(k for k, *_ in mp_))
            lk = {norm(x) for x in wk["test_strings_norm"]} | {norm(t["q"]) for k in wk["tests"] for t in wk["tests"][k]}
            tt = {(t["kind"], t["test_index"]): t for t in mr.build_tests(wk)}
            nk = Counter()
            for kind, i, t, e in mp_:
                assert 1 <= len(e["rewordings"]) <= 3 and len({norm(x) for x in e["rewordings"]}) == len(e["rewordings"]) and (kind == "twohop" or t["class"] in ("C2", "C4"))
                assert all(mr.check(x, tt[(kind, i)], lk) is None for x in e["rewordings"]), (kind, i, e["rewordings"])
                nk[len(e["rewordings"])] += 1
            out["data_file"] = {"entries": len(mp_), "kept_per_test": dict(sorted(nk.items())), "sha256": hashlib.sha256(fp.read_bytes()).hexdigest()[:16]}
        else:
            out["data_file"] = "skipped (data/week2_reworded.json not there)"
        return out
    finally:
        torch.set_rng_state(rng0)


def selftest_add17():
    """Addendum 17 on a stub of `datasets` (no download): the gate's ARC slice is the first n of the 570 validation rows, 100 with no n (as before), all 570 at n = 570, and the smoke fixture whatever n is."""
    import types
    rows = [{"question": f"q{i}", "choices": {"text": ["x", "y", "z"], "label": ["A", "B", "C"]}, "answerKey": "ABC"[i % 3]} for i in range(ARC_VAL_ROWS)]
    asked, had = [], sys.modules.get("datasets")
    sys.modules["datasets"] = types.SimpleNamespace(load_dataset=lambda *a, **kw: (asked.append((a, kw)), rows)[1])
    try:
        d, a570, a1 = load_arc_val(False), load_arc_val(False, 570), load_arc_val(False, 1)
        assert len(d) == 100 and [r["question"] for r in d] == [f"q{i}" for i in range(100)] and d == load_arc_val(False, 100), "default slice is the first 100"
        assert len(a570) == 570 and a570[:100] == d and a570[-1]["question"] == "q569" and len(a1) == 1 and a1 == d[:1]
        assert d[4]["answer"] == 1 and set(d[0]) == {"question", "choices", "answer"}
        assert all(a == ("allenai/ai2_arc", "ARC-Easy") and kw == {"split": "validation"} for a, kw in asked)
        n_asked = len(asked)
        assert load_arc_val(True) is ARC_SMOKE and load_arc_val(True, 570) is ARC_SMOKE and len(asked) == n_asked, "smoke: the fixture, no dataset call"
    finally:
        if had is None:
            del sys.modules["datasets"]
        else:
            sys.modules["datasets"] = had
    return {"default_n": len(d), "n570": len(a570), "n1": len(a1), "val_rows": ARC_VAL_ROWS}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=ARMS)
    ap.add_argument("--week", help="week1.json; with --smoke and no --week the built-in 2-day fixture is used")
    ap.add_argument("--out")
    ap.add_argument("--model", default="Qwen/Qwen3.5-2B")
    ap.add_argument("--revision", default=None, help="model repo revision (K2-Horizon: the pinned commit sha); default: the repo's main")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="run the SHY refactor, delta, local-plasticity, weighted-loss, rotation, time-budget, stale-filter, addendum-7 / -8 / -9 / -10 arm, K2 names-pass think-path and K2 REM chain-mode / unit / step-plan (addendum 14) and the text-scale / dream-vary / reword (addendum 15) unit checks and exit")
    ap.add_argument("--bench-dtype", choices=["bf16", "fp16"], default="bf16", help="--bench-train only: fp16 for a T4 (no bf16)")
    ap.add_argument("--bench-train", action="store_true", help="time Trainer.step OLD vs NEW (FAST off / on) on a synthetic batch at tok budgets 1024..8192, write --out/bench_train.json, print it and exit")
    ap.add_argument("--schedule", help="result_ab.json whose nights[i].steps become this arm's per-night steps (compute match)")
    ap.add_argument("--bsz", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--full-lr", type=float, default=2e-5, help="ab_ob_full / ab_ob_local: lr of the full-rank deltas (replaces --lr)")
    ap.add_argument("--full-lr-small", type=float, default=5e-6, help="ab_ob_full_s only: the gentler lr (replaces --lr; otherwise identical to ab_ob_full)")
    ap.add_argument("--local-k-frac", type=float, default=None, help="ab_ob_local: plastic delta entries per night as a fraction of all delta entries (default: as many as there are LoRA parameters)")
    ap.add_argument("--tag-batches", type=int, default=8, help="ab_ob_local: practice batches drawn each night to tag the plastic entries")
    ap.add_argument("--budget-scale", type=float, default=None, help="work scale s (steps, dreams per item, item cap, REM chains, gist dreams all x s); default 1 (B2_ARMS ab_ob_b2 / win / winp / tag2 / bridge: 2; B4_ARMS ab_ob_b4 / b4_names / b4_bridge / b4_nb / b4_nb_x4: 4)")
    ap.add_argument("--night-budget-s", type=float, default=None, help="seconds per night: s = clip(B / R, 0.25, 4) from a benchmark at the start of each night (ignored when --budget-scale or a b2 / b4 arm pins s)")
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--lora-shared", action="store_true", help="addendum 12 (Qwen3.5/3.6 MoE): LoRA also on mlp.shared_expert.{gate,up,down}_proj, which train.LORA_TARGETS does not match")
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
    ap.add_argument("--rem-chain-mode", choices=REM_CHAIN_MODES, default="default", help="addendum 14 (bridge arms, not x4): how REM writes a two-step dream. default: bridge_prompt, Question + Answer, think block closed (as before); q: bridge_q_prompt, only the question "
                    "(the answer is the given far end); think / q_think (K2 only): the same two prompts with the high-effort think block open first (stage 1: at most 512 sampled tokens, stage 2: prompt + thinking + close tag)")
    ap.add_argument("--rem-dirs", choices=["alt", "both"], default="alt", help="addendum 14 (bridge arms, not x4): alt: one direction per pair, alternating with the pair index (as before); both: each pair is two units (one per direction), tried every REM cycle until it has a kept dream, then never again")
    ap.add_argument("--rem-tries", type=int, default=1, help="addendum 14, with --rem-dirs both: samples per unit and cycle (unit-major); only the first sample that passes every check is kept")
    ap.add_argument("--rem-steps-mult", type=float, default=1.0, help="addendum 14: each cycle's REM steps x this (rounded); the night's cosine schedule covers the new total. 1.0 = as before")
    ap.add_argument("--card-stats", action="store_true", help="sleep efficiency, report-only (training unchanged): per night, the share of practice examples the model already answered right before their step "
                    "(every target but the final eos is the argmax), by kind and by quarter of the night, from the logits the loss already computes -> nights[i].cards")
    ap.add_argument("--skip-known", type=float, default=None, help="sleep efficiency: a card (NREM paraphrase or Q&A, REM-pool dream) that was right at its last closed-book or text practice is kept with this "
                    "probability, else drawn again (at most SKIP_TRIES draws); a wrong morning probe marks the item's cards not known; implies --card-stats. Default: off")
    ap.add_argument("--lora-plus", type=float, default=None, help="sleep efficiency (LoRA+, Hayou et al. 2024): the lora_B matrices step at lr x this. Default: off (one lr)")
    ap.add_argument("--ob-share", type=float, default=0.5, help="OB_ARMS: share of practice Q&A examples that are open-book (the diary-test prompt). 0.5 = as before")
    ap.add_argument("--lr-sched", choices=["cosine", "wsd"], default="cosine", help="each night's lr schedule: cosine from --lr to 0 (as before), or wsd: --lr, then linear to 0 over the last WSD_DECAY of the night's steps")
    ap.add_argument("--rem-views", type=float, default=None, help="sleep efficiency: each REM cycle gives the REM pool about this x pool x (cycle's REM steps / night's REM steps) practice slots (at most round(0.7 bsz) a step), "
                    "so a dream in the pool all night gets about this many practices (one made in a later cycle only its share of the REM steps left); unused slots go to NREM cards. Default: off (always round(0.7 bsz) a step)")
    ap.add_argument("--gate-arc-n", type=int, default=100, help=f"addendum 17: the pre-sleep base score and the nightly morning gate use the first N ARC-Easy validation questions (1..{ARC_VAL_ROWS}); 100 = as before. The smoke fixture is unchanged")
    ap.add_argument("--force-revert", type=int, default=0, help="test hook: revert this night (smoke sets 2)")
    ap.add_argument("--smoke-correct", type=float, default=0.8)
    ap.add_argument("--arc-base", action="store_true", help="addendum 11: score the ARC-Easy questions of the final score on the base model (adapter off) before night 1 -> result['arc_easy_base']")
    ap.add_argument("--q4-base", action="store_true", help="Mac study: replace every Linear / Embedding weight of the frozen base by an MLX-style affine fake-quantized copy (before LoRA)")
    ap.add_argument("--q4-group", type=int, default=64, help="--q4-base: group size along the input dim")
    ap.add_argument("--q4-bits", type=int, default=4, help="--q4-base: bits per weight (levels = 2**bits - 1)")
    ap.add_argument("--q4-mlx-moe", action="store_true", help="--q4-base, Qwen3.5/3.6 MoE: also quantize the fused 3-D expert tensors and the router Parameter, with 8 bits for every mlp.gate and mlp.shared_expert_gate "
                    "(the mlx-community/Qwen3.6-35B-A3B-4bit recipe)")
    ap.add_argument("--freeze-lora", action="store_true", help="addendum 13b (training delta arms only): every Trainer re-freezes the LoRA, so only the fp32 delta trains")
    ap.add_argument("--think-eval", action="store_true", help="addendum 14 (K2 only, report-only): after the final scoring, ask the two-hop and the C2 + C4 forward questions again with the high-effort think block open (at most 512 greedy tokens, then the answer), weights only -> result['think_eval']")
    ap.add_argument("--text-scale", type=float, default=None, help="addendum 15 (needs --budget-scale): the generation knobs (k, item cap, REM chain cap, REM gist cap, dream token budget) are x this instead of x the work scale; the training steps stay at --budget-scale. "
                    "Default: the knobs follow --budget-scale, as before")
    ap.add_argument("--dream-vary", choices=["off", "mix", "plain"], default="off", help="addendum 15 (open-book arms, not the twist arms): nrem_prompt asks for ceil(k/4) paraphrases (and k question cards), then the base model writes ceil(k/4) texts in each of 3 styles "
                    "(story, note in Sam's voice, and weird dream scenes (mix) or plain2 ordinary paraphrases (plain)), kept under twist's checks and added to the item's paraphrases. off: as before")
    ap.add_argument("--reword", default=None, metavar="FILE", help="addendum 15 (report-only): after ALL scoring and after the final result JSON is written, score the new wordings in FILE (make_reworded.py's data/week2_reworded.json) weights-only, with the exact-card, seen and "
                    "variety measures -> result['reword'] (the file is rewritten); an error there goes to result['reword_error'] and costs nothing else")
    ap.add_argument("--q4-eval", action="store_true", help="addendum 13 (delta arms only, not with --q4-base): after the final scoring, also score the final model under F0 / Q0 / Q / Qf (--q4-group / --q4-bits) -> result['q4_eval']")
    args = ap.parse_args()
    globals()["TOK_BUDGET"] = args.tok_budget
    if args.selftest:
        print(json.dumps(selftest_shy()))
        print(json.dumps({"delta": selftest_delta()}))
        print(json.dumps({"local": {**selftest_elem(), **selftest_local()}}))
        print(json.dumps({"weighted": selftest_weighted()}))
        print(json.dumps({"rot": selftest_rot()}))
        print(json.dumps({"fast": selftest_fast()}))
        print(json.dumps({"cards": selftest_cards()}))
        print(json.dumps({"budget": selftest_budget()}))
        print(json.dumps({"stale": selftest_stale()}))
        print(json.dumps({"arms7": selftest_arms7()}))
        print(json.dumps({"arms8": selftest_arms8()}))
        print(json.dumps({"arms9": selftest_arms9()}))
        print(json.dumps({"arms10": selftest_arms10()}))
        print(json.dumps({"q4": selftest_q4()}))
        print(json.dumps({"q4_eval": selftest_q4_eval()}))
        print(json.dumps({"names_k2": selftest_names_k2()}))
        print(json.dumps({"rem_k2": selftest_rem_k2()}))
        print(json.dumps({"k2": selftest_k2()}))
        print(json.dumps({"add15": selftest_add15()}))
        print(json.dumps({"add17": selftest_add17()}))
        return
    if args.bench_train:
        if not args.out:
            ap.error("--out is required")
        from peft import LoraConfig, get_peft_model
        torch.manual_seed(args.seed)
        device = torch.device("cuda" if torch.cuda.is_available() and not args.smoke else "cpu")
        lm, tok = load_model(args, device, {"bf16": torch.bfloat16, "fp16": torch.float16}[args.bench_dtype] if device.type == "cuda" else torch.float32)
        pm = get_peft_model(lm, LoraConfig(r=args.rank, lora_alpha=args.alpha, lora_dropout=0.0, target_modules=LORA_TARGETS, bias="none"))
        res = bench_train(args, Lang(tok, args.smoke, device, k2=lm.config.model_type == K2_TYPE), pm)
        Path(args.out).mkdir(parents=True, exist_ok=True)
        (Path(args.out) / "bench_train.json").write_text(json.dumps(res, indent=1))
        print(json.dumps(res, indent=1))
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
    err = add15_error(args, args.budget_scale)  # (before default_scale: --text-scale needs a --budget-scale that was given)
    if err:
        ap.error(err)
    reword_spec = None
    if args.reword:  # addendum 15: a missing or broken file stops the run now, not after the night's work
        try:
            reword_spec = json.loads(Path(args.reword).read_text())
            assert all(isinstance(e, dict) and isinstance(e["rewordings"], list) and {"q_src", "target", "test_index"} <= set(e) for k in ("forward", "reverse", "twohop") for e in reword_spec["tests"].get(k, []))
        except Exception as e:
            ap.error(f"--reword {args.reword}: not a make_reworded.py file ({e!r})")
    args.budget_scale = default_scale(args.arm, args.budget_scale)  # ab_ob with 2x (B2_ARMS) or 4x (ab_ob_b4) the night's work, unless --budget-scale says otherwise
    if args.budget_scale is not None and not args.budget_scale > 0:
        ap.error("--budget-scale must be positive")
    if args.night_budget_s is not None and not args.night_budget_s > 0:
        ap.error("--night-budget-s must be positive")
    if (args.rem_chain_mode != "default" or args.rem_dirs != "alt") and (args.arm not in BRIDGE_ARMS or args.arm in TRIES_ARMS):
        ap.error(f"--rem-chain-mode / --rem-dirs are only for the bridge arms {tuple(a_ for a_ in BRIDGE_ARMS if a_ not in TRIES_ARMS)}")
    if args.rem_tries < 1 or (args.rem_tries > 1 and args.rem_dirs != "both"):
        ap.error("--rem-tries must be at least 1, and more than 1 needs --rem-dirs both (the x4 arm has its own X4_TRIES)")
    if not args.rem_steps_mult > 0:
        ap.error("--rem-steps-mult must be positive")
    if args.think_eval and args.arm == "ad":
        ap.error("--think-eval needs a weights-only score (not arm ad)")
    if (args.rem_chain_mode in ("think", "q_think") or args.think_eval) and not is_k2(args):
        ap.error("--rem-chain-mode think / q_think and --think-eval are for a K2-Horizon model (--model IFM/K2-Horizon-3.7B)")
    if args.q4_mlx_moe and not args.q4_base:
        ap.error("--q4-mlx-moe needs --q4-base")
    if args.freeze_lora and args.arm not in TRAIN_DELTA_ARMS:
        ap.error(f"--freeze-lora is only for the training delta arms {TRAIN_DELTA_ARMS}")
    if args.q4_eval and args.arm not in DELTA_ARMS:
        ap.error(f"--q4-eval is only for the delta arms {DELTA_ARMS}")
    if args.q4_eval and args.q4_base:
        ap.error("--q4-eval cannot be combined with --q4-base")
    if args.q4_eval and (args.q4_group < 1 or args.q4_bits < 1):
        ap.error("--q4-group and --q4-bits must be positive")
    if (args.card_stats or args.skip_known is not None) and args.arm in ("a0", "ad", "af"):
        ap.error("--card-stats / --skip-known need a sleeping Brain arm (not a0, ad or af)")
    if args.skip_known is not None and not 0 < args.skip_known < 1:
        ap.error("--skip-known is the keep probability of a known card, in (0, 1)")
    if args.lora_plus is not None and (not args.lora_plus > 0 or args.arm in ("a0", "ad", *TRAIN_DELTA_ARMS)):
        ap.error(f"--lora-plus must be positive, for an arm whose LoRA trains (not a0, ad or {TRAIN_DELTA_ARMS})")
    if not 0 <= args.ob_share <= 1 or (args.ob_share != 0.5 and args.arm not in OB_ARMS):
        ap.error("--ob-share must be in [0, 1], and only the open-book arms (OB_ARMS) use it")
    if args.rem_views is not None and (not args.rem_views > 0 or args.arm in ("a0", "ad", "af", "ab_norem")):
        ap.error("--rem-views must be positive, for a sleeping arm with REM (not a0, ad, af or ab_norem)")
    if not 1 <= args.gate_arc_n <= ARC_VAL_ROWS:
        ap.error(f"--gate-arc-n must be between 1 and {ARC_VAL_ROWS} (the ARC-Easy validation split has {ARC_VAL_ROWS} questions)")
    if args.rem_views is not None and args.rem_steps_mult != 1.0:
        ap.error("--rem-views and --rem-steps-mult != 1 do not combine: views fixes a dream's practices a night, so the extra REM steps would only be NREM steps")
    if args.budget_scale is not None and args.night_budget_s is not None:
        log(f"[budget] scale pinned at {args.budget_scale}: --night-budget-s {args.night_budget_s} is not used")
    t0 = time.time()
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.smoke else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    lm, tok = load_model(args, device, dtype)
    q4 = None
    if args.q4_base:
        if args.q4_group < 1 or args.q4_bits < 1:
            ap.error("--q4-group and --q4-bits must be positive")
        q4 = q4_apply(lm, args.q4_group, args.q4_bits, *((Q4_MLX_MOE_BITS, Q4_MLX_MOE_PARAMS) if args.q4_mlx_moe else ()))
        log(f"[q4] fake-quantized base: {q4['tensors']} tensors quantized, {q4['skipped']} skipped, {q4['params']:,} params, mean rel Frobenius error {q4['mean_rel_fro']} (group {q4['group']}, bits {q4['bits']})"
            + (f", by bits {q4['by_bits']}" if "by_bits" in q4 else ""))
    L = Lang(tok, args.smoke, device, k2=lm.config.model_type == K2_TYPE)
    assert L.k2 or not (args.rem_chain_mode in ("think", "q_think") or args.think_eval), "--rem-chain-mode think / q_think and --think-eval need a K2-Horizon model"
    week = json.loads(Path(args.week).read_text()) if args.week else smoke_week()
    check_week(week)
    diary = Diary(week)
    if L.k2:  # once: what a K2 prompt looks like and how its end tokenizes (the specials must be single ids)
        tp = tag_prompt(L, diary.turns[0]["text"])
        log(f"[k2] tagger prompt: {tp!r}")
        log(f"[k2] last 10 token ids: {L.ids(tp)[-10:]} = {tok.convert_ids_to_tokens(L.ids(tp)[-10:])}; eos id {L.eos}")
        if args.arm in NAMES_ARMS:  # addendum 11b / 11c: the names pass's think-open prompt (stage 1, K2_NAMES_EFFORT) and its stop ids
            npk = names_prompt(L, diary.turns[0]["text"], "A", "B", think=True, effort=K2_NAMES_EFFORT)
            log(f"[k2] names prompt tail (stage 1, block open, {K2_NAMES_EFFORT} effort): {npk[-60:]!r}; stops at ids {L.think_eos(K2_NAMES_EFFORT)} ({NAMES_THINK_MAX} tokens max)")
    leak = {norm(x) for x in week.get("test_strings_norm", [])} | {norm(t["q"]) for k in KINDS for t in week["tests"][k]}
    days = sorted({t["day"] for t in diary.turns})
    sched = None
    if args.schedule:
        sched = [n["steps"] for n in json.loads(Path(args.schedule).read_text())["nights"]]
        log(f"[schedule] {sched}")
    OFF = {"budget_scale": None, "night_budget_s": None, "revision": None, "arc_base": False, "q4_base": False, "q4_group": 64, "q4_bits": 4, "q4_mlx_moe": False, "q4_eval": False, "freeze_lora": False,
           "rem_chain_mode": "default", "rem_dirs": "alt", "rem_tries": 1, "rem_steps_mult": 1.0, "think_eval": False, "text_scale": None, "dream_vary": "off", "reword": None,
           "card_stats": False, "skip_known": None, "lora_plus": None, "ob_share": 0.5, "lr_sched": "cosine", "rem_views": None, "gate_arc_n": 100}  # options at their default are left out of result["args"] (older result files keep their keys)
    result = {"arm": args.arm, "model": args.model, "smoke": args.smoke, "args": {k: v for k, v in vars(args).items() if k not in ("week", "out", "schedule") and not (k in OFF and v == OFF[k])},
              "week": args.week, "n_user_turns": len(diary.turns), "days": days, "schedule": sched, "partial": True, **({"q4_base": q4} if q4 else {})}

    def dump(final, atomic=False):  # atomic (the --reword rewrite): the text is built first and replaces the file in one step, so a failure leaves the file that is on disk as it was
        result["partial"] = not final
        p = out / (f"result_{args.arm}.json" if final else f"result_{args.arm}.partial.json")
        txt = json.dumps(result, indent=1, default=lambda o: sorted(o) if isinstance(o, (set, frozenset)) else str(o))
        if atomic:
            tmp = p.with_name(p.name + ".tmp")
            tmp.write_text(txt)
            os.replace(tmp, p)
        else:
            p.write_text(txt)
        if final and (out / f"result_{args.arm}.partial.json").exists():
            (out / f"result_{args.arm}.partial.json").unlink()

    model, brain, pm = lm, None, None
    if args.arm not in ("a0", "ad"):
        from peft import LoraConfig, get_peft_model
        tm = f"(?:{LORA_TARGETS})|(?:{SHARED_RE})" if args.lora_shared else LORA_TARGETS  # addendum 12: + the MoE shared expert (its only dense MLP)
        pm = get_peft_model(lm, LoraConfig(r=args.rank, lora_alpha=args.alpha, lora_dropout=0.0, target_modules=tm, bias="none"))
        if args.lora_shared or getattr(lm.config, "num_experts", 0):
            from peft.tuners.lora import LoraLayer
            mm = [n.removeprefix("base_model.model.") for n, m in pm.named_modules() if isinstance(m, LoraLayer)]
            log(f"[lora] matched {len(mm)} modules ({sum('shared_expert' in n for n in mm)} shared-expert), trainable {sum(p.numel() for p in pm.parameters() if p.requires_grad):,}")
            assert not args.lora_shared or any("shared_expert" in n for n in mm), "--lora-shared matched no shared-expert module"
        if L.k2:
            from peft.tuners.lora import LoraLayer
            mm = [n.removeprefix("base_model.model.") for n, m in pm.named_modules() if isinstance(m, LoraLayer)]
            log(f"[k2] LoRA matched {len(mm)} modules: {mm if len(mm) <= 40 else mm[:7] + ['...']}")
            assert getattr(lm.config, "num_experts", 0) or len(mm) == 7 * lm.config.num_hidden_layers, "LORA_TARGETS should match q/k/v/o + gate/up/down in every layer of a dense K2"
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
        arc_val = load_arc_val(args.smoke, args.gate_arc_n)
        with pm.disable_adapter():
            arc_base = score_arc(L, pm, arc_val, bs=max(args.gen_bs // 2, 1))["acc"]
        result["arc_val_base"] = arc_base
        log(f"[base] ARC-Easy validation({args.gate_arc_n}) {arc_base:.3f}")
        if args.arc_base:  # addendum 11: the same questions as the final arc_easy score, on the base (adapter off), before night 1
            try:
                with pm.disable_adapter():
                    result["arc_easy_base"] = score_arc(L, pm, load_arc(args.smoke), bs=max(args.gen_bs // 2, 1))
                log(f"[base] ARC-Easy acc {result['arc_easy_base']['acc']:.3f} (n={result['arc_easy_base']['n']})")
            except Exception as e:  # datasets missing / offline
                result["arc_easy_base"] = {"error": repr(e)}
                log(f"[base] ARC-Easy FAILED: {e!r}")
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
    if args.think_eval:  # addendum 14 (K2, report-only): the two-hop and C2 + C4 forward questions again, with thinking; the scores above are in the partial file before and after
        te = result["think_eval"] = {}
        dump(False)
        try:
            te.update(think_eval(L, model, week, args.gen_bs, min(THINK_EVAL_MAX, 24) if args.smoke else THINK_EVAL_MAX))
            log("[think-eval] " + "; ".join(f"{k} {v['acc']} of {v['n']} (anywhere in the thinking too: {v['acc_any']}), {v['think_tokens_mean']} thinking tokens, {v['capped']} capped" for k, v in te.items()))
        except Exception as e:  # the main scores are already written; the final result still is
            import traceback
            te["error"] = {"error": repr(e)[:300], "trace": traceback.format_exc()[-3000:]}
            log(f"[think-eval] FAILED: {e!r}")
        dump(False)
    if args.q4_eval:  # addendum 13: after everything else; the final scores above are already in the partial file if this fails
        qe = result["q4_eval"] = {}
        dump(False)
        try:
            arc_rows = load_arc(args.smoke)
        except Exception as e:  # datasets missing / offline
            arc_rows, arc_err = None, {"error": repr(e)}

        def q4_score(cond):  # exactly the final "weights" scoring and the final ARC call
            sc = score_week(L, model, week, diary, "weights", args.gen_bs, dreamed, full)
            return {"scores": sc, "arc_easy": score_arc(L, model, arc_rows, bs=max(args.gen_bs // 2, 1)) if arc_rows else arc_err}
        try:
            q4_eval(lm, args.q4_group, args.q4_bits, q4_score, log, lambda: dump(False), qe)
        except Exception as e:  # the final result is still written below
            import traceback
            qe["error"] = {"error": repr(e)[:300], "trace": traceback.format_exc()[-3000:]}
            log(f"[q4eval] FAILED: {e!r}")
    result["wall_seconds"] = time.time() - t0
    dump(True)
    log(f"[done] {args.arm} wall {result['wall_seconds']:.0f}s -> {out}/result_{args.arm}.json")
    if reword_spec is not None:  # addendum 15 (report-only): AFTER all the scoring and AFTER the final result is on disk; whatever happens here, that file stays
        try:
            rw = result["reword"] = reword_eval(L, model, week, brain, reword_spec, args.gen_bs, args.seed, log)
            rw["file"], rw["file_sha256"] = args.reword, hashlib.sha256(Path(args.reword).read_bytes()).hexdigest()
            rw["week_sha256_matches_file"] = (reword_spec.get("source_sha256") == hashlib.sha256(Path(args.week).read_bytes()).hexdigest()) if args.week else None
            nw = rw["new_wording"]
            log(f"[reword] mapped {rw['mapped']} skipped {rw['skipped_unmapped']}; new-wording recall both {nw['both']['recall']} (share {nw['both']['share']}, n {nw['both']['n']}) forward {nw['forward']['recall']} reverse {nw['reverse']['recall']} "
                f"twohop {nw['twohop']['recall']} (n {nw['twohop']['n']}); cards {rw.get('cards')} gap {rw.get('cramming_gap_pts')} pts; seen {(rw.get('seen') or {}).get('seen')} of {(rw.get('seen') or {}).get('rewordings')}; variety {rw.get('variety')}; {rw['seconds']}s")
        except Exception as e:
            import traceback
            result.pop("reword", None)
            result["reword_error"] = {"error": repr(e)[:300], "trace": traceback.format_exc()[-3000:]}
            log(f"[reword] FAILED: {e!r}")
        try:
            dump(True, atomic=True)
        except Exception as e:  # the file written above is still the final result
            log(f"[reword] could not rewrite the result file: {e!r}")
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
