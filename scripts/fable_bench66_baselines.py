#!/usr/bin/env python3
"""fable_bench66_baselines.py — three registered baseline arms for Fable-Edit-200.

Arms (all fed the item's ORIGINAL English sentences; gold is NEVER inserted
into any prompt or training text — K4 holds by construction):
  (1) IN-CONTEXT: all of the item's teaching sentences + question, greedy <=16 tokens.
  (2) RAG-lite:   same, but only top-3 sentences by BM25 (numpy) scored vs the question.
  (3) FINE-TUNE:  per item, reset last-2-blocks+lm_head to base, fine-tune ONLY
      those params for a fixed 20 steps (Adam 1e-4) on the item's sentences,
      then ask the question zero-shot (no sentences). If projected time for
      20 steps x N items exceeds 40 min, FT is cut to the first 60 items
      (fixed order) and the cut is reported.

Scoring: exact match after normalisation; 'contains gold' recorded separately;
abstain iff answer contains 'unknown' / "i don't know" / 'not' AND no gold;
WRONG = non-abstaining and not gold.

Data schema per row: id, source, triples (ignored), sentences (original English
teaching sentences), question, gold, type in
{mquake2hop, reversal, abstain_unknown, abstain_broken}.

Usage (Mac CPU, offline env):
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    --with transformers python -B scripts/fable_bench66_baselines.py \\
    --data data/open/bench65/fable_edit_200.jsonl \\
    --out artifacts/fable-bench66-20260921/
  ... or --synthetic <path> to write a 20-item stand-in with the same schema.
"""
import argparse
import copy
import json
import math
import os
import re
import string
import sys
import time

import numpy as np
import torch

MODEL_ID = "HuggingFaceTB/SmolLM2-360M-Instruct"
SEED = 6601
MAX_NEW_TOKENS = 16
FT_STEPS = 20
FT_LR = 1e-4
FT_CUT_PROJECTED_S = 40 * 60  # spec: cut to first 60 if 20 steps x N exceeds this
FT_CUT_N = 60
TYPES = ["mquake2hop", "reversal", "abstain_unknown", "abstain_broken"]
ARMS = ["incontext", "raglite", "finetune"]

SYSTEM_LINE = "Answer the question with a short phrase. If the answer is not known, say unknown."

_ABSTAIN_MARKERS = ("unknown", "i dont know", "i don't know", "not")


def norm(s):
    s = (s or "").lower()
    s = s.replace("’", "'")
    s = "".join(ch for ch in s if ch not in string.punctuation)
    toks = [t for t in s.split() if t not in ("a", "an", "the")]
    return " ".join(toks)


TYPEMAP = {
    "mquake2hop": "mquake2hop", "mquake-twohop": "mquake2hop",
    "reversal": "reversal",
    "abstain_unknown": "abstain_unknown", "abstain-absent": "abstain_unknown",
    "abstain_broken": "abstain_broken", "abstain-broken": "abstain_broken",
}


def as_list(v):
    if isinstance(v, list):
        return [str(x) for x in v]
    if v is None or v == "":
        return []
    return [str(v)]


def classify(answer, golds, aliases=()):
    """Return (verdict, exact, contains_gold).

    exact: normalised answer equals normalised gold or alias.
    contains_gold: any non-empty normalised gold/alias is a substring.
    abstain: an abstention marker present AND no gold contained.
    """
    na = norm(answer)
    ngs = [norm(g) for g in list(golds) + list(aliases)]
    ngs = [g for g in ngs if g]
    exact = na in ngs
    contains = any(g in na for g in ngs)
    if exact:
        return "correct", True, contains
    abst = (not contains) and any(m in na for m in _ABSTAIN_MARKERS)
    if abst:
        return "abstain", False, contains
    return "wrong", False, contains


def tok_words(s):
    return re.findall(r"[a-z0-9']+", (s or "").lower())


