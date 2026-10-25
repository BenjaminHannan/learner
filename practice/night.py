"""Night training for Practice-1. Fresh LoRA on the base model each night, trained on lessons drawn from ALL tries gathered so far (expert iteration).
Arm P (checker): SFT on solved tries + DPO pairs (solved, failed) on the same puzzle. Arm C (no checker): same counts, drawn from all tries uniformly,
pairs are two random tries of the same puzzle in random order. Fixed size every night: N_SFT x EPOCHS sft items + up to N_PAIRS pairs (DPO beta 0.1,
weight 0.2), the same number of optimizer steps in both arms. Loss only on assistant turns (tool outputs and prompts are masked)."""
import random

from sleep2.askonce.config import LR
from sleep2.askonce.train_core import LoRATrainer

from .harness import IM_END, IM_START, THINK_EMPTY

N_SFT, EPOCHS, N_PAIRS, N_STEPS = 256, 2, 64, 32
DPO_W = 0.2
MAX_TRAIN_TOKENS = 4096


def segments(messages, bos=""):
    """[(text, trained?)] for a full transcript; only assistant text and its closing <|ifm|im_end|> are trained."""
    segs = [(bos, False)] if bos else []
    for m in messages:
        if m["role"] == "assistant":
            segs.append((f"{IM_START}assistant\n{THINK_EMPTY}", False))
            segs.append((m["content"] + IM_END, True))
        else:
            segs.append((f"{IM_START}{m['role']}\n{m['content']}{IM_END}", False))
    return segs


class MultiTurnTrainer(LoRATrainer):
    """LoRATrainer whose items may carry whole transcripts: sft target / pair chosen / rejected = a message list (prompt is then ignored)."""

    def encode(self, prompt, target):
        if not isinstance(target, list):
            return super().encode(prompt, target)
        ids, mask = [], []
        for text, trained in segments(target, self.tok.bos_token or ""):
            t = self.tok(text, add_special_tokens=False).input_ids
            ids += t
            mask += [1 if trained else 0] * len(t)
        return {"ids": ids, "mask": mask}


def transcript_len(tok, messages):
    return sum(len(tok(t, add_special_tokens=False).input_ids) for t, _ in segments(messages, tok.bos_token or ""))


def build_lessons(arm, store, tok, seed, night, n_sft=N_SFT, epochs=EPOCHS, n_pairs=N_PAIRS):
    """store: per-try records of all days so far (id, correct, messages). Returns (items, stats). Same counts in both arms by construction."""
    rng = random.Random(seed * 100003 + night * 17 + (1 if arm == "P" else 2))
    tries = [r for r in store if transcript_len(tok, r["messages"]) <= MAX_TRAIN_TOKENS]
    by = {}
    for r in tries:
        by.setdefault(r["id"], []).append(r)

    def fill(pool, n):
        if not pool:
            return []
        if len(pool) >= n:
            return rng.sample(pool, n)
        return list(pool) + [rng.choice(pool) for _ in range(n - len(pool))]  # resample with repetition

    if arm == "P":
        sft_src = fill([r for r in tries if r["correct"]], n_sft)
        cands = []
        for pid, rs in by.items():
            w, f = [r for r in rs if r["correct"]], [r for r in rs if not r["correct"]]
            if w and f:
                cands.append((rng.choice(w), rng.choice(f)))
        pairs = fill(cands, n_pairs) if len(cands) < n_pairs else rng.sample(cands, n_pairs)
        pairs = [(a, b) for a, b in pairs]
    else:
        sft_src = fill(tries, n_sft)
        cands = []
        for pid, rs in by.items():
            if len(rs) >= 2:
                a, b = rng.sample(rs, 2)  # random order, result not looked at
                cands.append((a, b))
        pairs = fill(cands, n_pairs) if len(cands) < n_pairs else rng.sample(cands, n_pairs)
    items = [{"kind": "sft", "prompt": "", "target": r["messages"]} for r in sft_src] * epochs
    items += [{"kind": "pair", "prompt": "", "chosen": a["messages"], "rejected": b["messages"]} for a, b in pairs]
    st = {"arm": arm, "night": night, "tries_in_store": len(store), "tries_usable": len(tries), "wins_in_store": sum(r["correct"] for r in tries),
          "sft_unique": len({(r["id"], r["try"]) for r in sft_src}), "sft_examples": len(sft_src) * epochs, "pairs": len(pairs),
          "pair_candidates": len(cands), "sft_correct_frac": round(sum(r["correct"] for r in sft_src) / max(1, len(sft_src)), 3),
          "pair_chosen_correct_frac": round(sum(a["correct"] for a, _ in pairs) / max(1, len(pairs)), 3),
          "pair_rejected_correct_frac": round(sum(b["correct"] for _, b in pairs) / max(1, len(pairs)), 3), "n_items": len(items)}
    return items, st


def train_night(model, tok, arm, store, seed, night, dev, use_scaler, anchors, n_steps=N_STEPS, n_sft=N_SFT, epochs=EPOCHS, n_pairs=N_PAIRS, lr=LR, log=print):
    """Fresh adapter on the clean base `model`. Returns (trainer or None, stats). Trainer.pm is the adapted model for the next day; call trainer.release() before the
    next night. With no lessons the adapter stays at its zero init (= the base model)."""
    items, st = build_lessons(arm, store, tok, seed, night, n_sft, epochs, n_pairs)
    trainer = MultiTurnTrainer(model, tok, seed, dev, use_scaler)
    if not items:
        st.update(skipped="no lessons")
        return trainer, st
    tr = trainer.run_night(items, anchors, n_steps, lr, night, log, dpo_w=DPO_W)
    st.update(train=tr)
    return trainer, st
