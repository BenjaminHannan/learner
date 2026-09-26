#!/usr/bin/env python3
"""k1h: GLM's answers -> a LoRA adapter on the LFM creative writer (Creative answers in chat thread, 2026-09-26).

The data gate (artifacts/claude-k1h-20260926/DATA-GATE-k1h.md, fixed 19:32 UTC before any answer existed) and the
training recipe (PASSMARKS-k1h.md) are fixed in advance. No Claude-written text is a target; blind judges' verdicts
decide gate 2's pass or fail only and never pick an answer.

check   (thread container, no model) the code filters and gate 1, the DEV overlap, and gate 2's packet:
          python -B scripts/claude_k1h_train.py check --items A.jsonl --items B.jsonl --answers ANS.jsonl \
              --dev DEV/items.jsonl --out DIR
        keeps an answer if it is non-empty, claude_chat338_agent.trim leaves it unchanged and guard333d passes it
        (known words: the request and the user's messages); drops practice chats that are near-copies of a DEV chat.
        Writes DIR/kept.jsonl {item_id, answer}, DIR/gate2_packet.jsonl (60 kept answers, seed 4611, ids G0000..,
        JUDGE-k1f.md's line format) and DIR/gate2_key.json; prints counts, gate 1 and the top openings (3 words).
gate2   the blind judges' verdicts on the gate-2 packet -> pass or fail (useful >= 48 of 60, made-up >= 1 on <= 3):
          python -B scripts/claude_k1h_train.py gate2 --key DIR/gate2_key.json --judges J1,J2[,J3] [--splits-out F]
train   (BensPC) pairs each practice chat's logged writer prompt (claude_k1h_cre.PromptLog, the last request of the
        chat) with its kept GLM answer, splits 10% of chats off as dev (seed 4612), and trains a LoRA adapter:
          python -B scripts/claude_k1h_train.py train --model L12DIR --items PRACTICE/items.jsonl \
              --prompts PROMPTS.jsonl --kept KEPT.jsonl --out OUT [--limit N --max-steps S]
        The prompt is rendered and tokenized exactly as the writer does at run time (claude_chat338_agent.Gen338
        ._render, then the tokenizer's defaults); the target is the answer plus the chat template's end-of-turn text,
        whose last token must be one the model stops on. Loss on the target tokens only. Recipe (fixed): LoRA rank 16,
        alpha 32, dropout 0.05, every linear layer; AdamW lr 2e-4, no weight decay; 2 epochs; batch 8 (4 x 2
        accumulation); warmup 5% then cosine to 0; rows longer than 1536 tokens dropped (counted); seed 4613; bf16
        weights on CUDA with the adapter in float32; the last step's adapter is kept (no choice by dev loss). Every
        trainable weight must get a gradient on the first step, else it stops (the autocast finding, 14dc0c013).
        Writes OUT/adapter/ (adapter_model.safetensors, adapter_config.json), OUT/train_log.jsonl, OUT/summary.json
        and prints "k1h-train: adapter sha256 = <sha>".
selftest (CPU, no model)
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
import time
import types
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_chat338_agent as C38     # noqa: E402
import claude_cre333d_agent as CD      # noqa: E402

GATE2_N, GATE2_SEED, GATE2_USEFUL, GATE2_MADEUP = 60, 4611, 48, 3
FRAME_OPEN_SHARE, FRAME_SENT_SHARE = 0.25, 0.02
DEV_SEED, TRAIN_SEED, DEV_SHARE = 4612, 4613, 0.10
RANK, ALPHA, DROPOUT, LR, EPOCHS, MICRO, ACCUM, WARM, MAX_LEN = 16, 32, 0.05, 2e-4, 2, 4, 2, 0.05, 1536
SENT = "K1HSENTINEL"


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def _words(t: str) -> set:
    return set(re.findall(r"[a-z0-9']+", t.lower()))


def filter_reason(ans: str, it: dict) -> str | None:
    """None if the answer is kept, else why not (the build's own trim and guard333d)."""
    a = (ans or "").strip()
    if not a:
        return "empty"
    if C38.trim(a) != a:
        return "trim"
    known = C38._words([it["last"]] + [t for t in it["turns"] if isinstance(t, str)])
    return CD.guard333d(a, it["last"], known)


def opening(a: str) -> str:
    return " ".join(re.findall(r"[a-z0-9']+", a.lower())[:3])


def sentences(a: str) -> set:
    return {re.sub(r"\s+", " ", s.strip().lower()) for s in re.split(r"(?<=[.!?])\s+", a) if s.strip()}


def gate1(answers: list[str]) -> dict:
    n = len(answers)
    op = Counter(opening(a) for a in answers)
    se = Counter(s for a in answers for s in sentences(a))
    top_o, top_s = op.most_common(1)[0] if op else ("", 0), se.most_common(1)[0][1] if se else 0
    return {"answers": n, "top_openings": op.most_common(8), "top_opening_share": round(top_o[1] / max(1, n), 3),
            "top_sentence_count": top_s, "top_sentence_share": round(top_s / max(1, n), 3),
            "pass": n > 0 and top_o[1] <= FRAME_OPEN_SHARE * n and top_s <= max(1.0, FRAME_SENT_SHARE * n)}


def near_copy(req: str, dev_reqs: list[str]) -> bool:
    a = _words(req)
    norm = " ".join(sorted(a))
    for d in dev_reqs:
        b = _words(d)
        if norm == " ".join(sorted(b)) or (len(a) >= 3 and len(a & b) >= 0.8 * len(a)):
            return True
    return False


def run_check(a) -> dict:
    items = [it for p in a.items for it in load(p)]
    by_id = {it["item_id"]: it for it in items}
    if len(by_id) != len(items):
        raise SystemExit("k1h check: duplicate item ids")
    dev_reqs = [it["last"] for it in load(a.dev)]
    answers = {}
    for r in load(a.answers):
        if r.get("answer"):
            answers[r["item_id"]] = r["answer"]            # a resumed item keeps its last non-empty answer
    why, kept = Counter(), []
    for iid in sorted(by_id):
        it = by_id[iid]
        if near_copy(it["last"], dev_reqs):
            why["near_copy_dev"] += 1
            continue
        if iid not in answers:
            why["no_answer"] += 1
            continue
        r = filter_reason(answers[iid], it)
        if r:
            why[r] += 1
            continue
        kept.append({"item_id": iid, "answer": answers[iid].strip()})
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "kept.jsonl").write_text("".join(json.dumps(k, ensure_ascii=False) + "\n" for k in kept), encoding="utf-8")
    pool = list(kept)
    random.Random(GATE2_SEED).shuffle(pool)
    key = {}
    with open(out / "gate2_packet.jsonl", "w", encoding="utf-8") as fh:
        for n, k in enumerate(pool[:GATE2_N]):
            it = by_id[k["item_id"]]
            key[f"G{n:04d}"] = k["item_id"]
            fh.write(json.dumps({"id": f"G{n:04d}", "chat": it["turns"], "request": it["last"], "reply": k["answer"]},
                                ensure_ascii=False) + "\n")
    (out / "gate2_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    res = {"items": len(items), "answered": sum(i in answers for i in by_id), "kept": len(kept),
           "dropped": dict(why), "gate1": gate1([k["answer"] for k in kept]), "gate2_lines": len(key),
           "kept_by_kind": dict(Counter(by_id[k["item_id"]]["kind"] for k in kept))}
    print(json.dumps(res, ensure_ascii=False))
    return res


