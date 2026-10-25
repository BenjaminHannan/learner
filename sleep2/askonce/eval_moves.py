"""Step 10: run one model state on Splits H and R, silent-wrong, 100 general prompts, 100 fact-recall questions and the ARC-Easy 500 subset.
Inputs are frozen files (eval_inputs.jsonl with the final slot memory already in each prompt), so every arm sees identical prompts.
ACT correctness is checked here by code (tools_mock); ASKs are mapped to slot ids later by grade.py (Haiku)."""
import re
import time

import torch

from .config import ACT_MAX_NEW, FACT_Q_MAX_NEW, jl_read, norm, shrink
from .model_io import generate
from .tools_mock import check_action, parse_reply
from .world import fact_messages, general_messages, render


def classify_general(text):
    """ASK / ANSWER for a general (non-assistant) prompt: did the model ask a question back instead of answering?"""
    t = (text or "").strip()
    if t.upper().startswith("ASK"):
        return "ASK"
    first = re.split(r"(?<=[.!?])\s", t)[0] if t else ""
    return "ASK" if t.endswith("?") and len(t.split()) <= 40 and "?" in first else "ANSWER"


def eval_moves(model, tok, items, bs=8, log=print):
    outs = generate(model, tok, [i["prompt"] for i in items], ACT_MAX_NEW, 0.0, 0, bs, log)
    rows = []
    for it, o in zip(items, outs):
        move, payload = parse_reply(o)
        row = {"req_id": it["req_id"], "split": it["split"], "move": move, "out": o.strip()[:400]}
        if move == "ACT":
            row["act_ok"] = bool(check_action(payload, it["gold"])[0])
        else:
            row["act_ok"] = False
            if move == "ASK":
                row["question"] = payload
        rows.append(row)
    return rows


def eval_general(model, tok, prompts, bs=8, log=print):
    ps = [render(general_messages(p), True, tok.bos_token or "") for p in prompts]
    outs = generate(model, tok, ps, 48, 0.0, 0, bs, log)
    return [{"prompt": p, "out": o.strip()[:300], "kind": classify_general(o)} for p, o in zip(prompts, outs)]


def eval_facts(model, tok, facts, bs=8, log=print):
    """facts: [{id, q, a}] -> closed-book (no memory in the prompt) short answers, exact containment after NFKC."""
    ps = [render(fact_messages(f["q"]), True, tok.bos_token or "") for f in facts]
    outs = generate(model, tok, ps, FACT_Q_MAX_NEW, 0.0, 0, bs, log)
    return [{"id": f["id"], "ok": norm(f["a"]) in norm(o), "out": o.strip()[:100]} for f, o in zip(facts, outs)]


@torch.no_grad()
def eval_arc(model, tok, arc, log=print):
    """Letter with the highest next-token logit after the assistant prefix; one forward per question."""
    dev = next(model.parameters()).device
    inner = model.base_model.model if hasattr(model, "base_model") and hasattr(model.base_model, "model") else model
    was = model.training
    model.eval()
    ok = 0
    for q in arc:
        user = q["q"] + "\n" + "\n".join(f"{l}. {t}" for l, t in zip(q["labels"], q["texts"])) + "\nAnswer with the letter only."
        p = render([{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": user}], True, tok.bos_token or "")
        ids = tok(p, return_tensors="pt", add_special_tokens=False).input_ids.to(dev)
        h = inner.model(input_ids=ids, use_cache=False).last_hidden_state[:, -1]
        lg = inner.lm_head(h).float()[0]
        cand = [tok(l, add_special_tokens=False).input_ids[0] for l in q["labels"]]
        pred = q["labels"][int(torch.argmax(lg[cand]))]
        ok += pred == q["a"]
    if was:
        model.train()
    return {"acc": ok / len(arc), "n": len(arc)}


def run_eval(model, tok, eval_inputs, general, facts, arc, bs=8, log=print):
    t0 = time.time()
    res = {"moves": eval_moves(model, tok, eval_inputs, bs, log)}
    log(f"  moves done {time.time() - t0:.0f}s")
    res["general"] = eval_general(model, tok, general, bs, log)
    res["facts"] = eval_facts(model, tok, facts, bs, log)
    res["arc"] = eval_arc(model, tok, arc, log)
    res["seconds"] = round(time.time() - t0, 1)
    return res


def load_eval_sets(data_dir):
    """-> (eval_inputs, general prompts, fact questions, arc) all shrunk by ASKONCE_SCALE equally for every arm."""
    from .config import jload
    ev = jl_read(data_dir / "eval_inputs.jsonl")
    by = {}
    for r in ev:
        by.setdefault(r["split"], []).append(r)
    items = [r for sp in sorted(by) for r in shrink(by[sp])]
    phr = jload(data_dir / "phrasings.json")
    gen = shrink(phr["general"][-100:])
    facts = shrink(jload(data_dir / "fact_questions.json"))
    arc = shrink(jload(data_dir / "arc_easy_500.json"))
    return items, gen, facts, arc