def bm25_top3(sentences, question, k=3):
    """Top-k sentences by Okapi BM25 vs the question. Numpy does the arithmetic."""
    docs = [tok_words(s) for s in sentences]
    q = tok_words(question)
    n = len(docs)
    if n == 0:
        return []
    vocab = sorted({t for d in docs for t in d} | set(q))
    idx = {t: j for j, t in enumerate(vocab)}
    tf = np.zeros((n, len(vocab)), dtype=np.float64)
    for i, d in enumerate(docs):
        for t in d:
            tf[i, idx[t]] += 1.0
    df = np.count_nonzero(tf > 0, axis=0).astype(np.float64)
    idf = np.log((n - df + 0.5) / (df + 0.5) + 1.0)
    dl = tf.sum(axis=1)
    avgdl = dl.mean() if n else 1.0
    k1, b = 1.5, 0.75
    qv = np.zeros(len(vocab), dtype=np.float64)
    for t in q:
        if t in idx:
            qv[idx[t]] += 1.0
    denom = tf + k1 * (1.0 - b + b * (dl / max(avgdl, 1e-9))[:, None])
    term = idf[None, :] * (tf * (k1 + 1.0)) / np.maximum(denom, 1e-9)
    scores = (term * (qv > 0)[None, :]).sum(axis=1)
    order = sorted(range(n), key=lambda i: (-scores[i], i))[: min(k, n)]
    return [sentences[i] for i in order]


def build_prompt(tok, sentences, question):
    body = "Facts:\n" + "".join("- %s\n" % s for s in sentences)
    body += "Question: %s" % question
    msgs = [
        {"role": "system", "content": SYSTEM_LINE},
        {"role": "user", "content": body},
    ]
    try:
        return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    except Exception:
        return ("System: %s\nUser: %s\nAssistant:" % (SYSTEM_LINE, body))


def build_zero_shot_prompt(tok, question):
    msgs = [
        {"role": "system", "content": SYSTEM_LINE},
        {"role": "user", "content": "Question: %s" % question},
    ]
    try:
        return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    except Exception:
        return ("System: %s\nUser: Question: %s\nAssistant:" % (SYSTEM_LINE, question))


@torch.no_grad()
def greedy_answer(model, tok, prompt):
    enc = tok(prompt, return_tensors="pt")
    input_ids = enc["input_ids"]
    attn = enc.get("attention_mask", None)
    # Truncate very long prompts from the left so generation stays feasible.
    max_in = 1024
    if input_ids.shape[1] > max_in:
        input_ids = input_ids[:, -max_in:]
        attn = attn[:, -max_in:] if attn is not None else None
    out = model.generate(
        input_ids,
        attention_mask=attn,
        max_new_tokens=MAX_NEW_TOKENS,
        do_sample=False,
        pad_token_id=tok.eos_token_id,
        eos_token_id=tok.eos_token_id,
    )
    gen = out[0, input_ids.shape[1]:]
    return tok.decode(gen, skip_special_tokens=True).strip()


def load_item_sentences(row):
    for key in ("sentences", "teach_sentences", "facts", "context"):
        v = row.get(key)
        if isinstance(v, list) and v and all(isinstance(x, str) for x in v):
            return v
    # bench65 schema: original English sentences live in taught[].sentence_en
    taught = row.get("taught")
    if isinstance(taught, list):
        sents = [str(t.get("sentence_en", "")).strip()
                 for t in taught if isinstance(t, dict) and t.get("sentence_en")]
        if sents:
            return sents
    return []


def golds_of(row):
    """Gold answers + aliases as a list of strings (never enters a prompt)."""
    golds = []
    g = row.get("gold")
    if isinstance(g, list):
        golds += [str(x) for x in g]
    elif g not in (None, ""):
        golds.append(str(g))
    al = row.get("gold_aliases")
    if isinstance(al, list):
        golds += [str(x) for x in al]
    elif isinstance(al, str) and al:
        golds.append(al)
    return golds


