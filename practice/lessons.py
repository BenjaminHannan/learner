"""Torch-free lesson building for Practice-1 (shared by the Kaggle night trainer and the Mac MLX trainer)."""
import random

from .harness import IM_END, IM_START, THINK_EMPTY


N_SFT, EPOCHS, N_PAIRS, N_STEPS = 256, 2, 64, 32
DPO_W = 0.2
MAX_TRAIN_TOKENS = 2048  # Kaggle full v2: night 1 OOMed on a T4 (backward of a ~4k-token pair); the Mac already used 2048


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


def transcript_len(tok, messages):
    return sum(len(tok(t, add_special_tokens=False).input_ids) for t, _ in segments(messages, tok.bos_token or ""))


def build_lessons(arm, store, tok, seed, night, n_sft=N_SFT, epochs=EPOCHS, n_pairs=N_PAIRS, max_tokens=MAX_TRAIN_TOKENS):
    """store: per-try records of all days so far (id, correct, messages). Returns (items, stats). Same counts in both arms by construction."""
    rng = random.Random(seed * 100003 + night * 17 + (1 if arm == "P" else 2))
    tries = [r for r in store if transcript_len(tok, r["messages"]) <= max_tokens]
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