def run_gate2(a) -> dict | None:
    import claude_k1c_score as KC
    key = json.loads(Path(a.key).read_text(encoding="utf-8"))
    js = KC._judges(a.judges)
    j1, j2 = js[0], js[1]
    if any(c not in j1 or c not in j2 for c in key):
        raise SystemExit("k1h gate2: ids missing from judge 1 or 2")
    split = sorted(c for c in key if KC.yes(j1[c]["useful"]) != KC.yes(j2[c]["useful"])
                   or KC.madeup(j1[c]) != KC.madeup(j2[c]))
    if len(js) < 3:
        if a.splits_out:
            Path(a.splits_out).write_text(json.dumps(split), encoding="utf-8")
        print(json.dumps({"lines": len(key), "need_third": len(split)}))
        return None
    j3 = js[2]
    if any(c not in j3 for c in split):
        raise SystemExit("k1h gate2: split ids missing from judge 3")
    u = m = 0
    for c in key:
        u1, u2, m1, m2 = KC.yes(j1[c]["useful"]), KC.yes(j2[c]["useful"]), KC.madeup(j1[c]), KC.madeup(j2[c])
        u += u1 if u1 == u2 else KC.yes(j3[c]["useful"])
        m += m1 if m1 == m2 else KC.madeup(j3[c])
    res = {"lines": len(key), "third_judged": len(split), "useful": u, "madeup": m,
           "need_useful": GATE2_USEFUL, "max_madeup": GATE2_MADEUP,
           "pass": len(key) == GATE2_N and u >= GATE2_USEFUL and m <= GATE2_MADEUP}
    print(json.dumps(res))
    return res