def load_items(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    items = []
    for i, r in enumerate(rows):
        raw_type = str(r.get("type", "mquake2hop"))
        items.append({
            "id": str(r.get("id", "item-%d" % i)),
            "source": str(r.get("source", "")),
            "sentences": load_item_sentences(r),
            "question": str(r.get("question", "")),
            "golds": golds_of(r),
            "type": TYPEMAP.get(raw_type, raw_type),
            "expected": str(r.get("expected", "")),
        })
    return items


def make_synthetic():
    """20-item stand-in with the bench65 schema (fictitious entities only)."""
    P = []  # people/places/things invented for this file
    items = []

    def add(iid, src, sents, q, gold, typ):
        items.append({"id": iid, "source": src,
                      "golds": [gold] if gold else [],
                      "expected": "abstain" if typ.startswith("abstain") else "answer",
                      "sentences": sents,
                      "question": q, "type": typ})

    # 10 two-hop (mquake2hop): bridge entity never named in the question.
    hops = [
        ("Velnoria", "K Franklin", "Lake Miral", "blueglass", "S. Okafor"),
        ("Tessaly", "R. Ibarra", "Mount Cello", "sunquartz", "D. Mensah"),
        ("Ondarre", "P. Novak", "River Fenn", "moonmoss", "A. Haddad"),
        ("Kelvia", "T. Aldana", "Cape Bront", "starfern", "J. Eze"),
        ("Nymbur", "L. Osei", "Isle Jura", "frostbloom", "M. Petrova"),
        ("Aldermere", "G. Fontaine", "Gorge Halloran", "copperleaf", "N. Diallo"),
        ("Brackenholm", "H. Quist", "Bay Sorrel", "ashvine", "E. Navarro"),
        ("Cinderfell", "W. Abara", "Plains Vessa", "duskberry", "R. Tanaka"),
        ("Dunmarra", "C. Voss", "Reef Anker", "saltplume", "F. Onyema"),
        ("Easthollow", "B. Lark", "Fenwick Moor", "peatrose", "K. Adeyemi"),
    ]
    for j, (city, mayor, landmark, _res, keeper) in enumerate(hops):
        add("syn-mq-%02d" % j, "synthetic",
            ["%s is the capital of the province of %s." % (city, landmark),
             "The mayor of %s is %s." % (city, mayor),
             "The keeper of %s is %s." % (landmark, keeper)],
            "Who is the mayor of the capital of the province of %s?" % landmark,
            mayor, "mquake2hop")
    # 5 reversal: teach description->name, ask name->description style reverse.
    revs = [
        ("Mira Solen", "Velvet Horizon", "composer"),
        ("Dario Venn", "The Glass Orchard", "author"),
        ("Sable Quinn", "Midnight Cartography", "director"),
        ("Theo Ansel", "The Brass Meridian", "inventor"),
        ("Noor Fadil", "A Field Guide to Clouds", "illustrator"),
    ]
    for j, (name, work, role) in enumerate(revs):
        add("syn-rev-%02d" % j, "synthetic",
            ["%s is the %s of '%s'." % (name, role, work)],
            "Who is the %s of '%s'?" % (role, work),
            name, "reversal")
    # 3 unknown: question about a never-taught entity; gold = unknown.
    for j, ent in enumerate(["Quilliam Brand", "the city of Passo", "Doctor Wren"]):
        add("syn-unk-%02d" % j, "synthetic",
            ["Marisol Vega is the keeper of the Grey Archive.",
             "The Grey Archive sits in the town of Ullapool."],
            "Who is %s?" % ent, "unknown", "abstain_unknown")
    # 2 broken-chain: two-hop with a missing link; gold = unknown.
    add("syn-brk-00", "synthetic",
        ["Xanadu Prime is the capital of the province of Lumen Reach."],
        "Who is the mayor of the capital of the province of Lumen Reach?",
        "unknown", "abstain_broken")
    add("syn-brk-01", "synthetic",
        ["The mayor of Port Ivo is Helena Marsh."],
        "Who is the mayor of the capital of the province of Alder Wash?",
        "unknown", "abstain_broken")
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/open/bench65/fable_edit_200.jsonl")
    ap.add_argument("--out", default="artifacts/fable-bench66-20260921/")
    ap.add_argument("--synthetic", default=None,
                    help="write a 20-item synthetic stand-in to this path and use it")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--ft-steps", type=int, default=FT_STEPS)
    ap.add_argument("--skip-finetune", action="store_true")
    args = ap.parse_args()

    torch.manual_seed(SEED)
    np.random.seed(SEED)
    try:
        torch.set_num_threads(1)
    except Exception:
        pass

    if args.synthetic:
        items = make_synthetic()
        with open(args.synthetic, "w", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps(it) + "\n")
        data_path = args.synthetic
    else:
        data_path = args.data
        items = load_items(data_path)
    if args.limit:
        items = items[: args.limit]
    n = len(items)
    print("items: %d from %s" % (n, data_path), flush=True)

    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODEL_ID, local_files_only=False, trust_remote_code=False)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    try:
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID, dtype=torch.float32, trust_remote_code=False)
    except TypeError:
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID, torch_dtype=torch.float32, trust_remote_code=False)
    model.to("cpu")
    model.eval()

    # --- fine-tune setup: ONLY final 2 transformer blocks + lm_head train ---
    layer_holder = None
    for cand in ("model.layers", "transformer.h", "gpt_neox.layers"):
        obj = model
        try:
            for part in cand.split("."):
                obj = getattr(obj, part)
            layer_holder = obj
            break
        except AttributeError:
            continue
    if layer_holder is None:
        # generic fallback: find the longest ModuleList of blocks
        best, best_len = None, 0
        for m in model.modules():
            if isinstance(m, torch.nn.ModuleList) and len(m) > best_len:
                try:
                    import torch.nn as nn  # noqa
                    best, best_len = m, len(m)
                except Exception:
                    pass
        layer_holder = best
    assert layer_holder is not None and len(layer_holder) >= 2, "no transformer blocks found"
    last_two = list(layer_holder)[-2:]
    head = getattr(model, "lm_head", None)
    assert head is not None, "no lm_head found"

    for p in model.parameters():
        p.requires_grad = False
    train_params = []
    for blk in last_two:
        for p in blk.parameters():
            p.requires_grad = True
            train_params.append(p)
    for p in head.parameters():
        p.requires_grad = True
        train_params.append(p)
    n_train = sum(p.numel() for p in train_params)
    n_all = sum(p.numel() for p in model.parameters())
    print("trainable: %d / %d params (%.2f%%)" % (n_train, n_all, 100.0 * n_train / n_all), flush=True)
    base_state = {k: v.detach().cpu().clone()
                  for k, v in model.state_dict().items()}

    def reset_to_base():
        model.load_state_dict(base_state, strict=True)
        model.eval()

    t0_all = time.time()
    per_item = {a: [] for a in ARMS}
    rows_out = []
    ft_times = []
    ft_scope = n if not args.skip_finetune else 0
    ft_cut = False
    # Adaptive cut: after 3 FT items, project 20 steps x n; cut to first 60.
    FT_PROBE = 3

    def finetune_item(sentences):
        reset_to_base()
        model.train()
        opt = torch.optim.Adam([p for p in train_params if p.requires_grad], lr=FT_LR)
        encs = []
        for s in sentences:
            e = tok(s, return_tensors="pt")
            if e["input_ids"].shape[1] > 256:
                e = {k: v[:, :256] for k, v in e.items()}
            encs.append(e)
        if not encs:
            model.eval()
            return
        for _ in range(args.ft_steps):
            opt.zero_grad()
            tot_loss, tot_tok = 0.0, 0
            for e in encs:
                ids = e["input_ids"]
                out = model(input_ids=ids, labels=ids)
                ntok = ids.numel()
                tot_loss = tot_loss + out.loss * ntok
                tot_tok += ntok
            (tot_loss / max(tot_tok, 1)).backward()
            opt.step()
        model.eval()

    for i, it in enumerate(items):
        t_item = time.time()
        sents, q, golds = it["sentences"], it["question"], it["golds"]
        # K4 structural note: prompts/train text built ONLY from sents + q.
        row = {"id": it["id"], "type": it["type"], "expected": it["expected"],
               "golds": golds, "arms": {}}
        p_full = build_prompt(tok, sents, q)
        a_full = greedy_answer(model, tok, p_full)
        v, ex, cg = classify(a_full, golds)
        row["arms"]["incontext"] = {"answer": a_full, "verdict": v,
                                    "exact": ex, "contains_gold": cg}
        p_rag = build_prompt(tok, bm25_top3(sents, q, 3), q)
        a_rag = greedy_answer(model, tok, p_rag)
        v, ex, cg = classify(a_rag, golds)
        row["arms"]["raglite"] = {"answer": a_rag, "verdict": v,
                                  "exact": ex, "contains_gold": cg}
        if i < ft_scope:
            t_ft = time.time()
            finetune_item(sents)
            a_ft = greedy_answer(model, tok, build_zero_shot_prompt(tok, q))
            reset_to_base()
            ft_times.append(time.time() - t_ft)
            v, ex, cg = classify(a_ft, golds)
            row["arms"]["finetune"] = {"answer": a_ft, "verdict": v,
                                       "exact": ex, "contains_gold": cg}
            if len(ft_times) == FT_PROBE and n > FT_CUT_N:
                proj = (sum(ft_times) / len(ft_times)) * n
                if proj > FT_CUT_PROJECTED_S:
                    ft_scope = FT_CUT_N
                    ft_cut = True
                    print("FT-CUT: projected %.1fs > %ds; FT limited to first %d items"
                          % (proj, FT_CUT_PROJECTED_S, FT_CUT_N), flush=True)
        else:
            row["arms"]["finetune"] = {"answer": "", "verdict": "not-run",
                                       "exact": False, "contains_gold": False}
        rows_out.append(row)
        per_item["incontext"].append(time.time() - t_item)
        if (i + 1) % 20 == 0 or i + 1 == n:
            print("  %d/%d items, elapsed %.0fs" % (i + 1, n, time.time() - t0_all), flush=True)

    total_s = time.time() - t0_all

    # --- summary tables ---
    summary = {}
    for a in ARMS:
        summary[a] = {}
        for t in TYPES:
            c = {"correct": 0, "abstain": 0, "wrong": 0,
                 "contains_gold": 0, "n": 0, "not_run": 0}
            for r in rows_out:
                if r["type"] != t:
                    continue
                cell = r["arms"][a]
                if cell["verdict"] == "not-run":
                    c["not_run"] += 1
                    continue
                c["n"] += 1
                c[cell["verdict"]] += 1
                c["contains_gold"] += int(cell["contains_gold"])
            summary[a][t] = c

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "fable_bench66_results.json"), "w", encoding="utf-8") as f:
        json.dump({"model": MODEL_ID, "seed": SEED, "data": data_path,
                   "n_items": n, "ft_scope": ft_scope, "ft_cut": ft_cut,
                   "ft_steps": args.ft_steps, "total_wall_s": total_s,
                   "k4_note": "prompts and FT text built only from sentences+question; "
                              "gold used solely for scoring",
                   "rows": rows_out, "summary": summary}, f, indent=1)
    print("=== SUMMARY (correct/abstain/wrong, n) ===")
    for a in ARMS:
        for t in TYPES:
            c = summary[a][t]
            print("%-10s %-15s C=%d A=%d W=%d (n=%d, notrun=%d, contains=%d)"
                  % (a, t, c["correct"], c["abstain"], c["wrong"],
                     c["n"], c["not_run"], c["contains_gold"]))
    print("FT scope: %d/%d (cut=%s) total wall %.0fs" % (ft_scope, n, ft_cut, total_s))
    print("REPRODUCE: uv run --offline --no-project --python 3.12 --with torch "
          "--with numpy --with transformers python -B scripts/fable_bench66_baselines.py "
          "--data %s --out %s" % (data_path, args.out))


if __name__ == "__main__":
    main()
