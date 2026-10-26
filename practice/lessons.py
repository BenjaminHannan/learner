"""Torch-free lesson building for Practice-1 (shared by the Kaggle night trainer and the Mac MLX trainer)."""
import random

from .harness import IM_END, IM_START, THINK_EMPTY


N_SFT, EPOCHS, N_PAIRS, N_STEPS = 256, 2, 64, 32
RG_N_SFT, RG_N_PAIRS, RG_MAX_STEPS = 700, 300, 128  # Practice-2 caps: a night stays near 1 h on a 4090 (1400 SFT items + 300 pairs ~ 2100 SFT-equivalents)
DPO_W = 0.2
MAX_TRAIN_TOKENS = 2048  # Kaggle full v2: night 1 OOMed on a T4 (backward of a ~4k-token pair); the Mac already used 2048


def segments(messages, bos=""):
    """[(text, trained?)] for a full transcript; only assistant text and its closing <|ifm|im_end|> are trained."""
    if isinstance(messages, dict):  # Practice-2 OpenCode try: segments rendered from the proxy log (oc_lessons.oc_segments, bos already in front)
        return [tuple(x) for x in messages["segs"]]
    segs = [(bos, False)] if bos else []
    for m in messages:
        if m["role"] == "assistant":
            segs.append((f"{IM_START}assistant\n{THINK_EMPTY}", False))
            segs.append((m["content"] + IM_END, True))
        else:
            segs.append((f"{IM_START}{m['role']}\n{m['content']}{IM_END}", False))
    return segs


def target_of(r):
    return {"segs": r["segs"]} if r.get("segs") else r["messages"]


def transcript_len(tok, messages):
    return sum(len(tok(t, add_special_tokens=False).input_ids) for t, _ in segments(messages, tok.bos_token or ""))


def steps_for(n_items):
    """Practice-2: optimizer steps scale with the lesson count (Practice-1: 576 items, 32 steps -> 18 items per step), floor N_STEPS, cap RG_MAX_STEPS."""
    return max(N_STEPS, min(RG_MAX_STEPS, round(n_items / 18)))


def build_lessons(arm, store, tok, seed, night, n_sft=N_SFT, epochs=EPOCHS, n_pairs=N_PAIRS, max_tokens=MAX_TRAIN_TOKENS, dedup=False):
    """store: per-try records of all days so far (id, correct, messages). Returns (items, stats). Same counts in both arms by construction.
    dedup (Practice-2): P = the shortest win of each solved puzzle (at most n_sft) and one pair per puzzle (shortest win vs a random failed try), no resampling with
    repetition; C = n_sft / n_pairs distinct random tries / random pairs, no repetition."""
    rng = random.Random(seed * 100003 + night * 17 + (1 if arm == "P" else 2))
    tlen = {}
    tries = []
    for r in store:
        n = transcript_len(tok, target_of(r))
        if n <= max_tokens:
            tries.append(r)
            tlen[id(r)] = n
    by = {}
    for r in tries:
        by.setdefault(r["id"], []).append(r)

    def fill(pool, n):
        if not pool:
            return []
        if len(pool) >= n:
            return rng.sample(pool, n)
        return list(pool) + [rng.choice(pool) for _ in range(n - len(pool))]  # resample with repetition

    def pick(pool, n):
        return list(pool) if len(pool) <= n else rng.sample(pool, n)

    if dedup and arm == "P":
        best = {}
        for r in tries:
            if r["correct"] and (r["id"] not in best or tlen[id(r)] < tlen[id(best[r["id"]])]):
                best[r["id"]] = r
        sft_src = pick(list(best.values()), n_sft)
        cands = []
        for pid, rs in by.items():
            f = [r for r in rs if not r["correct"]]
            if pid in best and f:
                cands.append((best[pid], rng.choice(f)))
        pairs = pick(cands, n_pairs)
    elif dedup:
        sft_src = pick(tries, n_sft)
        cands = []
        for pid, rs in by.items():
            if len(rs) >= 2:
                cands.append(tuple(rng.sample(rs, 2)))
        pairs = pick(cands, n_pairs)
    elif arm == "P":
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
    items = [{"kind": "sft", "prompt": "", "target": target_of(r)} for r in sft_src] * epochs
    items += [{"kind": "pair", "prompt": "", "chosen": target_of(a), "rejected": target_of(b)} for a, b in pairs]
    st = {"arm": arm, "night": night, "tries_in_store": len(store), "tries_usable": len(tries), "wins_in_store": sum(r["correct"] for r in tries),
          "sft_unique": len({(r["id"], r["try"]) for r in sft_src}), "sft_examples": len(sft_src) * epochs, "pairs": len(pairs),
          "pair_candidates": len(cands), "sft_correct_frac": round(sum(r["correct"] for r in sft_src) / max(1, len(sft_src)), 3),
          "pair_chosen_correct_frac": round(sum(a["correct"] for a, _ in pairs) / max(1, len(pairs)), 3),
          "pair_rejected_correct_frac": round(sum(b["correct"] for _, b in pairs) / max(1, len(pairs)), 3), "n_items": len(items)}
    return items, st