# ------------------------------------------------------------------ training rows and encoding
def pair_rows(items_path: str, prompts_path: str, kept_path: str) -> tuple[list, list, dict]:
    import claude_k1f_score as K1FS
    recs = K1FS._last_records(items_path, Path(prompts_path))       # {item_id: the log record of its last request}
    kept = {k["item_id"]: k["answer"] for k in load(kept_path)}
    ids = sorted(i for i in recs if i in kept)
    rng = random.Random(DEV_SEED)
    shuffled = list(ids)
    rng.shuffle(shuffled)
    dev_ids = set(shuffled[:round(DEV_SHARE * len(ids))])
    rows = [{"item_id": i, "msgs": recs[i]["msgs"], "target": kept[i]} for i in ids]
    counts = {"items": len(load(items_path)), "prompted": len(recs), "kept": len(kept), "paired": len(ids),
              "kept_without_prompt": len(set(kept) - set(recs)), "dev": len(dev_ids)}
    return [r for r in rows if r["item_id"] not in dev_ids], [r for r in rows if r["item_id"] in dev_ids], counts


def render(tok, msgs) -> str:
    """The writer's own rendering (Gen338._render: thinking off, add_generation_prompt, the no-system fallback)."""
    return C38.Gen338._render(types.SimpleNamespace(g=types.SimpleNamespace(tok=tok)), msgs)


def end_text(tok) -> str:
    full = tok.apply_chat_template([{"role": "user", "content": "x"}, {"role": "assistant", "content": SENT}],
                                   tokenize=False)
    return full.split(SENT, 1)[1].rstrip()


def stop_ids(tok, gen_cfg) -> set:
    e = getattr(gen_cfg, "eos_token_id", None) if gen_cfg is not None else None
    s = set(e if isinstance(e, (list, tuple)) else ([e] if e is not None else []))
    if tok.eos_token_id is not None:
        s.add(tok.eos_token_id)
    return s


def encode(tok, msgs, target: str, end: str, max_len: int):
    p = tok(render(tok, msgs))["input_ids"]
    t = tok(target + end, add_special_tokens=False)["input_ids"]
    if len(p) + len(t) > max_len:
        return None
    return p + t, [-100] * len(p) + t


def batches(enc, bs, pad_id, shuffle, rng, torch):
    idx = list(range(len(enc)))
    if shuffle:
        rng.shuffle(idx)
    for i in range(0, len(idx), bs):
        chunk = [enc[j] for j in idx[i:i + bs]]
        L = max(len(x[0]) for x in chunk)
        ids = torch.full((len(chunk), L), pad_id)
        lab = torch.full((len(chunk), L), -100)
        att = torch.zeros((len(chunk), L), dtype=torch.long)
        for k, (x, y) in enumerate(chunk):
            ids[k, :len(x)] = torch.tensor(x)
            lab[k, :len(y)] = torch.tensor(y)
            att[k, :len(x)] = 1
        yield ids, lab, att


def run_train(a) -> dict:
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from claude_k1h_cre import sha256_file
    torch.manual_seed(TRAIN_SEED)
    rng = random.Random(TRAIN_SEED)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    train_rows, dev_rows, counts = pair_rows(a.items, a.prompts, a.kept)
    if a.limit:
        train_rows, dev_rows = train_rows[:a.limit], dev_rows[:max(2, a.limit // 4)]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if dev == "cuda" else torch.float32
    tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=dtype, trust_remote_code=True).to(dev)
    end = end_text(tok)
    stops = stop_ids(tok, getattr(model, "generation_config", None))
    last_tok = tok(end, add_special_tokens=False)["input_ids"][-1]
    if last_tok not in stops:
        raise SystemExit(f"k1h train: TEMPLATE-FAIL: the end-of-turn text ends on token {last_tok}, not a stop token")
    pad_id = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    enc_t = [e for e in (encode(tok, r["msgs"], r["target"], end, MAX_LEN) for r in train_rows) if e]
    enc_d = [e for e in (encode(tok, r["msgs"], r["target"], end, MAX_LEN) for r in dev_rows) if e]
    counts.update({"train_rows": len(enc_t), "dev_rows": len(enc_d),
                   "too_long": len(train_rows) + len(dev_rows) - len(enc_t) - len(enc_d)})
    cfg = LoraConfig(r=RANK, lora_alpha=ALPHA, lora_dropout=DROPOUT, task_type="CAUSAL_LM", target_modules="all-linear")
    model = get_peft_model(model, cfg)
    for p in model.parameters():
        if p.requires_grad:
            p.data = p.data.float()
    n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    per_epoch = math.ceil(len(enc_t) / (MICRO * ACCUM))
    total = per_epoch * EPOCHS if not a.max_steps else min(a.max_steps, per_epoch * EPOCHS)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR, weight_decay=0.0)
    warm = max(1, round(WARM * total))
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1.0, (s + 1) / warm) * 0.5 * (1 + math.cos(math.pi * min(1.0, s / total))))

    def dev_loss():
        model.eval()
        tot = n = 0
        with torch.no_grad():
            for ids, lab, att in batches(enc_d, MICRO, pad_id, False, rng, torch):
                ids, lab, att = ids.to(dev), lab.to(dev), att.to(dev)
                with torch.autocast(dev, dtype=torch.bfloat16, enabled=dev == "cuda"):
                    loss = model(input_ids=ids, attention_mask=att, labels=lab).loss
                k = int((lab[:, 1:] != -100).sum())
                tot += loss.item() * k
                n += k
        model.train()
        return round(tot / max(1, n), 4)
    log = open(out / "train_log.jsonl", "w", encoding="utf-8")
    t0, step, micro, grad_none, dl = time.time(), 0, 0, None, [dev_loss()]
    print(json.dumps({"k1h-train": "start", **counts, "planned_steps": total, "dev_loss_0": dl[0],
                      "end_text": end, "trainable_params": n_train}), flush=True)
    model.train()
    for ep in range(EPOCHS):
        for ids, lab, att in batches(enc_t, MICRO, pad_id, True, rng, torch):
            if step >= total:
                break
            ids, lab, att = ids.to(dev), lab.to(dev), att.to(dev)
            with torch.autocast(dev, dtype=torch.bfloat16, enabled=dev == "cuda"):
                loss = model(input_ids=ids, attention_mask=att, labels=lab).loss / ACCUM
            loss.backward()
            micro += 1
            if micro % ACCUM:
                continue
            if grad_none is None:
                grad_none = sum(1 for p in model.parameters() if p.requires_grad and p.grad is None)
                if grad_none:
                    raise SystemExit(f"k1h train: {grad_none} trainable weights got no gradient on the first step")
            torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
            opt.step()
            sched.step()
            opt.zero_grad(set_to_none=True)
            step += 1
            if step % 10 == 0 or step == 1:
                rec = {"step": step, "total": total, "loss": round(loss.item() * ACCUM, 4),
                       "lr": sched.get_last_lr()[0], "min": round((time.time() - t0) / 60, 2)}
                log.write(json.dumps(rec) + "\n")
                log.flush()
                print(rec, flush=True)
        dl.append(dev_loss())
        print(json.dumps({"epoch": ep + 1, "dev_loss": dl[-1]}), flush=True)
    model.save_pretrained(out / "adapter")
    sha = sha256_file(out / "adapter" / "adapter_model.safetensors")
    summ = {**counts, "steps": step, "planned_steps": total, "dev_loss_by_epoch": dl, "trainable_params": n_train,
            "grad_none_after_first_step": grad_none, "minutes": round((time.time() - t0) / 60, 2), "device": dev,
            "end_text": end, "adapter_sha256": sha, "limit": a.limit, "max_steps": a.max_steps,
            "recipe": {"rank": RANK, "alpha": ALPHA, "dropout": DROPOUT, "lr": LR, "epochs": EPOCHS,
                       "batch": MICRO * ACCUM, "warmup": WARM, "max_len": MAX_LEN, "seed": TRAIN_SEED}}
    (out / "summary.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    print(f"k1h-train: adapter sha256 = {sha}", flush=True)
    return summ


# ------------------------------------------------------------------ selftest
class _Tok:
    """A character tokenizer with a ChatML-like template, enough to test rendering, masking and the end check."""
    eos_token_id, pad_token_id, chat_template = 1, 0, "x"

    def apply_chat_template(self, msgs, tokenize=False, add_generation_prompt=False, **kw):
        s = "".join(f"<{m['role']}>{m['content']}<end>\n" for m in msgs)
        return s + ("<assistant>" if add_generation_prompt else "")

    def __call__(self, text, add_special_tokens=True, **kw):
        ids = [2] if add_special_tokens else []
        i = 0
        while i < len(text):
            if text.startswith("<end>", i):
                ids.append(1)
                i += 5
            else:
                ids.append(3 + ord(text[i]) % 200)
                i += 1
        return {"input_ids": ids}


def selftest() -> None:
    import tempfile
    ok = 0
    it = {"item_id": "a", "turns": ["My sister Wren loves sailing."], "last": "a card for Wren?"}
    assert filter_reason("Fair winds, Wren! Happy birthday.", it) is None
    assert filter_reason("Fair winds, Wren! Happy birthday", it) == "trim"
    assert filter_reason("", it) == "empty"
    assert filter_reason(" ".join(["word"] * 150) + ".", it) == "G4"
    ok += 1
    g = gate1(["Here are three names. A. B.", "Here are three ideas. C.", "Try this. D.", "Why not a toast. E."])
    assert g["top_opening_share"] == 0.5 and g["pass"] is False           # one opening in 2 of 4 answers
    g = gate1([f"Idea {i}: row boat number {i}." for i in range(8)])
    assert g["top_opening_share"] == 0.125 and g["top_sentence_count"] == 1 and g["pass"] is True
    many = [f"Plan {i} starts here. Hope this helps." if i < 3 else f"Plan {i} starts here." for i in range(100)]
    g = gate1(many)
    assert g["top_sentence_count"] == 3 and g["pass"] is False           # one sentence in 3 of 100 answers
    assert near_copy("Any names for our pottery club?", ["any names for our pottery club"]) is True
    assert near_copy("3 names for a chess club", ["a poem for my dog"]) is False
    ok += 1
    tok = _Tok()
    end = end_text(tok)
    assert end == "<end>" and tok(end, add_special_tokens=False)["input_ids"][-1] in stop_ids(tok, None)
    msgs = [{"role": "system", "content": "S"}, {"role": "user", "content": "hi"}]
    ids, lab = encode(tok, msgs, "Ok.", end, 999)
    p = tok(render(tok, msgs))["input_ids"]
    assert ids[:len(p)] == p and lab[:len(p)] == [-100] * len(p) and lab[len(p):] == ids[len(p):]
    assert ids[-1] == 1 and len(ids) - len(p) == len("Ok.") + 1
    assert encode(tok, msgs, "Ok.", end, len(ids) - 1) is None
    ok += 1
    with tempfile.TemporaryDirectory() as d:
        items = [{"item_id": f"kh-{i:04d}", "kind": "idea", "turns": [], "last": f"give me {i} names?",
                  "facts": []} for i in range(20)]
        ip = Path(d) / "items.jsonl"
        ip.write_text("".join(json.dumps(x) + "\n" for x in items), encoding="utf-8")
        pl = Path(d) / "prompts.jsonl"
        with open(pl, "w", encoding="utf-8") as fh:
            for i, x in enumerate(items[:18]):
                m = [{"role": "system", "content": "S"}, {"role": "user", "content": x["last"]}]
                fh.write(json.dumps({"dir": f"p{i}", "request": x["last"], "msgs": m}) + "\n")
        kp = Path(d) / "kept.jsonl"
        kp.write_text("".join(json.dumps({"item_id": x["item_id"], "answer": "A."}) + "\n" for x in items[2:]),
                      encoding="utf-8")
        tr, dv, c = pair_rows(str(ip), str(pl), str(kp))
        assert c["paired"] == 16 and c["kept_without_prompt"] == 2 and len(dv) == 2 and len(tr) == 14, c
        assert not ({r["item_id"] for r in tr} & {r["item_id"] for r in dv})
        tr2, dv2, _ = pair_rows(str(ip), str(pl), str(kp))
        assert [r["item_id"] for r in dv2] == [r["item_id"] for r in dv]
        ok += 1
        pk = Path(d) / "k.json"
        pk.write_text(json.dumps({f"G{i:04d}": f"kh-{i:04d}" for i in range(60)}), encoding="utf-8")
        j1 = Path(d) / "j1.jsonl"
        j2 = Path(d) / "j2.jsonl"
        j3 = Path(d) / "j3.jsonl"
        j1.write_text("".join(json.dumps({"id": f"G{i:04d}", "useful": "yes" if i < 50 else "no",
                                          "made_up_user_facts": 0}) + "\n" for i in range(60)), encoding="utf-8")
        j2.write_text("".join(json.dumps({"id": f"G{i:04d}", "useful": "yes" if i < 46 else "no",
                                          "made_up_user_facts": 1 if i < 2 else 0}) + "\n" for i in range(60)),
                      encoding="utf-8")
        j3.write_text("".join(json.dumps({"id": f"G{i:04d}", "useful": "yes" if i < 48 else "no",
                                          "made_up_user_facts": 1 if i == 0 else 0}) + "\n" for i in range(60)),
                      encoding="utf-8")
        ns = argparse.Namespace(key=str(pk), judges=f"{j1},{j2}", splits_out=str(Path(d) / "s.json"))
        assert run_gate2(ns) is None and len(json.loads((Path(d) / "s.json").read_text())) == 6
        ns.judges = f"{j1},{j2},{j3}"
        r = run_gate2(ns)
        assert r["useful"] == 48 and r["madeup"] == 1 and r["pass"] is True, r
        ok += 1
    print(f"k1h train selftest {ok}/5 ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["check", "gate2", "train", "selftest"])
    ap.add_argument("--items", action="append")
    ap.add_argument("--answers")
    ap.add_argument("--dev")
    ap.add_argument("--out")
    ap.add_argument("--key")
    ap.add_argument("--judges")
    ap.add_argument("--splits-out", default="")
    ap.add_argument("--model")
    ap.add_argument("--prompts")
    ap.add_argument("--kept")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-steps", type=int, default=0)
    a = ap.parse_args()
    if a.mode == "selftest":
        return selftest()
    if a.mode == "check":
        return run_check(a)
    if a.mode == "gate2":
        return run_gate2(a)
    if len(a.items or []) != 1:
        raise SystemExit("k1h train: one --items file (the practice chats the prompts were logged on)")
    a.items = a.items[0]
    return run_train(a)


if __name__ == "__main__":
    main()
